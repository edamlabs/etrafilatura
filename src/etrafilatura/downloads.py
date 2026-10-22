"""Page downloading — same interface as trafilatura.downloads (fetch_url, fetch_response, is_live_page)."""

import ipaddress
import logging
import socket
from configparser import ConfigParser
from types import MappingProxyType
from typing import Any, Final
from urllib.parse import urlparse

import urllib3

from etrafilatura.settings import DEFAULT_CONFIG, Extractor
from etrafilatura.utils import Response

LOGGER = logging.getLogger(__package__)

DEFAULT_HEADERS: Final = MappingProxyType(
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (compatible; etrafilatura; +https://github.com/edamlabs/etrafilatura)",
    }
)

RETRY_STATUSES: Final = frozenset({429, 500, 502, 503, 504})
RETRY_METHODS: Final = frozenset({"GET", "HEAD"})
HTTP_OK: Final = 200
SUITABLE_TYPES: Final = ("html", "xml", "text")

_POOLS: dict[tuple[bool, int, int], urllib3.PoolManager] = {}


def _determine_headers(config: ConfigParser) -> dict[str, str]:
    """Headers from the configuration, over the defaults."""
    headers = dict(DEFAULT_HEADERS)
    agents = [
        agent.strip() for agent in config.get("DEFAULT", "USER_AGENTS", fallback="").splitlines() if agent.strip()
    ]
    headers["User-Agent"] = agents[0] if agents else headers["User-Agent"]
    if cookie := config.get("DEFAULT", "COOKIE", fallback=""):
        headers["Cookie"] = cookie
    return headers


def _get_retry_strategy(config: ConfigParser) -> urllib3.util.Retry:
    """Retry strategy honoring MAX_REDIRECTS."""
    redirects = config.getint("DEFAULT", "MAX_REDIRECTS", fallback=2)
    return urllib3.util.Retry(
        total=3,
        connect=3,
        read=3,
        redirect=redirects,
        backoff_factor=0.5,
        status_forcelist=sorted(RETRY_STATUSES),
        allowed_methods=sorted(RETRY_METHODS),
    )


def create_pool(**kwargs: Any) -> urllib3.PoolManager:
    """Build a connection pool manager."""
    kwargs.setdefault("cert_reqs", "CERT_REQUIRED")
    return urllib3.PoolManager(**kwargs)


def _initiate_pool(config: ConfigParser, no_ssl: bool = False) -> urllib3.PoolManager:
    """Return the shared pool for these download settings, creating it on first use."""
    timeout = config.getint("DEFAULT", "DOWNLOAD_TIMEOUT", fallback=30)
    max_size = config.getint("DEFAULT", "MAX_FILE_SIZE", fallback=20_000_000)
    key = (no_ssl, timeout, max_size)
    pool = _POOLS.get(key)
    if pool is None:
        kwargs: dict[str, Any] = {
            "headers": _determine_headers(config),
            "retries": _get_retry_strategy(config),
            "timeout": urllib3.Timeout(total=timeout, connect=timeout),
            "num_pools": 20,
        }
        if no_ssl:
            kwargs.update(cert_reqs="CERT_NONE", assert_hostname=False)
        pool = _POOLS[key] = create_pool(**kwargs)
    return pool


def _vet_host(url: str, config: ConfigParser) -> None:
    """Refuse non-public IP addresses when SSRF protection is on."""
    if not config.getboolean("DEFAULT", "SSRF_PROTECTION", fallback=True):
        return
    host = urlparse(url).hostname
    if host is None:
        message = "no host in URL"
        raise ValueError(message)
    for info in socket.getaddrinfo(host, None):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            message = f"blocked non-public IP address: {ip}"
            raise ValueError(message)


def _send_request(url: str, config: ConfigParser, *, no_ssl: bool) -> Response:
    """One GET request, capped at MAX_FILE_SIZE bytes."""
    _vet_host(url, config)
    max_size = config.getint("DEFAULT", "MAX_FILE_SIZE", fallback=20_000_000)
    pool = _initiate_pool(config, no_ssl)
    raw = pool.request("GET", url, preload_content=False)
    try:
        data = raw.read(max_size + 1)
    finally:
        raw.release_conn()
    response = Response(data=data, status=raw.status, url=url)
    response.store_headers(dict(raw.headers))
    return response


def _is_suitable_response(url: str, response: Response, options: Extractor) -> bool:
    """Status, content type and size checks before handing the page to extraction."""
    if response.status != HTTP_OK:
        LOGGER.warning("not a 200 response: %s %s", response.status, url)
        return False
    content_type = (response.headers or {}).get("content-type", "")
    if content_type and not any(kind in content_type for kind in SUITABLE_TYPES):
        LOGGER.warning("unfit content type: %s %s", content_type, url)
        return False
    if not response.data:
        LOGGER.warning("no body: %s", url)
        return False
    if len(response.data) < options.min_file_size:
        LOGGER.warning("too small: %s %s", len(response.data), url)
        return False
    if len(response.data) > options.max_file_size:
        LOGGER.warning("too large: %s %s", len(response.data), url)
        return False
    return True


def fetch_url(
    url: str,
    no_ssl: bool = False,
    config: ConfigParser = DEFAULT_CONFIG,
    options: Extractor | None = None,
) -> str | None:
    """Download a web page and seamlessly decode the response.

    Args:
        url: URL of the page to fetch.
        no_ssl: Do not try to establish a secure connection (to prevent SSLError).
        config: Pass configuration values for output control.
        options: Extraction options (supersedes config).

    Returns:
        Unicode string or None in case of failed downloads and invalid results.
    """
    config = options.config if options else config
    response = fetch_response(url, decode=True, no_ssl=no_ssl, config=config)
    if not response or not response.data:
        return None
    options = options or Extractor(config=config)
    return response.html if _is_suitable_response(url, response, options) else None


def fetch_response(
    url: str,
    *,
    decode: bool = False,
    no_ssl: bool = False,
    with_headers: bool = False,  # noqa: ARG001  # deprecated, kept for API compatibility
    config: ConfigParser = DEFAULT_CONFIG,
) -> Response | None:
    """Download a web page and return a full response object.

    Args:
        url: URL of the page to fetch.
        decode: Use html attribute to decode the data (boolean).
        no_ssl: Don't try to establish a secure connection (to prevent SSLError).
        with_headers: Deprecated and ignored, headers are always stored.
        config: Pass configuration values for output control.

    Returns:
        Response object or None in case of failed downloads and invalid results.
    """
    LOGGER.debug("sending request: %s", url)
    try:
        response = _send_request(url, config, no_ssl=no_ssl)
    except urllib3.exceptions.SSLError as err:
        if not config.getboolean("DEFAULT", "INSECURE_SSL_FALLBACK", fallback=True):
            LOGGER.error("SSL error, INSECURE_SSL_FALLBACK is off: %s %s", url, err)
            return None
        LOGGER.warning("retrying after SSL error: %s %s", url, err)
        try:
            response = _send_request(url, config, no_ssl=True)
        except (urllib3.exceptions.HTTPError, OSError, ValueError) as failure:
            LOGGER.warning("request failed: %s %s", url, failure)
            return None
    except (urllib3.exceptions.HTTPError, OSError, ValueError) as err:
        ### ValueError is the SSRF guard refusing a non-public address.
        LOGGER.warning("request failed: %s %s", url, err)
        return None
    response.decode_data(decode=decode, max_size=config.getint("DEFAULT", "MAX_FILE_SIZE"))
    return response


def is_live_page(url: str, config: ConfigParser = DEFAULT_CONFIG) -> bool:
    """Send a basic HTTP HEAD request and report whether the page answers 200."""
    try:
        _vet_host(url, config)
        raw = _initiate_pool(config).request("HEAD", url, preload_content=False)
    except (urllib3.exceptions.HTTPError, OSError, ValueError) as err:
        LOGGER.debug("HEAD request failed: %s %s", url, err)
        return False
    raw.release_conn()
    return raw.status == HTTP_OK

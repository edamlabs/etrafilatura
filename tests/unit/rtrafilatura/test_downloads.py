"""Downloading: pools, guards, suitability and the public verbs."""

import gzip
import logging
from collections.abc import Callable
from configparser import ConfigParser

import pytest
import urllib3

from rtrafilatura import downloads
from rtrafilatura.downloads import (
    _determine_headers,
    _get_retry_strategy,
    _initiate_pool,
    fetch_response,
    fetch_url,
    is_live_page,
)
from rtrafilatura.settings import Extractor, use_config
from rtrafilatura.utils import Response

pytestmark = pytest.mark.usefixtures("clear_pools")


##### FETCH_URL #####


def test_fetch_url_article(server: str, open_config: ConfigParser) -> None:
    page = fetch_url(f"{server}/article", config=open_config)
    assert page is not None
    assert "Quiet Revolution" in page


def test_fetch_url_gzip_route(server: str, open_config: ConfigParser) -> None:
    page = fetch_url(f"{server}/gzip", config=open_config)
    assert page is not None
    assert page.startswith(gzip.decompress(gzip.compress(page.encode()))[:20].decode())


def test_fetch_url_404(server: str, open_config: ConfigParser) -> None:
    assert fetch_url(f"{server}/missing", config=open_config) is None


def test_fetch_url_wrong_type(server: str, open_config: ConfigParser) -> None:
    assert fetch_url(f"{server}/data", config=open_config) is None


def test_fetch_url_too_small(server: str, make_config: Callable[..., ConfigParser]) -> None:
    config = make_config(SSRF_PROTECTION="off", MIN_FILE_SIZE="10")
    assert fetch_url(f"{server}/tiny", config=config) is None


def test_fetch_url_too_large(server: str, make_config: Callable[..., ConfigParser]) -> None:
    config = make_config(SSRF_PROTECTION="off", MAX_FILE_SIZE="1000")
    assert fetch_url(f"{server}/article", config=config) is None


def test_fetch_url_options_supersede(server: str, open_config: ConfigParser) -> None:
    options = Extractor(config=open_config)
    assert fetch_url(f"{server}/article", options=options) is not None


def test_fetch_url_bad_host(open_config: ConfigParser) -> None:
    assert fetch_url("http://no-such-host.invalid/page", config=open_config) is None


def test_fetch_url_ssrf_guard(server: str) -> None:
    assert fetch_url(f"{server}/article") is None


def test_fetch_url_no_host() -> None:
    assert fetch_url("notaurl") is None


##### FETCH_RESPONSE #####


def test_fetch_response_decode(server: str, open_config: ConfigParser) -> None:
    response = fetch_response(f"{server}/article", decode=True, config=open_config)
    assert isinstance(response, Response)
    assert response.status == 200
    assert response.headers is not None
    assert response.html is not None


def test_fetch_response_raw(server: str, open_config: ConfigParser) -> None:
    response = fetch_response(f"{server}/article", config=open_config)
    assert response is not None
    assert response.html is None
    assert response.data


def test_fetch_response_failure(open_config: ConfigParser) -> None:
    assert fetch_response("http://no-such-host.invalid/", config=open_config) is None


def test_fetch_response_ssl_fallback(open_config: ConfigParser, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    def guarded(url: str, _config: ConfigParser, *, no_ssl: bool) -> Response:
        calls.append(no_ssl)
        if not no_ssl:
            raise urllib3.exceptions.SSLError("boom")
        return Response(data=b"<html>ok</html>", status=200, url=url)

    monkeypatch.setattr(downloads, "_send_request", guarded)
    response = fetch_response("https://example.org", decode=True, config=open_config)
    assert calls == [False, True]
    assert response is not None
    assert response.html == "<html>ok</html>"


def test_fetch_response_ssl_refused(open_config: ConfigParser, monkeypatch: pytest.MonkeyPatch) -> None:
    config = use_config()
    config.set("DEFAULT", "SSRF_PROTECTION", "off")
    config.set("DEFAULT", "INSECURE_SSL_FALLBACK", "off")

    def failing(_url: str, _config: ConfigParser, *, no_ssl: bool) -> Response:
        raise urllib3.exceptions.SSLError("boom")

    monkeypatch.setattr(downloads, "_send_request", failing)
    assert fetch_response("https://example.org", config=config) is None


def test_fetch_response_ssl_retry_fails(open_config: ConfigParser, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(_url: str, _config: ConfigParser, *, no_ssl: bool) -> Response:
        raise urllib3.exceptions.SSLError("boom")

    monkeypatch.setattr(downloads, "_send_request", failing)
    assert fetch_response("https://example.org", config=open_config) is None


##### IS_LIVE_PAGE #####


def test_is_live_page_status(server: str, open_config: ConfigParser) -> None:
    assert is_live_page(f"{server}/article", config=open_config) is True
    assert is_live_page(f"{server}/missing", config=open_config) is False


def test_is_live_page_guarded(server: str) -> None:
    assert is_live_page(f"{server}/article") is False


##### INTERNALS #####


def test_determine_headers_config(make_config: Callable[..., ConfigParser]) -> None:
    plain = _determine_headers(use_config())
    assert plain["User-Agent"].startswith("Mozilla")
    config = make_config(USER_AGENTS="agent-one\nagent-two", COOKIE="a=b")
    headers = _determine_headers(config)
    assert headers["User-Agent"] == "agent-one"
    assert headers["Cookie"] == "a=b"


def test_get_retry_strategy_redirects() -> None:
    strategy = _get_retry_strategy(use_config())
    assert strategy.redirect == 2


def test_vet_host_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    """The guard walks every resolved address: public passes, a private tail is refused."""
    public = [(None, None, None, None, ("93.184.216.34", 0)), (None, None, None, None, ("93.184.216.35", 0))]
    monkeypatch.setattr(downloads.socket, "getaddrinfo", lambda *_args: public)
    downloads._vet_host("https://example.org/page", use_config())

    mixed = [public[0], (None, None, None, None, ("10.0.0.1", 0))]
    monkeypatch.setattr(downloads.socket, "getaddrinfo", lambda *_args: mixed)
    with pytest.raises(ValueError, match="non-public"):
        downloads._vet_host("https://example.org/page", use_config())


def test_is_suitable_response_body() -> None:
    options = Extractor()
    empty = Response(data=b"", status=200, url="u")
    empty.store_headers({"Content-Type": "text/html"})
    assert downloads._is_suitable_response("u", empty, options) is False

    untyped = Response(data=b"<html>ok</html>", status=200, url="u")
    untyped.store_headers({})
    assert downloads._is_suitable_response("u", untyped, options) is True


@pytest.mark.parametrize(
    ("data", "head", "logged"),
    [
        (b"<html>ok</html>", (404, "text/html"), "not a 200 response: 404 u"),
        (b"", (404, "text/html"), "not a 200 response: 404 u"),
        (b"<html>ok</html>", (200, "application/json"), "unfit content type: application/json u"),
        (b"", (200, "text/html"), "no body: u"),
        (b"<p>", (200, "text/html"), "too small: 3 u"),
        (b"<html>" + b"x" * 30 + b"</html>", (200, "text/html"), "too large: 43 u"),
    ],
    ids=["status", "status-before-body", "content-type", "body", "too-small", "too-large"],
)
def test_is_suitable_response_rules(
    make_config: Callable[..., ConfigParser],
    caplog: pytest.LogCaptureFixture,
    data: bytes,
    head: tuple[int, str],
    logged: str,
) -> None:
    options = Extractor(config=make_config(MIN_FILE_SIZE="5", MAX_FILE_SIZE="40"))
    status, content_type = head
    response = Response(data=data, status=status, url="u")
    response.store_headers({"Content-Type": content_type})
    assert downloads._is_suitable_response("u", response, options) is False
    assert [record.getMessage() for record in caplog.records] == [logged]


def test_initiate_pool_caching(open_config: ConfigParser) -> None:
    first = _initiate_pool(open_config)
    assert _initiate_pool(open_config) is first
    insecure = _initiate_pool(open_config, no_ssl=True)
    assert insecure is not first
    assert insecure.connection_pool_kw["cert_reqs"] == "CERT_NONE"


def test_fetch_response_logs(server: str, open_config: ConfigParser, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        fetch_response(f"{server}/article", config=open_config)
    assert "sending request" in caplog.text

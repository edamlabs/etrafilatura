"""Downloading: pools, guards, suitability and the public verbs."""

import gzip
import logging

import pytest
import urllib3

from etrafilatura import downloads
from etrafilatura.downloads import (
    _determine_headers,
    _get_retry_strategy,
    _initiate_pool,
    fetch_response,
    fetch_url,
    is_live_page,
)
from etrafilatura.settings import Extractor, use_config
from etrafilatura.utils import Response


@pytest.fixture
def open_config(make_config) -> object:  # type: ignore[no-untyped-def]
    """Config with the SSRF guard off: the test server is localhost."""
    return make_config(SSRF_PROTECTION="off")  # type: ignore[operator]


@pytest.fixture(autouse=True)
def clear_pools() -> object:
    """Every test starts with a fresh pool table."""
    downloads._POOLS.clear()
    yield
    downloads._POOLS.clear()


##### fetch_url #####


def test_downloads_fetch_url(server: str, open_config) -> None:  # type: ignore[no-untyped-def]
    page = fetch_url(f"{server}/article", config=open_config)  # type: ignore[arg-type]
    assert page is not None
    assert "Quiet Revolution" in page


def test_downloads_fetch_url_gzip_route(server: str, open_config) -> None:  # type: ignore[no-untyped-def]
    page = fetch_url(f"{server}/gzip", config=open_config)  # type: ignore[arg-type]
    assert page is not None
    assert page.startswith(gzip.decompress(gzip.compress(page.encode()))[:20].decode())


def test_downloads_fetch_url_404(server: str, open_config) -> None:  # type: ignore[no-untyped-def]
    assert fetch_url(f"{server}/missing", config=open_config) is None  # type: ignore[arg-type]


def test_downloads_fetch_url_wrong_type(server: str, open_config) -> None:  # type: ignore[no-untyped-def]
    assert fetch_url(f"{server}/data", config=open_config) is None  # type: ignore[arg-type]


def test_downloads_fetch_url_too_small(server: str, make_config) -> None:  # type: ignore[no-untyped-def]
    config = make_config(SSRF_PROTECTION="off", MIN_FILE_SIZE="10")  # type: ignore[operator]
    assert fetch_url(f"{server}/tiny", config=config) is None  # type: ignore[arg-type]


def test_downloads_fetch_url_too_large(server: str, make_config) -> None:  # type: ignore[no-untyped-def]
    config = make_config(SSRF_PROTECTION="off", MAX_FILE_SIZE="1000")  # type: ignore[operator]
    assert fetch_url(f"{server}/article", config=config) is None  # type: ignore[arg-type]


def test_downloads_fetch_url_options_supersede(server: str, open_config) -> None:  # type: ignore[no-untyped-def]
    options = Extractor(config=open_config)  # type: ignore[arg-type]
    assert fetch_url(f"{server}/article", options=options) is not None


def test_downloads_fetch_url_bad_host(open_config) -> None:  # type: ignore[no-untyped-def]
    assert fetch_url("http://no-such-host.invalid/page", config=open_config) is None  # type: ignore[arg-type]


def test_downloads_fetch_url_ssrf_guard(server: str) -> None:
    assert fetch_url(f"{server}/article") is None


def test_downloads_fetch_url_no_host() -> None:
    assert fetch_url("notaurl") is None


##### fetch_response #####


def test_downloads_fetch_response_decode(server: str, open_config) -> None:  # type: ignore[no-untyped-def]
    response = fetch_response(f"{server}/article", decode=True, config=open_config)  # type: ignore[arg-type]
    assert isinstance(response, Response)
    assert response.status == 200
    assert response.headers is not None
    assert response.html is not None


def test_downloads_fetch_response_raw(server: str, open_config) -> None:  # type: ignore[no-untyped-def]
    response = fetch_response(f"{server}/article", config=open_config)  # type: ignore[arg-type]
    assert response is not None
    assert response.html is None
    assert response.data


def test_downloads_fetch_response_failure(open_config) -> None:  # type: ignore[no-untyped-def]
    assert fetch_response("http://no-such-host.invalid/", config=open_config) is None  # type: ignore[arg-type]


def test_downloads_fetch_response_ssl_fallback(open_config, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[bool] = []

    def guarded(url: str, _config, *, no_ssl: bool):  # type: ignore[no-untyped-def]
        calls.append(no_ssl)
        if not no_ssl:
            raise urllib3.exceptions.SSLError("boom")
        return Response(data=b"<html>ok</html>", status=200, url=url)

    monkeypatch.setattr(downloads, "_send_request", guarded)
    response = fetch_response("https://example.org", decode=True, config=open_config)  # type: ignore[arg-type]
    assert calls == [False, True]
    assert response is not None
    assert response.html == "<html>ok</html>"


def test_downloads_fetch_response_ssl_refused(open_config, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    config = use_config()
    config.set("DEFAULT", "SSRF_PROTECTION", "off")
    config.set("DEFAULT", "INSECURE_SSL_FALLBACK", "off")

    def failing(_url: str, _config, *, no_ssl: bool):  # type: ignore[no-untyped-def]
        raise urllib3.exceptions.SSLError("boom")

    monkeypatch.setattr(downloads, "_send_request", failing)
    assert fetch_response("https://example.org", config=config) is None


def test_downloads_fetch_response_ssl_retry_fails(open_config, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    def failing(_url: str, _config, *, no_ssl: bool):  # type: ignore[no-untyped-def]
        raise urllib3.exceptions.SSLError("boom")

    monkeypatch.setattr(downloads, "_send_request", failing)
    assert fetch_response("https://example.org", config=open_config) is None  # type: ignore[arg-type]


##### is_live_page #####


def test_downloads_is_live_page(server: str, open_config) -> None:  # type: ignore[no-untyped-def]
    assert is_live_page(f"{server}/article", config=open_config) is True  # type: ignore[arg-type]
    assert is_live_page(f"{server}/missing", config=open_config) is False  # type: ignore[arg-type]


def test_downloads_is_live_page_guarded(server: str) -> None:
    assert is_live_page(f"{server}/article") is False


##### internals #####


def test_downloads_headers(make_config) -> None:  # type: ignore[no-untyped-def]
    plain = _determine_headers(use_config())
    assert plain["User-Agent"].startswith("Mozilla")
    config = make_config(USER_AGENTS="agent-one\nagent-two", COOKIE="a=b")  # type: ignore[operator]
    headers = _determine_headers(config)  # type: ignore[arg-type]
    assert headers["User-Agent"] == "agent-one"
    assert headers["Cookie"] == "a=b"


def test_downloads_retry_strategy() -> None:
    strategy = _get_retry_strategy(use_config())
    assert strategy.redirect == 2


def test_downloads_vet_host_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    """The guard walks every resolved address: public passes, a private tail is refused."""
    public = [(None, None, None, None, ("93.184.216.34", 0)), (None, None, None, None, ("93.184.216.35", 0))]
    monkeypatch.setattr(downloads.socket, "getaddrinfo", lambda *_args: public)
    downloads._vet_host("https://example.org/page", use_config())

    mixed = [public[0], (None, None, None, None, ("10.0.0.1", 0))]
    monkeypatch.setattr(downloads.socket, "getaddrinfo", lambda *_args: mixed)
    with pytest.raises(ValueError, match="non-public"):
        downloads._vet_host("https://example.org/page", use_config())


def test_downloads_suitability() -> None:
    options = Extractor()
    empty = Response(data=b"", status=200, url="u")
    empty.store_headers({"Content-Type": "text/html"})
    assert downloads._is_suitable_response("u", empty, options) is False

    untyped = Response(data=b"<html>ok</html>", status=200, url="u")
    untyped.store_headers({})
    assert downloads._is_suitable_response("u", untyped, options) is True


def test_downloads_pool_caching(open_config) -> None:  # type: ignore[no-untyped-def]
    first = _initiate_pool(open_config)  # type: ignore[arg-type]
    assert _initiate_pool(open_config) is first  # type: ignore[arg-type]
    insecure = _initiate_pool(open_config, no_ssl=True)  # type: ignore[arg-type]
    assert insecure is not first
    assert insecure.connection_pool_kw["cert_reqs"] == "CERT_NONE"


def test_downloads_send_request_logs(server: str, open_config, caplog: pytest.LogCaptureFixture) -> None:  # type: ignore[no-untyped-def]
    with caplog.at_level(logging.DEBUG):
        fetch_response(f"{server}/article", config=open_config)  # type: ignore[arg-type]
    assert "sending request" in caplog.text

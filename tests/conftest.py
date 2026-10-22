"""Session fixtures shared across the suite."""

import functools
import gzip
import http.server
import threading
from collections.abc import Callable, Iterator
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Final

import pytest

from etrafilatura.deduplication import LRU_TEST
from etrafilatura.settings import use_config

RESOURCES: Final = Path(__file__).parent / "resources"
HTML_DIR: Final = RESOURCES / "html"

ARTICLE: Final = (HTML_DIR / "article.html").read_text(encoding="utf-8")


##### PAGES #####


@pytest.fixture(scope="session")
def resources() -> Path:
    """Root of the fixture tree."""
    return RESOURCES


@pytest.fixture(scope="session")
def page_of() -> Callable[[str], str]:
    """Reader returning the source of an HTML fixture by filename."""

    def _read(name: str) -> str:
        return (HTML_DIR / name).read_text(encoding="utf-8")

    return _read


@pytest.fixture(scope="session")
def article() -> str:
    """An English article page with boilerplate around it."""
    return ARTICLE


@pytest.fixture(scope="session")
def comments_page(page_of: Callable[[str], str]) -> str:
    """An article page with a comments section and JSON-LD metadata."""
    return page_of("comments.html")


@pytest.fixture(scope="session")
def metadata_page(page_of: Callable[[str], str]) -> str:
    """A Spanish page rich in meta, OpenGraph and JSON-LD metadata."""
    return page_of("metadata.html")


@pytest.fixture(scope="session")
def tables_page(page_of: Callable[[str], str]) -> str:
    """An article page built around a table."""
    return page_of("tables.html")


@pytest.fixture(scope="session")
def minimal_page(page_of: Callable[[str], str]) -> str:
    """A page with almost no content."""
    return page_of("minimal.html")


@pytest.fixture(scope="session")
def empty_page(page_of: Callable[[str], str]) -> str:
    """A page with an empty body."""
    return page_of("empty.html")


##### CONFIG #####


@pytest.fixture
def make_config() -> Callable[..., ConfigParser]:
    """Factory returning a ConfigParser seeded with the defaults plus overrides."""

    def _make(**overrides: str) -> ConfigParser:
        config = use_config()
        config.read_dict({"DEFAULT": {key.upper(): value for key, value in overrides.items()}})
        return config

    return _make


@pytest.fixture(autouse=True)
def reset_lru() -> Iterator[None]:
    """The global dedup cache never leaks between tests."""
    yield
    LRU_TEST.clear()


##### SERVER #####


class _Handler(http.server.BaseHTTPRequestHandler):
    """Routes: /article (html), /missing (404), /data (json), /tiny (1 byte), /gzip (compressed)."""

    def log_message(self, format: str, *args: Any) -> None:
        """Silence the request log."""

    def _respond(self, body: bytes, status: int, content_type: str, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:
        """Serve the fixture routes."""
        self.route()

    def do_HEAD(self) -> None:
        """Serve the fixture routes without a body."""
        self.route()

    def route(self) -> None:
        """One route table for GET and HEAD."""
        path = self.path.split("?")[0]
        routes = {
            "/article": functools.partial(self._respond, ARTICLE.encode(), 200, "text/html; charset=utf-8"),
            "/missing": functools.partial(self._respond, b"nope", 404, "text/html"),
            "/data": functools.partial(self._respond, b'{"a": 1}', 200, "application/json"),
            "/tiny": functools.partial(self._respond, b"x", 200, "text/html"),
            "/gzip": functools.partial(
                self._respond, gzip.compress(ARTICLE.encode()), 200, "text/html", {"Content-Encoding": "identity"}
            ),
        }
        handler = routes.get(path)
        if handler is None:
            self._respond(b"nope", 404, "text/html")
        else:
            handler()


@pytest.fixture(scope="session")
def server() -> Iterator[str]:
    """A local HTTP server on a random port; yields its base URL."""
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    thread.join(timeout=5)
    httpd.server_close()

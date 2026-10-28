"""Fixtures shared by the rtrafilatura unit modules."""

from collections.abc import Callable, Iterator
from configparser import ConfigParser

import pytest
from lxml.etree import _Element, fromstring
from lxml.html import HtmlElement, fragment_fromstring

from rtrafilatura import downloads, source
from rtrafilatura.settings import Document

##### CONFIG #####


@pytest.fixture
def open_config(make_config: Callable[..., ConfigParser]) -> ConfigParser:
    """Config with the SSRF guard off: the test server is localhost."""
    return make_config(SSRF_PROTECTION="off")


##### NETWORK #####


@pytest.fixture
def clear_pools() -> Iterator[None]:
    """A fresh pool table before and after the test."""
    downloads._POOLS.clear()
    yield
    downloads._POOLS.clear()


@pytest.fixture
def no_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any download attempt fails the test."""

    def refuse(*args: object, **kwargs: object) -> None:
        pytest.fail("fetched without opt-in")

    monkeypatch.setattr(source, "fetch_response", refuse)


##### TREES #####


@pytest.fixture
def body_of() -> Callable[[str], _Element]:
    """Builder of a `<body>` tree around an XML fragment."""

    def _build(markup: str) -> _Element:
        return fromstring(f"<body>{markup}</body>")

    return _build


@pytest.fixture
def element_of() -> Callable[[str], HtmlElement]:
    """Builder of an HTML `<body><div><p>` element around a text."""

    def _build(text: str) -> HtmlElement:
        return fragment_fromstring(f"<div><p>{text}</p></div>", create_parent="body")

    return _build


@pytest.fixture
def document(body_of: Callable[[str], _Element]) -> Document:
    """A populated document with a trafilatura-vocabulary body and comments."""
    return Document(
        title="Title: colon",
        author="Author Name",
        url="https://example.org/page",
        hostname="example.org",
        date="2026-01-02",
        categories=["news", "tech"],
        tags=["rust"],
        idval="id-1",
        license_val="CC-BY",
        body=body_of('<head rend="h1">Heading</head><p>Hello <hi rend="#b">world</hi></p>'),
        commentsbody=body_of("<p>Nice post</p>"),
        comments="Nice post",
        raw_text="Hello world",
    )

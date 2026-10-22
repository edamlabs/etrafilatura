"""Input resolution: input_format="auto" fetches URLs and reads paths; the default never does."""

from collections.abc import Callable
from configparser import ConfigParser
from pathlib import Path

import pytest

from etrafilatura import source
from etrafilatura.core import bare_extraction, extract
from etrafilatura.metadata import extract_metadata
from etrafilatura.settings import Document, Extractor
from etrafilatura.source import MAX_PATH_LENGTH, AutoSource
from etrafilatura.utils import Response

##### DEFAULT: TRAFILATURA'S BEHAVIOUR #####


@pytest.mark.usefixtures("no_fetch")
@pytest.mark.parametrize(
    "text",
    ["https://example.org/article", "tests/resources/html/article.html"],
    ids=["url", "path"],
)
def test_extract_string_is_html(text: str) -> None:
    assert extract(text) is None


def test_extract_path_object(tmp_path: Path, article: str) -> None:
    page = tmp_path / "article.html"
    page.write_text(article, encoding="utf-8")
    assert extract(page) == extract(article)


def test_extract_path_too_large(
    tmp_path: Path, article: str, make_config: Callable[..., ConfigParser], caplog: pytest.LogCaptureFixture
) -> None:
    page = tmp_path / "article.html"
    page.write_text(article, encoding="utf-8")
    assert extract(page, config=make_config(MAX_FILE_SIZE="100")) is None
    assert "file too large" in caplog.text


def test_extract_path_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract(tmp_path / "missing.html")


##### AUTO #####


def test_extract_auto_url(server: str, open_config: ConfigParser, article: str) -> None:
    assert extract(f"{server}/article", input_format="auto", config=open_config) == extract(article)


def test_extract_auto_url_options_untouched(server: str, open_config: ConfigParser) -> None:
    options = Extractor(config=open_config, with_metadata=True)
    document = bare_extraction(f"{server}/article", options=options, input_format="auto")
    assert isinstance(document, Document)
    ### The page's canonical URL wins over the fetched one, as trafilatura ranks meta over default_url.
    assert document.url == "https://example.org/posts/small-tools"
    assert options.url is None


def test_extract_auto_url_unreachable(server: str, open_config: ConfigParser) -> None:
    assert extract(f"{server}/missing", input_format="auto", config=open_config) is None


def test_extract_auto_path(tmp_path: Path, article: str) -> None:
    page = tmp_path / "article.html"
    page.write_text(article, encoding="utf-8")
    assert extract(f"  {page}\n", input_format="auto") == extract(article)


@pytest.mark.usefixtures("no_fetch")
@pytest.mark.parametrize(
    "text",
    [
        "https://example.org/a b",
        "ftp://example.org/page.html",
        "missing-file.html",
        "x" * (MAX_PATH_LENGTH + 1),
        "a\x00b",
        "x" * 300,
    ],
    ids=["url-with-space", "other-scheme", "missing-path", "too-long", "nul-byte", "name-too-long"],
)
def test_extract_auto_falls_back_to_html(text: str) -> None:
    assert extract(text, input_format="auto") is None


@pytest.mark.usefixtures("no_fetch")
def test_extract_auto_html(article: str) -> None:
    assert extract(article, input_format="auto") == extract(article)


def test_extract_unknown_input_format(article: str) -> None:
    with pytest.raises(ValueError, match="FormatSource"):
        extract(article, input_format="pdf")


##### METADATA #####


def test_extract_metadata_auto_url(monkeypatch: pytest.MonkeyPatch, metadata_page: str) -> None:
    response = Response(metadata_page.encode(), 200, "https://example.org/final")
    response.html = metadata_page
    monkeypatch.setattr(source, "fetch_response", lambda *args, **kwargs: response)
    document = extract_metadata("https://example.org/start", input_format="auto")
    assert document.title == extract_metadata(metadata_page).title


def test_extract_metadata_auto_url_refused() -> None:
    ### The default config keeps the SSRF guard on: localhost is never fetched.
    assert extract_metadata("http://127.0.0.1:9/page", input_format="auto").title is None


##### BIND #####


def test_autosource_bind_without_url() -> None:
    options = Extractor()
    assert AutoSource.bind(options, None) is options


def test_autosource_bind_fetched_url() -> None:
    options = Extractor()
    bound = AutoSource.bind(options, "https://example.org/final")
    assert (bound.url, bound.source, options.url) == ("https://example.org/final", "https://example.org/final", None)


def test_autosource_bind_caller_url() -> None:
    options = Extractor(url="https://example.org/given")
    assert AutoSource.bind(options, "https://example.org/final") is options

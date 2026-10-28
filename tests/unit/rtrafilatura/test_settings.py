"""Configuration objects: use_config, Extractor, Document."""

import logging
from collections.abc import Callable
from configparser import ConfigParser
from pathlib import Path

import pytest
from lxml.etree import Element
from lxml.html import fromstring

from rtrafilatura.deduplication import LRUCache
from rtrafilatura.settings import (
    BASIC_CLEAN_XPATH,
    DEFAULT_CONFIG,
    INLINE_CARRIED,
    INLINE_CONSUMING,
    INLINE_FORMATTABLE,
    SUPPORTED_FORMATS,
    Document,
    Extractor,
    set_date_params,
    use_config,
)

##### USE_CONFIG #####


def test_use_config_defaults() -> None:
    config = use_config()
    assert config.getint("DEFAULT", "MIN_EXTRACTED_SIZE") == 250
    assert config.getint("DEFAULT", "DOWNLOAD_TIMEOUT") == 30
    assert DEFAULT_CONFIG.get("DEFAULT", "SSRF_PROTECTION") == "on"


def test_use_config_passthrough() -> None:
    config = ConfigParser()
    assert use_config(config=config) is config


def test_use_config_file(tmp_path: Path) -> None:
    override = tmp_path / "custom.cfg"
    override.write_text("[DEFAULT]\nMIN_EXTRACTED_SIZE = 50\n", encoding="utf-8")
    config = use_config(str(override))
    assert config.getint("DEFAULT", "MIN_EXTRACTED_SIZE") == 50
    assert config.getint("DEFAULT", "MIN_OUTPUT_SIZE") == 1


def test_use_config_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        use_config("/nonexistent/settings.cfg")


def test_extractor_config_none_falls_back() -> None:
    assert Extractor(config=None).config is DEFAULT_CONFIG


##### EXTRACTOR #####


def test_extractor_defaults() -> None:
    options = Extractor()
    assert options.format == "txt"
    assert options.focus == "balanced"
    assert options.formatting is False
    assert options.with_metadata is False
    assert options.max_tree_size is None
    assert options.author_blacklist == set()
    assert options.date_params["extensive_search"] is True


def test_extractor_markdown_implies_formatting() -> None:
    assert Extractor(output_format="markdown").formatting is True
    assert Extractor(output_format="markdown", formatting=False).formatting is False


def test_extractor_focus(caplog: pytest.LogCaptureFixture) -> None:
    assert Extractor(precision=True).focus == "precision"
    assert Extractor(recall=True).focus == "recall"
    with caplog.at_level(logging.WARNING):
        assert Extractor(precision=True, recall=True).focus == "recall"
    assert "mutually exclusive" in caplog.text


def test_extractor_invalid_format() -> None:
    with pytest.raises(AttributeError, match="Cannot set format"):
        Extractor(output_format="pdf")
    with pytest.raises(AttributeError, match="Cannot set format"):
        Extractor(output_format="yaml")


def test_extractor_format_universe() -> None:
    assert {"csv", "html", "json", "markdown", "python", "txt", "xml", "xmltei"} == SUPPORTED_FORMATS


def test_extractor_warnings(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        Extractor(tei_validation=True, output_format="xml")
        Extractor(formatting=True, output_format="json")
    assert "tei_validation has no effect" in caplog.text
    assert "include_formatting has no effect" in caplog.text


def test_extractor_with_metadata_derived() -> None:
    assert Extractor(url_blacklist={"x"}).with_metadata is True
    assert Extractor(author_blacklist={"y"}).with_metadata is True
    assert Extractor(only_with_metadata=True).with_metadata is True
    assert Extractor(output_format="xmltei").with_metadata is True


def test_extractor_source_and_thresholds(make_config: Callable[..., ConfigParser]) -> None:
    config = make_config(MAX_TREE_SIZE="100000", MIN_FILE_SIZE="64")
    options = Extractor(config=config, url="https://example.org/page")
    assert options.source == "https://example.org/page"
    assert options.max_tree_size == 100000
    assert options.min_file_size == 64
    assert Extractor(config=config, source="src").source == "src"


def test_extractor_max_tree_size_non_numeric(make_config: Callable[..., ConfigParser]) -> None:
    config = make_config(MAX_TREE_SIZE="abc")
    assert Extractor(config=config).max_tree_size is None


def test_extractor_dedup_instance() -> None:
    cache = LRUCache(maxsize=4)
    assert Extractor(dedup=cache).dedup is cache


##### DOCUMENT #####


def test_document_defaults_and_as_dict() -> None:
    document = Document()
    assert document.body.tag == "body"
    assert document.commentsbody.tag == "body"
    data = document.as_dict()
    assert data["title"] is None
    assert set(data) == set(Document.__slots__)


def test_document_explicit_trees() -> None:
    body = Element("body")
    document = Document(body=body, commentsbody=body)
    assert document.body is body


def test_document_from_dict_roundtrip() -> None:
    document = Document.from_dict({"title": "T", "text": "body"})
    assert document.title == "T"
    assert document.as_dict()["text"] == "body"


def test_document_clean_and_trim() -> None:
    document = Document(title="A &amp; B  ", description="x" * 12000)
    document.clean_and_trim()
    assert document.title == "A & B"
    assert document.description is not None
    assert document.description.endswith("…")
    assert len(document.description) == 10000


def test_document_clean_and_trim_to_none() -> None:
    document = Document(title="   ")
    document.clean_and_trim()
    assert document.title is None


##### HELPERS #####


def test_set_date_params() -> None:
    params = set_date_params(False)
    assert params["original_date"] is True
    assert params["extensive_search"] is False
    assert "max_date" in params


def test_inline_ladder() -> None:
    assert {"hi", "ref", "del"} == INLINE_CONSUMING
    assert INLINE_CONSUMING | {"code"} == INLINE_FORMATTABLE
    assert INLINE_FORMATTABLE | {"graphic"} == INLINE_CARRIED


def test_basic_clean_xpath() -> None:
    tree = fromstring('<html><body><aside>x</aside><footer class="cookie-banner">c</footer><p>keep</p></body></html>')
    matches = BASIC_CLEAN_XPATH(tree)
    assert {element.tag for element in matches} == {"aside", "footer"}

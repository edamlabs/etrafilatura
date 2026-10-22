"""Configuration objects: use_config, Extractor, Document."""

import logging
from configparser import ConfigParser

import pytest

from etrafilatura.deduplication import LRUCache
from etrafilatura.settings import (
    DEFAULT_CONFIG,
    SUPPORTED_FORMATS,
    Document,
    Extractor,
    _yaml_scalar,
    set_date_params,
    use_config,
)

##### use_config #####


def test_use_config_defaults() -> None:
    config = use_config()
    assert config.getint("DEFAULT", "MIN_EXTRACTED_SIZE") == 250
    assert config.getint("DEFAULT", "DOWNLOAD_TIMEOUT") == 30
    assert DEFAULT_CONFIG.get("DEFAULT", "SSRF_PROTECTION") == "on"


def test_use_config_passthrough() -> None:
    config = ConfigParser()
    assert use_config(config=config) is config


def test_use_config_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    override = tmp_path / "custom.cfg"
    override.write_text("[DEFAULT]\nMIN_EXTRACTED_SIZE = 50\n")
    config = use_config(str(override))
    assert config.getint("DEFAULT", "MIN_EXTRACTED_SIZE") == 50
    assert config.getint("DEFAULT", "MIN_OUTPUT_SIZE") == 1


def test_use_config_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        use_config("/nonexistent/settings.cfg")


def test_extractor_config_none_falls_back() -> None:
    assert Extractor(config=None).config is DEFAULT_CONFIG


##### Extractor #####


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


def test_extractor_format_universe() -> None:
    assert {"csv", "html", "json", "markdown", "python", "txt", "xml", "xmltei", "yaml"} == SUPPORTED_FORMATS


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


def test_extractor_source_and_thresholds(make_config) -> None:  # type: ignore[no-untyped-def]
    config = make_config(MAX_TREE_SIZE="100000", MIN_FILE_SIZE="64")  # type: ignore[operator]
    options = Extractor(config=config, url="https://example.org/page")  # type: ignore[arg-type]
    assert options.source == "https://example.org/page"
    assert options.max_tree_size == 100000
    assert options.min_file_size == 64
    assert Extractor(config=config, source="src").source == "src"  # type: ignore[arg-type]


def test_extractor_max_tree_size_non_numeric(make_config) -> None:  # type: ignore[no-untyped-def]
    config = make_config(MAX_TREE_SIZE="abc")  # type: ignore[operator]
    assert Extractor(config=config).max_tree_size is None  # type: ignore[arg-type]


def test_extractor_dedup_instance() -> None:
    cache = LRUCache(maxsize=4)
    assert Extractor(dedup=cache).dedup is cache


##### Document #####


def test_document_defaults_and_as_dict() -> None:
    document = Document()
    assert document.body == ""
    assert document.commentsbody == ""
    data = document.as_dict()
    assert data["title"] is None
    assert set(data) == set(Document.__slots__)


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


##### helpers #####


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("plain title", "plain title"),
        ("title: with colon", '"title: with colon"'),
        ("yes", '"yes"'),
        ("trailing:", '"trailing:"'),
        (" hash #tag", '" hash #tag"'),
        ('say "hi"', 'say "hi"'),
        ("back\\slash", "back\\slash"),
        ("tab\there", '"tab\\there"'),
        ("lead\u00e9", "lead\u00e9"),
    ],
)
def test_yaml_scalar(value: str, expected: str) -> None:
    assert _yaml_scalar(value) == expected


def test_set_date_params() -> None:
    params = set_date_params(False)
    assert params["original_date"] is True
    assert params["extensive_search"] is False
    assert "max_date" in params

"""The public extraction surface: extract, bare_extraction, extract_with_metadata."""

import json
import logging
from xml.dom.minidom import parseString

import pytest

from etrafilatura.core import bare_extraction, determine_returnstring, extract, extract_with_metadata
from etrafilatura.deduplication import LRUCache
from etrafilatura.settings import DEFAULT_CONFIG, Document, Extractor, use_config

##### extract: formats #####


def test_core_extract_txt(article: str) -> None:
    text = extract(article)
    assert text is not None
    assert "small tools" in text.lower()
    assert "<p>" not in text


def test_core_extract_formats(article: str) -> None:
    markdown = extract(article, output_format="markdown")
    assert markdown is not None
    assert "<nav>" not in markdown

    xml_output = extract(article, output_format="xml", record_id="r-1")
    assert xml_output is not None
    parseString(xml_output)
    assert "<main>" in xml_output
    assert 'id="r-1"' in xml_output

    tei = extract(article, output_format="xmltei", tei_validation=True)
    assert tei is not None
    parseString(tei)

    payload = extract(article, output_format="json", with_metadata=True)
    assert payload is not None
    data = json.loads(payload)
    assert data["title"] == "The Quiet Revolution of Small Tools"

    row = extract(article, output_format="csv")
    assert row is not None
    assert "\t" in row

    page = extract(article, output_format="html", with_metadata=True)
    assert page is not None
    assert page.startswith("<!DOCTYPE html>")

    yaml_output = extract(article, output_format="yaml", with_metadata=True)
    assert yaml_output is not None
    assert yaml_output.startswith("---\ntitle: The Quiet Revolution of Small Tools")


def test_core_extract_comments(comments_page: str) -> None:
    with_comments = extract(comments_page)
    without = extract(comments_page, include_comments=False)
    assert with_comments is not None
    assert without is not None
    assert "Benchmarked" in with_comments
    assert "Benchmarked" not in without


def test_core_extract_flags(article: str) -> None:
    assert extract(article, fast=True) is not None
    assert extract(article, favor_precision=True) is not None
    assert extract(article, favor_recall=True) is not None
    assert extract(article, include_links=True) is not None
    assert extract(article, include_images=True) is not None
    formatted = extract(article, output_format="txt", include_formatting=True)
    assert formatted is not None


def test_core_extract_tables(tables_page: str) -> None:
    assert extract(tables_page, include_tables=True) is not None
    assert extract(tables_page, include_tables=False) is not None


##### extract: rejections #####


def test_core_extract_empty() -> None:
    assert extract("") is None


def test_core_extract_language(article: str) -> None:
    assert extract(article, target_language="fr") is None
    assert extract(article, target_language="en") is not None


def test_core_extract_only_with_metadata(minimal_page: str, metadata_page: str) -> None:
    assert extract(minimal_page, only_with_metadata=True) is None
    assert extract(metadata_page, only_with_metadata=True, url="https://example.org/es/metadatos") is not None


def test_core_extract_url_blacklist(metadata_page: str) -> None:
    assert extract(metadata_page, url_blacklist={"https://example.org/es/metadatos"}) is None
    assert extract(metadata_page, url_blacklist={"https://other.example.org"}) is not None


def test_core_extract_author_blacklist(metadata_page: str) -> None:
    payload = extract(metadata_page, author_blacklist={"Marta Gil"}, output_format="json", with_metadata=True)
    assert payload is not None
    assert json.loads(payload)["author"] is None


def test_core_extract_deduplicate(article: str) -> None:
    assert extract(article, deduplicate=True) is not None
    assert extract(article, deduplicate=True) is not None
    assert extract(article, deduplicate=True) is None
    cache = LRUCache(maxsize=8)
    assert extract(article, deduplicate=cache) is not None
    assert extract(article, deduplicate=cache) is not None
    assert extract(article, deduplicate=cache) is None


def test_core_extract_python_format_raises(article: str) -> None:
    with pytest.raises(ValueError, match="only usable in bare_extraction"):
        extract(article, output_format="python")


def test_core_extract_max_tree_size_rejected(article: str) -> None:
    with pytest.raises(ValueError, match="max_tree_size"):
        extract(article, max_tree_size=1000)


##### extract: configuration #####


def test_core_extract_prune(article: str) -> None:
    assert extract(article, prune_xpath="nav, footer") is not None
    assert extract(article, prune_xpath=["nav"]) is not None
    assert extract(article, prune_xpath=[]) is not None


def test_core_extract_settingsfile(article: str, tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = tmp_path / "custom.cfg"
    settings.write_text("[DEFAULT]\nMIN_OUTPUT_SIZE = 1\n")
    assert extract(article, settingsfile=str(settings)) is not None


def test_core_extract_options_object(article: str) -> None:
    options = Extractor(output_format="markdown", recall=True)
    assert extract(article, options=options) is not None


def test_core_extract_config_passthrough(article: str) -> None:
    assert extract(article, config=use_config()) is not None
    assert extract(article, config=DEFAULT_CONFIG) is not None


def test_core_extract_date_params(metadata_page: str) -> None:
    params = {"original_date": True, "extensive_search": False}
    assert extract(metadata_page, date_extraction_params=params) is not None


def test_core_extract_language_metadata(article: str) -> None:
    document = extract_with_metadata(article)
    assert document is not None
    assert document.language == "en"


##### bare_extraction #####


def test_core_bare_extraction(article: str) -> None:
    document = bare_extraction(article)
    assert isinstance(document, Document)
    assert document.text is not None
    assert "<p>" in document.body
    assert document.raw_text
    assert document.commentsbody == ""


def test_core_bare_extraction_comments(comments_page: str) -> None:
    document = bare_extraction(comments_page)
    assert isinstance(document, Document)
    assert "comment" in document.commentsbody
    assert document.comments


def test_core_bare_extraction_metadata(article: str) -> None:
    document = bare_extraction(article, with_metadata=True)
    assert isinstance(document, Document)
    assert document.title == "The Quiet Revolution of Small Tools"
    assert document.author == "Alice Ferrer"


def test_core_bare_extraction_as_dict(article: str) -> None:
    with pytest.warns(DeprecationWarning, match="as_dict"):
        data = bare_extraction(article, as_dict=True)
    assert isinstance(data, dict)
    assert data["text"]


def test_core_bare_extraction_formatting(article: str) -> None:
    document = bare_extraction(article, include_formatting=True)
    assert isinstance(document, Document)
    assert document.text is not None


def test_core_bare_extraction_no_comments(article: str) -> None:
    document = bare_extraction(article, include_comments=False)
    assert isinstance(document, Document)
    assert document.commentsbody == ""


def test_core_bare_extraction_rejects(article: str) -> None:
    assert bare_extraction("") is None
    assert bare_extraction(article, target_language="de") is None


def test_core_bare_extraction_no_fallback_deprecated(article: str) -> None:
    with pytest.warns(DeprecationWarning, match="no_fallback"):
        assert bare_extraction(article, no_fallback=True) is not None


def test_core_bare_extraction_options_object(article: str) -> None:
    options = Extractor(output_format="python")
    document = bare_extraction(article, options=options)
    assert isinstance(document, Document)


##### extract_with_metadata #####


def test_core_extract_with_metadata(metadata_page: str) -> None:
    document = extract_with_metadata(metadata_page, output_format="xml", record_id="rec-9")
    assert isinstance(document, Document)
    assert document.title == "Una página rica en metadatos"
    assert document.id == "rec-9"
    assert document.fingerprint
    assert document.text is not None
    parseString(document.text)


def test_core_extract_with_metadata_none() -> None:
    assert extract_with_metadata("") is None


def test_core_fingerprint_txt_formats(article: str) -> None:
    text = extract(article)
    assert text is not None


##### determine_returnstring #####


def test_core_determine_returnstring(article: str) -> None:
    document = bare_extraction(article, with_metadata=True)
    assert isinstance(document, Document)
    for name in ("txt", "markdown", "yaml", "xml", "xmltei", "json", "csv", "html"):
        options = Extractor(output_format=name, with_metadata=True)
        assert determine_returnstring(document, options)


def test_core_rejection_logged(article: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert extract(article, target_language="fr") is None
    assert "discarding data" in caplog.text

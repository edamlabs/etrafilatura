"""Output renderers."""

import json
from xml.dom.minidom import parseString

import pytest

from etrafilatura.settings import Document, Extractor
from etrafilatura.xml import (
    build_html_output,
    build_json_output,
    build_tei_output,
    build_xml_output,
    control_xml_output,
    meta_items,
    render_text,
    validate_tei,
    xmltocsv,
)


@pytest.fixture
def document() -> Document:
    """A populated document with body and comments."""
    return Document(
        title="Title: colon",
        author="Author",
        url="https://example.org/page",
        hostname="example.org",
        date="2026-01-02",
        categories=["news", "tech"],
        tags=["rust"],
        idval="id-1",
        license_val="CC-BY",
        body='<p>Hello <hi rend="#b">world</hi></p>',
        commentsbody="<p>Nice post</p>",
        comments="Nice post",
        raw_text="Hello world",
    )


def test_xml_render_text_modes() -> None:
    assert render_text("<p>a</p><p>b</p>", False).split() == ["a", "b"]
    markdown = render_text("<h1>t</h1><p>x</p>", True)
    assert "# t" in markdown


def test_xml_meta_items(document: Document) -> None:
    items = dict(meta_items(document))
    assert items["categories"] == "news;tech"
    assert items["title"] == "Title: colon"
    assert "body" not in items


def test_xml_build_xml_output(document: Document) -> None:
    output = build_xml_output(document)
    parseString(output)
    assert "<main>" in output
    assert "<comments>" in output
    assert 'title="Title: colon"' in output
    assert 'comments="9"' in output


def test_xml_build_xml_output_empty() -> None:
    output = build_xml_output(Document())
    parseString(output)
    assert "<main/>" in output
    assert "<comments/>" in output


def test_xml_build_tei(document: Document) -> None:
    output = build_tei_output(document)
    parseString(output)
    assert "<TEI" in output
    assert "keywords" in output
    assert 'type="comments"' in output


def test_xml_build_tei_minimal() -> None:
    output = build_tei_output(Document(body="<p>line</p>"))
    parseString(output)
    assert "<author>" not in output


def test_xml_validate_tei() -> None:
    assert validate_tei("<TEI><text/></TEI>") is True
    with pytest.raises(ValueError, match="well-formed"):
        validate_tei("<TEI><text></TEI>")


def test_xml_control_output(document: Document) -> None:
    assert "<main>" in control_xml_output(document, Extractor(output_format="xml"))
    tei = control_xml_output(document, Extractor(output_format="xmltei", tei_validation=True))
    assert "<TEI" in tei


def test_xml_build_json(document: Document) -> None:
    with_meta = json.loads(build_json_output(document, with_metadata=True))
    assert with_meta["source"] == "https://example.org/page"
    assert with_meta["source-hostname"] is None
    assert with_meta["categories"] == "news;tech"
    assert with_meta["text"].strip() == "Hello world"
    without_meta = json.loads(build_json_output(document, with_metadata=False))
    assert set(without_meta) == {"text", "comments"}


def test_xml_csv(document: Document) -> None:
    row = xmltocsv(document, False)
    fields = row.rstrip("\r\n").split("\t")
    assert fields[0] == "https://example.org/page"
    assert fields[3] == "example.org"
    assert fields[9] == "CC-BY"


def test_xml_csv_nulls() -> None:
    row = xmltocsv(Document(), False)
    assert row.startswith("null\tnull")


def test_xml_html_output(document: Document) -> None:
    plain = build_html_output(document)
    assert "<main>" in plain
    assert "content=" not in plain.split("<body>")[0].replace('<meta charset="utf-8"/>', "")
    rich = build_html_output(document, with_metadata=True)
    assert 'name="title"' in rich
    assert "<aside>" in rich


def test_xml_html_output_no_comments() -> None:
    assert "<aside>" not in build_html_output(Document(body="<p>x</p>"))

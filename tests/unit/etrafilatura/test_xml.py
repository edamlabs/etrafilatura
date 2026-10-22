"""Output renderers (vendored module) exercised through the public shapes."""

import json
from xml.dom.minidom import parseString

import pytest
from lxml.etree import Element, XPath, fromstring, tostring

from etrafilatura.core import extract
from etrafilatura.htmlprocessing import build_html_output, convert_to_html, prune_unwanted_nodes
from etrafilatura.settings import Document, Extractor
from etrafilatura.xml import (
    build_json_output,
    build_tei_output,
    build_xml_output,
    control_xml_output,
    delete_element,
    meta_items,
    remove_empty_elements,
    strip_double_tags,
    validate_tei,
    xmltocsv,
    xmltotxt,
)


def body_with(html: str):  # type: ignore[no-untyped-def]
    return fromstring(f"<body>{html}</body>")


@pytest.fixture
def document() -> Document:
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
        body=body_with('<head rend="h1">Heading</head><p>Hello <hi rend="#b">world</hi></p>'),
        commentsbody=body_with("<p>Nice post</p>"),
        comments="Nice post",
        raw_text="Hello world",
    )


def test_xml_xmltotxt_modes(document: Document) -> None:
    assert xmltotxt(document.body, include_formatting=False).split() == ["Heading", "Hello", "world"]
    formatted = xmltotxt(document.body, include_formatting=True)
    assert "# Heading" in formatted
    assert "**world**" in formatted


def test_xml_meta_items(document: Document) -> None:
    items = dict(meta_items(document))
    assert items["categories"] == "news;tech"
    assert items["title"] == "Title: colon"
    assert "body" not in items


def test_xml_build_xml_output(document: Document) -> None:
    output = build_xml_output(document)
    serialized = control_xml_output(document, Extractor(output_format="xml"))
    parseString(serialized)
    assert "<main>" in serialized
    assert "<comments>" in serialized
    assert 'title="Title: colon"' in serialized
    assert output.tag == "doc"


def test_xml_tei_output(document: Document) -> None:
    tree = build_tei_output(document)
    assert str(tree.tag).endswith("TEI")
    serialized = control_xml_output(document, Extractor(output_format="xmltei"))
    parseString(serialized)
    assert "teiHeader" in serialized


def test_xml_tei_validation(article: str) -> None:
    tei = extract(article, output_format="xmltei", tei_validation=True, with_metadata=True)
    assert tei is not None
    assert "TEI" in tei


def test_xml_validate_tei(document: Document) -> None:
    tree = build_tei_output(document)
    assert validate_tei(tree) is True
    broken = Element("TEI")
    broken.append(Element("bogus"))
    assert validate_tei(broken) is False


def test_xml_build_json(document: Document) -> None:
    with_meta = json.loads(build_json_output(document, with_metadata=True))
    assert with_meta["source"] == "https://example.org/page"
    assert with_meta["categories"] == "news;tech"
    assert with_meta["text"].strip().startswith("Heading")
    without_meta = json.loads(build_json_output(document, with_metadata=False))
    assert set(without_meta) == {"text", "comments"}


def test_xml_csv(document: Document) -> None:
    row = xmltocsv(document, False)
    fields = row.rstrip("\r\n").split("\t")
    assert fields[0] == "https://example.org/page"
    assert fields[9] == "CC-BY"


def test_xml_html_output(document: Document) -> None:
    rich = build_html_output(document, with_metadata=True)
    assert "<h1>" in rich
    assert 'name="title"' in rich
    plain = build_html_output(Document(body=body_with("<p>x</p>")))
    assert "<html>" in plain
    assert "content=" not in plain


def test_xml_convert_to_html() -> None:
    tree = convert_to_html(body_with('<list><item>a</item></list><ref target="https://x.org">l</ref><lb/>'))
    serialized = tostring(tree, encoding="unicode")
    assert "<ul>" in serialized
    assert '<a href="https://x.org">' in serialized
    assert "<br/>" in serialized


def test_xml_prune_unwanted_nodes() -> None:
    from lxml.html import fromstring as html_fromstring  # noqa: PLC0415

    tree = html_fromstring("<html><body><nav>menu</nav><p>keep</p></body></html>")
    pruned = prune_unwanted_nodes(tree, [XPath(".//nav")])
    assert pruned.find(".//nav") is None
    assert "keep" in "".join(pruned.itertext())


def test_xml_tree_helpers() -> None:
    tree = body_with("<p>text</p><p></p>")
    remove_empty_elements(tree)
    assert len(tree.findall("p")) == 1
    doubled = body_with("<p>outer<p>inner</p></p>")
    strip_double_tags(doubled)
    assert doubled.find(".//p/p") is None
    parent = body_with("<p>a<span>b</span></p>")
    span = parent.find(".//span")
    assert span is not None
    delete_element(span)
    assert parent.find(".//span") is None

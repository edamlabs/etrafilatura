"""Baseline extraction and tag stripping (vendored module)."""

from lxml.etree import _Element
from lxml.html import fromstring

from etrafilatura.baseline import baseline, block_text, html2txt


def test_baseline_article(article: str) -> None:
    tree, text, length = baseline(article)
    assert isinstance(tree, _Element)
    assert tree.tag == "body"
    assert "small tools" in text.lower()
    assert length == len(text)


def test_baseline_empty_input() -> None:
    tree, text, length = baseline("")
    assert tree.tag == "body"
    assert (text, length) == ("", 0)


def test_baseline_json_ld() -> None:
    body = (
        "The full article text lives inside the JSON-LD payload of the page, "
        "long enough to clear the minimum content length the baseline strategy applies."
    )
    page = (
        '<html><body><script type="application/ld+json">{"@type": "Article", '
        f'"articleBody": "{body}"}}</script>'
        "</body></html>"
    )
    _tree, text, length = baseline(page)
    assert "JSON-LD" in text
    assert length == len(text)


def test_baseline_element_input(article: str) -> None:
    tree = fromstring(article)
    _body, text, _length = baseline(tree)
    assert "small tools" in text.lower()
    assert tree.find(".//aside") is not None


def test_html2txt_clean() -> None:
    html = "<html><body><p>one</p><script>evil()</script><p>two</p></body></html>"
    cleaned = html2txt(html)
    assert "one" in cleaned
    assert "two" in cleaned
    assert "evil" not in cleaned
    raw = html2txt(html, clean=False)
    assert "one" in raw


def test_html2txt_empty() -> None:
    assert html2txt("") == ""


def test_html2txt_no_body() -> None:
    assert html2txt("<feed><entry>x</entry></feed>") == ""
    tree = fromstring("<div><p>fragment content</p></div>")
    assert "fragment content" in html2txt(tree)


def test_block_text_paragraphs() -> None:
    element = fromstring("<div><p>block</p><p>text</p></div>")
    assert "block" in block_text(element)

"""Baseline extraction and tag stripping."""

from etrafilatura.baseline import baseline, html2txt
from etrafilatura.settings import Document


def test_baseline_article(article: str) -> None:
    document, text, length = baseline(article)
    assert isinstance(document, Document)
    assert "small tools" in text.lower()
    assert length == len(text)
    assert "<p>" in document.body


def test_baseline_empty_input() -> None:
    document, text, length = baseline("")
    assert isinstance(document, Document)
    assert (text, length) == ("", 0)


def test_baseline_unextractable() -> None:
    document, text, length = baseline("<html><body></body></html>")
    assert text == ""
    assert length == 0
    assert document.body == ""


def test_baseline_title_only(empty_page: str) -> None:
    _document, text, _length = baseline(empty_page)
    ### The engine's own baseline fallback keeps the title as last-resort text.
    assert text == "Empty"


def test_baseline_html2txt_fallback(minimal_page: str) -> None:
    document, text, _length = baseline(minimal_page)
    assert text
    assert isinstance(document.text, str)


def test_baseline_html2txt_clean() -> None:
    html = "<html><body><p>one</p>\n\n<p>two</p></body></html>"
    cleaned = html2txt(html)
    assert "one" in cleaned
    assert "\n\n\n" not in cleaned
    assert html2txt(html, clean=False)


def test_baseline_html2txt_empty() -> None:
    assert html2txt("") == ""

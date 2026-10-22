"""Baseline extraction and tag stripping — same interface as trafilatura.baseline."""

from etrafilatura import _native
from etrafilatura.errors import ExtractionError
from etrafilatura.settings import Document
from etrafilatura.utils import HtmlInput, load_html, sanitize


def baseline(filecontent: HtmlInput) -> tuple[Document, str, int]:
    """Last-resort extraction through the engine's recall pipeline.

    Returns:
        A tuple (document, text, text length); empty text when there is nothing to extract.
    """
    html = load_html(filecontent)
    if html is None:
        return Document(), "", 0
    try:
        result = _native.extract_html(html, fallback=True, focus="recall")
    except ExtractionError:
        result = None
    text = result.content_text if result else sanitize(html2txt(html, clean=False)) or ""
    document = Document(body=result.content_html if result else "", text=text, raw_text=text)
    return document, text, len(text)


def html2txt(content: HtmlInput, clean: bool = True) -> str:
    """Strip every tag and return the visible text of the document."""
    html = load_html(content)
    if html is None:
        return ""
    text = _native.html_to_text(html)
    return sanitize(text) or "" if clean else text

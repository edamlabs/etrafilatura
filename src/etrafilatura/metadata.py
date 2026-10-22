"""Metadata extraction — same interface as trafilatura.metadata.extract_metadata."""

from typing import Any
from urllib.parse import urlparse

from lxml.etree import tostring

from etrafilatura import _native
from etrafilatura.settings import Document
from etrafilatura.utils import HtmlInput, load_html


def extract_metadata(
    filecontent: HtmlInput,
    default_url: str | None = None,
    date_config: dict[str, Any] | None = None,
    extensive: bool = True,
    author_blacklist: set[str] | None = None,
) -> Document:
    """Extract metadata from an HTML string, tree or any accepted input, as a `Document`.

    Args:
        filecontent: HTML code as string, bytes, lxml tree or Response.
        default_url: Previously known URL of the downloaded document.
        date_config: Extraction parameters; `extensive_search` picks the date mode.
        extensive: Use extensive search for date extraction.
        author_blacklist: Author names to filter out.

    Returns:
        A Document containing the extracted metadata; empty when there is nothing to parse.
    """
    tree = load_html(filecontent)
    if tree is None:
        return Document()
    html = tostring(tree, encoding="unicode", method="html")
    params = dict(date_config) if date_config else {}
    date_mode = "extensive" if params.get("extensive_search", extensive) else "fast"
    meta = _native.extract_metadata_html(
        html,
        url=default_url,
        excluded_authors=sorted(author_blacklist or ()),
        date_mode=date_mode,
    )
    url = meta.url or default_url
    hostname = meta.hostname or (urlparse(url).netloc if url else None)
    return Document(
        title=meta.title or None,
        author=meta.author or None,
        url=url,
        hostname=hostname or None,
        description=meta.description or None,
        sitename=meta.sitename.lstrip("@") if meta.sitename else None,
        date=meta.date,
        categories=meta.categories or None,
        tags=meta.tags or None,
        fingerprint=meta.fingerprint or None,
        idval=meta.id or None,
        license_val=meta.license or None,
        language=meta.language or None,
        image=meta.image or None,
        pagetype=meta.page_type or None,
    )

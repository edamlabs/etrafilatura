"""Metadata extraction — same interface as trafilatura.metadata.extract_metadata."""

from os import PathLike
from typing import Any

from lxml.etree import tostring

from etrafilatura import _native
from etrafilatura.settings import DEFAULT_CONFIG, Document, set_date_params
from etrafilatura.source import AutoSource
from etrafilatura.utils import HtmlInput, absolute_url, extract_domain, load_html


def extract_metadata(
    filecontent: HtmlInput | PathLike[str],
    default_url: str | None = None,
    date_config: dict[str, Any] | None = None,
    extensive: bool = True,
    author_blacklist: set[str] | None = None,
    *,
    input_format: str = "html",
) -> Document:
    """Extract metadata from an HTML string, tree or any accepted input, as a `Document`.

    Args:
        filecontent: HTML code as string, bytes, lxml tree or Response.
        default_url: Previously known URL of the downloaded document.
        date_config: Extraction parameters; `extensive_search` picks the date mode, `max_date` the file date.
        extensive: Use extensive search for date extraction.
        author_blacklist: Author names to filter out.
        input_format: "html" (trafilatura's behaviour) or "auto": a URL string is fetched, a file path read.

    Returns:
        A Document containing the extracted metadata; empty when there is nothing to parse.
    """
    content, fetched_url = AutoSource().run(filecontent, input_format, DEFAULT_CONFIG)
    default_url = default_url or fetched_url
    tree = load_html(content) if content is not None else None
    if tree is None:
        return Document()
    date_config = {**date_config} if date_config else set_date_params(extensive)
    meta = _native.extract_metadata_html(
        tostring(tree, encoding="unicode", method="html"),
        url=absolute_url(default_url),
        excluded_authors=sorted(author_blacklist or ()),
        date_mode="extensive" if date_config.get("extensive_search", extensive) else "fast",
    )
    url = meta.url or default_url
    return Document(
        title=meta.title or None,
        author=meta.author or None,
        url=url,
        hostname=extract_domain(url) if url else None,
        description=meta.description or None,
        sitename=meta.sitename.lstrip("@") if meta.sitename else None,
        date=meta.date,
        categories=list(meta.categories),
        tags=list(meta.tags),
        fingerprint=meta.fingerprint or None,
        idval=meta.id or None,
        license_val=meta.license or None,
        language=meta.language or None,
        image=meta.image or None,
        pagetype=meta.page_type.lower() or None,
        filedate=date_config.get("max_date"),
    )

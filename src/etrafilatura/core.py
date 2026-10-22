"""Extraction entry points — same interface as trafilatura.core."""

import logging
import warnings
from types import MappingProxyType
from typing import Any, Final

from etrafilatura import _native
from etrafilatura.deduplication import LRUCache, content_fingerprint, duplicate_test
from etrafilatura.errors import ExtractionError
from etrafilatura.metadata import extract_metadata
from etrafilatura.settings import (
    DEFAULT_CONFIG,
    YAML_FIELDS,
    Document,
    Extractor,
    _yaml_scalar,
    use_config,
)
from etrafilatura.utils import HtmlInput, load_html, normalize_unicode
from etrafilatura.xml import build_html_output, build_json_output, control_xml_output, render_text, xmltocsv

LOGGER = logging.getLogger(__package__)

TXT_FORMATS: Final = frozenset({"markdown", "txt"})


def _check_deprecation(
    fast: bool = False,
    *,
    no_fallback: bool = False,
    as_dict: bool = False,
    max_tree_size: int | None = None,
    stacklevel: int = 2,
) -> bool:
    """Check deprecated params and return the effective "fast" flag."""
    if no_fallback:
        warnings.warn(
            '"no_fallback" will be removed, use "fast" instead',
            DeprecationWarning,
            stacklevel=stacklevel,
        )
    if as_dict:
        warnings.warn(
            '"as_dict" will be removed, use the .as_dict() method instead',
            DeprecationWarning,
            stacklevel=stacklevel,
        )
    if max_tree_size:
        message = '"max_tree_size" will be removed, use settings.cfg instead'
        raise ValueError(message)
    return fast or no_fallback


def _join_selectors(prune_xpath: str | list[str] | None) -> str | None:
    """One CSS selector string from a single selector or a list of them."""
    if prune_xpath is None:
        return None
    selectors = [prune_xpath] if isinstance(prune_xpath, str) else list(prune_xpath)
    return ", ".join(selectors) or None


def _engine_options(options: Extractor) -> dict[str, Any]:
    """Native keyword arguments derived from the extractor configuration."""
    return {
        "url": options.url,
        "target_language": options.lang,
        "fallback": not options.fast,
        "focus": options.focus,
        "comments": options.comments,
        "tables": options.tables,
        "images": options.images,
        "links": options.links,
        "excluded_authors": sorted(options.author_blacklist),
        "essential_metadata": options.only_with_metadata,
        "max_tree_size": options.max_tree_size,
        "date_mode": "extensive" if options.date_params.get("extensive_search") else "fast",
        "min_extracted_size": options.min_extracted_size,
        "min_output_size": options.min_output_size,
        "min_output_comment_size": options.min_output_comm_size,
        "min_duplicate_check_size": options.min_duplcheck_size,
        "max_duplicate_count": options.max_repetitions,
    }


##### OUTPUT #####


def _render_xml(document: Document, options: Extractor) -> str:
    return control_xml_output(document, options)


def _render_csv(document: Document, options: Extractor) -> str:
    return xmltocsv(document, options.formatting)


def _render_json(document: Document, options: Extractor) -> str:
    return build_json_output(document, options.with_metadata)


def _render_html(document: Document, options: Extractor) -> str:
    return build_html_output(document, options.with_metadata)


def _render_text(document: Document, options: Extractor) -> str:
    text = render_text(document.body, options.formatting)
    if document.commentsbody:
        text = f"{text}\n{render_text(document.commentsbody, options.formatting)}".strip()
    if not options.with_metadata:
        return text
    fields = "".join(
        f"{attr}: {_yaml_scalar(value) if isinstance(value, str) else value}\n"
        for attr in YAML_FIELDS
        if (value := getattr(document, attr))
    )
    return f"---\n{fields}---\n{text}"


RENDERERS: Final[MappingProxyType[str, Any]] = MappingProxyType(
    {
        "csv": _render_csv,
        "html": _render_html,
        "json": _render_json,
        "markdown": _render_text,
        "txt": _render_text,
        "xml": _render_xml,
        "xmltei": _render_xml,
        "yaml": _render_text,
    }
)


def determine_returnstring(document: Document, options: Extractor) -> str:
    """Convert the document to the chosen output format and return it as a string."""
    returnstring = RENDERERS[options.format](document, options)
    return normalize_unicode(returnstring)


##### EXTRACTION #####


def bare_extraction(
    filecontent: HtmlInput,
    url: str | None = None,
    fast: bool = False,
    no_fallback: bool = False,
    favor_precision: bool = False,
    favor_recall: bool = False,
    include_comments: bool = True,
    output_format: str = "python",
    target_language: str | None = None,
    include_tables: bool = True,
    include_images: bool = False,
    include_formatting: bool | None = None,
    include_links: bool = False,
    deduplicate: bool | LRUCache = False,
    date_extraction_params: dict[str, Any] | None = None,
    with_metadata: bool = False,
    only_with_metadata: bool = False,
    max_tree_size: int | None = None,
    url_blacklist: set[str] | None = None,
    author_blacklist: set[str] | None = None,
    as_dict: bool = False,
    prune_xpath: str | list[str] | None = None,
    config: Any = DEFAULT_CONFIG,
    options: Extractor | None = None,
) -> Document | dict[str, Any] | None:
    """Text extraction returning bare Python variables; same interface as trafilatura.bare_extraction.

    Differences: `prune_xpath` takes CSS selectors (the Rust engine prunes by CSS), the returned
    Document carries cleaned HTML strings in `.body` / `.commentsbody`, and `deduplicate` accepts
    an `etrafilatura.deduplication.LRUCache`.

    Returns:
        A Document (or a dict with `as_dict=True`) containing all the extracted information, or None.
    """
    fast = _check_deprecation(
        fast,
        no_fallback=no_fallback,
        as_dict=as_dict,
        max_tree_size=max_tree_size,
        stacklevel=3,
    )
    if not options or not isinstance(options, Extractor):
        options = Extractor(
            config=config,
            output_format=output_format,
            fast=fast,
            precision=favor_precision,
            recall=favor_recall,
            comments=include_comments,
            formatting=include_formatting,
            links=include_links,
            images=include_images,
            tables=include_tables,
            dedup=deduplicate,
            lang=target_language,
            url=url,
            with_metadata=with_metadata,
            only_with_metadata=only_with_metadata,
            author_blacklist=author_blacklist,
            url_blacklist=url_blacklist,
            date_params=date_extraction_params,
        )
    try:
        html = load_html(filecontent, options.max_file_size)
        if html is None:
            LOGGER.error("empty HTML input: %s", options.source)
            raise ValueError
        document = (
            extract_metadata(
                html,
                options.url,
                options.date_params,
                not options.fast,
                options.author_blacklist,
            )
            if options.with_metadata
            else Document()
        )
        if document.url in options.url_blacklist:
            LOGGER.warning("blacklisted URL: %s", document.url)
            raise ValueError
        if options.only_with_metadata and not (document.date and document.title and document.url):
            LOGGER.error("no metadata: %s", options.source)
            raise ValueError
        result = _native.extract_html(
            html,
            prune_selector=_join_selectors(prune_xpath),
            deduplicate=bool(options.dedup),
            **_engine_options(options),
        )
        if options.dedup and duplicate_test(result.content_text, options):
            LOGGER.debug("discarding duplicate document: %s", options.source)
            raise ValueError
    except (ExtractionError, TypeError, ValueError):
        LOGGER.warning("discarding data: %s", options.source)
        return None

    document.body = result.content_html
    document.raw_text = result.content_text
    document.language = document.language or result.metadata.language or None
    if options.comments:
        document.commentsbody = result.comments_html
        document.comments = result.comments_markdown if options.formatting else result.comments_text
    if options.format == "python":
        document.text = result.markdown if options.formatting else result.content_text
    return document.as_dict() if as_dict else document


def _internal_extraction(
    filecontent: HtmlInput,
    url: str | None = None,
    record_id: str | None = None,
    fast: bool = False,
    no_fallback: bool = False,
    favor_precision: bool = False,
    favor_recall: bool = False,
    include_comments: bool = True,
    output_format: str = "txt",
    tei_validation: bool = False,
    target_language: str | None = None,
    include_tables: bool = True,
    include_images: bool = False,
    include_formatting: bool | None = None,
    include_links: bool = False,
    deduplicate: bool | LRUCache = False,
    date_extraction_params: dict[str, Any] | None = None,
    with_metadata: bool = False,
    only_with_metadata: bool = False,
    max_tree_size: int | None = None,
    url_blacklist: set[str] | None = None,
    author_blacklist: set[str] | None = None,
    settingsfile: str | None = None,
    prune_xpath: str | list[str] | None = None,
    config: Any = DEFAULT_CONFIG,
    options: Extractor | None = None,
) -> Document | None:
    """Internal method to do the extraction."""
    fast = _check_deprecation(
        fast,
        no_fallback=no_fallback,
        as_dict=False,
        max_tree_size=max_tree_size,
        stacklevel=4,
    )
    if not options or not isinstance(options, Extractor):
        options = Extractor(
            config=use_config(settingsfile) if settingsfile else config,
            output_format=output_format,
            fast=fast,
            precision=favor_precision,
            recall=favor_recall,
            comments=include_comments,
            formatting=include_formatting,
            links=include_links,
            images=include_images,
            tables=include_tables,
            dedup=deduplicate,
            lang=target_language,
            url=url,
            with_metadata=with_metadata,
            only_with_metadata=only_with_metadata,
            tei_validation=tei_validation,
            author_blacklist=author_blacklist,
            url_blacklist=url_blacklist,
            date_params=date_extraction_params,
        )
    document = bare_extraction(filecontent, options=options, as_dict=False, prune_xpath=prune_xpath)
    if not document or not isinstance(document, Document):
        return None
    if options.format == "python":
        message = "'python' format only usable in bare_extraction() function"
        raise ValueError(message)
    if options.format not in TXT_FORMATS or options.with_metadata:
        document.id = record_id
        document.fingerprint = content_fingerprint(f"{document.title} {document.raw_text}")
    document.text = determine_returnstring(document, options)
    return document


def extract(
    filecontent: HtmlInput,
    url: str | None = None,
    record_id: str | None = None,
    fast: bool = False,
    no_fallback: bool = False,
    favor_precision: bool = False,
    favor_recall: bool = False,
    include_comments: bool = True,
    output_format: str = "txt",
    tei_validation: bool = False,
    target_language: str | None = None,
    include_tables: bool = True,
    include_images: bool = False,
    include_formatting: bool | None = None,
    include_links: bool = False,
    deduplicate: bool | LRUCache = False,
    date_extraction_params: dict[str, Any] | None = None,
    with_metadata: bool = False,
    only_with_metadata: bool = False,
    max_tree_size: int | None = None,
    url_blacklist: set[str] | None = None,
    author_blacklist: set[str] | None = None,
    settingsfile: str | None = None,
    prune_xpath: str | list[str] | None = None,
    config: Any = DEFAULT_CONFIG,
    options: Extractor | None = None,
) -> str | None:
    """Main function exposed by the package: extraction and conversion to the chosen output format.

    Args:
        filecontent: HTML code as string, bytes, path or Response.
        url: URL of the webpage.
        record_id: Add an ID to the metadata.
        fast: Use faster heuristics and skip backup extraction.
        no_fallback: Deprecated, use "fast" instead.
        favor_precision: prefer less text but correct extraction.
        favor_recall: when unsure, prefer more text.
        include_comments: Extract comments along with the main text.
        output_format: "csv", "html", "json", "markdown", "txt", "xml", "xmltei" or "yaml".
        tei_validation: Validate the XML-TEI output with respect to well-formedness.
        target_language: Discard documents in another language (ISO 639-1).
        include_tables: Take into account information within the HTML <table> element.
        include_images: Take images into account.
        include_formatting: Keep structural elements (Markdown for text formats).
        include_links: Keep links along with their targets.
        deduplicate: Remove duplicate segments and documents; accepts an LRUCache.
        date_extraction_params: Date extraction parameters as dict().
        with_metadata: Extract metadata fields and add them to the output.
        only_with_metadata: Only keep documents featuring date, title and url.
        url_blacklist: URLs to filter out as set().
        author_blacklist: Author names to filter out as set().
        settingsfile: Use a configuration file to override the standard settings.
        prune_xpath: CSS selector(s) to prune before extraction (str or list of str).
        config: Directly provide a configparser configuration.
        options: Directly provide a whole extractor configuration.

    Returns:
        A string in the desired format or None.
    """
    ### Must stay the first statement: a signature drift raises TypeError.
    document = _internal_extraction(**locals())
    return document.text if document is not None else None


def extract_with_metadata(
    filecontent: HtmlInput,
    url: str | None = None,
    record_id: str | None = None,
    fast: bool = False,
    favor_precision: bool = False,
    favor_recall: bool = False,
    include_comments: bool = True,
    output_format: str = "txt",
    tei_validation: bool = False,
    target_language: str | None = None,
    include_tables: bool = True,
    include_images: bool = False,
    include_formatting: bool | None = None,
    include_links: bool = False,
    deduplicate: bool | LRUCache = False,
    date_extraction_params: dict[str, Any] | None = None,
    url_blacklist: set[str] | None = None,
    author_blacklist: set[str] | None = None,
    settingsfile: str | None = None,
    prune_xpath: str | list[str] | None = None,
    config: Any = DEFAULT_CONFIG,
    options: Extractor | None = None,
) -> Document | None:
    """Extraction returning Document metadata with the content string in the desired format, or None."""
    return _internal_extraction(**locals(), with_metadata=True)

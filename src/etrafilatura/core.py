"""Extraction entry points — same interface as trafilatura.core.

`determine_returnstring`, `_check_deprecation` and `_yaml_scalar` are vendored from trafilatura 2.3.1
(https://github.com/adbar/trafilatura), Apache-2.0, Copyright 2019-present Adrien Barbaresi and
contributors; see NOTICE.md. The extraction pipeline itself runs in the Rust engine.
"""

import logging
import warnings
from copy import copy
from json import dumps as json_dumps
from typing import TYPE_CHECKING, Any, Final

from lxml.etree import XPath, tostring
from lxml.html import fragment_fromstring

from etrafilatura import _native
from etrafilatura.deduplication import LRUCache, content_fingerprint, duplicate_test
from etrafilatura.errors import ExtractionError
from etrafilatura.htmlprocessing import build_html_output, prune_unwanted_nodes
from etrafilatura.metadata import extract_metadata
from etrafilatura.settings import DEFAULT_CONFIG, Document, Extractor, use_config
from etrafilatura.utils import HtmlInput, load_html, normalize_unicode
from etrafilatura.xml import build_json_output, control_xml_output, delete_element, keeps_empty, xmltocsv, xmltotxt

if TYPE_CHECKING:
    from lxml.etree import _Element
    from lxml.html import HtmlElement

LOGGER = logging.getLogger(__package__)

# recall escalation constants live in the engine; the output contract is trafilatura's.
TXT_FORMATS: Final = {"markdown", "txt"}
_YAML_FIELDS = [
    "title",
    "author",
    "url",
    "hostname",
    "description",
    "sitename",
    "date",
    "categories",
    "tags",
    "fingerprint",
    "id",
    "license",
]

# Metadata is emitted as a YAML-style Markdown header; values such as a title
# containing ": " (or a leading indicator, or a reserved word) otherwise produce
# invalid YAML or get reinterpreted as a non-string. See GH #814.
_YAML_RESERVED = frozenset({"true", "false", "yes", "no", "on", "off", "y", "n", "null", "none", "~"})


def _yaml_scalar(value: str) -> str:
    "Render a metadata string as a plain or double-quoted YAML-safe scalar."
    if (
        value
        and value == value.strip()
        and value[0].isalpha()
        and ": " not in value
        and " #" not in value
        and not value.endswith(":")
        and value.lower() not in _YAML_RESERVED
        and all(ch >= " " and ch != "\x7f" for ch in value)
    ):
        return value
    # a JSON string is always a valid, exactly round-tripping YAML double-quoted scalar
    return json_dumps(value)


def determine_returnstring(document: Document, options: Extractor) -> str:
    """Convert XML tree to chosen format, clean the result and output it as a string"""
    # XML (TEI) steps
    if "xml" in options.format:
        # last cleaning
        for element in document.body.iter("*"):
            if len(element) == 0 and not element.text and not element.tail and not keeps_empty(element):
                delete_element(element, keep_tail=False)
        # build output tree
        returnstring = control_xml_output(document, options)
    # CSV
    elif options.format == "csv":
        returnstring = xmltocsv(document, options.formatting)
    # JSON
    elif options.format == "json":
        returnstring = build_json_output(document, options.with_metadata)
    # HTML
    elif options.format == "html":
        returnstring = build_html_output(document, options.with_metadata)
    # Markdown and TXT
    else:
        header = ""
        if options.with_metadata:
            # categories/tags are lists, their repr is a valid flow sequence
            fields = "".join(
                f"{attr}: {_yaml_scalar(value) if isinstance(value, str) else value}\n"
                for attr in _YAML_FIELDS
                if (value := getattr(document, attr))
            )
            header = f"---\n{fields}---\n"
        returnstring = f"{header}{xmltotxt(document.body, options.formatting)}"
        ### commentsbody is always a tree (Document defaults it to <body/>): the append is unconditional.
        returnstring = f"{returnstring}\n{xmltotxt(document.commentsbody, options.formatting)}".strip()
    # normalize Unicode format (defaults to NFC)
    return normalize_unicode(returnstring)


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


##### ENGINE BRIDGE #####


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
        "deduplicate": bool(options.dedup),
        "essential_metadata": options.only_with_metadata,
        "max_tree_size": options.max_tree_size,
        "date_mode": "extensive" if options.date_params.get("extensive_search") else "fast",
        "min_extracted_size": options.min_extracted_size,
        "min_output_size": options.min_output_size,
        "min_output_comment_size": options.min_output_comm_size,
        "min_duplicate_check_size": options.min_duplcheck_size,
        "max_duplicate_count": options.max_repetitions,
    }


def _engine_sequence(
    tree: "HtmlElement", options: Extractor, prune_xpath: str | list[str] | None
) -> tuple["_Element", str, "_Element", str]:
    """One extraction through the Rust engine: pruned tree in, trafilatura-shaped trees and texts out."""
    if prune_xpath is not None:
        expressions = [prune_xpath] if isinstance(prune_xpath, str) else list(prune_xpath)
        tree = prune_unwanted_nodes(tree, [XPath(expression) for expression in expressions])
    html = tostring(tree, encoding="unicode", method="html")
    result = _native.extract_html(html, **_engine_options(options))
    postbody = fragment_fromstring(result.content_html, create_parent="body")
    commentsbody = fragment_fromstring(result.comments_html, create_parent="body")
    return postbody, result.content_text, commentsbody, result.metadata.language


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
    deduplicate: "bool | LRUCache" = False,
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
    """Internal function for text extraction returning bare Python variables.

    Args:
        filecontent: HTML code as string, bytes, lxml tree or Response.
        url: URL of the webpage.
        fast: Use faster heuristics and skip backup extraction.
        no_fallback: Deprecated, use "fast" instead.
        favor_precision: prefer less text but correct extraction.
        favor_recall: prefer more text even when unsure.
        include_comments: Extract comments along with the main text.
        output_format: Define an output format, Python being the default
            and the interest of this internal function.
            Other values: "csv", "html", "json", "markdown", "txt", "xml", and "xmltei".
        target_language: Define a language to discard invalid documents (ISO 639-1 format).
        include_tables: Take into account information within the HTML <table> element.
        include_images: Take images into account.
        include_formatting: Keep structural elements related to formatting
            (kept in XML, rendered as markdown for text formats; ignored for JSON).
        include_links: Keep links along with their targets.
        deduplicate: Remove duplicate segments and documents.
            Accepts an LRUCache instance as dedicated, scoped cache.
        date_extraction_params: Provide extraction parameters for the date search as dict().
        with_metadata: Extract metadata fields and add them to the output.
        only_with_metadata: Only keep documents featuring all essential metadata
            (date, title, url).
        url_blacklist: Provide a blacklist of URLs as set() to filter out documents.
        author_blacklist: Provide a blacklist of Author Names as set() to filter out authors.
        as_dict: Deprecated, use the .as_dict() method instead.
        prune_xpath: Provide an XPath expression to prune the tree before extraction.
            can be str or list of str.
        config: Directly provide a configparser configuration.
        options: Directly provide a whole extractor configuration.

    Returns:
        A Document (a dict with `as_dict=True`) containing all the extracted information, or None.
    """
    # deprecations: stacklevel=3 → user → bare_extraction → _check_deprecation
    fast = _check_deprecation(
        fast,
        no_fallback=no_fallback,
        as_dict=as_dict,
        max_tree_size=max_tree_size,
        stacklevel=3,
    )

    # regroup extraction options
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
        # load the HTML tree
        tree = load_html(filecontent, options.max_file_size)
        if tree is None:
            LOGGER.error("empty HTML tree: %s", options.source)
            raise ValueError
        if tree is filecontent:
            tree = copy(tree)

        # extract metadata if necessary
        if options.with_metadata:
            document = extract_metadata(
                tree,
                options.url,
                options.date_params,
                not options.fast,
                options.author_blacklist,
            )

            # cut short if extracted URL in blacklist
            if document.url in options.url_blacklist:
                LOGGER.warning("blacklisted URL: %s", document.url)
                raise ValueError

            # cut short if core elements are missing
            if options.only_with_metadata and not (document.date and document.title and document.url):
                LOGGER.error("no metadata: %s", options.source)
                raise ValueError
        else:
            document = Document()

        postbody, temp_text, commentsbody, language = _engine_sequence(tree, options, prune_xpath)

        ### Tree size and minimum sizes are enforced by the engine (TreeTooLargeError / InsufficientContentError).

        # check duplicates at body level
        if options.dedup and duplicate_test(postbody, options) is True:
            LOGGER.debug("discarding duplicate document: %s", options.source)
            raise ValueError

        # sanity check on language
        if options.lang:
            document.language = language or None
    except (ExtractionError, TypeError, ValueError):
        LOGGER.warning("discarding data: %s", options.source)
        return None

    # special case: python variables
    if options.format == "python":
        document.text = xmltotxt(postbody, options.formatting)
        if options.comments:
            document.comments = xmltotxt(commentsbody, options.formatting)
            document.commentsbody = commentsbody
        document.raw_text = document.text
    else:
        document.raw_text, document.commentsbody = temp_text, commentsbody
    document.body = postbody

    return document if not as_dict else document.as_dict()


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
    deduplicate: "bool | LRUCache" = False,
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
    """Internal method to do the extraction"""
    # stacklevel=4 → user → extract → _internal_extraction → _check_deprecation
    fast = _check_deprecation(
        fast,
        no_fallback=no_fallback,
        as_dict=False,
        max_tree_size=max_tree_size,
        stacklevel=4,
    )

    # regroup extraction options
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

    # extraction
    document = bare_extraction(
        filecontent,
        options=options,
        as_dict=False,
        prune_xpath=prune_xpath,
    )

    # post-processing
    if not isinstance(document, Document):
        return None

    # TXT formats only output the ID and fingerprint in their metadata header
    if options.format not in TXT_FORMATS or options.with_metadata:
        if options.format == "python":
            message = "'python' format only usable in bare_extraction() function"
            raise ValueError(message)
        # add record ID to metadata
        document.id = record_id
        # calculate fingerprint (raw_text is always set by the engine sequence)
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
    deduplicate: "bool | LRUCache" = False,
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
    """Main function exposed by the package:
       Wrapper for text extraction and conversion to chosen output format.

    Args:
        filecontent: HTML code as string, bytes, lxml tree or Response.
        url: URL of the webpage.
        record_id: Add an ID to the metadata.
        fast: Use faster heuristics and skip backup extraction.
        no_fallback: Deprecated, use "fast" instead.
        favor_precision: prefer less text but correct extraction.
        favor_recall: when unsure, prefer more text.
        include_comments: Extract comments along with the main text.
        output_format: Define an output format:
            "csv", "html", "json", "markdown", "txt", "xml", and "xmltei".
        tei_validation: Validate the XML-TEI output with respect to the TEI standard.
        target_language: Define a language to discard invalid documents (ISO 639-1 format).
        include_tables: Take into account information within the HTML <table> element.
        include_images: Take images into account.
        include_formatting: Keep structural elements related to formatting
            (kept in XML, rendered as markdown for text formats; ignored for JSON).
        include_links: Keep links along with their targets.
        deduplicate: Remove duplicate segments and documents.
            Accepts an LRUCache instance as dedicated, scoped cache.
        date_extraction_params: Provide extraction parameters for the date search as dict().
        with_metadata: Extract metadata fields and add them to the output.
        only_with_metadata: Only keep documents featuring all essential metadata
            (date, title, url).
        url_blacklist: Provide a blacklist of URLs as set() to filter out documents.
        author_blacklist: Provide a blacklist of Author Names as set() to filter out authors.
        settingsfile: Use a configuration file to override the standard settings.
        prune_xpath: Provide an XPath expression to prune the tree before extraction.
            can be str or list of str.
        config: Directly provide a configparser configuration.
        options: Directly provide a whole extractor configuration.

    Returns:
        A string in the desired format or None.
    """
    # must stay the first statement: a signature drift raises TypeError
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
    deduplicate: "bool | LRUCache" = False,
    date_extraction_params: dict[str, Any] | None = None,
    url_blacklist: set[str] | None = None,
    author_blacklist: set[str] | None = None,
    settingsfile: str | None = None,
    prune_xpath: str | list[str] | None = None,
    config: Any = DEFAULT_CONFIG,
    options: Extractor | None = None,
) -> Document | None:
    """Main function exposed by the package:
       Wrapper for text extraction and conversion to chosen output format.
       This method also returns document metadata.

    Returns:
        Document metadata with content string in the desired format or None.
    """
    return _internal_extraction(**locals(), with_metadata=True)

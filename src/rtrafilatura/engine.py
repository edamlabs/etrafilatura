"""Bridge to the trafilatura-rs engine: an lxml tree in, trafilatura-shaped trees and texts out.

The engine serializes its result as HTML (`<h1>`, `<blockquote>`, `<td>`); trafilatura's renderers
read its XML vocabulary (`<head rend="h1">`, `<quote>`, `<cell>`). The vendored `convert_tags`
closes that gap. Rescue, size and duplicate checks stay in Python, as trafilatura runs them, so
the engine only selects content.
"""

from collections import deque
from collections.abc import Callable, Mapping
from copy import copy
from types import MappingProxyType
from typing import Any, Final

from lxml.etree import _Element, strip_tags, tostring
from lxml.html import HtmlElement, fragment_fromstring

from rtrafilatura import _native
from rtrafilatura.baseline import baseline
from rtrafilatura.htmlprocessing import convert_tags
from rtrafilatura.settings import Extractor
from rtrafilatura.utils import absolute_url

### The engine's own rescue, size and duplicate gates are neutralised: Python runs trafilatura's.
NEUTRAL_OPTIONS: Final[Mapping[str, Any]] = MappingProxyType(
    {
        "essential_metadata": False,
        "deduplicate": False,
        "max_tree_size": None,
        "min_extracted_size": 0,
        "min_output_size": 0,
        "min_output_comment_size": 0,
    }
)
TABLE_WRAPPERS: Final = ("thead", "tbody", "tfoot")


def convert_row(elem: _Element) -> None:
    "Rename a table row."
    elem.tag = "row"


def convert_cell(elem: _Element) -> None:
    "Rename a data cell, dropping its attributes."
    elem.attrib.clear()
    elem.tag = "cell"


def convert_head_cell(elem: _Element) -> None:
    "Rename a header cell, marking its role."
    convert_cell(elem)
    elem.set("role", "head")


TABLE_CONVERSIONS: Final[Mapping[str, Callable[[_Element], None]]] = MappingProxyType(
    {
        "tr": convert_row,
        "td": convert_cell,
        "th": convert_head_cell,
    }
)


class NativeEngine:
    """One extraction through trafilatura-rs, returned in trafilatura's tree vocabulary."""

    __slots__ = ()

    ##### PRIVATE #####

    @staticmethod
    def _run_options(options: Extractor) -> dict[str, Any]:
        """Native keyword arguments derived from the extractor configuration."""
        return {
            "url": absolute_url(options.url),
            "target_language": options.lang,
            "fallback": not options.fast,
            "focus": options.focus,
            "comments": options.comments,
            "tables": options.tables,
            "images": options.images,
            "links": options.links,
            "excluded_authors": sorted(options.author_blacklist),
            "date_mode": "extensive" if options.date_params.get("extensive_search") else "fast",
            **NEUTRAL_OPTIONS,
        }

    @staticmethod
    def _run_tree(html: str, options: Extractor, url: str | None) -> _Element:
        """Engine HTML parsed and converted to trafilatura's XML vocabulary."""
        tree = convert_tags(fragment_fromstring(html, create_parent="body"), options, url)
        strip_tags(tree, *TABLE_WRAPPERS)
        deque((TABLE_CONVERSIONS[str(elem.tag)](elem) for elem in tree.iter(*TABLE_CONVERSIONS)), maxlen=0)
        return tree

    @staticmethod
    def _run_comments(tree: _Element) -> _Element:
        """Comment blocks without attributes, as trafilatura's comment extraction leaves them."""
        deque((elem.attrib.clear() for elem in tree), maxlen=0)
        return tree

    ############################################################

    ##### PUBLIC #####

    def run(self, tree: HtmlElement, options: Extractor, url: str | None) -> tuple[_Element, str, _Element, str, str]:
        """Body, body text, comments, comments text and detected language of one document."""
        result = _native.extract_html(tostring(tree, encoding="unicode", method="html"), **self._run_options(options))
        postbody, temp_text = self._run_tree(result.content_html, options, url), result.content_text
        ### Rescue on the original tree, as trafilatura_sequence does.
        rescue = len(temp_text) < options.min_extracted_size and options.focus != "precision"
        postbody, temp_text = baseline(copy(tree))[:2] if rescue else (postbody, temp_text)
        commentsbody = self._run_comments(self._run_tree(result.comments_html, options, url))
        return postbody, temp_text, commentsbody, result.comments_text, result.metadata.language

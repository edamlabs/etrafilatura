"""HTML tree processing: pruning and conversion of the extraction vocabulary to HTML.

# Vendored from trafilatura 2.3.1 (https://github.com/adbar/trafilatura), Apache-2.0,
# Copyright 2019-present Adrien Barbaresi and contributors.
# Subset copied verbatim except the import block (absolute imports of this package); do not edit:
# re-sync from upstream instead. See NOTICE.md.
"""

from typing import TYPE_CHECKING

from lxml.etree import Element, SubElement, XPath, _Element, tostring
from lxml.html import HtmlElement

from etrafilatura.xml import delete_element, meta_items

if TYPE_CHECKING:
    from etrafilatura.settings import Document


def prune_unwanted_nodes(tree: HtmlElement, nodelist: list[XPath], with_backup: bool = False) -> HtmlElement:
    "Prune the HTML tree by removing unwanted sections."
    if not with_backup:
        for expression in nodelist:
            for subtree in expression(tree):
                delete_element(subtree)  # the tail text is preserved
        return tree
    # guard: prune nothing if it would remove too much text, the tree keeps its elements
    matches = dict.fromkeys(elem for expression in nodelist for elem in expression(tree))
    outer = [elem for elem in matches if not any(a in matches for a in elem.iterancestors())]
    old_len = len(tree.text_content())
    # todo: adjust for recall and precision settings
    if old_len - sum(len(elem.text_content()) for elem in outer) > old_len / 7:
        for elem in outer:
            delete_element(elem)
    return tree


REND_TAG_MAPPING = {
    **dict.fromkeys(("em", "i"), "#i"),
    **dict.fromkeys(("b", "strong"), "#b"),
    "u": "#u",
    **dict.fromkeys(("kbd", "samp", "tt", "var"), "#t"),
    "sub": "#sub",
    "sup": "#sup",
}

HTML_TAG_MAPPING = {v: k for k, v in REND_TAG_MAPPING.items()}

HTML_CONVERSIONS = {
    "list": "ul",
    "item": "li",
    "code": "pre",
    "quote": "blockquote",
    "head": lambda elem: f"h{int(elem.get('rend', 'h3')[1:])}",
    "lb": "br",
    "graphic": "img",
    "ref": "a",
    "hi": lambda elem: HTML_TAG_MAPPING[elem.get("rend", "#i")],
    "row": "tr",
    "cell": lambda elem: "th" if elem.get("role") == "head" else "td",
}


def convert_to_html(tree: _Element) -> _Element:
    "Convert XML to simplified HTML."
    for elem in tree.iter(HTML_CONVERSIONS.keys()):
        conversion = HTML_CONVERSIONS[str(elem.tag)]
        elem.tag = conversion(elem) if callable(conversion) else conversion  # type: ignore[assignment]
        # handle attributes
        if elem.tag == "a":
            elem.set("href", elem.attrib.pop("target", ""))
        elif elem.tag != "img":  # keep <img> src/alt/title; drop everything else
            elem.attrib.clear()
    tree.tag = "body"
    root = Element("html")
    root.append(tree)
    return root


def build_html_output(document: "Document", with_metadata: bool = False) -> str:
    "Convert the document to HTML and return a string."
    html_tree = convert_to_html(document.body)

    if with_metadata:
        head = Element("head")
        for item, value in meta_items(document):
            SubElement(head, "meta", name=item, content=value)
        html_tree.insert(0, head)

    return tostring(html_tree, pretty_print=True, encoding="unicode").strip()

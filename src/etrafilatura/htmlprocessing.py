"""HTML tree processing: pruning and conversion of the extraction vocabulary to HTML.

# Vendored from trafilatura 2.3.1 (https://github.com/adbar/trafilatura), Apache-2.0,
# Copyright 2019-present Adrien Barbaresi and contributors.
# Subset (pruning, `convert_tags` and its converters, HTML output) copied verbatim except the import block (absolute imports of this package); do not edit:
# re-sync from upstream instead. See NOTICE.md.
"""

from lxml.etree import Element, SubElement, XPath, _Element, strip_tags, tostring
from lxml.html import HtmlElement

from etrafilatura.settings import Document, Extractor
from etrafilatura.utils import safe_base_url, safe_relative_url
from etrafilatura.xml import delete_element, meta_items


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

CODE_INDICATORS = ["{", '("', "('", "\n    "]

def convert_lists(elem: _Element) -> None:
    "Convert <ul> and <ol> to <list> and underlying <li> elements to <item>."
    elem.set("rend", elem.tag)
    elem.tag = "list"
    i = 1
    for subelem in elem.iter("dd", "dt", "li"):
        # keep track of dd/dt items
        if subelem.tag in ("dd", "dt"):
            subelem.set("rend", f"{subelem.tag!s}-{i}")
            # increment counter after <dd> in description list
            if subelem.tag == "dd":
                i += 1
        # convert elem tag (needs to happen after the rest)
        subelem.tag = "item"


def convert_quotes(elem: _Element) -> None:
    "Convert quoted elements while accounting for nested structures."
    # a pre is code if it wraps a single span, carries highlight.js spans or code-like text
    hljs = elem.xpath(".//span[starts-with(@class,'hljs')]") if elem.tag == "pre" else []
    for subelem in hljs:
        subelem.attrib.clear()
    is_code = elem.tag == "pre" and (
        (len(elem) == 1 and elem[0].tag == "span") or bool(hljs) or any(i in (elem.text or "") for i in CODE_INDICATORS)
    )
    elem.tag = "code" if is_code else "quote"


def convert_headings(elem: _Element) -> None:
    "Add head tags and delete attributes."
    elem.attrib.clear()
    elem.set("rend", elem.tag)
    elem.tag = "head"


def convert_line_breaks(elem: _Element) -> None:
    "Convert <br> and <hr> to <lb>"
    elem.tag = "lb"


def convert_deletions(elem: _Element) -> None:
    'Convert <del>, <s>, <strike> to <del rend="overstrike">'
    elem.tag = "del"
    elem.set("rend", "overstrike")


def convert_details(elem: _Element) -> None:
    "Handle details and summary."
    elem.tag = "div"
    for subelem in elem.iter("summary"):
        subelem.tag = "head"


CONVERSIONS = {
    **dict.fromkeys(("dl", "ol", "ul"), convert_lists),
    **dict.fromkeys(("h1", "h2", "h3", "h4", "h5", "h6"), convert_headings),
    **dict.fromkeys(("br", "hr"), convert_line_breaks),
    **dict.fromkeys(("blockquote", "pre", "q"), convert_quotes),
    **dict.fromkeys(("del", "s", "strike"), convert_deletions),
    "details": convert_details,
}


def convert_link(elem: HtmlElement, base_url: str | None) -> None:
    "Replace link tags and href attributes, delete the rest."
    elem.tag = "ref"
    target = elem.get("href")  # defaults to None
    elem.attrib.clear()
    if target:
        # convert relative URLs
        if base_url:
            target = safe_relative_url(base_url, target) or target
        elem.set("target", target)


def convert_tags(tree: HtmlElement, options: Extractor, url: str | None = None) -> HtmlElement:
    "Simplify markup and convert relevant HTML tags to an XML standard."
    # delete links for faster processing
    if not options.links:
        containers = ("div", "li", "p", "table") if options.tables else ("div", "li", "p")
        # necessary for further detection, the tree root does not count as a container
        for elem in tree.iter("a"):
            if next(elem.iterancestors(containers), tree) is not tree:
                elem.tag = "ref"
        # strip the rest
        strip_tags(tree, "a")
    else:
        # get base URL for converting relative URLs
        base_url = url and safe_base_url(url)
        for elem in tree.iter("a", "ref"):
            convert_link(elem, base_url)

    # Yoast FAQ blocks: question headers are bold but act as titles (#471)
    for elem in tree.iter("strong"):
        if "schema-faq-question" in elem.get("class", ""):
            elem.attrib.clear()
            elem.set("rend", "h3")
            elem.tag = "head"

    # an empty sup/sub carries nothing to raise or lower, and process_node() would later
    # hand it the following text as its own, so the marker would wrap the wrong words.
    # The tail is kept in every focus mode, unlike the pruning of CUT_EMPTY_ELEMS.
    for elem in tree.iter("sub", "sup"):
        if not elem.text and len(elem) == 0:
            delete_element(elem)

    if options.formatting:
        for elem in tree.iter(REND_TAG_MAPPING.keys()):
            elem.attrib.clear()
            elem.set("rend", REND_TAG_MAPPING[elem.tag])  # type: ignore[index]
            elem.tag = "hi"
    else:
        strip_tags(tree, *REND_TAG_MAPPING.keys())

    # iterate over all concerned elements
    for elem in tree.iter(CONVERSIONS.keys()):
        CONVERSIONS[elem.tag](elem)  # type: ignore[index]
    # images
    if options.images:
        for elem in tree.iter("img"):
            elem.tag = "graphic"
        # move images out of links to prevent duplication/loss
        if options.links:
            for ref in list(tree.iter("ref")):
                graphics = list(ref.iter("graphic"))
                # iterate in reverse so addnext preserves original order
                for graphic in reversed(graphics):
                    ref.addnext(graphic)
                # remove ref if it only contained images (no text),
                # its leftover children (picture, source) would
                # otherwise trigger justext fallback and lose images
                if graphics and not ref.text_content().strip():
                    delete_element(ref)

    return tree


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


def build_html_output(document: Document, with_metadata: bool = False) -> str:
    "Convert the document to HTML and return a string."
    html_tree = convert_to_html(document.body)

    if with_metadata:
        head = Element("head")
        for item, value in meta_items(document):
            SubElement(head, "meta", name=item, content=value)
        html_tree.insert(0, head)

    return tostring(html_tree, pretty_print=True, encoding="unicode").strip()

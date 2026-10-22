"""Input handling and text helpers — same interface as trafilatura.utils.

Portions vendored from trafilatura 2.3.1 (https://github.com/adbar/trafilatura), Apache-2.0,
Copyright 2019-present Adrien Barbaresi and contributors: `load_html`, `repair_faulty_html`,
`fromstring_bytes`, `sanitize_tree`, `text_chars_test`, `textfilter`, `as_list`, `image_src`,
`is_image_file`, `trim`, `sanitize`, `line_processing`, `remove_control_characters`,
`normalize_unicode`. Copied verbatim except absolute imports; see NOTICE.md.
"""

import bz2
import gzip
import logging
import lzma
import re
import zipfile
from collections.abc import Iterable, Mapping
from functools import lru_cache
from io import BytesIO
from typing import Any, Final, Literal
from unicodedata import normalize

from charset_normalizer import from_bytes
from lxml.etree import _Element
from lxml.html import HtmlElement, HTMLParser, fromstring
from urllib3.response import HTTPResponse

LOGGER = logging.getLogger(__name__)


class Response:
    """Store information gathered in a HTTP response object."""

    __slots__ = ["data", "headers", "html", "status", "url"]

    def __init__(self, data: bytes | None, status: int, url: str) -> None:
        self.data = data
        self.headers: dict[str, str] | None = None
        self.html: str | None = None
        self.status = status
        self.url = url

    def __bool__(self) -> bool:
        return self.data is not None

    def __repr__(self) -> str:
        return self.html or decode_file(self.data)

    def store_headers(self, headerdict: Mapping[str, str]) -> None:
        """Store response headers with lowercase names."""
        self.headers = {k.lower(): v for k, v in headerdict.items()}

    def decode_data(self, decode: bool, max_size: int | None = None) -> None:
        """Decode the bytestring in data and store a string in html."""
        if decode and self.data:
            self.html = decode_file(self.data, max_size)

    def as_dict(self) -> dict[str, Any]:
        """Convert the response object to a dictionary."""
        return {attr: getattr(self, attr) for attr in self.__slots__}


##### INPUT TYPES #####

type HtmlInput = HtmlElement | HTTPResponse | Response | bytes | str

UNICODE_ALIASES: Final = frozenset({"utf-8", "utf_8"})
DETECT_SAMPLE: Final = 10000
GZIP_MAGIC: Final = b"\x1f\x8b"
BZIP_MAGIC: Final = b"BZh"
XZ_MAGIC: Final = b"\xfd7zXZ"
ZIP_MAGIC: Final = b"PK\x03\x04"

DOCTYPE_TAG = re.compile("^< ?! ?DOCTYPE[^>]*/[^<>]*>", re.IGNORECASE)
FAULTY_HTML = re.compile(r"(<html.*?)\s*/>", re.IGNORECASE)
INVALID_XML_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
LINES_TRIMMING = re.compile(r"(?<![p{P}>])\n", flags=re.UNICODE | re.MULTILINE)
IMAGE_EXTENSION = re.compile(r"[^\s]+\.(avif|bmp|gif|hei[cf]|jpe?g|png|webp)(\b|$)", re.IGNORECASE)

HTML_PARSER = HTMLParser(
    collect_ids=False, default_doctype=False, encoding="utf-8", remove_comments=True, remove_pis=True
)

FORMATTING_PROTECTED = {"cell", "head", "hi", "item", "p", "quote", "ref", "td"}
SPACING_PROTECTED = {"code", "pre"}

# Mostly filters for social media (text-level analog of the xpaths social/share tokens)
RE_FILTER = re.compile(
    r"\W*(Drucken|E-?Mail|Facebook|Flipboard|Google|Instagram|"
    r"Linkedin|Mail|PDF|Pinterest|Pocket|Print|QQ|Reddit|Twitter|"
    r"WeChat|WeiBo|Whatsapp|Xing|Mehr zum Thema:?|More on this.{,8}$)$",
    flags=re.IGNORECASE,
)

##### DECOMPRESSION #####


def _capped(chunks: Iterable[bytes], max_size: int) -> bytes:
    """Accumulate decompressed chunks, rejecting payloads over max_size."""
    out = bytearray()
    for chunk in chunks:
        out += chunk
        if len(out) > max_size:
            message = "decompressed content exceeds MAX_FILE_SIZE"
            raise ValueError(message)
    return bytes(out)


def handle_compressed_file(filecontent: bytes, max_size: int | None = None) -> bytes:
    """Decompress a binary string by its magic number, capped against decompression bombs."""
    limit = max_size if max_size is not None else 20_000_000
    try:
        if filecontent.startswith(GZIP_MAGIC):
            return _capped([gzip.decompress(filecontent)], limit)
        if filecontent.startswith(BZIP_MAGIC):
            return _capped([bz2.decompress(filecontent)], limit)
        if filecontent.startswith(XZ_MAGIC):
            return _capped([lzma.decompress(filecontent)], limit)
        if filecontent.startswith(ZIP_MAGIC):
            with zipfile.ZipFile(BytesIO(filecontent)) as archive:
                members = [name for name in archive.namelist() if name.lower().endswith((".html", ".htm"))]
                return _capped([archive.read(name) for name in members[:1]], limit)
    except (OSError, ValueError, zipfile.BadZipFile, EOFError, lzma.LZMAError):
        LOGGER.warning("invalid or oversized compressed file")
    return filecontent


##### DECODING #####


def detect_encoding(bytesobject: bytes) -> list[str]:
    """Read all input or first chunk and return a list of encodings."""
    try:
        bytesobject.decode("UTF-8")
        return ["utf-8"]
    except UnicodeDecodeError:
        pass
    sample = (
        bytesobject
        if len(bytesobject) < DETECT_SAMPLE
        else bytesobject[: DETECT_SAMPLE // 2] + bytesobject[-DETECT_SAMPLE // 2 :]
    )
    detection_results = from_bytes(sample) or from_bytes(bytesobject)
    return [guess.encoding for guess in detection_results if guess.encoding not in UNICODE_ALIASES]


def decode_file(filecontent: bytes | str | None, max_size: int | None = None) -> str:
    """Decompress the bytestring if necessary, guess its encoding and decode to a Unicode string."""
    if filecontent is None:
        return ""
    if isinstance(filecontent, str):
        return filecontent
    filecontent = handle_compressed_file(filecontent, max_size)
    try:
        return filecontent.decode("utf-8")
    except UnicodeDecodeError:
        pass
    for guessed_encoding in detect_encoding(filecontent):
        try:
            return filecontent.decode(guessed_encoding)
        except (LookupError, UnicodeDecodeError):
            LOGGER.warning("wrong encoding detected: %s", guessed_encoding)
    return str(filecontent, encoding="utf-8", errors="replace")


##### LOADING #####


def is_dubious_html(beginning: str) -> bool:
    "Assess if the object is proper HTML (awith a corresponding tag or declaration)."
    return "html" not in beginning


def repair_faulty_html(htmlstring: str, beginning: str) -> str:
    "Repair faulty HTML strings to make then palatable for libxml2."
    htmlstring = INVALID_XML_CHARS.sub("", htmlstring)
    # libxml2/LXML issue: https://bugs.launchpad.net/lxml/+bug/1955915
    if "doctype" in beginning:
        firstline, _, rest = htmlstring.partition("\n")
        htmlstring = DOCTYPE_TAG.sub("", firstline, count=1) + "\n" + rest
    # self-closing <html/> in the first lines
    for line in htmlstring[:4096].splitlines()[:4]:
        if "<html" in line and line.endswith("/>"):
            htmlstring = FAULTY_HTML.sub(r"\1>", htmlstring, count=1)
            break
    return htmlstring


def fromstring_bytes(htmlobject: str) -> HtmlElement | None:
    "Try to pass bytes to LXML parser."
    try:
        return fromstring(htmlobject.encode("utf8", "surrogatepass"), parser=HTML_PARSER)
    except Exception as err:  # noqa: BLE001
        LOGGER.error("lxml parser bytestring %s", err)
    return None


def load_html(htmlobject: HtmlInput, max_size: int | None = None) -> HtmlElement | None:
    """Load object given as input and validate its type
    (accepted: lxml.html tree, trafilatura/urllib3 response, bytestring and string).

    Expects a full document: the dubious-HTML check below rejects a single-block
    fragment (e.g. "<p>x</p>" alone has one child and is treated as not-quite-HTML).
    Wrap bare fragments in an extra element (e.g. f"<div>{fragment}</div>") first.
    """
    # use tree directly
    if isinstance(htmlobject, HtmlElement):
        return htmlobject
    # use trafilatura or urllib3 responses directly
    if isinstance(htmlobject, HTTPResponse) or hasattr(htmlobject, "data"):
        htmlobject = htmlobject.data  # ty: ignore[invalid-assignment]
    # do not accept any other type after this point
    if not isinstance(htmlobject, (bytes, str)):
        raise TypeError("incompatible input type", type(htmlobject))
    # start processing
    tree = None
    # try to guess encoding and decode file: if None then keep original
    htmlobject = decode_file(htmlobject, max_size)
    # sanity checks
    beginning = htmlobject[:50].lower()
    check_flag = is_dubious_html(beginning)
    # repair first
    htmlobject = repair_faulty_html(htmlobject, beginning)
    # first pass: use Unicode string
    fallback_parse = False
    try:
        tree = fromstring(htmlobject, parser=HTML_PARSER)
    except ValueError:
        # "Unicode strings with encoding declaration are not supported."
        tree = fromstring_bytes(htmlobject)
        fallback_parse = True
    except Exception as err:  # noqa: BLE001
        LOGGER.error("lxml parsing failed: %s", err)
    # second pass: try passing bytes to LXML
    if (tree is None or len(tree) < 1) and not fallback_parse:
        tree = fromstring_bytes(htmlobject)
    # rejection test: is it (well-formed) HTML at all?
    # log parsing errors
    if tree is not None and check_flag is True and len(tree) < 2:
        LOGGER.error("parsed tree length: %s, wrong data type or not valid HTML", len(tree))
        tree = None
    return tree


##### TEXT #####


@lru_cache(maxsize=2**14)
def return_printables_and_spaces(char: str) -> str:
    "Return a character if it belongs to certain classes"
    return char if char.isprintable() or char.isspace() else ""


def remove_control_characters(string: str) -> str:
    """Prevent non-printable and XML invalid character errors"""
    # in case most strings are already clean
    if string.isprintable():
        return string
    return "".join(map(return_printables_and_spaces, string))


def normalize_unicode(string: str, unicodeform: Literal["NFC", "NFD", "NFKC", "NFKD"] = "NFC") -> str:
    "Normalize the given string to the specified unicode format."
    return normalize(unicodeform, string)


@lru_cache(maxsize=1024)
def trim(string: str) -> str:
    "Remove unnecessary spaces within a text string."
    try:
        # remove newlines that are not related to punctuation or markup + proper trimming
        return " ".join(string.split()).strip()
    except (AttributeError, TypeError):
        return ""


@lru_cache(maxsize=1024)
def line_processing(line: str, preserve_space: bool = False, trailing_space: bool = False) -> str | None:
    """Remove HTML space entities, then discard incompatible unicode
    and invalid XML characters on line level"""
    # spacing HTML entities: https://www.w3.org/MarkUp/html-spec/html-spec_13.html
    # unique code spaces
    new_line = remove_control_characters(line.replace("&#13;", "\r").replace("&#10;", "\n").replace("&nbsp;", "\u00a0"))
    if not preserve_space:
        # remove newlines that are not related to punctuation or markup
        # remove non-printable chars and normalize space characters (including Unicode spaces)
        new_line = trim(LINES_TRIMMING.sub(r" ", new_line))
        # prune empty lines
        if all(map(str.isspace, new_line)):
            new_line = None  # type: ignore[assignment]
        elif trailing_space:
            space_before = " " if line[0].isspace() else ""
            space_after = " " if line[-1].isspace() else ""
            new_line = f"{space_before}{new_line}{space_after}"
    return new_line


def sanitize(text: str, preserve_space: bool = False, trailing_space: bool = False) -> str | None:
    """Convert text and discard incompatible and invalid characters"""
    # consider all text as a single line
    if trailing_space:
        return line_processing(text, preserve_space, True)
    # process line by line
    try:
        return "\n".join(filter(None, (line_processing(line, preserve_space) for line in text.splitlines()))).replace(
            "\u2424",
            "",
        )
    except AttributeError:
        return None


def sanitize_tree(tree: _Element) -> _Element:
    """Trims spaces, removes control characters and normalizes unicode"""
    for elem in tree.iter():
        parent = elem.getparent()
        parent_tag = parent.tag if parent is not None else ""

        # preserve space if the element or its parent is a specific tag, or if the element has text and children
        # the last part is relevant for item elements with ref inside for example
        preserve_space = elem.tag in SPACING_PROTECTED or parent_tag in SPACING_PROTECTED
        trailing_space = elem.tag in FORMATTING_PROTECTED or parent_tag in FORMATTING_PROTECTED or preserve_space

        # remove invalid attributes (copy: pop() during iteration)
        for attribute in list(elem.attrib):
            if ":" in attribute:  # colon is reserved for namespaces in XML
                # a declared prefix with a literal colon name is unreachable via parsing
                if not elem.attrib[attribute] or attribute.split(":", 1)[0] not in tree.nsmap:  # pragma: no branch
                    elem.attrib.pop(attribute)

        if elem.text:
            elem.text = sanitize(elem.text, preserve_space, trailing_space)
        if elem.tail:
            elem.tail = sanitize(elem.tail, preserve_space, trailing_space)
    return tree


def textfilter(element: _Element) -> bool:
    """Filter out unwanted text"""
    testtext = element.tail if element.text is None else element.text
    # to check: line len → continue if len(line) <= 5
    return not testtext or testtext.isspace() or any(map(RE_FILTER.match, testtext.splitlines()))


def text_chars_test(string: str | None) -> bool:
    """Determine if a string is only composed of spaces and/or control characters"""
    return bool(string and not string.isspace())


def as_list(value: Any) -> list[Any]:
    "Normalize a JSON-like value that may be a single object, a list of them, or None."
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def image_src(element: _Element) -> str | None:
    "Image source of an element: src, data-src, or the first data-src* attribute pointing to an image file."
    for attr in ("data-src", "src"):
        src = element.get(attr, "")
        if is_image_file(src):
            return src
    return next((v for a, v in element.attrib.items() if a.startswith("data-src") and is_image_file(v)), None)


def is_image_file(imagesrc: str | None) -> bool:
    """Check if the observed string corresponds to a valid image extension.
    Use a length threshold and apply a regex on the content."""
    if imagesrc is None or len(imagesrc) > 8192:
        return False
    return bool(IMAGE_EXTENSION.search(imagesrc))

"""Input handling: Response, decoding, compressed files and `load_html` — same interface as trafilatura.utils.

Difference: `load_html` returns a normalized HTML **string** (the Rust engine parses it), not an lxml tree.
"""

import bz2
import gzip
import logging
import lzma
import re
import unicodedata
import zipfile
from collections.abc import Iterable, Mapping
from io import BytesIO
from pathlib import Path
from typing import Any, Final, Literal

from charset_normalizer import from_bytes

LOGGER = logging.getLogger(__name__)


class Response:
    """Information gathered in a HTTP response object."""

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

type FileInput = str | bytes | Path
type HtmlInput = FileInput | Response
type UnicodeForm = Literal["NFC", "NFD", "NFKC", "NFKD"]

UNICODE_ALIASES: Final = frozenset({"utf-8", "utf_8"})
DETECT_SAMPLE: Final = 10000
INVALID_XML_CHARS: Final = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
LINES_TRIMMING: Final = re.compile(r"(?<![p{P}>])\n", flags=re.UNICODE | re.MULTILINE)
GZIP_MAGIC: Final = b"\x1f\x8b"
BZIP_MAGIC: Final = b"BZh"
XZ_MAGIC: Final = b"\xfd7zXZ"
ZIP_MAGIC: Final = b"PK\x03\x04"

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
    """Assess if the object is proper HTML (with a corresponding tag or declaration)."""
    return "html" not in beginning and "<" not in beginning


def load_html(htmlobject: HtmlInput, max_size: int | None = None) -> str | None:
    """Normalize any accepted input to an HTML string, or None when there is nothing to parse.

    Accepts str, bytes (decompressed and decoded), a path-like or a `Response`.
    """
    match htmlobject:
        case Response() as response:
            html = response.html if response.html is not None else decode_file(response.data, max_size)
        case Path() as path:
            html = decode_file(path.read_bytes(), max_size) if path.is_file() else None
        case bytes() as data:
            html = decode_file(data, max_size)
        case str() as text if "<" not in text[:200]:
            ### A string without markup is treated as a path first, then as raw content.
            path = Path(text)
            html = decode_file(path.read_bytes(), max_size) if path.is_file() else text
        case str() as text:
            html = text
        case _:
            LOGGER.error("unsupported input type: %s", type(htmlobject).__name__)
            return None
    return html if html and len(html) <= (max_size or len(html)) else None


##### TEXT #####


def normalize_unicode(string: str, unicodeform: UnicodeForm = "NFC") -> str:
    """Normalize a string to the given Unicode form."""
    return unicodedata.normalize(unicodeform, string)


def remove_control_characters(string: str) -> str:
    """Remove invalid XML and control characters from a string."""
    return INVALID_XML_CHARS.sub("", string)


def line_processing(line: str, preserve_space: bool = False, trailing_space: bool = False) -> str | None:
    """Remove control characters, normalize spaces and line endings of one line."""
    line = remove_control_characters(line)
    line = line.replace("\r", " ")
    if not preserve_space:
        line = re.sub(r"\s+", " ", line)
    line = line.strip() if not trailing_space else line.rstrip()
    return line or None


def sanitize(text: str, preserve_space: bool = False, trailing_space: bool = False) -> str | None:
    """Sanitize text: split into lines, process each, rejoin."""
    lines = (
        processed for line in text.splitlines() if (processed := line_processing(line, preserve_space, trailing_space))
    )
    return "\n".join(lines) or None


def trim(string: str) -> str:
    """Trim a string: remove trailing spaces of each line and trailing newlines."""
    return LINES_TRIMMING.sub("", string).strip()

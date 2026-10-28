"""Input handling: Response, decoding, compression, load_html and the text helpers."""

import bz2
import gzip
import lzma
import zipfile
import zlib
from io import BytesIO
from typing import Final

import brotli
import pytest
from lxml.etree import Element
from lxml.html import fromstring

from rtrafilatura import utils
from rtrafilatura.utils import (
    HAS_ZSTD,
    MAX_MEMBERS,
    Response,
    absolute_url,
    as_list,
    decode_file,
    detect_encoding,
    extract_domain,
    fix_relative_urls,
    fromstring_bytes,
    get_base_url,
    handle_compressed_file,
    image_src,
    is_dubious_html,
    is_image_file,
    line_processing,
    load_html,
    normalize_unicode,
    remove_control_characters,
    repair_faulty_html,
    safe_base_url,
    safe_relative_url,
    sanitize,
    sanitize_tree,
    text_chars_test,
    textfilter,
    trim,
)

FULL_PAGE = "<html><head><title>t</title></head><body><p>one</p><p>two</p></body></html>"


##### RESPONSE #####


def test_response_init_and_bool() -> None:
    response = Response(data=b"<html></html>", status=200, url="https://example.org")
    assert response
    assert response.html is None
    assert not Response(data=None, status=0, url="")


def test_response_repr() -> None:
    response = Response(data=b"body", status=200, url="u")
    assert repr(response) == "body"
    response.html = "decoded"
    assert repr(response) == "decoded"
    assert repr(Response(data=None, status=0, url="u")) == ""


def test_response_headers_and_decode() -> None:
    response = Response(data=b"<p>x</p>", status=200, url="u")
    response.store_headers({"Content-Type": "text/html"})
    assert response.headers == {"content-type": "text/html"}
    response.decode_data(False)
    assert response.html is None
    response.decode_data(True)
    assert response.html == "<p>x</p>"
    empty = Response(data=b"", status=200, url="u")
    empty.decode_data(True)
    assert empty.html is None
    assert set(empty.as_dict()) == {"data", "headers", "html", "status", "url"}


##### COMPRESSION #####

PAYLOAD: Final = b"<html>hello</html>"


def zip_of(name: str, content: bytes) -> bytes:
    """A one-member zip archive."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)
    return buffer.getvalue()


CODECS: Final = {
    "gzip": gzip.compress,
    "gzip-multimember": lambda data: gzip.compress(data[:6]) + gzip.compress(data[6:]),
    "bzip2": bz2.compress,
    "xz": lzma.compress,
    "zip": lambda data: zip_of("page.html", data),
    "deflate": zlib.compress,
    "brotli": brotli.compress,
    **({"zstd": utils.zstd.compress} if HAS_ZSTD else {}),
}


@pytest.mark.parametrize("codec", list(CODECS), ids=list(CODECS))
def test_handle_compressed_file_roundtrip(codec: str) -> None:
    assert handle_compressed_file(CODECS[codec](PAYLOAD)) == PAYLOAD


@pytest.mark.parametrize("codec", list(CODECS), ids=list(CODECS))
def test_handle_compressed_file_bomb(codec: str) -> None:
    bomb = CODECS[codec](b"x" * 5000)
    assert handle_compressed_file(bomb, max_size=100) == bomb


@pytest.mark.parametrize(
    "payload",
    [b"\x1f\x8b\x08not-gzip", zip_of("notes.txt", PAYLOAD), b"<html></html>", gzip.compress(b"x") * (MAX_MEMBERS + 1)],
    ids=["corrupt-gzip", "zip-without-html", "plain", "too-many-members"],
)
def test_handle_compressed_file_unchanged(payload: bytes) -> None:
    assert handle_compressed_file(payload) == payload


def test_handle_compressed_file_text() -> None:
    assert handle_compressed_file("<html></html>") == "<html></html>"  # ty: ignore[invalid-argument-type]


##### DECODING #####


def test_detect_encoding_utf8() -> None:
    assert detect_encoding("héllo".encode()) == ["utf-8"]


def test_detect_encoding_guess() -> None:
    guesses = detect_encoding("café résumé".encode("latin-1"))
    assert "utf-8" not in guesses


def test_decode_file_paths() -> None:
    assert decode_file("already text") == "already text"
    assert decode_file(None) == ""
    assert decode_file("<p>ü</p>".encode()) == "<p>ü</p>"


def test_decode_file_guessed_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rtrafilatura.utils.detect_encoding", lambda _data: ["no-such-codec", "latin-1"])
    assert decode_file("café".encode("latin-1")) == "café"


def test_decode_file_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rtrafilatura.utils.detect_encoding", lambda _data: ["no-such-codec"])
    assert decode_file(b"caf\xe9 end") == "caf\ufffd end"


def test_decode_file_large_sample() -> None:
    data = ("x" * 12000).encode() + b"\xe9"
    assert isinstance(decode_file(data), str)


##### LOAD_HTML #####


def test_load_html_string() -> None:
    tree = load_html(FULL_PAGE)
    assert tree is not None
    assert tree.tag == "html"


def test_load_html_tree_passthrough() -> None:
    tree = fromstring(FULL_PAGE)
    assert load_html(tree) is tree


def test_load_html_bytes() -> None:
    tree = load_html(FULL_PAGE.encode())
    assert tree is not None
    assert tree.tag == "html"


def test_load_html_response() -> None:
    response = Response(data=FULL_PAGE.encode(), status=200, url="u")
    tree = load_html(response)
    assert tree is not None
    response.decode_data(True)
    assert load_html(response) is not None


def test_load_html_response_like() -> None:
    class Fake:
        data = FULL_PAGE.encode()

    assert load_html(Fake()) is not None  # ty: ignore[invalid-argument-type]


def test_load_html_rejects() -> None:
    with pytest.raises(TypeError):
        load_html(42)  # ty: ignore[invalid-argument-type]
    assert load_html("") is None
    assert load_html("<p>single fragment</p>") is None


def test_load_html_encoding_declaration() -> None:
    declared = '<?xml version="1.0" encoding="utf-8"?><html><body><p>a</p><p>b</p></body></html>'
    assert load_html(declared) is not None


def test_is_dubious_html_markup() -> None:
    assert is_dubious_html("plain words") is True
    assert is_dubious_html("<html>") is False


def test_repair_faulty_html_doctype() -> None:
    beginning = "<!doctype html>"
    faulty = '<!DOCTYPE html PUBLIC "-//W3C//DTD" "http://x/dtd">\n<html/>\n<body></body></html>'
    repaired = repair_faulty_html(faulty, beginning)
    assert "<html>" in repaired
    assert "DOCTYPE" not in repaired.split("\n")[0]
    assert repair_faulty_html("a\x00b", "a") == "ab"


def test_fromstring_bytes_failure() -> None:
    assert fromstring_bytes("") is None


def test_fromstring_bytes_ok() -> None:
    assert fromstring_bytes("<html><body><p>x</p></body></html>") is not None


##### TEXT HELPERS #####


def test_normalize_unicode_and_control() -> None:
    assert normalize_unicode("e\u0301") == "é"
    assert remove_control_characters("a\x00b\ufffec") == "abc"
    assert remove_control_characters("clean") == "clean"


def test_line_processing_spaces() -> None:
    assert line_processing("  a \t b \n c ") == "a b c"
    assert line_processing("a&#13;b&#10;c&nbsp;d") is not None
    assert line_processing("a  b", preserve_space=True) == "a  b"
    assert line_processing(" a ", trailing_space=True) == " a "
    assert line_processing("   ") is None


def test_sanitize_lines() -> None:
    assert sanitize("one\ntwo") == "one\ntwo"
    assert sanitize("   \n  ") == ""
    assert sanitize("line", trailing_space=True) == "line"
    assert sanitize(None) is None  # ty: ignore[invalid-argument-type]


def test_trim_spaces() -> None:
    assert trim("  a \n b  ") == "a b"
    assert trim(None) == ""


def test_sanitize_tree() -> None:
    tree = fromstring(
        '<html xmlns:x="urn:x"><body><p>  spaced  </p>tail<pre>  kept  </pre>'
        '<i x:bad="1" x:empty="" ok="2">t</i></body></html>'
    )
    sanitize_tree(tree)
    paragraph = tree.find(".//p")
    assert paragraph is not None
    ### p is FORMATTING_PROTECTED: one flanking space survives.
    assert paragraph.text == " spaced "
    pre = tree.find(".//pre")
    assert pre is not None
    assert pre.text == "  kept  "
    emph = tree.find(".//i")
    assert emph is not None
    ### colon attributes are dropped: the HTML parser registers no namespaces.
    assert "x:empty" not in emph.attrib
    assert "x:bad" not in emph.attrib
    assert "ok" in emph.attrib


def test_text_chars_test_and_as_list() -> None:
    assert text_chars_test("x") is True
    assert text_chars_test("  ") is False
    assert text_chars_test(None) is False
    assert as_list(None) == []
    assert as_list("x") == ["x"]
    assert as_list(["x"]) == ["x"]


def test_image_src_candidates() -> None:
    element = Element("img", src="photo.png")
    assert image_src(element) == "photo.png"
    lazy = Element("img")
    lazy.set("data-src-large", "big.jpeg")
    assert image_src(lazy) == "big.jpeg"
    assert image_src(Element("img", src="doc.pdf")) is None
    assert is_image_file(None) is False
    assert is_image_file("x" * 9000) is False


def test_textfilter_social() -> None:
    element = Element("p")
    element.text = "Facebook"
    assert textfilter(element) is True
    keep = Element("p")
    keep.text = "genuine sentence"
    assert textfilter(keep) is False
    empty = Element("p")
    assert textfilter(empty) is True


##### URLS #####


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://en.wikipedia.org/wiki/X", "wikipedia.org"),
        ("https://example.org:8443/a", "example.org"),
        ("http://192.168.1.10/a", "192.168.1.10"),
        ("https://www.bbc.co.uk/news", "www.bbc.co.uk"),
        ("http://localhost:8080/x", "localhost"),
    ],
    ids=["subdomain", "port", "ipv4", "multipart-tld-host", "no-dot-host"],
)
def test_extract_domain(url: str, expected: str) -> None:
    assert extract_domain(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.org/x", "https://example.org/x"),
        ("not a url", None),
        (None, None),
        ("ftp://example.org/x", None),
        ("http://[::1", None),
    ],
    ids=["absolute", "relative", "none", "other-scheme", "malformed"],
)
def test_absolute_url(url: str | None, expected: str | None) -> None:
    assert absolute_url(url) == expected


@pytest.mark.parametrize(
    ("base", "url", "expected"),
    [
        ("https://example.org/a/", "b/c", "https://example.org/a/b/c"),
        ("https://example.org", "//cdn.example.com/x", "http://cdn.example.com/x"),
        ("https://example.org", "{tpl}", "{tpl}"),
        ("https://example.org", "https://other.org/x", "https://other.org/x"),
    ],
    ids=["relative", "scheme-relative", "template", "external"],
)
def test_fix_relative_urls(base: str, url: str, expected: str) -> None:
    assert fix_relative_urls(base, url) == expected


def test_get_base_url_safe() -> None:
    assert get_base_url("https://example.org/a/b?c") == "https://example.org"
    assert get_base_url("example.org/a") == ""
    assert safe_base_url("http://[::1") == ""
    assert safe_relative_url("https://example.org", "http://[::1") == ""

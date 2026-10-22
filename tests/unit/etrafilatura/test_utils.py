"""Input handling: Response, decoding, compression, load_html and the text helpers."""

import bz2
import gzip
import lzma
import zipfile
from io import BytesIO

import pytest
from lxml.etree import Element
from lxml.html import fromstring

from etrafilatura.utils import (
    Response,
    as_list,
    decode_file,
    detect_encoding,
    fromstring_bytes,
    handle_compressed_file,
    image_src,
    is_dubious_html,
    is_image_file,
    line_processing,
    load_html,
    normalize_unicode,
    remove_control_characters,
    repair_faulty_html,
    sanitize,
    sanitize_tree,
    text_chars_test,
    textfilter,
    trim,
)

FULL_PAGE = "<html><head><title>t</title></head><body><p>one</p><p>two</p></body></html>"


##### Response #####


def test_utils_response_init_and_bool() -> None:
    response = Response(data=b"<html></html>", status=200, url="https://example.org")
    assert response
    assert response.html is None
    assert not Response(data=None, status=0, url="")


def test_utils_response_repr() -> None:
    response = Response(data=b"body", status=200, url="u")
    assert repr(response) == "body"
    response.html = "decoded"
    assert repr(response) == "decoded"
    assert repr(Response(data=None, status=0, url="u")) == ""


def test_utils_response_headers_and_decode() -> None:
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


##### compression #####


def test_utils_compressed_gzip() -> None:
    payload = b"<html>hello</html>"
    assert handle_compressed_file(gzip.compress(payload)) == payload


def test_utils_compressed_bzip2() -> None:
    payload = b"<html>hello</html>"
    assert handle_compressed_file(bz2.compress(payload)) == payload


def test_utils_compressed_xz() -> None:
    payload = b"<html>hello</html>"
    assert handle_compressed_file(lzma.compress(payload)) == payload


def test_utils_compressed_zip() -> None:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("page.html", "<html>zipped</html>")
    assert handle_compressed_file(buffer.getvalue()) == b"<html>zipped</html>"


def test_utils_compressed_broken() -> None:
    broken = b"\x1f\x8bnot-gzip"
    assert handle_compressed_file(broken) == broken


def test_utils_compressed_bomb() -> None:
    payload = gzip.compress(b"x" * 5000)
    assert handle_compressed_file(payload, max_size=100) == payload


def test_utils_compressed_plain_passthrough() -> None:
    assert handle_compressed_file(b"<html></html>") == b"<html></html>"


##### decoding #####


def test_utils_detect_encoding_utf8() -> None:
    assert detect_encoding("héllo".encode()) == ["utf-8"]


def test_utils_detect_encoding_guess() -> None:
    guesses = detect_encoding("café résumé".encode("latin-1"))
    assert "utf-8" not in guesses


def test_utils_decode_file_paths() -> None:
    assert decode_file("already text") == "already text"
    assert decode_file(None) == ""
    assert decode_file("<p>ü</p>".encode()) == "<p>ü</p>"


def test_utils_decode_file_guessed_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("etrafilatura.utils.detect_encoding", lambda _data: ["no-such-codec", "latin-1"])
    assert decode_file("café".encode("latin-1")) == "café"


def test_utils_decode_file_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("etrafilatura.utils.detect_encoding", lambda _data: ["no-such-codec"])
    assert decode_file(b"caf\xe9 end") == "caf\ufffd end"


def test_utils_decode_file_large_sample() -> None:
    data = ("x" * 12000).encode() + b"\xe9"
    assert isinstance(decode_file(data), str)


##### load_html #####


def test_utils_load_html_string() -> None:
    tree = load_html(FULL_PAGE)
    assert tree is not None
    assert tree.tag == "html"


def test_utils_load_html_tree_passthrough() -> None:
    tree = fromstring(FULL_PAGE)
    assert load_html(tree) is tree


def test_utils_load_html_bytes() -> None:
    tree = load_html(FULL_PAGE.encode())
    assert tree is not None
    assert tree.tag == "html"


def test_utils_load_html_response() -> None:
    response = Response(data=FULL_PAGE.encode(), status=200, url="u")
    tree = load_html(response)
    assert tree is not None
    response.decode_data(True)
    assert load_html(response) is not None


def test_utils_load_http_response_like() -> None:
    class Fake:
        data = FULL_PAGE.encode()

    assert load_html(Fake()) is not None  # ty: ignore[invalid-argument-type]


def test_utils_load_html_rejects() -> None:
    with pytest.raises(TypeError):
        load_html(42)  # ty: ignore[invalid-argument-type]
    assert load_html("") is None
    assert load_html("<p>single fragment</p>") is None


def test_utils_load_html_encoding_declaration() -> None:
    declared = '<?xml version="1.0" encoding="utf-8"?><html><body><p>a</p><p>b</p></body></html>'
    assert load_html(declared) is not None


def test_utils_is_dubious_html() -> None:
    assert is_dubious_html("plain words") is True
    assert is_dubious_html("<html>") is False


def test_utils_repair_faulty_html() -> None:
    beginning = "<!doctype html>"
    faulty = '<!DOCTYPE html PUBLIC "-//W3C//DTD" "http://x/dtd">\n<html/>\n<body></body></html>'
    repaired = repair_faulty_html(faulty, beginning)
    assert "<html>" in repaired
    assert "DOCTYPE" not in repaired.split("\n")[0]
    assert repair_faulty_html("a\x00b", "a") == "ab"


def test_utils_fromstring_bytes_failure() -> None:
    assert fromstring_bytes("") is None


def test_utils_fromstring_bytes_ok() -> None:
    assert fromstring_bytes("<html><body><p>x</p></body></html>") is not None


##### text helpers #####


def test_utils_normalize_and_control() -> None:
    assert normalize_unicode("e\u0301") == "é"
    assert remove_control_characters("a\x00b\ufffec") == "abc"
    assert remove_control_characters("clean") == "clean"


def test_utils_line_processing() -> None:
    assert line_processing("  a \t b \n c ") == "a b c"
    assert line_processing("a&#13;b&#10;c&nbsp;d") is not None
    assert line_processing("a  b", preserve_space=True) == "a  b"
    assert line_processing(" a ", trailing_space=True) == " a "
    assert line_processing("   ") is None


def test_utils_sanitize() -> None:
    assert sanitize("one\ntwo") == "one\ntwo"
    assert sanitize("   \n  ") == ""
    assert sanitize("line", trailing_space=True) == "line"
    assert sanitize(None) is None  # ty: ignore[invalid-argument-type]


def test_utils_trim() -> None:
    assert trim("  a \n b  ") == "a b"
    assert trim(None) == ""  # type: ignore[arg-type]


def test_utils_sanitize_tree() -> None:
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


def test_utils_text_chars_and_lists() -> None:
    assert text_chars_test("x") is True
    assert text_chars_test("  ") is False
    assert text_chars_test(None) is False
    assert as_list(None) == []
    assert as_list("x") == ["x"]
    assert as_list(["x"]) == ["x"]


def test_utils_images() -> None:
    element = Element("img", src="photo.png")
    assert image_src(element) == "photo.png"
    lazy = Element("img")
    lazy.set("data-src-large", "big.jpeg")
    assert image_src(lazy) == "big.jpeg"
    assert image_src(Element("img", src="doc.pdf")) is None
    assert is_image_file(None) is False
    assert is_image_file("x" * 9000) is False


def test_utils_textfilter() -> None:
    element = Element("p")
    element.text = "Facebook"
    assert textfilter(element) is True
    keep = Element("p")
    keep.text = "genuine sentence"
    assert textfilter(keep) is False
    empty = Element("p")
    assert textfilter(empty) is True

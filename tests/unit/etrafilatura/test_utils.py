"""Input handling: Response, decoding, compression, load_html, text helpers."""

import bz2
import gzip
import lzma
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from etrafilatura.utils import (
    Response,
    decode_file,
    detect_encoding,
    handle_compressed_file,
    is_dubious_html,
    line_processing,
    load_html,
    normalize_unicode,
    remove_control_characters,
    sanitize,
    trim,
)

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
    assert load_html("<html><body>x</body></html>") == "<html><body>x</body></html>"


def test_utils_load_html_bytes() -> None:
    assert load_html(b"<html>b</html>") == "<html>b</html>"


def test_utils_load_html_path(tmp_path: Path) -> None:
    page = tmp_path / "page.html"
    page.write_text("<html>file</html>")
    assert load_html(page) == "<html>file</html>"
    assert load_html(str(page)) == "<html>file</html>"


def test_utils_load_html_dubious_not_a_file() -> None:
    assert load_html("just some words without markup") == "just some words without markup"


def test_utils_load_html_response() -> None:
    response = Response(data=b"<html>r</html>", status=200, url="u")
    assert load_html(response) == "<html>r</html>"
    response.decode_data(True)
    assert load_html(response) == "<html>r</html>"


def test_utils_load_html_rejects() -> None:
    assert load_html(42) is None  # ty: ignore[invalid-argument-type]
    assert load_html("") is None
    assert load_html("<html>long</html>", max_size=4) is None


def test_utils_is_dubious_html() -> None:
    assert is_dubious_html("plain words") is True
    assert is_dubious_html("<html>") is False


##### text helpers #####


def test_utils_normalize_and_control() -> None:
    assert normalize_unicode("e\u0301") == "é"
    assert remove_control_characters("a\x00b\ufffec") == "abc"


def test_utils_line_processing() -> None:
    assert line_processing("  a \t b \r c ") == "a b c"
    assert line_processing("a  b", preserve_space=True) == "a  b"
    assert line_processing("a  ", trailing_space=True) == "a"
    assert line_processing("  ") is None


def test_utils_sanitize_and_trim() -> None:
    assert sanitize("one\ntwo") == "one\ntwo"
    assert sanitize("   \n  ") is None
    ### trim strips newlines not preceded by punctuation, like trafilatura's.
    assert trim("a \nb") == "a b"
    assert trim("  spaced  ") == "spaced"

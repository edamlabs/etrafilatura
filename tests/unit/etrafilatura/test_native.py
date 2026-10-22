"""The native bridge: options, results, error mapping."""

import pytest

from etrafilatura import _native
from etrafilatura.errors import (
    InsufficientContentError,
    LanguageMismatchError,
    MissingMetadataError,
    TreeTooLargeError,
)

ARTICLE_MIN = (
    "<html><head><title>T</title></head><body><article>"
    "<p>Enough content for the engine to keep the paragraph: it runs past every minimum "
    "size the default configuration applies to extracted text segments.</p>"
    "</article></body></html>"
)


def test_engine_version_set() -> None:
    assert _native.ENGINE_VERSION


def test_extract_html_defaults() -> None:
    result = _native.extract_html(ARTICLE_MIN)
    assert "Enough content" in result.content_text
    assert "<" in result.content_html
    assert isinstance(result.metadata, _native.MetadataResult)
    assert result.metadata.title == "T"
    assert "chars" in repr(result)


def test_extract_html_full_options() -> None:
    result = _native.extract_html(
        ARTICLE_MIN,
        url="https://example.org/page",
        target_language="en",
        fallback=False,
        focus="recall",
        comments=False,
        tables=False,
        images=True,
        links=True,
        excluded_authors=["nobody"],
        deduplicate=True,
        essential_metadata=False,
        max_tree_size=100000,
        prune_selector="script, style",
        date_mode="fast",
        min_extracted_size=1,
        min_output_size=1,
        min_output_comment_size=1,
        min_duplicate_check_size=10,
        max_duplicate_count=2,
        cache_size=8,
    )
    assert result.content_text


def test_extract_html_focus() -> None:
    for focus in ("balanced", "precision", "recall"):
        assert _native.extract_html(ARTICLE_MIN, focus=focus).content_text
    with pytest.raises(ValueError, match="focus must be"):
        _native.extract_html(ARTICLE_MIN, focus="sideways")  # ty: ignore[invalid-argument-type]


def test_extract_html_date_mode() -> None:
    for mode in ("default", "fast", "extensive", "disabled"):
        assert _native.extract_html(ARTICLE_MIN, date_mode=mode).content_text
    with pytest.raises(ValueError, match="date_mode must be"):
        _native.extract_html(ARTICLE_MIN, date_mode="solar")  # ty: ignore[invalid-argument-type]


def test_extract_html_invalid_url() -> None:
    with pytest.raises(ValueError, match="invalid url"):
        _native.extract_html(ARTICLE_MIN, url="::::")


def test_extract_html_language_mismatch() -> None:
    with pytest.raises(LanguageMismatchError) as caught:
        _native.extract_html(ARTICLE_MIN, target_language="fr")
    assert caught.value.expected == "fr"


def test_extract_html_insufficient_content() -> None:
    with pytest.raises(InsufficientContentError):
        _native.extract_html("<html><body></body></html>", fallback=False, min_output_size=10)


def test_extract_html_missing_metadata() -> None:
    with pytest.raises(MissingMetadataError):
        _native.extract_html("<html><body><p>text</p></body></html>", essential_metadata=True)


def test_extract_html_tree_too_large() -> None:
    paragraphs = "".join(
        f"<p>Paragraph number {index} with enough words to be kept by the extraction "
        f"pipeline as genuine main content of the page under test.</p>"
        for index in range(10)
    )
    page = f"<html><head><title>Big</title></head><body><article>{paragraphs}</article></body></html>"
    with pytest.raises(TreeTooLargeError) as caught:
        _native.extract_html(page, max_tree_size=1)
    assert caught.value.size >= 1


def test_extract_html_views() -> None:
    result = _native.extract_html(
        "<html><head><title>V</title></head><body><article>"
        "<p>First paragraph long enough for the extractor to accept it as the main content.</p>"
        "<p>Second paragraph gives the page the volume of a genuine article body.</p>"
        "</article></body></html>"
    )
    assert "First paragraph" in result.content_html
    assert result.comments_text == ""
    assert result.comments_html == ""


def test_extract_metadata_html_repr() -> None:
    metadata = _native.extract_metadata_html(ARTICLE_MIN)
    assert "title=" in repr(metadata)
    assert metadata.date is None
    assert metadata.categories == []


def test_extract_metadata_html_options() -> None:
    page = ARTICLE_MIN.replace("<title>T</title>", '<title>T</title><meta name="author" content="Ann Smith">')
    assert _native.extract_metadata_html(page).author == "Ann Smith"
    assert _native.extract_metadata_html(page, excluded_authors=["Ann Smith"]).author == ""
    assert _native.extract_metadata_html(page, url="https://example.org", date_mode="extensive").url


def test_extract_metadata_html_invalid() -> None:
    with pytest.raises(ValueError, match="date_mode must be"):
        _native.extract_metadata_html(ARTICLE_MIN, date_mode="nope")  # ty: ignore[invalid-argument-type]
    with pytest.raises(ValueError, match="invalid url"):
        _native.extract_metadata_html(ARTICLE_MIN, url="::::")

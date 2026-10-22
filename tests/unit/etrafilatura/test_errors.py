"""The exception tree."""

import pytest

from etrafilatura.errors import (
    DuplicateContentError,
    ExtractionError,
    InsufficientContentError,
    LanguageMismatchError,
    MissingMetadataError,
    ParseError,
    TreeTooLargeError,
)


@pytest.mark.parametrize(
    "kind",
    [
        ParseError,
        LanguageMismatchError,
        InsufficientContentError,
        MissingMetadataError,
        DuplicateContentError,
        TreeTooLargeError,
    ],
    ids=[
        "parse",
        "language-mismatch",
        "insufficient-content",
        "missing-metadata",
        "duplicate-content",
        "tree-too-large",
    ],
)
def test_extraction_root(kind: type[ExtractionError]) -> None:
    assert issubclass(kind, ExtractionError)


def test_languagemismatch_attributes() -> None:
    error = LanguageMismatchError("wrong language", "fr", "en")
    assert (error.expected, error.got) == ("fr", "en")
    assert str(error) == "wrong language"


def test_treetoolarge_size() -> None:
    error = TreeTooLargeError("too large", 42)
    assert error.size == 42


def test_insufficientcontent_caught_as_root() -> None:
    with pytest.raises(ExtractionError):
        raise InsufficientContentError("nothing left")

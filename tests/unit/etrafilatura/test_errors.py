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
)
def test_errors_rooted(kind: type[ExtractionError]) -> None:
    assert issubclass(kind, ExtractionError)


def test_errors_language_attributes() -> None:
    error = LanguageMismatchError("wrong language", "fr", "en")
    assert (error.expected, error.got) == ("fr", "en")
    assert str(error) == "wrong language"


def test_errors_tree_size_attribute() -> None:
    error = TreeTooLargeError("too large", 42)
    assert error.size == 42


def test_errors_catch_as_root() -> None:
    with pytest.raises(ExtractionError):
        raise InsufficientContentError("nothing left")

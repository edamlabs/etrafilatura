"""Every failure rtrafilatura raises, rooted in `ExtractionError`; the native engine raises into this tree.

The public extraction functions catch these and return None, like trafilatura; the classes are public
so callers who want the reason can call the native layer or inspect logs.
"""


class ExtractionError(Exception):
    """The extraction failed on this document."""


class ParseError(ExtractionError):
    """The input could not be parsed as HTML."""


class LanguageMismatchError(ExtractionError):
    """The document language is not the requested one."""

    def __init__(self, message: str, expected: str, got: str) -> None:
        super().__init__(message)
        self.expected = expected
        self.got = got


class InsufficientContentError(ExtractionError):
    """The extracted text and comments are shorter than the configured minimums."""


class MissingMetadataError(ExtractionError):
    """Essential metadata (title, url or date) is missing and was required."""


class DuplicateContentError(ExtractionError):
    """The extracted body is a duplicate of an already seen document."""


class TreeTooLargeError(ExtractionError):
    """The output tree exceeds the configured maximum number of elements."""

    def __init__(self, message: str, size: int) -> None:
        super().__init__(message)
        self.size = size

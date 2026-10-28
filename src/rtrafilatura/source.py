"""Input resolution: `input_format="auto"` fetches a URL or reads a file path; `"html"` is trafilatura's behaviour.

An `os.PathLike` is read under either format: trafilatura rejects it with a TypeError, so reading it widens the
API without changing any accepted input. A `str` is only resolved on explicit opt-in: guessing would fetch or
read on behalf of callers that pass untrusted HTML.
"""

import logging
from configparser import ConfigParser
from copy import copy
from enum import StrEnum, auto
from os import PathLike
from os.path import isfile
from pathlib import Path
from typing import Final

from rtrafilatura.downloads import fetch_response
from rtrafilatura.settings import Extractor
from rtrafilatura.utils import MAX_FILE_SIZE, HtmlInput, Response, absolute_url

LOGGER = logging.getLogger(__name__)

MAX_PATH_LENGTH: Final = 4096


class FormatSource(StrEnum):
    """How a `str` input is read."""

    HTML = auto()
    AUTO = auto()


class AutoSource:
    """Content and origin URL of an input: fetched, read from disk or passed through."""

    __slots__ = ()

    ##### PRIVATE #####

    @staticmethod
    def _bind_copy(options: Extractor, url: str) -> Extractor:
        """A copy of the options pointing at the URL."""
        bound = copy(options)
        bound.url = bound.source = url
        return bound

    @staticmethod
    def _common_read(path: Path, config: ConfigParser) -> bytes | None:
        """File content capped at MAX_FILE_SIZE, as downloads are; None when the file is larger."""
        limit = config.getint("DEFAULT", "MAX_FILE_SIZE", fallback=MAX_FILE_SIZE)
        with path.open("rb") as handle:
            content = handle.read(limit + 1)
        return content if len(content) <= limit else AutoSource._common_oversized(path, limit)

    @staticmethod
    def _common_oversized(path: Path, limit: int) -> None:
        """Log a file rejected for its size."""
        LOGGER.warning("file too large (> %s bytes): %s", limit, path)

    @staticmethod
    def _run_url(text: str) -> str | None:
        """The text as a URL to fetch: absolute http(s), one token, nothing else."""
        return absolute_url(text) if text and not any(char.isspace() for char in text) else None

    @staticmethod
    def _run_path(text: str) -> Path | None:
        """The text as an existing file: short, one line, no markup."""
        plausible = 0 < len(text) <= MAX_PATH_LENGTH and "\n" not in text and "<" not in text
        ### Path.is_file raises ENAMETOOLONG on 3.12; os.path.isfile absorbs OS and NUL-byte errors everywhere.
        return Path(text) if plausible and isfile(text) else None  # noqa: PTH113

    @staticmethod
    def _run_fetch(url: str, config: ConfigParser) -> tuple[Response | None, str]:
        """Downloaded response and the URL it ends at, after redirects."""
        response = fetch_response(url, decode=True, config=config)
        return response, response.url if response is not None else url

    def _run_text(self, text: str, config: ConfigParser) -> tuple[HtmlInput | None, str | None]:
        """A string resolved as URL, then file path, then HTML."""
        token = text.strip()
        match self._run_url(token):
            case str() as url:
                return self._run_fetch(url, config)
            case None if (path := self._run_path(token)) is not None:
                return self._common_read(path, config), None
            case _:
                return text, None

    ############################################################

    ##### PUBLIC #####

    @staticmethod
    def bind(options: Extractor, url: str | None) -> Extractor:
        """The options with a fetched URL as document URL, unless the caller set one; the caller's object untouched."""
        return options if url is None or options.url else AutoSource._bind_copy(options, url)

    def run(
        self, filecontent: HtmlInput | PathLike[str], input_format: str, config: ConfigParser
    ) -> tuple[HtmlInput | None, str | None]:
        """Content to extract and the URL it was fetched from, if any; None content when a fetch fails or a file is too large."""
        mode = FormatSource(input_format)
        match filecontent:
            case PathLike():
                return self._common_read(Path(filecontent), config), None
            case str() if mode is FormatSource.AUTO:
                return self._run_text(filecontent, config)
            case _:
                return filecontent, None

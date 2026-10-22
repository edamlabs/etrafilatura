"""Configuration objects and the `Document` class — same interface as trafilatura.settings."""

import json
import logging
from configparser import ConfigParser
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any, Final

from etrafilatura.deduplication import LRUCache
from etrafilatura.utils import line_processing

LOGGER = logging.getLogger(__name__)

SUPPORTED_FMT_CLI: Final = ("csv", "html", "json", "markdown", "txt", "xml", "xmltei", "yaml")
SUPPORTED_FORMATS: Final = frozenset(SUPPORTED_FMT_CLI) | {"python"}

# Metadata is emitted as a YAML-style header; values such as a title containing ": "
# otherwise produce invalid YAML or get reinterpreted as a non-string.
YAML_FIELDS: Final = [
    "title",
    "author",
    "url",
    "hostname",
    "description",
    "sitename",
    "date",
    "categories",
    "tags",
    "fingerprint",
    "id",
    "license",
]
MAX_METADATA_LENGTH: Final = 10000
YAML_RESERVED: Final = frozenset({"true", "false", "yes", "no", "on", "off", "y", "n", "null", "none", "~"})


def use_config(filename: str | None = None, config: ConfigParser | None = None) -> ConfigParser:
    """Use configuration object or read and parse a settings file."""
    if config is not None:
        return config
    parser = ConfigParser()
    default_file = str(Path(__file__).parent / "settings.cfg")
    if filename is None:
        parser.read(default_file)
    else:
        if not Path(filename).is_file():
            message = "The given config file does not exist"
            raise FileNotFoundError(message)
        ### Seed defaults first so a partial user file only overrides the keys it sets.
        parser.read([default_file, filename])
    return parser


DEFAULT_CONFIG = use_config()


def _get_optional_int(config: ConfigParser, option: str) -> int | None:
    """Read an optional positive integer setting; None when empty or non-numeric."""
    value = config.get("DEFAULT", option, fallback="").strip()
    return int(value) if value.isdigit() else None


def set_date_params(extensive: bool = True) -> dict[str, Any]:
    """Provide default parameters for date extraction."""
    return {
        "original_date": True,
        "extensive_search": extensive,
        "max_date": datetime.now().astimezone().strftime("%Y-%m-%d"),
    }


def _yaml_scalar(value: str) -> str:
    """Render a metadata string as a plain or double-quoted YAML-safe scalar."""
    if (
        value
        and value == value.strip()
        and value[0].isalpha()
        and ": " not in value
        and " #" not in value
        and not value.endswith(":")
        and value.lower() not in YAML_RESERVED
        and all(ch >= " " and ch != "\x7f" for ch in value)
    ):
        return value
    # a JSON string is always a valid, exactly round-tripping YAML double-quoted scalar
    return json.dumps(value)


class Extractor:
    """Stores all extraction options; same slots and semantics as trafilatura.settings.Extractor."""

    __slots__ = [
        "author_blacklist",
        "comments",
        "config",
        "date_params",
        "dedup",
        "fast",
        "focus",
        "format",
        "formatting",
        "images",
        "lang",
        "links",
        "max_file_size",
        "max_repetitions",
        "max_tree_size",
        "min_duplcheck_size",
        "min_extracted_size",
        "min_file_size",
        "min_output_comm_size",
        "min_output_size",
        "only_with_metadata",
        "source",
        "tables",
        "tei_validation",
        "url",
        "url_blacklist",
        "with_metadata",
    ]

    def __init__(
        self,
        *,
        config: ConfigParser | None = DEFAULT_CONFIG,
        output_format: str = "txt",
        fast: bool = False,
        precision: bool = False,
        recall: bool = False,
        comments: bool = True,
        formatting: bool | None = None,
        links: bool = False,
        images: bool = False,
        tables: bool = True,
        dedup: bool | LRUCache = False,
        lang: str | None = None,
        url: str | None = None,
        source: str | None = None,
        with_metadata: bool = False,
        only_with_metadata: bool = False,
        tei_validation: bool = False,
        author_blacklist: set[str] | None = None,
        url_blacklist: set[str] | None = None,
        date_params: dict[str, Any] | None = None,
    ) -> None:
        if precision and recall:
            LOGGER.warning("'precision' and 'recall' are mutually exclusive, 'recall' takes precedence")
        if output_format not in SUPPORTED_FORMATS:
            message = f"Cannot set format, must be one of: {', '.join(sorted(SUPPORTED_FORMATS))}"
            raise AttributeError(message)
        self.config: ConfigParser = config or DEFAULT_CONFIG
        self.format = output_format
        source = url or source
        self.source = source and source.encode("utf-8", "replace").decode("utf-8")
        self.url: str | None = url
        if tei_validation and self.format != "xmltei":
            LOGGER.warning("tei_validation has no effect unless output_format is 'xmltei'")
        if formatting and self.format == "json":
            LOGGER.warning("include_formatting has no effect on JSON output")
        self.min_extracted_size: int = self.config.getint("DEFAULT", "MIN_EXTRACTED_SIZE")
        self.min_output_size: int = self.config.getint("DEFAULT", "MIN_OUTPUT_SIZE")
        self.min_output_comm_size: int = self.config.getint("DEFAULT", "MIN_OUTPUT_COMM_SIZE")
        self.min_duplcheck_size: int = self.config.getint("DEFAULT", "MIN_DUPLCHECK_SIZE")
        self.max_repetitions: int = self.config.getint("DEFAULT", "MAX_REPETITIONS")
        self.max_file_size: int = self.config.getint("DEFAULT", "MAX_FILE_SIZE")
        self.min_file_size: int = self.config.getint("DEFAULT", "MIN_FILE_SIZE")
        self.max_tree_size: int | None = _get_optional_int(self.config, "MAX_TREE_SIZE")
        self.fast: bool = fast
        self.focus: str = "recall" if recall else "precision" if precision else "balanced"
        self.comments: bool = comments
        ### Markdown implies formatting by default, but an explicit formatting=False is honored.
        self.formatting: bool = (self.format == "markdown") if formatting is None else formatting
        self.links: bool = links
        self.images: bool = images
        self.tables: bool = tables
        self.dedup: bool | LRUCache = dedup
        self.lang: str | None = lang
        self.only_with_metadata: bool = only_with_metadata
        self.tei_validation: bool = tei_validation
        self.author_blacklist: set[str] = author_blacklist or set()
        self.url_blacklist: set[str] = url_blacklist or set()
        self.with_metadata: bool = (
            with_metadata
            or only_with_metadata
            or bool(url_blacklist)
            or bool(author_blacklist)
            or output_format == "xmltei"
        )
        self.date_params: dict[str, Any] = date_params or set_date_params(
            self.config.getboolean("DEFAULT", "EXTENSIVE_DATE_SEARCH")
        )


class Document:
    """Stores all necessary data and metadata fields for extracted information.

    Difference with trafilatura: `body` and `commentsbody` hold cleaned HTML strings, not lxml trees.
    """

    __slots__ = [
        "author",
        "body",
        "categories",
        "comments",
        "commentsbody",
        "date",
        "description",
        "filedate",
        "fingerprint",
        "hostname",
        "id",
        "image",
        "language",
        "license",
        "pagetype",
        "raw_text",
        "sitename",
        "tags",
        "text",
        "title",
        "url",
    ]

    def __init__(
        self,
        *,
        title: str | None = None,
        author: str | None = None,
        url: str | None = None,
        hostname: str | None = None,
        description: str | None = None,
        sitename: str | None = None,
        date: str | None = None,
        categories: list[str] | None = None,
        tags: list[str] | None = None,
        fingerprint: str | None = None,
        idval: str | None = None,
        license_val: str | None = None,
        body: str | None = None,
        comments: str | None = None,
        commentsbody: str | None = None,
        raw_text: str | None = None,
        text: str | None = None,
        language: str | None = None,
        image: str | None = None,
        pagetype: str | None = None,
        filedate: str | None = None,
    ) -> None:
        self.title: str | None = title
        self.author: str | None = author
        self.url: str | None = url
        self.hostname: str | None = hostname
        self.description: str | None = description
        self.sitename: str | None = sitename
        self.date: str | None = date
        self.categories: list[str] | None = categories
        self.tags: list[str] | None = tags
        self.fingerprint: str | None = fingerprint
        self.id: str | None = idval
        self.license: str | None = license_val
        self.body: str = body if body is not None else ""
        self.comments: str | None = comments
        self.commentsbody: str = commentsbody if commentsbody is not None else ""
        self.raw_text: str | None = raw_text
        self.text: str | None = text
        self.language: str | None = language
        self.image: str | None = image
        self.pagetype: str | None = pagetype
        self.filedate: str | None = filedate

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        """Set a series of attributes using a dictionary."""
        doc = cls()
        for key, value in data.items():
            setattr(doc, key, value)
        return doc

    def clean_and_trim(self) -> None:
        """Limit text length and trim the attributes."""
        for slot in self.__slots__:
            value = getattr(self, slot)
            if isinstance(value, str):
                value = value[: MAX_METADATA_LENGTH - 1] + "…" if len(value) > MAX_METADATA_LENGTH else value
                value = line_processing(unescape(value))
                setattr(self, slot, value)

    def as_dict(self) -> dict[str, Any]:
        """Convert the document to a dictionary."""
        return {attr: getattr(self, attr, None) for attr in self.__slots__}

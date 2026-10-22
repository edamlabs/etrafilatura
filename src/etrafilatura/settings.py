"""Configuration objects and the `Document` class — same interface as trafilatura.settings.

The tree-processing constants (`BASIC_CLEAN_XPATH`, the inline-tag ladder) are vendored from
trafilatura 2.3.1, Apache-2.0, Copyright 2019-present Adrien Barbaresi and contributors; see NOTICE.md.
"""

import logging
from configparser import ConfigParser
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from lxml.etree import Element, XPath, _Element

from etrafilatura.utils import line_processing

if TYPE_CHECKING:
    from etrafilatura.deduplication import LRUCache

LOGGER = logging.getLogger(__name__)

SUPPORTED_FMT_CLI: Final = ("csv", "json", "html", "markdown", "txt", "xml", "xmltei")
SUPPORTED_FORMATS: Final = frozenset(SUPPORTED_FMT_CLI) | {"python"}

MAX_METADATA_LENGTH: Final = 10000
LRU_SIZE: Final = 4096


def use_config(filename: str | None = None, config: ConfigParser | None = None) -> ConfigParser:
    """Use configuration object or read and parse a settings file."""
    if config is not None:
        return config
    parser = ConfigParser()
    default_file = str(Path(__file__).parent / "settings.cfg")
    if filename is None:
        parser.read(default_file, encoding="utf-8")
    else:
        if not Path(filename).is_file():
            message = "The given config file does not exist"
            raise FileNotFoundError(message)
        ### Seed defaults first so a partial user file only overrides the keys it sets.
        parser.read([default_file, filename], encoding="utf-8")
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


##### TREE CONSTANTS (vendored) #####

# prune cookie/consent banners: fluent prose justext's density metric can't classify; class/id is
# English even on localized templates.
_COOKIE_CONSENT_RE = (
    "cookie[-_]?(?:banner|bar|consent|law|notice|policy|description)|notice[-_]{0,2}cookie"
    "|consent[-_]?(?:banner|manager|sdk)|borlabs|cookiebot|cmplz|onetrust|moove[-_]?gdpr"
)
BASIC_CLEAN_XPATH = XPath(
    ".//aside|.//div[contains(@class|@id, 'footer')]|.//fencedframe|.//footer|.//script|.//style|.//svg|.//template"
    f"|.//*[re:test(@class, '{_COOKIE_CONSENT_RE}', 'i') or re:test(@id, '{_COOKIE_CONSENT_RE}', 'i')]",
    namespaces={"re": "http://exslt.org/regular-expressions"},
)

# min length for a repeated span to count as an extraction artifact (not coincidental content).
MIN_DUPLICATE_LENGTH = 50

# the substring-dedup scans are O(n^2) in accumulated text; skip beyond this size.
DEDUPE_SCAN_CAP = 200_000

# inline-tag ladder (single source of truth shared by extractor and serializer):
INLINE_CONSUMING = {"hi", "ref", "del"}  # element folds its children into its own text
INLINE_FORMATTABLE = INLINE_CONSUMING | {"code"}  # + code: has text, rendered verbatim
INLINE_CARRIED = INLINE_FORMATTABLE | {"graphic"}  # + graphic: no text, rendered as image markup


##### EXTRACTOR #####


class Extractor:
    """Stores all extraction options; same slots and semantics as trafilatura.settings.Extractor."""

    __slots__ = [  # noqa: RUF023 — upstream declaration order
        "config",
        "format",
        "fast",
        "focus",
        "comments",
        "formatting",
        "links",
        "images",
        "tables",
        "dedup",
        "lang",
        "min_extracted_size",
        "min_output_size",
        "min_output_comm_size",
        "min_duplcheck_size",
        "max_repetitions",
        "max_file_size",
        "min_file_size",
        "max_tree_size",
        "source",
        "url",
        "with_metadata",
        "only_with_metadata",
        "tei_validation",
        "date_params",
        "author_blacklist",
        "url_blacklist",
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
        dedup: "bool | LRUCache" = False,
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


##### DOCUMENT #####


class Document:
    "Defines a class to store all necessary data and metadata fields for extracted information."

    __slots__ = [  # noqa: RUF023 — ordered by output precedence, not alphabetical
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
        "body",
        "comments",
        "commentsbody",
        "raw_text",
        "text",
        "language",
        "image",
        "pagetype",
        "filedate",
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
        body: _Element | None = None,
        comments: str | None = None,
        commentsbody: _Element | None = None,
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
        self.body: _Element = body if body is not None else Element("body")
        self.comments: str | None = comments
        self.commentsbody: _Element = commentsbody if commentsbody is not None else Element("body")
        self.raw_text: str | None = raw_text
        self.text: str | None = text
        self.language: str | None = language
        self.image: str | None = image
        self.pagetype: str | None = pagetype
        self.filedate: str | None = filedate

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        "Set a series of attributes using a dictionary."
        doc = cls()
        for key, value in data.items():
            setattr(doc, key, value)
        return doc

    def clean_and_trim(self) -> None:
        "Limit text length and trim the attributes."
        for slot in self.__slots__:
            value = getattr(self, slot)
            if isinstance(value, str):
                value = value[: MAX_METADATA_LENGTH - 1] + "…" if len(value) > MAX_METADATA_LENGTH else value
                value = line_processing(unescape(value))
                setattr(self, slot, value)

    def as_dict(self) -> dict[str, Any]:
        "Convert the document to a dictionary."
        # heterogeneous value types (str, list, lxml _Element, None)
        return {attr: getattr(self, attr, None) for attr in self.__slots__}

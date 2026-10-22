"""Type stubs for the native etrafilatura binding."""

from typing import Literal

type Focus = Literal["balanced", "precision", "recall"]
type DateMode = Literal["default", "fast", "extensive", "disabled"]

class MetadataResult:
    title: str
    author: str
    url: str
    hostname: str
    description: str
    sitename: str
    date: str | None
    categories: list[str]
    tags: list[str]
    id: str
    fingerprint: str
    license: str
    language: str
    image: str
    page_type: str

class ExtractionResult:
    content_text: str
    comments_text: str
    content_html: str
    comments_html: str
    metadata: MetadataResult

def extract_html(
    html: str,
    *,
    url: str | None = None,
    target_language: str | None = None,
    fallback: bool = True,
    focus: Focus = "balanced",
    comments: bool = True,
    tables: bool = True,
    images: bool = False,
    links: bool = False,
    excluded_authors: list[str] = ...,
    deduplicate: bool = False,
    essential_metadata: bool = False,
    max_tree_size: int | None = None,
    prune_selector: str | None = None,
    date_mode: DateMode = "default",
    min_extracted_size: int = 250,
    min_output_size: int = 1,
    min_output_comment_size: int = 1,
    min_duplicate_check_size: int = 100,
    max_duplicate_count: int = 2,
    cache_size: int = 4096,
) -> ExtractionResult: ...
def extract_metadata_html(
    html: str,
    *,
    url: str | None = None,
    excluded_authors: list[str] = ...,
    date_mode: DateMode = "default",
) -> MetadataResult: ...
def absolute_url(url: str) -> str | None: ...

ENGINE_VERSION: str

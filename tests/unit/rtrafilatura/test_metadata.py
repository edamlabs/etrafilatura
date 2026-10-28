"""Metadata extraction."""

from pathlib import Path

from rtrafilatura.metadata import extract_metadata
from rtrafilatura.settings import Document


def test_extract_metadata_full_page(metadata_page: str) -> None:
    document = extract_metadata(metadata_page)
    assert document.title == "Una página rica en metadatos"
    assert document.author == "Marta Gil"
    assert document.date == "2026-05-20"
    assert document.url == "https://example.org/es/metadatos"
    assert document.hostname == "example.org"
    assert document.sitename == "El Laboratorio"
    assert document.image == "https://example.org/img/portada.png"
    assert document.description == "Página de prueba con metadatos completos."


def test_extract_metadata_default_url(minimal_page: str) -> None:
    document = extract_metadata(minimal_page, default_url="https://fallback.example.org/page")
    assert document.url == "https://fallback.example.org/page"
    assert document.hostname == "example.org"


def test_extract_metadata_empty_input() -> None:
    document = extract_metadata("")
    assert isinstance(document, Document)
    assert document.title is None


def test_extract_metadata_bytes_input(metadata_page: str) -> None:
    document = extract_metadata(metadata_page.encode())
    assert document.title == "Una página rica en metadatos"


def test_extract_metadata_path(tmp_path: Path, metadata_page: str) -> None:
    page = tmp_path / "meta.html"
    page.write_text(metadata_page, encoding="utf-8")
    ### trafilatura raises TypeError on a Path: reading it widens the API without changing accepted inputs.
    assert extract_metadata(page).title == extract_metadata(metadata_page).title


def test_extract_metadata_author_blacklist(metadata_page: str) -> None:
    assert extract_metadata(metadata_page, author_blacklist={"Marta Gil"}).author is None
    assert extract_metadata(metadata_page, author_blacklist={"Someone Else"}).author == "Marta Gil"


def test_extract_metadata_date_modes(metadata_page: str) -> None:
    fast = extract_metadata(metadata_page, date_config={"extensive_search": False})
    extensive = extract_metadata(metadata_page, extensive=False)
    assert fast.date == "2026-05-20"
    assert extensive.date == "2026-05-20"


def test_extract_metadata_sitename_strips_at(minimal_page: str) -> None:
    page = minimal_page.replace(
        "<title>Bare Page</title>",
        '<title>Bare Page</title><meta property="og:site_name" content="@handle">',
    )
    ### The engine title-cases sitenames; the binding strips a leading @.
    assert extract_metadata(page).sitename == "Handle"


def test_extract_metadata_categories_and_tags(metadata_page: str) -> None:
    document = extract_metadata(metadata_page)
    assert document.categories or document.tags

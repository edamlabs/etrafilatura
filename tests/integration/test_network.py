"""Live network calls; deselected by default (`make integration`)."""

import pytest

from etrafilatura.core import extract
from etrafilatura.downloads import fetch_url

pytestmark = pytest.mark.integration


def test_integration_live_extraction() -> None:
    page = fetch_url("https://example.org/")
    assert page is not None
    assert "Example Domain" in page


def test_integration_end_to_end() -> None:
    page = fetch_url("https://en.wikipedia.org/wiki/Web_scraping")
    if page is None:  # pragma: no cover - network-dependent
        pytest.skip("wikipedia unreachable")
    text = extract(page, output_format="txt", url="https://en.wikipedia.org/wiki/Web_scraping")
    assert text is not None
    assert len(text) > 500

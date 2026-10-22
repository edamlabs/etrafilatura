"""Benchmarks: etrafilatura against Python trafilatura over the fixture corpus.

Run with `make benchmark`; results feed `tools/benchchart.py` (docs/benchmark.md).
"""

from pathlib import Path
from typing import Any, Final

import pytest
import trafilatura

import etrafilatura

pytestmark = pytest.mark.bench

RESOURCES: Final = Path(__file__).resolve().parent.parent / "resources" / "html"

DOCUMENTS: Final = ("minimal", "article", "comments", "tables", "real_pep8", "real_wikipedia")

LIBRARIES: Final[dict[str, Any]] = {"etrafilatura": etrafilatura, "trafilatura": trafilatura}

METHODS: Final[dict[str, Any]] = {
    "extract_txt": lambda lib, html: lib.extract(html),
    "extract_markdown": lambda lib, html: lib.extract(html, output_format="markdown"),
    "extract_xml_meta": lambda lib, html: lib.extract(html, output_format="xml", with_metadata=True),
    "bare_extraction": lambda lib, html: lib.bare_extraction(html),
    "extract_metadata": lambda lib, html: lib.extract_metadata(html),
    "html2txt": lambda lib, html: lib.html2txt(html),
    "baseline": lambda lib, html: lib.baseline(html),
}


@pytest.mark.parametrize("library", sorted(LIBRARIES))
@pytest.mark.parametrize("method", sorted(METHODS))
@pytest.mark.parametrize("document", DOCUMENTS)
def test_bench(benchmark: Any, library: str, method: str, document: str) -> None:
    """One (library, method, document) timing; pytest-benchmark calibrates the rounds."""
    html = (RESOURCES / f"{document}.html").read_text(encoding="utf-8")
    benchmark(METHODS[method], LIBRARIES[library], html)

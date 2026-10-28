"""Fixtures shared by the tools unit modules."""

from typing import Any

import pytest

##### BENCHCHART #####


@pytest.fixture
def bench_payload() -> dict[str, Any]:
    """A pytest-benchmark JSON payload: two documents, every method, both libraries."""
    methods = (
        "extract_txt",
        "extract_markdown",
        "extract_xml_meta",
        "bare_extraction",
        "extract_metadata",
        "html2txt",
        "baseline",
    )
    medians = {"rtrafilatura": 0.001, "trafilatura": 0.004}
    return {
        "machine_info": {"cpu": {"brand": "Test CPU"}, "python_implementation": "CPython"},
        "commit_info": {"id": "0123456789abcdef"},
        "benchmarks": [
            {
                "params": {"method": method, "document": document, "library": library},
                "stats": {"median": median * (index + 1)},
            }
            for method in methods
            for index, document in enumerate(("minimal", "article"))
            for library, median in medians.items()
        ],
    }

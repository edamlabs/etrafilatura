"""Fixtures shared by the tools unit modules."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from tools.health import PulseHealth, RegistryHealth

##### HEALTH #####


@pytest.fixture
def now() -> datetime:
    """The evaluation instant of the health rules."""
    return datetime(2026, 10, 15, tzinfo=UTC)


@pytest.fixture
def pulse_of(now: datetime) -> Callable[..., PulseHealth]:
    """Builder of a healthy pulse, with field overrides."""

    def _build(**overrides: Any) -> PulseHealth:
        base: dict[str, Any] = {
            "name": "trafilatura",
            "registry": RegistryHealth.CRATES,
            "released": now - timedelta(days=30),
            "repository": "nchapman/trafilatura-rs",
            "archived": False,
            "pushed": now - timedelta(days=3),
        }
        return PulseHealth(**(base | overrides))

    return _build


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
    medians = {"etrafilatura": 0.001, "trafilatura": 0.004}
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

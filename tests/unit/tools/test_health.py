"""Dependency health verdicts: pure rules over registry and repository pulses."""

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from tools.health import FindingHealth, ManifestHealth, PulseHealth, RegistryHealth, VerdictHealth

##### PULSE #####


def test_pulse_evaluate_healthy(pulse_of: Callable[..., PulseHealth], now: datetime) -> None:
    assert pulse_of().evaluate(now) == []


def test_pulse_evaluate_archived(pulse_of: Callable[..., PulseHealth], now: datetime) -> None:
    assert [finding.verdict for finding in pulse_of(archived=True).evaluate(now)] == [VerdictHealth.ARCHIVED]


def test_pulse_evaluate_missing(pulse_of: Callable[..., PulseHealth], now: datetime) -> None:
    assert [finding.verdict for finding in pulse_of(released=None).evaluate(now)] == [VerdictHealth.MISSING]


def test_pulse_evaluate_stale(pulse_of: Callable[..., PulseHealth], now: datetime) -> None:
    findings = pulse_of(released=now - timedelta(days=600)).evaluate(now)
    assert [finding.verdict for finding in findings] == [VerdictHealth.STALE]
    assert findings[0].detail == "last release 600 days ago (2025-02-22)"


def test_pulse_evaluate_dormant(pulse_of: Callable[..., PulseHealth], now: datetime) -> None:
    findings = pulse_of(pushed=now - timedelta(days=400)).evaluate(now)
    assert [finding.verdict for finding in findings] == [VerdictHealth.DORMANT]


def test_pulse_evaluate_unknown_repository(pulse_of: Callable[..., PulseHealth], now: datetime) -> None:
    assert pulse_of(repository=None, pushed=None).evaluate(now) == []


def test_pulse_evaluate_every_verdict(pulse_of: Callable[..., PulseHealth], now: datetime) -> None:
    old = now - timedelta(days=900)
    found = [finding.verdict for finding in pulse_of(archived=True, released=old, pushed=old).evaluate(now)]
    assert found == [VerdictHealth.ARCHIVED, VerdictHealth.STALE, VerdictHealth.DORMANT]


@pytest.mark.parametrize(
    ("stamp", "expected"),
    [("2026-10-15T08:00:00+00:00", datetime.fromisoformat("2026-10-15T08:00:00+00:00")), ("", None), (None, None)],
    ids=["iso", "empty", "none"],
)
def test_pulse_moment(stamp: str | None, expected: datetime | None) -> None:
    assert PulseHealth.moment(stamp) == expected


##### MANIFEST #####


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/nchapman/trafilatura-rs", "nchapman/trafilatura-rs"),
        ("https://github.com/PyO3/pyo3.git", "PyO3/pyo3"),
        ("git+https://github.com/tokio-rs/tokio#readme", "tokio-rs/tokio"),
        ("https://gitlab.com/owner/repo", None),
        (None, None),
    ],
    ids=["plain", "dot-git", "fragment", "not-github", "none"],
)
def test_manifest_repository_from_url(url: str | None, expected: str | None) -> None:
    assert ManifestHealth.repository(url) == expected


def test_manifest_run_crates_and_python_groups(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text(
        '[workspace.dependencies]\npyo3 = "0.29"\nhtml2markdown = "0.3"\n', encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["msgspec>=0.19"]\n'
        '[project.optional-dependencies]\nocr = ["liteparse>=2.16"]\nfull = ["x[ocr]"]\n'
        '[dependency-groups]\ntest = ["pytest>=9.1", "hypothesis[cli]>=6"]\ndev = [{ include-group = "test" }, "prek>=0.4"]\n',
        encoding="utf-8",
    )
    found = set(ManifestHealth(tmp_path).run())
    assert found == {
        ("pyo3", RegistryHealth.CRATES),
        ("html2markdown", RegistryHealth.CRATES),
        ("msgspec", RegistryHealth.PYPI),
        ("liteparse", RegistryHealth.PYPI),
        ("pytest", RegistryHealth.PYPI),
        ("hypothesis", RegistryHealth.PYPI),
        ("prek", RegistryHealth.PYPI),
    }


##### FINDING #####


def test_finding_report_table(pulse_of: Callable[..., PulseHealth], now: datetime) -> None:
    report = FindingHealth.report(pulse_of(archived=True).evaluate(now))
    assert "| trafilatura | crates | archived |" in report

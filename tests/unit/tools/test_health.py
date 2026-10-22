"""Dependency health verdicts: pure rules over registry and repository pulses."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from tools.health import FindingHealth, ManifestHealth, PulseHealth, RegistryHealth, VerdictHealth, evaluate_health

NOW = datetime(2026, 10, 15, tzinfo=UTC)


def pulse(**overrides) -> PulseHealth:
    base: dict[str, Any] = {
        "name": "trafilatura",
        "registry": RegistryHealth.CRATES,
        "released": NOW - timedelta(days=30),
        "repository": "nchapman/trafilatura-rs",
        "archived": False,
        "pushed": NOW - timedelta(days=3),
    }
    return PulseHealth(**(base | overrides))


def verdicts(findings: list[FindingHealth]) -> list[VerdictHealth]:
    return [finding.verdict for finding in findings]


def test_evaluate_healthy_dependency_has_no_findings():
    assert evaluate_health(pulse(), NOW) == []


def test_evaluate_archived_repository():
    assert verdicts(evaluate_health(pulse(archived=True), NOW)) == [VerdictHealth.ARCHIVED]


def test_evaluate_missing_release():
    assert verdicts(evaluate_health(pulse(released=None), NOW)) == [VerdictHealth.MISSING]


def test_evaluate_stale_release():
    assert verdicts(evaluate_health(pulse(released=NOW - timedelta(days=600)), NOW)) == [VerdictHealth.STALE]


def test_evaluate_dormant_repository():
    assert verdicts(evaluate_health(pulse(pushed=NOW - timedelta(days=400)), NOW)) == [VerdictHealth.DORMANT]


def test_evaluate_unknown_repository_is_not_a_finding():
    assert evaluate_health(pulse(repository=None, pushed=None), NOW) == []


def test_evaluate_accumulates_every_verdict():
    old = NOW - timedelta(days=900)
    found = verdicts(evaluate_health(pulse(archived=True, released=old, pushed=old), NOW))
    assert set(found) == {VerdictHealth.ARCHIVED, VerdictHealth.STALE, VerdictHealth.DORMANT}


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/nchapman/trafilatura-rs", "nchapman/trafilatura-rs"),
        ("https://github.com/PyO3/pyo3.git", "PyO3/pyo3"),
        ("git+https://github.com/tokio-rs/tokio#readme", "tokio-rs/tokio"),
        ("https://gitlab.com/owner/repo", None),
        (None, None),
    ],
)
def test_repository_from_url(url, expected):
    assert ManifestHealth.repository(url) == expected


def test_manifest_collects_crates_and_python_groups(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text('[workspace.dependencies]\npyo3 = "0.29"\nhtml2markdown = "0.3"\n')
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["msgspec>=0.19"]\n'
        '[project.optional-dependencies]\nocr = ["liteparse>=2.16"]\nfull = ["x[ocr]"]\n'
        '[dependency-groups]\ntest = ["pytest>=9.1", "hypothesis[cli]>=6"]\ndev = [{ include-group = "test" }, "prek>=0.4"]\n'
    )
    found = {(name, registry) for name, registry in ManifestHealth(tmp_path).run()}
    assert found == {
        ("pyo3", RegistryHealth.CRATES),
        ("html2markdown", RegistryHealth.CRATES),
        ("msgspec", RegistryHealth.PYPI),
        ("liteparse", RegistryHealth.PYPI),
        ("pytest", RegistryHealth.PYPI),
        ("hypothesis", RegistryHealth.PYPI),
        ("prek", RegistryHealth.PYPI),
    }


def test_report_lists_findings_as_table():
    findings = evaluate_health(pulse(archived=True), NOW)
    report = FindingHealth.report(findings)
    assert "| trafilatura | crates | archived |" in report

"""Dependency health: archived, dormant or stale upstreams of the binding, as a Markdown report."""

import argparse
import asyncio
import json
import re
import sys
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum, auto
from http import HTTPStatus
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

STALE_AFTER: Final = timedelta(days=540)
DORMANT_AFTER: Final = timedelta(days=365)
CONCURRENCY: Final = 8
TIMEOUT: Final = 30
FINDINGS_EXIT: Final = 3
GITHUB: Final = re.compile(r"github\.com[/:]([^/\s]+)/([^/\s#?]+?)(?:\.git)?(?:[/#?].*)?$")
REQUIREMENT: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")


class RegistryHealth(StrEnum):
    CRATES = auto()
    PYPI = auto()


class VerdictHealth(StrEnum):
    ARCHIVED = auto()
    MISSING = auto()
    STALE = auto()
    DORMANT = auto()


@dataclass(frozen=True, slots=True)
class PulseHealth:
    """Last signs of life of one dependency: registry release and repository activity."""

    name: str
    registry: RegistryHealth
    released: datetime | None
    repository: str | None
    archived: bool
    pushed: datetime | None


@dataclass(frozen=True, slots=True)
class FindingHealth:
    """One reason to look at a dependency."""

    name: str
    registry: RegistryHealth
    verdict: VerdictHealth
    detail: str

    @staticmethod
    def report(findings: "list[FindingHealth]") -> str:
        """Markdown table of findings."""
        rows = "\n".join(f"| {f.name} | {f.registry} | {f.verdict} | {f.detail} |" for f in findings)
        return f"| Dependency | Registry | Verdict | Detail |\n|---|---|---|---|\n{rows}\n"


##### RULES #####


def _age(moment: datetime, now: datetime) -> str:
    return f"{(now - moment).days} days ago ({moment.date().isoformat()})"


def rule_archived(pulse: PulseHealth, _now: datetime) -> FindingHealth | None:
    return (
        FindingHealth(pulse.name, pulse.registry, VerdictHealth.ARCHIVED, f"`{pulse.repository}` is archived")
        if pulse.archived
        else None
    )


def rule_missing(pulse: PulseHealth, _now: datetime) -> FindingHealth | None:
    return (
        FindingHealth(pulse.name, pulse.registry, VerdictHealth.MISSING, "no release found on the registry")
        if pulse.released is None
        else None
    )


def rule_stale(pulse: PulseHealth, now: datetime) -> FindingHealth | None:
    return (
        FindingHealth(pulse.name, pulse.registry, VerdictHealth.STALE, f"last release {_age(released, now)}")
        if (released := pulse.released) is not None and now - released > STALE_AFTER
        else None
    )


def rule_dormant(pulse: PulseHealth, now: datetime) -> FindingHealth | None:
    return (
        FindingHealth(pulse.name, pulse.registry, VerdictHealth.DORMANT, f"last push {_age(pushed, now)}")
        if (pushed := pulse.pushed) is not None and now - pushed > DORMANT_AFTER
        else None
    )


RULES: Final[tuple[Callable[[PulseHealth, datetime], FindingHealth | None], ...]] = (
    rule_archived,
    rule_missing,
    rule_stale,
    rule_dormant,
)


def evaluate_health(pulse: PulseHealth, now: datetime) -> list[FindingHealth]:
    """Every rule the pulse breaks."""
    return [finding for rule in RULES if (finding := rule(pulse, now)) is not None]


##### MANIFEST #####


class ManifestHealth:
    """Direct dependencies declared by the project manifests."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def _run_crates(self) -> Iterator[tuple[str, RegistryHealth]]:
        cargo = tomllib.loads((self._root / "Cargo.toml").read_text())
        return ((name, RegistryHealth.CRATES) for name in cargo.get("workspace", {}).get("dependencies", {}))

    def _run_python(self) -> Iterator[tuple[str, RegistryHealth]]:
        project = tomllib.loads((self._root / "pyproject.toml").read_text())
        groups = [
            *project.get("dependency-groups", {}).values(),
            *project.get("project", {}).get("optional-dependencies", {}).values(),
        ]
        requirements = [*project.get("project", {}).get("dependencies", []), *(r for g in groups for r in g)]
        return (
            (match.group(0), RegistryHealth.PYPI)
            for requirement in requirements
            if isinstance(requirement, str)
            and (match := REQUIREMENT.match(requirement))
            and match.group(0) != project.get("project", {}).get("name")
        )

    ############################################################

    @staticmethod
    def repository(url: str | None) -> str | None:
        """`owner/repo` of a GitHub URL, or None."""
        return f"{found.group(1)}/{found.group(2)}" if url and (found := GITHUB.search(url)) else None

    def run(self) -> list[tuple[str, RegistryHealth]]:
        """Unique (name, registry) pairs, crates first."""
        return list(dict.fromkeys([*self._run_crates(), *self._run_python()]))


##### PROBE #####


def _when(stamp: str | None) -> datetime | None:
    return datetime.fromisoformat(stamp) if stamp else None


def _pulse_crates(payload: Mapping[str, Any]) -> tuple[datetime | None, str | None]:
    crate = payload["crate"]
    latest = crate.get("max_stable_version") or crate.get("max_version")
    stamps = [v["created_at"] for v in payload.get("versions", []) if v["num"] == latest]
    return _when(next(iter(stamps), None)), ManifestHealth.repository(crate.get("repository"))


def _pulse_pypi(payload: Mapping[str, Any]) -> tuple[datetime | None, str | None]:
    info = payload["info"]
    files = payload.get("releases", {}).get(info["version"], [])
    stamps = sorted(f["upload_time_iso_8601"] for f in files)
    urls = [*(info.get("project_urls") or {}).values(), info.get("home_page")]
    repositories = [repo for url in urls if (repo := ManifestHealth.repository(url))]
    return _when(stamps[-1] if stamps else None), next(iter(repositories), None)


REGISTRIES: Final[Mapping[RegistryHealth, tuple[str, Callable[[Mapping[str, Any]], Any]]]] = MappingProxyType(
    {
        RegistryHealth.CRATES: ("https://crates.io/api/v1/crates/{name}", _pulse_crates),
        RegistryHealth.PYPI: ("https://pypi.org/pypi/{name}/json", _pulse_pypi),
    }
)


class ProbeHealth:
    """Registry and GitHub lookups, bounded and concurrent."""

    def __init__(self, token: str | None) -> None:
        self._token = token
        self._gate = asyncio.Semaphore(CONCURRENCY)

    def _run_get(self, url: str) -> Mapping[str, Any] | None:
        authorization = {"Authorization": f"Bearer {self._token}"} if self._token and "api.github.com" in url else {}
        request = urllib.request.Request(url, headers={"User-Agent": "etrafilatura-health", **authorization})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            error.close()
            ### A vanished package is a finding; any other failure must fail the job loudly.
            return None if error.code == HTTPStatus.NOT_FOUND else _raise(error)

    async def _run_fetch(self, url: str) -> Mapping[str, Any] | None:
        async with self._gate:
            return await asyncio.to_thread(self._run_get, url)

    async def _run_one(self, name: str, registry: RegistryHealth) -> PulseHealth:
        template, read = REGISTRIES[registry]
        payload = await self._run_fetch(template.format(name=name))
        released, repository = read(payload) if payload else (None, None)
        github = await self._run_fetch(f"https://api.github.com/repos/{repository}") if repository else None
        return PulseHealth(
            name=name,
            registry=registry,
            released=released,
            repository=repository,
            archived=bool(github and github.get("archived")),
            pushed=_when(github.get("pushed_at")) if github else None,
        )

    ############################################################

    async def run(self, dependencies: list[tuple[str, RegistryHealth]]) -> list[PulseHealth]:
        """Pulse of every dependency."""
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(self._run_one(name, registry)) for name, registry in dependencies]
        return [task.result() for task in tasks]


def _raise(error: Exception) -> None:
    raise error


##### ENTRYPOINT #####


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--token", default=None, help="GitHub token, raises the API rate limit")
    arguments = parser.parse_args()
    dependencies = ManifestHealth(arguments.root).run()
    pulses = asyncio.run(ProbeHealth(arguments.token).run(dependencies))
    now = datetime.now(UTC)
    findings = [finding for pulse in pulses for finding in evaluate_health(pulse, now)]
    arguments.output.write_text(FindingHealth.report(findings))
    sys.stdout.write(f"{len(dependencies)} dependencies checked, {len(findings)} findings\n")
    return FINDINGS_EXIT if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

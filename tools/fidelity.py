"""Extraction fidelity: a reference corpus through etrafilatura and through Python trafilatura, scored.

`make fidelity` re-measures, compares against the committed baseline and refreshes the chart.
Needs the `bench` group: `uv run --group bench python -m tools.fidelity [--update]`.
"""

import argparse
import difflib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Final

import trafilatura

import etrafilatura

ROOT: Final = Path(__file__).resolve().parent.parent
CORPUS_DIR: Final = ROOT / "tests" / "resources" / "html"
BASELINE: Final = ROOT / "docs" / "fidelity.json"
CHART: Final = ROOT / "docs" / "assets" / "fidelity.svg"
MINI: Final = ROOT / "docs" / "assets" / "fidelity-mini.svg"
TOLERANCE: Final = 0.05

FORMATS: Final = ("txt", "markdown")
EXACT_FORMATS: Final = ("txt", "markdown", "json", "xml", "xmltei", "csv", "html")
META_FIELDS: Final = ("title", "author", "date", "sitename", "url", "hostname", "categories", "tags", "pagetype")

type Scores = Mapping[str, Mapping[str, float | None]]


class CorpusFidelity:
    """Agreement of etrafilatura with Python trafilatura over the reference corpus."""

    __slots__ = ()

    ##### PRIVATE #####

    @staticmethod
    def _measure_page(html: str) -> dict[str, float | None]:
        """Agreement of one page, per text format and on metadata."""
        scores: dict[str, float | None] = {
            f"format:{name}": CorpusFidelity.agreement(
                etrafilatura.extract(html, output_format=name),
                trafilatura.extract(html, output_format=name),
            )
            for name in FORMATS
        }
        scores |= {
            f"exact:{name}": float(
                etrafilatura.extract(html, output_format=name) == trafilatura.extract(html, output_format=name)
            )
            for name in EXACT_FORMATS
        }
        ours = etrafilatura.extract_metadata(html)
        theirs = trafilatura.extract_metadata(html)
        matches = sum(getattr(ours, field) == getattr(theirs, field) for field in META_FIELDS)
        scores["metadata"] = matches / len(META_FIELDS)
        return scores

    @staticmethod
    def _chart_bar(index: int, name: str, score: float | None, *, step: int, left: int, width: int) -> tuple[str, ...]:
        """Label, track, bar and value of one metric."""
        y, ratio = 44 + index * step, score or 0.0
        tone = "#c9cbd1" if score is None else "#1b5e8f"
        value = "n/a" if score is None else f"{score:.0%}"
        return (
            (
                f'<text x="{left - 10}" y="{y + step // 2 - 4}" text-anchor="end" font-family="sans-serif" '
                f'font-size="12.5" fill="#333">{name}</text>'
            ),
            f'<rect x="{left}" y="{y}" width="{width}" height="{step - 14}" rx="3" fill="#dfe8ef"/>',
            f'<rect x="{left}" y="{y}" width="{width * ratio:.0f}" height="{step - 14}" rx="3" fill="{tone}"/>',
            (
                f'<text x="{left + width * ratio + 8:.0f}" y="{y + step // 2 - 4}" font-family="sans-serif" '
                f'font-size="12" fill="#555">{value}</text>'
            ),
        )

    @staticmethod
    def _run_update(averaged: Mapping[str, float | None], pages: int) -> str:
        """Baseline and charts rewritten; the line to print."""
        BASELINE.write_text(json.dumps(averaged, indent=2) + "\n", encoding="utf-8")
        CHART.parent.mkdir(parents=True, exist_ok=True)
        CHART.write_text(
            CorpusFidelity.chart(averaged, step=40, left=200, width=540, pages=pages, note="mean over the corpus"),
            encoding="utf-8",
        )
        MINI.write_text(
            CorpusFidelity.chart(averaged, step=34, left=170, width=420, pages=pages, note="mean over the corpus"),
            encoding="utf-8",
        )
        return f"updated {BASELINE.relative_to(ROOT)}, {CHART.relative_to(ROOT)} and {MINI.relative_to(ROOT)}\n"

    ############################################################

    ##### PUBLIC #####

    @staticmethod
    def tokens(text: str) -> tuple[str, ...]:
        """Comparable token sequence of a text output."""
        return tuple(word.lower() for word in re.findall(r"[\w']+", text))

    @staticmethod
    def agreement(ours: str | None, theirs: str | None) -> float:
        """Token agreement between the two extractions: whitespace- and markup-blind, a refusal on one side only scores 0."""
        match (ours, theirs):
            case (str(), str()):
                mine, reference = CorpusFidelity.tokens(ours), CorpusFidelity.tokens(theirs)
                return (
                    difflib.SequenceMatcher(None, mine, reference, autojunk=False).ratio()
                    if reference
                    else float(not mine)
                )
            case _:
                return float(ours is theirs)

    def measure(self) -> dict[str, dict[str, float | None]]:
        """Agreement per corpus page."""
        return {
            page.stem: self._measure_page(page.read_text(encoding="utf-8"))
            for page in sorted(CORPUS_DIR.glob("*.html"))
        }

    @staticmethod
    def means(scores: Scores) -> dict[str, float | None]:
        """Mean agreement per metric across the corpus."""
        names = sorted({name for page in scores.values() for name in page})
        return {
            name: sum(found) / len(found)
            if (found := [value for page in scores.values() if (value := page.get(name)) is not None])
            else None
            for name in names
        }

    @staticmethod
    def compare(scores: Mapping[str, float | None], baseline: Mapping[str, float | None]) -> tuple[str, ...]:
        """Regression lines against the committed baseline."""
        return tuple(
            f"{name}: {before:.0%} -> {now:.0%}"
            for name, now in scores.items()
            if now is not None
            and name in baseline
            and (before := baseline[name]) is not None
            and now < before - TOLERANCE
        )

    @staticmethod
    def chart(items: Mapping[str, float | None], *, step: int, left: int, width: int, pages: int, note: str) -> str:
        """One horizontal bar per metric: mean agreement with trafilatura, in percent."""
        height = step * len(items) + 60
        parts = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{left + width + 80}" height="{height}" role="img">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            (
                '<text x="14" y="26" font-family="sans-serif" font-size="14" font-weight="bold" '
                'fill="#333">Agreement with trafilatura (%)</text>'
            ),
            *(
                part
                for index, (name, score) in enumerate(items.items())
                for part in CorpusFidelity._chart_bar(index, name, score, step=step, left=left, width=width)
            ),
            (
                f'<text x="{left}" y="{height - 12}" font-family="sans-serif" font-size="11" fill="#777">'
                f"corpus of {pages} pages · etrafilatura vs trafilatura · {note}</text>"
            ),
            "</svg>",
        )
        return "\n".join(parts) + "\n"

    @staticmethod
    def report(scores: Scores) -> str:
        """The per-page matrix."""
        return "".join(
            f"{page:<16} "
            + "  ".join(f"{name}={'n/a' if value is None else f'{value:.1%}'}" for name, value in page_scores.items())
            + "\n"
            for page, page_scores in scores.items()
        )

    def run(self, *, update: bool) -> int:
        """Measure, print and compare; 1 on a regression beyond the tolerance."""
        scores = self.measure()
        averaged = self.means(scores)
        baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
        regressions = self.compare(averaged, baseline)
        sys.stdout.write(self.report(scores))
        sys.stdout.write("".join(f"{name:<16} {value:.1%}\n" for name, value in averaged.items() if value is not None))
        sys.stdout.write(self._run_update(averaged, len(scores)) if update else "")
        sys.stdout.write("".join(f"REGRESSION  {line}\n" for line in regressions))
        return 1 if regressions else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure extraction agreement with Python trafilatura.")
    parser.add_argument("--update", action="store_true", help="rewrite the baseline and the chart")
    raise SystemExit(CorpusFidelity().run(update=parser.parse_args().update))

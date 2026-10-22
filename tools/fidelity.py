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
META_FIELDS: Final = ("title", "author", "date", "sitename", "url")


def tokens(text: str) -> tuple[str, ...]:
    """Comparable token sequence of a text output."""
    return tuple(word.lower() for word in re.findall(r"[\w']+", text))


def agreement(ours: str | None, theirs: str | None) -> float | None:
    """Token agreement between the two extractions; None when trafilatura refuses the page."""
    if theirs is None:
        return None
    if ours is None:
        return 0.0
    a, b = tokens(ours), tokens(theirs)
    if not b:
        return 1.0 if not a else 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def measure_page(html: str) -> dict[str, float | None]:
    """Agreement of one page, per text format and on metadata."""
    scores: dict[str, float | None] = {
        f"format:{name}": agreement(
            etrafilatura.extract(html, output_format=name),
            trafilatura.extract(html, output_format=name),
        )
        for name in FORMATS
    }
    ours = etrafilatura.extract_metadata(html)
    theirs = trafilatura.extract_metadata(html)
    matches = sum(getattr(ours, field) == getattr(theirs, field) for field in META_FIELDS)
    scores["metadata"] = matches / len(META_FIELDS)
    return scores


def measure() -> dict[str, dict[str, float | None]]:
    """Agreement per corpus page."""
    return {page.stem: measure_page(page.read_text()) for page in sorted(CORPUS_DIR.glob("*.html"))}


def means(scores: Mapping[str, Mapping[str, float | None]]) -> dict[str, float | None]:
    """Mean agreement per metric across the corpus."""
    names = {name for page in scores.values() for name in page}
    averaged: dict[str, float | None] = {}
    for name in sorted(names):
        found = [value for page in scores.values() if (value := page.get(name)) is not None]
        averaged[name] = sum(found) / len(found) if found else None
    return averaged


def compare(scores: dict[str, float | None], baseline: dict[str, float | None]) -> tuple[str, ...]:
    """Regression lines against the committed baseline."""
    return tuple(
        f"{name}: {before:.0%} -> {now:.0%}"
        for name, now in scores.items()
        if now is not None and name in baseline and (before := baseline[name]) is not None and now < before - TOLERANCE
    )


def chart(items: Mapping[str, float | None], *, step: int, left: int, width: int, pages: int, note: str) -> str:
    """One horizontal bar per metric: mean agreement with trafilatura, in percent."""
    height = step * len(items) + 60
    head = (
        '<text x="14" y="26" font-family="sans-serif" font-size="14" font-weight="bold" '
        'fill="#333">Agreement with trafilatura (%)</text>'
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{left + width + 80}" height="{height}" role="img">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        head,
    ]
    for index, (name, score) in enumerate(items.items()):
        y, ratio = 44 + index * step, score or 0.0
        tone = "#c9cbd1" if score is None else "#1b5e8f"
        value = "n/a" if score is None else f"{score:.0%}"
        parts.append(
            f'<text x="{left - 10}" y="{y + step // 2 - 4}" text-anchor="end" font-family="sans-serif" '
            f'font-size="12.5" fill="#333">{name}</text>',
        )
        parts.append(f'<rect x="{left}" y="{y}" width="{width}" height="{step - 14}" rx="3" fill="#dfe8ef"/>')
        parts.append(
            f'<rect x="{left}" y="{y}" width="{width * ratio:.0f}" height="{step - 14}" rx="3" fill="{tone}"/>'
        )
        parts.append(
            f'<text x="{left + width * ratio + 8:.0f}" y="{y + step // 2 - 4}" font-family="sans-serif" '
            f'font-size="12" fill="#555">{value}</text>',
        )
    footer = (
        f'<text x="{left}" y="{height - 12}" font-family="sans-serif" font-size="11" fill="#777">'
        f"corpus of {pages} pages · etrafilatura vs trafilatura · {note}</text>"
    )
    parts += [footer, "</svg>"]
    return "\n".join(parts) + "\n"


def report(scores: Mapping[str, Mapping[str, float | None]]) -> None:
    """Print the per-page matrix."""
    for page, page_scores in scores.items():
        row = "  ".join(f"{name}={'n/a' if value is None else f'{value:.1%}'}" for name, value in page_scores.items())
        sys.stdout.write(f"{page:<16} {row}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure extraction agreement with Python trafilatura.")
    parser.add_argument("--update", action="store_true", help="rewrite the baseline and the chart")
    arguments = parser.parse_args()

    scores = measure()
    averaged = means(scores)
    baseline = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    regressions = compare(averaged, baseline)
    report(scores)
    sys.stdout.write("\n".join(f"{name:<16} {value:.1%}\n" for name, value in averaged.items() if value is not None))
    if arguments.update:
        BASELINE.write_text(json.dumps(averaged, indent=2) + "\n")
        CHART.parent.mkdir(parents=True, exist_ok=True)
        CHART.write_text(chart(averaged, step=40, left=200, width=540, pages=len(scores), note="mean over the corpus"))
        MINI.write_text(chart(averaged, step=34, left=170, width=420, pages=len(scores), note="mean over the corpus"))
        sys.stdout.write(
            f"updated {BASELINE.relative_to(ROOT)}, {CHART.relative_to(ROOT)} and {MINI.relative_to(ROOT)}\n"
        )
    sys.stdout.write("".join(f"REGRESSION  {line}\n" for line in regressions))
    return 1 if regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())

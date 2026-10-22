"""Benchmark chart and page: `bench.json` (pytest-benchmark) → docs/benchmark.md + docs/assets/benchmark.svg.

usage: uv run --group bench python -m tools.benchchart bench.json
"""

import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

ROOT: Final = Path(__file__).resolve().parent.parent
PAGE: Final = ROOT / "docs" / "benchmark.md"
CHART: Final = ROOT / "docs" / "assets" / "benchmark.svg"

OURS: Final = "#1b5e8f"
THEIRS: Final = "#c9cbd1"
METHOD_ORDER: Final = (
    "extract_txt",
    "extract_markdown",
    "extract_xml_meta",
    "bare_extraction",
    "extract_metadata",
    "html2txt",
    "baseline",
)


def collect(payload: Mapping[str, Any]) -> dict[tuple[str, str, str], float]:
    """(method, document, library) → median milliseconds."""
    timings: dict[tuple[str, str, str], float] = {}
    for entry in payload["benchmarks"]:
        params = entry["params"]
        key = (params["method"], params["document"], params["library"])
        timings[key] = entry["stats"]["median"] * 1000
    return timings


def documents(timings: Mapping[tuple[str, str, str], float]) -> tuple[str, ...]:
    """Document order as found in the corpus."""
    seen = dict.fromkeys(method_document[1] for method_document in timings)
    return tuple(seen)


def chart(timings: Mapping[tuple[str, str, str], float], docs: tuple[str, ...]) -> str:
    """Two horizontal bars per method: corpus-total median milliseconds, speedup label at the end."""
    step, left, width = 54, 190, 520
    totals = {
        (method, library): sum(timings.get((method, document, library), 0.0) for document in docs)
        for method in METHOD_ORDER
        for library in ("trafilatura", "etrafilatura")
    }
    scale = max(totals.values()) or 1.0
    height = step * len(METHOD_ORDER) + 90
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{left + width + 150}" height="{height}" role="img">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        (
            '<text x="14" y="24" font-family="sans-serif" font-size="14" font-weight="bold" fill="#333">'
            "Median time, whole corpus (ms, lower is better)</text>"
        ),
        f'<rect x="{left}" y="34" width="14" height="10" fill="{THEIRS}"/>',
        f'<text x="{left + 20}" y="43" font-family="sans-serif" font-size="11" fill="#555">trafilatura</text>',
        f'<rect x="{left + 110}" y="34" width="14" height="10" fill="{OURS}"/>',
        f'<text x="{left + 130}" y="43" font-family="sans-serif" font-size="11" fill="#555">etrafilatura</text>',
    ]
    for index, method in enumerate(METHOD_ORDER):
        top = 58 + index * step
        for row, (library, tone) in enumerate((("trafilatura", THEIRS), ("etrafilatura", OURS))):
            value = totals[(method, library)]
            y = top + row * 20
            parts.append(
                f'<text x="{left - 10}" y="{y + 12}" text-anchor="end" font-family="sans-serif" '
                f'font-size="12" fill="#333">{method if row == 0 else ""}</text>'
            )
            parts.append(f'<rect x="{left}" y="{y}" width="{width}" height="15" rx="3" fill="#eceff2"/>')
            parts.append(
                f'<rect x="{left}" y="{y}" width="{max(width * value / scale, 2):.0f}" height="15" rx="3" fill="{tone}"/>'
            )
            parts.append(
                f'<text x="{left + max(width * value / scale, 2) + 8:.0f}" y="{y + 12}" font-family="sans-serif" '
                f'font-size="11" fill="#555">{value:,.0f} ms</text>'
            )
        theirs, ours = totals[(method, "trafilatura")], totals[(method, "etrafilatura")]
        speedup = f"{theirs / ours:.1f}\u00d7" if ours else "\u221e"
        parts.append(
            f'<text x="{left + width + 90}" y="{top + 22}" font-family="sans-serif" font-size="12" '
            f'font-weight="bold" fill="{OURS}">{speedup}</text>'
        )
    parts.append(
        f'<text x="{left}" y="{height - 10}" font-family="sans-serif" font-size="11" fill="#777">'
        f"pytest-benchmark medians · {len(docs)} documents · one machine, one run</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def table(timings: Mapping[tuple[str, str, str], float], docs: tuple[str, ...]) -> str:
    """Per-document median matrix with speedups."""
    head = "| method | " + " | ".join(docs) + " |"
    rule = "|---" * (len(docs) + 1) + "|"
    rows = []
    for method in METHOD_ORDER:
        cells = []
        for document in docs:
            theirs = timings.get((method, document, "trafilatura"))
            ours = timings.get((method, document, "etrafilatura"))
            if theirs is None or ours is None or not ours:
                cells.append("—")
            else:
                cells.append(f"{ours:.2f} / {theirs:.2f} ms (**{theirs / ours:.1f}\u00d7**)")
        rows.append(f"| `{method}` | " + " | ".join(cells) + " |")
    return "\n".join([head, rule, *rows])


def page(payload: Mapping[str, Any], timings: Mapping[tuple[str, str, str], float], docs: tuple[str, ...]) -> str:
    """The generated benchmark page."""
    machine = payload.get("machine_info", {})
    cpu = (machine.get("cpu") or {}).get("brand", machine.get("system", "unknown"))
    python = (machine.get("python_implementation") or "").lower()
    commit = (payload.get("commit_info") or {}).get("id", "")[:8]
    stamp = datetime.now(UTC).date().isoformat()
    return f"""# Benchmark

etrafilatura against [trafilatura](https://pypi.org/project/trafilatura/) {_trafilatura_version()} —
pytest-benchmark medians over the fixture corpus (`tests/resources/html/`): two synthetic small pages, an article,
a comments page, a tables page, PEP 8 and a Wikipedia article (121 KB and 236 KB of real HTML).

Generated by `make benchmark` on {stamp} · {cpu} · {python or "cpython"}{f" · commit {commit}" if commit else ""}.

![Benchmark](assets/benchmark.svg)

## Matrix

Median milliseconds per call, etrafilatura / trafilatura (**speedup**):

{table(timings, docs)}

## Reproduce

```bash
make benchmark    # uv run --group bench pytest -m bench --benchmark-json=bench.json, then the chart
```

Numbers move with the machine, the Python version and the engine releases; the committed chart is a snapshot,
`make benchmark` regenerates it. Both libraries run in the same process, interleaved by pytest-benchmark,
on the same fixtures.
"""


def _trafilatura_version() -> str:
    import trafilatura  # noqa: PLC0415

    return trafilatura.__version__


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "bench.json"
    payload = json.loads(source.read_text())
    timings = collect(payload)
    docs = documents(timings)
    CHART.parent.mkdir(parents=True, exist_ok=True)
    CHART.write_text(chart(timings, docs))
    PAGE.write_text(page(payload, timings, docs))
    total_ours = sum(
        value
        for (method, _, library), value in timings.items()
        if library == "etrafilatura" and method == "extract_txt"
    )
    total_theirs = sum(
        value for (method, _, library), value in timings.items() if library == "trafilatura" and method == "extract_txt"
    )
    sys.stdout.write(
        f"extract_txt corpus totals: etrafilatura {total_ours:.0f} ms vs trafilatura {total_theirs:.0f} ms\n"
    )
    sys.stdout.write(f"wrote {PAGE.relative_to(ROOT)} and {CHART.relative_to(ROOT)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Benchmark chart and page: `bench.json` (pytest-benchmark) → docs/benchmark.md + docs/assets/benchmark.svg.

usage: uv run --group bench python -m tools.benchchart bench.json
"""

import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import trafilatura

ROOT: Final = Path(__file__).resolve().parent.parent
PAGE: Final = ROOT / "docs" / "benchmark.md"
CHART: Final = ROOT / "docs" / "assets" / "benchmark.svg"

OURS: Final = "#1b5e8f"
THEIRS: Final = "#c9cbd1"
BARS: Final = (("trafilatura", THEIRS), ("etrafilatura", OURS))
STEP: Final = 54
LEFT: Final = 190
WIDTH: Final = 520
METHOD_ORDER: Final = (
    "extract_txt",
    "extract_markdown",
    "extract_xml_meta",
    "bare_extraction",
    "extract_metadata",
    "html2txt",
    "baseline",
)

type Timings = Mapping[tuple[str, str, str], float]


class PageBenchchart:
    """Benchmark page and chart of one pytest-benchmark run."""

    __slots__ = ("_docs", "_payload", "_timings")

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = payload
        self._timings: Timings = self.collect(payload)
        self._docs = tuple(dict.fromkeys(document for _, document, _ in self._timings))

    ##### PRIVATE #####

    def _common_total(self, method: str, library: str) -> float:
        """Corpus-total median milliseconds of one method and library."""
        return sum(self._timings.get((method, document, library), 0.0) for document in self._docs)

    @staticmethod
    def _chart_bar(y: int, label: str, value: float, tone: str, scale: float) -> tuple[str, ...]:
        """Label, track, bar and value of one library row."""
        length = max(WIDTH * value / scale, 2)
        return (
            (
                f'<text x="{LEFT - 10}" y="{y + 12}" text-anchor="end" font-family="sans-serif" '
                f'font-size="12" fill="#333">{label}</text>'
            ),
            f'<rect x="{LEFT}" y="{y}" width="{WIDTH}" height="15" rx="3" fill="#eceff2"/>',
            f'<rect x="{LEFT}" y="{y}" width="{length:.0f}" height="15" rx="3" fill="{tone}"/>',
            (
                f'<text x="{LEFT + length + 8:.0f}" y="{y + 12}" font-family="sans-serif" '
                f'font-size="11" fill="#555">{value:,.0f} ms</text>'
            ),
        )

    def _chart_method(self, index: int, method: str, scale: float) -> tuple[str, ...]:
        """Both library rows of one method and its speedup label."""
        top = 58 + index * STEP
        theirs, ours = self._common_total(method, "trafilatura"), self._common_total(method, "etrafilatura")
        speedup = f"{theirs / ours:.1f}\u00d7" if ours else "\u221e"
        bars = (
            part
            for row, (library, tone) in enumerate(BARS)
            for part in self._chart_bar(
                top + row * 20, method if row == 0 else "", self._common_total(method, library), tone, scale
            )
        )
        return (
            *bars,
            (
                f'<text x="{LEFT + WIDTH + 90}" y="{top + 22}" font-family="sans-serif" font-size="12" '
                f'font-weight="bold" fill="{OURS}">{speedup}</text>'
            ),
        )

    def _table_cell(self, method: str, document: str) -> str:
        """etrafilatura / trafilatura medians of one document, with the speedup."""
        theirs = self._timings.get((method, document, "trafilatura"))
        ours = self._timings.get((method, document, "etrafilatura"))
        return "—" if theirs is None or not ours else f"{ours:.2f} / {theirs:.2f} ms (**{theirs / ours:.1f}\u00d7**)"

    ############################################################

    ##### PUBLIC #####

    @staticmethod
    def collect(payload: Mapping[str, Any]) -> dict[tuple[str, str, str], float]:
        """(method, document, library) → median milliseconds."""
        return {
            (entry["params"]["method"], entry["params"]["document"], entry["params"]["library"]): entry["stats"][
                "median"
            ]
            * 1000
            for entry in payload["benchmarks"]
        }

    @property
    def docs(self) -> tuple[str, ...]:
        """Document order as found in the corpus."""
        return self._docs

    def chart(self) -> str:
        """Two horizontal bars per method: corpus-total median milliseconds, speedup label at the end."""
        scale = max(self._common_total(method, library) for method in METHOD_ORDER for library, _ in BARS) or 1.0
        height = STEP * len(METHOD_ORDER) + 90
        parts = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{LEFT + WIDTH + 150}" height="{height}" role="img">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            (
                '<text x="14" y="24" font-family="sans-serif" font-size="14" font-weight="bold" fill="#333">'
                "Median time, whole corpus (ms, lower is better)</text>"
            ),
            f'<rect x="{LEFT}" y="34" width="14" height="10" fill="{THEIRS}"/>',
            f'<text x="{LEFT + 20}" y="43" font-family="sans-serif" font-size="11" fill="#555">trafilatura</text>',
            f'<rect x="{LEFT + 110}" y="34" width="14" height="10" fill="{OURS}"/>',
            f'<text x="{LEFT + 130}" y="43" font-family="sans-serif" font-size="11" fill="#555">etrafilatura</text>',
            *(part for index, method in enumerate(METHOD_ORDER) for part in self._chart_method(index, method, scale)),
            (
                f'<text x="{LEFT}" y="{height - 10}" font-family="sans-serif" font-size="11" fill="#777">'
                f"pytest-benchmark medians · {len(self._docs)} documents · one machine, one run</text>"
            ),
            "</svg>",
        )
        return "\n".join(parts) + "\n"

    def table(self) -> str:
        """Per-document median matrix with speedups."""
        head = "| method | " + " | ".join(self._docs) + " |"
        rule = "|---" * (len(self._docs) + 1) + "|"
        rows = (
            f"| `{method}` | " + " | ".join(self._table_cell(method, document) for document in self._docs) + " |"
            for method in METHOD_ORDER
        )
        return "\n".join([head, rule, *rows])

    def page(self) -> str:
        """The generated benchmark page."""
        machine = self._payload.get("machine_info", {})
        cpu = (machine.get("cpu") or {}).get("brand", machine.get("system", "unknown"))
        python = (machine.get("python_implementation") or "").lower()
        commit = (self._payload.get("commit_info") or {}).get("id", "")[:8]
        stamp = datetime.now(UTC).date().isoformat()
        return f"""# Benchmark

etrafilatura against [trafilatura](https://pypi.org/project/trafilatura/) {trafilatura.__version__} —
pytest-benchmark medians over the fixture corpus (`tests/resources/html/`): two synthetic small pages, an article,
a comments page, a tables page, PEP 8 and a Wikipedia article (121 KB and 236 KB of real HTML).

Generated by `make benchmark` on {stamp} · {cpu} · {python or "cpython"}{f" · commit {commit}" if commit else ""}.

![Benchmark](assets/benchmark.svg)

## Matrix

Median milliseconds per call, etrafilatura / trafilatura (**speedup**):

{self.table()}

## Reproduce

```bash
make benchmark    # uv run --group bench pytest -m bench --benchmark-json=bench.json, then the chart
```

Numbers move with the machine, the Python version and the engine releases; the committed chart is a snapshot,
`make benchmark` regenerates it. Both libraries run in the same process, interleaved by pytest-benchmark,
on the same fixtures.
"""

    def run(self, page: Path = PAGE, chart: Path = CHART) -> str:
        """Chart and page written; the summary to print."""
        chart.parent.mkdir(parents=True, exist_ok=True)
        chart.write_text(self.chart(), encoding="utf-8")
        page.write_text(self.page(), encoding="utf-8")
        return (
            f"extract_txt corpus totals: etrafilatura {self._common_total('extract_txt', 'etrafilatura'):.0f} ms"
            f" vs trafilatura {self._common_total('extract_txt', 'trafilatura'):.0f} ms\n"
            f"wrote {page} and {chart}\n"
        )


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "bench.json"
    sys.stdout.write(PageBenchchart(json.loads(source.read_text(encoding="utf-8"))).run())

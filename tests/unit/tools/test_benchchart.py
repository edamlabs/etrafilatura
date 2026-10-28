"""Benchmark page and chart: pure rendering of a pytest-benchmark payload."""

from pathlib import Path
from typing import Any

import trafilatura
from tools.benchchart import PageBenchchart


def test_pagebenchchart_collect(bench_payload: dict[str, Any]) -> None:
    timings = PageBenchchart.collect(bench_payload)
    assert len(timings) == 28
    assert timings[("extract_txt", "article", "trafilatura")] == 8.0


def test_pagebenchchart_docs_order(bench_payload: dict[str, Any]) -> None:
    assert PageBenchchart(bench_payload).docs == ("minimal", "article")


def test_pagebenchchart_table_speedups(bench_payload: dict[str, Any]) -> None:
    lines = PageBenchchart(bench_payload).table().splitlines()
    assert lines[:2] == ["| method | minimal | article |", "|---|---|---|"]
    assert lines[2] == "| `extract_txt` | 1.00 / 4.00 ms (**4.0\u00d7**) | 2.00 / 8.00 ms (**4.0\u00d7**) |"
    assert len(lines) == 9


def test_pagebenchchart_table_missing_cell(bench_payload: dict[str, Any]) -> None:
    bench_payload["benchmarks"] = [
        entry for entry in bench_payload["benchmarks"] if entry["params"]["library"] == "rtrafilatura"
    ]
    assert "| `baseline` | — | — |" in PageBenchchart(bench_payload).table()


def test_pagebenchchart_chart_bars(bench_payload: dict[str, Any]) -> None:
    svg = PageBenchchart(bench_payload).chart()
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg" width="860" height="468" role="img">')
    assert svg.endswith("</svg>\n")
    assert svg.count("4.0\u00d7") == 7
    assert "2 documents" in svg


def test_pagebenchchart_page_header(bench_payload: dict[str, Any]) -> None:
    page = PageBenchchart(bench_payload).page()
    assert page.startswith("# Benchmark\n")
    assert f"trafilatura/) {trafilatura.__version__}" in page
    assert "Test CPU · cpython · commit 01234567" in page


def test_pagebenchchart_run_writes(bench_payload: dict[str, Any], tmp_path: Path) -> None:
    page, chart = tmp_path / "benchmark.md", tmp_path / "assets" / "benchmark.svg"
    summary = PageBenchchart(bench_payload).run(page=page, chart=chart)
    assert summary.startswith("extract_txt corpus totals: rtrafilatura 3 ms vs trafilatura 12 ms\n")
    assert page.read_text(encoding="utf-8").startswith("# Benchmark")
    assert chart.read_text(encoding="utf-8").startswith("<svg")

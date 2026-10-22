"""Extraction fidelity: pure scoring and rendering, no corpus run."""

import pytest
from tools.fidelity import CorpusFidelity


def test_corpusfidelity_tokens_markup_blind() -> None:
    assert CorpusFidelity.tokens("It's  <b>Bold</b>\nText") == ("it's", "b", "bold", "b", "text")


@pytest.mark.parametrize(
    ("ours", "theirs", "expected"),
    [
        (None, None, 1.0),
        ("text", None, 0.0),
        (None, "text", 0.0),
        ("", "", 1.0),
        ("words", "", 0.0),
        ("same words here", "Same   words\nhere", 1.0),
        ("one two", "one three", 0.5),
    ],
    ids=["both-refuse", "they-refuse", "we-refuse", "both-empty", "they-empty", "whitespace-blind", "partial"],
)
def test_corpusfidelity_agreement(ours: str | None, theirs: str | None, expected: float) -> None:
    assert CorpusFidelity.agreement(ours, theirs) == expected


def test_corpusfidelity_means_skip_none() -> None:
    scores = {"a": {"x": 1.0, "y": None}, "b": {"x": 0.5, "y": None}}
    assert CorpusFidelity.means(scores) == {"x": 0.75, "y": None}


def test_corpusfidelity_compare_tolerance() -> None:
    baseline = {"x": 0.9, "y": 0.9, "z": None}
    scores = {"x": 0.8, "y": 0.86, "z": 0.1, "new": 0.0}
    assert CorpusFidelity.compare(scores, baseline) == ("x: 90% -> 80%",)


def test_corpusfidelity_chart_bars() -> None:
    svg = CorpusFidelity.chart({"x": 0.5, "y": None}, step=40, left=200, width=540, pages=3, note="n")
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg" width="820" height="140" role="img">')
    assert 'width="270" height="26" rx="3" fill="#1b5e8f"' in svg
    assert ">n/a</text>" in svg
    assert "corpus of 3 pages" in svg


def test_corpusfidelity_report_rows() -> None:
    assert CorpusFidelity.report({"page": {"x": 0.5, "y": None}}) == "page             x=50.0%  y=n/a\n"

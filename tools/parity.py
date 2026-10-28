"""Byte-parity goldens: Python trafilatura's output for every synthetic page, format and metadata switch.

`make parity` rewrites `tests/resources/parity/<page>.json`; the unit suite compares rtrafilatura
against them byte for byte. Needs the `bench` group: `uv run --group bench python -m tools.parity`.
"""

import json
from pathlib import Path
from typing import Final

import trafilatura

ROOT: Final = Path(__file__).resolve().parent.parent
HTML_DIR: Final = ROOT / "tests" / "resources" / "html"
GOLDEN_DIR: Final = ROOT / "tests" / "resources" / "parity"
PAGES: Final = ("article", "comments", "empty", "metadata", "minimal", "tables")
FORMATS: Final = ("txt", "markdown", "json", "xml", "xmltei", "csv", "html")
DATE_PARAMS: Final = {"original_date": True, "extensive_search": True, "max_date": "2026-10-22"}


class GoldenParity:
    """Golden outputs of the reference implementation, one JSON file per page."""

    __slots__ = ()

    ##### PRIVATE #####

    @staticmethod
    def _run_page(html: str) -> dict[str, str | None]:
        """Reference output of one page, keyed `<format>` and `<format>+metadata`."""
        return {
            f"{name}{'+metadata' if meta else ''}": trafilatura.extract(
                html, output_format=name, with_metadata=meta, date_extraction_params=DATE_PARAMS
            )
            for name in FORMATS
            for meta in (False, True)
        }

    ############################################################

    ##### PUBLIC #####

    def run(self) -> tuple[Path, ...]:
        """Goldens rewritten from the installed trafilatura."""
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        written = tuple(GOLDEN_DIR / f"{page}.json" for page in PAGES)
        tuple(
            path.write_text(
                json.dumps(
                    self._run_page((HTML_DIR / f"{path.stem}.html").read_text(encoding="utf-8")),
                    indent=1,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            for path in written
        )
        return written


if __name__ == "__main__":
    print(f"trafilatura {trafilatura.__version__}: {len(GoldenParity().run())} goldens")  # noqa: T201

"""The command-line entry point."""

import io
import sys
from pathlib import Path

import pytest

from etrafilatura.cli import build_parser, main


def test_cli_parser_defaults() -> None:
    args = build_parser().parse_args([])
    assert args.output_format == "txt"
    assert args.comments is True
    assert args.tables is True


def test_cli_file(article: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    page = tmp_path / "page.html"
    page.write_text(article)
    assert main([str(page)]) == 0
    assert "small tools" in capsys.readouterr().out.lower()


def test_cli_stdin(article: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(article))
    assert main([]) == 0
    assert "small tools" in capsys.readouterr().out.lower()


def test_cli_url(article: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("etrafilatura.cli.fetch_url", lambda _url: article)
    assert main(["-u", "https://example.org/page", "-o", "markdown"]) == 0
    assert capsys.readouterr().out


def test_cli_url_fetch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("etrafilatura.cli.fetch_url", lambda _url: None)
    assert main(["-u", "https://example.org/dead"]) == 1


def test_cli_no_output(tmp_path: Path) -> None:
    empty = tmp_path / "empty.html"
    empty.write_text("<html><body></body></html>")
    assert main([str(empty)]) == 1


def test_cli_every_flag(article: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    page = tmp_path / "page.html"
    page.write_text(article)
    code = main(
        [
            str(page),
            "-o",
            "txt",
            "--fast",
            "--recall",
            "--no-comments",
            "--no-tables",
            "--images",
            "--links",
            "--formatting",
            "--lang",
            "en",
            "--deduplicate",
            "--with-metadata",
            "--prune",
            "nav",
            "-v",
        ]
    )
    assert code == 0
    assert capsys.readouterr().out


def test_cli_precision_flag(article: str, tmp_path: Path) -> None:
    page = tmp_path / "page.html"
    page.write_text(article)
    assert main([str(page), "--precision", "--only-with-metadata"]) in (0, 1)


def test_cli_config_file(article: str, tmp_path: Path) -> None:
    page = tmp_path / "page.html"
    page.write_text(article)
    settings = tmp_path / "custom.cfg"
    settings.write_text("[DEFAULT]\nMIN_OUTPUT_SIZE = 1\n")
    assert main([str(page), "--config", str(settings)]) == 0


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert "engine" in capsys.readouterr().out

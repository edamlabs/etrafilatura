"""Public surface of the package."""

import re

import etrafilatura


def test_all_resolves() -> None:
    for name in etrafilatura.__all__:
        assert hasattr(etrafilatura, name), name


def test_dunders_identity() -> None:
    assert etrafilatura.__title__ == "etrafilatura"
    assert etrafilatura.__author__ == "EDamLabs"
    assert etrafilatura.__license__ == "MIT"
    assert "EDamLabs" in etrafilatura.__copyright__


def test_versions_format() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:\.\w+)?", etrafilatura.__version__)
    assert re.fullmatch(r"\d+\.\d+\.\d+(-[\w.]+)?", etrafilatura.ENGINE_VERSION)


def test_extract_dropin_syntax(article: str) -> None:
    result = etrafilatura.extract(article)
    assert result is not None
    assert "small tools" in result.lower()

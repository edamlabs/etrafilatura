"""Public surface of the package."""

import re

import rtrafilatura


def test_all_resolves() -> None:
    for name in rtrafilatura.__all__:
        assert hasattr(rtrafilatura, name), name


def test_dunders_identity() -> None:
    assert rtrafilatura.__title__ == "rtrafilatura"
    assert rtrafilatura.__author__ == "EDamLabs"
    assert rtrafilatura.__license__ == "MIT"
    assert "EDamLabs" in rtrafilatura.__copyright__


def test_versions_format() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:\.\w+)?", rtrafilatura.__version__)
    assert re.fullmatch(r"\d+\.\d+\.\d+(-[\w.]+)?", rtrafilatura.ENGINE_VERSION)


def test_extract_dropin_syntax(article: str) -> None:
    result = rtrafilatura.extract(article)
    assert result is not None
    assert "small tools" in result.lower()

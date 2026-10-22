"""Deduplication primitives."""

import pickle

import pytest

from etrafilatura.deduplication import (
    LRU_TEST,
    LRUCache,
    content_fingerprint,
    duplicate_test,
    generate_bow_hash,
    sample_tokens,
)
from etrafilatura.settings import Extractor


def test_deduplication_sample_tokens() -> None:
    text = " ".join(f"word{i}" for i in range(300))
    tokens = sample_tokens(text)
    assert len(tokens) <= 64
    assert sample_tokens("short text") == ["short", "text"]


def test_deduplication_hash_and_fingerprint() -> None:
    digest = generate_bow_hash("some content", length=24)
    assert len(digest) == 24
    first = content_fingerprint("the same content everywhere")
    assert first == content_fingerprint("the same content everywhere")
    assert first != content_fingerprint("completely different material here")


def test_deduplication_cache_operations() -> None:
    cache = LRUCache(maxsize=2)
    assert cache.get("missing") == -1
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1
    cache.put("c", 3)
    assert cache.get("b") == -1
    assert cache.increment("c") == 3
    assert cache.get("c") == 4
    cache.clear()
    assert cache.get("c") == -1
    assert bool(LRUCache()) is True


def test_deduplication_cache_invalid_size() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        LRUCache(maxsize=0)


def test_deduplication_cache_pickling() -> None:
    cache = LRUCache(maxsize=4)
    cache.put("a", 1)
    restored = pickle.loads(pickle.dumps(cache))  # noqa: S301
    assert restored.get("a") == 1
    restored.put("b", 2)
    assert cache.get("b") == -1


def test_deduplication_test_short_content() -> None:
    options = Extractor(dedup=True)
    assert duplicate_test("tiny", options) is False


def test_deduplication_test_with_scoped_cache() -> None:
    cache = LRUCache(maxsize=8)
    options = Extractor(dedup=cache)
    content = " ".join(f"token{i}" for i in range(200))
    assert duplicate_test(content, options) is False
    assert duplicate_test(content, options) is False
    assert duplicate_test(content, options) is True


def test_deduplication_test_with_global_cache() -> None:
    options = Extractor(dedup=True)
    content = " ".join(f"global{i}" for i in range(200))
    assert duplicate_test(content, options) is False
    assert LRU_TEST.get(content_fingerprint(content)) == 1

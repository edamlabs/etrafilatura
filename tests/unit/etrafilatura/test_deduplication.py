"""Deduplication primitives (vendored module): fingerprints, LRU cache, duplicate test."""

import pickle

import pytest
from lxml.html import fragment_fromstring

from etrafilatura.deduplication import (
    LRU_TEST,
    LRUCache,
    Simhash,
    content_fingerprint,
    duplicate_test,
    generate_bow_hash,
    is_similar_domain,
    sample_tokens,
)
from etrafilatura.settings import Extractor


def element_with(text: str):  # type: ignore[no-untyped-def]
    return fragment_fromstring(f"<div><p>{text}</p></div>", create_parent="body")


def test_deduplication_sample_tokens() -> None:
    tokens = sample_tokens(" ".join(f"word{i}" for i in range(300)))
    assert tokens
    assert all(len(token) > 4 for token in tokens)
    assert sample_tokens("short text") == ["short", "text"]
    assert sample_tokens("punct, only!") == ["punct", "only"]
    assert sample_tokens("... !!!") == []


def test_deduplication_hash_and_fingerprint() -> None:
    digest = generate_bow_hash("some content", length=24)
    assert len(digest) == 24
    first = content_fingerprint("the same content everywhere in this document")
    assert first == content_fingerprint("the same content everywhere in this document")
    assert first != content_fingerprint("completely different material shows up right here")
    assert all(char in "0123456789abcdef" for char in first)


def test_deduplication_simhash_validate() -> None:
    fresh = Simhash("").hash
    assert Simhash("", existing_hash=42).hash == 42
    assert Simhash("", existing_hash="2a").hash == 42
    assert Simhash("", existing_hash="123456789012345678").hash == 123456789012345678
    assert Simhash("", existing_hash="not-a-number").hash == fresh
    assert Simhash("", existing_hash=2**64).hash == fresh
    assert Simhash("some text here").similarity(Simhash("some text here")) == 1.0


def test_deduplication_similar_domain() -> None:
    assert is_similar_domain("example.org", "example.org") is True
    assert is_similar_domain("example.org", "totally-other.de") is False


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
    assert duplicate_test(element_with("tiny"), options) is False


def test_deduplication_test_with_scoped_cache() -> None:
    cache = LRUCache(maxsize=8)
    options = Extractor(dedup=cache)
    element = element_with(" ".join(f"token{i}" for i in range(200)))
    assert duplicate_test(element, options) is False
    assert duplicate_test(element, options) is False
    assert duplicate_test(element, options) is False
    assert duplicate_test(element, options) is True


def test_deduplication_test_with_global_cache() -> None:
    options = Extractor(dedup=True)
    element = element_with(" ".join(f"global{i}" for i in range(200)))
    assert duplicate_test(element, options) is False
    assert len(LRU_TEST.cache) == 1

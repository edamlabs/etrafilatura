"""Document-level deduplication: same interface as trafilatura.deduplication (subset)."""

import hashlib
import re
from collections import OrderedDict
from threading import RLock
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from etrafilatura.settings import Extractor

PUNCTUATION: Final = re.compile(r"[^\w\s]")
LRU_SIZE: Final = 4096


def sample_tokens(inputstring: str, length: int = 64) -> list[str]:
    """Return a sample of tokens from the input string."""
    without_punctuation = PUNCTUATION.sub("", inputstring)
    tokendegree = len(without_punctuation) // length or 1
    tokens = without_punctuation.split()
    return tokens[::tokendegree][:length]


def generate_bow_hash(inputstring: str, length: int = 24) -> bytes:
    """Generate a hash of a bag of words, truncated to `length` bytes."""
    sample = " ".join(sample_tokens(inputstring)).encode("utf-8")
    return hashlib.blake2b(sample, digest_size=length).digest()


def content_fingerprint(content: str) -> str:
    """Return a hex fingerprint of the content."""
    return generate_bow_hash(content).hex()


class LRUCache:
    """Least Recently Used (LRU) cache backed by an OrderedDict."""

    def __init__(self, maxsize: int = 128) -> None:
        if maxsize < 1:
            message = "maxsize must be at least 1"
            raise ValueError(message)
        self.lock = RLock()
        self.maxsize = maxsize
        self.cache: OrderedDict[str, int] = OrderedDict()

    def __getstate__(self) -> dict[str, Any]:
        with self.lock:
            state = self.__dict__.copy()
            state["cache"] = self.cache.copy()
        del state["lock"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        self.lock = RLock()

    def __bool__(self) -> bool:
        """Always true, even when empty: instances passed as dedup option enable deduplication."""
        return True

    def get(self, key: str) -> int:
        """Retrieve a value from the cache, or -1 if the key is absent."""
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
        return -1

    def put(self, key: str, value: int) -> None:
        """Store a given key in the cache, evicting the oldest entry if full."""
        with self.lock:
            self.cache[key] = value
            self.cache.move_to_end(key)
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)

    def increment(self, key: str) -> int:
        """Increment the stored count, return the previous count or -1."""
        with self.lock:
            previous = self.cache.pop(key, -1)
            self.put(key, max(previous, 0) + 1)
            return previous

    def clear(self) -> None:
        """Delete all cache content."""
        with self.lock:
            self.cache.clear()


LRU_TEST = LRUCache(maxsize=LRU_SIZE)


def duplicate_test(content: str, options: "Extractor") -> bool:
    """Check if the content was already seen, using the extractor's cache and thresholds."""
    if len(content) < options.min_duplcheck_size:
        return False
    key = content_fingerprint(content)
    cache = options.dedup if isinstance(options.dedup, LRUCache) else LRU_TEST
    return cache.increment(key) >= options.max_repetitions

"""Concurrency and volume: the GIL is released and the engine is reentrant."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser

import pytest

from rtrafilatura.core import extract
from rtrafilatura.downloads import fetch_response

pytestmark = pytest.mark.stress


def _page(index: int) -> str:
    paragraphs = "".join(
        f"<p>Paragraph {number} of article {index}: enough text for the extractor to treat "
        f"this paragraph as genuine main content and keep it through every stage.</p>"
        for number in range(20)
    )
    return (
        f"<html><head><title>Article {index}</title></head><body>"
        f"<nav><a href='/'>home</a></nav><article>{paragraphs}</article>"
        f"<footer>Copyright</footer></body></html>"
    )


def test_extract_threads(article: str) -> None:
    """One page extracted concurrently from eight threads, identical results."""
    results: list[str | None] = [None] * 8

    def worker(slot: int) -> None:
        results[slot] = extract(article)

    threads = [threading.Thread(target=worker, args=(slot,)) for slot in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    assert all(result is not None for result in results)
    assert len(set(results)) == 1


def test_extract_volume() -> None:
    """Two hundred distinct pages through a thread pool."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        outputs = list(pool.map(lambda index: extract(_page(index)), range(200), timeout=300))
    assert len(outputs) == 200
    assert all(output for output in outputs)


def test_extract_mixed_formats(article: str) -> None:
    """Every output format under contention."""
    formats = ("txt", "markdown", "xml", "json", "csv", "html", "xmltei")
    with ThreadPoolExecutor(max_workers=8) as pool:
        outputs = list(
            pool.map(lambda name: extract(article, output_format=name, with_metadata=True), formats, timeout=120)
        )
    assert all(output for output in outputs)


def test_fetch_response_loop(server: str, make_config: Callable[..., ConfigParser]) -> None:
    """Repeated downloads against the local server."""
    config = make_config(SSRF_PROTECTION="off")
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: fetch_response(f"{server}/article", config=config), range(20), timeout=120))
    assert all(response is not None and response.status == 200 for response in responses)

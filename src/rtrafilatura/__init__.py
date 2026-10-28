"""rtrafilatura: web page extraction at Rust speed, with trafilatura-compatible syntax.

Declared `__init__` exception (tax-py-naming): the distribution's public surface is the package itself,
`import rtrafilatura as trafilatura; trafilatura.extract(...)`, a drop-in for trafilatura on the
trafilatura-rs engine. This module holds the public re-exports, the library's `NullHandler` hook and the
package metadata dunders, and nothing else (docs/decisions.md).
"""

import logging
from importlib.metadata import version

from rtrafilatura._native import ENGINE_VERSION
from rtrafilatura.baseline import baseline, html2txt
from rtrafilatura.core import bare_extraction, extract, extract_with_metadata
from rtrafilatura.downloads import fetch_response, fetch_url
from rtrafilatura.metadata import extract_metadata
from rtrafilatura.utils import load_html

logging.getLogger(__name__).addHandler(logging.NullHandler())

__title__ = "rtrafilatura"
__author__ = "EDamLabs"
__license__ = "MIT"
__copyright__ = "Copyright 2026 EDamLabs"
__version__ = version("rtrafilatura")

__all__ = [
    "ENGINE_VERSION",
    "bare_extraction",
    "baseline",
    "extract",
    "extract_metadata",
    "extract_with_metadata",
    "fetch_response",
    "fetch_url",
    "html2txt",
    "load_html",
]

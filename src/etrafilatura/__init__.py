"""etrafilatura: web page extraction at Rust speed, with trafilatura-compatible syntax.

Declared `__init__` exception (tax-py-naming): the distribution's public surface is the package itself,
`import etrafilatura as trafilatura; trafilatura.extract(...)`, a drop-in for trafilatura on the
trafilatura-rs engine. This module holds the public re-exports, the library's `NullHandler` hook and the
package metadata dunders, and nothing else (docs/decisions.md).
"""

import logging
from importlib.metadata import version

from etrafilatura._native import ENGINE_VERSION
from etrafilatura.baseline import baseline, html2txt
from etrafilatura.core import bare_extraction, extract, extract_with_metadata
from etrafilatura.downloads import fetch_response, fetch_url
from etrafilatura.metadata import extract_metadata
from etrafilatura.utils import load_html

logging.getLogger(__name__).addHandler(logging.NullHandler())

__title__ = "etrafilatura"
__author__ = "EDamLabs"
__license__ = "MIT"
__copyright__ = "Copyright 2026 EDamLabs"
__version__ = version("etrafilatura")

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

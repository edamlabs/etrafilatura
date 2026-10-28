"""Command-line entry point: extraction from files, URLs or stdin."""

import argparse
import logging
import sys
from configparser import ConfigParser
from pathlib import Path

from rtrafilatura import ENGINE_VERSION, __version__
from rtrafilatura.core import extract
from rtrafilatura.downloads import fetch_url
from rtrafilatura.settings import SUPPORTED_FMT_CLI, use_config


def build_parser() -> argparse.ArgumentParser:
    """The argument parser of the `rtrafilatura` command."""
    parser = argparse.ArgumentParser(
        prog="rtrafilatura",
        description="Extract the main content of web pages, at Rust speed.",
    )
    parser.add_argument("inputs", nargs="*", help="HTML files to process; stdin when omitted")
    parser.add_argument("-u", "--url", default=None, help="fetch and process this URL")
    parser.add_argument("-o", "--output-format", default="txt", choices=SUPPORTED_FMT_CLI)
    parser.add_argument("--fast", action="store_true", help="skip backup extraction")
    parser.add_argument("--precision", action="store_true", help="prefer less text but correct extraction")
    parser.add_argument("--recall", action="store_true", help="prefer more text even when unsure")
    parser.add_argument("--comments", action="store_true", default=True)
    parser.add_argument("--no-comments", dest="comments", action="store_false")
    parser.add_argument("--tables", action="store_true", default=True)
    parser.add_argument("--no-tables", dest="tables", action="store_false")
    parser.add_argument("--images", action="store_true", help="keep images")
    parser.add_argument("--links", action="store_true", help="keep links")
    parser.add_argument("--formatting", action="store_true", help="keep formatting (Markdown in text formats)")
    parser.add_argument("--lang", default=None, help="discard documents in another language (ISO 639-1)")
    parser.add_argument("--deduplicate", action="store_true")
    parser.add_argument("--with-metadata", action="store_true")
    parser.add_argument("--only-with-metadata", action="store_true")
    parser.add_argument("--prune", action="append", default=None, help="XPath expression to prune (repeatable)")
    parser.add_argument("--config", default=None, help="path to a settings.cfg override")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--version", action="version", version=f"rtrafilatura {__version__} (engine {ENGINE_VERSION})")
    return parser


def _main_extract(source: bytes | str, url: str | None, args: argparse.Namespace, config: ConfigParser) -> str | None:
    """One document through `extract` with the command-line options."""
    return extract(
        source,
        url=url,
        fast=args.fast,
        favor_precision=args.precision,
        favor_recall=args.recall,
        include_comments=args.comments,
        output_format=args.output_format,
        target_language=args.lang,
        include_tables=args.tables,
        include_images=args.images,
        include_links=args.links,
        include_formatting=args.formatting or None,
        deduplicate=args.deduplicate,
        with_metadata=args.with_metadata,
        only_with_metadata=args.only_with_metadata,
        prune_xpath=args.prune,
        config=config,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; returns 0 when at least one document produced output."""
    args = build_parser().parse_args(argv)
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    config = use_config(args.config)
    sources: list[tuple[bytes | str, str | None]] = (
        [(b"", args.url)]
        if args.url
        else [(Path(path).read_bytes(), None) for path in args.inputs] or [(sys.stdin.read(), None)]
    )
    ### Lazy: each document is extracted and written before the next one is fetched.
    results = (
        _main_extract(content, url, args, config)
        for source, url in sources
        if (content := fetch_url(url) if url else source) is not None
    )
    written = [sys.stdout.write(result.rstrip() + "\n") for result in results if result]
    return 0 if written else 1

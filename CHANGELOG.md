# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [0.1.0] - 2026-10-22

Initial release: PyO3 binding of trafilatura-rs 0.5.0, 100 % API-compatible with trafilatura 2.3.x.

### Added

- `extract` / `bare_extraction` / `extract_with_metadata`: the trafilatura extraction surface — every keyword
  argument, the same `Extractor` and `Document` classes (lxml `body` / `commentsbody` trees), `settings.cfg`
  compatibility — over the Rust engine, with the GIL released during extraction.
- Output formats `txt`, `markdown`, `xml`, `xmltei`, `json`, `csv`, `html`, rendered by trafilatura's own
  code vendored verbatim (Apache-2.0, `NOTICE.md`): byte-identical XML/TEI/JSON/CSV/Markdown, TEI validated
  against trafilatura's `tei_corpus.dtd`.
- `extract_metadata`, `fetch_url`, `fetch_response`, `load_html` (returns lxml trees), `baseline` and
  `html2txt` (vendored implementation), real XPath `prune_xpath`, vendored `deduplication` (Simhash
  fingerprints identical to trafilatura's).
- Downloads: urllib3 pool with retries, SSRF protection, insecure-SSL fallback, MAX_FILE_SIZE cap — configured
  through the same `settings.cfg` keys as trafilatura.
- Errors: typed tree rooted at `ExtractionError`; extraction failures return None, like trafilatura.
- CLI: `etrafilatura` command for files, URLs and stdin.
- Type stubs (`py.typed`), abi3 wheels (CPython ≥ 3.12), sdist.
- CI (lint, types, arch, Rust gates, tests on Linux, macOS and Windows × Python 3.12/3.14, docs, Pages) and a
  tag-driven release with build provenance attestations.
- Rust line coverage of the binding driven by the Python suite (`cargo llvm-cov`, gate 90 %).
- Self-maintenance: Renovate, version and license sync, upstream API diff, a Qwen agent that repairs or extends
  the binding on dependency updates, and a monthly dependency health check.
- Fidelity harness comparing the binding against Python trafilatura on a reference corpus.

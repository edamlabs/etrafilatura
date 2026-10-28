# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-10-28

### Added

- `rtrafilatura._native.html2txt`: the engine's block-aware text dump, new in trafilatura-rs 0.6.0 and the
  measure its recall escalation compares an extraction against. Private and typed in `_native.pyi`; the public
  `html2txt` stays trafilatura's vendored implementation.
- Docs site: `docs.yml` builds the Zensical site and deploys it to GitHub Pages from `main` behind the
  `DOCS_DEPLOY` gate; live at <https://edamlabs.github.io/rtrafilatura/> (2026-10-27).

### Changed

- Renamed: project and library `etrafilatura` → `rtrafilatura` (crate `rtrafilatura-native`). The `e-` prefix
  carried no signal at the import site; `r` names the engine that does the work.
- Engine: trafilatura-rs 0.6.0 ([release notes](https://github.com/nchapman/trafilatura-rs/releases/tag/v0.6.0)).
- Compatibility: escaped text is no longer a divergence — the engine keeps it from 0.6.0 on, closing the
  upstream report [nchapman/trafilatura-rs#13](https://github.com/nchapman/trafilatura-rs/issues/13).
- README: badge layout, description and identity line standardized on the EDamLabs template.

## [0.1.0] - 2026-10-22

First release: PyO3 binding of trafilatura-rs 0.5.0 with trafilatura 2.3's syntax.

### Added

- `extract`, `bare_extraction`, `extract_with_metadata`, `extract_metadata`: trafilatura's signatures and defaults,
  `Extractor` and `Document` with trafilatura's slots in trafilatura's order, `settings.cfg` with the same keys,
  over the Rust engine with the GIL released.
- Trees in trafilatura's vocabulary (`head rend`, `quote`, `list`/`item`, `ref`, `hi`, `row`/`cell`): the engine's
  HTML goes through trafilatura's vendored `convert_tags`, and trafilatura's rescue, size, tree-size and
  duplicate checks run in Python after the engine.
- Output formats `txt`, `markdown`, `xml`, `xmltei`, `json`, `csv`, `html`, rendered by trafilatura's code vendored
  verbatim (Apache-2.0, `NOTICE.md`): byte-identical on 64 of 84 golden cases of the synthetic corpus, the rest
  declared in the compatibility page.
- `fetch_url`, `fetch_response`, `load_html` (lxml trees), `baseline` and `html2txt` (vendored), XPath
  `prune_xpath`, vendored `deduplication`.
- Downloads: urllib3 pools with retries, SSRF protection, insecure-SSL fallback and size caps, configured through
  trafilatura's `settings.cfg` keys. Compressed input decoded with a streaming output cap: gzip, zstd, brotli and
  deflate as trafilatura, plus bz2, xz and zip.
- Input resolution, an extension: `os.PathLike` inputs are read; keyword-only `input_format="auto"` fetches an
  absolute http(s) URL string (validated by the engine's WHATWG `url` crate) or reads a file path string, capped
  at `MAX_FILE_SIZE`. The default `"html"` keeps trafilatura's behaviour.
- Errors: rejected pages return `None` as in trafilatura; the native layer raises into a typed tree rooted at
  `ExtractionError`.
- CLI: `etrafilatura` for files, URLs and stdin.
- Type stubs (`py.typed`), abi3 wheels for CPython ≥ 3.12, sdist.
- Parity tooling: byte-parity goldens from Python trafilatura (`make parity`) checked by the unit suite with
  strict `xfail` for each declared divergence; `make fidelity` for byte-exact and token agreement per format;
  `make benchmark` against trafilatura; documentation examples run as doctests.
- CI on Linux, macOS and Windows × Python 3.12 and 3.14 (lint, types, import contracts, Rust gates, 100 % Python
  coverage, Rust coverage driven by the Python suite, strict docs build) and a tag-driven release with
  build-provenance attestations.
- Self-maintenance: Renovate (runtime ranges widened, never raised; reference trafilatura in its own PR; tooling
  grouped), changelog and license sync, upstream API diff, an agent that repairs or extends the binding on
  dependency updates within an allowlist, and a monthly dependency health check.

[Unreleased]: https://github.com/edamlabs/rtrafilatura/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/edamlabs/rtrafilatura/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/edamlabs/rtrafilatura/releases/tag/v0.1.0

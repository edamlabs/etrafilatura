# Upstream and versioning

## trafilatura-rs

[trafilatura-rs](https://github.com/nchapman/trafilatura-rs) is a pure-Rust library and CLI by
[nchapman](https://github.com/nchapman) that extracts the main text, comments and metadata of web pages —
a faithful port of [go-trafilatura](https://github.com/markusmobius/go-trafilatura). No Python runtime,
no C bindings, no subprocesses.

This package compiles it into a Python extension with [PyO3](https://pyo3.rs) and [maturin](https://www.maturin.rs),
and adds:

| From trafilatura-rs | Added here |
|---|---|
| The extraction pipeline: content, comments, metadata, fallbacks | The trafilatura-compatible Python API and its module layout |
| Language filtering | trafilatura's renderers (XML, TEI, JSON, CSV, HTML, Markdown), its tree vocabulary, its rescue, size and deduplication checks |
| `Options` / `Config` tuning | `Extractor`, `Document`, `settings.cfg` compatibility |
| Performance | Downloads (urllib3, retries, SSRF guard), URL and file input resolution, CLI, GIL release |

Wrong extraction on a page → [trafilatura-rs issues](https://github.com/nchapman/trafilatura-rs/issues).
Anything about the Python API → [ours](https://github.com/edamlabs/etrafilatura/issues).

## Versions

```python
import etrafilatura

etrafilatura.__version__      # '0.1.0' — this package, its own semver
etrafilatura.ENGINE_VERSION   # '0.5.0' — the trafilatura-rs release compiled in
```

The engine is pinned to an exact release. Every new release is picked up automatically and recorded in the
[changelog](changelog.md) → [Self-maintenance](maintenance.md).

## Other ways to use the engine

| Runtime | Install |
|---|---|
| Rust | `cargo add trafilatura` |
| CLI | `cargo install trafilatura --features cli` |
| Python | `pip install etrafilatura` |

## Licenses

The binding is MIT © EDamLabs; the engine is Apache-2.0. Wheels statically link the engine and its
dependencies, under permissive licenses. All license texts are in
[`THIRD_PARTY_LICENSES.md`](https://github.com/edamlabs/etrafilatura/blob/main/THIRD_PARTY_LICENSES.md),
shipped inside every wheel and regenerated with `make licenses`.

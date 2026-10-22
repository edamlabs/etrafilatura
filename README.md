# etrafilatura

[![PyPI](https://img.shields.io/pypi/v/etrafilatura.svg)](https://pypi.org/project/etrafilatura/)
[![Python](https://img.shields.io/pypi/pyversions/etrafilatura.svg)](https://pypi.org/project/etrafilatura/)
[![Docs](https://img.shields.io/badge/docs-edamlabs.github.io%2Fetrafilatura-1b5e8f)](https://edamlabs.github.io/etrafilatura/)
[![CI](https://github.com/edamlabs/etrafilatura/actions/workflows/ci.yml/badge.svg)](https://github.com/edamlabs/etrafilatura/actions/workflows/ci.yml)
[![Upstream](https://img.shields.io/crates/v/trafilatura.svg?label=trafilatura-rs)](https://crates.io/crates/trafilatura)

**Python binding of [trafilatura-rs](https://github.com/nchapman/trafilatura-rs)** — the pure-Rust engine by
[nchapman](https://github.com/nchapman) that extracts the main text, comments and metadata of web pages,
stripping boilerplate. 100 % API-compatible with [trafilatura](https://github.com/adbar/trafilatura): same
signatures, same lxml trees, same output bytes (its renderers are vendored verbatim) — on a compiled engine,
with three dependencies instead of seven. GIL released.

📖 **Documentation: <https://edamlabs.github.io/etrafilatura/>**

```bash
pip install etrafilatura       # or: uv add etrafilatura
```

```python
import etrafilatura as trafilatura   # drop-in syntax

downloaded = trafilatura.fetch_url("https://example.org/article")
trafilatura.extract(downloaded, output_format="markdown", with_metadata=True)

trafilatura.extract(html_string)                       # 'txt' by default
trafilatura.bare_extraction(html_string)               # Document with .text, .body, .comments…
trafilatura.extract_metadata(html_string)              # title, author, date, sitename…
```

**Extraction agreement** — the share of reference articles each output format recovers identically to what the
engine extracts natively ([method](https://edamlabs.github.io/etrafilatura/outputs/#fidelity)).

| | |
|---|---|
| [Outputs](https://edamlabs.github.io/etrafilatura/outputs/) | Every output format, and what each carries |
| [API](https://edamlabs.github.io/etrafilatura/api/) | `extract`, `bare_extraction`, `fetch_url`, `extract_metadata`, … |
| [Errors](https://edamlabs.github.io/etrafilatura/errors/) | What can fail, and how to catch it |
| [Compatibility](https://edamlabs.github.io/etrafilatura/compatibility/) | Drop-in map from trafilatura, and the known gaps |
| [Self-maintenance](https://edamlabs.github.io/etrafilatura/maintenance/) | How the binding follows trafilatura-rs on its own |

Extraction quality, heuristics and performance belong to
[trafilatura-rs](https://github.com/nchapman/trafilatura-rs): extraction issues go
[upstream](https://github.com/nchapman/trafilatura-rs/issues), Python API issues [here](https://github.com/edamlabs/etrafilatura/issues).

MIT, binding © EDamLabs; the engine is Apache-2.0. Wheels statically link the engine and its dependencies;
their licenses ship in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

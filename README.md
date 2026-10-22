# etrafilatura

[![PyPI](https://img.shields.io/pypi/v/etrafilatura.svg)](https://pypi.org/project/etrafilatura/)
[![Python](https://img.shields.io/pypi/pyversions/etrafilatura.svg)](https://pypi.org/project/etrafilatura/)
[![Docs](https://img.shields.io/badge/docs-edamlabs.github.io%2Fetrafilatura-1b5e8f)](https://edamlabs.github.io/etrafilatura/)
[![CI](https://github.com/edamlabs/etrafilatura/actions/workflows/ci.yml/badge.svg)](https://github.com/edamlabs/etrafilatura/actions/workflows/ci.yml)
[![Upstream](https://img.shields.io/crates/v/trafilatura.svg?label=trafilatura-rs)](https://crates.io/crates/trafilatura)

**Python binding of [trafilatura-rs](https://github.com/nchapman/trafilatura-rs)** — the pure-Rust engine by
[nchapman](https://github.com/nchapman) that extracts the main text, comments and metadata of web pages,
stripping boilerplate, with [trafilatura](https://github.com/adbar/trafilatura)'s syntax: same signatures, same
lxml trees in trafilatura's vocabulary, trafilatura's own renderers — on a compiled engine, with three
dependencies instead of seven and the GIL released.

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

trafilatura.extract("https://example.org/article", input_format="auto")   # extension: fetch, then extract
```

**Benchmark** — pytest-benchmark medians against Python trafilatura 2.3.1: on the two real pages (PEP 8,
Wikipedia), 1.2–1.5× faster plain-text extraction, 1.6–2.1× with XML and metadata, 2.7–4.4× on metadata alone.
On small synthetic pages, under a millisecond, the Python-side tree conversion weighs more: 0.6–2.9×.
`html2txt` and `baseline` run the same vendored code on both sides and measure the noise: 0.9–1.2×
([full matrix and method](https://edamlabs.github.io/etrafilatura/benchmark/)).

![etrafilatura vs trafilatura](https://raw.githubusercontent.com/edamlabs/etrafilatura/main/docs/assets/benchmark.svg)

**Agreement with trafilatura** — on the synthetic test pages, 64 of 84 format cases are byte-identical and the
other 20 are declared differences (tags, TEI version). On the eight-page corpus, real pages included, word-token
agreement is 99.5 % (txt) and 99.6 % (markdown); the real pages differ by the engine's content selection
([method](https://edamlabs.github.io/etrafilatura/outputs/#fidelity), [map](https://edamlabs.github.io/etrafilatura/compatibility/)).

| | |
|---|---|
| [Outputs](https://edamlabs.github.io/etrafilatura/outputs/) | Every output format, and what each carries |
| [Benchmark](https://edamlabs.github.io/etrafilatura/benchmark/) | Timings against Python trafilatura, per method and document |
| [API](https://edamlabs.github.io/etrafilatura/api/) | `extract`, `bare_extraction`, `fetch_url`, `extract_metadata`, … |
| [Errors](https://edamlabs.github.io/etrafilatura/errors/) | What can fail, and how to catch it |
| [Compatibility](https://edamlabs.github.io/etrafilatura/compatibility/) | Drop-in map from trafilatura, and the known gaps |
| [Self-maintenance](https://edamlabs.github.io/etrafilatura/maintenance/) | How the binding follows trafilatura-rs on its own |

Extraction quality, heuristics and performance belong to
[trafilatura-rs](https://github.com/nchapman/trafilatura-rs): extraction issues go
[upstream](https://github.com/nchapman/trafilatura-rs/issues), Python API issues [here](https://github.com/edamlabs/etrafilatura/issues).

MIT, binding © EDamLabs; the engine is Apache-2.0. Wheels statically link the engine and its dependencies;
their licenses ship in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

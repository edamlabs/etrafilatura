<p align="center">
  <a href="https://github.com/edamlabs/rtrafilatura/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/edamlabs/rtrafilatura/ci.yml?label=test" alt="CI"></a>
  <a href="https://pypi.org/project/rtrafilatura/"><img src="https://img.shields.io/pypi/v/rtrafilatura?color=166b7e" alt="PyPI"></a>
  <a href="https://pypi.org/project/rtrafilatura/"><img src="https://img.shields.io/pypi/pyversions/rtrafilatura" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/pypi/l/rtrafilatura?color=166b7e" alt="License"></a>
</p>

Python binding of trafilatura-rs: web page main text, comments and metadata extraction at Rust speed, trafilatura-compatible syntax.

An **EDamLabs binding**: a Python binding of a third-party engine that keeps its upstream's syntax and follows its releases ([EDamLabs families](https://github.com/edamlabs/esteward#identity)).

## Install

```bash
pip install rtrafilatura       # or: uv add rtrafilatura
```

## Usage

```python
import rtrafilatura as trafilatura   # drop-in syntax

downloaded = trafilatura.fetch_url("https://example.org/article")
trafilatura.extract(downloaded, output_format="markdown", with_metadata=True)

trafilatura.extract(html_string)                       # 'txt' by default
trafilatura.bare_extraction(html_string)               # Document with .text, .body, .comments…
trafilatura.extract_metadata(html_string)              # title, author, date, sitename…

trafilatura.extract("https://example.org/article", input_format="auto")   # extension: fetch, then extract
```

## Benchmark

**Benchmark** — pytest-benchmark medians against Python trafilatura 2.3.1: on the two real pages (PEP 8, Wikipedia), 1.2–1.5× faster plain-text extraction, 1.6–2.1× with XML and metadata, 2.7–4.4× on metadata alone. Extraction on small synthetic pages, under a millisecond, weighs the Python-side tree conversion more: 0.6–2.9×. `html2txt` and `baseline` run the same vendored code on both sides and measure the noise: 0.9–1.2× ([full matrix and method](https://edamlabs.github.io/rtrafilatura/benchmark/)).

![rtrafilatura vs trafilatura](https://raw.githubusercontent.com/edamlabs/rtrafilatura/main/docs/assets/benchmark.svg)

## Agreement with trafilatura

**Agreement with trafilatura** — on the synthetic test pages, 64 of 84 format cases are byte-identical and the other 20 are declared differences (tags, TEI version). On the eight-page corpus, real pages included, word-token agreement is 99.5 % (txt) and 99.6 % (markdown); the real pages differ by the engine's content selection ([method](https://edamlabs.github.io/rtrafilatura/outputs/#fidelity), [map](https://edamlabs.github.io/rtrafilatura/compatibility/)).

| | |
| --- | --- |
| [Outputs](https://edamlabs.github.io/rtrafilatura/outputs/) | Every output format, and what each carries |
| [Benchmark](https://edamlabs.github.io/rtrafilatura/benchmark/) | Timings against Python trafilatura, per method and document |
| [API](https://edamlabs.github.io/rtrafilatura/api/) | `extract`, `bare_extraction`, `fetch_url`, `extract_metadata`, … |
| [Errors](https://edamlabs.github.io/rtrafilatura/errors/) | What can fail, and how to catch it |
| [Compatibility](https://edamlabs.github.io/rtrafilatura/compatibility/) | Drop-in map from trafilatura, and the known gaps |
| [Self-maintenance](https://edamlabs.github.io/rtrafilatura/maintenance/) | How the binding follows trafilatura-rs on its own |

Extraction quality, heuristics and performance belong to [trafilatura-rs](https://github.com/nchapman/trafilatura-rs): extraction issues go [upstream](https://github.com/nchapman/trafilatura-rs/issues), Python API issues [here](https://github.com/edamlabs/rtrafilatura/issues).

## License

MIT, binding © EDamLabs; the engine is Apache-2.0. Wheels statically link the engine and its dependencies; their licenses ship in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

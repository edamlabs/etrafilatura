# Development

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (the whole toolchain runs through it)
- A Rust toolchain (`rustup`) — the extension compiles with maturin

```bash
git clone https://github.com/edamlabs/etrafilatura && cd etrafilatura
uv sync            # dev groups: lint, test, bench, build, docs
make build         # compile the extension into the venv (debug)
make test          # unit suite, 100 % coverage gate
uv run prek install
```

## Layout

```
crates/native/src/lib.rs     the PyO3 bridge: functions, result classes, error mapping
src/etrafilatura/            the trafilatura-compatible Python surface
  settings.py                use_config, Extractor, Document, settings.cfg keys
  core.py                    extract, bare_extraction, extract_with_metadata, renderers dispatch
  engine.py                  NativeEngine: the engine call and the HTML → trafilatura-vocabulary conversion
  source.py                  input_format: URL and file input resolution
  metadata.py downloads.py cli.py errors.py utils.py
  xml.py baseline.py htmlprocessing.py deduplication.py   vendored verbatim from trafilatura (NOTICE.md)
  data/tei_corpus.dtd        the TEI DTD, from trafilatura
tests/unit/etrafilatura/     mirror of src; tests/resources/html feeds units and the fidelity corpus
tests/resources/parity/      byte-parity goldens produced by Python trafilatura (make parity)
tools/                       coverage.sh, apidiff.sh, fidelity.py, parity.py, benchchart.py
```

The vendored modules are frozen upstream code: excluded from ruff/ty/coverage gates, exercised through the
suite, and re-synced from trafilatura releases rather than edited.

## Make targets

| Target | Does |
|---|---|
| `make check` | lint + types + arch + build + test (the full local gate) |
| `make suite` | everything including stress and integration, one coverage gate |
| `make cov` | Rust line coverage driven by the Python suite (gate 90 %) |
| `make fidelity` | extraction agreement vs Python trafilatura (`ARGS=--update` rewrites the baseline) |
| `make parity` | rewrite the byte-parity goldens from Python trafilatura |
| `make benchmark` | pytest-benchmark vs Python trafilatura; regenerates `docs/benchmark.md` and its chart |
| `make licenses` | regenerate `THIRD_PARTY_LICENSES.md` from the Rust dependency tree |
| `make apidiff OLD=x NEW=y` | engine public API diff between two crate versions |
| `make dist` / `make publish` | release wheels + sdist / PyPI upload |
| `make docs` / `make serve` | strict docs build / local server |

## Conventions

- Python: ruff (a wide rule set, `ban-relative-imports = "all"`), ty with `error-on-warning`, tach import
  contracts (`tach.toml`), 100 % branch coverage, no comments except a single `### reason` line where logic
  needs it, dispatch mappings instead of `if/elif` chains.
- Rust: rustfmt, clippy with `-D warnings`, no `unsafe`, no `unwrap()`/`expect()` outside build.rs, GIL
  released around every engine call.
- prek (`prek.toml`) is the single source of truth for hooks; CI runs `prek run --all-files` — the same gate
  as a local commit.

## Testing

```bash
make test          # units (default: stress and integration deselected)
make stress        # concurrency and volume
make integration   # live network calls
```

Fixtures are plain files under `tests/resources/`; the download tests run against a local HTTP server, so the
unit suite needs no network. The code examples in `docs/*.md` run as doctests in the same suite. The `bench`
group installs Python trafilatura for `make fidelity`, `make parity` and `make benchmark`.

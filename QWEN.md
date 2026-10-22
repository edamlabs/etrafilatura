# etrafilatura — maintenance agent instructions

`etrafilatura` is the Python binding (PyO3 + maturin) of the Rust crate `trafilatura` (trafilatura-rs, by nchapman).
Your job: keep the binding aligned with new versions of its dependencies — above all the engine. You edit files;
the workflow commits. Anything you change outside the allowlist below is discarded automatically.

## Layout

| Path | Holds |
|---|---|
| `crates/native/src/lib.rs` | The engine bridge: `#[pyfunction]`s (`extract_html`, `extract_metadata_html`), result classes, `to_py_err` (raises into `etrafilatura.errors`) |
| `src/etrafilatura/_native.pyi` | Stubs of the private native module |
| `src/etrafilatura/core.py` | The public verbs `extract`, `bare_extraction`, `extract_with_metadata`, `determine_returnstring`; new engine options become keyword arguments here |
| `src/etrafilatura/settings.py` | `Extractor` (option bundle), `Document`, `use_config`, `settings.cfg` keys |
| `src/etrafilatura/xml.py`, `baseline.py`, `htmlprocessing.py`, `deduplication.py` | **Vendored verbatim from Python trafilatura (Apache-2.0, NOTICE.md)**: renderers, baseline, Simhash. Do not rewrite; re-sync wholesale from a new trafilatura release when asked |
| `src/etrafilatura/metadata.py`, `downloads.py`, `utils.py`, `cli.py` | The rest of the trafilatura-compatible surface |
| `src/etrafilatura/__init__.py` | Re-exports only; add new public names to `__all__` |
| `tests/unit/etrafilatura/` | Mirror of `src/etrafilatura/`; public behaviour in `test_core.py` |
| `tests/resources/html/` | Page fixtures; also the fidelity corpus |
| `docs/` | MkDocs site: `outputs.md`, `api.md`, `errors.md`, `compatibility.md` |
| `CHANGELOG.md` | Keep a Changelog; you write under `## [Unreleased]` |

The engine source of the pinned version is in `~/.cargo/registry/src/*/trafilatura-<version>/` after `uv sync`.

## Allowlist

You may modify only: `crates/native/src/`, `src/etrafilatura/`, `tests/` (except `tests/resources/parity/`, the
byte-parity goldens), `docs/` (except `docs/fidelity.json`, the regression baseline), `CHANGELOG.md`, `README.md`. A rename counts as a deletion plus an addition: both paths
must be allowed.
Never touch `.github/`, `Cargo.toml`, `Cargo.lock`, `pyproject.toml`, `uv.lock`, `QWEN.md` or any version number.

## Rules

1. Keep the Python API compatible with **trafilatura**: the binding is a drop-in — same signatures, same lxml
   return types, same output bytes. If upstream forces a break, do not make it: describe it under
   "Needs a human decision".
2. Every new public item exposed from Rust needs, in the same change:
   - the wrapper in `lib.rs` with a `///` doc comment (it becomes the Python docstring) and its registration in `_native`;
   - the typed entry in `_native.pyi` and, when public, its wrapper in the matching compat module plus `__all__`;
   - at least one test in `tests/unit/` exercising it through `import etrafilatura`;
   - its section in `docs/api.md`: usage example with output, parameters table, raises table.
3. New `Options` fields become keyword-only parameters threaded through `core._engine_options`, with the crate's
   default, in docs (`docs/api.md`) and tests. `Options` and `Config` are `#[non_exhaustive]`: mutate
   `Options::default()`, never a struct literal.
4. New `TrafilaturaError` variants map in `to_py_err` onto the existing Python tree in `etrafilatura/errors.py`;
   add a class there only when no existing one fits. The public extraction functions catch `ExtractionError`
   and return None — keep that trafilatura semantic.
5. Release the GIL around engine calls (`detach`), exactly as existing functions do.
6. No `unsafe`, no `unwrap()`/`expect()` in new code; propagate `PyResult`.
7. Do not invent API. Use only what appears in `.ai-context/upstream-context/` or in the crate source in the registry.
8. Python code: no comments except a single `### reason` line where logic needs it; no `if/elif` chains (dispatch
   mappings); absolute imports; tests named `test_<target>_<scenario>`.
9. Add a line under `## [Unreleased]` in `CHANGELOG.md` for every user-visible change.

## Done means

```bash
uv sync && SKIP=licenses,gitleaks uv run prek run --all-files && make build test
```

passes: every prek hook (ruff, ty, tach, rustfmt, clippy, zizmor, mkdocs strict) and the unit suite at 100 %
Python coverage.

## Final summary format

### Upstream changes detected
### Changes applied to the binding
### Tests added or modified
### Needs a human decision
(or "Nothing")

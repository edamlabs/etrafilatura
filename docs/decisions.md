# Decisions

Architectural decisions and the house-style exceptions the drop-in contract imposes. One entry per decision:
date, decision, evidence, rejected alternatives. The contract that justifies most of them: `import etrafilatura
as trafilatura` must keep working byte for byte, so trafilatura's public shape wins over the house style
wherever the two meet.

## House-style exceptions

### 2026-10-22 · `__init__.py` holds the public surface

**Decision.** `src/etrafilatura/__init__.py` exists and holds the re-exports of the public names, the library's
`logging.NullHandler` hook and the package metadata dunders (`__title__`, `__author__`, `__license__`,
`__copyright__`, `__version__`), nothing else.

**Evidence.** trafilatura's users call `trafilatura.extract(...)` on the package: without the re-exports the
drop-in breaks at the first attribute. The `NullHandler` is the stdlib-recommended hook for libraries.
`test_package.py` pins the surface.

**Rejected.** A namespace package with users importing `etrafilatura.core`: it breaks every trafilatura call site.

### 2026-10-22 · Positional booleans in public signatures

**Decision.** `extract`, `bare_extraction`, `extract_with_metadata`, `fetch_url`, `baseline`, `extract_metadata`
keep trafilatura's positional `bool` parameters, in trafilatura's order; ruff `FBT001/FBT002/FBT003` are ignored
per file (`pyproject.toml`).

**Evidence.** trafilatura call sites pass them positionally; reordering or making them keyword-only raises
`TypeError` in user code. `extract` forwards `**locals()`, so a signature drift fails the suite.

**Rejected.** Keyword-only booleans: house style, but a breaking change for every positional caller.

### 2026-10-22 · Vendored modules stay verbatim

**Decision.** `xml.py`, `baseline.py`, `htmlprocessing.py` (subset), `deduplication.py` and the bodies listed in
`NOTICE.md` (in `settings.py`, `utils.py`, `core.py`) are trafilatura 2.3.1 / courlan 1.4.0 code, re-synced from
upstream releases and never restyled: names, loops, `if` chains, comments and mutable constants included. The
four whole modules are excluded from ruff, ty and coverage.

**Evidence.** Byte-identical output is the contract: `test_extract_parity` compares against Python trafilatura's
goldens. A local rewrite turns every upstream re-sync into a manual merge.

**Rejected.** Restyling the vendored code to the house rules: each upstream release would need a re-port, and any
slip shows up as a parity diff.

### 2026-10-22 · trafilatura's class and function names

**Decision.** `Extractor`, `Document`, `LRUCache`, `Simhash`, `Response` and every public function keep
trafilatura's names, without the module surname the house naming law requires.

**Evidence.** `isinstance(doc, Document)`, `Extractor(...)` and `from trafilatura.settings import Extractor`
appear in user code; the names are part of the API.

**Rejected.** `SettingsExtractor`, `SettingsDocument`: lawful, and a rename of the public API.

### 2026-10-22 · Upstream private helper names

**Decision.** Private helpers mirrored from trafilatura (`_determine_headers`, `_get_retry_strategy`,
`_initiate_pool`, `_send_request`, `_is_suitable_response`, `_check_deprecation`, `_internal_extraction`) keep the
upstream names instead of the `_<public>_<what>` genealogy.

**Evidence.** Tests and monkeypatches written against trafilatura target these names; one name per concept across
the two projects keeps diffs against upstream readable.

**Rejected.** House genealogy names: no behavioural gain, a permanent translation table against upstream.

### 2026-10-22 · Stdlib `logging`, not structlog

**Decision.** Modules log through `logging.getLogger(__name__)` with %-style arguments.

**Evidence.** trafilatura logs through stdlib `logging`; its users configure handlers and levels on
`trafilatura.*` loggers. A library must not impose a logging framework on its host application.

**Rejected.** structlog: a new runtime dependency and a different configuration surface for every user.

### 2026-10-22 · `ConfigParser`, not pydantic-settings

**Decision.** Configuration is a `configparser.ConfigParser` read from `settings.cfg`, passed as `config=` or
`settingsfile=`; public signatures type it `ConfigParser`.

**Evidence.** trafilatura's contract: `use_config()`, `settings.cfg` keys, `config.getint("DEFAULT", ...)` in user
code.

**Rejected.** pydantic-settings: validated, and incompatible with every existing `settings.cfg` and `config=`
caller.

### 2026-10-22 · Synchronous API

**Decision.** The public API is synchronous; the GIL is released inside the engine call so threads scale.

**Evidence.** trafilatura's API is synchronous. The extraction is CPU-bound Rust: `tests/stress` runs it from
eight threads concurrently with identical results.

**Rejected.** An async API: a second surface trafilatura does not have, and async buys nothing for CPU-bound work.

### 2026-10-22 · Tests stay synchronous

**Decision.** Test functions are plain `def test_*`.

**Evidence.** The code under test is synchronous; an `async def` test would only wrap sync calls in a loop.

**Rejected.** `async def` tests with pytest-asyncio: ceremony with no awaited I/O.

### 2026-10-22 · No beartype on the public surface

**Decision.** Public functions are statically typed (ty) but not runtime-checked.

**Evidence.** trafilatura accepts loosely typed inputs (`str | bytes | HtmlElement | Response`, duck-typed
responses with `.data`) and raises its own errors (`TypeError` in `load_html`) or returns `None`. A runtime
checker would raise where trafilatura returns `None`, and it costs on the hot path.

**Rejected.** `@beartype` on the public functions: a different error contract from trafilatura's.

### 2026-10-22 · `_native` and PyO3 class names

**Decision.** The compiled module is `etrafilatura._native`, its classes `ExtractionResult`/`MetadataResult` as
declared by PyO3 in `crates/native`.

**Evidence.** maturin's `module-name = "etrafilatura._native"`; the underscore marks the private extension behind
the Python façade, the convention of PyO3 projects. The names are fixed in Rust and mirrored in `_native.pyi`.

**Rejected.** A public `etrafilatura.native`: it would invite users to bypass trafilatura's surface.

### 2026-10-22 · `settings` ↔ `deduplication` import under `TYPE_CHECKING`

**Decision.** `settings.py` imports `LRUCache` from `deduplication` only under `if TYPE_CHECKING:`.

**Evidence.** It mirrors upstream: `deduplication` imports `settings` at runtime, `settings` needs the type for
`Extractor.dedup`. `tach` forbids the runtime cycle.

**Rejected.** Moving `LRUCache` into `settings`: diverges from the vendored module layout.

## Architecture

### 2026-10-22 · Engine HTML → trafilatura XML through the vendored `convert_tags`

**Decision.** The engine's HTML result (`h1`, `blockquote`, `ul/li`, `a`, `b`, `td`) is converted to
trafilatura's XML vocabulary (`head rend`, `quote`, `list/item`, `ref`, `hi`, `row/cell`) by trafilatura's own
`convert_tags` before the vendored renderers run (`engine.py`).

**Evidence.** Headings, line breaks and TEI validity match trafilatura; the parity goldens pass for every
non-declared case.

**Rejected.** Rendering the engine's HTML directly (output diverges from trafilatura); a hand-written converter
(re-implements code upstream already has).

### 2026-10-22 · Rescue, size and duplicate checks run in Python

**Decision.** The engine's own rescue, size, tree-size and duplicate gates are neutralised (`NEUTRAL_OPTIONS` in
`engine.py`); `bare_extraction` applies trafilatura's checks on the converted tree.

**Evidence.** trafilatura-rs 0.5.0 bugs, reported upstream as
[nchapman/trafilatura-rs#13](https://github.com/nchapman/trafilatura-rs/issues/13): the baseline fallback appends
instead of replacing, an empty body returns the `<title>`, escaped `&lt;b …&gt;` text becomes markup. With the
checks in Python an empty `<body>` returns `None` and a short page no longer repeats its text.

**Rejected.** Trusting the engine gates until upstream fixes them: wrong output today.

### 2026-10-22 · Declared parity divergences

**Decision.** Two divergences from Python trafilatura are strict `xfail`s in `test_extract_parity`: `tags` (the
engine reads JSON-LD keywords and splits meta keywords on commas) and the TEI `<application>` version (it names
etrafilatura's version, not trafilatura's).

**Evidence.** 20 strict xfails over the goldens; a fix on either side turns them into failures that force the
divergence list to be updated.

**Rejected.** Post-processing tags in Python to imitate trafilatura (guesses the engine's internals); writing
trafilatura's version into TEI (misreports the producing software).

### 2026-10-22 · Opt-in `input_format`, URL validation in Rust

**Decision.** A `str` is HTML by default, as in trafilatura; keyword-only `input_format="auto"` fetches an absolute
http(s) URL or reads a file path. URLs are validated by the engine's WHATWG `url` crate (`_native.absolute_url`).

**Evidence.** Guessing on the default path would fetch or read on behalf of callers that pass untrusted HTML; the
engine already links the `url` crate, so validation costs no dependency. `test_source.py` covers both modes.

**Rejected.** `furl`: pure Python, and a new dependency for what the compiled engine already does.

### 2026-10-22 · Organisation-level `SM_*` secrets

**Decision.** The maintenance agent's provider is configured by `SM_API_KEY` (secret), `SM_BASE_URL` and
`SM_MODEL` (variables) at organisation level (`docs/maintenance.md`).

**Evidence.** One provider serves every repository of the organisation; nothing is stored in the repository and a
rotation happens in one place.

**Rejected.** Repository-level secrets: one copy per repository to rotate.

### 2026-10-22 · Documentation built with Zensical

**Decision.** The site builds with [Zensical](https://zensical.org) (`zensical build --strict --clean`) in place
of MkDocs + Material for MkDocs. `mkdocs.yml` stays the configuration: Zensical reads it natively and its migration
guide recommends keeping it. Default `modern` variant. New EDamLabs projects start on Zensical.

**Evidence.** Material for MkDocs is in maintenance mode, with critical and security fixes until 2026-11-05;
MkDocs 2.0 removes the plugin system and the theme overrides, with no migration path. The existing `mkdocs.yml`
built unchanged with Zensical 0.0.71 ("No issues found"); the pages were compared side by side, and the doctested
examples are unaffected (they run in pytest, not in the site build).

**Rejected.** Pinning `mkdocs<2` with Material 9.7 (frozen on a framework out of maintenance in two weeks);
converting to `zensical.toml` now (no gain while `mkdocs.yml` is read; it can follow when Zensical stabilises).

### 2026-10-26 · Routine updates merge themselves; health moves to esteward

**Decision.** Renovate merges, through GitHub auto-merge after every required check, Python tooling, GitHub
actions, lock file maintenance, the agent's CLI pin and runtime patch releases. The engine, `pyo3`/`url` and the
reference trafilatura never merge themselves. `health.yml` and `tools/health.py` are removed: esteward's `deps`
module covers them daily, with PEP 792 status, license changes and OSV advisories on top.

**Evidence.** PRs #15 (Qwen CLI) and #16 (tooling) sat green waiting for a human; esteward has run
etrafilatura daily since 2026-10-22 with one self-maintained status issue (#13).

**Rejected.** Merging from esteward itself (Renovate already merges on the platform's own gate — the cheapest
plane); keeping `health.yml` beside esteward (two reports of the same facts).

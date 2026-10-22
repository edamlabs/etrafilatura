# Compatibility with trafilatura

`import etrafilatura as trafilatura` and most call sites keep working. This page is the honest map: what is
identical, what is adapted, what is not here.

## Identical

| Surface | Status |
|---|---|
| `extract`, `bare_extraction`, `extract_with_metadata`, `extract_metadata`, `fetch_url`, `fetch_response`, `load_html`, `baseline`, `html2txt` | Same names, same parameter lists, same defaults, same `None`-on-rejection semantics |
| `settings.use_config`, `settings.Extractor`, `settings.Document`, `settings.DEFAULT_CONFIG` | Same interface; `settings.cfg` reads trafilatura's file unchanged (same keys) |
| Output formats `txt`, `markdown`, `yaml`, `xml`, `json`, `csv`, `html` | Same shapes; XML `<doc>` carries the same metadata attributes |
| `deduplication.LRUCache`, `content_fingerprint` | Same interface |
| Deprecation warnings (`no_fallback`, `as_dict`) and `max_tree_size` rejection | Same messages, same `stacklevel` semantics |

## Adapted

| Surface | Difference |
|---|---|
| `load_html` | Returns a normalized HTML **string**, not an lxml tree — the Rust engine parses internally. Accepts str, bytes, `Path`, `Response`. |
| `Document.body` / `.commentsbody` | Cleaned HTML strings instead of lxml elements. `as_dict()` therefore serializes fully to JSON. |
| `prune_xpath` | Takes **CSS selectors** (str or list, joined as a union). XPath expressions are not translated. |
| `baseline()` | Returns `(Document, text, length)`; the extraction runs the engine's recall pipeline instead of lxml heuristics. |
| `xmltei` | A minimal well-formed TEI document (titleStmt, sourceDesc, profileDesc, body paragraphs, comments in `<back>`); `tei_validation` checks well-formedness, not the TEI schema. |
| Date extraction | The engine's meta + JSON-LD date search (`extensive_search` maps to its date mode); no htmldate body-text sweep. |
| Language detection | `whatlang` in the engine instead of langdetect/pycld2/htpy; `target_language` rejection works the same. |
| `fetch_response` | urllib3 only (no pycurl path); `with_headers` kept and ignored, as in trafilatura. |
| Compression in `load_html` | gzip, bzip2, xz and single-member ZIP; no brotli/zstd. |

## Not here (yet)

| Surface | Note |
|---|---|
| `trafilatura.feeds`, `trafilatura.sitemaps`, `trafilatura.spider` | Discovery and crawling are out of scope for the binding |
| `trafilatura.cli` parity | The `etrafilatura` command covers extraction from files, URLs and stdin — not feed/crawl modes |
| `htmldate`-level date heuristics | See "Date extraction" above |
| `external.py` (justext/readability rescue knobs) | The engine runs its own readability + baseline fallbacks internally (`fast` disables them) |

## Engines

trafilatura (Python) and trafilatura-rs are independent implementations of the same pipeline — trafilatura-rs
ports [go-trafilatura](https://github.com/markusmobius/go-trafilatura), which ports trafilatura's algorithms.
Extraction results agree on the large majority of pages and differ on edge cases; `make fidelity` measures the
agreement continuously → [Outputs](outputs.md#fidelity).

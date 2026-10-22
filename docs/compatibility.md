# Compatibility with trafilatura

`import etrafilatura as trafilatura` and your call sites keep working — same signatures, same
return **types**, same output bytes, same configuration keys. This page is the honest map of what is
identical and what still differs inside the engine.

## Identical

| Surface | Status |
|---|---|
| `extract`, `bare_extraction`, `extract_with_metadata`, `extract_metadata`, `fetch_url`, `fetch_response`, `load_html`, `baseline`, `html2txt` | Same names, parameter lists, defaults and `None`-on-rejection semantics |
| `load_html` | Returns an **lxml `HtmlElement`** (or None), accepts tree/str/bytes/Response/HTTPResponse, raises `TypeError` on anything else — like trafilatura |
| `Document.body` / `.commentsbody` | **lxml elements**, rooted at `<body>`; `Document()`, `as_dict()`, `from_dict()`, `clean_and_trim()` identical |
| `prune_xpath` | Real **XPath** expressions (str or list), pruned with lxml before extraction |
| Output formats `txt`, `markdown`, `xml`, `xmltei`, `json`, `csv`, `html` | Produced by trafilatura's own renderers, vendored verbatim: byte-identical `<doc>` XML, TEI (DTD-validated with trafilatura's `tei_corpus.dtd`), JSON, CSV, Markdown |
| `xmltotxt`, `control_xml_output`, `build_json_output`, `xmltocsv`, `build_tei_output`, `validate_tei`, `delete_element`, `meta_items`… | The trafilatura `xml` module, vendored |
| `baseline()` | Returns `(lxml Element, text, length)`; the vendored trafilatura implementation (JSON-LD, Discourse, article, paragraph strategies) |
| `deduplication` | Vendored module: `Simhash`, `content_fingerprint` (same hex values as trafilatura), `LRUCache`, `duplicate_test(element, options)` |
| `settings.use_config`, `Extractor`, `DEFAULT_CONFIG`, `settings.cfg` | Same keys, same validation, same derived flags; `SUPPORTED_FORMATS` identical |
| Deprecation warnings (`no_fallback`, `as_dict`) and `max_tree_size` rejection | Same messages and stacklevels |
| `fetch_response` | urllib3 pools, retries, `INSECURE_SSL_FALLBACK`, SSRF guard, `MAX_FILE_SIZE` cap |

## Engine-internal differences (same contract, different implementation)

| Area | trafilatura | etrafilatura |
|---|---|---|
| Extraction pipeline | Python + lxml heuristics | Rust ([trafilatura-rs](https://github.com/nchapman/trafilatura-rs), port of go-trafilatura), GIL released |
| Date extraction | htmldate (meta, JSON-LD, body sweep) | Engine's meta + JSON-LD search (`extensive_search` maps to its date mode) |
| Language detection | langdetect / pycld2 / py3langid | whatlang (in the engine); `target_language` rejection behaves the same |
| Fallbacks | readability-lxml + justext rescue | Engine's libreadability + baseline fallbacks (`fast=True` disables them) |
| Compression in inputs | gz/bz2/xz/zip/brotli/zstd | gz/bz2/xz/zip (no brotli/zstd) |
| Downloads | urllib3 **or** pycurl | urllib3 only (`with_headers` kept and ignored, as in trafilatura) |

Extraction results agree on the large majority of pages and can differ on edge cases — the engines
are independent implementations. `make fidelity` measures the agreement continuously →
[Outputs](outputs.md#fidelity).

## Extensions

Additive only: every trafilatura call keeps its signature, defaults and result.

| Surface | Extension |
|---|---|
| `extract`, `bare_extraction`, `extract_with_metadata`, `extract_metadata` | `os.PathLike` inputs are read; keyword-only `input_format="auto"` fetches URL strings and reads path strings ([Input resolution](api.md#input-resolution)) |

## Not here

| Surface | Note |
|---|---|
| `trafilatura.feeds`, `trafilatura.sitemaps`, `trafilatura.spider` | Discovery and crawling are out of scope for the binding |
| `trafilatura.cli` parity | The `etrafilatura` command covers extraction from files, URLs and stdin — not feed/crawl modes |
| `output_format="yaml"` | Not a trafilatura 2.3 format either: rejected with the same `AttributeError` |

## Vendored code

The renderers, the deduplication module, `baseline`/`html2txt` and the tree helpers are copied from
trafilatura 2.3.1 (Apache-2.0) — see [`NOTICE.md`](https://github.com/edamlabs/etrafilatura/blob/main/NOTICE.md).
They are re-synced from upstream releases; that is what makes the output formats identical rather
than equivalent.

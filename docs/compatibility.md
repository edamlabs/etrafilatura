# Compatibility with trafilatura

`import etrafilatura as trafilatura` keeps your call sites working: the public signatures are trafilatura's, the
trees are in trafilatura's vocabulary, the renderers are trafilatura's code. Extraction itself runs in another
engine, so content can differ page by page. This page says where, measured against trafilatura 2.3.1.

## Measured

| Check | Result | How |
|---|---|---|
| Signatures of the 9 top-level calls | Identical names, order, kinds and defaults; etrafilatura only appends keyword-only arguments | `inspect.signature` |
| Byte-identical output, 6 synthetic pages × 7 formats × metadata on/off | 64 of 84 cases; the other 20 are the declared divergences below | `test_extract_parity` against goldens from `make parity` |
| Token agreement on the full corpus (8 pages, two real) | txt 99.5 %, markdown 99.6 %; real pages 97.5–99.2 % | `make fidelity` → [Outputs](outputs.md#fidelity) |
| `Document`, `Extractor` | Same slots in the same order: `as_dict()` and JSON keys come out alike | slot lists compared |
| `settings.cfg` | Same keys, same values | `DEFAULT_CONFIG` compared |

## Identical by construction

| Surface | Why |
|---|---|
| Output formats `txt`, `markdown`, `xml`, `xmltei`, `json`, `csv`, `html` | trafilatura's renderers, vendored verbatim |
| `Document.body` / `.commentsbody` | lxml trees in trafilatura's vocabulary: the engine's HTML goes through trafilatura's own `convert_tags` |
| Rescue, size, tree-size and duplicate checks | trafilatura's code, run in Python after the engine |
| `baseline`, `html2txt`, `deduplication` (`Simhash`, `LRUCache`, `content_fingerprint`, `duplicate_test`) | vendored |
| `load_html`, `fetch_url`, `fetch_response` | same inputs, `None` on failure, same `settings.cfg` keys (pools, retries, SSRF guard, size limits) |
| Deprecations (`no_fallback`, `as_dict`, `max_tree_size`) and input errors | same messages, same types → [API](api.md) |

## Divergences

| Area | trafilatura | etrafilatura | Visible as |
|---|---|---|---|
| Content selection | Python + lxml heuristics, readability and justext fallbacks | trafilatura-rs, a port of go-trafilatura, with the GIL released | Real pages differ by a heading, a table of contents, an aside |
| Tags | `<meta name="keywords">` first, kept as one string | JSON-LD `keywords` first; meta keywords split on commas | `tags` in metadata and every format carrying it |
| Dates | htmldate | the engine's meta and JSON-LD search; `extensive_search` selects its mode | Some pages date differently |
| `hostname` | courlan with the public suffix list | courlan's fast rule; the full host when it does not apply | `www.bbc.co.uk` instead of `bbc.co.uk` |
| Language detection | py3langid, when installed | whatlang, in the engine | Same `target_language` rejection, another detector |
| TEI `<application>` | `Trafilatura 2.3.1` | etrafilatura's own version | Deliberate: naming trafilatura's release would be false |
| Compressed input | gzip, zstd, brotli, deflate | the same, plus bz2, xz and zip | Extra formats only |
| Downloads | urllib3 or pycurl | urllib3 | — |

## Extensions

Additive only: no trafilatura call changes signature, default or result.

| Surface | Extension |
|---|---|
| `extract`, `bare_extraction`, `extract_with_metadata`, `extract_metadata` | `os.PathLike` inputs are read; keyword-only `input_format="auto"` fetches URL strings and reads path strings → [Input resolution](api.md#input-resolution) |
| `etrafilatura.ENGINE_VERSION` | The trafilatura-rs release compiled in |

## Not here

| Surface | Note |
|---|---|
| `trafilatura.feeds`, `.sitemaps`, `.spider` | Discovery and crawling are out of scope |
| `downloads.buffered_downloads`, `buffered_response_downloads`, `load_download_buffer`, `add_to_compressed_dict` | Batch downloading: loop over `fetch_url` |
| `metadata.extract_title`, `extract_author`, `extract_url`, `extract_sitename`, `extract_catstags`, `extract_license`, `extract_meta_json`, `extract_opengraph`, `examine_meta` | Metadata is the engine's: use `extract_metadata` |
| `core.extract_content`, `extract_comments`, `trafilatura_sequence`, `compare_extraction`, `justext_rescue` | Pipeline internals, replaced by the engine |
| `utils.language_filter`, `check_html_lang`, `is_acceptable_length`, `make_chunks` and the other pipeline helpers | Same |
| `htmlprocessing.tree_cleaning`, `prune_html`, `link_density_test` and the other pre-extraction passes | Same; `convert_tags`, `prune_unwanted_nodes`, `convert_to_html`, `build_html_output` are here |
| `settings.args_to_extractor` and the CLI internals | The `etrafilatura` command extracts files, URLs and stdin, without feed or crawl modes |
| `output_format="yaml"` | Not a trafilatura format either: same `AttributeError` |

## Vendored code

Renderers, deduplication, `baseline`/`html2txt`, `convert_tags` and the tree helpers come from trafilatura 2.3.1,
two URL helpers from courlan 1.4.0, both Apache-2.0 → [`NOTICE.md`](https://github.com/edamlabs/etrafilatura/blob/main/NOTICE.md).
They are re-synced from upstream releases, never edited.

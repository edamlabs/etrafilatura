# Notice: vendored code

Portions of this package are copied from [trafilatura](https://github.com/adbar/trafilatura)
(version 2.3.1), Copyright 2019-present Adrien Barbaresi and contributors, licensed under the
Apache License, Version 2.0. The full license text is available at
<https://www.apache.org/licenses/LICENSE-2.0> and in the appendix below.

## Vendored files

| File | Content |
|---|---|
| `src/etrafilatura/xml.py` | The complete XML/TEI/JSON/CSV/text rendering pipeline |
| `src/etrafilatura/baseline.py` | The baseline extraction and `html2txt` |
| `src/etrafilatura/htmlprocessing.py` | Subset: `prune_unwanted_nodes`, `convert_tags` and its converters (`convert_lists`, `convert_quotes`, `convert_headings`, `convert_line_breaks`, `convert_deletions`, `convert_details`, `convert_link`), `convert_to_html`, `build_html_output`, tag mappings |
| `src/etrafilatura/deduplication.py` | The complete deduplication module: `Simhash`, `LRUCache`, `duplicate_test` |
| `src/etrafilatura/data/tei_corpus.dtd` | The TEI DTD used by `validate_tei` |
| `src/etrafilatura/settings.py` | `Document`, `Extractor` (slots in upstream order; `encoding="utf-8"` on the config read) and the constants `BASIC_CLEAN_XPATH`, the inline-tag ladder, `MIN_DUPLICATE_LENGTH`, `DEDUPE_SCAN_CAP` |
| `src/etrafilatura/utils.py` | Helpers: `load_html`, `repair_faulty_html`, `fromstring_bytes`, `sanitize_tree`, `sanitize`, `line_processing`, `trim`, `remove_control_characters`, `normalize_unicode`, `textfilter`, `text_chars_test`, `as_list`, `image_src`, `is_image_file`, `is_dubious_html`, `return_printables_and_spaces`, `safe_base_url`, `safe_relative_url`, `_bounded_members`, `_bounded_inflate`, `_bounded_unbrotli` and the optional brotli/zstd imports |
| `src/etrafilatura/core.py` | `determine_returnstring`, `_check_deprecation`, `_yaml_scalar`, and the body of `bare_extraction` (its engine call excepted) |

From [courlan](https://github.com/adbar/courlan) 1.4.0 (same authors, Apache-2.0), `src/etrafilatura/utils.py`
carries `get_base_url` and `fix_relative_urls` (its `_parse` helper inlined), and the fast-path patterns
`DOMAIN_REGEX` / `STRIP_PORT_REGEX` of `extract_domain`.

The copies are verbatim except for their import blocks (absolute imports of this package), the
package name in `PKG_VERSION`, and the house lint requirements where behavior is unchanged.
They are re-synced from upstream trafilatura releases; do not edit them locally.

The extraction pipeline itself is NOT vendored: it runs in the Rust engine
[trafilatura-rs](https://github.com/nchapman/trafilatura-rs) (Apache-2.0), compiled into
`etrafilatura._native`.

-------------------------------------------------------------------------

Licensed under the Apache License, Version 2.0 (the "License"); you may not use the vendored
files except in compliance with the License. You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the
License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions
and limitations under the License.

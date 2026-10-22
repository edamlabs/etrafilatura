# API

```python
import etrafilatura as trafilatura
```

Every public call mirrors trafilatura's signature. This page documents each one with its parameters and
returns; the [compatibility map](compatibility.md) lists the known gaps.

## extract

```python
trafilatura.extract(html, output_format="markdown", include_comments=False)
```

Main function: extraction and conversion to the chosen output format.

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `filecontent` | str \| bytes \| HtmlElement \| Response | — | The page |
| `url` | str \| None | `None` | Original URL, resolves relative links |
| `record_id` | str \| None | `None` | ID added to the metadata |
| `fast` | bool | `False` | Skip backup (fallback) extraction |
| `favor_precision` / `favor_recall` | bool | `False` | Extraction focus |
| `include_comments` | bool | `True` | Extract comments separately |
| `output_format` | str | `"txt"` | `csv`, `html`, `json`, `markdown`, `txt`, `xml`, `xmltei` |
| `tei_validation` | bool | `False` | Validate TEI well-formedness |
| `target_language` | str \| None | `None` | Discard other languages (ISO 639-1) |
| `include_tables` / `include_images` / `include_links` | bool | `True` / `False` / `False` | Keep these elements |
| `include_formatting` | bool \| None | `None` | Keep formatting; implied by `markdown` |
| `deduplicate` | bool \| LRUCache | `False` | Segment and document deduplication |
| `date_extraction_params` | dict \| None | `None` | Date search parameters (`extensive_search`) |
| `with_metadata` / `only_with_metadata` | bool | `False` | Metadata in output / require date+title+url |
| `url_blacklist` / `author_blacklist` | set[str] \| None | `None` | Discard filtered documents/authors |
| `settingsfile` | str \| None | `None` | `settings.cfg` override |
| `prune_xpath` | str \| list[str] \| None | `None` | XPath expression(s) pruned before extraction |
| `config` / `options` | ConfigParser / Extractor | defaults | Direct configuration |
| `input_format` *(etrafilatura, keyword-only)* | `"html"` \| `"auto"` | `"html"` | How a `str` input is read — see [Input resolution](#input-resolution) |

Returns `str | None` — `None` on every rejection (wrong language, too little content, duplicate, blacklist…).

## bare_extraction

Same parameters as `extract` (minus `record_id`, `tei_validation`, `settingsfile`; plus `as_dict`), with
`output_format="python"` by default. Returns a [`Document`](#document) — `.text`, `.body` (lxml tree), `.comments`,
`.commentsbody` (lxml tree), `.raw_text` and the metadata fields — a `dict` with `as_dict=True`, or `None`.

## extract_with_metadata

Same parameters as `extract` with `with_metadata` forced on. Returns a `Document` whose `.text` carries the
rendered output, or `None`.

## Input resolution

An etrafilatura extension on `extract`, `bare_extraction`, `extract_with_metadata` and `extract_metadata`. Without
it the behaviour is trafilatura's: a string is HTML.

```python
from pathlib import Path

trafilatura.extract(Path("page.html"))                                # read from disk, any input_format
trafilatura.extract("https://example.org/article", input_format="auto")  # fetched, then extracted
trafilatura.extract("page.html", input_format="auto")                  # read from disk
trafilatura.extract("https://example.org/article")                     # None: a URL string is not HTML
```

| Input | `input_format="html"` (default) | `input_format="auto"` |
|---|---|---|
| `os.PathLike` | read (trafilatura: `TypeError`) | read |
| `str`, absolute `http(s)` URL, one token (WHATWG parser of the engine) | HTML | `fetch_response` with the call's config — SSRF guard, size and type checks; the final URL becomes `url` unless given |
| `str`, existing file path (≤ 4096 chars, one line, no `<`) | HTML | read |
| any other `str`, `bytes`, lxml tree, `Response` | as trafilatura | as trafilatura |

Files are read up to `MAX_FILE_SIZE`; larger ones return `None`. A failed download returns `None`. Strings are
resolved only on opt-in: guessing would fetch or read on behalf of a caller passing untrusted HTML.

## extract_metadata

```python
document = trafilatura.extract_metadata(html, default_url="https://example.org/page")
document.title, document.author, document.date, document.sitename
```

| Parameter | Type | Default |
|---|---|---|
| `filecontent` | str \| bytes \| HtmlElement \| Response | — |
| `default_url` | str \| None | `None` |
| `date_config` | dict \| None | `None` |
| `extensive` | bool | `True` |
| `author_blacklist` | set[str] \| None | `None` |

Always returns a `Document` (empty when there is nothing to parse).

## fetch_url · fetch_response · is_live_page

```python
page = trafilatura.fetch_url("https://example.org")
response = trafilatura.fetch_response("https://example.org", decode=True)
```

`fetch_url(url, no_ssl=False, config=DEFAULT_CONFIG, options=None) -> str | None` — downloads and decodes;
returns `None` on failures and unsuitable responses (status, content type, size limits).
`fetch_response(url, *, decode=False, no_ssl=False, config=DEFAULT_CONFIG) -> Response | None` — the full
response object (`.status`, `.headers`, `.data`, `.html`). `is_live_page(url)` answers a HEAD probe.

Pooling, retries, timeouts, user agents, cookies, SSRF protection and the insecure-SSL fallback are configured
through the same `settings.cfg` keys as trafilatura.

## load_html · baseline · html2txt

```python
tree = trafilatura.load_html(b"...")        # bytes/str/Response → lxml HtmlElement (or None)
tree, text, length = trafilatura.baseline(html)   # (lxml Element, str, int)
trafilatura.html2txt(html)                  # tag stripping
```

## Document

`etrafilatura.settings.Document`: same slots and methods as trafilatura's (`as_dict()`, `from_dict()`,
`clean_and_trim()`). `.body` and `.commentsbody` are lxml elements rooted at `<body>`, like trafilatura's.

## Extractor · use_config

```python
from etrafilatura.settings import Extractor, use_config

config = use_config("my-settings.cfg")     # FileNotFoundError when missing
options = Extractor(config=config, output_format="xml", recall=True, lang="en")
trafilatura.extract(html, options=options)
```

`Extractor` validates `output_format` (`AttributeError` otherwise), derives `focus`, `formatting` and
`with_metadata` exactly like trafilatura's, and reads the size and deduplication thresholds from the config.

## Native layer

`etrafilatura.ENGINE_VERSION` is the trafilatura-rs release compiled in; `etrafilatura.__version__` is this
package's own semver. The compiled module `etrafilatura._native` (`extract_html`,
`extract_metadata_html`) is private; it is typed in `_native.pyi` and covered by the same suite.

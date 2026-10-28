# API

Every public call keeps trafilatura's signature; rtrafilatura only adds keyword-only arguments
([Compatibility](compatibility.md)). The examples on this page run as doctests on every `make test`: the output
shown is the output you get.

```pycon
>>> import rtrafilatura as trafilatura
>>> html = """<html><head><title>Small tools win</title><meta name="author" content="Ada Lovelace">
... <meta property="og:site_name" content="Example Blog"><link rel="canonical" href="https://example.org/small-tools"></head>
... <body><nav><a href="/">Home</a> <a href="/about">About</a></nav>
... <article><h1>Small tools win</h1>
... <p>A tool that does one job is cheap to audit, cheap to replace, and composes with the rest through plain text.</p>
... <p>Platforms accumulate switching costs until leaving them costs more than staying; small tools never do.</p>
... <blockquote>Write programs that do one thing and do it well.</blockquote>
... <ul><li>grep searches</li><li>sort orders</li></ul>
... </article><footer>© 2026 Example Blog</footer></body></html>"""

```

## extract

```pycon
>>> print(trafilatura.extract(html))
Small tools win
A tool that does one job is cheap to audit, cheap to replace, and composes with the rest through plain text.
Platforms accumulate switching costs until leaving them costs more than staying; small tools never do.
Write programs that do one thing and do it well.
- grep searches
- sort orders
>>> print(trafilatura.extract(html, output_format="markdown", with_metadata=True))
---
title: Small tools win
author: Ada Lovelace
url: https://example.org/small-tools
hostname: example.org
sitename: Example Blog
date: "2026-01-01"
fingerprint: "25687d829efc2e43"
---
# Small tools win
<BLANKLINE>
A tool that does one job is cheap to audit, cheap to replace, and composes with the rest through plain text.
<BLANKLINE>
Platforms accumulate switching costs until leaving them costs more than staying; small tools never do.
<BLANKLINE>
Write programs that do one thing and do it well.
<BLANKLINE>
- grep searches
- sort orders
>>> trafilatura.extract("<html><body></body></html>") is None
True

```

| Parameter | Type | Default | Effect |
|---|---|---|---|
| `filecontent` | `str` \| `bytes` \| `HtmlElement` \| `Response` \| `os.PathLike` | — | The page; a path is read from disk |
| `url` | `str` \| `None` | `None` | Document URL: metadata fallback and base for relative links |
| `record_id` | `str` \| `None` | `None` | `id` in the metadata |
| `fast` | `bool` | `False` | Skip the fallback extractors |
| `favor_precision` / `favor_recall` | `bool` | `False` | Less but surer text / more text when unsure |
| `include_comments` | `bool` | `True` | Extract the comments section |
| `output_format` | `str` | `"txt"` | `txt`, `markdown`, `json`, `xml`, `xmltei`, `csv`, `html` → [Outputs](outputs.md) |
| `tei_validation` | `bool` | `False` | Validate `xmltei` against the TEI DTD |
| `target_language` | `str` \| `None` | `None` | ISO 639-1 code; other languages return `None` |
| `include_tables` / `include_images` / `include_links` | `bool` | `True` / `False` / `False` | Keep tables, images, link targets |
| `include_formatting` | `bool` \| `None` | `None` | Keep bold, italics…; implied by `markdown` |
| `deduplicate` | `bool` \| `LRUCache` | `False` | Drop repeated segments and documents |
| `date_extraction_params` | `dict` \| `None` | `None` | `extensive_search`, `max_date` |
| `with_metadata` / `only_with_metadata` | `bool` | `False` | Metadata in the output / require title, date and URL |
| `url_blacklist` / `author_blacklist` | `set[str]` \| `None` | `None` | Reject URLs, drop authors |
| `settingsfile` / `config` / `options` | `str` / `ConfigParser` / `Extractor` | defaults | Configuration → [Extractor](#extractor-use_config) |
| `prune_xpath` | `str` \| `list[str]` \| `None` | `None` | XPath expressions removed before extraction |
| `max_tree_size`, `no_fallback` | — | — | Deprecated, as in trafilatura |
| `input_format` *(keyword-only, rtrafilatura)* | `"html"` \| `"auto"` | `"html"` | → [Input resolution](#input-resolution) |

Returns `str`, or `None` when the page is rejected: too little content, wrong language, duplicate, blacklisted URL.

| Raises | When |
|---|---|
| `AttributeError` | Unknown `output_format` |
| `ValueError` | `max_tree_size` passed, `output_format="python"`, unknown `input_format` |
| `FileNotFoundError` | Missing `settingsfile`, or a path input that does not exist |
| `DeprecationWarning` (warning) | `no_fallback` |

## bare_extraction

```pycon
>>> document = trafilatura.bare_extraction(html, with_metadata=True)
>>> document.title, document.author, document.sitename
('Small tools win', 'Ada Lovelace', 'Example Blog')
>>> [child.tag for child in document.body]
['head', 'p', 'p', 'quote', 'list']
>>> list(document.as_dict())[:5]
['title', 'author', 'url', 'hostname', 'description']

```

Same parameters as `extract` without `record_id`, `tei_validation` and `settingsfile`, plus `as_dict`
(deprecated); `output_format` defaults to `"python"`. Returns a [`Document`](#document), or `None` on rejection.
`.body` and `.commentsbody` are lxml trees in trafilatura's vocabulary (`head`, `p`, `quote`, `list`/`item`,
`table`/`row`/`cell`, `hi`, `ref`). Raises as `extract`, plus a `DeprecationWarning` for `as_dict`.

## extract_with_metadata

```pycon
>>> trafilatura.extract_with_metadata(html).url
'https://example.org/small-tools'

```

Same parameters as `extract`, metadata always on. Returns a `Document` whose `.text` is the rendered output, or
`None`.

## extract_metadata

```pycon
>>> metadata = trafilatura.extract_metadata(html)
>>> metadata.title, metadata.url, metadata.hostname, metadata.date
('Small tools win', 'https://example.org/small-tools', 'example.org', '2026-01-01')

```

| Parameter | Type | Default | Effect |
|---|---|---|---|
| `filecontent` | as `extract` | — | The page |
| `default_url` | `str` \| `None` | `None` | URL used when the page declares none |
| `date_config` | `dict` \| `None` | `None` | `extensive_search`, `max_date` (also the `filedate`) |
| `extensive` | `bool` | `True` | Extensive date search when `date_config` is not given |
| `author_blacklist` | `set[str]` \| `None` | `None` | Authors to drop |
| `input_format` *(keyword-only, rtrafilatura)* | `"html"` \| `"auto"` | `"html"` | → [Input resolution](#input-resolution) |

Returns a `Document`, empty when the input parses to nothing.

| Raises | When |
|---|---|
| `TypeError` | Input of an unsupported type |
| `ValueError` | Unknown `input_format` |

## Input resolution

rtrafilatura's extension on `extract`, `bare_extraction`, `extract_with_metadata` and `extract_metadata`. The
default keeps trafilatura's behaviour: a string is HTML.

```pycon
>>> import tempfile, pathlib
>>> page = pathlib.Path(tempfile.mkdtemp()) / "page.html"
>>> _ = page.write_text(html, encoding="utf-8")
>>> trafilatura.extract(page) == trafilatura.extract(html)
True
>>> trafilatura.extract(str(page)) is None
True
>>> trafilatura.extract(str(page), input_format="auto") == trafilatura.extract(html)
True
>>> trafilatura.extract("https://example.org/article", input_format="auto")  # doctest: +SKIP
'…'

```

| Input | `input_format="html"` (default) | `input_format="auto"` |
|---|---|---|
| `os.PathLike` | read (trafilatura: `TypeError`) | read |
| `str`: absolute http(s) URL, one token, WHATWG-validated by the engine | HTML | fetched with `fetch_response` and the call's config (SSRF guard, size and type checks); the final URL becomes `url` unless one is given |
| `str`: existing file path, ≤ 4096 chars, one line, no `<` | HTML | read |
| anything else | as trafilatura | as trafilatura |

Files are read up to `MAX_FILE_SIZE`; a larger file or a failed download returns `None`. Strings are resolved
only on opt-in: guessing would fetch or read on behalf of a caller passing untrusted HTML.

## fetch_url · fetch_response · is_live_page

```pycon
>>> trafilatura.fetch_url("https://example.org")  # doctest: +SKIP
'<!doctype html>…'
>>> trafilatura.fetch_url("not a url") is None
True

```

| Call | Returns |
|---|---|
| `fetch_url(url, no_ssl=False, config=DEFAULT_CONFIG, options=None)` | Decoded HTML `str`, or `None` |
| `fetch_response(url, *, decode=False, no_ssl=False, with_headers=False, config=DEFAULT_CONFIG)` | `Response` (`.status`, `.url`, `.headers`, `.data`, `.html`), or `None` |
| `rtrafilatura.downloads.is_live_page(url)` | `bool` from a HEAD probe |

`None` covers every failure: network, status, content type, `MIN_FILE_SIZE`/`MAX_FILE_SIZE`, and private
addresses while `SSRF_PROTECTION` is on. Pools, retries, timeouts, user agents and cookies come from the same
`settings.cfg` keys as trafilatura. `with_headers` is accepted and ignored, as in trafilatura.

## load_html · baseline · html2txt

```pycon
>>> trafilatura.load_html(html).tag
'html'
>>> body, text, length = trafilatura.baseline(html)
>>> body.tag, length == len(text)
('body', True)
>>> trafilatura.html2txt("<html><body><p>One</p><p>Two</p></body></html>")
'One Two'

```

| Call | Returns | Raises |
|---|---|---|
| `load_html(htmlobject)` | lxml `HtmlElement`, or `None` when nothing parses | `TypeError` on unsupported input |
| `baseline(filecontent)` | `(lxml body, text, length)`: trafilatura's last-resort extraction | `TypeError` |
| `html2txt(content, clean=True)` | All the text of the page; `clean` drops scripts, styles and the like first | `TypeError` |

## Document

`rtrafilatura.settings.Document`: trafilatura's slots in trafilatura's order (`title`, `author`, `url`,
`hostname`, `description`, `sitename`, `date`, `categories`, `tags`, `fingerprint`, `id`, `license`, `body`,
`comments`, `commentsbody`, `raw_text`, `text`, `language`, `image`, `pagetype`, `filedate`) and its methods
`as_dict()`, `from_dict()`, `clean_and_trim()`.

## Extractor · use_config

```pycon
>>> from rtrafilatura.settings import Extractor, use_config
>>> options = Extractor(config=use_config(), output_format="xml", recall=True)
>>> options.focus, options.format
('recall', 'xml')
>>> trafilatura.extract(html, options=options).startswith("<doc")
True

```

`Extractor` validates `output_format` (`AttributeError`) and derives `focus`, `formatting` and `with_metadata`
as trafilatura does; `use_config(path)` reads a `settings.cfg` (`FileNotFoundError` when missing) with
trafilatura's keys.

## Native layer

`rtrafilatura.ENGINE_VERSION` is the trafilatura-rs release compiled in; `rtrafilatura.__version__` this
package's own version. `rtrafilatura._native` (`extract_html`, `extract_metadata_html`, `html2txt`,
`absolute_url`) is private, typed in `_native.pyi`.

`_native.html2txt(html)` is the engine's own block-aware text dump, the measure its recall escalation
compares an extraction against. It is not the public `html2txt`, which is trafilatura's vendored code: the
engine's takes a string only, always cleans, and returns what its HTML parser hands it — cookie-consent
banners, `<noscript>` content as markup text, soft hyphens dropped and text NFC-normalized.

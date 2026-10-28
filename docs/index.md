# rtrafilatura

<div class="rx-hero" markdown>
<p>Web page extraction at Rust speed, with trafilatura's syntax. The Python binding of <a href="https://github.com/nchapman/trafilatura-rs"><strong>trafilatura-rs</strong></a>, a pure-Rust engine by nchapman.</p>
</div>

An **EDamLabs binding**: a Python binding of a third-party engine that keeps its upstream's syntax and follows its releases ([EDamLabs families](https://github.com/edamlabs/esteward#identity)).

```bash
pip install rtrafilatura
```

```python
import rtrafilatura as trafilatura   # drop-in syntax

downloaded = trafilatura.fetch_url("https://example.org/article")
text = trafilatura.extract(downloaded, output_format="markdown", with_metadata=True)
```

Same verbs, keyword arguments, `Document` and lxml trees, renderers and `settings.cfg` as
[trafilatura](https://trafilatura.readthedocs.io/), on a compiled engine and with three dependencies (lxml,
urllib3, charset-normalizer) instead of seven. On the synthetic test pages the output is byte-identical in 64 of
84 format cases; on real pages the engine selects slightly different content → [Compatibility](compatibility.md).

| Call | Does |
|---|---|
| `extract(html)` | Page → string in the chosen output format |
| `bare_extraction(html)` | Page → `Document` with `.text`, `.body`, `.comments`, metadata |
| `extract_with_metadata(html)` | Page → `Document`, metadata always included |
| `extract_metadata(html)` | Page → metadata-only `Document` |
| `fetch_url(url)` / `fetch_response(url)` | Download, decode, SSRF-guarded |
| `load_html(source)` | str/bytes/Response → lxml `HtmlElement` |
| `baseline(html)` / `html2txt(html)` | Last-resort extraction / tag stripping |

## Why

<div class="rx-grid" markdown>
<div markdown>
### Speed
The extraction pipeline is Rust: html5ever parsing, scoring and fallbacks run compiled, with the GIL released.
</div>
<div markdown>
### Light
`lxml`, `urllib3` and `charset-normalizer` are the only Python dependencies — no htmldate, courlan, justext or
certifi, and no native toolchain at install time: abi3 wheels for Linux, macOS and Windows.
</div>
<div markdown>
### Compatible
Import it as trafilatura and keep your call sites: same signatures, output formats and configuration keys.
Extensions are keyword-only, such as `input_format="auto"` to extract straight from a URL or a file.
</div>
</div>

Format by format → [Outputs](outputs.md) · every call → [API](api.md) · what can fail → [Errors](errors.md) ·
gap-by-gap drop-in map → [Compatibility](compatibility.md)

!!! info "trafilatura-rs"
    Extraction quality, heuristics and performance belong to [trafilatura-rs](https://github.com/nchapman/trafilatura-rs)
    (itself a port of [go-trafilatura](https://github.com/markusmobius/go-trafilatura)). Extraction issues are
    [upstream issues](https://github.com/nchapman/trafilatura-rs/issues); anything about the Python API is
    [ours](https://github.com/edamlabs/rtrafilatura/issues).

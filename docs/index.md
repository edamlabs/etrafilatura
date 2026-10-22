# etrafilatura

<div class="rx-hero" markdown>
<p>Web page extraction at Rust speed, with trafilatura's syntax. The Python binding of <a href="https://github.com/nchapman/trafilatura-rs"><strong>trafilatura-rs</strong></a>, a pure-Rust engine by nchapman.</p>
</div>

```bash
pip install etrafilatura
```

```python
import etrafilatura as trafilatura   # drop-in syntax

downloaded = trafilatura.fetch_url("https://example.org/article")
text = trafilatura.extract(downloaded, output_format="markdown", with_metadata=True)
```

Same verbs, same keyword arguments, same `Document`, same `settings.cfg` as
[trafilatura](https://trafilatura.readthedocs.io/) — on a compiled engine, with two small pure dependencies
instead of lxml, htmldate, courlan and friends.

| Call | Does |
|---|---|
| `extract(html)` | Page → string in the chosen output format |
| `bare_extraction(html)` | Page → `Document` with `.text`, `.body`, `.comments`, metadata |
| `extract_with_metadata(html)` | Page → `Document`, metadata always included |
| `extract_metadata(html)` | Page → metadata-only `Document` |
| `fetch_url(url)` / `fetch_response(url)` | Download, decode, SSRF-guarded |
| `load_html(source)` | Normalize str/bytes/path/Response to an HTML string |
| `baseline(html)` / `html2txt(html)` | Last-resort extraction / tag stripping |

## Why

<div class="rx-grid" markdown>
<div markdown>
### Speed
The extraction pipeline is Rust: html5ever parsing, scoring and fallbacks run compiled, with the GIL released.
</div>
<div markdown>
### Light
`urllib3` and `charset-normalizer` are the only Python dependencies. No lxml, no native C toolchain at install
time — abi3 wheels for Linux, macOS and Windows.
</div>
<div markdown>
### Compatible
Import it as trafilatura and keep your call sites: same signatures, same output formats, same configuration keys.
</div>
</div>

Format by format → [Outputs](outputs.md) · every call → [API](api.md) · what can fail → [Errors](errors.md) ·
gap-by-gap drop-in map → [Compatibility](compatibility.md)

!!! info "trafilatura-rs"
    Extraction quality, heuristics and performance belong to [trafilatura-rs](https://github.com/nchapman/trafilatura-rs)
    (itself a port of [go-trafilatura](https://github.com/markusmobius/go-trafilatura)). Extraction issues are
    [upstream issues](https://github.com/nchapman/trafilatura-rs/issues); anything about the Python API is
    [ours](https://github.com/edamlabs/etrafilatura/issues).

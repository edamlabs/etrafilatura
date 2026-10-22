# Output formats

`extract(..., output_format=...)` renders the extraction in any of these formats. All of them carry the same
extracted content; they differ in serialization.

| Format | Returns | Notes |
|---|---|---|
| `txt` *(default)* | Plain text of the main content, comments appended | With `with_metadata=True`, a YAML-style header |
| `markdown` | Content rendered as Markdown | Formatting implied, like trafilatura |
| `yaml` | YAML metadata header + Markdown content | Header appears with `with_metadata=True` |
| `xml` | trafilatura-flavored `<doc>` XML: metadata attributes, `<main>`, `<comments>` | |
| `xmltei` | Minimal TEI document | `tei_validation=True` checks well-formedness |
| `json` | Metadata fields + `text` + `comments` | `ensure_ascii=False` |
| `csv` | One row: url, id, fingerprint, hostname, title, image, date, text, comments, license, pagetype | Tab-delimited |
| `html` | Self-contained HTML document | `<meta>` head with `with_metadata=True` |

```python
import etrafilatura as trafilatura

trafilatura.extract(html, output_format="json", with_metadata=True)
```

## Fidelity

`make fidelity` runs a reference corpus through etrafilatura and through Python trafilatura and scores the
agreement: token-level similarity of the `txt` and `markdown` outputs, plus field-level metadata agreement.
The chart shows the mean over the corpus; regressions beyond the tolerance fail the check.

![Agreement with trafilatura](assets/fidelity.svg)

The baseline lives in [`fidelity.json`](fidelity.json) and is rewritten by `make fidelity ARGS=--update`.
Differences are expected — the engines are independent implementations — the harness keeps them visible.

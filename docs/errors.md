# Errors

The public calls behave as trafilatura's: a rejected page is `None`, a wrong argument is a standard exception.

```pycon
>>> import etrafilatura as trafilatura
>>> page = "<html><body><article><p>" + "Ceci est une page en français, assez longue pour être extraite. " * 8 + "</p></article></body></html>"
>>> trafilatura.extract(page, target_language="en") is None
True
>>> trafilatura.extract(page, output_format="yaml")
Traceback (most recent call last):
...
AttributeError: Cannot set format, must be one of: csv, html, json, markdown, python, txt, xml, xmltei

```

## Rejections: `None`

`extract`, `bare_extraction` and `extract_with_metadata` log a warning (`discarding data: …`) and return `None` when
the content is too short, the language is not `target_language`, the document is a duplicate, its URL is
blacklisted or `only_with_metadata` lacks a field. `fetch_url` and `fetch_response` return `None` on every
download failure.

## Argument errors

| Exception | Raised by | When |
|---|---|---|
| `AttributeError` | `extract*`, `Extractor` | Unknown `output_format` |
| `ValueError` | `extract*` | `max_tree_size` passed (deprecated), `output_format="python"` outside `bare_extraction`, unknown `input_format` |
| `TypeError` | `load_html`, `extract_metadata`, `baseline`, `html2txt` | Input of an unsupported type |
| `FileNotFoundError` | `extract*`, `use_config` | Missing `settingsfile` or config path; a path input that does not exist |
| `DeprecationWarning` | `extract*`, `bare_extraction` | `no_fallback`, `as_dict` |

## The native layer

`etrafilatura.errors` holds the tree the compiled engine raises into, for callers of the private
`etrafilatura._native`. Through the public calls only `LanguageMismatchError` occurs, caught and turned into `None`:
the other engine gates are switched off because trafilatura's checks run in Python.

| Exception | `_native.extract_html` raises it when | Attributes |
|---|---|---|
| `ExtractionError` | Root; an engine failure without a class of its own | |
| `LanguageMismatchError` | `target_language` differs from the detected language | `.expected`, `.got` |
| `InsufficientContentError` | Text and comments below `min_output_size` / `min_output_comment_size` | |
| `MissingMetadataError` | `essential_metadata=True` and title, URL or date missing | |
| `TreeTooLargeError` | More than `max_tree_size` elements after stripping formatting | `.size` |
| `ParseError`, `DuplicateContentError` | Never: reserved, unreachable through the string API | |

The native functions also raise `ValueError` for an invalid `url`, `focus` or `date_mode`, and `RuntimeError` if
the engine panics: the panic is caught at the boundary, never propagated as an abort.

# Errors

Every failure the binding raises is rooted in `ExtractionError` (`etrafilatura.errors`). The native engine
raises into this tree.

```python
from etrafilatura.errors import ExtractionError, LanguageMismatchError
```

| Exception | Raised when | Attributes |
|---|---|---|
| `ExtractionError` | Root of the tree; unknown engine failure | |
| `ParseError` | The input could not be parsed as HTML | |
| `LanguageMismatchError` | The document language is not `target_language` | `.expected`, `.got` |
| `InsufficientContentError` | Extracted text and comments are below the configured minimums | |
| `MissingMetadataError` | `only_with_metadata` and title/url/date is missing | |
| `DuplicateContentError` | The extracted body is a duplicate (`deduplicate=True`) | |
| `TreeTooLargeError` | The output tree exceeds `MAX_TREE_SIZE` | `.size` |

## The trafilatura semantic

`extract`, `bare_extraction` and `extract_with_metadata` **catch** these errors, log a warning and return
`None` — exactly like trafilatura. You normally never see the exception:

```python
result = trafilatura.extract(html, target_language="fr")
if result is None:
    ...  # wrong language, too little content, duplicate, blacklisted…
```

The classes exist for the log record, for callers of the native layer, and for tests. Downloading has no
exception tree of its own: `fetch_url` and `fetch_response` return `None` on any network failure, like
trafilatura.

Input problems raise the standard Python errors: `ValueError` for a deprecated `max_tree_size`,
`AttributeError` for an unknown `output_format`, `FileNotFoundError` for a missing `settingsfile`.

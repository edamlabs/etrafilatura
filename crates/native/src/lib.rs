// ##### DEPENDENCIES #####

use std::any::Any;
use std::panic::AssertUnwindSafe;

use pyo3::exceptions::PyRuntimeError;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use trafilatura::Config;
use trafilatura::ExtractResult;
use trafilatura::ExtractionFocus;
use trafilatura::HtmlDateMode;
use trafilatura::Metadata;
use trafilatura::Options;
use trafilatura::TrafilaturaError;
use trafilatura::create_markdown_document;
use trafilatura::create_readable_document;
use trafilatura::dom::Document;
use trafilatura::dom::NodeId;
use trafilatura::extract as rs_extract;
use trafilatura::metadata::extract_metadata as rs_extract_metadata;

// ##### EXCEPTIONS #####

// The exception tree is Python (`etrafilatura.errors`); the engine only raises into it.
pyo3::import_exception!(etrafilatura.errors, ExtractionError);
pyo3::import_exception!(etrafilatura.errors, ParseError);
pyo3::import_exception!(etrafilatura.errors, LanguageMismatchError);
pyo3::import_exception!(etrafilatura.errors, InsufficientContentError);
pyo3::import_exception!(etrafilatura.errors, MissingMetadataError);
pyo3::import_exception!(etrafilatura.errors, DuplicateContentError);
pyo3::import_exception!(etrafilatura.errors, TreeTooLargeError);

fn to_py_err(error: TrafilaturaError) -> PyErr {
    let message = error.to_string();
    match error {
        TrafilaturaError::ParseError(_) => ParseError::new_err(message),
        TrafilaturaError::LanguageMismatch { expected, got } => {
            LanguageMismatchError::new_err((message, expected, got))
        }
        TrafilaturaError::InsufficientContent { .. } => InsufficientContentError::new_err(message),
        TrafilaturaError::MissingMetadata(_) => MissingMetadataError::new_err(message),
        TrafilaturaError::DuplicateContent => DuplicateContentError::new_err(message),
        TrafilaturaError::TreeTooLarge(size) => TreeTooLargeError::new_err((message, size)),
        TrafilaturaError::Io(source) => PyErr::from(source),
        // The engine enum is `#[non_exhaustive]`: an unknown variant stays a root error.
        _ => ExtractionError::new_err(message),
    }
}

fn panicked(payload: Box<dyn Any + Send>) -> PyErr {
    let reason = payload
        .downcast::<String>()
        .unwrap_or_else(|_| Box::new("unknown panic".to_string()));
    PyRuntimeError::new_err(format!("extraction panicked: {reason}"))
}

fn detach<T: Send>(py: Python<'_>, work: impl FnOnce() -> T + Send) -> PyResult<T> {
    py.detach(move || std::panic::catch_unwind(AssertUnwindSafe(work)))
        .map_err(panicked)
}

// ##### RESULTS #####

/// Metadata extracted from the document via meta tags, JSON-LD and OpenGraph.
#[pyclass(module = "etrafilatura._native", frozen, get_all)]
pub struct MetadataResult {
    title: String,
    author: String,
    url: String,
    hostname: String,
    description: String,
    sitename: String,
    /// Publication date as ISO `YYYY-MM-DD`, or None.
    date: Option<String>,
    categories: Vec<String>,
    tags: Vec<String>,
    id: String,
    fingerprint: String,
    license: String,
    language: String,
    image: String,
    page_type: String,
}

impl MetadataResult {
    fn build(inner: &Metadata) -> Self {
        Self {
            title: inner.title.clone(),
            author: inner.author.clone(),
            url: inner.url.clone(),
            hostname: inner.hostname.clone(),
            description: inner.description.clone(),
            sitename: inner.sitename.clone(),
            date: inner.date.map(|date| date.to_string()),
            categories: inner.categories.clone(),
            tags: inner.tags.clone(),
            id: inner.id.clone(),
            fingerprint: inner.fingerprint.clone(),
            license: inner.license.clone(),
            language: inner.language.clone(),
            image: inner.image.clone(),
            page_type: inner.page_type.clone(),
        }
    }
}

#[pymethods]
impl MetadataResult {
    fn __repr__(&self) -> String {
        format!(
            "MetadataResult(title={:?}, author={:?}, date={:?})",
            self.title, self.author, self.date
        )
    }
}

/// Outcome of one extraction: main text, comments, cleaned HTML and metadata.
#[pyclass(module = "etrafilatura._native", frozen)]
pub struct ExtractionResult {
    inner: ExtractResult,
}

#[pymethods]
impl ExtractionResult {
    /// Extracted main content as plain text.
    #[getter]
    fn content_text(&self) -> String {
        self.inner.content_text.clone()
    }

    /// Extracted comments as plain text; empty when comments were excluded.
    #[getter]
    fn comments_text(&self) -> String {
        self.inner.comments_text.clone()
    }

    /// Extracted main content as cleaned, trafilatura-flavored HTML.
    #[getter]
    fn content_html(&self) -> String {
        self.inner.content_html.clone()
    }

    /// Extracted comments as cleaned HTML.
    #[getter]
    fn comments_html(&self) -> String {
        self.inner.comments_html.clone()
    }

    /// Main content rendered as Markdown.
    #[getter]
    fn markdown(&self) -> String {
        self.inner.content_markdown()
    }

    /// Comments rendered as Markdown.
    #[getter]
    fn comments_markdown(&self) -> String {
        self.inner.comments_markdown()
    }

    /// Complete, self-contained HTML document: metadata header, content and comments.
    #[getter]
    fn readable_document(&self) -> String {
        create_readable_document(&self.inner)
    }

    /// Full document as Markdown with a YAML front matter, content and comments.
    #[getter]
    fn markdown_document(&self) -> String {
        create_markdown_document(&self.inner)
    }

    /// Metadata extracted from the document.
    #[getter]
    fn metadata(&self) -> MetadataResult {
        MetadataResult::build(&self.inner.metadata)
    }

    fn __repr__(&self) -> String {
        format!(
            "ExtractionResult(text={} chars, comments={} chars)",
            self.inner.content_text.chars().count(),
            self.inner.comments_text.chars().count(),
        )
    }
}

// ##### OPTIONS #####

const FOCUS_PRECISION: &str = "precision";
const FOCUS_RECALL: &str = "recall";

fn parse_focus(focus: &str) -> PyResult<ExtractionFocus> {
    match focus {
        "balanced" => Ok(ExtractionFocus::Balanced),
        FOCUS_PRECISION => Ok(ExtractionFocus::FavorPrecision),
        FOCUS_RECALL => Ok(ExtractionFocus::FavorRecall),
        other => Err(PyValueError::new_err(format!(
            "focus must be 'balanced', '{FOCUS_PRECISION}' or '{FOCUS_RECALL}', got {other:?}"
        ))),
    }
}

fn parse_date_mode(mode: &str) -> PyResult<HtmlDateMode> {
    match mode {
        "default" => Ok(HtmlDateMode::Default),
        "fast" => Ok(HtmlDateMode::Fast),
        "extensive" => Ok(HtmlDateMode::Extensive),
        "disabled" => Ok(HtmlDateMode::Disabled),
        other => Err(PyValueError::new_err(format!(
            "date_mode must be 'default', 'fast', 'extensive' or 'disabled', got {other:?}"
        ))),
    }
}

fn parse_url(url: &str) -> PyResult<url::Url> {
    url::Url::parse(url)
        .map_err(|error| PyValueError::new_err(format!("invalid url {url:?}: {error}")))
}

#[allow(clippy::too_many_arguments)]
fn build_options(
    url: Option<String>,
    target_language: Option<String>,
    fallback: bool,
    focus: &str,
    comments: bool,
    tables: bool,
    images: bool,
    links: bool,
    excluded_authors: Vec<String>,
    deduplicate: bool,
    essential_metadata: bool,
    max_tree_size: Option<usize>,
    prune_selector: Option<String>,
    date_mode: &str,
    min_extracted_size: usize,
    min_output_size: usize,
    min_output_comment_size: usize,
    min_duplicate_check_size: usize,
    max_duplicate_count: usize,
    cache_size: usize,
) -> PyResult<Options> {
    // `Options` and `Config` are `#[non_exhaustive]`: mutate the default, never a literal.
    let mut options = Options::default();
    options.config = Config::default()
        .with_cache_size(cache_size)
        .with_min_duplicate_check_size(min_duplicate_check_size)
        .with_max_duplicate_count(max_duplicate_count)
        .with_min_extracted_size(min_extracted_size)
        .with_min_extracted_comment_size(min_output_comment_size.max(1))
        .with_min_output_size(min_output_size)
        .with_min_output_comment_size(min_output_comment_size);
    options.original_url = url.as_deref().map(parse_url).transpose()?;
    options.target_language = target_language;
    options.enable_fallback = fallback;
    options.focus = parse_focus(focus)?;
    options.exclude_comments = !comments;
    options.exclude_tables = !tables;
    options.include_images = images;
    options.include_links = links;
    options.excluded_authors = excluded_authors;
    options.deduplicate = deduplicate;
    options.has_essential_metadata = essential_metadata;
    options.max_tree_size = max_tree_size;
    options.prune_selector = prune_selector;
    options.enable_log = false;
    options.html_date_mode = parse_date_mode(date_mode)?;
    Ok(options)
}

// ##### EXTRACTION #####

/// Parse an HTML string and extract its main content, comments and metadata.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
#[pyo3(
    signature = (html, *, url = None, target_language = None, fallback = true, focus = String::from("balanced"),
                 comments = true, tables = true, images = false, links = false,
                 excluded_authors = Vec::new(), deduplicate = false, essential_metadata = false,
                 max_tree_size = None, prune_selector = None, date_mode = String::from("default"),
                 min_extracted_size = 250, min_output_size = 1, min_output_comment_size = 1,
                 min_duplicate_check_size = 100, max_duplicate_count = 2, cache_size = 4096)
)]
fn extract_html(
    py: Python<'_>,
    html: String,
    url: Option<String>,
    target_language: Option<String>,
    fallback: bool,
    focus: String,
    comments: bool,
    tables: bool,
    images: bool,
    links: bool,
    excluded_authors: Vec<String>,
    deduplicate: bool,
    essential_metadata: bool,
    max_tree_size: Option<usize>,
    prune_selector: Option<String>,
    date_mode: String,
    min_extracted_size: usize,
    min_output_size: usize,
    min_output_comment_size: usize,
    min_duplicate_check_size: usize,
    max_duplicate_count: usize,
    cache_size: usize,
) -> PyResult<ExtractionResult> {
    let options = build_options(
        url,
        target_language,
        fallback,
        &focus,
        comments,
        tables,
        images,
        links,
        excluded_authors,
        deduplicate,
        essential_metadata,
        max_tree_size,
        prune_selector,
        &date_mode,
        min_extracted_size,
        min_output_size,
        min_output_comment_size,
        min_duplicate_check_size,
        max_duplicate_count,
        cache_size,
    )?;
    let outcome = detach(py, move || rs_extract(&html, &options))?;
    Ok(ExtractionResult {
        inner: outcome.map_err(to_py_err)?,
    })
}

/// Extract only the metadata of an HTML string.
#[pyfunction]
#[pyo3(signature = (html, *, url = None, excluded_authors = Vec::new(), date_mode = String::from("default")))]
fn extract_metadata_html(
    py: Python<'_>,
    html: String,
    url: Option<String>,
    excluded_authors: Vec<String>,
    date_mode: String,
) -> PyResult<MetadataResult> {
    let mut options = Options::default();
    options.excluded_authors = excluded_authors;
    options.html_date_mode = parse_date_mode(&date_mode)?;
    options.original_url = url.as_deref().map(parse_url).transpose()?;
    let metadata = detach(py, move || {
        let document = Document::parse(&html);
        rs_extract_metadata(&document, &options)
    })?;
    Ok(MetadataResult::build(&metadata))
}

// ##### TEXT #####

const BLOCK_TAGS: &[&str] = &[
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "caption",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
];

const SKIP_TAGS: &[&str] = &["script", "style", "noscript", "template"];

fn is_block(tag: &str) -> bool {
    BLOCK_TAGS.contains(&tag)
}

fn walk_text(document: &Document, id: NodeId, out: &mut String) {
    out.push_str(&document.text(id));
    for child in document.children(id) {
        let tag = document.tag_name(child);
        if SKIP_TAGS.contains(&tag) {
            continue;
        }
        let block = is_block(tag);
        if block {
            out.push('\n');
        }
        walk_text(document, child, out);
        out.push_str(&document.tail(child));
        if block {
            out.push('\n');
        }
    }
}

/// Strip every tag and return the visible text of an HTML string, blocks on their own line.
#[pyfunction]
fn html_to_text(py: Python<'_>, html: String) -> PyResult<String> {
    detach(py, move || {
        let document = Document::parse(&html);
        let root = document.body().unwrap_or_else(|| document.root());
        let mut text = String::new();
        walk_text(&document, root, &mut text);
        text
    })
}

/// Convert an HTML fragment to Markdown.
#[pyfunction]
fn html_to_markdown(py: Python<'_>, html: String) -> PyResult<String> {
    detach(py, move || html2markdown::convert(&html))
}

// ##### MODULE #####

/// The version of the trafilatura-rs engine compiled into this extension.
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(extract_html, m)?)?;
    m.add_function(wrap_pyfunction!(extract_metadata_html, m)?)?;
    m.add_function(wrap_pyfunction!(html_to_text, m)?)?;
    m.add_function(wrap_pyfunction!(html_to_markdown, m)?)?;
    m.add_class::<ExtractionResult>()?;
    m.add_class::<MetadataResult>()?;
    m.add("ENGINE_VERSION", env!("TRAFILATURA_ENGINE_VERSION"))?;
    Ok(())
}

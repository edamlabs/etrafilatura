"""Output renderers: XML, TEI, JSON, CSV, HTML and text — same output shapes as trafilatura.xml."""

import csv
import json
from collections.abc import Iterator
from io import StringIO
from xml.dom.minidom import parseString
from xml.sax.saxutils import escape, quoteattr

from etrafilatura import _native
from etrafilatura.settings import Document, Extractor


def render_text(html: str, formatting: bool) -> str:
    """Render cleaned body HTML as plain text, or as Markdown with formatting."""
    return _native.html_to_markdown(html) if formatting else _native.html_to_text(html)


def meta_items(docmeta: Document) -> Iterator[tuple[str, str]]:
    """Non-empty metadata fields as strings, lists joined with semicolons."""
    for attr in docmeta.__slots__:
        if attr in ("body", "commentsbody", "comments", "raw_text", "text"):
            continue
        value = getattr(docmeta, attr)
        if isinstance(value, list):
            yield attr, ";".join(value)
        elif value:
            yield attr, str(value)


def _xml_meta(document: Document) -> str:
    pairs = " ".join(f"{name.replace('_', '-')}={quoteattr(value)}" for name, value in meta_items(document))
    counts = f'comments="{len(document.comments or "")}" raw-text="{len(document.raw_text or "")}"'
    return f"{pairs} {counts}".strip()


def build_xml_output(docmeta: Document) -> str:
    """Build the trafilatura XML output string based on extracted information."""
    body = f"<main>{docmeta.body}</main>" if docmeta.body else "<main/>"
    comments = f"<comments>{docmeta.commentsbody}</comments>" if docmeta.commentsbody else "<comments/>"
    attrs = _xml_meta(docmeta)
    opening = f"<doc {attrs}>" if attrs else "<doc>"
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{opening}{body}{comments}</doc>'


def build_tei_output(docmeta: Document) -> str:
    """Bundle the extracted post and comments into a minimal TEI document."""
    title = escape(docmeta.title or "Unknown")
    author = f"<author>{escape(docmeta.author)}</author>" if docmeta.author else ""
    date = f'<date when="{docmeta.date}"/>' if docmeta.date else ""
    license = f'<licence target="{escape(docmeta.license)}"/>' if docmeta.license else ""
    source = f"<p>{escape(docmeta.url or '')}</p>"
    keywords = ""
    if terms := [*(docmeta.categories or []), *(docmeta.tags or [])]:
        joined = "".join(f"<term>{escape(term)}</term>" for term in terms)
        keywords = f"<textClass><keywords>{joined}</keywords></textClass>"
    paragraphs = "".join(
        f"<p>{escape(line)}</p>" for line in render_text(docmeta.body, formatting=False).splitlines() if line.strip()
    )
    comments = ""
    if docmeta.commentsbody:
        comment_lines = "".join(
            f'<div type="comment"><p>{escape(line)}</p></div>'
            for line in render_text(docmeta.commentsbody, formatting=False).splitlines()
            if line.strip()
        )
        comments = f'<back><div type="comments">{comment_lines}</div></back>'
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc>"
        f"<titleStmt><title>{title}</title>{author}</titleStmt>"
        f'<publicationStmt><publisher>etrafilatura</publisher><availability status="free">{license}</availability></publicationStmt>'
        f"<sourceDesc>{source}</sourceDesc>"
        "</fileDesc>"
        f"<profileDesc>{date}{keywords}</profileDesc>"
        "</teiHeader>"
        f"<text><body>{paragraphs}</body>{comments}</text>"
        "</TEI>"
    )


def validate_tei(xmldoc: str) -> bool:
    """Check that the TEI output is well-formed XML."""
    try:
        parseString(xmldoc)
    except Exception as err:
        message = f"TEI output is not well-formed: {err}"
        raise ValueError(message) from err
    return True


def control_xml_output(document: Document, options: Extractor) -> str:
    """Make sure the XML output is conform and valid if required."""
    builder = build_xml_output if options.format == "xml" else build_tei_output
    output = builder(document)
    if options.format == "xmltei" and options.tei_validation:
        validate_tei(output)
    return output


def build_json_output(docmeta: Document, with_metadata: bool = True) -> str:
    """Build JSON output based on extracted information."""
    if with_metadata:
        outputdict: dict[str, object] = {
            "id": docmeta.id,
            "title": docmeta.title,
            "author": docmeta.author,
            "source": docmeta.url,
            "source-hostname": docmeta.sitename,
            "excerpt": docmeta.description,
            "categories": ";".join(docmeta.categories or []),
            "tags": ";".join(docmeta.tags or []),
            "date": docmeta.date,
            "fingerprint": docmeta.fingerprint,
            "license": docmeta.license,
            "language": docmeta.language,
            "image": docmeta.image,
            "pagetype": docmeta.pagetype,
            "filedate": docmeta.filedate,
            "text": render_text(docmeta.body, formatting=False),
        }
    else:
        outputdict = {"text": render_text(docmeta.body, formatting=False)}
    outputdict["comments"] = render_text(docmeta.commentsbody, formatting=False)
    return json.dumps(outputdict, ensure_ascii=False)


def xmltocsv(document: Document, include_formatting: bool, *, delim: str = "\t", null: str = "null") -> str:
    """Convert the document to a one-row CSV string."""
    posttext = render_text(document.body, formatting=include_formatting) or null
    commentstext = render_text(document.commentsbody, formatting=include_formatting) or null
    output = StringIO()
    writer = csv.writer(output, delimiter=delim, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            value or null
            for value in (
                document.url,
                document.id,
                document.fingerprint,
                document.hostname,
                document.title,
                document.image,
                document.date,
                posttext,
                commentstext,
                document.license,
                document.pagetype,
            )
        ]
    )
    return output.getvalue()


def build_html_output(document: Document, with_metadata: bool = False) -> str:
    """Convert the document to a self-contained HTML string."""
    head = "".join(f'<meta name="{escape(name)}" content="{escape(value)}"/>' for name, value in meta_items(document))
    head = f'<meta charset="utf-8"/>{head}' if with_metadata else '<meta charset="utf-8"/>'
    comments = f"<aside>{document.commentsbody}</aside>" if document.commentsbody else ""
    return f"<!DOCTYPE html>\n<html><head>{head}</head><body><main>{document.body}</main>{comments}</body></html>"

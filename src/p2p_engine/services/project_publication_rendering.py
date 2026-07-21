from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path


PDF_OPTIONAL_INSTALL_MESSAGE = (
    "PDF rendering requires the optional p2p-engine[pdf] capability with WeasyPrint "
    "and its native dependencies installed."
)


@dataclass(frozen=True)
class PublicationRenderResult:
    status: str
    path: Path
    sha256: str
    curated_sha256: str
    validation_sha256: str
    theme: str
    renderer: str
    rendered_at: str
    language: str = "en"
    edition_key: str = "project-en"


PdfRenderer = Callable[..., str]


def render_pdf_with_weasyprint(
    markdown_text: str,
    output_path: Path,
    root: Path,
    *,
    language: str = "en",
    title: str = "Project Publication",
) -> str:
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        raise ValueError(PDF_OPTIONAL_INSTALL_MESSAGE) from exc
    try:
        from weasyprint import CSS, HTML
    except ImportError as exc:
        raise ValueError(PDF_OPTIONAL_INSTALL_MESSAGE) from exc

    html_body = MarkdownIt("commonmark", {"html": False}).enable("table").render(markdown_text)
    rendered_html = _html_document(html_body, language=language, title=title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=output_path.parent, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        HTML(string=rendered_html, base_url=str(root)).write_pdf(
            str(temp_path),
            stylesheets=[CSS(string=_neutral_css())],
        )
        temp_path.replace(output_path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
    return "weasyprint-neutral-v1"


def _html_document(
    body: str,
    *,
    language: str = "en",
    title: str = "Project Publication",
) -> str:
    return (
        "<!doctype html>\n"
        f"<html lang=\"{escape(language, quote=True)}\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        f"  <title>{escape(title)}</title>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )


def _neutral_css() -> str:
    return """
@page {
  size: A4;
  margin: 22mm 18mm;
}
body {
  color: #202124;
  font-family: "DejaVu Serif", Georgia, serif;
  font-size: 10.5pt;
  line-height: 1.48;
}
h1, h2, h3, h4 {
  color: #111827;
  font-family: "DejaVu Sans", Arial, sans-serif;
  font-weight: 700;
  page-break-after: avoid;
}
h1 {
  font-size: 22pt;
  margin: 0 0 16pt;
}
h2 {
  border-bottom: 0.4pt solid #d0d7de;
  font-size: 15pt;
  margin-top: 20pt;
  padding-bottom: 4pt;
}
h3 {
  font-size: 12pt;
  margin-top: 14pt;
}
a {
  color: #0645ad;
}
code, pre {
  font-family: "DejaVu Sans Mono", monospace;
}
pre {
  background: #f6f8fa;
  border: 0.4pt solid #d0d7de;
  padding: 8pt;
  white-space: pre-wrap;
}
table {
  border-collapse: collapse;
  width: 100%;
}
th, td {
  border: 0.4pt solid #d0d7de;
  padding: 4pt 6pt;
  vertical-align: top;
}
blockquote {
  border-left: 3pt solid #d0d7de;
  color: #4b5563;
  margin-left: 0;
  padding-left: 10pt;
}
""".strip()


def write_bytes_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)
        temp_path.replace(path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

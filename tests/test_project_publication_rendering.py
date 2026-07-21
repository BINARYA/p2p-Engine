from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.services.project_publication_rendering import (
    _html_document,
    render_pdf_with_weasyprint,
)


def test_publication_html_preserves_language_title_and_unicode() -> None:
    document = _html_document(
        "<p>Contenuto con qualita.</p>",
        language="it-IT",
        title="Qualita & utilita",
    )

    assert '<html lang="it-IT">' in document
    assert "<title>Qualita &amp; utilita</title>" in document
    assert "Contenuto con qualita." in document


@pytest.mark.parametrize("language", ["en", "it"])
def test_real_renderer_writes_nonblank_language_editions(
    tmp_path: Path,
    language: str,
) -> None:
    pytest.importorskip("markdown_it")
    pytest.importorskip("weasyprint")
    output = tmp_path / f"manual-{language}.pdf"
    markdown = (
        "# Project\n\n"
        "## Details\n\n"
        "| Field | Value |\n| --- | --- |\n| Language | "
        + language
        + " |\n\n```text\nrender-safe code\n```\n\n"
        + ("A developed chapter. " * 400)
    )

    renderer = render_pdf_with_weasyprint(
        markdown,
        output,
        tmp_path,
        language=language,
        title=f"Project {language}",
    )

    assert renderer == "weasyprint-neutral-v1"
    assert output.read_bytes().startswith(b"%PDF-")
    assert output.stat().st_size > 1_000


def test_renderer_failure_preserves_previous_pdf_and_cleans_temp_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("markdown_it")
    weasyprint = pytest.importorskip("weasyprint")
    output = tmp_path / "project-en.pdf"
    previous = b"%PDF-1.4\nprevious\n"
    output.write_bytes(previous)
    before = set(tmp_path.iterdir())

    def fail_write_pdf(self, target, **kwargs):
        Path(target).write_bytes(b"partial")
        raise RuntimeError("injected renderer failure")

    monkeypatch.setattr(weasyprint.HTML, "write_pdf", fail_write_pdf)

    with pytest.raises(RuntimeError, match="injected renderer failure"):
        render_pdf_with_weasyprint(
            "# Project\n",
            output,
            tmp_path,
            language="en",
            title="Project",
        )

    assert output.read_bytes() == previous
    assert set(tmp_path.iterdir()) == before

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import builtins

import pytest
import yaml

from p2p_engine.services.project_publication import ProjectPublicationService
from p2p_engine.services.project_publication_rendering import render_pdf_with_weasyprint
from p2p_engine.services.visible_project_export import VisibleProjectExportService


def _accepted(proposal_dir: Path) -> list[dict[str, object]]:
    return [
        {
            "proposal_id": "PROP-001",
            "title": "Canonical Publication",
            "status": "accepted",
            "feature_id": "canonical-publication",
            "path": proposal_dir,
            "source": ".p2p/proposals/PROP-001-canonical-publication",
        }
    ]


def _write_project_state(tmp_path: Path) -> Path:
    p2p_dir = tmp_path / ".p2p"
    proposal_dir = p2p_dir / "proposals" / "PROP-001-canonical-publication"
    proposal_dir.mkdir(parents=True)
    (p2p_dir / "registries").mkdir(parents=True)
    (p2p_dir / "project.yml").write_text("project:\n  name: Demo Project\n", encoding="utf-8")
    (p2p_dir / "registries" / "proposals.yml").write_text("proposals: []\n", encoding="utf-8")
    (p2p_dir / "registries" / "decisions.yml").write_text("decisions: []\n", encoding="utf-8")
    (p2p_dir / "registries" / "artifacts.yml").write_text("artifacts: []\n", encoding="utf-8")
    (p2p_dir / "registries" / "readiness.yml").write_text("readiness: []\n", encoding="utf-8")
    (proposal_dir / "proposal.md").write_text(
        "# PROP-001 - Canonical Publication\n\n"
        "## Status\n\n"
        "`accepted`\n\n"
        "## Proposal\n\n"
        "Publish a readable canonical project document.\n\n"
        "## Acceptance Criteria\n\n"
        "- A publication packet exists.\n",
        encoding="utf-8",
    )
    return proposal_dir


def _service(tmp_path: Path, proposal_dir: Path, *, pdf_renderer=None) -> ProjectPublicationService:
    visible = VisibleProjectExportService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        project_name=lambda: "Demo Project",
        accepted_proposals=lambda: _accepted(proposal_dir),
    )
    return ProjectPublicationService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        export_visible_project=visible.export,
        accepted_proposals=lambda: _accepted(proposal_dir),
        pdf_renderer=pdf_renderer,
    )


def _fake_pdf_renderer(markdown_text: str, output_path: Path, root: Path) -> str:
    assert "# Demo Project" in markdown_text
    output_path.write_bytes(b"%PDF-1.4\n% fake publication pdf\n")
    return "fake-pdf-renderer"


def test_publication_prepare_writes_profile_packet_and_manifest_idempotently(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)

    first = service.prepare()
    second = service.prepare()

    assert first.exported is True
    assert first.archived_path is None
    assert second.exported is False
    assert second.reused_export is True
    assert not (tmp_path / "outputs" / "review-001").exists()
    assert (tmp_path / "outputs" / "latest" / "project.md").exists()
    assert (tmp_path / "outputs" / "latest" / "publication-profile.yml").exists()
    packet = (tmp_path / "outputs" / "latest" / "curator-input.md").read_text(encoding="utf-8")
    assert "Produce one canonical human project document" in packet
    assert "source_of_truth: `.p2p/`" in packet
    manifest = yaml.safe_load((tmp_path / "outputs" / "latest" / "publication-manifest.yml").read_text(encoding="utf-8"))
    assert manifest["pipeline"] == "human_project_publication"
    assert manifest["publication_role"] == "canonical_human_publication"
    assert manifest["stages"]["source_export"]["path"] == "outputs/latest/project.md"
    assert manifest["stages"]["curator_packet"]["source_sha256"] == second.source_sha256


def test_publication_prepare_packet_records_present_vertical_summary(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    visible = VisibleProjectExportService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        project_name=lambda: "Demo Project",
        accepted_proposals=lambda: _accepted(proposal_dir),
    )
    service = ProjectPublicationService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        export_visible_project=visible.export,
        accepted_proposals=lambda: _accepted(proposal_dir),
        project_vertical_lock_status=lambda: SimpleNamespace(
            status="locked",
            locked=SimpleNamespace(vertical_id="software_project"),
        ),
        project_definition_view=lambda: SimpleNamespace(exists=True, valid=True),
    )

    service.prepare()
    packet = (tmp_path / "outputs" / "latest" / "curator-input.md").read_text(encoding="utf-8")

    assert "active_vertical: software_project" in packet
    assert "definition_state_exists: true" in packet


def test_publication_prepare_exports_and_archives_when_source_fingerprint_changes(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)

    service.prepare()
    (proposal_dir / "proposal.md").write_text(
        "# PROP-001 - Canonical Publication\n\n## Status\n\n`accepted`\n\n## Proposal\n\nChanged source.\n",
        encoding="utf-8",
    )

    result = service.prepare()

    assert result.exported is True
    assert result.archived_path == Path("outputs/review-001")
    assert (tmp_path / "outputs" / "review-001" / "project.md").exists()
    assert "curated" in result.stale_downstream


def test_publication_import_writes_curated_output_and_status(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    draft = drafts / "project.curated.draft.md"
    draft.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project publishes one canonical human project document.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )

    result = service.import_curated(draft)
    status = service.status()

    assert result.curated_path == Path("outputs/latest/project.curated.md")
    assert result.imported_from == Path("drafts/project.curated.draft.md")
    assert (tmp_path / result.curated_path).read_text(encoding="utf-8").startswith("# Demo Project")
    assert next(stage for stage in status.stages if stage.name == "curated").status == "ready"
    assert next(stage for stage in status.stages if stage.name == "validation").status == "missing"
    assert status.approved_for_publication is False


def test_publication_validate_writes_report_and_manifest_status(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    draft = tmp_path / "project.curated.draft.md"
    draft.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication for this project vertical.\n\n"
        "## Current And Planned State\n\n"
        "Current and planned work remains traceable to PROP-001.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(draft)

    result = service.validate()
    status = service.status()

    assert result.status == "passed"
    assert (tmp_path / "outputs" / "latest" / "publication-validation.yml").exists()
    assert status.validation_status == "passed"


def test_publication_validate_fails_deterministic_contract_errors(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    draft = tmp_path / "bad-curated.md"
    draft.write_text("# One\n\n# Two\n\nNo source statement.\n", encoding="utf-8")
    service.import_curated(draft)

    result = service.validate()

    assert result.status == "failed"
    codes = {finding.code for finding in result.findings if finding.severity == "error"}
    assert "single_h1_required" in codes
    assert "executive_summary_missing" in codes
    assert "source_of_truth_missing" in codes


def test_publication_validate_warnings_do_not_fail_document(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    draft = tmp_path / "proposal-dump-curated.md"
    draft.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication.\n\n"
        "## PROP-001\n\n"
        "Current evidence remains traceable to PROP-001.\n\n"
        "## PROP-002\n\n"
        "Planned evidence remains traceable to PROP-002.\n\n"
        "## PROP-003\n\n"
        "Pending evidence remains traceable to PROP-003.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(draft)

    result = service.validate()

    assert result.status == "passed"
    assert any(finding.code == "probable_proposal_dump" for finding in result.findings)


def test_publication_validate_warns_on_placeholder_text(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    draft = tmp_path / "placeholder-curated.md"
    draft.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication. TODO clarify one detail.\n\n"
        "## Current And Planned State\n\n"
        "Current and planned work remains traceable to PROP-001.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(draft)

    result = service.validate()

    assert result.status == "passed"
    assert any(finding.code == "placeholder_text" for finding in result.findings)


def test_publication_validate_reports_missing_curated_output(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()

    result = service.validate()

    assert result.status == "failed"
    assert any(finding.code == "missing_curated" for finding in result.findings)
    assert (tmp_path / "outputs" / "latest" / "publication-validation.yml").exists()


def test_publication_render_and_review_current_package(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir, pdf_renderer=_fake_pdf_renderer)
    service.prepare()
    draft = tmp_path / "project.curated.draft.md"
    draft.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication for this project vertical.\n\n"
        "## Current And Planned State\n\n"
        "Current and planned work remains traceable to PROP-001.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(draft)
    assert service.validate().status == "passed"

    render = service.render()
    review = service.review(status="approved", reviewer="owner", notes=["Ready to publish."])
    status = service.status()

    assert render.status == "rendered"
    assert render.path == Path("outputs/latest/project.pdf")
    assert review.status == "approved"
    assert review.review_path == Path("outputs/latest/publication-review.yml")
    assert status.render_status == "rendered"
    assert status.review_status == "approved"
    assert status.approved_for_publication is True


def test_publication_render_refuses_failed_validation(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir, pdf_renderer=_fake_pdf_renderer)
    service.prepare()
    draft = tmp_path / "bad-curated.md"
    draft.write_text("# One\n\n# Two\n", encoding="utf-8")
    service.import_curated(draft)
    assert service.validate().status == "failed"

    with pytest.raises(ValueError, match="must pass"):
        service.render()


def test_publication_render_refuses_stale_validation(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir, pdf_renderer=_fake_pdf_renderer)
    service.prepare()
    draft = tmp_path / "project.curated.draft.md"
    draft.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(draft)
    assert service.validate().status == "passed"
    (tmp_path / "outputs" / "latest" / "project.curated.md").write_text(
        "# Demo Project\n\nChanged after validation.\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="validation is missing or stale"):
        service.render()


def test_publication_review_is_stale_after_curated_change(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir, pdf_renderer=_fake_pdf_renderer)
    service.prepare()
    draft = tmp_path / "project.curated.draft.md"
    draft.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication for this project vertical.\n\n"
        "## Current And Planned State\n\n"
        "Current and planned work remains traceable to PROP-001.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(draft)
    service.validate()
    service.render()
    service.review(status="approved")
    (tmp_path / "outputs" / "latest" / "project.curated.md").write_text(
        "# Demo Project\n\nChanged.\n",
        encoding="utf-8",
    )

    status = service.status()

    assert next(stage for stage in status.stages if stage.name == "curated").status == "stale"
    assert status.review_status == "stale"
    assert status.approved_for_publication is False


def test_publication_review_requires_rendered_pdf(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir, pdf_renderer=_fake_pdf_renderer)
    service.prepare()
    draft = tmp_path / "project.curated.draft.md"
    draft.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(draft)
    service.validate()

    with pytest.raises(ValueError, match="PDF is missing or stale"):
        service.review(status="approved")


def test_publication_review_records_changes_requested(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir, pdf_renderer=_fake_pdf_renderer)
    service.prepare()
    draft = tmp_path / "project.curated.draft.md"
    draft.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication for this project vertical.\n\n"
        "## Current And Planned State\n\n"
        "Current and planned work remains traceable to PROP-001.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(draft)
    service.validate()
    service.render()

    review = service.review(status="changes_requested", notes=["Clarify scope."])
    status = service.status()

    assert review.status == "changes_requested"
    assert status.review_status == "changes_requested"
    assert status.approved_for_publication is False


def test_publication_owner_review_loop_can_reimport_and_approve(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir, pdf_renderer=_fake_pdf_renderer)
    service.prepare()
    first = tmp_path / "first-curated.md"
    first.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication for this project vertical.\n\n"
        "## Current And Planned State\n\n"
        "Current and planned work remains traceable to PROP-001.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(first)
    service.validate()
    service.render()
    service.review(status="changes_requested", notes=["Clarify the implementation boundary."])

    second = tmp_path / "second-curated.md"
    second.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication for this project vertical.\n\n"
        "## Current And Planned State\n\n"
        "Current implemented and planned work remains traceable to PROP-001, with pending gaps explicit.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(second)
    stale_status = service.status()
    assert stale_status.review_status == "stale"

    service.validate()
    service.render()
    service.review(status="approved")

    assert service.status().approved_for_publication is True


def test_publication_cascading_invalidation_for_profile_validation_and_pdf(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir, pdf_renderer=_fake_pdf_renderer)
    service.prepare()
    draft = tmp_path / "project.curated.draft.md"
    draft.write_text(
        "# Demo Project\n\n"
        "## Executive Summary\n\n"
        "Demo Project is the current canonical project publication for this project vertical.\n\n"
        "## Current And Planned State\n\n"
        "Current and planned work remains traceable to PROP-001.\n\n"
        "## Source Of Truth\n\n"
        "The `.p2p/` directory remains authoritative.\n",
        encoding="utf-8",
    )
    service.import_curated(draft)
    service.validate()
    service.render()
    service.review(status="approved")

    (tmp_path / "outputs" / "latest" / "publication-validation.yml").write_text("changed validation\n", encoding="utf-8")
    validation_changed = service.status()
    assert validation_changed.render_status == "stale"
    assert validation_changed.review_status == "stale"

    service.validate()
    service.render()
    service.review(status="approved")
    (tmp_path / "outputs" / "latest" / "project.pdf").write_bytes(b"%PDF-1.4\nchanged\n")
    pdf_changed = service.status()
    assert pdf_changed.render_status == "stale"
    assert pdf_changed.review_status == "stale"

    service.render()
    service.review(status="approved")
    (tmp_path / "outputs" / "latest" / "publication-profile.yml").write_text("changed profile\n", encoding="utf-8")
    profile_changed = service.status()
    assert next(stage for stage in profile_changed.stages if stage.name == "profile").status == "stale"
    assert profile_changed.validation_status == "stale"
    assert profile_changed.review_status == "stale"


def test_publication_import_requires_prepared_packet(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    draft = tmp_path / "draft.md"
    draft.write_text("# Curated\n", encoding="utf-8")

    with pytest.raises(ValueError, match="manifest is missing"):
        service.import_curated(draft)


def test_publication_import_rejects_sources_outside_project_root(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    outside = tmp_path.parent / "outside-curated.md"
    outside.write_text("# Outside\n", encoding="utf-8")

    with pytest.raises(ValueError, match="inside the project root"):
        service.import_curated(outside)


def test_publication_import_rejects_sources_under_p2p(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    source = tmp_path / ".p2p" / "curated.md"
    source.write_text("# Curated\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must not be under .p2p"):
        service.import_curated(source)


def test_publication_import_rejects_canonical_output_path(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    canonical = tmp_path / "outputs" / "latest" / "project.curated.md"
    canonical.write_text("# Curated\n", encoding="utf-8")

    with pytest.raises(ValueError, match="external curated draft path"):
        service.import_curated(canonical)


def test_publication_output_paths_are_fixed_under_outputs_latest(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    latest = (tmp_path / "outputs" / "latest").resolve()

    paths = service.paths()

    for output_path in (
        paths.source_export,
        paths.profile,
        paths.curator_input,
        paths.curated,
        paths.validation,
        paths.pdf,
        paths.review,
        paths.manifest,
    ):
        output_path.resolve().relative_to(latest)


def test_publication_import_rejects_stale_curator_packet(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    (tmp_path / "outputs" / "latest" / "curator-input.md").write_text("changed packet\n", encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text("# Curated\n", encoding="utf-8")

    with pytest.raises(ValueError, match="packet hash changed"):
        service.import_curated(draft)


def test_publication_import_rejects_changed_source_export_hash(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    (tmp_path / "outputs" / "latest" / "project.md").write_text("changed source export\n", encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text("# Curated\n", encoding="utf-8")

    with pytest.raises(ValueError, match="source export hash changed"):
        service.import_curated(draft)


def test_publication_import_rejects_changed_source_fingerprint(tmp_path: Path) -> None:
    proposal_dir = _write_project_state(tmp_path)
    service = _service(tmp_path, proposal_dir)
    service.prepare()
    (proposal_dir / "proposal.md").write_text(
        "# PROP-001 - Canonical Publication\n\n## Status\n\n`accepted`\n\n## Proposal\n\nChanged.\n",
        encoding="utf-8",
    )
    draft = tmp_path / "draft.md"
    draft.write_text("# Curated\n", encoding="utf-8")

    with pytest.raises(ValueError, match="P2P source fingerprint changed"):
        service.import_curated(draft)


def test_pdf_renderer_reports_optional_capability_when_weasyprint_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "weasyprint":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ValueError, match="p2p-engine\\[pdf\\]"):
        render_pdf_with_weasyprint("# Demo\n", tmp_path / "project.pdf", tmp_path)


def test_pdf_renderer_handles_publication_markdown_when_weasyprint_is_available(
    tmp_path: Path,
) -> None:
    pytest.importorskip("weasyprint")
    markdown = (
        "# Progetto Dimostrativo\n\n"
        "## Executive Summary\n\n"
        "Questo documento contiene testo italiano con accenti, caffe, città e responsabilità.\n\n"
        "## Tabella\n\n"
        "| Stato | Evidenza |\n"
        "| --- | --- |\n"
        "| corrente | PROP-001 |\n\n"
        "## Codice\n\n"
        "```text\n"
        "p2p project publish render\n"
        "```\n\n"
        + "\n\n".join(f"## Sezione {index}\n\nContenuto esteso per la pagina {index}." for index in range(1, 30))
    )
    output = tmp_path / "project.pdf"

    renderer = render_pdf_with_weasyprint(markdown, output, tmp_path)

    assert renderer == "weasyprint-neutral-v1"
    assert output.read_bytes().startswith(b"%PDF")
    assert output.stat().st_size > 1000

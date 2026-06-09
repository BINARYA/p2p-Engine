from __future__ import annotations

from pathlib import Path

from p2p_engine.core.project_verticals import ProjectReadinessReview, VerticalSectionReview
from p2p_engine.services.visible_project_export import VisibleProjectExportService


def _accepted(proposal_dir: Path) -> list[dict[str, object]]:
    return [
        {
            "proposal_id": "PROP-001",
            "title": "Visible Export",
            "status": "accepted",
            "feature_id": "visible-export",
            "path": proposal_dir,
            "source": ".p2p/proposals/PROP-001-visible-export",
        }
    ]


def test_visible_project_export_writes_latest_and_archives_previous(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    proposal_dir = p2p_dir / "proposals" / "PROP-001-visible-export"
    proposal_dir.mkdir(parents=True)
    (proposal_dir / "proposal.md").write_text(
        "# PROP-001 - Visible Export\n\n"
        "## Status\n\n"
        "`accepted`\n\n"
        "## Context\n\n"
        "A human-readable project definition is needed.\n\n"
        "## Goals\n\n"
        "- Write a visible project document.\n\n"
        "## Non-Goals\n\n"
        "- Do not replace P2P state.\n\n"
        "## Proposal\n\n"
        "Export a chaptered project definition.\n\n"
        "## Acceptance Criteria\n\n"
        "- outputs/latest/project.md exists.\n\n"
        "## Decision\n\n"
        "Accepted.\n",
        encoding="utf-8",
    )
    (proposal_dir / "risks.md").write_text("# Risks\n\nCompatibility must be preserved.\n", encoding="utf-8")

    service = VisibleProjectExportService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        project_name=lambda: "Demo Project",
        accepted_proposals=lambda: _accepted(proposal_dir),
    )

    first = service.export()
    assert first.latest_path == Path("outputs/latest/project.md")
    assert first.archived_path is None
    latest = tmp_path / first.latest_path
    assert latest.exists()
    assert "## Generated Metadata" in latest.read_text(encoding="utf-8")
    assert "source_of_truth: .p2p/" in latest.read_text(encoding="utf-8")

    latest.write_text("old generated output\n", encoding="utf-8")
    second = service.export()

    assert second.archived_path == Path("outputs/review-001")
    assert (tmp_path / "outputs" / "review-001" / "project.md").read_text(encoding="utf-8") == "old generated output\n"
    assert (tmp_path / "outputs" / "latest" / "project.md").exists()
    assert (tmp_path / "outputs" / "latest" / "exports").is_dir()

    status = service.status()
    assert status.latest_exists is True
    assert status.review_paths == [Path("outputs/review-001")]


def test_visible_project_export_can_include_vertical_readiness_review(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    proposal_dir = p2p_dir / "proposals" / "PROP-001-visible-export"
    proposal_dir.mkdir(parents=True)
    (proposal_dir / "proposal.md").write_text(
        "# PROP-001 - Visible Export\n\n## Status\n\n`accepted`\n\n## Proposal\n\nExport.\n",
        encoding="utf-8",
    )
    review = ProjectReadinessReview(
        active_vertical_id="social_impact_program_design",
        vertical_source="internal",
        fallback_used=False,
        sections=[
            VerticalSectionReview(
                section_id="measurement_reporting",
                title="Measurement And Reporting",
                status="covered",
                proposals=["PROP-001"],
                gaps=[],
                risks=[],
                questions=[],
            )
        ],
        unmapped_proposals=[],
        missing_capisaldi=[],
        generated_questions=[],
        suggested_next=[],
    )
    service = VisibleProjectExportService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        project_name=lambda: "Demo Project",
        accepted_proposals=lambda: _accepted(proposal_dir),
        project_readiness_review=lambda: review,
    )

    result = service.export()
    text = (tmp_path / result.latest_path).read_text(encoding="utf-8")

    assert "### Project Vertical Skeleton" in text
    assert "active_vertical: social_impact_program_design" in text
    assert "measurement_reporting: covered" in text

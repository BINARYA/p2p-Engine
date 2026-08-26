from __future__ import annotations

from pathlib import Path

from p2p_engine.core.contribution import ContributionType
from p2p_engine.core.proposal_artifact_state import (
    ProposalArtifactExpectation,
    ProposalArtifactStatus,
)
from p2p_engine.core.proposal_questions import ProposalQuestionPriority
from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.storage.filesystem import P2PWorkspace


def _snapshot_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _by_key(items: list[object], key: str):
    return next(item for item in items if getattr(item, "key") == key)


def _meaningful_text(label: str) -> str:
    return (
        f"# {label}\n\n"
        "This artifact contains enough concrete detail to count as meaningful "
        "evidence for the proposal review view and owner-facing status output.\n"
    )


def test_artifact_catalog_lists_logical_slots_for_reduced_footprint(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Review View", starter_id="empty")
    proposal = workspace.create_proposal_with_details(
        title="Reduced Footprint",
        problem="Reduced proposals should not need every possible artifact file.",
        proposal="Derive a logical view from current state and files.",
    )
    before = _snapshot_files(tmp_path)

    catalog = workspace.proposal_artifact_catalog(proposal.proposal_id)

    assert _snapshot_files(tmp_path) == before
    assert {item.key for item in catalog} >= {
        "proposal",
        "readiness",
        "open_questions",
        "findings",
        "alternatives",
        "impact_map",
        "related_proposals",
    }
    findings = _by_key(catalog, "findings")
    alternatives = _by_key(catalog, "alternatives")
    assert findings.path is None
    assert findings.source_hint == "none"
    assert findings.materialization_kind == "not_materialized"
    assert findings.provenance_confidence == "explicit"
    assert alternatives.expectation == ProposalArtifactExpectation.required_when_applicable
    assert alternatives.status == ProposalArtifactStatus.missing


def test_artifact_catalog_rejects_narrative_files_without_current_state(tmp_path: Path) -> None:
    documents = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    proposal = documents.create_with_details(
        title="Legacy Narrative",
        problem="Legacy proposals may already have narrative artifacts.",
    )
    proposal_dir = tmp_path / proposal.path
    (proposal_dir / "findings.md").write_text(_meaningful_text("Findings"), encoding="utf-8")
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\n- Which owner constraint should guide the next choice?\n",
        encoding="utf-8",
    )
    before = _snapshot_files(tmp_path)
    workspace = P2PWorkspace(tmp_path)

    try:
        workspace.proposal_artifact_catalog(proposal.proposal_id)
    except ValueError as exc:
        assert "missing artifact-state.yml" in str(exc)
    else:
        raise AssertionError("Missing current artifact state must be rejected")

    assert _snapshot_files(tmp_path) == before
    assert not (proposal_dir / "artifact-state.yml").exists()


def test_artifact_catalog_reports_imported_artifacts_from_current_files(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Review View", starter_id="empty")
    proposal = workspace.create_proposal_with_details(title="Imported Artifacts")

    workspace.import_proposal_artifact_content(
        proposal.proposal_id,
        "explore",
        artifacts={
            "findings.md": _meaningful_text("Findings"),
            "risks.md": _meaningful_text("Risks"),
        },
    )
    workspace.import_proposal_artifact_content(
        proposal.proposal_id,
        "impact",
        content="impact:\n  proposal: PROP-001\n  features:\n    - owner review view\n",
    )

    catalog = workspace.proposal_artifact_catalog(proposal.proposal_id)
    findings = _by_key(catalog, "findings")
    impact = _by_key(catalog, "impact_map")

    assert findings.status == ProposalArtifactStatus.satisfied
    assert findings.materialization_kind == "imported_file"
    assert "meaningful evidence" in findings.summary
    assert impact.status == ProposalArtifactStatus.satisfied
    assert impact.materialization_kind == "imported_file"


def test_full_view_separates_question_sources_and_preserves_files(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Review View", starter_id="empty")
    proposal = workspace.create_proposal_with_details(
        title="Question Groups",
        problem="Question-like data comes from multiple sources.",
        proposal="Render each source separately.",
        acceptance_criteria=["Owner questions and analytical questions stay separate."],
    )
    workspace.add_contribution(
        proposal.proposal_id,
        ContributionType.open_question,
        text="Which compatibility constraint should be challenged first?",
        relevance_hint="readiness",
        author="codex",
    )
    workspace.add_proposal_question(
        proposal.proposal_id,
        gap="owner_questions_resolution",
        question="Which owner decision is still needed before acceptance?",
        priority=ProposalQuestionPriority.high,
        rationale="Readiness needs owner input.",
        actor="codex",
    )
    proposal_dir = tmp_path / proposal.path
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\n- Should the legacy artifact stay visible?\n",
        encoding="utf-8",
    )
    before = _snapshot_files(tmp_path)

    view = workspace.proposal_full_view(proposal.proposal_id)

    assert _snapshot_files(tmp_path) == before
    assert view.core_sections["problem"] == "Question-like data comes from multiple sources."
    assert len(view.questions.owner_questions) == 1
    assert len(view.questions.analytical_open_questions) == 1
    assert len(view.questions.narrative_question_artifacts) == 1
    assert view.questions.owner_questions[0].question_id == "Q001"
    assert view.questions.analytical_open_questions[0].contribution_id == "C001"
    assert view.questions.narrative_question_artifacts[0].key == "open_questions"


def test_readiness_and_artifact_status_remain_separate_when_they_diverge(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Review View")
    proposal = workspace.create_proposal_with_details(
        title="Divergent Status",
        problem="Readiness and artifact status answer different questions.",
    )
    workspace.set_proposal_artifact_state(
        proposal.proposal_id,
        "impact_map",
        status=ProposalArtifactStatus.not_applicable,
        reason="No cross-proposal impact.",
        actor="codex",
    )
    workspace.write_proposal_readiness(
        proposal.proposal_id,
        {
            "status": "assessed",
            "profile_id": "default-readiness-v0.1",
            "profile_version": "0.1",
            "computed_score": 68,
            "computed_label": "weak",
            "confidence": "low",
            "failed_gates": ["impact_overlap_analysis"],
            "missing": ["impact_overlap_analysis"],
            "suggested_next": ["p2p impact prompt PROP-001"],
            "criteria": {},
        },
    )

    view = workspace.proposal_full_view(proposal.proposal_id)
    impact = _by_key(view.artifact_status, "impact_map")

    assert view.readiness.status == "assessed"
    assert view.readiness.failed_gates == ["impact_overlap_analysis"]
    assert impact.status == ProposalArtifactStatus.not_applicable
    assert impact.status != ProposalArtifactStatus.missing


def test_full_view_clips_long_narrative_artifact_summaries(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Review View", starter_id="empty")
    proposal = workspace.create_proposal_with_details(title="Long Narrative")
    long_text = "# Findings\n\n" + ("Detailed owner-visible evidence. " * 30)
    (tmp_path / proposal.path / "findings.md").write_text(long_text, encoding="utf-8")

    view = workspace.proposal_full_view(proposal.proposal_id)
    findings = _by_key(view.narrative_artifacts, "findings")

    assert len(findings.summary) <= 240
    assert findings.summary.endswith("...")

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.proposal_decision_events import ProposalDecisionEventType
from p2p_engine.foundation.markdown import replace_section
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import ensure_global_scope


def _apply(
    workspace: P2PWorkspace,
    proposal_id: str,
    event_type: ProposalDecisionEventType,
    reason: str,
) -> object:
    ensure_global_scope(workspace, proposal_id)
    service = workspace._proposal_decision_service()
    preview = service.preview(
        service.request(
            proposal_id=proposal_id,
            event_type=event_type,
            reason=reason,
            actor_id="owner",
        )
    )
    return service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )


def _accepted_workspace(root: Path) -> tuple[P2PWorkspace, str, Path]:
    workspace = P2PWorkspace(root)
    workspace.init_project("Consumer Convergence", owner="owner")
    proposal = workspace.create_proposal_with_details(
        "Lifecycle source",
        problem="Consumers need one authority.",
        proposal="Use the decision ledger.",
        acceptance_criteria=["Consumers agree."],
    )
    _apply(
        workspace,
        proposal.proposal_id,
        ProposalDecisionEventType.accepted,
        "Accepted source.",
    )
    return workspace, proposal.proposal_id, root / proposal.path


def test_proposal_views_and_registry_use_ledger_when_projection_status_drifts(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _accepted_workspace(tmp_path)
    proposal_path = proposal_dir / "proposal.md"
    proposal_path.write_text(
        replace_section(
            proposal_path.read_text(encoding="utf-8"),
            "Status",
            "`rejected`",
        ),
        encoding="utf-8",
    )

    shown = workspace.show_proposal(proposal_id)
    summary = workspace.proposal_summaries()[0]
    proposal_record = workspace._registry_record_builder_service().proposal_records()[0]
    decision_record = workspace._registry_record_builder_service().decision_records(
        [proposal_record]
    )[0]
    validation = workspace.validate()

    assert shown.status == "accepted"
    assert shown.head_event_id
    assert shown.event_count == 1
    assert shown.active is True
    assert shown.lifecycle_diagnostics == (
        "P2P362_DECISION_PROJECTION_DIVERGENCE: proposal.md",
    )
    assert summary.status == "accepted"
    assert summary.active is True
    assert proposal_record["status"] == "accepted"
    assert proposal_record["head_event_id"] == shown.head_event_id
    assert proposal_record["event_count"] == 1
    assert "events" not in proposal_record
    assert decision_record["outcome"] == "accepted"
    assert decision_record["decision_semantic_sha256"]
    assert any(
        finding.code == "P2P362_DECISION_PROJECTION_DIVERGENCE"
        and finding.path.name == "proposal.md"
        for finding in validation.findings
    )
    assert not any(
        finding.code == "P2P112_STATUS_MISMATCH"
        for finding in validation.findings
    )


def test_decided_proposal_semantics_cannot_be_rewritten_in_place(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _accepted_workspace(tmp_path)
    before = (proposal_dir / "proposal.md").read_bytes()

    with pytest.raises(ValueError, match="create a linked proposal"):
        workspace.update_proposal(
            proposal_id,
            proposal="A materially different direction.",
        )

    assert (proposal_dir / "proposal.md").read_bytes() == before


def test_revocation_deactivates_views_but_preserves_change_spec_and_work(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _accepted_workspace(tmp_path)
    change = workspace.create_change_set(proposal_id, "Dependent delivery")
    workspace.refresh_software_spec(change.change_id)
    workspace.export_software_spec(change.change_id, "generic")
    work = workspace.create_work_plan(change.change_id, "generic")
    change_dir = tmp_path / change.path
    spec_dir = (
        tmp_path / ".p2p" / "outputs" / "software-spec" / change.change_id
    )
    work_dir = tmp_path / work.path
    before_change = {
        path.relative_to(change_dir).as_posix(): path.read_bytes()
        for path in change_dir.rglob("*")
        if path.is_file()
    }
    before_spec = {
        path.relative_to(spec_dir).as_posix(): path.read_bytes()
        for path in spec_dir.rglob("*")
        if path.is_file()
    }
    before_work = {
        path.relative_to(work_dir).as_posix(): path.read_bytes()
        for path in work_dir.rglob("*")
        if path.is_file()
    }

    _apply(
        workspace,
        proposal_id,
        ProposalDecisionEventType.revoked,
        "The source direction is no longer authoritative.",
    )

    assert workspace.show_proposal(proposal_id).status == "revoked"
    assert workspace.proposal_summaries()[0].ever_active is True
    assert (
        workspace._registry_record_builder_service().accepted_proposals()
        == []
    )
    detail = workspace.show_change_set(change.change_id)
    assert detail.status == "proposed"
    assert any(
        "is now revoked" in diagnostic
        for diagnostic in detail.source_authority_diagnostics
    )
    lifecycle = workspace.software_spec_lifecycle(
        "implementation_spec",
        change_id=change.change_id,
    )
    assert lifecycle.blockers[0].code == "source_decision_inactive"
    spec_status = next(
        item
        for item in workspace.software_spec_statuses()
        if item.change_id == change.change_id
    )
    assert spec_status.freshness.value == "stale"
    assert (
        ".p2p/proposals/PROP-001-lifecycle-source/decision-events.yml"
        in spec_status.changed_sources
    )
    with pytest.raises(ValueError, match="no current active bound authority"):
        workspace.create_work_plan(change.change_id, "generic")
    with pytest.raises(ValueError, match="no current active decision authority"):
        workspace.create_change_set(proposal_id, "Must be blocked")

    assert {
        path.relative_to(change_dir).as_posix(): path.read_bytes()
        for path in change_dir.rglob("*")
        if path.is_file()
    } == before_change
    assert {
        path.relative_to(spec_dir).as_posix(): path.read_bytes()
        for path in spec_dir.rglob("*")
        if path.is_file()
    } == before_spec
    assert {
        path.relative_to(work_dir).as_posix(): path.read_bytes()
        for path in work_dir.rglob("*")
        if path.is_file()
    } == before_work


def test_new_change_and_work_bind_current_decision_head_and_fingerprint(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _accepted_workspace(tmp_path)
    lifecycle = workspace.proposal_decision_status(proposal_id)
    change = workspace.create_change_set(proposal_id, "Bound delivery")
    change_dir = tmp_path / change.path
    included = yaml.safe_load(
        (change_dir / "included-decisions.yml").read_text(encoding="utf-8")
    )["included_decisions"][0]
    workspace.refresh_software_spec(change.change_id)
    workspace.export_software_spec(change.change_id, "generic")
    work = workspace.create_work_plan(change.change_id, "generic")
    work_manifest = yaml.safe_load(
        (tmp_path / work.path / "manifest.yml").read_text(encoding="utf-8")
    )

    assert included["head_event_id"] == lifecycle.head_event_id
    assert (
        included["decision_semantic_sha256"]
        == lifecycle.decision_semantic_sha256
    )
    assert included["ledger_file"].endswith("/decision-events.yml")
    assert work_manifest["source"]["decisions"] == [
        {
            "proposal": proposal_id,
            "head_event_id": lifecycle.head_event_id,
            "decision_semantic_sha256": (
                lifecycle.decision_semantic_sha256
            ),
        }
    ]

    proposal_records = (
        workspace._registry_record_builder_service().proposal_records()
    )
    artifact_records = (
        workspace._registry_record_builder_service().artifact_records(
            proposal_records,
            workspace._registry_record_builder_service().change_records(),
        )
    )
    roles = {
        record["artifact_type"]: record["authority_role"]
        for record in artifact_records
        if record["owner_type"] == "proposal"
    }
    assert roles["decision-events.yml"] == "canonical_decision_ledger"
    assert roles["decision.md"] == "decision_projection"


def test_export_and_publication_fingerprint_retain_inactive_rationale(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _accepted_workspace(tmp_path)
    publication = workspace._project_publication_service()
    before = publication.source_fingerprint()

    _apply(
        workspace,
        proposal_id,
        ProposalDecisionEventType.revoked,
        "No longer the current direction.",
    )

    markdown = (
        workspace._visible_project_export_service()._render_project_markdown()
    )
    after = publication.source_fingerprint()

    assert "## Historical And Inactive Proposal Decisions" in markdown
    assert f"- {proposal_id}" in markdown
    assert "classification: previously_active" in markdown
    assert "effective_state: revoked" in markdown
    assert "No longer the current direction." in markdown
    assert before.sha256 != after.sha256
    assert any(
        item["path"].endswith("/decision-events.yml")
        for item in after.inputs
    )

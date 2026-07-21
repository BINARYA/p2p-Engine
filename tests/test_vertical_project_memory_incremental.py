from __future__ import annotations

from pathlib import Path

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.proposal_decision_events import ProposalDecisionEventType
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


def _workspace(root: Path) -> tuple[P2PWorkspace, str]:
    workspace = P2PWorkspace(root)
    workspace.init_project(
        "Incremental memory",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    proposal = workspace.create_proposal_with_details(
        "Data model",
        problem="Domain entities need a lifecycle.",
        goals=["Define domain entities."],
        non_goals=["Track implementation."],
        proposal="Define the domain data model.",
    )
    record_decision(
        workspace,
        proposal.proposal_id,
        DecisionOutcome.accepted,
        "The data model is required.",
        "owner",
    )
    _apply_coverage(workspace, proposal.proposal_id, "data_model")
    workspace.refresh_vertical_project_memory()
    return workspace, proposal.proposal_id


def _apply_coverage(workspace: P2PWorkspace, proposal_id: str, section_id: str):
    payload = {
        "vertical_coverage": {
            "schema_version": 2,
            "proposal_id": proposal_id,
            "vertical_id": "software_project",
            "sections": [
                {
                    "id": section_id,
                    "relevance": "direct",
                    "rationale": f"Applies to {section_id}.",
                    "source": "owner_review",
                    "provenance": {"evidence": ["proposal.md"]},
                }
            ],
            "provenance": {
                "operation_id": f"proposal-vertical-coverage:{proposal_id}",
                "actor": "owner",
                "authority": "owner_confirmed",
                "source": "owner_review",
            },
        }
    }
    preview = workspace.preview_proposal_vertical_coverage(
        proposal_id,
        payload,
        actor="owner",
    )
    result = workspace.apply_proposal_vertical_coverage(
        proposal_id,
        payload,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )
    assert result.status == "applied"
    return result


def _assert_incremental_equals_full(
    workspace: P2PWorkspace,
    changed_paths: list[str],
) -> object:
    service = workspace._vertical_project_memory_service()
    incremental, impact = service.build_incremental(changed_paths)
    full = service.build_full()
    assert not impact.full_rebuild
    assert incremental.candidates == full.candidates
    assert incremental.view == full.view
    return impact


def test_proposal_edit_rebuilds_only_exact_semantic_sections(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    proposal_path = workspace._proposal_document_service().find_dir(proposal_id) / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8").replace(
            "Domain entities need a lifecycle.",
            "Domain entities need an explicit lifecycle.",
        ),
        encoding="utf-8",
    )

    impact = _assert_incremental_equals_full(
        workspace,
        [proposal_path.relative_to(tmp_path).as_posix()],
    )

    assert proposal_id in impact.proposal_ids
    assert "data_model" in impact.section_ids


def test_coverage_move_rebuilds_previous_and_new_sections(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    _apply_coverage(workspace, proposal_id, "workflows_use_cases")
    coverage_path = (
        workspace._proposal_document_service().find_dir(proposal_id)
        / "vertical-coverage.yml"
    )

    impact = _assert_incremental_equals_full(
        workspace,
        [coverage_path.relative_to(tmp_path).as_posix()],
    )

    assert {"data_model", "workflows_use_cases"} <= set(impact.section_ids)


def test_decision_revocation_moves_active_contribution_to_history(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    decision = workspace._proposal_decision_service()
    request = decision.request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.revoked,
        reason="Direction is no longer active.",
        actor_id="owner",
        source_head_event_id=workspace.proposal_decision_status(proposal_id).head_event_id,
    )
    preview = decision.preview(request)
    applied = decision.apply(
        request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    assert applied.status == "applied"
    ledger = workspace._proposal_document_service().find_dir(proposal_id) / "decision-events.yml"

    _assert_incremental_equals_full(
        workspace,
        [ledger.relative_to(tmp_path).as_posix()],
    )


def test_non_authoritative_delivery_change_has_no_projection_impact(tmp_path: Path) -> None:
    workspace, _ = _workspace(tmp_path)
    service = workspace._vertical_project_memory_service()
    impact = service.impact_classifier.classify(
        [".p2p/changes/CHANGE-001/change.md"],
        prior_view=workspace.vertical_project_memory(allow_fallback=False),
    )

    assert not impact.full_rebuild
    assert not impact.aggregate_changed or not impact.scopes
    assert impact.proposal_ids == ()


def test_post_commit_incremental_refresh_updates_atomic_generation(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    proposal_path = workspace._proposal_document_service().find_dir(proposal_id) / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8").replace(
            "Domain entities need a lifecycle.",
            "Domain entities need a governed lifecycle.",
        ),
        encoding="utf-8",
    )
    relative = proposal_path.relative_to(tmp_path).as_posix()

    result = workspace._vertical_project_memory_service().refresh_incremental(
        [relative],
        typed_proposal_id=proposal_id,
    )

    assert result.state == "updated"
    assert "data_model" in result.affected_sections
    assert workspace.vertical_project_memory_status().state == "current"
    full = workspace._vertical_project_memory_service().build_full()
    assert all(
        (tmp_path / path).read_bytes() == content
        for path, content in full.candidates.items()
    )


def test_incremental_refresh_refuses_unreported_source_drift(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    proposal_dir = workspace._proposal_document_service().find_dir(proposal_id)
    proposal_path = proposal_dir / "proposal.md"
    decision_path = proposal_dir / "decision.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8") + "\nUnreported change.\n",
        encoding="utf-8",
    )
    decision_path.write_text(
        decision_path.read_text(encoding="utf-8") + "\nReported change.\n",
        encoding="utf-8",
    )

    result = workspace._vertical_project_memory_service().refresh_incremental(
        [decision_path.relative_to(tmp_path).as_posix()],
        typed_proposal_id=proposal_id,
    )

    assert result.state == "stale"
    assert "proposal.md" in result.reason


def test_definition_patch_rebuilds_exact_section_and_matches_full(tmp_path: Path) -> None:
    workspace, _ = _workspace(tmp_path)
    patch = tmp_path / "definition-patch.yml"
    patch.write_text(
        "project_definition_patch:\n"
        "  schema_version: 1\n"
        "  actor: owner\n"
        "  operations:\n"
        "    - op: set_field\n"
        "      section_id: data_model\n"
        "      field_id: domain_entities\n"
        "      value: Proposal and decision entities.\n"
        "      provenance:\n"
        "        source: owner_answer\n",
        encoding="utf-8",
    )
    preview = workspace.preview_project_definition_update(patch, actor="owner")
    applied = workspace.apply_project_definition_update(
        patch,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )
    assert applied.status == "applied"
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"

    candidate, impact = workspace._vertical_project_memory_service().build_incremental(
        [definition_path.relative_to(tmp_path).as_posix()],
        typed_section_ids=["data_model"],
    )
    full = workspace._vertical_project_memory_service().build_full()

    assert not impact.full_rebuild
    assert impact.section_ids == ("data_model",)
    assert candidate.candidates == full.candidates

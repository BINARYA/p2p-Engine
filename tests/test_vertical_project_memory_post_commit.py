from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.core.proposal_decision_events import ProposalDecisionEventType
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.test_vertical_project_memory_incremental import _apply_coverage, _workspace


def _derived_state(payload: dict[str, object]) -> str:
    update = payload["vertical_project_memory"]
    assert isinstance(update, dict)
    return str(update["state"])


def test_decision_apply_updates_current_memory_after_canonical_commit(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    request = workspace._proposal_decision_service().request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.revoked,
        reason="The direction is no longer authoritative.",
        actor_id="owner",
        source_head_event_id=workspace.proposal_decision_status(proposal_id).head_event_id,
    )
    preview = workspace.preview_proposal_decision(request)

    result = workspace.apply_proposal_decision(
        request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert result.mutation is not None
    assert _derived_state(dict(result.mutation.derived_updates)) == "updated"
    assert workspace.vertical_project_memory_status().state == "current"
    section = next(
        item
        for item in workspace.vertical_project_memory(allow_fallback=False).sections
        if item.section_id == "data_model"
    )
    assert not section.active_contributions
    assert [item.proposal_id for item in section.historical_contributions] == [proposal_id]


def test_derived_failure_does_not_rollback_decision_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    memory_service = workspace._vertical_project_memory_service()
    original_refresh = memory_service.refresh_incremental

    def fail_refresh(*args, **kwargs):
        raise RuntimeError("injected derived failure")

    monkeypatch.setattr(memory_service, "refresh_incremental", fail_refresh)
    request = workspace._proposal_decision_service().request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.revoked,
        reason="The direction is no longer authoritative.",
        actor_id="owner",
        source_head_event_id=workspace.proposal_decision_status(proposal_id).head_event_id,
    )
    preview = workspace.preview_proposal_decision(request)

    result = workspace.apply_proposal_decision(
        request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert result.mutation is not None
    assert _derived_state(dict(result.mutation.derived_updates)) == "failed"
    assert workspace.proposal_decision_status(proposal_id).head_event_type == (
        ProposalDecisionEventType.revoked
    )
    assert workspace.vertical_project_memory_status().state == "stale"

    monkeypatch.setattr(memory_service, "refresh_incremental", original_refresh)
    assert workspace.refresh_vertical_project_memory().status == "applied"
    assert workspace.vertical_project_memory_status().state == "current"


def test_coverage_apply_reports_incremental_update(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)

    result = _apply_coverage(workspace, proposal_id, "workflows_use_cases")

    assert _derived_state(dict(result.derived_updates)) == "updated"
    assert workspace.vertical_project_memory_status().state == "current"


def test_question_and_convergence_apply_keep_memory_current(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Question memory", owner="owner", vertical_id="base_project")
    workspace.refresh_vertical_project_memory()
    question = workspace.next_project_question()
    assert question is not None

    answered = workspace.answer_project_question(
        question.question_id,
        values={"value": "Owner supplied value"},
        actor="owner",
        expected_revision=question.revision,
    )
    assert _derived_state(dict(answered.mutation.derived_updates)) == "updated"

    preview = workspace.preview_project_readiness_convergence(
        [question.question_id],
        actor="owner",
    )
    applied = workspace.apply_project_readiness_convergence(
        [question.question_id],
        actor="owner",
        preview_token=preview.preview.preview_token,
        confirm=True,
    )

    assert applied.status == "applied"
    assert _derived_state(dict(applied.mutation.derived_updates)) == "updated"
    assert workspace.vertical_project_memory_status().state == "current"


def test_vertical_selection_reports_stale_instead_of_hidden_full_rebuild(
    tmp_path: Path,
) -> None:
    workspace, _ = _workspace(tmp_path)

    selected = workspace.select_project_vertical("base_project", actor="owner")

    assert _derived_state(dict(selected.derived_updates)) == "stale"
    assert workspace.vertical_project_memory_status().state == "stale"
    stale = workspace.vertical_project_memory(allow_fallback=False, allow_stale=True)
    assert stale.vertical_id == "software_project"
    assert stale.source == "stale_last_known"

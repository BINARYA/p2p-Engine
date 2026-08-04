from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from p2p_engine.core.proposal_decision_events import ProposalDecisionEventType
from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Demo Project", project_domain="software")
    return workspace


def _apply_decision(
    workspace: P2PWorkspace,
    proposal_id: str,
    event_type: ProposalDecisionEventType,
    reason: str,
) -> object:
    service = workspace._proposal_decision_service()
    values: dict[str, object] = {}
    if event_type == ProposalDecisionEventType.reinstated:
        history = service.history(proposal_id, limit=20)
        accepted = next(
            event
            for event in history.items
            if event.event_type
            in {
                ProposalDecisionEventType.accepted,
                ProposalDecisionEventType.accepted_with_changes,
            }
        )
        revoked = history.items[-1]
        values = {
            "affected_event_id": accepted.event_id,
            "revocation_event_id": revoked.event_id,
        }
    preview = service.preview(
        service.request(
            proposal_id=proposal_id,
            event_type=event_type,
            reason=reason,
            actor_id="owner",
            **values,
        )
    )
    return service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )


def test_next_action_service_manages_curated_lifecycle(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._next_action_service()

    action = service.add(
        kind="verify_integration",
        target="mcp-client",
        priority="high",
        reason="Verify real MCP client setup.",
        command="p2p-mcp-server --root /path/to/project",
    )
    listed = service.list(limit=1)
    result = service.complete(action.action_id, "Verified successfully.")

    assert action.action_id == "NEXT-001"
    assert listed[0].kind == "verify_integration"
    assert listed[0].source == ".p2p/project/next-actions.yml"
    assert result["action"]["status"] == "completed"
    assert result["path"] == ".p2p/project/next-actions-log.yml"
    active = yaml.safe_load((tmp_path / ".p2p" / "project" / "next-actions.yml").read_text(encoding="utf-8"))
    log = yaml.safe_load((tmp_path / ".p2p" / "project" / "next-actions-log.yml").read_text(encoding="utf-8"))
    assert active["next_actions"] == []
    assert log["next_action_log"][0]["id"] == "NEXT-001"
    assert log["next_action_log"][0]["closed_reason"] == "Verified successfully."


def test_next_action_service_refreshes_and_dedupes_generated_actions(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._next_action_service()
    service.add(
        kind="refresh_registry",
        target="registries",
        priority="medium",
        reason="Curated registry refresh.",
    )

    refreshed = service.refresh()
    actions = service.list()
    refresh_actions = [
        action for action in actions if action.kind == "refresh_registry" and action.target == "registries"
    ]

    assert refreshed["active_curated"] == 1
    assert refreshed["generated"] >= 1
    assert len(refresh_actions) == 1
    assert refresh_actions[0].source == ".p2p/project/next-actions.yml"


def test_next_action_service_prioritizes_active_choice_blockers(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Governance Model")
    _apply_decision(
        workspace,
        "PROP-001",
        ProposalDecisionEventType.accepted,
        "Needed.",
    )
    workspace.create_change_set("PROP-001", "Governance Model")
    workspace.update_change_set_status("CHANGE-001", "planned")
    workspace.create_choice(
        "Governance Scope",
        ["Minimal governance", "Full governance"],
        related=["PROP-001"],
    )
    workspace.block_choice(
        "CHOICE-001",
        target="CHANGE-001",
        target_type="change",
        reason="Governance scope must be decided first.",
    )

    action = workspace._next_action_service().list(limit=1)[0]

    assert action.action_id == "NEXT-BLOCKER-001"
    assert action.priority == "high"
    assert action.kind == "resolve_choice"
    assert action.target == "CHOICE-001"
    assert "blocks change CHANGE-001" in action.reason


def test_next_actions_distinguish_project_choices_from_proposal_local_votes(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Local Vote")
    workspace.record_vote(
        proposal.proposal_id,
        choice="A",
        reason="Proposal-local preference only.",
        voter="owner",
        role="owner",
    )

    actions = workspace._next_action_service().list()

    assert not any(
        action.kind == "resolve_choice" and action.target.startswith("CHOICE-PROP-")
        for action in actions
    )
    assert not any(
        node.node_id.startswith("CHOICE-PROP-")
        for node in workspace.decision_context_index().nodes
    )


def test_next_actions_use_concrete_project_question_and_apply_operations(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Readiness Actions", owner="owner", vertical_id="base_project")
    question = workspace.next_project_question()
    assert question is not None

    unanswered_actions = workspace._next_action_service().list()
    assert any(
        item.kind == "project_question_answer" and item.target == question.question_id
        for item in unanswered_actions
    )

    workspace.answer_project_question(
        question.question_id,
        values={"value": "Owner answer"},
        actor="owner",
        expected_revision=question.revision,
    )
    answered_actions = workspace._next_action_service().list()
    assert any(
        item.kind == "project_question_apply" and item.target == question.question_id
        for item in answered_actions
    )
    assert not any(item.kind == "review_project_readiness" for item in answered_actions)


def test_next_actions_resolve_only_open_normalized_project_choices(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    choice = workspace.create_choice("Project Choice", ["A", "B"])

    open_actions = workspace._next_action_service().list()
    workspace.decide_choice(choice.choice_id, "A", "A is selected.", "owner")
    decided_actions = workspace._next_action_service().list()

    assert any(
        action.kind == "resolve_choice" and action.target == choice.choice_id
        for action in open_actions
    )
    assert not any(
        action.kind == "resolve_choice" and action.target == choice.choice_id
        for action in decided_actions
    )


def test_decided_choice_with_missing_target_has_no_active_edge_or_action(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    choice = workspace.create_choice("Missing Target Choice", ["A", "B"])
    workspace.decide_choice(choice.choice_id, "A", "A is selected.", "owner")
    choice_dir = tmp_path / choice.path
    (choice_dir / "links.yml").write_text(
        "related_proposals:\n"
        "  - proposal: PROP-999\n"
        "    relationship: references\n",
        encoding="utf-8",
    )

    index = workspace.decision_context_index()
    actions = workspace._next_action_service().list()

    assert any(
        diagnostic.code == "DC-RELATION-INVALID-TARGET"
        and diagnostic.target_id == "PROP-999"
        for diagnostic in index.diagnostics
    )
    assert not any(relation.target_id == "PROP-999" for relation in index.relations)
    assert not any(action.target == choice.choice_id for action in actions)


def test_next_actions_use_normalized_change_proposal_relationships(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Change Relationship")
    _apply_decision(
        workspace,
        proposal.proposal_id,
        ProposalDecisionEventType.accepted,
        "Needed.",
    )
    change = workspace.create_change_set(proposal.proposal_id, "Change Relationship")
    workspace.update_change_set_status(change.change_id, "planned")

    action = next(
        action
        for action in workspace._next_action_service().list()
        if action.kind == "continue_change"
    )

    assert action.target == change.change_id
    assert f"Included proposals: {proposal.proposal_id}." in action.reason


def test_next_actions_include_every_active_change_set(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    change_ids: list[str] = []
    for title in ("First active change", "Second active change"):
        proposal = workspace.create_proposal(title)
        _apply_decision(
            workspace,
            proposal.proposal_id,
            ProposalDecisionEventType.accepted,
            "Needed.",
        )
        change = workspace.create_change_set(proposal.proposal_id, title)
        change_ids.append(change.change_id)

    actions = [
        action
        for action in workspace._next_action_service().list()
        if action.kind == "continue_change"
    ]

    assert [action.target for action in actions] == change_ids
    assert [action.action_id for action in actions] == [
        f"NEXT-CHANGE-{change_id}" for change_id in change_ids
    ]


def test_next_change_actions_use_registry_authority_stable_order_and_ids(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._next_action_service()
    empty_index = replace(
        workspace.decision_context_index(),
        nodes=(),
        relations=(),
    )
    records = [
        {"id": "CHANGE-009", "status": "custom_active"},
        {"id": "CHANGE-006", "status": "completed"},
        {"id": "CHANGE-004", "status": "in_progress"},
        {"id": "", "status": "planned"},
        {"id": "CHANGE-003", "status": "blocked"},
        {"id": "CHANGE-008", "status": "cancelled"},
        {"id": "CHANGE-001", "status": "planned"},
        {"id": "CHANGE-005", "status": "in_review"},
        {"id": "CHANGE-007", "status": "superseded"},
        {"id": "CHANGE-002", "status": "implementation_ready"},
    ]

    def listed(change_records: list[dict[str, str]]) -> list[object]:
        actions = service.list(
            context_snapshot={
                "change_statuses": change_records,
                "decision_context_index": empty_index,
                "registry_status": workspace.registry_status(),
            }
        )
        return [action for action in actions if action.kind == "continue_change"]

    first = listed(records)
    reordered = listed(list(reversed(records)))

    assert [action.target for action in first] == [
        "CHANGE-003",
        "CHANGE-001",
        "CHANGE-002",
        "CHANGE-004",
        "CHANGE-005",
        "CHANGE-009",
    ]
    assert [action.action_id for action in first] == [
        f"NEXT-CHANGE-{action.target}" for action in first
    ]
    assert [
        (action.action_id, action.target, action.priority)
        for action in reordered
    ] == [
        (action.action_id, action.target, action.priority)
        for action in first
    ]
    assert first[-1].priority == "medium"
    assert "custom_active" in first[-1].reason
    assert "Included proposals:" not in first[-1].reason


def test_next_change_actions_preserve_curated_dedupe_and_complete_refresh_count(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    changes = []
    for title in ("First curated target", "Second generated target"):
        proposal = workspace.create_proposal(title)
        _apply_decision(
            workspace,
            proposal.proposal_id,
            ProposalDecisionEventType.accepted,
            "Needed.",
        )
        changes.append(workspace.create_change_set(proposal.proposal_id, title))
    workspace.refresh_registries()
    service = workspace._next_action_service()
    curated = service.add(
        kind="continue_change",
        target=changes[0].change_id,
        reason="Owner-curated Change Set action.",
        command=f"p2p change tasks {changes[0].change_id}",
    )

    actions = [
        action for action in service.list() if action.kind == "continue_change"
    ]

    assert [action.target for action in actions] == [
        changes[0].change_id,
        changes[1].change_id,
    ]
    assert actions[0].action_id == curated.action_id
    assert actions[0].source == ".p2p/project/next-actions.yml"
    assert actions[1].action_id == f"NEXT-CHANGE-{changes[1].change_id}"

    path = tmp_path / ".p2p" / "project" / "next-actions.yml"
    before = path.read_bytes()
    expected_generated = len(
        service._generated_actions(None, workspace.decision_context_index())
    )
    refreshed = service.refresh()

    assert refreshed["generated"] == expected_generated
    assert path.read_bytes() == before
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert [record["id"] for record in payload["next_actions"]] == [
        curated.action_id
    ]


def test_next_action_limit_applies_after_complete_composition_and_dedupe(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    for title in ("First limit target", "Second limit target", "Third limit target"):
        proposal = workspace.create_proposal(title)
        _apply_decision(
            workspace,
            proposal.proposal_id,
            ProposalDecisionEventType.accepted,
            "Needed.",
        )
        workspace.create_change_set(proposal.proposal_id, title)
    service = workspace._next_action_service()

    complete = service.list()

    assert service.list(limit=0) == []
    assert service.list(limit=1) == complete[:1]
    assert service.list(limit=3) == complete[:3]
    assert service.list(limit=999) == complete


def test_historical_conflicts_and_legacy_projection_do_not_create_choice_actions(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    first = workspace.create_proposal("Current Direction")
    second = workspace.create_proposal("Historical Direction")
    _apply_decision(
        workspace,
        second.proposal_id,
        ProposalDecisionEventType.rejected,
        "Historical.",
    )
    (tmp_path / ".p2p" / "project" / "conflicts.yml").write_text(
        "conflicts:\n"
        f"  - proposals: [{first.proposal_id}, {second.proposal_id}]\n",
        encoding="utf-8",
    )
    registries = tmp_path / ".p2p" / "registries"
    registries.mkdir(exist_ok=True)
    (registries / "relations.yml").write_text(
        "relations:\n"
        "  - source: CHOICE-FAKE\n"
        "    target: PROP-001\n"
        "    type: blocks\n",
        encoding="utf-8",
    )

    actions = workspace._next_action_service().list()
    index = workspace.decision_context_index()

    assert not any(action.kind == "resolve_choice" for action in actions)
    assert not any(source.path.endswith("registries/relations.yml") for source in index.sources)


def test_next_actions_fall_back_to_project_review_when_no_semantic_work_exists(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    workspace.refresh_registries()

    actions = workspace._next_action_service().list()

    assert [(action.kind, action.target) for action in actions] == [
        ("refresh_derived_state", "project_projections"),
        ("review_project", "project"),
    ]


def test_next_action_service_rejects_invalid_payload_shapes(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._next_action_service()
    next_actions_path = tmp_path / ".p2p" / "project" / "next-actions.yml"
    next_actions_path.write_text("next_actions: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="next_actions must be a list"):
        service.add(kind="verify", target="target", reason="Invalid active payload.")

    next_actions_path.write_text(
        "next_actions:\n"
        "  - id: NEXT-001\n"
        "    kind: verify\n"
        "    reason: Valid active payload.\n",
        encoding="utf-8",
    )
    (tmp_path / ".p2p" / "project" / "next-actions-log.yml").write_text(
        "next_action_log: {}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="next_action_log must be a list"):
        service.retire("NEXT-001", "Invalid log payload.")


def test_revoked_decision_generates_stable_remediation_with_curated_precedence(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Revoked source")
    _apply_decision(
        workspace,
        proposal.proposal_id,
        ProposalDecisionEventType.accepted,
        "Initially accepted.",
    )
    change = workspace.create_change_set(proposal.proposal_id, "Dependent change")
    workspace.update_change_set_status(change.change_id, "planned")
    workspace.update_change_set_status(change.change_id, "implementation_ready")
    workspace.update_change_set_status(change.change_id, "in_progress")
    service = workspace._next_action_service()
    service.add(
        kind="review_revoked_change",
        target=change.change_id,
        priority="critical",
        reason="Owner-curated remediation.",
        command=f"p2p change show {change.change_id}",
    )
    _apply_decision(
        workspace,
        proposal.proposal_id,
        ProposalDecisionEventType.revoked,
        "The accepted direction is no longer authoritative.",
    )

    first = service.list()
    second = service.list()
    actions = [
        action
        for action in first
        if action.kind == "review_revoked_change"
        and action.target == change.change_id
    ]

    assert len(actions) == 1
    assert actions[0].source == ".p2p/project/next-actions.yml"
    assert actions[0].reason == "Owner-curated remediation."
    assert [
        (action.action_id, action.kind, action.target)
        for action in first
    ] == [
        (action.action_id, action.kind, action.target)
        for action in second
    ]


def test_next_actions_skip_deep_freshness_for_decision_remediation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Revoked freshness source")
    _apply_decision(
        workspace,
        proposal.proposal_id,
        ProposalDecisionEventType.accepted,
        "Initially accepted.",
    )
    change = workspace.create_change_set(proposal.proposal_id, "Dependent change")
    workspace.update_change_set_status(change.change_id, "planned")
    workspace.update_change_set_status(change.change_id, "implementation_ready")
    workspace.update_change_set_status(change.change_id, "in_progress")
    freshness_calls = 0

    def freshness_status(**kwargs: object) -> object:
        nonlocal freshness_calls
        freshness_calls += 1
        assert kwargs.get("decision_context_index_snapshot") is not None
        return type(
            "Freshness",
            (),
            {"status": "attention_required", "rebuild_plan": ()},
        )()

    monkeypatch.setattr(workspace, "project_freshness", freshness_status)
    _apply_decision(
        workspace,
        proposal.proposal_id,
        ProposalDecisionEventType.revoked,
        "The accepted direction is no longer authoritative.",
    )
    freshness_calls = 0

    actions = workspace._next_action_service().list()

    assert freshness_calls == 0
    assert not any(
        action.kind == "review_decision_freshness"
        and action.target == "derived_freshness"
        for action in actions
    )
    assert any(action.target == change.change_id for action in actions)


def test_reinstatement_keeps_review_actions_without_restoring_dependents(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    proposal = workspace.create_proposal("Reinstated source")
    _apply_decision(
        workspace,
        proposal.proposal_id,
        ProposalDecisionEventType.accepted,
        "Initially accepted.",
    )
    change = workspace.create_change_set(proposal.proposal_id, "Dependent change")
    workspace.update_change_set_status(change.change_id, "planned")
    workspace.update_change_set_status(change.change_id, "implementation_ready")
    workspace.update_change_set_status(change.change_id, "in_progress")
    workspace.update_change_set_status(change.change_id, "in_review")
    workspace.update_change_set_status(change.change_id, "completed")
    _apply_decision(
        workspace,
        proposal.proposal_id,
        ProposalDecisionEventType.revoked,
        "Temporarily revoked.",
    )
    change_path = tmp_path / change.path / "change.md"
    before_change = change_path.read_bytes()
    _apply_decision(
        workspace,
        proposal.proposal_id,
        ProposalDecisionEventType.reinstated,
        "Restore the exact prior decision.",
    )

    actions = workspace._next_action_service().list()
    remediation = next(
        action
        for action in actions
        if action.kind == "review_revoked_change"
        and action.target == change.change_id
    )

    assert "is reinstated" in remediation.reason
    assert "No rollback or technical restoration is implied." in remediation.reason
    assert change_path.read_bytes() == before_change

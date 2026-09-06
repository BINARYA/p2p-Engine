from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.choices import ChoiceLifecycleService, ChoiceStatus
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Demo Project", project_domain="software")
    return workspace


def _accepted_change_workspace(root: Path) -> P2PWorkspace:
    workspace = _workspace(root)
    workspace.create_proposal("Governance Model")
    record_decision(workspace, "PROP-001", DecisionOutcome.accepted, "Needed.", "owner")
    workspace.create_change_set("PROP-001", "Governance Model")
    workspace.update_change_set_status("CHANGE-001", "planned")
    return workspace


def _create_choice(
    service: ChoiceLifecycleService,
    title: str,
    options: list[str],
    **kwargs: object,
) -> ChoiceStatus:
    return service.create(
        title,
        options,
        problem=f"Choose the governed direction for {title}.",
        context="The project requires a complete and stable decision frame.",
        **kwargs,
    )


def test_choice_lifecycle_service_creates_lists_and_shows_choice(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Prompt Workflow")
    service = workspace._choice_lifecycle_service()

    created = _create_choice(
        service,
        "Initial AI Strategy",
        ["Prompt-only first", "Direct AI now"],
        related=["PROP-001"],
        source="INTAKE-001",
    )
    statuses = service.statuses()
    detail = service.show(created.choice_id)

    assert created.choice_id == "CHOICE-001"
    assert created.status == "open"
    assert statuses[0].title == "Initial AI Strategy"
    assert detail.options[0]["id"] == "A"
    assert detail.related_proposals[0]["proposal"] == "PROP-001"
    assert (tmp_path / ".p2p" / "choices" / "CHOICE-001-initial-ai-strategy" / "choice.md").exists()


def test_choice_lifecycle_service_discovers_advisory_findings(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Governance Model")
    workspace.record_vote("PROP-001", choice="A", reason="Prefer A", voter="owner", role="owner")
    _create_choice(
        workspace._choice_lifecycle_service(),
        "Governance Scope",
        ["Minimal governance", "Full governance"],
        related=["PROP-001"],
    )

    findings = workspace._choice_lifecycle_service().discover()

    assert [finding.kind for finding in findings] == [
        "proposal_local_choice_candidate",
        "open_project_choice",
    ]
    assert findings[0].target == "CHOICE-PROP-001"
    assert findings[1].target == "CHOICE-001"


def test_choice_lifecycle_service_blocks_and_unblocks_choice(tmp_path: Path) -> None:
    workspace = _accepted_change_workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    _create_choice(
        service,
        "Governance Scope",
        ["Minimal governance", "Full governance"],
        related=["PROP-001"],
    )

    blocked = service.block(
        "CHOICE-001",
        target="CHANGE-001",
        target_type="change",
        reason="Governance scope must be decided first.",
    )
    unblocked = service.unblock("CHOICE-001", target="CHANGE-001", target_type="change")

    assert blocked.blocks[0]["status"] == "active"
    assert unblocked.blocks[0]["status"] == "inactive"
    assert "cleared_on" in unblocked.blocks[0]


def test_choice_lifecycle_service_decides_choice(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    _create_choice(service, "Initial AI Strategy", ["Prompt-only first", "Direct AI now"])

    decided = service.decide("CHOICE-001", option="B", reason="Use direct AI now.", decider="owner")
    detail = service.show("CHOICE-001")
    options = yaml.safe_load(
        (tmp_path / ".p2p" / "choices" / "CHOICE-001-initial-ai-strategy" / "options.yml").read_text(
            encoding="utf-8"
        )
    )

    assert decided.status == "decided"
    assert decided.selected_option == "B - Direct AI now"
    assert detail.selected_option == "B - Direct AI now"
    assert options["options"] == [
        {"id": "A", "title": "Prompt-only first"},
        {"id": "B", "title": "Direct AI now"},
    ]
    assert detail.terminal is True
    assert detail.terminal_event is not None
    assert detail.terminal_event["selected_option_id"] == "B"


def test_choice_lifecycle_service_validates_error_paths(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()

    with pytest.raises(ValueError, match="requires 2-26 options"):
        _create_choice(service, "Invalid Choice", ["Only one"])

    _create_choice(service, "Initial AI Strategy", ["Prompt-only first", "Direct AI now"])

    with pytest.raises(ValueError, match="target_type must be"):
        service.block("CHOICE-001", target="PROP-999", target_type="invalid", reason="Invalid target.")

    choice_dir = tmp_path / ".p2p" / "choices" / "CHOICE-001-initial-ai-strategy"
    (choice_dir / "links.yml").write_text("blocks: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected `blocks` list"):
        service.unblock("CHOICE-001", target="PROP-001", target_type="proposal")

    (choice_dir / "links.yml").write_text("related_proposals: []\nrelated_changes: []\n", encoding="utf-8")
    (choice_dir / "options.yml").write_text("options: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected `options` list"):
        service.decide("CHOICE-001", option="A", reason="Invalid options.", decider="owner")

    (choice_dir / "options.yml").write_text("options:\n  - id: A\n    title: Prompt-only first\n", encoding="utf-8")
    with pytest.raises(ValueError, match="DIGEST_MISMATCH|DEFINITION_INVALID"):
        service.decide("CHOICE-001", option="Z", reason="Missing option.", decider="owner")


def test_choice_terminal_states_are_write_once_and_clear_blockers(tmp_path: Path) -> None:
    workspace = _accepted_change_workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    _create_choice(service, "Governance Scope", ["Minimal", "Complete"])
    service.block("CHOICE-001", "CHANGE-001", "change", "Await the Choice.")

    plan = service.transition_preview(
        "CHOICE-001",
        transition="withdraw",
        reason="The decision frame is obsolete.",
        actor_id="owner",
        operation_key="choice-withdraw-001",
    )
    result = service.transition_apply(
        "CHOICE-001",
        transition="withdraw",
        reason="The decision frame is obsolete.",
        actor_id="owner",
        operation_key="choice-withdraw-001",
        preview_token=plan.preview.preview_token,
        confirm=True,
    )

    assert result.choice.status == "withdrawn"
    assert service.show("CHOICE-001").blocks[0]["status"] == "inactive"
    with pytest.raises(ValueError, match="P2P_CHOICE_TERMINAL"):
        service.decide("CHOICE-001", "A", "Changed our mind.", "owner")
    with pytest.raises(ValueError, match="P2P_CHOICE_TERMINAL"):
        service.transition_preview(
            "CHOICE-001",
            transition="supersede",
            replacement_choice_id="CHOICE-002",
            reason="Replace it.",
            actor_id="owner",
            operation_key="choice-supersede-after-terminal",
        )


def test_choice_and_related_proposal_lifecycles_remain_independent(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Related proposal")
    service = workspace._choice_lifecycle_service()
    _create_choice(
        service,
        "Independent decision frame",
        ["Keep", "Replace"],
        related=["PROP-001"],
    )

    record_decision(
        workspace,
        "PROP-001",
        DecisionOutcome.rejected,
        "The proposal is not satisfactory.",
        "owner",
    )
    assert service.show("CHOICE-001").status == "open"

    service.withdraw(
        "CHOICE-001",
        reason="The separate decision frame is obsolete.",
        actor_id="owner",
        operation_key="choice-independent-lifecycle",
    )
    assert workspace.show_proposal("PROP-001").status == "rejected"


def test_choice_supersession_records_only_forward_lineage_and_derives_inverse(tmp_path: Path) -> None:
    service = _workspace(tmp_path)._choice_lifecycle_service()
    _create_choice(service, "Old frame", ["A one", "A two"])
    _create_choice(service, "New frame", ["B one", "B two"])

    plan = service.transition_preview(
        "CHOICE-001",
        transition="supersede",
        replacement_choice_id="CHOICE-002",
        reason="New evidence requires a different frame.",
        actor_id="owner",
        operation_key="choice-supersede-001",
    )
    service.transition_apply(
        "CHOICE-001",
        transition="supersede",
        replacement_choice_id="CHOICE-002",
        reason="New evidence requires a different frame.",
        actor_id="owner",
        operation_key="choice-supersede-001",
        preview_token=plan.preview.preview_token,
        confirm=True,
    )

    assert service.show("CHOICE-001").replacement_choice_id == "CHOICE-002"
    assert service.show("CHOICE-002").supersedes == ("CHOICE-001",)
    replacement_lifecycle = yaml.safe_load(
        next((tmp_path / ".p2p" / "choices").glob("CHOICE-002-*/lifecycle.yml")).read_text()
    )
    assert replacement_lifecycle["choice_lifecycle"]["terminal_event"] is None


def test_choice_transition_exact_replay_and_definition_drift(tmp_path: Path) -> None:
    service = _workspace(tmp_path)._choice_lifecycle_service()
    _create_choice(service, "Runtime", ["Keep", "Replace"])
    plan = service.transition_preview(
        "CHOICE-001",
        transition="decide",
        option="A",
        reason="Keep the stable runtime.",
        actor_id="owner",
        operation_key="choice-decision-replay",
    )
    first = service.transition_apply(
        "CHOICE-001",
        transition="decide",
        option="A",
        reason="Keep the stable runtime.",
        actor_id="owner",
        operation_key="choice-decision-replay",
        preview_token=plan.preview.preview_token,
        confirm=True,
    )
    replay = service.transition_apply(
        "CHOICE-001",
        transition="decide",
        option="A",
        reason="Keep the stable runtime.",
        actor_id="owner",
        operation_key="choice-decision-replay",
        preview_token=plan.preview.preview_token,
        confirm=True,
    )
    assert first.status == "applied"
    assert replay.status == "already_applied"
    assert replay.replayed is True

    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        service.transition_apply(
            "CHOICE-001",
            transition="decide",
            option="B",
            reason="Use a different request.",
            actor_id="owner",
            operation_key="choice-decision-replay",
            preview_token=plan.preview.preview_token,
            confirm=True,
        )

    _create_choice(service, "Storage", ["Filesystem", "Other"])
    choice_path = next((tmp_path / ".p2p" / "choices").glob("CHOICE-002-*/choice.md"))
    choice_path.write_text(choice_path.read_text().replace("Storage", "Changed", 1))
    with pytest.raises(ValueError, match="DIGEST_MISMATCH"):
        service.show("CHOICE-002")


def test_second_choice_decision_is_rejected_without_any_persistent_change(
    tmp_path: Path,
) -> None:
    service = _workspace(tmp_path)._choice_lifecycle_service()
    _create_choice(service, "Release channel", ["Stable", "Preview"])
    service.decide(
        "CHOICE-001",
        option="A",
        reason="Use the stable channel.",
        decider="owner",
    )
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in (tmp_path / ".p2p").rglob("*")
        if path.is_file()
    }

    with pytest.raises(ValueError, match="P2P_CHOICE_TERMINAL"):
        service.transition_preview(
            "CHOICE-001",
            transition="decide",
            option="B",
            reason="Attempt to rewrite the selected option.",
            actor_id="owner",
            operation_key="choice-second-decision-must-fail",
        )

    after = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in (tmp_path / ".p2p").rglob("*")
        if path.is_file()
    }
    assert after == before


def test_incomplete_legacy_choice_can_close_without_rewriting_options(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    _create_choice(service, "Legacy frame", ["Keep", "Replace"])
    choice_dir = next((tmp_path / ".p2p" / "choices").glob("CHOICE-001-*"))
    lifecycle = choice_dir / "lifecycle.yml"
    lifecycle.unlink()
    choice = choice_dir / "choice.md"
    choice.write_text(
        choice.read_text().replace(
            "The project requires a complete and stable decision frame.", "Pending."
        ),
        encoding="utf-8",
    )
    options = choice_dir / "options.yml"
    legacy_options = yaml.safe_load(options.read_text())
    for item in legacy_options["options"]:
        item["status"] = "available"
    options.write_text(yaml.safe_dump(legacy_options, sort_keys=False), encoding="utf-8")

    before = options.read_bytes()
    result = service.withdraw(
        "CHOICE-001",
        reason="Retire an incomplete legacy frame.",
        actor_id="owner",
        operation_key="choice-legacy-withdraw",
    )

    assert result.status == "withdrawn"
    assert result.seal_status == "incomplete_unsealed"
    assert options.read_bytes() == before


def test_choice_terminal_transition_rolls_back_all_artifacts_on_failure(tmp_path: Path) -> None:
    service = _workspace(tmp_path)._choice_lifecycle_service()
    _create_choice(service, "Runtime", ["Keep", "Replace"])
    fired = False

    def fail_after_first_replace(stage: str, target: str) -> None:
        nonlocal fired
        if stage == "after_replace" and target and not fired:
            fired = True
            raise RuntimeError("injected Choice transition failure")

    service.atomic_writer = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=fail_after_first_replace,
    )
    plan = service.transition_preview(
        "CHOICE-001",
        transition="withdraw",
        reason="Obsolete frame.",
        actor_id="owner",
        operation_key="choice-rollback-001",
    )

    with pytest.raises(ValueError, match="P2P_CHOICE_TRANSITION_FAILED"):
        service.transition_apply(
            "CHOICE-001",
            transition="withdraw",
            reason="Obsolete frame.",
            actor_id="owner",
            operation_key="choice-rollback-001",
            preview_token=plan.preview.preview_token,
            confirm=True,
        )

    assert service.show("CHOICE-001").status == "open"
    assert service.receipts.read(idempotency_key="choice-rollback-001") is None


def test_terminal_choice_is_history_in_registry_context_and_next_actions(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    _create_choice(service, "Obsolete question", ["Continue", "Stop"])
    service.withdraw(
        "CHOICE-001",
        reason="The question no longer applies.",
        actor_id="owner",
        operation_key="choice-history-001",
    )

    workspace.refresh_registries()
    record = next(
        item for item in workspace.show_registry("choices").records
        if item.get("id") == "CHOICE-001"
    )
    index = workspace.decision_context_index()
    actions = workspace._next_action_service().list()

    assert record["status"] == "withdrawn"
    assert record["terminal"] is True
    assert any(
        item.owner_id == "CHOICE-001" and item.text == "withdrawn"
        for item in index.records
    )
    assert not any(
        item.kind == "resolve_choice" and item.target == "CHOICE-001"
        for item in actions
    )


def test_choice_supersession_context_lineage_is_derived_from_replacement(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    _create_choice(service, "Old frame", ["Keep old", "Replace old"])
    _create_choice(service, "New frame", ["Adopt new", "Delay new"])
    service.supersede(
        "CHOICE-001",
        replacement_choice_id="CHOICE-002",
        reason="The replacement captures the revised decision frame.",
        actor_id="owner",
        operation_key="choice-lineage-direction",
    )

    index = workspace.decision_context_index()

    assert any(
        relation.source_id == "CHOICE-002"
        and relation.target_id == "CHOICE-001"
        and relation.relation_type.value == "supersedes"
        for relation in index.relations
    )


def test_validation_reports_choice_integrity_without_repairing_it(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_choice(
        "Runtime",
        ["Keep", "Replace"],
        problem="Choose the runtime.",
        context="The runtime choice must remain stable.",
    )
    choice_path = next((tmp_path / ".p2p" / "choices").glob("CHOICE-001-*/choice.md"))
    choice_path.write_text(choice_path.read_text().replace("Runtime", "Rewritten", 1))

    result = workspace.validate()

    assert result.ok is False
    assert any(finding.code == "P2P_CHOICE_INVALID" for finding in result.findings)
    assert "Rewritten" in choice_path.read_text()

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.decision_context import Activation, Authority, RelationType
from p2p_engine.foundation.markdown import read_frontmatter, replace_frontmatter
from p2p_engine.services.choices import ChoiceLifecycleService
from p2p_engine.services.project_replication import (
    FilesystemProjectReplicationStore,
    set_replication_command,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data
from tests.filesystem_assertions import assert_no_workspace_mutation
from tests.test_durable_project_replication import _command

pytestmark = pytest.mark.service


def _workspace(root: Path) -> tuple[P2PWorkspace, ChoiceLifecycleService]:
    workspace = P2PWorkspace(root)
    workspace.init_project("Decided Choice supersession", project_domain="software")
    service = workspace._choice_lifecycle_service()
    for title in ("Earlier direction", "Replacement direction"):
        service.create(
            title,
            ["Keep direction", "Change direction"],
            problem=f"Choose the governed direction for {title}.",
            context="The project owner needs one complete decision frame.",
        )
    return workspace, service


def _decide(service: ChoiceLifecycleService, choice_id: str) -> None:
    service.decide(choice_id, "A", "The owner selected the direction.", "owner")


def _supersede_request() -> dict[str, str]:
    return {
        "transition": "supersede",
        "replacement_choice_id": "CHOICE-002",
        "reason": "The later owner decision replaces the earlier direction.",
        "actor_id": "owner",
        "operation_key": "decided-choice-supersession",
    }


def _choice_files(root: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}


@pytest.mark.cli
@pytest.mark.parametrize("transition,decided_source", [
    ("decide", False), ("withdraw", False), ("supersede", False), ("supersede", True),
])
def test_choice_transition_status_preserves_immutable_semantics_without_paths(
    tmp_path: Path, transition: str, decided_source: bool,
) -> None:
    _, service = _workspace(tmp_path)
    if decided_source:
        _decide(service, "CHOICE-001")
        _decide(service, "CHOICE-002")
    key = f"receipt-{transition}-{'decided' if decided_source else 'open'}"
    request = {
        "transition": transition, "reason": "Qualify durable transition recovery.",
        "actor_id": "owner", "operation_key": key,
    }
    if transition == "decide":
        request["option"] = "B"
    if transition == "supersede":
        request["replacement_choice_id"] = "CHOICE-002"
    plan = service.transition_preview("CHOICE-001", **request)
    service.transition_apply(
        "CHOICE-001", **request, preview_token=plan.preview.preview_token, confirm=True,
    )
    receipt = service.receipts.read(idempotency_key=key)
    assert receipt is not None
    expected = {field: value for field, value in receipt.result.items() if field != "changed_paths"}
    digest_request = {
        "choice_id": "CHOICE-001", "transition": transition,
        "reason": request["reason"], "actor_id": "owner", "executor_id": "owner",
        "executor_kind": "person", "operation_key_sha256": hashlib.sha256(key.encode()).hexdigest(),
        "option": request.get("option"), "replacement_choice_id": request.get("replacement_choice_id"),
        "effective_on": None, "blocker_override": False, "channel": "cli",
        "authority_context_sha256": None, "consent_id": None,
    }
    expected_digest = hashlib.sha256(json.dumps(
        digest_request, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    assert expected["replay_request_sha256"] == expected_digest == plan.replay_request_sha256
    assert expected["contract"] == "p2p-choice-transition-result/v1"
    assert expected["choice_id"] == "CHOICE-001"
    assert expected["target_state"] == {"decide": "decided", "withdraw": "withdrawn", "supersede": "superseded"}[transition]
    assert set(expected) == {
        "contract", "choice_id", "transition", "target_state", "selected_option",
        "replacement_choice_id", "definition_digest", "blockers_cleared", "replay_request_sha256",
    }
    runner = CliRunner()
    for drifted in (False, True):
        if drifted:
            decision_path = tmp_path / service.show("CHOICE-001").path / "decision.md"
            decision_path.write_bytes(decision_path.read_bytes() + b"\nLater evidence drift.\n")
        with assert_no_workspace_mutation(tmp_path):
            status = runner.invoke(app, [
                "mutation", "status", "--operation-key", key, "--format", "json", "--root", str(tmp_path),
            ])
        assert status.exit_code == 0
        data = cli_data(status)
        assert data["state"] == ("postcondition_drift" if drifted else "applied")
        assert data["result"] == expected
        assert "changed_paths" not in status.stdout
        assert ".p2p/" not in json.dumps(data["result"])


@pytest.mark.integration
def test_decided_supersession_commits_and_replays_one_canonical_batch(tmp_path: Path) -> None:
    workspace, service = _workspace(tmp_path)
    _decide(service, "CHOICE-001")
    _decide(service, "CHOICE-002")
    store = FilesystemProjectReplicationStore(tmp_path)
    store.initialize(authority_epoch=2, project_revision=1)
    request = _supersede_request()
    plan = service.transition_preview("CHOICE-001", **request)
    command, _ = _command(tmp_path, operation_id="op_decided_supersession", revision=1,
        idempotency_key=request["operation_key"], command_name="choice.transition-apply",
        payload_contract="p2p-choice-transition-request/v1", payload={"choice_id": "CHOICE-001", **request})
    set_replication_command(command)
    try:
        applied = service.transition_apply("CHOICE-001", **request, preview_token=plan.preview.preview_token, confirm=True)
        assert applied.status == "applied"
        assert store.state().current_revision == 2
        with assert_no_workspace_mutation(tmp_path):
            replay = service.transition_apply("CHOICE-001", **request, preview_token=plan.preview.preview_token, confirm=True)
        assert replay.replayed
    finally:
        set_replication_command(None)
    batches = store.feed(after_revision=1, replica_id=command.replica_id.value).batches
    assert len(batches) == 1
    assert batches[0].operation_id == command.operation_id
    assert workspace.show_choice("CHOICE-001").status == "superseded"


@pytest.mark.integration
def test_choice_transition_rejects_an_unrelated_feed_command_without_writes(tmp_path: Path) -> None:
    _, service = _workspace(tmp_path)
    _decide(service, "CHOICE-001")
    _decide(service, "CHOICE-002")
    request = _supersede_request()
    plan = service.transition_preview("CHOICE-001", **request)
    command, _ = _command(tmp_path, operation_id="op_wrong_choice_command", revision=1,
                          idempotency_key=request["operation_key"])
    set_replication_command(command)
    try:
        with assert_no_workspace_mutation(tmp_path), pytest.raises(ValueError, match="P2P_REPLICATION_COMMAND_CONFLICT"):
            service.transition_apply("CHOICE-001", **request, preview_token=plan.preview.preview_token, confirm=True)
    finally:
        set_replication_command(None)


def test_decided_supersession_reuses_current_record_and_excludes_old_authority(
    tmp_path: Path,
) -> None:
    workspace, service = _workspace(tmp_path)
    _decide(service, "CHOICE-001")
    _decide(service, "CHOICE-002")
    source = service.show("CHOICE-001")
    source_dir = tmp_path / source.path
    source_definition = service.detail_read("CHOICE-001").definition.to_dict()
    source_files = _choice_files(source_dir)
    replacement_dir = tmp_path / service.show("CHOICE-002").path
    replacement_files = _choice_files(replacement_dir)
    request = _supersede_request()

    with assert_no_workspace_mutation(tmp_path):
        plan = service.transition_preview("CHOICE-001", **request)

    assert plan.preview.semantic_diff["state_before"] == "decided"
    assert plan.preview.semantic_diff["state_after"] == "superseded"
    applied = service.transition_apply(
        "CHOICE-001", **request, preview_token=plan.preview.preview_token, confirm=True
    )

    assert applied.choice.choice_id == "CHOICE-001"
    assert applied.choice.status == "superseded"
    assert applied.choice.definition_digest == source.definition_digest
    assert applied.choice.selected_option is None
    assert applied.choice.replacement_choice_id == "CHOICE-002"
    assert service.detail_read("CHOICE-001").definition.to_dict() == source_definition
    assert _choice_files(source_dir)["options.yml"] == source_files["options.yml"]
    assert set(_choice_files(source_dir)) == set(source_files)
    lifecycle = yaml.safe_load((source_dir / "lifecycle.yml").read_bytes())["choice_lifecycle"]
    assert lifecycle["state"] == "superseded"
    assert lifecycle["terminal_event"]["kind"] == "superseded"
    assert lifecycle["terminal_event"]["selected_option_id"] is None
    assert lifecycle["terminal_event"]["replacement_choice_id"] == "CHOICE-002"
    assert "No option selected." in (source_dir / "decision.md").read_text()
    assert _choice_files(replacement_dir) == replacement_files
    assert service.show("CHOICE-002").supersedes == ("CHOICE-001",)

    with assert_no_workspace_mutation(tmp_path):
        replay = service.transition_apply(
            "CHOICE-001", **request, preview_token=plan.preview.preview_token, confirm=True
        )
    assert replay.replayed is True
    assert replay.status == "already_applied"

    workspace.refresh_registries()
    registry_record = next(
        item for item in workspace.show_registry("choices").records
        if item["id"] == "CHOICE-001"
    )
    assert registry_record["status"] == "superseded"
    assert registry_record["selected_option"] is None
    assert registry_record["replacement_choice_id"] == "CHOICE-002"
    index = workspace.decision_context_index()
    active_decisions = {
        record.owner_id for record in index.records
        if record.authority == Authority.DECIDED_PROJECT_CHOICE
        and record.activation == Activation.ACTIVE
    }
    assert active_decisions == {"CHOICE-002"}
    assert any(
        relation.source_id == "CHOICE-002"
        and relation.target_id == "CHOICE-001"
        and relation.relation_type == RelationType.SUPERSEDES
        for relation in index.relations
    )
    assert not any(
        finding.target == "CHOICE-001" for finding in service.discover()
    )
    assert not any(
        action.kind == "resolve_choice" and action.target in {"CHOICE-001", "CHOICE-002"}
        for action in workspace._next_action_service().list()
    )
    assert workspace.validate().ok is True


@pytest.mark.parametrize("decided_id", ("CHOICE-001", "CHOICE-002"))
def test_choice_supersession_rejects_open_decided_state_mismatch_without_writes(
    tmp_path: Path, decided_id: str,
) -> None:
    _, service = _workspace(tmp_path)
    _decide(service, decided_id)

    with assert_no_workspace_mutation(tmp_path):
        with pytest.raises(ValueError, match="P2P_CHOICE_REPLACEMENT_INVALID"):
            service.transition_preview("CHOICE-001", **_supersede_request())


def test_decided_replacement_decision_change_invalidates_supersession_preview(
    tmp_path: Path,
) -> None:
    _, service = _workspace(tmp_path)
    _decide(service, "CHOICE-001")
    _decide(service, "CHOICE-002")
    request = _supersede_request()
    plan = service.transition_preview("CHOICE-001", **request)
    replacement_dir = tmp_path / service.show("CHOICE-002").path
    decision_path = replacement_dir / "decision.md"
    decision_path.write_text(
        decision_path.read_text().replace(
            "The owner selected the direction.", "Changed decision evidence."
        )
    )

    with assert_no_workspace_mutation(tmp_path):
        with pytest.raises(ValueError, match="P2P_PREVIEW_STALE"):
            service.transition_apply(
                "CHOICE-001", **request,
                preview_token=plan.preview.preview_token, confirm=True,
            )
    assert service.show("CHOICE-001").status == "decided"


def test_legacy_decided_supersession_retains_unsealed_definition(
    tmp_path: Path,
) -> None:
    _, service = _workspace(tmp_path)
    _decide(service, "CHOICE-001")
    _decide(service, "CHOICE-002")
    source_dir = tmp_path / service.show("CHOICE-001").path
    (source_dir / "lifecycle.yml").unlink()
    source_options = (source_dir / "options.yml").read_bytes()
    request = _supersede_request()

    with assert_no_workspace_mutation(tmp_path):
        source = service.show("CHOICE-001")
        plan = service.transition_preview("CHOICE-001", **request)
    assert source.status == "decided"
    assert source.seal_status == "complete_unsealed"
    applied = service.transition_apply(
        "CHOICE-001", **request, preview_token=plan.preview.preview_token, confirm=True
    )

    assert applied.choice.status == "superseded"
    assert applied.choice.seal_status == "complete_unsealed"
    assert applied.choice.definition_digest is None
    assert (source_dir / "options.yml").read_bytes() == source_options
    lifecycle = yaml.safe_load((source_dir / "lifecycle.yml").read_bytes())["choice_lifecycle"]
    assert lifecycle["definition_contract"] == "legacy"
    assert lifecycle["definition_digest"] is None


def test_legacy_decided_supersession_requires_explicit_source_identity(
    tmp_path: Path,
) -> None:
    _, service = _workspace(tmp_path)
    _decide(service, "CHOICE-001")
    _decide(service, "CHOICE-002")
    source_dir = tmp_path / service.show("CHOICE-001").path
    (source_dir / "lifecycle.yml").unlink()
    choice_path = source_dir / "choice.md"
    choice_text = choice_path.read_text()
    frontmatter = read_frontmatter(choice_text)
    del frontmatter["choice_id"]
    choice_path.write_text(replace_frontmatter(choice_text, frontmatter))

    with assert_no_workspace_mutation(tmp_path):
        with pytest.raises(ValueError, match="P2P_CHOICE_.*(?:INVALID|IDENTITY|LEGACY)"):
            service.transition_preview("CHOICE-001", **_supersede_request())

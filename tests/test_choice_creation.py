from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.authority import AuthorityBasis, AuthorityClaim, AuthorityProjectBinding
from p2p_engine.core.choice_creation import CHOICE_CREATE_FIELD_LIMITS
from p2p_engine.core.governed_capabilities import governed_capability
from p2p_engine.services.project_replication import FilesystemProjectReplicationStore
from p2p_engine.services.workspace_transactions import (
    AtomicMutationWriter,
    WorkspaceTransactionRecoveryService,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data, cli_error
from tests.filesystem_assertions import assert_no_workspace_mutation
from tests.test_authority_decisions import _external_context
from tests.test_durable_project_replication import _command

RUNNER = CliRunner()
KEY = "wavekit:123e4567e89b12d3a456426614174000"
REQUEST = {
    "title": "Runtime strategy",
    "problem": "Choose how the project runs.",
    "context": "The project needs a stable decision frame.",
    "governance_boundary": "The project owner decides.",
    "options": ["Keep current", "Adopt replacement"],
    "actor_id": "owner",
}


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Choice creation", owner="owner", starter_id="empty")
    return workspace


def _create(workspace: P2PWorkspace, **changes: object) -> dict[str, object]:
    return workspace.create_choice_with_operation_key(**{**REQUEST, "operation_key": KEY, **changes})


def _cli(root: Path, *, key: str | None = KEY, prefix: list[str] | None = None):
    arguments = (prefix or []) + [
        "choice", "create", "--title", REQUEST["title"], "--problem", REQUEST["problem"],
        "--context", REQUEST["context"], "--governance-boundary", REQUEST["governance_boundary"],
        "--option", "Keep current", "--option", "Adopt replacement", "--actor", "owner",
        "--format", "json", "--root", str(root),
    ]
    if key is not None:
        arguments += ["--operation-key", key]
    return RUNNER.invoke(app, arguments)


def test_choice_creation_replay_preserves_normalized_outcome_and_key_secrecy(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Related one")
    workspace.create_proposal("Related two")
    first = _create(workspace, title=" Runtime strategy\r\n", related=["PROP-002", "PROP-001", "PROP-001"])
    with assert_no_workspace_mutation(tmp_path):
        replay = _create(workspace, related=["PROP-001", "PROP-002"])
        status = workspace.mutation_status(idempotency_key=KEY)
    assert first["choice_create"] == replay["choice_create"]
    summary = first["choice_create"]["choice"]
    assert summary["choice_id"] == "CHOICE-001"
    assert summary["state"] == "open"
    assert summary["seal_status"] == "sealed"
    assert replay["mutation"]["status"] == "already_applied"
    assert status.operation == "choice_create"
    assert status.state == "applied"
    assert status.result == first["choice_create"]
    assert status.authority["claims"][0]["capability"] == "choice.create"
    receipt = tmp_path / workspace._mutation_receipt_service().relative_path(KEY)
    assert KEY not in receipt.read_text(encoding="utf-8")
    assert KEY not in receipt.name
    assert "changed_paths" not in status.result
    assert len(workspace.choice_statuses()) == 1


@pytest.mark.parametrize("changes", [
    {"title": "Different title"}, {"problem": "Different problem"},
    {"context": "Different context"}, {"governance_boundary": "Different authority scope"},
    {"options": ["Adopt replacement", "Keep current"]}, {"source": "INTAKE-002"},
    {"actor_id": "another-owner"}, {"executor_id": "other-executor"},
    {"executor_kind": "agent"}, {"related": ["PROP-001"]}, {"channel": "mcp"},
])
def test_choice_creation_conflicts_bind_all_semantic_inputs(tmp_path: Path, changes: dict[str, object]) -> None:
    workspace = _workspace(tmp_path)
    _create(workspace)
    with assert_no_workspace_mutation(tmp_path), pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        _create(workspace, **changes)


def test_choice_creation_replay_after_decision_and_authority_rotation_is_read_only(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    first = _create(workspace)
    workspace.decide_choice("CHOICE-001", option="B", reason="Owner selected replacement.", decider="owner")
    preview = workspace.preview_project_authority_rotation(
        operation_key="rotation-after-create", actor_id="owner", executor_id="owner", executor_kind="person",
        display_name="Rotated authority", rotated_at="2026-10-04T12:00:00Z",
    )
    workspace.apply_project_authority_rotation(
        operation_key="rotation-after-create", actor_id="owner", executor_id="owner", executor_kind="person",
        display_name="Rotated authority", rotated_at="2026-10-04T12:00:00Z",
        preview_token=preview.mutation.preview_token, confirm=True,
    )
    with assert_no_workspace_mutation(tmp_path):
        replay = _create(workspace)
        status = workspace.mutation_status(idempotency_key=KEY)
    assert replay["choice_create"] == first["choice_create"]
    assert replay["authority"] == first["authority"]
    assert workspace.show_choice("CHOICE-001").status == "decided"
    assert status.state == "postcondition_drift"
    assert status.result["choice"]["choice_id"] == "CHOICE-001"


def test_choice_creation_rejects_nonowner_without_mutation(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.permissions_actor_add("supporter", role="contributor")
    assert governed_capability("choice.create").external_root_required is True
    with assert_no_workspace_mutation(tmp_path), pytest.raises(ValueError, match="P2P_AUTHORIZATION_DENIED"):
        _create(workspace, actor_id="supporter")


def _external_workspace(root: Path):
    bootstrap = _external_context((AuthorityClaim(
        capability="project.initialize", basis=AuthorityBasis.root_authority, authority_generation=1,
    ),))
    workspace = P2PWorkspace(root)
    workspace.init_project("External creation", authority_context=bootstrap, starter_id="empty")
    context = replace(bootstrap, claims=(AuthorityClaim(
        capability="choice.create", basis=AuthorityBasis.root_authority, authority_generation=1,
    ),))
    return workspace, context


@pytest.mark.parametrize("invalid", ["grant", "capability", "generation", "subject", "executor", "kind"])
def test_choice_creation_external_authority_failures_are_nonmutating(tmp_path: Path, invalid: str) -> None:
    workspace, context = _external_workspace(tmp_path)
    request = {
        "actor_id": context.subject.identity_id, "executor_id": context.executor.identity_id,
        "executor_kind": context.executor.kind.value, "authority_context": context,
    }
    if invalid == "grant":
        request["authority_context"] = replace(context, claims=(AuthorityClaim(
            capability="choice.create", basis=AuthorityBasis.capability_grant,
            grant_ref="create-grant", grant_generation=1,
        ),))
    elif invalid == "capability":
        request["authority_context"] = replace(context, claims=(AuthorityClaim(
            capability="choice.lifecycle.transition", basis=AuthorityBasis.root_authority, authority_generation=1,
        ),))
    elif invalid == "generation":
        request["authority_context"] = replace(context, project_authority=AuthorityProjectBinding(
            authority_id=context.project_authority.authority_id, generation=2,
            provider_id="wavekit", provider_policy_version="wavekit-capabilities-v1",
        ))
    else:
        request[{"subject": "actor_id", "executor": "executor_id", "kind": "executor_kind"}[invalid]] = "wrong"
    with assert_no_workspace_mutation(tmp_path), pytest.raises(ValueError, match="P2P_(AUTH|CAPABILITY)"):
        _create(workspace, **request)


def test_choice_creation_external_owner_records_distinct_subject_and_executor(tmp_path: Path) -> None:
    workspace, context = _external_workspace(tmp_path)
    request = {
        "actor_id": context.subject.identity_id, "executor_id": context.executor.identity_id,
        "executor_kind": context.executor.kind.value, "authority_context": context,
    }
    result = _create(workspace, **request)
    assert result["authority"]["subject"] == context.subject.to_dict()
    assert result["authority"]["executor"] == context.executor.to_dict()
    receipt = workspace.mutation_status(idempotency_key=KEY)
    assert receipt.authority == result["authority"]
    with assert_no_workspace_mutation(tmp_path):
        assert _create(workspace, **request)["choice_create"] == result["choice_create"]
    changed_context = replace(context, authorization_decision_id="different-authz")
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        _create(workspace, **{**request, "authority_context": changed_context})


@pytest.mark.parametrize("field", list(CHOICE_CREATE_FIELD_LIMITS) + ["related"])
def test_choice_creation_machine_limits_are_explicit_and_nonmutating(tmp_path: Path, field: str) -> None:
    workspace = _workspace(tmp_path)
    if field == "option":
        changes = {"options": ["x" * 501, "Valid second option"]}
    elif field == "related":
        changes = {"related": ["PROP-001"] * 33}
    else:
        changes = {field: "x" * (CHOICE_CREATE_FIELD_LIMITS[field] + 1)}
    with assert_no_workspace_mutation(tmp_path), pytest.raises(ValueError, match="P2P_CHOICE_CREATE_INVALID"):
        _create(workspace, **changes)


@pytest.mark.cli
def test_cli_choice_create_json_flags_envelope_status_and_replay(tmp_path: Path) -> None:
    _workspace(tmp_path)
    first = _cli(tmp_path)
    assert first.exit_code == 0, first.output
    data = cli_data(first, operation="choice.create")
    assert data["choice_create"]["contract"] == "p2p-choice-create-result/v1"
    assert data["mutation"]["status"] == "applied"
    with assert_no_workspace_mutation(tmp_path):
        replay = _cli(tmp_path)
        status = RUNNER.invoke(app, ["mutation", "status", "--operation-key", KEY, "--format", "json", "--root", str(tmp_path)])
    assert replay.exit_code == 0, replay.output
    assert cli_data(replay)["choice_create"] == data["choice_create"]
    assert cli_data(replay)["mutation"]["replayed"] is True
    assert cli_data(status)["result"] == data["choice_create"]
    assert KEY not in first.stdout + replay.stdout + status.stdout


@pytest.mark.cli
def test_cli_choice_create_json_requires_key_and_legacy_text_stays_supported(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    with assert_no_workspace_mutation(tmp_path):
        missing = _cli(tmp_path, key=None)
    assert missing.exit_code == 2
    assert cli_error(missing)["code"] == "P2P_IDEMPOTENCY_KEY_REQUIRED"
    text = RUNNER.invoke(app, ["choice", "create", "--title", "Legacy text", "--problem", "Stable problem",
        "--context", "Stable context", "--option", "First", "--option", "Second", "--root", str(tmp_path)])
    assert text.exit_code == 0, text.output
    assert "Choice created." in text.stdout
    assert workspace.show_choice("CHOICE-001").status == "open"


def test_choice_creation_allocation_race_cannot_duplicate_numeric_ids(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    writer_apply = service.atomic_writer.apply

    def interfere(**request):
        P2PWorkspace(tmp_path).create_choice("Different title", ["One", "Two"], problem="Stable problem", context="Stable context")
        return writer_apply(**request)

    monkeypatch.setattr(service.atomic_writer, "apply", interfere)
    with pytest.raises(ValueError, match="P2P_CHOICE_CREATE_PRECONDITION_CHANGED"):
        _create(workspace)
    assert [item.choice_id for item in workspace.choice_statuses()] == ["CHOICE-001"]
    assert workspace.mutation_status(idempotency_key=KEY).state == "not_found"
    monkeypatch.setattr(service.atomic_writer, "apply", writer_apply)
    assert _create(workspace)["choice_create"]["choice"]["choice_id"] == "CHOICE-002"


@pytest.mark.parametrize("field", ["contract", "choice_id", "definition_digest", "state", "changed_paths", "authority"])
def test_choice_creation_receipt_validation_rejects_corruption(tmp_path: Path, field: str) -> None:
    workspace = _workspace(tmp_path)
    _create(workspace)
    path = tmp_path / workspace._mutation_receipt_service().relative_path(KEY)
    document = yaml.safe_load(path.read_bytes())
    receipt = document["mutation_receipt"]
    if field == "authority":
        receipt["authority"]["claims"][0]["capability"] = "choice.lifecycle.transition"
    elif field == "contract":
        receipt["result"][field] = "unsupported/v1"
    elif field == "changed_paths":
        receipt["result"][field][0] = ".p2p/choices/CHOICE-999-other/choice.md"
    else:
        receipt["result"]["choice"][field] = "invalid"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_RECEIPT_CORRUPT"):
        workspace.mutation_status(idempotency_key=KEY)


def test_choice_creation_interruption_uses_existing_incomplete_status_and_recovery(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    interrupted = []

    def interrupt(stage: str, target: str) -> None:
        if stage == "after_replace" and not interrupted:
            interrupted.append(target)
            (tmp_path / target).write_bytes(b"external edit prevents rollback")
            raise RuntimeError("injected interruption")

    service.atomic_writer = AtomicMutationWriter(root=tmp_path, p2p_dir=tmp_path / ".p2p", failure_injector=interrupt)
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_INCOMPLETE_TRANSACTION"):
        _create(workspace)
    status = workspace.mutation_status(idempotency_key=KEY)
    assert status.state == "incomplete" and status.recovery_required
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_INCOMPLETE_TRANSACTION"):
        _create(workspace)
    transaction = tmp_path / ".p2p/.internal/workspace-transactions/transactions" / status.transaction_id
    (tmp_path / interrupted[0]).write_bytes((transaction / "candidates" / interrupted[0]).read_bytes())
    recovery = WorkspaceTransactionRecoveryService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    assert recovery.resume(transaction_id=status.transaction_id, actor="owner", confirm=True).status == "applied"
    with assert_no_workspace_mutation(tmp_path):
        replay = _create(workspace)
    assert replay["mutation"]["status"] == "already_applied"
    assert workspace.show_choice("CHOICE-001").seal_status == "sealed"


@pytest.mark.integration
def test_choice_creation_worker_commit_and_exact_replay_return_one_durable_batch(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = FilesystemProjectReplicationStore(tmp_path)
    store.initialize(authority_epoch=2, project_revision=1)
    command, path = _command(tmp_path, operation_id="op_choice_1", revision=1, idempotency_key=KEY,
        command_name="choice.create", payload_contract="p2p-choice-create/v1", payload=REQUEST)
    first = _cli(tmp_path, prefix=["--replication-command-envelope", str(path)])
    assert first.exit_code == 0, first.output
    data = cli_data(first)
    assert data["replication_receipt"]["operation_id"] == command.operation_id
    assert store.state().current_revision == 2
    feed = store.feed(after_revision=1, replica_id=command.replica_id.value)
    assert len(feed.batches) == 1
    assert len([item for item in feed.batches[0].upserts if item.kind == "p2p.choices.document"]) == 5
    assert workspace.mutation_status(idempotency_key=KEY).state == "applied"
    with assert_no_workspace_mutation(tmp_path):
        replay = _cli(tmp_path, prefix=["--replication-command-envelope", str(path)])
    assert replay.exit_code == 0, replay.output
    assert cli_data(replay)["replication_receipt"] == data["replication_receipt"]
    assert cli_data(replay)["choice_create"] == data["choice_create"]
    for changed in (replace(command, operation_id="other_op"), replace(command, idempotency_key="other_key"),
        replace(command, payload={"title": "Different envelope content"}), replace(command, command="project.domain.set")):
        from p2p_engine.core.canonical_memory import canonical_json_bytes
        path.write_bytes(canonical_json_bytes(changed.to_dict()))
        with assert_no_workspace_mutation(tmp_path):
            conflict = _cli(tmp_path, prefix=["--replication-command-envelope", str(path)])
        assert conflict.exit_code != 0
        assert cli_error(conflict)["code"] in {"P2P_REPLICATION_STATE_INVALID", "P2P_REPLICATION_IDEMPOTENCY_CONFLICT", "P2P_REPLICATION_OPERATION_CONFLICT", "P2P_REPLICATION_COMMAND_CONFLICT"}
    assert store.state().current_revision == 2


@pytest.mark.integration
def test_choice_creation_failed_worker_commit_rolls_back_domain_receipt_and_batch(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = FilesystemProjectReplicationStore(tmp_path)
    store.initialize(authority_epoch=2, project_revision=1)
    command, _path = _command(tmp_path, operation_id="op_choice_failure", revision=1, idempotency_key=KEY,
        command_name="choice.create", payload_contract="p2p-choice-create/v1", payload=REQUEST)
    from p2p_engine.services.project_replication import set_replication_command

    def fail(stage: str, _target: str) -> None:
        if stage == "after_replace":
            raise RuntimeError("injected worker failure")

    workspace._choice_lifecycle_service().atomic_writer = AtomicMutationWriter(
        root=tmp_path, p2p_dir=tmp_path / ".p2p", failure_injector=fail,
    )
    set_replication_command(command)
    try:
        with pytest.raises(ValueError, match="P2P_CHOICE_CREATE_FAILED"):
            _create(workspace)
    finally:
        set_replication_command(None)
    assert not workspace.choice_statuses()
    assert workspace.mutation_status(idempotency_key=KEY).state == "not_found"
    assert store.receipt(command.operation_id) is None
    assert not store.feed(after_revision=1, replica_id=command.replica_id.value).batches
    assert store.state().current_revision == 1

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.cli_commands.project_readiness import _load_answer_file
from p2p_engine.core.authority import AuthorityBasis, AuthorityClaim
from p2p_engine.core.canonical_memory import canonical_json_bytes
from p2p_engine.core.proposal_questions import ProposalQuestionPriority
from p2p_engine.core.question_contracts import (
    QUESTION_OPERATIONS,
    validate_question_mutation_result,
    validate_question_projection,
)
from p2p_engine.services.project_replication import FilesystemProjectReplicationStore
from p2p_engine.services.question_contracts import question_projection
from p2p_engine.services.workspace_transactions import (
    AtomicMutationWriter,
    WorkspaceTransactionRecoveryService,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data, cli_error
from tests.filesystem_assertions import assert_no_workspace_mutation
from tests.test_authority_decisions import _external_context
from tests.test_authority_decisions import _workspace as _external_workspace
from tests.test_durable_project_replication import _command

RUNNER = CliRunner()
KEY = "wavekit:123e4567e89b12d3a456426614174000"


def _workspace(root: Path) -> tuple[P2PWorkspace, str]:
    workspace = P2PWorkspace(root)
    workspace.init_project("Question contracts", owner="owner", vertical_id="base_project")
    question = workspace.next_project_question()
    assert question is not None
    return workspace, question.question_id


def _proposal(workspace: P2PWorkspace) -> str:
    proposal = workspace.create_proposal("Question contract proposal")
    workspace.add_proposal_question(
        proposal.proposal_id,
        gap="alternatives_quality",
        question="Which alternative?",
        priority=ProposalQuestionPriority.high,
        actor="owner",
    )
    return proposal.proposal_id


def _mutate(workspace: P2PWorkspace, question_id: str, **changes: object):
    return workspace.question_contract_service().mutate(
        **{
            "scope": "project",
            "leaf": "answer",
            "question_id": question_id,
            "expected_revision": 1,
            "values": {"value": "Owner answer"},
            "operation_key": KEY,
            "actor_id": "owner",
            **changes,
        }
    )


def test_question_page_and_next_are_bounded_pure_projections(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    proposal_id = _proposal(workspace)
    service = workspace.question_contract_service()
    with assert_no_workspace_mutation(tmp_path):
        page = service.page(scope="project", limit=2)["question_page"]
        next_item = service.next(scope="project")["question_next"]
        proposal_page = service.page(scope="proposal", proposal_id=proposal_id, limit=1)[
            "question_page"
        ]
    assert page["contract"] == "p2p-question-page/v1"
    assert len(page["items"]) == 2
    assert next_item["question"]["id"] == question_id
    assert next_item["question"]["revision"] == 1
    assert next_item["question"]["answer_contract"]["required_fields"] == ["value"]
    assert "answers" not in page["items"][0]
    assert "transitions" not in page["items"][0]
    assert proposal_page["items"][0]["id"] == "Q001"
    assert proposal_page["items"][0]["revision"] == 1


def test_keyed_answer_replay_is_immutable_after_replacement(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    first = _mutate(workspace, question_id)
    _mutate(
        workspace,
        question_id,
        operation_key="second-answer",
        expected_revision=2,
        values={"value": "New answer"},
        replace_answer=True,
    )
    with assert_no_workspace_mutation(tmp_path):
        replay = _mutate(workspace, question_id)
        status = workspace.mutation_status(idempotency_key=KEY)
    assert replay["question_mutation"] == first["question_mutation"]
    assert replay["mutation"]["replayed"] is True
    assert status.state == "postcondition_drift"
    assert status.result == first["question_mutation"]
    assert workspace.project_question(question_id).revision == 3


@pytest.mark.parametrize(
    "changes",
    [
        {"values": {"value": "Different"}},
        {"expected_revision": 2},
        {"executor_id": "worker"},
        {"leaf": "mute", "reason": "Later"},
        {"actor_id": "another"},
        {"evidence_refs": ["note:1"]},
    ],
)
def test_reused_question_key_conflicts_before_current_state(
    tmp_path: Path, changes: dict[str, object]
) -> None:
    workspace, question_id = _workspace(tmp_path)
    _mutate(workspace, question_id)
    with (
        assert_no_workspace_mutation(tmp_path),
        pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"),
    ):
        _mutate(workspace, question_id, **changes)


@pytest.mark.parametrize("scope", ["project", "proposal"])
def test_revision_conflicts_do_not_write(tmp_path: Path, scope: str) -> None:
    workspace, question_id = _workspace(tmp_path)
    proposal_id = _proposal(workspace) if scope == "proposal" else None
    with (
        assert_no_workspace_mutation(tmp_path),
        pytest.raises(ValueError, match="REVISION|STALE_PREVIEW"),
    ):
        _mutate(
            workspace,
            "Q001" if proposal_id else question_id,
            scope=scope,
            proposal_id=proposal_id,
            expected_revision=2,
            answer="Owner answer",
        )


@pytest.mark.parametrize("scope", ["project", "proposal"])
def test_question_state_transitions_preserve_revisions(tmp_path: Path, scope: str) -> None:
    workspace, question_id = _workspace(tmp_path)
    proposal_id = _proposal(workspace) if scope == "proposal" else None
    question_id = "Q001" if proposal_id else question_id
    for leaf, revision, expected in [
        ("defer", 1, "defer" if scope == "proposal" else "deferred"),
        ("reopen", 2, "to_answer"),
        ("mute", 3, "muted"),
        ("reopen", 4, "to_answer"),
    ]:
        result = _mutate(
            workspace,
            question_id,
            scope=scope,
            proposal_id=proposal_id,
            leaf=leaf,
            expected_revision=revision,
            reason="Owner requested later review",
            operation_key=f"{scope}-{leaf}-{revision}",
        )
        assert result["question_mutation"]["questions"][0]["state"] == expected
        assert result["question_mutation"]["questions"][0]["revision"] == revision + 1


def test_proposal_apply_only_registers_plan_and_never_writes_proposal(tmp_path: Path) -> None:
    workspace, _ = _workspace(tmp_path)
    proposal_id = _proposal(workspace)
    _mutate(
        workspace,
        "Q001",
        scope="proposal",
        proposal_id=proposal_id,
        answer="Compare current and new",
        operation_key="proposal-answer",
    )
    path = workspace._proposal_question_service().find_proposal_dir(proposal_id) / "proposal.md"
    before = path.read_bytes()
    result = workspace.question_contract_service().mutate(
        scope="proposal",
        leaf="apply",
        proposal_id=proposal_id,
        question_ids=["Q001"],
        actor_id="owner",
        operation_key=KEY,
    )
    assert path.read_bytes() == before
    assert result["question_mutation"]["effect"] == "plan_registered"
    assert result["question_mutation"]["questions"][0]["application_effect"] == "plan_registered"
    assert workspace.read_proposal_questions(proposal_id).questions[0].apply_plan
    assert workspace.mutation_status(idempotency_key=KEY).state == "applied"


@pytest.mark.parametrize("leaf", ["apply", "reconcile"])
def test_project_preview_and_apply_use_exact_authority_and_receipt(
    tmp_path: Path, leaf: str
) -> None:
    workspace, question_id = _workspace(tmp_path)
    service = workspace.question_contract_service()
    if leaf == "apply":
        _mutate(workspace, question_id, operation_key="answer-before-apply")
    ids = [question_id] if leaf == "apply" else []
    with assert_no_workspace_mutation(tmp_path):
        preview = service.preview(leaf=leaf, question_ids=ids, actor_id="owner", operation_key=KEY)
    token = preview["question_preview"]["preview_token"]
    result = service.mutate(
        scope="project",
        leaf=leaf,
        question_ids=ids,
        actor_id="owner",
        operation_key=KEY,
        preview_token=token,
        confirm=True,
    )
    with assert_no_workspace_mutation(tmp_path):
        replay = service.mutate(
            scope="project",
            leaf=leaf,
            question_ids=ids,
            actor_id="owner",
            operation_key=KEY,
            preview_token=token,
            confirm=True,
        )
    assert replay["question_mutation"] == result["question_mutation"]
    assert (
        result["question_mutation"]["operation_id"]
        == QUESTION_OPERATIONS[f"project_question_{leaf}"][2]
    )
    assert workspace.mutation_status(idempotency_key=KEY).state == "applied"


def test_project_preview_becomes_stale_after_source_change(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    _mutate(workspace, question_id, operation_key="answer-before-apply")
    service = workspace.question_contract_service()
    token = service.preview(
        leaf="apply", question_ids=[question_id], actor_id="owner", operation_key=KEY
    )["question_preview"]["preview_token"]
    path = tmp_path / ".p2p/project/permissions.yml"
    path.write_bytes(path.read_bytes() + b"\n")
    with (
        assert_no_workspace_mutation(tmp_path),
        pytest.raises(ValueError, match="P2P_PREVIEW_STALE"),
    ):
        service.mutate(
            scope="project",
            leaf="apply",
            question_ids=[question_id],
            actor_id="owner",
            operation_key=KEY,
            preview_token=token,
            confirm=True,
        )


@pytest.mark.parametrize("basis", [AuthorityBasis.root_authority, AuthorityBasis.capability_grant])
def test_external_question_leaf_accepts_root_and_exact_grant(
    tmp_path: Path, basis: AuthorityBasis
) -> None:
    workspace, proposal_id = _external_workspace(tmp_path)
    workspace.add_proposal_question(
        proposal_id,
        gap="scope",
        question="Who is served?",
        priority=ProposalQuestionPriority.high,
        actor="local-maintainer",
    )
    claim = AuthorityClaim(
        "proposal.question.answer",
        basis,
        authority_generation=1 if basis == AuthorityBasis.root_authority else None,
        grant_ref="question-grant" if basis == AuthorityBasis.capability_grant else None,
        grant_generation=1 if basis == AuthorityBasis.capability_grant else None,
    )
    context = _external_context((claim,))
    result = _mutate(
        workspace,
        "Q001",
        scope="proposal",
        proposal_id=proposal_id,
        answer="Project audience",
        actor_id=context.subject.identity_id,
        executor_id=context.executor.identity_id,
        executor_kind=context.executor.kind.value,
        authority_context=context,
    )
    stored = workspace.read_proposal_questions(proposal_id).questions[0]
    assert stored.provided_by == context.subject.identity_id
    assert stored.recorded_by == context.executor.identity_id
    assert result["authority"]["claims"][0]["capability"] == "proposal.question.answer"
    with (
        assert_no_workspace_mutation(tmp_path),
        pytest.raises(ValueError, match="P2P_CAPABILITY_MISMATCH"),
    ):
        _mutate(
            workspace,
            "Q001",
            scope="proposal",
            proposal_id=proposal_id,
            leaf="mute",
            reason="Later",
            expected_revision=2,
            operation_key="different-leaf",
            actor_id=context.subject.identity_id,
            executor_id=context.executor.identity_id,
            executor_kind=context.executor.kind.value,
            authority_context=context,
        )


def test_question_worker_receipt_and_batch_are_attached_once(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    store = FilesystemProjectReplicationStore(tmp_path)
    store.initialize(authority_epoch=2, project_revision=1)
    command, command_path = _command(
        tmp_path,
        operation_id="op_question_answer",
        revision=1,
        idempotency_key=KEY,
        command_name="project.readiness.questions.answer",
        payload_contract="p2p-question-answer/v1",
    )
    arguments = [
        "--replication-command-envelope",
        str(command_path),
        "project",
        "readiness",
        "questions",
        "answer",
        question_id,
        "--value",
        "Owner answer",
        "--actor",
        "owner",
        "--expected-revision",
        "1",
        "--operation-key",
        KEY,
        "--format",
        "json",
        "--root",
        str(tmp_path),
    ]
    first = RUNNER.invoke(app, arguments)
    assert first.exit_code == 0, first.output
    data = cli_data(first)
    assert data["replication_receipt"]["status"] == "completed"
    assert store.state().current_revision == 2
    with assert_no_workspace_mutation(tmp_path):
        replay = RUNNER.invoke(app, arguments)
    assert replay.exit_code == 0, replay.output
    assert cli_data(replay)["replication_receipt"] == data["replication_receipt"]
    for changed in (
        replace(command, command="project.readiness.apply"),
        replace(command, operation_id="other_operation"),
        replace(command, idempotency_key="other-key"),
        replace(command, payload={"answer": "different envelope"}),
    ):
        command_path.write_bytes(canonical_json_bytes(changed.to_dict()))
        with assert_no_workspace_mutation(tmp_path):
            conflict = RUNNER.invoke(app, arguments)
        assert conflict.exit_code != 0
        assert cli_error(conflict)["code"].startswith("P2P_REPLICATION_")
    assert store.state().current_revision == 2


def test_cli_proposal_keyed_answer_and_status_contract(tmp_path: Path) -> None:
    workspace, _ = _workspace(tmp_path)
    proposal_id = _proposal(workspace)
    result = RUNNER.invoke(
        app,
        [
            "proposal",
            "questions",
            "answer",
            proposal_id,
            "Q001",
            "Owner answer",
            "--actor",
            "owner",
            "--expected-revision",
            "1",
            "--operation-key",
            KEY,
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert cli_data(result)["question_mutation"]["questions"][0]["revision"] == 2
    page = RUNNER.invoke(
        app,
        [
            "proposal",
            "questions",
            "status",
            proposal_id,
            "--format",
            "json",
            "--limit",
            "1",
            "--root",
            str(tmp_path),
        ],
    )
    assert page.exit_code == 0, page.output
    assert cli_data(page)["question_page"]["items"][0]["id"] == "Q001"


def test_cli_context_without_key_is_fail_closed(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    with assert_no_workspace_mutation(tmp_path):
        result = RUNNER.invoke(
            app,
            [
                "project",
                "readiness",
                "questions",
                "answer",
                question_id,
                "--value",
                "Owner answer",
                "--actor",
                "owner",
                "--expected-revision",
                "1",
                "--executor",
                "worker",
                "--format",
                "json",
                "--root",
                str(tmp_path),
            ],
        )
    assert cli_error(result)["code"] == "P2P_IDEMPOTENCY_KEY_REQUIRED"


@pytest.mark.parametrize(
    "changes",
    [
        {"values": {"value": "x" * 8001}},
        {"evidence_refs": ["x" * 513]},
        {"question_ids": ["Q001"] * 33},
    ],
)
def test_machine_question_limits_fail_before_writes(
    tmp_path: Path, changes: dict[str, object]
) -> None:
    workspace, question_id = _workspace(tmp_path)
    with (
        assert_no_workspace_mutation(tmp_path),
        pytest.raises(ValueError, match="P2P_QUESTION_LIMIT_INVALID"),
    ):
        _mutate(workspace, question_id, **changes)


def test_receipt_rejects_forged_question_result(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    result = _mutate(workspace, question_id)["question_mutation"]
    result = {
        **result,
        "changed_paths": [".p2p/project/questions.yml"],
        "effect": "proposal_written",
    }
    with pytest.raises(ValueError, match="effect"):
        validate_question_mutation_result(result, operation="project_question_answer")


def test_question_partial_commit_uses_existing_recovery(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    service = workspace.question_contract_service()

    interrupted: list[str] = []

    def fail_after_receipt(stage: str, path: str) -> None:
        if stage == "after_replace" and not interrupted:
            interrupted.append(path)
            (tmp_path / path).write_bytes(b"external edit prevents rollback")
            raise RuntimeError("simulated replacement interruption")

    service.writer = AtomicMutationWriter(
        root=tmp_path, p2p_dir=tmp_path / ".p2p", failure_injector=fail_after_receipt
    )
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_INCOMPLETE_TRANSACTION"):
        service.mutate(
            scope="project",
            leaf="answer",
            question_id=question_id,
            expected_revision=1,
            values={"value": "Owner answer"},
            operation_key=KEY,
            actor_id="owner",
        )
    status = workspace.mutation_status(idempotency_key=KEY)
    assert status.state == "incomplete" and status.recovery_required
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_INCOMPLETE_TRANSACTION"):
        _mutate(workspace, question_id)
    transaction = (
        tmp_path / ".p2p/.internal/workspace-transactions/transactions" / status.transaction_id
    )
    (tmp_path / interrupted[0]).write_bytes(
        (transaction / "candidates" / interrupted[0]).read_bytes()
    )
    recovery = WorkspaceTransactionRecoveryService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    assert (
        recovery.resume(transaction_id=status.transaction_id, actor="owner", confirm=True).status
        == "applied"
    )
    with assert_no_workspace_mutation(tmp_path):
        replay = _mutate(workspace, question_id)
    assert replay["mutation"]["replayed"]
    assert workspace.project_question(question_id).revision == 2


def test_question_replay_precedes_changed_authority(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    first = _mutate(workspace, question_id)
    preview = workspace.preview_project_authority_rotation(
        operation_key="rotate-question-authority",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        display_name="Rotated authority",
        rotated_at="2026-10-05T12:00:00Z",
    )
    workspace.apply_project_authority_rotation(
        operation_key="rotate-question-authority",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        display_name="Rotated authority",
        rotated_at="2026-10-05T12:00:00Z",
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    with assert_no_workspace_mutation(tmp_path):
        replay = _mutate(workspace, question_id)
    assert replay["question_mutation"] == first["question_mutation"]
    assert replay["authority"] == first["authority"]


def test_question_authority_source_is_rechecked_under_writer_lock(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    service = workspace.question_contract_service()
    permissions = tmp_path / ".p2p/project/permissions.yml"
    before = (tmp_path / ".p2p/project/questions.yml").read_bytes()

    def change_authority(stage: str, target: str) -> None:
        if stage == "before_final_source_recheck":
            permissions.write_bytes(permissions.read_bytes() + b"\n")

    service.writer = AtomicMutationWriter(
        root=tmp_path, p2p_dir=tmp_path / ".p2p", failure_injector=change_authority
    )
    with pytest.raises(ValueError, match="MUTATION_FAILED"):
        service.mutate(
            scope="project",
            leaf="answer",
            question_id=question_id,
            expected_revision=1,
            values={"value": "Owner answer"},
            operation_key=KEY,
            actor_id="owner",
        )
    assert (tmp_path / ".p2p/project/questions.yml").read_bytes() == before
    assert workspace.mutation_status(idempotency_key=KEY).state == "not_found"


def test_worker_failure_rolls_back_question_receipt_and_batch(tmp_path: Path) -> None:
    from p2p_engine.services.project_replication import set_replication_command

    workspace, question_id = _workspace(tmp_path)
    service = workspace.question_contract_service()
    store = FilesystemProjectReplicationStore(tmp_path)
    store.initialize(authority_epoch=2, project_revision=1)
    command, _ = _command(
        tmp_path,
        operation_id="op_question_failure",
        revision=1,
        idempotency_key=KEY,
        command_name="project.readiness.questions.answer",
        payload_contract="p2p-question-answer/v1",
    )

    def fail(stage: str, target: str) -> None:
        if stage == "after_replace":
            raise RuntimeError("simulated worker failure")

    service.writer = AtomicMutationWriter(
        root=tmp_path, p2p_dir=tmp_path / ".p2p", failure_injector=fail
    )
    set_replication_command(command)
    try:
        with pytest.raises(ValueError, match="MUTATION_FAILED"):
            service.mutate(
                scope="project",
                leaf="answer",
                question_id=question_id,
                expected_revision=1,
                values={"value": "Owner answer"},
                operation_key=KEY,
                actor_id="owner",
            )
    finally:
        set_replication_command(None)
    assert workspace.project_question(question_id).revision == 1
    assert workspace.mutation_status(idempotency_key=KEY).state == "not_found"
    assert store.receipt(command.operation_id) is None
    assert store.state().current_revision == 1


def test_bounded_page_truncates_legacy_long_text_without_touching_state(tmp_path: Path) -> None:
    workspace, _ = _workspace(tmp_path)
    proposal_id = _proposal(workspace)
    path = workspace._proposal_question_service().find_proposal_dir(proposal_id) / "questions.yml"
    payload = yaml.safe_load(path.read_bytes())
    original = payload["proposal_questions"]["questions"][0]
    original["question"] = "Q" * 9000
    original["answer"] = "A" * 16000
    for index in range(2, 12):
        payload["proposal_questions"]["questions"].append({**original, "id": f"Q{index:03d}"})
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with assert_no_workspace_mutation(tmp_path):
        page = workspace.question_contract_service().page(
            scope="proposal", proposal_id=proposal_id, limit=100
        )["question_page"]
    assert len(canonical_json_bytes(page)) <= 48 * 1024
    assert page["page"]["has_more"] is True
    assert page["page"]["next_offset"] == len(page["items"])
    assert page["items"][0]["truncated_fields"] == ["answer", "question"]
    assert len(page["items"][0]["question"]) == 2000


@pytest.mark.parametrize(
    "change", [{"revision": True}, {"unknown": "secret"}, {"state": "applied"}]
)
def test_receipt_rejects_invalid_question_projection(
    tmp_path: Path, change: dict[str, object]
) -> None:
    workspace, question_id = _workspace(tmp_path)
    result = _mutate(workspace, question_id)["question_mutation"]
    result = {
        **result,
        "changed_paths": [".p2p/project/questions.yml"],
        "questions": [{**result["questions"][0], **change}],
    }
    with pytest.raises(ValueError):
        validate_question_mutation_result(result, operation="project_question_answer")


@pytest.mark.parametrize(
    "invalid", ["symlink", "parent_symlink", "oversize", "traversal", "bool_revision", "duplicate"]
)
def test_external_answer_input_rejects_unsafe_or_invalid_contract(
    tmp_path: Path, invalid: str
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    payload = {
        "project_question_answer": {
            "schema_version": 1,
            "question_id": "PRQ-question",
            "expected_revision": 1,
            "values": {"value": "Owner answer"},
            "evidence_refs": [],
        }
    }
    source = tmp_path / "server-answer.yml"
    source.write_text(yaml.safe_dump(payload), encoding="utf-8")
    if invalid == "symlink":
        link = tmp_path / "link.yml"
        link.symlink_to(source)
        source = link
    elif invalid == "parent_symlink":
        staging = tmp_path / "staging"
        staging.mkdir()
        (staging / "answer.yml").write_text(yaml.safe_dump(payload), encoding="utf-8")
        link = tmp_path / "linked"
        link.symlink_to(staging, target_is_directory=True)
        source = link / "answer.yml"
    elif invalid == "oversize":
        source.write_text("X" * (65536 + 1), encoding="utf-8")
    elif invalid == "traversal":
        source = root / ".." / source.name
    elif invalid == "bool_revision":
        payload["project_question_answer"]["expected_revision"] = True
        source.write_text(yaml.safe_dump(payload), encoding="utf-8")
    else:
        source.write_text(
            source.read_text(encoding="utf-8") + "project_question_answer: {}\n", encoding="utf-8"
        )
    with pytest.raises(ValueError):
        _load_answer_file(
            root,
            source,
            question_id="PRQ-question",
            expected_revision=1,
            allow_external=True,
            strict=True,
        )


def test_external_answer_input_preserves_legacy_root_boundary(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    source = tmp_path / "server-answer.yml"
    source.write_text(
        yaml.safe_dump(
            {
                "project_question_answer": {
                    "schema_version": 1,
                    "question_id": "PRQ-question",
                    "expected_revision": 1,
                    "values": {"value": "Owner answer"},
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="inside the project root"):
        _load_answer_file(root, source, question_id="PRQ-question", expected_revision=1)
    assert _load_answer_file(
        root,
        source,
        question_id="PRQ-question",
        expected_revision=1,
        allow_external=True,
        strict=True,
    ) == ({"value": "Owner answer"}, ())


def test_cli_external_structured_answer_records_subject_and_executor(tmp_path: Path) -> None:
    root = tmp_path / "project"
    workspace, _ = _external_workspace(root)
    question = next(
        item
        for item in workspace.question_contract_service().project.read().questions
        if item.answer_contract.kind.value == "field_value"
    )
    context = _external_context(
        (
            AuthorityClaim(
                "project.question.answer",
                AuthorityBasis.capability_grant,
                grant_ref="project-question-grant",
                grant_generation=1,
            ),
        )
    )
    context_path = tmp_path / "authority.json"
    context_path.write_bytes(canonical_json_bytes(context.to_dict()))
    answer_path = tmp_path / "answer.json"
    answer_path.write_bytes(
        canonical_json_bytes(
            {
                "project_question_answer": {
                    "schema_version": 1,
                    "question_id": question.question_id,
                    "expected_revision": question.revision,
                    "values": {"value": "Externally supplied owner answer"},
                    "evidence_refs": ["note:source"],
                }
            }
        )
    )
    arguments = [
        "project",
        "readiness",
        "questions",
        "answer",
        question.question_id,
        "--input",
        str(answer_path),
        "--actor",
        context.subject.identity_id,
        "--executor",
        context.executor.identity_id,
        "--executor-kind",
        context.executor.kind.value,
        "--authority-context",
        str(context_path),
        "--expected-revision",
        str(question.revision),
        "--operation-key",
        KEY,
        "--format",
        "json",
        "--root",
        str(root),
    ]
    result = RUNNER.invoke(app, arguments)
    assert result.exit_code == 0, result.output
    answer = cli_data(result)["question_mutation"]["questions"][0]["answer"]
    assert answer["provided_by"] == context.subject.identity_id
    assert answer["recorded_by"] == context.executor.identity_id
    with assert_no_workspace_mutation(root):
        replay = RUNNER.invoke(app, arguments)
    assert replay.exit_code == 0, replay.output
    assert cli_data(replay)["mutation"]["replayed"] is True


def test_proposal_decide_capability_does_not_authorize_question_answer(tmp_path: Path) -> None:
    workspace, proposal_id = _external_workspace(tmp_path)
    workspace.add_proposal_question(
        proposal_id,
        gap="scope",
        question="Who is served?",
        priority=ProposalQuestionPriority.high,
        actor="local-maintainer",
    )
    context = _external_context(
        (AuthorityClaim("proposal.decide", AuthorityBasis.root_authority, authority_generation=1),)
    )
    with (
        assert_no_workspace_mutation(tmp_path),
        pytest.raises(ValueError, match="P2P_CAPABILITY_MISMATCH"),
    ):
        _mutate(
            workspace,
            "Q001",
            scope="proposal",
            proposal_id=proposal_id,
            answer="Owner answer",
            actor_id=context.subject.identity_id,
            executor_id=context.executor.identity_id,
            executor_kind=context.executor.kind.value,
            authority_context=context,
        )


def test_local_contributor_cannot_mutate_questions(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    with (
        assert_no_workspace_mutation(tmp_path),
        pytest.raises(ValueError, match="P2P_AUTHORIZATION_DENIED"),
    ):
        _mutate(workspace, question_id, actor_id="contributor")


def test_cli_keyed_revision_conflict_uses_conflict_exit_class(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    with assert_no_workspace_mutation(tmp_path):
        result = RUNNER.invoke(
            app,
            [
                "project",
                "readiness",
                "questions",
                "answer",
                question_id,
                "--value",
                "Owner answer",
                "--actor",
                "owner",
                "--expected-revision",
                "2",
                "--operation-key",
                KEY,
                "--format",
                "json",
                "--root",
                str(tmp_path),
            ],
        )
    assert result.exit_code == 3
    assert cli_error(result)["code"] == "P2P_QUESTION_REVISION_CONFLICT"


def test_cli_release_contract_inventory_includes_question_dimensions(tmp_path: Path) -> None:
    result = RUNNER.invoke(app, ["version", "--format", "json"])
    assert result.exit_code == 0, result.output
    inventory = cli_data(result)
    assert inventory["question_page_contract"] == "p2p-question-page/v1"
    assert inventory["question_next_contract"] == "p2p-question-next/v1"
    assert inventory["question_preview_contract"] == "p2p-question-preview/v1"
    assert inventory["question_mutation_contract"] == "p2p-question-mutation-result/v1"


def test_cli_hosted_unkeyed_json_question_write_is_fail_closed(tmp_path: Path) -> None:
    workspace, _ = _external_workspace(tmp_path)
    question = next(
        item
        for item in workspace.question_contract_service().project.read().questions
        if item.answer_contract.kind.value == "field_value"
    )
    with assert_no_workspace_mutation(tmp_path):
        result = RUNNER.invoke(
            app,
            [
                "project",
                "readiness",
                "questions",
                "answer",
                question.question_id,
                "--value",
                "Owner answer",
                "--actor",
                "local-maintainer",
                "--expected-revision",
                str(question.revision),
                "--format",
                "json",
                "--root",
                str(tmp_path),
            ],
        )
    assert result.exit_code == 4
    assert cli_error(result)["code"] == "P2P_AUTHORITY_CONTEXT_REQUIRED"


def test_projection_clamps_legacy_identity_evidence_and_nonfinite_values(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    _mutate(workspace, question_id)
    question = workspace.project_question(question_id)
    answer = replace(
        question.answers[-1],
        provided_by="P" * 600,
        recorded_by="R" * 600,
        evidence_refs=("E" * 600,),
        values={"value": float("inf")},
    )
    projected = question_projection(replace(question, answers=(answer,)), scope="project")
    validate_question_projection(projected, scope="project")
    assert len(projected["answer"]["provided_by"]) == 512
    assert len(projected["answer"]["recorded_by"]) == 512
    assert len(projected["answer"]["evidence_refs"][0]) == 512
    assert projected["answer"]["values"]["value"] is None
    assert projected["truncated_fields"] == ["answer"]
    proposal_id = _proposal(workspace)
    proposal_question = workspace.read_proposal_questions(proposal_id).questions[0]
    projected = question_projection(
        replace(
            proposal_question, group_id="G" * 600, provided_by="P" * 600, recorded_by="R" * 600
        ),
        scope="proposal",
    )
    validate_question_projection(projected, scope="proposal")
    assert all(len(projected[field]) == 512 for field in ("group_id", "provided_by", "recorded_by"))


@pytest.mark.parametrize("changes", [{"limit": True}, {"offset": True}])
def test_page_rejects_boolean_pagination(tmp_path: Path, changes: dict[str, object]) -> None:
    workspace, _ = _workspace(tmp_path)
    with (
        assert_no_workspace_mutation(tmp_path),
        pytest.raises(ValueError, match="P2P_QUESTION_LIMIT_INVALID"),
    ):
        workspace.question_contract_service().page(scope="project", **changes)

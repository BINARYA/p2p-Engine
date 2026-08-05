from __future__ import annotations

import threading
from pathlib import Path

import pytest

import p2p_engine.services.workspace_transactions as workspace_transactions
from p2p_engine.core.mutation_preview import MutationPreviewService, semantic_sha256, source_precondition
from p2p_engine.services.workspace_transactions import (
    AtomicMutationWriter,
    WorkspaceTransactionLockService,
    WorkspaceTransactionRecoveryService,
)


def test_preview_token_context_is_opt_in_and_preserves_existing_token_contract() -> None:
    source = source_precondition(".p2p/project/definition.yml", b"before")
    semantics = {"definition": {"status": "partial"}}
    expected = semantic_sha256(
        {
            "operation_id": "definition",
            "targets": [".p2p/project/definition.yml"],
            "sources": [source.to_dict()],
            "candidate_semantics": semantics,
            "policy_version": 1,
        }
    )

    legacy = MutationPreviewService.token(
        operation_id="definition",
        targets=(".p2p/project/definition.yml",),
        sources=(source,),
        candidate_semantics=semantics,
    )
    contextual = MutationPreviewService.token(
        operation_id="definition",
        targets=(".p2p/project/definition.yml",),
        sources=(source,),
        candidate_semantics=semantics,
        token_context={"actor": "owner"},
    )

    assert legacy == expected
    assert contextual != legacy


def test_workspace_lock_is_invisible_until_its_payload_is_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WorkspaceTransactionLockService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    publication_ready = threading.Event()
    allow_publication = threading.Event()
    original_link = workspace_transactions.os.link
    failures: list[BaseException] = []

    def delayed_link(source, target, *args, **kwargs):
        publication_ready.set()
        if not allow_publication.wait(timeout=5):
            raise RuntimeError("lock publication test timed out")
        return original_link(source, target, *args, **kwargs)

    def acquire() -> None:
        try:
            service.acquire("mutation-test-atomic-publication", owner="owner")
        except BaseException as exc:  # noqa: BLE001 - thread boundary captures diagnostics
            failures.append(exc)

    monkeypatch.setattr(workspace_transactions.os, "link", delayed_link)
    thread = threading.Thread(target=acquire)
    thread.start()
    assert publication_ready.wait(timeout=5)
    try:
        observed = service.status()
        assert observed.state == "absent"
        assert not service.lock_path.exists()
    finally:
        allow_publication.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert failures == []
    published = service.status()
    assert published.state == "active"
    assert published.transaction_id == "mutation-test-atomic-publication"
    service.release(published.transaction_id)


def test_workspace_lock_writer_retries_partial_os_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WorkspaceTransactionLockService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    original_write = workspace_transactions.os.write
    write_calls = 0

    def partial_write(descriptor: int, content) -> int:
        nonlocal write_calls
        write_calls += 1
        return original_write(descriptor, content[:3])

    monkeypatch.setattr(workspace_transactions.os, "write", partial_write)
    acquired = service.acquire("mutation-test-partial-write", owner="owner")
    observed = service.status()

    assert write_calls > 1
    assert observed.state == "active"
    assert observed.transaction_id == acquired.transaction_id
    assert observed.owner == "owner"
    service.release(acquired.transaction_id)


def test_workspace_lock_disappearing_during_read_is_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WorkspaceTransactionLockService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    service.acquire("mutation-test-disappearing-lock", owner="owner")
    original_read_text = Path.read_text

    def disappearing_read(path: Path, *args, **kwargs):
        if path == service.lock_path:
            path.unlink()
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", disappearing_read)

    assert service.status().state == "absent"


def test_workspace_lock_contention_preserves_winner_and_leaves_no_temporary_file(
    tmp_path: Path,
) -> None:
    service = WorkspaceTransactionLockService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    acquired = service.acquire("mutation-test-winner", owner="winner")

    with pytest.raises(ValueError, match="P2P_WORKSPACE_TRANSACTION_LOCKED"):
        service.acquire("mutation-test-loser", owner="loser")

    observed = service.status()
    assert observed.state == "active"
    assert observed.transaction_id == acquired.transaction_id
    assert list(service.transaction_root.glob(".apply.lock.*.tmp")) == []
    service.release(acquired.transaction_id)


def test_workspace_lock_malformed_payload_remains_invalid(tmp_path: Path) -> None:
    service = WorkspaceTransactionLockService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    service.transaction_root.mkdir(parents=True)
    service.lock_path.write_text("not: [valid", encoding="utf-8")

    observed = service.status()

    assert observed.state == "invalid"
    assert "Cannot parse workspace transaction lock" in observed.message


def test_atomic_writer_rechecks_non_target_sources_under_lock(tmp_path: Path) -> None:
    target = tmp_path / ".p2p" / "project" / "questions.yml"
    non_target = tmp_path / ".p2p" / "project" / "permissions.yml"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"before")
    non_target.write_bytes(b"owner")
    sources = (
        source_precondition(".p2p/project/questions.yml", target.read_bytes()),
        source_precondition(".p2p/project/permissions.yml", non_target.read_bytes()),
    )
    non_target.write_bytes(b"changed")

    result = AtomicMutationWriter(root=tmp_path, p2p_dir=tmp_path / ".p2p").apply(
        operation_id="convergence",
        candidates={".p2p/project/questions.yml": b"after"},
        sources=sources,
        preview_token="token",
        actor="owner",
    )

    assert result.status == "failed"
    assert "source changed" in result.message
    assert target.read_bytes() == b"before"


def test_atomic_writer_candidate_validator_reads_overlay_before_journal(tmp_path: Path) -> None:
    target = tmp_path / ".p2p" / "project" / "questions.yml"
    preserved = tmp_path / ".p2p" / "project" / "permissions.yml"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"before")
    preserved.write_bytes(b"owner")
    seen: list[tuple[bytes, bytes]] = []

    def validate(view) -> None:
        seen.append(
            (
                view.read_bytes(".p2p/project/questions.yml"),
                view.read_bytes(".p2p/project/permissions.yml"),
            )
        )
        raise ValueError("candidate rejected")

    result = AtomicMutationWriter(root=tmp_path, p2p_dir=tmp_path / ".p2p").apply(
        operation_id="convergence",
        candidates={".p2p/project/questions.yml": b"after"},
        sources=(
            source_precondition(".p2p/project/questions.yml", target.read_bytes()),
            source_precondition(".p2p/project/permissions.yml", preserved.read_bytes()),
        ),
        preview_token="token",
        actor="owner",
        candidate_validator=validate,
    )

    assert result.status == "failed"
    assert seen == [(b"after", b"owner")]
    assert target.read_bytes() == b"before"


@pytest.mark.parametrize(
    "failed_stage",
    [
        "after_source_recheck",
        "before_staging",
        "before_candidate_validation",
        "after_candidate_validation",
        "before_journal",
        "after_journal",
    ],
)
def test_atomic_writer_precommit_failures_leave_no_state_or_recovery_lock(
    tmp_path: Path,
    failed_stage: str,
) -> None:
    target = tmp_path / ".p2p" / "project" / "questions.yml"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"before")

    def fail(stage: str, _target: str) -> None:
        if stage == failed_stage:
            raise RuntimeError("injected precommit failure")

    result = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=fail,
    ).apply(
        operation_id="convergence",
        candidates={".p2p/project/questions.yml": b"after"},
        sources=(source_precondition(".p2p/project/questions.yml", target.read_bytes()),),
        preview_token="token",
        actor="owner",
        candidate_validator=lambda view: view.read_bytes(".p2p/project/questions.yml"),
    )

    assert result.status == "failed"
    assert target.read_bytes() == b"before"
    assert not (tmp_path / ".p2p" / ".internal" / "workspace-transactions" / "apply.lock").exists()
    transactions = tmp_path / ".p2p" / ".internal" / "workspace-transactions" / "transactions"
    assert not transactions.exists() or not any(transactions.iterdir())


def test_interrupted_atomic_mutation_can_be_rolled_back_explicitly(tmp_path: Path) -> None:
    target = tmp_path / ".p2p" / "project" / "questions.yml"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"before")

    def interrupt(stage: str, _target: str) -> None:
        if stage == "after_replace":
            target.write_bytes(b"external")
            raise RuntimeError("injected interruption")

    result = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=interrupt,
    ).apply(
        operation_id="question-update",
        candidates={".p2p/project/questions.yml": b"after"},
        sources=(source_precondition(".p2p/project/questions.yml", b"before"),),
        preview_token="rollback-token",
        actor="owner",
    )
    recovery = WorkspaceTransactionRecoveryService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
    )
    status = recovery.status()

    assert result.status == "recovery_required"
    assert status.required is True
    assert status.available_actions == ("rollback", "resume")
    target.write_bytes(b"after")

    rolled_back = recovery.rollback(
        transaction_id=status.transaction_id,
        actor="owner",
        confirm=True,
    )

    assert rolled_back.status == "rolled_back"
    assert target.read_bytes() == b"before"
    assert recovery.status().required is False


def test_interrupted_atomic_mutation_can_resume_remaining_targets(tmp_path: Path) -> None:
    first = tmp_path / ".p2p" / "project" / "definition.yml"
    second = tmp_path / ".p2p" / "project" / "questions.yml"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"definition-before")
    second.write_bytes(b"questions-before")

    def interrupt(stage: str, relative: str) -> None:
        if stage == "after_replace" and relative == ".p2p/project/definition.yml":
            first.write_bytes(b"external")
            raise RuntimeError("injected interruption")

    result = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=interrupt,
    ).apply(
        operation_id="definition-and-questions",
        candidates={
            ".p2p/project/definition.yml": b"definition-after",
            ".p2p/project/questions.yml": b"questions-after",
        },
        sources=(
            source_precondition(".p2p/project/definition.yml", b"definition-before"),
            source_precondition(".p2p/project/questions.yml", b"questions-before"),
        ),
        preview_token="resume-token",
        actor="owner",
    )
    recovery = WorkspaceTransactionRecoveryService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
    )
    status = recovery.status()

    assert result.status == "recovery_required"
    first.write_bytes(b"definition-after")

    resumed = recovery.resume(
        transaction_id=status.transaction_id,
        actor="owner",
        confirm=True,
    )

    assert resumed.status == "applied"
    assert first.read_bytes() == b"definition-after"
    assert second.read_bytes() == b"questions-after"
    assert recovery.status().required is False

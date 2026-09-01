from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from p2p_engine.cli import app as cli_app
from p2p_engine.core.canonical_memory import canonical_json_bytes
from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    ProjectStateMutation,
    ProjectStorageError,
    ProjectStorageErrorCode,
)
from p2p_engine.foundation.files import write_bytes_atomic
from p2p_engine.services.project_application import (
    open_project_application,
    project_memory_recovery_apply,
    project_memory_recovery_status,
)
from p2p_engine.services.workspace_transactions import WorkspaceTransactionLockService
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.project_storage import ProjectStorageManifestStore
from p2p_engine.storage.sqlite_adapter import SQLiteBackupPort
from p2p_engine.storage.sqlite_recovery import (
    SQLITE_ACTIVATION_CONTRACT,
    SQLITE_ACTIVATION_MARKER,
    SQLITE_MAINTENANCE_CONTRACT,
    SQLITE_RECOVERY_COMPLETION_CONTRACT,
    SQLITE_RECOVERY_COMPLETION_ROOT,
    SQLiteRecoveryCoordinator,
    new_sqlite_recovery_identity,
    write_sqlite_auxiliary_backup,
)
from p2p_engine.storage.sqlite_schema import (
    SQLITE_ADAPTER,
    SQLITE_DATABASE_PATH,
    SQLITE_MAINTENANCE_MARKER,
)


def _initialize(root: Path, *, adapter: str = SQLITE_ADAPTER):
    P2PWorkspace(root).init_project(
        "SQLite recovery contract",
        owner="owner",
        agent_profile="generic",
        storage_adapter=adapter,
    )
    return open_project_application(root)


def _backup_database(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(target) as target_connection:
            source_connection.backup(target_connection)


def _symlink_or_skip(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:  # pragma: no cover - depends on Windows runner policy.
        pytest.skip(f"symlink creation is unavailable: {exc}")


def _auxiliary_entry(root: Path, relative: Path) -> dict[str, object]:
    content = (root / relative).read_bytes()
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


@pytest.mark.parametrize(
    "relative",
    (
        ".p2p/local/project.sqlite3.",
        ".p2p/local/project.sqlite3 ",
        ".p2p/local/value:stream",
        ".p2p/local/CON",
        ".p2p/local/CONOUT$.txt",
        ".p2p/local/com1.txt",
        ".p2p/local/lpt¹.log",
        ".p2p/local/question?.yml",
        ".p2p/local//duplicated-separator.yml",
    ),
)
def test_recovery_rejects_portably_ambiguous_auxiliary_paths(
    tmp_path: Path,
    relative: str,
) -> None:
    from p2p_engine.storage import sqlite_recovery as recovery_module

    root = tmp_path / "project"
    root.mkdir()

    with pytest.raises(ValueError, match="safe relative path"):
        recovery_module._safe_auxiliary_path(root, relative)


def test_recovery_accepts_portable_auxiliary_path(tmp_path: Path) -> None:
    from p2p_engine.storage import sqlite_recovery as recovery_module

    root = tmp_path / "project"
    root.mkdir()

    result = recovery_module._safe_auxiliary_path(
        root,
        ".p2p/local/preferences.yml",
    )

    assert result == root / ".p2p/local/preferences.yml"


@pytest.mark.parametrize(
    "relative",
    (
        ".p2p/local/PROJECT.SQLITE3",
        ".p2p/local/PROJECT.SQLITE3-WAL",
        ".p2p/local/SQLITE-MAINTENANCE.JSON",
        ".p2p/local/SQLITE-ACTIVATION.JSON",
        ".p2p/local/STORAGE.YML",
    ),
)
def test_recovery_rejects_casefolded_windows_aliases_of_reserved_state(
    tmp_path: Path,
    relative: str,
) -> None:
    from p2p_engine.storage import sqlite_recovery as recovery_module

    root = tmp_path / "project"
    root.mkdir()

    with pytest.raises(ValueError, match="reserved"):
        recovery_module._safe_auxiliary_path(root, relative)


def _maintenance_marker(
    root: Path,
    *,
    operation: str = "restore",
    auxiliary_backup: str = "",
    auxiliary_remove: list[dict[str, object]] | None = None,
    auxiliary_target: list[dict[str, object]] | None = None,
    transaction_id: str = "",
) -> tuple[str, str]:
    app = open_project_application(root)
    snapshot = app.canonical_memory_snapshot()
    recovery_id, recovery_token = new_sqlite_recovery_identity()
    operation_prefix = {
        "restore": ("sqlite-restore", "sqlite-recovery"),
        "identity-transition": ("sqlite-identity", "sqlite-pre-identity"),
    }[operation]
    recovery = (
        root
        / ".p2p/backups"
        / f"{operation_prefix[1]}-{recovery_id}.sqlite3"
    )
    _backup_database(root / SQLITE_DATABASE_PATH, recovery)
    stage = root / ".p2p/local" / f"{operation_prefix[0]}-{recovery_id}.stage"
    stage.mkdir(parents=True)
    payload: dict[str, object] = {
        "contract": SQLITE_MAINTENANCE_CONTRACT,
        "recovery_id": recovery_id,
        "recovery_token": recovery_token,
        "operation": operation,
        "phase": "old_moved",
        "actor": "owner",
        "transaction_id": transaction_id or f"sqlite-test-{recovery_id}",
        "source": {
            "project_uuid": snapshot.project_uuid,
            "semantic_state_digest": snapshot.semantic_state_digest,
        },
        "target": {
            "project_uuid": snapshot.project_uuid,
            "semantic_state_digest": snapshot.semantic_state_digest,
        },
        "stage": stage.relative_to(root).as_posix(),
        "recovery": recovery.relative_to(root).as_posix(),
    }
    payload["blob_changes"] = []
    if operation == "identity-transition":
        expected_backup = (
            root
            / ".p2p/backups"
            / f"sqlite-pre-identity-{recovery_id}.aux"
        )
        if auxiliary_backup:
            supplied_backup = root / auxiliary_backup
            os.replace(supplied_backup, expected_backup)
        else:
            write_sqlite_auxiliary_backup(
                root,
                expected_backup.relative_to(root),
                {},
            )
        backup_manifest = json.loads(
            (expected_backup / "manifest.json").read_bytes()
        )
        payload["auxiliary_backup"] = expected_backup.relative_to(root).as_posix()
        payload["auxiliary_remove"] = auxiliary_remove or []
        payload["auxiliary_source"] = [
            {
                "path": item["path"],
                "sha256": item["sha256"],
                "size": item["size"],
            }
            for item in backup_manifest["files"]
        ]
        payload["auxiliary_target"] = auxiliary_target or auxiliary_remove or []
    write_bytes_atomic(
        root / SQLITE_MAINTENANCE_MARKER,
        canonical_json_bytes(payload),
    )
    with sqlite3.connect(root / SQLITE_DATABASE_PATH) as connection:
        connection.execute(
            "UPDATE storage_metadata SET maintenance_state = 'restoring' "
            "WHERE singleton = 1"
        )
    return recovery_id, recovery_token


def test_restore_recovery_is_owner_authorized_and_idempotent(tmp_path: Path) -> None:
    _initialize(tmp_path)
    recovery_id, recovery_token = _maintenance_marker(tmp_path)

    status = project_memory_recovery_status(tmp_path)
    assert status.state == "recovery_required"
    assert status.applicable is True
    assert status.allowed_actions == ("rollback",)
    assert status.recovery_id == recovery_id
    assert status.recovery_token == recovery_token

    with pytest.raises(ProjectStorageError, match="requires a source-project owner"):
        project_memory_recovery_apply(
            tmp_path,
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="contributor",
            confirm=True,
        )

    result = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )
    assert result.status == "rolled_back"
    assert result.replayed is False
    assert project_memory_recovery_status(tmp_path).state == "clean"
    assert ProjectStorageManifestStore(tmp_path).load().adapter == SQLITE_ADAPTER
    with sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH) as connection:
        state = connection.execute(
            "SELECT maintenance_state FROM storage_metadata WHERE singleton = 1"
        ).fetchone()
    assert state == ("ready",)

    replay = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )
    assert replay.replayed is True
    assert replay.semantic_state_digest == result.semantic_state_digest


def test_live_recovery_claim_uses_cross_platform_process_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _initialize(tmp_path)
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    claim = tmp_path / ".p2p-sqlite-recovery-apply.lock"
    claim.mkdir()
    write_bytes_atomic(
        claim / "owner.json",
        canonical_json_bytes(
            {
                "contract": "p2p-sqlite-recovery-claim/v2",
                "recovery_id": recovery_id,
                "pid": 424242,
            }
        ),
    )
    observed: list[int] = []

    def running(pid: int) -> bool:
        observed.append(pid)
        return True

    monkeypatch.setattr(
        "p2p_engine.storage.sqlite_recovery.pid_is_running",
        running,
    )

    with pytest.raises(ProjectStorageError) as raised:
        project_memory_recovery_apply(
            tmp_path,
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            confirm=True,
        )

    assert raised.value.code == ProjectStorageErrorCode.busy
    assert observed == [424242]
    assert claim.is_dir()


def test_stale_recovery_claim_is_replaced_through_cross_platform_process_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _initialize(tmp_path)
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    claim = tmp_path / ".p2p-sqlite-recovery-apply.lock"
    claim.mkdir()
    write_bytes_atomic(
        claim / "owner.json",
        canonical_json_bytes(
            {
                "contract": "p2p-sqlite-recovery-claim/v2",
                "recovery_id": recovery_id,
                "pid": 424243,
            }
        ),
    )
    observed: list[int] = []

    def stopped(pid: int) -> bool:
        observed.append(pid)
        return False

    monkeypatch.setattr(
        "p2p_engine.storage.sqlite_recovery.pid_is_running",
        stopped,
    )

    result = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert observed == [424243]
    assert not claim.exists()


def test_claim_cleanup_failure_cannot_leave_the_global_recovery_name_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_recovery

    _initialize(tmp_path)
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    original_rmtree = sqlite_recovery.shutil.rmtree

    def interrupted_tombstone_cleanup(path, *args, **kwargs) -> None:
        if str(path).endswith(".released"):
            return
        original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(
        sqlite_recovery.shutil,
        "rmtree",
        interrupted_tombstone_cleanup,
    )

    first = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )

    claim = tmp_path / ".p2p-sqlite-recovery-apply.lock"
    assert first.status == "rolled_back"
    assert not claim.exists()
    assert list(tmp_path.glob(".*.released"))

    replay = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )
    assert replay.replayed is True
    assert not claim.exists()


def test_forward_restore_marker_fences_an_already_staged_writer(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    source = tmp_path / "same-state.p2pbundle"
    app.canonical_bundle_export(source)
    snapshot = app.canonical_memory_snapshot()
    unit = app.project_state_unit_of_work()
    unit.stage(
        ProjectStateMutation(
            operation_id="writer-paused-during-forward-restore",
            actor="owner",
            expected_revision=app.project_state_revision(),
            target=snapshot,
        )
    )
    observed: list[ProjectStorageErrorCode] = []

    def inject(stage: str) -> None:
        if stage != "after_restore_activation":
            return
        with pytest.raises(ProjectStorageError) as raised:
            unit.commit()
        observed.append(raised.value.code)

    port = SQLiteBackupPort(app.adapter.repository, failure_injector=inject)
    preview = port.restore_preview(
        source=source,
        operation_key="restore-fences-staged-writer",
        actor="owner",
    )
    result = port.restore_apply(
        source=source,
        operation_key="restore-fences-staged-writer",
        actor="owner",
        preview_token=preview.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert observed == [ProjectStorageErrorCode.recovery_required]


def test_recovery_marker_fences_an_already_staged_writer_until_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _initialize(tmp_path)
    snapshot = app.canonical_memory_snapshot()
    unit = app.project_state_unit_of_work()
    unit.stage(
        ProjectStateMutation(
            operation_id="writer-paused-during-recovery",
            actor="owner",
            expected_revision=app.project_state_revision(),
            target=snapshot,
        )
    )
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    coordinator = SQLiteRecoveryCoordinator(tmp_path)
    original = coordinator._rollback_blob_changes
    observed: list[ProjectStorageErrorCode] = []

    def paused(marker) -> None:
        with pytest.raises(ProjectStorageError) as raised:
            unit.commit()
        observed.append(raised.value.code)
        original(marker)

    monkeypatch.setattr(coordinator, "_rollback_blob_changes", paused)

    result = coordinator.apply(
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        action="rollback",
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert observed == [ProjectStorageErrorCode.recovery_required]


def test_recovery_replay_rejects_tampered_completion_result(tmp_path: Path) -> None:
    _initialize(tmp_path)
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )
    completion = tmp_path / SQLITE_RECOVERY_COMPLETION_ROOT / f"{recovery_id}.json"
    payload = json.loads(completion.read_bytes())
    payload["result"]["action"] = "commit"
    write_bytes_atomic(completion, canonical_json_bytes(payload))

    with pytest.raises(ProjectStorageError) as raised:
        project_memory_recovery_apply(
            tmp_path,
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            confirm=True,
        )
    assert raised.value.code == ProjectStorageErrorCode.integrity_failure


def test_precreated_completion_cannot_skip_source_rollback(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    source = app.canonical_memory_snapshot()
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    live_database = tmp_path / SQLITE_DATABASE_PATH
    live_database.unlink()
    for suffix in ("-wal", "-shm", "-journal"):
        live_database.with_name(live_database.name + suffix).unlink(missing_ok=True)
    completion = tmp_path / SQLITE_RECOVERY_COMPLETION_ROOT / f"{recovery_id}.json"
    write_bytes_atomic(
        completion,
        canonical_json_bytes(
            {
                "contract": SQLITE_RECOVERY_COMPLETION_CONTRACT,
                "marker_sha256": hashlib.sha256(marker.read_bytes()).hexdigest(),
                "recovery_token": recovery_token,
                "completed_at": "2026-08-31T12:00:00Z",
                "result": {
                    "contract": "p2p-memory-recovery-result/v1",
                    "status": "rolled_back",
                    "recovery_id": recovery_id,
                    "operation": "restore",
                    "action": "rollback",
                    "actor": "owner",
                    "project_uuid": source.project_uuid,
                    "semantic_state_digest": source.semantic_state_digest,
                    "replayed": False,
                    "message": (
                        "Interrupted SQLite maintenance was rolled back to its "
                        "verified source state."
                    ),
                },
            }
        ),
    )

    result = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )

    assert result.replayed is True
    assert live_database.is_file()
    assert open_project_application(tmp_path).canonical_memory_snapshot() == source


def test_invalid_precreated_completion_is_quarantined_after_verified_rollback(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    completion = tmp_path / SQLITE_RECOVERY_COMPLETION_ROOT / f"{recovery_id}.json"
    invalid = b'{"contract":"attacker-controlled"\n'
    write_bytes_atomic(completion, invalid)

    result = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert project_memory_recovery_status(tmp_path).state == "clean"
    payload = json.loads(completion.read_bytes())
    assert payload["contract"] == SQLITE_RECOVERY_COMPLETION_CONTRACT
    quarantined = list(
        (completion.parent / "quarantine").glob(f"{recovery_id}-*.invalid")
    )
    assert len(quarantined) == 1
    assert quarantined[0].read_bytes() == invalid


def test_non_owner_precreated_completion_is_quarantined_after_verified_rollback(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    source = app.canonical_memory_snapshot()
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    completion = tmp_path / SQLITE_RECOVERY_COMPLETION_ROOT / f"{recovery_id}.json"
    write_bytes_atomic(
        completion,
        canonical_json_bytes(
            {
                "contract": SQLITE_RECOVERY_COMPLETION_CONTRACT,
                "marker_sha256": hashlib.sha256(marker.read_bytes()).hexdigest(),
                "recovery_token": recovery_token,
                "completed_at": "2026-08-31T12:00:00Z",
                "result": {
                    "contract": "p2p-memory-recovery-result/v1",
                    "status": "rolled_back",
                    "recovery_id": recovery_id,
                    "operation": "restore",
                    "action": "rollback",
                    "actor": "contributor",
                    "project_uuid": source.project_uuid,
                    "semantic_state_digest": source.semantic_state_digest,
                    "replayed": False,
                    "message": (
                        "Interrupted SQLite maintenance was rolled back to its "
                        "verified source state."
                    ),
                },
            }
        ),
    )

    result = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )

    assert result.actor == "owner"
    assert result.replayed is False
    assert project_memory_recovery_status(tmp_path).state == "clean"
    stored = json.loads(completion.read_bytes())
    assert stored["result"]["actor"] == "owner"
    quarantined = list(
        (completion.parent / "quarantine").glob(f"{recovery_id}-*.invalid")
    )
    assert len(quarantined) == 1


def test_recovery_cleanup_paths_are_bound_to_recovery_id(tmp_path: Path) -> None:
    _initialize(tmp_path)
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    unrelated = tmp_path / ".p2p/local/do-not-delete.stage"
    unrelated.mkdir(parents=True)
    write_bytes_atomic(unrelated / "evidence.txt", b"keep\n")
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    payload = json.loads(marker.read_bytes())
    payload["stage"] = unrelated.relative_to(tmp_path).as_posix()
    write_bytes_atomic(marker, canonical_json_bytes(payload))

    assert project_memory_recovery_status(tmp_path).state == "invalid_marker"
    with pytest.raises(ValueError, match="not owned by this recovery identifier"):
        project_memory_recovery_apply(
            tmp_path,
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            confirm=True,
        )
    assert (unrelated / "evidence.txt").read_bytes() == b"keep\n"


def test_recovery_rejects_invalid_workspace_lock_even_with_matching_id(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    marker_payload = json.loads((tmp_path / SQLITE_MAINTENANCE_MARKER).read_bytes())
    locks = WorkspaceTransactionLockService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    write_bytes_atomic(
        locks.lock_path,
        (
            f"transaction_id: {marker_payload['transaction_id']}\n"
            "pid: invalid\n"
        ).encode(),
    )

    with pytest.raises(ProjectStorageError) as raised:
        project_memory_recovery_apply(
            tmp_path,
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            confirm=True,
        )
    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert (tmp_path / SQLITE_MAINTENANCE_MARKER).is_file()


def test_second_current_owner_can_finish_completed_recovery_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _initialize(tmp_path)
    app.permissions_actor_add("second-owner", role="owner")
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    coordinator = SQLiteRecoveryCoordinator(tmp_path)
    original_cleanup = coordinator._cleanup

    def interrupted_cleanup(marker) -> None:
        original_cleanup(marker)
        raise RuntimeError("simulated death during cleanup")

    monkeypatch.setattr(coordinator, "_cleanup", interrupted_cleanup)
    with pytest.raises(RuntimeError, match="simulated death"):
        coordinator.apply(
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            action="rollback",
            confirm=True,
        )

    replay = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="second-owner",
        confirm=True,
    )
    assert replay.replayed is True
    assert replay.actor == "owner"
    assert project_memory_recovery_status(tmp_path).state == "clean"

    lost_ack_retry = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="second-owner",
        confirm=True,
    )
    assert lost_ack_retry.replayed is True
    assert lost_ack_retry.actor == "owner"


def test_completed_recovery_replay_reauthorizes_the_original_actor(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    app.permissions_actor_add("second-owner", role="owner")
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )
    reopened = open_project_application(tmp_path)
    reopened.permissions_actor_add("owner", role="contributor")

    with pytest.raises(ProjectStorageError, match="requires a source-project owner"):
        project_memory_recovery_apply(
            tmp_path,
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            confirm=True,
        )


def test_owner_handoff_survives_marker_disappearing_before_claim_recheck(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _initialize(tmp_path)
    app.permissions_actor_add("second-owner", role="owner")
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )
    coordinator = SQLiteRecoveryCoordinator(tmp_path)
    calls = 0

    def marker_then_completion() -> list[Path]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return [tmp_path / SQLITE_MAINTENANCE_MARKER]
        return []

    monkeypatch.setattr(coordinator, "_present_markers", marker_then_completion)

    replay = coordinator.apply(
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="second-owner",
        action="rollback",
        confirm=True,
    )

    assert replay.replayed is True
    assert replay.actor == "owner"


def test_already_open_application_reports_the_same_v2_recovery_status(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    recovery_id, _recovery_token = _maintenance_marker(tmp_path)

    status = app.canonical_memory_recovery_status()

    assert status.state == "recovery_required"
    assert status.recovery_id == recovery_id
    assert status.marker_contract == SQLITE_MAINTENANCE_CONTRACT


def test_recovery_refuses_to_run_while_forward_writer_lock_is_live(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    transaction_id = "sqlite-test-live-writer"
    recovery_id, recovery_token = _maintenance_marker(
        tmp_path,
        transaction_id=transaction_id,
    )
    lock = WorkspaceTransactionLockService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    lock.acquire(transaction_id, owner="owner")
    try:
        with pytest.raises(ProjectStorageError) as raised:
            project_memory_recovery_apply(
                tmp_path,
                recovery_id=recovery_id,
                recovery_token=recovery_token,
                actor="owner",
                confirm=True,
            )
        assert raised.value.code == ProjectStorageErrorCode.busy
    finally:
        lock.release(transaction_id)


def test_recovery_apply_cli_requires_exact_token_and_confirmation(tmp_path: Path) -> None:
    _initialize(tmp_path)
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    runner = CliRunner()

    wrong = runner.invoke(
        cli_app,
        [
            "project",
            "memory",
            "recovery-apply",
            "--recovery-id",
            recovery_id,
            "--token",
            "0" * 64,
            "--actor",
            "owner",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert wrong.exit_code != 0
    assert "P2P_IDEMPOTENCY_CONFLICT" in wrong.output

    applied = runner.invoke(
        cli_app,
        [
            "project",
            "memory",
            "recovery-apply",
            "--recovery-id",
            recovery_id,
            "--token",
            recovery_token,
            "--actor",
            "owner",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert applied.exit_code == 0, applied.output
    payload = json.loads(applied.stdout)
    assert payload["data"]["recovery"]["status"] == "rolled_back"


def test_legacy_marker_is_visible_but_not_applicable(tmp_path: Path) -> None:
    _initialize(tmp_path)
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    write_bytes_atomic(
        marker,
        canonical_json_bytes(
            {
                "contract": "p2p-sqlite-maintenance/v1",
                "operation": "restore",
                "stage": ".p2p/local/legacy.stage",
                "recovery": ".p2p/backups/legacy.sqlite3",
            }
        ),
    )

    status = project_memory_recovery_status(tmp_path)
    assert status.state == "recovery_required"
    assert status.applicable is False
    assert status.marker_contract == "p2p-sqlite-maintenance/v1"
    with pytest.raises(ProjectStorageError, match="Legacy SQLite recovery markers"):
        project_memory_recovery_apply(
            tmp_path,
            recovery_id="00000000-0000-0000-0000-000000000001",
            recovery_token="0" * 64,
            actor="owner",
            confirm=True,
        )


def test_marker_path_tampering_is_rejected_without_mutation(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    snapshot = app.canonical_memory_snapshot()
    recovery_id, recovery_token = new_sqlite_recovery_identity()
    before = (tmp_path / SQLITE_DATABASE_PATH).read_bytes()
    write_bytes_atomic(
        tmp_path / SQLITE_MAINTENANCE_MARKER,
        canonical_json_bytes(
            {
                "contract": SQLITE_MAINTENANCE_CONTRACT,
                "recovery_id": recovery_id,
                "recovery_token": recovery_token,
                "operation": "restore",
                "phase": "fenced",
                "actor": "owner",
                "transaction_id": f"sqlite-test-{recovery_id}",
                "source": {
                    "project_uuid": snapshot.project_uuid,
                    "semantic_state_digest": snapshot.semantic_state_digest,
                },
                "target": {
                    "project_uuid": snapshot.project_uuid,
                    "semantic_state_digest": snapshot.semantic_state_digest,
                },
                "stage": ".p2p/local/restore.stage",
                "recovery": "../../outside.sqlite3",
                "blob_changes": [],
            }
        ),
    )

    assert project_memory_recovery_status(tmp_path).state == "invalid_marker"
    with pytest.raises(ValueError, match="safe relative path"):
        project_memory_recovery_apply(
            tmp_path,
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            confirm=True,
        )
    assert (tmp_path / SQLITE_DATABASE_PATH).read_bytes() == before


def test_marker_phase_must_belong_to_its_operation(tmp_path: Path) -> None:
    _initialize(tmp_path)
    recovery_id, recovery_token = _maintenance_marker(tmp_path)
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    payload = json.loads(marker.read_bytes())
    payload["phase"] = "auxiliary_applied"
    write_bytes_atomic(marker, canonical_json_bytes(payload))

    assert project_memory_recovery_status(tmp_path).state == "invalid_marker"
    with pytest.raises(ValueError, match="phase is invalid"):
        project_memory_recovery_apply(
            tmp_path,
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            confirm=True,
        )


def test_identity_rollback_restores_auxiliary_files_and_absence(tmp_path: Path) -> None:
    _initialize(tmp_path)
    previous = Path(".p2p/local/owner-preferences.yml")
    created_by_target = Path(".p2p/local/target-only.yml")
    write_bytes_atomic(tmp_path / previous, b"source: true\n")
    backup_relative = Path(".p2p/backups/identity-auxiliary")
    write_sqlite_auxiliary_backup(
        tmp_path,
        backup_relative,
        {previous: (tmp_path / previous).read_bytes()},
    )
    write_bytes_atomic(tmp_path / previous, b"target: true\n")
    write_bytes_atomic(tmp_path / created_by_target, b"target-only: true\n")
    recovery_id, recovery_token = _maintenance_marker(
        tmp_path,
        operation="identity-transition",
        auxiliary_backup=backup_relative.as_posix(),
        auxiliary_remove=[_auxiliary_entry(tmp_path, created_by_target)],
        auxiliary_target=[
            _auxiliary_entry(tmp_path, previous),
            _auxiliary_entry(tmp_path, created_by_target),
        ],
    )

    project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )

    assert (tmp_path / previous).read_bytes() == b"source: true\n"
    assert not (tmp_path / created_by_target).exists()


def test_identity_rollback_refuses_to_delete_changed_target_only_auxiliary(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    created_by_target = Path(".p2p/local/target-only.yml")
    original = b"target-only: true\n"
    write_bytes_atomic(tmp_path / created_by_target, original)
    backup_relative = Path(".p2p/backups/identity-drift-auxiliary")
    write_sqlite_auxiliary_backup(tmp_path, backup_relative, {})
    recovery_id, recovery_token = _maintenance_marker(
        tmp_path,
        operation="identity-transition",
        auxiliary_backup=backup_relative.as_posix(),
        auxiliary_remove=[_auxiliary_entry(tmp_path, created_by_target)],
    )
    write_bytes_atomic(tmp_path / created_by_target, b"changed-after-crash: true\n")

    with pytest.raises(ProjectStorageError, match="changed auxiliary"):
        project_memory_recovery_apply(
            tmp_path,
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            confirm=True,
        )

    assert (tmp_path / created_by_target).read_bytes() == b"changed-after-crash: true\n"


def test_identity_recovery_retries_after_completion_cleanup_interruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _initialize(tmp_path)
    previous = Path(".p2p/local/owner-preferences.yml")
    write_bytes_atomic(tmp_path / previous, b"source: true\n")
    backup_relative = Path(".p2p/backups/identity-retry-auxiliary")
    write_sqlite_auxiliary_backup(
        tmp_path,
        backup_relative,
        {previous: (tmp_path / previous).read_bytes()},
    )
    write_bytes_atomic(tmp_path / previous, b"target: true\n")
    recovery_id, recovery_token = _maintenance_marker(
        tmp_path,
        operation="identity-transition",
        auxiliary_backup=backup_relative.as_posix(),
        auxiliary_target=[_auxiliary_entry(tmp_path, previous)],
    )
    coordinator = SQLiteRecoveryCoordinator(tmp_path)
    original_cleanup = coordinator._cleanup

    def interrupted_cleanup(marker) -> None:
        original_cleanup(marker)
        raise RuntimeError("simulated death after cleanup")

    monkeypatch.setattr(coordinator, "_cleanup", interrupted_cleanup)
    with pytest.raises(RuntimeError, match="simulated death"):
        coordinator.apply(
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            action="rollback",
            confirm=True,
        )

    result = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )
    assert result.replayed is True
    assert (tmp_path / previous).read_bytes() == b"source: true\n"
    assert project_memory_recovery_status(tmp_path).state == "clean"


def test_initial_activation_rollback_restores_detached_filesystem_state(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path, adapter=FILESYSTEM_ADAPTER)
    snapshot = app.canonical_memory_snapshot()
    recovery_id, recovery_token = new_sqlite_recovery_identity()
    relative = Path(".p2p/project/permissions.yml")
    live = tmp_path / relative
    content = live.read_bytes()
    activation_root = (
        tmp_path / ".p2p/local" / f"sqlite-activation-{recovery_id}.stage"
    )
    canonical_stage = activation_root / "canonical"
    staged = canonical_stage / relative
    staged.parent.mkdir(parents=True)
    os.replace(live, staged)
    write_bytes_atomic(
        tmp_path / SQLITE_ACTIVATION_MARKER,
        canonical_json_bytes(
            {
                "contract": SQLITE_ACTIVATION_CONTRACT,
                "recovery_id": recovery_id,
                "recovery_token": recovery_token,
                "operation": "initial-activation",
                "phase": "detached",
                "actor": "owner",
                "transaction_id": f"sqlite-test-{recovery_id}",
                "source": {
                    "project_uuid": snapshot.project_uuid,
                    "semantic_state_digest": snapshot.semantic_state_digest,
                },
                "target": {
                    "project_uuid": snapshot.project_uuid,
                    "semantic_state_digest": snapshot.semantic_state_digest,
                },
                "database_stage": (
                    activation_root / "project.sqlite3"
                ).relative_to(tmp_path).as_posix(),
                "canonical_stage": canonical_stage.relative_to(tmp_path).as_posix(),
                "detached": [
                    {
                        "path": relative.as_posix(),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                ],
            }
        ),
    )

    result = project_memory_recovery_apply(
        tmp_path,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        actor="owner",
        confirm=True,
    )

    assert result.operation == "initial-activation"
    assert live.read_bytes() == content
    assert ProjectStorageManifestStore(tmp_path).load().adapter == FILESYSTEM_ADAPTER
    assert open_project_application(tmp_path).canonical_memory_snapshot() == snapshot


def test_activation_rollback_rechecks_detached_parent_after_marker_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_recovery as recovery_module

    root = tmp_path / "project"
    app = _initialize(root, adapter=FILESYSTEM_ADAPTER)
    snapshot = app.canonical_memory_snapshot()
    recovery_id, recovery_token = new_sqlite_recovery_identity()
    relative = Path(".p2p/project/permissions.yml")
    live = root / relative
    content = live.read_bytes()
    activation_root = root / ".p2p/local" / f"sqlite-activation-{recovery_id}.stage"
    canonical_stage = activation_root / "canonical"
    staged = canonical_stage / relative
    staged.parent.mkdir(parents=True)
    os.replace(live, staged)
    write_bytes_atomic(
        root / SQLITE_ACTIVATION_MARKER,
        canonical_json_bytes(
            {
                "contract": SQLITE_ACTIVATION_CONTRACT,
                "recovery_id": recovery_id,
                "recovery_token": recovery_token,
                "operation": "initial-activation",
                "phase": "detached",
                "actor": "owner",
                "transaction_id": f"sqlite-test-{recovery_id}",
                "source": {
                    "project_uuid": snapshot.project_uuid,
                    "semantic_state_digest": snapshot.semantic_state_digest,
                },
                "target": {
                    "project_uuid": snapshot.project_uuid,
                    "semantic_state_digest": snapshot.semantic_state_digest,
                },
                "database_stage": (
                    activation_root / "project.sqlite3"
                ).relative_to(root).as_posix(),
                "canonical_stage": canonical_stage.relative_to(root).as_posix(),
                "detached": [
                    {
                        "path": relative.as_posix(),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                ],
            }
        ),
    )
    coordinator = SQLiteRecoveryCoordinator(root)
    original_parse = recovery_module._parse_v2_marker
    displaced = tmp_path / "displaced-project-state"
    external = tmp_path / "external-project-state"

    def parse_then_replace_parent(*args, **kwargs):
        marker = original_parse(*args, **kwargs)
        live.parent.replace(displaced)
        external.mkdir()
        _symlink_or_skip(live.parent, external, directory=True)
        return marker

    monkeypatch.setattr(
        recovery_module,
        "_parse_v2_marker",
        parse_then_replace_parent,
    )

    with pytest.raises(ProjectStorageError) as raised:
        coordinator.apply(
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            actor="owner",
            action="rollback",
            confirm=True,
        )

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert not (external / "permissions.yml").exists()
    assert staged.read_bytes() == content

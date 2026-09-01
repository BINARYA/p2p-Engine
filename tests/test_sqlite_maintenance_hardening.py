from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path, PureWindowsPath

import pytest

from p2p_engine.core.project_state_storage import (
    ProjectArchive,
    ProjectStateMutation,
    ProjectStorageError,
    ProjectStorageErrorCode,
)
from p2p_engine.services.project_application import (
    open_project_application,
    project_memory_recovery_apply,
    project_memory_recovery_status,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.sqlite_adapter import SQLiteBackupPort
from p2p_engine.storage.sqlite_project_state import (
    SQLiteCanonicalStore,
    snapshot_digest,
)
from p2p_engine.storage.sqlite_schema import (
    SQLITE_ADAPTER,
    SQLITE_DATABASE_PATH,
    SQLITE_MAINTENANCE_MARKER,
)


def _initialize(root: Path):
    P2PWorkspace(root).init_project(
        "SQLite maintenance hardening",
        owner="owner",
        agent_profile="generic",
        storage_adapter=SQLITE_ADAPTER,
    )
    return open_project_application(root)


def test_recovery_marker_locators_are_posix_on_windows_paths() -> None:
    from p2p_engine.storage.sqlite_adapter import _portable_project_locator

    root = PureWindowsPath("C:/work/project")
    path = root / ".p2p/local/sqlite-restore-id.stage"

    assert _portable_project_locator(root, path) == (
        ".p2p/local/sqlite-restore-id.stage"
    )


def _symlink_or_skip(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:  # pragma: no cover - Windows runner policy dependent.
        pytest.skip(f"symlink creation is unavailable: {exc}")


def _replace_document(snapshot, technical_id: str, document: object):
    entities = tuple(
        replace(
            entity,
            payload={**entity.payload, "document": document},
            entity_version=entity.entity_version + 1,
        )
        if entity.technical_id == technical_id
        else entity
        for entity in snapshot.entities
    )
    provisional = replace(
        snapshot,
        entities=entities,
        semantic_state_digest="0" * 64,
        source_revision={"kind": "local", "value": "0" * 64},
    )
    digest = snapshot_digest(provisional)
    return replace(
        provisional,
        semantic_state_digest=digest,
        source_revision={"kind": "local", "value": digest},
    )


def _commit_document(app, *, operation_id: str, technical_id: str, document: object):
    target = _replace_document(
        app.canonical_memory_snapshot(),
        technical_id,
        document,
    )
    with app.project_state_unit_of_work() as unit:
        unit.stage(
            ProjectStateMutation(
                operation_id=operation_id,
                actor="owner",
                expected_revision=app.project_state_revision(),
                target=target,
            )
        )
        unit.commit()
    return target


def test_restore_rejects_symlinked_internal_backup_directory_before_writing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    app = _initialize(root)
    source = tmp_path / "source.p2pbundle"
    app.canonical_bundle_export(source)
    before = app.canonical_memory_snapshot()
    backup_dir = root / ".p2p/backups"
    if backup_dir.exists():
        backup_dir.rename(root / ".p2p/backups-original")
    external = tmp_path / "outside-backups"
    external.mkdir()
    _symlink_or_skip(backup_dir, external, directory=True)
    operation_key = "restore-backup-parent-symlink"
    preview = app.canonical_memory_restore_preview(
        source=source,
        operation_key=operation_key,
        actor="owner",
    )

    with pytest.raises(ProjectStorageError) as raised:
        app.canonical_memory_restore_apply(
            source=source,
            operation_key=operation_key,
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert not list(external.iterdir())
    assert app.canonical_memory_snapshot() == before
    assert not (root / SQLITE_MAINTENANCE_MARKER).exists()
    assert not list((root / ".p2p/local").glob("sqlite-restore-*.stage"))


def test_restore_rejects_simulated_windows_backup_reparse_point(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import path_safety

    root = tmp_path / "project"
    app = _initialize(root)
    source = tmp_path / "source.p2pbundle"
    app.canonical_bundle_export(source)
    before = app.canonical_memory_snapshot()
    backup_dir = root / ".p2p/backups"
    original = path_safety.is_link_or_reparse_point
    monkeypatch.setattr(
        path_safety,
        "is_link_or_reparse_point",
        lambda path: path == backup_dir or original(path),
    )
    operation_key = "restore-backup-parent-reparse"
    preview = app.canonical_memory_restore_preview(
        source=source,
        operation_key=operation_key,
        actor="owner",
    )

    with pytest.raises(ProjectStorageError) as raised:
        app.canonical_memory_restore_apply(
            source=source,
            operation_key=operation_key,
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert app.canonical_memory_snapshot() == before
    assert not (root / SQLITE_MAINTENANCE_MARKER).exists()


def test_restore_rejects_symlinked_internal_backup_leaf_before_reading(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    app = _initialize(root)
    source = tmp_path / "source.p2pbundle"
    app.canonical_bundle_export(source)
    before = app.canonical_memory_snapshot()
    operation_key = "restore-backup-leaf-symlink"
    backup_dir = root / ".p2p/backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    key_digest = hashlib.sha256(operation_key.encode("utf-8")).hexdigest()[:24]
    backup_path = backup_dir / (
        f"sqlite-pre-restore-{key_digest}-{before.semantic_state_digest[:24]}.p2pbackup"
    )
    external = tmp_path / "outside-backup.p2pbackup"
    external.write_bytes(b"must not be read or replaced")
    _symlink_or_skip(backup_path, external)
    preview = app.canonical_memory_restore_preview(
        source=source,
        operation_key=operation_key,
        actor="owner",
    )

    with pytest.raises(ProjectStorageError) as raised:
        app.canonical_memory_restore_apply(
            source=source,
            operation_key=operation_key,
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert external.read_bytes() == b"must not be read or replaced"
    assert app.canonical_memory_snapshot() == before
    assert not (root / SQLITE_MAINTENANCE_MARKER).exists()


def test_post_commit_fence_failure_preserves_recoverable_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_driver

    app = _initialize(tmp_path)
    source = tmp_path / "source.p2pbundle"
    app.canonical_bundle_export(source)
    preview = app.canonical_memory_restore_preview(
        source=source,
        operation_key="restore-fence-post-commit-failure",
        actor="owner",
    )
    original = sqlite_driver._restrict_permissions

    def fail_database_permission_check(path: Path, *, directory: bool) -> None:
        if not directory:
            raise OSError("simulated post-commit permission verification failure")
        original(path, directory=directory)

    monkeypatch.setattr(
        sqlite_driver,
        "_restrict_permissions",
        fail_database_permission_check,
    )

    with pytest.raises(ProjectStorageError) as raised:
        app.canonical_memory_restore_apply(
            source=source,
            operation_key="restore-fence-post-commit-failure",
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )

    assert raised.value.code == ProjectStorageErrorCode.recovery_required
    assert (tmp_path / SQLITE_MAINTENANCE_MARKER).is_file()
    status = project_memory_recovery_status(tmp_path)
    assert status.state == "recovery_required"
    assert status.applicable is True

    monkeypatch.setattr(sqlite_driver, "_restrict_permissions", original)
    recovered = project_memory_recovery_apply(
        tmp_path,
        recovery_id=status.recovery_id,
        recovery_token=status.recovery_token,
        actor="owner",
        confirm=True,
    )

    assert recovered.status == "rolled_back"
    assert open_project_application(tmp_path).storage_selection().adapter == SQLITE_ADAPTER


def test_commit_then_error_is_classified_as_a_durable_maintenance_fence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage.sqlite_adapter import _fence_database

    app = _initialize(tmp_path)
    repository = app.adapter.repository

    class CommitThenError:
        def __init__(self, inner) -> None:
            self.inner = inner

        def __getattr__(self, name: str):
            return getattr(self.inner, name)

        def execute(self, sql: str, *args, **kwargs):
            result = self.inner.execute(sql, *args, **kwargs)
            if sql.strip().upper() == "COMMIT":
                raise sqlite3.OperationalError(
                    "simulated lost maintenance COMMIT acknowledgement"
                )
            return result

    original_connect = repository.connections.connect

    @contextmanager
    def wrapped_connect(*, writable: bool, busy_timeout_ms: int | None = None):
        with original_connect(
            writable=writable,
            busy_timeout_ms=busy_timeout_ms,
        ) as connection:
            yield CommitThenError(connection) if writable else connection

    monkeypatch.setattr(repository.connections, "connect", wrapped_connect)

    with pytest.raises(ProjectStorageError) as raised:
        _fence_database(
            repository,
            expected_revision=app.project_state_revision().sha256,
            state="restoring",
        )

    assert raised.value.code == ProjectStorageErrorCode.recovery_required
    assert "fence committed" in raised.value.safe_message
    with sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH) as connection:
        state = connection.execute(
            "SELECT maintenance_state FROM storage_metadata WHERE singleton = 1"
        ).fetchone()
    assert state == ("restoring",)


def test_identity_transition_rejects_symlinked_backup_directory_before_writing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    app = _initialize(root)
    before = app.canonical_memory_snapshot()
    arguments = {
        "operation_key": "identity-backup-parent-symlink",
        "actor_id": "owner",
        "executor_id": "owner",
        "executor_kind": "person",
    }
    preview = app.preview_project_identity_derivation(**arguments)
    backup_dir = root / ".p2p/backups"
    if backup_dir.exists():
        backup_dir.rename(root / ".p2p/backups-original")
    external = tmp_path / "outside-identity-backups"
    external.mkdir()
    _symlink_or_skip(backup_dir, external, directory=True)

    with pytest.raises(ProjectStorageError) as raised:
        app.apply_project_identity_derivation(
            **arguments,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert not list(external.iterdir())
    assert app.canonical_memory_snapshot() == before
    assert not (root / SQLITE_MAINTENANCE_MARKER).exists()


@pytest.mark.parametrize("actor", ("contributor", "unknown"))
def test_sqlite_restore_preview_requires_current_owner(tmp_path: Path, actor: str) -> None:
    app = _initialize(tmp_path)
    source = tmp_path / "source.p2pbundle"
    app.canonical_bundle_export(source)

    with pytest.raises(ValueError, match="OWNER_REQUIRED"):
        app.canonical_memory_restore_preview(
            source=source,
            operation_key=f"restore-not-owner-{actor}",
            actor=actor,
        )


def test_sqlite_restore_apply_reauthorizes_after_preview(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    source = tmp_path / "source.p2pbundle"
    app.canonical_bundle_export(source)
    preview = app.canonical_memory_restore_preview(
        source=source,
        operation_key="restore-owner-revoked-after-preview",
        actor="owner",
    )
    permissions_entity = next(
        entity
        for entity in app.canonical_memory_snapshot().entities
        if entity.technical_id == "project:permissions"
    )
    permissions = dict(permissions_entity.payload["document"])
    identities = dict(permissions["identities"])
    owner = dict(identities["owner"])
    owner["role"] = "contributor"
    identities["owner"] = owner
    permissions["identities"] = identities
    _commit_document(
        app,
        operation_id="revoke-restore-owner-before-apply",
        technical_id="project:permissions",
        document=permissions,
    )

    with pytest.raises(ValueError, match="OWNER_REQUIRED"):
        app.canonical_memory_restore_apply(
            source=source,
            operation_key="restore-owner-revoked-after-preview",
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )


def test_retry_same_restore_key_uses_backup_of_fresh_source_revision(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    source = tmp_path / "restore-target.p2pbundle"
    app.canonical_bundle_export(source)
    first = _commit_document(
        app,
        operation_id="restore-source-revision-one",
        technical_id="project:definition",
        document={"name": "source revision one"},
    )

    def fail_after_backup(stage: str) -> None:
        if stage == "after_restore_stage":
            raise OSError(stage)

    operation_key = "same-key-new-source-revision"
    failed_port = SQLiteBackupPort(
        app.adapter.repository,
        failure_injector=fail_after_backup,
    )
    first_preview = failed_port.restore_preview(
        source=source,
        operation_key=operation_key,
        actor="owner",
    )
    with pytest.raises(OSError, match="after_restore_stage"):
        failed_port.restore_apply(
            source=source,
            operation_key=operation_key,
            actor="owner",
            preview_token=first_preview.preview_token,
            confirm=True,
        )
    first_backups = set((tmp_path / ".p2p/backups").glob("sqlite-pre-restore-*.p2pbackup"))
    assert len(first_backups) == 1

    second = _commit_document(
        app,
        operation_id="restore-source-revision-two",
        technical_id="project:definition",
        document={"name": "source revision two"},
    )
    assert second.semantic_state_digest != first.semantic_state_digest
    port = SQLiteBackupPort(app.adapter.repository)
    second_preview = port.restore_preview(
        source=source,
        operation_key=operation_key,
        actor="owner",
    )
    result = port.restore_apply(
        source=source,
        operation_key=operation_key,
        actor="owner",
        preview_token=second_preview.preview_token,
        confirm=True,
    )

    assert Path(result.backup_path) not in first_backups
    decoded = port.codec.decode_physical_backup(Path(result.backup_path))
    assert decoded.manifest["source_revision"] == second.semantic_state_digest


def test_physical_backup_with_fenced_database_is_rejected(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    port = SQLiteBackupPort(app.adapter.repository)
    clean = port.create_backup()
    decoded = port.codec.decode_physical_backup(clean.content)
    files = dict(decoded.files)
    staged_database = tmp_path / "fenced.sqlite3"
    staged_database.write_bytes(files[SQLITE_DATABASE_PATH])
    with sqlite3.connect(staged_database) as connection:
        connection.execute(
            "UPDATE storage_metadata SET maintenance_state = 'restoring' "
            "WHERE singleton = 1"
        )
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    files[SQLITE_DATABASE_PATH] = staged_database.read_bytes()
    content = port.codec.encode_physical_backup(
        store=SQLiteCanonicalStore(app.adapter.repository),
        files=files,
        directories=tuple(decoded.manifest["directories"]),
        semantic_state_digest=decoded.semantic_state_digest,
        source_revision=str(decoded.manifest["source_revision"]),
    )
    fenced = ProjectArchive(
        kind="physical_backup",
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        semantic_state_digest=decoded.semantic_state_digest,
    )

    with pytest.raises(ProjectStorageError) as raised:
        port.verify_backup(fenced)

    assert raised.value.code == ProjectStorageErrorCode.recovery_required

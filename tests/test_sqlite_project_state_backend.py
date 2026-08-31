from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from p2p_engine.cli import app as cli_app
from p2p_engine.core.canonical_memory import ManagedBlob
from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    ProjectStateMutation,
    ProjectStateQuery,
    ProjectStorageError,
    ProjectStorageErrorCode,
    ProjectStorageManifest,
)
from p2p_engine.foundation.files import write_bytes_atomic
from p2p_engine.services.project_application import (
    open_project_application,
    project_memory_recovery_status,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.project_storage import (
    PROJECT_STORAGE_MANIFEST_PATH,
    ProjectStorageManifestStore,
)
from p2p_engine.storage.sqlite_adapter import (
    SQLITE_MAINTENANCE_MARKER,
    SQLiteBackupPort,
    SQLiteMigrationPort,
)
from p2p_engine.storage.sqlite_driver import SQLiteConnectionFactory
from p2p_engine.storage.sqlite_initialization import activate_sqlite_from_filesystem
from p2p_engine.storage.sqlite_project_state import (
    SQLiteProjectStateRepository,
    SQLiteProjectUnitOfWork,
    snapshot_digest,
    sqlite_blob_path,
)
from p2p_engine.storage.sqlite_schema import (
    SQLITE_ADAPTER,
    SQLITE_APPLICATION_ID,
    SQLITE_DATABASE_PATH,
    SQLITE_SCHEMA_CONTRACT,
    SQLITE_SCHEMA_V1,
    SQLITE_SCHEMA_VERSION,
)


def _initialize(root: Path, *, adapter: str = SQLITE_ADAPTER):
    P2PWorkspace(root).init_project(
        "SQLite adapter contract",
        owner="owner",
        agent_profile="generic",
        storage_adapter=adapter,
    )
    return open_project_application(root)


def _target_with_documents(snapshot, changes: dict[str, object]):
    entities = []
    for entity in snapshot.entities:
        if entity.technical_id not in changes:
            entities.append(entity)
            continue
        payload = dict(entity.payload)
        document = payload["document"]
        updated: object
        if isinstance(document, dict):
            updated = dict(document)
            updated["sqlite_test_value"] = changes[entity.technical_id]
        else:
            updated = f"{document}\n\n{changes[entity.technical_id]}\n"
        payload["document"] = updated
        entities.append(
            replace(
                entity,
                payload=payload,
                entity_version=entity.entity_version + 1,
            )
        )
    provisional = replace(
        snapshot,
        entities=tuple(entities),
        semantic_state_digest="0" * 64,
        source_revision={"kind": "local", "value": "0" * 64},
    )
    digest = snapshot_digest(provisional)
    return replace(
        provisional,
        semantic_state_digest=digest,
        source_revision={"kind": "local", "value": digest},
    )


def _target_with_blob(snapshot, content: bytes):
    from p2p_engine.core.canonical_memory import semantic_sha256

    raw_digest = hashlib.sha256(content).hexdigest()
    digest = f"sha256:{raw_digest}"
    first = next(
        entity
        for entity in snapshot.entities
        if isinstance(entity.payload.get("document"), dict)
    )
    payload = dict(first.payload)
    document = dict(payload["document"])
    document["sqlite_blob"] = {"kind": "managed_blob", "digest": digest}
    payload["document"] = document
    entities = tuple(
        replace(entity, payload=payload) if entity.technical_id == first.technical_id else entity
        for entity in snapshot.entities
    )
    blob = ManagedBlob(
        digest=digest,
        size=len(content),
        storage_locator=f".p2p/blobs/sha256/{raw_digest[:2]}/{raw_digest}",
    )
    provisional = replace(
        snapshot,
        entities=entities,
        blobs=(blob,),
        blob_manifest_digest=semantic_sha256([blob.to_dict()]),
        semantic_state_digest="0" * 64,
        source_revision={"kind": "local", "value": "0" * 64},
    )
    state_digest = snapshot_digest(provisional)
    return (
        replace(
            provisional,
            semantic_state_digest=state_digest,
            source_revision={"kind": "local", "value": state_digest},
        ),
        digest,
    )


def _activate_existing_filesystem(root: Path) -> tuple[bytes, dict[Path, bytes]]:
    P2PWorkspace(root).init_project(
        "SQLite adapter contract",
        owner="owner",
        agent_profile="codex",
        storage_adapter=FILESYSTEM_ADAPTER,
    )
    app = open_project_application(root)
    bundle = app.adapter.snapshots.export_bundle().content
    generated = {
        path.relative_to(root)
        for path in (root / ".agents").rglob("*")
        if path.is_file()
    }
    generated.update(
        {
            Path("AGENTS.md"),
            Path("P2P-SETUP.md"),
            Path(".p2p/agent-policy.yml"),
            Path(".p2p/agent-integrations.yml"),
        }
    )
    instructions = {
        relative: (root / relative).read_bytes()
        for relative in sorted(generated)
    }
    identity = app.project_identity()
    write_bytes_atomic(
        root / PROJECT_STORAGE_MANIFEST_PATH,
        ProjectStorageManifestStore.render(
            ProjectStorageManifest(
                project_uuid=identity.project_uuid.value,
                adapter=SQLITE_ADAPTER,
            )
        ),
    )
    activate_sqlite_from_filesystem(root)
    return bundle, instructions


def test_schema_is_versioned_hybrid_semantic_and_indexed() -> None:
    lowered = SQLITE_SCHEMA_V1.lower()
    required_tables = {
        "projects",
        "storage_metadata",
        "entities",
        "entity_revisions",
        "entity_relations",
        "project_authority",
        "structure_assignments",
        "blobs",
        "blob_references",
        "receipts",
        "operation_records",
        "schema_migrations",
    }

    assert all(f"create table {table}" in lowered for table in required_tables)
    assert "path/content" not in lowered
    assert "create table path" not in lowered
    assert "foreign key" not in lowered or "references" in lowered
    assert lowered.count("create index") >= 8
    assert "payload_json text" in lowered
    assert SQLITE_SCHEMA_VERSION == 1
    assert SQLITE_SCHEMA_CONTRACT.endswith("/v1")


def test_explicit_init_reopen_default_and_no_dual_write(tmp_path: Path) -> None:
    filesystem_root = tmp_path / "filesystem"
    sqlite_root = tmp_path / "sqlite"
    default = _initialize(filesystem_root, adapter=FILESYSTEM_ADAPTER)
    candidate = _initialize(sqlite_root)

    assert default.storage_selection().adapter == FILESYSTEM_ADAPTER
    assert candidate.storage_selection().adapter == SQLITE_ADAPTER
    assert open_project_application(sqlite_root).storage_selection().adapter == SQLITE_ADAPTER
    assert (sqlite_root / SQLITE_DATABASE_PATH).is_file()
    assert not (sqlite_root / ".p2p/project.yml").exists()
    assert not (sqlite_root / ".p2p/project/identity.yml").exists()
    assert candidate.adapter.repository.integrity_check() == ()

    (sqlite_root / ".p2p/project.yml").write_text("project: {}\n", encoding="utf-8")
    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(sqlite_root)
    assert raised.value.code == ProjectStorageErrorCode.configuration_contradiction


def test_sqlite_runtime_pragmas_capabilities_permissions_and_network_rejection(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    database = tmp_path / SQLITE_DATABASE_PATH
    factory = SQLiteConnectionFactory(database)
    capabilities = factory.detect_capabilities()

    assert capabilities.json_functions is True
    assert capabilities.online_backup is True
    assert capabilities.foreign_keys is True
    assert capabilities.journal_mode == "wal"
    assert capabilities.synchronous == "full"
    if os.name != "nt":
        assert database.stat().st_mode & 0o777 == 0o600
        assert database.parent.stat().st_mode & 0o777 == 0o700

    unsafe = SQLiteConnectionFactory(
        tmp_path / "unsafe.sqlite3",
        filesystem_detector=lambda _path: "nfs",
    )
    with pytest.raises(ProjectStorageError) as raised:
        unsafe.validate_environment()
    assert raised.value.code == ProjectStorageErrorCode.unsupported_capability
    assert app.storage_capabilities.serialized_writers is True


def test_bundle_digest_and_generated_agent_surfaces_match_filesystem(
    tmp_path: Path,
) -> None:
    bundle, instructions = _activate_existing_filesystem(tmp_path)
    sqlite_app = open_project_application(tmp_path)

    assert sqlite_app.adapter.snapshots.export_bundle().content == bundle
    assert {
        relative: (tmp_path / relative).read_bytes() for relative in instructions
    } == instructions
    assert not (tmp_path / ".p2p/project.yml").exists()


def test_shared_query_and_multi_entity_unit_of_work_contract(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    before = app.canonical_memory_snapshot()
    target = _target_with_documents(
        before,
        {
            "project:definition": "definition changed",
            "project:domain": "domain changed",
        },
    )
    mutation = ProjectStateMutation(
        operation_id="sqlite-two-entity-contract",
        actor="owner",
        expected_revision=app.project_state_revision(),
        target=target,
        receipt_id="sqlite-two-entity-receipt",
    )

    with app.project_state_unit_of_work() as unit:
        unit.stage(mutation)
        result = unit.commit()

    assert result.revision.sha256 == target.semantic_state_digest
    assert len(result.changed_entities) == 2
    assert result.receipt_id == "sqlite-two-entity-receipt"
    records = app.query_project_state(
        ProjectStateQuery(
            technical_ids=("project:definition", "project:domain"),
        )
    )
    assert len(records) == 2

    with app.project_state_unit_of_work() as replay:
        replay.stage(replace(mutation, expected_revision=app.project_state_revision()))
        replayed = replay.commit()
    assert replayed.replayed is True


@pytest.mark.parametrize("adapter", (FILESYSTEM_ADAPTER, SQLITE_ADAPTER))
def test_shared_adapter_contract_matrix(tmp_path: Path, adapter: str) -> None:
    app = _initialize(tmp_path / adapter, adapter=adapter)
    snapshot = app.canonical_memory_snapshot()
    revision = app.project_state_revision()
    records = app.query_project_state(
        ProjectStateQuery(entity_types=("p2p.project.manifest",))
    )
    bundle = app.adapter.snapshots.export_bundle()
    backup = app.adapter.backups.create_backup()

    assert app.project_identity().project_uuid.value == snapshot.project_uuid
    assert revision.sha256 == snapshot.semantic_state_digest
    assert len(records) == 1
    assert app.project_state_entity(records[0].ref) == records[0]
    assert app.adapter.snapshots.verify_bundle(bundle) == snapshot
    app.adapter.backups.verify_backup(backup)
    assert app.storage_capabilities.to_dict() == {
        "adapter": adapter,
        "schema_version": 1,
        "consistent_reads": True,
        "atomic_multi_entity_writes": True,
        "managed_blobs": True,
        "portable_bundles": True,
        "physical_backup_restore": True,
        "concurrent_readers": True,
        "serialized_writers": True,
    }


@pytest.mark.parametrize(
    "failure_stage",
    ("after_begin", "after_blob_stage", "after_state_write", "before_commit"),
)
def test_mutation_faults_rollback_every_precommit_boundary(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    app = _initialize(tmp_path)
    before = app.canonical_memory_snapshot()
    target = _target_with_documents(before, {"project:definition": failure_stage})

    def inject(stage: str) -> None:
        if stage == failure_stage:
            raise OSError(f"injected {stage}")

    repository = SQLiteProjectStateRepository(tmp_path, failure_injector=inject)
    unit = SQLiteProjectUnitOfWork(repository)
    unit.stage(
        ProjectStateMutation(
            operation_id=f"fault-{failure_stage}",
            actor="owner",
            expected_revision=repository.current_revision(),
            target=target,
        )
    )
    with pytest.raises(ProjectStorageError):
        unit.commit()

    assert repository.snapshot().semantic_state_digest == before.semantic_state_digest
    assert repository.integrity_check() == ()


def test_after_commit_interruption_is_recovered_by_receipt_replay(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    blob_content = b"lost acknowledgement blob\n"
    target, blob_digest = _target_with_blob(app.canonical_memory_snapshot(), blob_content)

    def inject(stage: str) -> None:
        if stage == "after_commit":
            raise OSError("process lost acknowledgement")

    repository = SQLiteProjectStateRepository(tmp_path, failure_injector=inject)
    mutation = ProjectStateMutation(
        operation_id="sqlite-lost-acknowledgement",
        actor="owner",
        expected_revision=repository.current_revision(),
        target=target,
        blob_payloads={blob_digest: blob_content},
    )
    unit = SQLiteProjectUnitOfWork(repository)
    unit.stage(mutation)
    with pytest.raises(ProjectStorageError):
        unit.commit()

    assert repository.current_revision().sha256 == target.semantic_state_digest
    assert sqlite_blob_path(tmp_path, blob_digest).read_bytes() == blob_content
    assert repository.integrity_check() == ()
    retry = SQLiteProjectUnitOfWork(SQLiteProjectStateRepository(tmp_path))
    retry.stage(replace(mutation, expected_revision=repository.current_revision()))
    assert retry.commit().replayed is True


def test_concurrent_reader_stale_revision_and_bounded_writer(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    repository = app.adapter.repository
    before = repository.snapshot()
    target = _target_with_documents(before, {"project:definition": "concurrent"})
    unit = SQLiteProjectUnitOfWork(repository)
    unit.stage(
        ProjectStateMutation(
            operation_id="sqlite-bounded-writer",
            actor="owner",
            expected_revision=repository.current_revision(),
            target=target,
            lock_wait_timeout=0.01,
        )
    )

    holder = sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH, isolation_level=None)
    holder.execute("PRAGMA foreign_keys = ON")
    holder.execute("BEGIN IMMEDIATE")
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            read = pool.submit(repository.snapshot)
            assert read.result(timeout=2).semantic_state_digest == before.semantic_state_digest
        with pytest.raises(ProjectStorageError) as raised:
            unit.commit()
        assert raised.value.code == ProjectStorageErrorCode.busy
    finally:
        holder.execute("ROLLBACK")
        holder.close()

    changed = _target_with_documents(before, {"project:domain": "other writer"})
    current_unit = SQLiteProjectUnitOfWork(repository)
    current_unit.stage(
        ProjectStateMutation(
            operation_id="sqlite-current-writer",
            actor="owner",
            expected_revision=repository.current_revision(),
            target=changed,
        )
    )
    current_unit.commit()
    stale = SQLiteProjectUnitOfWork(repository)
    with pytest.raises(ProjectStorageError) as raised:
        stale.stage(
            ProjectStateMutation(
                operation_id="sqlite-stale-writer",
                actor="owner",
                expected_revision=replace(repository.current_revision(), sha256=before.semantic_state_digest),
                target=target,
            )
        )
    assert raised.value.code == ProjectStorageErrorCode.stale_revision


def test_blob_metadata_is_transactional_but_bytes_remain_external(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    before = app.canonical_memory_snapshot()
    content = b"managed SQLite blob\n"
    target, digest = _target_with_blob(before, content)

    unit = app.project_state_unit_of_work()
    unit.stage(
        ProjectStateMutation(
            operation_id="sqlite-managed-blob",
            actor="owner",
            expected_revision=app.project_state_revision(),
            target=target,
            blob_payloads={digest: content},
        )
    )
    unit.commit()

    blob_path = sqlite_blob_path(tmp_path, digest)
    assert blob_path.read_bytes() == content
    with sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH) as connection:
        assert connection.execute("SELECT count(*) FROM blobs").fetchone()[0] == 1
        assert all("BLOB" not in str(row[2]).upper() for row in connection.execute("PRAGMA table_info(blobs)"))
    blob_path.unlink()
    assert any("blob:" in issue for issue in app.adapter.repository.integrity_check())


def test_online_backup_restore_and_archive_exclude_wal(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    before = app.canonical_memory_snapshot()
    bundle = tmp_path / "before.p2pbundle"
    backup = tmp_path / "before.p2pbackup"
    app.canonical_bundle_export(bundle)
    app.canonical_memory_backup(backup)
    with pytest.raises(ValueError, match="P2P_BACKUP_OUTPUT_EXISTS"):
        app.canonical_memory_backup(backup)
    with pytest.raises(ValueError, match="P2P_BACKUP_OUTPUT_UNSAFE"):
        app.canonical_memory_backup(tmp_path / ".p2p/unsafe.p2pbackup")
    decoded = app.adapter.backups.codec.decode_physical_backup(backup)
    assert SQLITE_DATABASE_PATH in decoded.files
    assert all(not path.endswith(("-wal", "-shm", "-journal")) for path in decoded.files)

    target = _target_with_documents(before, {"project:definition": "restore me"})
    unit = app.project_state_unit_of_work()
    unit.stage(
        ProjectStateMutation(
            operation_id="sqlite-before-restore",
            actor="owner",
            expected_revision=app.project_state_revision(),
            target=target,
        )
    )
    unit.commit()
    preview = app.canonical_memory_restore_preview(
        source=bundle,
        operation_key="sqlite-restore-contract-12345678",
        actor="owner",
    )
    result = app.canonical_memory_restore_apply(
        source=bundle,
        operation_key="sqlite-restore-contract-12345678",
        actor="owner",
        preview_token=preview.preview_token,
        confirm=True,
    )
    assert result.semantic_state_digest == before.semantic_state_digest
    assert app.adapter.repository.integrity_check() == ()

    changed_again = _target_with_documents(
        app.canonical_memory_snapshot(),
        {"project:definition": "restore the physical backup"},
    )
    unit = app.project_state_unit_of_work()
    unit.stage(
        ProjectStateMutation(
            operation_id="sqlite-before-physical-restore",
            actor="owner",
            expected_revision=app.project_state_revision(),
            target=changed_again,
        )
    )
    unit.commit()
    physical_preview = app.canonical_memory_restore_preview(
        source=backup,
        operation_key="sqlite-physical-restore-contract-12345678",
        actor="owner",
    )
    physical_result = app.canonical_memory_restore_apply(
        source=backup,
        operation_key="sqlite-physical-restore-contract-12345678",
        actor="owner",
        preview_token=physical_preview.preview_token,
        confirm=True,
    )
    assert physical_result.semantic_state_digest == before.semantic_state_digest
    assert app.adapter.repository.integrity_check() == ()
    replay = app.canonical_memory_restore_apply(
        source=backup,
        operation_key="sqlite-physical-restore-contract-12345678",
        actor="owner",
        preview_token=physical_preview.preview_token,
        confirm=True,
    )
    assert replay.replayed is True
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        app.canonical_memory_restore_apply(
            source=bundle,
            operation_key="sqlite-physical-restore-contract-12345678",
            actor="owner",
            preview_token=physical_preview.preview_token,
            confirm=True,
        )
    if os.name != "nt":
        assert (tmp_path / SQLITE_DATABASE_PATH).stat().st_mode & 0o777 == 0o600
    assert app.canonical_memory_recovery_status().state == "clean"


@pytest.mark.parametrize(
    "failure_stage",
    (
        "after_restore_marker",
        "after_restore_stage",
        "after_restore_old_database_move",
        "after_restore_activation",
        "after_restore_receipt",
    ),
)
def test_restore_faults_preserve_previous_database(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    app = _initialize(tmp_path)
    original = app.canonical_memory_snapshot()
    bundle = tmp_path / "original.p2pbundle"
    app.canonical_bundle_export(bundle)
    changed = _target_with_documents(original, {"project:definition": "keep current"})
    unit = app.project_state_unit_of_work()
    unit.stage(
        ProjectStateMutation(
            operation_id=f"restore-fault-current-{failure_stage}",
            actor="owner",
            expected_revision=app.project_state_revision(),
            target=changed,
        )
    )
    unit.commit()

    def inject(stage: str) -> None:
        if stage == failure_stage:
            raise OSError(stage)

    backup = SQLiteBackupPort(app.adapter.repository, failure_injector=inject)
    preview = backup.restore_preview(
        source=bundle,
        operation_key=f"restore-fault-{failure_stage}-12345678",
        actor="owner",
    )
    with pytest.raises(OSError):
        backup.restore_apply(
            source=bundle,
            operation_key=f"restore-fault-{failure_stage}-12345678",
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )

    reopened = open_project_application(tmp_path)
    assert reopened.project_state_revision().sha256 == changed.semantic_state_digest
    assert reopened.adapter.repository.integrity_check() == ()
    assert not (tmp_path / SQLITE_MAINTENANCE_MARKER).exists()


@pytest.mark.parametrize("failure_stage", ("before_online_backup", "after_online_backup"))
def test_online_backup_fault_never_publishes_partial_archive(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    app = _initialize(tmp_path)

    def inject(stage: str) -> None:
        if stage == failure_stage:
            raise OSError(stage)

    output = tmp_path / "partial.p2pbackup"
    backup = SQLiteBackupPort(app.adapter.repository, failure_injector=inject)
    with pytest.raises(OSError):
        backup.backup_to(output)
    assert not output.exists()


def test_unclean_wal_is_recovered_and_maintenance_fence_blocks_open(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    expected = app.project_state_revision().sha256
    program = """
import os
import sqlite3
import sys
connection = sqlite3.connect(sys.argv[1], isolation_level=None)
connection.execute('PRAGMA journal_mode = WAL')
connection.execute('PRAGMA synchronous = FULL')
connection.execute('BEGIN IMMEDIATE')
connection.execute("UPDATE storage_metadata SET updated_at = 'unclean-wal-test' WHERE singleton = 1")
connection.execute('COMMIT')
os._exit(0)
"""
    subprocess.run(
        [sys.executable, "-c", program, str(tmp_path / SQLITE_DATABASE_PATH)],
        check=True,
    )

    reopened = open_project_application(tmp_path)
    assert reopened.project_state_revision().sha256 == expected
    assert reopened.adapter.repository.integrity_check() == ()

    with sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH) as connection:
        connection.execute(
            "UPDATE storage_metadata SET maintenance_state = 'migrating' WHERE singleton = 1"
        )
    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)
    assert raised.value.code == ProjectStorageErrorCode.recovery_required


def test_maintenance_fence_blocks_an_already_open_writer(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    before = app.canonical_memory_snapshot()
    target = _target_with_documents(before, {"project:definition": "must wait"})
    unit = app.project_state_unit_of_work()
    unit.stage(
        ProjectStateMutation(
            operation_id="maintenance-fence-open-writer",
            actor="owner",
            expected_revision=app.project_state_revision(),
            target=target,
        )
    )
    with sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH) as connection:
        connection.execute(
            "UPDATE storage_metadata SET maintenance_state = 'restoring' WHERE singleton = 1"
        )
    try:
        with pytest.raises(ProjectStorageError) as raised:
            unit.commit()
        assert raised.value.code == ProjectStorageErrorCode.recovery_required
        assert app.canonical_memory_snapshot().semantic_state_digest == (
            before.semantic_state_digest
        )
    finally:
        with sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH) as connection:
            connection.execute(
                "UPDATE storage_metadata SET maintenance_state = 'ready' WHERE singleton = 1"
            )


def test_maintenance_marker_blocks_reopen_even_when_database_is_ready(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    write_bytes_atomic(marker, b'{}\n')

    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)

    assert raised.value.code == ProjectStorageErrorCode.recovery_required
    assert project_memory_recovery_status(tmp_path).state == "invalid_marker"


def test_recovery_status_cli_remains_available_while_sqlite_open_is_fenced(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    marker.write_text(
        json.dumps(
            {
                "contract": "p2p-sqlite-maintenance/v1",
                "operation": "restore",
                "stage": ".p2p/local/restore.stage",
                "recovery": ".p2p/backups/recovery.sqlite3",
            }
        ),
        encoding="utf-8",
    )

    status = project_memory_recovery_status(tmp_path)
    assert status.state == "recovery_required"
    assert status.staging_path == str(tmp_path / ".p2p/local/restore.stage")
    result = CliRunner().invoke(
        cli_app,
        [
            "project",
            "memory",
            "recovery-status",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["data"]["recovery"]["state"] == "recovery_required"


def test_backup_normalizes_maintenance_fence_in_recovery_database(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    with sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH) as connection:
        connection.execute(
            "UPDATE storage_metadata SET maintenance_state = 'migrating' WHERE singleton = 1"
        )
    backup = SQLiteBackupPort(app.adapter.repository)
    archive = backup.create_backup()
    decoded = backup.codec.decode_physical_backup(archive.content)
    recovered = tmp_path / "recovered.sqlite3"
    recovered.write_bytes(decoded.files[SQLITE_DATABASE_PATH])

    with sqlite3.connect(recovered) as connection:
        state = connection.execute(
            "SELECT maintenance_state FROM storage_metadata WHERE singleton = 1"
        ).fetchone()[0]

    assert state == "ready"


def test_init_operation_receipt_replays_without_reactivation(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    first = workspace.init_project_with_operation_key(
        "SQLite replay",
        operation_key="sqlite-init-replay-contract-v1",
        owner="owner",
        agent_profile="generic",
        starter_id="generic",
        storage_adapter=SQLITE_ADAPTER,
    )
    database_before = (tmp_path / SQLITE_DATABASE_PATH).stat().st_mtime_ns
    second = P2PWorkspace(tmp_path).init_project_with_operation_key(
        "SQLite replay",
        operation_key="sqlite-init-replay-contract-v1",
        owner="owner",
        agent_profile="generic",
        starter_id="generic",
        storage_adapter=SQLITE_ADAPTER,
    )

    assert first["mutation"]["status"] == "applied"
    assert second["mutation"]["status"] == "already_applied"
    assert (tmp_path / SQLITE_DATABASE_PATH).stat().st_mtime_ns == database_before
    assert not (tmp_path / ".p2p/project.yml").exists()


def test_identity_derivation_replaces_single_project_database_and_replays(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    previous = app.project_identity()
    arguments = {
        "operation_key": "sqlite-identity-derive-12345678",
        "actor_id": "owner",
        "executor_id": "owner",
        "executor_kind": "person",
    }
    preview = app.preview_project_identity_derivation(**arguments)

    result = app.apply_project_identity_derivation(
        **arguments,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert result.current.project_uuid != previous.project_uuid
    reopened = open_project_application(tmp_path)
    assert reopened.project_identity() == result.current
    assert reopened.storage_selection().manifest.project_uuid == (
        result.current.project_uuid.value
    )
    assert not (tmp_path / ".p2p/project.yml").exists()
    assert not (tmp_path / SQLITE_MAINTENANCE_MARKER).exists()

    replay = reopened.apply_project_identity_derivation(
        **arguments,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    assert replay.status == "already_applied"
    assert replay.current == result.current


@pytest.mark.parametrize(
    "failure_stage",
    (
        "after_identity_stage",
        "after_identity_fence",
        "after_identity_backup",
        "after_identity_old_database_move",
        "after_identity_activation",
        "after_identity_manifest",
        "after_identity_auxiliary",
    ),
)
def test_identity_derivation_fault_restores_database_manifest_and_auxiliary_state(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    app = _initialize(tmp_path)
    before = app.canonical_memory_snapshot()
    identity = app.project_identity()
    manifest = (tmp_path / PROJECT_STORAGE_MANIFEST_PATH).read_bytes()
    operation_key = f"sqlite-identity-fault-{failure_stage}-12345678"
    arguments = {
        "operation_key": operation_key,
        "actor_id": "owner",
        "executor_id": "owner",
        "executor_kind": "person",
    }
    preview = app.preview_project_identity_derivation(**arguments)

    def inject(stage: str) -> None:
        if stage == failure_stage:
            raise OSError(stage)

    app.adapter.repository.failure_injector = inject
    with pytest.raises(OSError, match=failure_stage):
        app.apply_project_identity_derivation(
            **arguments,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )

    reopened = open_project_application(tmp_path)
    assert reopened.project_identity() == identity
    assert reopened.canonical_memory_snapshot().semantic_state_digest == (
        before.semantic_state_digest
    )
    assert (tmp_path / PROJECT_STORAGE_MANIFEST_PATH).read_bytes() == manifest
    assert not (tmp_path / SQLITE_MAINTENANCE_MARKER).exists()
    assert not (tmp_path / ".p2p/project.yml").exists()
    assert not list((tmp_path / ".p2p/local").glob("sqlite-identity-*.stage"))


@pytest.mark.parametrize(
    "failure_stage",
    (
        "before_schema",
        "before_schema_commit",
        "after_sqlite_stage",
        "after_canonical_detach",
        "after_sqlite_activation",
    ),
)
def test_initial_activation_failure_restores_authoritative_filesystem(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    filesystem = _initialize(tmp_path, adapter=FILESYSTEM_ADAPTER)
    identity = filesystem.project_identity()
    write_bytes_atomic(
        tmp_path / PROJECT_STORAGE_MANIFEST_PATH,
        ProjectStorageManifestStore.render(
            ProjectStorageManifest(
                project_uuid=identity.project_uuid.value,
                adapter=SQLITE_ADAPTER,
            )
        ),
    )

    def inject(stage: str) -> None:
        if stage == failure_stage:
            raise OSError(stage)

    with pytest.raises(OSError):
        activate_sqlite_from_filesystem(tmp_path, failure_injector=inject)

    reopened = open_project_application(tmp_path)
    assert reopened.storage_selection().adapter == FILESYSTEM_ADAPTER
    assert (tmp_path / ".p2p/project.yml").is_file()
    assert not (tmp_path / SQLITE_DATABASE_PATH).exists()
    assert not (tmp_path / ".p2p/local/sqlite-activation.json").exists()
    assert not list((tmp_path / ".p2p/local").glob("sqlite-activation-*.stage"))


def test_manifest_database_mismatch_corruption_and_newer_schema_are_blocked(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    database = tmp_path / SQLITE_DATABASE_PATH
    with sqlite3.connect(database) as connection:
        connection.execute(f"PRAGMA user_version = {SQLITE_SCHEMA_VERSION + 1}")
    migration = SQLiteMigrationPort(SQLiteProjectStateRepository(tmp_path))
    with pytest.raises(ProjectStorageError) as raised:
        migration.verify_current()
    assert raised.value.code == ProjectStorageErrorCode.unsupported_capability

    with sqlite3.connect(database) as connection:
        connection.execute(f"PRAGMA user_version = {SQLITE_SCHEMA_VERSION}")
    manifest = ProjectStorageManifestStore(tmp_path).load()
    write_bytes_atomic(
        tmp_path / PROJECT_STORAGE_MANIFEST_PATH,
        ProjectStorageManifestStore.render(
            replace(manifest, project_uuid="00000000-0000-0000-0000-000000000001")
        ),
    )
    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)
    assert raised.value.code == ProjectStorageErrorCode.identity_mismatch

    write_bytes_atomic(
        tmp_path / PROJECT_STORAGE_MANIFEST_PATH,
        ProjectStorageManifestStore.render(manifest),
    )
    database.write_bytes(b"not sqlite")
    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)
    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert app.storage_selection().adapter == SQLITE_ADAPTER


def test_database_header_and_schema_migration_ledger_are_exact(tmp_path: Path) -> None:
    _initialize(tmp_path)
    with sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH) as connection:
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        migrations = connection.execute(
            "SELECT version, contract, length(ddl_sha256) FROM schema_migrations"
        ).fetchall()

    assert application_id == SQLITE_APPLICATION_ID
    assert version == SQLITE_SCHEMA_VERSION
    assert migrations == [(SQLITE_SCHEMA_VERSION, SQLITE_SCHEMA_CONTRACT, 64)]


def _downgrade_to_preversioned_sqlite(root: Path) -> SQLiteMigrationPort:
    with sqlite3.connect(root / SQLITE_DATABASE_PATH) as connection:
        connection.execute("DELETE FROM schema_migrations")
        connection.execute("PRAGMA user_version = 0")
    return SQLiteMigrationPort(SQLiteProjectStateRepository(root))


def test_preversioned_schema_migrates_with_verified_backup_and_is_idempotent(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    migration = _downgrade_to_preversioned_sqlite(tmp_path)
    backup = tmp_path / "pre-migration.p2pbackup"

    assert migration.migrate_to_current(backup_path=backup) == "migrated"
    assert backup.is_file()
    assert migration.schema_version() == SQLITE_SCHEMA_VERSION
    assert migration.migrate_to_current(backup_path=backup) == "current"
    assert migration.repository.integrity_check() == ()
    assert not (tmp_path / SQLITE_MAINTENANCE_MARKER).exists()


@pytest.mark.parametrize(
    "failure_stage",
    ("after_migration_fence", "after_migration_backup", "before_migration_commit"),
)
def test_migration_precommit_fault_rolls_back(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    _initialize(tmp_path)
    migration = _downgrade_to_preversioned_sqlite(tmp_path)
    backup = tmp_path / "migration-recovery.p2pbackup"

    def inject(stage: str) -> None:
        if stage == failure_stage:
            raise OSError(stage)

    with pytest.raises(OSError):
        migration.migrate_to_current(
            backup_path=backup,
            failure_injector=inject,
        )
    assert migration.schema_version() == 0
    assert migration._maintenance_state() == "ready"
    assert not (tmp_path / SQLITE_MAINTENANCE_MARKER).exists()
    assert migration.migrate_to_current(backup_path=backup) == "migrated"
    assert migration.schema_version() == SQLITE_SCHEMA_VERSION



@pytest.mark.parametrize(
    "failure_stage",
    (
        "after_migration_commit",
        "after_migration_verification",
        "before_migration_finalize",
    ),
)
def test_migration_postcommit_fault_resumes(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    _initialize(tmp_path)
    migration = _downgrade_to_preversioned_sqlite(tmp_path)
    backup = tmp_path / "migration-recovery.p2pbackup"

    def inject(stage: str) -> None:
        if stage == failure_stage:
            raise OSError(stage)

    with pytest.raises(OSError):
        migration.migrate_to_current(
            backup_path=backup,
            failure_injector=inject,
        )
    assert migration.schema_version() == SQLITE_SCHEMA_VERSION
    assert migration._maintenance_state() == "migrating"
    assert (tmp_path / SQLITE_MAINTENANCE_MARKER).is_file()
    assert migration.migrate_to_current(backup_path=backup) == "resumed"
    assert migration._maintenance_state() == "ready"
    assert migration.repository.integrity_check() == ()


def test_sql_and_credentials_stay_outside_public_and_domain_layers() -> None:
    package = Path(__file__).resolve().parents[1] / "src/p2p_engine"
    public_and_domain = [
        package / "core",
        package / "services",
        package / "mcp",
        package / "cli.py",
        package / "cli_commands",
    ]
    forbidden_sql = ("SELECT * FROM", "INSERT INTO", "PRAGMA journal_mode")
    for target in public_and_domain:
        paths = sorted(target.rglob("*.py")) if target.is_dir() else [target]
        for path in paths:
            source = path.read_text(encoding="utf-8")
            assert not any(fragment in source for fragment in forbidden_sql), path

    lowered = SQLITE_SCHEMA_V1.lower()
    assert "access_token" not in lowered
    assert "refresh_token" not in lowered
    assert "password" not in lowered
    assert "private_key" not in lowered

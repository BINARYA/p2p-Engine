from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path, PureWindowsPath

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app as cli_app
from p2p_engine.core.canonical_memory import ManagedBlob
from p2p_engine.core.mutation_receipts import MUTATION_RECEIPT_ROOT
from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    ProjectStateCommitResult,
    ProjectStateMutation,
    ProjectStateQuery,
    ProjectStorageError,
    ProjectStorageErrorCode,
    ProjectStorageManifest,
)
from p2p_engine.foundation.files import write_bytes_atomic
from p2p_engine.services.mutation_receipts import idempotency_key_sha256
from p2p_engine.services.project_application import (
    open_project_application,
    project_memory_recovery_apply,
    project_memory_recovery_status,
)
from p2p_engine.services.workspace_transactions import WorkspaceTransactionLockService
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.project_storage import (
    PROJECT_STORAGE_MANIFEST_PATH,
    ProjectStorageManifestStore,
)
from p2p_engine.storage.sqlite_adapter import (
    SQLITE_MAINTENANCE_MARKER,
    SQLiteBackupPort,
    SQLiteCompatibilityWorkspace,
    SQLiteMigrationPort,
)
from p2p_engine.storage.sqlite_driver import (
    SQLiteConnectionFactory,
    _windows_filesystem_type,
)
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


def _sqlite_revision_and_receipt_count(root: Path) -> tuple[int, int]:
    with sqlite3.connect(root / SQLITE_DATABASE_PATH) as connection:
        revision = connection.execute(
            "SELECT project_revision FROM projects"
        ).fetchone()
        receipt_count = connection.execute("SELECT count(*) FROM receipts").fetchone()
    assert revision is not None
    assert receipt_count is not None
    return int(revision[0]), int(receipt_count[0])


def _proposal_create_arguments(
    operation_key: str,
    *,
    title: str = "SQLite facade receipt",
) -> dict[str, object]:
    return {
        "title": title,
        "operation_key": operation_key,
        "actor": "owner",
        "problem": "The SQLite facade must preserve exact idempotent replay.",
        "proposal": "Commit project state and its public receipt atomically.",
        "acceptance_criteria": ["An exact retry returns already_applied."],
    }


def _structure_export_arguments(tmp_path: Path) -> dict[str, object]:
    return {
        "publisher": "acme",
        "vertical_id": "sqlite_export",
        "version": "1.0.0",
        "name": "SQLite Export",
        "license_id": "MIT",
        "primary_domain": {
            "key": "software",
            "name": "Software",
            "source": "local",
            "external_ref": None,
        },
        "domain_tags": ("software",),
        "lineage_mode": "independent",
        "materialization_target": tmp_path / "build" / "sqlite-export",
        "package_output": tmp_path / "dist" / "sqlite-export.p2pv",
        "actor_id": "owner",
        "executor_id": "owner",
        "executor_kind": "person",
    }


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


def test_windows_unc_and_remote_mapped_drives_are_rejected_as_multi_host() -> None:
    assert _windows_filesystem_type(
        PureWindowsPath("//server/share/project/.p2p/local/project.sqlite3")
    ) == "windows-remote"
    assert _windows_filesystem_type(
        PureWindowsPath("Z:/project/.p2p/local/project.sqlite3"),
        drive_type_resolver=lambda _root: 4,
    ) == "windows-remote"
    assert _windows_filesystem_type(
        PureWindowsPath("C:/project/.p2p/local/project.sqlite3"),
        drive_type_resolver=lambda _root: 3,
    ) == "windows-local"


def test_lost_commit_ack_keeps_blobs_referenced_by_the_durable_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _initialize(tmp_path)
    repository = app.adapter.repository
    content = b"durable blob after ambiguous commit acknowledgement"
    target, digest = _target_with_blob(app.canonical_memory_snapshot(), content)
    mutation = ProjectStateMutation(
        operation_id="sqlite-commit-ack-lost-with-blob",
        actor="owner",
        expected_revision=app.project_state_revision(),
        target=target,
        blob_payloads={digest: content},
    )

    class CommitThenError:
        def __init__(self, inner) -> None:
            self.inner = inner

        def __getattr__(self, name: str):
            return getattr(self.inner, name)

        def execute(self, sql: str, *args, **kwargs):
            result = self.inner.execute(sql, *args, **kwargs)
            if sql.strip().upper() == "COMMIT":
                raise sqlite3.OperationalError(
                    "simulated lost COMMIT acknowledgement"
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
    unit = SQLiteProjectUnitOfWork(repository)
    unit.stage(mutation)

    with pytest.raises(ProjectStorageError) as raised:
        unit.commit()

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert "acknowledgement was lost" in raised.value.safe_message
    fresh = SQLiteProjectStateRepository(tmp_path)
    assert fresh.current_revision().sha256 == target.semantic_state_digest
    assert sqlite_blob_path(tmp_path, digest).read_bytes() == content
    assert fresh.integrity_check() == ()

    replay = SQLiteProjectUnitOfWork(fresh)
    replay.stage(replace(mutation, expected_revision=fresh.current_revision()))
    assert replay.commit().replayed is True


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


def test_sqlite_activation_rejects_a_symlinked_memory_parent(tmp_path: Path) -> None:
    filesystem = _initialize(tmp_path, adapter=FILESYSTEM_ADAPTER)
    identity = filesystem.project_identity()
    proposals = tmp_path / ".p2p/proposals"
    external = tmp_path / "external-proposals"
    proposals.rename(external)
    proposals.symlink_to(external, target_is_directory=True)
    write_bytes_atomic(
        tmp_path / PROJECT_STORAGE_MANIFEST_PATH,
        ProjectStorageManifestStore.render(
            ProjectStorageManifest(
                project_uuid=identity.project_uuid.value,
                adapter=SQLITE_ADAPTER,
            )
        ),
    )

    with pytest.raises(ProjectStorageError) as raised:
        activate_sqlite_from_filesystem(tmp_path)

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert "symlink" in raised.value.safe_message.lower()
    assert not (tmp_path / SQLITE_DATABASE_PATH).exists()


def test_sqlite_activation_rejects_a_windows_reparse_point_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_initialization as initialization_module

    filesystem = _initialize(tmp_path, adapter=FILESYSTEM_ADAPTER)
    identity = filesystem.project_identity()
    proposals = tmp_path / ".p2p/proposals"
    is_link_or_reparse_point = initialization_module._is_link_or_reparse_point

    def mark_proposals_as_reparse_point(path: Path) -> bool:
        return path == proposals or is_link_or_reparse_point(path)

    monkeypatch.setattr(
        initialization_module,
        "_is_link_or_reparse_point",
        mark_proposals_as_reparse_point,
    )
    write_bytes_atomic(
        tmp_path / PROJECT_STORAGE_MANIFEST_PATH,
        ProjectStorageManifestStore.render(
            ProjectStorageManifest(
                project_uuid=identity.project_uuid.value,
                adapter=SQLITE_ADAPTER,
            )
        ),
    )

    with pytest.raises(ProjectStorageError) as raised:
        activate_sqlite_from_filesystem(tmp_path)

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert "reparse" in raised.value.safe_message.lower()
    assert not (tmp_path / SQLITE_DATABASE_PATH).exists()


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


def test_unit_of_work_rejects_operation_id_reuse_for_a_different_target(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    before = app.canonical_memory_snapshot()
    first_target = _target_with_documents(
        before,
        {"project:definition": "first operation payload"},
    )
    operation_id = "sqlite-operation-id-conflict"
    with app.project_state_unit_of_work() as unit:
        unit.stage(
            ProjectStateMutation(
                operation_id=operation_id,
                actor="owner",
                expected_revision=app.project_state_revision(),
                target=first_target,
                receipt_id="first-receipt",
            )
        )
        unit.commit()
    second_target = _target_with_documents(
        first_target,
        {"project:domain": "different operation payload"},
    )
    with app.project_state_unit_of_work() as unit:
        unit.stage(
            ProjectStateMutation(
                operation_id=operation_id,
                actor="owner",
                expected_revision=app.project_state_revision(),
                target=second_target,
                receipt_id="first-receipt",
            )
        )
        with pytest.raises(ProjectStorageError) as raised:
            unit.commit()

    assert raised.value.code == ProjectStorageErrorCode.idempotency_conflict
    assert app.project_state_revision().sha256 == first_target.semantic_state_digest


@pytest.mark.parametrize(
    "operation_id",
    (
        f"sqlite-public-mutation-{'a' * 64}",
        f"sqlite-restore-{'b' * 64}",
        "sqlite-bootstrap-forged",
    ),
)
def test_unit_of_work_rejects_reserved_operation_namespaces(
    tmp_path: Path,
    operation_id: str,
) -> None:
    app = _initialize(tmp_path)
    before = app.canonical_memory_snapshot()
    target = _target_with_documents(
        before,
        {"project:definition": operation_id},
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
        with pytest.raises(ProjectStorageError) as raised:
            unit.commit()

    assert raised.value.code == ProjectStorageErrorCode.configuration_contradiction
    assert app.project_state_revision().sha256 == before.semantic_state_digest
    assert app.adapter.repository.integrity_check() == ()


def test_sqlite_facade_exact_proposal_replay_and_status_are_stable(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    operation_key = "sqlite-facade-exact-replay-12345678"
    arguments = _proposal_create_arguments(operation_key)
    workspace = P2PWorkspace(tmp_path)

    first = workspace.create_proposal_with_operation_key(**arguments)

    assert first["mutation"]["status"] == "applied"
    assert workspace.mutation_status(idempotency_key=operation_key).state == "applied"
    receipt_root = tmp_path / MUTATION_RECEIPT_ROOT
    assert not receipt_root.exists() or not tuple(receipt_root.glob("*.yml"))
    authoritative_receipts = app.adapter.repository.public_mutation_receipts()
    assert [item.key_sha256 for item in authoritative_receipts] == [
        idempotency_key_sha256(operation_key)
    ]
    snapshot_after_first = workspace.canonical_memory_snapshot()
    proposals_after_first = workspace.proposal_summaries()
    counters_after_first = _sqlite_revision_and_receipt_count(tmp_path)

    replay = P2PWorkspace(tmp_path).create_proposal_with_operation_key(**arguments)

    reopened = P2PWorkspace(tmp_path)
    assert replay["mutation"]["status"] == "already_applied"
    assert reopened.mutation_status(idempotency_key=operation_key).state == "applied"
    assert reopened.canonical_memory_snapshot().semantic_state_digest == (
        snapshot_after_first.semantic_state_digest
    )
    assert reopened.proposal_summaries() == proposals_after_first
    assert _sqlite_revision_and_receipt_count(tmp_path) == counters_after_first


def test_sqlite_facade_same_key_writer_race_commits_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_adapter as sqlite_adapter_module

    app = _initialize(tmp_path)
    operation_key = "sqlite-facade-writer-race-12345678"
    arguments = _proposal_create_arguments(operation_key)
    revision_before, receipt_count_before = _sqlite_revision_and_receipt_count(tmp_path)
    proposal_count_before = len(app.proposal_summaries())
    first_commit_finished = threading.Event()
    projection_calls_lock = threading.Lock()
    projection_calls = 0
    normalize_receipts = sqlite_adapter_module._normalize_new_public_receipts
    commit = SQLiteProjectUnitOfWork.commit

    def normalize_receipts_then_race(**kwargs: object):
        nonlocal projection_calls
        receipts = normalize_receipts(**kwargs)
        with projection_calls_lock:
            projection_calls += 1
            call_number = projection_calls
        # Let writer one commit before writer two attempts to stage the state
        # projected from the old revision. A third call is writer two's retry
        # after it reopens the authoritative receipt from SQLite.
        if call_number == 2:
            assert first_commit_finished.wait(timeout=10)
        return receipts

    def commit_then_release(self: SQLiteProjectUnitOfWork):
        result = commit(self)
        if not result.replayed:
            first_commit_finished.set()
        return result

    monkeypatch.setattr(
        sqlite_adapter_module,
        "_normalize_new_public_receipts",
        normalize_receipts_then_race,
    )
    monkeypatch.setattr(SQLiteProjectUnitOfWork, "commit", commit_then_release)

    def write_once() -> dict[str, object]:
        workspace = P2PWorkspace(tmp_path)
        return workspace.create_proposal_with_operation_key(**arguments)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write_once) for _ in range(2)]
        results = [future.result(timeout=30) for future in futures]

    statuses = sorted(str(result["mutation"]["status"]) for result in results)
    proposal_ids = {
        str(result["proposal_create"]["proposal"]["proposal_id"])
        for result in results
    }
    reopened = P2PWorkspace(tmp_path)
    assert statuses == ["already_applied", "applied"]
    assert proposal_ids == {"PROP-001"}
    assert len(reopened.proposal_summaries()) == proposal_count_before + 1
    assert _sqlite_revision_and_receipt_count(tmp_path) == (
        revision_before + 1,
        receipt_count_before + 1,
    )
    assert reopened.mutation_status(idempotency_key=operation_key).state == "applied"
    receipt_root = tmp_path / MUTATION_RECEIPT_ROOT
    assert not receipt_root.exists() or not tuple(receipt_root.glob("*.yml"))
    assert [
        item.key_sha256
        for item in app.adapter.repository.public_mutation_receipts()
        if item.key_sha256 == idempotency_key_sha256(operation_key)
    ] == [idempotency_key_sha256(operation_key)]


def test_serialized_writer_can_advance_after_first_commit_before_first_returns(
    tmp_path: Path,
) -> None:
    first_app = _initialize(tmp_path)
    initial = first_app.canonical_memory_snapshot()
    first_target = _target_with_documents(
        initial,
        {"project:definition": "first serialized writer"},
    )
    first_unit = first_app.project_state_unit_of_work()
    first_unit.stage(
        ProjectStateMutation(
            operation_id="serialized-writer-first",
            actor="owner",
            expected_revision=first_app.project_state_revision(),
            target=first_target,
        )
    )
    first_committed = threading.Event()
    release_first = threading.Event()
    first_results: list[ProjectStateCommitResult] = []
    first_errors: list[BaseException] = []

    def pause_after_commit(stage: str) -> None:
        if stage == "after_commit":
            first_committed.set()
            assert release_first.wait(timeout=10)

    first_unit.failure_injector = pause_after_commit

    def commit_first() -> None:
        try:
            first_results.append(first_unit.commit())
        except BaseException as exc:  # pragma: no cover - asserted below.
            first_errors.append(exc)

    thread = threading.Thread(target=commit_first)
    thread.start()
    assert first_committed.wait(timeout=10)

    second_app = open_project_application(tmp_path)
    assert second_app.project_state_revision().sha256 == (
        first_target.semantic_state_digest
    )
    second_target = _target_with_documents(
        first_target,
        {"project:definition": "second serialized writer"},
    )
    with second_app.project_state_unit_of_work() as second_unit:
        second_unit.stage(
            ProjectStateMutation(
                operation_id="serialized-writer-second",
                actor="owner",
                expected_revision=second_app.project_state_revision(),
                target=second_target,
            )
        )
        second_result = second_unit.commit()

    release_first.set()
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert first_errors == []
    assert len(first_results) == 1
    assert first_results[0].revision.sha256 == first_target.semantic_state_digest
    assert second_result.revision.sha256 == second_target.semantic_state_digest
    assert open_project_application(tmp_path).project_state_revision().sha256 == (
        second_target.semantic_state_digest
    )


def test_sqlite_public_replay_accepts_different_generated_target_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.services import proposal_artifact_state

    _initialize(tmp_path)
    operation_key = "sqlite-generated-target-race-12345678"
    arguments = _proposal_create_arguments(operation_key)
    revision_before, receipt_count_before = _sqlite_revision_and_receipt_count(tmp_path)
    invoke = SQLiteCompatibilityWorkspace._invoke
    commit = SQLiteProjectUnitOfWork.commit
    timestamps = (
        "2026-08-31T12:00:00Z",
        "2026-08-31T12:00:01Z",
    )
    clocks: dict[int, str] = {}
    clocks_lock = threading.Lock()
    commit_barrier = threading.Barrier(2)
    observations: list[tuple[str, str, str]] = []
    observations_lock = threading.Lock()

    def deterministic_now() -> str:
        thread_id = threading.get_ident()
        with clocks_lock:
            if thread_id not in clocks:
                clocks[thread_id] = timestamps[len(clocks)]
            return clocks[thread_id]

    def invoke_without_replica_lock(
        self: SQLiteCompatibilityWorkspace,
        method_name: str,
        *args: object,
        **kwargs: object,
    ):
        kwargs.setdefault("_replica_lock_id", "test-concurrent-uow")
        return invoke(self, method_name, *args, **kwargs)

    def commit_together(self: SQLiteProjectUnitOfWork):
        mutation = self._mutation
        public_record = self._public_mutation
        assert mutation is not None
        assert public_record is not None
        with observations_lock:
            observations.append(
                (
                    mutation.target.semantic_state_digest,
                    public_record.receipt.request_fingerprint_sha256,
                    public_record.receipt.preview_token_sha256,
                )
            )
        commit_barrier.wait(timeout=10)
        return commit(self)

    monkeypatch.setattr(proposal_artifact_state, "_now", deterministic_now)
    monkeypatch.setattr(
        SQLiteCompatibilityWorkspace,
        "_invoke",
        invoke_without_replica_lock,
    )
    monkeypatch.setattr(SQLiteProjectUnitOfWork, "commit", commit_together)

    def write_once() -> dict[str, object]:
        return P2PWorkspace(tmp_path).create_proposal_with_operation_key(**arguments)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            future.result(timeout=30)
            for future in [pool.submit(write_once) for _ in range(2)]
        ]

    assert len({item[0] for item in observations}) == 2
    assert len({item[1] for item in observations}) == 1
    assert len({item[2] for item in observations}) == 1
    assert sorted(str(result["mutation"]["status"]) for result in results) == [
        "already_applied",
        "applied",
    ]
    assert {
        str(result["proposal_create"]["proposal"]["proposal_id"])
        for result in results
    } == {"PROP-001"}
    assert _sqlite_revision_and_receipt_count(tmp_path) == (
        revision_before + 1,
        receipt_count_before + 1,
    )


def test_sqlite_facade_conflicting_proposal_replay_does_not_duplicate_state(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    operation_key = "sqlite-facade-conflict-12345678"
    arguments = _proposal_create_arguments(operation_key)
    workspace = P2PWorkspace(tmp_path)
    first = workspace.create_proposal_with_operation_key(**arguments)
    assert first["mutation"]["status"] == "applied"
    snapshot_after_first = workspace.canonical_memory_snapshot()
    proposals_after_first = workspace.proposal_summaries()
    counters_after_first = _sqlite_revision_and_receipt_count(tmp_path)

    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        P2PWorkspace(tmp_path).create_proposal_with_operation_key(
            **_proposal_create_arguments(
                operation_key,
                title="A different request using the same key",
            )
        )

    reopened = P2PWorkspace(tmp_path)
    assert reopened.canonical_memory_snapshot().semantic_state_digest == (
        snapshot_after_first.semantic_state_digest
    )
    assert reopened.proposal_summaries() == proposals_after_first
    assert _sqlite_revision_and_receipt_count(tmp_path) == counters_after_first


def test_sqlite_facade_detects_real_proposal_postcondition_drift(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    create_key = "sqlite-facade-real-drift-create-12345678"
    create_arguments = _proposal_create_arguments(create_key)
    workspace = P2PWorkspace(tmp_path)
    created = workspace.create_proposal_with_operation_key(**create_arguments)
    proposal_id = str(created["proposal_create"]["proposal"]["proposal_id"])

    assert workspace.mutation_status(idempotency_key=create_key).state == "applied"
    updated = workspace.update_proposal_with_operation_key(
        proposal_id=proposal_id,
        operation_key="sqlite-facade-real-drift-update-12345678",
        actor="owner",
        problem="A later governed mutation changed the created proposal.",
    )
    assert updated["mutation"]["status"] == "applied"
    after_update = workspace.canonical_memory_snapshot()
    proposals_after_update = workspace.proposal_summaries()
    counters_after_update = _sqlite_revision_and_receipt_count(tmp_path)

    assert P2PWorkspace(tmp_path).mutation_status(idempotency_key=create_key).state == (
        "postcondition_drift"
    )
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_POSTCONDITION_DRIFT"):
        P2PWorkspace(tmp_path).create_proposal_with_operation_key(**create_arguments)

    reopened = P2PWorkspace(tmp_path)
    assert reopened.canonical_memory_snapshot().semantic_state_digest == (
        after_update.semantic_state_digest
    )
    assert reopened.proposal_summaries() == proposals_after_update
    assert _sqlite_revision_and_receipt_count(tmp_path) == counters_after_update


def test_sqlite_facade_lost_ack_after_commit_replays_one_proposal_and_receipt(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    operation_key = "sqlite-facade-lost-ack-12345678"
    arguments = _proposal_create_arguments(operation_key)
    proposal_count_before = len(app.proposal_summaries())
    _revision_before, receipt_count_before = _sqlite_revision_and_receipt_count(tmp_path)

    def inject(stage: str) -> None:
        if stage == "after_commit":
            raise OSError("injected lost acknowledgement after SQLite commit")

    app.adapter.repository.failure_injector = inject
    try:
        with pytest.raises(ProjectStorageError):
            app.create_proposal_with_operation_key(**arguments)
    finally:
        app.adapter.repository.failure_injector = None

    reopened = P2PWorkspace(tmp_path)
    proposal_count_after_commit = len(reopened.proposal_summaries())
    revision_after_commit, receipt_count_after_commit = (
        _sqlite_revision_and_receipt_count(tmp_path)
    )
    assert proposal_count_after_commit == proposal_count_before + 1
    assert receipt_count_after_commit == receipt_count_before + 1
    assert reopened.mutation_status(idempotency_key=operation_key).state == "applied"

    replay = reopened.create_proposal_with_operation_key(**arguments)

    assert replay["mutation"]["status"] == "already_applied"
    assert len(P2PWorkspace(tmp_path).proposal_summaries()) == proposal_count_after_commit
    assert _sqlite_revision_and_receipt_count(tmp_path) == (
        revision_after_commit,
        receipt_count_after_commit,
    )


def test_sqlite_facade_failure_before_commit_rolls_back_state_and_receipt(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    operation_key = "sqlite-facade-before-commit-rollback-12345678"
    arguments = _proposal_create_arguments(operation_key)
    snapshot_before = app.canonical_memory_snapshot()
    proposals_before = app.proposal_summaries()
    counters_before = _sqlite_revision_and_receipt_count(tmp_path)

    def inject(stage: str) -> None:
        if stage == "before_commit":
            raise OSError("injected failure before SQLite commit")

    app.adapter.repository.failure_injector = inject
    try:
        with pytest.raises(ProjectStorageError):
            app.create_proposal_with_operation_key(**arguments)
    finally:
        app.adapter.repository.failure_injector = None

    reopened = P2PWorkspace(tmp_path)
    assert reopened.canonical_memory_snapshot().semantic_state_digest == (
        snapshot_before.semantic_state_digest
    )
    assert reopened.proposal_summaries() == proposals_before
    assert _sqlite_revision_and_receipt_count(tmp_path) == counters_before
    assert reopened.mutation_status(idempotency_key=operation_key).state == "not_found"


def test_sqlite_structure_export_lost_ack_replays_db_owned_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P2P_HOME", str(tmp_path / "p2p-home"))
    app = _initialize(tmp_path / "project")
    arguments = _structure_export_arguments(tmp_path)
    preview = app.preview_project_structure_export(
        **{
            key: value
            for key, value in arguments.items()
            if key
            not in {
                "materialization_target",
                "package_output",
                "executor_kind",
            }
        }
    )
    operation_key = "sqlite-export-lost-ack-12345678"
    apply_arguments = {
        **arguments,
        "expected_structure_revision": preview.source.revision,
        "expected_structure_checksum": preview.source.checksum,
        "preview_token": preview.preview.preview_token,
        "operation_key": operation_key,
        "confirm": True,
    }

    def inject(stage: str) -> None:
        if stage == "after_commit":
            raise OSError("injected export acknowledgement loss")

    app.adapter.repository.failure_injector = inject
    try:
        with pytest.raises(ProjectStorageError):
            app.apply_project_structure_export(**apply_arguments)
    finally:
        app.adapter.repository.failure_injector = None

    key_hash = idempotency_key_sha256(operation_key)
    marker = (
        tmp_path
        / "project/.p2p/.internal/project-structure-exports"
        / f"{key_hash}.yml"
    )
    marker_relative = marker.relative_to(tmp_path / "project").as_posix()
    assert not marker.exists()
    assert marker_relative in app.adapter.repository.public_mutation_documents()

    replay = app.apply_project_structure_export(**apply_arguments)

    assert replay.status == "already_applied"
    assert marker.is_file()
    assert app.mutation_status(idempotency_key=operation_key).state == "applied"


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


def test_sqlite_bundle_manifest_uses_the_encoded_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _initialize(tmp_path)
    repository = app.adapter.repository
    snapshots = app.adapter.snapshots
    before = repository.snapshot()
    target = _target_with_documents(
        before,
        {"project:definition": "writer committed after bundle encoding"},
    )
    original_encode = snapshots.codec.encode_bundle
    injected = False

    def encode_then_write(store, snapshot):
        nonlocal injected
        encoded = original_encode(store, snapshot)
        if not injected:
            injected = True
            with SQLiteProjectUnitOfWork(repository) as unit:
                unit.stage(
                    ProjectStateMutation(
                        operation_id="sqlite-bundle-concurrent-writer",
                        actor="owner",
                        expected_revision=repository.current_revision(),
                        target=target,
                    )
                )
                unit.commit()
        return encoded

    monkeypatch.setattr(snapshots.codec, "encode_bundle", encode_then_write)
    output = tmp_path / "consistent.p2pbundle"

    result = snapshots.export_bundle_to(output)
    decoded = snapshots.codec.decode_bundle(output)

    assert injected is True
    assert result.manifest == decoded.manifest
    assert result.archive_sha256 == decoded.archive_sha256
    assert decoded.snapshot.semantic_state_digest == before.semantic_state_digest
    assert repository.snapshot().semantic_state_digest == target.semantic_state_digest


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


def test_online_backup_uses_the_revision_copied_by_sqlite(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    repository = app.adapter.repository
    before = repository.snapshot()
    target = _target_with_documents(
        before,
        {"project:definition": "writer committed while backup started"},
    )
    injected = False

    def inject(stage: str) -> None:
        nonlocal injected
        if stage != "before_online_backup" or injected:
            return
        injected = True
        with SQLiteProjectUnitOfWork(repository) as unit:
            unit.stage(
                ProjectStateMutation(
                    operation_id="sqlite-backup-concurrent-writer",
                    actor="owner",
                    expected_revision=repository.current_revision(),
                    target=target,
                )
            )
            unit.commit()

    backup = SQLiteBackupPort(repository, failure_injector=inject)
    archive = backup.create_backup()
    backup.verify_backup(archive)
    decoded = backup.codec.decode_physical_backup(archive.content)

    assert injected is True
    assert archive.semantic_state_digest == target.semantic_state_digest
    assert decoded.semantic_state_digest == target.semantic_state_digest


def test_online_backup_rejects_a_mismatched_declared_semantic_digest(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    backup = SQLiteBackupPort(app.adapter.repository)
    archive = backup.create_backup()

    with pytest.raises(ProjectStorageError) as raised:
        backup.verify_backup(replace(archive, semantic_state_digest="0" * 64))

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure


def test_existing_sqlite_backup_retry_normalizes_corruption_error(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    backup = SQLiteBackupPort(app.adapter.repository)
    corrupt = tmp_path / "corrupt-existing.p2pbackup"
    corrupt.write_bytes(b"not a physical backup")

    with pytest.raises(ProjectStorageError) as raised:
        backup._existing_backup_result(corrupt)

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure


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


def test_restore_rollback_never_replaces_live_database_with_corrupt_recovery(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    original = app.canonical_memory_snapshot()
    bundle = tmp_path / "original-for-corrupt-recovery.p2pbundle"
    app.canonical_bundle_export(bundle)
    changed = _target_with_documents(
        original,
        {"project:definition": "source before restore"},
    )
    with app.project_state_unit_of_work() as unit:
        unit.stage(
            ProjectStateMutation(
                operation_id="restore-corrupt-recovery-source",
                actor="owner",
                expected_revision=app.project_state_revision(),
                target=changed,
            )
        )
        unit.commit()

    def corrupt_recovery(stage: str) -> None:
        if stage == "after_restore_activation":
            recovery = tuple(
                (tmp_path / ".p2p/backups").glob("sqlite-recovery-*.sqlite3")
            )
            assert len(recovery) == 1
            recovery[0].write_bytes(b"corrupt recovery database\n")
            raise OSError("force rollback with corrupt recovery")

    backup = SQLiteBackupPort(
        app.adapter.repository,
        failure_injector=corrupt_recovery,
    )
    operation_key = "restore-corrupt-recovery-12345678"
    preview = backup.restore_preview(
        source=bundle,
        operation_key=operation_key,
        actor="owner",
    )

    with pytest.raises(ProjectStorageError) as raised:
        backup.restore_apply(
            source=bundle,
            operation_key=operation_key,
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )

    assert raised.value.code == ProjectStorageErrorCode.recovery_required
    active = SQLiteProjectStateRepository(tmp_path)
    assert active.integrity_check() == ()
    assert active.snapshot().semantic_state_digest == original.semantic_state_digest
    assert (tmp_path / SQLITE_MAINTENANCE_MARKER).is_file()
    recovery = tuple(
        (tmp_path / ".p2p/backups").glob("sqlite-recovery-*.sqlite3")
    )
    assert len(recovery) == 1
    assert recovery[0].read_bytes() == b"corrupt recovery database\n"


def test_restore_rollback_permission_error_retains_recovery_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_adapter as sqlite_adapter_module

    app = _initialize(tmp_path)
    source = tmp_path / "rollback-permission-source.p2pbundle"
    app.canonical_bundle_export(source)

    def inject(stage: str) -> None:
        if stage == "after_restore_activation":
            raise OSError("force restore rollback")

    backup = SQLiteBackupPort(app.adapter.repository, failure_injector=inject)
    operation_key = "sqlite-restore-rollback-permission-12345678"
    preview = backup.restore_preview(
        source=source,
        operation_key=operation_key,
        actor="owner",
    )
    database = tmp_path / SQLITE_DATABASE_PATH
    replace = sqlite_adapter_module.os.replace

    def deny_recovery_replace(source_path: object, target_path: object) -> None:
        source_candidate = Path(source_path)
        target_candidate = Path(target_path)
        if (
            source_candidate.parent == tmp_path / ".p2p/backups"
            and source_candidate.name.startswith("sqlite-recovery-")
            and target_candidate == database
        ):
            raise PermissionError("simulated Windows sharing violation")
        replace(source_path, target_path)

    monkeypatch.setattr(sqlite_adapter_module.os, "replace", deny_recovery_replace)

    with pytest.raises(ProjectStorageError) as raised:
        backup.restore_apply(
            source=source,
            operation_key=operation_key,
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )

    assert raised.value.code == ProjectStorageErrorCode.recovery_required
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    recovery = tuple((tmp_path / ".p2p/backups").glob("sqlite-recovery-*.sqlite3"))
    assert marker.is_file()
    assert len(recovery) == 1
    assert recovery[0].is_file()
    assert not database.exists()


def test_restore_marker_rejects_writer_between_preview_and_database_fence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_adapter as sqlite_adapter_module

    app = _initialize(tmp_path)
    source_snapshot = app.canonical_memory_snapshot()
    source = tmp_path / "restore-source.p2pbundle"
    app.canonical_bundle_export(source)
    current = _target_with_documents(
        app.canonical_memory_snapshot(),
        {"project:definition": "state visible when restore was previewed"},
    )
    with app.project_state_unit_of_work() as unit:
        unit.stage(
            ProjectStateMutation(
                operation_id="sqlite-restore-preview-current",
                actor="owner",
                expected_revision=app.project_state_revision(),
                target=current,
            )
        )
        unit.commit()
    backup = SQLiteBackupPort(app.adapter.repository)
    preview = backup.restore_preview(
        source=source,
        operation_key="sqlite-restore-cas-12345678",
        actor="owner",
    )
    late = _target_with_documents(
        current,
        {"project:domain": "writer committed after restore preview"},
    )
    fence_database = sqlite_adapter_module._fence_database
    injected = False
    blocked: list[ProjectStorageErrorCode] = []

    def fence_after_writer(repository, *, expected_revision: str, state: str) -> None:
        nonlocal injected
        if not injected:
            injected = True
            try:
                with SQLiteProjectUnitOfWork(repository) as unit:
                    unit.stage(
                        ProjectStateMutation(
                            operation_id="sqlite-restore-late-writer",
                            actor="owner",
                            expected_revision=repository.current_revision(),
                            target=late,
                        )
                    )
                    unit.commit()
            except ProjectStorageError as exc:
                blocked.append(exc.code)
        fence_database(
            repository,
            expected_revision=expected_revision,
            state=state,
        )

    monkeypatch.setattr(sqlite_adapter_module, "_fence_database", fence_after_writer)

    result = backup.restore_apply(
        source=source,
        operation_key="sqlite-restore-cas-12345678",
        actor="owner",
        preview_token=preview.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert injected is True
    assert blocked == [ProjectStorageErrorCode.recovery_required]
    assert app.adapter.repository.current_revision().sha256 == (
        source_snapshot.semantic_state_digest
    )
    assert app.adapter.repository.integrity_check() == ()
    assert not (tmp_path / SQLITE_MAINTENANCE_MARKER).exists()


def test_concurrent_restores_cannot_clear_another_owners_fence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_adapter as sqlite_adapter_module

    app = _initialize(tmp_path)
    source = tmp_path / "concurrent-restore-source.p2pbundle"
    app.canonical_bundle_export(source)
    current = _target_with_documents(
        app.canonical_memory_snapshot(),
        {"project:definition": "state before concurrent restore"},
    )
    with app.project_state_unit_of_work() as unit:
        unit.stage(
            ProjectStateMutation(
                operation_id="sqlite-concurrent-restore-current",
                actor="owner",
                expected_revision=app.project_state_revision(),
                target=current,
            )
        )
        unit.commit()
    first_backup = SQLiteBackupPort(app.adapter.repository)
    second_backup = SQLiteBackupPort(app.adapter.repository)
    operation_key = "sqlite-concurrent-restore-same-key-12345678"
    first_preview = first_backup.restore_preview(
        source=source,
        operation_key=operation_key,
        actor="owner",
    )
    second_preview = second_backup.restore_preview(
        source=source,
        operation_key=operation_key,
        actor="owner",
    )
    fence_database = sqlite_adapter_module._fence_database
    first_fenced = threading.Event()
    release_first = threading.Event()
    fence_calls_lock = threading.Lock()
    fence_calls = 0

    def hold_first_fence(repository, *, expected_revision: str, state: str) -> None:
        nonlocal fence_calls
        fence_database(
            repository,
            expected_revision=expected_revision,
            state=state,
        )
        with fence_calls_lock:
            fence_calls += 1
            call_number = fence_calls
        if call_number == 1:
            first_fenced.set()
            assert release_first.wait(timeout=10)

    monkeypatch.setattr(sqlite_adapter_module, "_fence_database", hold_first_fence)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            first_backup.restore_apply,
            source=source,
            operation_key=operation_key,
            actor="owner",
            preview_token=first_preview.preview_token,
            confirm=True,
        )
        assert first_fenced.wait(timeout=10)
        second = pool.submit(
            second_backup.restore_apply,
            source=source,
            operation_key=operation_key,
            actor="owner",
            preview_token=second_preview.preview_token,
            confirm=True,
        )
        try:
            with pytest.raises(ProjectStorageError) as raised:
                second.result(timeout=10)
            assert raised.value.code == ProjectStorageErrorCode.recovery_required
            assert (tmp_path / SQLITE_MAINTENANCE_MARKER).is_file()
            with sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH) as connection:
                state = connection.execute(
                    "SELECT maintenance_state FROM storage_metadata WHERE singleton = 1"
                ).fetchone()
            assert state == ("restoring",)
        finally:
            release_first.set()
        result = first.result(timeout=30)

    assert result.status == "applied"
    replay = second_backup.restore_apply(
        source=source,
        operation_key=operation_key,
        actor="owner",
        preview_token=second_preview.preview_token,
        confirm=True,
    )
    assert replay.replayed is True
    assert app.adapter.repository.integrity_check() == ()
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


def test_interrupted_sqlite_replica_lock_has_an_explicit_recovery_path(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    transaction_id = "sqlite-compat-interrupted-test"
    program = """
import sys
from pathlib import Path
from p2p_engine.services.workspace_transactions import WorkspaceTransactionLockService
root = Path(sys.argv[1])
WorkspaceTransactionLockService(root=root, p2p_dir=root / '.p2p').acquire(
    sys.argv[2], owner='owner'
)
"""
    subprocess.run(
        [sys.executable, "-c", program, str(tmp_path), transaction_id],
        check=True,
    )
    app = open_project_application(tmp_path)

    status = app.workspace_transaction_recovery_status()
    assert status.required is True
    assert status.transaction_id == transaction_id
    unauthorized = app.rollback_workspace_transaction(
        transaction_id=transaction_id,
        actor="contributor",
        confirm=True,
    )
    assert unauthorized.status == "blocked"
    assert app.workspace_transaction_recovery_status().required is True
    recovered = app.rollback_workspace_transaction(
        transaction_id=transaction_id,
        actor="owner",
        confirm=True,
    )

    assert recovered.status == "rolled_back"
    assert app.workspace_transaction_recovery_status().required is False
    assert app.refresh_agent_instructions(profile="generic").profile == "generic"


def test_sqlite_replica_writer_lock_wait_is_bounded_and_typed(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    lock = WorkspaceTransactionLockService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    lock.acquire("sqlite-compat-held-test", owner="owner")
    try:
        with pytest.raises(ProjectStorageError) as raised:
            app.refresh_agent_instructions(profile="generic")
    finally:
        lock.release("sqlite-compat-held-test")

    assert raised.value.code == ProjectStorageErrorCode.busy


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


def test_sqlite_replay_rematerializes_identity_adoption_backup(tmp_path: Path) -> None:
    _initialize(tmp_path, adapter=FILESYSTEM_ADAPTER)
    (tmp_path / ".p2p/project/identity.yml").unlink()
    (tmp_path / ".p2p/local/replica.yml").unlink()
    project_manifest = tmp_path / ".p2p/project.yml"
    legacy_manifest = yaml.safe_load(project_manifest.read_text(encoding="utf-8"))
    del legacy_manifest["project"]["uuid"]
    project_manifest.write_text(
        yaml.safe_dump(legacy_manifest, sort_keys=False),
        encoding="utf-8",
    )
    legacy = P2PWorkspace(tmp_path)
    arguments = {
        "operation_key": "sqlite-identity-adopt-12345678",
        "actor_id": "owner",
        "executor_id": "owner",
        "executor_kind": "person",
    }
    preview = legacy.preview_project_identity_adoption(**arguments)
    applied = legacy.apply_project_identity_adoption(
        **arguments,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    assert applied.status == "applied"
    identity = legacy.project_identity()
    write_bytes_atomic(
        tmp_path / PROJECT_STORAGE_MANIFEST_PATH,
        ProjectStorageManifestStore.render(
            ProjectStorageManifest(
                project_uuid=identity.project_uuid.value,
                adapter=SQLITE_ADAPTER,
            )
        ),
    )
    activate_sqlite_from_filesystem(tmp_path)
    app = open_project_application(tmp_path)
    durable_backups = {
        relative: content
        for relative, content in app.adapter.repository.public_mutation_documents().items()
        if relative.startswith(".p2p/.internal/identity-adoption-backups/")
    }
    assert durable_backups
    for relative in durable_backups:
        (tmp_path / relative).unlink()

    replay = app.apply_project_identity_adoption(
        **arguments,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert replay.status == "already_applied"
    assert {
        relative: (tmp_path / relative).read_bytes()
        for relative in durable_backups
    } == durable_backups


def test_concurrent_identity_derivations_preserve_fence_owner_and_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_adapter as sqlite_adapter_module

    first_workspace = _initialize(tmp_path)
    second_workspace = open_project_application(tmp_path)
    arguments = {
        "operation_key": "sqlite-identity-concurrent-derive-12345678",
        "actor_id": "owner",
        "executor_id": "owner",
        "executor_kind": "person",
    }
    preview = first_workspace.preview_project_identity_derivation(**arguments)
    fence_database = sqlite_adapter_module._fence_database
    first_fenced = threading.Event()
    release_first = threading.Event()
    fence_calls_lock = threading.Lock()
    fence_calls = 0

    def hold_first_fence(repository, *, expected_revision: str, state: str) -> None:
        nonlocal fence_calls
        fence_database(
            repository,
            expected_revision=expected_revision,
            state=state,
        )
        with fence_calls_lock:
            fence_calls += 1
            call_number = fence_calls
        if call_number == 1:
            first_fenced.set()
            assert release_first.wait(timeout=10)

    monkeypatch.setattr(sqlite_adapter_module, "_fence_database", hold_first_fence)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            first_workspace.apply_project_identity_derivation,
            **arguments,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )
        assert first_fenced.wait(timeout=10)
        second = pool.submit(
            second_workspace.apply_project_identity_derivation,
            **arguments,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )
        try:
            with pytest.raises(ProjectStorageError) as raised:
                second.result(timeout=10)
            assert raised.value.code == ProjectStorageErrorCode.recovery_required
            assert (tmp_path / SQLITE_MAINTENANCE_MARKER).is_file()
            with sqlite3.connect(tmp_path / SQLITE_DATABASE_PATH) as connection:
                state = connection.execute(
                    "SELECT maintenance_state FROM storage_metadata WHERE singleton = 1"
                ).fetchone()
            assert state == ("restoring",)
        finally:
            release_first.set()
        applied = first.result(timeout=30)

    replay = open_project_application(tmp_path).apply_project_identity_derivation(
        **arguments,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    assert applied.status == "applied"
    assert replay.status == "already_applied"
    assert replay.current == applied.current
    assert not (tmp_path / SQLITE_MAINTENANCE_MARKER).exists()
    assert open_project_application(tmp_path).adapter.repository.integrity_check() == ()


def test_identity_apply_cannot_overwrite_a_concurrent_agent_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refresh_workspace = _initialize(tmp_path)
    identity_workspace = open_project_application(tmp_path)
    arguments = {
        "operation_key": "sqlite-identity-agent-refresh-12345678",
        "actor_id": "owner",
        "executor_id": "owner",
        "executor_kind": "person",
    }
    preview = identity_workspace.preview_project_identity_derivation(**arguments)
    synchronize = SQLiteCompatibilityWorkspace._synchronize_auxiliary_state
    refresh_holds_lock = threading.Event()
    release_refresh = threading.Event()
    calls_lock = threading.Lock()
    calls = 0

    def hold_first_synchronization(
        self: SQLiteCompatibilityWorkspace,
        staged_root: Path,
    ) -> None:
        nonlocal calls
        with calls_lock:
            calls += 1
            call_number = calls
        if call_number == 1:
            refresh_holds_lock.set()
            assert release_refresh.wait(timeout=10)
        synchronize(self, staged_root)

    monkeypatch.setattr(
        SQLiteCompatibilityWorkspace,
        "_synchronize_auxiliary_state",
        hold_first_synchronization,
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        refreshed = pool.submit(
            refresh_workspace.refresh_agent_instructions,
            profile="claude",
        )
        assert refresh_holds_lock.wait(timeout=10)
        identity = pool.submit(
            identity_workspace.apply_project_identity_derivation,
            **arguments,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )
        assert not identity.done()
        release_refresh.set()
        refreshed.result(timeout=30)
        derived = identity.result(timeout=30)

    assert derived.status == "stale_preview"
    assert (tmp_path / "CLAUDE.md").is_file()
    policy = (tmp_path / ".p2p/agent-policy.yml").read_text(encoding="utf-8")
    assert "- claude" in policy
    assert not (tmp_path / SQLITE_MAINTENANCE_MARKER).exists()


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


def test_identity_auxiliary_inventory_excludes_casefolded_reserved_sqlite_paths(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    reserved = (
        ".p2p/local/PROJECT.SQLITE3",
        ".p2p/local/PROJECT.SQLITE3-WAL",
        ".p2p/local/STORAGE.YML",
        ".p2p/local/SQLITE-MAINTENANCE.JSON",
        ".p2p/local/SQLITE-ACTIVATION.JSON",
        ".p2p/local/SQLITE-RECOVERY-COMPLETIONS/receipt.json",
    )
    for relative in reserved:
        write_bytes_atomic(tmp_path / relative, b"must not be auxiliary\n")

    paths = SQLiteCompatibilityWorkspace._auxiliary_paths(tmp_path)

    assert not {Path(relative) for relative in reserved} & paths


def test_identity_rollback_never_replaces_live_database_with_corrupt_recovery(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    arguments = {
        "operation_key": "sqlite-identity-corrupt-recovery-12345678",
        "actor_id": "owner",
        "executor_id": "owner",
        "executor_kind": "person",
    }
    preview = app.preview_project_identity_derivation(**arguments)

    def corrupt_recovery(stage: str) -> None:
        if stage == "after_identity_activation":
            recovery = tuple(
                (tmp_path / ".p2p/backups").glob(
                    "sqlite-pre-identity-*.sqlite3"
                )
            )
            assert len(recovery) == 1
            recovery[0].write_bytes(b"corrupt identity recovery database\n")
            raise OSError("force identity rollback with corrupt recovery")

    app.adapter.repository.failure_injector = corrupt_recovery

    with pytest.raises(ProjectStorageError) as raised:
        app.apply_project_identity_derivation(
            **arguments,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )

    assert raised.value.code == ProjectStorageErrorCode.recovery_required
    active = SQLiteProjectStateRepository(tmp_path)
    assert active.integrity_check() == ()
    assert active.identity() == preview.candidate
    assert (tmp_path / SQLITE_MAINTENANCE_MARKER).is_file()
    recovery = tuple(
        (tmp_path / ".p2p/backups").glob("sqlite-pre-identity-*.sqlite3")
    )
    assert len(recovery) == 1
    assert recovery[0].read_bytes() == b"corrupt identity recovery database\n"


def test_identity_rollback_permission_error_retains_recovery_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_adapter as sqlite_adapter_module

    app = _initialize(tmp_path)
    arguments = {
        "operation_key": "sqlite-identity-rollback-permission-12345678",
        "actor_id": "owner",
        "executor_id": "owner",
        "executor_kind": "person",
    }
    preview = app.preview_project_identity_derivation(**arguments)

    def inject(stage: str) -> None:
        if stage == "after_identity_activation":
            raise OSError("force identity rollback")

    app.adapter.repository.failure_injector = inject
    database = tmp_path / SQLITE_DATABASE_PATH
    replace = sqlite_adapter_module.os.replace

    def deny_recovery_replace(source_path: object, target_path: object) -> None:
        source_candidate = Path(source_path)
        target_candidate = Path(target_path)
        if (
            source_candidate.parent == tmp_path / ".p2p/backups"
            and source_candidate.name.startswith("sqlite-pre-identity-")
            and target_candidate == database
        ):
            raise PermissionError("simulated Windows sharing violation")
        replace(source_path, target_path)

    monkeypatch.setattr(sqlite_adapter_module.os, "replace", deny_recovery_replace)

    with pytest.raises((PermissionError, ProjectStorageError)) as raised:
        app.apply_project_identity_derivation(
            **arguments,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )

    if isinstance(raised.value, ProjectStorageError):
        assert raised.value.code == ProjectStorageErrorCode.recovery_required
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    recovery = tuple(
        (tmp_path / ".p2p/backups").glob("sqlite-pre-identity-*.sqlite3")
    )
    assert marker.is_file()
    assert len(recovery) == 1
    assert recovery[0].is_file()
    assert not database.exists()


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


def _recover_interrupted_migration(root: Path) -> None:
    status = project_memory_recovery_status(root)
    assert status.state == "recovery_required"
    assert status.operation == "schema-migration"
    assert status.applicable is True
    recovered = project_memory_recovery_apply(
        root,
        recovery_id=status.recovery_id,
        recovery_token=status.recovery_token,
        actor="owner",
        action="rollback",
        confirm=True,
    )
    assert recovered.status == "rolled_back"
    assert recovered.operation == "schema-migration"


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
    assert migration._maintenance_state() == "migrating"
    assert (tmp_path / SQLITE_MAINTENANCE_MARKER).is_file()
    _recover_interrupted_migration(tmp_path)
    assert migration.schema_version() == 0
    assert migration._maintenance_state() == "ready"
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
def test_migration_postcommit_fault_requires_rollback_before_retry(
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
    with pytest.raises(ProjectStorageError) as raised:
        migration.migrate_to_current(backup_path=backup)
    assert raised.value.code == ProjectStorageErrorCode.recovery_required
    _recover_interrupted_migration(tmp_path)
    assert migration.schema_version() == 0
    assert migration.migrate_to_current(backup_path=backup) == "migrated"
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

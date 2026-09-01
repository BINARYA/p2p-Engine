from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Literal
from uuid import uuid4

from p2p_engine.core.canonical_memory import (
    BundleExportResult,
    BundleValidationResult,
    CanonicalMemorySnapshot,
    MemoryRecoveryStatus,
    MemoryRestorePreview,
    MemoryRestoreResult,
    PhysicalBackupResult,
    ProjectBundleManifest,
    canonical_json_bytes,
    semantic_sha256,
)
from p2p_engine.core.mutation_receipts import MUTATION_RECEIPT_ROOT
from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    ProjectArchive,
    ProjectStateMutation,
    ProjectStateRevision,
    ProjectStorageCapabilities,
    ProjectStorageError,
    ProjectStorageErrorCode,
    ProjectStorageManifest,
    ProjectStorageSelection,
)
from p2p_engine.core.workspace_schema import WorkspaceTransactionRecoveryResult
from p2p_engine.foundation.files import sync_directory, write_bytes_atomic
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.services.mutation_receipts import (
    parse_mutation_receipt,
    rebind_mutation_receipt_postconditions,
    render_mutation_receipt,
    validate_idempotency_key,
)
from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.workspace_transactions import (
    WorkspaceTransactionLockService,
    WorkspaceTransactionRecoveryService,
)
from p2p_engine.storage.canonical_memory import (
    FilesystemCanonicalMemoryStore,
    classify_memory_path,
)
from p2p_engine.storage.path_safety import (
    UnsafeProjectStoragePath,
    validate_confined_project_path,
)
from p2p_engine.storage.project_storage import (
    PROJECT_STORAGE_MANIFEST_PATH,
    ProjectStorageManifestStore,
)
from p2p_engine.storage.sqlite_project_state import (
    SQLiteBlobStore,
    SQLiteCanonicalStore,
    SQLiteProjectStateRepository,
    SQLiteProjectUnitOfWork,
    SQLitePublicMutationRecord,
    create_sqlite_database,
    install_sqlite_blob_bytes,
    read_sqlite_blob_bytes,
    sqlite_blob_path,
    sqlite_public_mutation_record,
    sqlite_public_receipt_document_path,
    sqlite_public_receipt_operation_id,
)
from p2p_engine.storage.sqlite_recovery import (
    SQLiteRecoveryCoordinator,
    new_sqlite_recovery_identity,
    write_sqlite_auxiliary_backup,
)
from p2p_engine.storage.sqlite_schema import (
    SQLITE_ACTIVATION_MARKER,
    SQLITE_ADAPTER,
    SQLITE_DATABASE_PATH,
    SQLITE_MAINTENANCE_MARKER,
    SQLITE_SCHEMA_CONTRACT,
    SQLITE_SCHEMA_V1_SHA256,
    SQLITE_SCHEMA_VERSION,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sync_directories(*directories: Path) -> bool:
    """Best-effort directory sync without claiming support where it is absent."""
    synced = True
    seen: set[Path] = set()
    for directory in directories:
        if directory in seen:
            continue
        seen.add(directory)
        synced = sync_directory(directory) and synced
    return synced


def _replace_and_sync_directories(source: Path, target: Path) -> bool:
    os.replace(source, target)
    return _sync_directories(target.parent, source.parent)


def _unlink_and_sync_directory(path: Path, *, missing_ok: bool = True) -> bool:
    try:
        path.unlink()
    except FileNotFoundError:
        if missing_ok:
            return True
        raise
    return sync_directory(path.parent)


def _remove_tree_and_sync_parent(path: Path) -> bool:
    existed = path.exists()
    shutil.rmtree(path, ignore_errors=True)
    if existed and not path.exists():
        return sync_directory(path.parent)
    return not existed


def _is_link_or_reparse_point(path: Path) -> bool:
    """Recognize POSIX links and Windows junction/reparse-point indirection."""
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if callable(is_junction) and is_junction():
            return True
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_flag)


def _path_escapes_root(root: Path, path: Path) -> bool:
    try:
        return not path.resolve(strict=False).is_relative_to(root.resolve())
    except OSError:
        return True


def _assert_safe_path_components(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary path escapes the project root",
            diagnostic=str(path),
        ) from exc
    current = root
    for part in relative.parts:
        current /= part
        if _is_link_or_reparse_point(current) or _path_escapes_root(root, current):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite auxiliary path contains a symlink, junction or reparse point",
                diagnostic=relative.as_posix(),
            )


def _assert_confined_workspace_path(
    root: Path,
    path: Path,
    *,
    expected: Literal["file", "directory"],
    must_exist: bool,
    operation: str,
) -> Path:
    try:
        return validate_confined_project_path(
            root,
            path,
            expected=expected,
            must_exist=must_exist,
        )
    except UnsafeProjectStoragePath as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            f"SQLite {operation} workspace path is unsafe",
            diagnostic=f"{path}: {exc}",
        ) from exc


def _read_confined_project_file(
    root: Path,
    path: Path,
    *,
    operation: str,
) -> bytes:
    """Read one project file only while it remains a confined regular file."""

    _assert_confined_workspace_path(
        root,
        path,
        expected="file",
        must_exist=True,
        operation=operation,
    )
    content = path.read_bytes()
    _assert_confined_workspace_path(
        root,
        path,
        expected="file",
        must_exist=True,
        operation=operation,
    )
    return content


def _portable_project_locator(root: PurePath, path: PurePath) -> str:
    """Serialize a project-relative marker path with platform-neutral separators."""
    return path.relative_to(root).as_posix()


class _CommittedMaintenanceFenceError(ProjectStorageError):
    """The maintenance fence committed but post-commit verification failed."""


def _assert_safe_regular_file(root: Path, path: Path) -> None:
    _assert_safe_path_components(root, path)
    if not path.is_file():
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary artifact is not a regular file",
            diagnostic=str(path),
        )


def _assert_safe_directory_tree(root: Path, directory: Path) -> None:
    _assert_safe_path_components(root, directory)
    if not directory.is_dir():
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary artifact is not a directory",
            diagnostic=str(directory),
        )
    for path in directory.rglob("*"):
        _assert_safe_path_components(root, path)


def _receipt_documents(root: Path) -> dict[str, bytes]:
    receipt_root = root / MUTATION_RECEIPT_ROOT
    if not receipt_root.exists():
        return {}
    if receipt_root.is_symlink() or not receipt_root.is_dir():
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "public mutation receipt directory is unsafe",
        )
    documents: dict[str, bytes] = {}
    for path in sorted(receipt_root.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".yml":
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "public mutation receipt path is unsafe",
            )
        relative = path.relative_to(root).as_posix()
        documents[relative] = path.read_bytes()
    return documents


def _normalize_new_public_receipts(
    *,
    staged_root: Path,
    store: FilesystemCanonicalMemoryStore,
    before_documents: Mapping[str, bytes],
    snapshot: CanonicalMemorySnapshot,
) -> tuple[SQLitePublicMutationRecord, ...]:
    """Bind new physical postconditions to SQLite's canonical projection bytes."""
    after_documents = _receipt_documents(staged_root)
    changed_existing = sorted(
        relative
        for relative, content in before_documents.items()
        if after_documents.get(relative) != content
    )
    if changed_existing:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "public mutation receipts are immutable",
            diagnostic=", ".join(changed_existing),
        )
    new_paths = sorted(set(after_documents) - set(before_documents))
    if len(new_paths) > 1:
        raise ProjectStorageError(
            ProjectStorageErrorCode.internal,
            "one compatibility command produced multiple public receipts",
        )
    canonical_documents = store.activation_documents(snapshot.entities)
    records: list[SQLitePublicMutationRecord] = []
    for relative in new_paths:
        path = staged_root / relative
        receipt = parse_mutation_receipt(
            after_documents[relative],
            expected_key_sha256=path.stem,
        )
        projection_candidates: dict[str, bytes] = {}
        durable_documents: dict[str, bytes] = {}
        for postcondition in receipt.postconditions:
            target = staged_root / postcondition.path
            if target.is_symlink() or not target.is_file():
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "public mutation receipt targets a missing or unsafe projection",
                    diagnostic=postcondition.path,
                )
            current = target.read_bytes()
            if hashlib.sha256(current).hexdigest() != postcondition.physical_sha256:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "new public mutation receipt disagrees with its projected state",
                    diagnostic=postcondition.path,
                )
            canonical = canonical_documents.get(postcondition.path)
            if canonical is not None:
                write_bytes_atomic(target, canonical)
                current = canonical
            elif sqlite_public_receipt_document_path(postcondition.path):
                durable_documents[postcondition.path] = current
            projection_candidates[postcondition.path] = current
        normalized = rebind_mutation_receipt_postconditions(
            receipt,
            projection_candidates,
        )
        write_bytes_atomic(path, render_mutation_receipt(normalized))
        records.append(sqlite_public_mutation_record(normalized, durable_documents))
    return tuple(records)


class SQLiteSnapshotPort:
    def __init__(self, repository: SQLiteProjectStateRepository) -> None:
        self.repository = repository
        self.store = SQLiteCanonicalStore(repository)
        self.codec = CanonicalBundleCodec()

    def _export_bundle_parts(self) -> tuple[ProjectArchive, ProjectBundleManifest]:
        snapshot = self.repository.snapshot()
        content, manifest = self.codec.encode_bundle(self.store, snapshot)
        return (
            ProjectArchive(
                kind="portable_bundle",
                content=content,
                sha256=hashlib.sha256(content).hexdigest(),
                semantic_state_digest=snapshot.semantic_state_digest,
            ),
            manifest,
        )

    def export_bundle(self) -> ProjectArchive:
        archive, _manifest = self._export_bundle_parts()
        return archive

    def verify_bundle(self, archive: ProjectArchive):
        if archive.kind != "portable_bundle":
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "archive is not a portable project bundle",
            )
        try:
            decoded = self.codec.decode_bundle(archive.content)
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "portable project bundle is invalid",
                diagnostic=str(exc),
            ) from exc
        if decoded.archive_sha256 != archive.sha256:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "portable project bundle digest does not match",
            )
        return decoded.snapshot

    def bundle_metadata(self) -> BundleExportResult:
        archive, manifest = self._export_bundle_parts()
        return BundleExportResult(
            status="ready",
            output="",
            manifest=manifest,
            archive_sha256=archive.sha256,
            archive_size=len(archive.content),
        )

    def export_bundle_to(self, output: Path) -> BundleExportResult:
        archive, manifest = self._export_bundle_parts()
        target = output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        write_bytes_atomic(target, archive.content)
        return BundleExportResult(
            status="exported",
            output=str(target),
            manifest=manifest,
            archive_sha256=archive.sha256,
            archive_size=len(archive.content),
        )

    def verify_archive(self, source: Path) -> BundleValidationResult:
        try:
            decoded = self.codec.decode_bundle(source)
        except ValueError:
            try:
                physical = self.codec.decode_physical_backup(source)
                _verify_sqlite_backup(self.repository.root, physical.files, physical.manifest)
            except (ValueError, ProjectStorageError) as exc:
                return BundleValidationResult(
                    status="invalid",
                    archive_kind="unknown",
                    issues=(str(exc),),
                )
            return BundleValidationResult(
                status="valid",
                archive_kind="physical_backup",
                project_uuid=physical.project_uuid,
                semantic_state_digest=physical.semantic_state_digest,
                archive_sha256=physical.archive_sha256,
            )
        return BundleValidationResult(
            status="valid",
            archive_kind="portable_bundle",
            project_uuid=decoded.snapshot.project_uuid,
            semantic_state_digest=decoded.snapshot.semantic_state_digest,
            archive_sha256=decoded.archive_sha256,
            entity_count=len(decoded.snapshot.entities),
            relation_count=len(decoded.snapshot.relations),
            lineage_count=len(decoded.snapshot.lineage),
            blob_count=len(decoded.snapshot.blobs),
        )


class SQLiteBackupPort:
    def __init__(
        self,
        repository: SQLiteProjectStateRepository,
        *,
        failure_injector=None,
    ) -> None:
        self.repository = repository
        self.codec = CanonicalBundleCodec()
        self.failure_injector = failure_injector

    def create_backup(self) -> ProjectArchive:
        content, snapshot = self._backup_content()
        return ProjectArchive(
            kind="physical_backup",
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
            semantic_state_digest=snapshot.semantic_state_digest,
        )

    def verify_backup(self, archive: ProjectArchive) -> None:
        if archive.kind != "physical_backup":
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "archive is not a physical project backup",
            )
        try:
            decoded = self.codec.decode_physical_backup(archive.content)
            _verify_sqlite_backup(self.repository.root, decoded.files, decoded.manifest)
        except ProjectStorageError:
            raise
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite physical backup is invalid",
                diagnostic=str(exc),
            ) from exc
        if decoded.archive_sha256 != archive.sha256:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite physical backup digest does not match",
            )
        if decoded.semantic_state_digest != archive.semantic_state_digest:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite physical backup semantic digest does not match",
            )

    def backup_to(self, output: Path, *, coordinated: bool = True) -> PhysicalBackupResult:
        return self._backup_to(output, coordinated=coordinated, allow_internal=False)

    def _backup_to(
        self,
        output: Path,
        *,
        coordinated: bool = True,
        allow_internal: bool,
    ) -> PhysicalBackupResult:
        if not coordinated:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "SQLite physical backup must be coordinated",
            )
        lexical_target = output.absolute()
        internal_target = lexical_target.is_relative_to(
            self.repository.root / ".p2p"
        )
        if allow_internal and internal_target:
            target = lexical_target
            _assert_confined_workspace_path(
                self.repository.root,
                target,
                expected="file",
                must_exist=False,
                operation="internal backup",
            )
        else:
            target = output.resolve()
        if not allow_internal and target.is_relative_to(self.repository.root / ".p2p"):
            raise ValueError("P2P_BACKUP_OUTPUT_UNSAFE: backup output must be outside .p2p")
        if target.exists() or _is_link_or_reparse_point(target):
            raise ValueError("P2P_BACKUP_OUTPUT_EXISTS: refusing to overwrite backup output")
        archive = self.create_backup()
        target.parent.mkdir(parents=True, exist_ok=True)
        if allow_internal and internal_target:
            _assert_confined_workspace_path(
                self.repository.root,
                target.parent,
                expected="directory",
                must_exist=True,
                operation="internal backup",
            )
            _assert_confined_workspace_path(
                self.repository.root,
                target,
                expected="file",
                must_exist=False,
                operation="internal backup",
            )
        write_bytes_atomic(target, archive.content, mode=0o600)
        decoded = self.codec.decode_physical_backup(archive.content)
        return PhysicalBackupResult(
            status="created",
            output=str(target),
            project_uuid=decoded.project_uuid,
            source_revision=str(decoded.manifest["source_revision"]),
            archive_sha256=archive.sha256,
            archive_size=len(archive.content),
            file_count=len(decoded.files),
            coordinated=True,
        )

    def restore_preview(
        self, *, source: Path, operation_key: str, actor: str
    ) -> MemoryRestorePreview:
        try:
            validate_idempotency_key(operation_key)
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                str(exc),
            ) from exc
        _require_sqlite_owner(
            self.repository,
            actor,
            operation="project_memory_restore",
        )
        current = self.repository.snapshot()
        target_uuid, target_digest, archive_sha, entity_count = self._restore_target(source)
        if target_uuid != current.project_uuid:
            raise ProjectStorageError(
                ProjectStorageErrorCode.identity_mismatch,
                "restore archive belongs to another project",
            )
        token = semantic_sha256(
            {
                "operation_key": operation_key,
                "actor": actor,
                "archive_sha256": archive_sha,
                "current": current.semantic_state_digest,
                "target": target_digest,
            }
        )
        return MemoryRestorePreview(
            status="ready",
            operation_key=operation_key,
            archive_kind=_archive_kind(self.codec, source),
            archive_sha256=archive_sha,
            project_uuid=target_uuid,
            current_semantic_digest=current.semantic_state_digest,
            target_semantic_digest=target_digest,
            preview_token=token,
            changed_entity_count=entity_count,
        )

    def restore_apply(
        self,
        *,
        source: Path,
        operation_key: str,
        actor: str,
        preview_token: str,
        confirm: bool,
    ) -> MemoryRestoreResult:
        transaction_id = f"sqlite-restore-{uuid4().hex}"
        lock = WorkspaceTransactionLockService(
            root=self.repository.root,
            p2p_dir=self.repository.root / ".p2p",
        )
        try:
            lock.acquire(transaction_id, owner=actor)
        except ValueError as exc:
            code = (
                ProjectStorageErrorCode.recovery_required
                if (
                    (self.repository.root / SQLITE_MAINTENANCE_MARKER).exists()
                    or _is_link_or_reparse_point(
                        self.repository.root / SQLITE_MAINTENANCE_MARKER
                    )
                )
                else ProjectStorageErrorCode.busy
            )
            raise ProjectStorageError(
                code,
                "SQLite restore could not acquire the project transaction lock",
                diagnostic=str(exc),
            ) from exc
        try:
            return self._restore_apply_locked(
                source=source,
                operation_key=operation_key,
                actor=actor,
                preview_token=preview_token,
                confirm=confirm,
                transaction_id=transaction_id,
            )
        finally:
            if lock.status().transaction_id == transaction_id:
                lock.release(transaction_id)

    def _restore_apply_locked(
        self,
        *,
        source: Path,
        operation_key: str,
        actor: str,
        preview_token: str,
        confirm: bool,
        transaction_id: str,
    ) -> MemoryRestoreResult:
        if not confirm:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "SQLite restore requires explicit confirmation",
            )
        try:
            validate_idempotency_key(operation_key)
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                str(exc),
            ) from exc
        # Apply re-authorizes against the current authoritative state. A
        # preview is evidence of intent, never an authorization grant.
        _require_sqlite_owner(
            self.repository,
            actor,
            operation="project_memory_restore",
        )
        replay = self._restore_replay(
            source=source,
            operation_key=operation_key,
            actor=actor,
        )
        if replay is not None:
            return replay
        preview = self.restore_preview(source=source, operation_key=operation_key, actor=actor)
        if preview.preview_token != preview_token:
            raise ProjectStorageError(
                ProjectStorageErrorCode.stale_revision,
                "SQLite restore preview is stale or does not match the archive",
            )
        local_dir = self.repository.root / ".p2p/local"
        backup_dir = self.repository.root / ".p2p/backups"
        _assert_confined_workspace_path(
            self.repository.root,
            local_dir,
            expected="directory",
            must_exist=True,
            operation="restore",
        )
        _assert_confined_workspace_path(
            self.repository.root,
            backup_dir,
            expected="directory",
            must_exist=False,
            operation="restore",
        )
        backup_dir.mkdir(parents=True, exist_ok=True)
        _assert_confined_workspace_path(
            self.repository.root,
            backup_dir,
            expected="directory",
            must_exist=True,
            operation="restore",
        )
        source_revision_key = preview.current_semantic_digest[:24]
        backup_path = backup_dir / (
            f"sqlite-pre-restore-{operation_key_sha(operation_key)}-"
            f"{source_revision_key}.p2pbackup"
        )
        backup_result: PhysicalBackupResult | None = None
        recovery_id, recovery_token = new_sqlite_recovery_identity()
        recovery_path = backup_dir / f"sqlite-recovery-{recovery_id}.sqlite3"
        marker = self.repository.root / SQLITE_MAINTENANCE_MARKER
        staging_dir = local_dir / (
            f"sqlite-restore-{recovery_id}.stage"
        )
        for candidate in (backup_path, recovery_path):
            _assert_confined_workspace_path(
                self.repository.root,
                candidate,
                expected="file",
                must_exist=False,
                operation="restore",
            )
        if recovery_path.exists() or _is_link_or_reparse_point(recovery_path):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite restore recovery path already exists",
            )
        _assert_confined_workspace_path(
            self.repository.root,
            staging_dir,
            expected="directory",
            must_exist=False,
            operation="restore",
        )
        staging_dir.mkdir(parents=True, exist_ok=False)
        _assert_confined_workspace_path(
            self.repository.root,
            staging_dir,
            expected="directory",
            must_exist=True,
            operation="restore",
        )
        stage_db = staging_dir / "project.sqlite3"
        _assert_confined_workspace_path(
            self.repository.root,
            stage_db,
            expected="file",
            must_exist=False,
            operation="restore",
        )
        marker_payload: dict[str, object] = {
            "contract": "p2p-sqlite-maintenance/v2",
            "recovery_id": recovery_id,
            "recovery_token": recovery_token,
            "operation": "restore",
            "operation_key": operation_key,
            "actor": actor,
            "transaction_id": transaction_id,
            "phase": "prepared",
            "source": {
                "project_uuid": preview.project_uuid,
                "semantic_state_digest": preview.current_semantic_digest,
            },
            "target": {
                "project_uuid": preview.project_uuid,
                "semantic_state_digest": preview.target_semantic_digest,
            },
            "stage": _portable_project_locator(self.repository.root, staging_dir),
            "recovery": _portable_project_locator(self.repository.root, recovery_path),
            "backup": _portable_project_locator(self.repository.root, backup_path),
            "blob_changes": [],
        }
        owns_marker = False
        owns_fence = False
        safe_to_clear_marker = False
        result: MemoryRestoreResult | None = None
        try:
            _write_marker(
                marker,
                marker_payload,
            )
            owns_marker = True
            try:
                _fence_database(
                    self.repository,
                    expected_revision=preview.current_semantic_digest,
                    state="restoring",
                )
            except _CommittedMaintenanceFenceError:
                owns_fence = True
                raise
            owns_fence = True
            _update_marker(marker, marker_payload, phase="fenced")
            self._inject("after_restore_marker")
            _assert_confined_workspace_path(
                self.repository.root,
                backup_path,
                expected="file",
                must_exist=False,
                operation="restore",
            )
            backup_result = (
                self._existing_backup_result(
                    backup_path,
                    expected_source_revision=preview.current_semantic_digest,
                )
                if backup_path.exists()
                else self._backup_to(
                    backup_path,
                    coordinated=True,
                    allow_internal=True,
                )
            )
            _update_marker(marker, marker_payload, phase="backup_created")
            blob_payloads = self._prepare_restore_database(source, stage_db)
            marker_payload["blob_changes"] = [
                {
                    "path": sqlite_blob_path(self.repository.root, digest)
                    .relative_to(self.repository.root)
                    .as_posix(),
                    "digest": digest,
                    "existed_before": sqlite_blob_path(
                        self.repository.root,
                        digest,
                    ).exists(),
                }
                for digest in sorted(blob_payloads)
            ]
            _update_marker(marker, marker_payload, phase="staged")
            self._inject("after_restore_stage")
            staged = SQLiteProjectStateRepository(
                self.repository.root,
                database_path=stage_db,
            )
            issues = staged.integrity_check(verify_blobs=False)
            if issues or staged.snapshot().semantic_state_digest != preview.target_semantic_digest:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "staged SQLite restore failed verification",
                    diagnostic="; ".join(issues),
            )
            _checkpoint(self.repository)
            _assert_confined_workspace_path(
                self.repository.root,
                recovery_path,
                expected="file",
                must_exist=False,
                operation="restore",
            )
            if recovery_path.exists() or _is_link_or_reparse_point(recovery_path):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite restore recovery path changed before activation",
                )
            _replace_and_sync_directories(
                self.repository.database_path,
                recovery_path,
            )
            _assert_confined_workspace_path(
                self.repository.root,
                recovery_path,
                expected="file",
                must_exist=True,
                operation="restore",
            )
            _update_marker(marker, marker_payload, phase="old_moved")
            self._inject("after_restore_old_database_move")
            _assert_confined_workspace_path(
                self.repository.root,
                stage_db,
                expected="file",
                must_exist=True,
                operation="restore",
            )
            _replace_and_sync_directories(stage_db, self.repository.database_path)
            _update_marker(marker, marker_payload, phase="activated")
            _install_blob_payloads(self.repository.root, blob_payloads)
            _update_marker(marker, marker_payload, phase="side_effects_applied")
            self._inject("after_restore_activation")
            final_issues = self.repository.integrity_check()
            if final_issues:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "activated SQLite restore failed verification",
                    diagnostic="; ".join(final_issues),
                )
            final = self.repository.snapshot()
            result = MemoryRestoreResult(
                status="applied",
                operation_key=operation_key,
                archive_kind=preview.archive_kind,
                project_uuid=final.project_uuid,
                semantic_state_digest=final.semantic_state_digest,
                archive_sha256=preview.archive_sha256,
                preview_token=preview.preview_token,
                backup_path=backup_result.output,
                recovery_path=str(recovery_path),
                changed_entity_count=preview.changed_entity_count,
                message="SQLite project state restored through staged atomic activation.",
            )
            self._record_restore_receipt(
                result,
                actor=actor,
                expected_revision=preview.current_semantic_digest,
            )
            _update_marker(marker, marker_payload, phase="receipt_committed")
            self._inject("after_restore_receipt")
            safe_to_clear_marker = True
        except Exception as original:
            try:
                if owns_fence:
                    _assert_confined_workspace_path(
                        self.repository.root,
                        recovery_path,
                        expected="file",
                        must_exist=False,
                        operation="restore rollback",
                    )
                    if recovery_path.is_file():
                        _verify_recovered_database(
                            self.repository.root,
                            database_path=recovery_path,
                            project_uuid=preview.project_uuid,
                            semantic_state_digest=preview.current_semantic_digest,
                        )
                        _unlink_and_sync_directory(self.repository.database_path)
                        _replace_and_sync_directories(
                            recovery_path,
                            self.repository.database_path,
                        )
                    if self.repository.database_path.is_file():
                        _set_database_maintenance_state(self.repository, "ready")
                    _rollback_blob_changes(
                        self.repository.root,
                        marker_payload.get("blob_changes"),
                    )
                    _verify_recovered_database(
                        self.repository.root,
                        project_uuid=preview.project_uuid,
                        semantic_state_digest=preview.current_semantic_digest,
                    )
                safe_to_clear_marker = True
            except Exception as rollback_error:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.recovery_required,
                    "SQLite restore rollback did not complete; explicit recovery is required",
                    diagnostic=(
                        f"forward failure: {original}; rollback failure: {rollback_error}"
                    ),
                ) from rollback_error
            raise
        finally:
            if not owns_marker or safe_to_clear_marker:
                if staging_dir.exists() or _is_link_or_reparse_point(staging_dir):
                    _assert_confined_workspace_path(
                        self.repository.root,
                        staging_dir,
                        expected="directory",
                        must_exist=True,
                        operation="restore cleanup",
                    )
                    _remove_tree_and_sync_parent(staging_dir)
            if owns_marker and safe_to_clear_marker:
                _unlink_and_sync_directory(marker)
        assert result is not None
        return result

    def recovery_status(self) -> MemoryRecoveryStatus:
        return SQLiteRecoveryCoordinator(self.repository.root).status()

    def _restore_replay(
        self,
        *,
        source: Path,
        operation_key: str,
        actor: str,
    ) -> MemoryRestoreResult | None:
        operation_id = _restore_operation_id(operation_key)
        with self.repository.connections.connect(writable=False) as connection:
            row = connection.execute(
                "SELECT actor, result_json FROM receipts WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        if row is None:
            return None
        _project_uuid, _digest, archive_sha, _count = self._restore_target(source)
        payload = json.loads(str(row["result_json"]))
        if str(row["actor"]) != actor or str(payload.get("archive_sha256") or "") != archive_sha:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: restore key was used by another actor or archive"
            )
        return _restore_result_from_payload(payload, replayed=True)

    def _record_restore_receipt(
        self,
        result: MemoryRestoreResult,
        *,
        actor: str,
        expected_revision: str,
    ) -> None:
        operation_id = _restore_operation_id(result.operation_key)
        now = _utc_now()
        with self.repository.connections.connect(writable=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "INSERT INTO receipts(operation_id, receipt_id, project_uuid, actor, "
                    "expected_revision_sha256, result_revision_sha256, status, result_json, "
                    "created_at) VALUES (?, ?, ?, ?, ?, ?, 'applied', ?, ?)",
                    (
                        operation_id,
                        operation_id,
                        result.project_uuid,
                        actor,
                        expected_revision,
                        result.semantic_state_digest,
                        _json_text(result.to_dict()),
                        now,
                    ),
                )
                connection.execute(
                    "INSERT INTO operation_records(operation_id, project_uuid, operation_kind, "
                    "status, started_at, completed_at) "
                    "VALUES (?, ?, 'project-state-restore', 'applied', ?, ?)",
                    (operation_id, result.project_uuid, now, now),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _existing_backup_result(
        self,
        path: Path,
        *,
        expected_source_revision: str | None = None,
    ) -> PhysicalBackupResult:
        content = path.read_bytes()
        try:
            decoded = self.codec.decode_physical_backup(content)
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite physical backup is invalid",
                diagnostic=str(exc),
            ) from exc
        archive = ProjectArchive(
            kind="physical_backup",
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
            semantic_state_digest=decoded.semantic_state_digest,
        )
        self.verify_backup(archive)
        source_revision = str(decoded.manifest["source_revision"])
        if (
            expected_source_revision is not None
            and source_revision != expected_source_revision
        ):
            raise ProjectStorageError(
                ProjectStorageErrorCode.stale_revision,
                "existing SQLite pre-operation backup belongs to another revision",
            )
        return PhysicalBackupResult(
            status="created",
            output=str(path.resolve()),
            project_uuid=decoded.project_uuid,
            source_revision=source_revision,
            archive_sha256=archive.sha256,
            archive_size=len(content),
            file_count=len(decoded.files),
            coordinated=True,
        )

    def _backup_content(self) -> tuple[bytes, CanonicalMemorySnapshot]:
        """Encode metadata and blobs from the exact online-backup revision."""
        self._inject("before_online_backup")
        with tempfile.TemporaryDirectory(prefix="p2p-sqlite-backup-") as raw:
            backup_db = Path(raw) / "project.sqlite3"
            with self.repository.connections.connect(writable=False) as source:
                destination = sqlite3.connect(backup_db)
                try:
                    source.backup(destination)
                    destination.execute(
                        "UPDATE storage_metadata SET maintenance_state = 'ready' "
                        "WHERE singleton = 1"
                    )
                    destination.commit()
                finally:
                    destination.close()
            self._inject("after_online_backup")
            staged = SQLiteProjectStateRepository(
                self.repository.root,
                database_path=backup_db,
            )
            snapshot = staged.snapshot()
            files = {SQLITE_DATABASE_PATH: backup_db.read_bytes()}
            manifest = self.repository.root / PROJECT_STORAGE_MANIFEST_PATH
            manifest_content = _read_confined_project_file(
                self.repository.root,
                manifest,
                operation="physical backup manifest",
            )
            expected_manifest = ProjectStorageManifestStore.render(
                ProjectStorageManifest(
                    project_uuid=snapshot.project_uuid,
                    adapter=SQLITE_ADAPTER,
                    schema_version=SQLITE_SCHEMA_VERSION,
                )
            )
            if manifest_content != expected_manifest:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.stale_revision,
                    "SQLite storage identity changed during online backup",
                )
            files[PROJECT_STORAGE_MANIFEST_PATH] = manifest_content
            for blob in snapshot.blobs:
                path = sqlite_blob_path(self.repository.root, blob.digest)
                relative = path.relative_to(self.repository.root).as_posix()
                files[relative] = read_sqlite_blob_bytes(
                    self.repository.root,
                    blob.digest,
                )
            content = self.codec.encode_physical_backup(
                store=SQLiteCanonicalStore(staged),
                files=dict(sorted(files.items())),
                directories=(".p2p/local", ".p2p/blobs", ".p2p/blobs/sha256"),
                semantic_state_digest=snapshot.semantic_state_digest,
                source_revision=snapshot.semantic_state_digest,
            )
        return content, snapshot

    def _restore_target(self, source: Path) -> tuple[str, str, str, int]:
        try:
            decoded = self.codec.decode_bundle(source)
        except ValueError:
            physical = self.codec.decode_physical_backup(source)
            _verify_sqlite_backup(self.repository.root, physical.files, physical.manifest)
            with _temporary_sqlite_repository(physical.files[SQLITE_DATABASE_PATH]) as staged:
                snapshot = staged.snapshot()
            return (
                snapshot.project_uuid,
                snapshot.semantic_state_digest,
                physical.archive_sha256,
                len(snapshot.entities),
            )
        return (
            decoded.snapshot.project_uuid,
            decoded.snapshot.semantic_state_digest,
            decoded.archive_sha256,
            len(decoded.snapshot.entities),
        )

    def _prepare_restore_database(self, source: Path, stage_db: Path) -> dict[str, bytes]:
        try:
            decoded = self.codec.decode_bundle(source)
        except ValueError:
            physical = self.codec.decode_physical_backup(source)
            _verify_sqlite_backup(self.repository.root, physical.files, physical.manifest)
            stage_db.write_bytes(physical.files[SQLITE_DATABASE_PATH])
            if os.name != "nt":
                stage_db.chmod(0o600)
            return {
                path_to_digest(path): content
                for path, content in physical.files.items()
                if path.startswith(".p2p/blobs/sha256/")
            }
        identity = self.repository.identity()
        create_sqlite_database(
            stage_db,
            identity=identity,
            snapshot=decoded.snapshot,
            public_receipts=self.repository.public_mutation_records(),
        )
        return dict(decoded.blob_bytes)

    def _inject(self, stage: str) -> None:
        if self.failure_injector is not None:
            self.failure_injector(stage)


class SQLiteMigrationPort:
    """Backup-protected migration and recovery for the versioned SQLite schema."""

    def __init__(self, repository: SQLiteProjectStateRepository) -> None:
        self.repository = repository

    def schema_version(self) -> int:
        with self.repository.connections.connect(writable=False) as connection:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])

    def can_migrate_from(self, schema_version: int) -> bool:
        return schema_version in {0, SQLITE_SCHEMA_VERSION}

    def verify_current(self) -> None:
        version = self.schema_version()
        if version > SQLITE_SCHEMA_VERSION:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "SQLite project schema is newer than this runtime",
            )
        if version != SQLITE_SCHEMA_VERSION:
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite project schema requires a backup-protected migration",
            )
        issues = self.repository.integrity_check()
        if issues:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite schema verification failed",
                diagnostic="; ".join(issues),
            )

    def migrate_to_current(
        self,
        *,
        backup_path: Path,
        actor: str = "owner",
        failure_injector=None,
    ) -> str:
        """Migrate under a durable writer fence and a recoverable v2 marker.

        ``actor`` defaults to the legacy local owner name for compatibility,
        but is always resolved against canonical project permissions.
        """
        transaction_id = f"sqlite-migration-{uuid4().hex}"
        lock = WorkspaceTransactionLockService(
            root=self.repository.root,
            p2p_dir=self.repository.root / ".p2p",
        )
        try:
            lock.acquire(transaction_id, owner=actor)
        except ValueError as exc:
            code = (
                ProjectStorageErrorCode.recovery_required
                if (
                    (self.repository.root / SQLITE_MAINTENANCE_MARKER).exists()
                    or _is_link_or_reparse_point(
                        self.repository.root / SQLITE_MAINTENANCE_MARKER
                    )
                )
                else ProjectStorageErrorCode.busy
            )
            raise ProjectStorageError(
                code,
                "SQLite migration could not acquire the project transaction lock",
                diagnostic=str(exc),
            ) from exc
        try:
            return self._migrate_to_current_locked(
                backup_path=backup_path,
                actor=actor,
                transaction_id=transaction_id,
                failure_injector=failure_injector,
            )
        finally:
            if lock.status().transaction_id == transaction_id:
                lock.release(transaction_id)

    def _migrate_to_current_locked(
        self,
        *,
        backup_path: Path,
        actor: str,
        transaction_id: str,
        failure_injector=None,
    ) -> str:
        marker = self.repository.root / SQLITE_MAINTENANCE_MARKER
        if marker.exists() or _is_link_or_reparse_point(marker):
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "an interrupted SQLite migration requires explicit rollback",
            )
        version = self.schema_version()
        state = self._maintenance_state()
        if version > SQLITE_SCHEMA_VERSION:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "SQLite project schema is newer than this runtime",
            )
        if version == SQLITE_SCHEMA_VERSION:
            if state != "ready":
                raise ProjectStorageError(
                    ProjectStorageErrorCode.recovery_required,
                    "SQLite project is fenced by an interrupted maintenance operation",
                )
            self.verify_current()
            return "current"
        if version != 0:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "SQLite project schema has no ordered migration path",
            )
        if state != "ready":
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite project is fenced by an interrupted maintenance operation",
            )
        _require_sqlite_owner(
            self.repository,
            actor,
            operation="sqlite_schema_migration",
        )
        source = self.repository.snapshot()
        local = self.repository.root / ".p2p/local"
        backups_root = self.repository.root / ".p2p/backups"
        _assert_safe_path_components(self.repository.root, local)
        _assert_safe_path_components(self.repository.root, backups_root)
        local.mkdir(parents=True, exist_ok=True)
        backups_root.mkdir(parents=True, exist_ok=True)
        _assert_safe_path_components(self.repository.root, local)
        _assert_safe_path_components(self.repository.root, backups_root)
        recovery_id, recovery_token = new_sqlite_recovery_identity()
        stage_dir = local / f"sqlite-migration-{recovery_id}.stage"
        stage_db = stage_dir / "source.sqlite3"
        recovery_db = backups_root / f"sqlite-migration-{recovery_id}.sqlite3"
        marker_payload: dict[str, object] = {
            "contract": "p2p-sqlite-maintenance/v2",
            "recovery_id": recovery_id,
            "recovery_token": recovery_token,
            "operation": "schema-migration",
            "phase": "prepared",
            "actor": actor,
            "transaction_id": transaction_id,
            "source": {
                "project_uuid": source.project_uuid,
                "semantic_state_digest": source.semantic_state_digest,
            },
            "target": {
                "project_uuid": source.project_uuid,
                "semantic_state_digest": source.semantic_state_digest,
            },
            "source_schema_version": version,
            "target_schema_version": SQLITE_SCHEMA_VERSION,
            "stage": stage_dir.relative_to(self.repository.root).as_posix(),
            "recovery": recovery_db.relative_to(self.repository.root).as_posix(),
            "blob_changes": [],
        }
        _write_marker(marker, marker_payload)
        try:
            self._inject(failure_injector, "after_migration_marker")
            _fence_database(
                self.repository,
                expected_revision=source.semantic_state_digest,
                state="migrating",
            )
            _update_marker(marker, marker_payload, phase="fenced")
            self._inject(failure_injector, "after_migration_fence")
            stage_dir.mkdir(parents=True, exist_ok=False)
            self._create_recovery_database(
                stage_db,
                expected_project_uuid=source.project_uuid,
                expected_revision=source.semantic_state_digest,
                expected_schema_version=version,
            )
            _replace_and_sync_directories(stage_db, recovery_db)
            _update_marker(marker, marker_payload, phase="recovery_created")
            self._inject(failure_injector, "after_migration_recovery")
            backups = SQLiteBackupPort(self.repository)
            if backup_path.exists():
                backups._existing_backup_result(
                    backup_path,
                    expected_source_revision=source.semantic_state_digest,
                )
                self._verify_migration_backup_schema(backup_path, version)
            else:
                backups._backup_to(
                    backup_path,
                    coordinated=True,
                    allow_internal=True,
                )
            _update_marker(marker, marker_payload, phase="backup_created")
            self._inject(failure_injector, "after_migration_backup")
            with self.repository.connections.connect(writable=True) as connection:
                connection.execute("BEGIN IMMEDIATE")
                if int(connection.execute("PRAGMA user_version").fetchone()[0]) != version:
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.stale_revision,
                        "SQLite schema changed before migration could start",
                    )
                connection.execute(
                    "INSERT INTO schema_migrations(version, contract, ddl_sha256, applied_at) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        SQLITE_SCHEMA_VERSION,
                        SQLITE_SCHEMA_CONTRACT,
                        SQLITE_SCHEMA_V1_SHA256,
                        _utc_now(),
                    ),
                )
                connection.execute(f"PRAGMA user_version = {SQLITE_SCHEMA_VERSION}")
                self._inject(failure_injector, "before_migration_commit")
                connection.execute("COMMIT")
            _update_marker(marker, marker_payload, phase="committed")
            self._inject(failure_injector, "after_migration_commit")
            issues = self.repository.integrity_check()
            migrated = self.repository.snapshot()
            if (
                issues
                or self.schema_version() != SQLITE_SCHEMA_VERSION
                or migrated.project_uuid != source.project_uuid
                or migrated.semantic_state_digest != source.semantic_state_digest
            ):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "migrated SQLite schema failed integrity verification",
                    diagnostic="; ".join(issues),
                )
            _update_marker(marker, marker_payload, phase="verified")
            self._inject(failure_injector, "after_migration_verification")
            self._inject(failure_injector, "before_migration_finalize")
            self._set_maintenance_state("ready")
            _unlink_and_sync_directory(marker)
            # Marker removal is the commit point. Cleanup is idempotent and
            # never makes a completed migration look interrupted again. A
            # platform-specific cleanup failure must not report the already
            # committed migration as failed.
            try:
                _unlink_and_sync_directory(recovery_db)
                _remove_tree_and_sync_parent(stage_dir)
            except OSError:
                pass
            return "migrated"
        except Exception:
            # The explicit public coordinator owns rollback after publication
            # of the durable marker, including ordinary injected failures.
            raise

    def _create_recovery_database(
        self,
        output: Path,
        *,
        expected_project_uuid: str,
        expected_revision: str,
        expected_schema_version: int,
    ) -> None:
        with self.repository.connections.connect(writable=False) as source:
            destination = sqlite3.connect(output)
            try:
                source.backup(destination)
                destination.execute(
                    "UPDATE storage_metadata SET maintenance_state = 'ready' "
                    "WHERE singleton = 1"
                )
                destination.commit()
            finally:
                destination.close()
        if os.name != "nt":
            output.chmod(0o600)
        descriptor = os.open(output, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        staged = SQLiteProjectStateRepository(
            self.repository.root,
            database_path=output,
        )
        staged_snapshot = staged.snapshot()
        with staged.connections.connect(writable=False) as connection:
            staged_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        issues = staged.integrity_check()
        if (
            issues
            or staged_version != expected_schema_version
            or staged_snapshot.project_uuid != expected_project_uuid
            or staged_snapshot.semantic_state_digest != expected_revision
        ):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite migration recovery database failed verification",
                diagnostic="; ".join(issues),
            )

    def _verify_migration_backup_schema(
        self,
        backup_path: Path,
        expected_schema_version: int,
    ) -> None:
        try:
            decoded = CanonicalBundleCodec().decode_physical_backup(backup_path)
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite migration backup is invalid",
                diagnostic=str(exc),
            ) from exc
        with _temporary_sqlite_repository(
            decoded.files[SQLITE_DATABASE_PATH]
        ) as repository:
            with repository.connections.connect(writable=False) as connection:
                schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if schema_version != expected_schema_version:
            raise ProjectStorageError(
                ProjectStorageErrorCode.stale_revision,
                "existing SQLite migration backup has the wrong source schema version",
            )

    def _maintenance_state(self) -> str:
        with self.repository.connections.connect(writable=False) as connection:
            row = connection.execute(
                "SELECT maintenance_state FROM storage_metadata WHERE singleton = 1"
            ).fetchone()
        if row is None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite maintenance state is missing",
            )
        return str(row["maintenance_state"])

    def _set_maintenance_state(self, state: str) -> None:
        _set_database_maintenance_state(self.repository, state)

    @staticmethod
    def _inject(failure_injector, stage: str) -> None:
        if failure_injector is not None:
            failure_injector(stage)


class SQLiteCompatibilityWorkspace:
    """Run legacy domain services against an ephemeral filesystem projection.

    The projection exists only for the duration of one call. Canonical changes
    are committed through the SQLite unit of work and the projection is then
    destroyed, so this compatibility layer is not a second authoritative store.
    """

    def __init__(self, adapter: SQLiteProjectStateAdapter) -> None:
        self.adapter = adapter
        self.root = adapter.root
        self.p2p_dir = self.root / ".p2p"

    def project_identity(self):
        return self.adapter.repository.identity()

    def canonical_memory_snapshot(self):
        return self.adapter.repository.snapshot()

    def canonical_bundle_metadata(self):
        return self.adapter.snapshots.bundle_metadata()

    def canonical_bundle_export(self, output: Path):
        return self.adapter.snapshots.export_bundle_to(output)

    def canonical_archive_verify(self, source: Path):
        return self.adapter.snapshots.verify_archive(source)

    def canonical_memory_backup(self, output: Path, *, coordinated: bool = True):
        return self.adapter.backups.backup_to(output, coordinated=coordinated)

    def _root_transaction_recovery(self) -> WorkspaceTransactionRecoveryService:
        return WorkspaceTransactionRecoveryService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )

    def workspace_transaction_recovery_status(self):
        return self._root_transaction_recovery().status()

    def rollback_workspace_transaction(
        self,
        *,
        transaction_id: str,
        actor: str,
        confirm: bool,
    ):
        service = self._root_transaction_recovery()
        effective_actor = self._authorized_recovery_actor(
            service,
            transaction_id=transaction_id,
            actor=actor,
        )
        if effective_actor is None:
            return WorkspaceTransactionRecoveryResult(
                status="blocked",
                transaction_id=transaction_id,
                message=f"Actor {actor} is not authorized to recover workspace transactions.",
                recovery_required=True,
            )
        return service.rollback(
            transaction_id=transaction_id,
            actor=effective_actor,
            confirm=confirm,
        )

    def resume_workspace_transaction(
        self,
        *,
        transaction_id: str,
        actor: str,
        confirm: bool,
    ):
        service = self._root_transaction_recovery()
        effective_actor = self._authorized_recovery_actor(
            service,
            transaction_id=transaction_id,
            actor=actor,
        )
        if effective_actor is None:
            return WorkspaceTransactionRecoveryResult(
                status="blocked",
                transaction_id=transaction_id,
                message=f"Actor {actor} is not authorized to recover workspace transactions.",
                recovery_required=True,
            )
        return service.resume(
            transaction_id=transaction_id,
            actor=effective_actor,
            confirm=confirm,
        )

    def _authorized_recovery_actor(
        self,
        service: WorkspaceTransactionRecoveryService,
        *,
        transaction_id: str,
        actor: str,
    ) -> str | None:
        permissions = next(
            (
                item.payload.get("document")
                for item in self.adapter.repository.snapshot().entities
                if item.technical_id == "project:permissions"
            ),
            None,
        )
        if not isinstance(permissions, Mapping):
            return None
        try:
            resolved = PermissionsService(
                root=self.root,
                p2p_dir=self.p2p_dir,
            ).resolve_actor_payload(actor, permissions)
        except ValueError:
            return None
        if resolved.role != "owner":
            return None
        status = service.status()
        if (
            transaction_id.startswith("sqlite-compat-")
            and status.lock.transaction_id == transaction_id
            and status.lock.owner
        ):
            # Compatibility locks contain no mutation journal. The generic
            # recovery service falls back to lock ownership when the canonical
            # permissions file lives only in SQLite, so use its stored owner
            # after independently authorizing the caller against DB state.
            return status.lock.owner
        return actor

    def __getattr__(self, name: str):
        def invoke(*args: object, **kwargs: object):
            return self._invoke(name, *args, **kwargs)

        return invoke

    def _invoke(
        self,
        method_name: str,
        *args: object,
        _race_retry: bool = False,
        _replica_lock_id: str = "",
        **kwargs: object,
    ):
        if not _replica_lock_id:
            lock = WorkspaceTransactionLockService(
                root=self.root,
                p2p_dir=self.p2p_dir,
            )
            transaction_id = f"sqlite-compat-{uuid4().hex}"
            deadline = time.monotonic() + (
                self.adapter.repository.connections.busy_timeout_ms / 1000
            )
            while True:
                try:
                    lock.acquire(
                        transaction_id,
                        owner=_sqlite_replica_lock_owner(
                            self.adapter.repository,
                            kwargs,
                        ),
                    )
                    break
                except ValueError as exc:
                    if (
                        (self.root / SQLITE_MAINTENANCE_MARKER).exists()
                        or _is_link_or_reparse_point(
                            self.root / SQLITE_MAINTENANCE_MARKER
                        )
                    ):
                        raise ProjectStorageError(
                            ProjectStorageErrorCode.recovery_required,
                            "SQLite project is fenced by a maintenance operation",
                            diagnostic=str(exc),
                        ) from exc
                    if time.monotonic() >= deadline:
                        raise ProjectStorageError(
                            ProjectStorageErrorCode.busy,
                            "SQLite project writer did not acquire the replica-local lock "
                            "within its timeout",
                            diagnostic=str(exc),
                        ) from exc
                    time.sleep(0.01)
            try:
                return self._invoke(
                    method_name,
                    *args,
                    _race_retry=_race_retry,
                    _replica_lock_id=transaction_id,
                    **kwargs,
                )
            finally:
                if lock.status().transaction_id == transaction_id:
                    lock.release(transaction_id)
        before = self.adapter.repository.snapshot()
        with tempfile.TemporaryDirectory(prefix="p2p-sqlite-compat-") as raw:
            staged_root = Path(raw)
            staged_store = self._materialize(staged_root, before)
            receipts_before = _receipt_documents(staged_root)
            if method_name == "init_project_with_operation_key" and str(
                kwargs.get("storage_adapter") or ""
            ).strip().lower() == SQLITE_ADAPTER:
                write_bytes_atomic(
                    staged_root / PROJECT_STORAGE_MANIFEST_PATH,
                    ProjectStorageManifestStore.render(
                        ProjectStorageManifest(
                            project_uuid=before.project_uuid,
                            adapter=SQLITE_ADAPTER,
                        )
                    ),
                )
            from p2p_engine.storage.filesystem import FilesystemWorkspace

            workspace = FilesystemWorkspace(staged_root)
            target = getattr(workspace, method_name)
            result = target(*args, **kwargs)
            codec = CanonicalBundleCodec()
            projected_after = codec.snapshot(staged_store)
            new_public_mutations = _normalize_new_public_receipts(
                staged_root=staged_root,
                store=staged_store,
                before_documents=receipts_before,
                snapshot=projected_after,
            )
            after = codec.snapshot(staged_store)
            if after.semantic_state_digest != projected_after.semantic_state_digest:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "receipt normalization changed canonical project semantics",
                )
            identity_changed = after.project_uuid != before.project_uuid
            if (
                after.semantic_state_digest != before.semantic_state_digest
                or new_public_mutations
            ):
                if identity_changed:
                    public_mutations = {
                        item.receipt.key_sha256: item
                        for item in self.adapter.repository.public_mutation_records()
                    }
                    public_mutations.update(
                        {
                            item.receipt.key_sha256: item
                            for item in new_public_mutations
                        }
                    )
                    try:
                        self._activate_identity_transition(
                            name=method_name,
                            arguments=kwargs,
                            transaction_id=_replica_lock_id,
                            before=before,
                            after=after,
                            staged_store=staged_store,
                            staged_root=staged_root,
                            public_receipts=tuple(public_mutations.values()),
                        )
                    except ProjectStorageError as exc:
                        if (
                            not new_public_mutations
                            or exc.code != ProjectStorageErrorCode.stale_revision
                            or _race_retry
                        ):
                            raise
                        return self._invoke(
                            method_name,
                            *args,
                            _race_retry=True,
                            _replica_lock_id=_replica_lock_id,
                            **kwargs,
                        )
                else:
                    blob_payloads = {
                        blob.digest: staged_store.read_blob_bytes(blob)
                        for blob in after.blobs
                    }
                    public_record = (
                        new_public_mutations[0] if new_public_mutations else None
                    )
                    public_receipt = (
                        public_record.receipt if public_record is not None else None
                    )
                    operation_id = (
                        sqlite_public_receipt_operation_id(public_receipt.key_sha256)
                        if public_receipt is not None
                        else f"sqlite-compat-{method_name}-{uuid4().hex}"
                    )
                    try:
                        with self.adapter.unit_of_work() as unit:
                            unit.stage(
                                ProjectStateMutation(
                                    operation_id=operation_id,
                                    actor=(
                                        public_receipt.actor
                                        if public_receipt is not None
                                        else _compatibility_actor(kwargs)
                                    ),
                                    expected_revision=ProjectStateRevision(
                                        before.semantic_state_digest
                                    ),
                                    target=after,
                                    blob_payloads=blob_payloads,
                                    receipt_id=(
                                        public_receipt.key_sha256
                                        if public_receipt is not None
                                        else ""
                                    ),
                                )
                            )
                            if public_receipt is not None:
                                assert public_record is not None
                                unit.stage_public_receipt(
                                    public_receipt,
                                    durable_documents=public_record.document_map(),
                                )
                            committed = unit.commit()
                    except ProjectStorageError as exc:
                        if (
                            public_receipt is None
                            or exc.code != ProjectStorageErrorCode.stale_revision
                            or _race_retry
                        ):
                            raise
                        # A competing writer may have committed this exact
                        # public operation after the compatibility projection
                        # was created but before Unit-of-Work staging. Rebuild
                        # once from SQLite so the durable receipt decides
                        # whether this is a replay or a key conflict.
                        return self._invoke(
                            method_name,
                            *args,
                            _race_retry=True,
                            _replica_lock_id=_replica_lock_id,
                            **kwargs,
                        )
                    if committed.replayed:
                        if _race_retry:
                            raise ProjectStorageError(
                                ProjectStorageErrorCode.internal,
                                "public receipt replay did not converge after a writer race",
                            )
                        return self._invoke(
                            method_name,
                            *args,
                            _race_retry=True,
                            _replica_lock_id=_replica_lock_id,
                            **kwargs,
                        )
            if not identity_changed:
                self._synchronize_auxiliary_state(staged_root)
            return result

    def _activate_identity_transition(
        self,
        *,
        name: str,
        arguments: Mapping[str, object],
        transaction_id: str,
        before,
        after,
        staged_store: FilesystemCanonicalMemoryStore,
        staged_root: Path,
        public_receipts: tuple[SQLitePublicMutationRecord, ...],
    ) -> None:
        """Atomically replace the one-project DB when identity is governed anew."""
        operation_key = str(arguments.get("operation_key") or uuid4().hex)
        operation_hash = operation_key_sha(operation_key)
        local = self.root / ".p2p/local"
        backup_dir = self.root / ".p2p/backups"
        _assert_confined_workspace_path(
            self.root,
            local,
            expected="directory",
            must_exist=True,
            operation="identity transition",
        )
        _assert_confined_workspace_path(
            self.root,
            backup_dir,
            expected="directory",
            must_exist=False,
            operation="identity transition",
        )
        local.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)
        _assert_confined_workspace_path(
            self.root,
            local,
            expected="directory",
            must_exist=True,
            operation="identity transition",
        )
        _assert_confined_workspace_path(
            self.root,
            backup_dir,
            expected="directory",
            must_exist=True,
            operation="identity transition",
        )
        recovery_id, recovery_token = new_sqlite_recovery_identity()
        stage_dir = local / f"sqlite-identity-{recovery_id}.stage"
        stage_db = stage_dir / "project.sqlite3"
        source_revision_key = before.semantic_state_digest[:24]
        recovery_db = backup_dir / f"sqlite-pre-identity-{recovery_id}.sqlite3"
        backup_path = backup_dir / (
            f"sqlite-pre-identity-{operation_hash}-{source_revision_key}.p2pbackup"
        )
        marker = self.root / SQLITE_MAINTENANCE_MARKER
        manifest_store = ProjectStorageManifestStore(self.root)
        previous_manifest = _read_confined_project_file(
            self.root,
            manifest_store.path,
            operation="identity transition manifest",
        )
        previous_auxiliary = self._auxiliary_snapshot(self.root)
        target_auxiliary = self._auxiliary_snapshot(staged_root)
        auxiliary_backup_relative = Path(".p2p/backups") / (
            f"sqlite-pre-identity-{recovery_id}.aux"
        )
        auxiliary_backup = self.root / auxiliary_backup_relative
        for candidate in (recovery_db, backup_path):
            _assert_confined_workspace_path(
                self.root,
                candidate,
                expected="file",
                must_exist=False,
                operation="identity transition",
            )
        if recovery_db.exists() or _is_link_or_reparse_point(recovery_db):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite identity recovery path already exists",
            )
        _assert_confined_workspace_path(
            self.root,
            stage_dir,
            expected="directory",
            must_exist=False,
            operation="identity transition",
        )
        marker_payload: dict[str, object] = {
            "contract": "p2p-sqlite-maintenance/v2",
            "recovery_id": recovery_id,
            "recovery_token": recovery_token,
            "operation": "identity-transition",
            "phase": "prepared",
            "actor": _compatibility_actor(arguments),
            "transaction_id": transaction_id,
            "domain_operation": name,
            "operation_key": operation_key,
            "source": {
                "project_uuid": before.project_uuid,
                "semantic_state_digest": before.semantic_state_digest,
            },
            "target": {
                "project_uuid": after.project_uuid,
                "semantic_state_digest": after.semantic_state_digest,
            },
            "stage": _portable_project_locator(self.root, stage_dir),
            "recovery": _portable_project_locator(self.root, recovery_db),
            "backup": _portable_project_locator(self.root, backup_path),
            "auxiliary_backup": _portable_project_locator(
                self.root,
                auxiliary_backup,
            ),
            "auxiliary_remove": [
                {
                    "path": relative.as_posix(),
                    "sha256": hashlib.sha256(
                        (staged_root / relative).read_bytes()
                    ).hexdigest(),
                    "size": (staged_root / relative).stat().st_size,
                }
                for relative in sorted(
                    target_auxiliary.keys() - previous_auxiliary.keys()
                )
            ],
            "auxiliary_source": [
                {
                    "path": relative.as_posix(),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size": len(content),
                }
                for relative, content in sorted(previous_auxiliary.items())
            ],
            "auxiliary_target": [
                {
                    "path": relative.as_posix(),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size": len(content),
                }
                for relative, content in sorted(target_auxiliary.items())
            ],
            "blob_changes": [
                {
                    "path": sqlite_blob_path(self.root, blob.digest)
                    .relative_to(self.root)
                    .as_posix(),
                    "digest": blob.digest,
                    "existed_before": sqlite_blob_path(
                        self.root,
                        blob.digest,
                    ).exists(),
                }
                for blob in sorted(after.blobs, key=lambda item: item.digest)
            ],
        }
        owns_marker = False
        owns_fence = False
        safe_to_clear_marker = False
        try:
            _write_marker(marker, marker_payload)
            owns_marker = True
            write_sqlite_auxiliary_backup(
                self.root,
                auxiliary_backup_relative,
                previous_auxiliary,
            )
            _update_marker(marker, marker_payload, phase="auxiliary_backed")
            stage_dir.mkdir(parents=True, exist_ok=False)
            _assert_confined_workspace_path(
                self.root,
                stage_dir,
                expected="directory",
                must_exist=True,
                operation="identity transition",
            )
            _assert_confined_workspace_path(
                self.root,
                stage_db,
                expected="file",
                must_exist=False,
                operation="identity transition",
            )
            identity = staged_store.project_identity()
            create_sqlite_database(
                stage_db,
                identity=identity,
                snapshot=after,
                public_receipts=public_receipts,
            )
            staged = SQLiteProjectStateRepository(self.root, database_path=stage_db)
            issues = staged.integrity_check(verify_blobs=False)
            if issues or staged.snapshot().semantic_state_digest != after.semantic_state_digest:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "staged SQLite identity transition failed verification",
                    diagnostic="; ".join(issues),
            )
            _update_marker(marker, marker_payload, phase="staged")
            self._inject_identity_failure("after_identity_stage")
            try:
                _fence_database(
                    self.adapter.repository,
                    expected_revision=before.semantic_state_digest,
                    state="restoring",
                )
            except _CommittedMaintenanceFenceError:
                owns_fence = True
                raise
            owns_fence = True
            _update_marker(marker, marker_payload, phase="fenced")
            self._inject_identity_failure("after_identity_fence")
            backups = SQLiteBackupPort(self.adapter.repository)
            _assert_confined_workspace_path(
                self.root,
                backup_path,
                expected="file",
                must_exist=False,
                operation="identity transition",
            )
            if backup_path.exists():
                backups._existing_backup_result(
                    backup_path,
                    expected_source_revision=before.semantic_state_digest,
                )
            else:
                backups._backup_to(
                    backup_path,
                    coordinated=True,
                    allow_internal=True,
                )
            _update_marker(marker, marker_payload, phase="backup_created")
            self._inject_identity_failure("after_identity_backup")
            _checkpoint(self.adapter.repository)
            _assert_confined_workspace_path(
                self.root,
                recovery_db,
                expected="file",
                must_exist=False,
                operation="identity transition",
            )
            if recovery_db.exists() or _is_link_or_reparse_point(recovery_db):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite identity recovery path changed before activation",
                )
            _replace_and_sync_directories(
                self.adapter.repository.database_path,
                recovery_db,
            )
            _assert_confined_workspace_path(
                self.root,
                recovery_db,
                expected="file",
                must_exist=True,
                operation="identity transition",
            )
            _update_marker(marker, marker_payload, phase="old_moved")
            self._inject_identity_failure("after_identity_old_database_move")
            _assert_confined_workspace_path(
                self.root,
                stage_db,
                expected="file",
                must_exist=True,
                operation="identity transition",
            )
            _replace_and_sync_directories(
                stage_db,
                self.adapter.repository.database_path,
            )
            _update_marker(marker, marker_payload, phase="activated")
            self._inject_identity_failure("after_identity_activation")
            write_bytes_atomic(
                manifest_store.path,
                ProjectStorageManifestStore.render(
                    ProjectStorageManifest(
                        project_uuid=after.project_uuid,
                        adapter=SQLITE_ADAPTER,
                        schema_version=SQLITE_SCHEMA_VERSION,
                    )
                ),
            )
            _update_marker(marker, marker_payload, phase="manifest_updated")
            self._inject_identity_failure("after_identity_manifest")
            _install_blob_payloads(
                self.root,
                {
                    blob.digest: staged_store.read_blob_bytes(blob)
                    for blob in after.blobs
                },
            )
            active = SQLiteProjectStateRepository(self.root)
            active_issues = active.integrity_check()
            if (
                active_issues
                or active.identity().project_uuid.value != after.project_uuid
                or active.snapshot().semantic_state_digest != after.semantic_state_digest
            ):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "activated SQLite identity transition failed verification",
                    diagnostic="; ".join(active_issues),
                )
            self._synchronize_auxiliary_state(staged_root)
            _update_marker(marker, marker_payload, phase="auxiliary_applied")
            self._inject_identity_failure("after_identity_auxiliary")
            safe_to_clear_marker = True
        except Exception as original:
            try:
                if owns_fence:
                    _assert_confined_workspace_path(
                        self.root,
                        recovery_db,
                        expected="file",
                        must_exist=False,
                        operation="identity rollback",
                    )
                    if recovery_db.is_file():
                        _verify_recovered_database(
                            self.root,
                            database_path=recovery_db,
                            project_uuid=before.project_uuid,
                            semantic_state_digest=before.semantic_state_digest,
                        )
                        _unlink_and_sync_directory(
                            self.adapter.repository.database_path
                        )
                        _replace_and_sync_directories(
                            recovery_db,
                            self.adapter.repository.database_path,
                        )
                    write_bytes_atomic(manifest_store.path, previous_manifest)
                    self._restore_auxiliary_snapshot(previous_auxiliary)
                    if self.adapter.repository.database_path.is_file():
                        _set_database_maintenance_state(self.adapter.repository, "ready")
                    _verify_recovered_database(
                        self.root,
                        project_uuid=before.project_uuid,
                        semantic_state_digest=before.semantic_state_digest,
                    )
                    if (
                        _read_confined_project_file(
                            self.root,
                            manifest_store.path,
                            operation="identity rollback manifest",
                        )
                        != previous_manifest
                    ):
                        raise ProjectStorageError(
                            ProjectStorageErrorCode.recovery_required,
                            "SQLite identity rollback did not restore its manifest",
                        )
                    if self._auxiliary_snapshot(self.root) != previous_auxiliary:
                        raise ProjectStorageError(
                            ProjectStorageErrorCode.recovery_required,
                            "SQLite identity rollback did not restore auxiliary state",
                        )
                    _rollback_blob_changes(
                        self.root,
                        marker_payload.get("blob_changes"),
                    )
                safe_to_clear_marker = True
            except Exception as rollback_error:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.recovery_required,
                    "SQLite identity rollback did not complete; explicit recovery is required",
                    diagnostic=(
                        f"forward failure: {original}; rollback failure: {rollback_error}"
                    ),
                ) from rollback_error
            raise
        finally:
            if not owns_marker or safe_to_clear_marker:
                if stage_dir.exists() or _is_link_or_reparse_point(stage_dir):
                    _assert_confined_workspace_path(
                        self.root,
                        stage_dir,
                        expected="directory",
                        must_exist=True,
                        operation="identity cleanup",
                    )
                    _remove_tree_and_sync_parent(stage_dir)
            if owns_marker and safe_to_clear_marker:
                _unlink_and_sync_directory(marker)
            if safe_to_clear_marker:
                if auxiliary_backup.exists() or _is_link_or_reparse_point(
                    auxiliary_backup
                ):
                    _assert_confined_workspace_path(
                        self.root,
                        auxiliary_backup,
                        expected="directory",
                        must_exist=True,
                        operation="identity cleanup",
                    )
                    _remove_tree_and_sync_parent(auxiliary_backup)

    def _inject_identity_failure(self, stage: str) -> None:
        if self.adapter.repository.failure_injector is not None:
            self.adapter.repository.failure_injector(stage)

    @classmethod
    def _auxiliary_snapshot(cls, root: Path) -> dict[Path, bytes]:
        return {
            relative: (root / relative).read_bytes()
            for relative in cls._recovery_auxiliary_paths(root)
        }

    def _restore_auxiliary_snapshot(self, snapshot: Mapping[Path, bytes]) -> None:
        for directory in (Path(".agents"), Path(".cursor")):
            target = self.root / directory
            if target.exists() or _is_link_or_reparse_point(target):
                _assert_safe_directory_tree(self.root, target)
                _remove_tree_and_sync_parent(target)
        for relative in self._recovery_auxiliary_paths(self.root):
            target = self.root / relative
            _assert_safe_regular_file(self.root, target)
            _unlink_and_sync_directory(target)
        for relative, content in snapshot.items():
            target = self.root / relative
            _assert_safe_path_components(self.root, target.parent)
            write_bytes_atomic(target, content)

    @classmethod
    def _recovery_auxiliary_paths(cls, root: Path) -> set[Path]:
        paths = cls._auxiliary_paths(root)
        for relative in (
            Path("AGENTS.md"),
            Path("CLAUDE.md"),
            Path("GEMINI.md"),
            Path("P2P-SETUP.md"),
            Path(".github/copilot-instructions.md"),
        ):
            path = root / relative
            if path.exists() or _is_link_or_reparse_point(path):
                _assert_safe_regular_file(root, path)
                paths.add(relative)
        for directory in (Path(".agents"), Path(".cursor")):
            base = root / directory
            if not base.exists() and not _is_link_or_reparse_point(base):
                continue
            _assert_safe_directory_tree(root, base)
            paths.update(
                path.relative_to(root)
                for path in base.rglob("*")
                if path.is_file()
            )
        return paths

    def _materialize(
        self,
        staged_root: Path,
        snapshot,
    ) -> FilesystemCanonicalMemoryStore:
        store = FilesystemCanonicalMemoryStore(staged_root)
        documents = store.activation_documents(snapshot.entities)
        blob_payloads = {
            blob.digest: self.adapter.blobs.read(blob.digest)
            for blob in snapshot.blobs
        }
        documents.update(store.blob_documents(snapshot.blobs, blob_payloads))
        for relative, content in documents.items():
            write_bytes_atomic(staged_root / relative, content)
        for relative in (".p2p/prompts", ".p2p/proposals"):
            (staged_root / relative).mkdir(parents=True, exist_ok=True)
        self._copy_auxiliary_state(self.root, staged_root)
        self._materialize_public_receipts(staged_root)
        manifest = ProjectStorageManifest(
            project_uuid=snapshot.project_uuid,
            adapter=FILESYSTEM_ADAPTER,
        )
        write_bytes_atomic(
            staged_root / PROJECT_STORAGE_MANIFEST_PATH,
            ProjectStorageManifestStore.render(manifest),
        )
        self._copy_agent_surfaces(self.root, staged_root)
        return store

    def _materialize_public_receipts(self, staged_root: Path) -> None:
        """Project authoritative SQLite receipts and their governed markers."""
        for record in self.adapter.repository.public_mutation_records():
            receipt = record.receipt
            path = (
                staged_root
                / MUTATION_RECEIPT_ROOT
                / f"{receipt.key_sha256}.yml"
            )
            write_bytes_atomic(path, render_mutation_receipt(receipt))
            for relative, content in record.durable_documents:
                write_bytes_atomic(staged_root / relative, content)

    def _synchronize_auxiliary_state(self, staged_root: Path) -> None:
        current = self._auxiliary_paths(self.root)
        staged = self._auxiliary_paths(staged_root)
        for relative in sorted(current - staged, reverse=True):
            _unlink_and_sync_directory(self.root / relative)
        for relative in sorted(staged):
            source = staged_root / relative
            write_bytes_atomic(
                self.root / relative,
                _read_confined_project_file(
                    staged_root,
                    source,
                    operation="identity auxiliary synchronization",
                ),
            )
        # Some public receipts govern replica-local recovery documents whose
        # broad classification is ``backup``. They intentionally stay out of
        # the generic auxiliary copy set, but SQLite owns their exact bytes and
        # must rematerialize them after an interrupted acknowledgement or loss.
        for relative, content in sorted(
            self.adapter.repository.public_mutation_documents().items()
        ):
            write_bytes_atomic(self.root / relative, content)
        self._copy_agent_surfaces(staged_root, self.root)

    @classmethod
    def _copy_auxiliary_state(cls, source_root: Path, target_root: Path) -> None:
        for relative in sorted(cls._auxiliary_paths(source_root)):
            source = source_root / relative
            write_bytes_atomic(
                target_root / relative,
                _read_confined_project_file(
                    source_root,
                    source,
                    operation="identity auxiliary copy",
                ),
            )

    @staticmethod
    def _auxiliary_paths(root: Path) -> set[Path]:
        p2p = root / ".p2p"
        paths: set[Path] = set()
        if not p2p.exists() and not _is_link_or_reparse_point(p2p):
            return paths
        _assert_safe_directory_tree(root, p2p)
        for path in p2p.rglob("*"):
            if not path.is_file():
                continue
            relative_p2p = path.relative_to(p2p).as_posix()
            classification, _kind, _reason = classify_memory_path(relative_p2p)
            relative = Path(".p2p") / relative_p2p
            relative_text = relative.as_posix()
            folded_p2p = relative_p2p.casefold()
            folded = relative_text.casefold()
            if (
                folded_p2p.startswith("local/sqlite-")
                and ".stage/" in folded_p2p
            ) or folded_p2p.startswith("local/.project.sqlite3."):
                continue
            if folded == PROJECT_STORAGE_MANIFEST_PATH.casefold():
                continue
            if folded == SQLITE_MAINTENANCE_MARKER.casefold():
                continue
            if folded == SQLITE_ACTIVATION_MARKER.casefold():
                continue
            if folded == ".p2p/local/sqlite-recovery.apply.lock":
                continue
            if folded.startswith(
                ".p2p/local/sqlite-recovery-completions/"
            ):
                continue
            if folded.startswith(f"{MUTATION_RECEIPT_ROOT.casefold()}/"):
                continue
            if folded == SQLITE_DATABASE_PATH.casefold() or folded.startswith(
                f"{SQLITE_DATABASE_PATH.casefold()}-"
            ):
                continue
            if classification in {
                "integration_artifact",
                "replica_local",
                "derived_projection",
                "personal_configuration",
                "external_material",
            }:
                paths.add(relative)
        return paths

    @staticmethod
    def _copy_agent_surfaces(source_root: Path, target_root: Path) -> None:
        exact = (
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "P2P-SETUP.md",
            ".github/copilot-instructions.md",
        )
        for relative in exact:
            source = source_root / relative
            if source.exists() or _is_link_or_reparse_point(source):
                _assert_safe_regular_file(source_root, source)
                target = target_root / relative
                _assert_safe_path_components(target_root, target.parent)
                write_bytes_atomic(
                    target,
                    _read_confined_project_file(
                        source_root,
                        source,
                        operation="agent surface copy",
                    ),
                )
        for relative in (".agents", ".cursor"):
            source = source_root / relative
            if not source.exists() and not _is_link_or_reparse_point(source):
                continue
            _assert_safe_directory_tree(source_root, source)
            target = target_root / relative
            if target.exists() or _is_link_or_reparse_point(target):
                _assert_safe_directory_tree(target_root, target)
                shutil.rmtree(target)
            _assert_safe_path_components(target_root, target.parent)
            shutil.copytree(source, target)


class SQLiteProjectStateAdapter:
    def __init__(
        self,
        root: Path,
        selection: ProjectStorageSelection,
        *,
        failure_injector=None,
    ) -> None:
        self.root = root.resolve()
        self._selection = selection
        self._repository = SQLiteProjectStateRepository(
            self.root,
            failure_injector=failure_injector,
        )
        self._blobs = SQLiteBlobStore(self._repository)
        self._snapshots = SQLiteSnapshotPort(self._repository)
        self._backups = SQLiteBackupPort(
            self._repository,
            failure_injector=failure_injector,
        )
        self._migrations = SQLiteMigrationPort(self._repository)
        self._compatibility: SQLiteCompatibilityWorkspace | None = None
        self._migrations.verify_current()

    @property
    def selection(self) -> ProjectStorageSelection:
        return self._selection

    @property
    def capabilities(self) -> ProjectStorageCapabilities:
        return ProjectStorageCapabilities(
            adapter=SQLITE_ADAPTER,
            schema_version=SQLITE_SCHEMA_VERSION,
        )

    @property
    def repository(self) -> SQLiteProjectStateRepository:
        return self._repository

    @property
    def blobs(self) -> SQLiteBlobStore:
        return self._blobs

    @property
    def snapshots(self) -> SQLiteSnapshotPort:
        return self._snapshots

    @property
    def backups(self) -> SQLiteBackupPort:
        return self._backups

    @property
    def migrations(self) -> SQLiteMigrationPort:
        return self._migrations

    def unit_of_work(self) -> SQLiteProjectUnitOfWork:
        return SQLiteProjectUnitOfWork(self._repository)

    def refresh_selection(self, selection: ProjectStorageSelection) -> None:
        if selection.adapter != SQLITE_ADAPTER:
            raise ProjectStorageError(
                ProjectStorageErrorCode.configuration_contradiction,
                "SQLite adapter cannot adopt a different storage selection",
            )
        self._selection = selection

    def compatibility_target(self) -> SQLiteCompatibilityWorkspace:
        if self._compatibility is None:
            self._compatibility = SQLiteCompatibilityWorkspace(self)
        return self._compatibility


def _verify_sqlite_backup(
    root: Path,
    files: Mapping[str, bytes],
    manifest: Mapping[str, object],
) -> None:
    if SQLITE_DATABASE_PATH not in files or PROJECT_STORAGE_MANIFEST_PATH not in files:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite physical backup lacks database or storage manifest",
        )
    with _temporary_sqlite_repository(files[SQLITE_DATABASE_PATH]) as repository:
        issues = repository.integrity_check(verify_blobs=False)
        snapshot = repository.snapshot()
        with repository.connections.connect(writable=False) as connection:
            maintenance = connection.execute(
                "SELECT maintenance_state FROM storage_metadata WHERE singleton = 1"
            ).fetchone()
    if issues:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite backup database failed integrity verification",
            diagnostic="; ".join(issues),
        )
    if maintenance is None or str(maintenance["maintenance_state"]) != "ready":
        raise ProjectStorageError(
            ProjectStorageErrorCode.recovery_required,
            "SQLite physical backup contains a fenced maintenance state",
        )
    if (
        snapshot.project_uuid != str(manifest.get("project_uuid") or "")
        or snapshot.semantic_state_digest
        != str(manifest.get("semantic_state_digest") or "")
    ):
        raise ProjectStorageError(
            ProjectStorageErrorCode.identity_mismatch,
            "SQLite backup manifest disagrees with its database",
        )
    for blob in snapshot.blobs:
        path = sqlite_blob_path(root, blob.digest).relative_to(root).as_posix()
        content = files.get(path)
        if content is None or len(content) != blob.size or hashlib.sha256(content).hexdigest() != (
            blob.digest.removeprefix("sha256:")
        ):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite backup contains a missing or corrupt managed blob",
            )


class _temporary_sqlite_repository:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.temporary: tempfile.TemporaryDirectory[str] | None = None
        self.repository: SQLiteProjectStateRepository | None = None

    def __enter__(self) -> SQLiteProjectStateRepository:
        self.temporary = tempfile.TemporaryDirectory(prefix="p2p-sqlite-verify-")
        root = Path(self.temporary.name)
        path = root / SQLITE_DATABASE_PATH
        path.parent.mkdir(parents=True)
        path.write_bytes(self.content)
        self.repository = SQLiteProjectStateRepository(root, database_path=path)
        return self.repository

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.temporary is not None:
            self.temporary.cleanup()


def _archive_kind(codec: CanonicalBundleCodec, source: Path) -> str:
    try:
        codec.decode_bundle(source)
    except ValueError:
        return "physical_backup"
    return "portable_bundle"


def _checkpoint(repository: SQLiteProjectStateRepository) -> None:
    with repository.connections.connect(writable=True) as connection:
        row = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if row is not None and int(row[0]) != 0:
            raise ProjectStorageError(
                ProjectStorageErrorCode.busy,
                "SQLite WAL checkpoint could not complete before activation",
            )


def _set_database_maintenance_state(
    repository: SQLiteProjectStateRepository,
    state: str,
) -> None:
    """Fence or release writes using state stored in the authoritative DB."""
    with repository.connections.connect(writable=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            changed = connection.execute(
                "UPDATE storage_metadata SET maintenance_state = ?, updated_at = ? "
                "WHERE singleton = 1",
                (state, _utc_now()),
            ).rowcount
            if changed != 1:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite maintenance metadata is missing",
                )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise


def _verify_recovered_database(
    root: Path,
    *,
    database_path: Path | None = None,
    project_uuid: str,
    semantic_state_digest: str,
) -> None:
    repository = SQLiteProjectStateRepository(
        root,
        database_path=database_path,
    )
    issues = repository.integrity_check()
    snapshot = repository.snapshot()
    if (
        issues
        or snapshot.project_uuid != project_uuid
        or snapshot.semantic_state_digest != semantic_state_digest
    ):
        raise ProjectStorageError(
            ProjectStorageErrorCode.recovery_required,
            "recovered SQLite source database failed post-rollback verification",
            diagnostic="; ".join(issues),
        )


def _fence_database(
    repository: SQLiteProjectStateRepository,
    *,
    expected_revision: str,
    state: str,
) -> None:
    """Acquire the writer lock and fence only the revision that was previewed."""
    committed = False
    try:
        with repository.connections.connect(writable=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT semantic_state_digest, maintenance_state "
                    "FROM storage_metadata WHERE singleton = 1"
                ).fetchone()
                if row is None:
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.integrity_failure,
                        "SQLite maintenance metadata is missing",
                    )
                if str(row["maintenance_state"]) != "ready":
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.recovery_required,
                        "SQLite project is already fenced by maintenance",
                    )
                if str(row["semantic_state_digest"]) != expected_revision:
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.stale_revision,
                        "SQLite project changed before maintenance could start",
                    )
                connection.execute(
                    "UPDATE storage_metadata SET maintenance_state = ?, updated_at = ? "
                    "WHERE singleton = 1",
                    (state, _utc_now()),
                )
                try:
                    connection.execute("COMMIT")
                except Exception:
                    # A transport/driver error may be raised after SQLite
                    # durably committed. An ended transaction is therefore a
                    # conservative committed-fence outcome, not a safe retry.
                    try:
                        committed = not connection.in_transaction
                    except (AttributeError, sqlite3.Error):
                        committed = True
                    raise
                committed = True
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
    except Exception as exc:
        if committed:
            raise _CommittedMaintenanceFenceError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite maintenance fence committed but post-commit verification failed",
                diagnostic=str(exc),
            ) from exc
        raise


def _write_marker(path: Path, payload: Mapping[str, object]) -> None:
    root = path.parents[2]
    _assert_safe_path_components(root, path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = canonical_json_bytes(payload)
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("SQLite maintenance marker write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        _sync_directories(path.parent)
    except FileExistsError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.recovery_required,
            "another SQLite maintenance operation owns the recovery marker",
        ) from exc
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            _unlink_and_sync_directory(path)
        raise


def _update_marker(path: Path, payload: dict[str, object], *, phase: str) -> None:
    """Durably advance an owned maintenance marker without changing identity."""
    _assert_safe_regular_file(path.parents[2], path)
    payload["phase"] = phase
    write_bytes_atomic(path, canonical_json_bytes(payload), mode=0o600)


def _maintenance_marker_path(root: Path, value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("maintenance path is not project-relative")
    resolved = (root / relative).resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ValueError("maintenance path escapes the project root")
    return str(resolved)


def _install_blob_payloads(root: Path, payloads: Mapping[str, bytes]) -> None:
    for digest, content in payloads.items():
        if hashlib.sha256(content).hexdigest() != digest.removeprefix("sha256:"):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "restore blob payload digest is invalid",
            )
        install_sqlite_blob_bytes(root, digest, content)


def _rollback_blob_changes(root: Path, value: object) -> None:
    if not isinstance(value, list):
        return
    for item in value:
        if not isinstance(item, Mapping) or bool(item.get("existed_before")):
            continue
        relative = Path(str(item.get("path") or ""))
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite rollback blob path is unsafe",
            )
        path = root / relative
        expected = str(item.get("digest") or "").removeprefix("sha256:")
        if not path.exists() and not _is_link_or_reparse_point(path):
            continue
        try:
            content = read_sqlite_blob_bytes(root, f"sha256:{expected}")
        except ProjectStorageError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite rollback blob target is unsafe",
                diagnostic=exc.diagnostic,
            ) from exc
        if hashlib.sha256(content).hexdigest() != expected:
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite rollback refuses to remove a changed blob",
            )
        _unlink_and_sync_directory(path)


def path_to_digest(path: str) -> str:
    name = Path(path).name
    return f"sha256:{name}"


def operation_key_sha(operation_key: str) -> str:
    return hashlib.sha256(operation_key.encode("utf-8")).hexdigest()[:24]


def _restore_operation_id(operation_key: str) -> str:
    return f"sqlite-restore-{hashlib.sha256(operation_key.encode('utf-8')).hexdigest()}"


def _restore_result_from_payload(
    payload: Mapping[str, object],
    *,
    replayed: bool,
) -> MemoryRestoreResult:
    if payload.get("contract") != "p2p-memory-restore-result/v1":
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite restore receipt contract is invalid",
        )
    try:
        return MemoryRestoreResult(
            status=str(payload["status"]),
            operation_key=str(payload["operation_key"]),
            archive_kind=str(payload["archive_kind"]),
            project_uuid=str(payload["project_uuid"]),
            semantic_state_digest=str(payload["semantic_state_digest"]),
            archive_sha256=str(payload["archive_sha256"]),
            preview_token=str(payload["preview_token"]),
            backup_path=str(payload["backup_path"]),
            recovery_path=str(payload["recovery_path"]),
            changed_entity_count=int(payload["changed_entity_count"]),
            replayed=replayed,
            message=str(payload.get("message") or ""),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite restore receipt payload is invalid",
            diagnostic=str(exc),
        ) from exc


def _json_text(value: object) -> str:
    return canonical_json_bytes(value).decode("utf-8").rstrip("\n")


def _compatibility_actor(arguments: Mapping[str, object]) -> str:
    for key in (
        "actor",
        "actor_id",
        "owner",
        "decider",
        "reviewer",
        "created_by",
    ):
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "local-owner"


def _sqlite_replica_lock_owner(
    repository: SQLiteProjectStateRepository,
    arguments: Mapping[str, object],
) -> str:
    explicit = _compatibility_actor(arguments)
    if explicit != "local-owner":
        return explicit
    for entity in repository.snapshot().entities:
        if entity.technical_id != "project:permissions":
            continue
        document = entity.payload.get("document")
        identities = document.get("identities") if isinstance(document, Mapping) else None
        if not isinstance(identities, Mapping):
            break
        for actor_id, identity in identities.items():
            if (
                isinstance(actor_id, str)
                and isinstance(identity, Mapping)
                and identity.get("role") == "owner"
            ):
                return actor_id
    return explicit


def _require_sqlite_owner(
    repository: SQLiteProjectStateRepository,
    actor: str,
    *,
    operation: str,
) -> None:
    """Authorize a maintenance caller from canonical DB state.

    SQLite projects do not retain the canonical permissions YAML projection,
    so authorization must not fall back to a marker, preview, or generated
    filesystem file.
    """
    permissions = next(
        (
            entity.payload.get("document")
            for entity in repository.snapshot().entities
            if entity.technical_id == "project:permissions"
        ),
        None,
    )
    if not isinstance(permissions, Mapping):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "canonical project permissions are missing",
        )
    try:
        resolved = PermissionsService(
            root=repository.root,
            p2p_dir=repository.root / ".p2p",
        ).resolve_actor_payload(actor, permissions)
    except ValueError as exc:
        raise ValueError(
            f"P2P343_PROJECT_QUESTION_OWNER_REQUIRED: operation `{operation}` "
            f"requires role `owner`; actor `{actor}` is not an authorized owner"
        ) from exc
    if resolved.role != "owner":
        raise ValueError(
            f"P2P343_PROJECT_QUESTION_OWNER_REQUIRED: operation `{operation}` requires "
            f"role `owner`; actor `{resolved.actor_id}` has role `{resolved.role}`"
        )

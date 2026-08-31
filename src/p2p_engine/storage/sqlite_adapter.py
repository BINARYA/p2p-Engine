from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from p2p_engine.core.canonical_memory import (
    BundleExportResult,
    BundleValidationResult,
    MemoryRecoveryStatus,
    MemoryRestorePreview,
    MemoryRestoreResult,
    PhysicalBackupResult,
    canonical_json_bytes,
    semantic_sha256,
)
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
from p2p_engine.foundation.files import write_bytes_atomic
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.storage.canonical_memory import (
    FilesystemCanonicalMemoryStore,
    classify_memory_path,
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
    create_sqlite_database,
    sqlite_blob_path,
)
from p2p_engine.storage.sqlite_schema import (
    SQLITE_ADAPTER,
    SQLITE_DATABASE_PATH,
    SQLITE_MAINTENANCE_MARKER,
    SQLITE_SCHEMA_CONTRACT,
    SQLITE_SCHEMA_V1_SHA256,
    SQLITE_SCHEMA_VERSION,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SQLiteSnapshotPort:
    def __init__(self, repository: SQLiteProjectStateRepository) -> None:
        self.repository = repository
        self.store = SQLiteCanonicalStore(repository)
        self.codec = CanonicalBundleCodec()

    def export_bundle(self) -> ProjectArchive:
        snapshot = self.repository.snapshot()
        content, _manifest = self.codec.encode_bundle(self.store, snapshot)
        return ProjectArchive(
            kind="portable_bundle",
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
            semantic_state_digest=snapshot.semantic_state_digest,
        )

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
        archive = self.export_bundle()
        return BundleExportResult(
            status="ready",
            output="",
            manifest=self.codec.manifest(self.repository.snapshot()),
            archive_sha256=archive.sha256,
            archive_size=len(archive.content),
        )

    def export_bundle_to(self, output: Path) -> BundleExportResult:
        archive = self.export_bundle()
        target = output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        write_bytes_atomic(target, archive.content)
        return BundleExportResult(
            status="exported",
            output=str(target),
            manifest=self.codec.manifest(self.repository.snapshot()),
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
        snapshot = self.repository.snapshot()
        files = self._backup_files(snapshot)
        content = self.codec.encode_physical_backup(
            store=SQLiteCanonicalStore(self.repository),
            files=files,
            directories=(".p2p/local", ".p2p/blobs", ".p2p/blobs/sha256"),
            semantic_state_digest=snapshot.semantic_state_digest,
            source_revision=snapshot.semantic_state_digest,
        )
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
        target = output.resolve()
        if not allow_internal and target.is_relative_to(self.repository.root / ".p2p"):
            raise ValueError("P2P_BACKUP_OUTPUT_UNSAFE: backup output must be outside .p2p")
        if target.exists():
            raise ValueError("P2P_BACKUP_OUTPUT_EXISTS: refusing to overwrite backup output")
        archive = self.create_backup()
        target.parent.mkdir(parents=True, exist_ok=True)
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
        if not operation_key.strip() or not actor.strip():
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "restore operation and actor are required",
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
        if not confirm:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "SQLite restore requires explicit confirmation",
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
        backup_dir = self.repository.root / ".p2p/backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"sqlite-pre-restore-{operation_key_sha(operation_key)}.p2pbackup"
        backup_result: PhysicalBackupResult | None = None
        recovery_path = backup_dir / f"sqlite-recovery-{operation_key_sha(operation_key)}.sqlite3"
        marker = self.repository.root / SQLITE_MAINTENANCE_MARKER
        staging_dir = self.repository.root / ".p2p/local" / (
            f"sqlite-restore-{operation_key_sha(operation_key)}.stage"
        )
        staging_dir.mkdir(parents=True, exist_ok=False)
        stage_db = staging_dir / "project.sqlite3"
        safe_to_clear_marker = False
        result: MemoryRestoreResult | None = None
        try:
            _write_marker(
                marker,
                {
                    "contract": "p2p-sqlite-maintenance/v1",
                    "operation": "restore",
                    "operation_key": operation_key,
                    "stage": str(staging_dir.relative_to(self.repository.root)),
                    "recovery": str(recovery_path.relative_to(self.repository.root)),
                },
            )
            _set_database_maintenance_state(self.repository, "restoring")
            self._inject("after_restore_marker")
            backup_result = (
                self._existing_backup_result(backup_path)
                if backup_path.exists()
                else self._backup_to(
                    backup_path,
                    coordinated=True,
                    allow_internal=True,
                )
            )
            blob_payloads = self._prepare_restore_database(source, stage_db)
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
            os.replace(self.repository.database_path, recovery_path)
            self._inject("after_restore_old_database_move")
            os.replace(stage_db, self.repository.database_path)
            _install_blob_payloads(self.repository.root, blob_payloads)
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
            self._inject("after_restore_receipt")
            safe_to_clear_marker = True
        except Exception:
            if recovery_path.is_file():
                self.repository.database_path.unlink(missing_ok=True)
                os.replace(recovery_path, self.repository.database_path)
            if self.repository.database_path.is_file():
                _set_database_maintenance_state(self.repository, "ready")
            safe_to_clear_marker = True
            raise
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)
            if safe_to_clear_marker:
                marker.unlink(missing_ok=True)
        assert result is not None
        return result

    def recovery_status(self) -> MemoryRecoveryStatus:
        marker = self.repository.root / SQLITE_MAINTENANCE_MARKER
        if not marker.exists():
            return MemoryRecoveryStatus(
                state="clean",
                message="No interrupted SQLite maintenance is recorded.",
            )
        if marker.is_symlink() or not marker.is_file():
            return MemoryRecoveryStatus(
                state="invalid_marker",
                marker=str(marker),
                message="SQLite maintenance marker is not a safe regular file.",
            )
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("contract") != (
                "p2p-sqlite-maintenance/v1"
            ):
                raise ValueError("unsupported SQLite maintenance marker contract")
            staging_path = _maintenance_marker_path(
                self.repository.root,
                payload.get("stage"),
            )
            recovery_path = _maintenance_marker_path(
                self.repository.root,
                payload.get("recovery"),
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return MemoryRecoveryStatus(
                state="invalid_marker",
                marker=str(marker),
                message=f"SQLite maintenance marker is unreadable or invalid: {exc}",
            )
        return MemoryRecoveryStatus(
            state="recovery_required",
            marker=str(marker),
            staging_path=staging_path,
            recovery_path=recovery_path,
            message="Interrupted SQLite maintenance requires explicit recovery.",
        )

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

    def _existing_backup_result(self, path: Path) -> PhysicalBackupResult:
        content = path.read_bytes()
        archive = ProjectArchive(
            kind="physical_backup",
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
            semantic_state_digest=self.repository.snapshot().semantic_state_digest,
        )
        self.verify_backup(archive)
        decoded = self.codec.decode_physical_backup(content)
        return PhysicalBackupResult(
            status="created",
            output=str(path.resolve()),
            project_uuid=decoded.project_uuid,
            source_revision=str(decoded.manifest["source_revision"]),
            archive_sha256=archive.sha256,
            archive_size=len(content),
            file_count=len(decoded.files),
            coordinated=True,
        )

    def _backup_files(self, snapshot) -> dict[str, bytes]:
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
            files = {SQLITE_DATABASE_PATH: backup_db.read_bytes()}
        manifest = self.repository.root / PROJECT_STORAGE_MANIFEST_PATH
        files[PROJECT_STORAGE_MANIFEST_PATH] = manifest.read_bytes()
        for blob in snapshot.blobs:
            path = sqlite_blob_path(self.repository.root, blob.digest)
            relative = path.relative_to(self.repository.root).as_posix()
            files[relative] = path.read_bytes()
        return dict(sorted(files.items()))

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
        create_sqlite_database(stage_db, identity=identity, snapshot=decoded.snapshot)
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
        failure_injector=None,
    ) -> str:
        version = self.schema_version()
        state = self._maintenance_state()
        if version > SQLITE_SCHEMA_VERSION:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "SQLite project schema is newer than this runtime",
            )
        if version == SQLITE_SCHEMA_VERSION:
            if state == "ready":
                self.verify_current()
                return "current"
            if state != "migrating":
                raise ProjectStorageError(
                    ProjectStorageErrorCode.recovery_required,
                    "SQLite project is fenced by another maintenance operation",
                )
            self._verify_recovery_backup(backup_path)
            issues = self.repository.integrity_check()
            if issues:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "committed SQLite migration cannot be finalized",
                    diagnostic="; ".join(issues),
                )
            self._set_maintenance_state("ready")
            (self.repository.root / SQLITE_MAINTENANCE_MARKER).unlink(missing_ok=True)
            return "resumed"
        if version != 0:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "SQLite project schema has no ordered migration path",
            )

        marker = self.repository.root / SQLITE_MAINTENANCE_MARKER
        if marker.exists():
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "another SQLite maintenance operation requires recovery",
            )
        _write_marker(
            marker,
            {
                "contract": "p2p-sqlite-maintenance/v1",
                "operation": "schema-migration",
                "from_schema": 0,
                "to_schema": SQLITE_SCHEMA_VERSION,
                "backup": str(backup_path.resolve()),
            },
        )
        self._set_maintenance_state("migrating")
        committed = False
        try:
            self._inject(failure_injector, "after_migration_fence")
            backups = SQLiteBackupPort(self.repository)
            if backup_path.exists():
                backups._existing_backup_result(backup_path)
            else:
                backups.backup_to(backup_path)
            self._inject(failure_injector, "after_migration_backup")
            with self.repository.connections.connect(writable=True) as connection:
                connection.execute("BEGIN IMMEDIATE")
                if int(connection.execute("PRAGMA user_version").fetchone()[0]) != 0:
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
                committed = True
            self._inject(failure_injector, "after_migration_commit")
            issues = self.repository.integrity_check()
            if issues:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "migrated SQLite schema failed integrity verification",
                    diagnostic="; ".join(issues),
                )
            self._inject(failure_injector, "after_migration_verification")
            self._inject(failure_injector, "before_migration_finalize")
            self._set_maintenance_state("ready")
            marker.unlink(missing_ok=True)
            return "migrated"
        except Exception:
            if not committed and self.schema_version() == 0:
                self._set_maintenance_state("ready")
                marker.unlink(missing_ok=True)
            raise

    def _verify_recovery_backup(self, backup_path: Path) -> None:
        if not backup_path.is_file():
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite migration backup is missing",
            )
        try:
            content = backup_path.read_bytes()
        except OSError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite migration backup cannot be read",
                diagnostic=str(exc),
            ) from exc
        archive = ProjectArchive(
            kind="physical_backup",
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
            semantic_state_digest=self.repository.snapshot().semantic_state_digest,
        )
        SQLiteBackupPort(self.repository).verify_backup(archive)

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

    def __getattr__(self, name: str):
        def invoke(*args: object, **kwargs: object):
            return self._invoke(name, *args, **kwargs)

        return invoke

    def _invoke(self, name: str, *args: object, **kwargs: object):
        before = self.adapter.repository.snapshot()
        with tempfile.TemporaryDirectory(prefix="p2p-sqlite-compat-") as raw:
            staged_root = Path(raw)
            staged_store = self._materialize(staged_root, before)
            if name == "init_project_with_operation_key" and str(
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
            from p2p_engine.storage.filesystem import (
                FilesystemWorkspace,
                _project_init_operation_payload,
            )

            workspace = FilesystemWorkspace(staged_root)
            target = getattr(workspace, name)
            try:
                result = target(*args, **kwargs)
            except ValueError as exc:
                if name != "init_project_with_operation_key" or not str(exc).startswith(
                    "P2P_IDEMPOTENCY_POSTCONDITION_DRIFT:"
                ):
                    raise
                operation_key = str(kwargs.get("operation_key") or "")
                receipt = workspace._mutation_receipt_service().read(
                    idempotency_key=operation_key
                )
                if receipt is None or receipt.operation != "init":
                    raise
                identity = receipt.result.get("project_identity")
                if not isinstance(identity, Mapping) or str(
                    identity.get("project_uuid") or ""
                ) != before.project_uuid:
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.identity_mismatch,
                        "SQLite initialization receipt disagrees with the active project",
                    ) from exc
                result = _project_init_operation_payload(
                    dict(receipt.result),
                    status="already_applied",
                    actor=receipt.actor,
                    message=(
                        "Project initialization was already applied with this operation key."
                    ),
                )
            after = CanonicalBundleCodec().snapshot(staged_store)
            identity_changed = after.project_uuid != before.project_uuid
            if after.semantic_state_digest != before.semantic_state_digest:
                if identity_changed:
                    self._activate_identity_transition(
                        name=name,
                        arguments=kwargs,
                        before=before,
                        after=after,
                        staged_store=staged_store,
                        staged_root=staged_root,
                    )
                else:
                    blob_payloads = {
                        blob.digest: staged_store.read_blob_bytes(blob)
                        for blob in after.blobs
                    }
                    with self.adapter.unit_of_work() as unit:
                        unit.stage(
                            ProjectStateMutation(
                                operation_id=(
                                    f"sqlite-compat-{name}-{uuid4().hex}"
                                ),
                                actor=_compatibility_actor(kwargs),
                                expected_revision=ProjectStateRevision(
                                    before.semantic_state_digest
                                ),
                                target=after,
                                blob_payloads=blob_payloads,
                            )
                        )
                        unit.commit()
            if not identity_changed:
                self._synchronize_auxiliary_state(staged_root)
            return result

    def _activate_identity_transition(
        self,
        *,
        name: str,
        arguments: Mapping[str, object],
        before,
        after,
        staged_store: FilesystemCanonicalMemoryStore,
        staged_root: Path,
    ) -> None:
        """Atomically replace the one-project DB when identity is governed anew."""
        operation_key = str(arguments.get("operation_key") or uuid4().hex)
        operation_hash = operation_key_sha(operation_key)
        local = self.root / ".p2p/local"
        backup_dir = self.root / ".p2p/backups"
        local.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)
        stage_dir = local / f"sqlite-identity-{operation_hash}-{uuid4().hex}.stage"
        stage_dir.mkdir(parents=True, exist_ok=False)
        stage_db = stage_dir / "project.sqlite3"
        recovery_db = backup_dir / f"sqlite-pre-identity-{operation_hash}.sqlite3"
        backup_path = backup_dir / f"sqlite-pre-identity-{operation_hash}.p2pbackup"
        marker = self.root / SQLITE_MAINTENANCE_MARKER
        manifest_store = ProjectStorageManifestStore(self.root)
        previous_manifest = manifest_store.path.read_bytes()
        previous_auxiliary = self._auxiliary_snapshot(self.root)
        safe_to_clear_marker = False
        try:
            identity = staged_store.project_identity()
            create_sqlite_database(stage_db, identity=identity, snapshot=after)
            staged = SQLiteProjectStateRepository(self.root, database_path=stage_db)
            issues = staged.integrity_check(verify_blobs=False)
            if issues or staged.snapshot().semantic_state_digest != after.semantic_state_digest:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "staged SQLite identity transition failed verification",
                    diagnostic="; ".join(issues),
                )
            self._inject_identity_failure("after_identity_stage")
            _write_marker(
                marker,
                {
                    "contract": "p2p-sqlite-maintenance/v1",
                    "operation": "identity-transition",
                    "domain_operation": name,
                    "operation_key": operation_key,
                    "previous_project_uuid": before.project_uuid,
                    "target_project_uuid": after.project_uuid,
                    "stage": str(stage_dir.relative_to(self.root)),
                    "recovery": str(recovery_db.relative_to(self.root)),
                },
            )
            _fence_database(
                self.adapter.repository,
                expected_revision=before.semantic_state_digest,
                state="restoring",
            )
            self._inject_identity_failure("after_identity_fence")
            backups = SQLiteBackupPort(self.adapter.repository)
            if backup_path.exists():
                backups._existing_backup_result(backup_path)
            else:
                backups._backup_to(
                    backup_path,
                    coordinated=True,
                    allow_internal=True,
                )
            self._inject_identity_failure("after_identity_backup")
            _checkpoint(self.adapter.repository)
            os.replace(self.adapter.repository.database_path, recovery_db)
            self._inject_identity_failure("after_identity_old_database_move")
            os.replace(stage_db, self.adapter.repository.database_path)
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
            self._inject_identity_failure("after_identity_auxiliary")
            safe_to_clear_marker = True
        except Exception:
            if recovery_db.is_file():
                self.adapter.repository.database_path.unlink(missing_ok=True)
                os.replace(recovery_db, self.adapter.repository.database_path)
            write_bytes_atomic(manifest_store.path, previous_manifest)
            self._restore_auxiliary_snapshot(previous_auxiliary)
            if self.adapter.repository.database_path.is_file():
                _set_database_maintenance_state(self.adapter.repository, "ready")
            safe_to_clear_marker = True
            raise
        finally:
            shutil.rmtree(stage_dir, ignore_errors=True)
            if safe_to_clear_marker:
                marker.unlink(missing_ok=True)

    def _inject_identity_failure(self, stage: str) -> None:
        if self.adapter.repository.failure_injector is not None:
            self.adapter.repository.failure_injector(stage)

    @classmethod
    def _auxiliary_snapshot(cls, root: Path) -> dict[Path, bytes]:
        return {
            relative: (root / relative).read_bytes()
            for relative in cls._auxiliary_paths(root)
        }

    def _restore_auxiliary_snapshot(self, snapshot: Mapping[Path, bytes]) -> None:
        for relative in self._auxiliary_paths(self.root):
            (self.root / relative).unlink(missing_ok=True)
        for relative, content in snapshot.items():
            write_bytes_atomic(self.root / relative, content)

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

    def _synchronize_auxiliary_state(self, staged_root: Path) -> None:
        current = self._auxiliary_paths(self.root)
        staged = self._auxiliary_paths(staged_root)
        for relative in sorted(current - staged, reverse=True):
            (self.root / relative).unlink(missing_ok=True)
        for relative in sorted(staged):
            source = staged_root / relative
            write_bytes_atomic(self.root / relative, source.read_bytes())
        self._copy_agent_surfaces(staged_root, self.root)

    @classmethod
    def _copy_auxiliary_state(cls, source_root: Path, target_root: Path) -> None:
        for relative in sorted(cls._auxiliary_paths(source_root)):
            source = source_root / relative
            write_bytes_atomic(target_root / relative, source.read_bytes())

    @staticmethod
    def _auxiliary_paths(root: Path) -> set[Path]:
        p2p = root / ".p2p"
        paths: set[Path] = set()
        if not p2p.is_dir():
            return paths
        for path in p2p.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            relative_p2p = path.relative_to(p2p).as_posix()
            classification, _kind, _reason = classify_memory_path(relative_p2p)
            relative = Path(".p2p") / relative_p2p
            if relative.as_posix() == PROJECT_STORAGE_MANIFEST_PATH:
                continue
            if relative.as_posix() == SQLITE_MAINTENANCE_MARKER:
                continue
            if relative.as_posix() == SQLITE_DATABASE_PATH or relative.as_posix().startswith(
                f"{SQLITE_DATABASE_PATH}-"
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
            if source.is_file() and not source.is_symlink():
                write_bytes_atomic(target_root / relative, source.read_bytes())
        for relative in (".agents", ".cursor"):
            source = source_root / relative
            if not source.is_dir() or source.is_symlink():
                continue
            target = target_root / relative
            if target.exists():
                shutil.rmtree(target)
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
    if issues:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite backup database failed integrity verification",
            diagnostic="; ".join(issues),
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


def _fence_database(
    repository: SQLiteProjectStateRepository,
    *,
    expected_revision: str,
    state: str,
) -> None:
    """Acquire the writer lock and fence only the revision that was previewed."""
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
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise


def _write_marker(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_bytes_atomic(path, canonical_json_bytes(payload))


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
        path = sqlite_blob_path(root, digest)
        if path.exists():
            if path.read_bytes() != content:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "restore blob conflicts with content-addressed storage",
                )
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.stage")
        temporary.write_bytes(content)
        if os.name != "nt":
            temporary.chmod(0o600)
        os.replace(temporary, path)


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
    for key in ("actor", "owner", "decider", "reviewer", "created_by"):
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "local-owner"

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from p2p_engine.core.canonical_memory import (
    MemoryRecoveryResult,
    MemoryRecoveryStatus,
    canonical_json_bytes,
)
from p2p_engine.core.mutation_receipts import MUTATION_RECEIPT_ROOT
from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    ProjectStorageError,
    ProjectStorageErrorCode,
    ProjectStorageManifest,
)
from p2p_engine.core.workspace_schema import (
    LOCK_ABSENT,
    LOCK_ACTIVE,
    LOCK_INVALID,
    LOCK_RECOVERY_OWNED,
    LOCK_STALE,
)
from p2p_engine.foundation.files import identity_slug, sync_directory, write_bytes_atomic
from p2p_engine.foundation.processes import pid_is_running
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.workspace_transactions import WorkspaceTransactionLockService
from p2p_engine.storage.canonical_memory import (
    FilesystemCanonicalMemoryStore,
    classify_memory_path,
)
from p2p_engine.storage.project_storage import ProjectStorageManifestStore
from p2p_engine.storage.sqlite_driver import SQLiteConnectionFactory, validate_sqlite_header
from p2p_engine.storage.sqlite_project_state import SQLiteProjectStateRepository
from p2p_engine.storage.sqlite_schema import (
    SQLITE_ACTIVATION_MARKER,
    SQLITE_ADAPTER,
    SQLITE_DATABASE_PATH,
    SQLITE_MAINTENANCE_MARKER,
    SQLITE_SCHEMA_VERSION,
)

SQLITE_MAINTENANCE_CONTRACT = "p2p-sqlite-maintenance/v2"
SQLITE_ACTIVATION_CONTRACT = "p2p-sqlite-activation/v2"
SQLITE_AUXILIARY_BACKUP_CONTRACT = "p2p-sqlite-auxiliary-backup/v1"
SQLITE_RECOVERY_COMPLETION_CONTRACT = "p2p-sqlite-recovery-completion/v1"
SQLITE_RECOVERY_COMPLETION_ROOT = Path(
    ".p2p/local/sqlite-recovery-completions"
)

_LEGACY_MARKER_CONTRACTS = frozenset(
    {"p2p-sqlite-maintenance/v1", "p2p-sqlite-activation/v1"}
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_LABEL = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_MAX_MARKER_BYTES = 256 * 1024
_MAX_AUXILIARY_FILES = 4096
_MAX_AUXILIARY_BYTES = 128 * 1024 * 1024
_OPERATION_PHASES = {
    "restore": frozenset(
        {
            "prepared",
            "fenced",
            "backup_created",
            "staged",
            "old_moved",
            "activated",
            "side_effects_applied",
            "receipt_committed",
        }
    ),
    "identity-transition": frozenset(
        {
            "prepared",
            "auxiliary_backed",
            "staged",
            "fenced",
            "backup_created",
            "old_moved",
            "activated",
            "manifest_updated",
            "auxiliary_applied",
        }
    ),
    "schema-migration": frozenset(
        {
            "prepared",
            "fenced",
            "recovery_created",
            "backup_created",
            "committed",
            "verified",
        }
    ),
    "initial-activation": frozenset(
        {"prepared", "staged", "detached", "activated", "manifest_updated"}
    ),
}
# The claim stays outside ``.p2p`` so an in-flight rollback does not become a
# durable project-memory artifact while the source snapshot is being verified.
_RECOVERY_LOCK = Path(".p2p-sqlite-recovery-apply.lock")


@dataclass(frozen=True)
class _RecoveryMarker:
    path: Path
    contract: str
    raw_sha256: str
    recovery_id: str
    recovery_token: str
    operation: str
    phase: str
    actor: str
    source_project_uuid: str
    source_semantic_state_digest: str
    target_project_uuid: str
    target_semantic_state_digest: str
    source_schema_version: int | None = None
    target_schema_version: int | None = None
    stage: Path | None = None
    recovery: Path | None = None
    auxiliary_backup: Path | None = None
    database_stage: Path | None = None
    canonical_stage: Path | None = None
    detached: tuple[tuple[Path, str], ...] = ()
    blob_changes: tuple[tuple[Path, str, bool], ...] = ()
    auxiliary_remove: tuple[tuple[Path, str, int], ...] = ()
    auxiliary_source: tuple[tuple[Path, str, int], ...] = ()
    auxiliary_target: tuple[tuple[Path, str, int], ...] = ()
    transaction_id: str = ""

    def status(self) -> MemoryRecoveryStatus:
        staging = self.stage or self.canonical_stage or self.database_stage
        return MemoryRecoveryStatus(
            state="recovery_required",
            marker=str(self.path),
            staging_path=str(staging or ""),
            recovery_path=str(self.recovery or ""),
            operation=self.operation,
            phase=self.phase,
            recovery_id=self.recovery_id,
            recovery_token=self.recovery_token,
            applicable=True,
            allowed_actions=("rollback",),
            source_project_uuid=self.source_project_uuid,
            source_semantic_state_digest=self.source_semantic_state_digest,
            target_project_uuid=self.target_project_uuid,
            target_semantic_state_digest=self.target_semantic_state_digest,
            marker_contract=self.contract,
            message=(
                "Interrupted SQLite maintenance requires an explicit, "
                "owner-authorized rollback."
            ),
        )


def new_sqlite_recovery_identity() -> tuple[str, str]:
    """Return a public recovery identifier and independent confirmation token."""
    return str(uuid4()), os.urandom(32).hex()


def write_sqlite_auxiliary_backup(
    root: Path,
    backup_relative: Path,
    files: Mapping[Path, bytes],
) -> Path:
    """Durably archive identity-transition auxiliary files before cutover.

    ``backup_relative`` and every key in ``files`` are project-root-relative.
    The directory is installed only after every payload and checksum manifest
    has been synced, so an interrupted writer never exposes a partial archive.
    """
    resolved = root.resolve()
    backup = _safe_relative_path(
        resolved,
        backup_relative.as_posix(),
        prefixes=(".p2p/backups/",),
    )
    if backup.exists() or backup.is_symlink():
        raise ProjectStorageError(
            ProjectStorageErrorCode.configuration_contradiction,
            "SQLite auxiliary recovery backup already exists",
        )
    if len(files) > _MAX_AUXILIARY_FILES:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary recovery backup contains too many files",
        )
    total = sum(len(content) for content in files.values())
    if total > _MAX_AUXILIARY_BYTES:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary recovery backup exceeds its safe size",
        )
    temporary = backup.with_name(f".{backup.name}.{uuid4().hex}.stage")
    entries: list[dict[str, object]] = []
    try:
        temporary.mkdir(parents=True, exist_ok=False)
        for relative, content in sorted(files.items(), key=lambda item: item[0].as_posix()):
            source = _safe_auxiliary_path(resolved, relative.as_posix())
            relative_posix = source.relative_to(resolved).as_posix()
            payload_relative = PurePosixPath("payload") / relative_posix
            payload_path = temporary / payload_relative.as_posix()
            write_bytes_atomic(payload_path, bytes(content), mode=0o600)
            entries.append(
                {
                    "path": relative_posix,
                    "stored_path": payload_relative.as_posix(),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size": len(content),
                }
            )
        manifest = {
            "contract": SQLITE_AUXILIARY_BACKUP_CONTRACT,
            "files": entries,
        }
        write_bytes_atomic(
            temporary / "manifest.json",
            canonical_json_bytes(manifest),
            mode=0o600,
        )
        sync_directory(temporary)
        backup.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary, backup)
        sync_directory(backup.parent)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return backup


class SQLiteRecoveryCoordinator:
    """Recover a fenced project without opening its selected storage adapter."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.live_database = self.root / SQLITE_DATABASE_PATH
        self.manifests = ProjectStorageManifestStore(self.root)

    def status(self) -> MemoryRecoveryStatus:
        marker_paths = self._present_markers()
        if not marker_paths:
            return MemoryRecoveryStatus(
                state="clean",
                message="No interrupted SQLite maintenance is recorded.",
            )
        if len(marker_paths) != 1:
            return MemoryRecoveryStatus(
                state="invalid_marker",
                marker=", ".join(str(path) for path in marker_paths),
                message="Multiple SQLite maintenance markers are present.",
            )
        path = marker_paths[0]
        try:
            raw, payload = _read_marker_payload(self.root, path)
            contract = str(payload.get("contract") or "")
            if contract in _LEGACY_MARKER_CONTRACTS:
                return _legacy_status(self.root, path, payload)
            return _parse_v2_marker(self.root, path, raw, payload).status()
        except (OSError, ValueError, ProjectStorageError) as exc:
            return MemoryRecoveryStatus(
                state="invalid_marker",
                marker=str(path),
                message=f"SQLite maintenance marker is unreadable or invalid: {exc}",
            )

    def apply(
        self,
        *,
        recovery_id: str,
        recovery_token: str,
        actor: str,
        action: str,
        confirm: bool,
    ) -> MemoryRecoveryResult:
        normalized_id = _uuid(recovery_id, "recovery_id")
        normalized_token = _sha256(recovery_token, "recovery_token")
        supplied_actor = actor.strip()
        if not supplied_actor:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite recovery actor is required",
            )
        try:
            normalized_actor = PermissionsService(
                root=self.root,
                p2p_dir=self.root / ".p2p",
            ).identity_slug(supplied_actor)
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite recovery actor is invalid",
                diagnostic=str(exc),
            ) from exc
        if action.strip().lower() != "rollback":
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "SQLite recovery currently supports only rollback",
            )
        if not confirm:
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite recovery rollback requires explicit confirmation",
            )
        marker_paths = self._present_markers()
        if not marker_paths:
            replay = self._completion_replay(
                recovery_id=normalized_id,
                recovery_token=normalized_token,
                actor=normalized_actor,
                allow_owner_handoff=True,
            )
            if replay is not None:
                return replay
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "No matching interrupted SQLite maintenance is recorded",
            )
        if len(marker_paths) != 1:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "Multiple SQLite maintenance markers prevent recovery",
            )
        with _RecoveryClaim(self.root, normalized_id):
            marker_paths = self._present_markers()
            if not marker_paths:
                replay = self._completion_replay(
                    recovery_id=normalized_id,
                    recovery_token=normalized_token,
                    actor=normalized_actor,
                    allow_owner_handoff=True,
                )
                if replay is not None:
                    return replay
                raise ProjectStorageError(
                    ProjectStorageErrorCode.recovery_required,
                    "SQLite recovery marker disappeared before rollback",
                )
            if len(marker_paths) != 1:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "Multiple SQLite maintenance markers prevent recovery",
                )
            raw, payload = _read_marker_payload(self.root, marker_paths[0])
            if str(payload.get("contract") or "") in _LEGACY_MARKER_CONTRACTS:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.unsupported_capability,
                    "Legacy SQLite recovery markers are inspectable but not applicable",
                )
            marker = _parse_v2_marker(self.root, marker_paths[0], raw, payload)
            if marker.recovery_id != normalized_id or not hmac.compare_digest(
                marker.recovery_token,
                normalized_token,
            ):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.idempotency_conflict,
                    "SQLite recovery identifier or token does not match the active marker",
                )
            self._ensure_writer_is_not_active(marker)
            # A completion receipt is replay evidence, not proof that the live
            # store is already the source state. Do not even parse it before
            # the rollback: malformed local evidence must not prevent putting
            # the verified source back in place. The receipt is validated only
            # after the idempotent rollback has converged.
            if marker.operation == "initial-activation":
                self._authorize_activation_owner(marker, normalized_actor)
                self._rollback_activation(marker)
            else:
                source_database = self._source_database(marker)
                self._authorize_database_owner(source_database, normalized_actor)
                self._rollback_database_maintenance(marker, source_database)
            result = MemoryRecoveryResult(
                status="rolled_back",
                recovery_id=marker.recovery_id,
                operation=marker.operation,
                action="rollback",
                actor=normalized_actor,
                project_uuid=marker.source_project_uuid,
                semantic_state_digest=marker.source_semantic_state_digest,
                message="Interrupted SQLite maintenance was rolled back to its verified source state.",
            )
            stored = self._write_completion(marker, result)
            completed: MemoryRecoveryResult | None = None
            if stored is not None:
                # A different current owner may finish cleanup after the
                # original recovery executor died. Preserve the original audit
                # actor, but prove that actor was also authorized by the exact
                # source state before accepting the stored completion.
                if marker.operation == "initial-activation":
                    self._authorize_activation_owner(marker, stored.actor)
                else:
                    self._authorize_database_owner(
                        self.live_database,
                        stored.actor,
                    )
                completed = self._completion_replay(
                    recovery_id=normalized_id,
                    recovery_token=normalized_token,
                    actor=stored.actor,
                    expected_marker_sha256=marker.raw_sha256,
                )
            self._finalize(marker)
            return completed or result

    def _present_markers(self) -> list[Path]:
        paths = [
            self.root / SQLITE_MAINTENANCE_MARKER,
            self.root / SQLITE_ACTIVATION_MARKER,
        ]
        return [
            path
            for path in paths
            if path.exists() or _is_link_or_reparse_point(path)
        ]

    def _source_database(self, marker: _RecoveryMarker) -> Path:
        candidates: list[Path] = []
        if marker.recovery is not None and marker.recovery.exists():
            candidates.append(marker.recovery)
        if self.live_database.exists():
            candidates.append(self.live_database)
        diagnostics: list[str] = []
        for candidate in candidates:
            try:
                self._verify_database(candidate, marker)
                return candidate
            except ProjectStorageError as exc:
                diagnostics.append(f"{candidate}: {exc}")
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery has no verified source database",
            diagnostic="; ".join(diagnostics),
        )

    def _verify_database(self, path: Path, marker: _RecoveryMarker) -> None:
        _assert_safe_regular_file(self.root, path)
        repository = SQLiteProjectStateRepository(self.root, database_path=path)
        issues = repository.integrity_check()
        if issues:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite recovery source database failed integrity verification",
                diagnostic="; ".join(issues),
            )
        snapshot = repository.snapshot()
        if marker.source_schema_version is not None:
            with repository.connections.connect(writable=False) as connection:
                schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if schema_version != marker.source_schema_version:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite recovery database has the wrong source schema version",
                    diagnostic=(
                        f"expected {marker.source_schema_version}, got {schema_version}"
                    ),
                )
        if (
            snapshot.project_uuid != marker.source_project_uuid
            or snapshot.semantic_state_digest != marker.source_semantic_state_digest
        ):
            raise ProjectStorageError(
                ProjectStorageErrorCode.identity_mismatch,
                "SQLite recovery source database disagrees with the marker",
            )

    def _authorize_database_owner(
        self,
        source_database: Path,
        actor: str,
    ) -> None:
        repository = SQLiteProjectStateRepository(
            self.root,
            database_path=source_database,
        )
        snapshot = repository.snapshot()
        permissions = next(
            (
                entity.payload.get("document")
                for entity in snapshot.entities
                if entity.technical_id == "project:permissions"
            ),
            None,
        )
        self._require_owner(permissions, actor)

    def _authorize_filesystem_owner(self, actor: str) -> None:
        path = self.root / ".p2p/project/permissions.yml"
        _assert_safe_regular_file(self.root, path)
        try:
            permissions = load_yaml(
                path.read_bytes(),
                loader_contract=UNIQUE_LOADER_CONTRACT,
            )
        except (OSError, ValueError) as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite activation recovery permissions cannot be read",
                diagnostic=str(exc),
            ) from exc
        self._require_owner(permissions, actor)

    def _authorize_activation_owner(self, marker: _RecoveryMarker, actor: str) -> None:
        permissions_relative = Path(".p2p/project/permissions.yml")
        live = self.root / permissions_relative
        staged = (
            marker.canonical_stage / permissions_relative
            if marker.canonical_stage is not None
            else Path()
        )
        path = live if live.is_file() and not live.is_symlink() else staged
        _assert_safe_regular_file(self.root, path)
        try:
            permissions = load_yaml(
                path.read_bytes(),
                loader_contract=UNIQUE_LOADER_CONTRACT,
            )
        except (OSError, ValueError) as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite activation recovery permissions cannot be read",
                diagnostic=str(exc),
            ) from exc
        self._require_owner(permissions, actor)

    def _require_owner(self, permissions: object, actor: str) -> None:
        if not isinstance(permissions, Mapping):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite recovery source permissions are missing or invalid",
            )
        try:
            resolved = PermissionsService(
                root=self.root,
                p2p_dir=self.root / ".p2p",
            ).resolve_actor_payload(actor, permissions)
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite recovery requires a source-project owner",
                diagnostic=str(exc),
            ) from exc
        if resolved.role != "owner":
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite recovery requires a source-project owner",
            )

    def _rollback_database_maintenance(
        self,
        marker: _RecoveryMarker,
        source_database: Path,
    ) -> None:
        if source_database != self.live_database:
            _assert_no_symlink_components(self.root, self.live_database.parent)
            _assert_no_symlink_components(self.root, self.live_database)
            _assert_safe_regular_file(self.root, source_database)
            self.live_database.parent.mkdir(parents=True, exist_ok=True)
            _assert_no_symlink_components(self.root, self.live_database.parent)
            _assert_no_symlink_components(self.root, self.live_database)
            _assert_safe_regular_file(self.root, source_database)
            self._verify_database(source_database, marker)
            _remove_sqlite_sidecars(self.live_database)
            os.replace(source_database, self.live_database)
            sync_directory(self.live_database.parent)
        self._verify_database(self.live_database, marker)
        write_bytes_atomic(
            self.manifests.path,
            ProjectStorageManifestStore.render(
                ProjectStorageManifest(
                    project_uuid=marker.source_project_uuid,
                    adapter=SQLITE_ADAPTER,
                    schema_version=SQLITE_SCHEMA_VERSION,
                )
            ),
            mode=0o600,
        )
        if marker.operation == "identity-transition":
            if marker.auxiliary_backup:
                if marker.auxiliary_backup.exists():
                    _verify_auxiliary_rollback_inputs(
                        self.root,
                        marker.auxiliary_backup,
                        marker.auxiliary_source,
                        marker.auxiliary_target,
                    )
                    for path, digest, size in marker.auxiliary_remove:
                        if path.exists() or _is_link_or_reparse_point(path):
                            _assert_safe_regular_file(self.root, path)
                            content = path.read_bytes()
                            if (
                                len(content) != size
                                or hashlib.sha256(content).hexdigest() != digest
                            ):
                                raise ProjectStorageError(
                                    ProjectStorageErrorCode.integrity_failure,
                                    "SQLite identity recovery refuses to remove a changed auxiliary artifact",
                                    diagnostic=str(path),
                                )
                            path.unlink()
                            sync_directory(path.parent)
                    _restore_auxiliary_backup(self.root, marker.auxiliary_backup)
                _verify_auxiliary_source_state(
                    self.root,
                    marker.auxiliary_source,
                    marker.auxiliary_remove,
                )
        self._rollback_blob_changes(marker)
        manifest = self.manifests.load()
        if (
            manifest.adapter != SQLITE_ADAPTER
            or manifest.project_uuid != marker.source_project_uuid
        ):
            raise ProjectStorageError(
                ProjectStorageErrorCode.identity_mismatch,
                "Recovered SQLite manifest disagrees with source identity",
            )
        # Keep the database-level fence until every database, manifest, blob,
        # and auxiliary postcondition has converged. Already-open writers also
        # reject the still-present marker, closing the short ready/cleanup gap.
        _set_database_ready(self.live_database)

    def _rollback_blob_changes(self, marker: _RecoveryMarker) -> None:
        for path, digest, existed_before in marker.blob_changes:
            if not path.exists() and not _is_link_or_reparse_point(path):
                if existed_before:
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.integrity_failure,
                        "SQLite recovery source blob is missing",
                        diagnostic=str(path),
                    )
                continue
            _assert_safe_regular_file(self.root, path)
            expected = digest.removeprefix("sha256:")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite recovery blob disagrees with its marker digest",
                    diagnostic=str(path),
                )
            if not existed_before:
                path.unlink()
                sync_directory(path.parent)

    def _rollback_activation(self, marker: _RecoveryMarker) -> None:
        if marker.canonical_stage is None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite activation marker lacks its canonical stage",
            )
        for relative, digest in marker.detached:
            live = self.root / relative
            staged = marker.canonical_stage / relative
            live_ok = _regular_file_digest(self.root, live) == digest
            staged_ok = _regular_file_digest(self.root, staged) == digest
            if not live_ok and not staged_ok:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite activation rollback cannot verify a detached artifact",
                    diagnostic=relative.as_posix(),
                )
            if live.exists() and not live_ok:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite activation rollback refuses to overwrite a changed artifact",
                    diagnostic=relative.as_posix(),
                )
        for relative, digest in marker.detached:
            live = self.root / relative
            staged = marker.canonical_stage / relative
            if _regular_file_digest(self.root, live) == digest:
                continue
            _assert_no_symlink_components(self.root, live.parent)
            _assert_safe_regular_file(self.root, staged)
            live.parent.mkdir(parents=True, exist_ok=True)
            _assert_no_symlink_components(self.root, live.parent)
            _assert_no_symlink_components(self.root, live)
            _assert_safe_regular_file(self.root, staged)
            if _regular_file_digest(self.root, staged) != digest:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite activation rollback staged artifact changed before restore",
                    diagnostic=relative.as_posix(),
                )
            os.replace(staged, live)
            sync_directory(live.parent)
        for path in (marker.database_stage, self.live_database):
            if path is None:
                continue
            if path.exists() or _is_link_or_reparse_point(path):
                _assert_safe_regular_file(self.root, path)
                path.unlink()
            _remove_sqlite_sidecars(path)
        write_bytes_atomic(
            self.manifests.path,
            ProjectStorageManifestStore.render(
                ProjectStorageManifest(
                    project_uuid=marker.source_project_uuid,
                    adapter=FILESYSTEM_ADAPTER,
                )
            ),
            mode=0o600,
        )
        try:
            snapshot = CanonicalBundleCodec().snapshot(
                FilesystemCanonicalMemoryStore(self.root)
            )
        except (OSError, ValueError) as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "Recovered filesystem memory cannot be verified",
                diagnostic=str(exc),
            ) from exc
        if (
            snapshot.project_uuid != marker.source_project_uuid
            or snapshot.semantic_state_digest != marker.source_semantic_state_digest
        ):
            raise ProjectStorageError(
                ProjectStorageErrorCode.identity_mismatch,
                "Recovered filesystem memory disagrees with activation source",
            )

    def _write_completion(
        self,
        marker: _RecoveryMarker,
        result: MemoryRecoveryResult,
    ) -> MemoryRecoveryResult | None:
        path = self._completion_path(marker.recovery_id)
        _assert_no_symlink_components(self.root, path.parent)
        if _is_link_or_reparse_point(path):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite recovery completion path is unsafe",
            )
        payload = {
            "contract": SQLITE_RECOVERY_COMPLETION_CONTRACT,
            "marker_sha256": marker.raw_sha256,
            "recovery_token": marker.recovery_token,
            "completed_at": _utc_now(),
            "result": result.to_dict(),
        }
        encoded = canonical_json_bytes(payload)
        if path.exists():
            try:
                existing = _read_json_mapping(
                    path,
                    max_bytes=_MAX_MARKER_BYTES,
                    root=self.root,
                )
                _validate_completion(existing, marker.recovery_id)
                stored = _result_from_completion(existing, replayed=False)
                matches = (
                    hmac.compare_digest(
                        str(existing.get("marker_sha256") or ""),
                        marker.raw_sha256,
                    )
                    and hmac.compare_digest(
                        str(existing.get("recovery_token") or ""),
                        marker.recovery_token,
                    )
                    and stored.status == result.status
                    and stored.operation == result.operation
                    and stored.action == result.action
                    and stored.project_uuid == result.project_uuid
                    and stored.semantic_state_digest
                    == result.semantic_state_digest
                    and stored.message == result.message
                )
            except (OSError, ValueError, ProjectStorageError):
                matches = False
                stored = None
            if matches and stored is not None and stored.actor != result.actor:
                try:
                    if marker.operation == "initial-activation":
                        self._authorize_activation_owner(marker, stored.actor)
                    else:
                        self._authorize_database_owner(
                            self.live_database,
                            stored.actor,
                        )
                except ProjectStorageError:
                    matches = False
            if matches:
                assert stored is not None
                return stored
            # The active, owner-authorized marker and the verified rollback are
            # authoritative. Preserve conflicting/pre-created local evidence
            # for diagnosis, but never let it permanently fence the project.
            self._quarantine_completion(path, marker.recovery_id)
        write_bytes_atomic(path, encoded, mode=0o600)
        return None

    def _quarantine_completion(self, path: Path, recovery_id: str) -> None:
        quarantine = path.parent / "quarantine"
        _assert_no_symlink_components(self.root, path.parent)
        _assert_no_symlink_components(self.root, quarantine)
        quarantine.mkdir(parents=True, exist_ok=True)
        _assert_no_symlink_components(self.root, quarantine)
        target = quarantine / f"{recovery_id}-{uuid4().hex}.invalid"
        _assert_no_symlink_components(self.root, target.parent)
        os.replace(path, target)
        sync_directory(quarantine)
        sync_directory(path.parent)

    def _completion_replay(
        self,
        *,
        recovery_id: str,
        recovery_token: str,
        actor: str,
        expected_marker_sha256: str = "",
        allow_owner_handoff: bool = False,
    ) -> MemoryRecoveryResult | None:
        path = self._completion_path(recovery_id)
        if _is_link_or_reparse_point(path):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite recovery completion path is unsafe",
            )
        if not path.exists():
            return None
        payload = _read_json_mapping(
            path,
            max_bytes=_MAX_MARKER_BYTES,
            root=self.root,
        )
        _validate_completion(payload, recovery_id)
        token = str(payload.get("recovery_token") or "")
        marker_sha256 = str(payload.get("marker_sha256") or "")
        result = _result_from_completion(payload, replayed=True)
        if (
            not hmac.compare_digest(token, recovery_token)
            or (
                expected_marker_sha256
                and not hmac.compare_digest(
                    marker_sha256,
                    expected_marker_sha256,
                )
            )
        ):
            raise ProjectStorageError(
                ProjectStorageErrorCode.idempotency_conflict,
                "SQLite recovery completion belongs to a different request",
            )
        if allow_owner_handoff:
            # A completion preserves the historical actor for audit, but every
            # replay must still be authorized against the current source state.
            # This covers both an owner handoff and revocation of the original
            # actor after the maintenance operation completed.
            if result.operation == "initial-activation":
                self._authorize_filesystem_owner(actor)
            else:
                self._authorize_database_owner(self.live_database, actor)
        elif result.actor != actor:
            raise ProjectStorageError(
                ProjectStorageErrorCode.idempotency_conflict,
                "SQLite recovery completion belongs to a different request",
            )
        return result

    def _finalize(self, marker: _RecoveryMarker) -> None:
        """Idempotently remove only artifacts owned by a completed rollback."""
        self._cleanup(marker)
        self._release_stale_workspace_lock(marker)
        marker.path.unlink(missing_ok=True)
        sync_directory(marker.path.parent)

    def _completion_path(self, recovery_id: str) -> Path:
        return self.root / SQLITE_RECOVERY_COMPLETION_ROOT / f"{recovery_id}.json"

    def _cleanup(self, marker: _RecoveryMarker) -> None:
        paths: list[Path] = []
        if marker.stage is not None:
            paths.append(marker.stage)
        if marker.recovery is not None and marker.recovery != self.live_database:
            paths.append(marker.recovery)
        if marker.auxiliary_backup is not None:
            paths.append(marker.auxiliary_backup)
        if marker.database_stage is not None:
            paths.append(marker.database_stage)
        if marker.canonical_stage is not None:
            # The writer records the canonical payload directory; its parent is
            # the operation-owned activation stage when named ``canonical``.
            paths.append(
                marker.canonical_stage.parent
                if marker.canonical_stage.name == "canonical"
                else marker.canonical_stage
            )
        seen: set[Path] = set()
        for path in paths:
            if path in seen or path == self.live_database:
                continue
            seen.add(path)
            _remove_recovery_artifact(self.root, path)

    def _release_stale_workspace_lock(self, marker: _RecoveryMarker) -> None:
        if not marker.transaction_id:
            return
        service = WorkspaceTransactionLockService(
            root=self.root,
            p2p_dir=self.root / ".p2p",
        )
        status = service.status()
        if (
            status.state == LOCK_STALE
            and status.transaction_id == marker.transaction_id
        ):
            service.release(marker.transaction_id)

    def _ensure_writer_is_not_active(self, marker: _RecoveryMarker) -> None:
        if not marker.transaction_id:
            return
        status = WorkspaceTransactionLockService(
            root=self.root,
            p2p_dir=self.root / ".p2p",
        ).status()
        if status.state == LOCK_ABSENT:
            return
        if status.state == LOCK_INVALID:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite recovery found an invalid workspace transaction lock",
            )
        if status.transaction_id != marker.transaction_id:
            raise ProjectStorageError(
                ProjectStorageErrorCode.busy,
                "Another workspace transaction owns the project during SQLite recovery",
            )
        if status.state in {LOCK_ACTIVE, LOCK_RECOVERY_OWNED}:
            raise ProjectStorageError(
                ProjectStorageErrorCode.busy,
                "SQLite maintenance writer is still active",
            )
        if status.state != LOCK_STALE:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite recovery found an unsupported workspace lock state",
            )


class _RecoveryClaim:
    def __init__(self, root: Path, recovery_id: str) -> None:
        self.root = root
        self.path = root / _RECOVERY_LOCK
        self.recovery_id = recovery_id
        self.owned = False

    def __enter__(self) -> _RecoveryClaim:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(2):
            candidate = self.path.with_name(
                f".{self.path.name}.{os.getpid()}.{uuid4().hex}.stage"
            )
            try:
                candidate.mkdir(mode=0o700)
                write_bytes_atomic(
                    candidate / "owner.json",
                    canonical_json_bytes(
                        {
                            "contract": "p2p-sqlite-recovery-claim/v2",
                            "recovery_id": self.recovery_id,
                            "pid": os.getpid(),
                        }
                    ),
                    mode=0o600,
                )
                sync_directory(candidate)
                os.rename(candidate, self.path)
            except OSError as exc:
                if candidate.exists() and not candidate.is_symlink():
                    shutil.rmtree(candidate, ignore_errors=True)
                if attempt == 0 and self.path.exists() and _remove_stale_claim(
                    self.path
                ):
                    continue
                raise ProjectStorageError(
                    ProjectStorageErrorCode.busy,
                    "Another SQLite recovery process owns the rollback claim",
                ) from exc
            sync_directory(self.path.parent)
            self.owned = True
            return self
        raise AssertionError("unreachable")

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.owned:
            owner = _read_recovery_claim(self.path)
            if owner != (os.getpid(), self.recovery_id):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite recovery claim ownership changed unexpectedly",
                )
            _retire_recovery_claim(self.path, self.recovery_id)
            self.owned = False


def _parse_v2_marker(
    root: Path,
    path: Path,
    raw: bytes,
    payload: Mapping[str, object],
) -> _RecoveryMarker:
    contract = str(payload.get("contract") or "")
    expected_operation = {
        SQLITE_MAINTENANCE_CONTRACT: {
            "restore",
            "identity-transition",
            "schema-migration",
        },
        SQLITE_ACTIVATION_CONTRACT: {"initial-activation"},
    }.get(contract)
    if expected_operation is None:
        raise ValueError("unsupported SQLite maintenance marker contract")
    operation = _label(payload.get("operation"), "operation")
    if operation not in expected_operation:
        raise ValueError("SQLite maintenance operation disagrees with its contract")
    phase = _label(payload.get("phase"), "phase")
    if phase not in _OPERATION_PHASES[operation]:
        raise ValueError("SQLite maintenance phase is invalid for its operation")
    actor = str(payload.get("actor") or "").strip()
    if not actor or len(actor) > 512:
        raise ValueError("SQLite maintenance marker actor is invalid")
    source_uuid, source_digest = _state_ref(payload.get("source"), "source")
    target_uuid, target_digest = _state_ref(payload.get("target"), "target")
    recovery_id = _uuid(str(payload.get("recovery_id") or ""), "recovery_id")
    recovery_token = _sha256(
        str(payload.get("recovery_token") or ""),
        "recovery_token",
    )
    transaction_id = str(payload.get("transaction_id") or "").strip()
    if not transaction_id or len(transaction_id) > 512:
        raise ValueError("SQLite maintenance transaction ID is missing or too long")
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    if contract == SQLITE_MAINTENANCE_CONTRACT:
        stage = _safe_relative_path(
            root,
            str(payload.get("stage") or ""),
            prefixes=(".p2p/local/",),
        )
        recovery = _safe_relative_path(
            root,
            str(payload.get("recovery") or ""),
            prefixes=(".p2p/backups/", ".p2p/local/"),
        )
        auxiliary_raw = str(payload.get("auxiliary_backup") or "").strip()
        auxiliary = (
            _safe_relative_path(
                root,
                auxiliary_raw,
                prefixes=(".p2p/backups/",),
            )
            if auxiliary_raw
            else None
        )
        auxiliary_remove_raw = payload.get("auxiliary_remove", [])
        if not isinstance(auxiliary_remove_raw, list):
            raise ValueError("SQLite identity auxiliary removal inventory is invalid")
        auxiliary_remove = _parse_auxiliary_inventory(
            root,
            auxiliary_remove_raw,
            label="removal",
        )
        auxiliary_source_raw = payload.get("auxiliary_source", [])
        if not isinstance(auxiliary_source_raw, list):
            raise ValueError("SQLite identity auxiliary source inventory is invalid")
        auxiliary_source = _parse_auxiliary_inventory(
            root,
            auxiliary_source_raw,
            label="source",
        )
        auxiliary_target_raw = payload.get("auxiliary_target", [])
        if not isinstance(auxiliary_target_raw, list):
            raise ValueError("SQLite identity auxiliary target inventory is invalid")
        auxiliary_target = _parse_auxiliary_inventory(
            root,
            auxiliary_target_raw,
            label="target",
        )
        if operation == "identity-transition" and not {
            "auxiliary_backup",
            "auxiliary_remove",
            "auxiliary_source",
            "auxiliary_target",
        }.issubset(payload):
            raise ValueError("SQLite identity marker lacks auxiliary inventories")
        if operation == "identity-transition":
            source_by_path = {
                path: (digest, size) for path, digest, size in auxiliary_source
            }
            target_by_path = {
                path: (digest, size) for path, digest, size in auxiliary_target
            }
            removal_by_path = {
                path: (digest, size) for path, digest, size in auxiliary_remove
            }
            expected_removals = {
                path: value
                for path, value in target_by_path.items()
                if path not in source_by_path
            }
            if removal_by_path != expected_removals:
                raise ValueError("SQLite identity auxiliary inventories disagree")
        blob_changes_raw = payload.get("blob_changes", [])
        if not isinstance(blob_changes_raw, list):
            raise ValueError("SQLite restore blob change inventory is invalid")
        blob_changes: list[tuple[Path, str, bool]] = []
        blob_seen: set[Path] = set()
        for item in blob_changes_raw:
            if not isinstance(item, Mapping) or set(item) != {
                "path",
                "digest",
                "existed_before",
            }:
                raise ValueError("SQLite restore blob change fields are invalid")
            blob_path = _safe_relative_path(
                root,
                str(item.get("path") or ""),
                prefixes=(".p2p/blobs/sha256/",),
            )
            raw_digest = str(item.get("digest") or "")
            if not raw_digest.startswith("sha256:"):
                raise ValueError("SQLite restore blob digest is invalid")
            _sha256(raw_digest.removeprefix("sha256:"), "blob digest")
            if blob_path.name != raw_digest.removeprefix("sha256:"):
                raise ValueError("SQLite restore blob path disagrees with its digest")
            blob_sha256 = raw_digest.removeprefix("sha256:")
            expected_blob_path = (
                f".p2p/blobs/sha256/{blob_sha256[:2]}/{blob_sha256}"
            )
            if blob_path.relative_to(root).as_posix() != expected_blob_path:
                raise ValueError("SQLite restore blob path is not canonical")
            existed_before = item.get("existed_before")
            if not isinstance(existed_before, bool):
                raise ValueError("SQLite restore blob prior-existence flag is invalid")
            if blob_path in blob_seen:
                raise ValueError("SQLite restore blob path is duplicated")
            blob_seen.add(blob_path)
            blob_changes.append((blob_path, raw_digest, existed_before))
        if "blob_changes" not in payload:
            raise ValueError("SQLite maintenance marker lacks its blob change inventory")
        source_schema_version: int | None = None
        target_schema_version: int | None = None
        if operation == "schema-migration":
            source_schema_version = _schema_version(
                payload.get("source_schema_version"),
                "source_schema_version",
            )
            target_schema_version = _schema_version(
                payload.get("target_schema_version"),
                "target_schema_version",
            )
            if source_schema_version >= target_schema_version:
                raise ValueError("SQLite migration schema version range is invalid")
            if source_uuid != target_uuid or source_digest != target_digest:
                raise ValueError("SQLite schema migration cannot change semantic state")
        elif "source_schema_version" in payload or "target_schema_version" in payload:
            raise ValueError("non-migration marker contains schema migration fields")
        if operation != "identity-transition" and (
            auxiliary
            or auxiliary_remove
            or auxiliary_source
            or auxiliary_target
            or any(
                key in payload
                for key in (
                    "auxiliary_backup",
                    "auxiliary_remove",
                    "auxiliary_source",
                    "auxiliary_target",
                )
            )
        ):
            raise ValueError("SQLite maintenance marker contains identity auxiliary state")
        expected_stage, expected_recovery = {
            "restore": (
                root / f".p2p/local/sqlite-restore-{recovery_id}.stage",
                root / f".p2p/backups/sqlite-recovery-{recovery_id}.sqlite3",
            ),
            "identity-transition": (
                root / f".p2p/local/sqlite-identity-{recovery_id}.stage",
                root / f".p2p/backups/sqlite-pre-identity-{recovery_id}.sqlite3",
            ),
            "schema-migration": (
                root / f".p2p/local/sqlite-migration-{recovery_id}.stage",
                root / f".p2p/backups/sqlite-migration-{recovery_id}.sqlite3",
            ),
        }[operation]
        if stage != expected_stage or recovery != expected_recovery:
            raise ValueError(
                "SQLite maintenance paths are not owned by this recovery identifier"
            )
        if operation == "identity-transition" and auxiliary != (
            root / f".p2p/backups/sqlite-pre-identity-{recovery_id}.aux"
        ):
            raise ValueError(
                "SQLite auxiliary backup is not owned by this recovery identifier"
            )
        return _RecoveryMarker(
            path=path,
            contract=contract,
            raw_sha256=raw_sha256,
            recovery_id=recovery_id,
            recovery_token=recovery_token,
            operation=operation,
            phase=phase,
            actor=actor,
            source_project_uuid=source_uuid,
            source_semantic_state_digest=source_digest,
            target_project_uuid=target_uuid,
            target_semantic_state_digest=target_digest,
            source_schema_version=source_schema_version,
            target_schema_version=target_schema_version,
            stage=stage,
            recovery=recovery,
            auxiliary_backup=auxiliary,
            blob_changes=tuple(blob_changes),
            auxiliary_remove=tuple(auxiliary_remove),
            auxiliary_source=tuple(auxiliary_source),
            auxiliary_target=tuple(auxiliary_target),
            transaction_id=transaction_id,
        )
    database_stage = _safe_relative_path(
        root,
        str(payload.get("database_stage") or ""),
        prefixes=(".p2p/local/",),
    )
    canonical_stage = _safe_relative_path(
        root,
        str(payload.get("canonical_stage") or ""),
        prefixes=(".p2p/local/",),
    )
    activation_root = root / f".p2p/local/sqlite-activation-{recovery_id}.stage"
    if (
        database_stage != activation_root / "project.sqlite3"
        or canonical_stage != activation_root / "canonical"
    ):
        raise ValueError(
            "SQLite activation paths are not owned by this recovery identifier"
        )
    detached_raw = payload.get("detached")
    if not isinstance(detached_raw, list) or not detached_raw:
        raise ValueError("SQLite activation marker detached inventory is invalid")
    detached: list[tuple[Path, str]] = []
    seen: set[Path] = set()
    for item in detached_raw:
        if not isinstance(item, Mapping) or set(item) != {"path", "sha256"}:
            raise ValueError("SQLite activation detached entry fields are invalid")
        relative_target = _safe_activation_detached_path(
            root,
            str(item.get("path") or ""),
        )
        relative = relative_target.relative_to(root)
        if relative in seen or relative.as_posix() in {
            SQLITE_DATABASE_PATH,
            SQLITE_MAINTENANCE_MARKER,
            SQLITE_ACTIVATION_MARKER,
        }:
            raise ValueError("SQLite activation detached path is duplicated or reserved")
        seen.add(relative)
        detached.append((relative, _sha256(str(item.get("sha256") or ""), "sha256")))
    return _RecoveryMarker(
        path=path,
        contract=contract,
        raw_sha256=raw_sha256,
        recovery_id=recovery_id,
        recovery_token=recovery_token,
        operation=operation,
        phase=phase,
        actor=actor,
        source_project_uuid=source_uuid,
        source_semantic_state_digest=source_digest,
        target_project_uuid=target_uuid,
        target_semantic_state_digest=target_digest,
        database_stage=database_stage,
        canonical_stage=canonical_stage,
        detached=tuple(detached),
        transaction_id=transaction_id,
    )


def _legacy_status(
    root: Path,
    path: Path,
    payload: Mapping[str, object],
) -> MemoryRecoveryStatus:
    contract = str(payload.get("contract") or "")
    stage_key = "stage" if contract == "p2p-sqlite-maintenance/v1" else "canonical_stage"
    recovery_key = "recovery" if contract == "p2p-sqlite-maintenance/v1" else ""
    staging = ""
    recovery = ""
    try:
        raw_stage = str(payload.get(stage_key) or "")
        if raw_stage:
            staging = str(
                _safe_relative_path(root, raw_stage, prefixes=(".p2p/",))
            )
        raw_recovery = str(payload.get(recovery_key) or "") if recovery_key else ""
        if raw_recovery:
            recovery = str(
                _safe_relative_path(root, raw_recovery, prefixes=(".p2p/",))
            )
    except (ValueError, ProjectStorageError) as exc:
        raise ValueError(f"legacy SQLite marker paths are invalid: {exc}") from exc
    return MemoryRecoveryStatus(
        state="recovery_required",
        marker=str(path),
        staging_path=staging,
        recovery_path=recovery,
        operation=str(payload.get("operation") or ""),
        applicable=False,
        marker_contract=contract,
        message=(
            "Legacy SQLite maintenance is visible for diagnosis but cannot be "
            "applied automatically."
        ),
    )


def _read_marker_payload(root: Path, path: Path) -> tuple[bytes, Mapping[str, object]]:
    _assert_no_symlink_components(root, path)
    if not path.is_file():
        raise ValueError("SQLite maintenance marker is not a safe regular file")
    if path.stat().st_size > _MAX_MARKER_BYTES:
        raise ValueError("SQLite maintenance marker exceeds its safe size")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("SQLite maintenance marker is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("SQLite maintenance marker is not a JSON object")
    return raw, payload


def _state_ref(value: object, label: str) -> tuple[str, str]:
    if not isinstance(value, Mapping) or set(value) != {
        "project_uuid",
        "semantic_state_digest",
    }:
        raise ValueError(f"SQLite maintenance {label} fields are invalid")
    return (
        _uuid(str(value.get("project_uuid") or ""), f"{label}.project_uuid"),
        _sha256(
            str(value.get("semantic_state_digest") or ""),
            f"{label}.semantic_state_digest",
        ),
    )


def _uuid(value: str, label: str) -> str:
    try:
        normalized = str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"SQLite maintenance {label} is not a UUID") from exc
    if normalized != value:
        raise ValueError(f"SQLite maintenance {label} is not canonical")
    return normalized


def _sha256(value: str, label: str) -> str:
    if not _SHA256.fullmatch(value):
        raise ValueError(f"SQLite maintenance {label} is not a SHA-256 value")
    return value


def _label(value: object, label: str) -> str:
    normalized = str(value or "").strip()
    if not _SAFE_LABEL.fullmatch(normalized):
        raise ValueError(f"SQLite maintenance {label} is invalid")
    return normalized


def _schema_version(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"SQLite maintenance {label} is invalid")
    return value


def _safe_relative_path(
    root: Path,
    value: str,
    *,
    prefixes: tuple[str, ...],
) -> Path:
    if not value or "\\" in value or "\x00" in value:
        raise ValueError("SQLite recovery path is empty or ambiguous")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or not pure.parts
        or pure.as_posix() != value
        or any(part in {"", ".", ".."} for part in pure.parts)
        or any(_ambiguous_windows_path_component(part) for part in pure.parts)
    ):
        raise ValueError("SQLite recovery path is not a safe relative path")
    relative = pure.as_posix()
    matches = False
    for prefix in prefixes:
        if prefix.endswith("/"):
            matches = matches or relative.startswith(prefix)
        else:
            matches = matches or relative == prefix
    if not matches:
        raise ValueError("SQLite recovery path is outside its allowed project area")
    candidate = root / relative
    if not candidate.resolve(strict=False).is_relative_to(root):
        raise ValueError("SQLite recovery path escapes the project root")
    _assert_no_symlink_components(root, candidate)
    return candidate


def _ambiguous_windows_path_component(value: str) -> bool:
    """Reject marker paths that can alias another Win32 path or an NTFS ADS."""

    if value.endswith((" ", ".")):
        return True
    if any(ord(character) < 32 or character in '<>:"|?*' for character in value):
        return True
    basename = value.split(".", 1)[0].casefold()
    reserved = {"con", "prn", "aux", "nul", "conin$", "conout$"}
    reserved.update(f"com{index}" for index in range(1, 10))
    reserved.update(f"lpt{index}" for index in range(1, 10))
    reserved.update(f"com{index}" for index in "¹²³")
    reserved.update(f"lpt{index}" for index in "¹²³")
    return basename in reserved


def _safe_auxiliary_path(root: Path, value: str) -> Path:
    exact = {
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        "P2P-SETUP.md",
        ".github/copilot-instructions.md",
    }
    if value in exact:
        return _safe_relative_path(root, value, prefixes=(value,))
    if value.startswith((".agents/", ".cursor/")):
        return _safe_relative_path(root, value, prefixes=(".agents/", ".cursor/"))
    target = _safe_relative_path(root, value, prefixes=(".p2p/",))
    relative_p2p = target.relative_to(root / ".p2p").as_posix()
    classification, _kind, _reason = classify_memory_path(relative_p2p)
    if classification not in {
        "integration_artifact",
        "replica_local",
        "derived_projection",
        "personal_configuration",
        "external_material",
    }:
        raise ValueError("SQLite recovery auxiliary path is not auxiliary state")
    relative = target.relative_to(root).as_posix()
    folded = relative.casefold()
    reserved_exact = {
        SQLITE_DATABASE_PATH.casefold(),
        SQLITE_MAINTENANCE_MARKER.casefold(),
        SQLITE_ACTIVATION_MARKER.casefold(),
        ProjectStorageManifestStore(root)
        .path.relative_to(root)
        .as_posix()
        .casefold(),
    }
    if (
        folded in reserved_exact
        or folded.startswith(f"{SQLITE_DATABASE_PATH.casefold()}-")
        or folded.startswith(".p2p/local/sqlite-")
        or folded.startswith(
            f"{SQLITE_RECOVERY_COMPLETION_ROOT.as_posix().casefold()}/"
        )
    ):
        raise ValueError("SQLite recovery auxiliary path is reserved")
    return target


def _safe_activation_detached_path(root: Path, value: str) -> Path:
    target = _safe_relative_path(root, value, prefixes=(".p2p/",))
    relative = target.relative_to(root).as_posix()
    relative_p2p = target.relative_to(root / ".p2p").as_posix()
    classification, _kind, _reason = classify_memory_path(relative_p2p)
    receipt_pattern = rf"{re.escape(MUTATION_RECEIPT_ROOT)}/[0-9a-f]{{64}}\.yml"
    if classification != "canonical_project" and not re.fullmatch(
        receipt_pattern,
        relative,
    ):
        raise ValueError(
            "SQLite activation detached path is not canonical project state"
        )
    return target


def _parse_auxiliary_inventory(
    root: Path,
    raw: list[object],
    *,
    label: str,
) -> list[tuple[Path, str, int]]:
    inventory: list[tuple[Path, str, int]] = []
    seen: set[Path] = set()
    for item in raw:
        if not isinstance(item, Mapping) or set(item) != {"path", "sha256", "size"}:
            raise ValueError(f"SQLite identity auxiliary {label} entry is invalid")
        path = _safe_auxiliary_path(root, str(item.get("path") or ""))
        size = item.get("size")
        if path in seen:
            raise ValueError(f"SQLite identity auxiliary {label} path is duplicated")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError(f"SQLite identity auxiliary {label} size is invalid")
        seen.add(path)
        inventory.append(
            (
                path,
                _sha256(str(item.get("sha256") or ""), f"auxiliary {label} sha256"),
                size,
            )
        )
    return inventory


def _assert_no_symlink_components(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery path escapes the project root",
        ) from exc
    current = root
    for part in relative.parts:
        current /= part
        if _is_link_or_reparse_point(current) or _path_escapes_root(root, current):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite recovery path contains a symlink, junction or reparse point",
                diagnostic=relative.as_posix(),
            )


def _is_link_or_reparse_point(path: Path) -> bool:
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


def _assert_safe_regular_file(root: Path, path: Path) -> None:
    _assert_no_symlink_components(root, path)
    if not path.is_file():
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery artifact is missing or not a regular file",
            diagnostic=str(path),
        )


def _regular_file_digest(root: Path, path: Path) -> str:
    # Validate parents even when the leaf is absent. Otherwise a missing leaf
    # below a symlink/junction could be treated as a harmless absence and later
    # restored outside the project root.
    _assert_no_symlink_components(root, path)
    if not path.exists():
        return ""
    _assert_safe_regular_file(root, path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _set_database_ready(path: Path) -> None:
    factory = SQLiteConnectionFactory(path)
    with factory.connect(writable=True) as connection:
        validate_sqlite_header(connection)
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = connection.execute(
                "SELECT count(*) FROM storage_metadata WHERE singleton = 1"
            ).fetchone()
            if row is None or int(row[0]) != 1:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite recovery metadata is missing",
                )
            connection.execute(
                "UPDATE storage_metadata SET maintenance_state = 'ready' WHERE singleton = 1"
            )
            connection.execute("COMMIT")
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise


def _remove_sqlite_sidecars(path: Path) -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = path.with_name(path.name + suffix)
        if sidecar.exists() or _is_link_or_reparse_point(sidecar):
            if _is_link_or_reparse_point(sidecar) or not sidecar.is_file():
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite recovery sidecar is unsafe",
                    diagnostic=str(sidecar),
                )
            sidecar.unlink()


def _read_auxiliary_backup(root: Path, backup: Path) -> dict[Path, bytes]:
    _assert_no_symlink_components(root, backup)
    if not backup.is_dir():
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary recovery backup is missing",
        )
    manifest = _read_json_mapping(
        backup / "manifest.json",
        max_bytes=_MAX_MARKER_BYTES,
        root=backup,
    )
    if manifest.get("contract") != SQLITE_AUXILIARY_BACKUP_CONTRACT:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary recovery backup contract is unsupported",
        )
    raw_entries = manifest.get("files")
    if not isinstance(raw_entries, list) or len(raw_entries) > _MAX_AUXILIARY_FILES:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary recovery manifest is invalid",
        )
    prepared: dict[Path, bytes] = {}
    total = 0
    seen: set[Path] = set()
    for item in raw_entries:
        if not isinstance(item, Mapping) or set(item) != {
            "path",
            "stored_path",
            "sha256",
            "size",
        }:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite auxiliary recovery entry fields are invalid",
            )
        target = _safe_auxiliary_path(root, str(item.get("path") or ""))
        if target in seen:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite auxiliary recovery path is duplicated",
            )
        seen.add(target)
        stored = _safe_backup_payload_path(backup, str(item.get("stored_path") or ""))
        _assert_safe_regular_file(backup, stored)
        content = stored.read_bytes()
        size = item.get("size")
        digest = str(item.get("sha256") or "")
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size != len(content)
            or not _SHA256.fullmatch(digest)
            or hashlib.sha256(content).hexdigest() != digest
        ):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite auxiliary recovery payload failed verification",
            )
        total += len(content)
        if total > _MAX_AUXILIARY_BYTES:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite auxiliary recovery payload exceeds its safe size",
            )
        prepared[target] = content
    return prepared


def _verify_auxiliary_rollback_inputs(
    root: Path,
    backup: Path,
    expected_source_inventory: tuple[tuple[Path, str, int], ...],
    target_inventory: tuple[tuple[Path, str, int], ...],
) -> None:
    source_payloads = _read_auxiliary_backup(root, backup)
    source_inventory = {
        path: (hashlib.sha256(content).hexdigest(), len(content))
        for path, content in source_payloads.items()
    }
    expected_source = {
        path: (digest, size)
        for path, digest, size in expected_source_inventory
    }
    if source_inventory != expected_source:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite identity recovery backup disagrees with its source inventory",
        )
    target_by_path = {
        path: (digest, size) for path, digest, size in target_inventory
    }
    for path in sorted(source_inventory.keys() | target_by_path.keys()):
        if not path.exists() and not _is_link_or_reparse_point(path):
            continue
        _assert_safe_regular_file(root, path)
        content = path.read_bytes()
        observed = (hashlib.sha256(content).hexdigest(), len(content))
        allowed = {
            item
            for item in (source_inventory.get(path), target_by_path.get(path))
            if item is not None
        }
        if observed not in allowed:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite identity recovery found changed auxiliary state",
                diagnostic=str(path),
            )


def _verify_auxiliary_source_state(
    root: Path,
    source_inventory: tuple[tuple[Path, str, int], ...],
    removal_inventory: tuple[tuple[Path, str, int], ...],
) -> None:
    source_paths = {path for path, _digest, _size in source_inventory}
    for path, digest, size in source_inventory:
        _assert_safe_regular_file(root, path)
        content = path.read_bytes()
        if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite identity recovery did not restore its source auxiliary state",
                diagnostic=str(path),
            )
    for path, _digest, _size in removal_inventory:
        if path in source_paths:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite identity recovery auxiliary inventories overlap",
                diagnostic=str(path),
            )
        if path.exists() or _is_link_or_reparse_point(path):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite identity recovery left target-only auxiliary state behind",
                diagnostic=str(path),
            )


def _restore_auxiliary_backup(root: Path, backup: Path) -> None:
    for target, content in _read_auxiliary_backup(root, backup).items():
        _assert_no_symlink_components(root, target.parent)
        write_bytes_atomic(target, content, mode=0o600)


def _safe_backup_payload_path(backup: Path, value: str) -> Path:
    if not value.startswith("payload/") or "\\" in value:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary recovery payload path is invalid",
        )
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary recovery payload path is unsafe",
        )
    candidate = backup / pure.as_posix()
    if not candidate.resolve(strict=False).is_relative_to(backup.resolve()):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite auxiliary recovery payload escapes its archive",
        )
    return candidate


def _read_json_mapping(
    path: Path,
    *,
    max_bytes: int,
    root: Path | None = None,
) -> Mapping[str, object]:
    if root is not None:
        _assert_no_symlink_components(root, path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery JSON artifact is missing or unsafe",
        )
    try:
        payload = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery JSON artifact is invalid",
            diagnostic=str(exc),
        ) from exc
    if not isinstance(payload, Mapping):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery JSON artifact is not an object",
        )
    return payload


def _validate_completion(payload: Mapping[str, object], recovery_id: str) -> None:
    if set(payload) != {
        "contract",
        "marker_sha256",
        "recovery_token",
        "completed_at",
        "result",
    } or payload.get("contract") != SQLITE_RECOVERY_COMPLETION_CONTRACT:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery completion contract is unsupported",
        )
    result = payload.get("result")
    if (
        not isinstance(result, Mapping)
        or set(result)
        != {
            "contract",
            "status",
            "recovery_id",
            "operation",
            "action",
            "actor",
            "project_uuid",
            "semantic_state_digest",
            "replayed",
            "message",
        }
        or result.get("contract") != "p2p-memory-recovery-result/v1"
        or result.get("recovery_id") != recovery_id
        or result.get("status") != "rolled_back"
        or result.get("operation") not in _OPERATION_PHASES
        or result.get("action") != "rollback"
        or not isinstance(result.get("actor"), str)
        or str(result.get("actor") or "")
        != str(result.get("actor") or "").strip()
        or not str(result.get("actor") or "")
        or len(str(result.get("actor") or "")) > 512
        or result.get("replayed") is not False
        or not isinstance(result.get("message"), str)
        or len(str(result.get("message") or "")) > 4096
        or not _SHA256.fullmatch(str(payload.get("recovery_token") or ""))
        or not _SHA256.fullmatch(str(payload.get("marker_sha256") or ""))
    ):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery completion fields are invalid",
        )
    try:
        if identity_slug(str(result.get("actor") or "")) != result.get("actor"):
            raise ValueError("completion actor is not canonical")
        _uuid(str(result.get("project_uuid") or ""), "project_uuid")
        _sha256(
            str(result.get("semantic_state_digest") or ""),
            "semantic_state_digest",
        )
        completed_at = str(payload.get("completed_at") or "")
        completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        if not completed_at.endswith("Z") or completed.tzinfo is None:
            raise ValueError("completion timestamp is not UTC")
    except ValueError as exc:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery completion fields are invalid",
            diagnostic=str(exc),
        ) from exc


def _result_from_completion(
    payload: Mapping[str, object],
    *,
    replayed: bool,
) -> MemoryRecoveryResult:
    raw = payload.get("result")
    assert isinstance(raw, Mapping)
    return MemoryRecoveryResult(
        status=str(raw.get("status") or ""),
        recovery_id=str(raw.get("recovery_id") or ""),
        operation=str(raw.get("operation") or ""),
        action=str(raw.get("action") or ""),
        actor=str(raw.get("actor") or ""),
        project_uuid=_uuid(str(raw.get("project_uuid") or ""), "project_uuid"),
        semantic_state_digest=_sha256(
            str(raw.get("semantic_state_digest") or ""),
            "semantic_state_digest",
        ),
        replayed=replayed,
        message=str(raw.get("message") or ""),
    )


def _remove_recovery_artifact(root: Path, path: Path) -> None:
    _assert_no_symlink_components(root, path)
    if not path.exists() and not _is_link_or_reparse_point(path):
        return
    if _is_link_or_reparse_point(path):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery cleanup refuses a symlink, junction or reparse point",
        )
    if path.is_dir():
        shutil.rmtree(path)
    elif path.is_file():
        path.unlink()
        _remove_sqlite_sidecars(path)
    else:
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery cleanup artifact is unsafe",
        )


def _read_recovery_claim(path: Path) -> tuple[int, str]:
    if _is_link_or_reparse_point(path) or not path.is_dir():
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery claim is not a safe directory",
        )
    payload = _read_json_mapping(
        path / "owner.json",
        max_bytes=4096,
        root=path,
    )
    pid = payload.get("pid")
    recovery_id = str(payload.get("recovery_id") or "")
    if (
        payload.get("contract") != "p2p-sqlite-recovery-claim/v2"
        or isinstance(pid, bool)
        or not isinstance(pid, int)
        or pid < 1
    ):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite recovery claim metadata is invalid",
        )
    return pid, _uuid(recovery_id, "claim recovery_id")


def _remove_stale_claim(path: Path) -> bool:
    try:
        pid, recovery_id = _read_recovery_claim(path)
        try:
            running = pid_is_running(pid)
        except OSError:
            return False
        if not running:
            _retire_recovery_claim(path, recovery_id)
            return True
        return False
    except ProjectStorageError:
        return False


def _retire_recovery_claim(path: Path, recovery_id: str) -> None:
    """Free the global claim name before best-effort recursive cleanup."""
    tombstone = path.with_name(
        f".{path.name}.{recovery_id}.{uuid4().hex}.released"
    )
    os.rename(path, tombstone)
    sync_directory(path.parent)
    # A crash or cleanup failure can leave only an inert, uniquely named
    # tombstone; it cannot leave the globally contended name half-removed.
    shutil.rmtree(tombstone, ignore_errors=True)
    sync_directory(tombstone.parent)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

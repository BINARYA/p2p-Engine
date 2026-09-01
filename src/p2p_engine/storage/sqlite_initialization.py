from __future__ import annotations

import hashlib
import os
import shutil
import stat
from collections.abc import Mapping
from pathlib import Path

from p2p_engine.core.canonical_memory import CanonicalMemorySnapshot, canonical_json_bytes
from p2p_engine.core.mutation_receipts import MUTATION_RECEIPT_ROOT
from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    ProjectStorageError,
    ProjectStorageErrorCode,
    ProjectStorageManifest,
)
from p2p_engine.foundation.files import sync_directory, write_bytes_atomic
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.services.mutation_receipts import (
    parse_mutation_receipt,
    rebind_mutation_receipt_postconditions,
)
from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.workspace_transactions import WorkspaceTransactionLockService
from p2p_engine.storage.canonical_memory import FilesystemCanonicalMemoryStore
from p2p_engine.storage.project_storage import (
    PROJECT_STORAGE_MANIFEST_PATH,
    ProjectStorageManifestStore,
)
from p2p_engine.storage.sqlite_project_state import (
    SQLiteProjectStateRepository,
    SQLitePublicMutationRecord,
    create_sqlite_database,
    sqlite_public_mutation_record,
    sqlite_public_receipt_document_path,
)
from p2p_engine.storage.sqlite_recovery import new_sqlite_recovery_identity
from p2p_engine.storage.sqlite_schema import (
    SQLITE_ACTIVATION_MARKER,
    SQLITE_ADAPTER,
    SQLITE_DATABASE_PATH,
)


def _sync_directories(*directories: Path) -> bool:
    """Best-effort directory sync; False means the platform cannot promise it."""
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


def activate_sqlite_from_filesystem(root: Path, *, failure_injector=None) -> tuple[Path, ...]:
    """Atomically replace initialization staging files with authoritative SQLite state."""
    resolved = root.resolve()
    _assert_memory_tree_has_no_symlinks(resolved)
    recovery_id, recovery_token = new_sqlite_recovery_identity()
    transaction_id = f"sqlite-activation-{recovery_id}"
    lock = WorkspaceTransactionLockService(
        root=resolved,
        p2p_dir=resolved / ".p2p",
    )
    lock.acquire(transaction_id, owner="sqlite-activation")
    owns_lock = True
    snapshot: CanonicalMemorySnapshot | None = None
    local = resolved / ".p2p/local"
    local.mkdir(parents=True, exist_ok=True)
    stage_root = local / f"sqlite-activation-{recovery_id}.stage"
    stage_database = stage_root / "project.sqlite3"
    canonical_stage = stage_root / "canonical"
    marker = resolved / SQLITE_ACTIVATION_MARKER
    moved: list[tuple[Path, Path]] = []
    final_database = resolved / SQLITE_DATABASE_PATH
    activated = False
    owns_marker = False
    safe_to_clear_marker = False
    detached_paths: tuple[Path, ...] = ()
    try:
        manifest_store = ProjectStorageManifestStore(resolved)
        manifest = manifest_store.load()
        if manifest.adapter != SQLITE_ADAPTER:
            raise ProjectStorageError(
                ProjectStorageErrorCode.configuration_contradiction,
                "SQLite activation requires an explicit SQLite storage manifest",
            )
        if final_database.exists() or _is_link_or_reparse_point(final_database):
            raise ProjectStorageError(
                ProjectStorageErrorCode.configuration_contradiction,
                "SQLite activation refuses to overwrite an existing database",
            )
        filesystem = FilesystemCanonicalMemoryStore(resolved)
        codec = CanonicalBundleCodec()
        snapshot = codec.snapshot(filesystem)
        identity = filesystem.project_identity()
        if identity.project_uuid.value != manifest.project_uuid:
            raise ProjectStorageError(
                ProjectStorageErrorCode.identity_mismatch,
                "SQLite activation identity disagrees with its manifest",
            )
        inventory = filesystem.inventory()
        canonical_paths = tuple(
            resolved / artifact.locator
            for artifact in inventory.artifacts
            if artifact.classification == "canonical_project"
        )
        public_receipts, receipt_paths = _public_receipts_for_activation(
            resolved,
            filesystem=filesystem,
            snapshot=snapshot,
        )
        detached_paths = (*canonical_paths, *receipt_paths)
        detached: list[dict[str, str]] = []
        for path in detached_paths:
            if not _is_safe_regular_file(resolved, path):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite activation inventory contains an unsafe artifact",
                )
            detached.append(
                {
                    "path": path.relative_to(resolved).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        # Until the new DB has been verified and activated, the filesystem is
        # the recoverable authoritative source. This also makes a crash before
        # marker creation reopenable as a filesystem project.
        write_bytes_atomic(
            manifest_store.path,
            ProjectStorageManifestStore.render(
                ProjectStorageManifest(
                    project_uuid=snapshot.project_uuid,
                    adapter=FILESYSTEM_ADAPTER,
                )
            ),
            mode=0o600,
        )
        marker_payload: dict[str, object] = {
            "contract": "p2p-sqlite-activation/v2",
            "recovery_id": recovery_id,
            "recovery_token": recovery_token,
            "operation": "initial-activation",
            "phase": "prepared",
            "actor": _filesystem_owner(filesystem),
            "transaction_id": transaction_id,
            "source": {
                "project_uuid": snapshot.project_uuid,
                "semantic_state_digest": snapshot.semantic_state_digest,
            },
            "target": {
                "project_uuid": snapshot.project_uuid,
                "semantic_state_digest": snapshot.semantic_state_digest,
            },
            "database_stage": stage_database.relative_to(resolved).as_posix(),
            "canonical_stage": canonical_stage.relative_to(resolved).as_posix(),
            "detached": detached,
        }
        _write_activation_marker(marker, marker_payload)
        owns_marker = True
        stage_root.mkdir(parents=True, exist_ok=False)
        create_sqlite_database(
            stage_database,
            identity=identity,
            snapshot=snapshot,
            public_receipts=public_receipts,
            failure_injector=failure_injector,
        )
        staged = SQLiteProjectStateRepository(resolved, database_path=stage_database)
        issues = staged.integrity_check()
        if issues or staged.snapshot().semantic_state_digest != snapshot.semantic_state_digest:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "staged SQLite initialization failed verification",
                diagnostic="; ".join(issues),
            )
        _update_activation_marker(marker, marker_payload, phase="staged")
        if failure_injector is not None:
            failure_injector("after_sqlite_stage")
        for source in detached_paths:
            if not _is_safe_regular_file(resolved, source):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "canonical initialization staging contains an unsafe artifact",
            )
            target = canonical_stage / source.relative_to(resolved)
            target.parent.mkdir(parents=True, exist_ok=True)
            _replace_and_sync_directories(source, target)
            moved.append((source, target))
        _update_activation_marker(marker, marker_payload, phase="detached")
        if failure_injector is not None:
            failure_injector("after_canonical_detach")
        _replace_and_sync_directories(stage_database, final_database)
        activated = True
        _update_activation_marker(marker, marker_payload, phase="activated")
        if failure_injector is not None:
            failure_injector("after_sqlite_activation")
        active = SQLiteProjectStateRepository(resolved)
        issues = active.integrity_check()
        if issues or active.snapshot().semantic_state_digest != snapshot.semantic_state_digest:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "activated SQLite initialization failed verification",
                diagnostic="; ".join(issues),
            )
        write_bytes_atomic(
            manifest_store.path,
            ProjectStorageManifestStore.render(
                ProjectStorageManifest(
                    project_uuid=snapshot.project_uuid,
                    adapter=SQLITE_ADAPTER,
                )
            ),
            mode=0o600,
        )
        _update_activation_marker(marker, marker_payload, phase="manifest_updated")
        if failure_injector is not None:
            failure_injector("after_activation_manifest")
        safe_to_clear_marker = True
    except Exception as original:
        try:
            if activated:
                _unlink_and_sync_directory(final_database)
            for source, target in reversed(moved):
                source.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    _replace_and_sync_directories(target, source)
            # Candidate DB/WAL files are never part of the source snapshot and
            # must be gone before semantic post-rollback verification.
            _remove_tree_and_sync_parent(stage_root)
            if snapshot is not None:
                write_bytes_atomic(
                    resolved / PROJECT_STORAGE_MANIFEST_PATH,
                    ProjectStorageManifestStore.render(
                        ProjectStorageManifest(
                            project_uuid=snapshot.project_uuid,
                            adapter=FILESYSTEM_ADAPTER,
                        )
                    ),
                    mode=0o600,
                )
                recovered = CanonicalBundleCodec().snapshot(
                    FilesystemCanonicalMemoryStore(resolved)
                )
                if (
                    recovered.project_uuid != snapshot.project_uuid
                    or recovered.semantic_state_digest != snapshot.semantic_state_digest
                ):
                    raise ProjectStorageError(
                        ProjectStorageErrorCode.recovery_required,
                        "SQLite activation rollback did not restore filesystem state",
                    )
            safe_to_clear_marker = True
        except Exception as rollback_error:
            raise ProjectStorageError(
                ProjectStorageErrorCode.recovery_required,
                "SQLite activation rollback did not complete; explicit recovery is required",
                diagnostic=(
                    f"forward failure: {original}; rollback failure: {rollback_error}"
                ),
            ) from rollback_error
        raise
    finally:
        if not owns_marker or safe_to_clear_marker:
            _remove_tree_and_sync_parent(stage_root)
        if owns_marker and safe_to_clear_marker:
            _unlink_and_sync_directory(marker)
            _remove_empty_canonical_directories(resolved, detached_paths)
        if owns_lock and (not owns_marker or safe_to_clear_marker):
            lock.release(transaction_id)
    return (final_database, resolved / PROJECT_STORAGE_MANIFEST_PATH)


def _public_receipts_for_activation(
    root: Path,
    *,
    filesystem: FilesystemCanonicalMemoryStore,
    snapshot: CanonicalMemorySnapshot,
) -> tuple[tuple[SQLitePublicMutationRecord, ...], tuple[Path, ...]]:
    receipt_root = root / MUTATION_RECEIPT_ROOT
    if not receipt_root.exists():
        return (), ()
    if _has_symlink_component(root, receipt_root) or not receipt_root.is_dir():
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite activation found an unsafe public receipt directory",
        )
    canonical_documents = filesystem.activation_documents(snapshot.entities)
    receipts: list[SQLitePublicMutationRecord] = []
    paths: list[Path] = []
    for path in sorted(receipt_root.iterdir()):
        if not _is_safe_regular_file(root, path) or path.suffix != ".yml":
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite activation found an unsafe public receipt path",
            )
        receipt = parse_mutation_receipt(
            path.read_bytes(),
            expected_key_sha256=path.stem,
        )
        candidates: dict[str, bytes] = {}
        current_matches = True
        for postcondition in receipt.postconditions:
            target = root / postcondition.path
            if not _is_safe_regular_file(root, target):
                current_matches = False
                continue
            content = target.read_bytes()
            if hashlib.sha256(content).hexdigest() != postcondition.physical_sha256:
                current_matches = False
            candidates[postcondition.path] = canonical_documents.get(
                postcondition.path,
                content,
            )
        if current_matches and len(candidates) == len(receipt.postconditions):
            receipt = rebind_mutation_receipt_postconditions(receipt, candidates)
        durable_documents: dict[str, bytes] = {}
        for postcondition in receipt.postconditions:
            if not sqlite_public_receipt_document_path(postcondition.path):
                continue
            content = candidates.get(postcondition.path)
            if (
                content is None
                or hashlib.sha256(content).hexdigest()
                != postcondition.physical_sha256
            ):
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "SQLite activation cannot preserve a governed receipt document",
                    diagnostic=postcondition.path,
                )
            durable_documents[postcondition.path] = content
        receipts.append(sqlite_public_mutation_record(receipt, durable_documents))
        paths.append(path)
    return tuple(receipts), tuple(paths)


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


def _escapes_root(root: Path, path: Path) -> bool:
    try:
        return not path.resolve(strict=False).is_relative_to(root)
    except OSError:
        return True


def _assert_memory_tree_has_no_symlinks(root: Path) -> None:
    p2p = root / ".p2p"
    if _is_link_or_reparse_point(p2p) or _escapes_root(root, p2p) or not p2p.is_dir():
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite activation found an unsafe project-memory root",
        )
    for path in p2p.rglob("*"):
        if _is_link_or_reparse_point(path) or _escapes_root(root, path):
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "SQLite activation refuses symlinks or reparse points inside project memory",
                diagnostic=path.relative_to(root).as_posix(),
            )


def _has_symlink_component(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current /= part
        if _is_link_or_reparse_point(current) or _escapes_root(root, current):
            return True
    return False


def _is_safe_regular_file(root: Path, path: Path) -> bool:
    return not _has_symlink_component(root, path) and path.is_file()


def _filesystem_owner(filesystem: FilesystemCanonicalMemoryStore) -> str:
    permissions = PermissionsService(
        root=filesystem.root,
        p2p_dir=filesystem.root / ".p2p",
    ).show()
    identities = permissions.get("identities")
    if isinstance(identities, Mapping):
        for actor, identity in identities.items():
            if (
                isinstance(actor, str)
                and isinstance(identity, Mapping)
                and identity.get("role") == "owner"
            ):
                return actor
    raise ProjectStorageError(
        ProjectStorageErrorCode.integrity_failure,
        "SQLite activation source has no owner",
    )


def _write_activation_marker(marker: Path, payload: Mapping[str, object]) -> None:
    root = marker.parents[2]
    if _has_symlink_component(root, marker.parent):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite activation marker path is unsafe",
        )
    if marker.exists() or _is_link_or_reparse_point(marker):
        raise ProjectStorageError(
            ProjectStorageErrorCode.recovery_required,
            "another SQLite activation owns the recovery marker",
        )
    write_bytes_atomic(marker, canonical_json_bytes(payload), mode=0o600)


def _update_activation_marker(
    marker: Path,
    payload: dict[str, object],
    *,
    phase: str,
) -> None:
    if not _is_safe_regular_file(marker.parents[2], marker):
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "SQLite activation marker path became unsafe",
        )
    payload["phase"] = phase
    write_bytes_atomic(marker, canonical_json_bytes(payload), mode=0o600)


def _remove_empty_canonical_directories(root: Path, paths: tuple[Path, ...]) -> None:
    p2p = root / ".p2p"
    parents = {
        parent
        for path in paths
        for parent in path.parents
        if parent != p2p and parent.is_relative_to(p2p)
    }
    for parent in sorted(parents, key=lambda item: len(item.parts), reverse=True):
        try:
            parent.rmdir()
            sync_directory(parent.parent)
        except OSError:
            pass

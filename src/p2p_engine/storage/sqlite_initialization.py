from __future__ import annotations

import os
import shutil
from pathlib import Path

from p2p_engine.core.canonical_memory import canonical_json_bytes
from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    ProjectStorageError,
    ProjectStorageErrorCode,
    ProjectStorageManifest,
)
from p2p_engine.foundation.files import write_bytes_atomic
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.storage.canonical_memory import FilesystemCanonicalMemoryStore
from p2p_engine.storage.project_storage import (
    PROJECT_STORAGE_MANIFEST_PATH,
    ProjectStorageManifestStore,
)
from p2p_engine.storage.sqlite_project_state import (
    SQLiteProjectStateRepository,
    create_sqlite_database,
)
from p2p_engine.storage.sqlite_schema import (
    SQLITE_ADAPTER,
    SQLITE_DATABASE_PATH,
)

SQLITE_ACTIVATION_MARKER = ".p2p/local/sqlite-activation.json"


def activate_sqlite_from_filesystem(root: Path, *, failure_injector=None) -> tuple[Path, ...]:
    """Atomically replace initialization staging files with authoritative SQLite state."""
    resolved = root.resolve()
    manifest = ProjectStorageManifestStore(resolved).load()
    if manifest.adapter != SQLITE_ADAPTER:
        raise ProjectStorageError(
            ProjectStorageErrorCode.configuration_contradiction,
            "SQLite activation requires an explicit SQLite storage manifest",
        )
    final_database = resolved / SQLITE_DATABASE_PATH
    if final_database.exists():
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
    local = resolved / ".p2p/local"
    local.mkdir(parents=True, exist_ok=True)
    stage_database = local / f".project.sqlite3.{os.getpid()}.stage"
    stage_root = local / f"sqlite-activation-{os.getpid()}.stage"
    canonical_stage = stage_root / "canonical"
    marker = resolved / SQLITE_ACTIVATION_MARKER
    moved: list[tuple[Path, Path]] = []
    activated = False
    safely_restored = False
    inventory = filesystem.inventory()
    canonical_paths = tuple(
        resolved / artifact.locator
        for artifact in inventory.artifacts
        if artifact.classification == "canonical_project"
    )
    try:
        create_sqlite_database(
            stage_database,
            identity=identity,
            snapshot=snapshot,
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
        if failure_injector is not None:
            failure_injector("after_sqlite_stage")
        _write_activation_marker(
            marker,
            database=stage_database,
            canonical_stage=canonical_stage,
            project_uuid=snapshot.project_uuid,
        )
        for source in canonical_paths:
            if source.is_symlink() or not source.is_file():
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "canonical initialization staging contains an unsafe artifact",
                )
            target = canonical_stage / source.relative_to(resolved)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
            moved.append((source, target))
        if failure_injector is not None:
            failure_injector("after_canonical_detach")
        os.replace(stage_database, final_database)
        activated = True
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
    except Exception:
        if activated:
            final_database.unlink(missing_ok=True)
        for source, target in reversed(moved):
            source.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                os.replace(target, source)
        write_bytes_atomic(
            resolved / PROJECT_STORAGE_MANIFEST_PATH,
            ProjectStorageManifestStore.render(
                ProjectStorageManifest(
                    project_uuid=snapshot.project_uuid,
                    adapter=FILESYSTEM_ADAPTER,
                )
            ),
        )
        safely_restored = True
        raise
    finally:
        stage_database.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm", "-journal"):
            stage_database.with_name(stage_database.name + suffix).unlink(missing_ok=True)
        if activated or safely_restored:
            shutil.rmtree(stage_root, ignore_errors=True)
            marker.unlink(missing_ok=True)
            _remove_empty_canonical_directories(resolved, canonical_paths)
    return (final_database, resolved / PROJECT_STORAGE_MANIFEST_PATH)


def _write_activation_marker(
    marker: Path,
    *,
    database: Path,
    canonical_stage: Path,
    project_uuid: str,
) -> None:
    write_bytes_atomic(
        marker,
        canonical_json_bytes(
            {
                "contract": "p2p-sqlite-activation/v1",
                "project_uuid": project_uuid,
                "database_stage": database.name,
                "canonical_stage": canonical_stage.parent.name,
            }
        ),
    )


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
        except OSError:
            pass

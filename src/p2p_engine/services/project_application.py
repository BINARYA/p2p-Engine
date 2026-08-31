from __future__ import annotations

from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import Any

from p2p_engine.core.canonical_memory import MemoryRecoveryStatus
from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    ProjectEntityRecord,
    ProjectEntityRef,
    ProjectStateQuery,
    ProjectStorageCapabilities,
    ProjectStorageError,
    ProjectStorageErrorCode,
    ProjectStorageSelection,
)
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.ports.project_state import ProjectStateAdapter, ProjectUnitOfWork
from p2p_engine.storage.canonical_memory import FilesystemCanonicalMemoryStore
from p2p_engine.storage.filesystem_project_state import FilesystemProjectStateAdapter
from p2p_engine.storage.project_storage import ProjectStorageResolver
from p2p_engine.storage.sqlite_adapter import SQLiteBackupPort, SQLiteProjectStateAdapter
from p2p_engine.storage.sqlite_initialization import activate_sqlite_from_filesystem
from p2p_engine.storage.sqlite_project_state import SQLiteProjectStateRepository
from p2p_engine.storage.sqlite_schema import SQLITE_ADAPTER, SQLITE_MAINTENANCE_MARKER


class ProjectAdapterRegistry:
    """Internal adapter registry; product surfaces never import adapters directly."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    @property
    def available(self) -> tuple[str, ...]:
        return (FILESYSTEM_ADAPTER, SQLITE_ADAPTER)

    def open(self, selection: ProjectStorageSelection) -> ProjectStateAdapter:
        if selection.adapter == FILESYSTEM_ADAPTER:
            return FilesystemProjectStateAdapter(self.root, selection)
        if selection.adapter == SQLITE_ADAPTER:
            return SQLiteProjectStateAdapter(self.root, selection)
        raise ProjectStorageError(
            ProjectStorageErrorCode.adapter_unavailable,
            f"storage adapter '{selection.adapter}' is not available",
        )


class ProjectApplicationService:
    """Storage-neutral entry point shared by CLI, MCP, and compatibility callers."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.p2p_dir = self.root / ".p2p"
        self.registry = ProjectAdapterRegistry(self.root)
        self.selection = ProjectStorageResolver(
            self.root,
            available_adapters=self.registry.available,
        ).resolve()
        self.adapter = self.registry.open(self.selection)

    @property
    def storage_capabilities(self) -> ProjectStorageCapabilities:
        return self.adapter.capabilities

    def storage_selection(self) -> ProjectStorageSelection:
        return self.selection

    def project_state_revision(self):
        return self.adapter.repository.current_revision()

    def project_identity(self):
        return self.adapter.repository.identity()

    def project_state_entity(self, ref: ProjectEntityRef) -> ProjectEntityRecord | None:
        return self.adapter.repository.get(ref)

    def query_project_state(self, query: ProjectStateQuery) -> tuple[ProjectEntityRecord, ...]:
        return self.adapter.repository.query(query)

    def project_state_unit_of_work(self) -> ProjectUnitOfWork:
        return self.adapter.unit_of_work()

    def init_project(self, *args: Any, **kwargs: Any):
        activate_sqlite = self._needs_sqlite_activation(kwargs)
        result = getattr(self.adapter.compatibility_target(), "init_project")(
            *args, **kwargs
        )
        if activate_sqlite:
            activated = activate_sqlite_from_filesystem(self.root)
            result = [path for path in result if (self.root / path).exists()]
            result.extend(path.relative_to(self.root) for path in activated if path.exists())
        self._refresh_storage_binding()
        return result

    def init_project_with_summary(self, *args: Any, **kwargs: Any):
        activate_sqlite = self._needs_sqlite_activation(kwargs)
        result = getattr(
            self.adapter.compatibility_target(), "init_project_with_summary"
        )(*args, **kwargs)
        if activate_sqlite:
            activated = activate_sqlite_from_filesystem(self.root)
            created = [path for path in result.created if (self.root / path).exists()]
            created.extend(
                path.relative_to(self.root) for path in activated if path.exists()
            )
            result = replace(result, created=created)
        self._refresh_storage_binding()
        return result

    def init_project_with_operation_key(self, *args: Any, **kwargs: Any):
        activate_sqlite = self._needs_sqlite_activation(kwargs)
        result = getattr(
            self.adapter.compatibility_target(), "init_project_with_operation_key"
        )(*args, **kwargs)
        if activate_sqlite:
            activate_sqlite_from_filesystem(self.root)
        if self._requested_sqlite(kwargs):
            result = self._normalize_sqlite_init_result(result)
        self._refresh_storage_binding()
        return result

    def apply_project_identity_adoption(self, *args: Any, **kwargs: Any):
        result = getattr(
            self.adapter.compatibility_target(), "apply_project_identity_adoption"
        )(*args, **kwargs)
        self._refresh_storage_binding()
        return result

    def apply_project_identity_derivation(self, *args: Any, **kwargs: Any):
        result = getattr(
            self.adapter.compatibility_target(), "apply_project_identity_derivation"
        )(*args, **kwargs)
        self._refresh_storage_binding()
        return result

    def canonical_memory_snapshot(self):
        try:
            return self.adapter.repository.snapshot()
        except ProjectStorageError as exc:
            # Preserve the established canonical-memory public diagnostic while
            # typed storage queries retain the normalized adapter error.
            if exc.diagnostic:
                raise ValueError(exc.diagnostic) from exc
            raise

    def canonical_bundle_metadata(self):
        return self.adapter.snapshots.bundle_metadata()

    def canonical_bundle_export(self, output: Path):
        return self.adapter.snapshots.export_bundle_to(output)

    def canonical_archive_verify(self, source: Path):
        return self.adapter.snapshots.verify_archive(source)

    def canonical_memory_backup(self, output: Path, *, coordinated: bool = True):
        return self.adapter.backups.backup_to(output, coordinated=coordinated)

    def canonical_memory_restore_preview(
        self, *, source: Path, operation_key: str, actor: str
    ):
        return self.adapter.backups.restore_preview(
            source=source,
            operation_key=operation_key,
            actor=actor,
        )

    def canonical_memory_restore_apply(
        self,
        *,
        source: Path,
        operation_key: str,
        actor: str,
        preview_token: str,
        confirm: bool,
    ):
        return self.adapter.backups.restore_apply(
            source=source,
            operation_key=operation_key,
            actor=actor,
            preview_token=preview_token,
            confirm=confirm,
        )

    def canonical_memory_recovery_status(self):
        return self.adapter.backups.recovery_status()

    def read_governed_yaml(self, relative: str) -> object:
        try:
            return load_yaml(
                self.read_governed_bytes(relative),
                loader_contract=UNIQUE_LOADER_CONTRACT,
            )
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "governed project document cannot be read",
                diagnostic=str(exc),
            ) from exc

    def read_governed_bytes(self, relative: str) -> bytes:
        path = self._safe_project_path(relative)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            error: OSError = exc
            if self.selection.adapter == SQLITE_ADAPTER:
                documents = FilesystemCanonicalMemoryStore(self.root).activation_documents(
                    self.adapter.repository.snapshot().entities
                )
                content = documents.get(Path(relative).as_posix())
                if content is not None:
                    return content
        except OSError as exc:
            error = exc
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "governed project document cannot be read",
            diagnostic=str(error),
        ) from error

    def resolve_external_input(self, value: str) -> Path:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (self.root / path).resolve()

    def resolve_vertical_release(self, coordinate: str) -> object:
        target = self.adapter.compatibility_target()
        return getattr(target, "_project_vertical_service")().resolve_pack(coordinate)

    def __getattr__(self, name: str) -> Any:
        # Transitional compatibility delegation. Domain behavior remains in the
        # filesystem adapter while callers depend only on this application entry.
        return getattr(self.adapter.compatibility_target(), name)

    def _refresh_storage_binding(self) -> None:
        selection = ProjectStorageResolver(
            self.root,
            available_adapters=self.registry.available,
        ).resolve()
        if selection.adapter == self.selection.adapter:
            self.adapter.refresh_selection(selection)
        else:
            self.adapter = self.registry.open(selection)
        self.selection = selection

    @staticmethod
    def _requested_sqlite(kwargs: dict[str, Any]) -> bool:
        return str(kwargs.get("storage_adapter") or "").strip().lower() == SQLITE_ADAPTER

    def _needs_sqlite_activation(self, kwargs: dict[str, Any]) -> bool:
        return self.selection.adapter != SQLITE_ADAPTER and self._requested_sqlite(kwargs)

    def _normalize_sqlite_init_result(self, result: object) -> object:
        if not isinstance(result, dict):
            return result

        def normalize(value: object, *, field: str = "") -> object:
            if isinstance(value, dict):
                return {key: normalize(item, field=str(key)) for key, item in value.items()}
            if isinstance(value, list) and field in {
                "changed_paths",
                "created_file_paths",
                "created_paths",
            }:
                paths = [
                    str(item)
                    for item in value
                    if isinstance(item, str) and (self.root / item).exists()
                ]
                for relative in (
                    ".p2p/local/project.sqlite3",
                    ".p2p/local/storage.yml",
                ):
                    if (self.root / relative).exists() and relative not in paths:
                        paths.append(relative)
                return sorted(paths)
            if isinstance(value, list):
                return [normalize(item) for item in value]
            return value

        normalized = normalize(result)
        assert isinstance(normalized, dict)
        return normalized

    def _safe_project_path(self, relative: str) -> Path:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "governed project locator is unsafe",
            )
        candidate = (self.root / pure.as_posix()).resolve(strict=False)
        if not candidate.is_relative_to(self.root) or candidate.is_symlink():
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "governed project locator escapes the project root",
            )
        return candidate


def open_project_application(root: Path) -> ProjectApplicationService:
    return ProjectApplicationService(root)


def project_memory_recovery_status(root: Path) -> MemoryRecoveryStatus:
    """Read recovery state even when a SQLite maintenance fence blocks open."""
    resolved = root.resolve()
    marker = resolved / SQLITE_MAINTENANCE_MARKER
    if marker.exists() or marker.is_symlink():
        manifest = ProjectStorageResolver(resolved).manifests.load()
        if manifest.adapter == SQLITE_ADAPTER:
            return SQLiteBackupPort(
                SQLiteProjectStateRepository(resolved)
            ).recovery_status()
    return open_project_application(resolved).canonical_memory_recovery_status()

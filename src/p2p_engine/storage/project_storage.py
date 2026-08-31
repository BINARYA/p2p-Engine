from __future__ import annotations

from pathlib import Path
from uuid import UUID

from p2p_engine.core.project_identity import ProjectIdentity
from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    PROJECT_STORAGE_CONTRACT,
    PROJECT_STORAGE_SCHEMA_VERSION,
    ProjectStorageError,
    ProjectStorageErrorCode,
    ProjectStorageManifest,
    ProjectStorageSelection,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.storage.project_identity import FilesystemProjectIdentityStore

PROJECT_STORAGE_MANIFEST_PATH = ".p2p/local/storage.yml"
PROJECT_STORAGE_MANIFEST_MAX_BYTES = 16_384
_MANIFEST_FIELDS = frozenset({"contract", "project_uuid", "adapter", "schema_version"})
_SQLITE_CONTRADICTION_PATHS = (
    ".p2p/local/project.sqlite3",
    ".p2p/local/project.sqlite",
    ".p2p/local/project.db",
)


class ProjectStorageManifestStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.path = self.root / PROJECT_STORAGE_MANIFEST_PATH

    def exists(self) -> bool:
        return self.path.is_file() and not self.path.is_symlink()

    def load(self) -> ProjectStorageManifest:
        if not self.path.exists():
            raise ProjectStorageError(
                ProjectStorageErrorCode.manifest_invalid,
                "replica-local storage manifest is missing",
            )
        if self.path.is_symlink() or not self.path.is_file():
            raise ProjectStorageError(
                ProjectStorageErrorCode.manifest_invalid,
                "replica-local storage manifest is not a regular file",
            )
        if self.path.stat().st_size > PROJECT_STORAGE_MANIFEST_MAX_BYTES:
            raise ProjectStorageError(
                ProjectStorageErrorCode.manifest_invalid,
                "replica-local storage manifest exceeds its safe size",
            )
        try:
            payload = load_yaml(
                self.path.read_bytes(),
                loader_contract=UNIQUE_LOADER_CONTRACT,
            )
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.manifest_invalid,
                "replica-local storage manifest cannot be parsed",
                diagnostic=str(exc),
            ) from exc
        if not isinstance(payload, dict) or set(payload) != {"project_storage"}:
            raise ProjectStorageError(
                ProjectStorageErrorCode.manifest_invalid,
                "storage manifest must contain exactly project_storage",
            )
        raw = payload.get("project_storage")
        if not isinstance(raw, dict) or set(raw) != _MANIFEST_FIELDS:
            raise ProjectStorageError(
                ProjectStorageErrorCode.manifest_invalid,
                "project_storage fields are not exact",
            )
        schema_version = raw.get("schema_version")
        if isinstance(schema_version, bool) or not isinstance(schema_version, int):
            raise ProjectStorageError(
                ProjectStorageErrorCode.manifest_invalid,
                "storage schema version must be an integer",
            )
        try:
            project_uuid = str(UUID(str(raw.get("project_uuid") or "")))
            manifest = ProjectStorageManifest(
                contract=str(raw.get("contract") or ""),
                project_uuid=project_uuid,
                adapter=str(raw.get("adapter") or ""),
                schema_version=schema_version,
            )
        except (ValueError, AttributeError) as exc:
            if isinstance(exc, ProjectStorageError):
                raise
            raise ProjectStorageError(
                ProjectStorageErrorCode.manifest_invalid,
                "storage manifest values are invalid",
                diagnostic=str(exc),
            ) from exc
        return manifest

    @staticmethod
    def render(manifest: ProjectStorageManifest) -> bytes:
        return yaml_dump({"project_storage": manifest.to_dict()}).encode("ascii")


class ProjectStorageResolver:
    def __init__(self, root: Path, *, available_adapters: tuple[str, ...] = ()) -> None:
        self.root = root.resolve()
        self.p2p_dir = self.root / ".p2p"
        self.manifests = ProjectStorageManifestStore(self.root)
        self.available_adapters = available_adapters or (FILESYSTEM_ADAPTER,)

    def for_initialization(self, adapter: str = FILESYSTEM_ADAPTER) -> ProjectStorageSelection:
        normalized = adapter.strip().lower()
        if normalized not in self.available_adapters:
            raise ProjectStorageError(
                ProjectStorageErrorCode.adapter_unavailable,
                f"storage adapter '{normalized or adapter}' is not available",
            )
        if normalized != FILESYSTEM_ADAPTER:
            raise ProjectStorageError(
                ProjectStorageErrorCode.adapter_unavailable,
                f"storage adapter '{normalized}' is not implemented in this release",
            )
        return ProjectStorageSelection(
            manifest=ProjectStorageManifest(project_uuid=str(UUID(int=1)), adapter=normalized),
            source="initialization_default",
            persistent=False,
        )

    def resolve(self) -> ProjectStorageSelection:
        project_path = self.p2p_dir / "project.yml"
        if not project_path.exists():
            return self.for_initialization()
        if self.manifests.path.exists():
            manifest = self.manifests.load()
            self._validate_available(manifest)
            try:
                project_uuid, identity = self._selection_identity()
            except ProjectStorageError as exc:
                if not exc.diagnostic.startswith(
                    "P2P_PROJECT_IDENTITY_ADOPTION_REQUIRED:"
                ):
                    raise
                self._validate_contradictions(manifest.adapter)
                return ProjectStorageSelection(
                    manifest=manifest,
                    source="replica_local_manifest",
                    persistent=True,
                    warnings=(
                        "Storage opened only to permit explicit project identity adoption.",
                    ),
                )
            if manifest.project_uuid != project_uuid:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.identity_mismatch,
                    "storage manifest project UUID disagrees with canonical identity",
                )
            self._validate_contradictions(manifest.adapter)
            return ProjectStorageSelection(
                manifest=manifest,
                source="replica_local_manifest",
                persistent=True,
                identity=identity,
            )
        self._validate_legacy_filesystem_project()
        project_uuid, identity = self._selection_identity()
        self._validate_contradictions(FILESYSTEM_ADAPTER)
        return ProjectStorageSelection(
            manifest=ProjectStorageManifest(
                project_uuid=project_uuid,
                adapter=FILESYSTEM_ADAPTER,
                schema_version=PROJECT_STORAGE_SCHEMA_VERSION,
                contract=PROJECT_STORAGE_CONTRACT,
            ),
            source="validated_legacy_filesystem",
            persistent=False,
            warnings=(
                "Legacy filesystem project opened without writing a storage manifest.",
            ),
            identity=identity,
        )

    def manifest_for_new_project(
        self,
        *,
        project_uuid: str,
        adapter: str = FILESYSTEM_ADAPTER,
    ) -> ProjectStorageManifest:
        selection = self.for_initialization(adapter)
        return ProjectStorageManifest(
            project_uuid=project_uuid,
            adapter=selection.adapter,
            schema_version=PROJECT_STORAGE_SCHEMA_VERSION,
        )

    def _selection_identity(self) -> tuple[str, ProjectIdentity | None]:
        store = FilesystemProjectIdentityStore(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        try:
            identity = store.load()
        except ValueError:
            try:
                return store.storage_project_uuid().value, None
            except ValueError as exc:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "project identity is incomplete or invalid for storage selection: "
                    f"{exc}",
                    diagnostic=str(exc),
                ) from exc
        return identity.project_uuid.value, identity

    def _validate_available(self, manifest: ProjectStorageManifest) -> None:
        if manifest.adapter not in self.available_adapters:
            raise ProjectStorageError(
                ProjectStorageErrorCode.adapter_unavailable,
                f"storage adapter '{manifest.adapter}' is not available",
            )
        if manifest.adapter == FILESYSTEM_ADAPTER and (
            manifest.schema_version != PROJECT_STORAGE_SCHEMA_VERSION
        ):
            raise ProjectStorageError(
                ProjectStorageErrorCode.manifest_invalid,
                "filesystem storage schema version is unsupported",
            )

    def _validate_legacy_filesystem_project(self) -> None:
        if self.p2p_dir.is_symlink() or not self.p2p_dir.is_dir():
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "legacy filesystem project memory root is missing or unsafe",
            )
        project = self.p2p_dir / "project.yml"
        if project.is_symlink() or not project.is_file():
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "legacy filesystem project manifest is missing or unsafe",
            )

    def _validate_contradictions(self, adapter: str) -> None:
        if adapter != FILESYSTEM_ADAPTER:
            return
        conflicting = [path for path in _SQLITE_CONTRADICTION_PATHS if (self.root / path).exists()]
        if conflicting:
            raise ProjectStorageError(
                ProjectStorageErrorCode.configuration_contradiction,
                "filesystem adapter selection conflicts with SQLite storage artifacts",
                diagnostic=", ".join(conflicting),
            )

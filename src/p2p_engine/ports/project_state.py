from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from p2p_engine.core.authority_transfer import (
    AuthorityActivationReceipt,
    AuthorityTransferSession,
    TransferState,
)
from p2p_engine.core.canonical_memory import (
    BundleExportResult,
    BundleMaterializationResult,
    BundleValidationResult,
    CanonicalMemorySnapshot,
    MemoryRecoveryStatus,
    MemoryRestorePreview,
    MemoryRestoreResult,
    PhysicalBackupResult,
)
from p2p_engine.core.project_identity import ProjectIdentity
from p2p_engine.core.project_state_storage import (
    ProjectArchive,
    ProjectEntityRecord,
    ProjectEntityRef,
    ProjectStateCommitResult,
    ProjectStateMutation,
    ProjectStateQuery,
    ProjectStateRevision,
    ProjectStorageCapabilities,
    ProjectStorageSelection,
)


class ProjectStateRepository(Protocol):
    def identity(self) -> ProjectIdentity: ...

    def current_revision(self) -> ProjectStateRevision: ...

    def snapshot(self) -> CanonicalMemorySnapshot: ...

    def get(self, ref: ProjectEntityRef) -> ProjectEntityRecord | None: ...

    def query(self, query: ProjectStateQuery) -> tuple[ProjectEntityRecord, ...]: ...


class ProjectUnitOfWork(Protocol):
    @property
    def repository(self) -> ProjectStateRepository: ...

    def stage(self, mutation: ProjectStateMutation) -> None: ...

    def commit(self) -> ProjectStateCommitResult: ...

    def rollback(self) -> None: ...

    def __enter__(self) -> ProjectUnitOfWork: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class BlobStore(Protocol):
    def has(self, digest: str) -> bool: ...

    def read(self, digest: str) -> bytes: ...

    def verify(self, digests: Iterable[str]) -> tuple[str, ...]: ...


class ProjectSnapshotPort(Protocol):
    def export_bundle(self) -> ProjectArchive: ...

    def verify_bundle(self, archive: ProjectArchive) -> CanonicalMemorySnapshot: ...

    def bundle_metadata(self) -> BundleExportResult: ...

    def export_bundle_to(self, output: Path) -> BundleExportResult: ...

    def verify_archive(self, source: Path) -> BundleValidationResult: ...

    def materialize_bundle(
        self,
        *,
        source: Path,
        operation_key: str,
        actor: str,
        expected_project_uuid: str,
        expected_archive_sha256: str,
        confirm: bool,
    ) -> BundleMaterializationResult: ...


class ProjectBackupPort(Protocol):
    def create_backup(self) -> ProjectArchive: ...

    def verify_backup(self, archive: ProjectArchive) -> None: ...

    def backup_to(self, output: Path, *, coordinated: bool = True) -> PhysicalBackupResult: ...

    def restore_preview(
        self, *, source: Path, operation_key: str, actor: str
    ) -> MemoryRestorePreview: ...

    def restore_apply(
        self,
        *,
        source: Path,
        operation_key: str,
        actor: str,
        preview_token: str,
        confirm: bool,
    ) -> MemoryRestoreResult: ...

    def recovery_status(self) -> MemoryRecoveryStatus: ...


class ProjectMigrationPort(Protocol):
    def schema_version(self) -> int: ...

    def can_migrate_from(self, schema_version: int) -> bool: ...


class AuthorityTransferStatePort(Protocol):
    def load(self) -> AuthorityTransferSession | None: ...

    def receipt(self) -> AuthorityActivationReceipt | None: ...

    def save(self, session: AuthorityTransferSession) -> AuthorityTransferSession: ...

    def activate_linked(
        self,
        session: AuthorityTransferSession,
        receipt: AuthorityActivationReceipt,
    ) -> ProjectIdentity: ...

    def release_fence(
        self,
        session: AuthorityTransferSession,
        terminal_state: TransferState,
        *,
        error_code: str = "",
    ) -> AuthorityTransferSession: ...

    def writes_fenced(self) -> bool: ...

    def set_link_suspended(self, suspended: bool) -> ProjectIdentity: ...


class ProjectStateAdapter(Protocol):
    @property
    def selection(self) -> ProjectStorageSelection: ...

    @property
    def capabilities(self) -> ProjectStorageCapabilities: ...

    @property
    def repository(self) -> ProjectStateRepository: ...

    @property
    def blobs(self) -> BlobStore: ...

    @property
    def snapshots(self) -> ProjectSnapshotPort: ...

    @property
    def backups(self) -> ProjectBackupPort: ...

    @property
    def migrations(self) -> ProjectMigrationPort: ...

    @property
    def authority_transfers(self) -> AuthorityTransferStatePort: ...

    def unit_of_work(self) -> ProjectUnitOfWork: ...

    def refresh_selection(self, selection: ProjectStorageSelection) -> None: ...

    def compatibility_target(self) -> object: ...

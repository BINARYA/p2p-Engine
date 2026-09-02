from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable
from pathlib import Path

from p2p_engine.core.canonical_memory import CanonicalEntity, CanonicalMemorySnapshot
from p2p_engine.core.mutation_preview import semantic_sha256, source_precondition
from p2p_engine.core.project_identity import ProjectIdentity, ProjectMode
from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    PROJECT_STORAGE_SCHEMA_VERSION,
    ProjectArchive,
    ProjectEntityRecord,
    ProjectEntityRef,
    ProjectStateCommitResult,
    ProjectStateMutation,
    ProjectStateQuery,
    ProjectStateRevision,
    ProjectStorageCapabilities,
    ProjectStorageError,
    ProjectStorageErrorCode,
    ProjectStorageSelection,
)
from p2p_engine.ports.project_state import ProjectStateRepository
from p2p_engine.services.canonical_memory import CanonicalBundleCodec, CanonicalMemoryService
from p2p_engine.services.workspace_transactions import (
    AtomicMutationWriter,
    WorkspaceTransactionLockService,
)
from p2p_engine.storage.canonical_memory import FilesystemCanonicalMemoryStore
from p2p_engine.storage.filesystem_authority_transfer import FilesystemAuthorityTransferStore


def _record(entity: CanonicalEntity) -> ProjectEntityRecord:
    return ProjectEntityRecord(
        ref=ProjectEntityRef(entity.entity_type, entity.technical_id),
        human_key=entity.human_key,
        entity_version=entity.entity_version,
        payload=entity.payload,
    )


class FilesystemProjectStateRepository:
    def __init__(
        self,
        root: Path,
        *,
        identity_hint: ProjectIdentity | None = None,
    ) -> None:
        self.root = root.resolve()
        self.store = FilesystemCanonicalMemoryStore(self.root)
        self.codec = CanonicalBundleCodec()
        self._identity_hint = identity_hint
        self._identity_hint_fingerprint = self._identity_fingerprint()

    def identity(self):
        fingerprint = self._identity_fingerprint()
        if (
            self._identity_hint is not None
            and fingerprint == self._identity_hint_fingerprint
        ):
            return self._identity_hint
        identity = self.store.project_identity()
        self._identity_hint = identity
        self._identity_hint_fingerprint = fingerprint
        return identity

    def refresh_identity_hint(self, identity: ProjectIdentity | None) -> None:
        self._identity_hint = identity
        self._identity_hint_fingerprint = self._identity_fingerprint()

    def _identity_fingerprint(self) -> tuple[tuple[int, int, int] | None, ...]:
        paths = (
            self.store.identity_store.identity_path,
            self.store.identity_store.replica_path,
            self.store.identity_store.manifest_path,
        )
        fingerprint: list[tuple[int, int, int] | None] = []
        for path in paths:
            try:
                stat = path.stat()
            except OSError:
                fingerprint.append(None)
            else:
                fingerprint.append((stat.st_ino, stat.st_size, stat.st_mtime_ns))
        return tuple(fingerprint)

    def current_revision(self) -> ProjectStateRevision:
        return ProjectStateRevision(self.snapshot().semantic_state_digest)

    def snapshot(self) -> CanonicalMemorySnapshot:
        try:
            return self.codec.snapshot(self.store)
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "canonical project state cannot be read",
                diagnostic=str(exc),
            ) from exc

    def get(self, ref: ProjectEntityRef) -> ProjectEntityRecord | None:
        for entity in self.snapshot().entities:
            if entity.entity_type == ref.entity_type and entity.technical_id == ref.technical_id:
                return _record(entity)
        return None

    def query(self, query: ProjectStateQuery) -> tuple[ProjectEntityRecord, ...]:
        selected: list[ProjectEntityRecord] = []
        entity_types = frozenset(query.entity_types)
        technical_ids = frozenset(query.technical_ids)
        for entity in self.snapshot().entities:
            if entity_types and entity.entity_type not in entity_types:
                continue
            if technical_ids and entity.technical_id not in technical_ids:
                continue
            if query.human_key and entity.human_key != query.human_key:
                continue
            selected.append(_record(entity))
            if len(selected) >= query.limit:
                break
        return tuple(selected)


class FilesystemBlobStore:
    def __init__(self, repository: FilesystemProjectStateRepository) -> None:
        self.repository = repository

    def has(self, digest: str) -> bool:
        return any(item.digest == digest for item in self.repository.snapshot().blobs)

    def read(self, digest: str) -> bytes:
        for blob in self.repository.snapshot().blobs:
            if blob.digest == digest:
                return self.repository.store.read_blob_bytes(blob)
        raise ProjectStorageError(
            ProjectStorageErrorCode.integrity_failure,
            "managed blob is missing",
        )

    def verify(self, digests: Iterable[str]) -> tuple[str, ...]:
        failed: list[str] = []
        for digest in digests:
            try:
                self.read(digest)
            except ProjectStorageError:
                failed.append(digest)
        return tuple(sorted(failed))


class FilesystemSnapshotPort:
    def __init__(self, repository: FilesystemProjectStateRepository) -> None:
        self.repository = repository

    def export_bundle(self) -> ProjectArchive:
        snapshot = self.repository.snapshot()
        raw, _manifest = self.repository.codec.encode_bundle(
            self.repository.store,
            snapshot,
        )
        return ProjectArchive(
            kind="portable_bundle",
            content=raw,
            sha256=hashlib.sha256(raw).hexdigest(),
            semantic_state_digest=snapshot.semantic_state_digest,
        )

    def verify_bundle(self, archive: ProjectArchive) -> CanonicalMemorySnapshot:
        if archive.kind != "portable_bundle":
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "archive is not a portable project bundle",
            )
        try:
            decoded = self.repository.codec.decode_bundle(archive.content)
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

    def bundle_metadata(self):
        return self._service().bundle_metadata()

    def export_bundle_to(self, output: Path):
        return self._service().export_bundle(output)

    def verify_archive(self, source: Path):
        return self._service().verify_archive(source)

    def _service(self) -> CanonicalMemoryService:
        return CanonicalMemoryService(
            root=self.repository.root,
            p2p_dir=self.repository.root / ".p2p",
            store=self.repository.store,
            codec=self.repository.codec,
        )


class FilesystemBackupPort:
    def __init__(self, repository: FilesystemProjectStateRepository) -> None:
        self.repository = repository
        self.lock = WorkspaceTransactionLockService(
            root=repository.root,
            p2p_dir=repository.root / ".p2p",
        )

    def create_backup(self) -> ProjectArchive:
        transaction_id = f"storage-port-backup-{os.getpid()}"
        acquired = False
        try:
            self.lock.acquire(transaction_id, owner="storage-port-backup")
            acquired = True
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.busy,
                "coordinated physical backup could not acquire a consistent project state",
                diagnostic=str(exc),
            ) from exc
        try:
            inventory = self.repository.store.inventory()
            snapshot = self.repository.snapshot()
            raw = self.repository.codec.encode_physical_backup(
                store=self.repository.store,
                files=self.repository.store.physical_backup_files(inventory),
                directories=self.repository.store.physical_backup_directories(),
                semantic_state_digest=snapshot.semantic_state_digest,
                source_revision=self.repository.store.identity_store.source_revision().sha256,
            )
            return ProjectArchive(
                kind="physical_backup",
                content=raw,
                sha256=hashlib.sha256(raw).hexdigest(),
                semantic_state_digest=snapshot.semantic_state_digest,
            )
        except (OSError, ValueError) as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "coordinated physical backup could not encode project state",
                diagnostic=str(exc),
            ) from exc
        finally:
            if acquired:
                self.lock.release(transaction_id)

    def verify_backup(self, archive: ProjectArchive) -> None:
        if archive.kind != "physical_backup":
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "archive is not a physical project backup",
            )
        try:
            decoded = self.repository.codec.decode_physical_backup(archive.content)
        except ValueError as exc:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "physical project backup is invalid",
                diagnostic=str(exc),
            ) from exc
        if decoded.archive_sha256 != archive.sha256:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "physical project backup digest does not match",
            )
        if decoded.semantic_state_digest != archive.semantic_state_digest:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "physical project backup semantic digest does not match",
            )

    def backup_to(self, output: Path, *, coordinated: bool = True):
        return self._service().backup(output, coordinated=coordinated)

    def restore_preview(self, *, source: Path, operation_key: str, actor: str):
        return self._service().restore_preview(
            source=source,
            operation_key=operation_key,
            actor=actor,
        )

    def restore_apply(
        self,
        *,
        source: Path,
        operation_key: str,
        actor: str,
        preview_token: str,
        confirm: bool,
    ):
        return self._service().restore_apply(
            source=source,
            operation_key=operation_key,
            actor=actor,
            preview_token=preview_token,
            confirm=confirm,
        )

    def recovery_status(self):
        return self._service().recovery_status()

    def _service(self) -> CanonicalMemoryService:
        return CanonicalMemoryService(
            root=self.repository.root,
            p2p_dir=self.repository.root / ".p2p",
            store=self.repository.store,
            codec=self.repository.codec,
        )


class FilesystemMigrationPort:
    def schema_version(self) -> int:
        return PROJECT_STORAGE_SCHEMA_VERSION

    def can_migrate_from(self, schema_version: int) -> bool:
        return schema_version == PROJECT_STORAGE_SCHEMA_VERSION


class FilesystemProjectUnitOfWork:
    def __init__(self, repository: FilesystemProjectStateRepository) -> None:
        self._repository = repository
        self._mutation: ProjectStateMutation | None = None
        self._closed = False

    @property
    def repository(self) -> ProjectStateRepository:
        return self._repository

    def stage(self, mutation: ProjectStateMutation) -> None:
        if self._closed or self._mutation is not None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.internal,
                "unit of work already has a staged command",
            )
        identity = self._repository.identity()
        if identity.mode != ProjectMode.standalone:
            raise ProjectStorageError(
                ProjectStorageErrorCode.unsupported_capability,
                "local project-state mutations are blocked after authority transfer",
            )
        if FilesystemAuthorityTransferStore(self._repository.root).writes_fenced():
            raise ProjectStorageError(
                ProjectStorageErrorCode.busy,
                "local project-state mutations are fenced during authority transfer",
            )
        current = self._repository.snapshot()
        if mutation.expected_revision.sha256 != current.semantic_state_digest:
            raise ProjectStorageError(
                ProjectStorageErrorCode.stale_revision,
                "project state changed before the command was staged",
            )
        if mutation.target.project_uuid != current.project_uuid:
            raise ProjectStorageError(
                ProjectStorageErrorCode.identity_mismatch,
                "command target project UUID disagrees with active project",
            )
        self._mutation = mutation

    def commit(self) -> ProjectStateCommitResult:
        if self._closed or self._mutation is None:
            raise ProjectStorageError(
                ProjectStorageErrorCode.internal,
                "unit of work has no staged command",
            )
        mutation = self._mutation
        current = self._repository.snapshot()
        if mutation.expected_revision.sha256 != current.semantic_state_digest:
            raise ProjectStorageError(
                ProjectStorageErrorCode.stale_revision,
                "project state changed before the command could commit",
            )
        target_documents = self._repository.store.activation_documents(
            mutation.target.entities
        )
        blob_bytes: dict[str, bytes] = {}
        current_blobs = {item.digest: item for item in current.blobs}
        for blob in mutation.target.blobs:
            content = mutation.blob_payloads.get(blob.digest)
            if content is None and blob.digest in current_blobs:
                content = self._repository.store.read_blob_bytes(current_blobs[blob.digest])
            if content is None:
                raise ProjectStorageError(
                    ProjectStorageErrorCode.integrity_failure,
                    "command target references a managed blob without payload",
                )
            blob_bytes[blob.digest] = content
        target_documents.update(
            self._repository.store.blob_documents(mutation.target.blobs, blob_bytes)
        )
        current_paths = set(
            self._repository.store.current_portable_paths(
                self._repository.store.inventory()
            )
        )
        target_paths = set(target_documents)
        candidates: dict[str, bytes | None] = {
            **target_documents,
            **{path: None for path in current_paths - target_paths},
        }
        sources = tuple(
            source_precondition(
                path,
                (self._repository.root / path).read_bytes()
                if (self._repository.root / path).is_file()
                else None,
            )
            for path in sorted(candidates)
        )
        preview_token = semantic_sha256(
            {
                "operation_id": mutation.operation_id,
                "actor": mutation.actor,
                "expected_revision": mutation.expected_revision.sha256,
                "target_revision": mutation.target.semantic_state_digest,
                "receipt_id": mutation.receipt_id,
            }
        )
        result = AtomicMutationWriter(
            root=self._repository.root,
            p2p_dir=self._repository.root / ".p2p",
        ).apply(
            operation_id=mutation.operation_id,
            candidates=candidates,
            sources=sources,
            preview_token=preview_token,
            actor=mutation.actor,
            lock_wait_timeout=mutation.lock_wait_timeout,
        )
        self._closed = True
        if result.status != "applied":
            code = (
                ProjectStorageErrorCode.busy
                if result.status == "blocked"
                else ProjectStorageErrorCode.recovery_required
                if result.recovery_required
                else ProjectStorageErrorCode.internal
            )
            raise ProjectStorageError(
                code,
                "atomic project-state command did not commit",
                diagnostic=result.message,
            )
        final = self._repository.snapshot()
        if final.semantic_state_digest != mutation.target.semantic_state_digest:
            raise ProjectStorageError(
                ProjectStorageErrorCode.integrity_failure,
                "committed project state does not match the staged semantic digest",
            )
        changed_refs = _changed_entity_refs(current, final)
        return ProjectStateCommitResult(
            status="applied",
            operation_id=mutation.operation_id,
            revision=ProjectStateRevision(final.semantic_state_digest),
            changed_entities=changed_refs,
            receipt_id=mutation.receipt_id,
        )

    def rollback(self) -> None:
        self._mutation = None
        self._closed = True

    def __enter__(self) -> FilesystemProjectUnitOfWork:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc is not None and not self._closed:
            self.rollback()


def _changed_entity_refs(
    before: CanonicalMemorySnapshot,
    after: CanonicalMemorySnapshot,
) -> tuple[ProjectEntityRef, ...]:
    old = {(item.entity_type, item.technical_id): item for item in before.entities}
    new = {(item.entity_type, item.technical_id): item for item in after.entities}
    changed = {
        key
        for key in set(old) | set(new)
        if old.get(key) != new.get(key)
    }
    return tuple(ProjectEntityRef(*key) for key in sorted(changed))


class FilesystemProjectStateAdapter:
    def __init__(self, root: Path, selection: ProjectStorageSelection) -> None:
        self.root = root.resolve()
        self._selection = selection
        self._repository = FilesystemProjectStateRepository(
            self.root,
            identity_hint=selection.identity,
        )
        self._compatibility: object | None = None
        self._blobs = FilesystemBlobStore(self._repository)
        self._snapshots = FilesystemSnapshotPort(self._repository)
        self._backups = FilesystemBackupPort(self._repository)
        self._migrations = FilesystemMigrationPort()
        self._authority_transfers = FilesystemAuthorityTransferStore(self.root)

    @property
    def selection(self) -> ProjectStorageSelection:
        return self._selection

    @property
    def capabilities(self) -> ProjectStorageCapabilities:
        return ProjectStorageCapabilities(
            adapter=FILESYSTEM_ADAPTER,
            schema_version=PROJECT_STORAGE_SCHEMA_VERSION,
        )

    @property
    def repository(self) -> FilesystemProjectStateRepository:
        return self._repository

    @property
    def blobs(self) -> FilesystemBlobStore:
        return self._blobs

    @property
    def snapshots(self) -> FilesystemSnapshotPort:
        return self._snapshots

    @property
    def backups(self) -> FilesystemBackupPort:
        return self._backups

    @property
    def migrations(self) -> FilesystemMigrationPort:
        return self._migrations

    @property
    def authority_transfers(self) -> FilesystemAuthorityTransferStore:
        return self._authority_transfers

    def unit_of_work(self) -> FilesystemProjectUnitOfWork:
        return FilesystemProjectUnitOfWork(self._repository)

    def refresh_selection(self, selection: ProjectStorageSelection) -> None:
        if selection.adapter != FILESYSTEM_ADAPTER:
            raise ProjectStorageError(
                ProjectStorageErrorCode.configuration_contradiction,
                "filesystem adapter cannot adopt a different storage selection",
            )
        self._selection = selection
        self._repository.refresh_identity_hint(selection.identity)

    def compatibility_target(self) -> object:
        if self._compatibility is None:
            from p2p_engine.storage.filesystem import FilesystemWorkspace

            self._compatibility = FilesystemWorkspace(self.root)
        return self._compatibility

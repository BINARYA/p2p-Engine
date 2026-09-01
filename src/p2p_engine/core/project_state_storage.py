from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping
from uuid import UUID

from p2p_engine.core.canonical_memory import CanonicalMemorySnapshot
from p2p_engine.core.project_identity import ProjectIdentity

PROJECT_STORAGE_CONTRACT = "p2p-project-storage/v1"
PROJECT_STORAGE_SCHEMA_VERSION = 1
FILESYSTEM_ADAPTER = "filesystem"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ADAPTER = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class ProjectStorageErrorCode(str, Enum):
    manifest_invalid = "P2P_STORAGE_MANIFEST_INVALID"
    adapter_unavailable = "P2P_STORAGE_ADAPTER_UNAVAILABLE"
    configuration_contradiction = "P2P_STORAGE_CONFIGURATION_CONTRADICTION"
    identity_mismatch = "P2P_STORAGE_IDENTITY_MISMATCH"
    stale_revision = "P2P_STORAGE_STALE_REVISION"
    idempotency_conflict = "P2P_IDEMPOTENCY_CONFLICT"
    busy = "P2P_STORAGE_BUSY"
    integrity_failure = "P2P_STORAGE_INTEGRITY_FAILURE"
    recovery_required = "P2P_STORAGE_RECOVERY_REQUIRED"
    unsupported_capability = "P2P_STORAGE_CAPABILITY_UNSUPPORTED"
    internal = "P2P_STORAGE_INTERNAL_ERROR"


class ProjectStorageError(ValueError):
    """Storage-neutral failure safe for CLI/MCP translation."""

    def __init__(
        self,
        code: ProjectStorageErrorCode,
        message: str,
        *,
        diagnostic: str = "",
    ) -> None:
        self.code = code
        self.safe_message = message
        self.diagnostic = diagnostic
        super().__init__(f"{code.value}: {message}")


@dataclass(frozen=True, order=True)
class ProjectStateRevision:
    sha256: str
    namespace: str = field(default="canonical_state", compare=False)

    def __post_init__(self) -> None:
        if self.namespace != "canonical_state" or not _SHA256.fullmatch(self.sha256):
            raise ValueError("P2P_STORAGE_REVISION_INVALID: expected canonical SHA-256")

    def to_dict(self) -> dict[str, str]:
        return {"namespace": self.namespace, "sha256": self.sha256}


@dataclass(frozen=True, order=True)
class ProjectEntityRef:
    entity_type: str
    technical_id: str

    def __post_init__(self) -> None:
        if not self.entity_type.strip() or not self.technical_id.strip():
            raise ValueError("P2P_STORAGE_ENTITY_REF_INVALID: type and technical ID are required")


@dataclass(frozen=True)
class ProjectEntityRecord:
    ref: ProjectEntityRef
    human_key: str | None
    entity_version: int
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.entity_version < 1:
            raise ValueError("P2P_STORAGE_ENTITY_INVALID: entity version must be positive")


@dataclass(frozen=True)
class ProjectStateQuery:
    entity_types: tuple[str, ...] = ()
    human_key: str = ""
    technical_ids: tuple[str, ...] = ()
    limit: int = 1000

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 100_000:
            raise ValueError("P2P_STORAGE_QUERY_INVALID: limit is outside the safe range")


@dataclass(frozen=True)
class ProjectStorageCapabilities:
    adapter: str
    schema_version: int
    consistent_reads: bool = True
    atomic_multi_entity_writes: bool = True
    managed_blobs: bool = True
    portable_bundles: bool = True
    physical_backup_restore: bool = True
    concurrent_readers: bool = True
    serialized_writers: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter": self.adapter,
            "schema_version": self.schema_version,
            "consistent_reads": self.consistent_reads,
            "atomic_multi_entity_writes": self.atomic_multi_entity_writes,
            "managed_blobs": self.managed_blobs,
            "portable_bundles": self.portable_bundles,
            "physical_backup_restore": self.physical_backup_restore,
            "concurrent_readers": self.concurrent_readers,
            "serialized_writers": self.serialized_writers,
        }


@dataclass(frozen=True)
class ProjectStorageManifest:
    project_uuid: str
    adapter: str = FILESYSTEM_ADAPTER
    schema_version: int = PROJECT_STORAGE_SCHEMA_VERSION
    contract: str = PROJECT_STORAGE_CONTRACT

    def __post_init__(self) -> None:
        if self.contract != PROJECT_STORAGE_CONTRACT:
            raise ValueError("P2P_STORAGE_MANIFEST_INVALID: unsupported contract")
        if not _ADAPTER.fullmatch(self.adapter):
            raise ValueError("P2P_STORAGE_MANIFEST_INVALID: adapter identifier is invalid")
        if self.schema_version < 1:
            raise ValueError("P2P_STORAGE_MANIFEST_INVALID: schema version must be positive")
        try:
            UUID(self.project_uuid)
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                "P2P_STORAGE_MANIFEST_INVALID: project UUID is invalid"
            ) from exc

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "project_uuid": self.project_uuid,
            "adapter": self.adapter,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ProjectStorageSelection:
    manifest: ProjectStorageManifest
    source: str
    persistent: bool
    warnings: tuple[str, ...] = ()
    identity: ProjectIdentity | None = field(default=None, repr=False, compare=False)

    @property
    def adapter(self) -> str:
        return self.manifest.adapter

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": self.manifest.contract,
            "project_uuid": self.manifest.project_uuid,
            "adapter": self.manifest.adapter,
            "schema_version": self.manifest.schema_version,
            "source": self.source,
            "persistent": self.persistent,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ProjectStateCommitResult:
    status: str
    operation_id: str
    revision: ProjectStateRevision
    changed_entities: tuple[ProjectEntityRef, ...] = ()
    receipt_id: str = ""
    replayed: bool = False


@dataclass(frozen=True)
class ProjectStateMutation:
    operation_id: str
    actor: str
    expected_revision: ProjectStateRevision
    target: CanonicalMemorySnapshot
    blob_payloads: Mapping[str, bytes] = field(default_factory=dict)
    receipt_id: str = ""
    lock_wait_timeout: float = 0.0

    def __post_init__(self) -> None:
        if not self.operation_id.strip() or not self.actor.strip():
            raise ValueError("P2P_STORAGE_MUTATION_INVALID: operation and actor are required")
        if self.lock_wait_timeout < 0 or self.lock_wait_timeout > 60:
            raise ValueError("P2P_STORAGE_MUTATION_INVALID: lock timeout is outside the safe range")


@dataclass(frozen=True)
class ProjectArchive:
    kind: str
    content: bytes
    sha256: str
    semantic_state_digest: str

    def __post_init__(self) -> None:
        if self.kind not in {"portable_bundle", "physical_backup"}:
            raise ValueError("P2P_STORAGE_ARCHIVE_INVALID: unsupported archive kind")
        if not _SHA256.fullmatch(self.sha256) or not _SHA256.fullmatch(
            self.semantic_state_digest
        ):
            raise ValueError("P2P_STORAGE_ARCHIVE_INVALID: archive digests are invalid")
        if hashlib.sha256(self.content).hexdigest() != self.sha256:
            raise ValueError("P2P_STORAGE_ARCHIVE_INVALID: archive content digest differs")

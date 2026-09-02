from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Mapping

CANONICAL_MEMORY_CONTRACT = "p2p-canonical-memory/v1"
PROJECT_BUNDLE_SCHEMA = "p2p-project-bundle/v1"
PHYSICAL_BACKUP_SCHEMA = "p2p-physical-backup/v1"
DOMAIN_CONTRACT = "p2p-domain/v1"
MEMORY_SCHEMA_VERSION = 1
BUNDLE_ARCHIVE_ROOT = "p2p-project-bundle"
BACKUP_ARCHIVE_ROOT = "p2p-physical-backup"

PORTABLE_CLASSIFICATIONS = frozenset({"canonical_project", "managed_blob"})
KNOWN_CLASSIFICATIONS = frozenset(
    {
        *PORTABLE_CLASSIFICATIONS,
        "replica_local",
        "derived_projection",
        "runtime_transient",
        "backup",
        "legacy",
        "integration_artifact",
        "personal_configuration",
        "external_material",
        "unknown",
    }
)


def normalize_semantic_value(value: object) -> object:
    """Return the bounded portable JSON domain for hashing and serialization."""
    return _normalize_semantic_value(value, active=set(), depth=0)


def _normalize_semantic_value(value: object, *, active: set[int], depth: int) -> object:
    if depth > 128:
        raise ValueError("P2P_CANONICAL_VALUE_INVALID: semantic value nesting is too deep")
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError("P2P_CANONICAL_VALUE_INVALID: non-finite numbers are forbidden")
        return value
    if isinstance(value, datetime):
        normalized_datetime = value
        if normalized_datetime.tzinfo is None:
            normalized_datetime = normalized_datetime.replace(tzinfo=timezone.utc)
        return normalized_datetime.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    if isinstance(value, Mapping):
        marker = id(value)
        if marker in active:
            raise ValueError("P2P_CANONICAL_VALUE_INVALID: cyclic mappings are forbidden")
        active.add(marker)
        normalized_mapping: dict[str, object] = {}
        try:
            for raw_key, raw_value in value.items():
                if not isinstance(raw_key, str):
                    raise ValueError("P2P_CANONICAL_VALUE_INVALID: mapping keys must be strings")
                key = unicodedata.normalize("NFC", raw_key)
                if key in normalized_mapping:
                    raise ValueError(
                        "P2P_CANONICAL_VALUE_INVALID: mapping keys collide after Unicode normalization"
                    )
                normalized_mapping[key] = _normalize_semantic_value(
                    raw_value, active=active, depth=depth + 1
                )
            return dict(sorted(normalized_mapping.items()))
        finally:
            active.remove(marker)
    if isinstance(value, (list, tuple)):
        marker = id(value)
        if marker in active:
            raise ValueError("P2P_CANONICAL_VALUE_INVALID: cyclic sequences are forbidden")
        active.add(marker)
        try:
            return [
                _normalize_semantic_value(item, active=active, depth=depth + 1) for item in value
            ]
        finally:
            active.remove(marker)
    raise ValueError(
        f"P2P_CANONICAL_VALUE_INVALID: unsupported semantic value {type(value).__name__}"
    )


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            normalize_semantic_value(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def semantic_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True)
class MemoryArtifact:
    locator: str
    classification: str
    semantic_kind: str
    portable: bool
    reconstructible: bool
    size: int
    physical_sha256: str
    reason: str
    blocking: bool = False

    def __post_init__(self) -> None:
        if self.classification not in KNOWN_CLASSIFICATIONS:
            raise ValueError(
                "P2P_CANONICAL_MEMORY_CLASSIFICATION_INVALID: unsupported classification"
            )
        if not self.locator or self.locator.startswith("/") or ".." in self.locator.split("/"):
            raise ValueError("P2P_CANONICAL_MEMORY_PATH_UNSAFE: invalid inventory locator")

    def to_dict(self) -> dict[str, object]:
        return {
            "locator": self.locator,
            "classification": self.classification,
            "semantic_kind": self.semantic_kind,
            "portable": self.portable,
            "reconstructible": self.reconstructible,
            "size": self.size,
            "physical_sha256": self.physical_sha256,
            "reason": self.reason,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class CanonicalMemoryInventory:
    artifacts: tuple[MemoryArtifact, ...]
    contract: str = CANONICAL_MEMORY_CONTRACT

    @property
    def blockers(self) -> tuple[MemoryArtifact, ...]:
        return tuple(item for item in self.artifacts if item.blocking)

    @property
    def portable(self) -> tuple[MemoryArtifact, ...]:
        return tuple(item for item in self.artifacts if item.portable)

    def to_dict(self, *, limit: int = 4096) -> dict[str, object]:
        if limit < 1:
            raise ValueError("P2P_CANONICAL_MEMORY_LIMIT_INVALID: limit must be positive")
        counts: dict[str, int] = {}
        for item in self.artifacts:
            counts[item.classification] = counts.get(item.classification, 0) + 1
        visible = self.artifacts[:limit]
        return {
            "contract": self.contract,
            "status": "blocked" if self.blockers else "ready",
            "artifact_count": len(self.artifacts),
            "portable_artifact_count": len(self.portable),
            "blocking_count": len(self.blockers),
            "counts": dict(sorted(counts.items())),
            "artifacts": [item.to_dict() for item in visible],
            "truncated": len(visible) != len(self.artifacts),
        }


@dataclass(frozen=True)
class CanonicalEntity:
    entity_type: str
    technical_id: str
    entity_version: int
    payload: Mapping[str, object]
    human_key: str | None = None
    tombstone: bool = False
    storage_locator: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.entity_type or not self.technical_id:
            raise ValueError("P2P_CANONICAL_ENTITY_INVALID: type and technical ID are required")
        if isinstance(self.entity_version, bool) or self.entity_version < 1:
            raise ValueError("P2P_CANONICAL_ENTITY_INVALID: entity version must be positive")

    def to_dict(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "technical_id": self.technical_id,
            "human_key": self.human_key,
            "entity_version": self.entity_version,
            "payload": dict(self.payload),
            "tombstone": self.tombstone,
        }


@dataclass(frozen=True)
class CanonicalRelation:
    relation_type: str
    relation_id: str
    source_entity: str
    target_entity: str
    payload: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not all((self.relation_type, self.relation_id, self.source_entity, self.target_entity)):
            raise ValueError("P2P_CANONICAL_RELATION_INVALID: relation fields are required")

    def to_dict(self) -> dict[str, object]:
        return {
            "relation_type": self.relation_type,
            "relation_id": self.relation_id,
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class ManagedBlob:
    digest: str
    size: int
    media_type: str = "application/octet-stream"
    storage_locator: str = field(default="", repr=False, compare=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "digest": self.digest,
            "size": self.size,
            "media_type": self.media_type,
        }


@dataclass(frozen=True)
class CanonicalMemorySnapshot:
    project_uuid: str
    entities: tuple[CanonicalEntity, ...]
    relations: tuple[CanonicalRelation, ...]
    lineage: tuple[Mapping[str, object], ...]
    blobs: tuple[ManagedBlob, ...]
    semantic_state_digest: str
    blob_manifest_digest: str
    source_revision: Mapping[str, str]
    memory_schema: int = MEMORY_SCHEMA_VERSION
    domain_contract: str = DOMAIN_CONTRACT

    def to_metadata(self) -> dict[str, object]:
        return {
            "contract": CANONICAL_MEMORY_CONTRACT,
            "project_uuid": self.project_uuid,
            "source_revision": dict(self.source_revision),
            "memory_schema": self.memory_schema,
            "domain_contract": self.domain_contract,
            "semantic_state_digest": self.semantic_state_digest,
            "blob_manifest_digest": self.blob_manifest_digest,
            "entity_count": len(self.entities),
            "relation_count": len(self.relations),
            "lineage_count": len(self.lineage),
            "blob_count": len(self.blobs),
            "blob_bytes": sum(item.size for item in self.blobs),
        }


@dataclass(frozen=True)
class ProjectBundleManifest:
    project_uuid: str
    source_revision: Mapping[str, str]
    semantic_state_digest: str
    blob_manifest_digest: str
    entity_count: int
    relation_count: int
    lineage_count: int
    blob_count: int
    blob_bytes: int
    bundle_schema: str = PROJECT_BUNDLE_SCHEMA
    memory_schema: int = MEMORY_SCHEMA_VERSION
    domain_contract: str = DOMAIN_CONTRACT
    capabilities: tuple[str, ...] = (
        "complete-managed-blobs",
        "deterministic-jsonl",
        "staged-activation",
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "bundle_schema": self.bundle_schema,
            "project_uuid": self.project_uuid,
            "source_revision": dict(self.source_revision),
            "memory_schema": self.memory_schema,
            "domain_contract": self.domain_contract,
            "semantic_state_digest": self.semantic_state_digest,
            "blob_manifest_digest": self.blob_manifest_digest,
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "lineage_count": self.lineage_count,
            "blob_count": self.blob_count,
            "blob_bytes": self.blob_bytes,
            "capabilities": list(self.capabilities),
        }


@dataclass(frozen=True)
class BundleValidationResult:
    status: str
    archive_kind: str
    project_uuid: str = ""
    semantic_state_digest: str = ""
    archive_sha256: str = ""
    entity_count: int = 0
    relation_count: int = 0
    lineage_count: int = 0
    blob_count: int = 0
    issues: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return self.status == "valid" and not self.issues

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "p2p-bundle-validation/v1",
            "status": self.status,
            "archive_kind": self.archive_kind,
            "project_uuid": self.project_uuid,
            "semantic_state_digest": self.semantic_state_digest,
            "archive_sha256": self.archive_sha256,
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "lineage_count": self.lineage_count,
            "blob_count": self.blob_count,
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class BundleExportResult:
    status: str
    output: str
    manifest: ProjectBundleManifest
    archive_sha256: str
    archive_size: int

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "p2p-bundle-export/v1",
            "status": self.status,
            "output": self.output,
            "manifest": self.manifest.to_dict(),
            "archive_sha256": self.archive_sha256,
            "archive_size": self.archive_size,
        }


@dataclass(frozen=True)
class BundleMaterializationResult:
    status: str
    operation_key: str
    project_uuid: str
    semantic_state_digest: str
    blob_manifest_digest: str
    archive_sha256: str
    entity_count: int
    relation_count: int
    blob_count: int
    replayed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "p2p-bundle-materialization/v1",
            "status": self.status,
            "operation_key": self.operation_key,
            "project_uuid": self.project_uuid,
            "semantic_state_digest": self.semantic_state_digest,
            "blob_manifest_digest": self.blob_manifest_digest,
            "archive_sha256": self.archive_sha256,
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "blob_count": self.blob_count,
            "replayed": self.replayed,
        }


@dataclass(frozen=True)
class PhysicalBackupResult:
    status: str
    output: str
    project_uuid: str
    source_revision: str
    archive_sha256: str
    archive_size: int
    file_count: int
    coordinated: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "p2p-physical-backup-result/v1",
            "status": self.status,
            "output": self.output,
            "project_uuid": self.project_uuid,
            "source_revision": self.source_revision,
            "archive_sha256": self.archive_sha256,
            "archive_size": self.archive_size,
            "file_count": self.file_count,
            "coordinated": self.coordinated,
        }


@dataclass(frozen=True)
class MemoryRestorePreview:
    status: str
    operation_key: str
    archive_kind: str
    archive_sha256: str
    project_uuid: str
    current_semantic_digest: str
    target_semantic_digest: str
    preview_token: str
    changed_entity_count: int
    pre_restore_backup_required: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "p2p-memory-restore-preview/v1",
            "status": self.status,
            "operation_key": self.operation_key,
            "archive_kind": self.archive_kind,
            "archive_sha256": self.archive_sha256,
            "project_uuid": self.project_uuid,
            "current_semantic_digest": self.current_semantic_digest,
            "target_semantic_digest": self.target_semantic_digest,
            "preview_token": self.preview_token,
            "changed_entity_count": self.changed_entity_count,
            "pre_restore_backup_required": self.pre_restore_backup_required,
        }


@dataclass(frozen=True)
class MemoryRestoreResult:
    status: str
    operation_key: str
    archive_kind: str
    project_uuid: str
    semantic_state_digest: str
    archive_sha256: str
    preview_token: str
    backup_path: str
    recovery_path: str
    changed_entity_count: int
    replayed: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "p2p-memory-restore-result/v1",
            "status": self.status,
            "operation_key": self.operation_key,
            "archive_kind": self.archive_kind,
            "project_uuid": self.project_uuid,
            "semantic_state_digest": self.semantic_state_digest,
            "archive_sha256": self.archive_sha256,
            "preview_token": self.preview_token,
            "backup_path": self.backup_path,
            "recovery_path": self.recovery_path,
            "changed_entity_count": self.changed_entity_count,
            "replayed": self.replayed,
            "message": self.message,
        }


@dataclass(frozen=True)
class MemoryRecoveryStatus:
    state: str
    marker: str = ""
    staging_path: str = ""
    recovery_path: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "p2p-memory-recovery-status/v1",
            "state": self.state,
            "marker": self.marker,
            "staging_path": self.staging_path,
            "recovery_path": self.recovery_path,
            "message": self.message,
        }

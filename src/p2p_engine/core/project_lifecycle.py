from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from p2p_engine.core.canonical_memory import canonical_json_bytes
from p2p_engine.core.project_identity import (
    AuthorityEpoch,
    ProjectUuid,
    RemoteProjectId,
    ServerInstanceId,
)

PROJECT_LIFECYCLE_PROTOCOL = "p2p-project-lifecycle/v1"
PROJECT_LIFECYCLE_CAPABILITY_CONTRACT = "p2p-project-lifecycle-capabilities/v1"
PROJECT_LIFECYCLE_CAPABILITY_PATH = "/.well-known/p2p-project-lifecycle"
PROJECT_LIFECYCLE_PREVIEW_CONTRACT = "p2p-project-lifecycle-preview/v1"
PROJECT_LIFECYCLE_RECEIPT_CONTRACT = "p2p-project-lifecycle-receipt/v1"
PROJECT_LIFECYCLE_STATUS_CONTRACT = "p2p-project-lifecycle-status/v1"
DETACH_PREPARATION_CONTRACT = "p2p-project-detach-preparation/v1"
DETACH_RECEIPT_CONTRACT = "p2p-detach-receipt/v1"
PROJECT_PUBLICATION_CONTRACT = "p2p-project-publication/v1"
PROJECT_LIFECYCLE_LOCAL_STATE_CONTRACT = "p2p-local-project-lifecycle/v1"
PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES = 2_097_152

_OPAQUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+-]{0,511}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class LifecycleAction(str, Enum):
    suspend = "suspend"
    resume = "resume"
    detach = "detach"
    create_from_local = "create-from-local"
    remove_local_replica = "remove-local-replica"
    archive = "archive"
    restore = "restore"
    delete_remote = "delete-remote"
    publish_copy = "publish-copy"


class RemoteLifecycleState(str, Enum):
    active = "active"
    suspended = "suspended"
    archived = "archived"
    pending_delete = "pending-delete"
    retained = "retained"
    deleted = "deleted"
    tombstoned = "tombstoned"
    access_revoked = "access-revoked"
    unreachable = "unreachable"


class LifecycleOperationState(str, Enum):
    previewed = "previewed"
    prepared = "prepared"
    applied = "applied"
    failed = "failed"
    recovery_required = "recovery-required"


class DetachLineageMode(str, Enum):
    preserve_origin = "preserve-origin"
    private_origin = "private-origin"
    drop_origin = "drop-origin"
    emergency_unverified = "emergency-unverified"


class LocalReplicaDisposition(str, Enum):
    archive = "archive"
    remove = "remove"


class IntegrationDisposition(str, Enum):
    remove = "remove"
    remote_only = "remote-only"


def normalized_sha256(value: object, *, field: str) -> str:
    text = str(value or "").removeprefix("sha256:")
    if not _SHA256.fullmatch(text):
        raise ValueError(f"P2P_PROJECT_LIFECYCLE_INVALID: {field} must be a SHA-256")
    return text


def bounded_id(value: object, *, field: str) -> str:
    text = str(value or "")
    if not _OPAQUE.fullmatch(text):
        raise ValueError(f"P2P_PROJECT_LIFECYCLE_INVALID: {field} must be a bounded identifier")
    return text


@dataclass(frozen=True)
class LifecycleEndpoints:
    status: str
    preview: str
    apply: str
    operation: str
    detach_prepare: str
    detach_complete: str
    publication: str
    deactivate_replica: str

    def to_dict(self) -> dict[str, str]:
        return {
            "status": self.status,
            "preview": self.preview,
            "apply": self.apply,
            "operation": self.operation,
            "detach_prepare": self.detach_prepare,
            "detach_complete": self.detach_complete,
            "publication": self.publication,
            "deactivate_replica": self.deactivate_replica,
        }


@dataclass(frozen=True)
class LifecycleCapabilities:
    server_url: str
    server_instance_id: ServerInstanceId
    endpoints: LifecycleEndpoints
    retention_days: int
    allowed_lineage_modes: tuple[DetachLineageMode, ...]
    emergency_detach_allowed: bool = False
    protocol: str = PROJECT_LIFECYCLE_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != PROJECT_LIFECYCLE_PROTOCOL:
            raise ValueError(
                "P2P_PROJECT_LIFECYCLE_PROTOCOL_UNSUPPORTED: lifecycle protocol differs"
            )
        if not 1 <= self.retention_days <= 3650:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: retention is outside policy")
        if not self.allowed_lineage_modes:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: no detach lineage mode is allowed")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_LIFECYCLE_CAPABILITY_CONTRACT,
            "protocol": self.protocol,
            "server_instance_id": self.server_instance_id.value,
            "endpoints": self.endpoints.to_dict(),
            "retention_days": self.retention_days,
            "allowed_lineage_modes": [item.value for item in self.allowed_lineage_modes],
            "emergency_detach_allowed": self.emergency_detach_allowed,
        }


@dataclass(frozen=True)
class LifecyclePreview:
    action: LifecycleAction
    operation_id: str
    project_uuid: ProjectUuid
    remote_project_id: RemoteProjectId | None
    authority_epoch: AuthorityEpoch
    project_revision: int
    lifecycle_state: RemoteLifecycleState
    effects: tuple[str, ...]
    blockers: tuple[str, ...] = ()
    target_project_uuid: ProjectUuid | None = None
    target: str = ""
    lineage_mode: DetachLineageMode | None = None
    retention_days: int = 0
    preview_token: str = ""

    def __post_init__(self) -> None:
        bounded_id(self.operation_id, field="operation_id")
        if self.project_revision < 1:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: project revision must be positive")
        if self.retention_days < 0:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: retention cannot be negative")

    @property
    def eligible(self) -> bool:
        return not self.blockers

    def semantics(self) -> dict[str, object]:
        return {
            "contract": PROJECT_LIFECYCLE_PREVIEW_CONTRACT,
            "action": self.action.value,
            "operation_id": self.operation_id,
            "project_uuid": self.project_uuid.value,
            "remote_project_id": (
                self.remote_project_id.value if self.remote_project_id is not None else None
            ),
            "authority_epoch": self.authority_epoch.value,
            "project_revision": self.project_revision,
            "lifecycle_state": self.lifecycle_state.value,
            "target_project_uuid": (
                self.target_project_uuid.value if self.target_project_uuid is not None else None
            ),
            "target": self.target or None,
            "lineage_mode": self.lineage_mode.value if self.lineage_mode is not None else None,
            "retention_days": self.retention_days or None,
            "effects": list(self.effects),
            "blockers": list(self.blockers),
            "eligible": self.eligible,
        }

    def with_token(self) -> LifecyclePreview:
        from hashlib import sha256

        token = sha256(canonical_json_bytes(self.semantics())).hexdigest()
        return LifecyclePreview(
            action=self.action,
            operation_id=self.operation_id,
            project_uuid=self.project_uuid,
            remote_project_id=self.remote_project_id,
            authority_epoch=self.authority_epoch,
            project_revision=self.project_revision,
            lifecycle_state=self.lifecycle_state,
            effects=self.effects,
            blockers=self.blockers,
            target_project_uuid=self.target_project_uuid,
            target=self.target,
            lineage_mode=self.lineage_mode,
            retention_days=self.retention_days,
            preview_token=token,
        )

    def to_dict(self) -> dict[str, object]:
        payload = self.semantics()
        payload["preview_token"] = self.preview_token
        return payload


@dataclass(frozen=True)
class LifecycleReceipt:
    operation_id: str
    action: LifecycleAction
    status: LifecycleOperationState
    project_uuid: ProjectUuid
    remote_project_id: RemoteProjectId
    authority_epoch: AuthorityEpoch
    project_revision: int
    lifecycle_state: RemoteLifecycleState
    issued_at: str
    retention_until: str = ""
    message: str = ""

    def __post_init__(self) -> None:
        bounded_id(self.operation_id, field="operation_id")
        if self.project_revision < 1:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: receipt revision must be positive")
        if self.status not in {
            LifecycleOperationState.applied,
            LifecycleOperationState.recovery_required,
            LifecycleOperationState.failed,
        }:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: receipt status is not terminal")
        if not self.issued_at:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: receipt issued_at is required")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_LIFECYCLE_RECEIPT_CONTRACT,
            "operation_id": self.operation_id,
            "action": self.action.value,
            "status": self.status.value,
            "project_uuid": self.project_uuid.value,
            "remote_project_id": self.remote_project_id.value,
            "authority_epoch": self.authority_epoch.value,
            "project_revision": self.project_revision,
            "lifecycle_state": self.lifecycle_state.value,
            "issued_at": self.issued_at,
            "retention_until": self.retention_until or None,
            "message": self.message,
        }


@dataclass(frozen=True)
class DetachReceipt:
    detach_id: str
    source_project_uuid: ProjectUuid
    source_remote_project_id: RemoteProjectId
    source_revision: int
    source_authority_epoch: AuthorityEpoch
    new_project_uuid: ProjectUuid
    new_semantic_digest: str
    blob_manifest_digest: str
    lineage_mode: DetachLineageMode
    local_owner: str
    issued_at: str
    verification_token: str
    origin_verified: bool = True
    status: str = "verified"

    def __post_init__(self) -> None:
        bounded_id(self.detach_id, field="detach_id")
        bounded_id(self.local_owner, field="local_owner")
        bounded_id(self.verification_token, field="verification_token")
        if self.source_project_uuid == self.new_project_uuid:
            raise ValueError("P2P_PROJECT_LIFECYCLE_IDENTITY_CONFLICT: detach requires a new UUID")
        if self.source_revision < 1 or self.status != "verified" or not self.issued_at:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: detach receipt is incomplete")
        object.__setattr__(
            self,
            "new_semantic_digest",
            normalized_sha256(self.new_semantic_digest, field="new_semantic_digest"),
        )
        object.__setattr__(
            self,
            "blob_manifest_digest",
            normalized_sha256(self.blob_manifest_digest, field="blob_manifest_digest"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": DETACH_RECEIPT_CONTRACT,
            "detach_id": self.detach_id,
            "source_project_uuid": self.source_project_uuid.value,
            "source_remote_project_id": self.source_remote_project_id.value,
            "source_revision": self.source_revision,
            "source_authority_epoch": self.source_authority_epoch.value,
            "new_project_uuid": self.new_project_uuid.value,
            "new_semantic_digest": f"sha256:{self.new_semantic_digest}",
            "blob_manifest_digest": f"sha256:{self.blob_manifest_digest}",
            "lineage_mode": self.lineage_mode.value,
            "local_owner": self.local_owner,
            "issued_at": self.issued_at,
            "verification_token": self.verification_token,
            "origin_verified": self.origin_verified,
            "status": self.status,
        }


@dataclass(frozen=True)
class ProjectPublication:
    publication_id: str
    version: int
    project_uuid: ProjectUuid
    source_revision: int
    semantic_digest: str
    bundle_digest: str
    blob_manifest_digest: str
    created_at: str
    immutable: bool = True

    def __post_init__(self) -> None:
        bounded_id(self.publication_id, field="publication_id")
        if self.version < 1 or self.source_revision < 1 or not self.created_at:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: publication metadata is incomplete")
        for field in ("semantic_digest", "bundle_digest", "blob_manifest_digest"):
            object.__setattr__(self, field, normalized_sha256(getattr(self, field), field=field))
        if not self.immutable:
            raise ValueError("P2P_PROJECT_PUBLICATION_INVALID: publication must be immutable")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_PUBLICATION_CONTRACT,
            "publication_id": self.publication_id,
            "version": self.version,
            "project_uuid": self.project_uuid.value,
            "source_revision": self.source_revision,
            "semantic_digest": f"sha256:{self.semantic_digest}",
            "bundle_digest": f"sha256:{self.bundle_digest}",
            "blob_manifest_digest": f"sha256:{self.blob_manifest_digest}",
            "created_at": self.created_at,
            "immutable": self.immutable,
        }


@dataclass(frozen=True)
class LocalLifecycleState:
    operation_id: str
    action: LifecycleAction
    status: LifecycleOperationState
    project_uuid: ProjectUuid
    updated_at: str
    remote_state: RemoteLifecycleState | None = None
    recovery_path: str = ""
    message: str = ""

    def __post_init__(self) -> None:
        bounded_id(self.operation_id, field="operation_id")
        if not self.updated_at:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: updated_at is required")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_LIFECYCLE_LOCAL_STATE_CONTRACT,
            "operation_id": self.operation_id,
            "action": self.action.value,
            "status": self.status.value,
            "project_uuid": self.project_uuid.value,
            "remote_state": self.remote_state.value if self.remote_state is not None else None,
            "updated_at": self.updated_at,
            "recovery_path": self.recovery_path or None,
            "message": self.message,
        }


def local_lifecycle_state_from_mapping(raw: Mapping[str, object]) -> LocalLifecycleState:
    expected = {
        "contract",
        "operation_id",
        "action",
        "status",
        "project_uuid",
        "remote_state",
        "updated_at",
        "recovery_path",
        "message",
    }
    if set(raw) != expected or raw.get("contract") != PROJECT_LIFECYCLE_LOCAL_STATE_CONTRACT:
        raise ValueError("P2P_PROJECT_LIFECYCLE_STATE_INVALID: local state fields differ")
    remote = raw.get("remote_state")
    return LocalLifecycleState(
        operation_id=str(raw["operation_id"]),
        action=LifecycleAction(str(raw["action"])),
        status=LifecycleOperationState(str(raw["status"])),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        remote_state=RemoteLifecycleState(str(remote)) if remote is not None else None,
        updated_at=str(raw["updated_at"]),
        recovery_path=str(raw.get("recovery_path") or ""),
        message=str(raw.get("message") or ""),
    )


def lifecycle_receipt_from_mapping(raw: Mapping[str, object]) -> LifecycleReceipt:
    expected = {
        "contract",
        "operation_id",
        "action",
        "status",
        "project_uuid",
        "remote_project_id",
        "authority_epoch",
        "project_revision",
        "lifecycle_state",
        "issued_at",
        "retention_until",
        "message",
    }
    if set(raw) != expected or raw.get("contract") != PROJECT_LIFECYCLE_RECEIPT_CONTRACT:
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: receipt fields differ")
    return LifecycleReceipt(
        operation_id=str(raw["operation_id"]),
        action=LifecycleAction(str(raw["action"])),
        status=LifecycleOperationState(str(raw["status"])),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        remote_project_id=RemoteProjectId(str(raw["remote_project_id"])),
        authority_epoch=AuthorityEpoch(_positive_int(raw["authority_epoch"], "authority_epoch")),
        project_revision=_positive_int(raw["project_revision"], "project_revision"),
        lifecycle_state=RemoteLifecycleState(str(raw["lifecycle_state"])),
        issued_at=str(raw["issued_at"]),
        retention_until=str(raw.get("retention_until") or ""),
        message=str(raw.get("message") or ""),
    )


def detach_receipt_from_mapping(raw: Mapping[str, object]) -> DetachReceipt:
    expected = {
        "contract",
        "detach_id",
        "source_project_uuid",
        "source_remote_project_id",
        "source_revision",
        "source_authority_epoch",
        "new_project_uuid",
        "new_semantic_digest",
        "blob_manifest_digest",
        "lineage_mode",
        "local_owner",
        "issued_at",
        "verification_token",
        "origin_verified",
        "status",
    }
    if set(raw) != expected or raw.get("contract") != DETACH_RECEIPT_CONTRACT:
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: detach receipt fields differ")
    return DetachReceipt(
        detach_id=str(raw["detach_id"]),
        source_project_uuid=ProjectUuid(str(raw["source_project_uuid"])),
        source_remote_project_id=RemoteProjectId(str(raw["source_remote_project_id"])),
        source_revision=_positive_int(raw["source_revision"], "source_revision"),
        source_authority_epoch=AuthorityEpoch(
            _positive_int(raw["source_authority_epoch"], "source_authority_epoch")
        ),
        new_project_uuid=ProjectUuid(str(raw["new_project_uuid"])),
        new_semantic_digest=str(raw["new_semantic_digest"]),
        blob_manifest_digest=str(raw["blob_manifest_digest"]),
        lineage_mode=DetachLineageMode(str(raw["lineage_mode"])),
        local_owner=str(raw["local_owner"]),
        issued_at=str(raw["issued_at"]),
        verification_token=str(raw["verification_token"]),
        origin_verified=raw["origin_verified"] is True,
        status=str(raw["status"]),
    )


def publication_from_mapping(raw: Mapping[str, object]) -> ProjectPublication:
    expected = {
        "contract",
        "publication_id",
        "version",
        "project_uuid",
        "source_revision",
        "semantic_digest",
        "bundle_digest",
        "blob_manifest_digest",
        "created_at",
        "immutable",
    }
    if set(raw) != expected or raw.get("contract") != PROJECT_PUBLICATION_CONTRACT:
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: publication fields differ")
    return ProjectPublication(
        publication_id=str(raw["publication_id"]),
        version=_positive_int(raw["version"], "version"),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        source_revision=_positive_int(raw["source_revision"], "source_revision"),
        semantic_digest=str(raw["semantic_digest"]),
        bundle_digest=str(raw["bundle_digest"]),
        blob_manifest_digest=str(raw["blob_manifest_digest"]),
        created_at=str(raw["created_at"]),
        immutable=raw["immutable"] is True,
    )


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: {field} must be positive")
    return value

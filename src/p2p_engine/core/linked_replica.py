from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

from p2p_engine.core.authority_transfer import normalized_sha256, safe_profile_ref
from p2p_engine.core.project_identity import (
    AuthorityEpoch,
    ProjectUuid,
    RemoteProjectId,
    ReplicaId,
    ServerInstanceId,
)

LINKED_REPLICA_PROTOCOL = "p2p-linked-replica/v1"
LINKED_REPLICA_CAPABILITY_CONTRACT = "p2p-linked-replica-capabilities/v1"
LINKED_REPLICA_CAPABILITY_PATH = "/.well-known/p2p-linked-replica"
LINKED_REPLICA_BINDING_CONTRACT = "p2p-linked-replica-binding/v1"
LINKED_REPLICA_SNAPSHOT_CONTRACT = "p2p-linked-replica-snapshot/v1"
LINKED_REPLICA_CHANGE_CONTRACT = "p2p-linked-replica-change-batch/v1"
LINKED_REPLICA_STATUS_CONTRACT = "p2p-linked-replica-status/v1"
LINKED_REPLICA_MAX_RESPONSE_BYTES = 1_048_576
LINKED_REPLICA_MAX_BUNDLE_BYTES = 1_073_741_824
LINKED_REPLICA_MAX_BLOB_BYTES = 268_435_456
LINKED_REPLICA_MAX_BLOBS = 50_000

_SESSION_ID = re.compile(r"^rs_[0-9a-f]{32}$")
_ERROR_CODE = re.compile(r"^(?:P2P_[A-Z0-9_]+)?$")


def _non_negative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"P2P_LINKED_REPLICA_INVALID: {field_name} must be non-negative")
    return value


def _positive_int(value: object, field_name: str) -> int:
    result = _non_negative_int(value, field_name)
    if result < 1:
        raise ValueError(f"P2P_LINKED_REPLICA_INVALID: {field_name} must be positive")
    return result


def _session_id(value: object) -> str:
    text = str(value or "")
    if not _SESSION_ID.fullmatch(text):
        raise ValueError("P2P_LINKED_REPLICA_INVALID: clone session ID is invalid")
    return text


class ReplicaAccessState(str, Enum):
    active = "active"
    suspended = "suspended"
    access_revoked = "access-revoked"
    read_only = "read-only"
    rebuilding = "rebuilding"
    corrupt = "corrupt"


@dataclass(frozen=True)
class ReplicaEndpoints:
    register: str
    replica: str
    snapshot: str
    bundle: str
    blob: str
    changes: str
    deactivate: str
    move: str
    register_copy: str

    def to_dict(self) -> dict[str, str]:
        return {
            "register": self.register,
            "replica": self.replica,
            "snapshot": self.snapshot,
            "bundle": self.bundle,
            "blob": self.blob,
            "changes": self.changes,
            "deactivate": self.deactivate,
            "move": self.move,
            "register_copy": self.register_copy,
        }


@dataclass(frozen=True)
class ReplicaCapabilities:
    server_url: str
    server_instance_id: ServerInstanceId
    endpoints: ReplicaEndpoints
    max_bundle_bytes: int
    max_blob_bytes: int
    max_blobs: int
    retention_floor: int = 0
    protocol: str = LINKED_REPLICA_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != LINKED_REPLICA_PROTOCOL:
            raise ValueError(
                "P2P_LINKED_REPLICA_PROTOCOL_UNSUPPORTED: WaveKit replica protocol differs"
            )
        if not 1 <= self.max_bundle_bytes <= LINKED_REPLICA_MAX_BUNDLE_BYTES:
            raise ValueError("P2P_LINKED_REPLICA_INVALID: unsafe bundle limit")
        if not 1 <= self.max_blob_bytes <= LINKED_REPLICA_MAX_BLOB_BYTES:
            raise ValueError("P2P_LINKED_REPLICA_INVALID: unsafe blob limit")
        if not 1 <= self.max_blobs <= LINKED_REPLICA_MAX_BLOBS:
            raise ValueError("P2P_LINKED_REPLICA_INVALID: unsafe blob-count limit")
        _non_negative_int(self.retention_floor, "retention_floor")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": LINKED_REPLICA_CAPABILITY_CONTRACT,
            "protocol": self.protocol,
            "server_instance_id": self.server_instance_id.value,
            "endpoints": self.endpoints.to_dict(),
            "limits": {
                "max_bundle_bytes": self.max_bundle_bytes,
                "max_blob_bytes": self.max_blob_bytes,
                "max_blobs": self.max_blobs,
            },
            "retention_floor": self.retention_floor,
        }


@dataclass(frozen=True, order=True)
class ReplicaBlob:
    digest: str
    size: int
    media_type: str = "application/octet-stream"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "digest",
            normalized_sha256(self.digest, field_name="replica blob digest"),
        )
        _non_negative_int(self.size, "replica blob size")
        if self.size > LINKED_REPLICA_MAX_BLOB_BYTES:
            raise ValueError("P2P_LINKED_REPLICA_INVALID: replica blob exceeds safe limit")
        if (
            not self.media_type
            or len(self.media_type.encode("ascii", errors="ignore")) != len(self.media_type)
            or len(self.media_type) > 128
            or any(ord(char) < 32 for char in self.media_type)
        ):
            raise ValueError("P2P_LINKED_REPLICA_INVALID: blob media type is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "digest": f"sha256:{self.digest}",
            "size": self.size,
            "media_type": self.media_type,
        }


@dataclass(frozen=True)
class ReplicaSnapshotManifest:
    session_id: str
    server_instance_id: ServerInstanceId
    remote_project_id: RemoteProjectId
    project_uuid: ProjectUuid
    replica_id: ReplicaId
    authority_epoch: AuthorityEpoch
    remote_revision: int
    cursor: int
    semantic_state_digest: str
    bundle_digest: str
    blob_manifest_digest: str
    bundle_size: int
    blobs: tuple[ReplicaBlob, ...]
    expires_at: int
    status: str = "ready"

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _session_id(self.session_id))
        if self.status != "ready":
            raise ValueError("P2P_LINKED_REPLICA_INVALID: snapshot is not ready")
        _positive_int(self.remote_revision, "remote_revision")
        _non_negative_int(self.cursor, "cursor")
        _positive_int(self.bundle_size, "bundle_size")
        _positive_int(self.expires_at, "expires_at")
        if self.bundle_size > LINKED_REPLICA_MAX_BUNDLE_BYTES:
            raise ValueError("P2P_LINKED_REPLICA_INVALID: snapshot bundle exceeds safe limit")
        for name in (
            "semantic_state_digest",
            "bundle_digest",
            "blob_manifest_digest",
        ):
            object.__setattr__(
                self,
                name,
                normalized_sha256(getattr(self, name), field_name=name),
            )
        normalized = tuple(sorted(self.blobs))
        if len(normalized) != len(set(item.digest for item in normalized)):
            raise ValueError("P2P_LINKED_REPLICA_INVALID: blob manifest has duplicates")
        if len(normalized) > LINKED_REPLICA_MAX_BLOBS:
            raise ValueError("P2P_LINKED_REPLICA_INVALID: blob manifest exceeds safe limit")
        object.__setattr__(self, "blobs", normalized)

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": LINKED_REPLICA_SNAPSHOT_CONTRACT,
            "status": self.status,
            "session_id": self.session_id,
            "server_instance_id": self.server_instance_id.value,
            "remote_project_id": self.remote_project_id.value,
            "project_uuid": self.project_uuid.value,
            "replica_id": self.replica_id.value,
            "authority_epoch": self.authority_epoch.value,
            "remote_revision": self.remote_revision,
            "cursor": self.cursor,
            "semantic_state_digest": f"sha256:{self.semantic_state_digest}",
            "bundle_digest": f"sha256:{self.bundle_digest}",
            "blob_manifest_digest": f"sha256:{self.blob_manifest_digest}",
            "bundle_size": self.bundle_size,
            "blobs": [item.to_dict() for item in self.blobs],
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True)
class LinkedReplicaBinding:
    server_url: str
    server_instance_id: ServerInstanceId
    remote_project_id: RemoteProjectId
    project_uuid: ProjectUuid
    replica_id: ReplicaId
    authority_epoch: AuthorityEpoch
    last_applied_revision: int
    cursor: int
    snapshot_digest: str
    blob_manifest_digest: str
    account_profile_ref: str
    state: ReplicaAccessState = ReplicaAccessState.active
    last_verified_at: int = 0
    last_error_code: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "server_url", _normalize_server_url(self.server_url))
        _positive_int(self.last_applied_revision, "last_applied_revision")
        _non_negative_int(self.cursor, "cursor")
        _non_negative_int(self.last_verified_at, "last_verified_at")
        object.__setattr__(
            self,
            "snapshot_digest",
            normalized_sha256(self.snapshot_digest, field_name="snapshot_digest"),
        )
        object.__setattr__(
            self,
            "blob_manifest_digest",
            normalized_sha256(self.blob_manifest_digest, field_name="blob_manifest_digest"),
        )
        safe_profile_ref(self.account_profile_ref, field_name="account_profile_ref")
        if not _ERROR_CODE.fullmatch(self.last_error_code):
            raise ValueError("P2P_LINKED_REPLICA_INVALID: last_error_code is invalid")

    @property
    def writes_permitted(self) -> bool:
        return self.state == ReplicaAccessState.active

    def with_progress(
        self,
        *,
        remote_revision: int,
        cursor: int,
        snapshot_digest: str,
        blob_manifest_digest: str,
        verified_at: int,
    ) -> LinkedReplicaBinding:
        if remote_revision < self.last_applied_revision or cursor < self.cursor:
            raise ValueError("P2P_LINKED_REPLICA_CURSOR_REGRESSION: replica progress cannot regress")
        next_state = (
            ReplicaAccessState.read_only
            if self.state == ReplicaAccessState.read_only
            else ReplicaAccessState.active
        )
        return LinkedReplicaBinding(
            server_url=self.server_url,
            server_instance_id=self.server_instance_id,
            remote_project_id=self.remote_project_id,
            project_uuid=self.project_uuid,
            replica_id=self.replica_id,
            authority_epoch=self.authority_epoch,
            last_applied_revision=remote_revision,
            cursor=cursor,
            snapshot_digest=snapshot_digest,
            blob_manifest_digest=blob_manifest_digest,
            account_profile_ref=self.account_profile_ref,
            state=next_state,
            last_verified_at=verified_at,
        )

    def with_access_state(
        self,
        state: ReplicaAccessState,
        *,
        error_code: str = "",
    ) -> LinkedReplicaBinding:
        return LinkedReplicaBinding(
            server_url=self.server_url,
            server_instance_id=self.server_instance_id,
            remote_project_id=self.remote_project_id,
            project_uuid=self.project_uuid,
            replica_id=self.replica_id,
            authority_epoch=self.authority_epoch,
            last_applied_revision=self.last_applied_revision,
            cursor=self.cursor,
            snapshot_digest=self.snapshot_digest,
            blob_manifest_digest=self.blob_manifest_digest,
            account_profile_ref=self.account_profile_ref,
            state=state,
            last_verified_at=self.last_verified_at,
            last_error_code=error_code,
        )

    def to_storage_dict(self) -> dict[str, object]:
        return {
            "contract": LINKED_REPLICA_BINDING_CONTRACT,
            "server_url": self.server_url,
            "server_instance_id": self.server_instance_id.value,
            "remote_project_id": self.remote_project_id.value,
            "project_uuid": self.project_uuid.value,
            "replica_id": self.replica_id.value,
            "authority_epoch": self.authority_epoch.value,
            "last_applied_revision": self.last_applied_revision,
            "cursor": self.cursor,
            "snapshot_digest": self.snapshot_digest,
            "blob_manifest_digest": self.blob_manifest_digest,
            "account_profile_ref": self.account_profile_ref,
            "state": self.state.value,
            "last_verified_at": self.last_verified_at,
            "last_error_code": self.last_error_code,
        }

    def to_dict(self) -> dict[str, object]:
        payload = self.to_storage_dict()
        payload["snapshot_digest"] = f"sha256:{self.snapshot_digest}"
        payload["blob_manifest_digest"] = f"sha256:{self.blob_manifest_digest}"
        payload["writes_permitted"] = self.writes_permitted
        return payload


@dataclass(frozen=True)
class ReplicaFreshness:
    state: ReplicaAccessState
    source: str
    stale: bool
    last_applied_revision: int
    cursor: int
    last_verified_at: int
    writes_permitted: bool
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": LINKED_REPLICA_STATUS_CONTRACT,
            "state": self.state.value,
            "source": self.source,
            "stale": self.stale,
            "last_applied_revision": self.last_applied_revision,
            "cursor": self.cursor,
            "last_verified_at": self.last_verified_at or None,
            "writes_permitted": self.writes_permitted,
            "reason": self.reason or None,
        }


@dataclass(frozen=True)
class ReplicaOperationResult:
    status: str
    binding: LinkedReplicaBinding
    freshness: ReplicaFreshness
    integration_status: str = ""
    diagnostic_path: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": LINKED_REPLICA_PROTOCOL,
            "status": self.status,
            "binding": self.binding.to_dict(),
            "freshness": self.freshness.to_dict(),
            "integration_status": self.integration_status or None,
            "diagnostic_path": self.diagnostic_path or None,
            "message": self.message,
        }


def snapshot_manifest_from_mapping(raw: Mapping[str, object]) -> ReplicaSnapshotManifest:
    expected = {
        "contract",
        "status",
        "session_id",
        "server_instance_id",
        "remote_project_id",
        "project_uuid",
        "replica_id",
        "authority_epoch",
        "remote_revision",
        "cursor",
        "semantic_state_digest",
        "bundle_digest",
        "blob_manifest_digest",
        "bundle_size",
        "blobs",
        "expires_at",
    }
    blobs = raw.get("blobs")
    if (
        set(raw) != expected
        or raw.get("contract") != LINKED_REPLICA_SNAPSHOT_CONTRACT
        or not isinstance(blobs, list)
    ):
        raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: snapshot fields are not exact")
    parsed_blobs: list[ReplicaBlob] = []
    for item in blobs:
        if not isinstance(item, Mapping) or set(item) != {"digest", "size", "media_type"}:
            raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: blob entry is invalid")
        parsed_blobs.append(
            ReplicaBlob(
                digest=str(item["digest"]),
                size=item["size"],
                media_type=str(item["media_type"]),
            )
        )
    return ReplicaSnapshotManifest(
        session_id=str(raw["session_id"]),
        status=str(raw["status"]),
        server_instance_id=ServerInstanceId(str(raw["server_instance_id"])),
        remote_project_id=RemoteProjectId(str(raw["remote_project_id"])),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        replica_id=ReplicaId(str(raw["replica_id"])),
        authority_epoch=AuthorityEpoch(_positive_int(raw["authority_epoch"], "authority_epoch")),
        remote_revision=_positive_int(raw["remote_revision"], "remote_revision"),
        cursor=_non_negative_int(raw["cursor"], "cursor"),
        semantic_state_digest=str(raw["semantic_state_digest"]),
        bundle_digest=str(raw["bundle_digest"]),
        blob_manifest_digest=str(raw["blob_manifest_digest"]),
        bundle_size=_positive_int(raw["bundle_size"], "bundle_size"),
        blobs=tuple(parsed_blobs),
        expires_at=_positive_int(raw["expires_at"], "expires_at"),
    )


def linked_binding_from_mapping(raw: Mapping[str, object]) -> LinkedReplicaBinding:
    expected = {
        "contract",
        "server_url",
        "server_instance_id",
        "remote_project_id",
        "project_uuid",
        "replica_id",
        "authority_epoch",
        "last_applied_revision",
        "cursor",
        "snapshot_digest",
        "blob_manifest_digest",
        "account_profile_ref",
        "state",
        "last_verified_at",
        "last_error_code",
    }
    if set(raw) != expected or raw.get("contract") != LINKED_REPLICA_BINDING_CONTRACT:
        raise ValueError("P2P_LINKED_REPLICA_STATE_INVALID: binding fields are not exact")
    try:
        state = ReplicaAccessState(str(raw["state"]))
    except ValueError as exc:
        raise ValueError("P2P_LINKED_REPLICA_STATE_INVALID: access state is invalid") from exc
    return LinkedReplicaBinding(
        server_url=str(raw["server_url"]),
        server_instance_id=ServerInstanceId(str(raw["server_instance_id"])),
        remote_project_id=RemoteProjectId(str(raw["remote_project_id"])),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        replica_id=ReplicaId(str(raw["replica_id"])),
        authority_epoch=AuthorityEpoch(_positive_int(raw["authority_epoch"], "authority_epoch")),
        last_applied_revision=_positive_int(
            raw["last_applied_revision"], "last_applied_revision"
        ),
        cursor=_non_negative_int(raw["cursor"], "cursor"),
        snapshot_digest=str(raw["snapshot_digest"]),
        blob_manifest_digest=str(raw["blob_manifest_digest"]),
        account_profile_ref=str(raw["account_profile_ref"]),
        state=state,
        last_verified_at=_non_negative_int(raw["last_verified_at"], "last_verified_at"),
        last_error_code=str(raw["last_error_code"]),
    )


def _normalize_server_url(value: object) -> str:
    parsed = urlsplit(str(value or "").strip())
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not parsed.hostname
    ):
        raise ValueError("P2P_LINKED_REPLICA_INVALID: server URL is unsafe")
    if parsed.scheme == "https":
        pass
    elif parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        pass
    else:
        raise ValueError(
            "P2P_LINKED_REPLICA_INVALID: HTTPS is required outside loopback"
        )
    return urlunsplit(
        (parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", "")
    )

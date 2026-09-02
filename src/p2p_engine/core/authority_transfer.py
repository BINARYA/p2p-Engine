from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping
from urllib.parse import urlsplit

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.project_identity import (
    AuthorityEpoch,
    ProjectUuid,
    RemoteProjectId,
    ReplicaId,
    ServerInstanceId,
)

AUTHORITY_TRANSFER_PROTOCOL = "p2p-authority-transfer/v1"
AUTHORITY_TRANSFER_RECEIPT_CONTRACT = "p2p-authority-transfer-receipt/v1"
AUTHORITY_TRANSFER_CAPABILITY_CONTRACT = "p2p-authority-transfer-capabilities/v1"
AUTHORITY_TRANSFER_CAPABILITY_PATH = "/.well-known/p2p-authority-transfer"
LOCAL_AUTHORITY_TRANSFER_CONTRACT = "p2p-local-authority-transfer/v1"
LINKED_PROJECT_BINDING_CONTRACT = "p2p-linked-project-binding/v1"
AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES = 1_048_576
AUTHORITY_TRANSFER_MAX_BUNDLE_BYTES = 1_073_741_824
AUTHORITY_TRANSFER_MAX_BLOBS = 50_000
AUTHORITY_TRANSFER_MAX_BLOB_BYTES = 268_435_456

_SHA256 = re.compile(r"^(?:sha256:)?([0-9a-f]{64})$")
_TRANSFER_ID = re.compile(r"^tr_[0-9a-f]{32}$")
_PROFILE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+-]{0,255}$")
_ERROR_CODE = re.compile(r"^(?:P2P_[A-Z0-9_]+)?$")


def normalized_sha256(value: object, *, field_name: str) -> str:
    match = _SHA256.fullmatch(str(value or ""))
    if match is None:
        raise ValueError(
            f"P2P_AUTHORITY_TRANSFER_INVALID: {field_name} must be a lowercase SHA-256"
        )
    return match.group(1)


def safe_profile_ref(value: object, *, field_name: str) -> str:
    text = str(value or "")
    if not _PROFILE_REF.fullmatch(text):
        raise ValueError(
            f"P2P_AUTHORITY_TRANSFER_INVALID: {field_name} must be a bounded opaque identifier"
        )
    return text


class TransferState(str, Enum):
    preflighted = "preflighted"
    locally_fenced = "locally_fenced"
    remote_staging = "remote_staging"
    remote_committed = "remote_committed"
    local_binding_pending = "local_binding_pending"
    linked = "linked"
    rejected = "rejected"
    cancelled = "cancelled"
    expired = "expired"

    @property
    def local_writes_fenced(self) -> bool:
        return self in {
            TransferState.locally_fenced,
            TransferState.remote_staging,
            TransferState.remote_committed,
            TransferState.local_binding_pending,
        }

    @property
    def remote_authoritative(self) -> bool:
        return self in {
            TransferState.remote_committed,
            TransferState.local_binding_pending,
            TransferState.linked,
        }


@dataclass(frozen=True)
class OAuthDeviceConfiguration:
    device_authorization_endpoint: str
    token_endpoint: str
    client_id: str
    scopes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "device_authorization_endpoint": self.device_authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "client_id": self.client_id,
            "scopes": list(self.scopes),
        }


@dataclass(frozen=True)
class TransferEndpoints:
    eligibility: str
    sessions: str
    session: str
    manifest: str
    bundle: str
    blob: str
    commit: str
    cancel: str

    def to_dict(self) -> dict[str, str]:
        return {
            "eligibility": self.eligibility,
            "sessions": self.sessions,
            "session": self.session,
            "manifest": self.manifest,
            "bundle": self.bundle,
            "blob": self.blob,
            "commit": self.commit,
            "cancel": self.cancel,
        }


@dataclass(frozen=True)
class TransferCapabilities:
    server_url: str
    server_instance_id: ServerInstanceId
    endpoints: TransferEndpoints
    oauth_device: OAuthDeviceConfiguration
    max_bundle_bytes: int
    max_blob_bytes: int
    max_blobs: int
    protocol: str = AUTHORITY_TRANSFER_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != AUTHORITY_TRANSFER_PROTOCOL:
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_PROTOCOL_UNSUPPORTED: WaveKit transfer protocol differs"
            )
        if not 1 <= self.max_bundle_bytes <= AUTHORITY_TRANSFER_MAX_BUNDLE_BYTES:
            raise ValueError("P2P_AUTHORITY_TRANSFER_INVALID: unsafe bundle limit")
        if not 1 <= self.max_blob_bytes <= AUTHORITY_TRANSFER_MAX_BLOB_BYTES:
            raise ValueError("P2P_AUTHORITY_TRANSFER_INVALID: unsafe blob limit")
        if not 1 <= self.max_blobs <= AUTHORITY_TRANSFER_MAX_BLOBS:
            raise ValueError("P2P_AUTHORITY_TRANSFER_INVALID: unsafe blob-count limit")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": AUTHORITY_TRANSFER_CAPABILITY_CONTRACT,
            "protocol": self.protocol,
            "server_instance_id": self.server_instance_id.value,
            "endpoints": self.endpoints.to_dict(),
            "oauth_device": self.oauth_device.to_dict(),
            "limits": {
                "max_bundle_bytes": self.max_bundle_bytes,
                "max_blob_bytes": self.max_blob_bytes,
                "max_blobs": self.max_blobs,
            },
        }


@dataclass(frozen=True)
class WaveKitCredential:
    access_token: str
    refresh_token: str = ""
    token_type: str = "Bearer"
    expires_at: int = 0
    scopes: tuple[str, ...] = ()
    account_profile_ref: str = ""

    def __post_init__(self) -> None:
        if not self.access_token:
            raise ValueError("P2P_WAVEKIT_CREDENTIAL_INVALID: access token is required")

    def public_dict(self) -> dict[str, object]:
        return {
            "authenticated": True,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "scopes": list(self.scopes),
            "account_profile_ref": self.account_profile_ref or None,
        }


@dataclass(frozen=True)
class DeviceAuthorization:
    device_code: str = field(repr=False)
    user_code: str
    verification_uri: str
    verification_uri_complete: str = ""
    expires_in: int = 600
    interval: int = 5

    def public_dict(self) -> dict[str, object]:
        return {
            "user_code": self.user_code,
            "verification_uri": self.verification_uri,
            "verification_uri_complete": self.verification_uri_complete,
            "expires_in": self.expires_in,
            "interval": self.interval,
        }


@dataclass(frozen=True)
class AuthorityTransferPreview:
    transfer_id: str
    request_fingerprint: str
    preview_token: str
    project_uuid: ProjectUuid
    source_revision: str
    semantic_state_digest: str
    bundle_digest: str
    blob_manifest_digest: str
    server_url: str
    server_instance_id: ServerInstanceId
    owner_profile_ref: str
    storage_adapter: str
    entity_count: int
    relation_count: int
    blob_count: int
    blob_bytes: int
    source_authority_epoch: AuthorityEpoch = AuthorityEpoch(1)
    blockers: tuple[str, ...] = ()

    @property
    def eligible(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": AUTHORITY_TRANSFER_PROTOCOL,
            "operation": "transfer-authority",
            "eligible": self.eligible,
            "transfer_id": self.transfer_id,
            "request_fingerprint": f"sha256:{self.request_fingerprint}",
            "preview_token": self.preview_token,
            "project_uuid": self.project_uuid.value,
            "source_revision": self.source_revision,
            "semantic_state_digest": f"sha256:{self.semantic_state_digest}",
            "bundle_digest": f"sha256:{self.bundle_digest}",
            "blob_manifest_digest": f"sha256:{self.blob_manifest_digest}",
            "destination": {
                "server_url": self.server_url,
                "server_instance_id": self.server_instance_id.value,
                "owner_profile_ref": self.owner_profile_ref,
            },
            "source_authority_epoch": self.source_authority_epoch.value,
            "storage_adapter": self.storage_adapter,
            "counts": {
                "entities": self.entity_count,
                "relations": self.relation_count,
                "blobs": self.blob_count,
                "blob_bytes": self.blob_bytes,
            },
            "authority_change": {"from": "local", "to": "wavekit"},
            "confirmation_required": True,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class AuthorityTransferSession:
    transfer_id: str
    request_fingerprint: str
    state: TransferState
    project_uuid: ProjectUuid
    source_revision: str
    semantic_state_digest: str
    bundle_digest: str
    blob_manifest_digest: str
    server_url: str
    server_instance_id: ServerInstanceId
    owner_profile_ref: str
    source_authority_epoch: AuthorityEpoch
    required_blobs: tuple[str, ...]
    last_error_code: str = ""

    def __post_init__(self) -> None:
        if not _TRANSFER_ID.fullmatch(self.transfer_id):
            raise ValueError("P2P_AUTHORITY_TRANSFER_INVALID: transfer_id is invalid")
        object.__setattr__(
            self,
            "request_fingerprint",
            normalized_sha256(self.request_fingerprint, field_name="request_fingerprint"),
        )
        object.__setattr__(
            self,
            "source_revision",
            normalized_sha256(self.source_revision, field_name="source_revision"),
        )
        object.__setattr__(
            self, "semantic_state_digest", normalized_sha256(
                self.semantic_state_digest, field_name="semantic_state_digest"
            )
        )
        object.__setattr__(
            self, "bundle_digest", normalized_sha256(self.bundle_digest, field_name="bundle_digest")
        )
        object.__setattr__(
            self,
            "blob_manifest_digest",
            normalized_sha256(self.blob_manifest_digest, field_name="blob_manifest_digest"),
        )
        safe_profile_ref(self.owner_profile_ref, field_name="owner_profile_ref")
        parsed_server = urlsplit(self.server_url)
        if (
            parsed_server.username is not None
            or parsed_server.password is not None
            or parsed_server.query
            or parsed_server.fragment
            or not parsed_server.hostname
            or parsed_server.scheme not in {"http", "https"}
            or (
                parsed_server.scheme == "http"
                and parsed_server.hostname not in {"localhost", "127.0.0.1", "::1"}
            )
        ):
            raise ValueError("P2P_AUTHORITY_TRANSFER_INVALID: unsafe server URL")
        if not _ERROR_CODE.fullmatch(self.last_error_code):
            raise ValueError("P2P_AUTHORITY_TRANSFER_INVALID: last_error_code is invalid")
        normalized = tuple(
            sorted(normalized_sha256(item, field_name="required blob digest") for item in self.required_blobs)
        )
        if len(normalized) != len(set(normalized)) or len(normalized) > AUTHORITY_TRANSFER_MAX_BLOBS:
            raise ValueError("P2P_AUTHORITY_TRANSFER_INVALID: required blob set is invalid")
        object.__setattr__(self, "required_blobs", normalized)

    @property
    def local_writes_fenced(self) -> bool:
        return self.state.local_writes_fenced

    def with_state(self, state: TransferState, *, last_error_code: str = "") -> AuthorityTransferSession:
        return AuthorityTransferSession(
            transfer_id=self.transfer_id,
            request_fingerprint=self.request_fingerprint,
            state=state,
            project_uuid=self.project_uuid,
            source_revision=self.source_revision,
            semantic_state_digest=self.semantic_state_digest,
            bundle_digest=self.bundle_digest,
            blob_manifest_digest=self.blob_manifest_digest,
            server_url=self.server_url,
            server_instance_id=self.server_instance_id,
            owner_profile_ref=self.owner_profile_ref,
            source_authority_epoch=self.source_authority_epoch,
            required_blobs=self.required_blobs,
            last_error_code=last_error_code,
        )

    def to_storage_dict(self) -> dict[str, object]:
        return {
            "transfer_id": self.transfer_id,
            "request_fingerprint": self.request_fingerprint,
            "state": self.state.value,
            "project_uuid": self.project_uuid.value,
            "source_revision": self.source_revision,
            "semantic_state_digest": self.semantic_state_digest,
            "bundle_digest": self.bundle_digest,
            "blob_manifest_digest": self.blob_manifest_digest,
            "server_url": self.server_url,
            "server_instance_id": self.server_instance_id.value,
            "owner_profile_ref": self.owner_profile_ref,
            "source_authority_epoch": self.source_authority_epoch.value,
            "required_blobs": list(self.required_blobs),
            "last_error_code": self.last_error_code,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": AUTHORITY_TRANSFER_PROTOCOL,
            **self.to_storage_dict(),
            "request_fingerprint": f"sha256:{self.request_fingerprint}",
            "semantic_state_digest": f"sha256:{self.semantic_state_digest}",
            "bundle_digest": f"sha256:{self.bundle_digest}",
            "blob_manifest_digest": f"sha256:{self.blob_manifest_digest}",
            "local_writes_fenced": self.local_writes_fenced,
            "remote_authoritative": self.state.remote_authoritative,
        }


@dataclass(frozen=True)
class AuthorityActivationReceipt:
    transfer_id: str
    request_fingerprint: str
    project_uuid: ProjectUuid
    server_instance_id: ServerInstanceId
    remote_project_id: RemoteProjectId
    authority_epoch: AuthorityEpoch
    remote_revision: int
    replica_id: ReplicaId
    bundle_digest: str
    blob_manifest_digest: str
    required_blobs: tuple[str, ...]
    account_profile_ref: str
    cursor: int = 0
    status: str = "committed"

    def __post_init__(self) -> None:
        if self.status != "committed" or not _TRANSFER_ID.fullmatch(self.transfer_id):
            raise ValueError("P2P_AUTHORITY_TRANSFER_RECEIPT_INVALID: receipt status or ID is invalid")
        if self.remote_revision < 1 or self.cursor < 0:
            raise ValueError("P2P_AUTHORITY_TRANSFER_RECEIPT_INVALID: revision or cursor is invalid")
        object.__setattr__(
            self,
            "request_fingerprint",
            normalized_sha256(self.request_fingerprint, field_name="request_fingerprint"),
        )
        object.__setattr__(
            self, "bundle_digest", normalized_sha256(self.bundle_digest, field_name="bundle_digest")
        )
        object.__setattr__(
            self,
            "blob_manifest_digest",
            normalized_sha256(self.blob_manifest_digest, field_name="blob_manifest_digest"),
        )
        safe_profile_ref(self.account_profile_ref, field_name="account_profile_ref")
        object.__setattr__(
            self,
            "required_blobs",
            tuple(sorted(normalized_sha256(item, field_name="required blob digest") for item in self.required_blobs)),
        )
        if len(self.required_blobs) != len(set(self.required_blobs)):
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_RECEIPT_INVALID: required blob set has duplicates"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": AUTHORITY_TRANSFER_RECEIPT_CONTRACT,
            "status": self.status,
            "transfer_id": self.transfer_id,
            "request_fingerprint": f"sha256:{self.request_fingerprint}",
            "project_uuid": self.project_uuid.value,
            "server_instance_id": self.server_instance_id.value,
            "remote_project_id": self.remote_project_id.value,
            "authority_epoch": self.authority_epoch.value,
            "remote_revision": self.remote_revision,
            "replica_id": self.replica_id.value,
            "bundle_digest": f"sha256:{self.bundle_digest}",
            "blob_manifest_digest": f"sha256:{self.blob_manifest_digest}",
            "required_blobs": [f"sha256:{item}" for item in self.required_blobs],
            "account_profile_ref": self.account_profile_ref,
            "cursor": self.cursor,
        }

    @property
    def receipt_digest(self) -> str:
        return semantic_sha256(self.to_dict())


@dataclass(frozen=True)
class AuthorityTransferResult:
    status: str
    session: AuthorityTransferSession
    receipt: AuthorityActivationReceipt | None = None
    integration_status: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": AUTHORITY_TRANSFER_PROTOCOL,
            "status": self.status,
            "session": self.session.to_dict(),
            "receipt": self.receipt.to_dict() if self.receipt is not None else None,
            "integration_status": self.integration_status or None,
            "message": self.message,
        }


def transfer_id_for(project_uuid: ProjectUuid, operation_key: str, server_instance_id: ServerInstanceId) -> str:
    if not operation_key.strip() or len(operation_key.encode("utf-8")) > 512:
        raise ValueError("P2P_IDEMPOTENCY_KEY_REQUIRED: bounded operation key is required")
    digest = semantic_sha256(
        {
            "operation": "transfer-authority",
            "operation_key": operation_key,
            "project_uuid": project_uuid.value,
            "server_instance_id": server_instance_id.value,
        }
    )
    return f"tr_{digest[:32]}"


def session_from_mapping(raw: Mapping[str, object]) -> AuthorityTransferSession:
    expected = {
        "transfer_id", "request_fingerprint", "state", "project_uuid", "source_revision",
        "semantic_state_digest", "bundle_digest", "blob_manifest_digest", "server_url",
        "server_instance_id", "owner_profile_ref", "source_authority_epoch", "required_blobs",
        "last_error_code",
    }
    if set(raw) != expected or not isinstance(raw.get("required_blobs"), list):
        raise ValueError("P2P_AUTHORITY_TRANSFER_STATE_INVALID: local transfer fields are invalid")
    return AuthorityTransferSession(
        transfer_id=str(raw["transfer_id"]),
        request_fingerprint=str(raw["request_fingerprint"]),
        state=TransferState(str(raw["state"])),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        source_revision=str(raw["source_revision"]),
        semantic_state_digest=str(raw["semantic_state_digest"]),
        bundle_digest=str(raw["bundle_digest"]),
        blob_manifest_digest=str(raw["blob_manifest_digest"]),
        server_url=str(raw["server_url"]),
        server_instance_id=ServerInstanceId(str(raw["server_instance_id"])),
        owner_profile_ref=str(raw["owner_profile_ref"]),
        source_authority_epoch=AuthorityEpoch(int(raw["source_authority_epoch"])),
        required_blobs=tuple(str(item) for item in raw["required_blobs"]),
        last_error_code=str(raw["last_error_code"]),
    )


def receipt_from_mapping(raw: Mapping[str, object]) -> AuthorityActivationReceipt:
    expected = {
        "contract", "status", "transfer_id", "request_fingerprint", "project_uuid",
        "server_instance_id", "remote_project_id", "authority_epoch", "remote_revision",
        "replica_id", "bundle_digest", "blob_manifest_digest", "required_blobs",
        "account_profile_ref", "cursor",
    }
    if set(raw) != expected or raw.get("contract") != AUTHORITY_TRANSFER_RECEIPT_CONTRACT:
        raise ValueError("P2P_AUTHORITY_TRANSFER_RECEIPT_INVALID: receipt fields are not exact")
    required = raw.get("required_blobs")
    if not isinstance(required, list):
        raise ValueError("P2P_AUTHORITY_TRANSFER_RECEIPT_INVALID: required_blobs must be a list")
    return AuthorityActivationReceipt(
        transfer_id=str(raw["transfer_id"]),
        request_fingerprint=str(raw["request_fingerprint"]),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        server_instance_id=ServerInstanceId(str(raw["server_instance_id"])),
        remote_project_id=RemoteProjectId(str(raw["remote_project_id"])),
        authority_epoch=AuthorityEpoch(int(raw["authority_epoch"])),
        remote_revision=int(raw["remote_revision"]),
        replica_id=ReplicaId(str(raw["replica_id"])),
        bundle_digest=str(raw["bundle_digest"]),
        blob_manifest_digest=str(raw["blob_manifest_digest"]),
        required_blobs=tuple(str(item) for item in required),
        account_profile_ref=str(raw["account_profile_ref"]),
        cursor=int(raw["cursor"]),
        status=str(raw["status"]),
    )

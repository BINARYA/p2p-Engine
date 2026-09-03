from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from p2p_engine.core.authority_transfer import normalized_sha256
from p2p_engine.core.canonical_memory import (
    canonical_json_bytes,
    normalize_semantic_value,
    semantic_sha256,
)
from p2p_engine.core.project_identity import (
    AuthorityEpoch,
    ProjectUuid,
    RemoteProjectId,
    ReplicaId,
)

PROJECT_REPLICATION_PROTOCOL = "p2p-durable-replication/v1"
PROJECT_COMMAND_CONTRACT = "p2p-project-command/v1"
PROJECT_OPERATION_RECEIPT_CONTRACT = "p2p-project-operation-receipt/v1"
PROJECT_CHANGE_BATCH_CONTRACT = "p2p-project-change-batch/v1"
PROJECT_CHANGE_FEED_CONTRACT = "p2p-project-change-feed/v1"
PROJECT_NOTIFICATION_CONTRACT = "wavekit-project-notification/v1"
PROJECT_ACTIVITY_CONTRACT = "wavekit-project-activity/v1"
PROJECT_PRESENCE_CONTRACT = "wavekit-project-presence/v1"

MAX_COMMAND_BYTES = 1_048_576
MAX_BATCH_BYTES = 8_388_608
MAX_FEED_BYTES = 16_777_216
MAX_BATCH_ENTITIES = 4096
MAX_BATCH_BLOBS = 1024
MAX_FEED_BATCHES = 128

_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_CONTRACT = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,127}/v[1-9][0-9]*$")
_COMMAND = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_ERROR = re.compile(r"^P2P_[A-Z0-9_]{2,126}$")


def _bounded_id(value: object, field: str) -> str:
    text = str(value or "")
    if not _OPAQUE_ID.fullmatch(text):
        raise ValueError(f"P2P_REPLICATION_INVALID: {field} is invalid")
    return text


def _contract(value: object, field: str) -> str:
    text = str(value or "")
    if not _CONTRACT.fullmatch(text):
        raise ValueError(f"P2P_REPLICATION_INVALID: {field} is invalid")
    return text


def _revision(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"P2P_REPLICATION_INVALID: {field} must be non-negative")
    return value


def _positive(value: object, field: str) -> int:
    result = _revision(value, field)
    if result < 1:
        raise ValueError(f"P2P_REPLICATION_INVALID: {field} must be positive")
    return result


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"P2P_REPLICATION_INVALID: {field} must be a mapping")
    normalized = normalize_semantic_value(value)
    if not isinstance(normalized, Mapping):
        raise ValueError(f"P2P_REPLICATION_INVALID: {field} normalization failed")
    return normalized


def _exact(raw: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(raw) != expected:
        raise ValueError(f"P2P_REPLICATION_INVALID: {label} fields are not exact")


def _bounded(value: object, *, maximum: int, label: str) -> None:
    if len(canonical_json_bytes(value)) > maximum:
        raise ValueError(f"P2P_REPLICATION_PAYLOAD_TOO_LARGE: {label} exceeds its limit")


def replication_entity_version(
    *,
    kind: str,
    entity_id: str,
    payload_contract: str,
    payload: Mapping[str, object],
) -> int:
    """Return a stable positive optimistic-concurrency token for logical state."""
    digest = semantic_sha256(
        {
            "kind": kind,
            "id": entity_id,
            "payload_contract": payload_contract,
            "payload": payload,
        }
    )
    # Fifteen hex digits fit safely in signed 64-bit database integers.  Zero
    # remains reserved for an expected-absence precondition.
    return int(digest[:15], 16) + 1


@dataclass(frozen=True, order=True)
class EntityPrecondition:
    kind: str
    entity_id: str
    expected_version: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _bounded_id(self.kind, "entity kind"))
        object.__setattr__(self, "entity_id", _bounded_id(self.entity_id, "entity id"))
        _revision(self.expected_version, "expected entity version")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "id": self.entity_id,
            "expected_version": self.expected_version,
        }


@dataclass(frozen=True)
class ProjectCommand:
    operation_id: str
    idempotency_key: str
    project_uuid: ProjectUuid
    remote_project_id: RemoteProjectId
    replica_id: ReplicaId
    authority_epoch: AuthorityEpoch
    expected_project_revision: int
    entity_preconditions: tuple[EntityPrecondition, ...]
    command: str
    payload_contract: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_id", _bounded_id(self.operation_id, "operation_id"))
        object.__setattr__(
            self, "idempotency_key", _bounded_id(self.idempotency_key, "idempotency_key")
        )
        _revision(self.expected_project_revision, "expected_project_revision")
        if not _COMMAND.fullmatch(self.command):
            raise ValueError("P2P_REPLICATION_INVALID: command is invalid")
        object.__setattr__(self, "payload_contract", _contract(self.payload_contract, "payload_contract"))
        normalized = _mapping(self.payload, "payload")
        object.__setattr__(self, "payload", normalized)
        ordered = tuple(sorted(self.entity_preconditions))
        if len(ordered) != len(set((item.kind, item.entity_id) for item in ordered)):
            raise ValueError("P2P_REPLICATION_INVALID: entity preconditions contain duplicates")
        object.__setattr__(self, "entity_preconditions", ordered)
        _bounded(self.to_dict(), maximum=MAX_COMMAND_BYTES, label="command")

    @property
    def fingerprint(self) -> str:
        return semantic_sha256(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_COMMAND_CONTRACT,
            "operation_id": self.operation_id,
            "idempotency_key": self.idempotency_key,
            "project_uuid": self.project_uuid.value,
            "remote_project_id": self.remote_project_id.value,
            "replica_id": self.replica_id.value,
            "authority_epoch": self.authority_epoch.value,
            "expected_project_revision": self.expected_project_revision,
            "entity_preconditions": [item.to_dict() for item in self.entity_preconditions],
            "command": self.command,
            "payload_contract": self.payload_contract,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class ReplicationError:
    code: str
    message: str
    details: Mapping[str, object]

    def __post_init__(self) -> None:
        if not _ERROR.fullmatch(self.code):
            raise ValueError("P2P_REPLICATION_INVALID: error code is invalid")
        if not self.message or len(self.message.encode("utf-8")) > 2048:
            raise ValueError("P2P_REPLICATION_INVALID: error message is invalid")
        object.__setattr__(self, "details", _mapping(self.details, "error details"))

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


@dataclass(frozen=True)
class OperationReceipt:
    operation_id: str
    idempotency_key: str
    command_fingerprint: str
    status: str
    project_uuid: ProjectUuid
    authority_epoch: AuthorityEpoch
    base_project_revision: int
    project_revision: int | None
    change_batch_id: str | None
    result_contract: str | None
    result: Mapping[str, object] | None
    error: ReplicationError | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_id", _bounded_id(self.operation_id, "operation_id"))
        object.__setattr__(
            self,
            "idempotency_key",
            _bounded_id(self.idempotency_key, "idempotency_key"),
        )
        object.__setattr__(
            self,
            "command_fingerprint",
            normalized_sha256(
                self.command_fingerprint,
                field_name="command_fingerprint",
            ),
        )
        if self.status not in {"completed", "rejected", "conflicted", "failed"}:
            raise ValueError("P2P_REPLICATION_INVALID: receipt status is invalid")
        _revision(self.base_project_revision, "base_project_revision")
        if self.status == "completed":
            if self.project_revision is None:
                raise ValueError("P2P_REPLICATION_INVALID: completed receipt lacks revision")
            _revision(self.project_revision, "project_revision")
            if self.project_revision < self.base_project_revision:
                raise ValueError("P2P_REPLICATION_INVALID: receipt revision regresses")
            if self.change_batch_id is not None:
                object.__setattr__(
                    self, "change_batch_id", _bounded_id(self.change_batch_id, "change_batch_id")
                )
                if self.project_revision != self.base_project_revision + 1:
                    raise ValueError(
                        "P2P_REPLICATION_INVALID: changed receipt revision is not contiguous"
                    )
            elif self.project_revision != self.base_project_revision:
                raise ValueError(
                    "P2P_REPLICATION_INVALID: no-op receipt must keep its base revision"
                )
            if self.result_contract is None or self.result is None:
                raise ValueError("P2P_REPLICATION_INVALID: completed receipt lacks result")
            object.__setattr__(
                self, "result_contract", _contract(self.result_contract, "result_contract")
            )
            object.__setattr__(self, "result", _mapping(self.result, "result"))
            if self.error is not None:
                raise ValueError("P2P_REPLICATION_INVALID: completed receipt contains an error")
        else:
            if any(
                value is not None
                for value in (
                    self.project_revision,
                    self.change_batch_id,
                    self.result_contract,
                    self.result,
                )
            ) or self.error is None:
                raise ValueError("P2P_REPLICATION_INVALID: unsuccessful receipt fields differ")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_OPERATION_RECEIPT_CONTRACT,
            "operation_id": self.operation_id,
            "idempotency_key": self.idempotency_key,
            "command_fingerprint": f"sha256:{self.command_fingerprint}",
            "status": self.status,
            "project_uuid": self.project_uuid.value,
            "authority_epoch": self.authority_epoch.value,
            "base_project_revision": self.base_project_revision,
            "project_revision": self.project_revision,
            "change_batch_id": self.change_batch_id,
            "result_contract": self.result_contract,
            "result": dict(self.result) if self.result is not None else None,
            "error": self.error.to_dict() if self.error is not None else None,
        }


@dataclass(frozen=True, order=True)
class ChangeUpsert:
    kind: str
    entity_id: str
    entity_version: int
    payload_contract: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _bounded_id(self.kind, "entity kind"))
        object.__setattr__(self, "entity_id", _bounded_id(self.entity_id, "entity id"))
        _positive(self.entity_version, "entity_version")
        object.__setattr__(self, "payload_contract", _contract(self.payload_contract, "payload_contract"))
        object.__setattr__(self, "payload", _mapping(self.payload, "entity payload"))

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "id": self.entity_id,
            "entity_version": self.entity_version,
            "payload_contract": self.payload_contract,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, order=True)
class ChangeTombstone:
    kind: str
    entity_id: str
    previous_entity_version: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _bounded_id(self.kind, "entity kind"))
        object.__setattr__(self, "entity_id", _bounded_id(self.entity_id, "entity id"))
        _positive(self.previous_entity_version, "previous_entity_version")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "id": self.entity_id,
            "previous_entity_version": self.previous_entity_version,
        }


@dataclass(frozen=True, order=True)
class ChangeBlobReference:
    digest: str
    size: int
    media_type: str = "application/octet-stream"

    def __post_init__(self) -> None:
        object.__setattr__(self, "digest", normalized_sha256(self.digest, field_name="blob digest"))
        _revision(self.size, "blob size")
        if not self.media_type or len(self.media_type) > 128 or any(ord(char) < 32 for char in self.media_type):
            raise ValueError("P2P_REPLICATION_INVALID: blob media type is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "digest": f"sha256:{self.digest}",
            "size": self.size,
            "media_type": self.media_type,
        }


@dataclass(frozen=True)
class ChangeBatch:
    change_batch_id: str
    project_uuid: ProjectUuid
    authority_epoch: AuthorityEpoch
    previous_revision: int
    project_revision: int
    operation_id: str
    upserts: tuple[ChangeUpsert, ...]
    tombstones: tuple[ChangeTombstone, ...]
    blob_references: tuple[ChangeBlobReference, ...]
    semantic_state_digest: str
    blob_manifest_digest: str
    batch_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "change_batch_id", _bounded_id(self.change_batch_id, "change_batch_id")
        )
        object.__setattr__(self, "operation_id", _bounded_id(self.operation_id, "operation_id"))
        _revision(self.previous_revision, "previous_revision")
        _positive(self.project_revision, "project_revision")
        if self.project_revision != self.previous_revision + 1:
            raise ValueError("P2P_REPLICATION_CURSOR_GAP: batch revisions are not contiguous")
        if len(self.upserts) + len(self.tombstones) > MAX_BATCH_ENTITIES:
            raise ValueError("P2P_REPLICATION_PAYLOAD_TOO_LARGE: batch has too many entities")
        if len(self.blob_references) > MAX_BATCH_BLOBS:
            raise ValueError("P2P_REPLICATION_PAYLOAD_TOO_LARGE: batch has too many blobs")
        if not self.upserts and not self.tombstones and not self.blob_references:
            raise ValueError("P2P_REPLICATION_INVALID: empty changes require a no-op receipt")
        upserts = tuple(sorted(self.upserts))
        tombstones = tuple(sorted(self.tombstones))
        blobs = tuple(sorted(self.blob_references))
        keys = [(item.kind, item.entity_id) for item in (*upserts, *tombstones)]
        if len(keys) != len(set(keys)):
            raise ValueError("P2P_REPLICATION_INVALID: batch repeats an entity")
        if len(blobs) != len(set(item.digest for item in blobs)):
            raise ValueError("P2P_REPLICATION_INVALID: batch repeats a blob")
        object.__setattr__(self, "upserts", upserts)
        object.__setattr__(self, "tombstones", tombstones)
        object.__setattr__(self, "blob_references", blobs)
        object.__setattr__(
            self,
            "semantic_state_digest",
            normalized_sha256(self.semantic_state_digest, field_name="semantic_state_digest"),
        )
        object.__setattr__(
            self,
            "blob_manifest_digest",
            normalized_sha256(self.blob_manifest_digest, field_name="blob_manifest_digest"),
        )
        digest = semantic_sha256(self._unsigned_dict())
        if self.batch_digest:
            supplied = normalized_sha256(self.batch_digest, field_name="batch_digest")
            if supplied != digest:
                raise ValueError("P2P_REPLICATION_DIGEST_MISMATCH: change batch digest differs")
        object.__setattr__(self, "batch_digest", digest)
        _bounded(self.to_dict(), maximum=MAX_BATCH_BYTES, label="change batch")

    def _unsigned_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_CHANGE_BATCH_CONTRACT,
            "change_batch_id": self.change_batch_id,
            "project_uuid": self.project_uuid.value,
            "authority_epoch": self.authority_epoch.value,
            "previous_revision": self.previous_revision,
            "project_revision": self.project_revision,
            "operation_id": self.operation_id,
            "upserts": [item.to_dict() for item in self.upserts],
            "tombstones": [item.to_dict() for item in self.tombstones],
            "blob_references": [item.to_dict() for item in self.blob_references],
            "semantic_state_digest": f"sha256:{self.semantic_state_digest}",
            "blob_manifest_digest": f"sha256:{self.blob_manifest_digest}",
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._unsigned_dict(), "batch_digest": f"sha256:{self.batch_digest}"}


@dataclass(frozen=True)
class ChangeFeed:
    status: str
    project_uuid: ProjectUuid
    replica_id: ReplicaId
    authority_epoch: AuthorityEpoch
    after_revision: int
    oldest_available_revision: int
    current_revision: int
    batches: tuple[ChangeBatch, ...]
    has_more: bool
    snapshot: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if self.status not in {"up-to-date", "changes", "retention-gap"}:
            raise ValueError("P2P_REPLICATION_INVALID: feed status is invalid")
        for name in ("after_revision", "oldest_available_revision", "current_revision"):
            _revision(getattr(self, name), name)
        if self.after_revision > self.current_revision:
            raise ValueError("P2P_REPLICATION_CURSOR_REGRESSION: feed cursor exceeds head")
        if len(self.batches) > MAX_FEED_BATCHES:
            raise ValueError("P2P_REPLICATION_PAYLOAD_TOO_LARGE: feed page has too many batches")
        if self.status == "retention-gap":
            if self.batches or self.snapshot is None:
                raise ValueError("P2P_REPLICATION_INVALID: retention gap requires only snapshot")
            if self.after_revision >= self.oldest_available_revision - 1 or self.has_more:
                raise ValueError("P2P_REPLICATION_INVALID: retention gap boundary differs")
        elif self.snapshot is not None:
            raise ValueError("P2P_REPLICATION_INVALID: normal feed cannot contain snapshot")
        expected = self.after_revision
        for batch in self.batches:
            if batch.project_uuid != self.project_uuid or batch.authority_epoch != self.authority_epoch:
                raise ValueError("P2P_REPLICATION_IDENTITY_MISMATCH: feed batch identity differs")
            if batch.previous_revision != expected:
                raise ValueError("P2P_REPLICATION_CURSOR_GAP: feed batches are not contiguous")
            expected = batch.project_revision
        if self.status == "up-to-date" and (self.batches or self.after_revision != self.current_revision):
            raise ValueError("P2P_REPLICATION_INVALID: up-to-date feed progress differs")
        if self.status == "changes" and not self.batches:
            raise ValueError("P2P_REPLICATION_INVALID: changes feed is empty")
        if self.status != "retention-gap":
            expected_more = expected < self.current_revision
            if self.has_more != expected_more:
                raise ValueError("P2P_REPLICATION_INVALID: feed pagination flag differs")
        _bounded(self.to_dict(), maximum=MAX_FEED_BYTES, label="change feed")

    @property
    def to_revision(self) -> int:
        return self.batches[-1].project_revision if self.batches else self.after_revision

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_CHANGE_FEED_CONTRACT,
            "status": self.status,
            "project_uuid": self.project_uuid.value,
            "replica_id": self.replica_id.value,
            "authority_epoch": self.authority_epoch.value,
            "after_revision": self.after_revision,
            "oldest_available_revision": self.oldest_available_revision,
            "current_revision": self.current_revision,
            "batches": [item.to_dict() for item in self.batches],
            "has_more": self.has_more,
            "snapshot": dict(self.snapshot) if self.snapshot is not None else None,
        }


@dataclass(frozen=True)
class ProjectNotification:
    event_id: str
    kind: str
    project_uuid: ProjectUuid
    project_revision: int
    change_batch_id: str | None
    operation_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _bounded_id(self.event_id, "event_id"))
        if self.kind not in {"project.revision.available", "operation.state.changed", "heartbeat"}:
            raise ValueError("P2P_REPLICATION_INVALID: notification kind is invalid")
        _revision(self.project_revision, "project_revision")
        for field in ("change_batch_id", "operation_id"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _bounded_id(value, field))

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_NOTIFICATION_CONTRACT,
            "event_id": self.event_id,
            "kind": self.kind,
            "project_uuid": self.project_uuid.value,
            "project_revision": self.project_revision,
            "change_batch_id": self.change_batch_id,
            "operation_id": self.operation_id,
        }


def command_from_mapping(raw: Mapping[str, object]) -> ProjectCommand:
    _exact(
        raw,
        {
            "contract", "operation_id", "idempotency_key", "project_uuid",
            "remote_project_id", "replica_id", "authority_epoch",
            "expected_project_revision", "entity_preconditions", "command",
            "payload_contract", "payload",
        },
        "command",
    )
    if raw.get("contract") != PROJECT_COMMAND_CONTRACT:
        raise ValueError("P2P_REPLICATION_PROTOCOL_UNSUPPORTED: command contract differs")
    preconditions = raw.get("entity_preconditions")
    if not isinstance(preconditions, list) or len(preconditions) > MAX_BATCH_ENTITIES:
        raise ValueError("P2P_REPLICATION_INVALID: entity_preconditions is invalid")
    parsed: list[EntityPrecondition] = []
    for item in preconditions:
        value = _mapping(item, "entity precondition")
        _exact(value, {"kind", "id", "expected_version"}, "entity precondition")
        parsed.append(EntityPrecondition(str(value["kind"]), str(value["id"]), value["expected_version"]))
    return ProjectCommand(
        operation_id=str(raw["operation_id"]),
        idempotency_key=str(raw["idempotency_key"]),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        remote_project_id=RemoteProjectId(str(raw["remote_project_id"])),
        replica_id=ReplicaId(str(raw["replica_id"])),
        authority_epoch=AuthorityEpoch(_positive(raw["authority_epoch"], "authority_epoch")),
        expected_project_revision=_revision(raw["expected_project_revision"], "expected_project_revision"),
        entity_preconditions=tuple(parsed),
        command=str(raw["command"]),
        payload_contract=str(raw["payload_contract"]),
        payload=_mapping(raw["payload"], "payload"),
    )


def error_from_mapping(raw: Mapping[str, object]) -> ReplicationError:
    _exact(raw, {"code", "message", "details"}, "error")
    return ReplicationError(str(raw["code"]), str(raw["message"]), _mapping(raw["details"], "details"))


def receipt_from_mapping(raw: Mapping[str, object]) -> OperationReceipt:
    _exact(
        raw,
        {
            "contract", "operation_id", "idempotency_key", "command_fingerprint",
            "status", "project_uuid", "authority_epoch",
            "base_project_revision", "project_revision", "change_batch_id",
            "result_contract", "result", "error",
        },
        "operation receipt",
    )
    if raw.get("contract") != PROJECT_OPERATION_RECEIPT_CONTRACT:
        raise ValueError("P2P_REPLICATION_PROTOCOL_UNSUPPORTED: receipt contract differs")
    error = raw.get("error")
    return OperationReceipt(
        operation_id=str(raw["operation_id"]),
        idempotency_key=str(raw["idempotency_key"]),
        command_fingerprint=str(raw["command_fingerprint"]),
        status=str(raw["status"]),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        authority_epoch=AuthorityEpoch(_positive(raw["authority_epoch"], "authority_epoch")),
        base_project_revision=_revision(raw["base_project_revision"], "base_project_revision"),
        project_revision=(None if raw["project_revision"] is None else _revision(raw["project_revision"], "project_revision")),
        change_batch_id=(None if raw["change_batch_id"] is None else str(raw["change_batch_id"])),
        result_contract=(None if raw["result_contract"] is None else str(raw["result_contract"])),
        result=(None if raw["result"] is None else _mapping(raw["result"], "result")),
        error=(None if error is None else error_from_mapping(_mapping(error, "error"))),
    )


def batch_from_mapping(raw: Mapping[str, object]) -> ChangeBatch:
    _exact(
        raw,
        {
            "contract", "change_batch_id", "project_uuid", "authority_epoch",
            "previous_revision", "project_revision", "operation_id", "upserts",
            "tombstones", "blob_references", "semantic_state_digest",
            "blob_manifest_digest", "batch_digest",
        },
        "change batch",
    )
    if raw.get("contract") != PROJECT_CHANGE_BATCH_CONTRACT:
        raise ValueError("P2P_REPLICATION_PROTOCOL_UNSUPPORTED: change-batch contract differs")
    upserts = raw.get("upserts")
    tombstones = raw.get("tombstones")
    blobs = raw.get("blob_references")
    if not isinstance(upserts, list) or not isinstance(tombstones, list) or not isinstance(blobs, list):
        raise ValueError("P2P_REPLICATION_INVALID: change collections must be arrays")
    parsed_upserts: list[ChangeUpsert] = []
    for item in upserts:
        value = _mapping(item, "upsert")
        _exact(value, {"kind", "id", "entity_version", "payload_contract", "payload"}, "upsert")
        parsed_upserts.append(ChangeUpsert(str(value["kind"]), str(value["id"]), value["entity_version"], str(value["payload_contract"]), _mapping(value["payload"], "payload")))
    parsed_tombstones: list[ChangeTombstone] = []
    for item in tombstones:
        value = _mapping(item, "tombstone")
        _exact(value, {"kind", "id", "previous_entity_version"}, "tombstone")
        parsed_tombstones.append(ChangeTombstone(str(value["kind"]), str(value["id"]), value["previous_entity_version"]))
    parsed_blobs: list[ChangeBlobReference] = []
    for item in blobs:
        value = _mapping(item, "blob reference")
        _exact(value, {"digest", "size", "media_type"}, "blob reference")
        parsed_blobs.append(ChangeBlobReference(str(value["digest"]), value["size"], str(value["media_type"])))
    return ChangeBatch(
        change_batch_id=str(raw["change_batch_id"]),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        authority_epoch=AuthorityEpoch(_positive(raw["authority_epoch"], "authority_epoch")),
        previous_revision=_revision(raw["previous_revision"], "previous_revision"),
        project_revision=_positive(raw["project_revision"], "project_revision"),
        operation_id=str(raw["operation_id"]),
        upserts=tuple(parsed_upserts),
        tombstones=tuple(parsed_tombstones),
        blob_references=tuple(parsed_blobs),
        semantic_state_digest=str(raw["semantic_state_digest"]),
        blob_manifest_digest=str(raw["blob_manifest_digest"]),
        batch_digest=str(raw["batch_digest"]),
    )


def feed_from_mapping(raw: Mapping[str, object]) -> ChangeFeed:
    _exact(
        raw,
        {
            "contract", "status", "project_uuid", "replica_id", "authority_epoch",
            "after_revision", "oldest_available_revision", "current_revision",
            "batches", "has_more", "snapshot",
        },
        "change feed",
    )
    if raw.get("contract") != PROJECT_CHANGE_FEED_CONTRACT:
        raise ValueError("P2P_REPLICATION_PROTOCOL_UNSUPPORTED: feed contract differs")
    batches = raw.get("batches")
    if not isinstance(batches, list) or not isinstance(raw.get("has_more"), bool):
        raise ValueError("P2P_REPLICATION_INVALID: feed arrays or flags are invalid")
    snapshot = raw.get("snapshot")
    return ChangeFeed(
        status=str(raw["status"]),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        replica_id=ReplicaId(str(raw["replica_id"])),
        authority_epoch=AuthorityEpoch(_positive(raw["authority_epoch"], "authority_epoch")),
        after_revision=_revision(raw["after_revision"], "after_revision"),
        oldest_available_revision=_revision(raw["oldest_available_revision"], "oldest_available_revision"),
        current_revision=_revision(raw["current_revision"], "current_revision"),
        batches=tuple(batch_from_mapping(_mapping(item, "batch")) for item in batches),
        has_more=raw["has_more"],
        snapshot=None if snapshot is None else _mapping(snapshot, "snapshot"),
    )


def notification_from_mapping(raw: Mapping[str, object]) -> ProjectNotification:
    _exact(raw, {"contract", "event_id", "kind", "project_uuid", "project_revision", "change_batch_id", "operation_id"}, "notification")
    if raw.get("contract") != PROJECT_NOTIFICATION_CONTRACT:
        raise ValueError("P2P_REPLICATION_PROTOCOL_UNSUPPORTED: notification contract differs")
    return ProjectNotification(
        event_id=str(raw["event_id"]),
        kind=str(raw["kind"]),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        project_revision=_revision(raw["project_revision"], "project_revision"),
        change_batch_id=None if raw["change_batch_id"] is None else str(raw["change_batch_id"]),
        operation_id=None if raw["operation_id"] is None else str(raw["operation_id"]),
    )

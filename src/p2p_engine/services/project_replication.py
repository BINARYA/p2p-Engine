from __future__ import annotations

import hashlib
import json
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from p2p_engine.core.canonical_memory import (
    CANONICAL_MEMORY_CONTRACT,
    DOMAIN_CONTRACT,
    MEMORY_SCHEMA_VERSION,
    CanonicalEntity,
    ManagedBlob,
    canonical_json_bytes,
    semantic_sha256,
)
from p2p_engine.core.mutation_preview import MutationResult, SourcePrecondition, source_precondition
from p2p_engine.core.project_identity import AuthorityEpoch, ProjectUuid, ReplicaId
from p2p_engine.core.project_replication import (
    ChangeBatch,
    ChangeBlobReference,
    ChangeFeed,
    ChangeTombstone,
    ChangeUpsert,
    EntityPrecondition,
    OperationReceipt,
    ProjectCommand,
    batch_from_mapping,
    command_from_mapping,
    receipt_from_mapping,
    replication_entity_version,
)
from p2p_engine.storage.canonical_memory import (
    FilesystemCanonicalMemoryStore,
    canonical_entity_from_document,
    classify_memory_path,
    managed_blob_from_document,
)

PROJECT_REPLICATION_STATE_CONTRACT = "p2p-project-replication-state/v1"
PROJECT_REPLICATION_IDEMPOTENCY_CONTRACT = "p2p-project-idempotency-entry/v1"
PROJECT_REPLICATION_ROOT = ".p2p/local/project-replication"
PROJECT_REPLICATION_STATE_PATH = f"{PROJECT_REPLICATION_ROOT}/state.json"
PROJECT_REPLICATION_MAX_DOCUMENT_BYTES = 16_777_216
PROJECT_REPLICATION_DEFAULT_RETENTION = 2048


@dataclass(frozen=True)
class ProjectReplicationState:
    project_uuid: ProjectUuid
    authority_epoch: AuthorityEpoch
    current_revision: int
    oldest_available_revision: int
    retention_batches: int

    def __post_init__(self) -> None:
        if self.current_revision < 0 or self.oldest_available_revision < 0:
            raise ValueError("P2P_REPLICATION_STATE_INVALID: revisions must be non-negative")
        if self.oldest_available_revision > self.current_revision + 1:
            raise ValueError("P2P_REPLICATION_STATE_INVALID: retention floor exceeds head")
        if not 1 <= self.retention_batches <= 1_000_000:
            raise ValueError("P2P_REPLICATION_STATE_INVALID: retention bound is unsafe")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": PROJECT_REPLICATION_STATE_CONTRACT,
            "project_uuid": self.project_uuid.value,
            "authority_epoch": self.authority_epoch.value,
            "current_revision": self.current_revision,
            "oldest_available_revision": self.oldest_available_revision,
            "retention_batches": self.retention_batches,
        }


@dataclass
class ReplicationCommandContext:
    command: ProjectCommand
    receipt: OperationReceipt | None = None
    replayed: bool = False


_COMMAND_CONTEXT: ContextVar[ReplicationCommandContext | None] = ContextVar(
    "p2p_replication_command_context", default=None
)


def set_replication_command(command: ProjectCommand | None) -> None:
    _COMMAND_CONTEXT.set(None if command is None else ReplicationCommandContext(command))


def load_replication_command(path: Path) -> ProjectCommand:
    raw = _read_json(path, "command envelope", 1_048_576)
    return command_from_mapping(raw)


def current_replication_receipt() -> OperationReceipt | None:
    context = _COMMAND_CONTEXT.get()
    return None if context is None else context.receipt


class FilesystemProjectReplicationStore:
    """Durable server feed and receipt state stored beside one project root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.p2p_dir = self.root / ".p2p"
        self.memory = FilesystemCanonicalMemoryStore(self.root)

    def state(self) -> ProjectReplicationState | None:
        path = self.root / PROJECT_REPLICATION_STATE_PATH
        if not path.exists():
            return None
        raw = _read_json(path, "replication state", 262_144)
        if set(raw) != {
            "contract",
            "project_uuid",
            "authority_epoch",
            "current_revision",
            "oldest_available_revision",
            "retention_batches",
        } or raw.get("contract") != PROJECT_REPLICATION_STATE_CONTRACT:
            raise ValueError("P2P_REPLICATION_STATE_INVALID: state fields are not exact")
        return ProjectReplicationState(
            project_uuid=ProjectUuid(str(raw["project_uuid"])),
            authority_epoch=AuthorityEpoch(_positive(raw["authority_epoch"], "authority_epoch")),
            current_revision=_revision(raw["current_revision"], "current_revision"),
            oldest_available_revision=_revision(
                raw["oldest_available_revision"], "oldest_available_revision"
            ),
            retention_batches=_positive(raw["retention_batches"], "retention_batches"),
        )

    def initialize(
        self,
        *,
        authority_epoch: int,
        project_revision: int,
        retention_batches: int = PROJECT_REPLICATION_DEFAULT_RETENTION,
    ) -> ProjectReplicationState:
        identity = self.memory.project_identity()
        desired = ProjectReplicationState(
            project_uuid=identity.project_uuid,
            authority_epoch=AuthorityEpoch(_positive(authority_epoch, "authority_epoch")),
            current_revision=_revision(project_revision, "project_revision"),
            oldest_available_revision=project_revision + 1,
            retention_batches=_positive(retention_batches, "retention_batches"),
        )
        current = self.state()
        if current is not None:
            if current != desired:
                raise ValueError(
                    "P2P_REPLICATION_STATE_CONFLICT: existing replication state differs"
                )
            return current
        self._commit(
            operation="project-replication-initialize",
            candidates={PROJECT_REPLICATION_STATE_PATH: canonical_json_bytes(desired.to_dict())},
        )
        return desired

    def receipt(self, operation_id: str) -> OperationReceipt | None:
        path = self.root / _receipt_path(operation_id)
        if not path.exists():
            return None
        return receipt_from_mapping(
            _read_json(path, "operation receipt", PROJECT_REPLICATION_MAX_DOCUMENT_BYTES)
        )

    def idempotency_entry(self, idempotency_key: str) -> Mapping[str, object] | None:
        path = self.root / _idempotency_path(idempotency_key)
        if not path.exists():
            return None
        raw = _read_json(path, "idempotency entry", 262_144)
        if set(raw) != {
            "contract",
            "idempotency_key",
            "operation_id",
            "command_fingerprint",
        } or raw.get("contract") != PROJECT_REPLICATION_IDEMPOTENCY_CONTRACT:
            raise ValueError("P2P_REPLICATION_STATE_INVALID: idempotency entry fields differ")
        if raw.get("idempotency_key") != idempotency_key:
            raise ValueError("P2P_REPLICATION_STATE_INVALID: idempotency key digest differs")
        return raw

    def batch(self, revision: int) -> ChangeBatch | None:
        matches = sorted((self.root / f"{PROJECT_REPLICATION_ROOT}/batches").glob(
            f"{revision:020d}-*.json"
        ))
        if not matches:
            return None
        if len(matches) != 1:
            raise ValueError("P2P_REPLICATION_STATE_INVALID: duplicate batch revision")
        return batch_from_mapping(
            _read_json(matches[0], "change batch", PROJECT_REPLICATION_MAX_DOCUMENT_BYTES)
        )

    def feed(self, *, after_revision: int, replica_id: str, limit: int = 64) -> ChangeFeed:
        state = self._required_state()
        after = _revision(after_revision, "after_revision")
        if not 1 <= limit <= 128:
            raise ValueError("P2P_REPLICATION_INVALID: feed limit must be between 1 and 128")
        replica = ReplicaId(replica_id)
        if after < state.oldest_available_revision - 1:
            return ChangeFeed(
                status="retention-gap",
                project_uuid=state.project_uuid,
                replica_id=replica,
                authority_epoch=state.authority_epoch,
                after_revision=after,
                oldest_available_revision=state.oldest_available_revision,
                current_revision=state.current_revision,
                batches=(),
                has_more=False,
                snapshot={
                    "required": True,
                    "reason": "cursor is older than retained project changes",
                },
            )
        if after > state.current_revision:
            raise ValueError("P2P_REPLICATION_CURSOR_REGRESSION: cursor is ahead of project head")
        batches: list[ChangeBatch] = []
        for revision in range(after + 1, state.current_revision + 1):
            batch = self.batch(revision)
            if batch is None:
                raise ValueError("P2P_REPLICATION_STATE_INVALID: retained feed contains a gap")
            batches.append(batch)
            if len(batches) == limit:
                break
        return ChangeFeed(
            status="changes" if batches else "up-to-date",
            project_uuid=state.project_uuid,
            replica_id=replica,
            authority_epoch=state.authority_epoch,
            after_revision=after,
            oldest_available_revision=state.oldest_available_revision,
            current_revision=state.current_revision,
            batches=tuple(batches),
            has_more=bool(batches and batches[-1].project_revision < state.current_revision),
        )

    def compact(self, *, retain_after_revision: int) -> ProjectReplicationState:
        state = self._required_state()
        boundary = _revision(retain_after_revision, "retain_after_revision")
        boundary = min(boundary, state.current_revision)
        new_floor = max(state.oldest_available_revision, boundary + 1)
        candidates: dict[str, bytes | None] = {}
        for revision in range(state.oldest_available_revision, new_floor):
            batch = self.batch(revision)
            if batch is not None:
                candidates[_batch_path(batch)] = None
        updated = ProjectReplicationState(
            project_uuid=state.project_uuid,
            authority_epoch=state.authority_epoch,
            current_revision=state.current_revision,
            oldest_available_revision=new_floor,
            retention_batches=state.retention_batches,
        )
        candidates[PROJECT_REPLICATION_STATE_PATH] = canonical_json_bytes(updated.to_dict())
        self._commit(operation=f"project-replication-compact-{new_floor}", candidates=candidates)
        return updated

    def _required_state(self) -> ProjectReplicationState:
        state = self.state()
        if state is None:
            raise ValueError("P2P_REPLICATION_STATE_MISSING: initialize the server project feed")
        return state

    def _commit(self, *, operation: str, candidates: Mapping[str, bytes | None]) -> None:
        from p2p_engine.core.mutation_preview import semantic_sha256 as mutation_sha256
        from p2p_engine.services.workspace_transactions import AtomicMutationWriter

        sources = tuple(_source(self.root, path) for path in sorted(candidates))
        result = AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir).apply(
            operation_id=operation,
            candidates=dict(candidates),
            sources=sources,
            preview_token=mutation_sha256(
                {
                    "operation": operation,
                    "targets": sorted(candidates),
                    "digests": {
                        path: None if content is None else hashlib.sha256(content).hexdigest()
                        for path, content in sorted(candidates.items())
                    },
                }
            ),
            actor="wavekit-worker",
        )
        if result.status != "applied":
            raise ValueError("P2P_REPLICATION_COMMIT_FAILED: " + result.message)


def augment_replication_transaction(
    *,
    root: Path,
    candidates: dict[str, bytes | None],
    sources: tuple[SourcePrecondition, ...],
    mutation_operation_id: str,
) -> tuple[dict[str, bytes | None], tuple[SourcePrecondition, ...], MutationResult | None]:
    """Add feed, receipt and head state to a domain mutation while its lock is held."""
    context = _COMMAND_CONTEXT.get()
    if context is None:
        return candidates, sources, None
    store = FilesystemProjectReplicationStore(root)
    command = context.command
    state = store._required_state()
    existing = store.receipt(command.operation_id)
    if existing is not None:
        if (
            existing.project_uuid != command.project_uuid
            or existing.command_fingerprint != command.fingerprint
            or existing.idempotency_key != command.idempotency_key
        ):
            raise ValueError("P2P_REPLICATION_OPERATION_CONFLICT: operation identity was reused")
        context.receipt = existing
        context.replayed = True
        return candidates, sources, MutationResult(
            status="applied",
            operation_id=mutation_operation_id,
            message="Existing immutable replication receipt was replayed.",
        )
    idempotency_entry = store.idempotency_entry(command.idempotency_key)
    if idempotency_entry is not None:
        if (
            idempotency_entry.get("operation_id") != command.operation_id
            or idempotency_entry.get("command_fingerprint") != command.fingerprint
        ):
            raise ValueError(
                "P2P_REPLICATION_IDEMPOTENCY_CONFLICT: idempotency key was reused"
            )
        raise ValueError(
            "P2P_REPLICATION_STATE_INVALID: idempotency entry has no operation receipt"
        )
    if command.project_uuid != state.project_uuid:
        raise ValueError("P2P_REPLICATION_IDENTITY_MISMATCH: command project differs")
    if command.authority_epoch != state.authority_epoch:
        raise ValueError("P2P_REPLICATION_AUTHORITY_CHANGED: authority epoch differs")
    if (
        command.expected_project_revision != state.current_revision
        and not command.entity_preconditions
    ):
        raise ValueError(
            "P2P_REPLICATION_REVISION_CONFLICT: expected project revision is stale"
        )

    snapshot = _snapshot(store.memory)
    current_entities = {
        (item.entity_type, item.technical_id): item for item in snapshot["entities"]
    }
    _verify_entity_preconditions(command, current_entities)
    projected_entities = dict(current_entities)
    current_blobs = {item.digest: item for item in snapshot["blobs"]}
    projected_blobs = dict(current_blobs)
    upserts: list[ChangeUpsert] = []
    tombstones: list[ChangeTombstone] = []
    introduced_blobs: list[ChangeBlobReference] = []

    for target, content in sorted(candidates.items()):
        if not target.startswith(".p2p/"):
            continue
        relative = target.removeprefix(".p2p/")
        classification, _, _ = classify_memory_path(relative)
        if classification == "canonical_project":
            previous = _entity_for_locator(current_entities, target)
            if content is None:
                if previous is not None:
                    projected_entities.pop((previous.entity_type, previous.technical_id), None)
                    tombstones.append(
                        ChangeTombstone(
                            previous.entity_type,
                            previous.technical_id,
                            _entity_version(previous),
                        )
                    )
                continue
            entity = canonical_entity_from_document(relative, content)
            if previous == entity:
                continue
            projected_entities[(entity.entity_type, entity.technical_id)] = entity
            upserts.append(
                ChangeUpsert(
                    entity.entity_type,
                    entity.technical_id,
                    _entity_version(entity),
                    CANONICAL_MEMORY_CONTRACT,
                    entity.payload,
                )
            )
        elif classification == "managed_blob":
            if content is None:
                previous_blob = next(
                    (item for item in current_blobs.values() if item.storage_locator == target), None
                )
                if previous_blob is not None:
                    projected_blobs.pop(previous_blob.digest, None)
                continue
            blob = managed_blob_from_document(relative, content)
            projected_blobs[blob.digest] = blob
            if blob.digest not in current_blobs:
                introduced_blobs.append(
                    ChangeBlobReference(blob.digest, blob.size, blob.media_type)
                )

    if command.expected_project_revision != state.current_revision:
        affected = [
            (
                item.kind,
                item.entity_id,
                current_entities.get((item.kind, item.entity_id)),
            )
            for item in upserts
        ]
        affected.extend(
            (
                item.kind,
                item.entity_id,
                current_entities.get((item.kind, item.entity_id)),
            )
            for item in tombstones
        )
        for kind, entity_id, previous in affected:
            expected_version = 0 if previous is None else _entity_version(previous)
            if not any(
                _precondition_matches(
                    precondition,
                    kind=kind,
                    entity_id=entity_id,
                    human_key=None if previous is None else previous.human_key,
                )
                and precondition.expected_version == expected_version
                for precondition in command.entity_preconditions
            ):
                raise ValueError(
                    "P2P_REPLICATION_ENTITY_CONFLICT: stale work omits an affected entity precondition"
                )

    if not upserts and not tombstones and not introduced_blobs:
        receipt = OperationReceipt(
            operation_id=command.operation_id,
            idempotency_key=command.idempotency_key,
            command_fingerprint=command.fingerprint,
            status="completed",
            project_uuid=state.project_uuid,
            authority_epoch=state.authority_epoch,
            base_project_revision=state.current_revision,
            project_revision=state.current_revision,
            change_batch_id=None,
            result_contract="p2p-domain-command-result/v1",
            result={
                "mutation_operation": mutation_operation_id,
                "changed": False,
            },
        )
        augmented = dict(candidates)
        augmented[_receipt_path(command.operation_id)] = canonical_json_bytes(receipt.to_dict())
        augmented[_idempotency_path(command.idempotency_key)] = _idempotency_bytes(command)
        context.receipt = receipt
        return augmented, _merge_sources(root, sources, augmented, candidates), None

    next_revision = state.current_revision + 1
    state_digest, blob_digest = _projected_digests(
        store.memory,
        state.project_uuid.value,
        tuple(projected_entities.values()),
        tuple(projected_blobs.values()),
        snapshot["lineage"],
    )
    batch_seed = {
        "operation_id": command.operation_id,
        "project_uuid": state.project_uuid.value,
        "revision": next_revision,
        "semantic_state_digest": state_digest,
    }
    batch_id = f"chg_{semantic_sha256(batch_seed)[:32]}"
    batch = ChangeBatch(
        change_batch_id=batch_id,
        project_uuid=state.project_uuid,
        authority_epoch=state.authority_epoch,
        previous_revision=state.current_revision,
        project_revision=next_revision,
        operation_id=command.operation_id,
        upserts=tuple(upserts),
        tombstones=tuple(tombstones),
        blob_references=tuple(introduced_blobs),
        semantic_state_digest=state_digest,
        blob_manifest_digest=blob_digest,
    )
    receipt = OperationReceipt(
        operation_id=command.operation_id,
        idempotency_key=command.idempotency_key,
        command_fingerprint=command.fingerprint,
        status="completed",
        project_uuid=state.project_uuid,
        authority_epoch=state.authority_epoch,
        base_project_revision=state.current_revision,
        project_revision=next_revision,
        change_batch_id=batch_id,
        result_contract="p2p-domain-command-result/v1",
        result={
            "mutation_operation": mutation_operation_id,
            "changed": True,
        },
    )
    updated = ProjectReplicationState(
        project_uuid=state.project_uuid,
        authority_epoch=state.authority_epoch,
        current_revision=next_revision,
        oldest_available_revision=min(state.oldest_available_revision, next_revision),
        retention_batches=state.retention_batches,
    )
    augmented = dict(candidates)
    augmented.update(
        {
            _batch_path(batch): canonical_json_bytes(batch.to_dict()),
            _receipt_path(command.operation_id): canonical_json_bytes(receipt.to_dict()),
            _idempotency_path(command.idempotency_key): _idempotency_bytes(command),
            PROJECT_REPLICATION_STATE_PATH: canonical_json_bytes(updated.to_dict()),
        }
    )
    context.receipt = receipt
    return augmented, _merge_sources(root, sources, augmented, candidates), None


def _snapshot(memory: FilesystemCanonicalMemoryStore) -> dict[str, object]:
    from p2p_engine.services.canonical_memory import CanonicalBundleCodec

    snapshot = CanonicalBundleCodec().snapshot(memory)
    return {
        "entities": snapshot.entities,
        "blobs": snapshot.blobs,
        "lineage": snapshot.lineage,
    }


def _verify_entity_preconditions(
    command: ProjectCommand,
    entities: Mapping[tuple[str, str], CanonicalEntity],
) -> None:
    for precondition in command.entity_preconditions:
        matches = [
            item
            for item in entities.values()
            if _precondition_matches(
                precondition,
                kind=item.entity_type,
                entity_id=item.technical_id,
                human_key=item.human_key,
            )
        ]
        if not matches and precondition.expected_version == 0:
            continue
        if len(matches) != 1 or _entity_version(matches[0]) != precondition.expected_version:
            raise ValueError(
                "P2P_REPLICATION_ENTITY_CONFLICT: entity version precondition is stale"
            )


def _precondition_matches(
    precondition: EntityPrecondition,
    *,
    kind: str,
    entity_id: str,
    human_key: str | None,
) -> bool:
    expected_kind = precondition.kind
    expected_id = precondition.entity_id
    return (
        kind == expected_kind or kind.endswith(f".{expected_kind}")
    ) and expected_id in {entity_id, human_key}


def _entity_for_locator(
    entities: Mapping[tuple[str, str], CanonicalEntity], locator: str
) -> CanonicalEntity | None:
    return next((item for item in entities.values() if item.storage_locator == locator), None)


def _entity_version(entity: CanonicalEntity) -> int:
    return replication_entity_version(
        kind=entity.entity_type,
        entity_id=entity.technical_id,
        payload_contract=CANONICAL_MEMORY_CONTRACT,
        payload=entity.payload,
    )


def _projected_digests(
    memory: FilesystemCanonicalMemoryStore,
    project_uuid: str,
    entities: tuple[CanonicalEntity, ...],
    blobs: tuple[ManagedBlob, ...],
    lineage: object,
) -> tuple[str, str]:
    ordered_entities = tuple(sorted(entities, key=lambda item: (item.entity_type, item.technical_id)))
    relations = memory.read_relations(ordered_entities)
    ordered_blobs = tuple(sorted(blobs, key=lambda item: item.digest))
    state_payload = {
        "contract": CANONICAL_MEMORY_CONTRACT,
        "project_uuid": project_uuid,
        "memory_schema": MEMORY_SCHEMA_VERSION,
        "domain_contract": DOMAIN_CONTRACT,
        "entities": [item.to_dict() for item in ordered_entities],
        "relations": [item.to_dict() for item in relations],
        "lineage": list(lineage) if isinstance(lineage, tuple) else lineage,
        "blobs": [item.to_dict() for item in ordered_blobs],
    }
    return semantic_sha256(state_payload), semantic_sha256(
        [item.to_dict() for item in ordered_blobs]
    )


def _batch_path(batch: ChangeBatch) -> str:
    return (
        f"{PROJECT_REPLICATION_ROOT}/batches/"
        f"{batch.project_revision:020d}-{batch.change_batch_id}.json"
    )


def _receipt_path(operation_id: str) -> str:
    digest = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()
    return f"{PROJECT_REPLICATION_ROOT}/receipts/{digest}.json"


def _idempotency_path(idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"{PROJECT_REPLICATION_ROOT}/idempotency/{digest}.json"


def _idempotency_bytes(command: ProjectCommand) -> bytes:
    return canonical_json_bytes(
        {
            "contract": PROJECT_REPLICATION_IDEMPOTENCY_CONTRACT,
            "idempotency_key": command.idempotency_key,
            "operation_id": command.operation_id,
            "command_fingerprint": command.fingerprint,
        }
    )


def _source(root: Path, path: str) -> SourcePrecondition:
    target = root / path
    content = target.read_bytes() if target.is_file() and not target.is_symlink() else None
    return source_precondition(path, content)


def _merge_sources(
    root: Path,
    sources: tuple[SourcePrecondition, ...],
    augmented: Mapping[str, bytes | None],
    original: Mapping[str, bytes | None],
) -> tuple[SourcePrecondition, ...]:
    merged = {item.path: item for item in sources}
    for path in set(augmented) - set(original):
        merged[path] = _source(root, path)
    return tuple(merged[path] for path in sorted(merged))


def _read_json(path: Path, label: str, max_bytes: int) -> Mapping[str, object]:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
            raise ValueError("unsafe document")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"P2P_REPLICATION_STATE_INVALID: cannot read {label}") from exc
    if not isinstance(value, Mapping):
        raise ValueError(f"P2P_REPLICATION_STATE_INVALID: {label} must be a mapping")
    return value


def _revision(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"P2P_REPLICATION_INVALID: {field} must be non-negative")
    return value


def _positive(value: object, field: str) -> int:
    result = _revision(value, field)
    if result < 1:
        raise ValueError(f"P2P_REPLICATION_INVALID: {field} must be positive")
    return result

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from p2p_engine.core.canonical_memory import (
    CANONICAL_MEMORY_CONTRACT,
    DOMAIN_CONTRACT,
    MEMORY_SCHEMA_VERSION,
    CanonicalEntity,
    ManagedBlob,
    canonical_json_bytes,
)
from p2p_engine.core.canonical_memory import semantic_sha256 as canonical_semantic_sha256
from p2p_engine.core.linked_replica import (
    LINKED_REPLICA_BINDING_CONTRACT,
    LinkedReplicaBinding,
    ReplicaAccessState,
    ReplicaSnapshotManifest,
    linked_binding_from_mapping,
)
from p2p_engine.core.mutation_preview import semantic_sha256, source_precondition
from p2p_engine.core.project_identity import ProjectIdentity, ProjectMode, RemoteBinding
from p2p_engine.core.project_replication import ChangeBatch, replication_entity_version
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.canonical_memory import (
    FilesystemCanonicalMemoryStore,
    canonical_entity_from_document,
)
from p2p_engine.storage.filesystem_authority_transfer import FilesystemAuthorityTransferStore
from p2p_engine.storage.project_identity import FilesystemProjectIdentityStore

LINKED_REPLICA_BINDING_PATH = ".p2p/local/wavekit-binding.yml"
LINKED_REPLICA_DOCUMENT_MAX_BYTES = 262_144
LINKED_REPLICA_INBOX_ROOT = ".p2p/local/project-replication/inbox"


class FilesystemLinkedReplicaStore:
    """Replica-local, non-secret WaveKit binding behind the filesystem adapter."""

    def __init__(self, root: Path, *, failure_injector=None) -> None:
        self.root = root.resolve()
        self.p2p_dir = self.root / ".p2p"
        self.path = self.root / LINKED_REPLICA_BINDING_PATH
        self.identity_store = FilesystemProjectIdentityStore(root=self.root, p2p_dir=self.p2p_dir)
        self.failure_injector = failure_injector

    def load(self) -> LinkedReplicaBinding | None:
        if not self.path.exists():
            return None
        payload = self._read()
        contract = str(payload.get("contract") or "")
        if contract == LINKED_REPLICA_BINDING_CONTRACT:
            return linked_binding_from_mapping(payload)
        # Authority-transfer v1 created a smaller binding.  It is accepted as a
        # read-only predecessor and upgraded on the first successful catch-up.
        if contract == "p2p-linked-project-binding/v1":
            return self._legacy_binding(payload)
        raise ValueError("P2P_LINKED_REPLICA_STATE_INVALID: unsupported binding contract")

    def save(self, binding: LinkedReplicaBinding) -> LinkedReplicaBinding:
        identity = self.identity_store.load()
        self._verify_identity(identity, binding)
        self._commit(
            operation="linked-replica-binding-update",
            candidates={LINKED_REPLICA_BINDING_PATH: self._binding_bytes(binding)},
        )
        return binding

    def verify_active_identity(
        self, binding: LinkedReplicaBinding | None = None
    ) -> ProjectIdentity:
        current = binding or self.load()
        if current is None:
            raise ValueError("P2P_LINKED_REPLICA_NOT_FOUND: local binding is absent")
        identity = self.identity_store.load()
        self._verify_identity(identity, current)
        return identity

    def activate_snapshot(
        self,
        manifest: ReplicaSnapshotManifest,
        *,
        server_url: str,
        account_profile_ref: str,
        verified_at: int,
        preserve_replica_id: bool = False,
    ) -> LinkedReplicaBinding:
        current = self.identity_store.load()
        if current.project_uuid != manifest.project_uuid:
            raise ValueError(
                "P2P_LINKED_REPLICA_IDENTITY_MISMATCH: snapshot project UUID differs"
            )
        replica_id = current.replica_id if preserve_replica_id else manifest.replica_id
        if replica_id is None or (preserve_replica_id and replica_id != manifest.replica_id):
            raise ValueError(
                "P2P_LINKED_REPLICA_IDENTITY_MISMATCH: snapshot replica ID differs"
            )
        remote = RemoteBinding(
            server_instance_id=manifest.server_instance_id,
            remote_project_id=manifest.remote_project_id,
        )
        if current.remote_binding is not None and current.remote_binding != remote:
            raise ValueError(
                "P2P_LINKED_REPLICA_IDENTITY_MISMATCH: existing remote binding differs"
            )
        linked = ProjectIdentity(
            project_uuid=current.project_uuid,
            display_name=current.display_name,
            mode=ProjectMode.linked,
            replica_id=replica_id,
            remote_binding=remote,
            lineage=current.lineage,
        )
        binding = LinkedReplicaBinding(
            server_url=server_url,
            server_instance_id=manifest.server_instance_id,
            remote_project_id=manifest.remote_project_id,
            project_uuid=manifest.project_uuid,
            replica_id=replica_id,
            authority_epoch=manifest.authority_epoch,
            last_applied_revision=manifest.remote_revision,
            cursor=manifest.cursor,
            snapshot_digest=manifest.semantic_state_digest,
            blob_manifest_digest=manifest.blob_manifest_digest,
            account_profile_ref=account_profile_ref,
            state=ReplicaAccessState.active,
            last_verified_at=verified_at,
        )
        self._commit(
            operation="linked-replica-snapshot-activation",
            candidates={
                **self.identity_store.candidate_documents(linked),
                LINKED_REPLICA_BINDING_PATH: self._binding_bytes(binding),
            },
        )
        return binding

    def replace_replica_identity(
        self,
        binding: LinkedReplicaBinding,
        *,
        replacement: LinkedReplicaBinding,
    ) -> LinkedReplicaBinding:
        current = self.identity_store.load()
        self._verify_identity(current, binding)
        if (
            replacement.project_uuid != binding.project_uuid
            or replacement.server_instance_id != binding.server_instance_id
            or replacement.remote_project_id != binding.remote_project_id
        ):
            raise ValueError("P2P_LINKED_REPLICA_IDENTITY_MISMATCH: replacement binding differs")
        updated = ProjectIdentity(
            project_uuid=current.project_uuid,
            display_name=current.display_name,
            mode=(
                ProjectMode.link_suspended
                if replacement.state == ReplicaAccessState.suspended
                else ProjectMode.linked
            ),
            replica_id=replacement.replica_id,
            remote_binding=current.remote_binding,
            lineage=current.lineage,
        )
        self._commit(
            operation="linked-replica-identity-replacement",
            candidates={
                **self.identity_store.candidate_documents(updated),
                LINKED_REPLICA_BINDING_PATH: self._binding_bytes(replacement),
            },
        )
        return replacement

    def mark_access(
        self,
        state: ReplicaAccessState,
        *,
        error_code: str = "",
    ) -> LinkedReplicaBinding:
        current = self.load()
        if current is None:
            raise ValueError("P2P_LINKED_REPLICA_NOT_FOUND: local binding is absent")
        updated = current.with_access_state(state, error_code=error_code)
        identity = self.identity_store.load()
        mode = ProjectMode.link_suspended if state == ReplicaAccessState.suspended else ProjectMode.linked
        updated_identity = ProjectIdentity(
            project_uuid=identity.project_uuid,
            display_name=identity.display_name,
            mode=mode,
            replica_id=identity.replica_id,
            remote_binding=identity.remote_binding,
            lineage=identity.lineage,
        )
        self._commit(
            operation="linked-replica-access-state",
            candidates={
                **self.identity_store.candidate_documents(updated_identity),
                LINKED_REPLICA_BINDING_PATH: self._binding_bytes(updated),
            },
        )
        return updated

    def apply_change_batch(
        self,
        batch: ChangeBatch,
        *,
        blob_bytes: dict[str, bytes],
        verified_at: int,
    ) -> LinkedReplicaBinding:
        binding = self.load()
        if binding is None:
            raise ValueError("P2P_LINKED_REPLICA_NOT_FOUND: local binding is absent")
        self._verify_identity(self.identity_store.load(), binding)
        if batch.project_uuid != binding.project_uuid:
            raise ValueError("P2P_REPLICATION_IDENTITY_MISMATCH: batch project differs")
        if batch.authority_epoch != binding.authority_epoch:
            raise ValueError("P2P_REPLICATION_AUTHORITY_CHANGED: batch authority epoch differs")
        inbox_path = self._inbox_path(batch)
        existing_marker = self.root / inbox_path
        if existing_marker.exists():
            marker = existing_marker.read_bytes()
            expected = canonical_json_bytes(
                {
                    "contract": "p2p-replica-inbox-entry/v1",
                    "change_batch_id": batch.change_batch_id,
                    "project_revision": batch.project_revision,
                    "batch_digest": f"sha256:{batch.batch_digest}",
                }
            )
            if marker != expected or binding.last_applied_revision < batch.project_revision:
                raise ValueError("P2P_REPLICATION_INBOX_CORRUPT: batch marker differs")
            return binding
        if batch.previous_revision != binding.last_applied_revision:
            raise ValueError("P2P_REPLICATION_CURSOR_GAP: batch does not follow local revision")

        memory = FilesystemCanonicalMemoryStore(self.root)
        snapshot = CanonicalBundleCodec().snapshot(memory)
        entities = {(item.entity_type, item.technical_id): item for item in snapshot.entities}
        blobs = {item.digest: item for item in snapshot.blobs}
        candidates: dict[str, bytes | None] = {}
        for upsert in batch.upserts:
            if upsert.payload_contract != CANONICAL_MEMORY_CONTRACT:
                raise ValueError(
                    "P2P_REPLICATION_PROTOCOL_UNSUPPORTED: entity payload contract differs"
                )
            entity = CanonicalEntity(
                entity_type=upsert.kind,
                technical_id=upsert.entity_id,
                entity_version=upsert.entity_version,
                payload=upsert.payload,
            )
            document = memory.activation_documents((entity,))
            if len(document) != 1:
                raise ValueError("P2P_REPLICATION_INVALID: entity does not map to one document")
            locator = next(iter(document))
            parsed = canonical_entity_from_document(
                locator.removeprefix(".p2p/"), document[locator]
            )
            if (
                parsed.entity_type != upsert.kind
                or parsed.technical_id != upsert.entity_id
                or replication_entity_version(
                    kind=parsed.entity_type,
                    entity_id=parsed.technical_id,
                    payload_contract=CANONICAL_MEMORY_CONTRACT,
                    payload=parsed.payload,
                )
                != upsert.entity_version
            ):
                raise ValueError(
                    "P2P_REPLICATION_INVALID: entity identity disagrees with its payload"
                )
            previous = entities.get((parsed.entity_type, parsed.technical_id))
            if previous is not None and previous.storage_locator != locator:
                candidates[previous.storage_locator] = None
            entity = parsed
            entities[(entity.entity_type, entity.technical_id)] = entity
            candidates.update(document)
        for tombstone in batch.tombstones:
            key = (tombstone.kind, tombstone.entity_id)
            previous = entities.get(key)
            if (
                previous is None
                or replication_entity_version(
                    kind=previous.entity_type,
                    entity_id=previous.technical_id,
                    payload_contract=CANONICAL_MEMORY_CONTRACT,
                    payload=previous.payload,
                )
                != tombstone.previous_entity_version
            ):
                raise ValueError(
                    "P2P_REPLICATION_ENTITY_CONFLICT: tombstone preimage differs"
                )
            if not previous.storage_locator:
                raise ValueError("P2P_REPLICATION_INVALID: tombstone has no local locator")
            candidates[previous.storage_locator] = None
            entities.pop(key)
        for reference in batch.blob_references:
            digest = f"sha256:{reference.digest}"
            if digest in blobs:
                continue
            content = blob_bytes.get(digest)
            if content is None:
                raise ValueError(f"P2P_REPLICATION_BLOB_MISSING: {digest}")
            blob = ManagedBlob(digest=digest, size=reference.size, media_type=reference.media_type)
            documents = memory.blob_documents((blob,), {digest: content})
            candidates.update(documents)
            locator = next(iter(documents))
            blobs[digest] = ManagedBlob(
                digest=digest,
                size=reference.size,
                media_type=reference.media_type,
                storage_locator=locator,
            )

        state_digest, blob_digest = self._projected_digests(
            memory,
            project_uuid=binding.project_uuid.value,
            entities=tuple(entities.values()),
            blobs=tuple(blobs.values()),
            lineage=snapshot.lineage,
        )
        if (
            state_digest != batch.semantic_state_digest
            or blob_digest != batch.blob_manifest_digest
        ):
            raise ValueError(
                "P2P_REPLICATION_DIGEST_MISMATCH: projected local state differs from batch"
            )
        updated = binding.with_progress(
            remote_revision=batch.project_revision,
            cursor=batch.project_revision,
            snapshot_digest=state_digest,
            blob_manifest_digest=blob_digest,
            verified_at=verified_at,
        )
        candidates[LINKED_REPLICA_BINDING_PATH] = self._binding_bytes(updated)
        candidates[inbox_path] = canonical_json_bytes(
            {
                "contract": "p2p-replica-inbox-entry/v1",
                "change_batch_id": batch.change_batch_id,
                "project_revision": batch.project_revision,
                "batch_digest": f"sha256:{batch.batch_digest}",
            }
        )
        self._commit(
            operation=f"linked-replica-apply-{batch.change_batch_id}",
            candidates=candidates,
        )
        return updated

    @staticmethod
    def _verify_identity(identity: ProjectIdentity, binding: LinkedReplicaBinding) -> None:
        if (
            identity.mode not in {ProjectMode.linked, ProjectMode.link_suspended}
            or identity.project_uuid != binding.project_uuid
            or identity.replica_id != binding.replica_id
            or identity.remote_binding
            != RemoteBinding(binding.server_instance_id, binding.remote_project_id)
        ):
            raise ValueError(
                "P2P_LINKED_REPLICA_IDENTITY_MISMATCH: identity and binding disagree"
            )

    def _legacy_binding(self, raw: Mapping[str, object]) -> LinkedReplicaBinding:
        expected = {
            "contract",
            "project_uuid",
            "server_url",
            "server_instance_id",
            "remote_project_id",
            "replica_id",
            "authority_epoch",
            "remote_revision",
            "cursor",
            "account_profile_ref",
            "receipt_digest",
        }
        if set(raw) != expected:
            raise ValueError("P2P_LINKED_REPLICA_STATE_INVALID: legacy binding fields differ")
        transfer_store = FilesystemAuthorityTransferStore(self.root)
        session = transfer_store.load()
        receipt = transfer_store.receipt()
        if session is None or receipt is None:
            raise ValueError(
                "P2P_LINKED_REPLICA_STATE_INVALID: legacy binding lacks transfer evidence"
            )
        if (
            str(raw["project_uuid"]) != receipt.project_uuid.value
            or str(raw["replica_id"]) != receipt.replica_id.value
            or str(raw["receipt_digest"]) != receipt.receipt_digest
        ):
            raise ValueError(
                "P2P_LINKED_REPLICA_STATE_INVALID: legacy receipt does not match binding"
            )
        return LinkedReplicaBinding(
            server_url=str(raw["server_url"]),
            server_instance_id=receipt.server_instance_id,
            remote_project_id=receipt.remote_project_id,
            project_uuid=receipt.project_uuid,
            replica_id=receipt.replica_id,
            authority_epoch=receipt.authority_epoch,
            last_applied_revision=receipt.remote_revision,
            cursor=receipt.cursor,
            snapshot_digest=session.semantic_state_digest,
            blob_manifest_digest=receipt.blob_manifest_digest,
            account_profile_ref=receipt.account_profile_ref,
            state=ReplicaAccessState.active,
            last_verified_at=0,
        )

    def _commit(self, *, operation: str, candidates: dict[str, bytes]) -> None:
        atomic_candidates: dict[str, bytes | None] = dict(candidates)
        sources = tuple(
            source_precondition(
                relative,
                (self.root / relative).read_bytes()
                if (self.root / relative).is_file()
                and not (self.root / relative).is_symlink()
                else None,
            )
            for relative in sorted(candidates)
        )
        result = AtomicMutationWriter(
            root=self.root,
            p2p_dir=self.p2p_dir,
            failure_injector=self.failure_injector,
        ).apply(
            operation_id=operation,
            candidates=atomic_candidates,
            sources=sources,
            preview_token=semantic_sha256(
                {
                    "operation": operation,
                    "candidates": {
                        path: semantic_sha256(content.decode("ascii"))
                        for path, content in sorted(candidates.items())
                    },
                }
            ),
            actor="local-owner",
        )
        if result.status != "applied":
            raise ValueError("P2P_LINKED_REPLICA_LOCAL_COMMIT_FAILED: " + result.message)

    @staticmethod
    def _binding_bytes(binding: LinkedReplicaBinding) -> bytes:
        return yaml_dump(
            {"linked_project_binding": binding.to_storage_dict()}
        ).encode("ascii")

    @staticmethod
    def _inbox_path(batch: ChangeBatch) -> str:
        return f"{LINKED_REPLICA_INBOX_ROOT}/{batch.batch_digest}.json"

    @staticmethod
    def _projected_digests(
        memory: FilesystemCanonicalMemoryStore,
        *,
        project_uuid: str,
        entities: tuple[CanonicalEntity, ...],
        blobs: tuple[ManagedBlob, ...],
        lineage: tuple[Mapping[str, object], ...],
    ) -> tuple[str, str]:
        ordered_entities = tuple(
            sorted(entities, key=lambda item: (item.entity_type, item.technical_id))
        )
        ordered_blobs = tuple(sorted(blobs, key=lambda item: item.digest))
        relations = memory.read_relations(ordered_entities)
        payload = {
            "contract": CANONICAL_MEMORY_CONTRACT,
            "project_uuid": project_uuid,
            "memory_schema": MEMORY_SCHEMA_VERSION,
            "domain_contract": DOMAIN_CONTRACT,
            "entities": [item.to_dict() for item in ordered_entities],
            "relations": [item.to_dict() for item in relations],
            "lineage": list(lineage),
            "blobs": [item.to_dict() for item in ordered_blobs],
        }
        return canonical_semantic_sha256(payload), canonical_semantic_sha256(
            [item.to_dict() for item in ordered_blobs]
        )

    def _read(self) -> Mapping[str, object]:
        if (
            self.path.is_symlink()
            or not self.path.is_file()
            or self.path.stat().st_size > LINKED_REPLICA_DOCUMENT_MAX_BYTES
        ):
            raise ValueError("P2P_LINKED_REPLICA_STATE_INVALID: unsafe binding document")
        try:
            payload = load_yaml(
                self.path.read_bytes(), loader_contract=UNIQUE_LOADER_CONTRACT
            )
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError(
                "P2P_LINKED_REPLICA_STATE_INVALID: binding cannot be parsed"
            ) from exc
        if not isinstance(payload, Mapping) or set(payload) != {"linked_project_binding"}:
            raise ValueError("P2P_LINKED_REPLICA_STATE_INVALID: invalid binding root")
        raw = payload["linked_project_binding"]
        if not isinstance(raw, Mapping):
            raise ValueError("P2P_LINKED_REPLICA_STATE_INVALID: binding body is absent")
        return raw

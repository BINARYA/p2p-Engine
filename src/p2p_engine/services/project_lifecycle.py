from __future__ import annotations

import hashlib
import os
import re
import shutil
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from p2p_engine.adapters.wavekit_credentials import (
    KeyringWaveKitCredentialStore,
    WaveKitCredentialStore,
)
from p2p_engine.adapters.wavekit_transfer_http import (
    HTTPSWaveKitTransferTransport,
    WaveKitTransferTransport,
)
from p2p_engine.core.linked_replica import (
    LinkedReplicaBinding,
    ReplicaAccessState,
    ReplicaSnapshotManifest,
    snapshot_manifest_from_mapping,
)
from p2p_engine.core.project_identity import (
    AuthorityEpoch,
    LineageRelation,
    LineageVisibility,
    ProjectIdentity,
    ProjectLineage,
    ProjectMode,
    ProjectUuid,
    RemoteProjectId,
    ReplicaId,
    ServerInstanceId,
    SourceMemoryRevision,
)
from p2p_engine.core.project_lifecycle import (
    DETACH_PREPARATION_CONTRACT,
    PROJECT_LIFECYCLE_CAPABILITY_CONTRACT,
    PROJECT_LIFECYCLE_CAPABILITY_PATH,
    PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES,
    PROJECT_LIFECYCLE_PREVIEW_CONTRACT,
    PROJECT_LIFECYCLE_PROTOCOL,
    DetachLineageMode,
    DetachReceipt,
    IntegrationDisposition,
    LifecycleAction,
    LifecycleCapabilities,
    LifecycleEndpoints,
    LifecycleOperationState,
    LifecyclePreview,
    LifecycleReceipt,
    LocalLifecycleState,
    LocalReplicaDisposition,
    ProjectPublication,
    RemoteLifecycleState,
    detach_receipt_from_mapping,
    lifecycle_receipt_from_mapping,
    publication_from_mapping,
)
from p2p_engine.core.project_state_storage import ProjectStorageManifest
from p2p_engine.foundation.files import sync_directory, write_bytes_atomic
from p2p_engine.ports.project_state import ProjectLifecycleStatePort, ProjectStateAdapter
from p2p_engine.services.authority_transfer import normalize_server_url
from p2p_engine.services.canonical_memory import CanonicalMemoryService
from p2p_engine.services.linked_replica import LinkedReplicaService
from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.workspace_transactions import utc_now_iso
from p2p_engine.storage.canonical_memory import FilesystemCanonicalMemoryStore
from p2p_engine.storage.filesystem_project_lifecycle import FilesystemProjectLifecycleStore
from p2p_engine.storage.project_identity import FilesystemProjectIdentityStore
from p2p_engine.storage.project_storage import ProjectStorageManifestStore


class ProjectLifecycleService:
    """Authority-safe client lifecycle shared by CLI and read-only MCP views."""

    def __init__(
        self,
        *,
        root: Path,
        adapter: ProjectStateAdapter,
        transport: WaveKitTransferTransport | None = None,
        credentials: WaveKitCredentialStore | None = None,
        store: ProjectLifecycleStatePort | None = None,
        linked_replica: LinkedReplicaService | None = None,
        integration_transition: Callable[[str], object] | None = None,
        integration_remove: Callable[[], object] | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.root = root.resolve()
        self.adapter = adapter
        self.transport = transport or HTTPSWaveKitTransferTransport()
        self.credentials = credentials or KeyringWaveKitCredentialStore()
        self.store = store or FilesystemProjectLifecycleStore(self.root)
        self.now = now
        self.linked = linked_replica or LinkedReplicaService(
            root=self.root,
            transport=self.transport,
            credentials=self.credentials,
            store=self.adapter.linked_replicas,
            now=now,
        )
        self.integration_transition = integration_transition
        self.integration_remove = integration_remove

    def capabilities(self, server_url: str) -> LifecycleCapabilities:
        server = normalize_server_url(server_url)
        response = self.transport.request_json(
            "GET",
            _same_origin_url(server, PROJECT_LIFECYCLE_CAPABILITY_PATH),
            max_bytes=PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES,
        )
        payload = _envelope(response, "project_lifecycle_capabilities")
        endpoints = _mapping(payload.get("endpoints"), "endpoints")
        names = {
            "status",
            "preview",
            "apply",
            "operation",
            "detach_prepare",
            "detach_complete",
            "publication",
            "deactivate_replica",
        }
        raw_modes = payload.get("allowed_lineage_modes")
        if (
            set(payload)
            != {
                "contract",
                "protocol",
                "server_instance_id",
                "endpoints",
                "retention_days",
                "allowed_lineage_modes",
                "emergency_detach_allowed",
            }
            or payload.get("contract") != PROJECT_LIFECYCLE_CAPABILITY_CONTRACT
            or set(endpoints) != names
            or not isinstance(raw_modes, list)
            or not all(isinstance(item, str) for item in raw_modes)
        ):
            raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: capability fields differ")
        retention = payload.get("retention_days")
        if isinstance(retention, bool) or not isinstance(retention, int):
            raise ValueError(
                "P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: retention_days must be an integer"
            )
        return LifecycleCapabilities(
            server_url=server,
            server_instance_id=ServerInstanceId(str(payload["server_instance_id"])),
            endpoints=LifecycleEndpoints(
                **{name: _endpoint(endpoints, name) for name in sorted(names)}
            ),
            retention_days=retention,
            allowed_lineage_modes=tuple(DetachLineageMode(item) for item in raw_modes),
            emergency_detach_allowed=payload["emergency_detach_allowed"] is True,
            protocol=str(payload["protocol"]),
        )

    def status(self, *, online: bool = True) -> dict[str, object]:
        binding = self.adapter.linked_replicas.load()
        local = self.store.state()
        detach = self.store.detach_receipt()
        publications = self.store.publications()
        remote: Mapping[str, object] | None = None
        diagnostic = ""
        if binding is not None and online:
            try:
                capabilities = self.capabilities(binding.server_url)
                self._verify_server(binding, capabilities)
                credential = self._credential(capabilities.server_url)
                response = self.transport.request_json(
                    "GET",
                    self._url(
                        capabilities,
                        capabilities.endpoints.status,
                        remote_project_id=binding.remote_project_id.value,
                        replica_id=binding.replica_id.value,
                    ),
                    token=credential.access_token,
                    max_bytes=PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES,
                )
                remote = _remote_status(_envelope(response, "project_lifecycle_status"), binding)
            except ValueError as exc:
                diagnostic = str(exc)
        suggestions = self._suggestions(binding, remote, diagnostic)
        return {
            "contract": "p2p-project-lifecycle-status/v1",
            "project_uuid": (
                binding.project_uuid.value
                if binding is not None
                else self.adapter.repository.identity().project_uuid.value
            ),
            "linked_replica": binding.to_dict() if binding is not None else None,
            "local_operation": local.to_dict() if local is not None else None,
            "remote": dict(remote) if remote is not None else None,
            "detach_receipt": detach.to_dict() if detach is not None else None,
            "publications": [item.to_dict() for item in publications],
            "diagnostic": diagnostic or None,
            "available_actions": suggestions,
            "mutation_performed": False,
        }

    def preview(
        self,
        *,
        action: LifecycleAction,
        operation_id: str,
        target: Path | None = None,
        lineage_mode: DetachLineageMode | None = None,
        keep_local: bool = False,
    ) -> LifecyclePreview:
        binding = self._binding()
        capabilities = self.capabilities(binding.server_url)
        self._verify_server(binding, capabilities)
        selected_lineage = lineage_mode
        target_uuid: ProjectUuid | None = None
        target_kind = ""
        if action == LifecycleAction.detach:
            selected_lineage = selected_lineage or DetachLineageMode.preserve_origin
            if selected_lineage not in capabilities.allowed_lineage_modes:
                raise ValueError(
                    "P2P_PROJECT_LIFECYCLE_POLICY_DENIED: detach lineage mode is not allowed"
                )
            target_uuid = ProjectUuid.for_operation(binding.project_uuid, operation_id)
            target_kind = self._target_kind(target)
        credential = self._credential(capabilities.server_url)
        request = {
            "contract": PROJECT_LIFECYCLE_PROTOCOL,
            "action": action.value,
            "operation_id": operation_id,
            "project_uuid": binding.project_uuid.value,
            "remote_project_id": binding.remote_project_id.value,
            "replica_id": binding.replica_id.value,
            "authority_epoch": binding.authority_epoch.value,
            "project_revision": binding.last_applied_revision,
            "target_project_uuid": target_uuid.value if target_uuid is not None else None,
            "target_kind": target_kind or None,
            "lineage_mode": selected_lineage.value if selected_lineage is not None else None,
            "keep_local": keep_local,
        }
        response = self.transport.request_json(
            "POST",
            self._url(
                capabilities,
                capabilities.endpoints.preview,
                remote_project_id=binding.remote_project_id.value,
                replica_id=binding.replica_id.value,
            ),
            token=credential.access_token,
            json_body=request,
            max_bytes=PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES,
        )
        preview = _preview_from_mapping(_envelope(response, "project_lifecycle_preview"))
        expected = {
            "action": action,
            "operation_id": operation_id,
            "project_uuid": binding.project_uuid,
            "remote_project_id": binding.remote_project_id,
            "authority_epoch": binding.authority_epoch,
            "project_revision": binding.last_applied_revision,
            "target_project_uuid": target_uuid,
            "lineage_mode": selected_lineage,
        }
        for field, value in expected.items():
            if getattr(preview, field) != value:
                raise ValueError(f"P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: preview {field} differs")
        if preview.target != target_kind:
            raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: preview target differs")
        return preview

    def apply_remote(
        self,
        *,
        action: LifecycleAction,
        operation_id: str,
        preview_token: str,
        confirm: bool,
        keep_local: bool = False,
        detached_root: Path | None = None,
    ) -> LifecycleReceipt:
        if action not in {
            LifecycleAction.suspend,
            LifecycleAction.resume,
            LifecycleAction.archive,
            LifecycleAction.restore,
            LifecycleAction.delete_remote,
        }:
            raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: use the dedicated lifecycle flow")
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: lifecycle apply requires --confirm")
        replay = self.store.receipt(operation_id)
        if replay is not None:
            if replay.action != action:
                raise ValueError(
                    "P2P_PROJECT_LIFECYCLE_OPERATION_CONFLICT: operation ID belongs to another action"
                )
            return replay
        preview = self.preview(
            action=action,
            operation_id=operation_id,
            keep_local=keep_local,
        )
        if preview.preview_token != preview_token:
            raise ValueError("P2P_PREVIEW_STALE: lifecycle project state or inputs changed")
        if not preview.eligible:
            raise ValueError("P2P_PROJECT_LIFECYCLE_BLOCKED: " + "; ".join(preview.blockers))
        binding = self._binding()
        capabilities = self.capabilities(binding.server_url)
        credential = self._credential(capabilities.server_url)
        detach_receipt: dict[str, object] | None = None
        if action == LifecycleAction.delete_remote and keep_local:
            if detached_root is None:
                raise ValueError(
                    "P2P_DETACH_RECEIPT_REQUIRED: --detached-root is required when keeping local state"
                )
            receipt = FilesystemProjectLifecycleStore(detached_root).detach_receipt()
            if (
                receipt is None
                or receipt.source_project_uuid != binding.project_uuid
                or receipt.source_remote_project_id != binding.remote_project_id
                or not receipt.origin_verified
            ):
                raise ValueError(
                    "P2P_DETACH_RECEIPT_REQUIRED: a matching verified detach receipt is required"
                )
            detach_receipt = receipt.to_dict()
        request = {
            "contract": PROJECT_LIFECYCLE_PROTOCOL,
            "action": action.value,
            "operation_id": operation_id,
            "preview_token": preview_token,
            "project_uuid": binding.project_uuid.value,
            "remote_project_id": binding.remote_project_id.value,
            "replica_id": binding.replica_id.value,
            "authority_epoch": binding.authority_epoch.value,
            "expected_project_revision": binding.last_applied_revision,
            "keep_local": keep_local,
            "detach_receipt": detach_receipt,
            "confirm": True,
        }
        try:
            response = self.transport.request_json(
                "POST",
                self._url(
                    capabilities,
                    capabilities.endpoints.apply,
                    remote_project_id=binding.remote_project_id.value,
                    replica_id=binding.replica_id.value,
                ),
                token=credential.access_token,
                json_body=request,
                idempotency_key=operation_id,
                max_bytes=PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES,
            )
            receipt = lifecycle_receipt_from_mapping(
                _envelope(response, "project_lifecycle_receipt")
            )
        except ValueError as exc:
            if not any(
                marker in str(exc)
                for marker in ("P2P_WAVEKIT_RESPONSE_UNKNOWN", "P2P_WAVEKIT_UNAVAILABLE")
            ):
                raise
            recovered = self.operation_status(operation_id)
            if not isinstance(recovered, LifecycleReceipt):
                self._save_recovery(action, operation_id, binding, str(exc))
                raise ValueError(
                    "P2P_PROJECT_LIFECYCLE_OUTCOME_UNKNOWN: query the same operation ID"
                ) from exc
            receipt = recovered
        self._verify_receipt(
            receipt,
            action,
            binding,
            operation_id=operation_id,
        )
        self._apply_local_remote_state(receipt)
        self.store.save_receipt(receipt)
        self.store.save_state(
            LocalLifecycleState(
                operation_id=operation_id,
                action=action,
                status=LifecycleOperationState.applied,
                project_uuid=binding.project_uuid,
                remote_state=receipt.lifecycle_state,
                updated_at=utc_now_iso(),
                message=receipt.message,
            )
        )
        return receipt

    def detach(
        self,
        *,
        operation_id: str,
        preview_token: str,
        target: Path,
        local_owner: str,
        lineage_mode: DetachLineageMode,
        confirm: bool,
    ) -> DetachReceipt:
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: detach requires --confirm")
        target_root = self._validate_detach_target(target, operation_id=operation_id)
        preview = self.preview(
            action=LifecycleAction.detach,
            operation_id=operation_id,
            target=target_root,
            lineage_mode=lineage_mode,
        )
        if preview.preview_token != preview_token:
            raise ValueError("P2P_PREVIEW_STALE: detach project state or inputs changed")
        if not preview.eligible:
            raise ValueError("P2P_PROJECT_LIFECYCLE_BLOCKED: " + "; ".join(preview.blockers))
        binding = self._binding()
        capabilities = self.capabilities(binding.server_url)
        credential = self._credential(capabilities.server_url)
        target_kind = self._target_kind(target_root)
        new_uuid = preview.target_project_uuid
        assert new_uuid is not None
        response = self.transport.request_json(
            "POST",
            self._url(
                capabilities,
                capabilities.endpoints.detach_prepare,
                remote_project_id=binding.remote_project_id.value,
                replica_id=binding.replica_id.value,
            ),
            token=credential.access_token,
            json_body={
                "contract": PROJECT_LIFECYCLE_PROTOCOL,
                "operation_id": operation_id,
                "preview_token": preview_token,
                "project_uuid": binding.project_uuid.value,
                "remote_project_id": binding.remote_project_id.value,
                "replica_id": binding.replica_id.value,
                "authority_epoch": binding.authority_epoch.value,
                "expected_project_revision": binding.last_applied_revision,
                "new_project_uuid": new_uuid.value,
                "lineage_mode": lineage_mode.value,
                "local_owner": _safe_actor(local_owner),
                "target_kind": target_kind,
            },
            idempotency_key=operation_id,
            max_bytes=PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES,
        )
        preparation = _envelope(response, "project_detach_preparation")
        if (
            set(preparation)
            != {
                "contract",
                "detach_id",
                "operation_id",
                "project_uuid",
                "remote_project_id",
                "authority_epoch",
                "project_revision",
                "snapshot",
            }
            or preparation.get("contract") != DETACH_PREPARATION_CONTRACT
        ):
            raise ValueError(
                "P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: detach preparation fields differ"
            )
        if any(
            (
                str(preparation["operation_id"]) != operation_id,
                str(preparation["project_uuid"]) != binding.project_uuid.value,
                str(preparation["remote_project_id"]) != binding.remote_project_id.value,
                preparation["authority_epoch"] != binding.authority_epoch.value,
                preparation["project_revision"] != binding.last_applied_revision,
            )
        ):
            raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: detach source differs")
        snapshot = snapshot_manifest_from_mapping(_mapping(preparation["snapshot"], "snapshot"))
        detach_id = str(preparation["detach_id"])
        _safe_actor(detach_id)
        _manifest_matches_binding(snapshot, binding)
        selected, bundle_path = self.linked.download_verified_snapshot(
            operation_key=operation_id,
            manifest=snapshot,
        )
        staging = target_root.parent / (
            f".{target_root.name}.p2p-detach-{hashlib.sha256(operation_id.encode()).hexdigest()[:16]}"
        )
        if staging.exists() or staging.is_symlink():
            shutil.rmtree(staging, ignore_errors=True)
        try:
            detached_snapshot = self._materialize_detached(
                staging=staging,
                bundle_path=bundle_path,
                manifest=selected,
                operation_id=operation_id,
                new_uuid=new_uuid,
                lineage_mode=lineage_mode,
                local_owner=local_owner,
            )
            complete = self.transport.request_json(
                "POST",
                self._url(
                    capabilities,
                    capabilities.endpoints.detach_complete,
                    remote_project_id=binding.remote_project_id.value,
                    replica_id=binding.replica_id.value,
                    detach_id=detach_id,
                ),
                token=credential.access_token,
                json_body={
                    "contract": PROJECT_LIFECYCLE_PROTOCOL,
                    "detach_id": detach_id,
                    "operation_id": operation_id,
                    "source_project_uuid": binding.project_uuid.value,
                    "source_revision": binding.last_applied_revision,
                    "source_authority_epoch": binding.authority_epoch.value,
                    "new_project_uuid": new_uuid.value,
                    "new_semantic_digest": f"sha256:{detached_snapshot.semantic_state_digest}",
                    "blob_manifest_digest": f"sha256:{detached_snapshot.blob_manifest_digest}",
                    "lineage_mode": lineage_mode.value,
                    "local_owner": _safe_actor(local_owner),
                },
                idempotency_key=operation_id,
                max_bytes=PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES,
            )
            receipt = detach_receipt_from_mapping(_envelope(complete, "detach_receipt"))
            self._verify_detach_receipt(
                receipt,
                binding=binding,
                new_uuid=new_uuid,
                snapshot=detached_snapshot,
                lineage_mode=lineage_mode,
                local_owner=local_owner,
                detach_id=detach_id,
            )
            stage_store = FilesystemProjectLifecycleStore(staging)
            stage_store.save_detach_receipt(receipt)
            stage_store.save_state(
                LocalLifecycleState(
                    operation_id=operation_id,
                    action=LifecycleAction.detach,
                    status=LifecycleOperationState.applied,
                    project_uuid=new_uuid,
                    remote_state=None,
                    updated_at=utc_now_iso(),
                    message="Verified independent local project materialized.",
                )
            )
            self._publish_detached(staging, target_root, operation_id=operation_id)
            return receipt
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        finally:
            shutil.rmtree(bundle_path.parent, ignore_errors=True)

    def publish_copy(
        self,
        *,
        operation_id: str,
        preview_token: str,
        confirm: bool,
    ) -> ProjectPublication:
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: publish-copy requires --confirm")
        preview = self.preview(
            action=LifecycleAction.publish_copy,
            operation_id=operation_id,
        )
        if preview.preview_token != preview_token or not preview.eligible:
            raise ValueError("P2P_PREVIEW_STALE: publication preview is stale or blocked")
        binding = self._binding()
        before = binding.to_storage_dict()
        capabilities = self.capabilities(binding.server_url)
        credential = self._credential(capabilities.server_url)
        archive = self.adapter.snapshots.export_bundle()
        snapshot = self.adapter.snapshots.verify_bundle(archive)
        response = self.transport.upload_bytes(
            self._url(
                capabilities,
                capabilities.endpoints.publication,
                remote_project_id=binding.remote_project_id.value,
                replica_id=binding.replica_id.value,
                operation_id=operation_id,
            ),
            archive.content,
            token=credential.access_token,
            digest=archive.sha256,
            idempotency_key=operation_id,
            max_bytes=max(len(archive.content), 1),
            max_response_bytes=PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES,
        )
        publication = publication_from_mapping(_envelope(response, "project_publication"))
        if (
            publication.project_uuid != binding.project_uuid
            or publication.source_revision != binding.last_applied_revision
            or publication.semantic_digest != snapshot.semantic_state_digest
            or publication.bundle_digest != archive.sha256
            or publication.blob_manifest_digest != snapshot.blob_manifest_digest
        ):
            raise ValueError("P2P_PROJECT_PUBLICATION_MISMATCH: publication differs from snapshot")
        after = self._binding().to_storage_dict()
        if before != after:
            raise ValueError(
                "P2P_PROJECT_PUBLICATION_AUTHORITY_CHANGED: publication altered binding"
            )
        return self.store.save_publication(publication)

    def remove_local_replica(
        self,
        *,
        operation_id: str,
        preview_token: str,
        disposition: LocalReplicaDisposition,
        integration: IntegrationDisposition,
        archive_to: Path | None,
        confirm: bool,
    ) -> dict[str, object]:
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: local replica removal requires --confirm")
        binding = self._binding()
        destination: Path | None = None
        if disposition == LocalReplicaDisposition.archive:
            if archive_to is None:
                raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: --archive-to is required")
            destination = archive_to.expanduser().resolve()
            if (
                destination.exists()
                or destination.is_symlink()
                or destination.is_relative_to(self.root)
            ):
                raise ValueError(
                    "P2P_PROJECT_LIFECYCLE_ARCHIVE_UNSAFE: archive destination must be new and external"
                )
        recovery = self.adapter.backups.recovery_status()
        lock = self.root / ".p2p/.internal/workspace-transactions/apply.lock"
        if recovery.state != "clean" or lock.exists():
            raise ValueError(
                "P2P_PROJECT_LIFECYCLE_RECOVERY_REQUIRED: unresolved local recovery blocks removal"
            )
        receipt = self.store.receipt(operation_id)
        if receipt is None:
            preview = self.preview(
                action=LifecycleAction.remove_local_replica,
                operation_id=operation_id,
            )
            if preview.preview_token != preview_token or not preview.eligible:
                raise ValueError("P2P_PREVIEW_STALE: local-removal preview is stale or blocked")
            caught_up = self.linked.catch_up()
            binding = caught_up.binding
            if binding.last_applied_revision != preview.project_revision:
                raise ValueError(
                    "P2P_PREVIEW_STALE: catch-up advanced the project; prepare a new removal preview"
                )
            snapshot = self.adapter.repository.snapshot()
            if snapshot.semantic_state_digest != binding.snapshot_digest:
                raise ValueError(
                    "P2P_PROJECT_LIFECYCLE_DRIFT: local state differs from verified remote"
                )
            capabilities = self.capabilities(binding.server_url)
            credential = self._credential(capabilities.server_url)
            response = self.transport.request_json(
                "POST",
                self._url(
                    capabilities,
                    capabilities.endpoints.deactivate_replica,
                    remote_project_id=binding.remote_project_id.value,
                    replica_id=binding.replica_id.value,
                ),
                token=credential.access_token,
                json_body={
                    "contract": PROJECT_LIFECYCLE_PROTOCOL,
                    "operation_id": operation_id,
                    "project_uuid": binding.project_uuid.value,
                    "replica_id": binding.replica_id.value,
                    "expected_project_revision": binding.last_applied_revision,
                    "confirm": True,
                },
                idempotency_key=operation_id,
                max_bytes=PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES,
            )
            receipt = lifecycle_receipt_from_mapping(
                _envelope(response, "project_lifecycle_receipt")
            )
            self._verify_receipt(
                receipt,
                LifecycleAction.remove_local_replica,
                binding,
                operation_id=operation_id,
            )
            self.store.save_receipt(receipt)
        else:
            self._verify_receipt(
                receipt,
                LifecycleAction.remove_local_replica,
                binding,
                operation_id=operation_id,
            )
        try:
            integration_status = self._change_integration(integration)
        except (OSError, ValueError) as exc:
            self._save_recovery(
                LifecycleAction.remove_local_replica,
                operation_id,
                binding,
                str(exc),
            )
            raise
        p2p_dir = self.root / ".p2p"
        archived_path = ""
        if disposition == LocalReplicaDisposition.archive:
            assert destination is not None
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.replace(p2p_dir, destination)
            sync_directory(destination.parent)
            archived_path = str(destination)
        else:
            shutil.rmtree(p2p_dir)
            sync_directory(self.root)
        return {
            "contract": PROJECT_LIFECYCLE_PROTOCOL,
            "status": "removed-locally",
            "operation_id": operation_id,
            "project_uuid": binding.project_uuid.value,
            "remote_project_id": binding.remote_project_id.value,
            "remote_deleted": False,
            "disposition": disposition.value,
            "archive_path": archived_path or None,
            "integration": integration.value,
            "integration_status": integration_status,
        }

    def operation_status(self, operation_id: str) -> LifecycleReceipt | DetachReceipt | None:
        local = self.store.receipt(operation_id)
        if local is not None:
            return local
        binding = self._binding()
        capabilities = self.capabilities(binding.server_url)
        credential = self._credential(capabilities.server_url)
        response = self.transport.request_json(
            "GET",
            self._url(
                capabilities,
                capabilities.endpoints.operation,
                remote_project_id=binding.remote_project_id.value,
                operation_id=operation_id,
            ),
            token=credential.access_token,
            max_bytes=PROJECT_LIFECYCLE_MAX_RESPONSE_BYTES,
        )
        payload = _envelope(response, "project_lifecycle_operation")
        if set(payload) != {"contract", "operation_id", "receipt", "detach_receipt"}:
            raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: operation fields differ")
        if (
            payload.get("contract") != PROJECT_LIFECYCLE_PROTOCOL
            or payload.get("operation_id") != operation_id
        ):
            raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: operation identity differs")
        receipt = payload.get("receipt")
        detach = payload.get("detach_receipt")
        if receipt is not None and detach is not None:
            raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: operation has two receipts")
        if isinstance(receipt, Mapping):
            return lifecycle_receipt_from_mapping(receipt)
        if isinstance(detach, Mapping):
            return detach_receipt_from_mapping(detach)
        if receipt is not None or detach is not None:
            raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: receipt must be an object")
        return None

    def recover(self, operation_id: str) -> dict[str, object]:
        receipt = self.operation_status(operation_id)
        if receipt is None:
            return {
                "contract": PROJECT_LIFECYCLE_PROTOCOL,
                "operation_id": operation_id,
                "status": "pending",
                "mutation_performed": False,
            }
        if isinstance(receipt, LifecycleReceipt):
            binding = self._binding()
            self._verify_receipt(
                receipt,
                receipt.action,
                binding,
                operation_id=operation_id,
            )
            self._apply_local_remote_state(receipt)
            self.store.save_receipt(receipt)
            return {
                "contract": PROJECT_LIFECYCLE_PROTOCOL,
                "operation_id": operation_id,
                "status": "recovered",
                "receipt": receipt.to_dict(),
                "mutation_performed": True,
            }
        return {
            "contract": PROJECT_LIFECYCLE_PROTOCOL,
            "operation_id": operation_id,
            "status": "detach-receipt-found",
            "receipt": receipt.to_dict(),
            "mutation_performed": False,
            "message": "Repeat detach with the same inputs to publish its staged result.",
        }

    def _materialize_detached(
        self,
        *,
        staging: Path,
        bundle_path: Path,
        manifest: ReplicaSnapshotManifest,
        operation_id: str,
        new_uuid: ProjectUuid,
        lineage_mode: DetachLineageMode,
        local_owner: str,
    ):
        service = CanonicalMemoryService(root=staging, p2p_dir=staging / ".p2p")
        service.materialize_bundle(
            source=bundle_path,
            operation_key=operation_id,
            actor=_safe_actor(local_owner),
            expected_project_uuid=manifest.project_uuid.value,
            expected_archive_sha256=manifest.bundle_digest,
            confirm=True,
        )
        identity_store = FilesystemProjectIdentityStore(root=staging, p2p_dir=staging / ".p2p")
        source_identity = identity_store.load()
        lineage = source_identity.lineage
        if lineage_mode != DetachLineageMode.drop_origin:
            lineage = (
                *lineage,
                ProjectLineage(
                    relation=LineageRelation.detached_from,
                    source_project_uuid=manifest.project_uuid,
                    source_revision=SourceMemoryRevision(manifest.semantic_state_digest),
                    visibility=(
                        LineageVisibility.private
                        if lineage_mode
                        in {
                            DetachLineageMode.private_origin,
                            DetachLineageMode.emergency_unverified,
                        }
                        else LineageVisibility.preserved
                    ),
                ),
            )
        identity = ProjectIdentity(
            project_uuid=new_uuid,
            display_name=source_identity.display_name,
            mode=ProjectMode.detached,
            replica_id=ReplicaId.for_project_operation(new_uuid, operation_id),
            remote_binding=None,
            lineage=lineage,
        )
        for relative, content in identity_store.candidate_documents(
            identity,
            allow_project_uuid_change=True,
        ).items():
            write_bytes_atomic(staging / relative, content, mode=0o600)
        manifest_store = ProjectStorageManifestStore(staging)
        write_bytes_atomic(
            manifest_store.path,
            manifest_store.render(ProjectStorageManifest(project_uuid=new_uuid.value)),
            mode=0o600,
        )
        permissions = PermissionsService(root=staging, p2p_dir=staging / ".p2p")
        permissions.write_policy(permissions.default_policy_payload(_safe_actor(local_owner)))
        for relative in (
            ".p2p/local/wavekit-binding.yml",
            ".p2p/local/authority-transfer.yml",
            ".p2p/local/authority-transfer-receipt.yml",
        ):
            (staging / relative).unlink(missing_ok=True)
        shutil.rmtree(staging / ".p2p/local/project-replication", ignore_errors=True)
        snapshot = CanonicalMemoryService(
            root=staging,
            p2p_dir=staging / ".p2p",
            store=FilesystemCanonicalMemoryStore(staging),
        ).snapshot()
        if snapshot.project_uuid != new_uuid.value:
            raise ValueError("P2P_PROJECT_LIFECYCLE_IDENTITY_CONFLICT: detached UUID differs")
        return snapshot

    def _publish_detached(self, staging: Path, target: Path, *, operation_id: str) -> None:
        source_p2p = staging / ".p2p"
        if target != self.root:
            if target.exists() and any(target.iterdir()):
                raise ValueError("P2P_PROJECT_LIFECYCLE_TARGET_EXISTS: target must be empty")
            target.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.replace(source_p2p, target / ".p2p")
            sync_directory(target)
            shutil.rmtree(staging, ignore_errors=True)
            return
        digest = hashlib.sha256(operation_id.encode()).hexdigest()[:16]
        backup = self.root.parent / f".{self.root.name}.p2p-linked-backup-{digest}"
        if backup.exists() or backup.is_symlink():
            raise ValueError("P2P_PROJECT_LIFECYCLE_RECOVERY_REQUIRED: detach backup exists")
        active = self.root / ".p2p"
        os.replace(active, backup)
        try:
            os.replace(source_p2p, active)
            sync_directory(self.root)
        except Exception:
            if not active.exists() and backup.exists():
                os.replace(backup, active)
            raise

    def _apply_local_remote_state(self, receipt: LifecycleReceipt) -> None:
        state = receipt.lifecycle_state
        if receipt.action == LifecycleAction.suspend:
            self.adapter.linked_replicas.mark_access(ReplicaAccessState.suspended)
            return
        if receipt.action == LifecycleAction.resume:
            # Catch-up while suspended cannot itself restore write access.
            self.linked.catch_up()
            self.adapter.linked_replicas.mark_access(ReplicaAccessState.active)
            return
        if receipt.action == LifecycleAction.restore:
            self.linked.catch_up()
            self.adapter.linked_replicas.mark_access(ReplicaAccessState.active)
            return
        if state == RemoteLifecycleState.archived:
            self.adapter.linked_replicas.mark_access(
                ReplicaAccessState.archived,
                error_code="P2P_REMOTE_PROJECT_ARCHIVED",
            )
        elif state in {
            RemoteLifecycleState.deleted,
            RemoteLifecycleState.tombstoned,
            RemoteLifecycleState.pending_delete,
            RemoteLifecycleState.retained,
        }:
            self.adapter.linked_replicas.mark_access(
                ReplicaAccessState.tombstoned,
                error_code="P2P_REMOTE_PROJECT_TOMBSTONED",
            )
        elif state == RemoteLifecycleState.access_revoked:
            self.adapter.linked_replicas.mark_access(
                ReplicaAccessState.access_revoked,
                error_code="P2P_LINKED_REPLICA_ACCESS_REVOKED",
            )

    def _save_recovery(
        self,
        action: LifecycleAction,
        operation_id: str,
        binding: LinkedReplicaBinding,
        message: str,
    ) -> None:
        self.store.save_state(
            LocalLifecycleState(
                operation_id=operation_id,
                action=action,
                status=LifecycleOperationState.recovery_required,
                project_uuid=binding.project_uuid,
                updated_at=utc_now_iso(),
                message=message,
            )
        )

    def _change_integration(self, choice: IntegrationDisposition) -> str:
        callback = (
            self.integration_remove
            if choice == IntegrationDisposition.remove
            else (
                (lambda: self.integration_transition("remote-only"))
                if self.integration_transition is not None
                else None
            )
        )
        if callback is None:
            return "not-configured"
        result = callback()
        status = str(getattr(result, "status", "unknown"))
        if status == "blocked":
            raise ValueError(
                "P2P_PROJECT_LIFECYCLE_INTEGRATION_BLOCKED: user-owned integration content was preserved"
            )
        return status

    @staticmethod
    def _verify_receipt(
        receipt: LifecycleReceipt,
        action: LifecycleAction,
        binding: LinkedReplicaBinding,
        *,
        operation_id: str,
    ) -> None:
        if (
            receipt.operation_id != operation_id
            or receipt.action != action
            or receipt.project_uuid != binding.project_uuid
            or receipt.remote_project_id != binding.remote_project_id
            or receipt.authority_epoch != binding.authority_epoch
            or receipt.project_revision < binding.last_applied_revision
        ):
            raise ValueError("P2P_PROJECT_LIFECYCLE_RECEIPT_MISMATCH: receipt binding differs")

    @staticmethod
    def _verify_detach_receipt(
        receipt: DetachReceipt,
        *,
        binding: LinkedReplicaBinding,
        new_uuid: ProjectUuid,
        snapshot: object,
        lineage_mode: DetachLineageMode,
        local_owner: str,
        detach_id: str,
    ) -> None:
        if (
            receipt.detach_id != detach_id
            or receipt.source_project_uuid != binding.project_uuid
            or receipt.source_remote_project_id != binding.remote_project_id
            or receipt.source_revision != binding.last_applied_revision
            or receipt.source_authority_epoch != binding.authority_epoch
            or receipt.new_project_uuid != new_uuid
            or receipt.new_semantic_digest != getattr(snapshot, "semantic_state_digest")
            or receipt.blob_manifest_digest != getattr(snapshot, "blob_manifest_digest")
            or receipt.lineage_mode != lineage_mode
            or receipt.local_owner != _safe_actor(local_owner)
            or not receipt.origin_verified
        ):
            raise ValueError("P2P_DETACH_RECEIPT_MISMATCH: receipt differs from staged project")

    def _credential(self, server_url: str):
        credential = self.credentials.get(server_url)
        if credential is None or (
            credential.expires_at and credential.expires_at <= int(self.now()) + 15
        ):
            raise ValueError("P2P_WAVEKIT_AUTH_REQUIRED: login before lifecycle operation")
        return credential

    def _binding(self) -> LinkedReplicaBinding:
        binding = self.adapter.linked_replicas.load()
        if binding is None:
            raise ValueError("P2P_LINKED_REPLICA_NOT_FOUND: lifecycle requires a linked project")
        return binding

    @staticmethod
    def _verify_server(binding: LinkedReplicaBinding, capabilities: LifecycleCapabilities) -> None:
        if binding.server_instance_id != capabilities.server_instance_id:
            raise ValueError("P2P_LINKED_REPLICA_SERVER_MISMATCH: lifecycle server changed")

    def _target_kind(self, target: Path | None) -> str:
        if target is None:
            return "new-directory"
        expanded = target.expanduser()
        if expanded.is_symlink():
            raise ValueError("P2P_PROJECT_LIFECYCLE_TARGET_UNSAFE: symlink target is forbidden")
        resolved = expanded.resolve()
        if resolved == self.root:
            return "same-directory"
        if resolved.is_relative_to(self.root) or self.root.is_relative_to(resolved):
            raise ValueError("P2P_PROJECT_LIFECYCLE_TARGET_UNSAFE: nested detach is forbidden")
        return "new-directory"

    def _validate_detach_target(self, target: Path, *, operation_id: str) -> Path:
        resolved = target.expanduser().resolve()
        kind = self._target_kind(target)
        if kind == "new-directory":
            if resolved.exists() and (
                not resolved.is_dir() or any(resolved.iterdir())
            ):
                raise ValueError("P2P_PROJECT_LIFECYCLE_TARGET_EXISTS: target must be empty")
            return resolved
        digest = hashlib.sha256(operation_id.encode()).hexdigest()[:16]
        backup = self.root.parent / f".{self.root.name}.p2p-linked-backup-{digest}"
        if backup.exists() or backup.is_symlink():
            raise ValueError("P2P_PROJECT_LIFECYCLE_RECOVERY_REQUIRED: detach backup exists")
        return resolved

    def _url(
        self,
        capabilities: LifecycleCapabilities,
        endpoint: str,
        **values: str,
    ) -> str:
        rendered = endpoint
        for key, value in values.items():
            rendered = rendered.replace("{" + key + "}", quote(value, safe=""))
        if "{" in rendered or "}" in rendered:
            raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: endpoint is incomplete")
        return _same_origin_url(capabilities.server_url, rendered)

    @staticmethod
    def _suggestions(
        binding: LinkedReplicaBinding | None,
        remote: Mapping[str, object] | None,
        diagnostic: str,
    ) -> list[str]:
        if binding is None:
            return ["create-from-local"]
        state = str(remote.get("state")) if remote is not None else ""
        if state == RemoteLifecycleState.archived.value:
            return ["restore", "remove-local-replica"]
        if state in {
            RemoteLifecycleState.pending_delete.value,
            RemoteLifecycleState.retained.value,
            RemoteLifecycleState.deleted.value,
            RemoteLifecycleState.tombstoned.value,
        }:
            return ["wait-for-authorized-restore", "remove-local-replica"]
        if (
            state == RemoteLifecycleState.access_revoked.value
            or "ACCESS_REVOKED" in diagnostic
        ):
            return ["request-authorized-export", "remove-local-replica"]
        if state == RemoteLifecycleState.unreachable.value or diagnostic:
            return ["retry-status", "configure-emergency-detach-policy"]
        if (
            state == RemoteLifecycleState.suspended.value
            or binding.state == ReplicaAccessState.suspended
        ):
            return ["resume", "detach", "remove-local-replica"]
        return ["suspend", "detach", "archive", "publish-copy", "remove-local-replica"]


def _preview_from_mapping(raw: Mapping[str, object]) -> LifecyclePreview:
    expected = {
        "contract",
        "action",
        "operation_id",
        "project_uuid",
        "remote_project_id",
        "authority_epoch",
        "project_revision",
        "lifecycle_state",
        "target_project_uuid",
        "target",
        "lineage_mode",
        "retention_days",
        "effects",
        "blockers",
        "eligible",
        "preview_token",
    }
    effects = raw.get("effects")
    blockers = raw.get("blockers")
    if (
        set(raw) != expected
        or raw.get("contract") != PROJECT_LIFECYCLE_PREVIEW_CONTRACT
        or not isinstance(effects, list)
        or not all(isinstance(item, str) for item in effects)
        or not isinstance(blockers, list)
        or not all(isinstance(item, str) for item in blockers)
        or raw.get("eligible") is not (not blockers)
    ):
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: preview fields differ")
    remote = raw.get("remote_project_id")
    target = raw.get("target_project_uuid")
    lineage = raw.get("lineage_mode")
    epoch = raw.get("authority_epoch")
    revision = raw.get("project_revision")
    retention = raw.get("retention_days")
    if any(
        isinstance(value, bool) or not isinstance(value, int) for value in (epoch, revision)
    ) or (
        retention is not None and (isinstance(retention, bool) or not isinstance(retention, int))
    ):
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: numeric preview field differs")
    preview = LifecyclePreview(
        action=LifecycleAction(str(raw["action"])),
        operation_id=str(raw["operation_id"]),
        project_uuid=ProjectUuid(str(raw["project_uuid"])),
        remote_project_id=RemoteProjectId(str(remote)) if remote is not None else None,
        authority_epoch=AuthorityEpoch(epoch),
        project_revision=revision,
        lifecycle_state=RemoteLifecycleState(str(raw["lifecycle_state"])),
        target_project_uuid=ProjectUuid(str(target)) if target is not None else None,
        target=str(raw.get("target") or ""),
        lineage_mode=DetachLineageMode(str(lineage)) if lineage is not None else None,
        retention_days=retention or 0,
        effects=tuple(effects),
        blockers=tuple(blockers),
        preview_token=str(raw.get("preview_token") or ""),
    )
    if preview.with_token().preview_token != preview.preview_token:
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: preview token differs")
    return preview


def _remote_status(
    raw: Mapping[str, object], binding: LinkedReplicaBinding
) -> Mapping[str, object]:
    expected = {
        "contract",
        "project_uuid",
        "remote_project_id",
        "authority_epoch",
        "project_revision",
        "state",
        "retention_until",
        "tombstone_reason",
    }
    if set(raw) != expected or raw.get("contract") != "p2p-project-lifecycle-status/v1":
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: status fields differ")
    epoch = raw.get("authority_epoch")
    revision = raw.get("project_revision")
    if (
        str(raw["project_uuid"]) != binding.project_uuid.value
        or str(raw["remote_project_id"]) != binding.remote_project_id.value
        or isinstance(epoch, bool)
        or not isinstance(epoch, int)
        or epoch != binding.authority_epoch.value
        or isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision < binding.last_applied_revision
    ):
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: status binding differs")
    RemoteLifecycleState(str(raw["state"]))
    return raw


def _manifest_matches_binding(
    manifest: ReplicaSnapshotManifest, binding: LinkedReplicaBinding
) -> None:
    if (
        manifest.project_uuid != binding.project_uuid
        or manifest.remote_project_id != binding.remote_project_id
        or manifest.replica_id != binding.replica_id
        or manifest.authority_epoch != binding.authority_epoch
        or manifest.remote_revision != binding.last_applied_revision
    ):
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: snapshot binding differs")


def _same_origin_url(server_url: str, endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: endpoint must be relative")
    joined = urljoin(server_url.rstrip("/") + "/", endpoint.lstrip("/"))
    base = urlsplit(server_url)
    target = urlsplit(joined)
    if (target.scheme, target.hostname, target.port) != (base.scheme, base.hostname, base.port):
        raise ValueError("P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: endpoint changed origin")
    return urlunsplit((target.scheme, target.netloc, target.path, target.query, ""))


def _endpoint(mapping: Mapping[str, object], name: str) -> str:
    value = str(mapping.get(name) or "")
    parsed = urlsplit(value)
    if not value.startswith("/") or parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError(f"P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: {name} endpoint is unsafe")
    return value


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: {label} must be an object")
    return value


def _envelope(value: object, key: str) -> Mapping[str, object]:
    mapping = _mapping(value, "response")
    if set(mapping) != {key}:
        raise ValueError(f"P2P_PROJECT_LIFECYCLE_RESPONSE_INVALID: expected {key} envelope")
    return _mapping(mapping[key], key)


def _safe_actor(value: str) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}", text):
        raise ValueError("P2P_PROJECT_LIFECYCLE_INVALID: actor is invalid")
    return text

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

import pytest
from typer.testing import CliRunner

from p2p_engine.adapters.wavekit_credentials import MemoryWaveKitCredentialStore
from p2p_engine.cli import app
from p2p_engine.core.authority_transfer import WaveKitCredential
from p2p_engine.core.project_identity import (
    AuthorityEpoch,
    ProjectMode,
    ProjectUuid,
    RemoteProjectId,
)
from p2p_engine.core.project_lifecycle import (
    DETACH_PREPARATION_CONTRACT,
    DETACH_RECEIPT_CONTRACT,
    PROJECT_LIFECYCLE_CAPABILITY_CONTRACT,
    PROJECT_LIFECYCLE_PROTOCOL,
    PROJECT_LIFECYCLE_RECEIPT_CONTRACT,
    PROJECT_PUBLICATION_CONTRACT,
    DetachLineageMode,
    DetachReceipt,
    IntegrationDisposition,
    LifecycleAction,
    LifecycleOperationState,
    LifecyclePreview,
    LifecycleReceipt,
    LocalReplicaDisposition,
    ProjectPublication,
    RemoteLifecycleState,
    detach_receipt_from_mapping,
    lifecycle_receipt_from_mapping,
    publication_from_mapping,
)
from p2p_engine.mcp.registry import TOOL_NAMES
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.authority_transfer import AuthorityTransferService
from p2p_engine.services.linked_replica import LinkedReplicaService
from p2p_engine.services.project_application import ProjectApplicationService
from p2p_engine.services.project_lifecycle import ProjectLifecycleService
from p2p_engine.storage.filesystem_project_lifecycle import FilesystemProjectLifecycleStore
from tests.filesystem_assertions import assert_no_workspace_mutation
from tests.test_authority_transfer import OWNER_PROFILE as TRANSFER_OWNER_PROFILE
from tests.test_authority_transfer import FakeWaveKitTransport
from tests.test_linked_replica import (
    PROFILE,
    REMOTE_ID,
    SERVER,
    SERVER_ID,
    FakeIntegration,
    FakeReplicaTransport,
    _source_bundle,
)

runner = CliRunner()


class LifecycleTransport(FakeReplicaTransport):
    def __init__(self, bundle: bytes, snapshot: object) -> None:
        super().__init__(bundle, snapshot)
        self.lifecycle_state = RemoteLifecycleState.active
        self.receipts: dict[str, dict[str, object]] = {}
        self.preview_requests: list[dict[str, object]] = []
        self.lose_next_apply_response = False
        self.remote_deleted = False
        self.replica_deactivated = False
        self.deactivation_calls = 0
        self.fail_detach_complete = False
        self.lifecycle_unavailable = False

    def request_json(self, method: str, url: str, **kwargs: object) -> object:
        if url.endswith("/.well-known/p2p-project-lifecycle"):
            if self.lifecycle_unavailable:
                raise ValueError("P2P_WAVEKIT_UNAVAILABLE: lifecycle endpoint is offline")
            return _lifecycle_capabilities()
        json_body = kwargs.get("json_body")
        body = dict(json_body) if isinstance(json_body, Mapping) else {}
        if method == "POST" and url.endswith("/lifecycle/preview"):
            self.preview_requests.append(body)
            action = LifecycleAction(str(body["action"]))
            effects = {
                LifecycleAction.detach: ("create-new-local-project", "preserve-remote"),
                LifecycleAction.remove_local_replica: (
                    "deactivate-one-replica",
                    "preserve-remote",
                ),
                LifecycleAction.publish_copy: (
                    "create-immutable-publication",
                    "preserve-authority",
                ),
            }.get(action, (f"remote-{action.value}",))
            preview = LifecyclePreview(
                action=action,
                operation_id=str(body["operation_id"]),
                project_uuid=ProjectUuid(str(body["project_uuid"])),
                remote_project_id=RemoteProjectId(str(body["remote_project_id"])),
                authority_epoch=AuthorityEpoch(int(body["authority_epoch"])),
                project_revision=int(body["project_revision"]),
                lifecycle_state=self.lifecycle_state,
                target_project_uuid=(
                    ProjectUuid(str(body["target_project_uuid"]))
                    if body.get("target_project_uuid") is not None
                    else None
                ),
                target=str(body.get("target_kind") or ""),
                lineage_mode=(
                    DetachLineageMode(str(body["lineage_mode"]))
                    if body.get("lineage_mode") is not None
                    else None
                ),
                retention_days=30,
                effects=effects,
            ).with_token()
            return {"project_lifecycle_preview": preview.to_dict()}
        if method == "POST" and url.endswith("/lifecycle/apply"):
            action = LifecycleAction(str(body["action"]))
            next_state = {
                LifecycleAction.suspend: RemoteLifecycleState.suspended,
                LifecycleAction.resume: RemoteLifecycleState.active,
                LifecycleAction.archive: RemoteLifecycleState.archived,
                LifecycleAction.restore: RemoteLifecycleState.active,
                LifecycleAction.delete_remote: RemoteLifecycleState.retained,
            }[action]
            self.lifecycle_state = next_state
            self.remote_deleted = action == LifecycleAction.delete_remote
            receipt = self._receipt(str(body["operation_id"]), action, next_state)
            self.receipts[str(body["operation_id"])] = receipt
            if self.lose_next_apply_response:
                self.lose_next_apply_response = False
                raise ValueError("P2P_WAVEKIT_RESPONSE_UNKNOWN: response lost")
            return {"project_lifecycle_receipt": receipt}
        if method == "GET" and url.endswith("/lifecycle/status"):
            return {
                "project_lifecycle_status": {
                    "contract": "p2p-project-lifecycle-status/v1",
                    "project_uuid": self.snapshot.project_uuid,
                    "remote_project_id": REMOTE_ID,
                    "authority_epoch": 2,
                    "project_revision": self.remote_revision,
                    "state": self.lifecycle_state.value,
                    "retention_until": None,
                    "tombstone_reason": None,
                }
            }
        if method == "GET" and "/lifecycle/operations/" in url:
            operation_id = url.rsplit("/", 1)[-1]
            return {
                "project_lifecycle_operation": {
                    "contract": PROJECT_LIFECYCLE_PROTOCOL,
                    "operation_id": operation_id,
                    "receipt": self.receipts.get(operation_id),
                    "detach_receipt": None,
                }
            }
        if method == "POST" and url.endswith("/detach/prepare"):
            return {
                "project_detach_preparation": {
                    "contract": DETACH_PREPARATION_CONTRACT,
                    "detach_id": "det_test_001",
                    "operation_id": body["operation_id"],
                    "project_uuid": body["project_uuid"],
                    "remote_project_id": body["remote_project_id"],
                    "authority_epoch": body["authority_epoch"],
                    "project_revision": body["expected_project_revision"],
                    "snapshot": self._manifest(self.replica_id, session="9"),
                }
            }
        if method == "POST" and "/detach/det_test_001/complete" in url:
            if self.fail_detach_complete:
                raise ValueError("P2P_WAVEKIT_UNAVAILABLE: detach completion failed")
            return {
                "detach_receipt": {
                    "contract": DETACH_RECEIPT_CONTRACT,
                    "detach_id": body["detach_id"],
                    "source_project_uuid": body["source_project_uuid"],
                    "source_remote_project_id": REMOTE_ID,
                    "source_revision": body["source_revision"],
                    "source_authority_epoch": body["source_authority_epoch"],
                    "new_project_uuid": body["new_project_uuid"],
                    "new_semantic_digest": body["new_semantic_digest"],
                    "blob_manifest_digest": body["blob_manifest_digest"],
                    "lineage_mode": body["lineage_mode"],
                    "local_owner": body["local_owner"],
                    "issued_at": "2030-01-01T00:00:00Z",
                    "verification_token": "verification_token_001",
                    "origin_verified": True,
                    "status": "verified",
                }
            }
        if method == "POST" and url.endswith("/deactivate-replica"):
            self.replica_deactivated = True
            self.deactivation_calls += 1
            receipt = self._receipt(
                str(body["operation_id"]),
                LifecycleAction.remove_local_replica,
                RemoteLifecycleState.active,
            )
            return {"project_lifecycle_receipt": receipt}
        return super().request_json(method, url, **kwargs)

    def upload_bytes(self, url: str, content: bytes, **kwargs: object) -> object:
        if "/publications/" not in url:
            return super().upload_bytes(url, content, **kwargs)
        operation_id = url.rsplit("/", 1)[-1]
        return {
            "project_publication": {
                "contract": PROJECT_PUBLICATION_CONTRACT,
                "publication_id": f"pub_{operation_id}",
                "version": 1,
                "project_uuid": self.snapshot.project_uuid,
                "source_revision": self.remote_revision,
                "semantic_digest": f"sha256:{self.snapshot.semantic_state_digest}",
                "bundle_digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
                "blob_manifest_digest": f"sha256:{self.snapshot.blob_manifest_digest}",
                "created_at": "2030-01-01T00:00:00Z",
                "immutable": True,
            }
        }

    def _receipt(
        self,
        operation_id: str,
        action: LifecycleAction,
        state: RemoteLifecycleState,
    ) -> dict[str, object]:
        return {
            "contract": PROJECT_LIFECYCLE_RECEIPT_CONTRACT,
            "operation_id": operation_id,
            "action": action.value,
            "status": LifecycleOperationState.applied.value,
            "project_uuid": self.snapshot.project_uuid,
            "remote_project_id": REMOTE_ID,
            "authority_epoch": 2,
            "project_revision": self.remote_revision,
            "lifecycle_state": state.value,
            "issued_at": "2030-01-01T00:00:00Z",
            "retention_until": (
                "2030-01-31T00:00:00Z"
                if action == LifecycleAction.delete_remote
                else None
            ),
            "message": f"{action.value} applied",
        }


def _lifecycle_capabilities() -> dict[str, object]:
    return {
        "project_lifecycle_capabilities": {
            "contract": PROJECT_LIFECYCLE_CAPABILITY_CONTRACT,
            "protocol": PROJECT_LIFECYCLE_PROTOCOL,
            "server_instance_id": SERVER_ID,
            "endpoints": {
                "status": "/api/projects/{remote_project_id}/replicas/{replica_id}/lifecycle/status",
                "preview": "/api/projects/{remote_project_id}/replicas/{replica_id}/lifecycle/preview",
                "apply": "/api/projects/{remote_project_id}/replicas/{replica_id}/lifecycle/apply",
                "operation": "/api/projects/{remote_project_id}/lifecycle/operations/{operation_id}",
                "detach_prepare": "/api/projects/{remote_project_id}/replicas/{replica_id}/detach/prepare",
                "detach_complete": "/api/projects/{remote_project_id}/replicas/{replica_id}/detach/{detach_id}/complete",
                "publication": "/api/projects/{remote_project_id}/replicas/{replica_id}/publications/{operation_id}",
                "deactivate_replica": "/api/projects/{remote_project_id}/replicas/{replica_id}/deactivate-replica",
            },
            "retention_days": 30,
            "allowed_lineage_modes": [
                "preserve-origin",
                "private-origin",
                "drop-origin",
            ],
            "emergency_detach_allowed": False,
        }
    }


def _credentials() -> MemoryWaveKitCredentialStore:
    store = MemoryWaveKitCredentialStore()
    store.set(
        SERVER,
        WaveKitCredential(
            access_token="secret-access",
            account_profile_ref=PROFILE,
        ),
    )
    return store


def _scenario(tmp_path: Path):
    snapshot, bundle, digest = _source_bundle(tmp_path)
    root = tmp_path / "linked"
    transport = LifecycleTransport(bundle, snapshot)
    LinkedReplicaService(
        root=root,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_000,
    ).clone(
        server_url=SERVER,
        remote_project_id=REMOTE_ID,
        account_profile_ref=PROFILE,
        operation_key="owner:clone:lifecycle",
        confirm=True,
    )
    application = ProjectApplicationService(root)
    lifecycle = ProjectLifecycleService(
        root=root,
        adapter=application.adapter,
        transport=transport,
        credentials=_credentials(),
        linked_replica=LinkedReplicaService(
            root=root,
            transport=transport,
            credentials=_credentials(),
            integration_transition=lambda: FakeIntegration(),
            store=application.adapter.linked_replicas,
            now=lambda: 1_900_000_000,
        ),
        integration_transition=lambda _profile: FakeIntegration(),
        integration_remove=lambda: FakeIntegration(),
        now=lambda: 1_900_000_000,
    )
    return root, application, lifecycle, transport, digest


@pytest.mark.unit
def test_lifecycle_contracts_round_trip_and_reject_extra_fields() -> None:
    receipt = LifecycleReceipt(
        operation_id="op_suspend_1",
        action=LifecycleAction.suspend,
        status=LifecycleOperationState.applied,
        project_uuid=ProjectUuid("60f0a643-50aa-4a08-99ce-a0946f9951c1"),
        remote_project_id=RemoteProjectId(REMOTE_ID),
        authority_epoch=AuthorityEpoch(2),
        project_revision=4,
        lifecycle_state=RemoteLifecycleState.suspended,
        issued_at="2030-01-01T00:00:00Z",
    )
    assert lifecycle_receipt_from_mapping(receipt.to_dict()) == receipt
    with pytest.raises(ValueError, match="fields differ"):
        lifecycle_receipt_from_mapping({**receipt.to_dict(), "secret": "no"})

    detached = DetachReceipt(
        detach_id="det_contract_1",
        source_project_uuid=receipt.project_uuid,
        source_remote_project_id=receipt.remote_project_id,
        source_revision=4,
        source_authority_epoch=receipt.authority_epoch,
        new_project_uuid=ProjectUuid("736f2c07-5ac7-4d65-aa24-d04a4b17e925"),
        new_semantic_digest="1" * 64,
        blob_manifest_digest="2" * 64,
        lineage_mode=DetachLineageMode.private_origin,
        local_owner="owner",
        issued_at="2030-01-01T00:00:00Z",
        verification_token="verify_contract_1",
    )
    assert detach_receipt_from_mapping(detached.to_dict()) == detached

    publication = ProjectPublication(
        publication_id="pub_contract_1",
        version=1,
        project_uuid=receipt.project_uuid,
        source_revision=4,
        semantic_digest="1" * 64,
        bundle_digest="2" * 64,
        blob_manifest_digest="3" * 64,
        created_at="2030-01-01T00:00:00Z",
    )
    assert publication_from_mapping(publication.to_dict()) == publication


@pytest.mark.unit
def test_suspend_and_resume_preserve_identity_binding_and_cursor(tmp_path: Path) -> None:
    root, application, lifecycle, _transport, _digest = _scenario(tmp_path)
    before = application.adapter.linked_replicas.load()
    assert before is not None

    preview = lifecycle.preview(
        action=LifecycleAction.suspend,
        operation_id="op_suspend_identity_1",
    )
    lifecycle.apply_remote(
        action=LifecycleAction.suspend,
        operation_id=preview.operation_id,
        preview_token=preview.preview_token,
        confirm=True,
    )
    suspended = ProjectApplicationService(root)
    binding = suspended.adapter.linked_replicas.load()
    assert binding is not None
    assert binding.state.value == "suspended"
    assert suspended.project_identity().mode == ProjectMode.link_suspended
    assert (
        binding.project_uuid,
        binding.remote_project_id,
        binding.replica_id,
        binding.authority_epoch,
        binding.cursor,
    ) == (
        before.project_uuid,
        before.remote_project_id,
        before.replica_id,
        before.authority_epoch,
        before.cursor,
    )

    lifecycle = _service_for(root, lifecycle.transport)
    preview = lifecycle.preview(
        action=LifecycleAction.resume,
        operation_id="op_resume_identity_1",
    )
    lifecycle.apply_remote(
        action=LifecycleAction.resume,
        operation_id=preview.operation_id,
        preview_token=preview.preview_token,
        confirm=True,
    )
    resumed = ProjectApplicationService(root)
    assert resumed.project_identity().mode == ProjectMode.linked
    assert resumed.adapter.linked_replicas.load().state.value == "active"  # type: ignore[union-attr]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("lineage_mode", "expected_visibility", "expected_count"),
    [
        (DetachLineageMode.preserve_origin, "preserved", 1),
        (DetachLineageMode.private_origin, "private", 1),
        (DetachLineageMode.drop_origin, None, 0),
    ],
)
def test_detach_materializes_complete_independent_project_and_preserves_source(
    tmp_path: Path,
    lineage_mode: DetachLineageMode,
    expected_visibility: str | None,
    expected_count: int,
) -> None:
    root, application, lifecycle, transport, digest = _scenario(tmp_path)
    source_identity = application.project_identity()
    target = tmp_path / f"detached-{lineage_mode.value}"
    operation_id = f"op_detach_{lineage_mode.value.replace('-', '_')}"
    preview = lifecycle.preview(
        action=LifecycleAction.detach,
        operation_id=operation_id,
        target=target,
        lineage_mode=lineage_mode,
    )
    receipt = lifecycle.detach(
        operation_id=operation_id,
        preview_token=preview.preview_token,
        target=target,
        local_owner="mrjungle",
        lineage_mode=lineage_mode,
        confirm=True,
    )

    source = ProjectApplicationService(root)
    detached = ProjectApplicationService(target)
    identity = detached.project_identity()
    assert source.project_identity() == source_identity
    assert source.adapter.linked_replicas.load() is not None
    assert identity.mode == ProjectMode.detached
    assert identity.project_uuid != source_identity.project_uuid
    assert identity.remote_binding is None
    assert detached.adapter.linked_replicas.load() is None
    assert len(identity.lineage) == expected_count
    if identity.lineage:
        assert identity.lineage[-1].visibility.value == expected_visibility
    assert detached.adapter.blobs.read(f"sha256:{digest}") == b"linked replica managed blob\n"
    assert receipt.new_project_uuid == identity.project_uuid
    assert FilesystemProjectLifecycleStore(target).detach_receipt() == receipt
    assert transport.remote_deleted is False
    added = detached.permissions_actor_add("local-contributor")
    assert added.actor_id == "local-contributor"


@pytest.mark.unit
def test_detach_failure_discards_staging_and_leaves_source_untouched(tmp_path: Path) -> None:
    root, application, lifecycle, transport, _digest = _scenario(tmp_path)
    before = application.project_identity()
    target = tmp_path / "failed-detach"
    preview = lifecycle.preview(
        action=LifecycleAction.detach,
        operation_id="op_detach_failure_1",
        target=target,
        lineage_mode=DetachLineageMode.preserve_origin,
    )
    transport.fail_detach_complete = True

    with pytest.raises(ValueError, match="detach completion failed"):
        lifecycle.detach(
            operation_id=preview.operation_id,
            preview_token=preview.preview_token,
            target=target,
            local_owner="mrjungle",
            lineage_mode=DetachLineageMode.preserve_origin,
            confirm=True,
        )

    assert ProjectApplicationService(root).project_identity() == before
    assert ProjectApplicationService(root).adapter.linked_replicas.load() is not None
    assert not target.exists()
    assert not list(tmp_path.glob(".*.p2p-detach-*"))


@pytest.mark.unit
def test_detach_rejects_nonempty_target_before_remote_preparation(tmp_path: Path) -> None:
    root, application, lifecycle, transport, _digest = _scenario(tmp_path)
    target = tmp_path / "occupied-target"
    target.mkdir()
    (target / "user-file.txt").write_text("preserve me\n", encoding="utf-8")
    before = application.project_identity()

    with pytest.raises(ValueError, match="TARGET_EXISTS"):
        lifecycle.detach(
            operation_id="op_detach_occupied_target_1",
            preview_token="0" * 64,
            target=target,
            local_owner="mrjungle",
            lineage_mode=DetachLineageMode.preserve_origin,
            confirm=True,
        )

    assert transport.preview_requests == []
    assert (target / "user-file.txt").read_text(encoding="utf-8") == "preserve me\n"
    assert ProjectApplicationService(root).project_identity() == before


@pytest.mark.unit
def test_same_directory_detach_activates_new_identity_and_retains_backup(
    tmp_path: Path,
) -> None:
    root, application, lifecycle, _transport, _digest = _scenario(tmp_path)
    source_uuid = application.project_identity().project_uuid
    operation_id = "op_detach_same_directory_1"
    preview = lifecycle.preview(
        action=LifecycleAction.detach,
        operation_id=operation_id,
        target=root,
        lineage_mode=DetachLineageMode.private_origin,
    )

    receipt = lifecycle.detach(
        operation_id=operation_id,
        preview_token=preview.preview_token,
        target=root,
        local_owner="mrjungle",
        lineage_mode=DetachLineageMode.private_origin,
        confirm=True,
    )

    detached = ProjectApplicationService(root)
    assert detached.project_identity().mode == ProjectMode.detached
    assert detached.project_identity().project_uuid == receipt.new_project_uuid
    assert detached.project_identity().project_uuid != source_uuid
    assert detached.adapter.linked_replicas.load() is None
    backup = root.parent / (
        f".{root.name}.p2p-linked-backup-"
        f"{hashlib.sha256(operation_id.encode()).hexdigest()[:16]}"
    )
    assert (backup / "local/wavekit-binding.yml").is_file()


@pytest.mark.unit
def test_detached_project_can_transfer_as_new_remote_without_changing_uuid(
    tmp_path: Path,
) -> None:
    _root, _application, lifecycle, _transport, _digest = _scenario(tmp_path)
    target = tmp_path / "detached-transfer"
    preview = lifecycle.preview(
        action=LifecycleAction.detach,
        operation_id="op_detach_before_transfer_1",
        target=target,
        lineage_mode=DetachLineageMode.preserve_origin,
    )
    lifecycle.detach(
        operation_id=preview.operation_id,
        preview_token=preview.preview_token,
        target=target,
        local_owner="mrjungle",
        lineage_mode=DetachLineageMode.preserve_origin,
        confirm=True,
    )
    application = ProjectApplicationService(target)
    detached_uuid = application.project_identity().project_uuid
    transfer = AuthorityTransferService(
        adapter=application.adapter,
        integration_transition=lambda: FakeIntegration(),
        transport=FakeWaveKitTransport(),
        credentials=_credentials(),
        now=lambda: 1_900_000_000,
        sleep=lambda _seconds: None,
    )

    transfer_preview = transfer.preview(
        server_url=SERVER,
        owner_profile_ref=TRANSFER_OWNER_PROFILE,
        operation_key="detached-create-as-new",
    )
    result = transfer.apply(
        server_url=SERVER,
        owner_profile_ref=TRANSFER_OWNER_PROFILE,
        operation_key="detached-create-as-new",
        preview_token=transfer_preview.preview_token,
        confirm=True,
    )

    assert result.status == "linked"
    assert application.project_identity().mode == ProjectMode.linked
    assert application.project_identity().project_uuid == detached_uuid


@pytest.mark.unit
def test_publish_copy_is_immutable_and_authority_neutral(tmp_path: Path) -> None:
    _root, application, lifecycle, _transport, _digest = _scenario(tmp_path)
    binding = application.adapter.linked_replicas.load()
    assert binding is not None
    before = binding.to_storage_dict()
    preview = lifecycle.preview(
        action=LifecycleAction.publish_copy,
        operation_id="op_publication_1",
    )
    publication = lifecycle.publish_copy(
        operation_id=preview.operation_id,
        preview_token=preview.preview_token,
        confirm=True,
    )
    assert publication.immutable is True
    assert application.adapter.linked_replicas.load().to_storage_dict() == before  # type: ignore[union-attr]
    assert lifecycle.store.publication(publication.publication_id, 1) == publication


@pytest.mark.unit
def test_delete_keep_local_requires_matching_verified_detach_receipt(tmp_path: Path) -> None:
    _root, _application, lifecycle, transport, _digest = _scenario(tmp_path)
    preview = lifecycle.preview(
        action=LifecycleAction.delete_remote,
        operation_id="op_delete_without_receipt",
        keep_local=True,
    )
    with pytest.raises(ValueError, match="DETACH_RECEIPT_REQUIRED"):
        lifecycle.apply_remote(
            action=LifecycleAction.delete_remote,
            operation_id=preview.operation_id,
            preview_token=preview.preview_token,
            confirm=True,
            keep_local=True,
        )
    assert transport.remote_deleted is False


@pytest.mark.unit
def test_delete_keep_local_accepts_only_the_matching_verified_detached_project(
    tmp_path: Path,
) -> None:
    root, _application, lifecycle, transport, _digest = _scenario(tmp_path)
    detached_root = tmp_path / "detached-before-delete"
    detach_preview = lifecycle.preview(
        action=LifecycleAction.detach,
        operation_id="op_detach_before_delete_1",
        target=detached_root,
        lineage_mode=DetachLineageMode.private_origin,
    )
    lifecycle.detach(
        operation_id=detach_preview.operation_id,
        preview_token=detach_preview.preview_token,
        target=detached_root,
        local_owner="mrjungle",
        lineage_mode=DetachLineageMode.private_origin,
        confirm=True,
    )
    delete_preview = lifecycle.preview(
        action=LifecycleAction.delete_remote,
        operation_id="op_delete_with_receipt_1",
        keep_local=True,
    )

    receipt = lifecycle.apply_remote(
        action=LifecycleAction.delete_remote,
        operation_id=delete_preview.operation_id,
        preview_token=delete_preview.preview_token,
        confirm=True,
        keep_local=True,
        detached_root=detached_root,
    )

    assert receipt.lifecycle_state == RemoteLifecycleState.retained
    assert transport.remote_deleted is True
    assert ProjectApplicationService(root).adapter.linked_replicas.load().state.value == "tombstoned"  # type: ignore[union-attr]
    assert ProjectApplicationService(detached_root).project_identity().mode == ProjectMode.detached


@pytest.mark.unit
def test_lost_remote_response_recovers_by_same_operation_id(tmp_path: Path) -> None:
    root, _application, lifecycle, transport, _digest = _scenario(tmp_path)
    preview = lifecycle.preview(
        action=LifecycleAction.suspend,
        operation_id="op_suspend_lost_response",
    )
    transport.lose_next_apply_response = True
    receipt = lifecycle.apply_remote(
        action=LifecycleAction.suspend,
        operation_id=preview.operation_id,
        preview_token=preview.preview_token,
        confirm=True,
    )
    assert receipt.operation_id == preview.operation_id
    assert ProjectApplicationService(root).project_identity().mode == ProjectMode.link_suspended


@pytest.mark.unit
def test_archive_and_restore_preserve_identity_and_reactivate_after_catch_up(
    tmp_path: Path,
) -> None:
    root, application, lifecycle, _transport, _digest = _scenario(tmp_path)
    identity = application.project_identity()
    archive_preview = lifecycle.preview(
        action=LifecycleAction.archive,
        operation_id="op_archive_1",
    )
    lifecycle.apply_remote(
        action=LifecycleAction.archive,
        operation_id=archive_preview.operation_id,
        preview_token=archive_preview.preview_token,
        confirm=True,
    )
    archived = ProjectApplicationService(root)
    assert archived.project_identity().project_uuid == identity.project_uuid
    assert archived.adapter.linked_replicas.load().state.value == "archived"  # type: ignore[union-attr]

    restore_service = _service_for(root, lifecycle.transport)
    restore_preview = restore_service.preview(
        action=LifecycleAction.restore,
        operation_id="op_restore_1",
    )
    restore_service.apply_remote(
        action=LifecycleAction.restore,
        operation_id=restore_preview.operation_id,
        preview_token=restore_preview.preview_token,
        confirm=True,
    )
    restored = ProjectApplicationService(root)
    assert restored.project_identity() == identity
    assert restored.adapter.linked_replicas.load().state.value == "active"  # type: ignore[union-attr]


@pytest.mark.unit
def test_unreachable_remote_never_promotes_local_replica_to_authority(tmp_path: Path) -> None:
    root, application, lifecycle, transport, _digest = _scenario(tmp_path)
    before = application.project_identity()
    transport.lifecycle_unavailable = True

    status = lifecycle.status()

    assert status["remote"] is None
    assert "P2P_WAVEKIT_UNAVAILABLE" in str(status["diagnostic"])
    assert status["available_actions"] == [
        "retry-status",
        "configure-emergency-detach-policy",
    ]
    assert ProjectApplicationService(root).project_identity() == before
    assert ProjectApplicationService(root).project_identity().mode == ProjectMode.linked


@pytest.mark.unit
def test_revoked_remote_status_offers_no_local_authority_bypass(tmp_path: Path) -> None:
    root, application, lifecycle, transport, _digest = _scenario(tmp_path)
    before = application.project_identity()
    transport.lifecycle_state = RemoteLifecycleState.access_revoked

    status = lifecycle.status()

    assert status["remote"]["state"] == "access-revoked"  # type: ignore[index]
    assert status["available_actions"] == [
        "request-authorized-export",
        "remove-local-replica",
    ]
    assert ProjectApplicationService(root).project_identity() == before


@pytest.mark.unit
def test_cli_and_mcp_offline_lifecycle_reads_are_deterministic_and_mutation_free(
    tmp_path: Path,
) -> None:
    root, _application, _lifecycle, _transport, _digest = _scenario(tmp_path)

    with assert_no_workspace_mutation(root):
        cli = runner.invoke(
            app,
            [
                "wavekit",
                "lifecycle",
                "status",
                "--offline",
                "--root",
                str(root),
                "--format",
                "json",
            ],
        )
        mcp = call_tool(
            "p2p_project_lifecycle_status",
            {"root": str(root), "offline": True},
        )
        publications = call_tool(
            "p2p_project_publication_list",
            {"root": str(root)},
        )

    assert cli.exit_code == 0
    cli_payload = json.loads(cli.stdout)
    assert cli_payload["operation"] == "wavekit.lifecycle.status"
    assert cli_payload["data"]["project_lifecycle"]["remote"] is None
    assert mcp["project_lifecycle"]["remote"] is None
    assert mcp["mutation_performed"] is False
    assert publications == {
        "project_publications": [],
        "mutation_performed": False,
    }


@pytest.mark.unit
def test_local_replica_archive_preserves_remote_project(tmp_path: Path) -> None:
    root, _application, lifecycle, transport, _digest = _scenario(tmp_path)
    preview = lifecycle.preview(
        action=LifecycleAction.remove_local_replica,
        operation_id="op_remove_local_1",
    )
    archive = tmp_path / "archived-p2p"
    result = lifecycle.remove_local_replica(
        operation_id=preview.operation_id,
        preview_token=preview.preview_token,
        disposition=LocalReplicaDisposition.archive,
        integration=IntegrationDisposition.remove,
        archive_to=archive,
        confirm=True,
    )
    assert result["remote_deleted"] is False
    assert not (root / ".p2p").exists()
    assert (archive / "project.yml").is_file()
    assert transport.replica_deactivated is True
    assert transport.remote_deleted is False


@pytest.mark.unit
def test_local_replica_removal_recovers_after_integration_cleanup_block(
    tmp_path: Path,
) -> None:
    root, _application, lifecycle, transport, _digest = _scenario(tmp_path)
    preview = lifecycle.preview(
        action=LifecycleAction.remove_local_replica,
        operation_id="op_remove_local_recovery_1",
    )

    class BlockedIntegration:
        status = "blocked"

    lifecycle.integration_remove = lambda: BlockedIntegration()
    with pytest.raises(ValueError, match="INTEGRATION_BLOCKED"):
        lifecycle.remove_local_replica(
            operation_id=preview.operation_id,
            preview_token=preview.preview_token,
            disposition=LocalReplicaDisposition.archive,
            integration=IntegrationDisposition.remove,
            archive_to=tmp_path / "archive-after-recovery",
            confirm=True,
        )
    assert (root / ".p2p").is_dir()
    assert lifecycle.store.receipt(preview.operation_id) is not None
    assert transport.deactivation_calls == 1

    lifecycle.integration_remove = lambda: FakeIntegration()
    result = lifecycle.remove_local_replica(
        operation_id=preview.operation_id,
        preview_token=preview.preview_token,
        disposition=LocalReplicaDisposition.archive,
        integration=IntegrationDisposition.remove,
        archive_to=tmp_path / "archive-after-recovery",
        confirm=True,
    )

    assert result["status"] == "removed-locally"
    assert transport.deactivation_calls == 1
    assert not (root / ".p2p").exists()


@pytest.mark.unit
def test_mcp_exposes_only_lifecycle_read_and_preview_surfaces() -> None:
    assert {
        "p2p_project_lifecycle_status",
        "p2p_project_lifecycle_preview",
        "p2p_project_publication_list",
    } <= set(TOOL_NAMES)
    assert not {
        "p2p_project_lifecycle_apply",
        "p2p_project_detach_apply",
        "p2p_project_delete_remote",
        "p2p_remove_local_replica",
    } & set(TOOL_NAMES)


def _service_for(root: Path, transport: object) -> ProjectLifecycleService:
    application = ProjectApplicationService(root)
    assert isinstance(transport, LifecycleTransport)
    return ProjectLifecycleService(
        root=root,
        adapter=application.adapter,
        transport=transport,
        credentials=_credentials(),
        linked_replica=LinkedReplicaService(
            root=root,
            transport=transport,
            credentials=_credentials(),
            integration_transition=lambda: FakeIntegration(),
            store=application.adapter.linked_replicas,
            now=lambda: 1_900_000_000,
        ),
        integration_transition=lambda _profile: FakeIntegration(),
        integration_remove=lambda: FakeIntegration(),
        now=lambda: 1_900_000_000,
    )

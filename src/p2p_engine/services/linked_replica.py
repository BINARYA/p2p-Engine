from __future__ import annotations

import hashlib
import shutil
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import quote, urlencode, urljoin, urlsplit, urlunsplit

from p2p_engine.adapters.wavekit_credentials import (
    KeyringWaveKitCredentialStore,
    WaveKitCredentialStore,
)
from p2p_engine.adapters.wavekit_transfer_http import (
    HTTPSWaveKitTransferTransport,
    WaveKitTransferTransport,
)
from p2p_engine.core.authority_transfer import safe_profile_ref
from p2p_engine.core.linked_replica import (
    LINKED_REPLICA_CAPABILITY_CONTRACT,
    LINKED_REPLICA_CAPABILITY_PATH,
    LINKED_REPLICA_CHANGE_CONTRACT,
    LINKED_REPLICA_MAX_RESPONSE_BYTES,
    LINKED_REPLICA_PROTOCOL,
    LinkedReplicaBinding,
    ReplicaAccessState,
    ReplicaCapabilities,
    ReplicaEndpoints,
    ReplicaFreshness,
    ReplicaOperationResult,
    ReplicaSnapshotManifest,
    snapshot_manifest_from_mapping,
)
from p2p_engine.core.project_identity import RemoteProjectId, ServerInstanceId
from p2p_engine.foundation.files import sync_directory, write_bytes_atomic
from p2p_engine.ports.project_state import LinkedReplicaStatePort
from p2p_engine.services.authority_transfer import normalize_server_url
from p2p_engine.services.canonical_memory import CanonicalBundleCodec, CanonicalMemoryService
from p2p_engine.storage.canonical_memory import FilesystemCanonicalMemoryStore
from p2p_engine.storage.filesystem_linked_replica import FilesystemLinkedReplicaStore


class LinkedReplicaService:
    """Client-side clone and freshness service for one WaveKit-authoritative replica."""

    def __init__(
        self,
        *,
        root: Path,
        transport: WaveKitTransferTransport | None = None,
        credentials: WaveKitCredentialStore | None = None,
        integration_transition: Callable[[], object] | None = None,
        store: LinkedReplicaStatePort | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        # Keep the lexical root until workspace validation so a symlink target
        # cannot disappear through ``resolve()`` before it is rejected.
        self.root = root.expanduser().absolute()
        self.transport = transport or HTTPSWaveKitTransferTransport()
        self.credentials = credentials or KeyringWaveKitCredentialStore()
        self.integration_transition = integration_transition
        self.now = now
        self.store = store or FilesystemLinkedReplicaStore(self.root)
        self.codec = CanonicalBundleCodec()

    def capabilities(self, server_url: str) -> ReplicaCapabilities:
        server = normalize_server_url(server_url)
        response = self.transport.request_json(
            "GET",
            _same_origin_url(server, LINKED_REPLICA_CAPABILITY_PATH),
            max_bytes=LINKED_REPLICA_MAX_RESPONSE_BYTES,
        )
        payload = _envelope(response, "linked_replica_capabilities")
        if (
            payload.get("contract") != LINKED_REPLICA_CAPABILITY_CONTRACT
            or payload.get("protocol") != LINKED_REPLICA_PROTOCOL
        ):
            raise ValueError(
                "P2P_LINKED_REPLICA_PROTOCOL_UNSUPPORTED: capability contract differs"
            )
        endpoints = _mapping(payload.get("endpoints"), "endpoints")
        endpoint_names = {
            "register",
            "replica",
            "snapshot",
            "bundle",
            "blob",
            "changes",
            "deactivate",
            "move",
            "register_copy",
        }
        if set(endpoints) != endpoint_names:
            raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: endpoints are not exact")
        limits = _mapping(payload.get("limits"), "limits")
        if set(limits) != {"max_bundle_bytes", "max_blob_bytes", "max_blobs"}:
            raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: limits are not exact")
        return ReplicaCapabilities(
            server_url=server,
            server_instance_id=ServerInstanceId(_required(payload, "server_instance_id")),
            endpoints=ReplicaEndpoints(
                **{name: _endpoint(endpoints, name) for name in sorted(endpoint_names)}
            ),
            max_bundle_bytes=_positive_int(limits["max_bundle_bytes"], "max_bundle_bytes"),
            max_blob_bytes=_positive_int(limits["max_blob_bytes"], "max_blob_bytes"),
            max_blobs=_positive_int(limits["max_blobs"], "max_blobs"),
            retention_floor=_non_negative_int(
                payload.get("retention_floor", 0), "retention_floor"
            ),
        )

    def clone(
        self,
        *,
        server_url: str,
        remote_project_id: str,
        account_profile_ref: str,
        operation_key: str,
        confirm: bool,
        attach: bool = False,
        device_label: str = "local-device",
    ) -> ReplicaOperationResult:
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: linked clone requires --confirm")
        self._validate_target(attach=attach)
        capabilities = self.capabilities(server_url)
        credential = self._credential(capabilities.server_url)
        profile_ref = safe_profile_ref(
            account_profile_ref,
            field_name="account_profile_ref",
        )
        if (
            credential.account_profile_ref
            and credential.account_profile_ref != profile_ref
        ):
            raise ValueError(
                "P2P_WAVEKIT_ACCOUNT_MISMATCH: requested profile differs from login"
            )
        remote_id = RemoteProjectId(remote_project_id)
        response = self.transport.request_json(
            "POST",
            self._url(
                capabilities,
                capabilities.endpoints.register,
                remote_project_id=remote_id.value,
            ),
            token=credential.access_token,
            json_body={
                "contract": LINKED_REPLICA_PROTOCOL,
                "operation": "attach" if attach else "clone",
                "remote_project_id": remote_id.value,
                "account_profile_ref": profile_ref,
                "device_label": _safe_device_label(device_label),
            },
            idempotency_key=_bounded_operation_key(operation_key),
            max_bytes=LINKED_REPLICA_MAX_RESPONSE_BYTES,
        )
        manifest = snapshot_manifest_from_mapping(
            _envelope(response, "linked_replica_snapshot")
        )
        if (
            manifest.server_instance_id != capabilities.server_instance_id
            or manifest.remote_project_id != remote_id
        ):
            raise ValueError(
                "P2P_LINKED_REPLICA_IDENTITY_MISMATCH: registration response differs"
            )
        if manifest.expires_at <= int(self.now()):
            raise ValueError("P2P_LINKED_REPLICA_SNAPSHOT_EXPIRED: register a fresh clone")
        stage_root = self._stage_root(manifest.session_id)
        try:
            bundle = self._download_snapshot(
                capabilities,
                credential.access_token,
                manifest,
                stage_root,
            )
            materialized = stage_root / "project"
            self._materialize(
                materialized,
                bundle,
                manifest,
                operation_key=operation_key,
                account_profile_ref=profile_ref,
                server_url=capabilities.server_url,
            )
            self._publish_new(materialized)
            active = FilesystemLinkedReplicaStore(self.root).load()
            if active is None:
                raise ValueError("P2P_LINKED_REPLICA_ACTIVATION_FAILED: binding is absent")
            integration = self._transition_integration()
            freshness = _freshness(active, source="remote", stale=False)
            shutil.rmtree(stage_root, ignore_errors=True)
            return ReplicaOperationResult(
                status="attached" if attach else "cloned",
                binding=active,
                freshness=freshness,
                integration_status=integration,
                message=(
                    "WaveKit remains authoritative; a complete linked-local replica is active."
                ),
            )
        except Exception:
            # Staging is intentionally retained for bounded resume/diagnostics.
            raise

    def status(self) -> dict[str, object]:
        binding = self.store.load()
        if binding is None:
            return {
                "contract": "p2p-linked-replica-status/v1",
                "state": "absent",
                "binding": None,
                "freshness": None,
                "mutation_performed": False,
            }
        identity = self.store.verify_active_identity(binding)
        stale = binding.last_verified_at == 0 or binding.state != ReplicaAccessState.active
        return {
            "contract": "p2p-linked-replica-status/v1",
            "state": binding.state.value,
            "binding": binding.to_dict(),
            "freshness": _freshness(
                binding,
                source="local-cache" if stale else "remote",
                stale=stale,
                reason=("No successful online verification is recorded." if stale else ""),
            ).to_dict(),
            "identity_mode": identity.mode.value,
            "mutation_performed": False,
        }

    def catch_up(self) -> ReplicaOperationResult:
        binding = self._binding()
        if binding.state == ReplicaAccessState.access_revoked:
            raise ValueError("P2P_LINKED_REPLICA_ACCESS_REVOKED: server access was revoked")
        capabilities = self.capabilities(binding.server_url)
        self._verify_server(binding, capabilities)
        credential = self._credential(capabilities.server_url)
        url = self._url(
            capabilities,
            capabilities.endpoints.changes,
            replica_id=binding.replica_id.value,
        )
        separator = "&" if "?" in url else "?"
        response = self.transport.request_json(
            "GET",
            f"{url}{separator}{urlencode({'after': binding.cursor})}",
            token=credential.access_token,
            max_bytes=LINKED_REPLICA_MAX_RESPONSE_BYTES,
        )
        payload = _envelope(response, "linked_replica_changes")
        self._validate_change_envelope(payload, binding)
        state = str(payload["status"])
        if state == "up-to-date":
            remote_revision = _positive_int(payload["remote_revision"], "remote_revision")
            cursor = _non_negative_int(payload["to_cursor"], "to_cursor")
            if remote_revision != binding.last_applied_revision or cursor != binding.cursor:
                raise ValueError(
                    "P2P_LINKED_REPLICA_RESPONSE_INVALID: up-to-date progress differs"
                )
            updated = binding.with_progress(
                remote_revision=remote_revision,
                cursor=cursor,
                snapshot_digest=binding.snapshot_digest,
                blob_manifest_digest=binding.blob_manifest_digest,
                verified_at=int(self.now()),
            )
            self.store.save(updated)
            return ReplicaOperationResult(
                status="up-to-date",
                binding=updated,
                freshness=_freshness(updated, source="remote", stale=False),
                message="Linked replica is current at the verified WaveKit revision.",
            )
        if state not in {"snapshot", "retention-gap", "rebuild-required"}:
            raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: unsupported change status")
        raw_snapshot = payload.get("snapshot")
        if not isinstance(raw_snapshot, Mapping):
            raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: snapshot is required")
        manifest = snapshot_manifest_from_mapping(raw_snapshot)
        self._verify_snapshot_binding(manifest, binding, capabilities)
        stage_root = self._stage_root(manifest.session_id)
        bundle = self._download_snapshot(
            capabilities, credential.access_token, manifest, stage_root
        )
        materialized = stage_root / "project"
        self._materialize(
            materialized,
            bundle,
            manifest,
            operation_key=f"replica-catch-up:{binding.replica_id.value}:{manifest.cursor}",
            account_profile_ref=binding.account_profile_ref,
            server_url=capabilities.server_url,
            preserve_read_only=binding.state == ReplicaAccessState.read_only,
        )
        diagnostic = self._replace_active(materialized, previous=binding)
        rebuilt_binding = FilesystemLinkedReplicaStore(self.root).load()
        if rebuilt_binding is None:
            raise ValueError("P2P_LINKED_REPLICA_ACTIVATION_FAILED: rebuilt binding is absent")
        integration = self._transition_integration()
        shutil.rmtree(stage_root, ignore_errors=True)
        return ReplicaOperationResult(
            status="rebuilt" if state != "snapshot" else "caught-up",
            binding=rebuilt_binding,
            freshness=_freshness(rebuilt_binding, source="remote", stale=False),
            integration_status=integration,
            diagnostic_path=diagnostic,
            message="A verified WaveKit snapshot was atomically applied to the local replica.",
        )

    def before_operation(self, *, mutation: bool) -> ReplicaFreshness | None:
        binding = self.store.load()
        if binding is None:
            return None
        try:
            return self.catch_up().freshness
        except ValueError as exc:
            message = str(exc)
            if "ACCESS_REVOKED" in message:
                self.store.mark_access(
                    ReplicaAccessState.access_revoked,
                    error_code="P2P_LINKED_REPLICA_ACCESS_REVOKED",
                )
                raise
            if "AUTH_REQUIRED" in message:
                self.store.mark_access(
                    ReplicaAccessState.suspended,
                    error_code="P2P_WAVEKIT_AUTH_REQUIRED",
                )
            recoverable = any(
                code in message
                for code in (
                    "P2P_WAVEKIT_UNAVAILABLE",
                    "P2P_WAVEKIT_RESPONSE_UNKNOWN",
                    "P2P_WAVEKIT_AUTH_REQUIRED",
                )
            )
            if not recoverable:
                raise
            current = self._binding()
            if mutation:
                raise ValueError(
                    "P2P_REMOTE_AUTHORITY_UNAVAILABLE: linked mutations are never queued offline"
                ) from exc
            return _freshness(
                current,
                source="local-cache",
                stale=True,
                reason="WaveKit could not be verified; data is the last confirmed local state.",
            )

    def register_copy(self, *, operation_key: str, confirm: bool) -> ReplicaOperationResult:
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: replica copy registration requires --confirm")
        binding = self._binding()
        capabilities = self.capabilities(binding.server_url)
        self._verify_server(binding, capabilities)
        credential = self._credential(capabilities.server_url)
        response = self.transport.request_json(
            "POST",
            self._url(
                capabilities,
                capabilities.endpoints.register_copy,
                replica_id=binding.replica_id.value,
            ),
            token=credential.access_token,
            json_body={
                "contract": LINKED_REPLICA_PROTOCOL,
                "project_uuid": binding.project_uuid.value,
                "source_replica_id": binding.replica_id.value,
            },
            idempotency_key=_bounded_operation_key(operation_key),
            max_bytes=LINKED_REPLICA_MAX_RESPONSE_BYTES,
        )
        manifest = snapshot_manifest_from_mapping(
            _envelope(response, "linked_replica_snapshot")
        )
        if manifest.replica_id == binding.replica_id:
            raise ValueError("P2P_PROJECT_REPLICA_COLLISION: copy requires a new replica ID")
        self._verify_snapshot_project(manifest, binding, capabilities)
        stage_root = self._stage_root(manifest.session_id)
        bundle = self._download_snapshot(
            capabilities, credential.access_token, manifest, stage_root
        )
        materialized = stage_root / "project"
        self._materialize(
            materialized,
            bundle,
            manifest,
            operation_key=operation_key,
            account_profile_ref=binding.account_profile_ref,
            server_url=capabilities.server_url,
        )
        diagnostic = self._replace_active(materialized, previous=binding)
        updated = FilesystemLinkedReplicaStore(self.root).load()
        assert updated is not None
        shutil.rmtree(stage_root, ignore_errors=True)
        return ReplicaOperationResult(
            status="copy-registered",
            binding=updated,
            freshness=_freshness(updated, source="remote", stale=False),
            diagnostic_path=diagnostic,
            message="This physical copy now has a distinct registered replica identity.",
        )

    def move(self, *, operation_key: str, confirm: bool) -> ReplicaOperationResult:
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: replica move requires --confirm")
        binding = self._binding()
        capabilities = self.capabilities(binding.server_url)
        self._verify_server(binding, capabilities)
        credential = self._credential(capabilities.server_url)
        response = self.transport.request_json(
            "POST",
            self._url(
                capabilities,
                capabilities.endpoints.move,
                replica_id=binding.replica_id.value,
            ),
            token=credential.access_token,
            json_body={
                "contract": LINKED_REPLICA_PROTOCOL,
                "project_uuid": binding.project_uuid.value,
                "replica_id": binding.replica_id.value,
                "confirm_previous_deactivated": True,
            },
            idempotency_key=_bounded_operation_key(operation_key),
            max_bytes=LINKED_REPLICA_MAX_RESPONSE_BYTES,
        )
        payload = _envelope(response, "linked_replica_move")
        if set(payload) != {
            "contract",
            "status",
            "project_uuid",
            "replica_id",
            "previous_deactivated",
        } or payload.get("contract") != LINKED_REPLICA_PROTOCOL:
            raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: move response differs")
        if (
            payload.get("status") != "moved"
            or payload.get("previous_deactivated") is not True
            or str(payload.get("project_uuid")) != binding.project_uuid.value
            or str(payload.get("replica_id")) != binding.replica_id.value
        ):
            raise ValueError("P2P_LINKED_REPLICA_MOVE_CONFLICT: previous copy is still active")
        caught_up = self.catch_up()
        return ReplicaOperationResult(
            status="moved",
            binding=caught_up.binding,
            freshness=caught_up.freshness,
            integration_status=caught_up.integration_status,
            diagnostic_path=caught_up.diagnostic_path,
            message="Replica identity was preserved after server-confirmed source deactivation.",
        )

    def mark_read_only(self) -> ReplicaOperationResult:
        updated = self.store.mark_access(ReplicaAccessState.read_only)
        return ReplicaOperationResult(
            status="read-only",
            binding=updated,
            freshness=_freshness(
                updated,
                source="local-cache",
                stale=True,
                reason="Owner selected forensic read-only inspection.",
            ),
            message="Replica remains bound but no mutation is permitted.",
        )

    def _materialize(
        self,
        materialized: Path,
        bundle: Path,
        manifest: ReplicaSnapshotManifest,
        *,
        operation_key: str,
        account_profile_ref: str,
        server_url: str,
        preserve_read_only: bool = False,
    ) -> LinkedReplicaBinding:
        if materialized.exists():
            shutil.rmtree(materialized)
        service = CanonicalMemoryService(
            root=materialized,
            p2p_dir=materialized / ".p2p",
            store=FilesystemCanonicalMemoryStore(
                root=materialized, p2p_dir=materialized / ".p2p"
            ),
        )
        result = service.materialize_bundle(
            source=bundle,
            operation_key=_bounded_operation_key(operation_key),
            actor="wavekit-replica",
            expected_project_uuid=manifest.project_uuid.value,
            expected_archive_sha256=manifest.bundle_digest,
            confirm=True,
        )
        if (
            result.semantic_state_digest != manifest.semantic_state_digest
            or result.blob_manifest_digest != manifest.blob_manifest_digest
        ):
            raise ValueError(
                "P2P_LINKED_REPLICA_DIGEST_MISMATCH: materialized state differs from snapshot"
            )
        binding = FilesystemLinkedReplicaStore(materialized).activate_snapshot(
            manifest,
            server_url=server_url,
            account_profile_ref=account_profile_ref,
            verified_at=int(self.now()),
            preserve_replica_id=False,
        )
        if preserve_read_only:
            binding = FilesystemLinkedReplicaStore(materialized).mark_access(
                ReplicaAccessState.read_only
            )
        current = CanonicalBundleCodec().snapshot(
            FilesystemCanonicalMemoryStore(
                root=materialized, p2p_dir=materialized / ".p2p"
            )
        )
        if (
            current.semantic_state_digest != manifest.semantic_state_digest
            or current.blob_manifest_digest != manifest.blob_manifest_digest
        ):
            raise ValueError(
                "P2P_LINKED_REPLICA_DIGEST_MISMATCH: activated staging state differs"
            )
        return binding

    def _download_snapshot(
        self,
        capabilities: ReplicaCapabilities,
        token: str,
        manifest: ReplicaSnapshotManifest,
        stage_root: Path,
    ) -> Path:
        if manifest.expires_at <= int(self.now()):
            raise ValueError("P2P_LINKED_REPLICA_SNAPSHOT_EXPIRED: request a fresh snapshot")
        if manifest.bundle_size > capabilities.max_bundle_bytes:
            raise ValueError("P2P_LINKED_REPLICA_PAYLOAD_TOO_LARGE: bundle exceeds limit")
        if len(manifest.blobs) > capabilities.max_blobs or any(
            item.size > capabilities.max_blob_bytes for item in manifest.blobs
        ):
            raise ValueError("P2P_LINKED_REPLICA_PAYLOAD_TOO_LARGE: blob set exceeds limit")
        stage_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if stage_root.is_symlink():
            raise ValueError("P2P_LINKED_REPLICA_WORKSPACE_UNSAFE: staging path is a symlink")
        bundle_path = stage_root / "snapshot.p2pb"
        bundle = self._resume_or_download(
            bundle_path,
            self._url(
                capabilities,
                capabilities.endpoints.bundle,
                replica_id=manifest.replica_id.value,
                session_id=manifest.session_id,
            ),
            token=token,
            expected_digest=manifest.bundle_digest,
            expected_size=manifest.bundle_size,
            max_bytes=capabilities.max_bundle_bytes,
        )
        decoded = self.codec.decode_bundle(bundle)
        if (
            decoded.snapshot.project_uuid != manifest.project_uuid.value
            or decoded.snapshot.semantic_state_digest != manifest.semantic_state_digest
            or decoded.snapshot.blob_manifest_digest != manifest.blob_manifest_digest
        ):
            raise ValueError("P2P_LINKED_REPLICA_DIGEST_MISMATCH: snapshot manifest differs")
        decoded_blobs = {
            digest.removeprefix("sha256:"): content
            for digest, content in decoded.blob_bytes.items()
        }
        for item in manifest.blobs:
            blob_path = stage_root / "blobs" / item.digest[:2] / item.digest
            content = self._resume_or_download(
                blob_path,
                self._url(
                    capabilities,
                    capabilities.endpoints.blob,
                    replica_id=manifest.replica_id.value,
                    session_id=manifest.session_id,
                    digest=item.digest,
                ),
                token=token,
                expected_digest=item.digest,
                expected_size=item.size,
                max_bytes=capabilities.max_blob_bytes,
            )
            if decoded_blobs.get(item.digest) != content:
                raise ValueError(
                    "P2P_LINKED_REPLICA_DIGEST_MISMATCH: blob endpoint differs from bundle"
                )
        if set(decoded_blobs) != {item.digest for item in manifest.blobs}:
            raise ValueError("P2P_LINKED_REPLICA_DIGEST_MISMATCH: blob coverage differs")
        return bundle_path

    def _resume_or_download(
        self,
        path: Path,
        url: str,
        *,
        token: str,
        expected_digest: str,
        expected_size: int,
        max_bytes: int,
    ) -> bytes:
        if path.is_symlink():
            raise ValueError("P2P_LINKED_REPLICA_WORKSPACE_UNSAFE: staged artifact is a symlink")
        if path.is_file() and not path.is_symlink():
            content = path.read_bytes()
            if (
                len(content) == expected_size
                and hashlib.sha256(content).hexdigest() == expected_digest
            ):
                return content
        content = self.transport.download_bytes(url, token=token, max_bytes=max_bytes)
        if (
            len(content) != expected_size
            or hashlib.sha256(content).hexdigest() != expected_digest
        ):
            raise ValueError("P2P_LINKED_REPLICA_DIGEST_MISMATCH: downloaded bytes differ")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_bytes_atomic(path, content, mode=0o600)
        return content

    def _publish_new(self, materialized: Path) -> None:
        target_p2p = self.root / ".p2p"
        source_p2p = materialized / ".p2p"
        if target_p2p.exists() or target_p2p.is_symlink():
            raise ValueError("P2P_LINKED_REPLICA_TARGET_EXISTS: refusing to overwrite .p2p")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        source_p2p.replace(target_p2p)
        sync_directory(self.root)

    def _replace_active(self, materialized: Path, *, previous: LinkedReplicaBinding) -> str:
        source_p2p = materialized / ".p2p"
        target_p2p = self.root / ".p2p"
        temporary_old = self.root / f".p2p.previous-{previous.cursor}"
        if temporary_old.exists() or temporary_old.is_symlink():
            raise ValueError(
                "P2P_LINKED_REPLICA_RECOVERY_REQUIRED: previous diagnostic target exists"
            )
        target_p2p.replace(temporary_old)
        try:
            source_p2p.replace(target_p2p)
            sync_directory(self.root)
        except Exception:
            if not target_p2p.exists() and temporary_old.exists():
                temporary_old.replace(target_p2p)
            raise
        diagnostic = target_p2p / "local" / "replica-recovery" / f"previous-cursor-{previous.cursor}"
        diagnostic.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            temporary_old.replace(diagnostic)
            relative = diagnostic.relative_to(self.root).as_posix()
        except OSError:
            relative = temporary_old.relative_to(self.root).as_posix()
        return relative

    def _validate_target(self, *, attach: bool) -> None:
        if self.root.is_symlink():
            raise ValueError("P2P_LINKED_REPLICA_WORKSPACE_UNSAFE: target is a symlink")
        if (self.root / ".p2p").exists() or (self.root / ".p2p").is_symlink():
            raise ValueError(
                "P2P_LINKED_REPLICA_TARGET_EXISTS: choose another workspace, move, copy, or read-only"
            )
        parent = self.root.parent
        while parent != parent.parent:
            if (parent / ".p2p").is_dir():
                raise ValueError("P2P_LINKED_REPLICA_WORKSPACE_NESTED: target is inside a project")
            parent = parent.parent
        if attach and not self.root.is_dir():
            raise ValueError("P2P_LINKED_REPLICA_ATTACH_TARGET_MISSING: attach requires a workspace")

    def _stage_root(self, session_id: str) -> Path:
        return self.root.parent / f".p2p-linked-staging-{session_id}"

    def _binding(self) -> LinkedReplicaBinding:
        binding = self.store.load()
        if binding is None:
            raise ValueError("P2P_LINKED_REPLICA_NOT_FOUND: this workspace is not linked")
        return binding

    def _credential(self, server_url: str):
        credential = self.credentials.get(server_url)
        if credential is None:
            raise ValueError("P2P_WAVEKIT_AUTH_REQUIRED: login before using a linked replica")
        if credential.expires_at and credential.expires_at <= int(self.now()) + 15:
            raise ValueError("P2P_WAVEKIT_AUTH_REQUIRED: stored credential expired")
        return credential

    @staticmethod
    def _verify_server(
        binding: LinkedReplicaBinding, capabilities: ReplicaCapabilities
    ) -> None:
        if capabilities.server_instance_id != binding.server_instance_id:
            raise ValueError("P2P_LINKED_REPLICA_SERVER_MISMATCH: server identity changed")

    @staticmethod
    def _verify_snapshot_project(
        manifest: ReplicaSnapshotManifest,
        binding: LinkedReplicaBinding,
        capabilities: ReplicaCapabilities,
    ) -> None:
        if (
            manifest.project_uuid != binding.project_uuid
            or manifest.remote_project_id != binding.remote_project_id
            or manifest.server_instance_id != capabilities.server_instance_id
            or manifest.authority_epoch.value < binding.authority_epoch.value
        ):
            raise ValueError("P2P_LINKED_REPLICA_IDENTITY_MISMATCH: snapshot binding differs")

    @classmethod
    def _verify_snapshot_binding(
        cls,
        manifest: ReplicaSnapshotManifest,
        binding: LinkedReplicaBinding,
        capabilities: ReplicaCapabilities,
    ) -> None:
        cls._verify_snapshot_project(manifest, binding, capabilities)
        if manifest.replica_id != binding.replica_id:
            raise ValueError("P2P_PROJECT_REPLICA_COLLISION: server returned another replica ID")
        if (
            manifest.remote_revision < binding.last_applied_revision
            or manifest.cursor < binding.cursor
        ):
            raise ValueError("P2P_LINKED_REPLICA_CURSOR_REGRESSION: snapshot is older")

    @staticmethod
    def _validate_change_envelope(
        payload: Mapping[str, object], binding: LinkedReplicaBinding
    ) -> None:
        expected = {
            "contract",
            "status",
            "replica_id",
            "authority_epoch",
            "from_cursor",
            "to_cursor",
            "remote_revision",
            "snapshot",
            "reason",
        }
        if set(payload) != expected or payload.get("contract") != LINKED_REPLICA_CHANGE_CONTRACT:
            raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: change fields are not exact")
        if str(payload["replica_id"]) != binding.replica_id.value:
            raise ValueError("P2P_PROJECT_REPLICA_COLLISION: change response replica differs")
        if _positive_int(payload["authority_epoch"], "authority_epoch") != (
            binding.authority_epoch.value
        ):
            raise ValueError("P2P_LINKED_REPLICA_AUTHORITY_CHANGED: authority epoch differs")
        if _non_negative_int(payload["from_cursor"], "from_cursor") != binding.cursor:
            raise ValueError("P2P_LINKED_REPLICA_CURSOR_GAP: server response starts elsewhere")

    def _transition_integration(self) -> str:
        if self.integration_transition is not None:
            result = self.integration_transition()
        else:
            from p2p_engine.services.project_application import open_project_application

            target = open_project_application(self.root).adapter.compatibility_target()
            result = getattr(target, "activate_linked_project_integration")()
        return str(getattr(result, "status", "unknown"))

    def _url(
        self,
        capabilities: ReplicaCapabilities,
        endpoint: str,
        **values: str,
    ) -> str:
        rendered = endpoint
        for key, value in values.items():
            rendered = rendered.replace("{" + key + "}", quote(value, safe=""))
        if "{" in rendered or "}" in rendered:
            raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: endpoint template is incomplete")
        return _same_origin_url(capabilities.server_url, rendered)


def _freshness(
    binding: LinkedReplicaBinding,
    *,
    source: str,
    stale: bool,
    reason: str = "",
) -> ReplicaFreshness:
    return ReplicaFreshness(
        state=binding.state,
        source=source,
        stale=stale,
        last_applied_revision=binding.last_applied_revision,
        cursor=binding.cursor,
        last_verified_at=binding.last_verified_at,
        writes_permitted=binding.writes_permitted and not stale,
        reason=reason,
    )


def _same_origin_url(server_url: str, endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: endpoint must be relative")
    joined = urljoin(server_url.rstrip("/") + "/", endpoint.lstrip("/"))
    base = urlsplit(server_url)
    target = urlsplit(joined)
    if (target.scheme, target.hostname, target.port) != (base.scheme, base.hostname, base.port):
        raise ValueError("P2P_LINKED_REPLICA_RESPONSE_INVALID: endpoint changed origin")
    return urlunsplit((target.scheme, target.netloc, target.path, target.query, ""))


def _endpoint(mapping: Mapping[str, object], name: str) -> str:
    value = str(mapping.get(name) or "")
    parsed = urlsplit(value)
    if not value.startswith("/") or parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError(f"P2P_LINKED_REPLICA_RESPONSE_INVALID: {name} endpoint is unsafe")
    return value


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"P2P_LINKED_REPLICA_RESPONSE_INVALID: {label} must be a mapping")
    return value


def _envelope(value: object, key: str) -> Mapping[str, object]:
    mapping = _mapping(value, "response")
    if set(mapping) != {key}:
        raise ValueError(f"P2P_LINKED_REPLICA_RESPONSE_INVALID: expected {key} envelope")
    return _mapping(mapping[key], key)


def _required(mapping: Mapping[str, object], field: str) -> str:
    value = str(mapping.get(field) or "")
    if not value:
        raise ValueError(f"P2P_LINKED_REPLICA_RESPONSE_INVALID: {field} is required")
    return value


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"P2P_LINKED_REPLICA_RESPONSE_INVALID: {field} must be positive")
    return value


def _non_negative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"P2P_LINKED_REPLICA_RESPONSE_INVALID: {field} must be non-negative")
    return value


def _bounded_operation_key(value: str) -> str:
    text = str(value or "")
    if not text.strip() or len(text.encode("utf-8")) > 512 or "\x00" in text:
        raise ValueError("P2P_IDEMPOTENCY_KEY_REQUIRED: bounded operation key is required")
    return text


def _safe_device_label(value: str) -> str:
    text = str(value or "").strip()
    if not text or len(text.encode("utf-8")) > 128 or any(ord(char) < 32 for char in text):
        raise ValueError("P2P_LINKED_REPLICA_INVALID: device label is invalid")
    return text

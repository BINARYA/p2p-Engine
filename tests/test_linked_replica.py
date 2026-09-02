from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.adapters.wavekit_credentials import MemoryWaveKitCredentialStore
from p2p_engine.cli import app
from p2p_engine.core.authority_transfer import WaveKitCredential
from p2p_engine.core.linked_replica import (
    LINKED_REPLICA_CAPABILITY_CONTRACT,
    LINKED_REPLICA_CHANGE_CONTRACT,
    LINKED_REPLICA_PROTOCOL,
    LINKED_REPLICA_SNAPSHOT_CONTRACT,
    ReplicaAccessState,
)
from p2p_engine.core.project_identity import ProjectMode
from p2p_engine.mcp.registry import TOOL_NAMES
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.services.linked_replica import LinkedReplicaService
from p2p_engine.services.project_application import ProjectApplicationService

SERVER = "https://wavekit.example.test"
SERVER_ID = "wavekit-production-1"
REMOTE_ID = "wk_project_42"
PROFILE = "wavekit:user:owner-42"
REPLICA_ONE = "50f0a643-50aa-4a08-99ce-a0946f9951c1"
REPLICA_TWO = "736f2c07-5ac7-4d65-aa24-d04a4b17e925"
runner = CliRunner()


class FakeIntegration:
    status = "applied"


class FakeReplicaTransport:
    def __init__(self, bundle: bytes, snapshot: object, *, offline: bool = False) -> None:
        self.bundle = bundle
        self.snapshot = snapshot
        self.offline = offline
        self.replica_id = REPLICA_ONE
        self.change_status = "up-to-date"
        self.remote_revision = 1
        self.cursor = 1
        self.change_error = ""
        self.expires_at = 2_000_000_000
        self.requests: list[tuple[str, str]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        token: str = "",
        json_body: Mapping[str, object] | None = None,
        form: Mapping[str, str] | None = None,
        idempotency_key: str = "",
        max_bytes: int = 1_048_576,
    ) -> object:
        self.requests.append((method, url))
        if self.offline:
            raise ValueError("P2P_WAVEKIT_UNAVAILABLE: test server is offline")
        if url.endswith("/.well-known/p2p-linked-replica"):
            return _capabilities()
        assert token == "secret-access"
        if method == "POST" and url.endswith(f"/projects/{REMOTE_ID}/replicas"):
            assert json_body is not None
            assert "root" not in json.dumps(json_body)
            assert "backend" not in json.dumps(json_body)
            return {"linked_replica_snapshot": self._manifest(self.replica_id)}
        if method == "GET" and "/changes?after=" in url:
            if self.change_error:
                raise ValueError(self.change_error)
            binding_cursor = int(url.rsplit("=", 1)[-1])
            return {
                "linked_replica_changes": {
                    "contract": LINKED_REPLICA_CHANGE_CONTRACT,
                    "status": self.change_status,
                    "replica_id": self.replica_id,
                    "authority_epoch": 2,
                    "from_cursor": binding_cursor,
                    "to_cursor": (
                        binding_cursor
                        if self.change_status == "up-to-date"
                        else self.cursor
                    ),
                    "remote_revision": self.remote_revision,
                    "snapshot": (
                        None
                        if self.change_status == "up-to-date"
                        else self._manifest(
                            self.replica_id,
                            session="3",
                            remote_revision=self.remote_revision,
                            cursor=self.cursor,
                        )
                    ),
                    "reason": (
                        ""
                        if self.change_status == "up-to-date"
                        else "cursor is outside retained changes"
                    ),
                }
            }
        if method == "POST" and url.endswith("/register-copy"):
            self.replica_id = REPLICA_TWO
            return {"linked_replica_snapshot": self._manifest(self.replica_id, session="2")}
        if method == "POST" and url.endswith("/move"):
            return {
                "linked_replica_move": {
                    "contract": LINKED_REPLICA_PROTOCOL,
                    "status": "moved",
                    "project_uuid": self.snapshot.project_uuid,
                    "replica_id": self.replica_id,
                    "previous_deactivated": True,
                }
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    def download_bytes(self, url: str, *, token: str, max_bytes: int) -> bytes:
        if self.offline:
            raise ValueError("P2P_WAVEKIT_UNAVAILABLE: test server is offline")
        assert token == "secret-access"
        if url.endswith("/bundle"):
            return self.bundle
        digest = url.rsplit("/", 1)[-1]
        decoded = CanonicalBundleCodec().decode_bundle(self.bundle)
        return decoded.blob_bytes[f"sha256:{digest}"]

    def upload_bytes(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("clone never uploads project state")

    def _manifest(
        self,
        replica_id: str,
        *,
        session: str = "1",
        remote_revision: int | None = None,
        cursor: int | None = None,
    ) -> dict[str, object]:
        blobs = [item.to_dict() for item in self.snapshot.blobs]
        return {
            "contract": LINKED_REPLICA_SNAPSHOT_CONTRACT,
            "status": "ready",
            "session_id": f"rs_{session * 32}",
            "server_instance_id": SERVER_ID,
            "remote_project_id": REMOTE_ID,
            "project_uuid": self.snapshot.project_uuid,
            "replica_id": replica_id,
            "authority_epoch": 2,
            "remote_revision": remote_revision or self.remote_revision,
            "cursor": self.cursor if cursor is None else cursor,
            "semantic_state_digest": f"sha256:{self.snapshot.semantic_state_digest}",
            "bundle_digest": f"sha256:{hashlib.sha256(self.bundle).hexdigest()}",
            "blob_manifest_digest": f"sha256:{self.snapshot.blob_manifest_digest}",
            "bundle_size": len(self.bundle),
            "blobs": blobs,
            "expires_at": self.expires_at,
        }


def _capabilities() -> dict[str, object]:
    return {
        "linked_replica_capabilities": {
            "contract": LINKED_REPLICA_CAPABILITY_CONTRACT,
            "protocol": LINKED_REPLICA_PROTOCOL,
            "server_instance_id": SERVER_ID,
            "endpoints": {
                "register": "/api/projects/{remote_project_id}/replicas",
                "replica": "/api/project-replicas/{replica_id}",
                "snapshot": "/api/project-replicas/{replica_id}/snapshot",
                "bundle": "/api/project-replicas/{replica_id}/sessions/{session_id}/bundle",
                "blob": "/api/project-replicas/{replica_id}/sessions/{session_id}/blobs/{digest}",
                "changes": "/api/project-replicas/{replica_id}/changes",
                "deactivate": "/api/project-replicas/{replica_id}/deactivate",
                "move": "/api/project-replicas/{replica_id}/move",
                "register_copy": "/api/project-replicas/{replica_id}/register-copy",
            },
            "limits": {
                "max_bundle_bytes": 32_000_000,
                "max_blob_bytes": 8_000_000,
                "max_blobs": 1_000,
            },
            "retention_floor": 0,
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


def _source_bundle(tmp_path: Path):
    source = tmp_path / "source"
    application = ProjectApplicationService(source)
    application.init_project("Remote project", starter_id="empty")
    content = b"linked replica managed blob\n"
    digest = hashlib.sha256(content).hexdigest()
    blob = source / ".p2p" / "blobs" / "sha256" / digest[:2] / digest
    blob.parent.mkdir(parents=True)
    blob.write_bytes(content)
    evidence = source / ".p2p" / "governance" / "replica-evidence.yml"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        yaml.safe_dump(
            {
                "evidence": {"kind": "managed_blob", "digest": f"sha256:{digest}"},
                "canonical_relations": [
                    {
                        "id": "replica-evidence-project",
                        "type": "supports",
                        "target": "project:manifest",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    snapshot = application.canonical_memory_snapshot()
    bundle_path = tmp_path / "source.p2pbundle"
    application.canonical_bundle_export(bundle_path)
    return snapshot, bundle_path.read_bytes(), digest


def _clone(tmp_path: Path):
    snapshot, bundle, digest = _source_bundle(tmp_path)
    target = tmp_path / "workspace"
    target.mkdir()
    (target / "user-owned.txt").write_text("preserve\n", encoding="utf-8")
    transport = FakeReplicaTransport(bundle, snapshot)
    service = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_000,
    )
    result = service.clone(
        server_url=SERVER,
        remote_project_id=REMOTE_ID,
        account_profile_ref=PROFILE,
        operation_key="owner:clone:one",
        confirm=True,
        attach=True,
    )
    return target, snapshot, bundle, digest, transport, result


def test_clone_materializes_complete_verified_replica_and_preserves_workspace(
    tmp_path: Path,
) -> None:
    target, source_snapshot, _bundle, digest, _transport, result = _clone(tmp_path)
    application = ProjectApplicationService(target)
    cloned = application.canonical_memory_snapshot()
    identity = application.project_identity()
    status = application.linked_replica_status()

    assert result.status == "attached"
    assert cloned.semantic_state_digest == source_snapshot.semantic_state_digest
    assert cloned.blob_manifest_digest == source_snapshot.blob_manifest_digest
    assert application.adapter.blobs.read(f"sha256:{digest}") == b"linked replica managed blob\n"
    assert identity.mode == ProjectMode.linked
    assert identity.replica_id is not None and identity.replica_id.value == REPLICA_ONE
    assert identity.remote_binding is not None
    assert (target / "user-owned.txt").read_text(encoding="utf-8") == "preserve\n"
    assert status["state"] == "active"
    assert status["binding"]["account_profile_ref"] == PROFILE
    assert "secret-access" not in json.dumps(status)


def test_clone_failure_never_publishes_partial_p2p(tmp_path: Path) -> None:
    snapshot, bundle, _digest = _source_bundle(tmp_path)
    target = tmp_path / "failed"
    target.mkdir()
    transport = FakeReplicaTransport(bundle[:-10] + b"corruption", snapshot)
    service = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_000,
    )

    with pytest.raises(ValueError, match="P2P_BUNDLE_ARCHIVE_INVALID|DIGEST_MISMATCH"):
        service.clone(
            server_url=SERVER,
            remote_project_id=REMOTE_ID,
            account_profile_ref=PROFILE,
            operation_key="owner:clone:failed",
            confirm=True,
            attach=True,
        )

    assert not (target / ".p2p").exists()
    assert list(tmp_path.glob(".p2p-linked-staging-rs_*"))


def test_catch_up_marks_online_freshness_and_offline_reads_stale(tmp_path: Path) -> None:
    target, snapshot, bundle, _digest, transport, _result = _clone(tmp_path)
    online = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_100,
    )
    caught_up = online.catch_up()

    assert caught_up.status == "up-to-date"
    assert caught_up.freshness.stale is False
    assert caught_up.freshness.writes_permitted is True

    offline = LinkedReplicaService(
        root=target,
        transport=FakeReplicaTransport(bundle, snapshot, offline=True),
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_200,
    )
    stale = offline.before_operation(mutation=False)
    assert stale is not None and stale.stale is True
    assert stale.source == "local-cache"
    assert stale.writes_permitted is False
    with pytest.raises(ValueError, match="P2P_REMOTE_AUTHORITY_UNAVAILABLE"):
        offline.before_operation(mutation=True)


def test_physical_copy_requires_new_replica_or_explicit_read_only(tmp_path: Path) -> None:
    target, snapshot, bundle, _digest, transport, _result = _clone(tmp_path)
    service = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_100,
    )
    copied = service.register_copy(operation_key="owner:copy:one", confirm=True)

    assert copied.binding.replica_id.value == REPLICA_TWO
    assert copied.binding.project_uuid.value == snapshot.project_uuid
    diagnostic = target / copied.diagnostic_path
    assert diagnostic.is_dir()

    read_only = service.mark_read_only()
    assert read_only.binding.state == ReplicaAccessState.read_only
    assert read_only.freshness.writes_permitted is False

    caught_up = service.catch_up()
    assert caught_up.binding.state == ReplicaAccessState.read_only
    assert caught_up.freshness.writes_permitted is False


def test_retention_gap_rebuilds_atomically_and_preserves_forensic_state(
    tmp_path: Path,
) -> None:
    target, _snapshot, _bundle, _digest, transport, _result = _clone(tmp_path)
    marker = target / ".p2p" / "local" / "forensic-marker.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("old confirmed state\n", encoding="utf-8")
    transport.change_status = "retention-gap"
    transport.remote_revision = 2
    transport.cursor = 2
    service = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_100,
    )

    rebuilt = service.catch_up()

    assert rebuilt.status == "rebuilt"
    assert rebuilt.binding.replica_id.value == REPLICA_ONE
    assert rebuilt.binding.last_applied_revision == 2
    assert rebuilt.binding.cursor == 2
    diagnostic = target / rebuilt.diagnostic_path
    assert (diagnostic / "local" / "forensic-marker.txt").read_text(
        encoding="utf-8"
    ) == "old confirmed state\n"
    assert not list(tmp_path.glob(".p2p.previous-*"))


def test_revocation_and_expired_login_change_access_state_without_detaching(
    tmp_path: Path,
) -> None:
    target, snapshot, bundle, _digest, transport, _result = _clone(tmp_path)
    transport.change_error = (
        "P2P_LINKED_REPLICA_ACCESS_REVOKED: membership no longer grants project access"
    )
    revoked = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
    )
    with pytest.raises(ValueError, match="P2P_LINKED_REPLICA_ACCESS_REVOKED"):
        revoked.before_operation(mutation=False)
    revoked_status = revoked.status()
    assert revoked_status["state"] == "access-revoked"
    assert revoked_status["identity_mode"] == "linked"

    # Use a second replica because access revocation intentionally fails closed.
    second, *_rest = _clone(tmp_path / "second-case")
    expired_credentials = MemoryWaveKitCredentialStore()
    expired_credentials.set(
        SERVER,
        WaveKitCredential(
            access_token="secret-access",
            account_profile_ref=PROFILE,
            expires_at=1_800_000_000,
        ),
    )
    suspended = LinkedReplicaService(
        root=second,
        transport=FakeReplicaTransport(bundle, snapshot),
        credentials=expired_credentials,
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_000,
    )
    freshness = suspended.before_operation(mutation=False)
    assert freshness is not None and freshness.stale is True
    suspended_status = suspended.status()
    assert suspended_status["state"] == "suspended"
    assert suspended_status["identity_mode"] == "link-suspended"


def test_clone_rejects_symlink_existing_or_nested_workspace_before_download(
    tmp_path: Path,
) -> None:
    snapshot, bundle, _digest = _source_bundle(tmp_path)
    real = tmp_path / "real"
    real.mkdir()
    symlink = tmp_path / "linked-target"
    symlink.symlink_to(real, target_is_directory=True)
    transport = FakeReplicaTransport(bundle, snapshot)
    service = LinkedReplicaService(
        root=symlink,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
    )
    with pytest.raises(ValueError, match="WORKSPACE_UNSAFE"):
        service.clone(
            server_url=SERVER,
            remote_project_id=REMOTE_ID,
            account_profile_ref=PROFILE,
            operation_key="owner:clone:symlink",
            confirm=True,
        )
    assert transport.requests == []

    existing = tmp_path / "existing"
    (existing / ".p2p").mkdir(parents=True)
    with pytest.raises(ValueError, match="TARGET_EXISTS"):
        LinkedReplicaService(root=existing).clone(
            server_url=SERVER,
            remote_project_id=REMOTE_ID,
            account_profile_ref=PROFILE,
            operation_key="owner:clone:existing",
            confirm=True,
        )

    parent = tmp_path / "parent-project"
    (parent / ".p2p").mkdir(parents=True)
    nested = parent / "nested"
    with pytest.raises(ValueError, match="WORKSPACE_NESTED"):
        LinkedReplicaService(root=nested).clone(
            server_url=SERVER,
            remote_project_id=REMOTE_ID,
            account_profile_ref=PROFILE,
            operation_key="owner:clone:nested",
            confirm=True,
        )


def test_clone_generates_backend_neutral_linked_local_agent_guidance(
    tmp_path: Path,
) -> None:
    snapshot, bundle, _digest = _source_bundle(tmp_path)
    target = tmp_path / "integrated"
    service = LinkedReplicaService(
        root=target,
        transport=FakeReplicaTransport(bundle, snapshot),
        credentials=_credentials(),
        now=lambda: 1_900_000_000,
    )

    cloned = service.clone(
        server_url=SERVER,
        remote_project_id=REMOTE_ID,
        account_profile_ref=PROFILE,
        operation_key="owner:clone:integrated",
        confirm=True,
    )

    guide = (target / "P2P-INTEGRATION.md").read_text(encoding="utf-8")
    assert cloned.integration_status == "applied"
    assert "Profile: `linked-local`" in guide
    assert "p2p wavekit sync catch-up" in guide
    assert "filesystem" not in guide.lower()
    assert "sqlite" not in guide.lower()
    assert "secret-access" not in guide


def test_expired_snapshot_is_never_materialized(tmp_path: Path) -> None:
    snapshot, bundle, _digest = _source_bundle(tmp_path)
    transport = FakeReplicaTransport(bundle, snapshot)
    transport.expires_at = 1_800_000_000
    target = tmp_path / "expired"
    service = LinkedReplicaService(
        root=target,
        transport=transport,
        credentials=_credentials(),
        integration_transition=lambda: FakeIntegration(),
        now=lambda: 1_900_000_000,
    )

    with pytest.raises(ValueError, match="SNAPSHOT_EXPIRED"):
        service.clone(
            server_url=SERVER,
            remote_project_id=REMOTE_ID,
            account_profile_ref=PROFILE,
            operation_key="owner:clone:expired",
            confirm=True,
        )
    assert not (target / ".p2p").exists()


def test_clone_rejects_an_account_reference_that_differs_from_secure_login(
    tmp_path: Path,
) -> None:
    snapshot, bundle, _digest = _source_bundle(tmp_path)
    target = tmp_path / "wrong-account"
    service = LinkedReplicaService(
        root=target,
        transport=FakeReplicaTransport(bundle, snapshot),
        credentials=_credentials(),
    )

    with pytest.raises(ValueError, match="P2P_WAVEKIT_ACCOUNT_MISMATCH"):
        service.clone(
            server_url=SERVER,
            remote_project_id=REMOTE_ID,
            account_profile_ref="wavekit:user:someone-else",
            operation_key="owner:clone:wrong-account",
            confirm=True,
        )
    assert not (target / ".p2p").exists()


def test_cli_and_mcp_inventory_expose_replica_lifecycle_but_not_clone_mcp(
    tmp_path: Path,
) -> None:
    target, *_rest = _clone(tmp_path)
    result = runner.invoke(
        app,
        ["wavekit", "status", "--root", str(target), "--format", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["operation"] == "wavekit.status"
    assert payload["data"]["linked_replica_status"]["state"] == "active"
    assert "p2p_linked_replica_status" in TOOL_NAMES
    assert "p2p_linked_replica_catch_up" in TOOL_NAMES
    assert all("clone" not in name and "attach" not in name for name in TOOL_NAMES)

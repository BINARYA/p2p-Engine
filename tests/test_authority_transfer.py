from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from p2p_engine.adapters.wavekit_credentials import MemoryWaveKitCredentialStore
from p2p_engine.cli import app
from p2p_engine.core.authority_transfer import (
    AUTHORITY_TRANSFER_CAPABILITY_CONTRACT,
    AUTHORITY_TRANSFER_PROTOCOL,
    AUTHORITY_TRANSFER_RECEIPT_CONTRACT,
    DeviceAuthorization,
    TransferState,
    WaveKitCredential,
)
from p2p_engine.core.project_identity import ProjectMode
from p2p_engine.mcp.registry import TOOL_NAMES
from p2p_engine.services.authority_transfer import AuthorityTransferService, normalize_server_url
from p2p_engine.services.project_application import ProjectApplicationService

SERVER = "https://wavekit.example.test"
SERVER_INSTANCE_ID = "wavekit-dev-1"
OWNER_PROFILE = "profile:owner-1"
runner = CliRunner()


class FakeIntegrationResult:
    status = "applied"


class FakeWaveKitTransport:
    def __init__(self, *, commit_timeout: bool = False, terminal_state: str = "") -> None:
        self.commit_timeout = commit_timeout
        self.terminal_state = terminal_state
        self.session_request: dict[str, object] = {}
        self.uploads: list[tuple[str, bytes, str]] = []
        self.receipt: dict[str, object] | None = None

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
        assert "secret-access" not in url
        if url.endswith("/.well-known/p2p-authority-transfer"):
            return _capabilities()
        if url.endswith("/eligibility"):
            assert token == "secret-access"
            return {
                "authority_transfer_eligibility": {
                    "eligible": True,
                    "blockers": [],
                    "owner_profile_ref": OWNER_PROFILE,
                }
            }
        if url.endswith("/oauth/device"):
            return {
                "device_code": "private-device-code",
                "user_code": "ABCD-EFGH",
                "verification_uri": f"{SERVER}/activate",
                "expires_in": 600,
                "interval": 1,
            }
        if url.endswith("/oauth/token"):
            return {
                "access_token": "new-secret-access",
                "refresh_token": "new-secret-refresh",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "project:transfer",
                "account_profile_ref": OWNER_PROFILE,
            }
        if method == "POST" and url.endswith("/authority-transfers"):
            assert json_body is not None
            self.session_request = dict(json_body)
            return {
                "authority_transfer_session": {
                    "transfer_id": json_body["transfer_id"],
                    "state": "preflighted",
                }
            }
        if url.endswith("/manifest"):
            return {"authority_transfer_manifest": {"missing_blobs": []}}
        if url.endswith("/commit"):
            assert self.session_request
            self.receipt = _receipt(self.session_request)
            if self.commit_timeout:
                raise ValueError("P2P_WAVEKIT_RESPONSE_UNKNOWN: query the same transfer session")
            return {
                "authority_transfer_session": {
                    "transfer_id": self.session_request["transfer_id"],
                    "state": "committed",
                    "receipt": self.receipt,
                }
            }
        if method == "GET" and "/authority-transfers/tr_" in url:
            transfer_id = url.rsplit("/", 1)[-1]
            if self.terminal_state:
                return {
                    "authority_transfer_session": {
                        "transfer_id": transfer_id,
                        "state": self.terminal_state,
                        "error_code": "P2P_WAVEKIT_AUTHORIZATION_REVOKED",
                    }
                }
            assert self.receipt is not None
            return {
                "authority_transfer_session": {
                    "transfer_id": transfer_id,
                    "state": "committed",
                    "receipt": self.receipt,
                }
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    def upload_bytes(
        self,
        url: str,
        content: bytes,
        *,
        token: str,
        digest: str,
        idempotency_key: str,
        max_bytes: int,
        max_response_bytes: int = 1_048_576,
    ) -> object:
        assert token == "secret-access"
        assert len(content) <= max_bytes
        self.uploads.append((url, content, digest))
        return {"status": "accepted"}


def _capabilities() -> dict[str, object]:
    return {
        "authority_transfer_capabilities": {
            "contract": AUTHORITY_TRANSFER_CAPABILITY_CONTRACT,
            "protocol": AUTHORITY_TRANSFER_PROTOCOL,
            "server_instance_id": SERVER_INSTANCE_ID,
            "endpoints": {
                "eligibility": "/api/authority-transfers/eligibility",
                "sessions": "/api/authority-transfers",
                "session": "/api/authority-transfers/{transfer_id}",
                "manifest": "/api/authority-transfers/{transfer_id}/manifest",
                "bundle": "/api/authority-transfers/{transfer_id}/bundle",
                "blob": "/api/authority-transfers/{transfer_id}/blobs/{digest}",
                "commit": "/api/authority-transfers/{transfer_id}/commit",
                "cancel": "/api/authority-transfers/{transfer_id}/cancel",
            },
            "oauth_device": {
                "device_authorization_endpoint": "/oauth/device",
                "token_endpoint": "/oauth/token",
                "client_id": "p2p-engine",
                "scopes": ["project:transfer"],
            },
            "limits": {
                "max_bundle_bytes": 100_000_000,
                "max_blob_bytes": 10_000_000,
                "max_blobs": 10_000,
            },
        }
    }


def _receipt(request: Mapping[str, object]) -> dict[str, object]:
    return {
        "contract": AUTHORITY_TRANSFER_RECEIPT_CONTRACT,
        "status": "committed",
        "transfer_id": request["transfer_id"],
        "request_fingerprint": request["request_fingerprint"],
        "project_uuid": request["project_uuid"],
        "server_instance_id": SERVER_INSTANCE_ID,
        "remote_project_id": "wk_project_1",
        "authority_epoch": 2,
        "remote_revision": 1,
        "replica_id": str(uuid4()),
        "bundle_digest": request["bundle_digest"],
        "blob_manifest_digest": request["blob_manifest_digest"],
        "required_blobs": request["required_blobs"],
        "account_profile_ref": OWNER_PROFILE,
        "cursor": 0,
    }


def _service(
    tmp_path: Path,
    transport: FakeWaveKitTransport,
    *,
    actual_integration: bool = False,
) -> tuple[ProjectApplicationService, AuthorityTransferService]:
    project = tmp_path / "project"
    application = ProjectApplicationService(project)
    application.init_project("Transfer project")
    credentials = MemoryWaveKitCredentialStore()
    credentials.set(
        SERVER,
        WaveKitCredential(
            access_token="secret-access",
            refresh_token="secret-refresh",
            scopes=("project:transfer",),
            account_profile_ref=OWNER_PROFILE,
        ),
    )

    def transition() -> object:
        if actual_integration:
            return application.adapter.compatibility_target().activate_linked_project_integration()
        return FakeIntegrationResult()

    return application, AuthorityTransferService(
        adapter=application.adapter,
        integration_transition=transition,
        transport=transport,
        credentials=credentials,
        now=lambda: 1_000,
        sleep=lambda _seconds: None,
    )


def _preview(service: AuthorityTransferService):
    return service.preview(
        server_url=SERVER,
        owner_profile_ref=OWNER_PROFILE,
        operation_key="transfer-once",
    )


def test_transfer_preserves_identity_and_activates_linked_profile(tmp_path: Path) -> None:
    transport = FakeWaveKitTransport()
    application, service = _service(tmp_path, transport, actual_integration=True)
    before = application.project_identity()
    preview = _preview(service)

    result = service.apply(
        server_url=SERVER,
        owner_profile_ref=OWNER_PROFILE,
        operation_key="transfer-once",
        preview_token=preview.preview_token,
        confirm=True,
    )

    after = application.adapter.repository.identity()
    assert result.status == "linked"
    assert result.receipt is not None
    assert after.project_uuid == before.project_uuid
    assert after.mode == ProjectMode.linked
    assert after.remote_binding is not None
    assert after.remote_binding.remote_project_id.value == "wk_project_1"
    assert result.receipt.authority_epoch.value == 2
    assert transport.uploads and transport.uploads[0][0].endswith("/bundle")
    status = application.adapter.compatibility_target().project_integration_status()
    assert status["active_profile"] == "linked-local"
    assert status["profile"]["offline_mutations"] == "blocked"


def test_preview_is_stable_sanitized_and_does_not_fence_writes(tmp_path: Path) -> None:
    application, service = _service(tmp_path, FakeWaveKitTransport())
    first = _preview(service)
    second = _preview(service)
    serialized = json.dumps(first.to_dict(), sort_keys=True)

    assert first == second
    assert first.eligible is True
    assert "secret-access" not in serialized
    assert "secret-refresh" not in serialized
    assert str(tmp_path) not in serialized
    assert application.adapter.authority_transfers.load() is None
    assert application.project_identity().mode == ProjectMode.standalone


def test_confirmation_and_stale_preview_fail_before_local_fence(tmp_path: Path) -> None:
    application, service = _service(tmp_path, FakeWaveKitTransport())
    preview = _preview(service)

    with pytest.raises(ValueError, match="P2P_CONFIRMATION_REQUIRED"):
        service.apply(
            server_url=SERVER,
            owner_profile_ref=OWNER_PROFILE,
            operation_key="transfer-once",
            preview_token=preview.preview_token,
            confirm=False,
        )
    with pytest.raises(ValueError, match="P2P_PREVIEW_STALE"):
        service.apply(
            server_url=SERVER,
            owner_profile_ref=OWNER_PROFILE,
            operation_key="transfer-once",
            preview_token="0" * 64,
            confirm=True,
        )
    assert application.adapter.authority_transfers.load() is None


def test_lost_commit_response_keeps_fence_and_recovery_completes_cutover(
    tmp_path: Path,
) -> None:
    transport = FakeWaveKitTransport(commit_timeout=True)
    application, service = _service(tmp_path, transport)
    preview = _preview(service)

    with pytest.raises(ValueError, match="P2P_WAVEKIT_RESPONSE_UNKNOWN"):
        service.apply(
            server_url=SERVER,
            owner_profile_ref=OWNER_PROFILE,
            operation_key="transfer-once",
            preview_token=preview.preview_token,
            confirm=True,
        )
    session = application.adapter.authority_transfers.load()
    assert session is not None and session.state == TransferState.remote_staging
    assert application.adapter.authority_transfers.writes_fenced() is True
    transport.commit_timeout = False

    recovered = service.recover()

    assert recovered.status == "linked"
    assert application.adapter.repository.identity().mode == ProjectMode.linked
    assert application.adapter.authority_transfers.writes_fenced() is False


def test_async_commit_returns_pending_and_recovery_finishes_link(
    tmp_path: Path,
) -> None:
    class AsyncCommitTransport(FakeWaveKitTransport):
        def request_json(self, method: str, url: str, **kwargs: object) -> object:
            response = super().request_json(method, url, **kwargs)
            if url.endswith("/commit"):
                return {
                    "authority_transfer_session": {
                        "transfer_id": self.session_request["transfer_id"],
                        "state": "committing",
                        "receipt": None,
                    }
                }
            return response

    transport = AsyncCommitTransport()
    application, service = _service(tmp_path, transport)
    preview = _preview(service)

    pending = service.apply(
        server_url=SERVER,
        owner_profile_ref=OWNER_PROFILE,
        operation_key="transfer-once",
        preview_token=preview.preview_token,
        confirm=True,
    )

    assert pending.status == "pending"
    assert pending.receipt is None
    assert pending.session.state == TransferState.remote_staging
    assert application.adapter.authority_transfers.writes_fenced() is True

    recovered = service.recover()

    assert recovered.status == "linked"
    assert application.adapter.repository.identity().mode == ProjectMode.linked


def test_rejected_remote_session_releases_fence_without_binding(tmp_path: Path) -> None:
    transport = FakeWaveKitTransport(commit_timeout=True)
    application, service = _service(tmp_path, transport)
    preview = _preview(service)
    with pytest.raises(ValueError, match="P2P_WAVEKIT_RESPONSE_UNKNOWN"):
        service.apply(
            server_url=SERVER,
            owner_profile_ref=OWNER_PROFILE,
            operation_key="transfer-once",
            preview_token=preview.preview_token,
            confirm=True,
        )
    transport.terminal_state = "rejected"

    recovered = service.recover()

    assert recovered.status == "standalone_restored"
    assert recovered.session.state == TransferState.rejected
    assert application.adapter.repository.identity().mode == ProjectMode.standalone
    assert application.adapter.authority_transfers.writes_fenced() is False


def test_receipt_mismatch_fails_closed_after_remote_commit(tmp_path: Path) -> None:
    class MismatchedReceiptTransport(FakeWaveKitTransport):
        def request_json(self, method: str, url: str, **kwargs: object) -> object:
            response = super().request_json(method, url, **kwargs)
            if url.endswith("/commit") and isinstance(response, dict):
                receipt = response["authority_transfer_session"]["receipt"]
                receipt["project_uuid"] = str(uuid4())
            return response

    application, service = _service(tmp_path, MismatchedReceiptTransport())
    preview = _preview(service)
    with pytest.raises(ValueError, match="P2P_AUTHORITY_TRANSFER_RECEIPT_MISMATCH"):
        service.apply(
            server_url=SERVER,
            owner_profile_ref=OWNER_PROFILE,
            operation_key="transfer-once",
            preview_token=preview.preview_token,
            confirm=True,
        )
    assert application.adapter.repository.identity().mode == ProjectMode.standalone
    session = application.adapter.authority_transfers.load()
    assert session is not None and session.state.remote_authoritative is True


def test_mcp_exposes_only_read_only_transfer_surfaces() -> None:
    transfer_names = {name for name in TOOL_NAMES if "authority_transfer" in name}
    assert transfer_names == {
        "p2p_project_authority_transfer_eligibility",
        "p2p_project_authority_transfer_preview",
        "p2p_project_authority_transfer_status",
    }
    assert all("apply" not in name and "upload" not in name for name in transfer_names)


def test_logout_suspends_link_without_detach_and_login_resumes_it(tmp_path: Path) -> None:
    transport = FakeWaveKitTransport()
    application, service = _service(tmp_path, transport)
    preview = _preview(service)
    service.apply(
        server_url=SERVER,
        owner_profile_ref=OWNER_PROFILE,
        operation_key="transfer-once",
        preview_token=preview.preview_token,
        confirm=True,
    )

    logout = service.logout(SERVER)

    suspended = application.adapter.repository.identity()
    assert logout["removed"] is True
    assert logout["linked_replica_suspended"] is True
    assert suspended.mode == ProjectMode.link_suspended
    assert suspended.remote_binding is not None
    capabilities = service.capabilities(SERVER)
    service.complete_login(
        capabilities,
        DeviceAuthorization(
            device_code="private-device-code",
            user_code="ABCD-EFGH",
            verification_uri=f"{SERVER}/activate",
            interval=1,
        ),
    )
    assert application.adapter.repository.identity().mode == ProjectMode.linked


def test_cli_reports_absent_local_transfer_without_network(tmp_path: Path) -> None:
    project = tmp_path / "project"
    ProjectApplicationService(project).init_project("CLI project")

    result = runner.invoke(
        app,
        ["project", "transfer", "status", "--root", str(project), "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["operation"] == "project.transfer.status"
    assert payload["data"]["authority_transfer_status"]["state"] == "absent"


def test_wavekit_url_policy_rejects_credentials_and_non_tls_hosts() -> None:
    assert normalize_server_url("https://WaveKit.Example.test/") == SERVER
    assert normalize_server_url("http://localhost:8000/") == "http://localhost:8000"
    with pytest.raises(ValueError, match="P2P_WAVEKIT_INVALID_URL"):
        normalize_server_url("http://wavekit.example.test")
    with pytest.raises(ValueError, match="P2P_WAVEKIT_INVALID_URL"):
        normalize_server_url("https://user:secret@wavekit.example.test")

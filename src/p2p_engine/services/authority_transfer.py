from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping
from typing import Protocol
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from p2p_engine.adapters.wavekit_credentials import (
    KeyringWaveKitCredentialStore,
    WaveKitCredentialStore,
)
from p2p_engine.adapters.wavekit_transfer_http import (
    HTTPSWaveKitTransferTransport,
    WaveKitTransferTransport,
)
from p2p_engine.core.authority_transfer import (
    AUTHORITY_TRANSFER_CAPABILITY_CONTRACT,
    AUTHORITY_TRANSFER_CAPABILITY_PATH,
    AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES,
    AUTHORITY_TRANSFER_PROTOCOL,
    AuthorityActivationReceipt,
    AuthorityTransferPreview,
    AuthorityTransferResult,
    AuthorityTransferSession,
    DeviceAuthorization,
    OAuthDeviceConfiguration,
    TransferCapabilities,
    TransferEndpoints,
    TransferState,
    WaveKitCredential,
    receipt_from_mapping,
    safe_profile_ref,
    transfer_id_for,
)
from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.project_identity import AuthorityEpoch, ProjectMode, ServerInstanceId
from p2p_engine.ports.project_state import ProjectStateAdapter


class IntegrationTransition(Protocol):
    def __call__(self) -> object: ...


class AuthorityTransferService:
    def __init__(
        self,
        *,
        adapter: ProjectStateAdapter,
        integration_transition: IntegrationTransition,
        transport: WaveKitTransferTransport | None = None,
        credentials: WaveKitCredentialStore | None = None,
        now: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.adapter = adapter
        self.integration_transition = integration_transition
        self.transport = transport or HTTPSWaveKitTransferTransport()
        self.credentials = credentials or KeyringWaveKitCredentialStore()
        self.now = now
        self.sleep = sleep

    def capabilities(self, server_url: str) -> TransferCapabilities:
        server = normalize_server_url(server_url)
        raw = self.transport.request_json(
            "GET",
            _same_origin_url(server, AUTHORITY_TRANSFER_CAPABILITY_PATH),
            max_bytes=AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES,
        )
        payload = _envelope(raw, "authority_transfer_capabilities")
        if payload.get("contract") != AUTHORITY_TRANSFER_CAPABILITY_CONTRACT:
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_PROTOCOL_UNSUPPORTED: capability contract differs"
            )
        if payload.get("protocol") != AUTHORITY_TRANSFER_PROTOCOL:
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_PROTOCOL_UNSUPPORTED: transfer protocol differs"
            )
        endpoints = _mapping(payload.get("endpoints"), "endpoints")
        expected_endpoints = {
            "eligibility",
            "sessions",
            "session",
            "manifest",
            "bundle",
            "blob",
            "commit",
            "cancel",
        }
        if set(endpoints) != expected_endpoints:
            raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: transfer endpoints are not exact")
        oauth = _mapping(payload.get("oauth_device"), "oauth_device")
        if set(oauth) != {
            "device_authorization_endpoint",
            "token_endpoint",
            "client_id",
            "scopes",
        } or not isinstance(oauth.get("scopes"), list):
            raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: OAuth device configuration is invalid")
        limits = _mapping(payload.get("limits"), "limits")
        if set(limits) != {"max_bundle_bytes", "max_blob_bytes", "max_blobs"}:
            raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: transfer limits are not exact")
        return TransferCapabilities(
            server_url=server,
            server_instance_id=ServerInstanceId(_required(payload, "server_instance_id")),
            endpoints=TransferEndpoints(
                **{name: _endpoint(endpoints, name) for name in sorted(expected_endpoints)}
            ),
            oauth_device=OAuthDeviceConfiguration(
                device_authorization_endpoint=_endpoint(oauth, "device_authorization_endpoint"),
                token_endpoint=_endpoint(oauth, "token_endpoint"),
                client_id=_required(oauth, "client_id"),
                scopes=tuple(str(item) for item in oauth["scopes"] if str(item)),
            ),
            max_bundle_bytes=_positive_int(limits.get("max_bundle_bytes"), "max_bundle_bytes"),
            max_blob_bytes=_positive_int(limits.get("max_blob_bytes"), "max_blob_bytes"),
            max_blobs=_positive_int(limits.get("max_blobs"), "max_blobs"),
        )

    def start_login(self, server_url: str) -> tuple[TransferCapabilities, DeviceAuthorization]:
        capabilities = self.capabilities(server_url)
        oauth = capabilities.oauth_device
        raw = self.transport.request_json(
            "POST",
            _same_origin_url(capabilities.server_url, oauth.device_authorization_endpoint),
            form={"client_id": oauth.client_id, "scope": " ".join(oauth.scopes)},
            max_bytes=AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES,
        )
        payload = _mapping(raw, "device authorization response")
        try:
            authorization = DeviceAuthorization(
                device_code=_required(payload, "device_code"),
                user_code=_required(payload, "user_code"),
                verification_uri=_required(payload, "verification_uri"),
                verification_uri_complete=str(payload.get("verification_uri_complete") or ""),
                expires_in=_positive_int(payload.get("expires_in", 600), "expires_in"),
                interval=_positive_int(payload.get("interval", 5), "interval"),
            )
        except ValueError as exc:
            raise ValueError("P2P_WAVEKIT_AUTH_INVALID: invalid device authorization") from exc
        return capabilities, authorization

    def complete_login(
        self,
        capabilities: TransferCapabilities,
        authorization: DeviceAuthorization,
    ) -> WaveKitCredential:
        deadline = self.now() + authorization.expires_in
        interval = authorization.interval
        oauth = capabilities.oauth_device
        while self.now() < deadline:
            raw = self.transport.request_json(
                "POST",
                _same_origin_url(capabilities.server_url, oauth.token_endpoint),
                form={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": authorization.device_code,
                    "client_id": oauth.client_id,
                },
                max_bytes=AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES,
            )
            payload = _mapping(raw, "token response")
            error = str(payload.get("error") or "")
            if error == "authorization_pending":
                self.sleep(interval)
                continue
            if error == "slow_down":
                interval += 5
                self.sleep(interval)
                continue
            if error:
                raise ValueError(f"P2P_WAVEKIT_AUTH_FAILED: device flow returned {error}")
            credential = self._credential(payload)
            self.credentials.set(capabilities.server_url, credential)
            self._set_auth_suspension(capabilities.server_url, suspended=False)
            return credential
        raise ValueError("P2P_WAVEKIT_AUTH_EXPIRED: device authorization expired")

    def auth_status(self, server_url: str) -> dict[str, object]:
        server = normalize_server_url(server_url)
        credential = self.credentials.get(server)
        try:
            identity = self.adapter.repository.identity()
            linked_suspended = identity.mode == ProjectMode.link_suspended
        except (ValueError, OSError):
            linked_suspended = False
        return {
            "contract": "p2p-wavekit-auth-status/v1",
            "server_url": server,
            "credential": credential.public_dict()
            if credential is not None
            else {
                "authenticated": False,
                "token_type": None,
                "expires_at": 0,
                "scopes": [],
                "account_profile_ref": None,
            },
            "linked_replica_suspended": linked_suspended,
        }

    def logout(self, server_url: str) -> dict[str, object]:
        server = normalize_server_url(server_url)
        removed = self.credentials.delete(server)
        suspended = self._set_auth_suspension(server, suspended=True)
        return {
            "contract": "p2p-wavekit-auth-logout/v1",
            "server_url": server,
            "removed": removed,
            "linked_replica_suspended": suspended,
        }

    def preview(
        self,
        *,
        server_url: str,
        owner_profile_ref: str,
        operation_key: str,
    ) -> AuthorityTransferPreview:
        owner_profile_ref = safe_profile_ref(owner_profile_ref, field_name="owner_profile_ref")
        identity = self.adapter.repository.identity()
        if identity.mode not in {ProjectMode.standalone, ProjectMode.detached} or identity.remote_binding is not None:
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_NOT_LOCAL: transfer requires an unbound locally authoritative project"
            )
        active = self.adapter.authority_transfers.load()
        if active is not None and active.state not in {
            TransferState.rejected,
            TransferState.cancelled,
            TransferState.expired,
        }:
            if active.project_uuid != identity.project_uuid:
                raise ValueError("P2P_AUTHORITY_TRANSFER_ACTIVE: another transfer is active")
        capabilities = self.capabilities(server_url)
        credential = self._access_credential(capabilities)
        snapshot = self.adapter.repository.snapshot()
        archive = self.adapter.snapshots.export_bundle()
        if len(archive.content) > capabilities.max_bundle_bytes:
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_PAYLOAD_TOO_LARGE: bundle exceeds server limit"
            )
        if len(snapshot.blobs) > capabilities.max_blobs:
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_PAYLOAD_TOO_LARGE: blob count exceeds server limit"
            )
        if any(item.size > capabilities.max_blob_bytes for item in snapshot.blobs):
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_PAYLOAD_TOO_LARGE: a blob exceeds server limit"
            )
        failed_blobs = self.adapter.blobs.verify(item.digest for item in snapshot.blobs)
        recovery = self.adapter.backups.recovery_status()
        blockers = list(f"managed blob failed verification: {item}" for item in failed_blobs)
        if recovery.state != "clean":
            blockers.append("canonical-memory recovery is pending")
        transfer_id = transfer_id_for(
            identity.project_uuid, operation_key, capabilities.server_instance_id
        )
        source_revision = self.adapter.repository.current_revision().sha256
        request_semantics = {
            "contract": AUTHORITY_TRANSFER_PROTOCOL,
            "operation": "transfer-authority",
            "transfer_id": transfer_id,
            "project_uuid": identity.project_uuid.value,
            "source_revision": source_revision,
            "semantic_state_digest": snapshot.semantic_state_digest,
            "bundle_digest": archive.sha256,
            "blob_manifest_digest": snapshot.blob_manifest_digest,
            "required_blobs": sorted(item.digest for item in snapshot.blobs),
            "server_instance_id": capabilities.server_instance_id.value,
            "owner_profile_ref": owner_profile_ref,
            "source_authority_epoch": 1,
        }
        fingerprint = semantic_sha256(request_semantics)
        eligibility = self.transport.request_json(
            "POST",
            self._url(capabilities, capabilities.endpoints.eligibility),
            token=credential.access_token,
            json_body={
                **request_semantics,
                "request_fingerprint": f"sha256:{fingerprint}",
                "bundle_schema": "p2p-project-bundle/v1",
                "memory_schema": snapshot.memory_schema,
                "domain_contract": snapshot.domain_contract,
            },
            max_bytes=AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES,
        )
        remote = _envelope(eligibility, "authority_transfer_eligibility")
        remote_blockers = remote.get("blockers", [])
        if not isinstance(remote_blockers, list):
            raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: eligibility blockers must be a list")
        if remote.get("eligible") is not True:
            blockers.extend(str(item) for item in remote_blockers if str(item))
        mapped = str(remote.get("owner_profile_ref") or "")
        if mapped and mapped != owner_profile_ref:
            blockers.append("authenticated account does not map to the requested owner profile")
        preview_token = semantic_sha256({**request_semantics, "request_fingerprint": fingerprint})
        return AuthorityTransferPreview(
            transfer_id=transfer_id,
            request_fingerprint=fingerprint,
            preview_token=preview_token,
            project_uuid=identity.project_uuid,
            source_revision=source_revision,
            semantic_state_digest=snapshot.semantic_state_digest,
            bundle_digest=archive.sha256,
            blob_manifest_digest=snapshot.blob_manifest_digest,
            server_url=capabilities.server_url,
            server_instance_id=capabilities.server_instance_id,
            owner_profile_ref=owner_profile_ref,
            storage_adapter=self.adapter.selection.adapter,
            entity_count=len(snapshot.entities),
            relation_count=len(snapshot.relations),
            blob_count=len(snapshot.blobs),
            blob_bytes=sum(item.size for item in snapshot.blobs),
            blockers=tuple(sorted(set(blockers))),
        )

    def apply(
        self,
        *,
        server_url: str,
        owner_profile_ref: str,
        operation_key: str,
        preview_token: str,
        confirm: bool,
    ) -> AuthorityTransferResult:
        if not confirm:
            raise ValueError("P2P_CONFIRMATION_REQUIRED: authority transfer requires --confirm")
        existing = self.adapter.authority_transfers.load()
        if existing is not None and existing.state == TransferState.linked:
            receipt = self.adapter.authority_transfers.receipt()
            integration = self.integration_transition()
            return AuthorityTransferResult(
                status="already_applied",
                session=existing,
                receipt=receipt,
                integration_status=str(getattr(integration, "status", "unknown")),
                message="The exact authority transfer was already activated locally.",
            )
        preview = self.preview(
            server_url=server_url,
            owner_profile_ref=owner_profile_ref,
            operation_key=operation_key,
        )
        if preview.preview_token != preview_token:
            raise ValueError("P2P_PREVIEW_STALE: transfer inputs or project revision changed")
        if not preview.eligible:
            raise ValueError("P2P_AUTHORITY_TRANSFER_BLOCKED: " + "; ".join(preview.blockers))
        capabilities = self.capabilities(preview.server_url)
        credential = self._access_credential(capabilities)
        snapshot = self.adapter.repository.snapshot()
        archive = self.adapter.snapshots.export_bundle()
        required_blobs = tuple(
            sorted(item.digest.removeprefix("sha256:") for item in snapshot.blobs)
        )
        session = AuthorityTransferSession(
            transfer_id=preview.transfer_id,
            request_fingerprint=preview.request_fingerprint,
            state=TransferState.preflighted,
            project_uuid=preview.project_uuid,
            source_revision=preview.source_revision,
            semantic_state_digest=preview.semantic_state_digest,
            bundle_digest=preview.bundle_digest,
            blob_manifest_digest=preview.blob_manifest_digest,
            server_url=preview.server_url,
            server_instance_id=preview.server_instance_id,
            owner_profile_ref=preview.owner_profile_ref,
            source_authority_epoch=AuthorityEpoch(1),
            required_blobs=required_blobs,
        )
        request = self._session_request(session, snapshot)
        created = self.transport.request_json(
            "POST",
            self._url(capabilities, capabilities.endpoints.sessions),
            token=credential.access_token,
            json_body=request,
            idempotency_key=session.transfer_id,
            max_bytes=AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES,
        )
        created_payload = _envelope(created, "authority_transfer_session")
        if str(created_payload.get("transfer_id") or "") != session.transfer_id:
            raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: session ID differs")
        self.adapter.authority_transfers.save(session)
        session = self.adapter.authority_transfers.save(
            session.with_state(TransferState.locally_fenced)
        )
        manifest_response = self.transport.request_json(
            "PUT",
            self._session_url(capabilities, capabilities.endpoints.manifest, session.transfer_id),
            token=credential.access_token,
            json_body={
                "contract": AUTHORITY_TRANSFER_PROTOCOL,
                "transfer_id": session.transfer_id,
                "request_fingerprint": f"sha256:{session.request_fingerprint}",
                "bundle_digest": f"sha256:{session.bundle_digest}",
                "blob_manifest_digest": f"sha256:{session.blob_manifest_digest}",
                "blobs": [item.to_dict() for item in snapshot.blobs],
            },
            idempotency_key=session.transfer_id,
            max_bytes=AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES,
        )
        manifest = _envelope(manifest_response, "authority_transfer_manifest")
        missing = manifest.get("missing_blobs", [])
        if not isinstance(missing, list):
            raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: missing_blobs must be a list")
        missing_digests = tuple(sorted(str(item).removeprefix("sha256:") for item in missing))
        if not set(missing_digests).issubset(set(session.required_blobs)):
            raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: server requested an unknown blob")
        self.transport.upload_bytes(
            self._session_url(capabilities, capabilities.endpoints.bundle, session.transfer_id),
            archive.content,
            token=credential.access_token,
            digest=session.bundle_digest,
            idempotency_key=session.transfer_id,
            max_bytes=capabilities.max_bundle_bytes,
        )
        for digest in missing_digests:
            content = self.adapter.blobs.read(f"sha256:{digest}")
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError("P2P_MANAGED_BLOB_DIGEST_MISMATCH: upload content differs")
            self.transport.upload_bytes(
                self._blob_url(capabilities, session.transfer_id, digest),
                content,
                token=credential.access_token,
                digest=digest,
                idempotency_key=f"{session.transfer_id}:{digest}",
                max_bytes=capabilities.max_blob_bytes,
            )
        session = self.adapter.authority_transfers.save(
            session.with_state(TransferState.remote_staging)
        )
        committed = self.transport.request_json(
            "POST",
            self._session_url(capabilities, capabilities.endpoints.commit, session.transfer_id),
            token=credential.access_token,
            json_body={
                "contract": AUTHORITY_TRANSFER_PROTOCOL,
                "transfer_id": session.transfer_id,
                "request_fingerprint": f"sha256:{session.request_fingerprint}",
                "confirm_activation": True,
            },
            idempotency_key=session.transfer_id,
            max_bytes=AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES,
        )
        committed_session = _envelope(committed, "authority_transfer_session")
        if str(committed_session.get("transfer_id") or "") != session.transfer_id:
            raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: committed session ID differs")
        remote_state = str(committed_session.get("state") or "")
        if remote_state == "committing":
            return AuthorityTransferResult(
                status="pending",
                session=session,
                message=(
                    "WaveKit accepted the transfer and is importing it; "
                    "run p2p project transfer recover until it is committed."
                ),
            )
        if remote_state != "committed":
            raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: commit returned an invalid state")
        receipt = self._receipt(committed)
        session = self.adapter.authority_transfers.save(
            session.with_state(TransferState.remote_committed)
        )
        session = self.adapter.authority_transfers.save(
            session.with_state(TransferState.local_binding_pending)
        )
        self.adapter.authority_transfers.activate_linked(session, receipt)
        session = self.adapter.authority_transfers.load()
        assert session is not None
        integration = self.integration_transition()
        integration_status = str(getattr(integration, "status", "unknown"))
        return AuthorityTransferResult(
            status="linked",
            session=session,
            receipt=receipt,
            integration_status=integration_status,
            message="WaveKit is authoritative; local project is now a linked replica.",
        )

    def status(self, *, server_url: str = "") -> dict[str, object]:
        session = self.adapter.authority_transfers.load()
        receipt = self.adapter.authority_transfers.receipt()
        payload: dict[str, object] = {
            "contract": "p2p-authority-transfer-status/v1",
            "state": session.state.value if session is not None else "absent",
            "session": session.to_dict() if session is not None else None,
            "receipt": receipt.to_dict() if receipt is not None else None,
            "remote": None,
            "mutation_performed": False,
        }
        if session is not None and server_url:
            capabilities = self.capabilities(server_url)
            if capabilities.server_instance_id != session.server_instance_id:
                raise ValueError("P2P_AUTHORITY_TRANSFER_DESTINATION_MISMATCH: server differs")
            credential = self._access_credential(capabilities)
            payload["remote"] = self._remote_status(session, capabilities, credential)
        return payload

    def recover(self) -> AuthorityTransferResult:
        session = self.adapter.authority_transfers.load()
        if session is None:
            raise ValueError("P2P_AUTHORITY_TRANSFER_NOT_FOUND: no local transfer state exists")
        if session.state == TransferState.linked:
            integration = self.integration_transition()
            return AuthorityTransferResult(
                status="already_linked",
                session=session,
                receipt=self.adapter.authority_transfers.receipt(),
                integration_status=str(getattr(integration, "status", "unknown")),
                message="Local binding is already complete.",
            )
        capabilities = self.capabilities(session.server_url)
        if capabilities.server_instance_id != session.server_instance_id:
            raise ValueError("P2P_AUTHORITY_TRANSFER_DESTINATION_MISMATCH: server identity changed")
        credential = self._access_credential(capabilities)
        remote = self._remote_status(session, capabilities, credential)
        state = str(remote.get("state") or "")
        if state == "committed":
            receipt = self._receipt(remote)
            session = self.adapter.authority_transfers.save(
                session.with_state(TransferState.local_binding_pending)
            )
            self.adapter.authority_transfers.activate_linked(session, receipt)
            current = self.adapter.authority_transfers.load()
            assert current is not None
            integration = self.integration_transition()
            return AuthorityTransferResult(
                status="linked",
                session=current,
                receipt=receipt,
                integration_status=str(getattr(integration, "status", "unknown")),
                message="Committed remote authority was recovered and bound locally.",
            )
        terminal = {
            "rejected": TransferState.rejected,
            "cancelled": TransferState.cancelled,
            "expired": TransferState.expired,
        }.get(state)
        if terminal is not None:
            released = self.adapter.authority_transfers.release_fence(
                session, terminal, error_code=str(remote.get("error_code") or "")
            )
            return AuthorityTransferResult(
                status="standalone_restored",
                session=released,
                message="WaveKit did not commit; the local standalone fence was released.",
            )
        return AuthorityTransferResult(
            status="pending",
            session=session,
            message="Transfer remains in progress; retry recovery with the same transfer ID.",
        )

    def _access_credential(self, capabilities: TransferCapabilities) -> WaveKitCredential:
        credential = self.credentials.get(capabilities.server_url)
        if credential is None:
            raise ValueError("P2P_WAVEKIT_AUTH_REQUIRED: login before transferring authority")
        if not credential.expires_at or credential.expires_at > int(self.now()) + 15:
            return credential
        if not credential.refresh_token:
            raise ValueError("P2P_WAVEKIT_AUTH_REQUIRED: stored credential expired")
        oauth = capabilities.oauth_device
        raw = self.transport.request_json(
            "POST",
            _same_origin_url(capabilities.server_url, oauth.token_endpoint),
            form={
                "grant_type": "refresh_token",
                "refresh_token": credential.refresh_token,
                "client_id": oauth.client_id,
            },
            max_bytes=AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES,
        )
        payload = _mapping(raw, "token refresh")
        if payload.get("error"):
            raise ValueError("P2P_WAVEKIT_AUTH_REQUIRED: credential refresh failed")
        refreshed = self._credential(payload, previous=credential)
        self.credentials.set(capabilities.server_url, refreshed)
        self._set_auth_suspension(capabilities.server_url, suspended=False)
        return refreshed

    def _set_auth_suspension(self, server_url: str, *, suspended: bool) -> bool:
        session = self.adapter.authority_transfers.load()
        if session is None or session.server_url != server_url:
            return False
        identity = self.adapter.repository.identity()
        if identity.mode not in {ProjectMode.linked, ProjectMode.link_suspended}:
            return False
        self.adapter.authority_transfers.set_link_suspended(suspended)
        return suspended

    def _credential(
        self, raw: Mapping[str, object], *, previous: WaveKitCredential | None = None
    ) -> WaveKitCredential:
        access_token = _required(raw, "access_token")
        expires_in = int(raw.get("expires_in") or 0)
        scopes = tuple(str(raw.get("scope") or "").split())
        return WaveKitCredential(
            access_token=access_token,
            refresh_token=str(
                raw.get("refresh_token") or (previous.refresh_token if previous else "")
            ),
            token_type=str(raw.get("token_type") or "Bearer"),
            expires_at=int(self.now()) + expires_in if expires_in else 0,
            scopes=scopes or (previous.scopes if previous else ()),
            account_profile_ref=str(
                raw.get("account_profile_ref") or (previous.account_profile_ref if previous else "")
            ),
        )

    @staticmethod
    def _session_request(session: AuthorityTransferSession, snapshot: object) -> dict[str, object]:
        return {
            "contract": AUTHORITY_TRANSFER_PROTOCOL,
            "transfer_id": session.transfer_id,
            "request_fingerprint": f"sha256:{session.request_fingerprint}",
            "project_uuid": session.project_uuid.value,
            "source_revision": session.source_revision,
            "source_authority_epoch": session.source_authority_epoch.value,
            "semantic_state_digest": f"sha256:{session.semantic_state_digest}",
            "bundle_contract": "p2p-project-bundle/v1",
            "bundle_digest": f"sha256:{session.bundle_digest}",
            "blob_manifest_digest": f"sha256:{session.blob_manifest_digest}",
            "owner_profile_ref": session.owner_profile_ref,
            "required_blobs": [f"sha256:{item}" for item in session.required_blobs],
        }

    def _remote_status(
        self,
        session: AuthorityTransferSession,
        capabilities: TransferCapabilities,
        credential: WaveKitCredential,
    ) -> Mapping[str, object]:
        raw = self.transport.request_json(
            "GET",
            self._session_url(capabilities, capabilities.endpoints.session, session.transfer_id),
            token=credential.access_token,
            max_bytes=AUTHORITY_TRANSFER_MAX_RESPONSE_BYTES,
        )
        payload = _envelope(raw, "authority_transfer_session")
        if str(payload.get("transfer_id") or "") != session.transfer_id:
            raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: status session ID differs")
        return payload

    @staticmethod
    def _receipt(raw: object) -> AuthorityActivationReceipt:
        payload = _mapping(raw, "commit response")
        if "authority_transfer_session" in payload:
            payload = _mapping(payload["authority_transfer_session"], "authority_transfer_session")
        receipt = payload.get("receipt")
        if not isinstance(receipt, Mapping):
            raise ValueError("P2P_AUTHORITY_TRANSFER_RECEIPT_INVALID: committed receipt is missing")
        return receipt_from_mapping(receipt)

    @staticmethod
    def _url(capabilities: TransferCapabilities, endpoint: str) -> str:
        return _same_origin_url(capabilities.server_url, endpoint)

    def _session_url(
        self, capabilities: TransferCapabilities, endpoint: str, transfer_id: str
    ) -> str:
        return self._url(capabilities, endpoint.format(transfer_id=quote(transfer_id, safe="")))

    def _blob_url(self, capabilities: TransferCapabilities, transfer_id: str, digest: str) -> str:
        endpoint = capabilities.endpoints.blob.format(
            transfer_id=quote(transfer_id, safe=""), digest=quote(digest, safe="")
        )
        return self._url(capabilities, endpoint)


def normalize_server_url(value: str) -> str:
    parsed = urlsplit(str(value or "").strip())
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("P2P_WAVEKIT_INVALID_URL: credentials, query and fragment are forbidden")
    if parsed.scheme == "https":
        pass
    elif parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        pass
    else:
        raise ValueError("P2P_WAVEKIT_INVALID_URL: HTTPS is required outside loopback")
    if not parsed.hostname:
        raise ValueError("P2P_WAVEKIT_INVALID_URL: server host is required")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), path, "", ""))


def _same_origin_url(server_url: str, endpoint: str) -> str:
    base = normalize_server_url(server_url)
    candidate = urljoin(base + "/", endpoint)
    parsed_base = urlsplit(base)
    parsed_candidate = urlsplit(candidate)
    if (
        parsed_candidate.scheme != parsed_base.scheme
        or parsed_candidate.hostname != parsed_base.hostname
        or parsed_candidate.port != parsed_base.port
        or parsed_candidate.username is not None
        or parsed_candidate.password is not None
        or parsed_candidate.fragment
    ):
        raise ValueError("P2P_WAVEKIT_INVALID_URL: endpoint escapes configured server origin")
    return candidate


def _endpoint(raw: Mapping[str, object], field_name: str) -> str:
    value = _required(raw, field_name)
    if len(value) > 2048 or "\x00" in value:
        raise ValueError(f"P2P_WAVEKIT_RESPONSE_INVALID: unsafe {field_name} endpoint")
    return value


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"P2P_WAVEKIT_RESPONSE_INVALID: {field_name} must be a mapping")
    return value


def _required(raw: Mapping[str, object], field_name: str) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"P2P_WAVEKIT_RESPONSE_INVALID: {field_name} is required")
    return value


def _positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"P2P_WAVEKIT_RESPONSE_INVALID: {field_name} must be positive")
    return value


def _envelope(raw: object, key: str) -> Mapping[str, object]:
    payload = _mapping(raw, key)
    nested = payload.get(key)
    return _mapping(nested, key) if nested is not None else payload

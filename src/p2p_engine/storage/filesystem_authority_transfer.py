from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from p2p_engine.core.authority_transfer import (
    AUTHORITY_TRANSFER_RECEIPT_CONTRACT,
    LINKED_PROJECT_BINDING_CONTRACT,
    LOCAL_AUTHORITY_TRANSFER_CONTRACT,
    AuthorityActivationReceipt,
    AuthorityTransferSession,
    TransferState,
    receipt_from_mapping,
    session_from_mapping,
)
from p2p_engine.core.mutation_preview import semantic_sha256, source_precondition
from p2p_engine.core.project_identity import ProjectIdentity, ProjectMode, RemoteBinding
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.project_identity import FilesystemProjectIdentityStore

AUTHORITY_TRANSFER_STATE_PATH = ".p2p/local/authority-transfer.yml"
AUTHORITY_TRANSFER_RECEIPT_PATH = ".p2p/local/authority-transfer-receipt.yml"
LINKED_PROJECT_BINDING_PATH = ".p2p/local/wavekit-binding.yml"
AUTHORITY_TRANSFER_DOCUMENT_MAX_BYTES = 262_144


class FilesystemAuthorityTransferStore:
    """Replica-local transfer state behind the selected filesystem adapter."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.p2p_dir = self.root / ".p2p"
        self.identity_store = FilesystemProjectIdentityStore(root=self.root, p2p_dir=self.p2p_dir)

    @property
    def state_path(self) -> Path:
        return self.root / AUTHORITY_TRANSFER_STATE_PATH

    def load(self) -> AuthorityTransferSession | None:
        if not self.state_path.exists():
            return None
        payload = self._read(self.state_path, "authority_transfer")
        if payload.get("contract") != LOCAL_AUTHORITY_TRANSFER_CONTRACT:
            raise ValueError("P2P_AUTHORITY_TRANSFER_STATE_INVALID: unsupported local state contract")
        raw = payload.get("session")
        if not isinstance(raw, Mapping):
            raise ValueError("P2P_AUTHORITY_TRANSFER_STATE_INVALID: session mapping is missing")
        return session_from_mapping(raw)

    def receipt(self) -> AuthorityActivationReceipt | None:
        path = self.root / AUTHORITY_TRANSFER_RECEIPT_PATH
        if not path.exists():
            return None
        payload = self._read(path, "authority_transfer_receipt")
        raw = payload.get("receipt")
        if not isinstance(raw, Mapping):
            raise ValueError("P2P_AUTHORITY_TRANSFER_RECEIPT_INVALID: receipt mapping is missing")
        return receipt_from_mapping(raw)

    def save(self, session: AuthorityTransferSession) -> AuthorityTransferSession:
        current = self.load()
        if current is not None:
            if current.transfer_id != session.transfer_id:
                raise ValueError(
                    "P2P_AUTHORITY_TRANSFER_ACTIVE: another transfer session already owns this project"
                )
            if current.request_fingerprint != session.request_fingerprint:
                raise ValueError(
                    "P2P_AUTHORITY_TRANSFER_CONFLICT: transfer ID is bound to another request"
                )
        self._commit(
            operation="authority-transfer-state",
            actor="local-owner",
            candidates={AUTHORITY_TRANSFER_STATE_PATH: self._state_bytes(session)},
        )
        return session

    def activate_linked(
        self,
        session: AuthorityTransferSession,
        receipt: AuthorityActivationReceipt,
    ) -> ProjectIdentity:
        current = self.identity_store.load()
        if current.mode != ProjectMode.standalone or current.remote_binding is not None:
            if current.mode == ProjectMode.linked and self.receipt() == receipt:
                return current
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_CUTOVER_BLOCKED: local project is no longer standalone"
            )
        self._verify_receipt(session, receipt)
        linked = ProjectIdentity(
            project_uuid=current.project_uuid,
            display_name=current.display_name,
            mode=ProjectMode.linked,
            replica_id=receipt.replica_id,
            remote_binding=RemoteBinding(
                server_instance_id=receipt.server_instance_id,
                remote_project_id=receipt.remote_project_id,
            ),
            lineage=current.lineage,
        )
        linked_session = session.with_state(TransferState.linked)
        identity_candidates = self.identity_store.candidate_documents(linked)
        candidates = {
            **identity_candidates,
            AUTHORITY_TRANSFER_STATE_PATH: self._state_bytes(linked_session),
            AUTHORITY_TRANSFER_RECEIPT_PATH: yaml_dump(
                {
                    "authority_transfer_receipt": {
                        "contract": AUTHORITY_TRANSFER_RECEIPT_CONTRACT,
                        "receipt": receipt.to_dict(),
                        "receipt_digest": receipt.receipt_digest,
                    }
                }
            ).encode("ascii"),
            LINKED_PROJECT_BINDING_PATH: yaml_dump(
                {
                    "linked_project_binding": {
                        "contract": LINKED_PROJECT_BINDING_CONTRACT,
                        "project_uuid": receipt.project_uuid.value,
                        "server_url": session.server_url,
                        "server_instance_id": receipt.server_instance_id.value,
                        "remote_project_id": receipt.remote_project_id.value,
                        "replica_id": receipt.replica_id.value,
                        "authority_epoch": receipt.authority_epoch.value,
                        "remote_revision": receipt.remote_revision,
                        "cursor": receipt.cursor,
                        "account_profile_ref": receipt.account_profile_ref,
                        "receipt_digest": receipt.receipt_digest,
                    }
                }
            ).encode("ascii"),
        }
        self._commit(
            operation="authority-transfer-local-cutover",
            actor="local-owner",
            candidates=candidates,
        )
        return linked

    def release_fence(
        self,
        session: AuthorityTransferSession,
        terminal_state: TransferState,
        *,
        error_code: str = "",
    ) -> AuthorityTransferSession:
        if terminal_state not in {
            TransferState.rejected,
            TransferState.cancelled,
            TransferState.expired,
        }:
            raise ValueError("P2P_AUTHORITY_TRANSFER_STATE_INVALID: terminal state is required")
        if session.state.remote_authoritative:
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_RECOVERY_REQUIRED: remote authority cannot be released locally"
            )
        updated = session.with_state(terminal_state, last_error_code=error_code)
        return self.save(updated)

    def writes_fenced(self) -> bool:
        session = self.load()
        return bool(session is not None and session.local_writes_fenced)

    def set_link_suspended(self, suspended: bool) -> ProjectIdentity:
        current = self.identity_store.load()
        expected = ProjectMode.link_suspended if suspended else ProjectMode.linked
        allowed = {ProjectMode.linked, ProjectMode.link_suspended}
        if current.mode not in allowed or current.remote_binding is None:
            return current
        if current.mode == expected:
            return current
        updated = ProjectIdentity(
            project_uuid=current.project_uuid,
            display_name=current.display_name,
            mode=expected,
            replica_id=current.replica_id,
            remote_binding=current.remote_binding,
            lineage=current.lineage,
        )
        self._commit(
            operation="wavekit-auth-link-suspension",
            actor="local-owner",
            candidates=self.identity_store.candidate_documents(updated),
        )
        return updated

    @staticmethod
    def _verify_receipt(
        session: AuthorityTransferSession,
        receipt: AuthorityActivationReceipt,
    ) -> None:
        mismatches: list[str] = []
        comparisons = (
            ("transfer_id", receipt.transfer_id, session.transfer_id),
            ("request_fingerprint", receipt.request_fingerprint, session.request_fingerprint),
            ("project_uuid", receipt.project_uuid, session.project_uuid),
            ("server_instance_id", receipt.server_instance_id, session.server_instance_id),
            ("bundle_digest", receipt.bundle_digest, session.bundle_digest),
            ("blob_manifest_digest", receipt.blob_manifest_digest, session.blob_manifest_digest),
            ("required_blobs", receipt.required_blobs, session.required_blobs),
            ("account_profile_ref", receipt.account_profile_ref, session.owner_profile_ref),
        )
        mismatches.extend(name for name, actual, expected in comparisons if actual != expected)
        if receipt.authority_epoch.value != session.source_authority_epoch.value + 1:
            mismatches.append("authority_epoch")
        if mismatches:
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_RECEIPT_MISMATCH: " + ", ".join(sorted(mismatches))
            )

    def _commit(self, *, operation: str, actor: str, candidates: dict[str, bytes]) -> None:
        sources = tuple(
            source_precondition(
                relative,
                (self.root / relative).read_bytes()
                if (self.root / relative).is_file() and not (self.root / relative).is_symlink()
                else None,
            )
            for relative in sorted(candidates)
        )
        result = AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir).apply(
            operation_id=operation,
            candidates=candidates,
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
            actor=actor,
        )
        if result.status != "applied":
            raise ValueError(
                "P2P_AUTHORITY_TRANSFER_LOCAL_COMMIT_FAILED: " + result.message
            )

    @staticmethod
    def _state_bytes(session: AuthorityTransferSession) -> bytes:
        return yaml_dump(
            {
                "authority_transfer": {
                    "contract": LOCAL_AUTHORITY_TRANSFER_CONTRACT,
                    "session": session.to_storage_dict(),
                }
            }
        ).encode("ascii")

    @staticmethod
    def _read(path: Path, root_key: str) -> Mapping[str, object]:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > AUTHORITY_TRANSFER_DOCUMENT_MAX_BYTES:
            raise ValueError("P2P_AUTHORITY_TRANSFER_STATE_INVALID: unsafe local transfer document")
        try:
            payload = load_yaml(path.read_bytes(), loader_contract=UNIQUE_LOADER_CONTRACT)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError("P2P_AUTHORITY_TRANSFER_STATE_INVALID: local state cannot be parsed") from exc
        if not isinstance(payload, Mapping) or set(payload) != {root_key}:
            raise ValueError("P2P_AUTHORITY_TRANSFER_STATE_INVALID: invalid document root")
        value = payload[root_key]
        if not isinstance(value, Mapping):
            raise ValueError("P2P_AUTHORITY_TRANSFER_STATE_INVALID: document body is not a mapping")
        return value

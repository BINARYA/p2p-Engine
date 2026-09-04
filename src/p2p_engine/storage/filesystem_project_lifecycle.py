from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from p2p_engine.core.canonical_memory import canonical_json_bytes
from p2p_engine.core.project_lifecycle import (
    DETACH_RECEIPT_CONTRACT,
    PROJECT_LIFECYCLE_LOCAL_STATE_CONTRACT,
    PROJECT_LIFECYCLE_RECEIPT_CONTRACT,
    PROJECT_PUBLICATION_CONTRACT,
    DetachReceipt,
    LifecycleReceipt,
    LocalLifecycleState,
    ProjectPublication,
    detach_receipt_from_mapping,
    lifecycle_receipt_from_mapping,
    local_lifecycle_state_from_mapping,
    publication_from_mapping,
)
from p2p_engine.foundation.files import sync_directory, write_bytes_atomic

PROJECT_LIFECYCLE_STATE_PATH = ".p2p/local/project-lifecycle/state.json"
PROJECT_LIFECYCLE_RECEIPT_ROOT = ".p2p/local/project-lifecycle/receipts"
PROJECT_DETACH_RECEIPT_PATH = ".p2p/local/project-lifecycle/detach-receipt.json"
PROJECT_PUBLICATION_ROOT = ".p2p/local/project-lifecycle/publications"
PROJECT_LIFECYCLE_MAX_DOCUMENT_BYTES = 1_048_576


class FilesystemProjectLifecycleStore:
    """Replica-local lifecycle evidence behind the filesystem adapter."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.state_path = self.root / PROJECT_LIFECYCLE_STATE_PATH

    def state(self) -> LocalLifecycleState | None:
        if not self.state_path.exists():
            return None
        raw = self._read(self.state_path)
        if raw.get("contract") != PROJECT_LIFECYCLE_LOCAL_STATE_CONTRACT:
            raise ValueError("P2P_PROJECT_LIFECYCLE_STATE_INVALID: unsupported state contract")
        return local_lifecycle_state_from_mapping(raw)

    def save_state(self, state: LocalLifecycleState) -> LocalLifecycleState:
        self._write(self.state_path, state.to_dict())
        return state

    def receipt(self, operation_id: str) -> LifecycleReceipt | None:
        path = self._receipt_path(operation_id)
        if not path.exists():
            return None
        raw = self._read(path)
        if raw.get("contract") != PROJECT_LIFECYCLE_RECEIPT_CONTRACT:
            raise ValueError("P2P_PROJECT_LIFECYCLE_STATE_INVALID: unsupported receipt contract")
        receipt = lifecycle_receipt_from_mapping(raw)
        if receipt.operation_id != operation_id:
            raise ValueError("P2P_PROJECT_LIFECYCLE_STATE_INVALID: receipt identity differs")
        return receipt

    def save_receipt(self, receipt: LifecycleReceipt) -> LifecycleReceipt:
        path = self._receipt_path(receipt.operation_id)
        current = self.receipt(receipt.operation_id)
        if current is not None and current != receipt:
            raise ValueError(
                "P2P_PROJECT_LIFECYCLE_OPERATION_CONFLICT: operation ID has another receipt"
            )
        self._write(path, receipt.to_dict(), immutable=current is None)
        return receipt

    def detach_receipt(self) -> DetachReceipt | None:
        path = self.root / PROJECT_DETACH_RECEIPT_PATH
        if not path.exists():
            return None
        raw = self._read(path)
        if raw.get("contract") != DETACH_RECEIPT_CONTRACT:
            raise ValueError("P2P_PROJECT_LIFECYCLE_STATE_INVALID: unsupported detach receipt")
        return detach_receipt_from_mapping(raw)

    def save_detach_receipt(self, receipt: DetachReceipt) -> DetachReceipt:
        path = self.root / PROJECT_DETACH_RECEIPT_PATH
        existing = self.detach_receipt()
        if existing is not None and existing != receipt:
            raise ValueError(
                "P2P_PROJECT_LIFECYCLE_OPERATION_CONFLICT: detached project has another receipt"
            )
        self._write(path, receipt.to_dict(), immutable=existing is None)
        return receipt

    def publication(self, publication_id: str, version: int) -> ProjectPublication | None:
        path = self._publication_path(publication_id, version)
        if not path.exists():
            return None
        raw = self._read(path)
        if raw.get("contract") != PROJECT_PUBLICATION_CONTRACT:
            raise ValueError("P2P_PROJECT_LIFECYCLE_STATE_INVALID: publication contract differs")
        return publication_from_mapping(raw)

    def save_publication(self, publication: ProjectPublication) -> ProjectPublication:
        path = self._publication_path(publication.publication_id, publication.version)
        existing = self.publication(publication.publication_id, publication.version)
        if existing is not None and existing != publication:
            raise ValueError(
                "P2P_PROJECT_PUBLICATION_CONFLICT: immutable publication version differs"
            )
        self._write(path, publication.to_dict(), immutable=existing is None)
        return publication

    def publications(self) -> tuple[ProjectPublication, ...]:
        root = self.root / PROJECT_PUBLICATION_ROOT
        if not root.exists():
            return ()
        if root.is_symlink() or not root.is_dir():
            raise ValueError("P2P_PROJECT_LIFECYCLE_STATE_INVALID: publication root is unsafe")
        records: list[ProjectPublication] = []
        for path in sorted(root.glob("*.json")):
            raw = self._read(path)
            records.append(publication_from_mapping(raw))
        return tuple(records)

    def _receipt_path(self, operation_id: str) -> Path:
        digest = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()
        return self.root / PROJECT_LIFECYCLE_RECEIPT_ROOT / f"{digest}.json"

    def _publication_path(self, publication_id: str, version: int) -> Path:
        digest = hashlib.sha256(publication_id.encode("utf-8")).hexdigest()
        return self.root / PROJECT_PUBLICATION_ROOT / f"{digest}-v{version}.json"

    @staticmethod
    def _read(path: Path) -> Mapping[str, object]:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > PROJECT_LIFECYCLE_MAX_DOCUMENT_BYTES
        ):
            raise ValueError("P2P_PROJECT_LIFECYCLE_STATE_INVALID: unsafe local document")
        try:
            raw = json.loads(path.read_bytes())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "P2P_PROJECT_LIFECYCLE_STATE_INVALID: local document cannot be parsed"
            ) from exc
        if not isinstance(raw, Mapping):
            raise ValueError("P2P_PROJECT_LIFECYCLE_STATE_INVALID: document must be an object")
        return raw

    @staticmethod
    def _write(path: Path, payload: Mapping[str, object], *, immutable: bool = False) -> None:
        content = canonical_json_bytes(payload)
        if immutable and path.exists():
            if path.is_file() and not path.is_symlink() and path.read_bytes() == content:
                return
            raise ValueError("P2P_PROJECT_LIFECYCLE_OPERATION_CONFLICT: immutable evidence exists")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_bytes_atomic(path, content, mode=0o600)
        sync_directory(path.parent)

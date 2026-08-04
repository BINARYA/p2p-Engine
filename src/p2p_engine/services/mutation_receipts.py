from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path, PurePosixPath
import re
from typing import Mapping

import yaml

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.mutation_receipts import (
    MUTATION_RECEIPT_MAX_FILE_BYTES,
    MUTATION_RECEIPT_MAX_KEY_BYTES,
    MUTATION_RECEIPT_ROOT,
    MUTATION_RECEIPT_SCHEMA_VERSION,
    MutationPostcondition,
    MutationReceipt,
    MutationReceiptStatus,
)
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.workspace_transactions import physical_sha256


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def validate_idempotency_key(value: str) -> str:
    if not isinstance(value, str) or not value or not value.strip():
        raise ValueError("P2P_IDEMPOTENCY_KEY_REQUIRED: a non-empty idempotency key is required")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("P2P_IDEMPOTENCY_KEY_INVALID: key must be valid UTF-8") from exc
    if len(encoded) > MUTATION_RECEIPT_MAX_KEY_BYTES:
        raise ValueError(
            f"P2P_IDEMPOTENCY_KEY_INVALID: key exceeds {MUTATION_RECEIPT_MAX_KEY_BYTES} UTF-8 bytes"
        )
    return value


def idempotency_key_sha256(value: str) -> str:
    return hashlib.sha256(validate_idempotency_key(value).encode("utf-8")).hexdigest()


def preview_token_sha256(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def mutation_request_fingerprint(
    *,
    operation: str,
    actor: str,
    preview_token: str,
    semantic_inputs: Mapping[str, object],
) -> str:
    return semantic_sha256(
        {
            "fingerprint_version": 1,
            "operation": str(operation),
            "actor": str(actor),
            "preview_token_sha256": preview_token_sha256(preview_token),
            "semantic_inputs": dict(semantic_inputs),
        }
    )


class MutationReceiptService:
    def __init__(self, *, root: Path, p2p_dir: Path) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.receipt_root = self.root / MUTATION_RECEIPT_ROOT
        self.transaction_root = self.p2p_dir / ".internal" / "workspace-transactions" / "transactions"

    def relative_path(self, idempotency_key: str) -> str:
        return f"{MUTATION_RECEIPT_ROOT}/{idempotency_key_sha256(idempotency_key)}.yml"

    def fingerprint(
        self,
        *,
        operation: str,
        actor: str,
        preview_token: str,
        semantic_inputs: Mapping[str, object],
    ) -> str:
        return mutation_request_fingerprint(
            operation=operation,
            actor=actor,
            preview_token=preview_token,
            semantic_inputs=semantic_inputs,
        )

    def prepare(
        self,
        *,
        idempotency_key: str,
        operation: str,
        actor: str,
        request_fingerprint_sha256: str,
        preview_token: str,
        result: Mapping[str, object],
        candidates: Mapping[str, bytes],
    ) -> tuple[str, bytes, MutationReceipt]:
        key_hash = idempotency_key_sha256(idempotency_key)
        _require_sha256(request_fingerprint_sha256, "request fingerprint")
        postconditions = tuple(
            MutationPostcondition(
                path=path,
                physical_sha256=hashlib.sha256(content).hexdigest(),
            )
            for path, content in sorted(candidates.items())
        )
        receipt = MutationReceipt(
            key_sha256=key_hash,
            operation=operation,
            actor=actor,
            request_fingerprint_sha256=request_fingerprint_sha256,
            preview_token_sha256=preview_token_sha256(preview_token),
            completion_status="applied",
            completed_at=_utc_now_iso(),
            result=dict(result),
            postconditions=postconditions,
        )
        return (
            f"{MUTATION_RECEIPT_ROOT}/{key_hash}.yml",
            yaml_dump(receipt.to_payload()).encode("utf-8"),
            receipt,
        )

    def replay(
        self,
        *,
        idempotency_key: str,
        request_fingerprint_sha256: str,
    ) -> MutationReceipt | None:
        key_hash = idempotency_key_sha256(idempotency_key)
        relative = f"{MUTATION_RECEIPT_ROOT}/{key_hash}.yml"
        incomplete = self._incomplete_status(relative)
        if incomplete is not None:
            raise ValueError(
                "P2P_IDEMPOTENCY_INCOMPLETE_TRANSACTION: "
                f"workspace transaction {incomplete.transaction_id or 'unknown'} requires recovery"
            )
        path = self.root / relative
        if not path.exists():
            return None
        receipt = self._read_receipt(path, expected_key_sha256=key_hash)
        if receipt.request_fingerprint_sha256 != request_fingerprint_sha256:
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: idempotency key was already used for a different request"
            )
        if not self._postconditions_match(receipt):
            raise ValueError(
                "P2P_IDEMPOTENCY_POSTCONDITION_DRIFT: recorded mutation postconditions no longer match"
            )
        return receipt

    def status(self, idempotency_key: str) -> MutationReceiptStatus:
        key_hash = idempotency_key_sha256(idempotency_key)
        relative = f"{MUTATION_RECEIPT_ROOT}/{key_hash}.yml"
        incomplete = self._incomplete_status(relative)
        if incomplete is not None:
            return incomplete
        path = self.root / relative
        if not path.exists():
            return MutationReceiptStatus(
                state="not_found",
                message="No mutation receipt exists for the supplied idempotency key.",
            )
        receipt = self._read_receipt(path, expected_key_sha256=key_hash)
        postconditions_match = self._postconditions_match(receipt)
        return MutationReceiptStatus(
            state="applied" if postconditions_match else "postcondition_drift",
            operation=receipt.operation,
            actor=receipt.actor,
            completion_status=receipt.completion_status,
            result=receipt.result,
            postconditions_match=postconditions_match,
            message=(
                "Mutation receipt is complete and its postconditions match."
                if postconditions_match
                else "Mutation receipt is complete but its postconditions have drifted."
            ),
        )

    def _read_receipt(self, path: Path, *, expected_key_sha256: str) -> MutationReceipt:
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("receipt path is not a regular file")
            if path.stat().st_size > MUTATION_RECEIPT_MAX_FILE_BYTES:
                raise ValueError("receipt exceeds the size limit")
            payload = load_yaml(
                path.read_bytes(),
                loader_contract=UNIQUE_LOADER_CONTRACT,
            )
            receipt = _receipt_from_payload(payload)
        except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
            raise ValueError(f"P2P_IDEMPOTENCY_RECEIPT_CORRUPT: {exc}") from exc
        if receipt.key_sha256 != expected_key_sha256:
            raise ValueError(
                "P2P_IDEMPOTENCY_RECEIPT_CORRUPT: receipt key hash does not match its path"
            )
        return receipt

    def _postconditions_match(self, receipt: MutationReceipt) -> bool:
        try:
            return all(
                physical_sha256(self.root / item.path) == item.physical_sha256
                for item in receipt.postconditions
            )
        except (OSError, ValueError):
            return False

    def _incomplete_status(self, receipt_relative: str) -> MutationReceiptStatus | None:
        if not self.transaction_root.exists():
            return None
        matches: list[tuple[str, dict[str, object] | None]] = []
        for transaction_dir in sorted(self.transaction_root.iterdir()):
            if not transaction_dir.is_dir() or transaction_dir.is_symlink():
                continue
            staged = transaction_dir / "candidates" / receipt_relative
            if not staged.is_file() or staged.is_symlink():
                continue
            journal: dict[str, object] | None = None
            journal_path = transaction_dir / "journal.yml"
            if journal_path.is_file() and not journal_path.is_symlink():
                try:
                    loaded = load_yaml(journal_path.read_bytes())
                    journal = loaded if isinstance(loaded, dict) else None
                except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError):
                    journal = None
            matches.append((transaction_dir.name, journal))
        if not matches:
            return None
        transaction_id, journal = matches[0]
        operation = str(journal.get("operation_id") or "") if journal else ""
        actor = str(journal.get("actor") or "") if journal else ""
        state = str(journal.get("state") or "incomplete") if journal else "invalid"
        return MutationReceiptStatus(
            state="incomplete",
            operation=operation,
            actor=actor,
            completion_status=state,
            postconditions_match=None,
            recovery_required=True,
            transaction_id=transaction_id,
            message="The receipt belongs to an incomplete workspace transaction.",
        )


def _receipt_from_payload(payload: object) -> MutationReceipt:
    if not isinstance(payload, dict) or not isinstance(payload.get("mutation_receipt"), dict):
        raise ValueError("receipt document must contain mutation_receipt mapping")
    data = payload["mutation_receipt"]
    assert isinstance(data, dict)
    if data.get("schema_version") != MUTATION_RECEIPT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported receipt schema {data.get('schema_version')!r}; expected {MUTATION_RECEIPT_SCHEMA_VERSION}"
        )
    key_hash = _required_sha256(data, "key_sha256")
    request_fingerprint = _required_sha256(data, "request_fingerprint_sha256")
    token_hash = _required_sha256(data, "preview_token_sha256")
    operation = _required_text(data, "operation")
    if operation not in {"install", "adopt", "migrate"}:
        raise ValueError(f"unsupported receipt operation: {operation}")
    actor = _required_text(data, "actor")
    completion_status = _required_text(data, "completion_status")
    if completion_status != "applied":
        raise ValueError("receipt completion_status must be applied")
    completed_at = _required_text(data, "completed_at")
    result = data.get("result")
    if not isinstance(result, dict):
        raise ValueError("receipt result must be a mapping")
    _validate_result(result, operation=operation)
    raw_postconditions = data.get("postconditions")
    if not isinstance(raw_postconditions, list) or not raw_postconditions:
        raise ValueError("receipt postconditions must be a non-empty sequence")
    postconditions: list[MutationPostcondition] = []
    seen: set[str] = set()
    for raw in raw_postconditions:
        if not isinstance(raw, dict):
            raise ValueError("receipt postcondition must be a mapping")
        path = _validated_postcondition_path(_required_text(raw, "path"))
        if path in seen:
            raise ValueError(f"duplicate receipt postcondition path: {path}")
        seen.add(path)
        postconditions.append(
            MutationPostcondition(
                path=path,
                physical_sha256=_required_sha256(raw, "physical_sha256"),
            )
        )
    if result["changed_paths"] != [item.path for item in postconditions]:
        raise ValueError("receipt result paths do not match receipt postconditions")
    return MutationReceipt(
        key_sha256=key_hash,
        operation=operation,
        actor=actor,
        request_fingerprint_sha256=request_fingerprint,
        preview_token_sha256=token_hash,
        completion_status=completion_status,
        completed_at=completed_at,
        result=result,
        postconditions=tuple(postconditions),
    )


def _validate_result(result: Mapping[str, object], *, operation: str) -> None:
    allowed = {"operation", "operation_id", "coordinate", "changed_paths"}
    unknown = sorted(str(key) for key in result if key not in allowed)
    if unknown:
        raise ValueError(f"receipt result contains unsupported fields: {', '.join(unknown)}")
    if result.get("operation") != operation:
        raise ValueError("receipt result operation does not match receipt operation")
    _required_text(result, "operation_id")
    _required_text(result, "coordinate")
    changed_paths = result.get("changed_paths")
    if not isinstance(changed_paths, list) or not changed_paths:
        raise ValueError("receipt result changed_paths must be a non-empty sequence")
    normalized = [_validated_postcondition_path(str(path)) for path in changed_paths]
    if normalized != sorted(set(normalized)):
        raise ValueError("receipt result changed_paths must be unique and sorted")


def _validated_postcondition_path(value: str) -> str:
    pure = PurePosixPath(value.replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe receipt postcondition path: {value}")
    normalized = pure.as_posix()
    if not normalized.startswith(".p2p/") or normalized.startswith(".p2p/.internal/"):
        raise ValueError(f"receipt postcondition path is not canonical project state: {value}")
    return normalized


def _required_text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"receipt field {field} must be non-empty text")
    return value


def _required_sha256(payload: Mapping[str, object], field: str) -> str:
    value = _required_text(payload, field)
    _require_sha256(value, field)
    return value


def _require_sha256(value: str, field: str) -> None:
    if _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

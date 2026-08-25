from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


MUTATION_RECEIPT_SCHEMA_VERSION = 3
MUTATION_RECEIPT_ROOT = ".p2p/.internal/mutation-receipts"
MUTATION_RECEIPT_MAX_KEY_BYTES = 256
MUTATION_RECEIPT_MAX_FILE_BYTES = 65_536


@dataclass(frozen=True)
class MutationPostcondition:
    path: str
    physical_sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "physical_sha256": self.physical_sha256,
        }


@dataclass(frozen=True)
class MutationReceipt:
    key_sha256: str
    operation: str
    actor: str
    request_fingerprint_sha256: str
    preview_token_sha256: str
    completion_status: str
    completed_at: str
    result: Mapping[str, object]
    postconditions: tuple[MutationPostcondition, ...]
    authority: Mapping[str, object] | None = None
    schema_version: int = MUTATION_RECEIPT_SCHEMA_VERSION

    def to_payload(self) -> dict[str, object]:
        return {
            "mutation_receipt": {
                "schema_version": self.schema_version,
                "key_sha256": self.key_sha256,
                "operation": self.operation,
                "actor": self.actor,
                "request_fingerprint_sha256": self.request_fingerprint_sha256,
                "preview_token_sha256": self.preview_token_sha256,
                "completion_status": self.completion_status,
                "completed_at": self.completed_at,
                "result": dict(self.result),
                "authority": dict(self.authority) if self.authority is not None else None,
                "postconditions": [item.to_dict() for item in self.postconditions],
            }
        }


@dataclass(frozen=True)
class MutationReceiptStatus:
    state: str
    operation: str = ""
    actor: str = ""
    completion_status: str = ""
    result: Mapping[str, object] = field(default_factory=dict)
    authority: Mapping[str, object] | None = None
    postconditions_match: bool | None = None
    recovery_required: bool = False
    transaction_id: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "operation": self.operation,
            "actor": self.actor,
            "completion_status": self.completion_status,
            "result": dict(self.result),
            "authority": dict(self.authority) if self.authority is not None else None,
            "postconditions_match": self.postconditions_match,
            "recovery_required": self.recovery_required,
            "transaction_id": self.transaction_id,
            "message": self.message,
        }

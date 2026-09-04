from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from p2p_engine.core.canonical_memory import semantic_sha256

REPLICA_DRIFT_STATUS_CONTRACT = "p2p-replica-drift-status/v1"
REPLICA_SEMANTIC_DIFF_CONTRACT = "p2p-replica-semantic-diff/v1"
REPLICA_RECONCILIATION_PLAN_CONTRACT = "p2p-replica-reconciliation-plan/v1"
REPLICA_FORENSIC_BACKUP_CONTRACT = "p2p-replica-forensic-backup/v1"
REPLICA_RECONCILIATION_RESULT_CONTRACT = "p2p-replica-reconciliation-result/v1"
MAX_DRIFT_DIFF_ENTRIES = 256


class DriftClassification(str, Enum):
    stale_valid = "stale-valid"
    transient_valid = "transient-valid"
    semantic_drift = "semantic-drift"
    identity_mismatch = "identity-mismatch"
    structural_corruption = "structural-corruption"
    incomplete_local_operation = "incomplete-local-operation"


@dataclass(frozen=True)
class DriftFinding:
    code: str
    message: str
    blocking: bool
    entity_type: str = ""
    entity_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "blocking": self.blocking,
            "entity_type": self.entity_type or None,
            "entity_id": self.entity_id or None,
        }


@dataclass(frozen=True)
class ReplicaDriftStatus:
    status: str
    classification: DriftClassification | None
    project_uuid: str = ""
    replica_id: str = ""
    authority_epoch: int = 0
    confirmed_revision: int = 0
    confirmed_change_batch_id: str = ""
    confirmed_semantic_digest: str = ""
    current_semantic_digest: str = ""
    confirmed_blob_manifest_digest: str = ""
    current_blob_manifest_digest: str = ""
    findings: tuple[DriftFinding, ...] = ()
    next_actions: tuple[str, ...] = ()

    @property
    def blocking(self) -> bool:
        return any(item.blocking for item in self.findings)

    @property
    def writes_permitted(self) -> bool:
        return self.status == "healthy" and not self.blocking

    @property
    def diff_available(self) -> bool:
        return self.classification == DriftClassification.semantic_drift

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": REPLICA_DRIFT_STATUS_CONTRACT,
            "status": self.status,
            "classification": (
                self.classification.value if self.classification is not None else None
            ),
            "project_uuid": self.project_uuid or None,
            "replica_id": self.replica_id or None,
            "authority_epoch": self.authority_epoch if self.replica_id else None,
            "confirmed_revision": self.confirmed_revision if self.replica_id else None,
            "confirmed_change_batch_id": self.confirmed_change_batch_id or None,
            "confirmed_semantic_digest": _public_digest(
                self.confirmed_semantic_digest
            ),
            "current_semantic_digest": _public_digest(self.current_semantic_digest),
            "confirmed_blob_manifest_digest": _public_digest(
                self.confirmed_blob_manifest_digest
            ),
            "current_blob_manifest_digest": _public_digest(
                self.current_blob_manifest_digest
            ),
            "findings": [item.to_dict() for item in self.findings],
            "diff_available": self.diff_available,
            "writes_permitted": self.writes_permitted,
            "next_actions": list(self.next_actions),
            "mutation_performed": False,
        }


@dataclass(frozen=True)
class SemanticDiffEntry:
    change: str
    entity_type: str
    entity_id: str
    confirmed_version: int | None
    local_version: int | None
    confirmed_digest: str | None
    local_digest: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "change": self.change,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "confirmed_version": self.confirmed_version,
            "local_version": self.local_version,
            "confirmed_digest": _public_digest(self.confirmed_digest or ""),
            "local_digest": _public_digest(self.local_digest or ""),
        }


@dataclass(frozen=True)
class ReplicaSemanticDiff:
    project_uuid: str
    replica_id: str
    confirmed_revision: int
    current_remote_revision: int
    entries: tuple[SemanticDiffEntry, ...]
    complete: bool
    truncated: bool
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": REPLICA_SEMANTIC_DIFF_CONTRACT,
            "project_uuid": self.project_uuid,
            "replica_id": self.replica_id,
            "confirmed_revision": self.confirmed_revision,
            "current_remote_revision": self.current_remote_revision,
            "entries": [item.to_dict() for item in self.entries],
            "entry_count": len(self.entries),
            "complete": self.complete,
            "truncated": self.truncated,
            "issues": list(self.issues),
            "physical_paths_exposed": False,
            "mutation_performed": False,
        }


@dataclass(frozen=True)
class ReconciliationCommand:
    command: str
    payload_contract: str
    payload: Mapping[str, object]
    entity_preconditions: tuple[Mapping[str, object], ...]
    expected_effect: str

    def to_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "payload_contract": self.payload_contract,
            "payload": dict(self.payload),
            "entity_preconditions": [dict(item) for item in self.entity_preconditions],
            "expected_effect": self.expected_effect,
        }


@dataclass(frozen=True)
class ReplicaReconciliationPlan:
    project_uuid: str
    replica_id: str
    authority_epoch: int
    confirmed_revision: int
    current_remote_revision: int
    local_semantic_digest: str
    remote_semantic_digest: str
    commands: tuple[ReconciliationCommand, ...]
    unsupported_differences: tuple[Mapping[str, object], ...] = ()
    conflicts: tuple[Mapping[str, object], ...] = ()
    complete: bool = False
    server_preview_token: str = ""
    plan_digest: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_digest", semantic_sha256(self._digest_payload()))

    def _digest_payload(self) -> dict[str, object]:
        return {
            "contract": REPLICA_RECONCILIATION_PLAN_CONTRACT,
            "project_uuid": self.project_uuid,
            "replica_id": self.replica_id,
            "authority_epoch": self.authority_epoch,
            "confirmed_revision": self.confirmed_revision,
            "current_remote_revision": self.current_remote_revision,
            "local_semantic_digest": _public_digest(self.local_semantic_digest),
            "remote_semantic_digest": _public_digest(self.remote_semantic_digest),
            "commands": [item.to_dict() for item in self.commands],
            "unsupported_differences": [
                dict(item) for item in self.unsupported_differences
            ],
            "conflicts": [dict(item) for item in self.conflicts],
            "complete": self.complete,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._digest_payload(),
            "plan_digest": f"sha256:{self.plan_digest}",
            "server_preview_token": self.server_preview_token or None,
            "mutation_performed": False,
        }


@dataclass(frozen=True)
class ReplicaForensicBackup:
    backup_ref: str
    archive_sha256: str
    file_count: int
    byte_count: int
    verified: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": REPLICA_FORENSIC_BACKUP_CONTRACT,
            "backup_ref": self.backup_ref,
            "archive_sha256": _public_digest(self.archive_sha256),
            "file_count": self.file_count,
            "byte_count": self.byte_count,
            "verified": self.verified,
            "physical_path_exposed": False,
        }


def _public_digest(value: str) -> str | None:
    if not value:
        return None
    return value if value.startswith("sha256:") else f"sha256:{value}"

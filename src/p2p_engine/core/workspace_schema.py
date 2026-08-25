from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


WORKSPACE_SCHEMA_CONTRACT_VERSION = 1
CURRENT_WORKSPACE_SCHEMA_VERSION = 4
WORKSPACE_SCHEMA_POLICY_VERSION = 4

LAYOUT_CURRENT = "current"
LAYOUT_INVALID = "invalid"
LAYOUT_UNSUPPORTED = "unsupported"

ALIGNMENT_ALIGNED = "aligned"
ALIGNMENT_DEGRADED = "degraded"
ALIGNMENT_RECOVERY_REQUIRED = "recovery_required"

LOCK_ABSENT = "absent"
LOCK_ACTIVE = "active"
LOCK_STALE = "stale"
LOCK_RECOVERY_OWNED = "recovery_owned"
LOCK_INVALID = "invalid"

DIAGNOSTIC_NAMESPACE = "P2P3"


@dataclass(frozen=True)
class WorkspaceSchemaState:
    contract_version: int
    current_version: int
    baseline: str
    initialized_at: str
    initialized_by: str

    def to_payload(self) -> dict[str, object]:
        return {
            "workspace_schema": {
                "contract_version": self.contract_version,
                "current_version": self.current_version,
                "baseline": self.baseline,
                "initialized_at": self.initialized_at,
                "initialized_by": self.initialized_by,
            }
        }


@dataclass(frozen=True)
class WorkspaceDiagnostic:
    code: str
    severity: str
    path: str
    message: str
    suggested_command: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
            "suggested_command": self.suggested_command,
        }


@dataclass(frozen=True)
class WorkspaceSchemaStatus:
    schema_path: str
    state: str
    layout_status: str
    alignment_status: str
    current_version: int | None
    target_version: int
    contract_version: int | None = None
    schema: WorkspaceSchemaState | None = None
    findings: tuple[WorkspaceDiagnostic, ...] = ()
    recovery: Mapping[str, object] = field(default_factory=dict)

    @property
    def inspectable(self) -> bool:
        return self.layout_status == LAYOUT_CURRENT

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_path": self.schema_path,
            "state": self.state,
            "layout_status": self.layout_status,
            "alignment_status": self.alignment_status,
            "current_version": self.current_version,
            "target_version": self.target_version,
            "contract_version": self.contract_version,
            "inspectable": self.inspectable,
            "schema": self.schema.to_payload()["workspace_schema"] if self.schema else None,
            "recovery": dict(self.recovery),
            "findings": [item.to_dict() for item in self.findings],
        }


@dataclass(frozen=True)
class WorkspaceSchemaPreflight:
    schema_path: str
    state: str
    layout_status: str
    current_version: int | None
    target_version: int
    contract_version: int | None = None
    recovery: Mapping[str, object] = field(default_factory=dict)

    @property
    def inspectable(self) -> bool:
        return self.layout_status == LAYOUT_CURRENT

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_path": self.schema_path,
            "state": self.state,
            "layout_status": self.layout_status,
            "current_version": self.current_version,
            "target_version": self.target_version,
            "contract_version": self.contract_version,
            "inspectable": self.inspectable,
            "recovery": dict(self.recovery),
        }


@dataclass(frozen=True)
class WorkspaceTransactionLock:
    state: str
    path: str
    transaction_id: str = ""
    pid: int | None = None
    acquired_at: str = ""
    owner: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "path": self.path,
            "transaction_id": self.transaction_id,
            "pid": self.pid,
            "acquired_at": self.acquired_at,
            "owner": self.owner,
            "message": self.message,
        }


@dataclass(frozen=True)
class WorkspaceTransactionRecoveryStatus:
    required: bool
    lock: WorkspaceTransactionLock
    transaction_id: str = ""
    journal_state: str = ""
    available_actions: tuple[str, ...] = ()
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "required": self.required,
            "lock": self.lock.to_dict(),
            "transaction_id": self.transaction_id,
            "journal_state": self.journal_state,
            "available_actions": list(self.available_actions),
            "message": self.message,
        }


@dataclass(frozen=True)
class WorkspaceTransactionRecoveryResult:
    status: str
    transaction_id: str
    restored_paths: tuple[str, ...] = ()
    changed_paths: tuple[str, ...] = ()
    message: str = ""
    recovery_required: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "transaction_id": self.transaction_id,
            "restored_paths": list(self.restored_paths),
            "changed_paths": list(self.changed_paths),
            "message": self.message,
            "recovery_required": self.recovery_required,
        }

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


WORKSPACE_SCHEMA_CONTRACT_VERSION = 1
CURRENT_WORKSPACE_SCHEMA_VERSION = 1
WORKSPACE_SCHEMA_POLICY_VERSION = 1

LEGACY_WORKSPACE_VERSION = 0

LAYOUT_LEGACY = "legacy"
LAYOUT_CURRENT = "current"
LAYOUT_AHEAD = "ahead"
LAYOUT_INVALID = "invalid"
LAYOUT_UNSUPPORTED = "unsupported"
LAYOUT_INCOMPLETE = "incomplete"

ALIGNMENT_ALIGNED = "aligned"
ALIGNMENT_DEGRADED = "degraded"
ALIGNMENT_OWNER_INPUT_REQUIRED = "owner_input_required"
ALIGNMENT_REPOSITORY_CURATION_REQUIRED = "repository_curation_required"
ALIGNMENT_RECOVERY_REQUIRED = "recovery_required"

FINDING_COMPATIBLE = "compatible"
FINDING_DEGRADED = "degraded"
FINDING_MIGRATION_REQUIRED = "migration_required"
FINDING_OWNER_INPUT_REQUIRED = "owner_input_required"
FINDING_REPOSITORY_CURATION_REQUIRED = "repository_curation_required"
FINDING_ENGINE_PREREQUISITE_REQUIRED = "engine_prerequisite_required"
FINDING_UNSUPPORTED = "unsupported"
FINDING_INVALID = "invalid"

OP_CREATE_CANONICAL = "create_canonical"
OP_UPDATE_CANONICAL = "update_canonical"
OP_PRESERVE_LEGACY = "preserve_legacy"
OP_QUARANTINE_LEGACY = "quarantine_legacy"
OP_REFRESH_DERIVED = "refresh_derived"
OP_OWNER_INPUT = "owner_input"
OP_REPOSITORY_CURATION = "repository_curation"
OP_NO_OP = "no_op"

MIGRATION_STATUS_APPLIED = "applied"
MIGRATION_STATUS_NO_OP = "no_op"
MIGRATION_STATUS_BLOCKED = "blocked"
MIGRATION_STATUS_STALE_PLAN = "stale_plan"
MIGRATION_STATUS_STAGE_FAILED = "stage_failed"
MIGRATION_STATUS_ROLLED_BACK = "rolled_back"
MIGRATION_STATUS_RECOVERY_REQUIRED = "recovery_required"

LOCK_ABSENT = "absent"
LOCK_ACTIVE = "active"
LOCK_STALE = "stale"
LOCK_RECOVERY_OWNED = "recovery_owned"
LOCK_INVALID = "invalid"

DIAGNOSTIC_NAMESPACE = "P2P3"


@dataclass(frozen=True)
class AppliedWorkspaceMigration:
    migration_id: str
    source_version: int
    target_version: int
    applied_at: str
    actor: str
    plan_fingerprint_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.migration_id,
            "from": "legacy_undeclared" if self.source_version == 0 else self.source_version,
            "to": self.target_version,
            "applied_at": self.applied_at,
            "actor": self.actor,
            "plan_fingerprint_sha256": self.plan_fingerprint_sha256,
        }


@dataclass(frozen=True)
class WorkspaceSchemaState:
    contract_version: int
    current_version: int
    baseline: str
    initialized_at: str
    initialized_by: str
    applied_migrations: tuple[AppliedWorkspaceMigration, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "workspace_schema": {
                "contract_version": self.contract_version,
                "current_version": self.current_version,
                "baseline": self.baseline,
                "initialized_at": self.initialized_at,
                "initialized_by": self.initialized_by,
                "applied_migrations": [item.to_dict() for item in self.applied_migrations],
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
class TransitionRuntimeSupport:
    inspect: bool
    plan: bool
    apply: bool
    inspect_requires: str = ""
    plan_requires: str = ""
    apply_requires: str = ""
    capabilities: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "inspect": self.inspect,
            "plan": self.plan,
            "apply": self.apply,
            "inspect_requires": self.inspect_requires,
            "plan_requires": self.plan_requires,
            "apply_requires": self.apply_requires,
            "capabilities": list(self.capabilities),
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
    transition_support: TransitionRuntimeSupport | None = None
    recovery: Mapping[str, object] = field(default_factory=dict)

    @property
    def inspectable(self) -> bool:
        return self.layout_status not in {LAYOUT_INVALID, LAYOUT_UNSUPPORTED}

    @property
    def migration_required(self) -> bool:
        return self.layout_status == LAYOUT_LEGACY

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
            "migration_required": self.migration_required,
            "schema": self.schema.to_payload()["workspace_schema"] if self.schema else None,
            "transition_support": self.transition_support.to_dict() if self.transition_support else None,
            "recovery": dict(self.recovery),
            "findings": [item.to_dict() for item in self.findings],
        }


@dataclass(frozen=True)
class ArtifactInventoryEntry:
    path: str
    classification: str
    exists: bool
    size: int
    physical_sha256: str
    semantic_sha256: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "classification": self.classification,
            "exists": self.exists,
            "size": self.size,
            "physical_sha256": self.physical_sha256,
            "semantic_sha256": self.semantic_sha256,
        }


@dataclass(frozen=True)
class CompatibilityFinding:
    code: str
    classification: str
    message: str
    path: str = ""
    recovery_action: str = ""
    migration_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "classification": self.classification,
            "message": self.message,
            "path": self.path,
            "recovery_action": self.recovery_action,
            "migration_id": self.migration_id,
        }


@dataclass(frozen=True)
class CompatibilitySnapshot:
    schema_status: WorkspaceSchemaStatus
    project_id: str
    inventory: tuple[ArtifactInventoryEntry, ...]
    findings: tuple[CompatibilityFinding, ...]
    source_access: Mapping[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_status": self.schema_status.to_dict(),
            "project_id": self.project_id,
            "inventory": [item.to_dict() for item in self.inventory],
            "findings": [item.to_dict() for item in self.findings],
            "source_access": dict(self.source_access),
        }


@dataclass(frozen=True)
class MigrationOperation:
    operation_id: str
    kind: str
    target: str
    reason: str
    migration_id: str
    write_class: str
    canonical: bool
    before_exists: bool
    before_physical_sha256: str | None
    candidate_semantic_sha256: str | None
    validator: str
    rollback: str
    dependencies: tuple[str, ...] = ()
    applicable: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "kind": self.kind,
            "target": self.target,
            "reason": self.reason,
            "migration_id": self.migration_id,
            "write_class": self.write_class,
            "canonical": self.canonical,
            "before_exists": self.before_exists,
            "before_physical_sha256": self.before_physical_sha256,
            "candidate_semantic_sha256": self.candidate_semantic_sha256,
            "validator": self.validator,
            "rollback": self.rollback,
            "dependencies": list(self.dependencies),
            "applicable": self.applicable,
        }


@dataclass(frozen=True)
class MigrationPlan:
    status: str
    source_version: int
    target_version: int
    direction: str
    migration_ids: tuple[str, ...]
    operations: tuple[MigrationOperation, ...]
    findings: tuple[CompatibilityFinding, ...]
    owner_inputs: Mapping[str, object]
    planner_version: int
    fingerprint_sha256: str
    applicable: bool
    transition_support: tuple[TransitionRuntimeSupport, ...] = ()
    advisory_checkpoint: str = "Create a repository checkpoint before apply."
    candidate_files: Mapping[str, bytes] = field(default_factory=dict, repr=False, compare=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "source_version": self.source_version,
            "target_version": self.target_version,
            "direction": self.direction,
            "migration_ids": list(self.migration_ids),
            "operations": [item.to_dict() for item in self.operations],
            "findings": [item.to_dict() for item in self.findings],
            "owner_inputs": dict(self.owner_inputs),
            "planner_version": self.planner_version,
            "fingerprint_sha256": self.fingerprint_sha256,
            "applicable": self.applicable,
            "transition_support": [item.to_dict() for item in self.transition_support],
            "advisory_checkpoint": self.advisory_checkpoint,
        }


@dataclass(frozen=True)
class MigrationApplyResult:
    status: str
    source_version: int
    target_version: int
    plan_fingerprint_sha256: str
    transaction_id: str = ""
    changed_paths: tuple[str, ...] = ()
    restored_paths: tuple[str, ...] = ()
    semantic_hashes: Mapping[str, str] = field(default_factory=dict)
    physical_hashes: Mapping[str, str] = field(default_factory=dict)
    message: str = ""
    recovery_required: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "source_version": self.source_version,
            "target_version": self.target_version,
            "plan_fingerprint_sha256": self.plan_fingerprint_sha256,
            "transaction_id": self.transaction_id,
            "changed_paths": list(self.changed_paths),
            "restored_paths": list(self.restored_paths),
            "semantic_hashes": dict(self.semantic_hashes),
            "physical_hashes": dict(self.physical_hashes),
            "message": self.message,
            "recovery_required": self.recovery_required,
        }


@dataclass(frozen=True)
class MigrationLock:
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
class MigrationRecoveryStatus:
    required: bool
    lock: MigrationLock
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
class MigrationRecoveryResult:
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

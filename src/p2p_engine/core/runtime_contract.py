from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


RUNTIME_STATUS_COMPATIBLE = "compatible"
RUNTIME_STATUS_INCOMPATIBLE = "incompatible"
RUNTIME_STATUS_INVALID_CONTRACT = "invalid_contract"
RUNTIME_STATUS_UNSUPPORTED_CONTRACT = "unsupported_contract"
RUNTIME_STATUS_MISSING_CONTRACT = "missing_contract"

RUNTIME_CONTRACT_INVALID = "P2P260_RUNTIME_CONTRACT_INVALID"
RUNTIME_CONTRACT_UNSUPPORTED = "P2P261_RUNTIME_CONTRACT_UNSUPPORTED"
RUNTIME_CONTRACT_MISSING_FIELD = "P2P262_RUNTIME_CONTRACT_MISSING_FIELD"
RUNTIME_CONTRACT_INVALID_VERSION = "P2P263_RUNTIME_CONTRACT_INVALID_VERSION"
RUNTIME_CONTRACT_RECOMMENDED_OUT_OF_RANGE = "P2P264_RUNTIME_CONTRACT_RECOMMENDED_OUT_OF_RANGE"
RUNTIME_CONTRACT_INSTALLER_FIELD = "P2P265_RUNTIME_CONTRACT_INSTALLER_FIELD"
RUNTIME_CONTRACT_MISSING = "P2P266_RUNTIME_CONTRACT_MISSING"
RUNTIME_SETUP_GUIDE_DRIFT = "P2P268_RUNTIME_SETUP_GUIDE_DRIFT"
RUNTIME_SETUP_GUIDE_UNMANAGED = "P2P269_RUNTIME_SETUP_GUIDE_UNMANAGED"

RUNTIME_SETUP_GUIDE_MARKER = "<!-- P2P: generated-runtime-setup schema=1 source=.p2p/project/runtime.yml -->"

RUNTIME_CONTRACT_UPDATE_STATUS_APPLICABLE = "applicable"
RUNTIME_CONTRACT_UPDATE_STATUS_PREVIEW_BLOCKED = "preview_blocked"
RUNTIME_CONTRACT_UPDATE_STATUS_NO_CHANGE = "no_change"
RUNTIME_CONTRACT_UPDATE_STATUS_UPDATED = "updated"
RUNTIME_CONTRACT_UPDATE_STATUS_BLOCKED = "blocked"
RUNTIME_CONTRACT_UPDATE_STATUS_PARTIAL_FAILURE = "partial_failure"

RUNTIME_CONTRACT_IMPACT_RECOMMENDED_ONLY = "recommended_only"
RUNTIME_CONTRACT_IMPACT_RANGE_WIDENING = "range_widening"
RUNTIME_CONTRACT_IMPACT_RANGE_TIGHTENING = "range_tightening"
RUNTIME_CONTRACT_IMPACT_RUNTIME_LINE_CHANGE = "runtime_line_change"
RUNTIME_CONTRACT_IMPACT_CURRENT_RUNTIME_EXCLUDED = "current_runtime_excluded"

RUNTIME_SETUP_GUIDE_STATE_MISSING = "missing"
RUNTIME_SETUP_GUIDE_STATE_MANAGED_ALIGNED = "managed_aligned"
RUNTIME_SETUP_GUIDE_STATE_MANAGED_DRIFTED = "managed_drifted"
RUNTIME_SETUP_GUIDE_STATE_UNMANAGED = "unmanaged"

RUNTIME_SETUP_GUIDE_ACTION_NONE = "none"
RUNTIME_SETUP_GUIDE_ACTION_GENERATE = "generate"
RUNTIME_SETUP_GUIDE_ACTION_REGENERATE = "regenerate"
RUNTIME_SETUP_GUIDE_ACTION_BLOCKED = "blocked"

RUNTIME_CONTRACT_BLOCKER_UNMANAGED_SETUP_GUIDE = "unmanaged_setup_guide"
RUNTIME_CONTRACT_BLOCKER_INVALID_PROPOSED_CONTRACT = "invalid_proposed_contract"
RUNTIME_CONTRACT_BLOCKER_UNTRUSTED_CURRENT_CONTRACT = "untrusted_current_contract"
RUNTIME_CONTRACT_BLOCKER_STALE_PREVIEW = "stale_preview"
RUNTIME_CONTRACT_BLOCKER_OWNER_AUTHORITY_REQUIRED = "owner_authority_required"
RUNTIME_CONTRACT_BLOCKER_CONFIRMATION_REQUIRED = "confirmation_required"
RUNTIME_CONTRACT_BLOCKER_REASON_REQUIRED = "reason_required"


@dataclass(frozen=True)
class P2PRuntimeRequirement:
    requires: str
    recommended: str


@dataclass(frozen=True)
class RuntimeContract:
    schema_version: int
    p2p: P2PRuntimeRequirement


@dataclass(frozen=True)
class RuntimeFinding:
    code: str
    severity: str
    path: Path
    message: str
    suggested_command: str = ""


@dataclass(frozen=True)
class RuntimeStatus:
    contract_path: Path
    state: str
    compatible: bool
    requires: str | None = None
    recommended: str | None = None
    current_version: str | None = None
    findings: list[RuntimeFinding] = field(default_factory=list)
    suggested_command: str = "p2p runtime status"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_path": str(self.contract_path),
            "state": self.state,
            "compatible": self.compatible,
            "requires": self.requires,
            "recommended": self.recommended,
            "current_version": self.current_version,
            "suggested_command": self.suggested_command,
            "findings": [
                {
                    "code": finding.code,
                    "severity": finding.severity,
                    "path": str(finding.path),
                    "message": finding.message,
                    "suggested_command": finding.suggested_command,
                }
                for finding in self.findings
            ],
        }

@dataclass(frozen=True)
class RuntimeWritePreflight:
    operation: str
    allowed: bool
    status: RuntimeStatus
    message: str

    def require_allowed(self) -> None:
        if not self.allowed:
            raise ValueError(self.message)


@dataclass(frozen=True)
class RuntimeContractUpdateAuthority:
    required_for_apply: bool
    actor_resolved: bool
    apply_authorized: bool
    status: str
    actor: str = ""
    role: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_for_apply": self.required_for_apply,
            "actor_resolved": self.actor_resolved,
            "apply_authorized": self.apply_authorized,
            "status": self.status,
            "actor": self.actor,
            "role": self.role,
            "source": self.source,
        }


@dataclass(frozen=True)
class RuntimeContractUpdatePreview:
    status: str
    current_state: str
    proposed_requires: str | None
    proposed_recommended: str | None
    proposed_valid: bool
    validation_errors: list[str] = field(default_factory=list)
    comparison_available: bool = False
    impact_labels: list[str] = field(default_factory=list)
    reason_required: bool = False
    confirmation_required: bool = False
    release_availability: str = "unverified"
    active_runtime_satisfies_proposed_range: bool | None = None
    range_comparison: dict[str, Any] = field(default_factory=dict)
    setup_guide: dict[str, Any] = field(default_factory=dict)
    authority: RuntimeContractUpdateAuthority | None = None
    apply_allowed: bool = False
    apply_would_be_blocked: bool = True
    blocked_reason: str = ""
    required_workflow: str = ""
    expected_state_token: str | None = None
    files_changed: list[str] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "current_state": self.current_state,
            "proposed_contract": {
                "requires": self.proposed_requires,
                "recommended": self.proposed_recommended,
                "valid": self.proposed_valid,
            },
            "validation_errors": list(self.validation_errors),
            "comparison_available": self.comparison_available,
            "impact_labels": list(self.impact_labels),
            "reason_required": self.reason_required,
            "confirmation_required": self.confirmation_required,
            "release_availability": self.release_availability,
            "active_runtime_satisfies_proposed_range": self.active_runtime_satisfies_proposed_range,
            "range_comparison": dict(self.range_comparison),
            "setup_guide": dict(self.setup_guide),
            "authority": self.authority.to_dict() if self.authority else {},
            "apply_allowed": self.apply_allowed,
            "apply_would_be_blocked": self.apply_would_be_blocked,
            "blocked_reason": self.blocked_reason,
            "required_workflow": self.required_workflow,
            "expected_state_token": self.expected_state_token,
            "files_changed": list(self.files_changed),
            "audit": dict(self.audit),
        }


@dataclass(frozen=True)
class RuntimeContractUpdateResult:
    status: str
    current_state: str
    proposed_requires: str | None
    proposed_recommended: str | None
    files_changed: list[str] = field(default_factory=list)
    blocked_reason: str = ""
    message: str = ""
    impact_labels: list[str] = field(default_factory=list)
    setup_guide: dict[str, Any] = field(default_factory=dict)
    authority: RuntimeContractUpdateAuthority | None = None
    active_runtime_compatible_after_update: bool | None = None
    subsequent_governed_writes_blocked: bool = False
    post_update_mutations_performed: bool = False
    full_validation_deferred: bool = False
    audit: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "current_state": self.current_state,
            "proposed_contract": {
                "requires": self.proposed_requires,
                "recommended": self.proposed_recommended,
            },
            "files_changed": list(self.files_changed),
            "blocked_reason": self.blocked_reason,
            "message": self.message,
            "impact_labels": list(self.impact_labels),
            "setup_guide": dict(self.setup_guide),
            "authority": self.authority.to_dict() if self.authority else {},
            "active_runtime_compatible_after_update": self.active_runtime_compatible_after_update,
            "subsequent_governed_writes_blocked": self.subsequent_governed_writes_blocked,
            "post_update_mutations_performed": self.post_update_mutations_performed,
            "full_validation_deferred": self.full_validation_deferred,
            "audit": dict(self.audit),
        }

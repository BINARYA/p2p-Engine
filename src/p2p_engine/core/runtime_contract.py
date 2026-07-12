from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


RUNTIME_STATUS_COMPATIBLE = "compatible"
RUNTIME_STATUS_INCOMPATIBLE = "incompatible"
RUNTIME_STATUS_INVALID_CONTRACT = "invalid_contract"
RUNTIME_STATUS_UNSUPPORTED_CONTRACT = "unsupported_contract"
RUNTIME_STATUS_MISSING_CONTRACT = "missing_contract"
RUNTIME_STATUS_LEGACY_UNDECLARED = "legacy_undeclared"

RUNTIME_CONTRACT_INVALID = "P2P260_RUNTIME_CONTRACT_INVALID"
RUNTIME_CONTRACT_UNSUPPORTED = "P2P261_RUNTIME_CONTRACT_UNSUPPORTED"
RUNTIME_CONTRACT_MISSING_FIELD = "P2P262_RUNTIME_CONTRACT_MISSING_FIELD"
RUNTIME_CONTRACT_INVALID_VERSION = "P2P263_RUNTIME_CONTRACT_INVALID_VERSION"
RUNTIME_CONTRACT_RECOMMENDED_OUT_OF_RANGE = "P2P264_RUNTIME_CONTRACT_RECOMMENDED_OUT_OF_RANGE"
RUNTIME_CONTRACT_INSTALLER_FIELD = "P2P265_RUNTIME_CONTRACT_INSTALLER_FIELD"
RUNTIME_CONTRACT_MISSING = "P2P266_RUNTIME_CONTRACT_MISSING"
RUNTIME_CONTRACT_LEGACY_UNDECLARED = "P2P267_RUNTIME_CONTRACT_LEGACY_UNDECLARED"
RUNTIME_SETUP_GUIDE_DRIFT = "P2P268_RUNTIME_SETUP_GUIDE_DRIFT"
RUNTIME_SETUP_GUIDE_UNMANAGED = "P2P269_RUNTIME_SETUP_GUIDE_UNMANAGED"

RUNTIME_SETUP_GUIDE_MARKER = "<!-- P2P: generated-runtime-setup schema=1 source=.p2p/project/runtime.yml -->"


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

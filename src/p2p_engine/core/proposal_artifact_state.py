from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ProposalArtifactExpectation(StrEnum):
    required = "required"
    required_when_applicable = "required_when_applicable"
    optional_memory = "optional_memory"
    not_expected = "not_expected"


class ProposalArtifactStatus(StrEnum):
    unknown = "unknown"
    missing = "missing"
    weak = "weak"
    satisfied = "satisfied"
    deferred = "deferred"
    not_applicable = "not_applicable"
    absent_legacy = "absent_legacy"


class ProposalArtifactConfirmation(StrEnum):
    system = "system"
    agent_proposed = "agent_proposed"
    owner_confirmed = "owner_confirmed"
    unconfirmed = "unconfirmed"


class ProposalArtifactRiskFlag(StrEnum):
    governance_policy = "governance_policy"
    public_interface = "public_interface"
    persistent_state = "persistent_state"
    compatibility_migration = "compatibility_migration"
    cross_module = "cross_module"
    permission_security_sync = "permission_security_sync"
    source_of_truth_memory = "source_of_truth_memory"
    user_workflow_docs_release = "user_workflow_docs_release"
    dependency_runtime_infra = "dependency_runtime_infra"
    high_uncertainty_evidence = "high_uncertainty_evidence"
    alternatives = "alternatives"
    owner_clarification = "owner_clarification"


@dataclass(frozen=True)
class ProposalArtifactRecord:
    artifact_id: str
    filename: str
    expectation: ProposalArtifactExpectation
    status: ProposalArtifactStatus
    reason: str
    source: str
    actor: str
    confirmation: ProposalArtifactConfirmation
    confirmed_by: str
    risk_flags: list[ProposalArtifactRiskFlag]
    created_at: str
    updated_at: str
    history: list[dict[str, object]]


@dataclass(frozen=True)
class ProposalArtifactStateView:
    proposal_id: str
    status: str
    path: Path
    schema_version: int | None
    legacy_state: ProposalArtifactStatus | None
    legacy_reason: str
    artifacts: list[ProposalArtifactRecord]
    suggested_next: list[str]


@dataclass(frozen=True)
class ProposalArtifactOperation:
    proposal_id: str
    path: Path
    artifact: ProposalArtifactRecord | None
    view: ProposalArtifactStateView
    message: str

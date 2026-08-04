from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ProposalDecisionDiagnosticDefinition:
    code: str
    title: str
    severity: str
    recovery: str


_KNOWN = (
    (
        "P2P361_DECISION_LEDGER_INVALID",
        "Decision ledger invalid",
        "error",
        "Inspect validation diagnostics and use the governed ledger-repair workflow.",
    ),
    (
        "P2P362_DECISION_PROJECTION_DIVERGENCE",
        "Decision projection diverged",
        "warning",
        "Preview and apply projection repair; do not edit the projection manually.",
    ),
    (
        "P2P363_DECISION_TRANSITION_INVALID",
        "Decision transition invalid",
        "error",
        "Inspect decision status and choose a transition allowed from the current head.",
    ),
    (
        "P2P364_DECISION_OWNER_REQUIRED",
        "Current owner required",
        "error",
        "Use a current project owner identity and keep executor identity separate.",
    ),
    (
        "P2P365_DECISION_STALE_PREVIEW",
        "Decision preview stale",
        "error",
        "Generate a fresh preview from the current source head.",
    ),
    (
        "P2P366_DECISION_REPLAY_MISMATCH",
        "Decision replay mismatch",
        "error",
        "Reuse an operation key only with identical normalized semantics.",
    ),
    (
        "P2P367_DECISION_CONCURRENT_HEAD",
        "Decision head changed",
        "error",
        "Refresh status and preview against the new ledger head.",
    ),
    (
        "P2P368_DECISION_REINSTATEMENT_MISMATCH",
        "Reinstatement binding mismatch",
        "error",
        "Reference the original accepted event and its matching revocation event.",
    ),
    (
        "P2P369_DECISION_LINEAGE_INVALID",
        "Decision lineage invalid",
        "error",
        "Supply typed lineage and valid target proposal IDs.",
    ),
    (
        "P2P370_DECISION_IMPACT_INCOMPLETE",
        "Decision impact incomplete",
        "error",
        "Repair malformed dependency sources and regenerate the impact preview.",
    ),
    (
        "P2P371_DECISION_PREVIEW_REQUIRED",
        "Decision preview required",
        "error",
        "Run decision preview before any apply operation.",
    ),
    (
        "P2P372_DECISION_REPAIR_UNSAFE",
        "Decision repair unsafe",
        "error",
        "Use a reviewed candidate that preserves every valid event.",
    ),
    (
        "P2P373_DECISION_SOURCE_CHANGED",
        "Decision source changed",
        "error",
        "Restart the request after source capture stabilizes.",
    ),
    (
        "P2P374_DECISION_CONSENT_MISMATCH",
        "Decision consent mismatch",
        "error",
        "Grant proposal_decision_apply consent for the exact PROP-ID@preview-token target.",
    ),
    (
        "P2P375_DECISION_SCHEMA_V3_REQUIRED",
        "Workspace schema v3 required",
        "error",
        "Inspect workspace schema status; this runtime supports schema v3 only.",
    ),
    (
        "P2P376_DECISION_FUTURE_CONTRACT",
        "Future decision contract unsupported",
        "error",
        "Upgrade P2P Engine before reading or mutating this contract.",
    ),
    (
        "P2P377_DECISION_PROPOSAL_BINDING_DIVERGED",
        "Proposal semantics diverged",
        "error",
        "Create a linked revision proposal or restore the accepted semantic body.",
    ),
    (
        "P2P378_DECISION_RECONSIDERATION_REQUIRES_NEW_PROPOSAL",
        "Reconsideration requires a new proposal",
        "warning",
        "Create a linked proposal instead of rewriting rejected or withdrawn history.",
    ),
)

PROPOSAL_DECISION_DIAGNOSTICS: Mapping[
    str,
    ProposalDecisionDiagnosticDefinition,
] = MappingProxyType(
    {
        code: ProposalDecisionDiagnosticDefinition(
            code=code,
            title=title,
            severity=severity,
            recovery=recovery,
        )
        for code, title, severity, recovery in _KNOWN
    }
    | {
        f"P2P{number}_DECISION_RESERVED": ProposalDecisionDiagnosticDefinition(
            code=f"P2P{number}_DECISION_RESERVED",
            title="Reserved decision diagnostic",
            severity="error",
            recovery="Upgrade P2P Engine and inspect the current diagnostic catalog.",
        )
        for number in range(379, 390)
    }
)

_CODE = re.compile(r"\b(P2P3[6-8][0-9]_[A-Z0-9_]+)\b")


def proposal_decision_diagnostic(
    code_or_message: str,
) -> ProposalDecisionDiagnosticDefinition | None:
    match = _CODE.search(str(code_or_message))
    if match is None:
        return None
    return PROPOSAL_DECISION_DIAGNOSTICS.get(match.group(1))

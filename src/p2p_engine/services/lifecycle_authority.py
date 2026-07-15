from __future__ import annotations

from dataclasses import dataclass


PROPOSAL_LIFECYCLE_AUTHORITY_POLICY_VERSION = 1


@dataclass(frozen=True)
class ProposalLifecycleAuthority:
    status: str
    committed: bool
    active_projection: bool
    reason: str


_POLICY = {
    "accepted": ProposalLifecycleAuthority("accepted", True, True, "unconditional_acceptance"),
    "accepted_with_changes": ProposalLifecycleAuthority(
        "accepted_with_changes", True, True, "conditional_acceptance"
    ),
    "split": ProposalLifecycleAuthority("split", True, False, "lineage_replaced_by_split_targets"),
    "merged_into_other": ProposalLifecycleAuthority(
        "merged_into_other", True, False, "lineage_replaced_by_merge_target"
    ),
    "superseded": ProposalLifecycleAuthority("superseded", True, False, "historical_superseded_authority"),
}


def proposal_lifecycle_authority(status: str) -> ProposalLifecycleAuthority:
    normalized = str(status or "unknown").strip().lower().replace("-", "_").replace(" ", "_")
    return _POLICY.get(
        normalized,
        ProposalLifecycleAuthority(normalized or "unknown", False, False, "not_committed"),
    )


def is_committed_proposal(status: str) -> bool:
    return proposal_lifecycle_authority(status).committed


def is_active_project_projection(status: str) -> bool:
    return proposal_lifecycle_authority(status).active_projection

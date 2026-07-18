from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from p2p_engine.core.decision_context import (
    AUTHORITY_POLICY_VERSION,
    Activation,
    Authority,
    Canonicality,
    Confidence,
    SourceClassification,
    SourceDocument,
    SourceKind,
)


@dataclass(frozen=True)
class LifecycleAuthority:
    proposal_authority: Authority
    proposal_activation: Activation
    decision_authority: Authority
    decision_activation: Activation


@dataclass(frozen=True)
class SourceAuthority:
    canonicality: Canonicality
    authority: Authority
    activation: Activation
    confidence: Confidence


_LIFECYCLE_RULES: Mapping[str, LifecycleAuthority] = {
    "accepted": LifecycleAuthority(
        Authority.ACCEPTED_PROPOSAL_CONTEXT,
        Activation.ACTIVE,
        Authority.ACCEPTED_DECISION,
        Activation.ACTIVE,
    ),
    "accepted_with_changes": LifecycleAuthority(
        Authority.ACCEPTED_PROPOSAL_CONTEXT,
        Activation.ACTIVE,
        Authority.CONDITIONALLY_ACCEPTED_DECISION,
        Activation.ACTIVE,
    ),
    "deferred": LifecycleAuthority(
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
        Authority.HISTORICAL_PROPOSAL,
        Activation.UNRESOLVED,
    ),
    "rejected": LifecycleAuthority(
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
    ),
    "withdrawn": LifecycleAuthority(
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
    ),
    "revoked": LifecycleAuthority(
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
    ),
    "reinstated": LifecycleAuthority(
        Authority.ACCEPTED_PROPOSAL_CONTEXT,
        Activation.ACTIVE,
        Authority.ACCEPTED_DECISION,
        Activation.ACTIVE,
    ),
    "unknown_legacy": LifecycleAuthority(
        Authority.HISTORICAL_PROPOSAL,
        Activation.UNRESOLVED,
        Authority.UNKNOWN,
        Activation.UNRESOLVED,
    ),
    "split": LifecycleAuthority(
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
    ),
    "merged_into_other": LifecycleAuthority(
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
    ),
    "superseded": LifecycleAuthority(
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
        Authority.HISTORICAL_PROPOSAL,
        Activation.HISTORICAL,
    ),
    "pending": LifecycleAuthority(
        Authority.DRAFT_PROPOSAL,
        Activation.EXPLORATORY,
        Authority.UNKNOWN,
        Activation.UNRESOLVED,
    ),
    "draft": LifecycleAuthority(
        Authority.DRAFT_PROPOSAL,
        Activation.EXPLORATORY,
        Authority.UNKNOWN,
        Activation.UNRESOLVED,
    ),
}


class AuthorityPolicy:
    version = AUTHORITY_POLICY_VERSION

    _valid_activations: Mapping[Authority, frozenset[Activation]] = {
        Authority.ACCEPTED_DECISION: frozenset({Activation.ACTIVE}),
        Authority.CONDITIONALLY_ACCEPTED_DECISION: frozenset({Activation.ACTIVE}),
        Authority.DECIDED_PROJECT_CHOICE: frozenset({Activation.ACTIVE}),
        Authority.EXPLICIT_DECISION_PRECEDENT: frozenset({Activation.ACTIVE}),
        Authority.PROJECT_DEFINITION_CONSTRAINT: frozenset({Activation.ACTIVE}),
        Authority.ACCEPTED_PROPOSAL_CONTEXT: frozenset({Activation.ACTIVE}),
        Authority.OWNER_CONFIRMED_EVIDENCE: frozenset({Activation.ACTIVE, Activation.HISTORICAL}),
        Authority.SYSTEM_STATE: frozenset({Activation.ACTIVE, Activation.INACTIVE, Activation.HISTORICAL}),
        Authority.DRAFT_PROPOSAL: frozenset({Activation.EXPLORATORY}),
        Authority.AGENT_PROPOSED_EVIDENCE: frozenset(
            {Activation.EXPLORATORY, Activation.INACTIVE, Activation.HISTORICAL}
        ),
        Authority.PROPOSAL_LOCAL_VOTE: frozenset(
            {Activation.EXPLORATORY, Activation.INACTIVE, Activation.HISTORICAL}
        ),
        Authority.HISTORICAL_PROPOSAL: frozenset(
            {Activation.HISTORICAL, Activation.UNRESOLVED}
        ),
        Authority.HEURISTIC_SIGNAL: frozenset({Activation.INACTIVE}),
        Authority.UNKNOWN: frozenset({Activation.UNRESOLVED, Activation.INACTIVE}),
    }

    def lifecycle(self, proposal_status: str, decision_outcome: str) -> LifecycleAuthority:
        outcome = decision_outcome or proposal_status
        return _LIFECYCLE_RULES.get(
            outcome,
            LifecycleAuthority(
                Authority.HISTORICAL_PROPOSAL,
                Activation.UNRESOLVED,
                Authority.UNKNOWN,
                Activation.UNRESOLVED,
            ),
        )

    def source_default(self, document: SourceDocument) -> SourceAuthority:
        if document.source_kind == SourceKind.DECISION_PRECEDENTS:
            return SourceAuthority(
                Canonicality.CANONICAL,
                Authority.EXPLICIT_DECISION_PRECEDENT,
                Activation.ACTIVE,
                Confidence.EXPLICIT,
            )
        if document.source_kind == SourceKind.PROJECT_DEFINITION:
            return SourceAuthority(
                Canonicality.CANONICAL,
                Authority.PROJECT_DEFINITION_CONSTRAINT,
                Activation.ACTIVE,
                Confidence.EXPLICIT,
            )
        if document.source_kind == SourceKind.VERTICAL_HEURISTIC:
            return SourceAuthority(
                Canonicality.DERIVED,
                Authority.HEURISTIC_SIGNAL,
                Activation.INACTIVE,
                Confidence.HEURISTIC,
            )
        if document.classification == SourceClassification.QUALITY_METADATA:
            return SourceAuthority(
                Canonicality.CANONICAL,
                Authority.SYSTEM_STATE,
                Activation.INACTIVE,
                Confidence.EXPLICIT,
            )
        if document.classification == SourceClassification.EXECUTION_METADATA:
            return SourceAuthority(
                Canonicality.CANONICAL,
                Authority.SYSTEM_STATE,
                Activation.ACTIVE,
                Confidence.EXPLICIT,
            )
        if document.classification == SourceClassification.GOVERNED_EVIDENCE:
            return SourceAuthority(
                Canonicality.GOVERNED_IMPORT,
                Authority.AGENT_PROPOSED_EVIDENCE,
                Activation.EXPLORATORY,
                Confidence.EXPLICIT,
            )
        return SourceAuthority(
            Canonicality.CANONICAL,
            Authority.SYSTEM_STATE,
            Activation.ACTIVE,
            Confidence.EXPLICIT,
        )

    def validate(self, value: SourceAuthority) -> SourceAuthority:
        allowed = self._valid_activations.get(value.authority, frozenset())
        if value.activation not in allowed:
            raise ValueError(
                f"Unsupported authority/activation combination: "
                f"{value.authority.value}/{value.activation.value}"
            )
        if value.confidence == Confidence.HEURISTIC and value.authority != Authority.HEURISTIC_SIGNAL:
            raise ValueError("Heuristic confidence requires heuristic authority.")
        return value


class SourceMetadataResolver:
    def __init__(self, artifact_state_by_owner: Mapping[str, SourceDocument]) -> None:
        self.confirmations: dict[tuple[str, str], str] = {}
        for owner_id, document in artifact_state_by_owner.items():
            payload = document.frontmatter.get("proposal_artifacts")
            if not isinstance(payload, Mapping):
                continue
            artifacts = payload.get("artifacts")
            if not isinstance(artifacts, tuple):
                continue
            for item in artifacts:
                if not isinstance(item, Mapping):
                    continue
                filename = str(item.get("filename") or "").strip()
                confirmation = str(item.get("confirmation") or "").strip()
                if filename:
                    self.confirmations[(owner_id, filename)] = confirmation

    def resolve(self, document: SourceDocument, default: SourceAuthority) -> SourceAuthority:
        tracked_semantic_source = document.source_kind == SourceKind.VERTICAL_COVERAGE
        if document.classification != SourceClassification.GOVERNED_EVIDENCE and not tracked_semantic_source:
            return default
        filename = document.path.rsplit("/", 1)[-1]
        confirmation = self.confirmations.get((document.owner_id, filename), "")
        canonicality = (
            Canonicality.CANONICAL
            if tracked_semantic_source
            else Canonicality.GOVERNED_IMPORT
        )
        if confirmation == "owner_confirmed":
            return SourceAuthority(
                canonicality,
                Authority.OWNER_CONFIRMED_EVIDENCE,
                Activation.ACTIVE,
                Confidence.EXPLICIT,
            )
        if confirmation == "system":
            return SourceAuthority(
                canonicality,
                Authority.SYSTEM_STATE,
                Activation.ACTIVE,
                Confidence.EXPLICIT,
            )
        if confirmation == "agent_proposed":
            return SourceAuthority(
                canonicality,
                Authority.AGENT_PROPOSED_EVIDENCE,
                Activation.EXPLORATORY,
                Confidence.EXPLICIT,
            )
        return default


def lifecycle_rules() -> Mapping[str, LifecycleAuthority]:
    return _LIFECYCLE_RULES


def lifecycle_state_tokens() -> tuple[str, ...]:
    return tuple(sorted(_LIFECYCLE_RULES))

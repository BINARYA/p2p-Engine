from __future__ import annotations

from pathlib import Path

from p2p_engine.core.authority import (
    LOCAL_AUTHORITY_POLICY_VERSION,
    AuthorityBasis,
    AuthorityClaim,
    AuthorityContext,
    AuthorityIdentity,
    AuthorityIdentityKind,
    AuthorityMode,
    AuthorityProjectBinding,
    authority_evidence_from_context,
)
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAffectedDecision,
    ProposalDecisionAuthorityEvidence,
    ProposalDecisionCondition,
    ProposalDecisionEffectiveState,
    ProposalDecisionEvent,
    ProposalDecisionEventType,
    ProposalDecisionImpactBinding,
    ProposalDecisionLedger,
    ProposalDecisionLineage,
    ProposalDecisionReadinessBinding,
)
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    decision_semantic_sha256,
    operation_key,
    proposal_semantic_sha256,
    render_proposal_projection,
)
from p2p_engine.storage.filesystem import P2PWorkspace


def initialized_workspace(root: Path, *, owner: str = "owner") -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Decision Event Fixture", owner=owner)
    return workspace


def proposal_markdown(proposal_id: str = "PROP-001", *, status: str = "draft") -> str:
    return (
        f"# {proposal_id} - Fixture Proposal\n\n"
        "## Status\n\n"
        f"`{status}`\n\n"
        "## Problem\n\n"
        "A governed problem.\n\n"
        "## Context\n\n"
        "A stable context.\n\n"
        "## Goals\n\n"
        "- Preserve decisions.\n\n"
        "## Non-Goals\n\n"
        "- Rewrite history.\n\n"
        "## Proposal\n\n"
        "Use an append-only ledger.\n\n"
        "## Acceptance Criteria\n\n"
        "- History remains queryable.\n\n"
        "## Decision\n\n"
        "Pending.\n"
    )


def authority(owner: str = "owner") -> ProposalDecisionAuthorityEvidence:
    context = AuthorityContext(
        mode=AuthorityMode.local_policy,
        project_authority=AuthorityProjectBinding(
            authority_id="p2p-test-project-authority",
            generation=1,
            local_policy_version=LOCAL_AUTHORITY_POLICY_VERSION,
        ),
        subject=AuthorityIdentity(owner, AuthorityIdentityKind.person),
        executor=AuthorityIdentity(owner, AuthorityIdentityKind.person),
        authorization_decision_id="p2p-test-authority-decision",
        claims=(
            AuthorityClaim(
                capability="proposal.decide",
                basis=AuthorityBasis.local_policy,
            ),
        ),
    )
    return authority_evidence_from_context(
        context,
        channel="test_fixture",
        permission_policy_sha256="a" * 64,
    )


def append_event(
    ledger: ProposalDecisionLedger,
    *,
    event_type: ProposalDecisionEventType,
    effective_state: ProposalDecisionEffectiveState | None = None,
    decided_on: str = "2026-07-17",
    reason: str = "Recorded by fixture.",
    conditions: tuple[ProposalDecisionCondition, ...] = (),
    lineage: ProposalDecisionLineage = ProposalDecisionLineage(),
    affected: ProposalDecisionEvent | None = None,
    impact_required: bool = False,
    proposal_text_override: str = "",
    authority_evidence: ProposalDecisionAuthorityEvidence | None = None,
) -> tuple[ProposalDecisionLedger, ProposalDecisionEvent]:
    codec = ProposalDecisionLedgerCodec()
    proposal_text = proposal_text_override or proposal_markdown(ledger.proposal_id)
    proposal_sha = proposal_semantic_sha256(ledger.proposal_id, proposal_text)
    state = effective_state or ProposalDecisionEffectiveState(event_type.value)
    decision_sha = (
        affected.decision_semantic_sha256
        if affected is not None
        else decision_semantic_sha256(
            proposal_sha256=proposal_sha,
            outcome=state,
            rationale=reason,
            conditions=conditions,
        )
    )
    semantics = {
        "proposal_id": ledger.proposal_id,
        "event_type": event_type.value,
        "reason": reason,
        "decided_on": decided_on,
        "lineage": lineage.to_dict(),
    }
    key = operation_key(semantics, ledger.head_event_id)
    event = codec.build_event(
        proposal_id=ledger.proposal_id,
        event_type=event_type,
        effective_state=state,
        rationale=reason,
        conditions=conditions,
        decided_on=decided_on,
        authority=authority_evidence or authority(),
        predecessor=ledger.events[-1] if ledger.events else None,
        proposal_semantic_sha256=proposal_sha,
        decision_semantic_sha256=decision_sha,
        affected_decision=ProposalDecisionAffectedDecision(
            event_id=affected.event_id if affected else None,
            decision_semantic_sha256=(
                affected.decision_semantic_sha256 if affected else None
            ),
            revocation_event_id=(
                ledger.events[-1].event_id
                if event_type == ProposalDecisionEventType.reinstated
                and ledger.events
                else None
            ),
        ),
        lineage=lineage,
        impact=ProposalDecisionImpactBinding(
            required=impact_required,
            preview_token="b" * 64 if impact_required else None,
            source_fingerprint_sha256="c" * 64 if impact_required else None,
            total_count=1 if impact_required else 0,
        ),
        readiness=ProposalDecisionReadinessBinding(),
        preview_token="d" * 64,
        request_fingerprint_sha256="e" * 64,
        operation_key=key,
    )
    return codec.append(ledger, event), event


def ledger_with_acceptance(
    proposal_id: str = "PROP-001",
) -> tuple[ProposalDecisionLedger, ProposalDecisionEvent]:
    return append_event(
        ProposalDecisionLedgerCodec().empty(proposal_id),
        event_type=ProposalDecisionEventType.accepted,
    )


def write_current_proposal(
    proposal_dir: Path,
    ledger: ProposalDecisionLedger,
    *,
    proposal_text_override: str = "",
) -> None:
    codec = ProposalDecisionLedgerCodec()
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_text = proposal_text_override or proposal_markdown(ledger.proposal_id)
    (proposal_dir / "proposal.md").write_text(
        render_proposal_projection(proposal_text, ledger.effective_state),
        encoding="utf-8",
    )
    (proposal_dir / "decision-events.yml").write_bytes(codec.dumps(ledger))


def record_decision(
    workspace: P2PWorkspace,
    proposal_id: str,
    outcome: DecisionOutcome,
    reason: str,
    approver: str,
    **values,
):
    event_type = ProposalDecisionEventType(outcome.value)
    conditions = values.pop("conditions", ())
    if (
        event_type == ProposalDecisionEventType.accepted_with_changes
        and not conditions
    ):
        conditions = (
            ProposalDecisionCondition(
                condition_id="COND-TEST-001",
                text="Complete the condition recorded by the test fixture.",
            ),
        )
    request = workspace._proposal_decision_service().request(
        proposal_id=proposal_id,
        event_type=event_type,
        reason=reason,
        actor_id=approver,
        conditions=tuple(conditions),
        **values,
    )
    preview = workspace.preview_proposal_decision(request)
    return workspace.apply_proposal_decision(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

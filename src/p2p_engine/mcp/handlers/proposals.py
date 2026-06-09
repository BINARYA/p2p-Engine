from __future__ import annotations

from typing import Any

from p2p_engine.core.contribution import ContributionType
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.proposal_artifact_state import (
    ProposalArtifactExpectation,
    ProposalArtifactRiskFlag,
    ProposalArtifactStatus,
)
from p2p_engine.core.proposal_questions import ProposalQuestionPriority
from p2p_engine.mcp.consent_audit import (
    consume_consent_with_audit,
    mark_consent_error_on_head_change,
    safe_head,
)
from p2p_engine.mcp.handlers.common import optional_string, optional_string_list, required, to_jsonable
from p2p_engine.storage.filesystem import P2PWorkspace


def handle_proposal_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if name == "p2p_proposal_create":
        proposal = workspace.create_proposal_with_details(
            title=required(arguments, "title"),
            problem=optional_string(arguments, "problem"),
            context=optional_string(arguments, "context"),
            goals=optional_string_list(arguments, "goals"),
            non_goals=optional_string_list(arguments, "non_goals"),
            proposal=optional_string(arguments, "proposal"),
            acceptance_criteria=optional_string_list(arguments, "acceptance_criteria"),
        )
        return {
            "proposal": to_jsonable(proposal),
            "governance": {
                "status": "draft",
                "owner_decision_required": True,
                "decision_made": False,
            },
        }
    if name == "p2p_proposal_update":
        proposal_id = required(arguments, "proposal_id")
        path = workspace.update_proposal(
            proposal_id=proposal_id,
            problem=optional_string(arguments, "problem"),
            context=optional_string(arguments, "context"),
            goals=optional_string_list(arguments, "goals"),
            non_goals=optional_string_list(arguments, "non_goals"),
            proposal=optional_string(arguments, "proposal"),
            acceptance_criteria=optional_string_list(arguments, "acceptance_criteria"),
        )
        return {
            "updated": to_jsonable(path),
            "proposal": to_jsonable(workspace.show_proposal(proposal_id)),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
            },
        }
    if name == "p2p_proposal_contribution_add":
        proposal_id = required(arguments, "proposal_id")
        contribution = workspace.add_contribution(
            proposal_id=proposal_id,
            contribution_type=_contribution_type(arguments),
            text=required(arguments, "text"),
            relevance_hint=str(arguments.get("relevance") or "medium"),
            author=str(arguments.get("author") or "mcp"),
        )
        return {
            "contribution": to_jsonable(contribution),
            "proposal": to_jsonable(workspace.show_proposal(proposal_id)),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
            },
        }
    if name == "p2p_proposal_contribution_list":
        return {"contributions": to_jsonable(workspace.list_contributions(required(arguments, "proposal_id")))}
    if name == "p2p_proposal_list":
        status = arguments.get("status")
        return {"proposals": to_jsonable(workspace.proposal_summaries(str(status) if status else None))}
    if name == "p2p_proposal_show":
        return {"proposal": to_jsonable(workspace.show_proposal(required(arguments, "proposal_id")))}
    if name == "p2p_proposal_readiness_get":
        return {"readiness": to_jsonable(workspace.read_proposal_readiness(required(arguments, "proposal_id")))}
    if name == "p2p_proposal_readiness_init":
        readiness = workspace.initialize_proposal_readiness(required(arguments, "proposal_id"))
        return {
            "readiness": to_jsonable(readiness),
            "governance": {
                "owner_decision_required": False,
                "decision_made": False,
                "override_applied": False,
            },
        }
    if name == "p2p_proposal_readiness_refresh":
        readiness = workspace.refresh_proposal_readiness(required(arguments, "proposal_id"))
        return {
            "readiness": to_jsonable(readiness),
            "governance": {
                "owner_decision_required": False,
                "decision_made": False,
                "override_applied": False,
            },
        }
    if name == "p2p_proposal_readiness_assess":
        readiness = workspace.assess_proposal_readiness(required(arguments, "proposal_id"))
        return {
            "readiness": to_jsonable(readiness),
            "governance": {
                "owner_decision_required": False,
                "decision_made": False,
                "override_applied": False,
            },
        }
    if name == "p2p_proposal_readiness_explain":
        readiness = workspace.read_proposal_readiness(required(arguments, "proposal_id"))
        return {
            "readiness": to_jsonable(readiness),
            "explanation": {
                "failed_gates": readiness.failed_gates,
                "missing": readiness.missing,
                "suggested_next": readiness.suggested_next,
            },
        }
    if name == "p2p_proposal_readiness_list_gaps":
        readiness = workspace.read_proposal_readiness(required(arguments, "proposal_id"))
        return {
            "gaps": {
                "proposal_id": readiness.proposal_id,
                "failed_gates": readiness.failed_gates,
                "missing": readiness.missing,
                "suggested_next": readiness.suggested_next,
            }
        }
    if name == "p2p_proposal_readiness_review":
        return {"review": to_jsonable(workspace.review_proposal_readiness(required(arguments, "proposal_id")))}
    if name == "p2p_proposal_questions_status":
        return {"questions": to_jsonable(workspace.read_proposal_questions(required(arguments, "proposal_id")))}
    if name == "p2p_proposal_questions_init":
        return {
            "questions": to_jsonable(
                workspace.initialize_proposal_questions(
                    required(arguments, "proposal_id"),
                    actor=str(arguments.get("actor") or "mcp"),
                )
            ),
            "governance": {"owner_decision_required": False, "decision_made": False},
        }
    if name == "p2p_proposal_questions_add":
        priority = ProposalQuestionPriority(str(arguments.get("priority") or ProposalQuestionPriority.medium.value))
        return {
            "question": to_jsonable(
                workspace.add_proposal_question(
                    required(arguments, "proposal_id"),
                    gap=required(arguments, "gap"),
                    question=required(arguments, "question"),
                    priority=priority,
                    rationale=optional_string(arguments, "rationale") or "",
                    actor=str(arguments.get("actor") or "mcp"),
                )
            ),
            "governance": {"owner_decision_required": False, "decision_made": False},
        }
    if name == "p2p_proposal_questions_answer":
        return {
            "question": to_jsonable(
                workspace.answer_proposal_question(
                    required(arguments, "proposal_id"),
                    required(arguments, "question_id"),
                    required(arguments, "answer"),
                    source=str(arguments.get("source") or "owner"),
                    actor=str(arguments.get("actor") or "mcp"),
                )
            ),
            "governance": {"owner_decision_required": False, "decision_made": False},
        }
    if name == "p2p_proposal_questions_next":
        return {"question": to_jsonable(workspace.next_proposal_question(required(arguments, "proposal_id")))}
    if name == "p2p_proposal_questions_apply":
        return {
            "apply": to_jsonable(
                workspace.apply_proposal_question_answers(
                    required(arguments, "proposal_id"),
                    actor=str(arguments.get("actor") or "mcp"),
                )
            ),
            "governance": {"owner_decision_required": False, "decision_made": False},
        }
    if name == "p2p_proposal_artifact_status":
        return {"artifact_state": to_jsonable(workspace.read_proposal_artifacts(required(arguments, "proposal_id")))}
    if name == "p2p_proposal_artifact_init":
        return {
            "artifact_state": to_jsonable(
                workspace.initialize_proposal_artifacts(
                    required(arguments, "proposal_id"),
                    actor=str(arguments.get("actor") or "mcp"),
                )
            ),
            "governance": {"owner_decision_required": False, "decision_made": False},
        }
    if name == "p2p_proposal_artifact_set":
        expectation = _artifact_expectation(arguments)
        status = _artifact_status(arguments)
        risk_flags = _artifact_risk_flags(arguments)
        return {
            "artifact_operation": to_jsonable(
                workspace.set_proposal_artifact_state(
                    required(arguments, "proposal_id"),
                    required(arguments, "artifact_id"),
                    expectation=expectation,
                    status=status,
                    reason=optional_string(arguments, "reason") or "",
                    actor=str(arguments.get("actor") or "mcp"),
                    source=str(arguments.get("source") or "mcp"),
                    risk_flags=risk_flags,
                )
            ),
            "governance": {"owner_decision_required": False, "decision_made": False},
        }
    if name == "p2p_proposal_artifact_confirm":
        return {
            "artifact_operation": to_jsonable(
                workspace.confirm_proposal_artifact_state(
                    required(arguments, "proposal_id"),
                    required(arguments, "artifact_id"),
                    actor=str(arguments.get("actor") or "owner"),
                )
            ),
            "governance": {"owner_decision_required": False, "decision_made": False},
        }
    if name == "p2p_proposal_artifact_mark_legacy":
        return {
            "artifact_state": to_jsonable(
                workspace.mark_proposal_artifacts_legacy(
                    required(arguments, "proposal_id"),
                    reason=optional_string(arguments, "reason") or "Proposal predates artifact-aware state.",
                    actor=str(arguments.get("actor") or "mcp"),
                )
            ),
            "governance": {"owner_decision_required": False, "decision_made": False},
        }
    if name == "p2p_proposal_accept":
        return _proposal_decision_tool(workspace, arguments, "proposal_accept", DecisionOutcome.accepted)
    if name == "p2p_proposal_reject":
        return _proposal_decision_tool(workspace, arguments, "proposal_reject", DecisionOutcome.rejected)
    if name == "p2p_proposal_defer":
        return _proposal_decision_tool(workspace, arguments, "proposal_defer", DecisionOutcome.deferred)
    if name == "p2p_proposal_branch_scan":
        return {"proposal_branch_scan": to_jsonable(workspace.scan_proposal_branches())}
    return None


def _contribution_type(arguments: dict[str, Any]) -> ContributionType:
    value = str(arguments.get("type") or ContributionType.suggestion.value)
    try:
        return ContributionType(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ContributionType)
        raise ValueError(f"Invalid contribution type: {value}. Allowed: {allowed}") from exc


def _artifact_expectation(arguments: dict[str, Any]) -> ProposalArtifactExpectation | None:
    value = optional_string(arguments, "expectation")
    if value is None:
        return None
    try:
        return ProposalArtifactExpectation(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ProposalArtifactExpectation)
        raise ValueError(f"Invalid artifact expectation: {value}. Allowed: {allowed}") from exc


def _artifact_status(arguments: dict[str, Any]) -> ProposalArtifactStatus | None:
    value = optional_string(arguments, "status")
    if value is None:
        return None
    try:
        return ProposalArtifactStatus(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ProposalArtifactStatus)
        raise ValueError(f"Invalid artifact status: {value}. Allowed: {allowed}") from exc


def _artifact_risk_flags(arguments: dict[str, Any]) -> list[ProposalArtifactRiskFlag] | None:
    values = arguments.get("risk_flags")
    if values is None:
        return None
    if not isinstance(values, list):
        raise ValueError("Expected list argument: risk_flags")
    flags: list[ProposalArtifactRiskFlag] = []
    for value in values:
        try:
            flags.append(ProposalArtifactRiskFlag(str(value)))
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ProposalArtifactRiskFlag)
            raise ValueError(f"Invalid artifact risk flag: {value}. Allowed: {allowed}") from exc
    return flags


def _proposal_decision_tool(
    workspace: P2PWorkspace,
    arguments: dict[str, Any],
    operation: str,
    outcome: DecisionOutcome,
) -> dict[str, object]:
    proposal_id = required(arguments, "proposal_id")
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    reason = required(arguments, "reason")
    workspace.consent_validate(
        consent_id,
        operation=operation,
        target=proposal_id,
        actor_id=actor_id,
    )
    before_head = safe_head(workspace)
    try:
        decision = workspace.record_decision(
            proposal_id=proposal_id,
            outcome=outcome,
            reason=reason,
            approver=actor_id,
        )
    except ValueError as exc:
        mark_consent_error_on_head_change(
            workspace,
            consent_id,
            before_head,
            str(exc),
            operation,
            proposal_id,
            actor_id,
        )
        raise
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result={
            "operation": operation,
            "target": proposal_id,
            "actor_id": actor_id,
            "decision_outcome": decision.outcome.value,
        },
    )
    return {
        "proposal_decision": {
            "proposal_id": decision.proposal_id,
            "outcome": decision.outcome.value,
            "reason": decision.reason,
            "approver": decision.approver,
            "decided_on": decision.decided_on.isoformat(),
        },
        "consent": to_jsonable(consumed),
        "governance": {
            "owner_decision_required": True,
            "decision_made": True,
            "decision_outcome": decision.outcome.value,
            "merge_performed": False,
        },
    }

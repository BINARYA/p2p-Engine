from __future__ import annotations

from pathlib import Path
from typing import Any

from p2p_engine.core.contribution import ContributionType, parse_contribution_type
from p2p_engine.core.proposal_decision_events import ProposalDecisionEventType
from p2p_engine.core.proposal_artifact_state import (
    ProposalArtifactExpectation,
    ProposalArtifactRiskFlag,
    ProposalArtifactStatus,
)
from p2p_engine.core.proposal_questions import ProposalQuestionPriority
from p2p_engine.mcp.handlers.common import optional_string, optional_string_list, required, to_jsonable
from p2p_engine.mcp.handlers.proposal_decisions import (
    convenience_preview,
    handle_proposal_decision_tool,
)
from p2p_engine.storage.filesystem import P2PWorkspace


ARTIFACT_IMPORT_KINDS = {
    "p2p_explore_import": "explore",
    "p2p_impact_import": "impact",
    "p2p_clarify_import": "clarify",
    "p2p_synthesize_import": "synthesize",
    "p2p_plan_import": "plan",
    "p2p_tasks_import": "tasks",
}


def handle_proposal_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    decision_result = handle_proposal_decision_tool(
        workspace,
        name,
        arguments,
    )
    if decision_result is not None:
        return decision_result
    if name in ARTIFACT_IMPORT_KINDS:
        return _proposal_artifact_import_tool(workspace, name, arguments)
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
        proposal_id = required(arguments, "proposal_id")
        return {
            "contributions": to_jsonable(workspace.list_contributions(proposal_id)),
            "contribution_list": to_jsonable(
                workspace.proposal_contribution_list_contract(
                    proposal_id,
                    contribution_type=_optional_contribution_type(arguments),
                    limit=_optional_int(arguments, "limit", default=50),
                    offset=_optional_int(arguments, "offset", default=0),
                )
            ),
        }
    if name == "p2p_proposal_list":
        status = arguments.get("status")
        decision_state = arguments.get("decision_state")
        return {
            "proposals": to_jsonable(workspace.proposal_summaries(str(status) if status else None)),
            "proposal_list": to_jsonable(
                workspace.proposal_list_contract(
                    status=str(status) if status else None,
                    decision_state=str(decision_state) if decision_state else None,
                    limit=_optional_int(arguments, "limit", default=50),
                    offset=_optional_int(arguments, "offset", default=0),
                )
            ),
        }
    if name == "p2p_proposal_show":
        proposal_id = required(arguments, "proposal_id")
        result: dict[str, object] = {
            "proposal": to_jsonable(workspace.show_proposal(proposal_id)),
            "proposal_detail": to_jsonable(
                workspace.proposal_detail_contract(
                    proposal_id,
                    contribution_limit=_optional_int(arguments, "contribution_limit", default=50),
                )
            ),
        }
        if _optional_bool(arguments, "full"):
            result["proposal_view"] = to_jsonable(workspace.proposal_full_view(proposal_id))
        return result
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
                "owner_question_state": to_jsonable(readiness.owner_question_state),
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
                "owner_question_state": to_jsonable(readiness.owner_question_state),
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
        proposal_id = required(arguments, "proposal_id")
        return {
            "artifact_state": to_jsonable(workspace.read_proposal_artifacts(proposal_id)),
            "artifact_status": to_jsonable(workspace.proposal_artifact_catalog(proposal_id)),
        }
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
    if name == "p2p_proposal_accept":
        return convenience_preview(
            workspace,
            arguments,
            event_type=ProposalDecisionEventType.accepted,
        )
    if name == "p2p_proposal_reject":
        return convenience_preview(
            workspace,
            arguments,
            event_type=ProposalDecisionEventType.rejected,
        )
    if name == "p2p_proposal_defer":
        return convenience_preview(
            workspace,
            arguments,
            event_type=ProposalDecisionEventType.deferred,
        )
    if name == "p2p_proposal_branch_scan":
        return {"proposal_branch_scan": to_jsonable(workspace.scan_proposal_branches())}
    return None


def _proposal_artifact_import_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object]:
    raw_artifacts = arguments.get("artifacts")
    artifacts: dict[str, str] | None = None
    if raw_artifacts is not None:
        if not isinstance(raw_artifacts, dict):
            raise ValueError("Expected object argument: artifacts")
        artifacts = {str(filename): str(content) for filename, content in raw_artifacts.items()}
    source_value = optional_string(arguments, "source")
    content = str(arguments["content"]) if "content" in arguments and arguments["content"] is not None else None
    source = _artifact_import_source_path(workspace, source_value)
    result = workspace.import_proposal_artifact_content(
        required(arguments, "proposal_id"),
        ARTIFACT_IMPORT_KINDS[name],
        source=source,
        content=content,
        artifacts=artifacts,
    )
    return {
        "artifact_import": to_jsonable(result),
        "governance": {
            "owner_decision_required": False,
            "decision_made": False,
        },
    }


def _artifact_import_source_path(workspace: P2PWorkspace, source_value: str | None) -> Path | None:
    if source_value is None:
        return None
    source = Path(source_value)
    if source.is_absolute():
        return source
    return workspace.root / source


def _contribution_type(arguments: dict[str, Any]) -> ContributionType:
    return parse_contribution_type(arguments.get("type"))


def _optional_contribution_type(arguments: dict[str, Any]) -> ContributionType | None:
    value = optional_string(arguments, "type")
    if value is None:
        return None
    return parse_contribution_type(value)


def _optional_bool(arguments: dict[str, Any], name: str) -> bool:
    value = arguments.get(name)
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _optional_int(arguments: dict[str, Any], name: str, *, default: int) -> int:
    value = arguments.get(name)
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"Expected integer argument: {name}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected integer argument: {name}") from exc


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

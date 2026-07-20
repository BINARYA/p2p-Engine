from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.services.changes import CHANGE_TERMINAL_STATUSES
from p2p_engine.services.lifecycle_authority import is_active_project_projection


@dataclass(frozen=True)
class ProjectAssessment:
    path: Path
    generated_on: str
    assessment_type: str
    completion_score: int
    completion_status: str
    confidence: str
    factors: list[dict[str, object]]
    gaps: list[str]
    suggested_actions: list[str]
    maturity_status: str
    maturity_score: int | None
    basis: dict[str, object] | None = None
    freshness: dict[str, object] | None = None


class ProjectAssessmentService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        validate: Callable[[], object],
        registry_status: Callable[[], object],
        proposal_summaries: Callable[[], list[object]],
        choice_statuses: Callable[[], list[object]],
        change_set_statuses: Callable[[], list[object]],
        work_summaries: Callable[[], list[object]],
        project_state_status: Callable[..., object],
        next_actions: Callable[[int], list[object]],
        maturity_exists: Callable[[], bool],
        show_maturity: Callable[[], object],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.validate = validate
        self.registry_status = registry_status
        self.proposal_summaries = proposal_summaries
        self.choice_statuses = choice_statuses
        self.change_set_statuses = change_set_statuses
        self.work_summaries = work_summaries
        self.project_state_status = project_state_status
        self.next_actions = next_actions
        self.maturity_exists = maturity_exists
        self.show_maturity = show_maturity

    def refresh(self) -> ProjectAssessment:
        assessment = self.compute()
        path = self.p2p_dir / "project" / "assessment.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(project_assessment_payload(assessment)), encoding="utf-8")
        return assessment

    def show(self) -> ProjectAssessment:
        path = self.p2p_dir / "project" / "assessment.yml"
        if not path.exists():
            raise ValueError("Project assessment not found. Run `p2p assess refresh` first.")
        data = _read_yaml_mapping(path, default={})
        completion = data.get("completion", {})
        maturity = data.get("maturity", {})
        if not isinstance(completion, dict):
            completion = {}
        if not isinstance(maturity, dict):
            maturity = {}
        factors = data.get("factors", [])
        gaps = data.get("gaps", [])
        suggested_actions = data.get("suggested_actions", [])
        return ProjectAssessment(
            path=path.relative_to(self.root),
            generated_on=str(data.get("generated_on") or ""),
            assessment_type=str(data.get("assessment_type") or "deterministic_readiness"),
            completion_score=int(completion.get("score") or 0),
            completion_status=str(completion.get("status") or "unknown"),
            confidence=str(completion.get("confidence") or "unknown"),
            factors=[item for item in factors if isinstance(item, dict)] if isinstance(factors, list) else [],
            gaps=[str(item) for item in gaps] if isinstance(gaps, list) else [],
            suggested_actions=[str(item) for item in suggested_actions] if isinstance(suggested_actions, list) else [],
            maturity_status=str(maturity.get("status") or "not_assessed"),
            maturity_score=maturity.get("score") if isinstance(maturity.get("score"), int) else None,
            basis=data.get("basis") if isinstance(data.get("basis"), dict) else {"completion": "legacy_deterministic_readiness", "maturity": "heuristic_keyword_rubric"},
            freshness=data.get("freshness") if isinstance(data.get("freshness"), dict) else None,
        )

    def compute(self) -> ProjectAssessment:
        validation = self.validate()
        registry_status = self.registry_status()
        proposals = self.proposal_summaries()
        choices = self.choice_statuses()
        changes = self.change_set_statuses()
        works = self.work_summaries()
        next_actions = self.next_actions(3)
        project_status = self.project_state_status(
            next_actions_snapshot=next_actions,
        )

        draft_proposals = [proposal for proposal in proposals if getattr(proposal, "status", None) == "draft"]
        accepted_proposals = [
            proposal for proposal in proposals
            if is_active_project_projection(str(getattr(proposal, "status", "")))
        ]
        open_choices = [
            choice
            for choice in choices
            if getattr(choice, "status", None) in {"open", "draft", "pending"} and not getattr(choice, "selected_option", None)
        ]
        active_changes = [
            change
            for change in changes
            if getattr(change, "status", None) not in CHANGE_TERMINAL_STATUSES
        ]
        blocked_changes = [change for change in changes if getattr(change, "status", None) == "blocked"]
        terminal_work = {"accepted", "finalized", "cleaned", "retired", "completed", "cancelled", "superseded"}
        active_work = [work for work in works if getattr(work, "status", None) not in terminal_work]

        factors: list[dict[str, object]] = []
        gaps: list[str] = []
        suggested_actions = [str(getattr(action, "command", "")) for action in next_actions if getattr(action, "command", "")]

        def factor(
            factor_id: str,
            label: str,
            value: int | bool,
            impact: int,
            reason: str,
            gap: str | None = None,
        ) -> None:
            factors.append(
                {
                    "id": factor_id,
                    "label": label,
                    "value": value,
                    "impact": impact,
                    "reason": reason,
                }
            )
            if gap and impact < 0:
                gaps.append(gap)

        validation_errors = int(getattr(validation, "errors", 0))
        validation_warnings = int(getattr(validation, "warnings", 0))
        registries_stale = bool(getattr(registry_status, "stale", False))

        factor(
            "validation_errors",
            "Validation errors",
            validation_errors,
            -min(validation_errors * 30, 60),
            "Validation errors make project state unreliable.",
            "Resolve validation errors with `p2p validate`.",
        )
        factor(
            "validation_warnings",
            "Validation warnings",
            validation_warnings,
            -min(validation_warnings * 5, 20),
            "Validation warnings indicate recoverable project-state issues.",
            "Review validation warnings with `p2p validate`.",
        )
        factor(
            "stale_registries",
            "Registry freshness",
            registries_stale,
            -10 if registries_stale else 0,
            "Fresh registries are required for reliable assessment.",
            "Refresh registries with `p2p registry refresh`.",
        )
        factor(
            "draft_proposals",
            "Draft proposals",
            len(draft_proposals),
            -min(len(draft_proposals) * 4, 20),
            "Draft proposals still need owner review or refinement.",
            "Review draft proposals before treating project direction as settled.",
        )
        factor(
            "accepted_proposals",
            "Accepted proposals",
            len(accepted_proposals),
            0 if accepted_proposals else -15,
            "Accepted proposals define committed project direction.",
            "Accept at least one proposal when the project direction is clear.",
        )
        factor(
            "open_choices",
            "Open choices",
            len(open_choices),
            -min(len(open_choices) * 10, 30),
            "Open choices represent unresolved alternatives.",
            "Resolve or document open choices.",
        )
        factor(
            "active_changes",
            "Active Change Sets",
            len(active_changes),
            -min(len(active_changes) * 8, 24),
            "Active Change Sets still need lifecycle progress.",
            "Continue or complete active Change Sets.",
        )
        factor(
            "blocked_changes",
            "Blocked Change Sets",
            len(blocked_changes),
            -min(len(blocked_changes) * 12, 36),
            "Blocked Change Sets prevent implementation readiness.",
            "Resolve blockers before implementation.",
        )
        factor(
            "active_work",
            "Active Work items",
            len(active_work),
            -min(len(active_work) * 5, 20),
            "Active Work items still need review, acceptance, or cleanup.",
            "Finish or retire active Work items.",
        )
        factor(
            "operational_brief",
            "Operational brief",
            bool(getattr(project_status, "operational_brief_available", False)),
            0 if getattr(project_status, "operational_brief_available", False) else -5,
            "An operational brief helps agents and owners understand current state.",
            "Refresh/import an operational brief.",
        )

        score = max(0, min(100, 100 + sum(int(item["impact"]) for item in factors)))
        if validation_errors:
            status = "blocked"
        elif not proposals:
            status = "not_started"
        elif score >= 85:
            status = "ready"
        elif score >= 60:
            status = "needs_review"
        else:
            status = "at_risk"

        if validation_errors or registries_stale:
            confidence = "low" if validation_errors else "medium"
        elif validation_warnings:
            confidence = "medium"
        else:
            confidence = "high"

        maturity_status = "not_assessed"
        maturity_score = None
        if self.maturity_exists():
            maturity = self.show_maturity()
            maturity_status = str(getattr(maturity, "status", "not_assessed"))
            raw_score = getattr(maturity, "score", None)
            maturity_score = raw_score if isinstance(raw_score, int) else None

        return ProjectAssessment(
            path=(self.p2p_dir / "project" / "assessment.yml").relative_to(self.root),
            generated_on=date.today().isoformat(),
            assessment_type="deterministic_readiness",
            completion_score=score,
            completion_status=status,
            confidence=confidence,
            factors=factors,
            gaps=gaps,
            suggested_actions=suggested_actions,
            maturity_status=maturity_status,
            maturity_score=maturity_score,
            basis={
                "completion": "legacy_deterministic_readiness",
                "maturity": "heuristic_keyword_rubric",
                "authoritative_project_definition": False,
            },
        )


def project_assessment_payload(assessment: ProjectAssessment) -> dict[str, object]:
    return {
        "generated_on": assessment.generated_on,
        "assessment_type": assessment.assessment_type,
        "completion": {
            "score": assessment.completion_score,
            "status": assessment.completion_status,
            "confidence": assessment.confidence,
        },
        "maturity": {
            "status": assessment.maturity_status,
            "score": assessment.maturity_score,
        },
        "factors": assessment.factors,
        "gaps": assessment.gaps,
        "suggested_actions": assessment.suggested_actions,
        "basis": assessment.basis or {},
        "freshness": assessment.freshness or {"status": "not_assessed"},
    }

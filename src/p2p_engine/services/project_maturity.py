from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Callable, Protocol

import yaml

from p2p_engine.foundation.files import (
    read_yaml_mapping as _foundation_read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.services.lifecycle_authority import is_active_project_projection

PROJECT_RUBRIC_STARTERS = {"generic", "empty"}

class _ProposalSummaryLike(Protocol):
    proposal_id: str
    title: str
    status: str


class _ChangeStatusLike(Protocol):
    change_id: str
    title: str
    status: str


@dataclass(frozen=True)
class ProjectRubrics:
    path: Path
    structure_source: str
    status: str
    template: str | None
    criteria: list[dict[str, object]]
    selected_scope: dict[str, object] | None = None


@dataclass(frozen=True)
class ProjectDefinitionMaturity:
    path: Path
    generated_on: str
    structure_source: str
    score: int
    status: str
    criteria: list[dict[str, object]]
    gaps: list[str]
    suggested_actions: list[str]
    selected_criteria_count: int = 0
    disabled_criteria_count: int = 0
    total_default_criteria_count: int = 0
    scope_label: str = "selected_project_rubric"
    basis: str = "heuristic_keyword_rubric"
    authoritative_definition_completeness: bool = False


class ProjectMaturityService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        proposal_summaries: Callable[[], list[_ProposalSummaryLike]],
        find_proposal_dir: Callable[[str], Path],
        change_set_statuses: Callable[[], list[_ChangeStatusLike]],
        find_change_dir: Callable[[str], Path],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.proposal_summaries = proposal_summaries
        self.find_proposal_dir = find_proposal_dir
        self.change_set_statuses = change_set_statuses
        self.find_change_dir = find_change_dir

    def init_project_rubrics(self, starter: str = "generic", force: bool = False) -> ProjectRubrics:
        starter = normalize_rubric_starter(starter)
        path = self.p2p_dir / "project" / "rubrics.yml"
        if path.exists() and not force:
            raise ValueError("Project rubrics already exist. Use --force to replace them.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(rubrics_payload(starter)), encoding="utf-8")
        return self.show_project_rubrics()

    def init_project_rubrics_preview(self, starter: str = "generic") -> list[dict[str, object]]:
        payload = rubrics_payload(starter)
        criteria = payload.get("criteria", [])
        return [item for item in criteria if isinstance(item, dict)] if isinstance(criteria, list) else []

    def show_project_rubrics(self) -> ProjectRubrics:
        path = self.p2p_dir / "project" / "rubrics.yml"
        if not path.exists():
            raise ValueError("Project rubrics not found. Run `p2p project rubrics init` first.")
        data = _read_yaml_mapping(path, default={})
        source = data.get("structure_source")
        if not isinstance(source, dict) or source.get("kind") not in {
            "starter",
            "vertical_release",
        }:
            raise ValueError(
                "P2P_PROJECT_RUBRICS_INVALID: structure_source must identify a starter or vertical release"
            )
        if source.get("kind") == "starter":
            source_identity = normalize_rubric_starter(str(source.get("starter_id") or ""))
        else:
            source_identity = str(source.get("coordinate") or "").strip()
            if not source_identity:
                raise ValueError(
                    "P2P_PROJECT_RUBRICS_INVALID: vertical structure source requires coordinate"
                )
        status = str(data.get("status") or "starter_selected")
        template = data.get("template")
        criteria = data.get("criteria", [])
        selected_scope = data.get("selected_scope")
        if not isinstance(criteria, list):
            criteria = []
        return ProjectRubrics(
            path=path.relative_to(self.root),
            structure_source=source_identity,
            status=status,
            template=str(template) if template else None,
            criteria=[item for item in criteria if isinstance(item, dict)],
            selected_scope=selected_scope if isinstance(selected_scope, dict) else None,
        )

    def refresh_definition_maturity(self) -> ProjectDefinitionMaturity:
        maturity = self.compute_definition_maturity()
        path = self.p2p_dir / "project" / "maturity-assessment.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(definition_maturity_payload(maturity)), encoding="utf-8")
        return maturity

    def show_definition_maturity(self) -> ProjectDefinitionMaturity:
        path = self.p2p_dir / "project" / "maturity-assessment.yml"
        if not path.exists():
            raise ValueError("Project definition maturity not found. Run `p2p assess maturity refresh` first.")
        data = _read_yaml_mapping(path, default={})
        criteria = data.get("criteria", [])
        gaps = data.get("gaps", [])
        suggested = data.get("suggested_actions", [])
        return ProjectDefinitionMaturity(
            path=path.relative_to(self.root),
            generated_on=str(data.get("generated_on") or ""),
            structure_source=str(data.get("structure_source") or "generic"),
            score=int(data.get("score") or 0),
            status=str(data.get("status") or "unknown"),
            criteria=[item for item in criteria if isinstance(item, dict)] if isinstance(criteria, list) else [],
            gaps=[str(item) for item in gaps] if isinstance(gaps, list) else [],
            suggested_actions=[str(item) for item in suggested] if isinstance(suggested, list) else [],
            selected_criteria_count=int(data.get("selected_criteria_count") or 0),
            disabled_criteria_count=int(data.get("disabled_criteria_count") or 0),
            total_default_criteria_count=int(data.get("total_default_criteria_count") or 0),
            scope_label=str(data.get("scope_label") or "selected_project_rubric"),
            basis=str(data.get("basis") or "heuristic_keyword_rubric"),
            authoritative_definition_completeness=bool(data.get("authoritative_definition_completeness", False)),
        )

    def compute_definition_maturity(self) -> ProjectDefinitionMaturity:
        rubrics = self.show_project_rubrics()
        evidence = self._definition_evidence_records()
        results: list[dict[str, object]] = []
        gaps: list[str] = []
        suggested_actions: list[str] = []
        scores: list[int] = []

        enabled_criteria = [criterion for criterion in rubrics.criteria if criterion.get("enabled") is not False]
        disabled_count = len([criterion for criterion in rubrics.criteria if criterion.get("enabled") is False])
        total_default_count = len(rubrics.criteria)
        if rubrics.selected_scope:
            total_default_count = int(rubrics.selected_scope.get("total_default") or total_default_count)
        if rubrics.status in {"unresolved", "missing"} or not enabled_criteria:
            return ProjectDefinitionMaturity(
                path=(self.p2p_dir / "project" / "maturity-assessment.yml").relative_to(self.root),
                generated_on=date.today().isoformat(),
                structure_source=rubrics.structure_source,
                score=0,
                status="rubric_missing",
                criteria=[],
                gaps=[
                    "Project definition rubric is unresolved or has no enabled criteria.",
                    "Select or define project structure before assessing maturity.",
                    "Define structure coverage criteria.",
                ],
                suggested_actions=[
                    "Select a vertical release or edit the project structure.",
                    "Define project structure coverage criteria.",
                ],
                selected_criteria_count=0,
                disabled_criteria_count=disabled_count,
                total_default_criteria_count=total_default_count,
            )

        for criterion in enabled_criteria:
            criterion_id = str(criterion.get("id") or "unknown")
            title = str(criterion.get("title") or criterion_id)
            keywords = [str(item).lower() for item in criterion.get("keywords", []) if str(item).strip()]
            matches = _criterion_matches(evidence, keywords)
            accepted = [
                item for item in matches
                if item["state"] == "completed" or is_active_project_projection(item["state"])
            ]
            partial = [item for item in matches if item not in accepted]
            if accepted:
                status = "covered"
                score = 100
                criterion_evidence = accepted[:5]
            elif partial:
                status = "partial"
                score = 50
                criterion_evidence = partial[:5]
                gaps.append(f"{title} is only partially covered.")
                suggested_actions.append(f"Create or accept a proposal covering {title}.")
            else:
                status = "missing"
                score = 0
                criterion_evidence = []
                gaps.append(f"{title} has no clear P2P coverage.")
                suggested_actions.append(f"Create a proposal covering {title}.")
            scores.append(score)
            results.append(
                {
                    "id": criterion_id,
                    "title": title,
                    "status": status,
                    "score": score,
                    "required": bool(criterion.get("required", True)),
                    "evidence": criterion_evidence,
                    "suggested_action": suggested_actions[-1] if status != "covered" else "",
                }
            )

        score = round(sum(scores) / len(scores)) if scores else 0
        if score >= 85:
            status = "well_defined"
        elif score >= 60:
            status = "partially_defined"
        elif score > 0:
            status = "underdefined"
        else:
            status = "not_defined"
        return ProjectDefinitionMaturity(
            path=(self.p2p_dir / "project" / "maturity-assessment.yml").relative_to(self.root),
            generated_on=date.today().isoformat(),
            structure_source=rubrics.structure_source,
            score=score,
            status=status,
            criteria=results,
            gaps=gaps,
            suggested_actions=list(dict.fromkeys(suggested_actions)),
            selected_criteria_count=len(enabled_criteria),
            disabled_criteria_count=disabled_count,
            total_default_criteria_count=total_default_count,
        )

    def _definition_evidence_records(self) -> list[dict[str, str]]:
        records: list[dict[str, str]] = []
        for proposal in self.proposal_summaries():
            proposal_dir = self.find_proposal_dir(proposal.proposal_id)
            text = _read_optional(proposal_dir / "proposal.md") + "\n" + _read_optional(proposal_dir / "decision.md")
            records.append(
                {
                    "type": "proposal",
                    "id": proposal.proposal_id,
                    "title": proposal.title,
                    "state": proposal.status,
                    "text": text.lower(),
                }
            )
        for change in self.change_set_statuses():
            change_dir = self.find_change_dir(change.change_id)
            text = _read_optional(change_dir / "change.md") + "\n" + _read_optional(change_dir / "tasks.yml")
            records.append(
                {
                    "type": "change",
                    "id": change.change_id,
                    "title": change.title,
                    "state": change.status,
                    "text": text.lower(),
                }
            )
        return records


def normalize_rubric_starter(starter: str) -> str:
    normalized = starter.strip().lower()
    if normalized not in PROJECT_RUBRIC_STARTERS:
        raise ValueError("P2P_STRUCTURE_SOURCE_INVALID: rubric starter must be generic or empty")
    return normalized


def rubrics_payload(starter: str, rubric_enabled: dict[str, bool] | None = None) -> dict[str, object]:
    starter = normalize_rubric_starter(starter)
    rubric_enabled = rubric_enabled or {}
    if starter == "empty":
        return {
            "version": "1.0",
            "structure_source": {"kind": "starter", "starter_id": "empty"},
            "status": "empty",
            "template": "empty",
            "assessment_type": "project_definition_maturity",
            "scoring": {"covered": 100, "partial": 50, "missing": 0},
            "criteria": [],
        }
    return {
        "version": "1.0",
        "structure_source": {"kind": "starter", "starter_id": starter},
        "status": "starter_selected",
        "template": starter,
        "assessment_type": "project_definition_maturity",
        "scoring": {"covered": 100, "partial": 50, "missing": 0},
        "criteria": [
            {
                "id": str(item["id"]),
                "title": str(item["title"]),
                "enabled": bool(rubric_enabled.get(str(item["id"]), True)),
                "required": True,
                "keywords": list(item.get("keywords", [])),
            }
            for item in _generic_starter_rubrics()
        ],
    }


def _generic_starter_rubrics() -> list[dict[str, object]]:
    resource = files("p2p_engine").joinpath(
        "resources", "verticals", "base_project", "rubrics.yml"
    )
    payload = yaml.safe_load(resource.read_text(encoding="utf-8"))
    rubrics = payload.get("rubrics") if isinstance(payload, dict) else None
    if not isinstance(rubrics, list) or not all(
        isinstance(item, dict) for item in rubrics
    ):
        raise ValueError(
            "P2P_STRUCTURE_SOURCE_INVALID: generic starter rubrics are unavailable"
        )
    return [dict(item) for item in rubrics]


def definition_maturity_payload(maturity: ProjectDefinitionMaturity) -> dict[str, object]:
    return {
        "generated_on": maturity.generated_on,
        "assessment_type": "project_definition_maturity",
        "structure_source": maturity.structure_source,
        "score": maturity.score,
        "status": maturity.status,
        "criteria": maturity.criteria,
        "gaps": maturity.gaps,
        "suggested_actions": maturity.suggested_actions,
        "selected_criteria_count": maturity.selected_criteria_count,
        "disabled_criteria_count": maturity.disabled_criteria_count,
        "total_default_criteria_count": maturity.total_default_criteria_count,
        "scope_label": maturity.scope_label,
        "basis": maturity.basis,
        "authoritative_definition_completeness": maturity.authoritative_definition_completeness,
    }


def _criterion_matches(evidence: list[dict[str, str]], keywords: list[str]) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for item in evidence:
        text = item["text"]
        matched = [keyword for keyword in keywords if keyword in text]
        if matched:
            matches.append(
                {
                    "type": item["type"],
                    "id": item["id"],
                    "title": item["title"],
                    "state": item["state"],
                    "matched": ", ".join(matched[:5]),
                }
            )
    return matches


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_yaml_mapping(path: Path, default: dict[str, object]) -> dict[str, object]:
    return _foundation_read_yaml_mapping(
        path,
        default,
        error_message="YAML document must be a mapping: {path}",
    )

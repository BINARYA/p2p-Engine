from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Protocol

from p2p_engine.foundation.files import (
    read_yaml_mapping as _foundation_read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.services.lifecycle_authority import is_active_project_projection

PROJECT_DOMAIN_TEMPLATES = {"generic", "software", "grant_document", "board_game"}
PROJECT_DOMAINS = {"none", "custom", *PROJECT_DOMAIN_TEMPLATES}

_BUILT_IN_RUBRICS: dict[str, list[dict[str, object]]] = {
    "generic": [
        {"id": "problem_definition", "title": "Problem Definition", "keywords": ["problem", "need", "objective", "goal", "context"]},
        {"id": "scope_boundaries", "title": "Scope Boundaries", "keywords": ["scope", "non-goal", "boundary", "out of scope"]},
        {"id": "requirements", "title": "Requirements", "keywords": ["requirement", "criteria", "acceptance", "must"]},
        {"id": "risks_tradeoffs", "title": "Risks and Tradeoffs", "keywords": ["risk", "tradeoff", "alternative", "constraint"]},
        {"id": "validation_plan", "title": "Validation Plan", "keywords": ["test", "validation", "verify", "acceptance"]},
    ],
    "software": [
        {"id": "problem_definition", "title": "Problem Definition", "keywords": ["problem", "need", "objective", "goal", "context"]},
        {"id": "scope_boundaries", "title": "Scope Boundaries", "keywords": ["scope", "non-goal", "boundary", "out of scope"]},
        {"id": "user_workflows", "title": "User Roles and Workflows", "keywords": ["user", "workflow", "role", "journey", "onboarding"]},
        {"id": "functional_requirements", "title": "Functional Requirements", "keywords": ["feature", "command", "function", "requirement", "acceptance"]},
        {"id": "non_functional_requirements", "title": "Non-Functional Requirements", "keywords": ["performance", "reliability", "scalability", "maintainability", "compatibility"]},
        {"id": "security_privacy", "title": "Security and Privacy", "keywords": ["security", "privacy", "permission", "auth", "malicious", "sandbox"]},
        {"id": "data_model", "title": "Data Model", "keywords": ["data model", "schema", "yaml", "json", "storage", "registry"]},
        {"id": "integration_boundaries", "title": "Integration Boundaries", "keywords": ["integration", "mcp", "api", "adapter", "boundary", "interface"]},
        {"id": "deployment_operations", "title": "Deployment and Operations", "keywords": ["install", "packaging", "deploy", "release", "cloud", "local"]},
        {"id": "testing_strategy", "title": "Testing Strategy", "keywords": ["test", "pytest", "validation", "verify", "coverage"]},
        {"id": "ux_accessibility", "title": "UX and Accessibility", "keywords": ["ux", "usability", "accessibility", "wizard", "onboarding"]},
        {"id": "risks_tradeoffs", "title": "Risks and Tradeoffs", "keywords": ["risk", "tradeoff", "alternative", "constraint"]},
        {"id": "acceptance_criteria", "title": "Acceptance Criteria", "keywords": ["acceptance", "definition of done", "criteria", "done"]},
    ],
    "grant_document": [
        {"id": "call_requirements", "title": "Call Requirements", "keywords": ["call", "requirement", "eligibility", "deadline"]},
        {"id": "objectives", "title": "Objectives", "keywords": ["objective", "impact", "beneficiary", "goal"]},
        {"id": "budget", "title": "Budget", "keywords": ["budget", "cost", "funding", "expense"]},
        {"id": "evaluation_criteria", "title": "Evaluation Criteria", "keywords": ["evaluation", "score", "criteria", "award"]},
    ],
    "board_game": [
        {"id": "core_loop", "title": "Core Gameplay Loop", "keywords": ["turn", "round", "loop", "gameplay"]},
        {"id": "components", "title": "Components", "keywords": ["component", "card", "board", "token", "piece"]},
        {"id": "rules", "title": "Rules", "keywords": ["rule", "action", "phase", "win"]},
        {"id": "playtesting", "title": "Playtesting", "keywords": ["playtest", "balance", "test", "feedback"]},
    ],
}


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
    domain: str
    status: str
    template: str | None
    criteria: list[dict[str, object]]
    selected_scope: dict[str, object] | None = None


@dataclass(frozen=True)
class ProjectDefinitionMaturity:
    path: Path
    generated_on: str
    domain: str
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

    def init_project_rubrics(self, domain: str = "generic", force: bool = False) -> ProjectRubrics:
        domain = normalize_project_domain(domain)
        path = self.p2p_dir / "project" / "rubrics.yml"
        if path.exists() and not force:
            raise ValueError("Project rubrics already exist. Use --force to replace them.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(rubrics_payload(domain)), encoding="utf-8")
        domain_path = self.p2p_dir / "project" / "domain.yml"
        domain_path.write_text(_yaml_dump(domain_state_payload(domain)), encoding="utf-8")
        project_file = self.p2p_dir / "project.yml"
        data = _read_yaml_mapping(project_file, default={})
        project = data.get("project", {})
        if not isinstance(project, dict):
            project = {}
        project["domain"] = domain
        data["project"] = project
        project_file.write_text(_yaml_dump(data), encoding="utf-8")
        return self.show_project_rubrics()

    def init_project_rubrics_preview(self, domain: str = "generic") -> list[dict[str, object]]:
        payload = rubrics_payload(domain)
        criteria = payload.get("criteria", [])
        return [item for item in criteria if isinstance(item, dict)] if isinstance(criteria, list) else []

    def show_project_rubrics(self) -> ProjectRubrics:
        path = self.p2p_dir / "project" / "rubrics.yml"
        if not path.exists():
            raise ValueError("Project rubrics not found. Run `p2p project rubrics init` first.")
        data = _read_yaml_mapping(path, default={})
        domain = str(data.get("domain") or "generic")
        status = str(data.get("status") or "template_selected")
        template = data.get("template")
        criteria = data.get("criteria", [])
        selected_scope = data.get("selected_scope")
        if not isinstance(criteria, list):
            criteria = []
        return ProjectRubrics(
            path=path.relative_to(self.root),
            domain=domain,
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
            domain=str(data.get("domain") or "generic"),
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
                domain=rubrics.domain,
                score=0,
                status="rubric_missing",
                criteria=[],
                gaps=[
                    "Project definition rubric is unresolved or has no enabled criteria.",
                    "Define the project domain before assessing maturity.",
                    "Define the domain rubric and coverage criteria.",
                ],
                suggested_actions=[
                    "Define the project domain with the user and agent.",
                    "Define the project rubric and coverage criteria.",
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
            domain=rubrics.domain,
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


def normalize_project_domain(domain: str) -> str:
    normalized = domain.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "": "none",
        "no_template": "none",
        "no_domain": "none",
        "unresolved": "none",
        "blank": "none",
        "empty": "none",
        "custom_unresolved": "custom",
        "soft": "software",
        "software_development": "software",
        "grant": "grant_document",
        "bid": "grant_document",
        "tender": "grant_document",
        "game": "board_game",
        "boardgame": "board_game",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in PROJECT_DOMAINS:
        raise ValueError("Project domain must be none, custom, generic, software, grant_document, or board_game")
    return normalized


def domain_state_payload(domain: str) -> dict[str, object]:
    domain = normalize_project_domain(domain)
    if domain in PROJECT_DOMAIN_TEMPLATES:
        return {
            "version": "1.0",
            "status": "template_selected",
            "type": "template",
            "name": domain,
            "template": domain,
        }
    return {
        "version": "1.0",
        "status": "unresolved",
        "type": domain,
        "name": None,
        "template": None,
        "next_actions": [
            {"kind": "define_custom_domain" if domain == "custom" else "define_domain", "title": "Define the project domain with the user and agent"},
            {"kind": "define_domain_rubric", "title": "Define the project rubric and coverage criteria"},
        ],
    }


def domain_setup_next_actions_payload(domain: str) -> dict[str, object]:
    domain = normalize_project_domain(domain)
    label = "custom" if domain == "custom" else "project"
    return {
        "next_actions": [
            {
                "id": "NEXT-001",
                "priority": "high",
                "kind": "define_domain",
                "target": "project-domain",
                "reason": f"The {label} domain is unresolved and must be defined before maturity can be assessed.",
                "command": "p2p project show overview",
            },
            {
                "id": "NEXT-002",
                "priority": "high",
                "kind": "define_domain_rubric",
                "target": "project-rubric",
                "reason": "The project rubric is unresolved and has no enabled criteria.",
                "command": "p2p project rubrics show",
            },
        ]
    }


def rubrics_payload(domain: str, rubric_enabled: dict[str, bool] | None = None) -> dict[str, object]:
    domain = normalize_project_domain(domain)
    rubric_enabled = rubric_enabled or {}
    if domain not in PROJECT_DOMAIN_TEMPLATES:
        return {
            "version": "1.0",
            "domain": domain,
            "status": "unresolved",
            "template": None,
            "assessment_type": "project_definition_maturity",
            "scoring": {"covered": 100, "partial": 50, "missing": 0},
            "criteria": [],
            "next_actions": [
                {"kind": "define_domain", "title": "Define the project domain with the user and agent"},
                {"kind": "define_domain_rubric", "title": "Define the project rubric and coverage criteria"},
            ],
        }
    return {
        "version": "1.0",
        "domain": domain,
        "status": "template_selected",
        "template": domain,
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
            for item in _BUILT_IN_RUBRICS[domain]
        ],
    }


def definition_maturity_payload(maturity: ProjectDefinitionMaturity) -> dict[str, object]:
    return {
        "generated_on": maturity.generated_on,
        "assessment_type": "project_definition_maturity",
        "domain": maturity.domain,
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

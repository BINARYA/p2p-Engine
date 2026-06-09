from __future__ import annotations

import re
from dataclasses import asdict
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Protocol, TypeVar

import yaml

from p2p_engine.core.project_verticals import (
    ActiveProjectVertical,
    CustomVerticalCandidate,
    ProjectReadinessReview,
    ProjectVerticalAddResult,
    ProposalVerticalCoverage,
    ProposalVerticalCoverageSection,
    VerticalArtifact,
    VerticalListItem,
    VerticalPack,
    VerticalQuestion,
    VerticalRubric,
    VerticalSection,
    VerticalSectionReview,
    VerticalValidationIssue,
    VerticalValidationResult,
)
from p2p_engine.foundation.files import relative_to_root, slugify, yaml_dump

VERTICAL_SCHEMA_VERSION = 1
ACTIVE_VERTICAL_SCHEMA_VERSION = 1
PROPOSAL_COVERAGE_SCHEMA_VERSION = 1
BASE_PROJECT_VERTICAL_ID = "base_project"
PROJECT_LOCAL_SOURCE = "project_local"
INTERNAL_SOURCE = "internal"
FALLBACK_SOURCE = "fallback"

RELEVANCE_VALUES = {"direct", "indirect", "context", "unknown"}
QUESTION_PRIORITIES = {"high", "medium", "low"}
T = TypeVar("T")


class _ProposalSummaryLike(Protocol):
    proposal_id: str
    title: str
    status: str


def validate_vertical_pack_payload(payload: dict[str, object], *, target: str = "vertical") -> None:
    payload = _normalise_pack_payload(payload)
    issues = _vertical_pack_issues(payload)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        first = errors[0]
        raise ValueError(f"Invalid vertical pack {target}: {first.field}: {first.message}")


def validate_vertical_coverage_payload(payload: dict[str, object], *, target: str = "vertical-coverage") -> None:
    coverage = payload.get("vertical_coverage")
    if not isinstance(coverage, dict):
        raise ValueError(f"Invalid {target}: expected top-level `vertical_coverage` mapping.")
    proposal_id = str(coverage.get("proposal_id") or "").strip()
    vertical_id = str(coverage.get("vertical_id") or "").strip()
    sections = coverage.get("sections")
    if not proposal_id:
        raise ValueError(f"Invalid {target}: missing proposal_id.")
    if not vertical_id:
        raise ValueError(f"Invalid {target}: missing vertical_id.")
    if not isinstance(sections, list):
        raise ValueError(f"Invalid {target}: sections must be a list.")
    for index, item in enumerate(sections):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid {target}: sections[{index}] must be a mapping.")
        section_id = str(item.get("id") or "").strip()
        relevance = str(item.get("relevance") or "direct").strip()
        if not section_id:
            raise ValueError(f"Invalid {target}: sections[{index}].id is required.")
        if relevance not in RELEVANCE_VALUES:
            raise ValueError(f"Invalid {target}: sections[{index}].relevance must be one of {sorted(RELEVANCE_VALUES)}.")


class ProjectVerticalService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        proposal_summaries: Callable[[], list[_ProposalSummaryLike]],
        find_proposal_dir: Callable[[str], Path],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.proposal_summaries = proposal_summaries
        self.find_proposal_dir = find_proposal_dir

    def list_verticals(self) -> list[VerticalListItem]:
        active = self.active_vertical()
        packs_by_id = self._available_packs_by_id()
        items: list[VerticalListItem] = []
        for vertical_id in sorted(packs_by_id):
            pack = packs_by_id[vertical_id]
            items.append(
                VerticalListItem(
                    vertical_id=pack.vertical_id,
                    name=pack.name,
                    version=pack.version,
                    source=pack.source,
                    active=pack.vertical_id == active.vertical_id and not active.fallback_used,
                    path=relative_to_root(pack.path, self.root) if pack.path else None,
                )
            )
        return items

    def show_vertical(self, vertical_id: str) -> VerticalPack:
        return self._load_available_pack(vertical_id)

    def validate_vertical(self, target: str) -> VerticalValidationResult:
        try:
            pack = self._load_target(target)
        except ValueError as exc:
            return VerticalValidationResult(
                target=target,
                valid=False,
                vertical_id="",
                source="unknown",
                issues=[VerticalValidationIssue("error", "target", str(exc))],
            )
        issues = [*_vertical_pack_issues(_pack_payload(pack)), *self._extension_issues(pack)]
        return VerticalValidationResult(
            target=target,
            valid=not any(issue.severity == "error" for issue in issues),
            vertical_id=pack.vertical_id,
            source=pack.source,
            issues=issues,
        )

    def propose_vertical(self, idea: str) -> CustomVerticalCandidate:
        text = idea.strip()
        if not text:
            raise ValueError("Project idea is required.")
        lower = text.lower()
        if any(token in lower for token in ("scatola", "box", "packaging", "confezione")):
            pack = _candidate_pack(
                vertical_id="packaging_or_physical_product_design",
                name="Packaging Or Physical Product Design",
                description="Design a box or packaging solution from concept to manufacturable specification.",
                sections=[
                    ("contained_product", "Contained Product And Use Case", "Define what the box contains and how it will be used."),
                    ("success_definition", "Meaning Of Perfect", "Clarify which tradeoffs define a perfect box."),
                    ("structure_materials", "Structure And Materials", "Define dimensions, materials, sustainability, and physical structure."),
                    ("prototype_testing", "Prototype And Tests", "Define prototype plan and validation checks."),
                ],
                questions=[
                    ("contained_product_main", "contained_product", "What must the box contain?"),
                    ("perfect_tradeoff_main", "success_definition", "Does perfect mean beautiful, resistant, cheap, sustainable, memorable, or a weighted combination?"),
                ],
                artifacts=[
                    ("packaging_brief", "Packaging Brief", ["contained_product", "success_definition"]),
                    ("prototype_test_checklist", "Prototype Test Checklist", ["prototype_testing"]),
                ],
            )
        elif any(token in lower for token in ("banca", "bank", "sociale", "impact", "impatto")):
            pack = _candidate_pack(
                vertical_id="social_impact_program_design",
                name="Social Impact Program Design",
                description="Design social impact initiatives that are measurable, governed, credible, and connected to stakeholder needs.",
                sections=[
                    ("social_impact_vision", "Social Impact Vision", "Define the social change the program should create."),
                    ("theory_of_change", "Theory Of Change", "Explain how activities create outcomes for beneficiaries."),
                    ("beneficiary_communities", "Beneficiary Communities", "Identify who benefits and why they are prioritized."),
                    ("measurement_reporting", "Measurement And Reporting", "Define outcome metrics, evidence, and reporting cadence."),
                ],
                questions=[
                    ("beneficiary_main", "beneficiary_communities", "Which community or population should benefit?"),
                    ("measurement_main", "measurement_reporting", "How will real impact be measured and how will social-washing be avoided?"),
                ],
                artifacts=[
                    ("social_impact_strategy_brief", "Social Impact Strategy Brief", ["social_impact_vision"]),
                    ("outcome_metric_framework", "Outcome Metric Framework", ["measurement_reporting"]),
                ],
            )
        else:
            base_slug = slugify(text, fallback="custom_project")
            vertical_id = f"{base_slug}_design"
            pack = _candidate_pack(
                vertical_id=vertical_id,
                name=_title_from_slug(vertical_id),
                description=f"Project-local custom vertical candidate for: {text}",
                sections=[
                    ("domain_context", "Domain Context", "Define the specific domain and why base_project is not enough."),
                    ("specific_capisaldi", "Specific Capisaldi", "Identify the domain-specific pillars to address."),
                    ("specific_artifacts", "Specific Artifacts", "Define artifacts expected from this kind of project."),
                ],
                questions=[
                    ("domain_context_main", "domain_context", "What makes this project different from a generic project?"),
                    ("capisaldi_main", "specific_capisaldi", "Which domain-specific pillars must be addressed first?"),
                ],
                artifacts=[
                    ("custom_vertical_brief", "Custom Vertical Brief", ["domain_context", "specific_capisaldi"]),
                ],
            )

        payload = {
            "vertical_candidate": {
                "schema_version": VERTICAL_SCHEMA_VERSION,
                "source_idea": text,
                "candidate": _pack_payload(pack)["vertical"],
                "rationale": {
                    "base_project_sections_reused": ["vision", "objective", "stakeholders", "scope", "risks", "definition_of_done"],
                    "vertical_specific_additions": [section.section_id for section in pack.sections],
                },
            }
        }
        return CustomVerticalCandidate(
            source_idea=text,
            pack=pack,
            base_project_sections_reused=["vision", "objective", "stakeholders", "scope", "risks", "definition_of_done"],
            vertical_specific_additions=[section.section_id for section in pack.sections],
            yaml_text=yaml_dump(payload),
        )

    def add_vertical(self, source: Path, *, activate: bool = False, actor: str = "local") -> ProjectVerticalAddResult:
        pack = self._load_pack_from_path(source)
        validate_vertical_pack_payload(_pack_payload(pack), target=str(source))
        target_dir = self._project_verticals_dir() / pack.vertical_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / "vertical.yml"
        self._atomic_write(target_path, yaml_dump(_pack_payload(pack)))
        activated = False
        if activate:
            self.select_vertical(pack.vertical_id, actor=actor)
            activated = True
        return ProjectVerticalAddResult(
            vertical_id=pack.vertical_id,
            path=relative_to_root(target_path, self.root),
            activated=activated,
        )

    def select_vertical(self, vertical_id: str, *, actor: str = "local") -> ActiveProjectVertical:
        pack = self._load_available_pack(vertical_id)
        state_path = self._active_vertical_path()
        state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "project_vertical": {
                "schema_version": ACTIVE_VERTICAL_SCHEMA_VERSION,
                "active_vertical_id": pack.vertical_id,
                "active_source": pack.source,
                "selected_at": date.today().isoformat(),
                "selected_by": actor,
                "fallback_used": False,
            }
        }
        self._atomic_write(state_path, yaml_dump(payload))
        return self.active_vertical()

    def active_vertical(self) -> ActiveProjectVertical:
        path = self._active_vertical_path()
        if not path.exists():
            base = self._load_available_pack(BASE_PROJECT_VERTICAL_ID)
            return ActiveProjectVertical(
                vertical_id=BASE_PROJECT_VERTICAL_ID,
                source=base.source,
                path=relative_to_root(base.path, self.root) if base.path else None,
                fallback_used=True,
            )
        payload = _read_yaml_mapping(path)
        state = payload.get("project_vertical")
        if not isinstance(state, dict):
            raise ValueError(f"Invalid project vertical state: {path}")
        vertical_id = str(state.get("active_vertical_id") or "").strip()
        if not vertical_id:
            raise ValueError(f"Invalid project vertical state: missing active_vertical_id in {path}")
        pack = self._load_available_pack(vertical_id)
        return ActiveProjectVertical(
            vertical_id=vertical_id,
            source=str(state.get("active_source") or pack.source),
            path=relative_to_root(pack.path, self.root) if pack.path else None,
            selected_at=str(state.get("selected_at") or ""),
            selected_by=str(state.get("selected_by") or ""),
            fallback_used=bool(state.get("fallback_used") or False),
        )

    def read_proposal_vertical_coverage(self, proposal_id: str) -> ProposalVerticalCoverage | None:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "vertical-coverage.yml"
        if not path.exists():
            return None
        payload = _read_yaml_mapping(path)
        validate_vertical_coverage_payload(payload, target=str(path))
        coverage = payload["vertical_coverage"]
        assert isinstance(coverage, dict)
        sections = [
            ProposalVerticalCoverageSection(
                section_id=str(item.get("id") or ""),
                relevance=str(item.get("relevance") or "direct"),
                rationale=str(item.get("rationale") or ""),
                source=str(item.get("source") or "declared"),
            )
            for item in coverage.get("sections", [])
            if isinstance(item, dict)
        ]
        return ProposalVerticalCoverage(
            proposal_id=str(coverage.get("proposal_id") or proposal_id),
            vertical_id=str(coverage.get("vertical_id") or ""),
            sections=sections,
            path=relative_to_root(path, self.root),
        )

    def project_readiness_review(self, *, vertical_id: str | None = None) -> ProjectReadinessReview:
        active = self.active_vertical()
        pack = self._load_available_pack(vertical_id or active.vertical_id)
        fallback_used = active.fallback_used and vertical_id is None
        proposal_matches: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        proposal_statuses: dict[str, str] = {}
        mapped_proposals: set[str] = set()
        unmapped: list[str] = []

        for proposal in self.proposal_summaries():
            proposal_statuses[proposal.proposal_id] = proposal.status
            mapped_sections = self._mapped_sections_for_proposal(proposal, pack)
            if mapped_sections:
                mapped_proposals.add(proposal.proposal_id)
                for section_id in mapped_sections:
                    proposal_matches.setdefault(section_id, []).append(proposal.proposal_id)
            else:
                unmapped.append(proposal.proposal_id)

        section_reviews: list[VerticalSectionReview] = []
        missing_capisaldi: list[str] = []
        generated_questions: list[str] = []
        for section in sorted(pack.sections, key=lambda item: item.priority):
            proposals = sorted(dict.fromkeys(proposal_matches.get(section.section_id, [])))
            if proposals:
                accepted = [proposal_id for proposal_id in proposals if proposal_statuses.get(proposal_id) == "accepted"]
                status = "covered" if accepted else "partial"
            elif section.required:
                status = "missing"
            else:
                status = "not_applicable"
            gaps = []
            questions = []
            if status == "missing":
                gaps.append("missing_proposal_coverage")
                missing_capisaldi.append(section.section_id)
                questions = [
                    question.question
                    for question in pack.questions
                    if question.section_id == section.section_id
                ][:3]
                generated_questions.extend(questions)
            elif status == "partial":
                gaps.append("proposal_coverage_not_accepted")
            section_reviews.append(
                VerticalSectionReview(
                    section_id=section.section_id,
                    title=section.title,
                    status=status,
                    proposals=proposals,
                    gaps=gaps,
                    risks=[],
                    questions=questions,
                )
            )

        suggested = []
        if fallback_used:
            suggested.append('p2p project vertical propose "<project idea>"')
        if missing_capisaldi:
            suggested.append("Map or create proposals for missing vertical capisaldi.")
        suggested.append("p2p project readiness review")
        return ProjectReadinessReview(
            active_vertical_id=pack.vertical_id,
            vertical_source=pack.source if not fallback_used else FALLBACK_SOURCE,
            fallback_used=fallback_used,
            sections=section_reviews,
            unmapped_proposals=sorted(unmapped),
            missing_capisaldi=missing_capisaldi,
            generated_questions=list(dict.fromkeys(generated_questions)),
            suggested_next=list(dict.fromkeys(suggested)),
        )

    def validation_findings(self) -> list[tuple[str, str, Path, str, str]]:
        findings: list[tuple[str, str, Path, str, str]] = []
        for pack_path in sorted(self._project_verticals_dir().glob("*/vertical.yml")):
            try:
                payload = _read_yaml_mapping(pack_path)
                validate_vertical_pack_payload(payload, target=str(pack_path))
            except ValueError as exc:
                findings.append(
                    (
                        "P2P250_INVALID_PROJECT_VERTICAL",
                        "error",
                        pack_path,
                        str(exc),
                        "p2p project vertical validate " + str(relative_to_root(pack_path, self.root)),
                    )
                )
        state_path = self._active_vertical_path()
        if state_path.exists():
            try:
                active = self.active_vertical()
                self._load_available_pack(active.vertical_id)
            except ValueError as exc:
                findings.append(
                    (
                        "P2P251_INVALID_ACTIVE_VERTICAL",
                        "error",
                        state_path,
                        str(exc),
                        "p2p project vertical list",
                    )
                )
        for coverage_path in sorted(self.p2p_dir.glob("proposals/*/vertical-coverage.yml")):
            try:
                payload = _read_yaml_mapping(coverage_path)
                validate_vertical_coverage_payload(payload, target=str(coverage_path))
                self._validate_coverage_sections(payload, coverage_path)
            except ValueError as exc:
                findings.append(
                    (
                        "P2P252_INVALID_PROPOSAL_VERTICAL_COVERAGE",
                        "error",
                        coverage_path,
                        str(exc),
                        "",
                    )
                )
        return findings

    def _validate_coverage_sections(self, payload: dict[str, object], path: Path) -> None:
        coverage = payload.get("vertical_coverage")
        if not isinstance(coverage, dict):
            return
        vertical_id = str(coverage.get("vertical_id") or "")
        pack = self._load_available_pack(vertical_id)
        section_ids = {section.section_id for section in pack.sections}
        for item in coverage.get("sections", []):
            if isinstance(item, dict):
                section_id = str(item.get("id") or "")
                if section_id not in section_ids:
                    raise ValueError(f"Invalid proposal vertical coverage {path}: unknown section id `{section_id}` for vertical `{vertical_id}`.")

    def _extension_issues(self, pack: VerticalPack) -> list[VerticalValidationIssue]:
        if not pack.extends:
            return []
        if pack.extends in self._available_packs_by_id():
            return []
        return [
            VerticalValidationIssue(
                severity="error",
                field="vertical.extends",
                message=f"unknown base vertical `{pack.extends}`",
            )
        ]

    def _mapped_sections_for_proposal(self, proposal: _ProposalSummaryLike, pack: VerticalPack) -> list[str]:
        coverage = self.read_proposal_vertical_coverage(proposal.proposal_id)
        if coverage and coverage.vertical_id == pack.vertical_id:
            return [section.section_id for section in coverage.sections]
        base_section_ids: set[str] = set()
        if pack.extends:
            base = self._load_available_pack(pack.extends)
            base_section_ids = {section.section_id for section in base.sections}
        proposal_dir = self.find_proposal_dir(proposal.proposal_id)
        text = (
            _read_optional(proposal_dir / "proposal.md")
            + "\n"
            + _read_optional(proposal_dir / "decision.md")
            + "\n"
            + _read_optional(proposal_dir / "suggested-scope.md")
            + "\n"
            + _read_optional(proposal_dir / "risks.md")
        ).lower()
        mapped: list[str] = []
        for section in pack.sections:
            if section.section_id in base_section_ids:
                continue
            terms = {section.section_id.replace("_", " "), section.title.lower()}
            terms.update(_important_words(section.title))
            terms.update(_important_words(section.purpose))
            for rubric in pack.rubrics:
                if rubric.section_id == section.section_id:
                    terms.update(keyword.lower() for keyword in rubric.keywords)
            if any(term and term in text for term in terms):
                mapped.append(section.section_id)
        return mapped

    def _available_packs_by_id(self) -> dict[str, VerticalPack]:
        packs: dict[str, VerticalPack] = {}
        for pack in self._internal_packs():
            packs[pack.vertical_id] = pack
        for pack in self._project_local_packs():
            packs[pack.vertical_id] = pack
        return packs

    def _load_available_pack(self, vertical_id: str) -> VerticalPack:
        normalized = _normalize_vertical_id(vertical_id)
        packs = self._available_packs_by_id()
        if normalized in packs:
            return _compose_pack(packs[normalized], packs)
        raise ValueError(f"Unknown project vertical `{vertical_id}`. Run `p2p project vertical list`.")

    def _load_target(self, target: str) -> VerticalPack:
        path = Path(target)
        if path.exists():
            return self._load_pack_from_path(path)
        return self._load_available_pack(target)

    def _load_pack_from_path(self, source: Path) -> VerticalPack:
        if not source.is_absolute():
            source = self.root / source
        vertical_path = source / "vertical.yml" if source.is_dir() else source
        if not vertical_path.exists():
            raise ValueError(f"Vertical pack not found: {source}. Expected a vertical.yml file or pack directory.")
        payload = _read_yaml_mapping(vertical_path)
        validate_vertical_pack_payload(payload, target=str(vertical_path))
        return _pack_from_payload(payload, source=PROJECT_LOCAL_SOURCE, path=vertical_path)

    def _project_local_packs(self) -> list[VerticalPack]:
        packs: list[VerticalPack] = []
        root = self._project_verticals_dir()
        if not root.exists():
            return packs
        for vertical_path in sorted(root.glob("*/vertical.yml")):
            try:
                payload = _read_yaml_mapping(vertical_path)
                validate_vertical_pack_payload(payload, target=str(vertical_path))
                packs.append(_pack_from_payload(payload, source=PROJECT_LOCAL_SOURCE, path=vertical_path))
            except ValueError:
                continue
        return packs

    def _internal_packs(self) -> list[VerticalPack]:
        packs: list[VerticalPack] = []
        root = resources.files("p2p_engine.resources.verticals")
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            vertical = child / "vertical.yml"
            if not vertical.is_file():
                continue
            payload = yaml.safe_load(vertical.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            validate_vertical_pack_payload(payload, target=child.name)
            packs.append(_pack_from_payload(payload, source=INTERNAL_SOURCE, path=Path(str(vertical))))
        return packs

    def _project_verticals_dir(self) -> Path:
        return self.p2p_dir / "project" / "verticals"

    def _active_vertical_path(self) -> Path:
        return self.p2p_dir / "project" / "vertical.yml"

    def _atomic_write(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)


def _pack_from_payload(payload: dict[str, object], *, source: str, path: Path | None) -> VerticalPack:
    payload = _normalise_pack_payload(payload)
    vertical = payload.get("vertical")
    if not isinstance(vertical, dict):
        raise ValueError("Vertical pack must define top-level `vertical` mapping.")
    sections = [
        VerticalSection(
            section_id=str(item.get("id") or ""),
            title=str(item.get("title") or item.get("id") or ""),
            purpose=str(item.get("purpose") or ""),
            required=bool(item.get("required", True)),
            priority=int(item.get("priority") or 100),
        )
        for item in _mapping_list(vertical.get("sections"))
    ]
    rubrics = [
        VerticalRubric(
            rubric_id=str(item.get("id") or ""),
            title=str(item.get("title") or item.get("id") or ""),
            section_id=str(item.get("section_id") or ""),
            required=bool(item.get("required", True)),
            keywords=[str(keyword) for keyword in item.get("keywords", []) if str(keyword).strip()]
            if isinstance(item.get("keywords"), list)
            else [],
        )
        for item in _mapping_list(vertical.get("rubrics"))
    ]
    questions = [
        VerticalQuestion(
            question_id=str(item.get("id") or ""),
            section_id=str(item.get("section_id") or ""),
            question=str(item.get("question") or ""),
            priority=str(item.get("priority") or "medium"),
            rationale=str(item.get("rationale") or ""),
        )
        for item in _mapping_list(vertical.get("questions"))
    ]
    artifacts = [
        VerticalArtifact(
            artifact_id=str(item.get("id") or ""),
            title=str(item.get("title") or item.get("id") or ""),
            section_ids=[str(section_id) for section_id in item.get("section_ids", []) if str(section_id).strip()]
            if isinstance(item.get("section_ids"), list)
            else [],
            required=bool(item.get("required", False)),
        )
        for item in _mapping_list(vertical.get("artifacts"))
    ]
    return VerticalPack(
        vertical_id=str(vertical.get("id") or ""),
        name=str(vertical.get("name") or vertical.get("id") or ""),
        version=str(vertical.get("version") or ""),
        description=str(vertical.get("description") or ""),
        extends=str(vertical.get("extends")) if vertical.get("extends") else None,
        source=source,
        path=path,
        sections=sections,
        rubrics=rubrics,
        questions=questions,
        artifacts=artifacts,
        profiles=[str(item) for item in vertical.get("profiles", []) if str(item).strip()] if isinstance(vertical.get("profiles"), list) else [],
        modules=[str(item) for item in vertical.get("modules", []) if str(item).strip()] if isinstance(vertical.get("modules"), list) else [],
        examples=[str(item) for item in vertical.get("examples", []) if str(item).strip()] if isinstance(vertical.get("examples"), list) else [],
    )


def _pack_payload(pack: VerticalPack) -> dict[str, object]:
    return {
        "vertical": {
            "schema_version": VERTICAL_SCHEMA_VERSION,
            "id": pack.vertical_id,
            "name": pack.name,
            "version": pack.version,
            "description": pack.description,
            "extends": pack.extends,
            "sections": [
                {
                    "id": section.section_id,
                    "title": section.title,
                    "purpose": section.purpose,
                    "required": section.required,
                    "priority": section.priority,
                }
                for section in pack.sections
            ],
            "rubrics": [
                {
                    "id": rubric.rubric_id,
                    "title": rubric.title,
                    "section_id": rubric.section_id,
                    "required": rubric.required,
                    "keywords": rubric.keywords,
                }
                for rubric in pack.rubrics
            ],
            "questions": [
                {
                    "id": question.question_id,
                    "section_id": question.section_id,
                    "priority": question.priority,
                    "question": question.question,
                    "rationale": question.rationale,
                }
                for question in pack.questions
            ],
            "artifacts": [
                {
                    "id": artifact.artifact_id,
                    "title": artifact.title,
                    "section_ids": artifact.section_ids,
                    "required": artifact.required,
                }
                for artifact in pack.artifacts
            ],
            "profiles": pack.profiles,
            "modules": pack.modules,
            "examples": pack.examples,
        }
    }


def _normalise_pack_payload(payload: dict[str, object]) -> dict[str, object]:
    if "vertical" in payload:
        return payload
    candidate = payload.get("vertical_candidate")
    if not isinstance(candidate, dict):
        return payload
    candidate_payload = candidate.get("candidate")
    if isinstance(candidate_payload, dict):
        return {"vertical": candidate_payload}
    return payload


def _vertical_pack_issues(payload: dict[str, object]) -> list[VerticalValidationIssue]:
    issues: list[VerticalValidationIssue] = []

    def error(field: str, message: str) -> None:
        issues.append(VerticalValidationIssue("error", field, message))

    vertical = payload.get("vertical")
    if not isinstance(vertical, dict):
        error("vertical", "expected mapping")
        return issues
    for field in ("id", "name", "version", "description"):
        if not str(vertical.get(field) or "").strip():
            error(f"vertical.{field}", "required")
    section_items = _mapping_list(vertical.get("sections"))
    if not section_items:
        error("vertical.sections", "at least one section is required")
    section_ids = _ids(section_items, "vertical.sections", error)
    for index, item in enumerate(section_items):
        for field in ("id", "title", "purpose"):
            if not str(item.get(field) or "").strip():
                error(f"vertical.sections[{index}].{field}", "required")
    rubric_items = _mapping_list(vertical.get("rubrics"))
    _ids(rubric_items, "vertical.rubrics", error)
    for index, item in enumerate(rubric_items):
        if not str(item.get("id") or "").strip():
            error(f"vertical.rubrics[{index}].id", "required")
        section_id = str(item.get("section_id") or "").strip()
        if not section_id:
            error(f"vertical.rubrics[{index}].section_id", "required")
        elif section_id not in section_ids:
            error(f"vertical.rubrics[{index}].section_id", f"unknown section `{section_id}`")
    if not rubric_items:
        error("vertical.rubrics", "at least one rubric is required")
    question_items = _mapping_list(vertical.get("questions"))
    _ids(question_items, "vertical.questions", error)
    for index, item in enumerate(question_items):
        if not str(item.get("id") or "").strip():
            error(f"vertical.questions[{index}].id", "required")
        section_id = str(item.get("section_id") or "").strip()
        if not section_id:
            error(f"vertical.questions[{index}].section_id", "required")
        elif section_id not in section_ids:
            error(f"vertical.questions[{index}].section_id", f"unknown section `{section_id}`")
        priority = str(item.get("priority") or "medium")
        if priority not in QUESTION_PRIORITIES:
            error(f"vertical.questions[{index}].priority", f"must be one of {sorted(QUESTION_PRIORITIES)}")
        if not str(item.get("question") or "").strip():
            error(f"vertical.questions[{index}].question", "required")
    if not question_items:
        error("vertical.questions", "at least one blocking question is required")
    artifact_items = _mapping_list(vertical.get("artifacts"))
    _ids(artifact_items, "vertical.artifacts", error)
    for index, item in enumerate(artifact_items):
        if not str(item.get("id") or "").strip():
            error(f"vertical.artifacts[{index}].id", "required")
        section_ids_value = item.get("section_ids", [])
        if not isinstance(section_ids_value, list):
            error(f"vertical.artifacts[{index}].section_ids", "must be a list")
            continue
        for section_id in section_ids_value:
            text = str(section_id)
            if text not in section_ids:
                error(f"vertical.artifacts[{index}].section_ids", f"unknown section `{text}`")
    if not artifact_items:
        error("vertical.artifacts", "at least one expected artifact is required")
    return issues


def _compose_pack(pack: VerticalPack, packs: dict[str, VerticalPack]) -> VerticalPack:
    if not pack.extends:
        return pack
    base = packs.get(pack.extends)
    if base is None:
        raise ValueError(f"Unknown base vertical `{pack.extends}` for `{pack.vertical_id}`.")
    composed_base = _compose_pack(base, packs)
    return VerticalPack(
        vertical_id=pack.vertical_id,
        name=pack.name,
        version=pack.version,
        description=pack.description,
        extends=pack.extends,
        source=pack.source,
        path=pack.path,
        sections=_merge_by_id(composed_base.sections, pack.sections, lambda item: item.section_id),
        rubrics=_merge_by_id(composed_base.rubrics, pack.rubrics, lambda item: item.rubric_id),
        questions=_merge_by_id(composed_base.questions, pack.questions, lambda item: item.question_id),
        artifacts=_merge_by_id(composed_base.artifacts, pack.artifacts, lambda item: item.artifact_id),
        profiles=list(dict.fromkeys([*composed_base.profiles, *pack.profiles])),
        modules=list(dict.fromkeys([*composed_base.modules, *pack.modules])),
        examples=list(dict.fromkeys([*composed_base.examples, *pack.examples])),
    )


def _merge_by_id(base: list[T], overlay: list[T], key: Callable[[T], str]) -> list[T]:
    merged: dict[str, T] = {}
    order: list[str] = []
    for item in [*base, *overlay]:
        item_id = key(item)
        if item_id not in merged:
            order.append(item_id)
        merged[item_id] = item
    return [merged[item_id] for item_id in order]


def _mapping_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _ids(items: list[dict[str, object]], field: str, error: Callable[[str, str], None]) -> set[str]:
    seen: set[str] = set()
    ids: set[str] = set()
    for index, item in enumerate(items):
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            continue
        if item_id in seen:
            error(f"{field}[{index}].id", f"duplicate id `{item_id}`")
        seen.add(item_id)
        ids.add(item_id)
    return ids


def _candidate_pack(
    *,
    vertical_id: str,
    name: str,
    description: str,
    sections: list[tuple[str, str, str]],
    questions: list[tuple[str, str, str]],
    artifacts: list[tuple[str, str, list[str]]],
) -> VerticalPack:
    vertical_sections = [
        VerticalSection(section_id=section_id, title=title, purpose=purpose, required=True, priority=(index + 1) * 10)
        for index, (section_id, title, purpose) in enumerate(sections)
    ]
    rubrics = [
        VerticalRubric(
            rubric_id=f"{section_id}_coverage",
            title=f"{title} Coverage",
            section_id=section_id,
            required=True,
            keywords=_important_words(title + " " + purpose),
        )
        for section_id, title, purpose in sections
    ]
    vertical_questions = [
        VerticalQuestion(
            question_id=question_id,
            section_id=section_id,
            question=question,
            priority="high",
            rationale="Needed to define the custom vertical candidate.",
        )
        for question_id, section_id, question in questions
    ]
    vertical_artifacts = [
        VerticalArtifact(artifact_id=artifact_id, title=title, section_ids=section_ids, required=True)
        for artifact_id, title, section_ids in artifacts
    ]
    return VerticalPack(
        vertical_id=vertical_id,
        name=name,
        version="0.1.0",
        description=description,
        extends=BASE_PROJECT_VERTICAL_ID,
        source="candidate",
        path=None,
        sections=vertical_sections,
        rubrics=rubrics,
        questions=vertical_questions,
        artifacts=vertical_artifacts,
    )


def _normalize_vertical_id(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        raise ValueError("Vertical ID is required.")
    return normalized


def _title_from_slug(value: str) -> str:
    return " ".join(part.capitalize() for part in value.replace("-", "_").split("_") if part)


def _important_words(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z_]{3,}", text.lower())
    stop = {
        "acceptance",
        "context",
        "criteria",
        "decision",
        "define",
        "from",
        "goals",
        "must",
        "pending",
        "problem",
        "project",
        "proposal",
        "should",
        "that",
        "this",
        "what",
        "which",
        "will",
        "with",
    }
    return [word.replace("_", " ") for word in words if word not in stop][:12]


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"YAML document must be a mapping: {path}")
    return data


def dataclass_payload(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value

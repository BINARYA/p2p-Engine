from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Mapping

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.project_questions import (
    ProjectQuestionApplicability,
    ProjectQuestionState,
)
from p2p_engine.core.project_verticals import (
    ProjectDefinitionHistoryEntry,
    ProjectDefinitionOrphan,
    ProjectDefinitionState,
    VerticalMigrationCandidate,
)
from p2p_engine.core.vertical_transition_plan import VerticalTransitionPlan
from p2p_engine.foundation.files import yaml_dump
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.services.project_verticals import (
    ProjectVerticalService,
    project_definition_state_from_payload,
    project_definition_state_payload,
)
from p2p_engine.services.vertical_transition_analysis import TransitionAnalysis


class VerticalTransitionMaterializationService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        vertical_service: ProjectVerticalService,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.vertical_service = vertical_service

    def materialize(
        self,
        analysis: TransitionAnalysis,
        *,
        plan: VerticalTransitionPlan,
        actor: str,
    ) -> VerticalMigrationCandidate:
        candidate = analysis.baseline
        decisions = {item.source.ref: item for item in plan.decisions}
        definition = self._definition(analysis, decisions=decisions, actor=actor)
        files = dict(candidate.candidate_files)
        files[".p2p/project/definition.yml"] = yaml_dump(
            project_definition_state_payload(definition)
        ).encode("utf-8")
        files[".p2p/project/rubrics.yml"] = yaml_dump(
            self._rubrics(analysis, decisions=decisions)
        ).encode("utf-8")
        files[".p2p/project/questions.yml"] = self._questions(
            analysis,
            definition=definition,
            decisions=decisions,
            actor=actor,
        )
        materialized = replace(candidate, candidate_files=files, reconciliation_required=False)
        self.vertical_service.validate_migration_candidate(materialized)
        return materialized

    def _definition(
        self,
        analysis: TransitionAnalysis,
        *,
        decisions: Mapping[str, object],
        actor: str,
    ) -> ProjectDefinitionState:
        current = analysis.snapshot.definition
        assert current is not None
        payload = load_yaml(analysis.baseline.candidate_files[".p2p/project/definition.yml"])
        if not isinstance(payload, dict):
            raise ValueError("P2P_VERTICAL_INVALID_DEFINITION_CANDIDATE: expected mapping")
        target = project_definition_state_from_payload(
            payload,
            path=Path(".p2p/project/definition.yml"),
        )
        target_sections = {section.section_id: section for section in target.sections}
        existing_orphans = list(current.orphans)
        orphans = list(existing_orphans)

        for source_section in current.sections:
            for field_id, field in sorted(source_section.fields.items()):
                if not _meaningful(field.value):
                    continue
                source_ref = f"definition_field:{source_section.section_id}.{field_id}"
                decision = decisions.get(source_ref)
                target_ref = (
                    getattr(getattr(decision, "target", None), "ref", "")
                    if decision is not None and getattr(decision, "action", "") == "map"
                    else source_ref
                    if decision is None
                    else ""
                )
                if target_ref:
                    section_id, target_field_id = target_ref.split(":", 1)[1].split(".", 1)
                    section = target_sections[section_id]
                    section.fields[target_field_id] = replace(field, field_id=target_field_id)
                    section.missing_required_fields = [
                        item for item in section.missing_required_fields if item != target_field_id
                    ]
                else:
                    orphans.append(
                        _orphan(
                            current=current,
                            source_section_id=source_section.section_id,
                            source_field_id=field_id,
                            value=field.value,
                            source=field.source,
                            updated_at=field.updated_at,
                            target_vertical=analysis.impact.target.coordinate,
                        )
                    )
            for assumption in source_section.assumptions:
                source_ref = (
                    f"definition_assumption:{source_section.section_id}/{assumption.assumption_id}"
                )
                decision = decisions.get(source_ref)
                target_ref = (
                    getattr(getattr(decision, "target", None), "ref", "")
                    if decision is not None and getattr(decision, "action", "") == "map"
                    else source_ref
                    if decision is None
                    else ""
                )
                if target_ref:
                    section_id, assumption_id = target_ref.split(":", 1)[1].split("/", 1)
                    target_sections[section_id].assumptions.append(
                        replace(assumption, assumption_id=assumption_id)
                    )
                else:
                    orphans.append(
                        _orphan(
                            current=current,
                            source_section_id=source_section.section_id,
                            source_field_id=f"assumption/{assumption.assumption_id}",
                            value=assumption.__dict__,
                            source="project_definition",
                            updated_at="",
                            target_vertical=analysis.impact.target.coordinate,
                        )
                    )
            for blocker in source_section.blockers:
                source_ref = f"definition_blocker:{source_section.section_id}/{blocker.blocker_id}"
                decision = decisions.get(source_ref)
                target_ref = (
                    getattr(getattr(decision, "target", None), "ref", "")
                    if decision is not None and getattr(decision, "action", "") == "map"
                    else source_ref
                    if decision is None
                    else ""
                )
                if target_ref:
                    section_id, blocker_id = target_ref.split(":", 1)[1].split("/", 1)
                    target_sections[section_id].blockers.append(
                        replace(blocker, blocker_id=blocker_id)
                    )
                else:
                    orphans.append(
                        _orphan(
                            current=current,
                            source_section_id=source_section.section_id,
                            source_field_id=f"blocker/{blocker.blocker_id}",
                            value=blocker.__dict__,
                            source="project_definition",
                            updated_at="",
                            target_vertical=analysis.impact.target.coordinate,
                        )
                    )

        for section in target_sections.values():
            if section.blockers:
                section.status = "blocked"
            elif not section.missing_required_fields:
                section.status = "complete"
            elif section.fields or section.assumptions:
                section.status = "partial"
        return replace(
            target,
            sections=list(target_sections.values()),
            orphans=orphans,
            history=[
                *current.history,
                ProjectDefinitionHistoryEntry(
                    at=date.today().isoformat(),
                    actor=actor,
                    operation="migrate_project_vertical",
                ),
            ],
        )

    @staticmethod
    def _rubrics(
        analysis: TransitionAnalysis,
        *,
        decisions: Mapping[str, object],
    ) -> dict[str, object]:
        payload = load_yaml(analysis.baseline.candidate_files[".p2p/project/rubrics.yml"])
        if not isinstance(payload, dict) or not isinstance(payload.get("criteria"), list):
            raise ValueError("P2P_VERTICAL_RUBRIC_RECONCILIATION_BLOCKED: invalid target baseline")
        criteria = [dict(item) for item in payload["criteria"] if isinstance(item, dict)]
        targets = {str(item.get("id") or ""): item for item in criteria}
        impact_by_ref = {item.ref: item for item in analysis.impact.rubrics.items}
        for source in analysis.snapshot.rubrics:
            rubric_id = str(source.get("id") or "")
            if not rubric_id:
                continue
            source_ref = f"rubric:{rubric_id}"
            impact = impact_by_ref.get(source_ref)
            decision = decisions.get(source_ref)
            if decision is None and impact is not None and impact.disposition.startswith("preserved"):
                target = targets[rubric_id]
                _copy_rubric_customization(source, target)
                continue
            if decision is None:
                continue
            if getattr(decision, "action", "") == "map":
                target_id = getattr(getattr(decision, "target", None), "ref", "").split(":", 1)[1]
                target = targets.get(target_id)
                if target is None:
                    raise ValueError(
                        f"P2P_VERTICAL_RUBRIC_RECONCILIATION_BLOCKED: unknown target rubric:{target_id}"
                    )
                _copy_rubric_customization(source, target)
            else:
                orphan = dict(source)
                orphan.update(
                    {
                        "orphaned": True,
                        "unmapped_from_previous_vertical": True,
                        "counts_toward_active_baseline": False,
                    }
                )
                criteria.append(orphan)
        payload["criteria"] = criteria
        active = [item for item in criteria if item.get("counts_toward_active_baseline") is not False]
        selected_scope = payload.get("selected_scope")
        if isinstance(selected_scope, dict):
            selected_scope["enabled"] = sum(1 for item in active if item.get("enabled") is not False)
            selected_scope["disabled"] = sum(1 for item in active if item.get("enabled") is False)
        return payload

    def _questions(
        self,
        analysis: TransitionAnalysis,
        *,
        definition: ProjectDefinitionState,
        decisions: Mapping[str, object],
        actor: str,
    ) -> bytes:
        service = ProjectQuestionStateService(root=self.root, p2p_dir=self.p2p_dir)
        current = analysis.snapshot.questions
        if current is None:
            project_id = "project"
            seeded = service.seed_from_definition(
                project_id=project_id,
                definition=definition,
                pack=analysis.target_pack,
                lock_checksum=analysis.baseline.checksum,
                actor=actor,
                audit_at=date.today().isoformat(),
            ).artifact
            return service.candidate_bytes(seeded)
        if analysis.question_candidate is not None:
            reconciled = analysis.question_candidate.artifact
        else:
            question_decisions = {
                ref: item for ref, item in decisions.items() if ref.startswith("question:")
            }
            if not question_decisions:
                raise ValueError(
                    "P2P_VERTICAL_QUESTION_RECONCILIATION_BLOCKED: explicit question decisions are required"
                )
            reconciled = service.seed_from_definition(
                project_id=current.project_id,
                definition=definition,
                pack=analysis.target_pack,
                lock_checksum=analysis.baseline.checksum,
                actor=actor,
                audit_at=date.today().isoformat(),
            ).artifact
        questions = {item.question_id: item for item in reconciled.questions}
        current_questions = {item.question_id: item for item in current.questions}
        for source_ref, decision in decisions.items():
            if not source_ref.startswith("question:"):
                continue
            source_id = source_ref.split(":", 1)[1]
            source = current_questions.get(source_id)
            if source is None:
                raise ValueError(
                    f"P2P_VERTICAL_QUESTION_RECONCILIATION_BLOCKED: unknown source {source_ref}"
                )
            if getattr(decision, "action", "") == "preserve_as_orphan":
                if source_id not in questions:
                    questions[source_id] = replace(
                        source,
                        applicability=ProjectQuestionApplicability.TARGET_REMOVED,
                        updated_by=actor,
                    )
                continue
            target_ref = getattr(getattr(decision, "target", None), "ref", "")
            target_id = target_ref.split(":", 1)[1]
            target = questions.get(target_id)
            if target is None:
                raise ValueError(
                    f"P2P_VERTICAL_QUESTION_RECONCILIATION_BLOCKED: unknown target {target_ref}"
                )
            if source.answers:
                probe = replace(target, answer_contract=target.answer_contract)
                try:
                    service.validate_answer_values(probe, source.answers[-1].values)
                except ValueError as exc:
                    raise ValueError(
                        "P2P_VERTICAL_QUESTION_RECONCILIATION_BLOCKED: target answer contract "
                        f"is incompatible for {source_ref}"
                    ) from exc
            questions[target_id] = replace(
                target,
                state=source.state,
                answers=source.answers,
                applications=source.applications,
                transitions=source.transitions,
                updated_by=actor,
            )
            questions[source_id] = replace(
                source,
                state=ProjectQuestionState.SUPERSEDED,
                applicability=ProjectQuestionApplicability.TARGET_REMOVED,
                superseded_by=target_id,
                updated_by=actor,
            )
        ordered = tuple(sorted(questions.values(), key=lambda item: item.question_id))
        artifact = replace(
            reconciled,
            groups=service._groups_for_questions(analysis.target_pack.vertical_id, ordered),
            questions=ordered,
            updated_by=actor,
        )
        return service.candidate_bytes(artifact)


def _copy_rubric_customization(source: Mapping[str, object], target: dict[str, object]) -> None:
    for key in ("title", "keywords", "enabled"):
        if key in source:
            target[key] = source[key]


def _orphan(
    *,
    current: ProjectDefinitionState,
    source_section_id: str,
    source_field_id: str,
    value: object,
    source: str,
    updated_at: str,
    target_vertical: str,
) -> ProjectDefinitionOrphan:
    orphan_id = "ORPH-" + semantic_sha256(
        {
            "source_vertical": current.vertical_id,
            "source_section_id": source_section_id,
            "source_field_id": source_field_id,
            "value": value,
            "target_vertical": target_vertical,
        }
    )[:12]
    return ProjectDefinitionOrphan(
        orphan_id=orphan_id,
        source_vertical=current.vertical_id,
        source_section_id=source_section_id,
        source_field_id=source_field_id,
        value=value,
        source=source,
        updated_at=updated_at,
        reason="explicit_transition_orphan",
        target_vertical=target_vertical,
    )


def _meaningful(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True

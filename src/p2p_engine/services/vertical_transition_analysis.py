from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Mapping

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.project_questions import ProjectQuestionArtifact
from p2p_engine.core.project_verticals import VerticalMigrationCandidate, VerticalPack
from p2p_engine.core.vertical_transition_impact import (
    AdoptionImpact,
    ArtifactDisposition,
    ArtifactImpact,
    BoundedCollection,
    DomainReference,
    EvidenceDisposition,
    EvidenceKind,
    EvidenceTransition,
    IssueSeverity,
    LockImpact,
    MigrationImpact,
    QuestionImpact,
    RequiredDecision,
    RubricImpact,
    StructuralImpact,
    TransitionIssue,
    VERTICAL_TRANSITION_COLLECTION_LIMIT,
    VERTICAL_TRANSITION_IMPACT_CONTRACT,
    VERTICAL_TRANSITION_TOTAL_ITEM_LIMIT,
    VerticalIdentity,
    bounded_strings,
    impact_fingerprint,
)
from p2p_engine.core.vertical_transition_plan import VerticalTransitionPlan
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.project_questions import (
    ProjectQuestionReconciliationCandidate,
    ProjectQuestionStateService,
)
from p2p_engine.services.project_verticals import (
    ProjectVerticalService,
    project_definition_state_from_payload,
    project_definition_state_payload,
)
from p2p_engine.services.vertical_evidence_classifier import VerticalEvidenceSnapshot


@dataclass(frozen=True)
class TransitionAnalysis:
    impact: MigrationImpact
    snapshot: VerticalEvidenceSnapshot
    source_pack: VerticalPack
    target_pack: VerticalPack
    baseline: VerticalMigrationCandidate
    required_decisions: tuple[RequiredDecision, ...]
    question_candidate: ProjectQuestionReconciliationCandidate | None


class VerticalTransitionAnalysisService:
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

    def adoption_impact(
        self,
        *,
        snapshot: VerticalEvidenceSnapshot,
        coordinate: str,
        baseline: VerticalMigrationCandidate,
    ) -> AdoptionImpact:
        target = self._identity_for_target(coordinate, baseline)
        target_pack = self.vertical_service.resolve_pack(coordinate).pack
        dependency_additions = _pack_dependencies(target_pack)
        source = self._source_identity(snapshot)
        issues: list[TransitionIssue] = []
        if not snapshot.source_state.adoption_eligible:
            issues.append(
                TransitionIssue(
                    code="P2P_VERTICAL_ADOPTION_REQUIRES_MIGRATION",
                    severity=IssueSeverity.BLOCKER,
                    category="source_state",
                    reference=source.coordinate if source else "project",
                    recovery_action="Run project vertical migrate preview for the target coordinate.",
                )
            )
        if len(dependency_additions) > VERTICAL_TRANSITION_COLLECTION_LIMIT:
            issues.append(
                TransitionIssue(
                    code="P2P_VERTICAL_IMPACT_LIMIT_EXCEEDED",
                    severity=IssueSeverity.BLOCKER,
                    category="impact_limit",
                    reference=coordinate,
                    recovery_action="Reduce the target vertical dependency scope before adopting.",
                )
            )
        artifacts = self._artifact_impacts(baseline)
        seed = {
            "contract_version": VERTICAL_TRANSITION_IMPACT_CONTRACT,
            "operation": "adopt",
            "source_state": snapshot.source_state.to_dict(),
            "source_state_fingerprint_sha256": _snapshot_fingerprint(snapshot),
            "source": source.to_dict() if source else None,
            "target": target.to_dict(),
            "artifacts": [item.to_dict() for item in artifacts],
            "blockers": [item.to_dict() for item in issues],
        }
        return AdoptionImpact(
            analysis_fingerprint_sha256=impact_fingerprint(seed),
            source_state=snapshot.source_state,
            source=source,
            target=target,
            lock=LockImpact(
                before=source,
                after=target,
                dependency_additions=_bounded(
                    dependency_additions,
                    key=lambda item: item["coordinate"],
                ),
            ),
            artifacts=_bounded(artifacts, key=lambda item: item.kind),
            blockers=_bounded(issues, key=lambda item: (item.code, item.reference)),
            warnings=_bounded((), key=lambda item: item.code),
        )

    def migration_analysis(
        self,
        *,
        snapshot: VerticalEvidenceSnapshot,
        coordinate: str,
        baseline: VerticalMigrationCandidate,
        actor: str,
        plan: VerticalTransitionPlan | None,
    ) -> TransitionAnalysis:
        if snapshot.definition is None or snapshot.resolved is None or snapshot.lock is None:
            raise ValueError(
                "P2P_VERTICAL_MIGRATION_REQUIRES_DEFINITION: use adopt for an empty project"
            )
        source_pack = snapshot.resolved.pack
        target_resolved = self.vertical_service.resolve_pack(coordinate)
        target_pack = target_resolved.pack
        source_identity = self._source_identity(snapshot)
        assert source_identity is not None
        target_identity = self._identity_for_target(coordinate, baseline)

        structures = self._structural_impacts(source_pack, target_pack)
        evidence, decisions = self._definition_impacts(
            snapshot=snapshot,
            source_pack=source_pack,
            target_pack=target_pack,
            target_coordinate=coordinate,
        )
        rubrics, rubric_decisions = self._rubric_impacts(
            snapshot=snapshot,
            source_pack=source_pack,
            target_pack=target_pack,
            target_coordinate=coordinate,
        )
        decisions.extend(rubric_decisions)
        question_impact, question_candidate, question_decisions, question_issues = self._question_impacts(
            snapshot=snapshot,
            target_pack=target_pack,
            baseline=baseline,
            actor=actor,
            target_coordinate=coordinate,
        )
        decisions.extend(question_decisions)

        decisions = sorted(decisions, key=lambda item: item.decision_id)
        seed = {
            "contract_version": VERTICAL_TRANSITION_IMPACT_CONTRACT,
            "operation": "migrate",
            "source_state": snapshot.source_state.to_dict(),
            "source_state_fingerprint_sha256": _snapshot_fingerprint(snapshot),
            "source": source_identity.to_dict(),
            "target": target_identity.to_dict(),
            "sections": [item.to_dict() for item in structures],
            "evidence_transitions": [item.to_dict() for item in evidence],
            "rubrics": [item.to_dict() for item in rubrics],
            "questions": question_impact.to_dict(),
            "required_decisions": [item.to_dict() for item in decisions],
        }
        analysis_fingerprint = impact_fingerprint(seed)
        normalized_plan = self._validate_plan(
            plan,
            analysis_fingerprint=analysis_fingerprint,
            decisions=decisions,
            target_pack=target_pack,
            target_question_ids=self._target_question_ids(baseline, target_pack),
        )
        evidence = self._apply_plan_to_evidence(evidence, normalized_plan)
        rubrics = self._apply_plan_to_rubrics(rubrics, normalized_plan)

        blockers = list(question_issues)
        if not snapshot.source_state.migration_required:
            blockers.append(
                TransitionIssue(
                    code="P2P_VERTICAL_MIGRATION_REQUIRES_ADOPTION",
                    severity=IssueSeverity.BLOCKER,
                    category="source_state",
                    reference=source_identity.coordinate,
                    recovery_action="Use project vertical adopt for an empty project.",
                )
            )
        if decisions and normalized_plan is None:
            blockers.append(
                TransitionIssue(
                    code="P2P_VERTICAL_DECISION_REQUIRED",
                    severity=IssueSeverity.BLOCKER,
                    category="transition_plan",
                    reference=coordinate,
                    recovery_action="Create a complete transition plan and re-run preview with --mapping.",
                )
            )

        artifacts = self._artifact_impacts(baseline)
        dependency_additions = _dependency_delta(target_pack, source_pack)
        dependency_removals = _dependency_delta(source_pack, target_pack)
        collections = [structures, evidence, rubrics, decisions, artifacts]
        if _transition_material_exceeds_limit(
            collections,
            question_impact=question_impact,
            additional_counts=(len(dependency_additions), len(dependency_removals)),
        ):
            blockers.append(
                TransitionIssue(
                    code="P2P_VERTICAL_IMPACT_LIMIT_EXCEEDED",
                    severity=IssueSeverity.BLOCKER,
                    category="impact_limit",
                    reference=coordinate,
                    recovery_action="Reduce the vertical transition scope before applying.",
                )
            )

        impact = MigrationImpact(
            analysis_fingerprint_sha256=analysis_fingerprint,
            plan_fingerprint_sha256=normalized_plan.fingerprint_sha256 if normalized_plan else None,
            source_state=snapshot.source_state,
            source=source_identity,
            target=target_identity,
            sections=_bounded(structures, key=lambda item: (item.kind, item.ref)),
            evidence_transitions=_bounded(evidence, key=lambda item: item.source.ref),
            rubrics=_bounded(rubrics, key=lambda item: item.ref),
            questions=question_impact,
            lock=LockImpact(
                before=source_identity,
                after=target_identity,
                dependency_additions=_bounded(
                    dependency_additions,
                    key=lambda item: item["coordinate"],
                ),
                dependency_removals=_bounded(
                    dependency_removals,
                    key=lambda item: item["coordinate"],
                ),
            ),
            artifacts=_bounded(artifacts, key=lambda item: item.kind),
            required_decisions=_bounded(decisions, key=lambda item: item.decision_id),
            blockers=_bounded(blockers, key=lambda item: (item.code, item.reference)),
            warnings=_bounded((), key=lambda item: item.code),
        )
        return TransitionAnalysis(
            impact=impact,
            snapshot=snapshot,
            source_pack=source_pack,
            target_pack=target_pack,
            baseline=baseline,
            required_decisions=tuple(decisions),
            question_candidate=question_candidate,
        )

    def _definition_impacts(
        self,
        *,
        snapshot: VerticalEvidenceSnapshot,
        source_pack: VerticalPack,
        target_pack: VerticalPack,
        target_coordinate: str,
    ) -> tuple[list[EvidenceTransition], list[RequiredDecision]]:
        assert snapshot.definition is not None
        source_fields = _pack_fields(source_pack)
        target_fields = _pack_fields(target_pack)
        target_sections = {item.section_id for item in target_pack.sections}
        impacts: list[EvidenceTransition] = []
        decisions: list[RequiredDecision] = []

        for section in snapshot.definition.sections:
            for field_id, field in sorted(section.fields.items()):
                if not _meaningful(field.value):
                    continue
                source_ref = DomainReference(
                    EvidenceKind.DEFINITION_FIELD,
                    f"definition_field:{section.section_id}.{field_id}",
                )
                field_key = f"{section.section_id}.{field_id}"
                if field_key in target_fields and source_fields.get(field_key) == target_fields[field_key]:
                    impacts.append(
                        EvidenceTransition(
                            source=source_ref,
                            target=source_ref,
                            disposition=EvidenceDisposition.PRESERVED,
                            provenance_present=bool(field.source or field.updated_at),
                        )
                    )
                else:
                    decision = _required_decision(source_ref, target_coordinate)
                    decisions.append(decision)
                    impacts.append(
                        EvidenceTransition(
                            source=source_ref,
                            disposition=EvidenceDisposition.DECISION_REQUIRED,
                            provenance_present=bool(field.source or field.updated_at),
                            decision_id=decision.decision_id,
                        )
                    )
            for assumption in sorted(section.assumptions, key=lambda item: item.assumption_id):
                source_ref = DomainReference(
                    EvidenceKind.DEFINITION_ASSUMPTION,
                    f"definition_assumption:{section.section_id}/{assumption.assumption_id}",
                )
                if section.section_id in target_sections:
                    impacts.append(
                        EvidenceTransition(
                            source=source_ref,
                            target=source_ref,
                            disposition=EvidenceDisposition.PRESERVED,
                        )
                    )
                else:
                    decision = _required_decision(source_ref, target_coordinate)
                    decisions.append(decision)
                    impacts.append(
                        EvidenceTransition(
                            source=source_ref,
                            disposition=EvidenceDisposition.DECISION_REQUIRED,
                            decision_id=decision.decision_id,
                        )
                    )
            for blocker in sorted(section.blockers, key=lambda item: item.blocker_id):
                source_ref = DomainReference(
                    EvidenceKind.DEFINITION_BLOCKER,
                    f"definition_blocker:{section.section_id}/{blocker.blocker_id}",
                )
                if section.section_id in target_sections:
                    impacts.append(
                        EvidenceTransition(
                            source=source_ref,
                            target=source_ref,
                            disposition=EvidenceDisposition.PRESERVED,
                        )
                    )
                else:
                    decision = _required_decision(source_ref, target_coordinate)
                    decisions.append(decision)
                    impacts.append(
                        EvidenceTransition(
                            source=source_ref,
                            disposition=EvidenceDisposition.DECISION_REQUIRED,
                            decision_id=decision.decision_id,
                        )
                    )
        for orphan in sorted(snapshot.definition.orphans, key=lambda item: item.orphan_id):
            source_ref = DomainReference(
                EvidenceKind.DEFINITION_ORPHAN,
                f"definition_orphan:{orphan.orphan_id}",
            )
            impacts.append(
                EvidenceTransition(
                    source=source_ref,
                    disposition=EvidenceDisposition.PRESERVE_AS_ORPHAN,
                    provenance_present=True,
                )
            )
        return impacts, decisions

    def _rubric_impacts(
        self,
        *,
        snapshot: VerticalEvidenceSnapshot,
        source_pack: VerticalPack,
        target_pack: VerticalPack,
        target_coordinate: str,
    ) -> tuple[list[RubricImpact], list[RequiredDecision]]:
        source_defaults = {item.rubric_id: _rubric_pack_signature(item) for item in source_pack.rubrics}
        target_defaults = {item.rubric_id: _rubric_pack_signature(item) for item in target_pack.rubrics}
        impacts: list[RubricImpact] = []
        decisions: list[RequiredDecision] = []
        current_ids: set[str] = set()
        for item in snapshot.rubrics:
            rubric_id = str(item.get("id") or "")
            if not rubric_id:
                continue
            current_ids.add(rubric_id)
            source_ref = DomainReference(EvidenceKind.RUBRIC, f"rubric:{rubric_id}")
            source_signature = source_defaults.get(rubric_id)
            target_signature = target_defaults.get(rubric_id)
            current_signature = _rubric_payload_signature(item)
            customized = (
                source_signature is None
                or current_signature != source_signature
                or item.get("orphaned") is True
            )
            if target_signature is not None and source_signature == target_signature:
                impacts.append(
                    RubricImpact(
                        ref=source_ref.ref,
                        disposition="preserved_customization" if customized else "preserved_default",
                        target_ref=source_ref.ref,
                    )
                )
            elif customized:
                decision = _required_decision(source_ref, target_coordinate)
                decisions.append(decision)
                impacts.append(
                    RubricImpact(
                        ref=source_ref.ref,
                        disposition="decision_required",
                        decision_id=decision.decision_id,
                    )
                )
            else:
                impacts.append(RubricImpact(ref=source_ref.ref, disposition="removed"))
        for rubric_id in sorted(set(target_defaults) - current_ids):
            impacts.append(RubricImpact(ref=f"rubric:{rubric_id}", disposition="added"))
        return impacts, decisions

    def _question_impacts(
        self,
        *,
        snapshot: VerticalEvidenceSnapshot,
        target_pack: VerticalPack,
        baseline: VerticalMigrationCandidate,
        actor: str,
        target_coordinate: str,
    ) -> tuple[QuestionImpact, ProjectQuestionReconciliationCandidate | None, list[RequiredDecision], list[TransitionIssue]]:
        empty = QuestionImpact(*(bounded_strings(()) for _ in range(7)))
        if snapshot.questions is None or snapshot.definition is None:
            return empty, None, [], []
        definition_payload = load_yaml(baseline.candidate_files[".p2p/project/definition.yml"])
        if not isinstance(definition_payload, dict):
            raise ValueError("P2P_VERTICAL_INVALID_DEFINITION_CANDIDATE: expected mapping")
        definition = project_definition_state_from_payload(
            definition_payload,
            path=Path(".p2p/project/definition.yml"),
        )
        question_service = ProjectQuestionStateService(root=self.root, p2p_dir=self.p2p_dir)
        project_id = snapshot.questions.project_id
        try:
            candidate = question_service.reconcile_candidate(
                current=snapshot.questions,
                project_id=project_id,
                definition=definition,
                pack=target_pack,
                lock_checksum=baseline.checksum,
                actor=actor,
                audit_at=date.today().isoformat(),
            )
        except ValueError:
            owner_ids = sorted(
                item.question_id
                for item in snapshot.questions.questions
                if item.answers
                or item.applications
                or item.state.value in {"answered", "applied", "deferred", "muted"}
            )
            decisions = [
                _required_decision(
                    DomainReference(EvidenceKind.QUESTION, f"question:{question_id}"),
                    target_coordinate,
                )
                for question_id in owner_ids
            ]
            return (
                replace(
                    empty,
                    inactive_owner_evidence=bounded_strings(
                        f"question:{item}" for item in owner_ids
                    ),
                    owner_review_required=bounded_strings(
                        f"question:{item}" for item in owner_ids
                    ),
                ),
                None,
                decisions,
                [],
            )
        owner_ids = {
            item.question_id
            for item in snapshot.questions.questions
            if item.answers
            or item.applications
            or item.state.value in {"answered", "applied", "deferred", "muted"}
        }
        review_ids = sorted(
            owner_ids
            & set(
                (*candidate.inactive_evidence_ids, *candidate.superseded_ids, *candidate.owner_evidence_ids)
            )
        )
        decisions = [
            _required_decision(
                DomainReference(EvidenceKind.QUESTION, f"question:{question_id}"),
                target_coordinate,
            )
            for question_id in review_ids
        ]
        return (
            QuestionImpact(
                preserved=bounded_strings(f"question:{item}" for item in candidate.preserved_ids),
                revised=bounded_strings(f"question:{item}" for item in candidate.revised_ids),
                created=bounded_strings(f"question:{item}" for item in candidate.created_ids),
                retired=bounded_strings(f"question:{item}" for item in candidate.retired_ids),
                superseded=bounded_strings(f"question:{item}" for item in candidate.superseded_ids),
                inactive_owner_evidence=bounded_strings(
                    f"question:{item}" for item in candidate.inactive_evidence_ids
                ),
                owner_review_required=bounded_strings(f"question:{item}" for item in review_ids),
            ),
            candidate,
            decisions,
            [],
        )

    @staticmethod
    def _validate_plan(
        plan: VerticalTransitionPlan | None,
        *,
        analysis_fingerprint: str,
        decisions: list[RequiredDecision],
        target_pack: VerticalPack,
        target_question_ids: set[str],
    ) -> VerticalTransitionPlan | None:
        if plan is None:
            return None
        if plan.analysis_fingerprint_sha256 != analysis_fingerprint:
            raise ValueError(
                "P2P_VERTICAL_TRANSITION_PLAN_STALE: analysis fingerprint does not match current transition"
            )
        required = {item.decision_id: item for item in decisions}
        supplied = {item.decision_id: item for item in plan.decisions}
        missing = sorted(set(required) - set(supplied))
        extra = sorted(set(supplied) - set(required))
        if missing or extra:
            raise ValueError(
                "P2P_VERTICAL_TRANSITION_PLAN_INVALID: plan decisions do not exactly match analysis; "
                f"missing={missing}, extra={extra}"
            )
        targets: set[str] = set()
        target_fields = set(_pack_fields(target_pack))
        target_sections = {item.section_id for item in target_pack.sections}
        target_rubrics = {item.rubric_id for item in target_pack.rubrics}
        for decision_id, required_decision in required.items():
            decision = supplied[decision_id]
            if decision.source != required_decision.source:
                raise ValueError(
                    f"P2P_VERTICAL_TRANSITION_PLAN_INVALID: source mismatch for {decision_id}"
                )
            if decision.action not in required_decision.allowed_actions:
                raise ValueError(
                    f"P2P_VERTICAL_TRANSITION_PLAN_INVALID: action mismatch for {decision_id}"
                )
            if decision.target is None:
                continue
            if decision.target.kind.value not in required_decision.compatible_target_kinds:
                raise ValueError(
                    f"P2P_VERTICAL_MAPPING_CONFLICT: incompatible target kind for {decision_id}"
                )
            if decision.target.ref in targets:
                raise ValueError(
                    f"P2P_VERTICAL_MAPPING_CONFLICT: duplicate target {decision.target.ref}"
                )
            _validate_target_reference(
                decision.target,
                target_fields=target_fields,
                target_sections=target_sections,
                target_rubrics=target_rubrics,
                target_questions=target_question_ids,
            )
            targets.add(decision.target.ref)
        return plan

    @staticmethod
    def _apply_plan_to_evidence(
        impacts: list[EvidenceTransition], plan: VerticalTransitionPlan | None
    ) -> list[EvidenceTransition]:
        if plan is None:
            return impacts
        decisions = {item.decision_id: item for item in plan.decisions}
        result: list[EvidenceTransition] = []
        for item in impacts:
            decision = decisions.get(item.decision_id or "")
            if decision is None:
                result.append(item)
                continue
            result.append(
                replace(
                    item,
                    disposition=(
                        EvidenceDisposition.MAPPED
                        if decision.action == "map"
                        else EvidenceDisposition.PRESERVE_AS_ORPHAN
                    ),
                    target=decision.target,
                )
            )
        return result

    @staticmethod
    def _apply_plan_to_rubrics(
        impacts: list[RubricImpact], plan: VerticalTransitionPlan | None
    ) -> list[RubricImpact]:
        if plan is None:
            return impacts
        decisions = {item.decision_id: item for item in plan.decisions}
        result: list[RubricImpact] = []
        for item in impacts:
            decision = decisions.get(item.decision_id or "")
            if decision is None:
                result.append(item)
                continue
            result.append(
                replace(
                    item,
                    disposition="mapped" if decision.action == "map" else "preserve_as_orphan",
                    target_ref=decision.target.ref if decision.target else None,
                )
            )
        return result

    @staticmethod
    def _structural_impacts(source: VerticalPack, target: VerticalPack) -> list[StructuralImpact]:
        result: list[StructuralImpact] = []
        source_sections = {item.section_id: item for item in source.sections}
        target_sections = {item.section_id: item for item in target.sections}
        for section_id in sorted(set(source_sections) | set(target_sections)):
            before = source_sections.get(section_id)
            after = target_sections.get(section_id)
            if before is None:
                result.append(StructuralImpact("section", f"section:{section_id}", "added"))
                continue
            if after is None:
                result.append(StructuralImpact("section", f"section:{section_id}", "removed"))
                continue
            changed = tuple(
                name
                for name in ("title", "purpose", "required", "priority", "completion_policy")
                if getattr(before, name) != getattr(after, name)
            )
            result.append(
                StructuralImpact(
                    "section",
                    f"section:{section_id}",
                    "changed" if changed else "preserved",
                    changed,
                )
            )
        source_fields = _pack_fields(source)
        target_fields = _pack_fields(target)
        for field_ref in sorted(set(source_fields) | set(target_fields)):
            before = source_fields.get(field_ref)
            after = target_fields.get(field_ref)
            if before is None:
                disposition, changed = "added", ()
            elif after is None:
                disposition, changed = "removed", ()
            else:
                changed = tuple(key for key in before if before[key] != after[key])
                disposition = "changed" if changed else "preserved"
            result.append(
                StructuralImpact(
                    "field",
                    f"definition_field:{field_ref}",
                    disposition,
                    changed,
                )
            )
        return result

    def _artifact_impacts(self, candidate: VerticalMigrationCandidate) -> list[ArtifactImpact]:
        kinds = {
            ".p2p/project/vertical.yml": "vertical",
            ".p2p/project/vertical.lock.yml": "lock",
            ".p2p/project/definition.yml": "definition",
            ".p2p/project/rubrics.yml": "rubrics",
            ".p2p/project/questions.yml": "questions",
        }
        result: list[ArtifactImpact] = []
        for path, content in sorted(candidate.candidate_files.items()):
            kind = kinds.get(path)
            if kind is None:
                continue
            current_path = self.root / path
            before = _yaml_semantic_hash(current_path.read_bytes()) if current_path.exists() else None
            after = _yaml_semantic_hash(content)
            disposition = (
                ArtifactDisposition.CREATE
                if before is None
                else ArtifactDisposition.NO_CHANGE
                if before == after
                else ArtifactDisposition.UPDATE
            )
            result.append(ArtifactImpact(kind, disposition, before, after))
        return result

    @staticmethod
    def _source_identity(snapshot: VerticalEvidenceSnapshot) -> VerticalIdentity | None:
        if snapshot.lock is None:
            return None
        return VerticalIdentity(
            coordinate=snapshot.lock.coordinate or snapshot.lock.vertical_id,
            semantic_checksum=snapshot.lock.checksum,
            artifact_checksum=snapshot.lock.artifact_checksum,
            profile=snapshot.definition.profile if snapshot.definition else "default",
            modules=tuple(sorted(snapshot.definition.modules)) if snapshot.definition else (),
        )

    def _identity_for_target(
        self, coordinate: str, baseline: VerticalMigrationCandidate
    ) -> VerticalIdentity:
        resolved = self.vertical_service.resolve_pack(coordinate)
        lock_payload = load_yaml(baseline.candidate_files[".p2p/project/vertical.lock.yml"])
        artifact_checksum = ""
        if isinstance(lock_payload, Mapping):
            lock = lock_payload.get("project_vertical_lock")
            if isinstance(lock, Mapping):
                artifact = lock.get("artifact_checksum")
                if isinstance(artifact, Mapping):
                    artifact_checksum = str(artifact.get("value") or "")
        return VerticalIdentity(
            coordinate=resolved.pack.coordinate or coordinate,
            semantic_checksum=resolved.checksum,
            artifact_checksum=artifact_checksum,
            profile=baseline.profile,
            modules=tuple(sorted(baseline.modules)),
        )

    def _target_question_ids(
        self,
        baseline: VerticalMigrationCandidate,
        target_pack: VerticalPack,
    ) -> set[str]:
        content = baseline.candidate_files.get(".p2p/project/questions.yml")
        if content is None:
            return set()
        artifact = ProjectQuestionStateService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        ).parse_bytes(content, target="artifact:questions")
        return {
            item.question_id
            for item in artifact.questions
            if item.applicability.value == "active"
            and item.vertical_id == target_pack.vertical_id
        }


def _required_decision(source: DomainReference, target_coordinate: str) -> RequiredDecision:
    digest = semantic_sha256(
        {
            "contract_version": VERTICAL_TRANSITION_IMPACT_CONTRACT,
            "kind": "evidence_destination",
            "source": source.to_dict(),
            "target_coordinate": target_coordinate,
        }
    )
    return RequiredDecision(
        decision_id=f"VTD-{digest[:16]}",
        kind="evidence_destination",
        source=source,
        allowed_actions=("map", "preserve_as_orphan"),
        compatible_target_kinds=(source.kind.value,),
    )


def _validate_target_reference(
    target: DomainReference,
    *,
    target_fields: set[str],
    target_sections: set[str],
    target_rubrics: set[str],
    target_questions: set[str],
) -> None:
    suffix = target.ref.split(":", 1)[1]
    if target.kind == EvidenceKind.DEFINITION_FIELD and suffix not in target_fields:
        raise ValueError(f"P2P_VERTICAL_MAPPING_CONFLICT: unknown target {target.ref}")
    if target.kind in {EvidenceKind.DEFINITION_ASSUMPTION, EvidenceKind.DEFINITION_BLOCKER}:
        section_id = suffix.split("/", 1)[0]
        if section_id not in target_sections:
            raise ValueError(f"P2P_VERTICAL_MAPPING_CONFLICT: unknown target section {section_id}")
    if target.kind == EvidenceKind.RUBRIC and suffix not in target_rubrics:
        raise ValueError(f"P2P_VERTICAL_MAPPING_CONFLICT: unknown target {target.ref}")
    if target.kind == EvidenceKind.QUESTION:
        if suffix not in target_questions:
            raise ValueError(f"P2P_VERTICAL_MAPPING_CONFLICT: unknown target {target.ref}")


def _pack_fields(pack: VerticalPack) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for section in pack.sections:
        fields = section.fields
        if not fields:
            result[f"{section.section_id}.summary"] = {"field_id": "summary"}
        for field in fields:
            result[f"{section.section_id}.{field.field_id}"] = {
                "field_id": field.field_id,
                "label": field.label,
                "required": field.required,
                "question": field.question,
                "assisted_answer": field.assisted_answer,
                "completion_criteria": list(field.completion_criteria),
                "common_mistakes": list(field.common_mistakes),
                "suggested_artifacts": list(field.suggested_artifacts),
                "maturity_gates": list(field.maturity_gates),
            }
    return result


def _rubric_pack_signature(item) -> dict[str, object]:
    return {
        "title": item.title,
        "section_id": item.section_id,
        "required": item.required,
        "keywords": list(item.keywords),
        "enabled": True,
    }


def _rubric_payload_signature(item: Mapping[str, object]) -> dict[str, object]:
    return {
        "title": str(item.get("title") or ""),
        "section_id": str(item.get("section_id") or ""),
        "required": item.get("required") is not False,
        "keywords": [str(value) for value in item.get("keywords", [])]
        if isinstance(item.get("keywords"), list)
        else [],
        "enabled": item.get("enabled") is not False,
    }


def _meaningful(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _bounded(items, *, key) -> BoundedCollection:
    return BoundedCollection.build(items, key=key)


def _transition_material_exceeds_limit(
    collections: list[list[object]],
    *,
    question_impact: QuestionImpact,
    additional_counts: tuple[int, ...] = (),
) -> bool:
    counts = [len(items) for items in collections]
    counts.extend(
        (
            question_impact.preserved.total,
            question_impact.revised.total,
            question_impact.created.total,
            question_impact.retired.total,
            question_impact.superseded.total,
            question_impact.inactive_owner_evidence.total,
            question_impact.owner_review_required.total,
        )
    )
    counts.extend(additional_counts)
    return any(count > VERTICAL_TRANSITION_COLLECTION_LIMIT for count in counts) or (
        sum(counts) > VERTICAL_TRANSITION_TOTAL_ITEM_LIMIT
    )


def _pack_dependencies(pack: VerticalPack) -> tuple[dict[str, str], ...]:
    return tuple(
        {"coordinate": item.coordinate, "checksum": item.checksum}
        for item in sorted(
            pack.manifest.dependencies if pack.manifest else [],
            key=lambda item: item.coordinate,
        )
    )


def _dependency_delta(included: VerticalPack, excluded: VerticalPack) -> tuple[dict[str, str], ...]:
    included_dependencies = {
        item.coordinate: item.checksum
        for item in (included.manifest.dependencies if included.manifest else [])
    }
    excluded_coordinates = {
        item.coordinate for item in (excluded.manifest.dependencies if excluded.manifest else [])
    }
    return tuple(
        {"coordinate": coordinate, "checksum": included_dependencies[coordinate]}
        for coordinate in sorted(set(included_dependencies) - excluded_coordinates)
    )


def _yaml_semantic_hash(content: bytes) -> str:
    value = load_yaml(content)
    return semantic_sha256(value)


def _snapshot_fingerprint(snapshot: VerticalEvidenceSnapshot) -> str:
    return semantic_sha256(
        {
            "definition": project_definition_state_payload(snapshot.definition)
            if snapshot.definition is not None
            else None,
            "questions": snapshot.questions.semantic_payload()
            if snapshot.questions is not None
            else None,
            "rubrics": [dict(item) for item in snapshot.rubrics],
            "lock": {
                "coordinate": snapshot.lock.coordinate or snapshot.lock.vertical_id,
                "semantic_checksum": snapshot.lock.checksum,
                "artifact_checksum": snapshot.lock.artifact_checksum,
            }
            if snapshot.lock is not None
            else None,
        }
    )

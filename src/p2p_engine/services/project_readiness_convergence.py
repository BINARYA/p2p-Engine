from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Mapping, Sequence

import yaml

from p2p_engine.core.mutation_preview import (
    MutationPreviewService,
    MutationResult,
    SourcePrecondition,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.project_questions import (
    ProjectQuestion,
    ProjectQuestionAnswerKind,
    ProjectQuestionApplication,
    ProjectQuestionArtifact,
    ProjectQuestionApplicability,
    ProjectQuestionState,
    ProjectQuestionTransition,
)
from p2p_engine.core.project_readiness_convergence import (
    PROJECT_READINESS_CONVERGENCE_OPERATION,
    PROJECT_READINESS_CONVERGENCE_POLICY_VERSION,
    ProjectQuestionReconciliationPreview,
    ProjectReadinessConvergencePreview,
    ProjectReadinessConvergenceResult,
)
from p2p_engine.core.project_verticals import ProjectDefinitionPatch, ProjectDefinitionState, VerticalPack
from p2p_engine.services.candidate_workspace import CandidateWorkspaceView
from p2p_engine.services.permissions import PermissionActor, PermissionsService
from p2p_engine.services.project_questions import PROJECT_QUESTIONS_PATH, ProjectQuestionStateService
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter, utc_now_iso


DEFINITION_PATH = ".p2p/project/definition.yml"
PERMISSIONS_PATH = ".p2p/project/permissions.yml"
SCHEMA_PATH = ".p2p/project/workspace-schema.yml"
ACTIVE_VERTICAL_PATH = ".p2p/project/vertical.yml"
VERTICAL_LOCK_PATH = ".p2p/project/vertical.lock.yml"

CONVERGENCE_REBUILD_PLAN = (
    "project_readiness",
    "managed_next_actions",
    "project_progress",
    "decision_context",
    "project_assessment",
    "project_maturity",
    "project_brief",
    "project_export",
    "publication_inputs",
)


@dataclass(frozen=True)
class _ConvergenceSnapshot:
    definition: ProjectDefinitionState
    questions: ProjectQuestionArtifact
    pack: VerticalPack
    actor: PermissionActor
    source_bytes: Mapping[str, bytes]
    source_preconditions: tuple[SourcePrecondition, ...]
    schema_version: int
    lock_checksum: str
    permissions_sha256: str


@dataclass(frozen=True)
class _ConvergenceBundle:
    public: ProjectReadinessConvergencePreview
    snapshot: _ConvergenceSnapshot
    definition_candidate_bytes: bytes
    question_candidate: ProjectQuestionArtifact
    question_candidate_bytes: bytes


@dataclass(frozen=True)
class _ReconciliationBundle:
    public: ProjectQuestionReconciliationPreview
    snapshot: _ConvergenceSnapshot
    candidate: ProjectQuestionArtifact
    candidate_bytes: bytes


class ProjectReadinessConvergenceService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        vertical_service: ProjectVerticalService,
        question_service: ProjectQuestionStateService,
        permissions: PermissionsService,
        atomic_writer: AtomicMutationWriter | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.vertical_service = vertical_service
        self.question_service = question_service
        self.permissions = permissions
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir)
        self.clock = clock

    def preview(
        self,
        question_ids: Sequence[str],
        *,
        actor: str,
    ) -> ProjectReadinessConvergencePreview:
        return self._render_bundle(question_ids, actor=actor).public

    def reconciliation_preview(self, *, actor: str) -> ProjectQuestionReconciliationPreview:
        return self._render_reconciliation(actor=actor).public

    def reconciliation_apply(
        self,
        *,
        actor: str,
        preview_token: str,
        confirm: bool,
    ) -> ProjectReadinessConvergenceResult:
        bundle = self._render_reconciliation(actor=actor)
        preview = bundle.public.preview
        if not confirm:
            mutation = MutationResult(
                status="blocked",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=preview.actor,
                message="Explicit confirmation is required for question reconciliation.",
            )
            return ProjectReadinessConvergenceResult(
                status="blocked",
                operation_id=preview.operation_id,
                actor=preview.actor,
                question_ids=(),
                preview_token=preview.preview_token,
                mutation=mutation,
                message=mutation.message,
            )
        if preview.preview_token != preview_token:
            mutation = MutationResult(
                status="stale_preview",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=preview.actor,
                message="P2P345_PROJECT_READINESS_STALE_PREVIEW: reconciliation sources changed.",
            )
            return ProjectReadinessConvergenceResult(
                status="stale_preview",
                operation_id=preview.operation_id,
                actor=preview.actor,
                question_ids=(),
                preview_token=preview.preview_token,
                mutation=mutation,
                diagnostic_code="P2P345_PROJECT_READINESS_STALE_PREVIEW",
                message=mutation.message,
            )
        if not preview.apply_allowed:
            mutation = MutationResult(
                status="blocked",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=preview.actor,
                message="P2P343_PROJECT_QUESTION_OWNER_REQUIRED: reconciliation affects owner evidence.",
            )
            return ProjectReadinessConvergenceResult(
                status="blocked",
                operation_id=preview.operation_id,
                actor=preview.actor,
                question_ids=(),
                preview_token=preview.preview_token,
                mutation=mutation,
                diagnostic_code="P2P343_PROJECT_QUESTION_OWNER_REQUIRED",
                message=mutation.message,
            )
        questions_relative = PROJECT_QUESTIONS_PATH.as_posix()

        def validate_candidate(view: CandidateWorkspaceView) -> None:
            parsed = self.question_service.parse_bytes(
                view.read_bytes(questions_relative),
                target=questions_relative,
            )
            if parsed.semantic_sha256 != bundle.candidate.semantic_sha256:
                raise ValueError("P2P340_PROJECT_QUESTIONS_INVALID: reconciliation candidate drift")
            if parsed.lock_checksum != bundle.snapshot.lock_checksum:
                raise ValueError("P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED: candidate lock mismatch")

        mutation = self.atomic_writer.apply(
            operation_id=preview.operation_id,
            candidates={questions_relative: bundle.candidate_bytes},
            sources=bundle.snapshot.source_preconditions,
            preview_token=preview.preview_token,
            actor=preview.actor,
            candidate_validator=validate_candidate,
        )
        return ProjectReadinessConvergenceResult(
            status=mutation.status,
            operation_id=preview.operation_id,
            actor=preview.actor,
            question_ids=(),
            preview_token=preview.preview_token,
            mutation=mutation,
            rebuild_plan=CONVERGENCE_REBUILD_PLAN if mutation.status == "applied" else (),
            message=mutation.message,
        )

    def apply(
        self,
        question_ids: Sequence[str],
        *,
        actor: str,
        preview_token: str,
        confirm: bool,
    ) -> ProjectReadinessConvergenceResult:
        normalized_ids = self._normalize_question_ids(question_ids)
        replay = self._resolve_replay(
            normalized_ids,
            actor=actor,
            preview_token=preview_token,
        )
        if replay is not None:
            return replay
        bundle = self._render_bundle(normalized_ids, actor=actor)
        preview = bundle.public.preview
        if not confirm:
            return self._blocked_result(
                bundle,
                status="blocked",
                message="Explicit owner confirmation is required for convergence apply.",
            )
        if preview.preview_token != preview_token:
            return self._blocked_result(
                bundle,
                status="stale_preview",
                message="P2P345_PROJECT_READINESS_STALE_PREVIEW: convergence sources or inputs changed.",
                diagnostic_code="P2P345_PROJECT_READINESS_STALE_PREVIEW",
            )
        if not preview.apply_allowed or bundle.snapshot.actor.role != "owner":
            return self._blocked_result(
                bundle,
                status="blocked",
                message="P2P343_PROJECT_QUESTION_OWNER_REQUIRED: convergence apply requires the project owner.",
                diagnostic_code="P2P343_PROJECT_QUESTION_OWNER_REQUIRED",
            )

        definition_relative = DEFINITION_PATH
        questions_relative = PROJECT_QUESTIONS_PATH.as_posix()

        def validate_candidate(view: CandidateWorkspaceView) -> None:
            definition = self.vertical_service.parse_definition_bytes(
                view.read_bytes(definition_relative),
                path=self.root / definition_relative,
            )
            self.vertical_service.validate_definition_state(definition, bundle.snapshot.pack)
            questions = self.question_service.parse_bytes(
                view.read_bytes(questions_relative),
                target=questions_relative,
            )
            if questions.semantic_sha256 != bundle.public.question_candidate_sha256:
                raise ValueError("P2P340_PROJECT_QUESTIONS_INVALID: candidate semantic hash changed")
            selected = {item.question_id: item for item in questions.questions}
            for question_id in bundle.public.question_ids:
                question = selected.get(question_id)
                if question is None or question.state != ProjectQuestionState.APPLIED:
                    raise ValueError("P2P340_PROJECT_QUESTIONS_INVALID: selected question is not applied")
                application = next(
                    (item for item in question.applications if item.preview_token == preview.preview_token),
                    None,
                )
                if application is None:
                    raise ValueError("P2P340_PROJECT_QUESTIONS_INVALID: application reference is missing")
                if application.definition_semantic_sha256 != bundle.public.definition_candidate_sha256:
                    raise ValueError("P2P340_PROJECT_QUESTIONS_INVALID: definition reference mismatch")

        mutation = self.atomic_writer.apply(
            operation_id=PROJECT_READINESS_CONVERGENCE_OPERATION,
            candidates={
                definition_relative: bundle.definition_candidate_bytes,
                questions_relative: bundle.question_candidate_bytes,
            },
            sources=bundle.snapshot.source_preconditions,
            preview_token=preview.preview_token,
            actor=bundle.snapshot.actor.actor_id,
            candidate_validator=validate_candidate,
        )
        residual = ()
        if mutation.status == "applied":
            residual = tuple(
                item.gap_id
                for item in self.vertical_service.project_readiness_result().gaps
                if item.question_id in set(normalized_ids) or item.target_id in set(normalized_ids)
            )
        return ProjectReadinessConvergenceResult(
            status=mutation.status,
            operation_id=PROJECT_READINESS_CONVERGENCE_OPERATION,
            actor=bundle.snapshot.actor.actor_id,
            question_ids=normalized_ids,
            preview_token=preview.preview_token,
            mutation=mutation,
            rebuild_plan=CONVERGENCE_REBUILD_PLAN if mutation.status == "applied" else (),
            residual_gap_ids=residual,
            message=mutation.message,
        )

    def _render_bundle(self, question_ids: Sequence[str], *, actor: str) -> _ConvergenceBundle:
        normalized_ids = self._normalize_question_ids(question_ids)
        snapshot = self._capture(actor)
        questions_by_id = {item.question_id: item for item in snapshot.questions.questions}
        selected: list[ProjectQuestion] = []
        for question_id in normalized_ids:
            question = questions_by_id.get(question_id)
            if question is None:
                raise ValueError(f"P2P341_PROJECT_QUESTION_NOT_FOUND: `{question_id}`")
            if question.state != ProjectQuestionState.ANSWERED:
                raise ValueError(
                    f"P2P342_PROJECT_QUESTION_TRANSITION_INVALID: question `{question_id}` "
                    f"must be answered before convergence, current `{question.state.value}`"
                )
            if question.applicability != ProjectQuestionApplicability.ACTIVE:
                raise ValueError(
                    "P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED: question applicability is not active"
                )
            if question.lock_checksum != snapshot.lock_checksum:
                raise ValueError(
                    "P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED: question lock does not match active lock"
                )
            selected.append(question)

        operations = self._definition_operations(selected)
        definition_candidate = self.vertical_service.render_definition_candidate(
            state=snapshot.definition,
            patch=ProjectDefinitionPatch(actor=snapshot.actor.actor_id, operations=operations),
            pack=snapshot.pack,
            audit_at=self.clock(),
        )
        question_revisions = {item.question_id: item.revision for item in selected}
        request_identity = semantic_sha256(
            {
                "operation_id": PROJECT_READINESS_CONVERGENCE_OPERATION,
                "actor": snapshot.actor.actor_id,
                "question_ids": list(normalized_ids),
                "question_revisions": question_revisions,
            }
        )
        timestamp = self.clock()
        placeholder_token = "__P2P_PREVIEW_TOKEN__"
        placeholder_hash = "0" * 64
        candidate = self._applied_question_candidate(
            snapshot.questions,
            selected,
            actor=snapshot.actor.actor_id,
            applied_at=timestamp,
            preview_token=placeholder_token,
            request_identity=request_identity,
            definition_sha256=definition_candidate.semantic_sha256,
            question_sha256=placeholder_hash,
        )
        question_candidate_sha = candidate.semantic_sha256
        candidate = self._replace_application_reference(
            candidate,
            preview_token=placeholder_token,
            question_sha256=question_candidate_sha,
        )
        if candidate.semantic_sha256 != question_candidate_sha:
            raise ValueError("P2P340_PROJECT_QUESTIONS_INVALID: unstable application semantic identity")

        definition_before_sha = semantic_sha256(
            self.vertical_service.render_definition_candidate(
                state=snapshot.definition,
                patch=ProjectDefinitionPatch(actor=snapshot.actor.actor_id, operations=[]),
                pack=snapshot.pack,
                audit_at=timestamp,
            ).semantic_payload
        )
        targets = (DEFINITION_PATH, PROJECT_QUESTIONS_PATH.as_posix())
        candidate_semantics = {
            DEFINITION_PATH: definition_candidate.semantic_payload,
            PROJECT_QUESTIONS_PATH.as_posix(): candidate.semantic_payload(),
        }
        blockers = () if snapshot.actor.role == "owner" else ("owner_required",)
        preview = MutationPreviewService.build(
            operation_id=PROJECT_READINESS_CONVERGENCE_OPERATION,
            targets=targets,
            actor=snapshot.actor.actor_id,
            authority="owner_confirmed" if snapshot.actor.role == "owner" else "owner_required",
            sources=snapshot.source_preconditions,
            candidate_semantics=candidate_semantics,
            semantic_diff={
                DEFINITION_PATH: {
                    "operations": list(definition_candidate.operation_ids),
                    "changed_sections": list(definition_candidate.changed_sections),
                    "before_semantic_sha256": definition_before_sha,
                    "candidate_semantic_sha256": definition_candidate.semantic_sha256,
                },
                PROJECT_QUESTIONS_PATH.as_posix(): {
                    "question_ids": list(normalized_ids),
                    "from": "answered",
                    "to": "applied",
                    "candidate_semantic_sha256": question_candidate_sha,
                },
            },
            blockers=blockers,
            token_context={
                "actor": snapshot.actor.actor_id,
                "question_ids": list(normalized_ids),
                "question_revisions": question_revisions,
                "schema_version": snapshot.schema_version,
                "lock_checksum": snapshot.lock_checksum,
                "permissions_sha256": snapshot.permissions_sha256,
                "policy_version": PROJECT_READINESS_CONVERGENCE_POLICY_VERSION,
                "definition_candidate_sha256": definition_candidate.semantic_sha256,
                "question_candidate_sha256": question_candidate_sha,
            },
        )
        candidate = self._replace_application_reference(
            candidate,
            preview_token=preview.preview_token,
            question_sha256=question_candidate_sha,
        )
        self.question_service.validate_artifact(candidate)
        complete_before = sum(item.status == "complete" for item in snapshot.definition.sections)
        complete_after = sum(item.status == "complete" for item in definition_candidate.state.sections)
        public = ProjectReadinessConvergencePreview(
            preview=preview,
            question_ids=normalized_ids,
            question_revisions=question_revisions,
            definition_before_sha256=definition_before_sha,
            definition_candidate_sha256=definition_candidate.semantic_sha256,
            question_candidate_sha256=question_candidate_sha,
            affected_gap_ids=tuple(sorted(item.gap_id for item in selected)),
            progress_effect={
                "complete_sections_before": complete_before,
                "complete_sections_candidate": complete_after,
                "aggregate_percentage_added": False,
            },
            rebuild_plan=CONVERGENCE_REBUILD_PLAN,
        )
        return _ConvergenceBundle(
            public=public,
            snapshot=snapshot,
            definition_candidate_bytes=definition_candidate.candidate_bytes,
            question_candidate=candidate,
            question_candidate_bytes=self.question_service.candidate_bytes(candidate),
        )

    def _render_reconciliation(self, *, actor: str) -> _ReconciliationBundle:
        snapshot = self._capture(actor, require_question_alignment=False)
        candidate = self.question_service.reconcile_candidate(
            current=snapshot.questions,
            project_id=snapshot.questions.project_id,
            definition=snapshot.definition,
            pack=snapshot.pack,
            lock_checksum=snapshot.lock_checksum,
            actor=snapshot.actor.actor_id,
            audit_at=self.clock(),
        )
        owner_required = candidate.owner_evidence_affected
        blockers = (
            ("owner_required",)
            if owner_required and snapshot.actor.role != "owner"
            else ()
        )
        relative = PROJECT_QUESTIONS_PATH.as_posix()
        preview = MutationPreviewService.build(
            operation_id="project-question-reconciliation",
            targets=(relative,),
            actor=snapshot.actor.actor_id,
            authority=(
                "owner_confirmed"
                if snapshot.actor.role == "owner"
                else "known_actor"
            ),
            sources=snapshot.source_preconditions,
            candidate_semantics={relative: candidate.artifact.semantic_payload()},
            semantic_diff={
                relative: {
                    "preserved_ids": list(candidate.preserved_ids),
                    "revised_ids": list(candidate.revised_ids),
                    "created_ids": list(candidate.created_ids),
                    "retired_ids": list(candidate.retired_ids),
                    "superseded_ids": list(candidate.superseded_ids),
                    "inactive_evidence_ids": list(candidate.inactive_evidence_ids),
                }
            },
            blockers=blockers,
            token_context={
                "actor": snapshot.actor.actor_id,
                "schema_version": snapshot.schema_version,
                "lock_checksum": snapshot.lock_checksum,
                "permissions_sha256": snapshot.permissions_sha256,
                "policy_version": PROJECT_READINESS_CONVERGENCE_POLICY_VERSION,
                "question_candidate_sha256": candidate.artifact.semantic_sha256,
            },
        )
        public = ProjectQuestionReconciliationPreview(
            preview=preview,
            preserved_ids=candidate.preserved_ids,
            revised_ids=candidate.revised_ids,
            created_ids=candidate.created_ids,
            retired_ids=candidate.retired_ids,
            superseded_ids=candidate.superseded_ids,
            inactive_evidence_ids=candidate.inactive_evidence_ids,
            owner_apply_required=owner_required,
        )
        return _ReconciliationBundle(
            public=public,
            snapshot=snapshot,
            candidate=candidate.artifact,
            candidate_bytes=self.question_service.candidate_bytes(candidate.artifact),
        )

    def _capture(self, actor: str, *, require_question_alignment: bool = True) -> _ConvergenceSnapshot:
        paths = {
            DEFINITION_PATH: self.root / DEFINITION_PATH,
            PROJECT_QUESTIONS_PATH.as_posix(): self.root / PROJECT_QUESTIONS_PATH,
            PERMISSIONS_PATH: self.root / PERMISSIONS_PATH,
            SCHEMA_PATH: self.root / SCHEMA_PATH,
            ACTIVE_VERTICAL_PATH: self.root / ACTIVE_VERTICAL_PATH,
            VERTICAL_LOCK_PATH: self.root / VERTICAL_LOCK_PATH,
        }
        source_bytes: dict[str, bytes] = {}
        for relative, path in paths.items():
            if not path.exists():
                raise ValueError(f"P2P340_PROJECT_QUESTIONS_INVALID: required source is missing `{relative}`")
            source_bytes[relative] = path.read_bytes()
        schema = self._yaml_mapping(source_bytes[SCHEMA_PATH], SCHEMA_PATH)
        schema_payload = schema.get("workspace_schema")
        schema_version = (
            int(schema_payload.get("current_version") or 0)
            if isinstance(schema_payload, Mapping)
            else 0
        )
        if schema_version < 2:
            raise ValueError(
                "P2P348_WORKSPACE_OPERATION_SCHEMA_REQUIRED: convergence requires workspace schema v2; "
                "run `p2p workspace migrate plan --to 2 --format json`"
            )
        definition = self.vertical_service.parse_definition_bytes(
            source_bytes[DEFINITION_PATH],
            path=paths[DEFINITION_PATH],
        )
        questions = self.question_service.parse_bytes(
            source_bytes[PROJECT_QUESTIONS_PATH.as_posix()],
            target=PROJECT_QUESTIONS_PATH.as_posix(),
        )
        permissions_payload = self._yaml_mapping(source_bytes[PERMISSIONS_PATH], PERMISSIONS_PATH)
        permission_actor = self.permissions.resolve_actor_payload(actor, permissions_payload)
        lock = self.vertical_service.parse_vertical_lock_bytes(
            source_bytes[VERTICAL_LOCK_PATH],
            path=paths[VERTICAL_LOCK_PATH],
        )
        active_payload = self._yaml_mapping(source_bytes[ACTIVE_VERTICAL_PATH], ACTIVE_VERTICAL_PATH)
        active = active_payload.get("project_vertical")
        active_id = str(active.get("active_vertical_id") or "") if isinstance(active, Mapping) else ""
        if not active_id or active_id != definition.vertical_id or lock.vertical_id != definition.vertical_id:
            raise ValueError("P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED: active vertical identity drift")
        if definition.lock_checksum != lock.checksum:
            raise ValueError("P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED: vertical lock drift")
        if require_question_alignment and questions.lock_checksum != lock.checksum:
            raise ValueError("P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED: vertical lock drift")
        if require_question_alignment and (
            questions.vertical_id != definition.vertical_id
            or questions.vertical_version != definition.vertical_version
        ):
            raise ValueError("P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED: question vertical drift")
        pack = self.vertical_service.pack_for_definition(definition)
        self.vertical_service.validate_definition_state(definition, pack)
        return _ConvergenceSnapshot(
            definition=definition,
            questions=questions,
            pack=pack,
            actor=permission_actor,
            source_bytes=source_bytes,
            source_preconditions=tuple(
                source_precondition(relative, source_bytes[relative])
                for relative in sorted(source_bytes)
            ),
            schema_version=schema_version,
            lock_checksum=lock.checksum,
            permissions_sha256=hashlib.sha256(source_bytes[PERMISSIONS_PATH]).hexdigest(),
        )

    def _definition_operations(self, questions: Sequence[ProjectQuestion]) -> list[dict[str, object]]:
        by_target: dict[tuple[str, str, str], dict[str, object]] = {}
        for question in sorted(questions, key=lambda item: item.question_id):
            answer = question.answers[-1].values
            contract = question.answer_contract
            self.question_service.validate_answer_values(question, answer)
            operation: dict[str, object] | None
            if contract.kind == ProjectQuestionAnswerKind.FIELD_VALUE:
                operation = {
                    "op": "set_field",
                    "section_id": question.section_id,
                    "field_id": question.target.target_id,
                    "value": answer["value"],
                    "provenance": {"source": f"project_questions:{question.question_id}"},
                }
            elif contract.kind == ProjectQuestionAnswerKind.SECTION_DISPOSITION:
                operation = {
                    "op": "set_section_status",
                    "section_id": question.section_id,
                    "status": answer["status"],
                }
            elif contract.kind == ProjectQuestionAnswerKind.ASSUMPTION_RESOLUTION:
                operation = {
                    "op": "update_assumption_status",
                    "section_id": question.section_id,
                    "assumption_id": question.target.target_id,
                    "status": answer["outcome"],
                }
            elif contract.kind == ProjectQuestionAnswerKind.BLOCKER_RESOLUTION:
                operation = (
                    {
                        "op": "clear_blocker",
                        "section_id": question.section_id,
                        "blocker_id": question.target.target_id,
                    }
                    if answer["outcome"] == "clear"
                    else None
                )
            elif contract.kind == ProjectQuestionAnswerKind.OWNER_DECISION_REFERENCE:
                operation = {
                    "op": "set_field",
                    "section_id": question.section_id,
                    "field_id": question.target.target_id,
                    "value": answer["value"],
                    "provenance": {"source": f"project_questions:{question.question_id}"},
                }
            else:
                raise ValueError(
                    f"P2P342_PROJECT_QUESTION_TRANSITION_INVALID: question `{question.question_id}` "
                    "has no deterministic definition operation"
                )
            if operation is None:
                continue
            operation_name = str(operation["op"])
            if operation_name not in set(contract.allowed_definition_operations):
                raise ValueError("P2P340_PROJECT_QUESTIONS_INVALID: operation is outside answer contract")
            target_key = (question.section_id, question.target.kind, question.target.target_id)
            previous = by_target.get(target_key)
            if previous is not None and semantic_sha256(previous) != semantic_sha256(operation):
                raise ValueError(
                    f"P2P342_PROJECT_QUESTION_TRANSITION_INVALID: conflicting answers target `{target_key}`"
                )
            by_target[target_key] = operation
        return [by_target[key] for key in sorted(by_target)]

    def _applied_question_candidate(
        self,
        artifact: ProjectQuestionArtifact,
        selected: Sequence[ProjectQuestion],
        *,
        actor: str,
        applied_at: str,
        preview_token: str,
        request_identity: str,
        definition_sha256: str,
        question_sha256: str,
    ) -> ProjectQuestionArtifact:
        selected_ids = tuple(sorted(item.question_id for item in selected))
        revisions = {item.question_id: item.revision for item in selected}
        selected_set = set(selected_ids)
        updated_questions: list[ProjectQuestion] = []
        for question in artifact.questions:
            if question.question_id not in selected_set:
                updated_questions.append(question)
                continue
            application = ProjectQuestionApplication(
                operation_id=PROJECT_READINESS_CONVERGENCE_OPERATION,
                preview_token=preview_token,
                actor=actor,
                definition_semantic_sha256=definition_sha256,
                question_semantic_sha256=question_sha256,
                applied_at=applied_at,
                question_ids=selected_ids,
                question_revisions=revisions,
                request_identity_sha256=request_identity,
                changed_paths=(DEFINITION_PATH, PROJECT_QUESTIONS_PATH.as_posix()),
            )
            transition = ProjectQuestionTransition(
                operation="convergence_apply",
                from_state=question.state.value,
                to_state=ProjectQuestionState.APPLIED.value,
                actor=actor,
                role="owner",
                reason="Owner-confirmed convergence applied the recorded answer.",
                at=applied_at,
                provenance={"preview_token": preview_token},
            )
            updated_questions.append(
                replace(
                    question,
                    revision=question.revision + 1,
                    state=ProjectQuestionState.APPLIED,
                    applications=(*question.applications, application),
                    transitions=(*question.transitions, transition),
                    updated_at=applied_at,
                    updated_by=actor,
                )
            )
        return replace(
            artifact,
            questions=tuple(updated_questions),
            updated_at=applied_at,
            updated_by=actor,
        )

    @staticmethod
    def _replace_application_reference(
        artifact: ProjectQuestionArtifact,
        *,
        preview_token: str,
        question_sha256: str,
    ) -> ProjectQuestionArtifact:
        questions = []
        for question in artifact.questions:
            applications = tuple(
                replace(
                    item,
                    preview_token=preview_token,
                    question_semantic_sha256=question_sha256,
                )
                if item.preview_token == "__P2P_PREVIEW_TOKEN__" or item.question_semantic_sha256 == "0" * 64
                else item
                for item in question.applications
            )
            transitions = tuple(
                replace(item, provenance={"preview_token": preview_token})
                if item.operation == "convergence_apply"
                and item.provenance.get("preview_token") == "__P2P_PREVIEW_TOKEN__"
                else item
                for item in question.transitions
            )
            questions.append(replace(question, applications=applications, transitions=transitions))
        return replace(artifact, questions=tuple(questions))

    def _resolve_replay(
        self,
        question_ids: tuple[str, ...],
        *,
        actor: str,
        preview_token: str,
    ) -> ProjectReadinessConvergenceResult | None:
        artifact = self.question_service.read_optional()
        if artifact is None:
            return None
        applications = [
            item
            for question in artifact.questions
            for item in question.applications
            if item.preview_token == preview_token
        ]
        if not applications:
            return None
        application = applications[0]
        actor_id = self.permissions.identity_slug(actor)
        request_identity = semantic_sha256(
            {
                "operation_id": PROJECT_READINESS_CONVERGENCE_OPERATION,
                "actor": actor_id,
                "question_ids": list(question_ids),
                "question_revisions": dict(application.question_revisions),
            }
        )
        matches = (
            all(item == application for item in applications)
            and application.operation_id == PROJECT_READINESS_CONVERGENCE_OPERATION
            and application.actor == actor_id
            and tuple(application.question_ids) == question_ids
            and application.request_identity_sha256 == request_identity
        )
        if not matches:
            mutation = MutationResult(
                status="replay_mismatch",
                operation_id=PROJECT_READINESS_CONVERGENCE_OPERATION,
                preview_token=preview_token,
                actor=actor_id,
                message="P2P346_PREVIEW_REPLAY_MISMATCH: stored application does not match retry request.",
            )
            return ProjectReadinessConvergenceResult(
                status="replay_mismatch",
                operation_id=PROJECT_READINESS_CONVERGENCE_OPERATION,
                actor=actor_id,
                question_ids=question_ids,
                preview_token=preview_token,
                mutation=mutation,
                diagnostic_code="P2P346_PREVIEW_REPLAY_MISMATCH",
                message=mutation.message,
            )
        mutation = MutationResult(
            status="already_applied",
            operation_id=PROJECT_READINESS_CONVERGENCE_OPERATION,
            changed_paths=application.changed_paths,
            final_physical_hashes=application.final_physical_hashes,
            preview_token=preview_token,
            actor=actor_id,
            message="The exact convergence request was already committed.",
        )
        return ProjectReadinessConvergenceResult(
            status="already_applied",
            operation_id=PROJECT_READINESS_CONVERGENCE_OPERATION,
            actor=actor_id,
            question_ids=question_ids,
            preview_token=preview_token,
            mutation=mutation,
            rebuild_plan=CONVERGENCE_REBUILD_PLAN,
            already_applied=True,
            message=mutation.message,
            stored_physical_hashes=application.final_physical_hashes,
        )

    @staticmethod
    def _normalize_question_ids(question_ids: Sequence[str]) -> tuple[str, ...]:
        values = tuple(sorted(str(item).strip() for item in question_ids if str(item).strip()))
        if not values:
            raise ValueError("Convergence requires at least one explicit question id.")
        if len(values) != len(set(values)):
            raise ValueError("Convergence question ids must be unique.")
        return values

    @staticmethod
    def _yaml_mapping(content: bytes, target: str) -> dict[str, object]:
        try:
            payload = yaml.safe_load(content.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"Invalid convergence source `{target}`: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid convergence source `{target}`: expected a mapping")
        return payload

    @staticmethod
    def _blocked_result(
        bundle: _ConvergenceBundle,
        *,
        status: str,
        message: str,
        diagnostic_code: str = "",
    ) -> ProjectReadinessConvergenceResult:
        preview = bundle.public.preview
        mutation = MutationResult(
            status=status,
            operation_id=preview.operation_id,
            preview_token=preview.preview_token,
            actor=preview.actor,
            message=message,
        )
        return ProjectReadinessConvergenceResult(
            status=status,
            operation_id=preview.operation_id,
            actor=preview.actor,
            question_ids=bundle.public.question_ids,
            preview_token=preview.preview_token,
            mutation=mutation,
            diagnostic_code=diagnostic_code,
            message=message,
        )

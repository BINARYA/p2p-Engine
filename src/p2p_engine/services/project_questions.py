from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence

import yaml
from p2p_engine.foundation.yaml_loaders import load_yaml

from p2p_engine.core.mutation_preview import (
    MutationPreviewService,
    MutationResult,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.project_questions import (
    PROJECT_QUESTION_ANSWER_POLICY_VERSION,
    PROJECT_QUESTION_ARTIFACT_SCHEMA_VERSION,
    PROJECT_QUESTION_FALLBACK_POLICY_VERSION,
    PROJECT_QUESTION_IDENTITY_POLICY_VERSION,
    PROJECT_QUESTION_LIFECYCLE_POLICY_VERSION,
    ProjectQuestion,
    ProjectQuestionAnswerContract,
    ProjectQuestionAnswerKind,
    ProjectQuestionAnswerRevision,
    ProjectQuestionApplicability,
    ProjectQuestionApplication,
    ProjectQuestionArtifact,
    ProjectQuestionGroup,
    ProjectQuestionOperationResult,
    ProjectQuestionRevision,
    ProjectQuestionSourceType,
    ProjectQuestionState,
    ProjectQuestionTarget,
    ProjectQuestionTransition,
    project_question_group_identity,
    project_question_identity,
    project_question_wording_sha256,
)
from p2p_engine.core.project_readiness import (
    ProjectReadinessDiagnostic,
    ProjectReadinessGapKind,
    readiness_gap_identity,
)
from p2p_engine.core.project_verticals import (
    ProjectDefinitionSectionState,
    ProjectDefinitionState,
    VerticalField,
    VerticalPack,
    VerticalQuestion,
    VerticalSection,
)
from p2p_engine.foundation.files import read_yaml_mapping, yaml_dump
from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.project_readiness import ProjectReadinessPaginationService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter, utc_now_iso


PROJECT_QUESTIONS_PATH = Path(".p2p/project/questions.yml")

_ROOT_KEYS = frozenset({"project_questions"})
_ARTIFACT_KEYS = frozenset(
    {
        "schema_version",
        "project_id",
        "vertical",
        "policy_versions",
        "groups",
        "questions",
        "audit",
    }
)
_QUESTION_KEYS = frozenset(
    {
        "id",
        "identity_sha256",
        "revision",
        "wording_sha256",
        "question",
        "state",
        "applicability",
        "section_id",
        "gap_id",
        "target",
        "priority",
        "rationale",
        "source",
        "answer_contract",
        "deferred_trigger",
        "revisions",
        "answers",
        "applications",
        "transitions",
        "superseded_by",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by",
    }
)
_VERTICAL_KEYS = frozenset({"id", "version", "lock_checksum"})
_POLICY_KEYS = frozenset({"identity", "fallback", "lifecycle", "answer_binding"})
_AUDIT_KEYS = frozenset({"created_at", "created_by", "updated_at", "updated_by"})
_GROUP_KEYS = frozenset({"id", "identity_sha256", "gap_id", "section_id", "question_ids"})
_TARGET_KEYS = frozenset({"kind", "id"})
_SOURCE_KEYS = frozenset(
    {
        "kind",
        "question_id",
        "key",
        "vertical_id",
        "vertical_version",
        "lock_checksum",
        "fallback_policy_version",
    }
)
_CONTRACT_KEYS = frozenset(
    {"kind", "required_fields", "allowed_definition_operations", "allowed_values"}
)
_REVISION_KEYS = frozenset(
    {
        "revision",
        "wording_sha256",
        "question",
        "vertical_version",
        "lock_checksum",
        "answer_contract",
        "changed_at",
        "changed_by",
    }
)
_ANSWER_KEYS = frozenset(
    {"revision", "values", "evidence_refs", "provided_by", "recorded_by", "answered_at"}
)
_APPLICATION_KEYS = frozenset(
    {
        "operation_id",
        "preview_token",
        "actor",
        "definition_semantic_sha256",
        "question_semantic_sha256",
        "applied_at",
        "question_ids",
        "question_revisions",
        "request_identity_sha256",
        "changed_paths",
        "final_physical_hashes",
    }
)
_TRANSITION_KEYS = frozenset(
    {"operation", "from", "to", "actor", "role", "reason", "at", "provenance"}
)
ProjectQuestionSelection = tuple[
    str,
    ProjectQuestionTarget,
    ProjectQuestionAnswerContract,
    ProjectQuestionSourceType,
    str,
    str,
    Mapping[str, object],
]


@dataclass(frozen=True)
class ProjectQuestionSeedResult:
    artifact: ProjectQuestionArtifact
    diagnostics: tuple[ProjectReadinessDiagnostic, ...]
    migrated_count: int
    generated_count: int


@dataclass(frozen=True)
class ProjectQuestionReconciliationCandidate:
    artifact: ProjectQuestionArtifact
    preserved_ids: tuple[str, ...]
    revised_ids: tuple[str, ...]
    created_ids: tuple[str, ...]
    retired_ids: tuple[str, ...]
    superseded_ids: tuple[str, ...]
    inactive_evidence_ids: tuple[str, ...]
    owner_evidence_ids: tuple[str, ...] = ()

    @property
    def owner_evidence_affected(self) -> bool:
        return bool(self.inactive_evidence_ids or self.superseded_ids or self.owner_evidence_ids)


class ProjectQuestionStateService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        clock: Callable[[], str] = utc_now_iso,
        atomic_writer: AtomicMutationWriter | None = None,
        permissions: PermissionsService | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.path = self.root / PROJECT_QUESTIONS_PATH
        self.clock = clock
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir)
        self.permissions = permissions or PermissionsService(root=self.root, p2p_dir=self.p2p_dir)

    def empty_artifact(
        self,
        *,
        project_id: str,
        vertical_id: str,
        vertical_version: str,
        lock_checksum: str,
        actor: str,
        audit_at: str | None = None,
    ) -> ProjectQuestionArtifact:
        timestamp = audit_at or self.clock()
        return ProjectQuestionArtifact(
            project_id=project_id,
            vertical_id=vertical_id,
            vertical_version=vertical_version,
            lock_checksum=lock_checksum,
            groups=(),
            questions=(),
            created_at=timestamp,
            created_by=actor,
            updated_at=timestamp,
            updated_by=actor,
        )

    def read(self) -> ProjectQuestionArtifact:
        payload = read_yaml_mapping(
            self.path,
            default={},
            error_message="Project question artifact must be a YAML mapping: {path}",
        )
        return self.parse_payload(payload, target=str(self.path))

    def read_optional(self) -> ProjectQuestionArtifact | None:
        return self.read() if self.path.exists() else None

    def parse_bytes(self, content: bytes, *, target: str) -> ProjectQuestionArtifact:
        try:
            payload = load_yaml(content)
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"Invalid project question artifact {target}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid project question artifact {target}: expected a YAML mapping")
        return self.parse_payload(payload, target=target)

    def parse_payload(self, payload: Mapping[str, object], *, target: str) -> ProjectQuestionArtifact:
        unknown_root = set(payload) - _ROOT_KEYS
        if unknown_root:
            raise ValueError(f"Invalid project question artifact {target}: unknown root fields {sorted(unknown_root)}")
        raw = payload.get("project_questions")
        if not isinstance(raw, Mapping):
            raise ValueError(f"Invalid project question artifact {target}: project_questions mapping is required")
        unknown = set(raw) - _ARTIFACT_KEYS
        if unknown:
            raise ValueError(f"Invalid project question artifact {target}: unknown fields {sorted(unknown)}")
        schema_version = _required_int(raw, "schema_version", target)
        if schema_version != PROJECT_QUESTION_ARTIFACT_SCHEMA_VERSION:
            raise ValueError(
                f"Invalid project question artifact {target}: unsupported schema_version {schema_version}"
            )
        vertical = _required_mapping(raw, "vertical", target)
        policies = _required_mapping(raw, "policy_versions", target)
        audit = _required_mapping(raw, "audit", target)
        _reject_unknown_fields(vertical, _VERTICAL_KEYS, f"{target}.vertical")
        _reject_unknown_fields(policies, _POLICY_KEYS, f"{target}.policy_versions")
        _reject_unknown_fields(audit, _AUDIT_KEYS, f"{target}.audit")
        if set(policies) != _POLICY_KEYS:
            raise ValueError(
                f"Invalid {target}.policy_versions: required fields are {sorted(_POLICY_KEYS)}"
            )
        questions = tuple(
            self._parse_question(item, target=f"{target}.questions[{index}]")
            for index, item in enumerate(_required_sequence(raw, "questions", target))
        )
        groups = tuple(
            self._parse_group(item, target=f"{target}.groups[{index}]")
            for index, item in enumerate(_required_sequence(raw, "groups", target))
        )
        artifact = ProjectQuestionArtifact(
            schema_version=schema_version,
            project_id=_required_text(raw, "project_id", target),
            vertical_id=_required_text(vertical, "id", target),
            vertical_version=_required_text(vertical, "version", target),
            lock_checksum=_required_text(vertical, "lock_checksum", target),
            policy_versions={
                key: _required_int(policies, key, f"{target}.policy_versions")
                for key in sorted(_POLICY_KEYS)
            },
            groups=groups,
            questions=questions,
            created_at=_required_timestamp(audit, "created_at", target),
            created_by=_required_text(audit, "created_by", target),
            updated_at=_required_timestamp(audit, "updated_at", target),
            updated_by=_required_text(audit, "updated_by", target),
        )
        self.validate_artifact(artifact, target=target)
        return artifact

    def validate_artifact(self, artifact: ProjectQuestionArtifact, *, target: str = "project_questions") -> None:
        expected_policies = {
            "identity": PROJECT_QUESTION_IDENTITY_POLICY_VERSION,
            "fallback": PROJECT_QUESTION_FALLBACK_POLICY_VERSION,
            "lifecycle": PROJECT_QUESTION_LIFECYCLE_POLICY_VERSION,
            "answer_binding": PROJECT_QUESTION_ANSWER_POLICY_VERSION,
        }
        if dict(artifact.policy_versions) != expected_policies:
            raise ValueError(f"Invalid {target}: unsupported project-question policy versions")
        question_ids: dict[str, str] = {}
        identity_digests: dict[str, str] = {}
        for question in artifact.questions:
            if question.question_id in question_ids:
                raise ValueError(f"Invalid {target}: duplicate question id `{question.question_id}`")
            question_ids[question.question_id] = question.identity_sha256
            previous = identity_digests.setdefault(question.question_id, question.identity_sha256)
            if previous != question.identity_sha256:
                raise ValueError(f"Invalid {target}: question id collision `{question.question_id}`")
            expected_id, expected_digest = project_question_identity(
                vertical_id=question.vertical_id,
                section_id=question.section_id,
                gap_kind=_gap_kind_for_contract(question.answer_contract.kind),
                target_kind=question.target.kind,
                target_id=question.target.target_id,
                source_key=question.source_key,
            )
            if question.question_id != expected_id or question.identity_sha256 != expected_digest:
                raise ValueError(f"Invalid {target}: question identity mismatch `{question.question_id}`")
            if question.wording_sha256 != project_question_wording_sha256(question.question):
                raise ValueError(f"Invalid {target}: wording hash mismatch `{question.question_id}`")
            if question.revision < 1:
                raise ValueError(f"Invalid {target}: revision must be positive `{question.question_id}`")
            if question.applicability == ProjectQuestionApplicability.ACTIVE and (
                question.vertical_id != artifact.vertical_id
                or question.vertical_version != artifact.vertical_version
                or question.lock_checksum != artifact.lock_checksum
            ):
                raise ValueError(f"Invalid {target}: active question vertical binding mismatch `{question.question_id}`")
            for answer in question.answers:
                self.validate_answer_values(question, answer.values)
            self._validate_question_history(question, target=target)
        applications_by_token: dict[str, ProjectQuestionApplication] = {}
        for question in artifact.questions:
            if question.superseded_by and question.superseded_by not in question_ids:
                raise ValueError(
                    f"Invalid {target}: superseded question references unknown replacement "
                    f"`{question.superseded_by}`"
                )
            for application in question.applications:
                unknown_application_questions = set(application.question_ids) - set(question_ids)
                if unknown_application_questions:
                    raise ValueError(
                        f"Invalid {target}: application references unknown question "
                        f"`{sorted(unknown_application_questions)[0]}`"
                    )
                if set(application.question_revisions) != set(application.question_ids):
                    raise ValueError(
                        f"Invalid {target}: application revision map does not match question ids"
                    )
                previous_application = applications_by_token.setdefault(
                    application.preview_token,
                    application,
                )
                if previous_application != application:
                    raise ValueError(
                        f"Invalid {target}: preview token has conflicting application records"
                    )
        group_ids: set[str] = set()
        grouped_questions: dict[str, str] = {}
        questions_by_id = {item.question_id: item for item in artifact.questions}
        for group in artifact.groups:
            if group.group_id in group_ids:
                raise ValueError(f"Invalid {target}: duplicate group id `{group.group_id}`")
            group_ids.add(group.group_id)
            expected_group_id, expected_group_digest = project_question_group_identity(
                vertical_id=artifact.vertical_id,
                section_id=group.section_id,
                gap_id=group.gap_id,
            )
            if group.group_id != expected_group_id or group.identity_sha256 != expected_group_digest:
                raise ValueError(f"Invalid {target}: group identity mismatch `{group.group_id}`")
            unknown = set(group.question_ids) - set(question_ids)
            if unknown:
                raise ValueError(f"Invalid {target}: group references unknown question `{sorted(unknown)[0]}`")
            for question_id in group.question_ids:
                if question_id in grouped_questions:
                    raise ValueError(
                        f"Invalid {target}: question belongs to multiple groups `{question_id}`"
                    )
                question = questions_by_id[question_id]
                if question.section_id != group.section_id or question.gap_id != group.gap_id:
                    raise ValueError(
                        f"Invalid {target}: group scope mismatch for question `{question_id}`"
                    )
                grouped_questions[question_id] = group.group_id
        if set(grouped_questions) != set(question_ids):
            raise ValueError(f"Invalid {target}: every question must belong to exactly one group")

    def candidate_bytes(self, artifact: ProjectQuestionArtifact) -> bytes:
        self.validate_artifact(artifact)
        return yaml_dump(artifact.to_payload()).encode("utf-8")

    def question(self, question_id: str) -> ProjectQuestion:
        artifact = self.read()
        return self._find_question(artifact, question_id)

    def next_question(self) -> ProjectQuestion | None:
        artifact = self.read()
        eligible = [
            item
            for item in artifact.questions
            if item.state == ProjectQuestionState.TO_ANSWER
            and item.applicability == ProjectQuestionApplicability.ACTIVE
        ]
        return min(eligible, key=self._question_order_key) if eligible else None

    def page(
        self,
        *,
        state: str = "",
        limit: int = 20,
        cursor: str = "",
    ):
        artifact = self.read()
        normalized_state = state.strip()
        if normalized_state:
            ProjectQuestionState(normalized_state)
        items = tuple(
            sorted(
                (
                    item
                    for item in artifact.questions
                    if not normalized_state or item.state.value == normalized_state
                ),
                key=self._question_order_key,
            )
        )
        return ProjectReadinessPaginationService().page_items(
            collection=f"project_questions:{normalized_state or 'all'}",
            snapshot_fingerprint=artifact.semantic_sha256,
            items=items,
            key=lambda item: (*self._question_order_key(item), item.revision),
            limit=limit,
            cursor=cursor,
        )

    def answer(
        self,
        question_id: str,
        *,
        values: Mapping[str, object],
        actor: str,
        expected_revision: int,
        replace_answer: bool = False,
        evidence_refs: Sequence[str] = (),
    ) -> ProjectQuestionOperationResult:
        operation_id = "project_questions_answer"
        permission_actor = self.permissions.require_role(actor, "owner", operation=operation_id)
        content = self.path.read_bytes()
        artifact = self.parse_bytes(content, target=str(self.path))
        question = self._find_question(artifact, question_id)
        self._require_revision(question, expected_revision)
        if replace_answer:
            if question.state != ProjectQuestionState.ANSWERED:
                self._invalid_transition(question, "replace_answer")
        elif question.state != ProjectQuestionState.TO_ANSWER:
            self._invalid_transition(question, "answer")
        normalized_values = self.validate_answer_values(question, values)
        timestamp = self.clock()
        answer = ProjectQuestionAnswerRevision(
            revision=len(question.answers) + 1,
            values=normalized_values,
            evidence_refs=tuple(sorted({str(item).strip() for item in evidence_refs if str(item).strip()})),
            provided_by=permission_actor.actor_id,
            recorded_by=permission_actor.actor_id,
            answered_at=timestamp,
        )
        updated = replace(
            question,
            revision=question.revision + 1,
            state=ProjectQuestionState.ANSWERED,
            answers=(*question.answers, answer),
            transitions=(
                *question.transitions,
                self._transition(
                    question,
                    operation="replace_answer" if replace_answer else "answer",
                    to_state=ProjectQuestionState.ANSWERED,
                    actor=permission_actor.actor_id,
                    role=permission_actor.role,
                    reason="Owner answer recorded." if not replace_answer else "Owner answer replaced explicitly.",
                    at=timestamp,
                    provenance={"answer_revision": answer.revision},
                ),
            ),
            updated_at=timestamp,
            updated_by=permission_actor.actor_id,
        )
        return self._commit_question_update(
            artifact=artifact,
            source_content=content,
            updated=updated,
            operation_id=operation_id,
            actor=permission_actor.actor_id,
        )

    def defer(
        self,
        question_id: str,
        *,
        actor: str,
        expected_revision: int,
        reason: str,
    ) -> ProjectQuestionOperationResult:
        return self._lifecycle_transition(
            question_id,
            actor=actor,
            expected_revision=expected_revision,
            reason=reason,
            operation="defer",
            to_state=ProjectQuestionState.DEFERRED,
            allowed_from={ProjectQuestionState.TO_ANSWER, ProjectQuestionState.ANSWERED},
        )

    def mute(
        self,
        question_id: str,
        *,
        actor: str,
        expected_revision: int,
        reason: str,
    ) -> ProjectQuestionOperationResult:
        return self._lifecycle_transition(
            question_id,
            actor=actor,
            expected_revision=expected_revision,
            reason=reason,
            operation="mute",
            to_state=ProjectQuestionState.MUTED,
            allowed_from={ProjectQuestionState.TO_ANSWER, ProjectQuestionState.ANSWERED},
        )

    def reopen(
        self,
        question_id: str,
        *,
        actor: str,
        expected_revision: int,
        reason: str,
    ) -> ProjectQuestionOperationResult:
        return self._lifecycle_transition(
            question_id,
            actor=actor,
            expected_revision=expected_revision,
            reason=reason,
            operation="reopen",
            to_state=ProjectQuestionState.TO_ANSWER,
            allowed_from={ProjectQuestionState.DEFERRED, ProjectQuestionState.MUTED},
        )

    def reopen_deferred_triggers(
        self,
        definition: ProjectDefinitionState,
        *,
        actor: str = "system",
    ) -> MutationResult:
        content = self.path.read_bytes()
        artifact = self.parse_bytes(content, target=str(self.path))
        eligible = {
            item.question_id
            for item in artifact.questions
            if item.state == ProjectQuestionState.DEFERRED
            and self._deferred_trigger_matches(item.deferred_trigger, definition)
        }
        if not eligible:
            return MutationResult(
                status="no_op",
                operation_id="project_questions_trigger_reopen",
                actor=actor,
                message="No declared deferred trigger became eligible.",
            )
        timestamp = self.clock()
        questions = tuple(
            replace(
                item,
                revision=item.revision + 1,
                state=ProjectQuestionState.TO_ANSWER,
                transitions=(
                    *item.transitions,
                    self._transition(
                        item,
                        operation="declared_trigger_reopen",
                        to_state=ProjectQuestionState.TO_ANSWER,
                        actor=actor,
                        role="system",
                        reason="A versioned declared deferred trigger became true.",
                        at=timestamp,
                        provenance={"trigger": dict(item.deferred_trigger)},
                    ),
                ),
                updated_at=timestamp,
                updated_by=actor,
            )
            if item.question_id in eligible
            else item
            for item in artifact.questions
        )
        candidate = replace(
            artifact,
            questions=questions,
            updated_at=timestamp,
            updated_by=actor,
        )
        candidate_content = self.candidate_bytes(candidate)
        relative = PROJECT_QUESTIONS_PATH.as_posix()
        source = source_precondition(relative, content)
        preview = MutationPreviewService.build(
            operation_id="project_questions_trigger_reopen",
            targets=(relative,),
            actor=actor,
            authority="deterministic_system",
            sources=(source,),
            candidate_semantics={relative: candidate.semantic_payload()},
            semantic_diff={"reopened_question_ids": sorted(eligible)},
            confirmation_required=False,
            token_context={"question_ids": sorted(eligible), "trigger_policy_version": 1},
        )
        return self.atomic_writer.apply(
            operation_id=preview.operation_id,
            candidates={relative: candidate_content},
            sources=(source,),
            preview_token=preview.preview_token,
            actor=actor,
        )

    def validate_answer_values(
        self,
        question: ProjectQuestion,
        values: Mapping[str, object],
    ) -> dict[str, object]:
        if not isinstance(values, Mapping):
            raise ValueError("P2P342_PROJECT_QUESTION_TRANSITION_INVALID: answer values must be a mapping")
        normalized = {str(key): value for key, value in values.items()}
        missing = [key for key in question.answer_contract.required_fields if key not in normalized]
        if missing:
            raise ValueError(
                "P2P342_PROJECT_QUESTION_TRANSITION_INVALID: missing answer fields "
                + ", ".join(sorted(missing))
            )
        allowed_fields = set(question.answer_contract.required_fields)
        unknown = set(normalized) - allowed_fields
        if unknown:
            raise ValueError(
                "P2P342_PROJECT_QUESTION_TRANSITION_INVALID: unsupported answer fields "
                + ", ".join(sorted(unknown))
            )
        for key in question.answer_contract.required_fields:
            value = normalized[key]
            if isinstance(value, (Mapping, list, tuple, set)) or value is None:
                raise ValueError(
                    f"P2P342_PROJECT_QUESTION_TRANSITION_INVALID: `{key}` must be a scalar value"
                )
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    raise ValueError(
                        f"P2P342_PROJECT_QUESTION_TRANSITION_INVALID: `{key}` cannot be empty"
                    )
                normalized[key] = value
        selector = {
            ProjectQuestionAnswerKind.SECTION_DISPOSITION: "status",
            ProjectQuestionAnswerKind.ASSUMPTION_RESOLUTION: "outcome",
            ProjectQuestionAnswerKind.BLOCKER_RESOLUTION: "outcome",
        }.get(question.answer_contract.kind)
        if selector and question.answer_contract.allowed_values:
            selected = str(normalized.get(selector) or "")
            if selected not in question.answer_contract.allowed_values:
                raise ValueError(
                    f"P2P342_PROJECT_QUESTION_TRANSITION_INVALID: invalid `{selector}` value `{selected}`"
                )
        self._validate_contract_operations(question.answer_contract)
        return normalized

    def _lifecycle_transition(
        self,
        question_id: str,
        *,
        actor: str,
        expected_revision: int,
        reason: str,
        operation: str,
        to_state: ProjectQuestionState,
        allowed_from: set[ProjectQuestionState],
    ) -> ProjectQuestionOperationResult:
        operation_id = f"project_questions_{operation}"
        permission_actor = self.permissions.require_role(actor, "owner", operation=operation_id)
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValueError(
                f"P2P342_PROJECT_QUESTION_TRANSITION_INVALID: `{operation}` requires a non-empty reason"
            )
        content = self.path.read_bytes()
        artifact = self.parse_bytes(content, target=str(self.path))
        question = self._find_question(artifact, question_id)
        self._require_revision(question, expected_revision)
        if question.state not in allowed_from:
            self._invalid_transition(question, operation)
        timestamp = self.clock()
        updated = replace(
            question,
            revision=question.revision + 1,
            state=to_state,
            transitions=(
                *question.transitions,
                self._transition(
                    question,
                    operation=operation,
                    to_state=to_state,
                    actor=permission_actor.actor_id,
                    role=permission_actor.role,
                    reason=normalized_reason,
                    at=timestamp,
                ),
            ),
            updated_at=timestamp,
            updated_by=permission_actor.actor_id,
        )
        return self._commit_question_update(
            artifact=artifact,
            source_content=content,
            updated=updated,
            operation_id=operation_id,
            actor=permission_actor.actor_id,
        )

    def _commit_question_update(
        self,
        *,
        artifact: ProjectQuestionArtifact,
        source_content: bytes,
        updated: ProjectQuestion,
        operation_id: str,
        actor: str,
    ) -> ProjectQuestionOperationResult:
        candidate = replace(
            artifact,
            questions=tuple(
                updated if item.question_id == updated.question_id else item
                for item in artifact.questions
            ),
            updated_at=updated.updated_at,
            updated_by=actor,
        )
        candidate_content = self.candidate_bytes(candidate)
        relative = PROJECT_QUESTIONS_PATH.as_posix()
        source = source_precondition(relative, source_content)
        preview = MutationPreviewService.build(
            operation_id=operation_id,
            targets=(relative,),
            actor=actor,
            authority="owner",
            sources=(source,),
            candidate_semantics={relative: candidate.semantic_payload()},
            semantic_diff={"question_id": updated.question_id, "state": updated.state.value},
            confirmation_required=False,
            token_context={"question_id": updated.question_id, "revision": updated.revision},
        )
        mutation = self.atomic_writer.apply(
            operation_id=operation_id,
            candidates={relative: candidate_content},
            sources=(source,),
            preview_token=preview.preview_token,
            actor=actor,
        )
        return ProjectQuestionOperationResult(
            operation_id=operation_id,
            status=mutation.status,
            question=updated if mutation.status == "applied" else None,
            mutation=mutation,
        )

    @staticmethod
    def _question_order_key(question: ProjectQuestion) -> tuple[int, str, str]:
        priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(question.priority, 4)
        return priority, question.section_id, question.question_id

    @staticmethod
    def _find_question(artifact: ProjectQuestionArtifact, question_id: str) -> ProjectQuestion:
        question = next((item for item in artifact.questions if item.question_id == question_id), None)
        if question is None:
            raise ValueError(f"P2P341_PROJECT_QUESTION_NOT_FOUND: `{question_id}`")
        return question

    @staticmethod
    def _require_revision(question: ProjectQuestion, expected_revision: int) -> None:
        if question.revision != expected_revision:
            raise ValueError(
                f"P2P345_PROJECT_READINESS_STALE_PREVIEW: expected question revision "
                f"{expected_revision}, current is {question.revision}"
            )

    @staticmethod
    def _invalid_transition(question: ProjectQuestion, operation: str) -> None:
        raise ValueError(
            f"P2P342_PROJECT_QUESTION_TRANSITION_INVALID: cannot `{operation}` question "
            f"`{question.question_id}` from `{question.state.value}`"
        )

    @staticmethod
    def _transition(
        question: ProjectQuestion,
        *,
        operation: str,
        to_state: ProjectQuestionState,
        actor: str,
        role: str,
        reason: str,
        at: str,
        provenance: Mapping[str, object] | None = None,
    ) -> ProjectQuestionTransition:
        return ProjectQuestionTransition(
            operation=operation,
            from_state=question.state.value,
            to_state=to_state.value,
            actor=actor,
            role=role,
            reason=reason,
            at=at,
            provenance=dict(provenance or {}),
        )

    @staticmethod
    def _validate_contract_operations(contract: ProjectQuestionAnswerContract) -> None:
        allowlist = {
            ProjectQuestionAnswerKind.FIELD_VALUE: {"set_field"},
            ProjectQuestionAnswerKind.SECTION_DISPOSITION: {"set_section_status"},
            ProjectQuestionAnswerKind.ASSUMPTION_RESOLUTION: {"update_assumption_status"},
            ProjectQuestionAnswerKind.BLOCKER_RESOLUTION: {"clear_blocker"},
            ProjectQuestionAnswerKind.OWNER_DECISION_REFERENCE: {"set_field"},
            ProjectQuestionAnswerKind.INFORMATIONAL: set(),
        }
        declared = set(contract.allowed_definition_operations)
        if not declared.issubset(allowlist[contract.kind]):
            raise ValueError(
                "P2P340_PROJECT_QUESTIONS_INVALID: answer contract contains a non-allowlisted operation"
            )

    @staticmethod
    def _deferred_trigger_matches(
        trigger: Mapping[str, object],
        definition: ProjectDefinitionState,
    ) -> bool:
        if not isinstance(trigger, Mapping):
            return False
        try:
            policy_version = int(trigger.get("policy_version") or 0)
        except (TypeError, ValueError):
            return False
        if policy_version != 1:
            return False
        kind = str(trigger.get("kind") or "")
        section_id = str(trigger.get("section_id") or "")
        section = next((item for item in definition.sections if item.section_id == section_id), None)
        if section is None:
            return False
        if kind == "definition_field_present" and set(trigger) == {
            "policy_version",
            "kind",
            "section_id",
            "field_id",
        }:
            field = section.fields.get(str(trigger.get("field_id") or ""))
            return field is not None and field.value not in (None, "", [], {})
        if kind == "assumption_status" and set(trigger) == {
            "policy_version",
            "kind",
            "section_id",
            "assumption_id",
            "status",
        }:
            return any(
                item.assumption_id == str(trigger.get("assumption_id") or "")
                and item.status == str(trigger.get("status") or "")
                for item in section.assumptions
            )
        if kind == "blocker_cleared" and set(trigger) == {
            "policy_version",
            "kind",
            "section_id",
            "blocker_id",
        }:
            blocker_id = str(trigger.get("blocker_id") or "")
            return all(item.blocker_id != blocker_id or item.status != "open" for item in section.blockers)
        return False

    def seed_from_definition(
        self,
        *,
        project_id: str,
        definition: ProjectDefinitionState,
        pack: VerticalPack,
        lock_checksum: str,
        actor: str,
        audit_at: str,
        legacy_bindings: Mapping[str, Mapping[str, object]] | None = None,
    ) -> ProjectQuestionSeedResult:
        questions: list[ProjectQuestion] = []
        diagnostics: list[ProjectReadinessDiagnostic] = []
        migrated_count = 0
        generated_count = 0
        pack_sections = {section.section_id: section for section in pack.sections}
        definition_sections = {section.section_id: section for section in definition.sections}
        bindings = dict(legacy_bindings or {})
        consumed_bindings: set[str] = set()
        for section in sorted(pack.sections, key=lambda item: (item.priority, item.section_id)):
            state = definition_sections.get(section.section_id)
            if state is None or state.status in {"complete", "not_applicable"} or not section.required:
                continue
            seen_legacy: dict[str, str] = {}
            for legacy in state.open_questions:
                previous = seen_legacy.setdefault(legacy.question_id, legacy.question)
                if previous != legacy.question:
                    raise ValueError(
                        f"P2P350_AMBIGUOUS_LEGACY_QUESTION: section `{section.section_id}` "
                        f"contains conflicting `{legacy.question_id}` records"
                    )
                binding_key = f"{section.section_id}/{legacy.question_id}"
                explicit_binding = bindings.get(binding_key)
                if explicit_binding is not None:
                    binding = self._owner_legacy_binding(
                        explicit_binding,
                        state=state,
                        section=section,
                        pack=pack,
                        binding_key=binding_key,
                    )
                    consumed_bindings.add(binding_key)
                else:
                    binding = self._bind_legacy_question(legacy.field_id, state, section, pack)
                if binding is None:
                    raise ValueError(
                        f"P2P350_AMBIGUOUS_LEGACY_QUESTION: cannot bind `{legacy.question_id}` "
                        f"in section `{section.section_id}` without owner target input"
                    )
                target, contract = binding
                questions.append(
                    self._new_question(
                        project_id=project_id,
                        pack=pack,
                        lock_checksum=lock_checksum,
                        section=section,
                        state=state,
                        wording=legacy.question,
                        target=target,
                        contract=contract,
                        source_kind=ProjectQuestionSourceType.MIGRATED_LEGACY,
                        source_question_id=legacy.question_id,
                        source_key=f"legacy:{section.section_id}:{legacy.question_id}:{target.kind}:{target.target_id}",
                        actor=actor,
                        audit_at=audit_at,
                    )
                )
                migrated_count += 1
            if state.open_questions:
                continue
            selected_questions = self._declared_or_fallbacks(pack, section, state)
            if not selected_questions:
                diagnostics.append(
                    ProjectReadinessDiagnostic(
                        code="P2P344_PROJECT_QUESTION_NO_SAFE_FALLBACK",
                        severity="warning",
                        message=f"No deterministic safe question target exists for `{section.section_id}`.",
                        suggested_command=f"p2p project section show {section.section_id}",
                        section_id=section.section_id,
                    )
                )
                continue
            for (
                wording,
                target,
                contract,
                source_kind,
                source_question_id,
                source_key,
                deferred_trigger,
            ) in selected_questions:
                questions.append(
                    self._new_question(
                        project_id=project_id,
                        pack=pack,
                        lock_checksum=lock_checksum,
                        section=section,
                        state=state,
                        wording=wording,
                        target=target,
                        contract=contract,
                        source_kind=source_kind,
                        source_question_id=source_question_id,
                        source_key=source_key,
                        actor=actor,
                        audit_at=audit_at,
                        deferred_trigger=deferred_trigger,
                    )
                )
                generated_count += 1

        unused_bindings = sorted(set(bindings) - consumed_bindings)
        if unused_bindings:
            raise ValueError(
                f"P2P350_AMBIGUOUS_LEGACY_QUESTION: unknown legacy binding `{unused_bindings[0]}`"
            )
        self._validate_question_id_collisions(questions)
        groups = self._groups_for_questions(pack.vertical_id, questions)
        artifact = ProjectQuestionArtifact(
            project_id=project_id,
            vertical_id=pack.vertical_id,
            vertical_version=pack.version,
            lock_checksum=lock_checksum,
            groups=groups,
            questions=tuple(sorted(questions, key=lambda item: item.question_id)),
            created_at=audit_at,
            created_by=actor,
            updated_at=audit_at,
            updated_by=actor,
        )
        self.validate_artifact(artifact)
        return ProjectQuestionSeedResult(
            artifact=artifact,
            diagnostics=tuple(diagnostics),
            migrated_count=migrated_count,
            generated_count=generated_count,
        )

    @staticmethod
    def has_owner_evidence(artifact: ProjectQuestionArtifact) -> bool:
        owner_states = {
            ProjectQuestionState.ANSWERED,
            ProjectQuestionState.APPLIED,
            ProjectQuestionState.DEFERRED,
            ProjectQuestionState.MUTED,
        }
        return any(
            item.answers
            or item.applications
            or item.state in owner_states
            for item in artifact.questions
        )

    def mark_reconciliation_required(
        self,
        artifact: ProjectQuestionArtifact,
        *,
        actor: str,
        audit_at: str,
    ) -> ProjectQuestionArtifact:
        questions = tuple(
            replace(
                item,
                revision=item.revision + 1,
                applicability=ProjectQuestionApplicability.RECONCILIATION_REQUIRED,
                updated_at=audit_at,
                updated_by=actor,
            )
            if item.applicability == ProjectQuestionApplicability.ACTIVE
            else item
            for item in artifact.questions
        )
        candidate = replace(
            artifact,
            questions=questions,
            updated_at=audit_at,
            updated_by=actor,
        )
        self.validate_artifact(candidate)
        return candidate

    def reconcile_candidate(
        self,
        *,
        current: ProjectQuestionArtifact,
        project_id: str,
        definition: ProjectDefinitionState,
        pack: VerticalPack,
        lock_checksum: str,
        actor: str,
        audit_at: str,
    ) -> ProjectQuestionReconciliationCandidate:
        seeded = self.seed_from_definition(
            project_id=project_id,
            definition=definition,
            pack=pack,
            lock_checksum=lock_checksum,
            actor=actor,
            audit_at=audit_at,
        ).artifact
        new_by_id = {item.question_id: item for item in seeded.questions}
        consumed: set[str] = set()
        preserved: list[str] = []
        revised: list[str] = []
        retired: list[str] = []
        superseded: list[str] = []
        inactive: list[str] = []
        owner_evidence: list[str] = []
        result: list[ProjectQuestion] = []
        aliases: dict[str, ProjectQuestion] = {}
        semantic_replacements: dict[str, ProjectQuestion] = {}
        declared_by_id = {item.question_id: item for item in pack.questions}
        for candidate in seeded.questions:
            declared = declared_by_id.get(candidate.source_question_id)
            if declared is None:
                continue
            if current.vertical_id == pack.vertical_id:
                previous = semantic_replacements.get(candidate.source_question_id)
                if previous is not None and previous.question_id != candidate.question_id:
                    raise ValueError(
                        "P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED: duplicate declared "
                        f"question lineage `{candidate.source_question_id}`"
                    )
                semantic_replacements[candidate.source_question_id] = candidate
            for alias in declared.aliases:
                if alias in aliases:
                    raise ValueError(f"P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED: duplicate alias `{alias}`")
                aliases[alias] = candidate

        for old in current.questions:
            replacement = new_by_id.get(old.question_id)
            if replacement is not None:
                consumed.add(replacement.question_id)
                if old.state in {
                    ProjectQuestionState.APPLIED,
                    ProjectQuestionState.RETIRED,
                    ProjectQuestionState.SUPERSEDED,
                }:
                    revisions = (*old.revisions, self._revision_snapshot(old, actor=actor, at=audit_at))
                    result.append(
                        replace(
                            replacement,
                            revision=old.revision + 1,
                            state=ProjectQuestionState.TO_ANSWER,
                            applicability=ProjectQuestionApplicability.ACTIVE,
                            revisions=revisions,
                            answers=old.answers,
                            applications=old.applications,
                            transitions=old.transitions,
                            superseded_by="",
                            created_at=old.created_at,
                            created_by=old.created_by,
                            updated_at=audit_at,
                            updated_by=actor,
                        )
                    )
                    revised.append(old.question_id)
                    if old.answers or old.applications:
                        owner_evidence.append(old.question_id)
                    continue
                changed = any(
                    (
                        old.wording_sha256 != replacement.wording_sha256,
                        old.answer_contract != replacement.answer_contract,
                        old.vertical_version != replacement.vertical_version,
                        old.lock_checksum != replacement.lock_checksum,
                        old.applicability != ProjectQuestionApplicability.ACTIVE,
                    )
                )
                if old.answer_contract != replacement.answer_contract and old.answers:
                    probe = replace(old, answer_contract=replacement.answer_contract)
                    try:
                        self.validate_answer_values(probe, old.answers[-1].values)
                    except ValueError as exc:
                        raise ValueError(
                            "P2P347_PROJECT_QUESTION_RECONCILIATION_REQUIRED: changed answer "
                            f"contract invalidates owner evidence for `{old.question_id}`; declare "
                            "a replacement question identity"
                        ) from exc
                    owner_evidence.append(old.question_id)
                revisions = old.revisions
                revision = old.revision
                if changed:
                    revisions = (
                        *old.revisions,
                        self._revision_snapshot(old, actor=actor, at=audit_at),
                    )
                    revision += 1
                    revised.append(old.question_id)
                else:
                    preserved.append(old.question_id)
                result.append(
                    replace(
                        replacement,
                        revision=revision,
                        state=old.state,
                        applicability=ProjectQuestionApplicability.ACTIVE,
                        revisions=revisions,
                        answers=old.answers,
                        applications=old.applications,
                        transitions=old.transitions,
                        superseded_by=old.superseded_by,
                        created_at=old.created_at,
                        created_by=old.created_by,
                        updated_at=audit_at if changed else old.updated_at,
                        updated_by=actor if changed else old.updated_by,
                    )
                )
                continue

            lineage_replacement = (
                semantic_replacements.get(old.source_question_id)
                if old.source_kind == ProjectQuestionSourceType.VERTICAL_DECLARED
                else None
            )
            alias_replacement = lineage_replacement or aliases.get(old.source_question_id)
            if alias_replacement is not None:
                if (
                    old.state == ProjectQuestionState.SUPERSEDED
                    and old.superseded_by == alias_replacement.question_id
                ):
                    result.append(old)
                    continue
                old_state = old.state
                applicability = ProjectQuestionApplicability.TARGET_REMOVED
                superseded_by = alias_replacement.question_id
                if old.state not in {ProjectQuestionState.APPLIED, ProjectQuestionState.RETIRED}:
                    old_state = ProjectQuestionState.SUPERSEDED
                    superseded.append(old.question_id)
                else:
                    inactive.append(old.question_id)
                transitions = old.transitions
                if old_state == ProjectQuestionState.SUPERSEDED and old.state != ProjectQuestionState.SUPERSEDED:
                    transitions = (
                        *transitions,
                        self._reconciliation_transition(
                            old,
                            to_state=ProjectQuestionState.SUPERSEDED,
                            actor=actor,
                            at=audit_at,
                            reason="Question semantic target was superseded during vertical reconciliation.",
                            provenance={"superseded_by": superseded_by},
                        ),
                    )
                result.append(
                    replace(
                        old,
                        revision=old.revision + 1,
                        state=old_state,
                        applicability=applicability,
                        superseded_by=superseded_by,
                        transitions=transitions,
                        updated_at=audit_at,
                        updated_by=actor,
                    )
                )
                continue

            if old.applicability == ProjectQuestionApplicability.TARGET_REMOVED:
                result.append(old)
                if old.answers or old.applications or old.state in {
                    ProjectQuestionState.ANSWERED,
                    ProjectQuestionState.APPLIED,
                    ProjectQuestionState.DEFERRED,
                    ProjectQuestionState.MUTED,
                }:
                    inactive.append(old.question_id)
                continue
            if old.state == ProjectQuestionState.TO_ANSWER:
                result.append(
                    replace(
                        old,
                        revision=old.revision + 1,
                        state=ProjectQuestionState.RETIRED,
                        applicability=ProjectQuestionApplicability.TARGET_REMOVED,
                        transitions=(
                            *old.transitions,
                            self._reconciliation_transition(
                                old,
                                to_state=ProjectQuestionState.RETIRED,
                                actor=actor,
                                at=audit_at,
                                reason="Question target is no longer required by the active vertical.",
                            ),
                        ),
                        updated_at=audit_at,
                        updated_by=actor,
                    )
                )
                retired.append(old.question_id)
            else:
                result.append(
                    replace(
                        old,
                        revision=old.revision + 1,
                        applicability=ProjectQuestionApplicability.TARGET_REMOVED,
                        updated_at=audit_at,
                        updated_by=actor,
                    )
                )
                inactive.append(old.question_id)

        created = sorted(set(new_by_id) - consumed)
        result.extend(new_by_id[item] for item in created)
        ordered = tuple(sorted(result, key=lambda item: item.question_id))
        artifact = ProjectQuestionArtifact(
            project_id=project_id,
            vertical_id=pack.vertical_id,
            vertical_version=pack.version,
            lock_checksum=lock_checksum,
            groups=self._groups_for_questions(pack.vertical_id, ordered),
            questions=ordered,
            created_at=current.created_at,
            created_by=current.created_by,
            updated_at=audit_at,
            updated_by=actor,
        )
        self.validate_artifact(artifact)
        return ProjectQuestionReconciliationCandidate(
            artifact=artifact,
            preserved_ids=tuple(sorted(preserved)),
            revised_ids=tuple(sorted(revised)),
            created_ids=tuple(created),
            retired_ids=tuple(sorted(retired)),
            superseded_ids=tuple(sorted(superseded)),
            inactive_evidence_ids=tuple(sorted(inactive)),
            owner_evidence_ids=tuple(sorted(owner_evidence)),
        )

    @staticmethod
    def _revision_snapshot(
        question: ProjectQuestion,
        *,
        actor: str,
        at: str,
    ) -> ProjectQuestionRevision:
        return ProjectQuestionRevision(
            revision=question.revision,
            wording_sha256=question.wording_sha256,
            question=question.question,
            vertical_version=question.vertical_version,
            lock_checksum=question.lock_checksum,
            answer_contract=question.answer_contract,
            changed_at=at,
            changed_by=actor,
        )

    @staticmethod
    def _reconciliation_transition(
        question: ProjectQuestion,
        *,
        to_state: ProjectQuestionState,
        actor: str,
        at: str,
        reason: str,
        provenance: Mapping[str, object] | None = None,
    ) -> ProjectQuestionTransition:
        return ProjectQuestionTransition(
            operation="vertical_reconciliation",
            from_state=question.state.value,
            to_state=to_state.value,
            actor=actor,
            role="system",
            reason=reason,
            at=at,
            provenance=dict(provenance or {}),
        )

    def _new_question(
        self,
        *,
        project_id: str,
        pack: VerticalPack,
        lock_checksum: str,
        section: VerticalSection,
        state: ProjectDefinitionSectionState,
        wording: str,
        target: ProjectQuestionTarget,
        contract: ProjectQuestionAnswerContract,
        source_kind: ProjectQuestionSourceType,
        source_question_id: str,
        source_key: str,
        actor: str,
        audit_at: str,
        deferred_trigger: Mapping[str, object] | None = None,
    ) -> ProjectQuestion:
        gap_kind = _gap_kind_for_contract(contract.kind)
        gap_target_kind = "section" if contract.kind == ProjectQuestionAnswerKind.SECTION_DISPOSITION else target.kind
        gap_id, _ = readiness_gap_identity(
            vertical_id=pack.vertical_id,
            section_id=section.section_id,
            kind=ProjectReadinessGapKind(gap_kind),
            target_kind=gap_target_kind,
            target_id=target.target_id,
        )
        question_id, identity_digest = project_question_identity(
            vertical_id=pack.vertical_id,
            section_id=section.section_id,
            gap_kind=gap_kind,
            target_kind=target.kind,
            target_id=target.target_id,
            source_key=source_key,
        )
        return ProjectQuestion(
            question_id=question_id,
            identity_sha256=identity_digest,
            revision=1,
            wording_sha256=project_question_wording_sha256(wording),
            question=wording.strip(),
            state=ProjectQuestionState.TO_ANSWER,
            applicability=ProjectQuestionApplicability.ACTIVE,
            section_id=section.section_id,
            gap_id=gap_id,
            target=target,
            priority="high" if section.required else "medium",
            rationale=f"Required input for project definition section `{section.section_id}`.",
            source_kind=source_kind,
            source_question_id=source_question_id,
            source_key=source_key,
            vertical_id=pack.vertical_id,
            vertical_version=pack.version,
            lock_checksum=lock_checksum,
            fallback_policy_version=PROJECT_QUESTION_FALLBACK_POLICY_VERSION,
            answer_contract=contract,
            deferred_trigger=dict(deferred_trigger or {}),
            created_at=audit_at,
            created_by=actor,
            updated_at=audit_at,
            updated_by=actor,
        )

    def _declared_or_fallbacks(
        self,
        pack: VerticalPack,
        section: VerticalSection,
        state: ProjectDefinitionSectionState,
    ) -> tuple[ProjectQuestionSelection, ...]:
        explicit: list[ProjectQuestionSelection] = []
        implicit: list[ProjectQuestionSelection] = []
        for declared in sorted(
            (item for item in pack.questions if item.section_id == section.section_id),
            key=lambda item: item.question_id,
        ):
            binding = self._bind_declared_question(declared, state, section, pack)
            if binding is None:
                continue
            target, contract = binding
            selected = (
                declared.question,
                target,
                contract,
                ProjectQuestionSourceType.VERTICAL_DECLARED,
                declared.question_id,
                f"declared:{declared.question_id}",
                declared.deferred_trigger,
            )
            (explicit if declared.target_kind and declared.target_id else implicit).append(selected)
        selected_questions = explicit or implicit[:1]
        if selected_questions:
            seen_targets: set[tuple[str, str]] = set()
            typed: list[ProjectQuestionSelection] = []
            for selected in selected_questions:
                target = selected[1]
                assert isinstance(target, ProjectQuestionTarget)
                target_key = (target.kind, target.target_id)
                if target_key in seen_targets:
                    raise ValueError(
                        "P2P340_PROJECT_QUESTIONS_INVALID: multiple declared questions target "
                        f"`{section.section_id}/{target.kind}/{target.target_id}`"
                    )
                seen_targets.add(target_key)
                typed.append(selected)
            return tuple(typed)
        fallback = self._fallback_binding(state, section, pack)
        if fallback is None:
            return ()
        wording, target, contract, template_key = fallback
        return (
            (
                wording,
                target,
                contract,
                ProjectQuestionSourceType.DETERMINISTIC_FALLBACK,
                "",
                f"fallback:{template_key}",
                {},
            ),
        )

    def _bind_declared_question(
        self,
        declared: VerticalQuestion,
        state: ProjectDefinitionSectionState,
        section: VerticalSection,
        pack: VerticalPack,
    ) -> tuple[ProjectQuestionTarget, ProjectQuestionAnswerContract] | None:
        if declared.target_kind and declared.target_id:
            target = ProjectQuestionTarget(declared.target_kind, declared.target_id)
            if not self._target_is_applicable(target, state=state, section=section, pack=pack):
                return None
            contract = _contract_from_mapping(declared.answer_contract) if declared.answer_contract else None
            if contract is None:
                contract = _default_contract_for_target(declared.target_kind)
            self._validate_contract_operations(contract)
            return target, contract
        return self._safe_binding(state, section, pack)

    @staticmethod
    def _target_is_applicable(
        target: ProjectQuestionTarget,
        *,
        state: ProjectDefinitionSectionState,
        section: VerticalSection,
        pack: VerticalPack,
    ) -> bool:
        if target.kind == "field":
            known = {item.field_id for item in _section_fields(section, pack)}
            if target.target_id not in known:
                raise ValueError(
                    f"P2P340_PROJECT_QUESTIONS_INVALID: unknown declared field `{target.target_id}`"
                )
            return target.target_id in set(state.missing_required_fields)
        if target.kind == "assumption":
            matching = [item for item in state.assumptions if item.assumption_id == target.target_id]
            if not matching:
                raise ValueError(
                    f"P2P340_PROJECT_QUESTIONS_INVALID: unknown declared assumption `{target.target_id}`"
                )
            return matching[0].status == "to_validate"
        if target.kind == "blocker":
            matching = [item for item in state.blockers if item.blocker_id == target.target_id]
            if not matching:
                raise ValueError(
                    f"P2P340_PROJECT_QUESTIONS_INVALID: unknown declared blocker `{target.target_id}`"
                )
            return matching[0].status == "open"
        if target.kind == "section":
            if target.target_id != section.section_id:
                raise ValueError(
                    f"P2P340_PROJECT_QUESTIONS_INVALID: unknown declared section `{target.target_id}`"
                )
            return state.status not in {"complete", "not_applicable"}
        raise ValueError(
            f"P2P340_PROJECT_QUESTIONS_INVALID: unsupported declared target kind `{target.kind}`"
        )

    def _bind_legacy_question(
        self,
        field_id: str,
        state: ProjectDefinitionSectionState,
        section: VerticalSection,
        pack: VerticalPack,
    ) -> tuple[ProjectQuestionTarget, ProjectQuestionAnswerContract] | None:
        if field_id:
            if field_id not in {item.field_id for item in _section_fields(section, pack)}:
                raise ValueError(
                    f"P2P350_AMBIGUOUS_LEGACY_QUESTION: unknown field `{field_id}` in `{section.section_id}`"
                )
            return ProjectQuestionTarget("field", field_id), _field_value_contract()
        return self._safe_binding(state, section, pack)

    def _owner_legacy_binding(
        self,
        raw: Mapping[str, object],
        *,
        state: ProjectDefinitionSectionState,
        section: VerticalSection,
        pack: VerticalPack,
        binding_key: str,
    ) -> tuple[ProjectQuestionTarget, ProjectQuestionAnswerContract]:
        allowed = {"target_kind", "target_id", "answer_contract"}
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(
                f"P2P350_AMBIGUOUS_LEGACY_QUESTION: binding `{binding_key}` contains forbidden "
                f"fields {sorted(unknown)}"
            )
        target_kind = str(raw.get("target_kind") or "").strip()
        target_id = str(raw.get("target_id") or "").strip()
        if not target_kind or not target_id:
            raise ValueError(
                f"P2P350_AMBIGUOUS_LEGACY_QUESTION: binding `{binding_key}` requires target_kind and target_id"
            )
        if target_kind == "field":
            if target_id not in {item.field_id for item in _section_fields(section, pack)}:
                raise ValueError(f"P2P350_AMBIGUOUS_LEGACY_QUESTION: unknown field `{target_id}`")
        elif target_kind == "assumption":
            if target_id not in {item.assumption_id for item in state.assumptions}:
                raise ValueError(f"P2P350_AMBIGUOUS_LEGACY_QUESTION: unknown assumption `{target_id}`")
        elif target_kind == "blocker":
            if target_id not in {item.blocker_id for item in state.blockers}:
                raise ValueError(f"P2P350_AMBIGUOUS_LEGACY_QUESTION: unknown blocker `{target_id}`")
        elif target_kind == "section":
            if target_id != section.section_id:
                raise ValueError(f"P2P350_AMBIGUOUS_LEGACY_QUESTION: unknown section `{target_id}`")
        else:
            raise ValueError(f"P2P350_AMBIGUOUS_LEGACY_QUESTION: unsupported target kind `{target_kind}`")
        contract = _default_contract_for_target(target_kind)
        requested_contract = str(raw.get("answer_contract") or contract.kind.value).strip()
        if requested_contract != contract.kind.value:
            raise ValueError(
                f"P2P350_AMBIGUOUS_LEGACY_QUESTION: contract `{requested_contract}` does not match "
                f"target kind `{target_kind}`"
            )
        return ProjectQuestionTarget(target_kind, target_id), contract

    def _safe_binding(
        self,
        state: ProjectDefinitionSectionState,
        section: VerticalSection,
        pack: VerticalPack,
    ) -> tuple[ProjectQuestionTarget, ProjectQuestionAnswerContract] | None:
        missing = [item for item in state.missing_required_fields if item]
        if len(missing) == 1:
            return ProjectQuestionTarget("field", missing[0]), _field_value_contract()
        unresolved_assumptions = [item for item in state.assumptions if item.status == "to_validate"]
        if not missing and len(unresolved_assumptions) == 1:
            return (
                ProjectQuestionTarget("assumption", unresolved_assumptions[0].assumption_id),
                _assumption_contract(),
            )
        open_blockers = [item for item in state.blockers if item.status == "open"]
        if not missing and not unresolved_assumptions and len(open_blockers) == 1:
            return ProjectQuestionTarget("blocker", open_blockers[0].blocker_id), _blocker_contract()
        return None

    def _fallback_binding(
        self,
        state: ProjectDefinitionSectionState,
        section: VerticalSection,
        pack: VerticalPack,
    ) -> tuple[str, ProjectQuestionTarget, ProjectQuestionAnswerContract, str] | None:
        binding = self._safe_binding(state, section, pack)
        if binding is not None:
            target, contract = binding
            if target.kind == "field":
                field = next(item for item in _section_fields(section, pack) if item.field_id == target.target_id)
                wording = field.question or f"What value should `{field.label}` have?"
                return wording, target, contract, "single_missing_field"
            if target.kind == "assumption":
                return (
                    f"Should assumption `{target.target_id}` be validated or rejected?",
                    target,
                    contract,
                    "single_assumption_resolution",
                )
            if target.kind == "blocker":
                return (
                    f"Should blocker `{target.target_id}` be cleared or retained?",
                    target,
                    contract,
                    "single_blocker_resolution",
                )
        unresolved_assumptions = any(item.status == "to_validate" for item in state.assumptions)
        open_blockers = any(item.status == "open" for item in state.blockers)
        if not state.missing_required_fields and not unresolved_assumptions and not open_blockers:
            policy = section.completion_policy
            if policy is not None:
                return (
                    f"What is the reviewed disposition for section `{section.title}`?",
                    ProjectQuestionTarget("section", section.section_id),
                    _section_disposition_contract(),
                    "section_disposition",
                )
        return None

    @staticmethod
    def _groups_for_questions(
        vertical_id: str,
        questions: Sequence[ProjectQuestion],
    ) -> tuple[ProjectQuestionGroup, ...]:
        grouped: dict[tuple[str, str], list[str]] = {}
        for question in questions:
            grouped.setdefault((question.gap_id, question.section_id), []).append(question.question_id)
        result: list[ProjectQuestionGroup] = []
        for (gap_id, section_id), question_ids in sorted(grouped.items()):
            group_id, digest = project_question_group_identity(
                vertical_id=vertical_id,
                section_id=section_id,
                gap_id=gap_id,
            )
            result.append(
                ProjectQuestionGroup(
                    group_id=group_id,
                    identity_sha256=digest,
                    gap_id=gap_id,
                    section_id=section_id,
                    question_ids=tuple(sorted(question_ids)),
                )
            )
        return tuple(result)

    @staticmethod
    def _validate_question_id_collisions(questions: Sequence[ProjectQuestion]) -> None:
        seen: dict[str, str] = {}
        for question in questions:
            previous = seen.setdefault(question.question_id, question.identity_sha256)
            if previous != question.identity_sha256:
                raise ValueError(f"Project question id collision for `{question.question_id}`")

    def _parse_question(self, value: object, *, target: str) -> ProjectQuestion:
        raw = _mapping(value, target)
        _reject_unknown_fields(raw, _QUESTION_KEYS, target)
        source = _required_mapping(raw, "source", target)
        target_value = _required_mapping(raw, "target", target)
        _reject_unknown_fields(source, _SOURCE_KEYS, f"{target}.source")
        _reject_unknown_fields(target_value, _TARGET_KEYS, f"{target}.target")
        contract = _contract_from_mapping(_required_mapping(raw, "answer_contract", target))
        return ProjectQuestion(
            question_id=_required_text(raw, "id", target),
            identity_sha256=_required_text(raw, "identity_sha256", target),
            revision=_required_int(raw, "revision", target),
            wording_sha256=_required_text(raw, "wording_sha256", target),
            question=_required_text(raw, "question", target),
            state=ProjectQuestionState(_required_text(raw, "state", target)),
            applicability=ProjectQuestionApplicability(_required_text(raw, "applicability", target)),
            section_id=_required_text(raw, "section_id", target),
            gap_id=_required_text(raw, "gap_id", target),
            target=ProjectQuestionTarget(
                kind=_required_text(target_value, "kind", target),
                target_id=_required_text(target_value, "id", target),
            ),
            priority=_required_text(raw, "priority", target),
            rationale=_required_text(raw, "rationale", target),
            source_kind=ProjectQuestionSourceType(_required_text(source, "kind", target)),
            source_question_id=str(source.get("question_id") or ""),
            source_key=_required_text(source, "key", target),
            vertical_id=_required_text(source, "vertical_id", target),
            vertical_version=_required_text(source, "vertical_version", target),
            lock_checksum=_required_text(source, "lock_checksum", target),
            fallback_policy_version=_required_int(source, "fallback_policy_version", target),
            answer_contract=contract,
            deferred_trigger=dict(_optional_mapping(raw.get("deferred_trigger"), target)),
            revisions=tuple(
                _parse_question_revision(item, target=f"{target}.revisions[{index}]")
                for index, item in enumerate(_sequence(raw.get("revisions"), target))
            ),
            answers=tuple(
                _parse_answer(item, target=f"{target}.answers[{index}]")
                for index, item in enumerate(_sequence(raw.get("answers"), target))
            ),
            applications=tuple(
                _parse_application(item, target=f"{target}.applications[{index}]")
                for index, item in enumerate(_sequence(raw.get("applications"), target))
            ),
            transitions=tuple(
                _parse_transition(item, target=f"{target}.transitions[{index}]")
                for index, item in enumerate(_sequence(raw.get("transitions"), target))
            ),
            superseded_by=str(raw.get("superseded_by") or ""),
            created_at=_required_timestamp(raw, "created_at", target),
            created_by=_required_text(raw, "created_by", target),
            updated_at=_required_timestamp(raw, "updated_at", target),
            updated_by=_required_text(raw, "updated_by", target),
        )

    @staticmethod
    def _parse_group(value: object, *, target: str) -> ProjectQuestionGroup:
        raw = _mapping(value, target)
        _reject_unknown_fields(raw, _GROUP_KEYS, target)
        return ProjectQuestionGroup(
            group_id=_required_text(raw, "id", target),
            identity_sha256=_required_text(raw, "identity_sha256", target),
            gap_id=_required_text(raw, "gap_id", target),
            section_id=_required_text(raw, "section_id", target),
            question_ids=tuple(str(item) for item in _required_sequence(raw, "question_ids", target)),
        )

    @staticmethod
    def _validate_question_history(question: ProjectQuestion, *, target: str) -> None:
        if question.state == ProjectQuestionState.ANSWERED and not question.answers:
            raise ValueError(f"Invalid {target}: answered question has no answer `{question.question_id}`")
        if question.state == ProjectQuestionState.APPLIED and not question.applications:
            raise ValueError(f"Invalid {target}: applied question has no application `{question.question_id}`")
        if question.state == ProjectQuestionState.SUPERSEDED and not question.superseded_by:
            raise ValueError(f"Invalid {target}: superseded question has no replacement `{question.question_id}`")
        answer_revisions = [item.revision for item in question.answers]
        if answer_revisions != list(range(1, len(answer_revisions) + 1)):
            raise ValueError(f"Invalid {target}: answer revisions are not contiguous `{question.question_id}`")
        terminal = {
            ProjectQuestionState.APPLIED,
            ProjectQuestionState.RETIRED,
            ProjectQuestionState.SUPERSEDED,
        }
        for transition in question.transitions:
            try:
                ProjectQuestionState(transition.from_state)
                ProjectQuestionState(transition.to_state)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid {target}: transition contains unknown state `{question.question_id}`"
                ) from exc
            if transition.from_state in {item.value for item in terminal}:
                raise ValueError(f"Invalid {target}: terminal question was transitioned `{question.question_id}`")
            if not transition.reason.strip():
                raise ValueError(f"Invalid {target}: transition reason is required `{question.question_id}`")
        for application in question.applications:
            if application.question_ids and question.question_id not in application.question_ids:
                raise ValueError(
                    f"Invalid {target}: application omits owning question `{question.question_id}`"
                )


def _contract_from_mapping(raw: Mapping[str, object]) -> ProjectQuestionAnswerContract:
    _reject_unknown_fields(raw, _CONTRACT_KEYS, "answer_contract")
    return ProjectQuestionAnswerContract(
        kind=ProjectQuestionAnswerKind(_required_text(raw, "kind", "answer_contract")),
        required_fields=tuple(str(item) for item in _required_sequence(raw, "required_fields", "answer_contract")),
        allowed_definition_operations=tuple(
            str(item)
            for item in _required_sequence(raw, "allowed_definition_operations", "answer_contract")
        ),
        allowed_values=tuple(str(item) for item in _sequence(raw.get("allowed_values"), "answer_contract")),
    )


def _default_contract_for_target(target_kind: str) -> ProjectQuestionAnswerContract:
    contracts = {
        "field": _field_value_contract,
        "section": _section_disposition_contract,
        "assumption": _assumption_contract,
        "blocker": _blocker_contract,
    }
    factory = contracts.get(target_kind)
    if factory is None:
        return ProjectQuestionAnswerContract(
            kind=ProjectQuestionAnswerKind.INFORMATIONAL,
            required_fields=("value",),
            allowed_definition_operations=(),
        )
    return factory()


def _field_value_contract() -> ProjectQuestionAnswerContract:
    return ProjectQuestionAnswerContract(
        kind=ProjectQuestionAnswerKind.FIELD_VALUE,
        required_fields=("value",),
        allowed_definition_operations=("set_field",),
    )


def _section_disposition_contract() -> ProjectQuestionAnswerContract:
    return ProjectQuestionAnswerContract(
        kind=ProjectQuestionAnswerKind.SECTION_DISPOSITION,
        required_fields=("status", "rationale"),
        allowed_definition_operations=("set_section_status",),
        allowed_values=("complete", "partial", "blocked", "not_applicable"),
    )


def _assumption_contract() -> ProjectQuestionAnswerContract:
    return ProjectQuestionAnswerContract(
        kind=ProjectQuestionAnswerKind.ASSUMPTION_RESOLUTION,
        required_fields=("outcome", "rationale"),
        allowed_definition_operations=("update_assumption_status",),
        allowed_values=("validated", "rejected"),
    )


def _blocker_contract() -> ProjectQuestionAnswerContract:
    return ProjectQuestionAnswerContract(
        kind=ProjectQuestionAnswerKind.BLOCKER_RESOLUTION,
        required_fields=("outcome", "rationale"),
        allowed_definition_operations=("clear_blocker",),
        allowed_values=("clear", "retain"),
    )


def _gap_kind_for_contract(kind: ProjectQuestionAnswerKind) -> str:
    if kind == ProjectQuestionAnswerKind.ASSUMPTION_RESOLUTION:
        return ProjectReadinessGapKind.ASSUMPTION_TO_VALIDATE.value
    if kind == ProjectQuestionAnswerKind.BLOCKER_RESOLUTION:
        return ProjectReadinessGapKind.OWNER_DECISION_BLOCKER.value
    return ProjectReadinessGapKind.INCOMPLETE_REQUIRED_DEFINITION.value


def _section_fields(section: VerticalSection, pack: VerticalPack) -> list[VerticalField]:
    if section.fields:
        return section.fields
    question = next((item for item in pack.questions if item.section_id == section.section_id), None)
    return [
        VerticalField(
            field_id="summary",
            label=section.title,
            required=section.required,
            question=question.question if question else "",
        )
    ]


def _mapping(value: object, target: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Invalid {target}: expected a mapping")
    return value


def _required_mapping(value: Mapping[str, object], key: str, target: str) -> Mapping[str, object]:
    return _mapping(value.get(key), f"{target}.{key}")


def _sequence(value: object, target: str) -> Sequence[object]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"Invalid {target}: expected a sequence")
    return value


def _required_sequence(value: Mapping[str, object], key: str, target: str) -> Sequence[object]:
    return _sequence(value.get(key), f"{target}.{key}")


def _required_text(value: Mapping[str, object], key: str, target: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"Invalid {target}: `{key}` is required")
    return raw.strip()


def _required_timestamp(value: Mapping[str, object], key: str, target: str) -> str:
    raw = value.get(key)
    if isinstance(raw, str):
        text = raw.strip()
    elif isinstance(raw, (date, datetime)):
        text = str(raw)
    else:
        text = ""
    if not text:
        raise ValueError(f"Invalid {target}: `{key}` timestamp is required")
    return text


def _required_int(value: Mapping[str, object], key: str, target: str) -> int:
    return _coerce_int(value.get(key), f"{target}.{key}")


def _coerce_int(value: object, target: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Invalid {target}: must be an integer")
    return value


def _parse_question_revision(value: object, *, target: str) -> ProjectQuestionRevision:
    raw = _mapping(value, target)
    _reject_unknown_fields(raw, _REVISION_KEYS, target)
    return ProjectQuestionRevision(
        revision=_required_int(raw, "revision", target),
        wording_sha256=_required_text(raw, "wording_sha256", target),
        question=_required_text(raw, "question", target),
        vertical_version=_required_text(raw, "vertical_version", target),
        lock_checksum=_required_text(raw, "lock_checksum", target),
        answer_contract=_contract_from_mapping(_required_mapping(raw, "answer_contract", target)),
        changed_at=str(raw.get("changed_at") or ""),
        changed_by=str(raw.get("changed_by") or ""),
    )


def _parse_answer(value: object, *, target: str) -> ProjectQuestionAnswerRevision:
    raw = _mapping(value, target)
    _reject_unknown_fields(raw, _ANSWER_KEYS, target)
    values = _required_mapping(raw, "values", target)
    return ProjectQuestionAnswerRevision(
        revision=_required_int(raw, "revision", target),
        values=dict(values),
        evidence_refs=tuple(str(item) for item in _sequence(raw.get("evidence_refs"), target)),
        provided_by=_required_text(raw, "provided_by", target),
        recorded_by=_required_text(raw, "recorded_by", target),
        answered_at=_required_timestamp(raw, "answered_at", target),
    )


def _parse_application(value: object, *, target: str) -> ProjectQuestionApplication:
    raw = _mapping(value, target)
    _reject_unknown_fields(raw, _APPLICATION_KEYS, target)
    hashes = _required_mapping(raw, "final_physical_hashes", target)
    return ProjectQuestionApplication(
        operation_id=_required_text(raw, "operation_id", target),
        preview_token=_required_text(raw, "preview_token", target),
        actor=_required_text(raw, "actor", target),
        definition_semantic_sha256=_required_text(raw, "definition_semantic_sha256", target),
        question_semantic_sha256=_required_text(raw, "question_semantic_sha256", target),
        applied_at=_required_timestamp(raw, "applied_at", target),
        question_ids=tuple(str(item) for item in _sequence(raw.get("question_ids"), target)),
        question_revisions={
            str(key): _coerce_int(item, f"{target}.question_revisions.{key}")
            for key, item in _optional_mapping(raw.get("question_revisions"), target).items()
        },
        request_identity_sha256=str(raw.get("request_identity_sha256") or ""),
        changed_paths=tuple(str(item) for item in _sequence(raw.get("changed_paths"), target)),
        final_physical_hashes={str(key): str(item) for key, item in hashes.items()},
    )


def _optional_mapping(value: object, target: str) -> Mapping[str, object]:
    if value is None:
        return {}
    return _mapping(value, target)


def _parse_transition(value: object, *, target: str) -> ProjectQuestionTransition:
    raw = _mapping(value, target)
    _reject_unknown_fields(raw, _TRANSITION_KEYS, target)
    return ProjectQuestionTransition(
        operation=_required_text(raw, "operation", target),
        from_state=_required_text(raw, "from", target),
        to_state=_required_text(raw, "to", target),
        actor=_required_text(raw, "actor", target),
        role=_required_text(raw, "role", target),
        reason=_required_text(raw, "reason", target),
        at=_required_timestamp(raw, "at", target),
        provenance=dict(_required_mapping(raw, "provenance", target)),
    )


def _reject_unknown_fields(
    value: Mapping[str, object],
    allowed: frozenset[str],
    target: str,
) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"Invalid {target}: unknown fields {sorted(unknown)}")

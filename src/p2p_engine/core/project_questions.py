from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Sequence

from p2p_engine.core.mutation_preview import MutationResult, canonical_json_bytes, semantic_sha256


PROJECT_QUESTION_ARTIFACT_SCHEMA_VERSION = 1
PROJECT_QUESTION_IDENTITY_POLICY_VERSION = 1
PROJECT_QUESTION_FALLBACK_POLICY_VERSION = 1
PROJECT_QUESTION_LIFECYCLE_POLICY_VERSION = 1
PROJECT_QUESTION_ANSWER_POLICY_VERSION = 1


class ProjectQuestionState(StrEnum):
    TO_ANSWER = "to_answer"
    ANSWERED = "answered"
    APPLIED = "applied"
    DEFERRED = "deferred"
    MUTED = "muted"
    RETIRED = "retired"
    SUPERSEDED = "superseded"


class ProjectQuestionApplicability(StrEnum):
    ACTIVE = "active"
    VERTICAL_MISMATCH = "vertical_mismatch"
    TARGET_REMOVED = "target_removed"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class ProjectQuestionSourceType(StrEnum):
    VERTICAL_DECLARED = "vertical_declared"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class ProjectQuestionAnswerKind(StrEnum):
    FIELD_VALUE = "field_value"
    SECTION_DISPOSITION = "section_disposition"
    ASSUMPTION_RESOLUTION = "assumption_resolution"
    BLOCKER_RESOLUTION = "blocker_resolution"
    OWNER_DECISION_REFERENCE = "owner_decision_reference"
    INFORMATIONAL = "informational"


@dataclass(frozen=True)
class ProjectQuestionTarget:
    kind: str
    target_id: str

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "id": self.target_id}


@dataclass(frozen=True)
class ProjectQuestionAnswerContract:
    kind: ProjectQuestionAnswerKind
    required_fields: tuple[str, ...]
    allowed_definition_operations: tuple[str, ...]
    allowed_values: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind.value,
            "required_fields": list(self.required_fields),
            "allowed_definition_operations": list(self.allowed_definition_operations),
        }
        if self.allowed_values:
            payload["allowed_values"] = list(self.allowed_values)
        return payload


@dataclass(frozen=True)
class ProjectQuestionRevision:
    revision: int
    wording_sha256: str
    question: str
    vertical_version: str
    lock_checksum: str
    answer_contract: ProjectQuestionAnswerContract
    changed_at: str = ""
    changed_by: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "revision": self.revision,
            "wording_sha256": self.wording_sha256,
            "question": self.question,
            "vertical_version": self.vertical_version,
            "lock_checksum": self.lock_checksum,
            "answer_contract": self.answer_contract.to_dict(),
            "changed_at": self.changed_at,
            "changed_by": self.changed_by,
        }


@dataclass(frozen=True)
class ProjectQuestionAnswerRevision:
    revision: int
    values: Mapping[str, object]
    evidence_refs: tuple[str, ...]
    provided_by: str
    recorded_by: str
    answered_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "revision": self.revision,
            "values": dict(self.values),
            "evidence_refs": list(self.evidence_refs),
            "provided_by": self.provided_by,
            "recorded_by": self.recorded_by,
            "answered_at": self.answered_at,
        }


@dataclass(frozen=True)
class ProjectQuestionTransition:
    operation: str
    from_state: str
    to_state: str
    actor: str
    role: str
    reason: str
    at: str
    provenance: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "from": self.from_state,
            "to": self.to_state,
            "actor": self.actor,
            "role": self.role,
            "reason": self.reason,
            "at": self.at,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class ProjectQuestionApplication:
    operation_id: str
    preview_token: str
    actor: str
    definition_semantic_sha256: str
    question_semantic_sha256: str
    applied_at: str
    question_ids: tuple[str, ...] = ()
    question_revisions: Mapping[str, int] = field(default_factory=dict)
    request_identity_sha256: str = ""
    changed_paths: tuple[str, ...] = ()
    final_physical_hashes: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "preview_token": self.preview_token,
            "actor": self.actor,
            "definition_semantic_sha256": self.definition_semantic_sha256,
            "question_semantic_sha256": self.question_semantic_sha256,
            "applied_at": self.applied_at,
            "question_ids": list(self.question_ids),
            "question_revisions": dict(self.question_revisions),
            "request_identity_sha256": self.request_identity_sha256,
            "changed_paths": list(self.changed_paths),
            "final_physical_hashes": dict(self.final_physical_hashes),
        }


@dataclass(frozen=True)
class ProjectQuestion:
    question_id: str
    identity_sha256: str
    revision: int
    wording_sha256: str
    question: str
    state: ProjectQuestionState
    applicability: ProjectQuestionApplicability
    section_id: str
    gap_id: str
    target: ProjectQuestionTarget
    priority: str
    rationale: str
    source_kind: ProjectQuestionSourceType
    source_question_id: str
    source_key: str
    vertical_id: str
    vertical_version: str
    lock_checksum: str
    fallback_policy_version: int
    answer_contract: ProjectQuestionAnswerContract
    deferred_trigger: Mapping[str, object] = field(default_factory=dict)
    revisions: tuple[ProjectQuestionRevision, ...] = ()
    answers: tuple[ProjectQuestionAnswerRevision, ...] = ()
    applications: tuple[ProjectQuestionApplication, ...] = ()
    transitions: tuple[ProjectQuestionTransition, ...] = ()
    superseded_by: str = ""
    created_at: str = ""
    created_by: str = ""
    updated_at: str = ""
    updated_by: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.question_id,
            "identity_sha256": self.identity_sha256,
            "revision": self.revision,
            "wording_sha256": self.wording_sha256,
            "question": self.question,
            "state": self.state.value,
            "applicability": self.applicability.value,
            "section_id": self.section_id,
            "gap_id": self.gap_id,
            "target": self.target.to_dict(),
            "priority": self.priority,
            "rationale": self.rationale,
            "source": {
                "kind": self.source_kind.value,
                "question_id": self.source_question_id,
                "key": self.source_key,
                "vertical_id": self.vertical_id,
                "vertical_version": self.vertical_version,
                "lock_checksum": self.lock_checksum,
                "fallback_policy_version": self.fallback_policy_version,
            },
            "answer_contract": self.answer_contract.to_dict(),
            "deferred_trigger": dict(self.deferred_trigger),
            "revisions": [item.to_dict() for item in self.revisions],
            "answers": [item.to_dict() for item in self.answers],
            "applications": [item.to_dict() for item in self.applications],
            "transitions": [item.to_dict() for item in self.transitions],
            "superseded_by": self.superseded_by,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }


@dataclass(frozen=True)
class ProjectQuestionGroup:
    group_id: str
    identity_sha256: str
    gap_id: str
    section_id: str
    question_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.group_id,
            "identity_sha256": self.identity_sha256,
            "gap_id": self.gap_id,
            "section_id": self.section_id,
            "question_ids": list(self.question_ids),
        }


@dataclass(frozen=True)
class ProjectQuestionArtifact:
    project_id: str
    vertical_id: str
    vertical_version: str
    lock_checksum: str
    groups: tuple[ProjectQuestionGroup, ...]
    questions: tuple[ProjectQuestion, ...]
    created_at: str
    created_by: str
    updated_at: str
    updated_by: str
    schema_version: int = PROJECT_QUESTION_ARTIFACT_SCHEMA_VERSION
    policy_versions: Mapping[str, int] = field(
        default_factory=lambda: {
            "identity": PROJECT_QUESTION_IDENTITY_POLICY_VERSION,
            "fallback": PROJECT_QUESTION_FALLBACK_POLICY_VERSION,
            "lifecycle": PROJECT_QUESTION_LIFECYCLE_POLICY_VERSION,
            "answer_binding": PROJECT_QUESTION_ANSWER_POLICY_VERSION,
        }
    )

    def to_payload(self) -> dict[str, object]:
        return {
            "project_questions": {
                "schema_version": self.schema_version,
                "project_id": self.project_id,
                "vertical": {
                    "id": self.vertical_id,
                    "version": self.vertical_version,
                    "lock_checksum": self.lock_checksum,
                },
                "policy_versions": dict(self.policy_versions),
                "groups": [item.to_dict() for item in self.groups],
                "questions": [item.to_dict() for item in self.questions],
                "audit": {
                    "created_at": self.created_at,
                    "created_by": self.created_by,
                    "updated_at": self.updated_at,
                    "updated_by": self.updated_by,
                },
            }
        }

    def semantic_payload(self) -> dict[str, object]:
        payload = self.to_payload()["project_questions"]
        assert isinstance(payload, dict)
        semantic = dict(payload)
        semantic.pop("audit", None)
        semantic["questions"] = [_question_semantic_payload(item) for item in self.questions]
        return {"project_questions": semantic}

    @property
    def semantic_sha256(self) -> str:
        return semantic_sha256(self.semantic_payload())


@dataclass(frozen=True)
class ProjectQuestionOperationResult:
    operation_id: str
    status: str
    question: ProjectQuestion | None
    mutation: MutationResult

    @property
    def mutation_performed(self) -> bool:
        return self.mutation.status == "applied"

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "status": self.status,
            "mutation_performed": self.mutation_performed,
            "question": self.question.to_dict() if self.question is not None else None,
            "mutation": self.mutation.to_dict(),
        }


def project_question_identity(
    *,
    vertical_id: str,
    section_id: str,
    gap_kind: str,
    target_kind: str,
    target_id: str,
    source_key: str,
    policy_major: int = PROJECT_QUESTION_IDENTITY_POLICY_VERSION,
) -> tuple[str, str]:
    payload = {
        "vertical_id": vertical_id,
        "section_id": section_id,
        "gap_kind": gap_kind,
        "target_kind": target_kind,
        "target_id": target_id,
        "source_key": source_key,
        "policy_major": policy_major,
    }
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return f"PRQ-{digest[:16]}", digest


def project_question_group_identity(
    *,
    vertical_id: str,
    section_id: str,
    gap_id: str,
    policy_major: int = PROJECT_QUESTION_IDENTITY_POLICY_VERSION,
) -> tuple[str, str]:
    payload = {
        "vertical_id": vertical_id,
        "section_id": section_id,
        "gap_id": gap_id,
        "policy_major": policy_major,
    }
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return f"PRG-{digest[:16]}", digest


def project_question_wording_sha256(question: str) -> str:
    return semantic_sha256({"question": question.strip()})


def _question_semantic_payload(question: ProjectQuestion) -> dict[str, object]:
    payload = question.to_dict()
    for key in ("created_at", "updated_at"):
        payload.pop(key, None)
    for answer in payload.get("answers", []):
        if isinstance(answer, dict):
            answer.pop("answered_at", None)
    for transition in payload.get("transitions", []):
        if isinstance(transition, dict):
            transition.pop("at", None)
            provenance = transition.get("provenance")
            if isinstance(provenance, dict):
                provenance.pop("preview_token", None)
    for application in payload.get("applications", []):
        if isinstance(application, dict):
            application.pop("applied_at", None)
            application.pop("preview_token", None)
            application.pop("question_semantic_sha256", None)
            application.pop("changed_paths", None)
            application.pop("final_physical_hashes", None)
    for revision in payload.get("revisions", []):
        if isinstance(revision, dict):
            revision.pop("changed_at", None)
    return payload

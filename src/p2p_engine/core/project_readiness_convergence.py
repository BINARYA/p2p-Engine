from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from p2p_engine.core.mutation_preview import MutationPreview, MutationResult


PROJECT_READINESS_CONVERGENCE_POLICY_VERSION = 1
PROJECT_READINESS_CONVERGENCE_OPERATION = "project-readiness-convergence"


@dataclass(frozen=True)
class ProjectReadinessConvergencePreview:
    preview: MutationPreview
    question_ids: tuple[str, ...]
    question_revisions: Mapping[str, int]
    definition_before_sha256: str
    definition_candidate_sha256: str
    question_candidate_sha256: str
    affected_gap_ids: tuple[str, ...]
    progress_effect: Mapping[str, object]
    rebuild_plan: tuple[str, ...]

    @property
    def mutation_performed(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.preview.operation_id,
            "status": "preview",
            "mutation_performed": False,
            "question_ids": list(self.question_ids),
            "question_revisions": dict(self.question_revisions),
            "definition_before_sha256": self.definition_before_sha256,
            "definition_candidate_sha256": self.definition_candidate_sha256,
            "question_candidate_sha256": self.question_candidate_sha256,
            "affected_gap_ids": list(self.affected_gap_ids),
            "progress_effect": dict(self.progress_effect),
            "rebuild_plan": list(self.rebuild_plan),
            "preview": self.preview.to_dict(),
        }


@dataclass(frozen=True)
class ProjectReadinessConvergenceResult:
    status: str
    operation_id: str
    actor: str
    question_ids: tuple[str, ...]
    preview_token: str
    mutation: MutationResult
    rebuild_plan: tuple[str, ...] = ()
    residual_gap_ids: tuple[str, ...] = ()
    already_applied: bool = False
    diagnostic_code: str = ""
    message: str = ""
    stored_physical_hashes: Mapping[str, str] = field(default_factory=dict)

    @property
    def mutation_performed(self) -> bool:
        return self.mutation.status == "applied"

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "status": self.status,
            "actor": self.actor,
            "question_ids": list(self.question_ids),
            "preview_token": self.preview_token,
            "mutation_performed": self.mutation_performed,
            "already_applied": self.already_applied,
            "diagnostic_code": self.diagnostic_code,
            "message": self.message,
            "rebuild_plan": list(self.rebuild_plan),
            "residual_gap_ids": list(self.residual_gap_ids),
            "stored_physical_hashes": dict(self.stored_physical_hashes),
            "mutation": self.mutation.to_dict(),
        }


@dataclass(frozen=True)
class ProjectQuestionReconciliationPreview:
    preview: MutationPreview
    preserved_ids: tuple[str, ...]
    revised_ids: tuple[str, ...]
    created_ids: tuple[str, ...]
    retired_ids: tuple[str, ...]
    superseded_ids: tuple[str, ...]
    inactive_evidence_ids: tuple[str, ...]
    owner_apply_required: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.preview.operation_id,
            "status": "preview",
            "mutation_performed": False,
            "preserved_ids": list(self.preserved_ids),
            "revised_ids": list(self.revised_ids),
            "created_ids": list(self.created_ids),
            "retired_ids": list(self.retired_ids),
            "superseded_ids": list(self.superseded_ids),
            "inactive_evidence_ids": list(self.inactive_evidence_ids),
            "owner_apply_required": self.owner_apply_required,
            "preview": self.preview.to_dict(),
        }

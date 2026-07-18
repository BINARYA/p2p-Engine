from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from p2p_engine.core.workspace_schema import (
    LAYOUT_CURRENT,
    LAYOUT_LEGACY,
    LAYOUT_UPGRADEABLE,
    WorkspaceSchemaStatus,
)


@dataclass(frozen=True)
class WorkspaceOperationRequirement:
    operation_id: str
    minimum_schema_version: int
    maximum_schema_version: int | None = None
    reason: str = ""


@dataclass(frozen=True)
class WorkspaceOperationCompatibilityResult:
    operation_id: str
    allowed: bool
    current_version: int | None
    required_minimum: int
    required_maximum: int | None
    reason: str
    suggested_command: str
    recoverable: bool

    def require_allowed(self) -> None:
        if self.allowed:
            return
        maximum = f", maximum {self.required_maximum}" if self.required_maximum is not None else ""
        raise ValueError(
            f"P2P348_WORKSPACE_OPERATION_SCHEMA_REQUIRED: operation `{self.operation_id}` "
            f"requires workspace schema minimum {self.required_minimum}{maximum}; "
            f"current is {self.current_version}. {self.reason} {self.suggested_command}".strip()
        )


class WorkspaceOperationCompatibilityService:
    def __init__(self, requirements: Iterable[WorkspaceOperationRequirement] | None = None) -> None:
        values = tuple(requirements or default_workspace_operation_requirements())
        self._requirements = {item.operation_id: item for item in values}
        if len(self._requirements) != len(values):
            raise ValueError("Duplicate workspace operation schema requirement")

    @property
    def operation_ids(self) -> frozenset[str]:
        return frozenset(self._requirements)

    def check(
        self,
        operation_id: str,
        status: WorkspaceSchemaStatus,
    ) -> WorkspaceOperationCompatibilityResult:
        requirement = self._requirements.get(operation_id)
        if requirement is None:
            return WorkspaceOperationCompatibilityResult(
                operation_id=operation_id,
                allowed=False,
                current_version=status.current_version,
                required_minimum=1,
                required_maximum=None,
                reason="Unknown governed-write operation ids fail closed until classified.",
                suggested_command="Classify the operation in WorkspaceOperationCompatibilityService.",
                recoverable=False,
            )
        current = status.current_version
        writable_layout = status.layout_status in {LAYOUT_CURRENT, LAYOUT_UPGRADEABLE} or (
            status.layout_status == LAYOUT_LEGACY and requirement.minimum_schema_version == 0
        )
        allowed = writable_layout and current is not None and current >= requirement.minimum_schema_version
        if allowed and requirement.maximum_schema_version is not None and current is not None:
            allowed = current <= requirement.maximum_schema_version
        if allowed:
            reason = requirement.reason or "Operation is compatible with the current workspace schema."
            command = ""
            recoverable = True
        elif not writable_layout:
            reason = (
                f"Workspace layout `{status.layout_status}` is not writable by this runtime; "
                "only current or explicitly upgradeable layouts permit governed writes."
            )
            command = "p2p workspace schema status --format json"
            recoverable = False
        elif current is not None and current < requirement.minimum_schema_version:
            reason = requirement.reason or "Workspace migration is required before this operation."
            command = (
                f"p2p workspace migrate plan --to {requirement.minimum_schema_version} --format json"
            )
            recoverable = True
        else:
            reason = requirement.reason or "Operation is not supported by this workspace schema."
            command = "p2p workspace schema status --format json"
            recoverable = False
        return WorkspaceOperationCompatibilityResult(
            operation_id=operation_id,
            allowed=allowed,
            current_version=current,
            required_minimum=requirement.minimum_schema_version,
            required_maximum=requirement.maximum_schema_version,
            reason=reason,
            suggested_command=command,
            recoverable=recoverable,
        )


_V1_SAFE_OPERATIONS = frozenset(
    {
        "agent_install",
        "agent_instructions_refresh",
        "agent_uninstall",
        "change_create",
        "change_set_status_update",
        "choice_block",
        "choice_create",
        "choice_decide",
        "choice_unblock",
        "conflict_record",
        "conflict_update",
        "consent_consume",
        "consent_grant",
        "consent_mark_used_with_error",
        "consent_request",
        "consent_revoke",
        "definition_maturity_refresh",
        "governance_init",
        "governance_precedent_record",
        "governance_vote_record",
        "intake_apply_plan_create",
        "intake_apply_run",
        "intake_import",
        "intake_prompt_create",
        "next_action_add",
        "next_action_complete",
        "next_action_retire",
        "next_actions_refresh",
        "permissions_actor_add",
        "project_assessment_refresh",
        "project_brief_import",
        "project_brief_prompt",
        "project_definition_apply",
        "project_definition_export",
        "project_definition_update",
        "project_init_existing",
        "project_interaction_style_set",
        "project_metadata_apply",
        "project_publication_import",
        "project_publication_prepare",
        "project_publication_render",
        "project_publication_review",
        "project_publication_validate",
        "project_rubrics_init",
        "project_state_refresh",
        "project_vertical_add",
        "project_vertical_lock_repair",
        "project_vertical_select",
        "proposal_accept_branch",
        "proposal_artifact_import",
        "proposal_artifact_import_content",
        "proposal_artifacts_confirm",
        "proposal_artifacts_init",
        "proposal_artifacts_mark_legacy",
        "proposal_artifacts_set",
        "proposal_branch",
        "proposal_cleanup",
        "proposal_contribution_add",
        "proposal_create",
        "proposal_decide_branch",
        "proposal_draft_commit",
        "proposal_exploration_import",
        "proposal_finalize",
        "proposal_impact_apply",
        "proposal_impact_import",
        "proposal_merge",
        "proposal_merge_abort",
        "proposal_merge_continue",
        "proposal_prompt_generate",
        "proposal_publish",
        "proposal_questions_add",
        "proposal_questions_answer",
        "proposal_questions_apply",
        "proposal_questions_group_state",
        "proposal_questions_import",
        "proposal_questions_init",
        "proposal_questions_reassess",
        "proposal_questions_set_state",
        "proposal_questions_supersede",
        "proposal_readiness_assess",
        "proposal_readiness_init",
        "proposal_readiness_override",
        "proposal_readiness_refresh",
        "proposal_readiness_write",
        "proposal_reject_branch",
        "proposal_request_review",
        "proposal_retire_branch",
        "proposal_update",
        "proposal_vertical_coverage_apply",
        "registry_refresh",
        "remote_profile_configure",
        "repository_mode_set",
        "software_spec_export",
        "software_spec_import",
        "software_spec_prompt",
        "software_spec_refresh",
        "sync_fetch",
        "sync_pull",
        "sync_push",
        "work_accept",
        "work_accept_abort",
        "work_accept_continue",
        "work_branch",
        "work_cleanup",
        "work_finalize",
        "work_plan_create",
        "work_publish",
        "work_request_review",
        "work_retire",
        "work_review",
        "work_submit",
    }
)

_V2_ONLY_OPERATIONS = frozenset(
    {
        "project_questions_initialize",
        "project_questions_answer",
        "project_questions_defer",
        "project_questions_mute",
        "project_questions_reopen",
        "project_questions_trigger_reopen",
        "project_questions_reconcile_apply",
        "project_readiness_convergence_apply",
    }
)

_V3_ONLY_OPERATIONS = frozenset(
    {
        "proposal_decision_apply",
        "proposal_decision_ledger_repair",
        "proposal_decision_legacy_resolution",
        "proposal_decision_projection_repair",
        "proposal_decision_record",
    }
)


def default_workspace_operation_requirements() -> tuple[WorkspaceOperationRequirement, ...]:
    schema_independent_operations = {
        "agent_instructions_refresh",
        "project_init_existing",
        "repository_mode_set",
    }
    values = [
        WorkspaceOperationRequirement(
            operation_id=item,
            minimum_schema_version=0 if item in schema_independent_operations else 1,
            reason=(
                "This operation is schema-independent and remains available for legacy repair."
                if item in schema_independent_operations
                else ""
            ),
        )
        for item in sorted(_V1_SAFE_OPERATIONS)
    ]
    values.extend(
        WorkspaceOperationRequirement(
            operation_id=item,
            minimum_schema_version=2,
            reason="Project-question and convergence writes require workspace schema v2.",
        )
        for item in sorted(_V2_ONLY_OPERATIONS)
    )
    values.extend(
        WorkspaceOperationRequirement(
            operation_id=item,
            minimum_schema_version=3,
            reason=(
                "Proposal decision event writes require workspace schema v3. "
                "Preview remains read-only; migrate before apply."
            ),
        )
        for item in sorted(_V3_ONLY_OPERATIONS)
    )
    values.append(
        WorkspaceOperationRequirement(
            operation_id="project_definition_legacy_questions",
            minimum_schema_version=1,
            maximum_schema_version=1,
            reason="Definition-embedded project questions are writable only in schema v1.",
        )
    )
    return tuple(values)

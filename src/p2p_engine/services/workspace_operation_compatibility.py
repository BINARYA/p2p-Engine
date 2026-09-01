from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from p2p_engine.core.workspace_schema import (
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    LAYOUT_CURRENT,
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
    diagnostic_code: str = "P2P348_WORKSPACE_OPERATION_SCHEMA_REQUIRED"

    def require_allowed(self) -> None:
        if self.allowed:
            return
        if self.diagnostic_code == "P2P_WORKSPACE_UNSUPPORTED_SCHEMA":
            raise ValueError(
                f"{self.diagnostic_code}: workspace schema {self.current_version!r} is unsupported; "
                f"this runtime supports schema {CURRENT_WORKSPACE_SCHEMA_VERSION} only and provides "
                "no in-runtime conversion. Recreate or convert the workspace outside this runtime."
            )
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
                required_minimum=CURRENT_WORKSPACE_SCHEMA_VERSION,
                required_maximum=None,
                reason="Unknown governed-write operation ids fail closed until classified.",
                suggested_command="Classify the operation in WorkspaceOperationCompatibilityService.",
                recoverable=False,
            )
        current = status.current_version
        writable_layout = (
            status.layout_status == LAYOUT_CURRENT
            and current == CURRENT_WORKSPACE_SCHEMA_VERSION
        )
        allowed = writable_layout
        if allowed:
            reason = requirement.reason or "Operation is compatible with the current workspace schema."
            command = ""
            recoverable = True
        else:
            reason = (
                f"Workspace layout `{status.layout_status}` is not writable by this runtime; "
                f"workspace schema {CURRENT_WORKSPACE_SCHEMA_VERSION} is required."
            )
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
            diagnostic_code=(
                "P2P348_WORKSPACE_OPERATION_SCHEMA_REQUIRED"
                if allowed
                else "P2P_WORKSPACE_UNSUPPORTED_SCHEMA"
            ),
        )


_CURRENT_SCHEMA_OPERATIONS = frozenset(
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
        "project_authority_rotate_apply",
        "project_authority_rotate_preview",
        "project_brief_import",
        "project_brief_prompt",
        "project_definition_apply",
        "project_definition_export",
        "project_definition_update",
        "project_domain_change",
        "project_init_existing",
        "project_interaction_style_set",
        "project_identity_adopt",
        "project_identity_adopt_preview",
        "project_identity_derive",
        "project_identity_derive_preview",
        "project_integration_install",
        "project_integration_profile",
        "project_integration_refresh",
        "project_integration_remove",
        "project_memory_scope_change",
        "project_memory_restore",
        "project_metadata_apply",
        "project_publication_import",
        "project_publication_prepare",
        "project_publication_render",
        "project_publication_review",
        "project_publication_validate",
        "project_rubrics_init",
        "project_state_refresh",
        "project_structure_change",
        "project_structure_export",
        "project_structure_replacement",
        "project_structure_retirement",
        "project_vertical_adopt",
        "project_vertical_install",
        "project_vertical_lock_repair",
        "project_vertical_migrate",
        "project_vertical_select",
        "proposal_artifact_import",
        "proposal_artifact_import_content",
        "proposal_artifacts_confirm",
        "proposal_artifacts_init",
        "proposal_artifacts_set",
        "proposal_contribution_add",
        "proposal_create",
        "proposal_exploration_import",
        "proposal_impact_apply",
        "proposal_impact_import",
        "proposal_prompt_generate",
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
        "proposal_update",
        "proposal_vertical_coverage_apply",
        "registry_refresh",
        "runtime_contract_update",
        "software_spec_export",
        "software_spec_import",
        "software_spec_prompt",
        "software_spec_refresh",
        "work_plan_create",
        "work_retire",
    }
)

_CURRENT_PROJECT_QUESTION_OPERATIONS = frozenset(
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

_CURRENT_DECISION_LEDGER_OPERATIONS = frozenset(
    {
        "proposal_decision_apply",
        "proposal_decision_ledger_repair",
        "proposal_decision_projection_repair",
        "proposal_decision_record",
    }
)


def default_workspace_operation_requirements() -> tuple[WorkspaceOperationRequirement, ...]:
    operation_ids = (
        _CURRENT_SCHEMA_OPERATIONS
        | _CURRENT_PROJECT_QUESTION_OPERATIONS
        | _CURRENT_DECISION_LEDGER_OPERATIONS
    )
    return tuple(
        WorkspaceOperationRequirement(
            operation_id=item,
            minimum_schema_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
            maximum_schema_version=CURRENT_WORKSPACE_SCHEMA_VERSION,
            reason="All governed writes require the current workspace schema.",
        )
        for item in sorted(operation_ids)
    )

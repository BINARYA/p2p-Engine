from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from p2p_engine.core.contribution import Contribution, ContributionType
from p2p_engine.core.decision import Decision, DecisionOutcome
from p2p_engine.core.proposal import Proposal
from p2p_engine.core.project_verticals import (
    ActiveProjectVertical,
    CustomVerticalCandidate,
    ProjectDefinitionPatchResult,
    ProjectDefinitionView,
    ProjectReadinessReview,
    ProjectVerticalAddResult,
    ProjectVerticalContext,
    VerticalListItem,
    VerticalLock,
    VerticalLockStatus,
    VerticalPack,
    VerticalSection,
    VerticalValidationResult,
)
from p2p_engine.core.runtime_contract import (
    RuntimeContractAdoptionResult,
    RuntimeContractUpdatePreview,
    RuntimeContractUpdateResult,
    RuntimeStatus,
    RuntimeWritePreflight,
)
from p2p_engine.core.interaction_style import InteractionStyleView
from p2p_engine.foundation.files import (
    identity_slug as _identity_slug,
    read_yaml_mapping as _read_yaml_mapping,
    relative_to_root as _relative_to_root,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.validators import validate_yaml_key as _validate_yaml_key
from p2p_engine.services.agent_instructions import (
    AgentInstructionService,
    AgentInstructionsResult,
    AgentDoctorResult,
    AgentIntegrationResult,
)
from p2p_engine.services.agent_templates import (
    BUILT_IN_AGENT_ADAPTERS,
    agent_adapter_capabilities as _agent_adapter_capabilities,
    agent_adapter_files as _agent_adapter_files,
    agent_instruction_files as _agent_instruction_files,
    agent_policy as _agent_policy,
    expanded_agent_profiles as _expanded_agent_profiles,
    normalize_agent_profile as _normalize_agent_profile,
)
from p2p_engine.services.changes import (
    ChangeSetDetail,
    ChangeSetLifecycleService,
    ChangeSetPolicy,
    ChangeSetStatus,
    ChangeSetTaskView,
)
from p2p_engine.services.choices import ChoiceDetail, ChoiceDiscoveryFinding, ChoiceLifecycleService, ChoiceStatus
from p2p_engine.services.consent import ConsentReceipt, ConsentService
from p2p_engine.services.conflicts import ConflictMemoryService, ConflictStatus
from p2p_engine.services.governance import GovernanceService, GovernanceStatus, VoteStatus
from p2p_engine.services.governance_policy import (
    GovernancePolicyService,
    GovernancePreflightResult,
    GovernanceValidationResult,
    PrecedentMatch,
)
from p2p_engine.services.intake import IntakeAppliedAction, IntakeApplyPlan, IntakeLifecycleService, IntakePrompt, IntakeStatus
from p2p_engine.services.next_actions import NextAction, NextActionService
from p2p_engine.services.permissions import PermissionActor, PermissionsService
from p2p_engine.services.context_packets import ContextPacket, ContextPacketService
from p2p_engine.services.proposal_artifacts import (
    ArtifactImportKind,
    ArtifactImportResult,
    ExplorationArtifactStatus,
    ExplorationStatus,
    ImportKind,
    PromptKind,
    ProposalArtifactService,
)
from p2p_engine.services.proposal_artifact_state import ProposalArtifactStateService
from p2p_engine.services.proposal_decisions import ProposalDecisionService
from p2p_engine.services.proposal_drafts import ProposalDraftCommit, ProposalDraftCommitService
from p2p_engine.services.proposal_questions import ProposalQuestionService
from p2p_engine.services.proposal_review_view import (
    ProposalArtifactCatalogItem,
    ProposalFullView,
    ProposalReviewViewService,
)
from p2p_engine.services.proposals import ProposalContributionList, ProposalDetail, ProposalDocumentService
from p2p_engine.services.project_assessment import ProjectAssessment, ProjectAssessmentService
from p2p_engine.services.project_contexts import ProjectContextRendererService
from p2p_engine.services.project_maturity import (
    ProjectDefinitionMaturity,
    ProjectMaturityService,
    ProjectRubrics,
)
from p2p_engine.services.project_interaction_style import ProjectInteractionStyleService
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.project_initialization import (
    ProjectInitializationResult,
    ProjectInitializationService,
    normalize_repository_mode as _normalize_repository_mode,
)
from p2p_engine.services.project_state import ProjectBriefPrompt, ProjectStateService, ProjectStateStatus
from p2p_engine.services.proposal_branches import (
    ProposalBranchDetail,
    ProposalBranchScan,
    ProposalBranchService,
    ProposalCleanup,
    ProposalFinalize,
    ProposalMerge,
    ProposalMergeConflict,
)
from p2p_engine.services.readiness import ProposalReadiness, ReadinessProfile, ReadinessService
from p2p_engine.services.registries import RegistryService, RegistryStatus, RegistryView
from p2p_engine.services.registry_records import RegistryRecordBuilderService
from p2p_engine.services.remote_profile import RemoteProfileService, RemoteProjectProfile
from p2p_engine.services.runtime_contract import RuntimeContractService
from p2p_engine.services.spec_export import (
    SoftwareSpecExportStatus,
    SoftwareSpecExportValidation,
    SpecExportService,
)
from p2p_engine.services.sync import SyncResult, SyncService, SyncStatus
from p2p_engine.services.validation import ValidationFinding, ValidationResult, ValidationService
from p2p_engine.services.visible_project_export import (
    VisibleProjectExportResult,
    VisibleProjectExportService,
    VisibleProjectExportStatus,
)
from p2p_engine.services.software_spec import SoftwareSpecPrompt, SoftwareSpecService, SoftwareSpecStatus
from p2p_engine.services.software_spec_lifecycle import SoftwareSpecLifecycleService
from p2p_engine.core.software_spec_lifecycle import SpecLifecycleView
from p2p_engine.services.work_branches import (
    WorkAccept,
    WorkAcceptConflict,
    WorkBranch,
    WorkBranchService,
    WorkCleanup,
    WorkFinalize,
    WorkPublish,
    WorkReview,
    WorkReviewRequest,
    WorkScan,
    WorkSubmit,
)
from p2p_engine.services.work_planning import WorkDetail, WorkPlanningService, WorkRetire, WorkStatus, WorkSummary
from p2p_engine.services.workspace_status import (
    ProposalSummary,
    WorkspaceCheck,
    WorkspaceStatus,
    WorkspaceStatusService,
)
from p2p_engine.storage.git import (
    abort_merge,
    branch_exists,
    changed_files,
    checkout_branch,
    commit_all,
    conflicted_files,
    create_and_checkout_branch,
    delete_local_branch,
    delete_local_branch_force,
    delete_remote_branch,
    fetch_remote,
    get_git_status,
    head_commit,
    list_files_at_ref,
    list_local_proposal_branches,
    list_local_work_branches,
    list_remote_proposal_branches,
    merge_branch_no_commit,
    merge_in_progress,
    push_branch,
    read_file_at_ref,
    rename_current_branch,
    remote_url,
    pull_branch,
    stage_all,
    restore_path,
)

DEFAULT_READINESS_PROFILE_ID = "default-readiness-v0.1"
DEFAULT_READINESS_PROFILE_VERSION = "0.1"


class P2PWorkspace:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.p2p_dir = self.root / ".p2p"
        self._agent_instruction_service_instance: AgentInstructionService | None = None
        self._change_set_lifecycle_service_instance: ChangeSetLifecycleService | None = None
        self._choice_lifecycle_service_instance: ChoiceLifecycleService | None = None
        self._permissions_service_instance: PermissionsService | None = None
        self._consent_service_instance: ConsentService | None = None
        self._context_packet_service_instance: ContextPacketService | None = None
        self._conflict_memory_service_instance: ConflictMemoryService | None = None
        self._governance_service_instance: GovernanceService | None = None
        self._governance_policy_service_instance: GovernancePolicyService | None = None
        self._intake_lifecycle_service_instance: IntakeLifecycleService | None = None
        self._proposal_decision_service_instance: ProposalDecisionService | None = None
        self._proposal_draft_commit_service_instance: ProposalDraftCommitService | None = None
        self._proposal_document_service_instance: ProposalDocumentService | None = None
        self._proposal_question_service_instance: ProposalQuestionService | None = None
        self._project_assessment_service_instance: ProjectAssessmentService | None = None
        self._project_context_renderer_service_instance: ProjectContextRendererService | None = None
        self._project_interaction_style_service_instance: ProjectInteractionStyleService | None = None
        self._project_initialization_service_instance: ProjectInitializationService | None = None
        self._project_maturity_service_instance: ProjectMaturityService | None = None
        self._project_vertical_service_instance: ProjectVerticalService | None = None
        self._project_state_service_instance: ProjectStateService | None = None
        self._next_action_service_instance: NextActionService | None = None
        self._proposal_branch_service_instance: ProposalBranchService | None = None
        self._proposal_artifact_service_instance: ProposalArtifactService | None = None
        self._proposal_artifact_state_service_instance: ProposalArtifactStateService | None = None
        self._proposal_review_view_service_instance: ProposalReviewViewService | None = None
        self._readiness_service_instance: ReadinessService | None = None
        self._registry_service_instance: RegistryService | None = None
        self._registry_record_builder_service_instance: RegistryRecordBuilderService | None = None
        self._remote_profile_service_instance: RemoteProfileService | None = None
        self._runtime_contract_service_instance: RuntimeContractService | None = None
        self._spec_export_service_instance: SpecExportService | None = None
        self._software_spec_lifecycle_service_instance: SoftwareSpecLifecycleService | None = None
        self._software_spec_service_instance: SoftwareSpecService | None = None
        self._sync_service_instance: SyncService | None = None
        self._validation_service_instance: ValidationService | None = None
        self._visible_project_export_service_instance: VisibleProjectExportService | None = None
        self._work_branch_service_instance: WorkBranchService | None = None
        self._work_planning_service_instance: WorkPlanningService | None = None
        self._workspace_status_service_instance: WorkspaceStatusService | None = None

    def _permissions_service(self) -> PermissionsService:
        if self._permissions_service_instance is None:
            self._permissions_service_instance = PermissionsService(root=self.root, p2p_dir=self.p2p_dir)
        return self._permissions_service_instance

    def _agent_instruction_service(self) -> AgentInstructionService:
        if self._agent_instruction_service_instance is None:
            self._agent_instruction_service_instance = AgentInstructionService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                project_name=self._project_name,
                repository_mode=self._repository_mode,
                set_repository_mode=self._set_repository_mode,
                normalize_profile=_normalize_agent_profile,
                normalize_repository_mode=_normalize_repository_mode,
                expanded_profiles=_expanded_agent_profiles,
                instruction_files=_agent_instruction_files,
                adapter_files=_agent_adapter_files,
                adapter_capabilities=_agent_adapter_capabilities,
                agent_policy=_agent_policy,
                built_in_adapters=BUILT_IN_AGENT_ADAPTERS,
                interaction_style=self.project_interaction_style,
            )
        return self._agent_instruction_service_instance

    def _consent_service(self) -> ConsentService:
        if self._consent_service_instance is None:
            self._consent_service_instance = ConsentService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                permissions=self._permissions_service(),
            )
        return self._consent_service_instance

    def _validation_service(self) -> ValidationService:
        if self._validation_service_instance is None:
            self._validation_service_instance = ValidationService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                duplicate_proposal_ids=self._proposal_document_service().duplicate_ids,
                registry_status=self.registry_status,
                agent_integrations_path=self._agent_instruction_service().path,
                permissions_path=self._permissions_service().path,
                vertical_validation_findings=self._project_vertical_service().validation_findings,
                interaction_style_validation_findings=self._project_interaction_style_service().validation_findings,
                governance_validation_findings=self._governance_policy_service().validation_findings,
                runtime_validation_findings=self._runtime_contract_service().validation_findings,
            )
        return self._validation_service_instance

    def _context_packet_service(self) -> ContextPacketService:
        if self._context_packet_service_instance is None:
            self._context_packet_service_instance = ContextPacketService(
                project_name=self._project_name,
                validate=self.validate,
                registry_status=self.registry_status,
                project_state_status=self.project_state_status,
                proposal_summaries=self.proposal_summaries,
                show_proposal=self.show_proposal,
                choice_statuses=self.choice_statuses,
                show_choice=self.show_choice,
                change_set_statuses=self.change_set_statuses,
                show_change_set=self.show_change_set,
                work_summaries=self.work_summaries,
                show_work=self.show_work,
                next_actions=self.next_actions,
                proposal_artifacts=self.read_proposal_artifacts,
                interaction_style=self.project_interaction_style,
            )
        return self._context_packet_service_instance

    def _proposal_document_service(self) -> ProposalDocumentService:
        if self._proposal_document_service_instance is None:
            self._proposal_document_service_instance = ProposalDocumentService(root=self.root, p2p_dir=self.p2p_dir)
        return self._proposal_document_service_instance

    def _proposal_question_service(self) -> ProposalQuestionService:
        if self._proposal_question_service_instance is None:
            self._proposal_question_service_instance = ProposalQuestionService(
                root=self.root,
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
        return self._proposal_question_service_instance

    def _proposal_artifact_state_service(self) -> ProposalArtifactStateService:
        if self._proposal_artifact_state_service_instance is None:
            self._proposal_artifact_state_service_instance = ProposalArtifactStateService(
                root=self.root,
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
        return self._proposal_artifact_state_service_instance

    def _proposal_review_view_service(self) -> ProposalReviewViewService:
        if self._proposal_review_view_service_instance is None:
            self._proposal_review_view_service_instance = ProposalReviewViewService(
                root=self.root,
                find_proposal_dir=self._proposal_document_service().find_dir,
                show_proposal=self.show_proposal,
                read_proposal_readiness=self.read_proposal_readiness,
                read_proposal_questions=self.read_proposal_questions,
                read_proposal_artifacts=self.read_proposal_artifacts,
                list_contributions=self.list_contributions,
            )
        return self._proposal_review_view_service_instance

    def _proposal_draft_commit_service(self) -> ProposalDraftCommitService:
        if self._proposal_draft_commit_service_instance is None:
            self._proposal_draft_commit_service_instance = ProposalDraftCommitService(
                root=self.root,
                find_proposal_dir=self._proposal_document_service().find_dir,
                git_status=get_git_status,
                changed_files=changed_files,
                commit_all=commit_all,
                identity_slug=_identity_slug,
            )
        return self._proposal_draft_commit_service_instance

    def _proposal_branch_service(self) -> ProposalBranchService:
        if self._proposal_branch_service_instance is None:
            self._proposal_branch_service_instance = ProposalBranchService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_proposal_dir=self._proposal_document_service().find_dir,
                git_status=get_git_status,
                checkout_branch=checkout_branch,
                head_commit=head_commit,
                branch_exists=branch_exists,
                create_and_checkout_branch=create_and_checkout_branch,
                rename_current_branch=rename_current_branch,
                commit_all=commit_all,
                remote_profile=self.remote_profile,
                remote_url=remote_url,
                fetch_remote=fetch_remote,
                push_branch=push_branch,
                merge_branch_no_commit=merge_branch_no_commit,
                conflicted_files=conflicted_files,
                merge_in_progress=merge_in_progress,
                stage_all=stage_all,
                restore_path=restore_path,
                abort_merge=abort_merge,
                delete_local_branch=delete_local_branch,
                delete_local_branch_force=delete_local_branch_force,
                delete_remote_branch=delete_remote_branch,
                list_local_proposal_branches=list_local_proposal_branches,
                list_remote_proposal_branches=list_remote_proposal_branches,
                list_files_at_ref=list_files_at_ref,
                read_file_at_ref=read_file_at_ref,
            )
        return self._proposal_branch_service_instance

    def _proposal_decision_service(self) -> ProposalDecisionService:
        if self._proposal_decision_service_instance is None:
            self._proposal_decision_service_instance = ProposalDecisionService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
        return self._proposal_decision_service_instance

    def _project_state_service(self) -> ProjectStateService:
        if self._project_state_service_instance is None:
            self._project_state_service_instance = ProjectStateService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                accepted_proposals=self._registry_record_builder_service().accepted_proposals,
                project_name=self._project_name,
                next_actions=self.next_actions,
                registry_status=self.registry_status,
                project_brief_context=self._project_context_renderer_service().render_project_brief_context,
                validate_yaml_key=_validate_yaml_key,
            )
        return self._project_state_service_instance

    def _project_context_renderer_service(self) -> ProjectContextRendererService:
        if self._project_context_renderer_service_instance is None:
            self._project_context_renderer_service_instance = ProjectContextRendererService(
                p2p_dir=self.p2p_dir,
                show_registry=self.show_registry,
                intake_statuses=self.intake_statuses,
            )
        return self._project_context_renderer_service_instance

    def _project_assessment_service(self) -> ProjectAssessmentService:
        if self._project_assessment_service_instance is None:
            self._project_assessment_service_instance = ProjectAssessmentService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                validate=self.validate,
                registry_status=self.registry_status,
                proposal_summaries=self.proposal_summaries,
                choice_statuses=self.choice_statuses,
                change_set_statuses=self.change_set_statuses,
                work_summaries=self.work_summaries,
                project_state_status=self.project_state_status,
                next_actions=lambda limit=3: self.next_actions(limit=limit),
                maturity_exists=lambda: (self.p2p_dir / "project" / "maturity-assessment.yml").exists(),
                show_maturity=self.show_definition_maturity,
            )
        return self._project_assessment_service_instance

    def _project_maturity_service(self) -> ProjectMaturityService:
        if self._project_maturity_service_instance is None:
            self._project_maturity_service_instance = ProjectMaturityService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                proposal_summaries=self.proposal_summaries,
                find_proposal_dir=self._proposal_document_service().find_dir,
                change_set_statuses=self.change_set_statuses,
                find_change_dir=self._change_set_lifecycle_service().find_dir,
            )
        return self._project_maturity_service_instance

    def _project_interaction_style_service(self) -> ProjectInteractionStyleService:
        if self._project_interaction_style_service_instance is None:
            self._project_interaction_style_service_instance = ProjectInteractionStyleService(
                root=self.root,
                p2p_dir=self.p2p_dir,
            )
        return self._project_interaction_style_service_instance

    def _project_vertical_service(self) -> ProjectVerticalService:
        if self._project_vertical_service_instance is None:
            self._project_vertical_service_instance = ProjectVerticalService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                proposal_summaries=self.proposal_summaries,
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
        return self._project_vertical_service_instance

    def _next_action_service(self) -> NextActionService:
        if self._next_action_service_instance is None:
            self._next_action_service_instance = NextActionService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                registry_status=self.registry_status,
                change_registry_records=self._registry_record_builder_service().change_records,
                intake_statuses=self.intake_statuses,
                proposal_summaries=self.proposal_summaries,
                read_proposal_readiness=self.read_proposal_readiness,
                choice_registry_records=self._registry_record_builder_service().choice_records,
                choice_statuses=self.choice_statuses,
                show_choice=self.show_choice,
            )
        return self._next_action_service_instance

    def _conflict_memory_service(self) -> ConflictMemoryService:
        if self._conflict_memory_service_instance is None:
            self._conflict_memory_service_instance = ConflictMemoryService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
        return self._conflict_memory_service_instance

    def _governance_service(self) -> GovernanceService:
        if self._governance_service_instance is None:
            self._governance_service_instance = GovernanceService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
        return self._governance_service_instance

    def _governance_policy_service(self) -> GovernancePolicyService:
        if self._governance_policy_service_instance is None:
            self._governance_policy_service_instance = GovernancePolicyService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                permissions=self._permissions_service(),
                show_choice=self.show_choice,
            )
        return self._governance_policy_service_instance

    def _proposal_artifact_service(self) -> ProposalArtifactService:
        if self._proposal_artifact_service_instance is None:
            self._proposal_artifact_service_instance = ProposalArtifactService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
        return self._proposal_artifact_service_instance

    def _choice_lifecycle_service(self) -> ChoiceLifecycleService:
        if self._choice_lifecycle_service_instance is None:
            self._choice_lifecycle_service_instance = ChoiceLifecycleService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_proposal_dir=self._proposal_document_service().find_dir,
                find_change_dir=self._change_set_lifecycle_service().find_dir,
                choice_registry_records=self._registry_record_builder_service().choice_records,
            )
        return self._choice_lifecycle_service_instance

    def _intake_lifecycle_service(self) -> IntakeLifecycleService:
        if self._intake_lifecycle_service_instance is None:
            self._intake_lifecycle_service_instance = IntakeLifecycleService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                registry_status=self.registry_status,
                intake_context=self._project_context_renderer_service().render_intake_context,
                add_contribution=self.add_contribution,
                create_choice=self.create_choice,
            )
        return self._intake_lifecycle_service_instance

    def _change_set_lifecycle_service(self) -> ChangeSetLifecycleService:
        if self._change_set_lifecycle_service_instance is None:
            self._change_set_lifecycle_service_instance = ChangeSetLifecycleService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
        return self._change_set_lifecycle_service_instance

    def _readiness_service(self) -> ReadinessService:
        if self._readiness_service_instance is None:
            self._readiness_service_instance = ReadinessService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
        return self._readiness_service_instance

    def _registry_service(self) -> RegistryService:
        if self._registry_service_instance is None:
            records = self._registry_record_builder_service()
            self._registry_service_instance = RegistryService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                duplicate_proposal_ids=self._proposal_document_service().duplicate_ids,
                duplicate_message=lambda duplicates: _duplicate_proposal_ids_message(duplicates, self.root),
                proposal_records=records.proposal_records,
                change_records=records.change_records,
                decision_records=records.decision_records,
                choice_records=records.choice_records,
                relation_records=records.relation_records,
                artifact_records=records.artifact_records,
                readiness_records=records.readiness_records,
            )
        return self._registry_service_instance

    def _registry_record_builder_service(self) -> RegistryRecordBuilderService:
        if self._registry_record_builder_service_instance is None:
            self._registry_record_builder_service_instance = RegistryRecordBuilderService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                read_proposal_readiness=self.read_proposal_readiness,
            )
        return self._registry_record_builder_service_instance

    def _remote_profile_service(self) -> RemoteProfileService:
        if self._remote_profile_service_instance is None:
            self._remote_profile_service_instance = RemoteProfileService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                remote_url_resolver=remote_url,
            )
        return self._remote_profile_service_instance

    def _runtime_contract_service(self) -> RuntimeContractService:
        if self._runtime_contract_service_instance is None:
            self._runtime_contract_service_instance = RuntimeContractService(root=self.root, p2p_dir=self.p2p_dir)
        return self._runtime_contract_service_instance

    def _software_spec_service(self) -> SoftwareSpecService:
        if self._software_spec_service_instance is None:
            self._software_spec_service_instance = SoftwareSpecService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_change_dir=self._change_set_lifecycle_service().find_dir,
                show_proposal=self.show_proposal,
                show_change_set=self.show_change_set,
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
        return self._software_spec_service_instance

    def _software_spec_lifecycle_service(self) -> SoftwareSpecLifecycleService:
        if self._software_spec_lifecycle_service_instance is None:
            self._software_spec_lifecycle_service_instance = SoftwareSpecLifecycleService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_change_dir=self._change_set_lifecycle_service().find_dir,
                show_proposal=self.show_proposal,
                active_project_vertical=self.active_project_vertical,
                project_definition_view=self.project_definition_view,
                choice_statuses=self.choice_statuses,
                show_choice=self.show_choice,
            )
        return self._software_spec_lifecycle_service_instance

    def _sync_service(self) -> SyncService:
        if self._sync_service_instance is None:
            self._sync_service_instance = SyncService(
                root=self.root,
                remote_profile=self.remote_profile,
                git_status=get_git_status,
                remote_url=remote_url,
                fetch_remote=fetch_remote,
                pull_branch=pull_branch,
                push_branch=push_branch,
            )
        return self._sync_service_instance

    def _spec_export_service(self) -> SpecExportService:
        if self._spec_export_service_instance is None:
            self._spec_export_service_instance = SpecExportService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                show_change_set=self.show_change_set,
                status=self.status,
                accepted_proposals=self._registry_record_builder_service().accepted_proposals,
                proposal_summaries=self.proposal_summaries,
                required_spec_files=self._software_spec_service().required_files,
            )
        return self._spec_export_service_instance

    def _visible_project_export_service(self) -> VisibleProjectExportService:
        if self._visible_project_export_service_instance is None:
            self._visible_project_export_service_instance = VisibleProjectExportService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                project_name=self._project_name,
                accepted_proposals=self._registry_record_builder_service().accepted_proposals,
                project_readiness_review=self.review_project_readiness,
                project_vertical_lock_status=self.project_vertical_lock_status,
                project_definition_view=self.project_definition_view,
            )
        return self._visible_project_export_service_instance

    def _work_planning_service(self) -> WorkPlanningService:
        if self._work_planning_service_instance is None:
            self._work_planning_service_instance = WorkPlanningService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                export_targets=self._spec_export_service().export_targets,
                validate_export=self.validate_software_spec_export,
                find_change_dir=self._change_set_lifecycle_service().find_dir,
                scanned_work_items=self._scanned_work_items,
            )
        return self._work_planning_service_instance

    def _work_branch_service(self) -> WorkBranchService:
        if self._work_branch_service_instance is None:
            self._work_branch_service_instance = WorkBranchService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_work_dir=self._work_planning_service().find_dir,
                list_local_work_branches=list_local_work_branches,
                list_files_at_ref=list_files_at_ref,
                read_file_at_ref=read_file_at_ref,
                git_status=get_git_status,
                branch_exists=branch_exists,
                head_commit=head_commit,
                create_and_checkout_branch=create_and_checkout_branch,
                changed_files=changed_files,
                commit_all=commit_all,
                remote_url=remote_url,
                push_branch=push_branch,
                remote_profile=self.remote_profile,
                checkout_branch=checkout_branch,
                merge_branch_no_commit=merge_branch_no_commit,
                conflicted_files=conflicted_files,
                merge_in_progress=merge_in_progress,
                stage_all=stage_all,
                restore_path=restore_path,
                abort_merge=abort_merge,
                show_work=self.show_work,
                delete_local_branch=delete_local_branch,
                delete_remote_branch=delete_remote_branch,
            )
        return self._work_branch_service_instance

    def _workspace_status_service(self) -> WorkspaceStatusService:
        if self._workspace_status_service_instance is None:
            self._workspace_status_service_instance = WorkspaceStatusService(root=self.root, p2p_dir=self.p2p_dir)
        return self._workspace_status_service_instance

    def _project_initialization_service(self) -> ProjectInitializationService:
        if self._project_initialization_service_instance is None:
            self._project_initialization_service_instance = ProjectInitializationService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                remote_profile_default_payload=self._remote_profile_service().default_payload,
                readiness_default_profile_payload=self._readiness_service().default_profile_payload,
                permissions_default_policy_payload=self._permissions_service().default_policy_payload,
                refresh_agent_instructions=self.refresh_agent_instructions,
            )
        return self._project_initialization_service_instance

    def init_project(
        self,
        name: str,
        agent_profile: str | None = None,
        repository_mode: str = "local",
        project_domain: str = "none",
        rubric_enabled: dict[str, bool] | None = None,
        owner: str | None = None,
        remote_provider: str | None = None,
        remote_name: str = "origin",
        remote_url_value: str | None = None,
        vertical_id: str | None = None,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> list[Path]:
        return self.init_project_with_summary(
            name=name,
            agent_profile=agent_profile,
            repository_mode=repository_mode,
            project_domain=project_domain,
            rubric_enabled=rubric_enabled,
            owner=owner,
            remote_provider=remote_provider,
            remote_name=remote_name,
            remote_url_value=remote_url_value,
            vertical_id=vertical_id,
            profile=profile,
            modules=modules,
        ).created

    def init_project_with_summary(
        self,
        name: str,
        agent_profile: str | None = None,
        repository_mode: str = "local",
        project_domain: str = "none",
        rubric_enabled: dict[str, bool] | None = None,
        owner: str | None = None,
        remote_provider: str | None = None,
        remote_name: str = "origin",
        remote_url_value: str | None = None,
        vertical_id: str | None = None,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> ProjectInitializationResult:
        if (self.p2p_dir / "project.yml").exists():
            self._ensure_runtime_write_allowed("project_init_existing")
        result = self._project_initialization_service().init_project_with_summary(
            name=name,
            agent_profile=agent_profile,
            repository_mode=repository_mode,
            project_domain=project_domain,
            rubric_enabled=rubric_enabled,
            owner=owner,
            remote_provider=remote_provider,
            remote_name=remote_name,
            remote_url_value=remote_url_value,
        )
        created = list(result.created)
        if vertical_id:
            active = self._project_vertical_service().select_vertical(
                vertical_id,
                actor=owner or "owner",
                profile=profile,
                modules=modules,
            )
            for path in (
                Path(".p2p/project/vertical.yml"),
                Path(".p2p/project/vertical.lock.yml"),
                Path(".p2p/project/definition.yml"),
            ):
                if path is not None and path not in created:
                    created.append(path)
        return ProjectInitializationResult(
            created=created,
            agent_selection=result.agent_selection,
            agent_instructions=result.agent_instructions,
            mcp_hint=result.mcp_hint,
            gitignore_hygiene=result.gitignore_hygiene,
            warnings=list(result.warnings),
        )

    def refresh_agent_instructions(
        self,
        profile: str = "generic",
        repository_mode: str | None = None,
    ) -> AgentInstructionsResult:
        self._ensure_runtime_write_allowed("agent_instructions_refresh")
        return self._agent_instruction_service().refresh_instructions(profile, repository_mode)

    def agent_integrations_list(self) -> dict[str, object]:
        return self._agent_instruction_service().list_integrations()

    def agent_integration_show(self, adapter: str) -> dict[str, object]:
        return self._agent_instruction_service().show_integration(adapter)

    def agent_doctor(self, target: str | None = "all") -> AgentDoctorResult:
        return self._agent_instruction_service().doctor(target)

    def install_agent_integrations(
        self,
        target: str = "all",
        repository_mode: str | None = None,
        *,
        force: bool = False,
    ) -> AgentIntegrationResult:
        self._ensure_runtime_write_allowed("agent_install")
        return self._agent_instruction_service().install_integrations(target, repository_mode, force=force)

    def uninstall_agent_integration(self, adapter: str) -> AgentIntegrationResult:
        self._ensure_runtime_write_allowed("agent_uninstall")
        return self._agent_instruction_service().uninstall_integration(adapter)

    def permissions_show(self) -> dict[str, object]:
        return self._permissions_service().show(repository_mode=self._repository_mode(default="local"))

    def permissions_actor_add(
        self,
        actor_id: str,
        role: str = "contributor",
        kind: str = "person",
        display_name: str | None = None,
    ) -> PermissionActor:
        self._ensure_runtime_write_allowed("permissions_actor_add")
        return self._permissions_service().actor_add(
            actor_id,
            role=role,
            kind=kind,
            display_name=display_name,
            repository_mode=self._repository_mode(default="local"),
        )

    def consent_grant(
        self,
        operation: str,
        target: str,
        actor_id: str,
        approved_by: str = "owner",
        *,
        expires_on: str | None = None,
        single_use: bool = True,
        scope: str | None = None,
    ) -> ConsentReceipt:
        self._ensure_runtime_write_allowed("consent_grant")
        return self._consent_service().grant(
            operation,
            target,
            actor_id,
            approved_by=approved_by,
            expires_on=expires_on,
            single_use=single_use,
            scope=scope,
        )

    def consent_request(
        self,
        operation: str,
        target: str,
        actor_id: str,
        *,
        requested_by: str | None = None,
        scope: str | None = None,
        expires_on: str | None = None,
    ) -> ConsentReceipt:
        self._ensure_runtime_write_allowed("consent_request")
        return self._consent_service().request(
            operation,
            target,
            actor_id,
            requested_by=requested_by,
            scope=scope,
            expires_on=expires_on,
        )

    def consent_show(self, consent_id: str) -> ConsentReceipt:
        return self._consent_service().show(consent_id)

    def consent_statuses(self) -> list[ConsentReceipt]:
        return self._consent_service().statuses()

    def consent_revoke(self, consent_id: str, reason: str = "") -> ConsentReceipt:
        self._ensure_runtime_write_allowed("consent_revoke")
        return self._consent_service().revoke(consent_id, reason=reason)

    def consent_validate(
        self,
        consent_id: str,
        *,
        operation: str,
        target: str,
        actor_id: str,
    ) -> ConsentReceipt:
        return self._consent_service().validate(
            consent_id,
            operation=operation,
            target=target,
            actor_id=actor_id,
        )

    def consent_consume(self, consent_id: str, *, result: dict[str, object]) -> ConsentReceipt:
        self._ensure_runtime_write_allowed("consent_consume")
        return self._consent_service().consume(consent_id, result=result)

    def consent_mark_used_with_error(
        self,
        consent_id: str,
        *,
        error: str,
        result: dict[str, object] | None = None,
    ) -> ConsentReceipt:
        self._ensure_runtime_write_allowed("consent_mark_used_with_error")
        return self._consent_service().mark_used_with_error(consent_id, error=error, result=result)

    def _project_name(self) -> str:
        project_file = self.p2p_dir / "project.yml"
        if not project_file.exists():
            return self.root.name
        data = _read_yaml_mapping(project_file, default={})
        name = data.get("project", {}).get("name") if isinstance(data.get("project"), dict) else None
        return str(name or self.root.name)

    def _repository_mode(self, default: str = "local") -> str:
        project_file = self.p2p_dir / "project.yml"
        if not project_file.exists():
            return default
        data = _read_yaml_mapping(project_file, default={})
        repo_data = data.get("repository", {})
        if not isinstance(repo_data, dict):
            return default
        return str(repo_data.get("mode") or default)

    def _set_repository_mode(self, mode: str) -> None:
        self._ensure_runtime_write_allowed("repository_mode_set")
        mode = _normalize_repository_mode(mode)
        project_file = self.p2p_dir / "project.yml"
        data = _read_yaml_mapping(project_file, default={})
        repo_data = data.get("repository", {})
        if not isinstance(repo_data, dict):
            repo_data = {}
        repo_data["mode"] = mode
        repo_data.setdefault("managed_by_p2p", False)
        data["repository"] = repo_data
        project_file.parent.mkdir(parents=True, exist_ok=True)
        project_file.write_text(_yaml_dump(data), encoding="utf-8")

    def status(self) -> WorkspaceStatus:
        return self._workspace_status_service().status()

    def remote_profile(self) -> RemoteProjectProfile:
        return self._remote_profile_service().show()

    def configure_remote_profile(
        self,
        *,
        mode: str,
        provider: str | None = None,
        remote: str = "origin",
        url: str | None = None,
    ) -> RemoteProjectProfile:
        self._ensure_runtime_write_allowed("remote_profile_configure")
        return self._remote_profile_service().configure(
            mode=mode,
            provider=provider,
            remote=remote,
            url=url,
        )

    def sync_status(self, remote: str | None = None) -> SyncStatus:
        return self._sync_service().status(remote)

    def sync_fetch(self, remote: str | None = None) -> SyncResult:
        self._ensure_runtime_write_allowed("sync_fetch")
        return self._sync_service().fetch(remote)

    def sync_pull(self, remote: str | None = None) -> SyncResult:
        self._ensure_runtime_write_allowed("sync_pull")
        return self._sync_service().pull(remote)

    def sync_push(self, remote: str | None = None) -> SyncResult:
        self._ensure_runtime_write_allowed("sync_push")
        return self._sync_service().push(remote)

    def proposal_summaries(self, status: str | None = None) -> list[ProposalSummary]:
        return self._workspace_status_service().proposal_summaries(status)

    def show_proposal(self, proposal_id: str) -> ProposalDetail:
        return self._proposal_document_service().show(proposal_id)

    def proposal_artifact_catalog(self, proposal_id: str) -> list[ProposalArtifactCatalogItem]:
        return self._proposal_review_view_service().artifact_catalog(proposal_id)

    def proposal_full_view(self, proposal_id: str) -> ProposalFullView:
        return self._proposal_review_view_service().full_view(proposal_id)

    def commit_proposal_draft(self, proposal_id: str, actor: str = "local") -> ProposalDraftCommit:
        self._ensure_runtime_write_allowed("proposal_draft_commit")
        return self._proposal_draft_commit_service().commit(proposal_id, actor)

    def branch_proposal(
        self,
        proposal_id: str,
        actor: str = "local",
        base_branch: str | None = None,
        allow_proposal_base: bool = False,
    ) -> ProposalBranchDetail:
        self._ensure_runtime_write_allowed("proposal_branch")
        return self._proposal_branch_service().branch(
            proposal_id,
            actor=actor,
            base_branch=base_branch,
            allow_proposal_base=allow_proposal_base,
        )

    def show_proposal_branch(self, proposal_id: str) -> ProposalBranchDetail:
        return self._proposal_branch_service().show(proposal_id)

    def publish_proposal_branch(
        self,
        proposal_id: str,
        remote: str | None = None,
        *,
        auto_renumber: bool = False,
    ) -> ProposalBranchDetail:
        self._ensure_runtime_write_allowed("proposal_publish")
        return self._proposal_branch_service().publish(
            proposal_id,
            remote=remote,
            auto_renumber=auto_renumber,
        )

    def request_proposal_branch_review(self, proposal_id: str, provider: str | None = None) -> ProposalBranchDetail:
        self._ensure_runtime_write_allowed("proposal_request_review")
        return self._proposal_branch_service().request_review(proposal_id, provider)

    def retire_proposal_branch(self, proposal_id: str, reason: str) -> ProposalBranchDetail:
        self._ensure_runtime_write_allowed("proposal_retire_branch")
        return self._proposal_branch_service().retire(proposal_id, reason)

    def accept_proposal_branch(self, proposal_id: str, reason: str) -> ProposalBranchDetail:
        self._ensure_runtime_write_allowed("proposal_accept_branch")
        return self._proposal_branch_service().accept(proposal_id, reason)

    def reject_proposal_branch(self, proposal_id: str, reason: str) -> ProposalBranchDetail:
        self._ensure_runtime_write_allowed("proposal_reject_branch")
        return self._proposal_branch_service().reject(proposal_id, reason)

    def _decide_proposal_branch(self, proposal_id: str, outcome: str, reason: str) -> ProposalBranchDetail:
        self._ensure_runtime_write_allowed("proposal_decide_branch")
        return self._proposal_branch_service().decide(proposal_id, outcome, reason)

    def merge_proposal_branch(self, proposal_id: str) -> ProposalMerge | ProposalMergeConflict:
        self._ensure_runtime_write_allowed("proposal_merge")
        return self._proposal_branch_service().merge(proposal_id)

    def continue_merge_proposal_branch(self, proposal_id: str) -> ProposalMerge:
        self._ensure_runtime_write_allowed("proposal_merge_continue")
        return self._proposal_branch_service().continue_merge(proposal_id)

    def abort_merge_proposal_branch(self, proposal_id: str) -> ProposalBranchDetail:
        self._ensure_runtime_write_allowed("proposal_merge_abort")
        return self._proposal_branch_service().abort_merge_branch(proposal_id)

    def finalize_proposal_branch(self, proposal_id: str, remote: str | None = None) -> ProposalFinalize:
        self._ensure_runtime_write_allowed("proposal_finalize")
        return self._proposal_branch_service().finalize(proposal_id, remote)

    def cleanup_proposal_branch(
        self,
        proposal_id: str,
        *,
        delete_remote: bool = False,
        remote: str | None = None,
    ) -> ProposalCleanup:
        self._ensure_runtime_write_allowed("proposal_cleanup")
        return self._proposal_branch_service().cleanup(
            proposal_id,
            delete_remote=delete_remote,
            remote=remote,
        )

    def scan_proposal_branches(self) -> ProposalBranchScan:
        return self._proposal_branch_service().scan()

    def check(self) -> WorkspaceCheck:
        return self._workspace_status_service().check()

    def validate(self) -> ValidationResult:
        return self._validation_service().validate()

    def runtime_status(self) -> RuntimeStatus:
        return self._runtime_contract_service().status()

    def runtime_write_preflight(self, operation: str) -> RuntimeWritePreflight:
        return self._runtime_contract_service().write_preflight(operation)

    def runtime_contract_update_preview(
        self,
        *,
        requires: str,
        recommended: str,
        reason: str = "",
        decision: str = "",
        actor: str = "owner",
    ) -> RuntimeContractUpdatePreview:
        return self._runtime_contract_service().preview_update(
            requires=requires,
            recommended=recommended,
            reason=reason,
            decision=decision,
            actor=actor,
        )

    def runtime_contract_update_apply(
        self,
        *,
        requires: str,
        recommended: str,
        expected_state_token: str = "",
        confirm: bool = False,
        reason: str = "",
        decision: str = "",
        actor: str = "owner",
    ) -> RuntimeContractUpdateResult:
        return self._runtime_contract_service().apply_update(
            requires=requires,
            recommended=recommended,
            expected_state_token=expected_state_token,
            confirm=confirm,
            reason=reason,
            decision=decision,
            actor=actor,
        )

    def runtime_contract_adopt(
        self,
        *,
        requires: str,
        recommended: str,
        confirm: bool = False,
        actor: str = "owner",
    ) -> RuntimeContractAdoptionResult:
        return self._runtime_contract_service().adopt_contract(
            requires=requires,
            recommended=recommended,
            confirm=confirm,
            actor=actor,
        )

    def _ensure_runtime_write_allowed(self, operation: str) -> RuntimeWritePreflight:
        if not self.p2p_dir.exists() or not (self.p2p_dir / "project.yml").exists():
            return self._runtime_contract_service().write_preflight(operation)
        preflight = self._runtime_contract_service().write_preflight(operation)
        preflight.require_allowed()
        return preflight

    def readiness_profile(self, profile_id: str = DEFAULT_READINESS_PROFILE_ID) -> ReadinessProfile:
        return self._readiness_service().profile(profile_id)

    def read_proposal_readiness(self, proposal_id: str) -> ProposalReadiness:
        return self._readiness_service().read(proposal_id)

    def write_proposal_readiness(self, proposal_id: str, readiness: dict[str, object]) -> Path:
        self._ensure_runtime_write_allowed("proposal_readiness_write")
        return self._readiness_service().write(proposal_id, readiness)

    def record_proposal_readiness_override(
        self,
        proposal_id: str,
        reason: str,
        approver: str,
    ) -> Path:
        self._ensure_runtime_write_allowed("proposal_readiness_override")
        return self._readiness_service().record_override(proposal_id, reason, approver)

    def refresh_proposal_readiness(self, proposal_id: str) -> ProposalReadiness:
        self._ensure_runtime_write_allowed("proposal_readiness_refresh")
        return self._readiness_service().refresh(proposal_id)

    def initialize_proposal_readiness(self, proposal_id: str) -> ProposalReadiness:
        self._ensure_runtime_write_allowed("proposal_readiness_init")
        return self._readiness_service().initialize(proposal_id)

    def assess_proposal_readiness(self, proposal_id: str) -> ProposalReadiness:
        self._ensure_runtime_write_allowed("proposal_readiness_assess")
        return self._readiness_service().assess(proposal_id)

    def review_proposal_readiness(self, proposal_id: str):
        return self._readiness_service().review(proposal_id)

    def read_proposal_questions(self, proposal_id: str):
        return self._proposal_question_service().read(proposal_id)

    def initialize_proposal_questions(self, proposal_id: str, actor: str = "local"):
        self._ensure_runtime_write_allowed("proposal_questions_init")
        return self._proposal_question_service().initialize(proposal_id, actor=actor)

    def add_proposal_question(
        self,
        proposal_id: str,
        *,
        gap: str,
        question: str,
        priority,
        rationale: str = "",
        group_id: str = "",
        actor: str = "local",
    ):
        self._ensure_runtime_write_allowed("proposal_questions_add")
        return self._proposal_question_service().add(
            proposal_id,
            gap=gap,
            question=question,
            priority=priority,
            rationale=rationale,
            group_id=group_id,
            actor=actor,
        )

    def answer_proposal_question(
        self,
        proposal_id: str,
        question_id: str,
        answer: str,
        *,
        source: str = "owner",
        actor: str = "local",
        replace: bool = False,
    ):
        self._ensure_runtime_write_allowed("proposal_questions_answer")
        return self._proposal_question_service().answer(
            proposal_id,
            question_id,
            answer,
            source=source,
            actor=actor,
            replace=replace,
        )

    def set_proposal_question_state(self, proposal_id: str, question_id: str, state, *, reason: str = "", actor: str = "local"):
        self._ensure_runtime_write_allowed("proposal_questions_set_state")
        return self._proposal_question_service().set_state(proposal_id, question_id, state, reason=reason, actor=actor)

    def supersede_proposal_question(self, proposal_id: str, question_id: str, superseded_by: str, *, actor: str = "local"):
        self._ensure_runtime_write_allowed("proposal_questions_supersede")
        return self._proposal_question_service().supersede(proposal_id, question_id, superseded_by, actor=actor)

    def set_proposal_question_group_state(self, proposal_id: str, group_id: str, state, *, actor: str = "local"):
        self._ensure_runtime_write_allowed("proposal_questions_group_state")
        return self._proposal_question_service().group_state(proposal_id, group_id, state, actor=actor)

    def next_proposal_question(self, proposal_id: str, *, include_muted: bool = False, include_deferred: bool = False):
        return self._proposal_question_service().next_question(
            proposal_id,
            include_muted=include_muted,
            include_deferred=include_deferred,
        )

    def reassess_proposal_questions(self, proposal_id: str):
        self._ensure_runtime_write_allowed("proposal_questions_reassess")
        return self._proposal_question_service().reassess(proposal_id)

    def apply_proposal_question_answers(self, proposal_id: str, actor: str = "local"):
        self._ensure_runtime_write_allowed("proposal_questions_apply")
        return self._proposal_question_service().apply_summary(proposal_id, actor=actor)

    def import_proposal_questions(self, proposal_id: str, source: Path, actor: str = "local"):
        self._ensure_runtime_write_allowed("proposal_questions_import")
        return self._proposal_question_service().import_payload(proposal_id, source, actor=actor)

    def read_proposal_artifacts(self, proposal_id: str):
        return self._proposal_artifact_state_service().read(proposal_id)

    def initialize_proposal_artifacts(self, proposal_id: str, actor: str = "local"):
        self._ensure_runtime_write_allowed("proposal_artifacts_init")
        return self._proposal_artifact_state_service().initialize(proposal_id, actor=actor)

    def set_proposal_artifact_state(
        self,
        proposal_id: str,
        artifact_id: str,
        *,
        expectation=None,
        status=None,
        reason: str = "",
        actor: str = "local",
        source: str = "agent",
        risk_flags=None,
    ):
        self._ensure_runtime_write_allowed("proposal_artifacts_set")
        return self._proposal_artifact_state_service().set_artifact(
            proposal_id,
            artifact_id,
            expectation=expectation,
            status=status,
            reason=reason,
            actor=actor,
            source=source,
            risk_flags=risk_flags,
        )

    def confirm_proposal_artifact_state(self, proposal_id: str, artifact_id: str, actor: str = "owner"):
        self._ensure_runtime_write_allowed("proposal_artifacts_confirm")
        return self._proposal_artifact_state_service().confirm(proposal_id, artifact_id, actor=actor)

    def mark_proposal_artifacts_legacy(self, proposal_id: str, reason: str = "Proposal predates artifact-aware state.", actor: str = "local"):
        self._ensure_runtime_write_allowed("proposal_artifacts_mark_legacy")
        return self._proposal_artifact_state_service().mark_legacy(proposal_id, reason=reason, actor=actor)

    def create_proposal(self, title: str) -> Proposal:
        self._ensure_runtime_write_allowed("proposal_create")
        proposal = self._proposal_document_service().create(title)
        self._proposal_artifact_state_service().initialize(proposal.proposal_id)
        return proposal

    def create_proposal_with_details(
        self,
        title: str,
        problem: str | None = None,
        context: str | None = None,
        goals: list[str] | None = None,
        non_goals: list[str] | None = None,
        proposal: str | None = None,
        acceptance_criteria: list[str] | None = None,
    ) -> Proposal:
        self._ensure_runtime_write_allowed("proposal_create")
        proposal = self._proposal_document_service().create_with_details(
            title=title,
            problem=problem,
            context=context,
            goals=goals,
            non_goals=non_goals,
            proposal=proposal,
            acceptance_criteria=acceptance_criteria,
        )
        self._proposal_artifact_state_service().initialize(proposal.proposal_id)
        return proposal

    def update_proposal(
        self,
        proposal_id: str,
        problem: str | None = None,
        context: str | None = None,
        goals: list[str] | None = None,
        non_goals: list[str] | None = None,
        proposal: str | None = None,
        acceptance_criteria: list[str] | None = None,
    ) -> Path:
        self._ensure_runtime_write_allowed("proposal_update")
        return self._proposal_document_service().update(
            proposal_id,
            problem=problem,
            context=context,
            goals=goals,
            non_goals=non_goals,
            proposal=proposal,
            acceptance_criteria=acceptance_criteria,
        )

    def add_contribution(
        self,
        proposal_id: str,
        contribution_type: ContributionType,
        text: str,
        relevance_hint: str,
        author: str,
    ) -> Contribution:
        self._ensure_runtime_write_allowed("proposal_contribution_add")
        return self._proposal_document_service().add_contribution(
            proposal_id,
            contribution_type,
            text=text,
            relevance_hint=relevance_hint,
            author=author,
        )

    def list_contributions(self, proposal_id: str) -> ProposalContributionList:
        return self._proposal_document_service().list_contributions(proposal_id)

    def record_decision(
        self,
        proposal_id: str,
        outcome: DecisionOutcome,
        reason: str,
        approver: str,
    ) -> Decision:
        self._ensure_runtime_write_allowed("proposal_decision_record")
        return self._proposal_decision_service().record(proposal_id, outcome, reason, approver)

    def generate_prompt(self, proposal_id: str, kind: PromptKind) -> Path:
        self._ensure_runtime_write_allowed("proposal_prompt_generate")
        return self._proposal_artifact_service().generate_prompt(proposal_id, kind)

    def import_exploration(self, proposal_id: str, source: Path) -> list[Path]:
        self._ensure_runtime_write_allowed("proposal_exploration_import")
        return self._proposal_artifact_service().import_exploration(proposal_id, source)

    def exploration_status(self, proposal_id: str) -> ExplorationStatus:
        return self._proposal_artifact_service().exploration_status(proposal_id)

    def import_artifact(self, proposal_id: str, kind: ImportKind, source: Path) -> Path:
        self._ensure_runtime_write_allowed("proposal_artifact_import")
        return self._proposal_artifact_service().import_artifact(proposal_id, kind, source)

    def import_impact(self, proposal_id: str, source: Path) -> list[Path]:
        self._ensure_runtime_write_allowed("proposal_impact_import")
        return self._proposal_artifact_service().import_impact(proposal_id, source)

    def import_proposal_artifact_content(
        self,
        proposal_id: str,
        kind: ArtifactImportKind,
        *,
        source: Path | None = None,
        content: str | None = None,
        artifacts: dict[str, str] | None = None,
    ) -> ArtifactImportResult:
        self._ensure_runtime_write_allowed("proposal_artifact_import_content")
        return self._proposal_artifact_service().import_content(
            proposal_id,
            kind,
            source=source,
            content=content,
            artifacts=artifacts,
        )

    def init_governance(self, mode: str) -> list[Path]:
        self._ensure_runtime_write_allowed("governance_init")
        return self._governance_service().init_governance(mode)

    def governance_status(self) -> GovernanceStatus:
        return self._governance_service().governance_status()

    def record_vote(
        self,
        proposal_id: str,
        choice: str,
        reason: str,
        voter: str,
        role: str,
    ) -> VoteStatus:
        self._ensure_runtime_write_allowed("governance_vote_record")
        return self._governance_service().record_vote(proposal_id, choice, reason, voter, role)

    def vote_status(self, proposal_id: str) -> VoteStatus:
        return self._governance_service().vote_status(proposal_id)

    def record_precedent(self, proposal_id: str, title: str, reason: str) -> Path:
        self._ensure_runtime_write_allowed("governance_precedent_record")
        return self._governance_service().record_precedent(proposal_id, title, reason)

    def choice_governance_preflight(
        self,
        choice_id: str,
        *,
        option: str,
        actor: str,
        precedent_id: str | None = None,
        tag: str | None = None,
    ) -> GovernancePreflightResult:
        return self._governance_policy_service().choice_preflight(
            choice_id,
            option=option,
            actor=actor,
            precedent_id=precedent_id,
            tag=tag,
        )

    def search_decision_precedents(
        self,
        *,
        precedent_id: str | None = None,
        proposal_id: str | None = None,
        choice_id: str | None = None,
        tag: str | None = None,
    ) -> list[PrecedentMatch]:
        return self._governance_policy_service().search_precedents(
            precedent_id=precedent_id,
            proposal_id=proposal_id,
            choice_id=choice_id,
            tag=tag,
        )

    def validate_governance_policy(self) -> GovernanceValidationResult:
        return self._governance_policy_service().validate_governance()

    def refresh_project_state(self) -> list[Path]:
        self._ensure_runtime_write_allowed("project_state_refresh")
        return self._project_state_service().refresh()

    def project_state_status(self) -> ProjectStateStatus:
        return self._project_state_service().status()

    def show_project_state(self, section: str) -> str:
        return self._project_state_service().show(section)

    def project_interaction_style(self) -> InteractionStyleView:
        return self._project_interaction_style_service().show()

    def set_project_interaction_style(
        self,
        *,
        technical_verbosity: int | str | None = None,
        formality: int | str | None = None,
        assertiveness: int | str | None = None,
        actor: str = "local",
    ) -> InteractionStyleView:
        self._ensure_runtime_write_allowed("project_interaction_style_set")
        return self._project_interaction_style_service().set_style(
            technical_verbosity=technical_verbosity,
            formality=formality,
            assertiveness=assertiveness,
            actor=actor,
        )

    def export_visible_project_definition(self) -> VisibleProjectExportResult:
        self._ensure_runtime_write_allowed("project_definition_export")
        return self._visible_project_export_service().export()

    def visible_project_definition_export_status(self) -> VisibleProjectExportStatus:
        return self._visible_project_export_service().status()

    def project_verticals(self) -> list[VerticalListItem]:
        return self._project_vertical_service().list_verticals()

    def show_project_vertical(self, vertical_id: str) -> VerticalPack:
        return self._project_vertical_service().show_vertical(vertical_id)

    def validate_project_vertical(self, target: str) -> VerticalValidationResult:
        return self._project_vertical_service().validate_vertical(target)

    def propose_project_vertical(self, idea: str) -> CustomVerticalCandidate:
        return self._project_vertical_service().propose_vertical(idea)

    def add_project_vertical(
        self,
        source: Path,
        *,
        activate: bool = False,
        actor: str = "local",
    ) -> ProjectVerticalAddResult:
        self._ensure_runtime_write_allowed("project_vertical_add")
        return self._project_vertical_service().add_vertical(source, activate=activate, actor=actor)

    def select_project_vertical(
        self,
        vertical_id: str,
        *,
        actor: str = "local",
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> ActiveProjectVertical:
        self._ensure_runtime_write_allowed("project_vertical_select")
        return self._project_vertical_service().select_vertical(
            vertical_id,
            actor=actor,
            profile=profile,
            modules=modules,
        )

    def active_project_vertical(self) -> ActiveProjectVertical:
        return self._project_vertical_service().active_vertical()

    def review_project_readiness(self, vertical_id: str | None = None) -> ProjectReadinessReview:
        return self._project_vertical_service().project_readiness_review(vertical_id=vertical_id)

    def project_vertical_lock_status(self) -> VerticalLockStatus:
        return self._project_vertical_service().vertical_lock_status()

    def repair_project_vertical_lock(self, *, actor: str = "local") -> VerticalLock:
        self._ensure_runtime_write_allowed("project_vertical_lock_repair")
        return self._project_vertical_service().repair_vertical_lock(actor=actor)

    def project_vertical_context(self) -> ProjectVerticalContext:
        return self._project_vertical_service().project_context()

    def project_vertical_sections(self, vertical_id: str | None = None) -> list[VerticalSection]:
        return self._project_vertical_service().list_sections(vertical_id=vertical_id)

    def project_vertical_section(self, section_id: str, vertical_id: str | None = None) -> VerticalSection:
        return self._project_vertical_service().show_section(section_id, vertical_id=vertical_id)

    def project_definition_view(self) -> ProjectDefinitionView:
        return self._project_vertical_service().project_definition_view()

    def update_project_definition(self, patch_path: Path) -> ProjectDefinitionPatchResult:
        self._ensure_runtime_write_allowed("project_definition_update")
        return self._project_vertical_service().apply_definition_patch(patch_path)

    def create_project_brief_prompt(self) -> ProjectBriefPrompt:
        self._ensure_runtime_write_allowed("project_brief_prompt")
        return self._project_state_service().create_brief_prompt()

    def import_project_brief(self, source: Path) -> list[Path]:
        self._ensure_runtime_write_allowed("project_brief_import")
        return self._project_state_service().import_brief(source)

    def show_project_brief(self) -> str:
        return self._project_state_service().show_brief()

    def refresh_project_assessment(self) -> ProjectAssessment:
        self._ensure_runtime_write_allowed("project_assessment_refresh")
        return self._project_assessment_service().refresh()

    def show_project_assessment(self) -> ProjectAssessment:
        return self._project_assessment_service().show()

    def init_project_rubrics(self, domain: str = "generic", force: bool = False) -> ProjectRubrics:
        self._ensure_runtime_write_allowed("project_rubrics_init")
        return self._project_maturity_service().init_project_rubrics(domain, force=force)

    def init_project_rubrics_preview(self, domain: str = "generic") -> list[dict[str, object]]:
        return self._project_maturity_service().init_project_rubrics_preview(domain)

    def show_project_rubrics(self) -> ProjectRubrics:
        return self._project_maturity_service().show_project_rubrics()

    def refresh_definition_maturity(self) -> ProjectDefinitionMaturity:
        self._ensure_runtime_write_allowed("definition_maturity_refresh")
        return self._project_maturity_service().refresh_definition_maturity()

    def show_definition_maturity(self) -> ProjectDefinitionMaturity:
        return self._project_maturity_service().show_definition_maturity()

    def context_packet(self, budget: str = "small", target: str | None = None) -> ContextPacket:
        return self._context_packet_service().context_packet(budget, target)

    def refresh_software_spec(self, change_id: str) -> SoftwareSpecStatus:
        self._ensure_runtime_write_allowed("software_spec_refresh")
        lifecycle = self._software_spec_lifecycle_service().ensure_can_write(
            "implementation_spec",
            change_id=change_id,
        )
        status = self._software_spec_service().refresh(change_id)
        return replace(status, lifecycle=lifecycle)

    def software_spec_lifecycle(
        self,
        intent: str = "implementation_spec",
        *,
        change_id: str | None = None,
        target: str | None = None,
    ) -> SpecLifecycleView:
        return self._software_spec_lifecycle_service().lifecycle(
            intent,
            change_id=change_id,
            target=target,
        )

    def software_spec_statuses(self) -> list[SoftwareSpecStatus]:
        return self._software_spec_service().statuses()

    def show_software_spec(self, change_id: str) -> str:
        return self._software_spec_service().show(change_id)

    def create_software_spec_prompt(self, change_id: str) -> SoftwareSpecPrompt:
        self._ensure_runtime_write_allowed("software_spec_prompt")
        return self._software_spec_service().create_prompt(change_id)

    def import_software_spec(self, change_id: str, source: Path) -> list[Path]:
        self._ensure_runtime_write_allowed("software_spec_import")
        return self._software_spec_service().import_spec(change_id, source)

    def export_software_spec(self, change_id: str, target: str) -> SoftwareSpecExportStatus:
        self._ensure_runtime_write_allowed("software_spec_export")
        lifecycle = self._software_spec_lifecycle_service().ensure_can_write(
            "downstream_export",
            change_id=change_id,
            target=target,
        )
        status = self._spec_export_service().export(change_id, target)
        return replace(status, lifecycle=lifecycle)

    def software_spec_export_statuses(self) -> list[SoftwareSpecExportStatus]:
        return self._spec_export_service().statuses()

    def show_software_spec_export(self, change_id: str, target: str) -> str:
        return self._spec_export_service().show(change_id, target)

    def validate_software_spec_export(self, change_id: str, target: str) -> SoftwareSpecExportValidation:
        return self._spec_export_service().validate(change_id, target)

    def create_work_plan(self, change_id: str, target: str) -> WorkDetail:
        self._ensure_runtime_write_allowed("work_plan_create")
        return self._work_planning_service().create_plan(change_id, target)

    def work_statuses(self) -> list[WorkStatus]:
        return self._work_planning_service().statuses()

    def work_summaries(self) -> list[WorkSummary]:
        return self._work_planning_service().summaries()

    def show_work(self, work_id: str) -> WorkDetail:
        return self._work_planning_service().show(work_id)

    def branch_work(self, work_id: str) -> WorkBranch:
        self._ensure_runtime_write_allowed("work_branch")
        return self._work_branch_service().branch(work_id)

    def retire_work(self, work_id: str, reason: str) -> WorkRetire:
        self._ensure_runtime_write_allowed("work_retire")
        return self._work_planning_service().retire(work_id, reason)

    def submit_work(self, work_id: str) -> WorkSubmit:
        self._ensure_runtime_write_allowed("work_submit")
        return self._work_branch_service().submit(work_id)

    def review_work(self, work_id: str) -> WorkReview:
        self._ensure_runtime_write_allowed("work_review")
        return self._work_branch_service().review(work_id)

    def publish_work(self, work_id: str, remote: str = "origin") -> WorkPublish:
        self._ensure_runtime_write_allowed("work_publish")
        return self._work_branch_service().publish(work_id, remote)

    def request_external_work_review(
        self,
        work_id: str,
        provider: str | None = None,
    ) -> WorkReviewRequest:
        self._ensure_runtime_write_allowed("work_request_review")
        return self._work_branch_service().request_external_review(work_id, provider)

    def accept_work(self, work_id: str) -> WorkAccept | WorkAcceptConflict:
        self._ensure_runtime_write_allowed("work_accept")
        return self._work_branch_service().accept(work_id)

    def continue_accept_work(self, work_id: str) -> WorkAccept:
        self._ensure_runtime_write_allowed("work_accept_continue")
        return self._work_branch_service().continue_accept(work_id)

    def abort_accept_work(self, work_id: str) -> WorkDetail:
        self._ensure_runtime_write_allowed("work_accept_abort")
        return self._work_branch_service().abort_accept(work_id)  # type: ignore[return-value]

    def finalize_work(self, work_id: str, remote: str = "origin") -> WorkFinalize:
        self._ensure_runtime_write_allowed("work_finalize")
        return self._work_branch_service().finalize(work_id, remote)

    def cleanup_work(self, work_id: str, delete_remote: bool = False, remote: str = "origin") -> WorkCleanup:
        self._ensure_runtime_write_allowed("work_cleanup")
        return self._work_branch_service().cleanup(work_id, delete_remote=delete_remote, remote=remote)

    def _scanned_work_items(self) -> list[dict[str, object]]:
        path = self.p2p_dir / "registries" / "work.yml"
        data = _read_yaml_mapping(path, default={"work_items": []})
        items = data.get("work_items", [])
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]

    def scan_work_branches(self) -> WorkScan:
        return self._work_branch_service().scan()

    def next_actions(self, limit: int | None = None) -> list[NextAction]:
        return self._next_action_service().list(limit=limit)

    def next_action_add(
        self,
        *,
        kind: str,
        target: str,
        reason: str,
        command: str = "",
        priority: str = "medium",
        action_id: str | None = None,
    ) -> NextAction:
        self._ensure_runtime_write_allowed("next_action_add")
        return self._next_action_service().add(
            kind=kind,
            target=target,
            reason=reason,
            command=command,
            priority=priority,
            action_id=action_id,
        )

    def next_action_complete(self, action_id: str, reason: str) -> dict[str, object]:
        self._ensure_runtime_write_allowed("next_action_complete")
        return self._next_action_service().complete(action_id, reason)

    def next_action_retire(self, action_id: str, reason: str) -> dict[str, object]:
        self._ensure_runtime_write_allowed("next_action_retire")
        return self._next_action_service().retire(action_id, reason)

    def next_actions_refresh(self) -> dict[str, object]:
        self._ensure_runtime_write_allowed("next_actions_refresh")
        return self._next_action_service().refresh()

    def record_conflict(
        self,
        proposals: list[str],
        conflict_type: str,
        reason: str,
        winner: str | None,
    ) -> ConflictStatus:
        self._ensure_runtime_write_allowed("conflict_record")
        return self._conflict_memory_service().record(
            proposals=proposals,
            conflict_type=conflict_type,
            reason=reason,
            winner=winner,
        )

    def conflict_status(self) -> ConflictStatus:
        return self._conflict_memory_service().status()

    def create_change_set(self, source: str, title: str | None = None) -> ChangeSetStatus:
        self._ensure_runtime_write_allowed("change_create")
        return self._change_set_lifecycle_service().create(source, title=title)

    def change_set_statuses(self) -> list[ChangeSetStatus]:
        return self._change_set_lifecycle_service().statuses()

    def change_set_policy(self, change_id: str) -> ChangeSetPolicy:
        return self._change_set_lifecycle_service().policy(change_id)

    def show_change_set(self, change_id: str) -> ChangeSetDetail:
        return self._change_set_lifecycle_service().show(change_id)

    def update_change_set_status(self, change_id: str, new_status: str) -> ChangeSetStatus:
        self._ensure_runtime_write_allowed("change_set_status_update")
        return self._change_set_lifecycle_service().update_status(change_id, new_status)

    def change_set_tasks(self, change_id: str) -> ChangeSetTaskView:
        return self._change_set_lifecycle_service().tasks(change_id)

    def refresh_registries(self) -> list[Path]:
        self._ensure_runtime_write_allowed("registry_refresh")
        return self._registry_service().refresh()

    def registry_status(self) -> RegistryStatus:
        return self._registry_service().status()

    def show_registry(self, name: str) -> RegistryView:
        return self._registry_service().show(name)

    def create_intake_prompt(self, idea: str) -> IntakePrompt:
        self._ensure_runtime_write_allowed("intake_prompt_create")
        return self._intake_lifecycle_service().create_prompt(idea)

    def import_intake(self, intake_id: str, source: Path) -> list[Path]:
        self._ensure_runtime_write_allowed("intake_import")
        return self._intake_lifecycle_service().import_output(intake_id, source)

    def intake_statuses(self) -> list[IntakeStatus]:
        return self._intake_lifecycle_service().statuses()

    def create_intake_apply_plan(self, intake_id: str) -> IntakeApplyPlan:
        self._ensure_runtime_write_allowed("intake_apply_plan_create")
        return self._intake_lifecycle_service().create_apply_plan(intake_id)

    def show_intake_apply_plan(self, intake_id: str) -> IntakeApplyPlan:
        return self._intake_lifecycle_service().show_apply_plan(intake_id)

    def run_intake_apply_action(
        self,
        intake_id: str,
        action_id: str,
        options: list[str] | None = None,
    ) -> IntakeAppliedAction:
        self._ensure_runtime_write_allowed("intake_apply_run")
        return self._intake_lifecycle_service().run_apply_action(intake_id, action_id, options=options)

    def create_choice(
        self,
        title: str,
        options: list[str],
        related: list[str] | None = None,
        source: str | None = None,
    ) -> ChoiceStatus:
        self._ensure_runtime_write_allowed("choice_create")
        return self._choice_lifecycle_service().create(title, options, related=related, source=source)

    def choice_statuses(self) -> list[ChoiceStatus]:
        return self._choice_lifecycle_service().statuses()

    def show_choice(self, choice_id: str) -> ChoiceDetail:
        return self._choice_lifecycle_service().show(choice_id)

    def discover_choices(self) -> list[ChoiceDiscoveryFinding]:
        return self._choice_lifecycle_service().discover()

    def block_choice(
        self,
        choice_id: str,
        target: str,
        target_type: str,
        reason: str,
    ) -> ChoiceDetail:
        self._ensure_runtime_write_allowed("choice_block")
        return self._choice_lifecycle_service().block(choice_id, target, target_type, reason)

    def unblock_choice(self, choice_id: str, target: str, target_type: str) -> ChoiceDetail:
        self._ensure_runtime_write_allowed("choice_unblock")
        return self._choice_lifecycle_service().unblock(choice_id, target, target_type)

    def decide_choice(
        self,
        choice_id: str,
        option: str,
        reason: str,
        decider: str,
    ) -> ChoiceStatus:
        self._ensure_runtime_write_allowed("choice_decide")
        return self._choice_lifecycle_service().decide(choice_id, option, reason, decider)

def _duplicate_proposal_ids_message(duplicates: dict[str, list[Path]], root: Path) -> str:
    parts = []
    for proposal_id, paths in sorted(duplicates.items()):
        relative_paths = ", ".join(str(_relative_to_root(path, root)) for path in sorted(paths))
        parts.append(f"{proposal_id}: {relative_paths}")
    return (
        "Duplicate proposal IDs found; generated registries would be ambiguous. "
        + "; ".join(parts)
        + ". Rename or retire duplicate proposal directories, then run `p2p registry refresh`."
    )

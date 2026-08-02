from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
import hashlib
from pathlib import Path
from typing import TypeVar

from p2p_engine.core.contribution import Contribution, ContributionType
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.decision_context import DecisionContextIndex
from p2p_engine.core.derived_freshness import DerivedFreshnessStatus
from p2p_engine.core.mutation_preview import MutationPreview, MutationResult
from p2p_engine.core.portable_verticals import (
    PortableVerticalInspection,
    PortableVerticalPackageResult,
    VerticalLifecyclePreview,
    VerticalLifecycleResult,
)
from p2p_engine.core.project_metadata import ProjectMetadataView
from p2p_engine.core.project_progress import ProjectProgress
from p2p_engine.core.project_questions import (
    ProjectQuestion,
    ProjectQuestionArtifact,
    ProjectQuestionOperationResult,
)
from p2p_engine.core.project_readiness import ProjectReadinessResult, ProjectReadinessSnapshot
from p2p_engine.core.project_readiness import ProjectReadinessPage
from p2p_engine.core.project_readiness_convergence import (
    ProjectQuestionReconciliationPreview,
    ProjectReadinessConvergencePreview,
    ProjectReadinessConvergenceResult,
)
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionApplyResult,
    ProposalDecisionEventType,
    ProposalDecisionHistoryPage,
    ProposalDecisionImpactPage,
    ProposalDecisionImpactSnapshot,
    ProposalDecisionLifecycleView,
    ProposalDecisionPreview,
    ProposalDecisionRequest,
)
from p2p_engine.core.proposal import Proposal
from p2p_engine.core.project_verticals import (
    ActiveProjectVertical,
    CustomVerticalCandidate,
    ProjectDefinitionPatchResult,
    ProjectDefinitionView,
    ProposalVerticalCoverageStatus,
    ProposalVerticalCoverageSuggestion,
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
from p2p_engine.core.workspace_schema import (
    CompatibilitySnapshot,
    MigrationAttestationTemplate,
    MigrationApplyResult,
    MigrationPlan,
    MigrationRecoveryResult,
    MigrationRecoveryStatus,
    WorkspaceSchemaStatus,
    WorkspaceSchemaPreflight,
)
from p2p_engine.core.vertical_memory import (
    DerivedUpdateResult,
    VerticalMemoryOperationResult,
    VerticalMemoryAggregate,
    VerticalMemoryPage,
    VerticalMemoryStatus,
    VerticalProjectMemoryView,
    vertical_memory_derived_updates,
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
from p2p_engine.services.lifecycle_authority import ProposalLifecycleAuthorityService
from p2p_engine.services.next_actions import NextAction, NextActionService
from p2p_engine.services.permissions import PermissionActor, PermissionsService
from p2p_engine.services.context_packets import ContextPacket, ContextPacketService
from p2p_engine.services.decision_context import ProjectDecisionContextService
from p2p_engine.services.derived_freshness import DerivedFreshnessService
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
from p2p_engine.services.proposal_decision_impact import ProposalDecisionImpactService
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
from p2p_engine.services.project_metadata import ProjectMetadataService
from p2p_engine.services.project_progress import ProjectProgressService
from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.services.project_readiness import (
    ProjectReadinessGapService,
    ProjectReadinessPaginationService,
    readiness_snapshot_from_vertical_memory,
    unmapped_proposal_ids_from_vertical_memory,
)
from p2p_engine.services.project_readiness_convergence import ProjectReadinessConvergenceService
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.vertical_lifecycle import VerticalLifecycleService
from p2p_engine.services.vertical_packages import PortableVerticalPackageService
from p2p_engine.services.project_initialization import (
    ProjectInitializationResult,
    ProjectInitializationService,
    normalize_repository_mode as _normalize_repository_mode,
)
from p2p_engine.services.project_publication import (
    PublicationCatalogResult,
    ProjectPublicationImportResult,
    ProjectPublicationPrepareResult,
    ProjectPublicationReviewResult,
    ProjectPublicationService,
    ProjectPublicationStatus,
)
from p2p_engine.services.project_publication_rendering import PublicationRenderResult
from p2p_engine.services.project_publication_validation import PublicationValidationResult
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
from p2p_engine.services.workspace_schema import WorkspaceSchemaService
from p2p_engine.services.workspace_reads import WorkspaceReadContext
from p2p_engine.services.vertical_memory import (
    VerticalProjectMemoryBuilder,
    VerticalProjectMemoryService,
)
from p2p_engine.services.workspace_compatibility import WorkspaceCompatibilityService
from p2p_engine.services.workspace_migrations import WorkspaceMigrationService
from p2p_engine.services.workspace_transactions import MigrationLockService
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
    FastFreshnessService,
    ProposalSummary,
    WorkspaceCheck,
    WorkspaceStatus,
    WorkspaceStatusService,
)
from p2p_engine.services.workspace_operation_compatibility import (
    WorkspaceOperationCompatibilityService,
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
ReadResultT = TypeVar("ReadResultT")


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
        self._decision_context_service_instance: ProjectDecisionContextService | None = None
        self._derived_freshness_service_instance: DerivedFreshnessService | None = None
        self._conflict_memory_service_instance: ConflictMemoryService | None = None
        self._governance_service_instance: GovernanceService | None = None
        self._governance_policy_service_instance: GovernancePolicyService | None = None
        self._intake_lifecycle_service_instance: IntakeLifecycleService | None = None
        self._proposal_decision_service_instance: ProposalDecisionService | None = None
        self._proposal_decision_impact_service_instance: (
            ProposalDecisionImpactService | None
        ) = None
        self._proposal_lifecycle_authority_service_instance: (
            ProposalLifecycleAuthorityService | None
        ) = None
        self._proposal_draft_commit_service_instance: ProposalDraftCommitService | None = None
        self._proposal_document_service_instance: ProposalDocumentService | None = None
        self._proposal_question_service_instance: ProposalQuestionService | None = None
        self._project_assessment_service_instance: ProjectAssessmentService | None = None
        self._project_context_renderer_service_instance: ProjectContextRendererService | None = None
        self._project_interaction_style_service_instance: ProjectInteractionStyleService | None = None
        self._project_initialization_service_instance: ProjectInitializationService | None = None
        self._project_maturity_service_instance: ProjectMaturityService | None = None
        self._project_metadata_service_instance: ProjectMetadataService | None = None
        self._project_progress_service_instance: ProjectProgressService | None = None
        self._project_question_state_service_instance: ProjectQuestionStateService | None = None
        self._project_readiness_convergence_service_instance: (
            ProjectReadinessConvergenceService | None
        ) = None
        self._project_publication_service_instance: ProjectPublicationService | None = None
        self._project_vertical_service_instance: ProjectVerticalService | None = None
        self._portable_vertical_package_service_instance: PortableVerticalPackageService | None = None
        self._vertical_lifecycle_service_instance: VerticalLifecycleService | None = None
        self._vertical_project_memory_service_instance: VerticalProjectMemoryService | None = None
        self._project_state_service_instance: ProjectStateService | None = None
        self._fast_freshness_service_instance: FastFreshnessService | None = None
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
        self._workspace_schema_service_instance: WorkspaceSchemaService | None = None
        self._workspace_compatibility_service_instance: WorkspaceCompatibilityService | None = None
        self._workspace_migration_service_instance: WorkspaceMigrationService | None = None
        self._workspace_operation_compatibility_service_instance: (
            WorkspaceOperationCompatibilityService | None
        ) = None
        self._migration_lock_service_instance: MigrationLockService | None = None

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
                workspace_schema_validation_findings=self._workspace_schema_service().validation_findings,
                proposal_lifecycle_status=(
                    self._proposal_lifecycle_authority_service().status
                ),
            )
        return self._validation_service_instance

    def _context_packet_service(self) -> ContextPacketService:
        if self._context_packet_service_instance is None:
            self._context_packet_service_instance = ContextPacketService(
                project_name=self._project_name,
                validate=self.validate,
                registry_status=(
                    lambda read_context=None: self.registry_status(
                        read_context=read_context,
                        fast=True,
                    )
                ),
                project_state_status=lambda **snapshot: self._project_state_service().status(**snapshot),
                proposal_summaries=(
                    lambda status=None, read_context=None: self.proposal_summaries(
                        status,
                        read_context=read_context,
                        prefer_registry=False,
                    )
                ),
                show_proposal=self.show_proposal,
                choice_statuses=self.choice_statuses,
                show_choice=self.show_choice,
                change_set_statuses=self.change_set_statuses,
                show_change_set=self.show_change_set,
                work_summaries=self.work_summaries,
                show_work=self.show_work,
                next_actions=self.next_actions,
                decision_context_index=self.decision_context_index,
                proposal_artifacts=self.read_proposal_artifacts,
                interaction_style=self.project_interaction_style,
                workspace_schema_status=self.workspace_schema_status,
                workspace_schema_preflight=self.workspace_schema_preflight,
                derived_freshness_status=self.project_freshness,
                fast_freshness_status=self._fast_freshness_service().status,
                vertical_memory_status=self.vertical_project_memory_status,
                vertical_memory_view=self.vertical_project_memory,
                readiness_from_vertical_memory=self._readiness_from_vertical_memory,
            )
        return self._context_packet_service_instance

    def _readiness_from_vertical_memory(
        self,
        view: VerticalProjectMemoryView,
        proposal_summaries_snapshot: tuple[ProposalSummary, ...] | list[ProposalSummary] | None = None,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> ProjectReadinessResult:
        vertical_service = self._project_vertical_service()
        schema_path = self.p2p_dir / "project" / "workspace-schema.yml"
        permissions_path = self.p2p_dir / "project" / "permissions.yml"
        schema_content = (
            read_context.documents.bytes(schema_path)
            if read_context is not None and read_context.documents.capture(schema_path).exists
            else schema_path.read_bytes()
            if schema_path.is_file()
            else None
        )
        permissions_content = (
            read_context.documents.bytes(permissions_path)
            if read_context is not None and read_context.documents.capture(permissions_path).exists
            else permissions_path.read_bytes()
            if permissions_path.is_file()
            else None
        )
        schema_version, schema_state = vertical_service._readiness_workspace_schema_identity(
            schema_content
        )
        snapshot = readiness_snapshot_from_vertical_memory(
            view,
            workspace_schema_version=schema_version,
            workspace_schema_state=schema_state,
            owner_available=vertical_service._readiness_owner_available(
                permissions_content
            ),
            unmapped_proposals=unmapped_proposal_ids_from_vertical_memory(
                view,
                (
                    item.proposal_id
                    for item in (
                        proposal_summaries_snapshot
                        if proposal_summaries_snapshot is not None
                        else self.proposal_summaries()
                    )
                ),
            ),
        )
        return ProjectReadinessGapService().classify(snapshot)

    def _decision_context_service(self) -> ProjectDecisionContextService:
        if self._decision_context_service_instance is None:
            self._decision_context_service_instance = ProjectDecisionContextService(
                root=self.root,
                p2p_dir=self.p2p_dir,
            )
        return self._decision_context_service_instance

    def _derived_freshness_service(self) -> DerivedFreshnessService:
        if self._derived_freshness_service_instance is None:
            self._derived_freshness_service_instance = DerivedFreshnessService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                registry_status=self.registry_status,
                project_state_service=self._project_state_service(),
                decision_context_index=self.decision_context_index,
                project_progress=self.project_progress,
                software_spec_statuses=self.software_spec_statuses,
                visible_export_status=self.visible_project_definition_export_status,
                publication_status=self.project_publication_status,
                vertical_memory_status=self.vertical_project_memory_status,
                vertical_memory_view=lambda: self.vertical_project_memory(
                    allow_fallback=False
                ),
            )
        return self._derived_freshness_service_instance

    def _proposal_document_service(self) -> ProposalDocumentService:
        if self._proposal_document_service_instance is None:
            self._proposal_document_service_instance = ProposalDocumentService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                lifecycle_status=(
                    lambda proposal_id: (
                        self._proposal_lifecycle_authority_service().status(
                            proposal_id
                        )
                    )
                ),
            )
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
                workspace_schema_status=self.workspace_schema_status,
                permissions=self._permissions_service(),
                readiness=self._readiness_service(),
                impact_provider=self._proposal_decision_impact_service().provider,
                lifecycle=self._proposal_lifecycle_authority_service(),
            )
        return self._proposal_decision_service_instance

    def _proposal_decision_impact_service(self) -> ProposalDecisionImpactService:
        if self._proposal_decision_impact_service_instance is None:
            self._proposal_decision_impact_service_instance = (
                ProposalDecisionImpactService(
                    root=self.root,
                    p2p_dir=self.p2p_dir,
                    find_proposal_dir=self._proposal_document_service().find_dir,
                    freshness_status=self.project_freshness,
                )
            )
        return self._proposal_decision_impact_service_instance

    def _proposal_lifecycle_authority_service(
        self,
    ) -> ProposalLifecycleAuthorityService:
        if self._proposal_lifecycle_authority_service_instance is None:
            self._proposal_lifecycle_authority_service_instance = (
                ProposalLifecycleAuthorityService(
                    root=self.root,
                    p2p_dir=self.p2p_dir,
                    find_proposal_dir=self._proposal_document_service().find_dir,
                    workspace_schema_status=self.workspace_schema_status,
                    workspace_schema_preflight=self.workspace_schema_preflight,
                )
            )
        return self._proposal_lifecycle_authority_service_instance

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
                vertical_memory=self.vertical_project_memory,
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
                proposal_summaries=(
                    lambda status=None, read_context=None: self.proposal_summaries(
                        status,
                        read_context=read_context,
                    )
                ),
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
                proposal_summaries=(
                    lambda status=None, read_context=None: self.proposal_summaries(
                        status,
                        read_context=read_context,
                    )
                ),
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

    def _project_metadata_service(self) -> ProjectMetadataService:
        if self._project_metadata_service_instance is None:
            self._project_metadata_service_instance = ProjectMetadataService(
                root=self.root,
                p2p_dir=self.p2p_dir,
            )
        return self._project_metadata_service_instance

    def _project_progress_service(self) -> ProjectProgressService:
        if self._project_progress_service_instance is None:
            self._project_progress_service_instance = ProjectProgressService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                vertical_service=self._project_vertical_service(),
                proposal_summaries=self.proposal_summaries,
                question_service=self._project_question_state_service(),
                vertical_memory_view=lambda: self.vertical_project_memory(),
            )
        return self._project_progress_service_instance

    def _project_question_state_service(self) -> ProjectQuestionStateService:
        if self._project_question_state_service_instance is None:
            self._project_question_state_service_instance = ProjectQuestionStateService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                permissions=self._permissions_service(),
            )
        return self._project_question_state_service_instance

    def _project_readiness_convergence_service(self) -> ProjectReadinessConvergenceService:
        if self._project_readiness_convergence_service_instance is None:
            self._project_readiness_convergence_service_instance = ProjectReadinessConvergenceService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                vertical_service=self._project_vertical_service(),
                question_service=self._project_question_state_service(),
                permissions=self._permissions_service(),
            )
        return self._project_readiness_convergence_service_instance

    def _project_vertical_service(self) -> ProjectVerticalService:
        if self._project_vertical_service_instance is None:
            self._project_vertical_service_instance = ProjectVerticalService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                proposal_summaries=self.proposal_summaries,
                find_proposal_dir=self._proposal_document_service().find_dir,
                vertical_memory_view=lambda: self.vertical_project_memory(),
            )
        return self._project_vertical_service_instance

    def _portable_vertical_package_service(self) -> PortableVerticalPackageService:
        if self._portable_vertical_package_service_instance is None:
            self._portable_vertical_package_service_instance = PortableVerticalPackageService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                vertical_service=self._project_vertical_service(),
            )
        return self._portable_vertical_package_service_instance

    def _vertical_lifecycle_service(self) -> VerticalLifecycleService:
        if self._vertical_lifecycle_service_instance is None:
            self._vertical_lifecycle_service_instance = VerticalLifecycleService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                vertical_service=self._project_vertical_service(),
                package_service=self._portable_vertical_package_service(),
            )
        return self._vertical_lifecycle_service_instance

    def _vertical_project_memory_service(self) -> VerticalProjectMemoryService:
        if self._vertical_project_memory_service_instance is None:
            builder = VerticalProjectMemoryBuilder(
                root=self.root,
                p2p_dir=self.p2p_dir,
                vertical_service=self._project_vertical_service(),
                question_artifact=self._project_question_state_service().read_optional,
                proposal_lifecycles=lambda context: (
                    self._proposal_lifecycle_authority_service().capture_all(
                        read_context=context
                    )
                ),
                proposal_lifecycles_for=(
                    lambda proposal_ids, context: (
                        self._proposal_lifecycle_authority_service().evaluate_many(
                            proposal_ids,
                            read_context=context,
                        )
                    )
                ),
                find_proposal_dir=self._proposal_document_service().find_dir,
            )
            self._vertical_project_memory_service_instance = VerticalProjectMemoryService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                builder=builder,
            )
        return self._vertical_project_memory_service_instance

    def _post_commit_vertical_memory(
        self,
        changed_paths: tuple[str, ...] | list[str],
        *,
        proposal_id: str = "",
        section_ids: tuple[str, ...] = (),
    ) -> dict[str, object]:
        try:
            result = self._vertical_project_memory_service().refresh_incremental(
                changed_paths,
                typed_section_ids=section_ids,
                typed_proposal_id=proposal_id,
            )
        except Exception as exc:
            result = DerivedUpdateResult(
                state="failed",
                target="vertical_project_memory",
                reason=f"Post-commit vertical-memory refresh failed: {exc}",
                affected_sections=tuple(sorted(section_ids)),
            )
        return vertical_memory_derived_updates(result)

    def _with_vertical_memory_update(
        self,
        mutation: MutationResult,
        *,
        proposal_id: str = "",
        section_ids: tuple[str, ...] = (),
    ) -> MutationResult:
        if mutation.status != "applied":
            return mutation
        derived = self._post_commit_vertical_memory(
            mutation.changed_paths,
            proposal_id=proposal_id,
            section_ids=section_ids,
        )
        return replace(
            mutation,
            derived_updates={**dict(mutation.derived_updates), **derived},
        )

    def _project_definition_patch_sections(self, patch_path: Path) -> tuple[str, ...]:
        payload = _read_yaml_mapping(patch_path, {})
        patch = payload.get("project_definition_patch")
        if not isinstance(patch, dict):
            return ()
        operations = patch.get("operations")
        if not isinstance(operations, list):
            return ()
        return tuple(
            sorted(
                {
                    str(item.get("section_id") or "")
                    for item in operations
                    if isinstance(item, dict) and str(item.get("section_id") or "")
                }
            )
        )

    def _project_question_sections(
        self,
        question_ids: list[str] | tuple[str, ...] | None = None,
    ) -> tuple[str, ...]:
        artifact = self._project_question_state_service().read_optional()
        if artifact is None:
            return ()
        selected = set(question_ids or ())
        return tuple(
            sorted(
                {
                    item.section_id
                    for item in artifact.questions
                    if item.section_id and (not selected or item.question_id in selected)
                }
            )
        )

    def _next_action_service(self) -> NextActionService:
        if self._next_action_service_instance is None:
            self._next_action_service_instance = NextActionService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                registry_status=(
                    lambda read_context=None: self.registry_status(
                        read_context=read_context,
                        fast=True,
                    )
                ),
                change_registry_records=self._registry_record_builder_service().change_records,
                intake_statuses=self.intake_statuses,
                proposal_summaries=(
                    lambda status=None, read_context=None: self.proposal_summaries(
                        status,
                        read_context=read_context,
                        prefer_registry=False,
                    )
                ),
                read_proposal_readiness=self.read_proposal_readiness,
                decision_context_index=self.decision_context_index,
                show_choice=self.show_choice,
                choice_statuses=self.choice_statuses,
                workspace_schema_status=self.workspace_schema_status,
                workspace_schema_preflight=self.workspace_schema_preflight,
                derived_freshness_status=self.project_freshness,
                fast_freshness_status=self._fast_freshness_service().status,
                project_readiness_result=self.project_readiness_result,
                proposal_decision_lifecycles=(
                    self._proposal_lifecycle_authority_service().capture_all
                ),
                proposal_decision_impact=(
                    lambda proposal_id, event_type, lifecycle, freshness: (
                        self._proposal_decision_impact_service().capture(
                            proposal_id,
                            source_head_event_id=lifecycle.head_event_id,
                            event_type=event_type,
                            freshness_status_snapshot=freshness,
                        )
                    )
                ),
                vertical_memory_status=self.vertical_project_memory_status,
                vertical_memory_view=self.vertical_project_memory,
                readiness_from_vertical_memory=self._readiness_from_vertical_memory,
            )
        return self._next_action_service_instance

    def _fast_freshness_service(self) -> FastFreshnessService:
        if self._fast_freshness_service_instance is None:
            self._fast_freshness_service_instance = FastFreshnessService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                schema_preflight=self.workspace_schema_preflight,
                registry_status=self._registry_service().fast_status,
                vertical_memory_status=self._vertical_project_memory_service().fast_status,
            )
        return self._fast_freshness_service_instance

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
                decision_context_index=self.decision_context_index,
                vertical_service=self._project_vertical_service(),
                artifact_state_service=self._proposal_artifact_state_service(),
                proposal_lifecycle_status=(
                    self._proposal_lifecycle_authority_service().status
                ),
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
                decision_context_index=self.decision_context_index,
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
                proposal_lifecycle_status=(
                    self._proposal_lifecycle_authority_service().status
                ),
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
                proposal_records_with_changes=records.proposal_records,
            )
        return self._registry_service_instance

    def _registry_record_builder_service(self) -> RegistryRecordBuilderService:
        if self._registry_record_builder_service_instance is None:
            self._registry_record_builder_service_instance = RegistryRecordBuilderService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                read_proposal_readiness=self.read_proposal_readiness,
                proposal_decision_lifecycles=(
                    self._proposal_lifecycle_authority_service().capture_all
                ),
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
                show_change_set=self.show_change_set,
                find_proposal_dir=self._proposal_document_service().find_dir,
                proposal_lifecycle_status=(
                    self._proposal_lifecycle_authority_service().status
                ),
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
                proposal_lifecycle_status=(
                    self._proposal_lifecycle_authority_service().status
                ),
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
                proposal_decision_lifecycles=(
                    self._proposal_lifecycle_authority_service().capture_all
                ),
            )
        return self._visible_project_export_service_instance

    def _project_publication_service(self) -> ProjectPublicationService:
        if self._project_publication_service_instance is None:
            self._project_publication_service_instance = ProjectPublicationService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                export_visible_project=self.export_visible_project_definition,
                accepted_proposals=self._registry_record_builder_service().accepted_proposals,
                project_vertical_lock_status=self.project_vertical_lock_status,
                project_definition_view=self.project_definition_view,
                proposal_decision_lifecycles=(
                    self._proposal_lifecycle_authority_service().capture_all
                ),
                vertical_project_memory=self.vertical_project_memory,
            )
        return self._project_publication_service_instance

    def _work_planning_service(self) -> WorkPlanningService:
        if self._work_planning_service_instance is None:
            self._work_planning_service_instance = WorkPlanningService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                export_targets=self._spec_export_service().export_targets,
                validate_export=self.validate_software_spec_export,
                find_change_dir=self._change_set_lifecycle_service().find_dir,
                scanned_work_items=self._scanned_work_items,
                proposal_lifecycle_status=(
                    self._proposal_lifecycle_authority_service().status
                ),
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
            self._workspace_status_service_instance = WorkspaceStatusService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                workspace_schema_status=self.workspace_schema_status,
                workspace_schema_preflight=self.workspace_schema_preflight,
                derived_freshness_status=self.project_freshness,
                registry_status=self.registry_status,
                fast_freshness_status=self._fast_freshness_service().status,
                proposal_decision_lifecycles=(
                    self._proposal_lifecycle_authority_service().capture_all
                ),
            )
        return self._workspace_status_service_instance

    def _workspace_schema_service(self) -> WorkspaceSchemaService:
        if self._workspace_schema_service_instance is None:
            self._workspace_schema_service_instance = WorkspaceSchemaService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                recovery_status=lambda: self._workspace_migration_service().recovery_status(),
            )
        return self._workspace_schema_service_instance

    def _workspace_operation_compatibility_service(self) -> WorkspaceOperationCompatibilityService:
        if self._workspace_operation_compatibility_service_instance is None:
            self._workspace_operation_compatibility_service_instance = (
                WorkspaceOperationCompatibilityService()
            )
        return self._workspace_operation_compatibility_service_instance

    def _migration_lock_service(self) -> MigrationLockService:
        if self._migration_lock_service_instance is None:
            self._migration_lock_service_instance = MigrationLockService(
                root=self.root,
                p2p_dir=self.p2p_dir,
            )
        return self._migration_lock_service_instance

    def _workspace_compatibility_service(self) -> WorkspaceCompatibilityService:
        if self._workspace_compatibility_service_instance is None:
            self._workspace_compatibility_service_instance = WorkspaceCompatibilityService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                schema_service=self._workspace_schema_service(),
                runtime_status=self.runtime_status,
                vertical_context=self.project_vertical_context,
                decision_context_index=self.decision_context_index,
                freshness_status=self.project_freshness,
                vertical_candidate_renderer=self._project_vertical_service().render_migration_candidate,
            )
        return self._workspace_compatibility_service_instance

    def _workspace_migration_service(self) -> WorkspaceMigrationService:
        if self._workspace_migration_service_instance is None:
            self._workspace_migration_service_instance = WorkspaceMigrationService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                compatibility=self._workspace_compatibility_service(),
                schema_service=self._workspace_schema_service(),
                lock_service=self._migration_lock_service(),
            )
        return self._workspace_migration_service_instance

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
        vertical_pack: Path | None = None,
        expected_checksum: str = "",
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
            vertical_pack=vertical_pack,
            expected_checksum=expected_checksum,
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
        vertical_pack: Path | None = None,
        expected_checksum: str = "",
    ) -> ProjectInitializationResult:
        if (self.p2p_dir / "project.yml").exists():
            self._ensure_runtime_write_allowed("project_init_existing")
        install_preview = None
        if vertical_pack is not None:
            if vertical_id:
                raise ValueError("P2P_VERTICAL_INIT_CONFLICT: use either --vertical or --vertical-pack")
            if not expected_checksum:
                raise ValueError("P2P_VERTICAL_INVALID_CHECKSUM: --expected-checksum is required with --vertical-pack")
            install_preview = self._vertical_lifecycle_service().install_preview(
                vertical_pack,
                expected_checksum=expected_checksum,
                actor=owner or "owner",
            )
            if install_preview.blockers or install_preview.preview is None:
                raise ValueError(
                    "P2P_VERTICAL_OPERATION_BLOCKED: "
                    + "; ".join(install_preview.blockers or ("install preview is not applicable",))
                )
            inspected = self._portable_vertical_package_service().inspect(vertical_pack, view="effective")
            available_profiles = {
                "default",
                *inspected.pack.profiles,
                *(item.profile_id for item in inspected.pack.profile_specs),
            }
            if profile not in available_profiles:
                raise ValueError(f"Unknown vertical profile `{profile}` for `{inspected.pack.coordinate}`.")
            available_modules = {
                *inspected.pack.modules,
                *(item.module_id for item in inspected.pack.module_specs),
            }
            unknown_modules = sorted(set(modules or []) - available_modules)
            if unknown_modules:
                raise ValueError(f"Unknown vertical module `{unknown_modules[0]}` for `{inspected.pack.coordinate}`.")
            vertical_id = inspected.pack.coordinate
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
        if install_preview is not None and install_preview.preview is not None:
            installed = self._vertical_lifecycle_service().install_apply(
                vertical_pack,
                expected_checksum=expected_checksum,
                preview_token=install_preview.preview.preview_token,
                confirmed=True,
                actor=owner or "owner",
            )
            for path in installed.mutation.changed_paths:
                candidate = Path(path)
                if candidate not in created:
                    created.append(candidate)
        if vertical_id:
            artifact_checksum = ""
            if install_preview is not None:
                artifact_checksum = str(install_preview.impact.get("artifact_checksum") or "")
            active = self._project_vertical_service().select_vertical(
                vertical_id,
                actor=owner or "owner",
                profile=profile,
                modules=modules,
                artifact_checksum=artifact_checksum,
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

    def _project_name(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> str:
        project_file = self.p2p_dir / "project.yml"
        exists = (
            read_context.documents.capture(project_file).exists
            if read_context is not None
            else project_file.exists()
        )
        if not exists:
            return self.root.name
        data = (
            read_context.documents.yaml(project_file)
            if read_context is not None
            else _read_yaml_mapping(project_file, default={})
        )
        if not isinstance(data, Mapping):
            return self.root.name
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

    def status(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> WorkspaceStatus:
        if read_context is None:
            return self.read_consistently(
                lambda context: self._workspace_status_service().status(
                    read_context=context
                ),
                allow_existing_migration_lock=True,
            )
        return self._workspace_status_service().status(read_context=read_context)

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

    def proposal_summaries(
        self,
        status: str | None = None,
        *,
        read_context: WorkspaceReadContext | None = None,
        prefer_registry: bool = True,
    ) -> list[ProposalSummary]:
        if read_context is None:
            return self.read_consistently(
                lambda context: self._workspace_status_service().proposal_summaries(
                    status,
                    read_context=context,
                    prefer_registry=prefer_registry,
                )
            )
        return self._workspace_status_service().proposal_summaries(
            status,
            read_context=read_context,
            prefer_registry=prefer_registry,
        )

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

    def validate(self, *, registry_status_snapshot=None) -> ValidationResult:
        return self._validation_service().validate(
            registry_status_snapshot=registry_status_snapshot
        )

    def runtime_status(self) -> RuntimeStatus:
        return self._runtime_contract_service().status()

    def workspace_schema_status(self) -> WorkspaceSchemaStatus:
        return self._workspace_schema_service().status()

    def workspace_schema_preflight(self) -> WorkspaceSchemaPreflight:
        return self._workspace_schema_service().preflight()

    def read_context(
        self,
        *,
        allow_existing_migration_lock: bool = False,
    ) -> WorkspaceReadContext:
        return WorkspaceReadContext(
            self.root,
            allow_existing_migration_lock=allow_existing_migration_lock,
        )

    def read_consistently(
        self,
        operation: Callable[[WorkspaceReadContext], ReadResultT],
        *,
        allow_existing_migration_lock: bool = False,
    ) -> ReadResultT:
        last_changed: tuple[str, ...] = ()
        for _attempt in range(2):
            context = self.read_context(
                allow_existing_migration_lock=allow_existing_migration_lock,
            )
            value = operation(context)
            consistency = context.finalize()
            if consistency.current:
                return value
            last_changed = tuple(
                sorted(
                    set(consistency.changed_paths)
                    | set(consistency.changed_directories)
                )
            )
        detail = ", ".join(last_changed) or "workspace sources"
        raise ValueError(
            "P2P_READ_CONCURRENT_CHANGE: workspace changed during two consecutive "
            f"read attempts: {detail}"
        )

    def workspace_compatibility_snapshot(self) -> CompatibilitySnapshot:
        return self._workspace_compatibility_service().snapshot()

    def workspace_migration_plan(
        self,
        target_version: int = 1,
        owner_inputs: dict[str, object] | None = None,
    ) -> MigrationPlan:
        return self._workspace_compatibility_service().plan(target_version, owner_inputs)

    def workspace_migration_attestation_template(
        self,
        *,
        target_version: int,
        owner_id: str,
    ) -> MigrationAttestationTemplate:
        return (
            self._workspace_compatibility_service()
            .proposal_decision_attestation_template(
                target_version=target_version,
                owner_id=owner_id,
            )
        )

    def workspace_migration_apply(
        self,
        *,
        target_version: int,
        owner_inputs: dict[str, object] | None,
        plan_fingerprint: str,
        actor: str,
        confirm: bool,
    ) -> MigrationApplyResult:
        return self._workspace_migration_service().apply(
            target_version=target_version,
            owner_inputs=owner_inputs,
            plan_fingerprint=plan_fingerprint,
            actor=actor,
            confirm=confirm,
        )

    def workspace_migration_recovery_status(self) -> MigrationRecoveryStatus:
        return self._workspace_migration_service().recovery_status()

    def workspace_migration_rollback(
        self,
        *,
        transaction_id: str,
        actor: str,
        confirm: bool,
    ) -> MigrationRecoveryResult:
        return self._workspace_migration_service().rollback(
            transaction_id=transaction_id,
            actor=actor,
            confirm=confirm,
        )

    def workspace_migration_resume(
        self,
        *,
        transaction_id: str,
        actor: str,
        confirm: bool,
    ) -> MigrationRecoveryResult:
        return self._workspace_migration_service().resume(
            transaction_id=transaction_id,
            actor=actor,
            confirm=confirm,
        )

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
        # Updating an incompatible contract is the recovery path, so the current
        # contract cannot gate this operation. The migration lock still must.
        self._migration_lock_service().require_write_available("runtime_contract_update")
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
        self._migration_lock_service().require_write_available("runtime_contract_adopt")
        return self._runtime_contract_service().adopt_contract(
            requires=requires,
            recommended=recommended,
            confirm=confirm,
            actor=actor,
        )

    def _ensure_runtime_write_allowed(self, operation: str) -> RuntimeWritePreflight:
        self._migration_lock_service().require_write_available(operation)
        if not self.p2p_dir.exists() or not (self.p2p_dir / "project.yml").exists():
            return self._runtime_contract_service().write_preflight(operation)
        preflight = self._runtime_contract_service().write_preflight(operation)
        preflight.require_allowed()
        self._workspace_operation_compatibility_service().check(
            operation,
            self._workspace_schema_service().status(),
        ).require_allowed()
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
        *,
        decided_on: str = "",
        operation_key: str = "",
        source_head_event_id: str | None = None,
        preview_token: str = "",
        confirm: bool = False,
        readiness_override: bool = False,
    ) -> ProposalDecisionPreview | ProposalDecisionApplyResult:
        if preview_token:
            self._ensure_runtime_write_allowed("proposal_decision_record")
        result = self._proposal_decision_service().record(
            proposal_id,
            outcome,
            reason,
            approver,
            decided_on=decided_on,
            operation_key_value=operation_key,
            source_head_event_id=source_head_event_id,
            preview_token=preview_token,
            confirm=confirm,
            readiness_override=readiness_override,
        )
        if not isinstance(result, ProposalDecisionApplyResult) or result.mutation is None:
            return result
        return replace(
            result,
            mutation=self._with_vertical_memory_update(
                result.mutation,
                proposal_id=proposal_id,
            ),
        )

    def proposal_decision_status(
        self,
        proposal_id: str,
    ) -> ProposalDecisionLifecycleView:
        return self._proposal_decision_service().status(proposal_id)

    def proposal_decision_lifecycles(
        self,
        *,
        strict: bool = False,
    ) -> dict[str, ProposalDecisionLifecycleView]:
        return self._proposal_lifecycle_authority_service().capture_all(
            strict=strict
        )

    def proposal_decision_history(
        self,
        proposal_id: str,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> ProposalDecisionHistoryPage:
        return self._proposal_decision_service().history(
            proposal_id,
            limit=limit,
            cursor=cursor,
        )

    def proposal_decision_impact(
        self,
        proposal_id: str,
        *,
        event_type: ProposalDecisionEventType,
        source_head_event_id: str | None = None,
    ) -> ProposalDecisionImpactSnapshot:
        lifecycle = self.proposal_decision_status(proposal_id)
        selected_head = (
            lifecycle.head_event_id
            if source_head_event_id is None
            else source_head_event_id
        )
        if selected_head != lifecycle.head_event_id:
            raise ValueError(
                "P2P365_DECISION_STALE_PREVIEW: impact source head does not "
                "match the current lifecycle head"
            )
        return self._proposal_decision_impact_service().capture(
            proposal_id,
            source_head_event_id=selected_head,
            event_type=event_type,
        )

    def proposal_decision_impact_page(
        self,
        snapshot: ProposalDecisionImpactSnapshot,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> ProposalDecisionImpactPage:
        return self._proposal_decision_impact_service().page(
            snapshot,
            limit=limit,
            cursor=cursor,
        )

    def preview_proposal_decision(
        self,
        request: ProposalDecisionRequest,
    ) -> ProposalDecisionPreview:
        return self._proposal_decision_service().preview(request)

    def apply_proposal_decision(
        self,
        request: ProposalDecisionRequest,
        *,
        preview_token: str,
        confirm: bool,
    ) -> ProposalDecisionApplyResult:
        self._ensure_runtime_write_allowed("proposal_decision_apply")
        result = self._proposal_decision_service().apply(
            request,
            preview_token=preview_token,
            confirm=confirm,
        )
        if result.mutation is None:
            return result
        return replace(
            result,
            mutation=self._with_vertical_memory_update(
                result.mutation,
                proposal_id=request.proposal_id,
            ),
        )

    def preview_proposal_decision_projection_repair(
        self,
        proposal_id: str,
        *,
        actor_id: str,
        executor_actor_id: str | None = None,
    ):
        return self._proposal_decision_service().projection_repair_preview(
            proposal_id,
            actor_id=actor_id,
            executor_actor_id=executor_actor_id,
        )

    def apply_proposal_decision_projection_repair(
        self,
        proposal_id: str,
        *,
        actor_id: str,
        executor_actor_id: str | None = None,
        preview_token: str,
        confirm: bool,
    ):
        self._ensure_runtime_write_allowed("proposal_decision_projection_repair")
        return self._proposal_decision_service().projection_repair_apply(
            proposal_id,
            actor_id=actor_id,
            executor_actor_id=executor_actor_id,
            preview_token=preview_token,
            confirm=confirm,
        )

    def preview_proposal_decision_ledger_repair(
        self,
        proposal_id: str,
        *,
        candidate_path: Path,
        actor_id: str,
        executor_actor_id: str | None = None,
    ):
        return self._proposal_decision_service().ledger_repair_preview(
            proposal_id,
            candidate_path=candidate_path,
            actor_id=actor_id,
            executor_actor_id=executor_actor_id,
        )

    def apply_proposal_decision_ledger_repair(
        self,
        proposal_id: str,
        *,
        candidate_path: Path,
        actor_id: str,
        executor_actor_id: str | None = None,
        preview_token: str,
        confirm: bool,
    ):
        self._ensure_runtime_write_allowed("proposal_decision_ledger_repair")
        return self._proposal_decision_service().ledger_repair_apply(
            proposal_id,
            candidate_path=candidate_path,
            actor_id=actor_id,
            executor_actor_id=executor_actor_id,
            preview_token=preview_token,
            confirm=confirm,
        )

    def preview_proposal_decision_legacy_resolution(
        self,
        request: ProposalDecisionRequest,
    ) -> ProposalDecisionPreview:
        return self._proposal_decision_service().legacy_resolution_preview(request)

    def apply_proposal_decision_legacy_resolution(
        self,
        request: ProposalDecisionRequest,
        *,
        preview_token: str,
        confirm: bool,
    ) -> ProposalDecisionApplyResult:
        self._ensure_runtime_write_allowed("proposal_decision_legacy_resolution")
        return self._proposal_decision_service().legacy_resolution_apply(
            request,
            preview_token=preview_token,
            confirm=confirm,
        )

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

    def preview_proposal_impact(
        self,
        proposal_id: str,
        artifacts: dict[str, str],
        *,
        actor: str,
    ) -> MutationPreview:
        return self._proposal_artifact_service().preview_impact(
            proposal_id,
            artifacts,
            actor=actor,
        )

    def apply_proposal_impact(
        self,
        proposal_id: str,
        artifacts: dict[str, str],
        *,
        preview_token: str,
        actor: str,
        confirm: bool,
    ) -> MutationResult:
        self._ensure_runtime_write_allowed("proposal_impact_apply")
        return self._proposal_artifact_service().apply_impact(
            proposal_id,
            artifacts,
            preview_token=preview_token,
            actor=actor,
            confirm=confirm,
        )

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
        memory = self._vertical_project_memory_service().refresh()
        projected = self._project_state_service().refresh()
        return [*(Path(path) for path in memory.changed_paths), *projected]

    def refresh_vertical_project_memory(self) -> VerticalMemoryOperationResult:
        self._ensure_runtime_write_allowed("project_state_refresh")
        return self._vertical_project_memory_service().refresh()

    def vertical_project_memory_status(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> VerticalMemoryStatus:
        return self._vertical_project_memory_service().status(
            read_context=read_context
        )

    def vertical_project_memory(
        self,
        *,
        allow_fallback: bool = True,
        allow_stale: bool = False,
        read_context: WorkspaceReadContext | None = None,
    ) -> VerticalProjectMemoryView:
        return self._vertical_project_memory_service().view(
            allow_fallback=allow_fallback,
            allow_stale=allow_stale,
            read_context=read_context,
        )

    def show_vertical_project_memory(
        self,
        *,
        section_id: str | None = None,
        include_history: bool = False,
        limit: int = 20,
        cursor: str = "",
    ) -> VerticalMemoryAggregate | VerticalMemoryPage:
        return self._vertical_project_memory_service().show(
            section_id=section_id,
            include_history=include_history,
            limit=limit,
            cursor=cursor,
        )

    def project_state_status(
        self,
        *,
        accepted_proposals_count: int | None = None,
        next_actions_snapshot: list[object] | None = None,
    ) -> ProjectStateStatus:
        return self._project_state_service().status(
            accepted_proposals_count=accepted_proposals_count,
            next_actions_snapshot=next_actions_snapshot,
        )

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

    def prepare_project_publication(
        self,
        *,
        language: str = "en",
        output_name: str = "project",
        contributions: str = "auto",
    ) -> ProjectPublicationPrepareResult:
        self._ensure_runtime_write_allowed("project_publication_prepare")
        return self._project_publication_service().prepare(
            language=language,
            output_name=output_name,
            contributions=contributions,
        )

    def import_project_publication(
        self,
        source: Path | None = None,
        *,
        model: Path | None = None,
        evidence_accounting: Path | None = None,
        language: str = "en",
        output_name: str = "project",
    ) -> ProjectPublicationImportResult:
        self._ensure_runtime_write_allowed("project_publication_import")
        return self._project_publication_service().import_curated(
            source,
            model=model,
            evidence_accounting=evidence_accounting,
            language=language,
            output_name=output_name,
        )

    def validate_project_publication(
        self,
        *,
        language: str = "en",
        output_name: str = "project",
    ) -> PublicationValidationResult:
        self._ensure_runtime_write_allowed("project_publication_validate")
        return self._project_publication_service().validate(
            language=language,
            output_name=output_name,
        )

    def render_project_publication(
        self,
        *,
        language: str = "en",
        output_name: str = "project",
    ) -> PublicationRenderResult:
        self._ensure_runtime_write_allowed("project_publication_render")
        return self._project_publication_service().render(
            language=language,
            output_name=output_name,
        )

    def review_project_publication(
        self,
        *,
        status: str,
        reviewer: str = "owner",
        notes: list[str] | None = None,
        language: str = "en",
        output_name: str = "project",
    ) -> ProjectPublicationReviewResult:
        self._ensure_runtime_write_allowed("project_publication_review")
        return self._project_publication_service().review(
            status=status,
            reviewer=reviewer,
            notes=notes,
            language=language,
            output_name=output_name,
        )

    def project_publication_status(
        self,
        *,
        language: str = "en",
        output_name: str = "project",
    ) -> ProjectPublicationStatus:
        return self._project_publication_service().status(
            language=language,
            output_name=output_name,
        )

    def project_publication_editions(self) -> PublicationCatalogResult:
        return self._project_publication_service().list_editions()

    def project_verticals(self) -> list[VerticalListItem]:
        return self._project_vertical_service().list_verticals()

    def show_project_vertical(self, vertical_id: str) -> VerticalPack:
        return self._project_vertical_service().show_vertical(vertical_id)

    def validate_project_vertical(self, target: str) -> VerticalValidationResult:
        return self._project_vertical_service().validate_vertical(target)

    def portable_vertical_schema(self) -> dict[str, object]:
        return self._portable_vertical_package_service().authoring_schema()

    def scaffold_portable_vertical(
        self,
        target: Path,
        *,
        publisher: str,
        vertical_id: str,
        version: str,
        name: str,
        license_id: str,
        extends: str = "",
    ) -> PortableVerticalInspection:
        return self._portable_vertical_package_service().scaffold(
            target,
            publisher=publisher,
            vertical_id=vertical_id,
            version=version,
            name=name,
            license_id=license_id,
            extends=extends,
        )

    def inspect_portable_vertical(self, target: Path, *, view: str = "effective") -> PortableVerticalInspection:
        return self._portable_vertical_package_service().inspect(target, view=view)

    def validate_portable_vertical(self, target: Path) -> PortableVerticalInspection:
        return self._portable_vertical_package_service().validate(target)

    def package_portable_vertical(self, source: Path, *, output: Path) -> PortableVerticalPackageResult:
        return self._portable_vertical_package_service().package(source, output=output)

    def preview_portable_vertical_install(
        self,
        artifact: Path,
        *,
        expected_checksum: str,
        actor: str = "local",
    ) -> VerticalLifecyclePreview:
        return self._vertical_lifecycle_service().install_preview(
            artifact,
            expected_checksum=expected_checksum,
            actor=actor,
        )

    def apply_portable_vertical_install(
        self,
        artifact: Path,
        *,
        expected_checksum: str,
        preview_token: str,
        confirmed: bool,
        actor: str,
    ) -> VerticalLifecycleResult:
        self._ensure_runtime_write_allowed("project_vertical_install")
        return self._vertical_lifecycle_service().install_apply(
            artifact,
            expected_checksum=expected_checksum,
            preview_token=preview_token,
            confirmed=confirmed,
            actor=actor,
        )

    def preview_project_vertical_adoption(
        self,
        reference: str,
        *,
        actor: str = "local",
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecyclePreview:
        return self._vertical_lifecycle_service().adopt_preview(
            reference,
            actor=actor,
            profile=profile,
            modules=modules,
        )

    def apply_project_vertical_adoption(
        self,
        reference: str,
        *,
        preview_token: str,
        confirmed: bool,
        actor: str,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecycleResult:
        self._ensure_runtime_write_allowed("project_vertical_adopt")
        result = self._vertical_lifecycle_service().adopt_apply(
            reference,
            preview_token=preview_token,
            confirmed=confirmed,
            actor=actor,
            profile=profile,
            modules=modules,
        )
        self._post_commit_vertical_memory(result.mutation.changed_paths)
        return result

    def preview_project_vertical_migration(
        self,
        reference: str,
        *,
        actor: str = "local",
        mapping: Mapping[str, object] | None = None,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecyclePreview:
        return self._vertical_lifecycle_service().migrate_preview(
            reference,
            actor=actor,
            mapping=mapping,
            profile=profile,
            modules=modules,
        )

    def apply_project_vertical_migration(
        self,
        reference: str,
        *,
        preview_token: str,
        confirmed: bool,
        actor: str,
        mapping: Mapping[str, object] | None = None,
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> VerticalLifecycleResult:
        self._ensure_runtime_write_allowed("project_vertical_migrate")
        result = self._vertical_lifecycle_service().migrate_apply(
            reference,
            preview_token=preview_token,
            confirmed=confirmed,
            actor=actor,
            mapping=mapping,
            profile=profile,
            modules=modules,
        )
        self._post_commit_vertical_memory(result.mutation.changed_paths)
        return result

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
        artifact_checksum = ""
        resolved = self._project_vertical_service().resolve_pack(vertical_id)
        if resolved.pack.schema_version >= 2 and resolved.pack.path is not None:
            pack_root = resolved.pack.path.parent
            entries = self._portable_vertical_package_service().canonical_entries(pack_root)
            artifact_checksum = hashlib.sha256(
                self._portable_vertical_package_service().archive_bytes(entries)
            ).hexdigest()
        result = self._project_vertical_service().select_vertical(
            vertical_id,
            actor=actor,
            profile=profile,
            modules=modules,
            artifact_checksum=artifact_checksum,
        )
        derived = self._post_commit_vertical_memory(
            [
                ".p2p/project/vertical.yml",
                ".p2p/project/vertical.lock.yml",
                ".p2p/project/definition.yml",
                ".p2p/project/questions.yml",
            ]
        )
        return replace(result, derived_updates=derived)

    def active_project_vertical(self) -> ActiveProjectVertical:
        return self._project_vertical_service().active_vertical()

    def review_project_readiness(self, vertical_id: str | None = None) -> ProjectReadinessReview:
        return self._project_vertical_service().project_readiness_review(vertical_id=vertical_id)

    def project_readiness_result(self, vertical_id: str | None = None) -> ProjectReadinessResult:
        return self._project_vertical_service().project_readiness_result(vertical_id=vertical_id)

    def project_readiness_snapshot(self, vertical_id: str | None = None) -> ProjectReadinessSnapshot:
        return self._project_vertical_service().project_readiness_snapshot(vertical_id=vertical_id)

    def project_questions(self) -> ProjectQuestionArtifact:
        self._workspace_operation_compatibility_service().check(
            "project_questions_answer",
            self.workspace_schema_status(),
        ).require_allowed()
        return self._project_question_state_service().read()

    def project_question(self, question_id: str) -> ProjectQuestion:
        self._workspace_operation_compatibility_service().check(
            "project_questions_answer",
            self.workspace_schema_status(),
        ).require_allowed()
        return self._project_question_state_service().question(question_id)

    def project_questions_page(
        self,
        *,
        state: str = "",
        limit: int = 20,
        cursor: str = "",
    ) -> ProjectReadinessPage:
        self._workspace_operation_compatibility_service().check(
            "project_questions_answer",
            self.workspace_schema_status(),
        ).require_allowed()
        return self._project_question_state_service().page(
            state=state,
            limit=limit,
            cursor=cursor,
        )

    def project_readiness_gaps(
        self,
        *,
        kind: str = "",
        severity: str = "",
        limit: int = 20,
        cursor: str = "",
    ) -> ProjectReadinessPage:
        result = self.project_readiness_result()
        return ProjectReadinessPaginationService().page_gaps(
            result,
            limit=limit,
            cursor=cursor,
            predicate=lambda item: (
                (not kind or item.kind.value == kind)
                and (not severity or item.severity.value == severity)
            ),
        )

    def project_readiness_gap(self, gap_id: str):
        result = self.project_readiness_result()
        gap = next((item for item in result.gaps if item.gap_id == gap_id), None)
        if gap is None:
            raise ValueError(f"Project readiness gap not found: {gap_id}")
        return gap

    def next_project_question(self) -> ProjectQuestion | None:
        self._workspace_operation_compatibility_service().check(
            "project_questions_answer",
            self.workspace_schema_status(),
        ).require_allowed()
        return self._project_question_state_service().next_question()

    def answer_project_question(
        self,
        question_id: str,
        *,
        values: dict[str, object],
        actor: str,
        expected_revision: int,
        replace_answer: bool = False,
        evidence_refs: tuple[str, ...] = (),
    ) -> ProjectQuestionOperationResult:
        self._ensure_runtime_write_allowed("project_questions_answer")
        result = self._project_question_state_service().answer(
            question_id,
            values=values,
            actor=actor,
            expected_revision=expected_revision,
            replace_answer=replace_answer,
            evidence_refs=evidence_refs,
        )
        sections = (result.question.section_id,) if result.question is not None else ()
        return replace(
            result,
            mutation=self._with_vertical_memory_update(
                result.mutation,
                section_ids=sections,
            ),
        )

    def defer_project_question(
        self,
        question_id: str,
        *,
        actor: str,
        expected_revision: int,
        reason: str,
    ) -> ProjectQuestionOperationResult:
        self._ensure_runtime_write_allowed("project_questions_defer")
        result = self._project_question_state_service().defer(
            question_id,
            actor=actor,
            expected_revision=expected_revision,
            reason=reason,
        )
        sections = (result.question.section_id,) if result.question is not None else ()
        return replace(
            result,
            mutation=self._with_vertical_memory_update(
                result.mutation,
                section_ids=sections,
            ),
        )

    def mute_project_question(
        self,
        question_id: str,
        *,
        actor: str,
        expected_revision: int,
        reason: str,
    ) -> ProjectQuestionOperationResult:
        self._ensure_runtime_write_allowed("project_questions_mute")
        result = self._project_question_state_service().mute(
            question_id,
            actor=actor,
            expected_revision=expected_revision,
            reason=reason,
        )
        sections = (result.question.section_id,) if result.question is not None else ()
        return replace(
            result,
            mutation=self._with_vertical_memory_update(
                result.mutation,
                section_ids=sections,
            ),
        )

    def reopen_project_question(
        self,
        question_id: str,
        *,
        actor: str,
        expected_revision: int,
        reason: str,
    ) -> ProjectQuestionOperationResult:
        self._ensure_runtime_write_allowed("project_questions_reopen")
        result = self._project_question_state_service().reopen(
            question_id,
            actor=actor,
            expected_revision=expected_revision,
            reason=reason,
        )
        sections = (result.question.section_id,) if result.question is not None else ()
        return replace(
            result,
            mutation=self._with_vertical_memory_update(
                result.mutation,
                section_ids=sections,
            ),
        )

    def refresh_project_question_triggers(self, *, actor: str = "system") -> MutationResult:
        self._ensure_runtime_write_allowed("project_questions_trigger_reopen")
        view = self.project_definition_view()
        if not view.valid or view.state is None:
            raise ValueError("Project definition must be valid before evaluating deferred triggers.")
        result = self._project_question_state_service().reopen_deferred_triggers(
            view.state,
            actor=actor,
        )
        return self._with_vertical_memory_update(
            result,
            section_ids=self._project_question_sections(),
        )

    def preview_project_readiness_convergence(
        self,
        question_ids: list[str],
        *,
        actor: str,
    ) -> ProjectReadinessConvergencePreview:
        self._workspace_operation_compatibility_service().check(
            "project_readiness_convergence_apply",
            self.workspace_schema_status(),
        ).require_allowed()
        return self._project_readiness_convergence_service().preview(question_ids, actor=actor)

    def apply_project_readiness_convergence(
        self,
        question_ids: list[str],
        *,
        actor: str,
        preview_token: str,
        confirm: bool,
    ) -> ProjectReadinessConvergenceResult:
        self._ensure_runtime_write_allowed("project_readiness_convergence_apply")
        sections = self._project_question_sections(tuple(question_ids))
        result = self._project_readiness_convergence_service().apply(
            question_ids,
            actor=actor,
            preview_token=preview_token,
            confirm=confirm,
        )
        return replace(
            result,
            mutation=self._with_vertical_memory_update(
                result.mutation,
                section_ids=sections,
            ),
        )

    def preview_project_question_reconciliation(
        self,
        *,
        actor: str,
    ) -> ProjectQuestionReconciliationPreview:
        self._workspace_operation_compatibility_service().check(
            "project_questions_reconcile_apply",
            self.workspace_schema_status(),
        ).require_allowed()
        return self._project_readiness_convergence_service().reconciliation_preview(actor=actor)

    def apply_project_question_reconciliation(
        self,
        *,
        actor: str,
        preview_token: str,
        confirm: bool,
    ) -> ProjectReadinessConvergenceResult:
        self._ensure_runtime_write_allowed("project_questions_reconcile_apply")
        sections = self._project_question_sections()
        result = self._project_readiness_convergence_service().reconciliation_apply(
            actor=actor,
            preview_token=preview_token,
            confirm=confirm,
        )
        return replace(
            result,
            mutation=self._with_vertical_memory_update(
                result.mutation,
                section_ids=sections,
            ),
        )

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

    def proposal_vertical_coverage_status(self, proposal_id: str) -> ProposalVerticalCoverageStatus:
        return self._project_vertical_service().proposal_vertical_coverage_status(proposal_id)

    def suggest_proposal_vertical_coverage(self, proposal_id: str) -> ProposalVerticalCoverageSuggestion:
        return self._project_vertical_service().suggest_proposal_vertical_coverage(proposal_id)

    def preview_proposal_vertical_coverage(
        self,
        proposal_id: str,
        payload: dict[str, object],
        *,
        actor: str,
    ) -> MutationPreview:
        return self._proposal_artifact_service().preview_vertical_coverage(proposal_id, payload, actor=actor)

    def apply_proposal_vertical_coverage(
        self,
        proposal_id: str,
        payload: dict[str, object],
        *,
        preview_token: str,
        actor: str,
        confirm: bool,
    ) -> MutationResult:
        self._ensure_runtime_write_allowed("proposal_vertical_coverage_apply")
        result = self._proposal_artifact_service().apply_vertical_coverage(
            proposal_id,
            payload,
            preview_token=preview_token,
            actor=actor,
            confirm=confirm,
        )
        return self._with_vertical_memory_update(
            result,
            proposal_id=proposal_id,
        )

    def project_metadata_view(self) -> ProjectMetadataView:
        return self._project_metadata_service().show()

    def project_progress(
        self,
        *,
        proposal_summaries_snapshot: list[ProposalSummary] | None = None,
        include_heuristics: bool = False,
        vertical_memory_snapshot: VerticalProjectMemoryView | None = None,
        read_context: WorkspaceReadContext | None = None,
    ) -> ProjectProgress:
        if (
            read_context is None
            and proposal_summaries_snapshot is None
            and vertical_memory_snapshot is None
            and not include_heuristics
        ):
            return self.read_consistently(
                lambda context: self._project_progress_service().status(
                    vertical_memory_snapshot=context.provide(
                        "vertical_memory",
                        (True, False),
                        lambda: self.vertical_project_memory(read_context=context),
                    )
                )
            )
        if vertical_memory_snapshot is None and read_context is not None and not include_heuristics:
            vertical_memory_snapshot = read_context.provide(
                "vertical_memory",
                (True, False),
                lambda: self.vertical_project_memory(read_context=read_context),
            )
        return self._project_progress_service().status(
            proposal_summaries_snapshot=proposal_summaries_snapshot,
            include_heuristics=include_heuristics,
            vertical_memory_snapshot=vertical_memory_snapshot,
        )

    def project_freshness(
        self,
        *,
        registry_status_snapshot: object | None = None,
        decision_context_index_snapshot: object | None = None,
        proposal_summaries_snapshot: list[ProposalSummary] | None = None,
    ) -> DerivedFreshnessStatus:
        return self._derived_freshness_service().status(
            registry_status_snapshot=registry_status_snapshot,
            decision_context_index_snapshot=decision_context_index_snapshot,
            proposal_summaries_snapshot=proposal_summaries_snapshot,
        )

    def preview_project_metadata_update(self, patch_path: Path, *, actor: str) -> MutationPreview:
        return self._project_metadata_service().preview(patch_path, actor=actor)

    def apply_project_metadata_update(
        self,
        patch_path: Path,
        *,
        preview_token: str,
        actor: str,
        confirm: bool,
    ) -> MutationResult:
        self._ensure_runtime_write_allowed("project_metadata_apply")
        return self._project_metadata_service().apply(
            patch_path,
            preview_token=preview_token,
            actor=actor,
            confirm=confirm,
        )

    def update_project_definition(self, patch_path: Path) -> ProjectDefinitionPatchResult:
        self._ensure_runtime_write_allowed("project_definition_update")
        sections = self._project_definition_patch_sections(patch_path)
        result = self._project_vertical_service().apply_definition_patch(patch_path)
        derived = self._post_commit_vertical_memory(
            [".p2p/project/definition.yml"],
            section_ids=sections,
        )
        return replace(result, derived_updates=derived)

    def preview_project_definition_update(self, patch_path: Path, *, actor: str) -> MutationPreview:
        return self._project_vertical_service().preview_definition_patch(patch_path, actor=actor)

    def apply_project_definition_update(
        self,
        patch_path: Path,
        *,
        preview_token: str,
        actor: str,
        confirm: bool,
    ) -> MutationResult:
        self._ensure_runtime_write_allowed("project_definition_apply")
        sections = self._project_definition_patch_sections(patch_path)
        result = self._project_vertical_service().apply_definition_patch_previewed(
            patch_path,
            preview_token=preview_token,
            actor=actor,
            confirm=confirm,
        )
        return self._with_vertical_memory_update(
            result,
            section_ids=sections,
        )

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

    def context_packet(
        self,
        budget: str = "small",
        target: str | None = None,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> ContextPacket:
        if read_context is None:
            return self.read_consistently(
                lambda context: self._context_packet_service().context_packet(
                    budget,
                    target,
                    read_context=context,
                ),
                allow_existing_migration_lock=True,
            )
        return self._context_packet_service().context_packet(
            budget,
            target,
            read_context=read_context,
        )

    def decision_context_index(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> DecisionContextIndex:
        return self._decision_context_service().build_index(
            read_context=read_context
        )

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

    def next_actions(
        self,
        limit: int | None = None,
        *,
        context_snapshot: dict[str, object] | None = None,
        read_context: WorkspaceReadContext | None = None,
    ) -> list[NextAction]:
        if read_context is None and context_snapshot is None:
            return self.read_consistently(
                lambda context: self._next_action_service().list(
                    limit=limit,
                    read_context=context,
                ),
                allow_existing_migration_lock=True,
            )
        return self._next_action_service().list(
            limit=limit,
            context_snapshot=context_snapshot,
            read_context=read_context,
        )

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

    def conflict_show(self, conflict_id: str) -> dict[str, object]:
        return self._conflict_memory_service().show(conflict_id)

    def preview_conflict_update(
        self,
        conflict_id: str,
        patch: dict[str, object],
        *,
        actor: str,
    ) -> MutationPreview:
        return self._conflict_memory_service().preview_update(conflict_id, patch, actor=actor)

    def update_conflict(
        self,
        conflict_id: str,
        patch: dict[str, object],
        *,
        preview_token: str,
        actor: str,
        confirm: bool,
    ) -> MutationResult:
        self._ensure_runtime_write_allowed("conflict_update")
        return self._conflict_memory_service().update(
            conflict_id,
            patch,
            preview_token=preview_token,
            actor=actor,
            confirm=confirm,
        )

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

    def registry_status(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
        fast: bool = False,
    ) -> RegistryStatus:
        provider = (
            self._registry_service().fast_status
            if fast
            else self._registry_service().status
        )
        if read_context is None:
            return self.read_consistently(
                lambda context: provider(
                    read_context=context
                )
            )
        return provider(read_context=read_context)

    def show_registry(
        self,
        name: str,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> RegistryView:
        if read_context is None:
            return self.read_consistently(
                lambda context: self._registry_service().show(
                    name,
                    read_context=context,
                )
            )
        return self._registry_service().show(name, read_context=read_context)

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

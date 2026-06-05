from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import yaml

from p2p_engine.core.contribution import Contribution, ContributionType
from p2p_engine.core.decision import Decision, DecisionOutcome
from p2p_engine.core.proposal import Proposal
from p2p_engine.foundation.markdown import (
    markdown_has_section as _markdown_has_section,
    read_frontmatter as _read_frontmatter,
    read_markdown_section as _read_markdown_section,
    read_title as _read_title,
    replace_frontmatter as _replace_frontmatter,
    replace_section as _replace_section,
    strip_markdown_title as _strip_markdown_title,
)
from p2p_engine.foundation.validators import (
    validate_tasks_yaml as _validate_tasks_yaml,
    validate_yaml_key as _validate_yaml_key,
)
from p2p_engine.prompts.clarify import render_clarify_prompt
from p2p_engine.prompts.digest import render_digest_prompt
from p2p_engine.prompts.explore import render_explore_prompt
from p2p_engine.prompts.impact import render_impact_prompt
from p2p_engine.prompts.plan import render_plan_prompt
from p2p_engine.prompts.synthesize import render_synthesize_prompt
from p2p_engine.prompts.swot import render_swot_prompt
from p2p_engine.prompts.tasks import render_tasks_prompt
from p2p_engine.services.consent import ConsentService
from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.proposal_decisions import ProposalDecisionService
from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.services.project_assessment import ProjectAssessmentService
from p2p_engine.services.project_state import ProjectStateService
from p2p_engine.services.readiness import ReadinessService
from p2p_engine.services.registries import RegistryService
from p2p_engine.services.remote_profile import RemoteProfileService
from p2p_engine.services.spec_export import SpecExportService
from p2p_engine.services.software_spec import SoftwareSpecService
from p2p_engine.services.work_planning import WorkPlanningService
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

PromptKind = Literal["explore", "digest", "clarify", "synthesize", "plan", "tasks", "swot", "impact"]
ImportKind = Literal["clarify", "synthesize", "plan", "tasks"]

EXPLORATION_ARTIFACTS = (
    "exploration.md",
    "findings.md",
    "alternatives.md",
    "open-questions.md",
    "risks.md",
    "assumptions.md",
    "suggested-scope.md",
)

DEFAULT_READINESS_PROFILE_ID = "default-readiness-v0.1"
DEFAULT_READINESS_PROFILE_VERSION = "0.1"
READINESS_ARTIFACT_QUALITY_STATES = {
    "missing",
    "placeholder",
    "thin",
    "meaningful",
    "needs_owner_input",
    "ready",
}
READINESS_CONFIDENCE_LEVELS = {"low", "medium", "high"}
READINESS_TIERS = {"small", "medium", "architectural", "governance-critical"}
READINESS_LABELS = {"weak", "partial", "strong", "decision_ready"}

CHANGE_STATUS_TRANSITIONS = {
    "proposed": ["planned", "cancelled", "superseded"],
    "planned": ["implementation_ready", "blocked", "cancelled", "superseded"],
    "implementation_ready": ["in_progress", "blocked", "cancelled", "superseded"],
    "in_progress": ["in_review", "blocked", "cancelled", "superseded"],
    "blocked": ["planned", "implementation_ready", "in_progress", "cancelled", "superseded"],
    "in_review": ["completed", "in_progress", "blocked"],
    "completed": [],
    "cancelled": [],
    "superseded": [],
}


@dataclass(frozen=True)
class ProposalSummary:
    proposal_id: str
    slug: str
    status: str
    title: str = ""


@dataclass(frozen=True)
class ProposalDetail:
    proposal_id: str
    title: str
    status: str
    path: Path
    problem: str
    proposal: str
    decision_status: str
    decision_reason: str


@dataclass(frozen=True)
class ProposalBranchDetail:
    proposal_id: str
    status: str
    branch_name: str
    base_branch: str
    actor: str
    branch_hash16: str
    remote: str | None
    remote_url: str | None
    path: Path
    metadata: dict[str, object]


@dataclass(frozen=True)
class ProposalBranchScan:
    scanned_branches: list[str]
    proposals: list[dict[str, object]]
    path: Path


@dataclass(frozen=True)
class ProposalContributionList:
    proposal_id: str
    path: Path
    contributions: list[Contribution]


@dataclass(frozen=True)
class ProposalMerge:
    proposal_id: str
    branch_name: str
    base_branch: str
    merge_commit: str
    path: Path


@dataclass(frozen=True)
class ProposalMergeConflict:
    proposal_id: str
    branch_name: str
    base_branch: str
    conflicted_files: list[str]
    path: Path


@dataclass(frozen=True)
class ProposalFinalize:
    proposal_id: str
    branch_name: str
    base_branch: str
    remote: str
    remote_url: str
    finalize_commit: str
    path: Path


@dataclass(frozen=True)
class ProposalCleanup:
    proposal_id: str
    branch_name: str
    base_branch: str
    remote: str
    remote_url: str
    cleanup_commit: str
    local_deleted: bool
    remote_deleted: bool
    path: Path


@dataclass(frozen=True)
class WorkspaceStatus:
    root: Path
    project_name: str
    proposals: list[ProposalSummary]


@dataclass(frozen=True)
class ExplorationArtifactStatus:
    filename: str
    exists: bool
    has_content: bool
    quality_state: str


@dataclass(frozen=True)
class ExplorationStatus:
    proposal_id: str
    artifacts: list[ExplorationArtifactStatus]
    unresolved_questions: int
    suggested_next_command: str


@dataclass(frozen=True)
class WorkspaceCheck:
    ok: bool
    missing: list[Path]


@dataclass(frozen=True)
class ValidationFinding:
    code: str
    severity: str
    path: Path
    message: str
    suggested_command: str = ""


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: int
    warnings: int
    infos: int
    findings: list[ValidationFinding]


@dataclass(frozen=True)
class GovernanceStatus:
    mode: str
    roles_count: int
    precedents_count: int
    governance_file: Path


@dataclass(frozen=True)
class VoteStatus:
    proposal_id: str
    counts: dict[str, int]
    total_votes: int
    winner: str | None
    tied: bool


@dataclass(frozen=True)
class ProjectStateStatus:
    accepted_proposals: int
    features: list[str]
    project_dir: Path
    operational_brief_available: bool
    next_actions_count: int
    first_next_action: "NextAction | None"


@dataclass(frozen=True)
class ProjectAssessment:
    path: Path
    generated_on: str
    assessment_type: str
    completion_score: int
    completion_status: str
    confidence: str
    factors: list[dict[str, object]]
    gaps: list[str]
    suggested_actions: list[str]
    maturity_status: str
    maturity_score: int | None


@dataclass(frozen=True)
class ProjectRubrics:
    path: Path
    domain: str
    status: str
    template: str | None
    criteria: list[dict[str, object]]


@dataclass(frozen=True)
class ProjectDefinitionMaturity:
    path: Path
    generated_on: str
    domain: str
    score: int
    status: str
    criteria: list[dict[str, object]]
    gaps: list[str]
    suggested_actions: list[str]


@dataclass(frozen=True)
class ReadinessProfile:
    path: Path
    profile_id: str
    version: str
    criteria: dict[str, int]
    thresholds: dict[str, int]
    tier_requirements: dict[str, dict[str, object]]
    artifact_quality_caps: dict[str, dict[str, object]]
    gates: dict[str, object]
    override_policy: dict[str, object]


@dataclass(frozen=True)
class ProposalReadiness:
    proposal_id: str
    status: str
    path: Path
    profile_id: str | None
    profile_version: str | None
    computed_score: int | None
    computed_label: str | None
    confidence: str | None
    failed_gates: list[str]
    missing: list[str]
    suggested_next: list[str]


@dataclass(frozen=True)
class ContextPacket:
    budget: str
    target: str | None
    current_state: dict[str, object]
    next_actions: list[dict[str, object]]
    relevant_artifacts: list[dict[str, object]]
    allowed_commands: list[str]
    do_not_read: list[str]
    bounded_next_step: str
    notes: list[str]


@dataclass(frozen=True)
class NextAction:
    action_id: str
    priority: str
    kind: str
    target: str
    reason: str
    command: str
    source: str


@dataclass(frozen=True)
class ConflictStatus:
    conflicts_count: int
    conflicts: list[dict[str, object]]
    conflicts_file: Path


@dataclass(frozen=True)
class ChangeSetStatus:
    change_id: str
    title: str
    status: str
    path: Path


@dataclass(frozen=True)
class ChangeSetPolicy:
    change_id: str
    operation_level: str
    auto_commit: bool
    auto_branch: bool
    auto_tag: bool
    reasons: list[str]


@dataclass(frozen=True)
class ChangeSetDetail:
    change_id: str
    title: str
    status: str
    path: Path
    summary: str
    execution_domains: list[str]
    implementation_targets: list[str]
    spec_targets: list[str]
    export_targets: list[str]
    plan_ref: str
    tasks_ref: str


@dataclass(frozen=True)
class ChangeSetTaskView:
    change_id: str
    tasks: list[dict[str, object]]
    actions: list[dict[str, object]]


@dataclass(frozen=True)
class RegistryStatus:
    registries_dir: Path
    files: list[dict[str, object]]
    proposals_count: int
    changes_count: int
    stale: bool


@dataclass(frozen=True)
class RegistryView:
    name: str
    path: Path
    records: list[dict[str, object]]


@dataclass(frozen=True)
class ProjectBriefPrompt:
    context_path: Path
    prompt_path: Path


@dataclass(frozen=True)
class SoftwareSpecStatus:
    change_id: str
    title: str
    status: str
    path: Path


@dataclass(frozen=True)
class SoftwareSpecExportStatus:
    change_id: str
    target: str
    title: str
    status: str
    path: Path


@dataclass(frozen=True)
class SoftwareSpecExportValidation:
    change_id: str
    target: str
    path: Path
    checked: list[Path]


@dataclass(frozen=True)
class WorkStatus:
    work_id: str
    status: str
    change_id: str
    target: str
    path: Path


@dataclass(frozen=True)
class WorkDetail:
    work_id: str
    status: str
    change_id: str
    target: str
    branch_name: str
    path: Path
    manifest: dict[str, object]


@dataclass(frozen=True)
class WorkSummary:
    work_id: str
    status: str
    change_id: str
    target: str
    branch_name: str
    base_branch: str
    remote: str | None
    next_action: str
    note: str
    path: Path


@dataclass(frozen=True)
class WorkBranch:
    work_id: str
    branch_name: str
    base_branch: str
    base_commit: str
    head_commit: str
    path: Path


@dataclass(frozen=True)
class WorkRetire:
    work_id: str
    status: str
    reason: str
    path: Path


@dataclass(frozen=True)
class WorkSubmit:
    work_id: str
    branch_name: str
    commit: str
    changed_files: list[str]
    path: Path


@dataclass(frozen=True)
class WorkReview:
    work_id: str
    branch_name: str
    review_commit: str
    metadata_commit: str
    path: Path


@dataclass(frozen=True)
class RemoteProjectProfile:
    mode: str
    provider: str
    remote: str | None
    url: str | None
    review_request_mode: str
    opens_external_request: bool
    path: Path


@dataclass(frozen=True)
class SyncStatus:
    is_repository: bool
    branch: str | None
    is_clean: bool
    mode: str
    provider: str
    remote: str | None
    profile_url: str | None
    remote_url: str | None
    can_sync: bool
    reason: str


@dataclass(frozen=True)
class SyncResult:
    action: str
    status: str
    branch: str | None
    remote: str
    remote_url: str


@dataclass(frozen=True)
class ProposalDraftCommit:
    proposal_id: str
    commit: str
    changed_files: list[str]


@dataclass(frozen=True)
class WorkPublish:
    work_id: str
    branch_name: str
    remote: str
    remote_url: str
    publish_commit: str
    path: Path


@dataclass(frozen=True)
class WorkAccept:
    work_id: str
    branch_name: str
    base_branch: str
    merge_commit: str
    path: Path


@dataclass(frozen=True)
class WorkAcceptConflict:
    work_id: str
    branch_name: str
    base_branch: str
    conflicted_files: list[str]
    path: Path


@dataclass(frozen=True)
class WorkFinalize:
    work_id: str
    base_branch: str
    remote: str
    remote_url: str
    finalize_commit: str
    path: Path


@dataclass(frozen=True)
class WorkCleanup:
    work_id: str
    branch_name: str
    base_branch: str
    remote: str
    cleanup_commit: str
    local_deleted: bool
    remote_deleted: bool
    path: Path


@dataclass(frozen=True)
class WorkReviewRequest:
    work_id: str
    branch_name: str
    provider: str
    remote: str
    remote_url: str
    metadata_commit: str
    suggested_next: str
    path: Path


@dataclass(frozen=True)
class WorkScan:
    scanned_branches: list[str]
    work_items: list[dict[str, object]]
    path: Path


@dataclass(frozen=True)
class SoftwareSpecPrompt:
    change_id: str
    prompt_path: Path


@dataclass(frozen=True)
class IntakePrompt:
    intake_id: str
    path: Path
    prompt_path: Path


@dataclass(frozen=True)
class IntakeStatus:
    intake_id: str
    status: str
    path: Path
    recommendation: str


@dataclass(frozen=True)
class IntakeApplyPlan:
    intake_id: str
    path: Path
    actions: list[dict[str, object]]


@dataclass(frozen=True)
class IntakeAppliedAction:
    applied_id: str
    plan_action: str
    action_type: str
    target: str
    command: str
    path: Path


@dataclass(frozen=True)
class ChoiceStatus:
    choice_id: str
    title: str
    status: str
    path: Path
    selected_option: str | None


@dataclass(frozen=True)
class ChoiceDetail:
    choice_id: str
    title: str
    status: str
    path: Path
    selected_option: str | None
    options: list[dict[str, object]]
    related_proposals: list[dict[str, object]]
    related_changes: list[dict[str, object]]
    blocks: list[dict[str, object]]


@dataclass(frozen=True)
class ChoiceDiscoveryFinding:
    finding_id: str
    kind: str
    target: str
    severity: str
    reason: str
    suggested_command: str


@dataclass(frozen=True)
class AgentInstructionsResult:
    profile: str
    created: list[Path]
    updated: list[Path]
    policy_path: Path


@dataclass(frozen=True)
class AgentIntegrationResult:
    target: str
    created: list[Path]
    updated: list[Path]
    removed: list[Path]
    skipped: list[dict[str, object]]
    registry_path: Path


@dataclass(frozen=True)
class PermissionActor:
    actor_id: str
    role: str
    kind: str
    display_name: str
    path: Path


@dataclass(frozen=True)
class ConsentReceipt:
    consent_id: str
    operation: str
    target: str
    actor_id: str
    approved_by: str
    status: str
    single_use: bool
    expires_on: str | None
    path: Path


class P2PWorkspace:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.p2p_dir = self.root / ".p2p"
        self._permissions_service_instance: PermissionsService | None = None
        self._consent_service_instance: ConsentService | None = None
        self._proposal_decision_service_instance: ProposalDecisionService | None = None
        self._proposal_document_service_instance: ProposalDocumentService | None = None
        self._project_assessment_service_instance: ProjectAssessmentService | None = None
        self._project_state_service_instance: ProjectStateService | None = None
        self._readiness_service_instance: ReadinessService | None = None
        self._registry_service_instance: RegistryService | None = None
        self._remote_profile_service_instance: RemoteProfileService | None = None
        self._spec_export_service_instance: SpecExportService | None = None
        self._software_spec_service_instance: SoftwareSpecService | None = None
        self._work_planning_service_instance: WorkPlanningService | None = None

    def _permissions_service(self) -> PermissionsService:
        if self._permissions_service_instance is None:
            self._permissions_service_instance = PermissionsService(root=self.root, p2p_dir=self.p2p_dir)
        return self._permissions_service_instance

    def _consent_service(self) -> ConsentService:
        if self._consent_service_instance is None:
            self._consent_service_instance = ConsentService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                permissions=self._permissions_service(),
            )
        return self._consent_service_instance

    def _proposal_document_service(self) -> ProposalDocumentService:
        if self._proposal_document_service_instance is None:
            self._proposal_document_service_instance = ProposalDocumentService(root=self.root, p2p_dir=self.p2p_dir)
        return self._proposal_document_service_instance

    def _proposal_decision_service(self) -> ProposalDecisionService:
        if self._proposal_decision_service_instance is None:
            self._proposal_decision_service_instance = ProposalDecisionService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_proposal_dir=self._find_proposal_dir,
            )
        return self._proposal_decision_service_instance

    def _project_state_service(self) -> ProjectStateService:
        if self._project_state_service_instance is None:
            self._project_state_service_instance = ProjectStateService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                accepted_proposals=self._accepted_proposals,
                project_name=self._project_name,
                next_actions=self.next_actions,
                registry_status=self.registry_status,
                project_brief_context=self._project_brief_context,
                validate_yaml_key=_validate_yaml_key,
            )
        return self._project_state_service_instance

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

    def _readiness_service(self) -> ReadinessService:
        if self._readiness_service_instance is None:
            self._readiness_service_instance = ReadinessService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_proposal_dir=self._find_proposal_dir,
            )
        return self._readiness_service_instance

    def _registry_service(self) -> RegistryService:
        if self._registry_service_instance is None:
            self._registry_service_instance = RegistryService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                duplicate_proposal_ids=self._duplicate_proposal_ids,
                duplicate_message=lambda duplicates: _duplicate_proposal_ids_message(duplicates, self.root),
                proposal_records=self._proposal_registry_records,
                change_records=self._change_registry_records,
                decision_records=self._decision_registry_records,
                choice_records=self._choice_registry_records,
                relation_records=self._relation_registry_records,
                artifact_records=self._artifact_registry_records,
                readiness_records=self._readiness_registry_records,
            )
        return self._registry_service_instance

    def _remote_profile_service(self) -> RemoteProfileService:
        if self._remote_profile_service_instance is None:
            self._remote_profile_service_instance = RemoteProfileService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                remote_url_resolver=remote_url,
            )
        return self._remote_profile_service_instance

    def _software_spec_service(self) -> SoftwareSpecService:
        if self._software_spec_service_instance is None:
            self._software_spec_service_instance = SoftwareSpecService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                find_change_dir=self._find_change_dir,
                show_proposal=self.show_proposal,
                show_change_set=self.show_change_set,
                find_proposal_dir=self._find_proposal_dir,
            )
        return self._software_spec_service_instance

    def _spec_export_service(self) -> SpecExportService:
        if self._spec_export_service_instance is None:
            self._spec_export_service_instance = SpecExportService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                show_change_set=self.show_change_set,
                status=self.status,
                accepted_proposals=self._accepted_proposals,
                proposal_summaries=self.proposal_summaries,
                export_targets=_software_spec_export_targets,
                required_spec_files=self._software_spec_service().required_files,
                export_files=_software_spec_export_files,
                export_required_files=_software_spec_export_required_files,
                export_show_file=_software_spec_export_show_file,
                project_definition_sections=_project_definition_required_sections,
                markdown_has_section=_markdown_has_section,
                read_yaml_mapping=_read_yaml_mapping,
                read_optional=_read_optional,
            )
        return self._spec_export_service_instance

    def _work_planning_service(self) -> WorkPlanningService:
        if self._work_planning_service_instance is None:
            self._work_planning_service_instance = WorkPlanningService(
                root=self.root,
                p2p_dir=self.p2p_dir,
                export_targets=_software_spec_export_targets,
                validate_export=self.validate_software_spec_export,
                find_change_dir=self._find_change_dir,
                scanned_work_items=self._scanned_work_items,
            )
        return self._work_planning_service_instance

    def init_project(
        self,
        name: str,
        agent_profile: str = "generic",
        repository_mode: str = "local",
        project_domain: str = "none",
        rubric_enabled: dict[str, bool] | None = None,
        owner: str | None = None,
        remote_provider: str | None = None,
        remote_name: str = "origin",
        remote_url_value: str | None = None,
    ) -> list[Path]:
        agent_profile = _normalize_agent_profile(agent_profile)
        repository_mode = _normalize_repository_mode(repository_mode)
        project_domain = _normalize_project_domain(project_domain)
        remote_profile = self._remote_profile_service().default_payload(
            repository_mode=repository_mode,
            provider=remote_provider,
            remote=remote_name,
            url=remote_url_value,
        )
        project_id = _slugify(name)
        files: dict[Path, str] = {
            self.p2p_dir / "project.yml": _yaml_dump(
                {
                    "project": {
                        "id": project_id,
                        "name": name,
                        "version": "0.1.0",
                        "status": "active",
                        "domain": project_domain,
                    },
                    "storage": {
                        "mode": "file_based",
                        "documents_format": "markdown",
                        "structured_data_format": "yaml",
                    },
                    "workflow": {"current_phase": "cli_managed"},
                    "ai": {"mode": "prompt_only", "direct_invocation": False},
                    "repository": {
                        "mode": repository_mode,
                        "managed_by_p2p": False,
                    },
                    "remote": remote_profile,
                }
            ),
            self.p2p_dir / "project" / "domain.yml": _yaml_dump(_domain_state_payload(project_domain)),
            self.p2p_dir / "governance" / "constitution.md": "# Constitution\n\nPending.\n",
            self.p2p_dir / "governance" / "decision-rules.md": "# Decision Rules\n\nPending.\n",
            self.p2p_dir / "governance" / "relevance-criteria.md": "# Relevance Criteria\n\nPending.\n",
            self.p2p_dir / "templates" / "proposal-template.md": "# {{ proposal_id }} - {{ title }}\n",
            self.p2p_dir / "templates" / "decision-template.md": "# Decision - {{ proposal_id }}\n",
            self.p2p_dir / "templates" / "execution-plan-template.md": "# Execution Plan - {{ proposal_id }}\n",
            self.p2p_dir / "templates" / "tasks-template.yml": "tasks: []\n",
            self.p2p_dir
            / "config"
            / "readiness-profiles"
            / f"{DEFAULT_READINESS_PROFILE_ID}.yml": _yaml_dump(self._readiness_service().default_profile_payload()),
            self.p2p_dir / "project" / "rubrics.yml": _yaml_dump(
                _rubrics_payload(project_domain, rubric_enabled=rubric_enabled)
            ),
            self.p2p_dir / "project" / "permissions.yml": _yaml_dump(
                self._permissions_service().default_policy_payload(
                    owner_name=owner,
                    repository_mode=repository_mode,
                )
            ),
        }
        if project_domain not in PROJECT_DOMAIN_TEMPLATES:
            files[self.p2p_dir / "project" / "next-actions.yml"] = _yaml_dump(
                _domain_setup_next_actions_payload(project_domain)
            )
        created: list[Path] = []
        for path, content in files.items():
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                created.append(path.relative_to(self.root))

        for directory in (self.p2p_dir / "proposals", self.p2p_dir / "prompts"):
            if not directory.exists():
                directory.mkdir(parents=True)
                created.append(directory.relative_to(self.root))
        instructions = self.refresh_agent_instructions(
            profile=agent_profile,
            repository_mode=repository_mode,
        )
        for path in [*instructions.created, *instructions.updated]:
            if path not in created:
                created.append(path)
        return created

    def refresh_agent_instructions(
        self,
        profile: str = "generic",
        repository_mode: str | None = None,
    ) -> AgentInstructionsResult:
        profile = _normalize_agent_profile(profile)
        project_name = self._project_name()
        repository_mode = _normalize_repository_mode(
            repository_mode or self._repository_mode(default="local")
        )
        profiles = _expanded_agent_profiles(profile)
        policy_path = self.p2p_dir / "agent-policy.yml"
        existing_policy = _read_yaml_mapping(policy_path, default={}) if policy_path.exists() else {}
        existing_profiles = existing_policy.get("agent_profiles", [])
        if not isinstance(existing_profiles, list):
            existing_profiles = []
        merged_profiles = sorted({str(item) for item in existing_profiles} | set(profiles))
        files = _agent_instruction_files(project_name, merged_profiles, repository_mode)
        created: list[Path] = []
        updated: list[Path] = []

        for relative_path, content in files.items():
            path = self.root / relative_path
            relative = path.relative_to(self.root)
            if path.exists() and path.read_text(encoding="utf-8") == content:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            existed = path.exists()
            path.write_text(content, encoding="utf-8")
            if existed:
                updated.append(relative)
            else:
                created.append(relative)

        policy = _agent_policy(project_name, merged_profiles, repository_mode)
        policy_content = _yaml_dump(policy)
        relative_policy = policy_path.relative_to(self.root)
        if not policy_path.exists():
            policy_path.parent.mkdir(parents=True, exist_ok=True)
            policy_path.write_text(policy_content, encoding="utf-8")
            created.append(relative_policy)
        elif policy_path.read_text(encoding="utf-8") != policy_content:
            policy_path.write_text(policy_content, encoding="utf-8")
            updated.append(relative_policy)

        self._set_repository_mode(repository_mode)
        self._write_agent_integrations_registry(
            self._build_agent_integrations_registry(merged_profiles, repository_mode)
        )
        return AgentInstructionsResult(
            profile=profile,
            created=created,
            updated=updated,
            policy_path=relative_policy,
        )

    def agent_integrations_list(self) -> dict[str, object]:
        registry = self._agent_integrations_registry()
        adapters = registry.get("adapters", {})
        if not isinstance(adapters, dict):
            adapters = {}
        return {
            "registry_path": str(self._agent_integrations_path().relative_to(self.root)),
            "baseline_profile": registry.get("baseline_profile", "generic"),
            "adapters": [
                self._agent_integration_status(adapter_id, adapters.get(adapter_id, {}))
                for adapter_id in BUILT_IN_AGENT_ADAPTERS
            ],
        }

    def agent_integration_show(self, adapter: str) -> dict[str, object]:
        adapter = _normalize_agent_profile(adapter)
        if adapter == "all":
            raise ValueError("Use a specific adapter for show.")
        registry = self._agent_integrations_registry()
        adapters = registry.get("adapters", {})
        if not isinstance(adapters, dict):
            adapters = {}
        return self._agent_integration_status(adapter, adapters.get(adapter, {}), include_files=True)

    def install_agent_integrations(
        self,
        target: str = "all",
        repository_mode: str | None = None,
        *,
        force: bool = False,
    ) -> AgentIntegrationResult:
        target = _normalize_agent_profile(target)
        repository_mode = _normalize_repository_mode(
            repository_mode or self._repository_mode(default="local")
        )
        project_name = self._project_name()
        registry = self._agent_integrations_registry()
        existing_adapters = registry.get("adapters", {})
        existing_profiles = (
            [str(adapter_id) for adapter_id in existing_adapters.keys()]
            if isinstance(existing_adapters, dict)
            else []
        )
        profiles = sorted(set(existing_profiles) | set(_expanded_agent_profiles(target)))
        files = _agent_instruction_files(project_name, profiles, repository_mode)
        current_files = self._agent_registry_file_map(registry)
        created: list[Path] = []
        updated: list[Path] = []
        skipped: list[dict[str, object]] = []

        for relative_path, content in files.items():
            path = self.root / relative_path
            relative = path.relative_to(self.root)
            existing_record = current_files.get(str(relative_path))
            if path.exists():
                current_hash = _sha256_file(path)
                if existing_record and existing_record.get("sha256") != current_hash and not force:
                    skipped.append(
                        {
                            "path": str(relative),
                            "reason": "drifted",
                        }
                    )
                    continue
                if not existing_record and path.read_text(encoding="utf-8") != content and not force:
                    skipped.append(
                        {
                            "path": str(relative),
                            "reason": "unmanaged_exists",
                        }
                    )
                    continue
                if path.read_text(encoding="utf-8") == content:
                    continue
                path.write_text(content, encoding="utf-8")
                updated.append(relative)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                created.append(relative)

        policy = _agent_policy(project_name, profiles, repository_mode)
        policy_path = self.p2p_dir / "agent-policy.yml"
        policy_content = _yaml_dump(policy)
        relative_policy = policy_path.relative_to(self.root)
        if not policy_path.exists():
            policy_path.parent.mkdir(parents=True, exist_ok=True)
            policy_path.write_text(policy_content, encoding="utf-8")
            created.append(relative_policy)
        elif policy_path.read_text(encoding="utf-8") != policy_content:
            policy_path.write_text(policy_content, encoding="utf-8")
            updated.append(relative_policy)

        new_registry = self._build_agent_integrations_registry(profiles, repository_mode)
        if skipped:
            old_records = self._agent_registry_file_map(registry)
            skipped_paths = {str(item["path"]) for item in skipped}
            for adapter_record in new_registry.get("adapters", {}).values():
                if not isinstance(adapter_record, dict):
                    continue
                file_records = adapter_record.get("files", [])
                if not isinstance(file_records, list):
                    continue
                for index, record in enumerate(file_records):
                    if not isinstance(record, dict):
                        continue
                    path_key = str(record.get("path", ""))
                    if path_key in skipped_paths and path_key in old_records:
                        preserved = {**old_records[path_key]}
                        current_path = self.root / path_key
                        preserved["drift"] = (
                            "drifted"
                            if current_path.exists() and preserved.get("sha256") != _sha256_file(current_path)
                            else "missing"
                        )
                        file_records[index] = preserved
                    elif path_key in skipped_paths:
                        current_path = self.root / path_key
                        record["managed"] = False
                        record["sha256"] = _sha256_file(current_path) if current_path.exists() else ""
                        record["drift"] = "unmanaged" if current_path.exists() else "missing"
        registry = new_registry
        self._write_agent_integrations_registry(registry)
        self._set_repository_mode(repository_mode)
        return AgentIntegrationResult(
            target=target,
            created=created,
            updated=updated,
            removed=[],
            skipped=skipped,
            registry_path=self._agent_integrations_path().relative_to(self.root),
        )

    def uninstall_agent_integration(self, adapter: str) -> AgentIntegrationResult:
        adapter = _normalize_agent_profile(adapter)
        if adapter in {"all", "generic"}:
            raise ValueError("generic cannot be uninstalled.")
        registry = self._agent_integrations_registry()
        adapters = registry.get("adapters", {})
        if not isinstance(adapters, dict) or adapter not in adapters:
            raise ValueError(f"Agent integration is not installed: {adapter}")
        adapter_record = adapters.get(adapter, {})
        files = adapter_record.get("files", []) if isinstance(adapter_record, dict) else []
        removed: list[Path] = []
        skipped: list[dict[str, object]] = []
        for record in files if isinstance(files, list) else []:
            if not isinstance(record, dict):
                continue
            relative = Path(str(record.get("path", "")))
            if record.get("shared") is True:
                skipped.append({"path": str(relative), "reason": "shared"})
                continue
            path = self.root / relative
            if not path.exists():
                skipped.append({"path": str(relative), "reason": "missing"})
                continue
            if record.get("sha256") != _sha256_file(path):
                skipped.append({"path": str(relative), "reason": "drifted"})
                continue
            path.unlink()
            removed.append(relative)
            _remove_empty_parents(path.parent, stop_at=self.root)

        adapters.pop(adapter, None)
        registry["adapters"] = adapters
        remaining_profiles = sorted({"generic"} | {str(item) for item in adapters.keys()})
        project_name = self._project_name()
        repository_mode = self._repository_mode(default="local")
        shared_files = _agent_instruction_files(project_name, remaining_profiles, repository_mode)
        for relative_path in (Path("AGENTS.md"),):
            content = shared_files.get(relative_path)
            if content is None:
                continue
            path = self.root / relative_path
            path.write_text(content, encoding="utf-8")
        policy_path = self.p2p_dir / "agent-policy.yml"
        policy_path.write_text(
            _yaml_dump(_agent_policy(project_name, remaining_profiles, repository_mode)),
            encoding="utf-8",
        )
        registry = self._build_agent_integrations_registry(remaining_profiles, repository_mode)
        self._write_agent_integrations_registry(registry)
        return AgentIntegrationResult(
            target=adapter,
            created=[],
            updated=[],
            removed=removed,
            skipped=skipped,
            registry_path=self._agent_integrations_path().relative_to(self.root),
        )

    def _agent_integrations_path(self) -> Path:
        return self.p2p_dir / "agent-integrations.yml"

    def _agent_integrations_registry(self) -> dict[str, object]:
        path = self._agent_integrations_path()
        if not path.exists():
            return {
                "schema_version": 1,
                "baseline_profile": "generic",
                "adapters": {},
            }
        return _read_yaml_mapping(path, default={})

    def _write_agent_integrations_registry(self, registry: dict[str, object]) -> None:
        path = self._agent_integrations_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(registry), encoding="utf-8")

    def _agent_registry_file_map(self, registry: dict[str, object]) -> dict[str, dict[str, object]]:
        adapters = registry.get("adapters", {})
        records: dict[str, dict[str, object]] = {}
        if not isinstance(adapters, dict):
            return records
        for adapter in adapters.values():
            if not isinstance(adapter, dict):
                continue
            files = adapter.get("files", [])
            if not isinstance(files, list):
                continue
            for record in files:
                if isinstance(record, dict) and "path" in record:
                    records[str(record["path"])] = record
        return records

    def _build_agent_integrations_registry(
        self,
        profiles: list[str],
        repository_mode: str,
    ) -> dict[str, object]:
        project_name = self._project_name()
        installed = sorted(set(_expanded_agent_profiles("generic")) | set(profiles))
        adapters: dict[str, object] = {}
        for adapter_id in installed:
            files = _agent_adapter_files(project_name, adapter_id, installed, repository_mode)
            file_records = []
            for relative_path, template_id, shared, owner in files:
                path = self.root / relative_path
                file_records.append(
                    {
                        "path": str(relative_path),
                        "shared": shared,
                        "owner": owner,
                        "managed": path.exists(),
                        "template_id": template_id,
                        "sha256": _sha256_file(path) if path.exists() else "",
                        "drift": "clean" if path.exists() else "missing",
                    }
                )
            adapters[adapter_id] = {
                "status": "installed",
                "maturity": "stable",
                "template_version": "agent-template-v1",
                "capabilities": _agent_adapter_capabilities(adapter_id),
                "files": file_records,
            }
        return {
            "schema_version": 1,
            "baseline_profile": "generic",
            "generated_at": date.today().isoformat(),
            "adapters": adapters,
        }

    def _agent_integration_status(
        self,
        adapter_id: str,
        record: object,
        *,
        include_files: bool = False,
    ) -> dict[str, object]:
        installed = isinstance(record, dict) and record.get("status") == "installed"
        files = record.get("files", []) if isinstance(record, dict) else []
        file_statuses: list[dict[str, object]] = []
        if isinstance(files, list):
            for file_record in files:
                if not isinstance(file_record, dict):
                    continue
                path = self.root / str(file_record.get("path", ""))
                drift = "missing"
                if path.exists():
                    drift = "clean" if file_record.get("sha256") == _sha256_file(path) else "drifted"
                file_status = {**file_record, "drift": drift}
                file_statuses.append(file_status)
        status = {
            "adapter": adapter_id,
            "supported": adapter_id in BUILT_IN_AGENT_ADAPTERS,
            "installed": installed,
            "maturity": record.get("maturity", "stable") if isinstance(record, dict) else "stable",
            "drift": "drifted" if any(item.get("drift") == "drifted" for item in file_statuses) else "clean",
        }
        if include_files:
            status["files"] = file_statuses
            status["capabilities"] = _agent_adapter_capabilities(adapter_id)
        return status

    def permissions_show(self) -> dict[str, object]:
        return self._permissions_service().show(repository_mode=self._repository_mode(default="local"))

    def permissions_actor_add(
        self,
        actor_id: str,
        role: str = "contributor",
        kind: str = "person",
        display_name: str | None = None,
    ) -> PermissionActor:
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
        return self._consent_service().consume(consent_id, result=result)

    def consent_mark_used_with_error(
        self,
        consent_id: str,
        *,
        error: str,
        result: dict[str, object] | None = None,
    ) -> ConsentReceipt:
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

    def _permissions_path(self) -> Path:
        return self._permissions_service().path()

    def _consent_path(self, consent_id: str) -> Path:
        return self._consent_service().path(consent_id)

    def _next_consent_id(self) -> str:
        return self._consent_service().next_consent_id()

    def _set_repository_mode(self, mode: str) -> None:
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
        project_name = "Unknown"
        project_file = self.p2p_dir / "project.yml"
        if project_file.exists():
            data = yaml.safe_load(project_file.read_text(encoding="utf-8")) or {}
            project_name = data.get("project", {}).get("name", project_name)

        proposals: list[ProposalSummary] = []
        proposals_dir = self.p2p_dir / "proposals"
        if proposals_dir.exists():
            for path in sorted(proposals_dir.iterdir()):
                if path.is_dir():
                    proposal_id = path.name.split("-", 2)[:2]
                    status = _read_proposal_status(path / "proposal.md")
                    proposals.append(
                        ProposalSummary(
                            proposal_id="-".join(proposal_id),
                            slug=path.name,
                            status=status,
                            title=_clean_proposal_title(
                                _read_title(_read_optional(path / "proposal.md")) or path.name,
                                "-".join(proposal_id),
                            ),
                        )
                )
        return WorkspaceStatus(root=self.root, project_name=project_name, proposals=proposals)

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
        return self._remote_profile_service().configure(
            mode=mode,
            provider=provider,
            remote=remote,
            url=url,
        )

    def sync_status(self, remote: str | None = None) -> SyncStatus:
        profile = self.remote_profile()
        git_status = get_git_status(self.root)
        selected_remote = self._sync_remote(remote)
        resolved_remote_url = (
            remote_url(self.root, selected_remote) if git_status.is_repository and selected_remote else None
        )

        reason = "ready"
        can_sync = True
        if not git_status.is_repository:
            can_sync = False
            if profile.mode == "remote":
                reason = (
                    "not a Git repository; initialize or clone the repository, then ensure "
                    f"Git remote {profile.remote or 'origin'} matches the P2P remote profile"
                )
            else:
                reason = "not a Git repository"
        elif profile.mode == "local" and remote is None and not profile.remote:
            origin_url = remote_url(self.root, "origin") if git_status.is_repository else None
            can_sync = False
            if origin_url:
                reason = (
                    "project remote profile is local, but Git remote origin exists; "
                    "run p2p project remote configure --mode remote --remote origin"
                )
            else:
                reason = "project remote profile is local"
        elif not selected_remote:
            can_sync = False
            reason = "no Git remote configured"
        elif resolved_remote_url is None:
            can_sync = False
            if profile.url:
                reason = (
                    f"Git remote not found: {selected_remote}; add it with "
                    f"git remote add {selected_remote} {profile.url} or update the P2P profile "
                    "with p2p project remote configure"
                )
            else:
                reason = (
                    f"Git remote not found: {selected_remote}; configure it locally or run "
                    "p2p project remote configure with --url"
                )
        elif profile.url and resolved_remote_url != profile.url:
            can_sync = False
            reason = (
                f"P2P remote profile URL does not match Git remote {selected_remote}; "
                "run p2p project remote configure with the intended URL"
            )
        return SyncStatus(
            is_repository=git_status.is_repository,
            branch=git_status.branch,
            is_clean=git_status.is_clean,
            mode=profile.mode,
            provider=profile.provider,
            remote=selected_remote,
            profile_url=profile.url,
            remote_url=resolved_remote_url,
            can_sync=can_sync,
            reason=reason,
        )

    def sync_fetch(self, remote: str | None = None) -> SyncResult:
        status = self.sync_status(remote)
        selected_remote = self._require_sync_remote(status)
        if not fetch_remote(self.root, selected_remote):
            raise ValueError(f"Failed to fetch Git remote: {selected_remote}")
        return SyncResult(
            action="fetch",
            status="fetched",
            branch=status.branch,
            remote=selected_remote,
            remote_url=str(status.remote_url),
        )

    def sync_pull(self, remote: str | None = None) -> SyncResult:
        status = self.sync_status(remote)
        selected_remote = self._require_sync_remote(status)
        if not status.branch:
            raise ValueError("Cannot pull from detached HEAD")
        if not status.is_clean:
            raise ValueError("Cannot pull with uncommitted changes")
        if not pull_branch(self.root, status.branch, selected_remote):
            raise ValueError(f"Failed to pull {selected_remote}/{status.branch} with fast-forward only")
        return SyncResult(
            action="pull",
            status="pulled",
            branch=status.branch,
            remote=selected_remote,
            remote_url=str(status.remote_url),
        )

    def sync_push(self, remote: str | None = None) -> SyncResult:
        status = self.sync_status(remote)
        selected_remote = self._require_sync_remote(status)
        if not status.branch:
            raise ValueError("Cannot push from detached HEAD")
        if not status.is_clean:
            raise ValueError("Cannot push with uncommitted changes")
        if not push_branch(self.root, status.branch, selected_remote):
            raise ValueError(f"Failed to push {status.branch} to {selected_remote}")
        return SyncResult(
            action="push",
            status="pushed",
            branch=status.branch,
            remote=selected_remote,
            remote_url=str(status.remote_url),
        )

    def proposal_summaries(self, status: str | None = None) -> list[ProposalSummary]:
        proposals = self.status().proposals
        if status is None:
            return proposals
        return [proposal for proposal in proposals if proposal.status == status]

    def show_proposal(self, proposal_id: str) -> ProposalDetail:
        return self._proposal_document_service().show(proposal_id)

    def commit_proposal_draft(self, proposal_id: str, actor: str = "local") -> ProposalDraftCommit:
        self._find_proposal_dir(proposal_id)
        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot commit proposal draft outside a Git repository")
        if not git_status.branch:
            raise ValueError("Cannot commit proposal draft from detached HEAD")
        changed = changed_files(self.root)
        if not changed:
            raise ValueError("Cannot commit proposal draft without uncommitted changes")
        commit = commit_all(self.root, f"P2P proposal draft {proposal_id} by {_identity_slug(actor)}")
        if commit is None:
            raise ValueError("Failed to create proposal draft commit")
        return ProposalDraftCommit(proposal_id=proposal_id, commit=commit, changed_files=changed)

    def branch_proposal(
        self,
        proposal_id: str,
        actor: str = "local",
        base_branch: str | None = None,
        allow_proposal_base: bool = False,
    ) -> ProposalBranchDetail:
        proposal_dir = self._find_proposal_dir(proposal_id)
        proposal_text = _read_optional(proposal_dir / "proposal.md")
        title = _clean_proposal_title(_read_title(proposal_text) or proposal_id, proposal_id)
        actor_slug = _slugify(actor) or "local"

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot create managed proposal branch outside a Git repository")
        if not git_status.branch:
            raise ValueError("Cannot create managed proposal branch from detached HEAD")
        if not git_status.is_clean:
            raise ValueError("Cannot create managed proposal branch with uncommitted changes")

        selected_base = (base_branch or git_status.branch).strip()
        if not selected_base:
            raise ValueError("Base branch is required")
        if selected_base.startswith("p2p/proposal/") and not allow_proposal_base:
            raise ValueError("Cannot create managed proposal branch from another proposal branch without explicit allow_proposal_base")
        if git_status.branch != selected_base:
            if not checkout_branch(self.root, selected_base):
                raise ValueError(f"Failed to check out base branch: {selected_base}")
            git_status = get_git_status(self.root)
            if not git_status.is_clean:
                raise ValueError("Cannot create managed proposal branch with uncommitted changes")
        base_commit = head_commit(self.root)
        if base_commit is None:
            raise ValueError("Cannot resolve current Git commit")
        branch_hash16 = _branch_hash16(proposal_id, title, actor_slug, base_commit)
        branch_name = _proposal_branch_name(proposal_id, title, actor_slug, branch_hash16)
        if branch_exists(self.root, branch_name):
            raise ValueError(f"Managed proposal branch already exists: {branch_name}")

        if not create_and_checkout_branch(self.root, branch_name):
            raise ValueError(f"Failed to create managed proposal branch: {branch_name}")
        head = head_commit(self.root)
        if head is None:
            raise ValueError("Cannot resolve managed proposal branch commit")

        metadata = {
            "proposal_id": proposal_id,
            "status": "branched",
            "branch_name": branch_name,
            "branch_hash16": branch_hash16,
            "actor": actor,
            "actor_slug": actor_slug,
            "base_branch": selected_base,
            "base_commit": base_commit,
            "head_commit": head,
            "created_at": date.today().isoformat(),
            "remote": None,
            "remote_url": None,
            "remote_branch": None,
        }
        metadata_path = proposal_dir / "branch.yml"
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        if commit_all(self.root, f"P2P proposal branch {proposal_id}") is None:
            raise ValueError("Failed to create managed proposal branch metadata commit")
        return self.show_proposal_branch(proposal_id)

    def show_proposal_branch(self, proposal_id: str) -> ProposalBranchDetail:
        proposal_dir = self._find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default={})
        if not metadata:
            return ProposalBranchDetail(
                proposal_id=proposal_id,
                status="unbranched",
                branch_name="",
                base_branch="",
                actor="",
                branch_hash16="",
                remote=None,
                remote_url=None,
                path=proposal_dir.relative_to(self.root),
                metadata={},
            )
        return _proposal_branch_detail_from_metadata(proposal_id, metadata, proposal_dir.relative_to(self.root))

    def publish_proposal_branch(
        self,
        proposal_id: str,
        remote: str | None = None,
        *,
        auto_renumber: bool = False,
    ) -> ProposalBranchDetail:
        proposal_dir, metadata, metadata_path = self._proposal_branch_metadata(proposal_id)
        status = str(metadata.get("status") or "unknown")
        if status not in {"branched", "revised", "review_requested"}:
            raise ValueError(f"Proposal branch must be branched, revised, or review_requested before publish. Current status: {status}")
        branch_name = str(metadata.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid proposal branch metadata: branch_name is required")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot publish managed proposal branch outside a Git repository")
        if git_status.branch != branch_name:
            raise ValueError(f"Cannot publish managed proposal branch from {git_status.branch}; expected branch {branch_name}")
        if not git_status.is_clean:
            raise ValueError("Cannot publish managed proposal branch with uncommitted changes")

        selected_remote = remote or self.remote_profile().remote or "origin"
        resolved_remote_url = remote_url(self.root, selected_remote)
        if resolved_remote_url is None:
            raise ValueError(f"Cannot publish managed proposal branch: Git remote not found: {selected_remote}")

        if not fetch_remote(self.root, selected_remote):
            raise ValueError(f"Failed to fetch Git remote before proposal publish: {selected_remote}")
        remote_ids = self._remote_proposal_ids(selected_remote, str(metadata.get("base_branch") or "main"))
        if proposal_id in remote_ids:
            if not auto_renumber:
                raise ValueError(
                    f"Proposal ID collision detected on remote: {proposal_id}. "
                    f"Run `p2p proposal publish {proposal_id} --auto-renumber` to allocate the next available ID."
                )
            proposal_id, proposal_dir, metadata, metadata_path = self._auto_renumber_proposal_branch(
                proposal_id=proposal_id,
                metadata=metadata,
                remote_ids=remote_ids,
            )
            branch_name = str(metadata.get("branch_name") or "")
            if not branch_name:
                raise ValueError("Invalid proposal branch metadata after auto-renumber: branch_name is required")
            git_status = get_git_status(self.root)
            if git_status.branch != branch_name:
                raise ValueError(
                    f"Cannot publish auto-renumbered proposal branch from {git_status.branch}; expected branch {branch_name}"
                )
            if not git_status.is_clean:
                raise ValueError("Cannot publish auto-renumbered proposal branch with uncommitted changes")
            if proposal_id in self._remote_proposal_ids(selected_remote, str(metadata.get("base_branch") or "main")):
                raise ValueError(f"Proposal ID collision remains after auto-renumber: {proposal_id}")

        metadata["status"] = "published"
        metadata["remote"] = selected_remote
        metadata["remote_url"] = resolved_remote_url
        metadata["remote_branch"] = branch_name
        metadata["published_at"] = date.today().isoformat()
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        if commit_all(self.root, f"P2P proposal publish {proposal_id}") is None:
            raise ValueError("Failed to create managed proposal publish metadata commit")
        if not push_branch(self.root, branch_name, selected_remote):
            raise ValueError(f"Failed to push managed proposal branch to {selected_remote}: {branch_name}")
        return self.show_proposal_branch(proposal_id)

    def request_proposal_branch_review(self, proposal_id: str, provider: str | None = None) -> ProposalBranchDetail:
        proposal_dir, metadata, metadata_path = self._proposal_branch_metadata(proposal_id)
        status = str(metadata.get("status") or "unknown")
        if status != "published":
            raise ValueError(f"Proposal branch must be published before request-review. Current status: {status}")
        branch_name = str(metadata.get("branch_name") or "")
        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot request managed proposal review outside a Git repository")
        if git_status.branch != branch_name:
            raise ValueError(f"Cannot request managed proposal review from {git_status.branch}; expected branch {branch_name}")
        if not git_status.is_clean:
            raise ValueError("Cannot request managed proposal review with uncommitted changes")

        remote = str(metadata.get("remote") or self.remote_profile().remote or "origin")
        resolved_remote_url = str(metadata.get("remote_url") or remote_url(self.root, remote) or "")
        if not resolved_remote_url:
            raise ValueError(f"Cannot request managed proposal review: Git remote not found: {remote}")
        selected_provider = (provider or self.remote_profile().provider or "generic").strip().lower()
        if selected_provider == "local":
            selected_provider = "generic"
        if selected_provider not in {"generic", "github", "gitlab"}:
            raise ValueError("Proposal review provider must be generic, github, or gitlab")

        metadata["status"] = "review_requested"
        metadata["review"] = {
            "mode": "provider_advisory",
            "provider": selected_provider,
            "remote": remote,
            "remote_url": resolved_remote_url,
            "remote_branch": branch_name,
            "opens_external_request": False,
            "requested_at": date.today().isoformat(),
            "suggested_next": _review_request_suggestion(selected_provider, resolved_remote_url, branch_name),
        }
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        if commit_all(self.root, f"P2P proposal request review {proposal_id}") is None:
            raise ValueError("Failed to create managed proposal review metadata commit")
        return self.show_proposal_branch(proposal_id)

    def retire_proposal_branch(self, proposal_id: str, reason: str) -> ProposalBranchDetail:
        reason = reason.strip()
        if not reason:
            raise ValueError("Proposal branch retire reason is required")
        proposal_dir, metadata, metadata_path = self._proposal_branch_metadata(proposal_id)
        status = str(metadata.get("status") or "unknown")
        if status in {"merged", "finalized", "retired"}:
            raise ValueError(f"Proposal branch cannot be retired from status: {status}")
        branch_name = str(metadata.get("branch_name") or "")
        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot retire managed proposal branch outside a Git repository")
        if git_status.branch != branch_name:
            raise ValueError(f"Cannot retire managed proposal branch from {git_status.branch}; expected branch {branch_name}")
        if not git_status.is_clean:
            raise ValueError("Cannot retire managed proposal branch with uncommitted changes")

        metadata["status"] = "retired"
        metadata["retirement"] = {
            "reason": reason,
            "retired_at": date.today().isoformat(),
        }
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        if commit_all(self.root, f"P2P proposal retire {proposal_id}") is None:
            raise ValueError("Failed to create managed proposal retire metadata commit")
        return self.show_proposal_branch(proposal_id)

    def accept_proposal_branch(self, proposal_id: str, reason: str) -> ProposalBranchDetail:
        reason = reason.strip()
        if not reason:
            raise ValueError("Proposal branch accept reason is required")
        return self._decide_proposal_branch(proposal_id, "accepted", reason)

    def reject_proposal_branch(self, proposal_id: str, reason: str) -> ProposalBranchDetail:
        reason = reason.strip()
        if not reason:
            raise ValueError("Proposal branch reject reason is required")
        return self._decide_proposal_branch(proposal_id, "rejected", reason)

    def _decide_proposal_branch(self, proposal_id: str, outcome: str, reason: str) -> ProposalBranchDetail:
        proposal_dir, metadata, metadata_path = self._proposal_branch_metadata(proposal_id)
        status = str(metadata.get("status") or "unknown")
        if status not in {"published", "review_requested"}:
            raise ValueError(
                f"Proposal branch must be published or review_requested before {outcome}. Current status: {status}"
            )
        branch_name = str(metadata.get("branch_name") or "")
        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError(f"Cannot {outcome} managed proposal branch outside a Git repository")
        if git_status.branch != branch_name:
            raise ValueError(f"Cannot {outcome} managed proposal branch from {git_status.branch}; expected branch {branch_name}")
        if not git_status.is_clean:
            raise ValueError(f"Cannot {outcome} managed proposal branch with uncommitted changes")

        metadata["status"] = outcome
        metadata["branch_decision"] = {
            "outcome": outcome,
            "reason": reason,
            "decided_at": date.today().isoformat(),
            "governance_decision": True,
        }
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        verb = "accept" if outcome == "accepted" else "reject"
        if commit_all(self.root, f"P2P proposal branch {verb} {proposal_id}") is None:
            raise ValueError(f"Failed to create managed proposal branch {verb} metadata commit")
        return ProposalBranchDetail(
            proposal_id=str(metadata.get("proposal_id") or proposal_id),
            status=outcome,
            branch_name=branch_name,
            base_branch=str(metadata.get("base_branch") or "main"),
            actor=str(metadata.get("actor") or ""),
            branch_hash16=str(metadata.get("branch_hash16") or ""),
            remote=str(metadata.get("remote") or ""),
            remote_url=str(metadata.get("remote_url") or ""),
            path=proposal_dir.relative_to(self.root),
            metadata=metadata,
        )

    def merge_proposal_branch(self, proposal_id: str) -> ProposalMerge | ProposalMergeConflict:
        branch_name, metadata, branch_metadata_path = self._proposal_branch_metadata_from_local_ref(proposal_id)
        status = str(metadata.get("status") or "unknown")
        if status not in {"published", "review_requested", "accepted"}:
            raise ValueError(
                f"Proposal branch must be published, review_requested, or accepted before merge. Current status: {status}"
            )
        base_branch = str(metadata.get("base_branch") or "main")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot merge managed proposal branch outside a Git repository")
        if git_status.branch != base_branch:
            raise ValueError(f"Cannot merge managed proposal branch from {git_status.branch}; expected base branch {base_branch}")
        if not git_status.is_clean:
            raise ValueError("Cannot merge managed proposal branch with uncommitted changes")
        if not branch_exists(self.root, branch_name):
            raise ValueError(f"Managed proposal branch not found: {branch_name}")

        if not merge_branch_no_commit(self.root, branch_name):
            conflicts = conflicted_files(self.root)
            if not conflicts:
                raise ValueError(f"Failed to merge managed proposal branch: {branch_name}")
            metadata["status"] = "merge_conflict"
            metadata["merge_conflict"] = {
                "source_branch": branch_name,
                "base_branch": base_branch,
                "conflicted_files": conflicts,
                "continue_command": f"p2p proposal merge --continue {proposal_id}",
                "abort_command": f"p2p proposal merge --abort {proposal_id}",
            }
            metadata["merge_conflict_at"] = date.today().isoformat()
            metadata_path = self.root / branch_metadata_path
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
            return ProposalMergeConflict(
                proposal_id=proposal_id,
                branch_name=branch_name,
                base_branch=base_branch,
                conflicted_files=conflicts,
                path=branch_metadata_path.parent,
            )

        metadata_path = self.root / branch_metadata_path
        merged_metadata = _read_yaml_mapping(metadata_path, default=metadata)
        merged_metadata["status"] = "merged"
        merged_metadata["merged_at"] = date.today().isoformat()
        merged_metadata["merge"] = {
            "mode": "local_merge",
            "source_branch": branch_name,
            "merged_into": base_branch,
            "pushed": False,
            "cleanup": False,
        }
        metadata_path.write_text(_yaml_dump(merged_metadata), encoding="utf-8")
        merge_commit = commit_all(self.root, f"P2P proposal merge {proposal_id}")
        if merge_commit is None:
            raise ValueError("Failed to create managed proposal merge commit")
        return ProposalMerge(
            proposal_id=proposal_id,
            branch_name=branch_name,
            base_branch=base_branch,
            merge_commit=merge_commit,
            path=branch_metadata_path.parent,
        )

    def continue_merge_proposal_branch(self, proposal_id: str) -> ProposalMerge:
        proposal_dir = self._find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default={})
        status = str(metadata.get("status") or "unknown")
        if status != "merge_conflict":
            raise ValueError(f"Proposal branch must be merge_conflict before merge --continue. Current status: {status}")
        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot continue managed proposal merge outside a Git repository")
        if not merge_in_progress(self.root):
            raise ValueError("Cannot continue managed proposal merge: no merge is in progress")
        unresolved = [path for path in conflicted_files(self.root) if _file_has_conflict_markers(self.root / path)]
        if unresolved:
            raise ValueError("Cannot continue managed proposal merge with unresolved conflicts: " + ", ".join(unresolved))
        stage_all(self.root)
        conflicts = conflicted_files(self.root)
        if conflicts:
            raise ValueError("Cannot continue managed proposal merge with unresolved conflicts: " + ", ".join(conflicts))
        conflict = metadata.get("merge_conflict", {})
        if not isinstance(conflict, dict):
            conflict = {}
        branch_name = str(conflict.get("source_branch") or metadata.get("branch_name") or "")
        base_branch = str(conflict.get("base_branch") or metadata.get("base_branch") or git_status.branch or "main")
        metadata["status"] = "merged"
        metadata["merged_at"] = date.today().isoformat()
        metadata.pop("merge_conflict", None)
        metadata["merge"] = {
            "mode": "local_merge",
            "source_branch": branch_name,
            "merged_into": base_branch,
            "pushed": False,
            "cleanup": False,
            "resolved_conflict": True,
        }
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        merge_commit = commit_all(self.root, f"P2P proposal merge {proposal_id}")
        if merge_commit is None:
            raise ValueError("Failed to create managed proposal merge commit")
        return ProposalMerge(
            proposal_id=proposal_id,
            branch_name=branch_name,
            base_branch=base_branch,
            merge_commit=merge_commit,
            path=proposal_dir.relative_to(self.root),
        )

    def abort_merge_proposal_branch(self, proposal_id: str) -> ProposalBranchDetail:
        proposal_dir = self._find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default={})
        status = str(metadata.get("status") or "unknown")
        if status != "merge_conflict":
            raise ValueError(f"Proposal branch must be merge_conflict before merge --abort. Current status: {status}")
        branch_name = str(metadata.get("branch_name") or "")
        if merge_in_progress(self.root):
            restore_path(self.root, metadata_path.relative_to(self.root).as_posix())
            if not abort_merge(self.root):
                raise ValueError("Failed to abort managed proposal merge")
        if not checkout_branch(self.root, branch_name):
            raise ValueError(f"Failed to return to managed proposal branch after merge abort: {branch_name}")
        return self.show_proposal_branch(proposal_id)

    def finalize_proposal_branch(self, proposal_id: str, remote: str | None = None) -> ProposalFinalize:
        proposal_dir = self._find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default={})
        status = str(metadata.get("status") or "unknown")
        if status != "merged":
            raise ValueError(f"Proposal branch must be merged before finalize. Current status: {status}")
        merge = metadata.get("merge", {})
        if not isinstance(merge, dict):
            merge = {}
        branch_name = str(metadata.get("branch_name") or merge.get("source_branch") or "")
        base_branch = str(merge.get("merged_into") or metadata.get("base_branch") or "main")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot finalize managed proposal branch outside a Git repository")
        if git_status.branch != base_branch:
            raise ValueError(f"Cannot finalize managed proposal branch from {git_status.branch}; expected base branch {base_branch}")
        if not git_status.is_clean:
            raise ValueError("Cannot finalize managed proposal branch with uncommitted changes")

        selected_remote = remote or str(metadata.get("remote") or self.remote_profile().remote or "origin")
        resolved_remote_url = remote_url(self.root, selected_remote)
        if resolved_remote_url is None:
            raise ValueError(f"Cannot finalize managed proposal branch: Git remote not found: {selected_remote}")

        metadata["status"] = "finalized"
        metadata["finalized_at"] = date.today().isoformat()
        merge["pushed"] = True
        merge["cleanup"] = False
        metadata["merge"] = merge
        metadata["finalize"] = {
            "mode": "base_branch_push",
            "remote": selected_remote,
            "remote_url": resolved_remote_url,
            "base_branch": base_branch,
            "source_branch": branch_name,
            "cleanup": False,
        }
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        finalize_commit = commit_all(self.root, f"P2P proposal finalize {proposal_id}")
        if finalize_commit is None:
            raise ValueError("Failed to create managed proposal finalize commit")
        if not push_branch(self.root, base_branch, selected_remote):
            raise ValueError(f"Failed to push base branch to {selected_remote}: {base_branch}")
        return ProposalFinalize(
            proposal_id=proposal_id,
            branch_name=branch_name,
            base_branch=base_branch,
            remote=selected_remote,
            remote_url=resolved_remote_url,
            finalize_commit=finalize_commit,
            path=proposal_dir.relative_to(self.root),
        )

    def cleanup_proposal_branch(
        self,
        proposal_id: str,
        *,
        delete_remote: bool = False,
        remote: str | None = None,
    ) -> ProposalCleanup:
        proposal_dir = self._find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default={}) if metadata_path.exists() else {}
        status = str(metadata.get("status") or "unknown")
        if status not in {"finalized", "rejected", "retired"}:
            branch_name_from_ref, metadata_from_ref, ref_metadata_path = self._proposal_branch_metadata_from_local_ref(proposal_id)
            metadata = metadata_from_ref
            status = str(metadata.get("status") or "unknown")
            metadata_path = self.root / ref_metadata_path
            proposal_dir = metadata_path.parent
            if not str(metadata.get("branch_name") or ""):
                metadata["branch_name"] = branch_name_from_ref

        if status not in {"finalized", "rejected", "retired"}:
            raise ValueError(
                f"Proposal branch must be finalized, rejected, or retired before cleanup. Current status: {status}"
            )

        merge = metadata.get("merge", {})
        if not isinstance(merge, dict):
            merge = {}
        finalize = metadata.get("finalize", {})
        if not isinstance(finalize, dict):
            finalize = {}
        branch_name = str(
            metadata.get("branch_name")
            or finalize.get("source_branch")
            or merge.get("source_branch")
            or metadata.get("remote_branch")
            or ""
        )
        if not branch_name:
            raise ValueError("Invalid proposal branch metadata: managed branch is required before cleanup")
        base_branch = str(finalize.get("base_branch") or merge.get("merged_into") or metadata.get("base_branch") or "main")
        if branch_name == base_branch:
            raise ValueError("Cannot cleanup managed proposal branch: source branch matches base branch")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot cleanup managed proposal branch outside a Git repository")
        if git_status.branch != base_branch:
            raise ValueError(f"Cannot cleanup managed proposal branch from {git_status.branch}; expected base branch {base_branch}")
        if not git_status.is_clean:
            raise ValueError("Cannot cleanup managed proposal branch with uncommitted changes")
        if not branch_exists(self.root, branch_name):
            raise ValueError(f"Managed proposal branch not found: {branch_name}")

        selected_remote = remote or str(finalize.get("remote") or metadata.get("remote") or self.remote_profile().remote or "origin")
        resolved_remote_url = remote_url(self.root, selected_remote) or ""
        if delete_remote and not resolved_remote_url:
            raise ValueError(f"Cannot cleanup managed proposal branch: Git remote not found: {selected_remote}")

        local_deleted = (
            delete_local_branch(self.root, branch_name)
            if status == "finalized"
            else delete_local_branch_force(self.root, branch_name)
        )
        if not local_deleted:
            raise ValueError(f"Failed to delete local managed proposal branch: {branch_name}")
        remote_deleted = False
        if delete_remote:
            if not delete_remote_branch(self.root, branch_name, selected_remote):
                raise ValueError(f"Failed to delete remote managed proposal branch from {selected_remote}: {branch_name}")
            remote_deleted = True

        metadata["status"] = "cleaned"
        metadata["cleaned_at"] = date.today().isoformat()
        if finalize:
            finalize["cleanup"] = True
            metadata["finalize"] = finalize
        if merge:
            merge["cleanup"] = True
            metadata["merge"] = merge
        metadata["cleanup"] = {
            "mode": "branch_cleanup",
            "previous_status": status,
            "source_branch": branch_name,
            "base_branch": base_branch,
            "remote": selected_remote,
            "remote_url": resolved_remote_url,
            "local_deleted": True,
            "remote_deleted": remote_deleted,
        }
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        cleanup_commit = commit_all(self.root, f"P2P proposal cleanup {proposal_id}")
        if cleanup_commit is None:
            raise ValueError("Failed to create managed proposal cleanup commit")
        if resolved_remote_url and not push_branch(self.root, base_branch, selected_remote):
            raise ValueError(f"Failed to push cleanup metadata to {selected_remote}: {base_branch}")

        return ProposalCleanup(
            proposal_id=str(metadata.get("proposal_id") or proposal_id),
            branch_name=branch_name,
            base_branch=base_branch,
            remote=selected_remote,
            remote_url=resolved_remote_url,
            cleanup_commit=cleanup_commit,
            local_deleted=True,
            remote_deleted=remote_deleted,
            path=proposal_dir.relative_to(self.root),
        )

    def scan_proposal_branches(self) -> ProposalBranchScan:
        branches = list_local_proposal_branches(self.root)
        items: list[dict[str, object]] = []
        for branch in branches:
            for manifest_path in list_files_at_ref(self.root, branch, ".p2p/proposals"):
                if not manifest_path.endswith("/branch.yml"):
                    continue
                branch_file = read_file_at_ref(self.root, branch, manifest_path)
                if branch_file is None:
                    continue
                try:
                    metadata = yaml.safe_load(branch_file.content) or {}
                except yaml.YAMLError:
                    continue
                if not isinstance(metadata, dict):
                    continue
                items.append(
                    {
                        "proposal_id": str(metadata.get("proposal_id") or "PROP-???"),
                        "status": str(metadata.get("status") or "unknown"),
                        "branch_name": str(metadata.get("branch_name") or branch),
                        "actor": str(metadata.get("actor") or ""),
                        "branch_hash16": str(metadata.get("branch_hash16") or ""),
                        "path": manifest_path,
                    }
                )
        scan_path = self.p2p_dir / "registries" / "proposal-branches.yml"
        scan_path.parent.mkdir(parents=True, exist_ok=True)
        scan_path.write_text(
            _yaml_dump({"scanned_branches": branches, "proposal_branches": items}),
            encoding="utf-8",
        )
        return ProposalBranchScan(
            scanned_branches=branches,
            proposals=items,
            path=scan_path.relative_to(self.root),
        )

    def check(self) -> WorkspaceCheck:
        required = [
            self.p2p_dir / "project.yml",
            self.p2p_dir / "governance" / "constitution.md",
            self.p2p_dir / "governance" / "decision-rules.md",
            self.p2p_dir / "governance" / "relevance-criteria.md",
            self.p2p_dir / "templates" / "proposal-template.md",
            self.p2p_dir / "templates" / "decision-template.md",
            self.p2p_dir / "templates" / "execution-plan-template.md",
            self.p2p_dir / "templates" / "tasks-template.yml",
            self.p2p_dir / "proposals",
            self.p2p_dir / "prompts",
        ]
        missing = [path.relative_to(self.root) for path in required if not path.exists()]
        return WorkspaceCheck(ok=not missing, missing=missing)

    def validate(self) -> ValidationResult:
        findings: list[ValidationFinding] = []

        def add(
            code: str,
            severity: str,
            path: Path,
            message: str,
            suggested_command: str = "",
        ) -> None:
            findings.append(
                ValidationFinding(
                    code=code,
                    severity=severity,
                    path=_relative_to_root(path, self.root),
                    message=message,
                    suggested_command=suggested_command,
                )
            )

        required_paths = [
            self.p2p_dir / "project.yml",
            self.p2p_dir / "governance" / "constitution.md",
            self.p2p_dir / "governance" / "decision-rules.md",
            self.p2p_dir / "governance" / "relevance-criteria.md",
            self.p2p_dir / "templates" / "proposal-template.md",
            self.p2p_dir / "templates" / "decision-template.md",
            self.p2p_dir / "templates" / "execution-plan-template.md",
            self.p2p_dir / "templates" / "tasks-template.yml",
            self.p2p_dir / "proposals",
            self.p2p_dir / "prompts",
        ]
        for path in required_paths:
            if not path.exists():
                add("P2P001_MISSING_REQUIRED_PATH", "error", path, "Required P2P path is missing.")

        structured_files = [self.p2p_dir / "project.yml", self.p2p_dir / "agent-policy.yml"]
        structured_files.extend(self.p2p_dir.glob("config/**/*.yml"))
        structured_files.extend(self.p2p_dir.glob("registries/*.yml"))
        structured_files.extend(self.p2p_dir.glob("project/*.yml"))
        structured_files.extend(self.p2p_dir.glob("proposals/*/*.yml"))
        structured_files.extend(self.p2p_dir.glob("changes/*/*.yml"))
        structured_files.extend(self.p2p_dir.glob("choices/*/*.yml"))
        structured_files.extend(self.p2p_dir.glob("work/*/*.yml"))
        structured_files.extend(self.p2p_dir.glob("consents/*/*.yml"))
        for path in sorted(set(structured_files)):
            if path.exists() and path.is_file():
                try:
                    yaml.safe_load(path.read_text(encoding="utf-8"))
                except yaml.YAMLError as exc:
                    add("P2P010_INVALID_YAML", "error", path, f"Invalid YAML: {exc}")

        for profile_path in sorted(self.p2p_dir.glob("config/readiness-profiles/*.yml")):
            try:
                _validate_readiness_profile_payload(_read_yaml_mapping(profile_path, default={}))
            except ValueError as exc:
                add("P2P230_INVALID_READINESS_PROFILE", "error", profile_path, str(exc))

        for readiness_path in sorted(self.p2p_dir.glob("proposals/*/readiness.yml")):
            try:
                _validate_readiness_assessment_payload(_read_yaml_mapping(readiness_path, default={}))
            except ValueError as exc:
                add("P2P231_INVALID_READINESS_ASSESSMENT", "error", readiness_path, str(exc))

        agent_integrations_path = self._agent_integrations_path()
        if agent_integrations_path.exists():
            try:
                _validate_agent_integrations_payload(_read_yaml_mapping(agent_integrations_path, default={}))
            except ValueError as exc:
                add("P2P240_INVALID_AGENT_INTEGRATIONS", "error", agent_integrations_path, str(exc))

        permissions_path = self._permissions_path()
        if permissions_path.exists():
            try:
                permissions = _read_yaml_mapping(permissions_path, default={})
            except ValueError as exc:
                add("P2P210_INVALID_PERMISSIONS", "error", permissions_path, str(exc))
                permissions = {}
            identities = permissions.get("identities", {})
            if not isinstance(identities, dict) or not identities:
                add("P2P211_INVALID_PERMISSIONS_IDENTITIES", "error", permissions_path, "permissions.yml must define identities.")
            else:
                has_owner = False
                for actor_id, actor in identities.items():
                    if not isinstance(actor, dict):
                        add("P2P212_INVALID_PERMISSION_ACTOR", "error", permissions_path, f"Actor must be a mapping: {actor_id}")
                        continue
                    role = str(actor.get("role") or "")
                    kind = str(actor.get("kind") or "")
                    if role not in PERMISSION_ROLES:
                        add("P2P213_INVALID_PERMISSION_ROLE", "error", permissions_path, f"Invalid role for {actor_id}: {role}")
                    if kind not in ACTOR_KINDS:
                        add("P2P214_INVALID_ACTOR_KIND", "error", permissions_path, f"Invalid actor kind for {actor_id}: {kind}")
                    has_owner = has_owner or role == "owner"
                if not has_owner:
                    add("P2P215_MISSING_OWNER_IDENTITY", "error", permissions_path, "permissions.yml must define at least one owner identity.")

        for consent_path in sorted(self.p2p_dir.glob("consents/CONSENT-*/consent.yml")):
            consent_dir_id = consent_path.parent.name
            try:
                consent = _read_yaml_mapping(consent_path, default={})
            except ValueError as exc:
                add("P2P220_INVALID_CONSENT", "error", consent_path, str(exc))
                continue
            consent_id = str(consent.get("consent_id") or "")
            if consent_id != consent_dir_id:
                add("P2P221_CONSENT_ID_MISMATCH", "error", consent_path, f"Consent ID {consent_id} does not match directory {consent_dir_id}.")
            operation = str(consent.get("operation") or "")
            if operation not in CONSENT_OPERATIONS:
                add("P2P222_INVALID_CONSENT_OPERATION", "error", consent_path, f"Invalid consent operation: {operation}")
            status = str(consent.get("status") or "")
            if status not in {"requested", "granted", "consumed", "revoked", "expired", "used_with_error"}:
                add("P2P223_INVALID_CONSENT_STATUS", "error", consent_path, f"Invalid consent status: {status}")
            required_fields = ["target", "actor_id", "created_at"]
            if status != "requested":
                required_fields.append("approved_by")
            for required in required_fields:
                if not str(consent.get(required) or "").strip():
                    add("P2P224_MISSING_CONSENT_FIELD", "error", consent_path, f"Consent receipt missing required field: {required}")

        proposals_dir = self.p2p_dir / "proposals"
        if proposals_dir.exists():
            for proposal_id, paths in self._duplicate_proposal_ids().items():
                relative_paths = ", ".join(str(_relative_to_root(path, self.root)) for path in paths)
                add(
                    "P2P104_DUPLICATE_PROPOSAL_ID",
                    "error",
                    proposals_dir,
                    f"Duplicate proposal ID {proposal_id} found in: {relative_paths}.",
                    suggested_command="rename or retire duplicate proposal directories, then run p2p registry refresh",
                )

            for proposal_dir in sorted(path for path in proposals_dir.iterdir() if path.is_dir()):
                match = re.match(r"^(PROP-\d{3})-[a-z0-9][a-z0-9-]*$", proposal_dir.name)
                if not match:
                    add(
                        "P2P100_INVALID_PROPOSAL_DIRECTORY",
                        "error",
                        proposal_dir,
                        "Proposal directory must be named PROP-XXX-slug.",
                    )
                    proposal_id = proposal_dir.name.split("-", 2)[0]
                else:
                    proposal_id = match.group(1)
                proposal_path = proposal_dir / "proposal.md"
                decision_path = proposal_dir / "decision.md"
                if not proposal_path.exists():
                    add("P2P101_MISSING_PROPOSAL_FILE", "error", proposal_path, "proposal.md is missing.")
                    continue
                proposal_text = proposal_path.read_text(encoding="utf-8")
                for section in ("Status", "Problem", "Proposal", "Decision"):
                    if not _markdown_has_section(proposal_text, section):
                        add(
                            "P2P102_MISSING_PROPOSAL_SECTION",
                            "error",
                            proposal_path,
                            f"proposal.md is missing required section: {section}.",
                        )
                proposal_status = _read_proposal_status(proposal_path)
                if proposal_status == "unknown":
                    add(
                        "P2P103_MISSING_PROPOSAL_STATUS",
                        "error",
                        proposal_path,
                        "proposal.md is missing a machine-readable status.",
                    )

                if not decision_path.exists():
                    add("P2P110_MISSING_DECISION_FILE", "warning", decision_path, "decision.md is missing.")
                else:
                    decision_text = decision_path.read_text(encoding="utf-8")
                    if not _markdown_has_section(decision_text, "Status"):
                        add(
                            "P2P111_MISSING_DECISION_STATUS",
                            "warning",
                            decision_path,
                            "decision.md is missing Status section.",
                        )
                    decision_status = (_read_markdown_section(decision_text, "Status") or "").strip("`")
                    if (
                        proposal_status in {"accepted", "rejected", "deferred"}
                        and decision_status
                        and decision_status != proposal_status
                    ):
                        add(
                            "P2P112_STATUS_MISMATCH",
                            "warning",
                            decision_path,
                            f"Proposal status is {proposal_status}, but decision status is {decision_status}.",
                            suggested_command=f"p2p proposal show {proposal_id}",
                        )

        try:
            registry_status = self.registry_status()
        except ValueError as exc:
            add(
                "P2P200_REGISTRY_STATUS_ERROR",
                "warning",
                self.p2p_dir / "registries",
                f"Could not inspect registries: {exc}",
                suggested_command="p2p registry refresh",
            )
        else:
            if registry_status.stale:
                add(
                    "P2P201_STALE_REGISTRY",
                    "warning",
                    registry_status.registries_dir,
                    "Generated registries are missing or stale.",
                    suggested_command="p2p registry refresh",
                )

        errors = sum(1 for finding in findings if finding.severity == "error")
        warnings = sum(1 for finding in findings if finding.severity == "warning")
        infos = sum(1 for finding in findings if finding.severity == "info")
        return ValidationResult(
            ok=errors == 0,
            errors=errors,
            warnings=warnings,
            infos=infos,
            findings=findings,
        )

    def readiness_profile(self, profile_id: str = DEFAULT_READINESS_PROFILE_ID) -> ReadinessProfile:
        return self._readiness_service().profile(profile_id)

    def read_proposal_readiness(self, proposal_id: str) -> ProposalReadiness:
        return self._readiness_service().read(proposal_id)

    def write_proposal_readiness(self, proposal_id: str, readiness: dict[str, object]) -> Path:
        return self._readiness_service().write(proposal_id, readiness)

    def record_proposal_readiness_override(
        self,
        proposal_id: str,
        reason: str,
        approver: str,
    ) -> Path:
        return self._readiness_service().record_override(proposal_id, reason, approver)

    def refresh_proposal_readiness(self, proposal_id: str) -> ProposalReadiness:
        return self._readiness_service().refresh(proposal_id)

    def initialize_proposal_readiness(self, proposal_id: str) -> ProposalReadiness:
        return self._readiness_service().initialize(proposal_id)

    def create_proposal(self, title: str) -> Proposal:
        return self._proposal_document_service().create(title)

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
        return self._proposal_document_service().create_with_details(
            title=title,
            problem=problem,
            context=context,
            goals=goals,
            non_goals=non_goals,
            proposal=proposal,
            acceptance_criteria=acceptance_criteria,
        )

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
        return self._proposal_decision_service().record(proposal_id, outcome, reason, approver)

    def generate_prompt(self, proposal_id: str, kind: PromptKind) -> Path:
        proposal_dir = self._find_proposal_dir(proposal_id)
        context = {
            "proposal_id": proposal_id,
            "proposal": _read_optional(proposal_dir / "proposal.md"),
            "contributions": _read_optional(proposal_dir / "contributions.yml"),
            "comments": _read_optional(proposal_dir / "comments.yml"),
            "clarifications": _read_optional(proposal_dir / "clarifications.md"),
            "decision": _read_optional(proposal_dir / "decision.md"),
            "votes": _read_optional(proposal_dir / "votes.yml"),
            "swot_analysis": _read_optional(proposal_dir / "swot-analysis.md"),
            "exploration": _read_optional(proposal_dir / "exploration.md"),
            "findings": _read_optional(proposal_dir / "findings.md"),
            "alternatives": _read_optional(proposal_dir / "alternatives.md"),
            "open_questions": _read_optional(proposal_dir / "open-questions.md"),
            "risks": _read_optional(proposal_dir / "risks.md"),
            "assumptions": _read_optional(proposal_dir / "assumptions.md"),
            "suggested_scope": _read_optional(proposal_dir / "suggested-scope.md"),
            "governance": _read_optional(self.p2p_dir / "governance" / "governance.yml"),
            "roles": _read_optional(self.p2p_dir / "governance" / "roles.yml"),
            "decision_precedents": _read_optional(
                self.p2p_dir / "governance" / "decision-precedents.yml"
            ),
            "project_overview": _read_optional(self.p2p_dir / "project" / "overview.md"),
            "project_decisions": _read_optional(self.p2p_dir / "project" / "decisions-map.yml"),
            "project_conflicts": _read_optional(self.p2p_dir / "project" / "conflicts.yml"),
            "constitution": _read_optional(self.p2p_dir / "governance" / "constitution.md"),
            "decision_rules": _read_optional(self.p2p_dir / "governance" / "decision-rules.md"),
            "relevance_criteria": _read_optional(self.p2p_dir / "governance" / "relevance-criteria.md"),
        }
        renderers = {
            "explore": render_explore_prompt,
            "digest": render_digest_prompt,
            "clarify": render_clarify_prompt,
            "synthesize": render_synthesize_prompt,
            "plan": render_plan_prompt,
            "tasks": render_tasks_prompt,
            "swot": render_swot_prompt,
            "impact": render_impact_prompt,
        }
        output_dir = self.p2p_dir / "prompts" / proposal_id
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{kind}.prompt.md"
        path.write_text(renderers[kind](context), encoding="utf-8")
        return path.relative_to(self.root)

    def import_exploration(self, proposal_id: str, source: Path) -> list[Path]:
        proposal_dir = self._find_proposal_dir(proposal_id)
        source = source.resolve()
        imported: list[Path] = []
        if source.is_dir():
            for filename in EXPLORATION_ARTIFACTS:
                source_path = source / filename
                if source_path.exists():
                    target = proposal_dir / filename
                    shutil.copyfile(source_path, target)
                    imported.append(target.relative_to(self.root))
        elif source.is_file():
            target = proposal_dir / "exploration.md"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            imported.append(target.relative_to(self.root))
        else:
            raise ValueError(f"Exploration source not found: {source}")
        if not imported:
            raise ValueError(f"No exploration artifacts found in: {source}")
        return imported

    def exploration_status(self, proposal_id: str) -> ExplorationStatus:
        proposal_dir = self._find_proposal_dir(proposal_id)
        artifacts: list[ExplorationArtifactStatus] = []
        for filename in EXPLORATION_ARTIFACTS:
            path = proposal_dir / filename
            text = _read_optional(path)
            artifacts.append(
                ExplorationArtifactStatus(
                    filename=filename,
                    exists=path.exists(),
                    has_content=_has_meaningful_content(text),
                    quality_state=_artifact_quality_state(path, text),
                )
            )
        questions_text = _read_optional(proposal_dir / "open-questions.md")
        unresolved = _count_open_questions(questions_text)
        missing = [artifact for artifact in artifacts if not artifact.has_content]
        suggested = (
            f"p2p explore prompt {proposal_id}"
            if missing
            else f"p2p clarify prompt {proposal_id}"
        )
        return ExplorationStatus(
            proposal_id=proposal_id,
            artifacts=artifacts,
            unresolved_questions=unresolved,
            suggested_next_command=suggested,
        )

    def import_artifact(self, proposal_id: str, kind: ImportKind, source: Path) -> Path:
        proposal_dir = self._find_proposal_dir(proposal_id)
        source = source.resolve()
        if not source.is_file():
            raise ValueError(f"Import source not found: {source}")

        target_name = {
            "clarify": "clarifications.md",
            "synthesize": "proposal.md",
            "plan": "execution-plan.md",
            "tasks": "tasks.yml",
        }[kind]
        content = source.read_text(encoding="utf-8")
        if kind == "tasks":
            _validate_tasks_yaml(content)
        target = proposal_dir / target_name
        target.write_text(content, encoding="utf-8")
        return target.relative_to(self.root)

    def import_impact(self, proposal_id: str, source: Path) -> list[Path]:
        proposal_dir = self._find_proposal_dir(proposal_id)
        source = source.resolve()
        imported: list[Path] = []
        if source.is_dir():
            mappings = {
                "impact-map.yml": "impact",
                "related-proposals.yml": "related_proposals",
                "conflict-analysis.yml": "conflicts",
            }
            for filename, key in mappings.items():
                source_path = source / filename
                if source_path.exists():
                    _validate_yaml_key(source_path.read_text(encoding="utf-8"), key)
                    target = proposal_dir / filename
                    shutil.copyfile(source_path, target)
                    imported.append(target.relative_to(self.root))
        elif source.is_file():
            _validate_yaml_key(source.read_text(encoding="utf-8"), "impact")
            target = proposal_dir / "impact-map.yml"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            imported.append(target.relative_to(self.root))
        else:
            raise ValueError(f"Impact source not found: {source}")
        if not imported:
            raise ValueError(f"No impact artifacts found in: {source}")
        return imported

    def init_governance(self, mode: str) -> list[Path]:
        allowed_modes = {"owner_decides", "open_consensus", "exclusive_vote"}
        if mode not in allowed_modes:
            raise ValueError(f"Unsupported governance mode: {mode}")
        governance_dir = self.p2p_dir / "governance"
        governance_dir.mkdir(parents=True, exist_ok=True)
        files: dict[Path, str] = {
            governance_dir / "governance.yml": _yaml_dump(
                {
                    "governance": {
                        "mode": mode,
                        "status": "active",
                        "enforcement": "audit_only",
                        "default_decision_type": mode,
                    }
                }
            ),
            governance_dir / "roles.yml": _yaml_dump(
                {
                    "roles": [
                        {
                            "id": "owner",
                            "description": "Project owner or maintainer",
                            "can_decide": True,
                        }
                    ]
                }
            ),
            governance_dir / "decision-precedents.yml": _yaml_dump({"precedents": []}),
        }
        written: list[Path] = []
        for path, content in files.items():
            path.write_text(content, encoding="utf-8")
            written.append(path.relative_to(self.root))
        return written

    def governance_status(self) -> GovernanceStatus:
        governance_file = self.p2p_dir / "governance" / "governance.yml"
        roles_file = self.p2p_dir / "governance" / "roles.yml"
        precedents_file = self.p2p_dir / "governance" / "decision-precedents.yml"

        governance = _read_yaml_mapping(governance_file, default={})
        roles = _read_yaml_mapping(roles_file, default={})
        precedents = _read_yaml_mapping(precedents_file, default={})

        return GovernanceStatus(
            mode=governance.get("governance", {}).get("mode", "not_initialized"),
            roles_count=len(roles.get("roles", [])) if isinstance(roles.get("roles"), list) else 0,
            precedents_count=(
                len(precedents.get("precedents", []))
                if isinstance(precedents.get("precedents"), list)
                else 0
            ),
            governance_file=governance_file.relative_to(self.root),
        )

    def record_vote(
        self,
        proposal_id: str,
        choice: str,
        reason: str,
        voter: str,
        role: str,
    ) -> VoteStatus:
        proposal_dir = self._find_proposal_dir(proposal_id)
        path = proposal_dir / "votes.yml"
        data = _read_yaml_mapping(
            path,
            default={
                "proposal": proposal_id,
                "decision_type": "exclusive_vote",
                "status": "open",
                "votes": [],
                "result": {
                    "winner": None,
                    "decided_on": None,
                    "decision_precedent": None,
                },
            },
        )
        votes = data.setdefault("votes", [])
        if not isinstance(votes, list):
            raise ValueError("Invalid votes.yml: expected `votes` list.")
        votes.append(
            {
                "voter": voter,
                "role": role,
                "choice": choice,
                "reason": reason,
                "recorded_on": date.today().isoformat(),
            }
        )
        status = _vote_status_from_data(proposal_id, data)
        result = data.setdefault("result", {})
        result["winner"] = status.winner
        result["tied"] = status.tied
        path.write_text(_yaml_dump(data), encoding="utf-8")
        return status

    def vote_status(self, proposal_id: str) -> VoteStatus:
        proposal_dir = self._find_proposal_dir(proposal_id)
        path = proposal_dir / "votes.yml"
        data = _read_yaml_mapping(
            path,
            default={
                "proposal": proposal_id,
                "decision_type": "exclusive_vote",
                "status": "open",
                "votes": [],
                "result": {},
            },
        )
        return _vote_status_from_data(proposal_id, data)

    def record_precedent(self, proposal_id: str, title: str, reason: str) -> Path:
        self._find_proposal_dir(proposal_id)
        path = self.p2p_dir / "governance" / "decision-precedents.yml"
        data = _read_yaml_mapping(path, default={"precedents": []})
        precedents = data.setdefault("precedents", [])
        if not isinstance(precedents, list):
            raise ValueError("Invalid decision-precedents.yml: expected `precedents` list.")
        precedent_id = f"DP{len(precedents) + 1:03d}"
        precedents.append(
            {
                "id": precedent_id,
                "proposal": proposal_id,
                "title": title,
                "reason": reason,
                "recorded_on": date.today().isoformat(),
            }
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(data), encoding="utf-8")
        return path.relative_to(self.root)

    def refresh_project_state(self) -> list[Path]:
        return self._project_state_service().refresh()

    def project_state_status(self) -> ProjectStateStatus:
        return self._project_state_service().status()

    def show_project_state(self, section: str) -> str:
        return self._project_state_service().show(section)

    def create_project_brief_prompt(self) -> ProjectBriefPrompt:
        return self._project_state_service().create_brief_prompt()

    def import_project_brief(self, source: Path) -> list[Path]:
        return self._project_state_service().import_brief(source)

    def show_project_brief(self) -> str:
        return self._project_state_service().show_brief()

    def refresh_project_assessment(self) -> ProjectAssessment:
        return self._project_assessment_service().refresh()

    def show_project_assessment(self) -> ProjectAssessment:
        return self._project_assessment_service().show()

    def init_project_rubrics(self, domain: str = "generic", force: bool = False) -> ProjectRubrics:
        domain = _normalize_project_domain(domain)
        path = self.p2p_dir / "project" / "rubrics.yml"
        if path.exists() and not force:
            raise ValueError("Project rubrics already exist. Use --force to replace them.")
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = _rubrics_payload(domain)
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        domain_path = self.p2p_dir / "project" / "domain.yml"
        domain_path.write_text(_yaml_dump(_domain_state_payload(domain)), encoding="utf-8")
        project_file = self.p2p_dir / "project.yml"
        data = _read_yaml_mapping(project_file, default={})
        project = data.get("project", {})
        if not isinstance(project, dict):
            project = {}
        project["domain"] = domain
        data["project"] = project
        project_file.write_text(_yaml_dump(data), encoding="utf-8")
        return self.show_project_rubrics()

    def init_project_rubrics_preview(self, domain: str = "generic") -> list[dict[str, object]]:
        payload = _rubrics_payload(domain)
        criteria = payload.get("criteria", [])
        return [item for item in criteria if isinstance(item, dict)] if isinstance(criteria, list) else []

    def show_project_rubrics(self) -> ProjectRubrics:
        path = self.p2p_dir / "project" / "rubrics.yml"
        if not path.exists():
            raise ValueError("Project rubrics not found. Run `p2p project rubrics init` first.")
        data = _read_yaml_mapping(path, default={})
        domain = str(data.get("domain") or "generic")
        status = str(data.get("status") or "template_selected")
        template = data.get("template")
        criteria = data.get("criteria", [])
        if not isinstance(criteria, list):
            criteria = []
        return ProjectRubrics(
            path=path.relative_to(self.root),
            domain=domain,
            status=status,
            template=str(template) if template else None,
            criteria=[item for item in criteria if isinstance(item, dict)],
        )

    def refresh_definition_maturity(self) -> ProjectDefinitionMaturity:
        maturity = self._compute_definition_maturity()
        path = self.p2p_dir / "project" / "maturity-assessment.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(_definition_maturity_payload(maturity)), encoding="utf-8")
        return maturity

    def show_definition_maturity(self) -> ProjectDefinitionMaturity:
        path = self.p2p_dir / "project" / "maturity-assessment.yml"
        if not path.exists():
            raise ValueError("Project definition maturity not found. Run `p2p assess maturity refresh` first.")
        data = _read_yaml_mapping(path, default={})
        criteria = data.get("criteria", [])
        gaps = data.get("gaps", [])
        suggested = data.get("suggested_actions", [])
        return ProjectDefinitionMaturity(
            path=path.relative_to(self.root),
            generated_on=str(data.get("generated_on") or ""),
            domain=str(data.get("domain") or "generic"),
            score=int(data.get("score") or 0),
            status=str(data.get("status") or "unknown"),
            criteria=[item for item in criteria if isinstance(item, dict)] if isinstance(criteria, list) else [],
            gaps=[str(item) for item in gaps] if isinstance(gaps, list) else [],
            suggested_actions=[str(item) for item in suggested] if isinstance(suggested, list) else [],
        )

    def _compute_definition_maturity(self) -> ProjectDefinitionMaturity:
        rubrics = self.show_project_rubrics()
        evidence = self._definition_evidence_records()
        results: list[dict[str, object]] = []
        gaps: list[str] = []
        suggested_actions: list[str] = []
        scores: list[int] = []

        enabled_criteria = [
            criterion for criterion in rubrics.criteria if criterion.get("enabled") is not False
        ]
        if rubrics.status in {"unresolved", "missing"} or not enabled_criteria:
            return ProjectDefinitionMaturity(
                path=(self.p2p_dir / "project" / "maturity-assessment.yml").relative_to(self.root),
                generated_on=date.today().isoformat(),
                domain=rubrics.domain,
                score=0,
                status="rubric_missing",
                criteria=[],
                gaps=[
                    "Project definition rubric is unresolved or has no enabled criteria.",
                    "Define the project domain before assessing maturity.",
                    "Define the domain rubric and coverage criteria.",
                ],
                suggested_actions=[
                    "Define the project domain with the user and agent.",
                    "Define the project rubric and coverage criteria.",
                ],
            )

        for criterion in enabled_criteria:
            criterion_id = str(criterion.get("id") or "unknown")
            title = str(criterion.get("title") or criterion_id)
            keywords = [str(item).lower() for item in criterion.get("keywords", []) if str(item).strip()]
            matches = self._criterion_matches(evidence, keywords)
            accepted = [item for item in matches if item["state"] in {"accepted", "completed"}]
            partial = [item for item in matches if item["state"] not in {"accepted", "completed"}]
            if accepted:
                status = "covered"
                score = 100
                criterion_evidence = accepted[:5]
            elif partial:
                status = "partial"
                score = 50
                criterion_evidence = partial[:5]
                gaps.append(f"{title} is only partially covered.")
                suggested_actions.append(f"Create or accept a proposal covering {title}.")
            else:
                status = "missing"
                score = 0
                criterion_evidence = []
                gaps.append(f"{title} has no clear P2P coverage.")
                suggested_actions.append(f"Create a proposal covering {title}.")
            scores.append(score)
            results.append(
                {
                    "id": criterion_id,
                    "title": title,
                    "status": status,
                    "score": score,
                    "required": bool(criterion.get("required", True)),
                    "evidence": criterion_evidence,
                    "suggested_action": suggested_actions[-1] if status != "covered" else "",
                }
            )

        score = round(sum(scores) / len(scores)) if scores else 0
        if score >= 85:
            status = "well_defined"
        elif score >= 60:
            status = "partially_defined"
        elif score > 0:
            status = "underdefined"
        else:
            status = "not_defined"
        return ProjectDefinitionMaturity(
            path=(self.p2p_dir / "project" / "maturity-assessment.yml").relative_to(self.root),
            generated_on=date.today().isoformat(),
            domain=rubrics.domain,
            score=score,
            status=status,
            criteria=results,
            gaps=gaps,
            suggested_actions=list(dict.fromkeys(suggested_actions)),
        )

    def _definition_evidence_records(self) -> list[dict[str, str]]:
        records: list[dict[str, str]] = []
        for proposal in self.proposal_summaries():
            proposal_dir = self._find_proposal_dir(proposal.proposal_id)
            text = _read_optional(proposal_dir / "proposal.md") + "\n" + _read_optional(
                proposal_dir / "decision.md"
            )
            records.append(
                {
                    "type": "proposal",
                    "id": proposal.proposal_id,
                    "title": proposal.title,
                    "state": proposal.status,
                    "text": text.lower(),
                }
            )
        for change in self.change_set_statuses():
            change_dir = self._find_change_dir(change.change_id)
            text = _read_optional(change_dir / "change.md") + "\n" + _read_optional(
                change_dir / "tasks.yml"
            )
            records.append(
                {
                    "type": "change",
                    "id": change.change_id,
                    "title": change.title,
                    "state": change.status,
                    "text": text.lower(),
                }
            )
        return records

    def _criterion_matches(
        self,
        evidence: list[dict[str, str]],
        keywords: list[str],
    ) -> list[dict[str, str]]:
        matches: list[dict[str, str]] = []
        for item in evidence:
            text = item["text"]
            matched = [keyword for keyword in keywords if keyword in text]
            if matched:
                matches.append(
                    {
                        "type": item["type"],
                        "id": item["id"],
                        "title": item["title"],
                        "state": item["state"],
                        "matched": ", ".join(matched[:5]),
                    }
                )
        return matches

    def _compute_project_assessment(self) -> ProjectAssessment:
        return self._project_assessment_service().compute()

    def context_packet(self, budget: str = "small", target: str | None = None) -> ContextPacket:
        budget = budget.strip().lower()
        if budget not in {"small", "medium"}:
            raise ValueError("Context budget must be small or medium")
        normalized_target = target.strip().upper() if target else None
        validation = self.validate()
        registry_status = self.registry_status()
        project_status = self.project_state_status()
        proposals = self.proposal_summaries()
        choices = self.choice_statuses()
        changes = self.change_set_statuses()
        works = self.work_summaries()
        next_actions = self.next_actions(limit=3)

        current_state = {
            "project": self._project_name(),
            "validation": {
                "ok": validation.ok,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
            "registries_stale": registry_status.stale,
            "accepted_proposals": project_status.accepted_proposals,
            "proposals": len(proposals),
            "draft_proposals": len([proposal for proposal in proposals if proposal.status == "draft"]),
            "choices": len(choices),
            "open_choices": len(
                [
                    choice
                    for choice in choices
                    if choice.status in {"open", "draft", "pending"} and not choice.selected_option
                ]
            ),
            "changes": len(changes),
            "active_changes": len(
                [
                    change
                    for change in changes
                    if change.status not in {"completed", "cancelled", "superseded"}
                ]
            ),
            "work_items": len(works),
            "operational_brief_available": project_status.operational_brief_available,
        }

        relevant_artifacts = (
            [self._context_artifact(normalized_target, budget)] if normalized_target else self._default_context_artifacts()
        )
        allowed_commands = self._context_allowed_commands(normalized_target)
        bounded_next_step = (
            allowed_commands[0]
            if normalized_target and allowed_commands
            else next_actions[0].command
            if next_actions and next_actions[0].command
            else "p2p next --top 1"
        )
        notes = [
            "Read compact context first; read full artifacts only by explicit ID.",
            "Owner-controlled governance decisions still require explicit owner instruction.",
        ]
        if budget == "small":
            notes.append("Small budget omits full document bodies and favors IDs, statuses, paths, and commands.")

        return ContextPacket(
            budget=budget,
            target=normalized_target,
            current_state=current_state,
            next_actions=[
                {
                    "id": action.action_id,
                    "priority": action.priority,
                    "kind": action.kind,
                    "target": action.target,
                    "reason": action.reason,
                    "command": action.command,
                }
                for action in next_actions
            ],
            relevant_artifacts=relevant_artifacts,
            allowed_commands=allowed_commands,
            do_not_read=[
                "Do not scan all .p2p/ directories.",
                "Do not read all registries when this context packet is sufficient.",
                "Do not read all proposal, choice, change, or work files without a target ID.",
                "Do not inspect source code or Git history unless the task explicitly requires implementation details.",
                "Do not explain saved P2P artifacts from conversation memory; use show/context commands.",
            ],
            bounded_next_step=bounded_next_step,
            notes=notes,
        )

    def _default_context_artifacts(self) -> list[dict[str, object]]:
        artifacts: list[dict[str, object]] = []
        for proposal in self.proposal_summaries(status="draft")[:3]:
            artifacts.append(
                {
                    "type": "proposal",
                    "id": proposal.proposal_id,
                    "status": proposal.status,
                    "title": proposal.title,
                    "path": proposal.slug,
                    "command": f"p2p proposal show {proposal.proposal_id}",
                }
            )
        for choice in self.choice_statuses()[:3]:
            if choice.status in {"open", "draft", "pending"} and not choice.selected_option:
                artifacts.append(
                    {
                        "type": "choice",
                        "id": choice.choice_id,
                        "status": choice.status,
                        "title": choice.title,
                        "path": choice.path,
                        "command": f"p2p choice show {choice.choice_id}",
                    }
                )
        for change in self.change_set_statuses()[:3]:
            if change.status not in {"completed", "cancelled", "superseded"}:
                artifacts.append(
                    {
                        "type": "change",
                        "id": change.change_id,
                        "status": change.status,
                        "title": change.title,
                        "path": change.path,
                        "command": f"p2p change show {change.change_id}",
                    }
                )
        return artifacts[:5]

    def _context_artifact(self, target: str, budget: str) -> dict[str, object]:
        if target.startswith("PROP-"):
            detail = self.show_proposal(target)
            artifact: dict[str, object] = {
                "type": "proposal",
                "id": detail.proposal_id,
                "status": detail.status,
                "title": detail.title,
                "decision_status": detail.decision_status,
                "path": detail.path,
                "command": f"p2p proposal show {detail.proposal_id}",
            }
            if budget == "medium":
                artifact["problem"] = _short_text(detail.problem)
                artifact["proposal"] = _short_text(detail.proposal)
            return artifact
        if target.startswith("CHANGE-"):
            detail = self.show_change_set(target)
            artifact = {
                "type": "change",
                "id": detail.change_id,
                "status": detail.status,
                "title": detail.title,
                "path": detail.path,
                "command": f"p2p change show {detail.change_id}",
            }
            if budget == "medium":
                artifact["summary"] = _short_text(detail.summary)
            return artifact
        if target.startswith("CHOICE-"):
            detail = self.show_choice(target)
            return {
                "type": "choice",
                "id": detail.choice_id,
                "status": detail.status,
                "title": detail.title,
                "selected_option": detail.selected_option,
                "options_count": len(detail.options),
                "path": detail.path,
                "command": f"p2p choice show {detail.choice_id}",
            }
        if target.startswith("WORK-"):
            detail = self.show_work(target)
            return {
                "type": "work",
                "id": detail.work_id,
                "status": detail.status,
                "change_id": detail.change_id,
                "target": detail.target,
                "branch_name": detail.branch_name,
                "path": detail.path,
                "command": f"p2p work show {detail.work_id}",
            }
        raise ValueError("Context target must start with PROP-, CHANGE-, CHOICE-, or WORK-")

    def _context_allowed_commands(self, target: str | None) -> list[str]:
        commands = [
            "p2p context --budget small",
            "p2p next --top 1",
            "p2p validate",
            "p2p assess show",
        ]
        if target is None:
            commands.extend(
                [
                    "p2p proposal list",
                    "p2p choice list",
                    "p2p change status",
                    "p2p work status",
                ]
            )
            return commands
        if target.startswith("PROP-"):
            return [f"p2p proposal show {target}", f"p2p context --target {target} --budget medium", *commands]
        if target.startswith("CHANGE-"):
            return [f"p2p change show {target}", f"p2p context --target {target} --budget medium", *commands]
        if target.startswith("CHOICE-"):
            return [f"p2p choice show {target}", f"p2p context --target {target} --budget medium", *commands]
        if target.startswith("WORK-"):
            return [f"p2p work show {target}", f"p2p context --target {target} --budget medium", *commands]
        return commands

    def refresh_software_spec(self, change_id: str) -> SoftwareSpecStatus:
        return self._software_spec_service().refresh(change_id)

    def software_spec_statuses(self) -> list[SoftwareSpecStatus]:
        return self._software_spec_service().statuses()

    def show_software_spec(self, change_id: str) -> str:
        return self._software_spec_service().show(change_id)

    def create_software_spec_prompt(self, change_id: str) -> SoftwareSpecPrompt:
        return self._software_spec_service().create_prompt(change_id)

    def import_software_spec(self, change_id: str, source: Path) -> list[Path]:
        return self._software_spec_service().import_spec(change_id, source)

    def export_software_spec(self, change_id: str, target: str) -> SoftwareSpecExportStatus:
        return self._spec_export_service().export(change_id, target)

    def software_spec_export_statuses(self) -> list[SoftwareSpecExportStatus]:
        return self._spec_export_service().statuses()

    def show_software_spec_export(self, change_id: str, target: str) -> str:
        return self._spec_export_service().show(change_id, target)

    def validate_software_spec_export(self, change_id: str, target: str) -> SoftwareSpecExportValidation:
        return self._spec_export_service().validate(change_id, target)

    def _project_definition(self, change_id: str, change: ChangeSetDetail, spec_dir: Path) -> dict[str, object]:
        return self._spec_export_service().project_definition(change_id, change, spec_dir)

    def create_work_plan(self, change_id: str, target: str) -> WorkDetail:
        return self._work_planning_service().create_plan(change_id, target)

    def work_statuses(self) -> list[WorkStatus]:
        return self._work_planning_service().statuses()

    def work_summaries(self) -> list[WorkSummary]:
        return self._work_planning_service().summaries()

    def show_work(self, work_id: str) -> WorkDetail:
        return self._work_planning_service().show(work_id)

    def _work_summary_from_manifest(
        self,
        manifest: dict[str, object],
        path: Path,
        *,
        scanned: bool,
    ) -> WorkSummary:
        return self._work_planning_service().summary_from_manifest(manifest, path, scanned=scanned)

    def _work_summary_from_scan(self, item: dict[str, object]) -> WorkSummary:
        return self._work_planning_service().summary_from_scan(item)

    def branch_work(self, work_id: str) -> WorkBranch:
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "planned":
            raise ValueError(f"Work item must be planned before branching. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")
        if not branch_name.startswith("p2p/work/"):
            raise ValueError("Invalid Work manifest: git.branch_name must start with p2p/work/")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot create managed work branch outside a Git repository")
        if not git_status.branch:
            raise ValueError("Cannot create managed work branch from detached HEAD")
        if not git_status.is_clean:
            raise ValueError("Cannot create managed work branch with uncommitted changes")

        base_branch = str(git.get("base_branch") or git_status.branch)
        if git_status.branch != base_branch:
            raise ValueError(
                f"Cannot create managed work branch from {git_status.branch}; expected base branch {base_branch}"
            )
        if branch_exists(self.root, branch_name):
            raise ValueError(f"Managed work branch already exists: {branch_name}")

        base_commit = head_commit(self.root)
        if base_commit is None:
            raise ValueError("Cannot resolve current Git commit")
        if not create_and_checkout_branch(self.root, branch_name):
            raise ValueError(f"Failed to create managed work branch: {branch_name}")
        new_head_commit = head_commit(self.root)
        if new_head_commit is None:
            raise ValueError("Cannot resolve managed work branch commit")

        manifest["status"] = "branched"
        levels = manifest.get("managed_git_levels", [])
        if isinstance(levels, list):
            for level in levels:
                if isinstance(level, dict) and level.get("level") == 2:
                    level["enabled"] = True
        git["mode"] = "managed_branch"
        git["base_branch"] = base_branch
        git["base_commit"] = base_commit
        git["head_commit"] = new_head_commit
        git["current_branch"] = branch_name
        git["branched_at"] = date.today().isoformat()
        manifest["git"] = git
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        return WorkBranch(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            base_branch=base_branch,
            base_commit=base_commit,
            head_commit=new_head_commit,
            path=work_dir.relative_to(self.root),
        )

    def retire_work(self, work_id: str, reason: str) -> WorkRetire:
        reason = reason.strip()
        if not reason:
            raise ValueError("Work retire reason is required")
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "planned":
            raise ValueError(f"Work item must be planned before retire. Current status: {status}")

        manifest["status"] = "retired"
        manifest["retirement"] = {
            "reason": reason,
            "retired_at": date.today().isoformat(),
            "mode": "metadata_only",
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")
        return WorkRetire(
            work_id=str(manifest.get("work_id") or work_id),
            status="retired",
            reason=reason,
            path=work_dir.relative_to(self.root),
        )

    def submit_work(self, work_id: str) -> WorkSubmit:
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest_rel = manifest_path.relative_to(self.root).as_posix()
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "branched":
            raise ValueError(f"Work item must be branched before submit. Current status: {status}")

        source = manifest.get("source", {})
        change_id = str(source.get("change") if isinstance(source, dict) else "unknown")
        git = manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot submit managed work outside a Git repository")
        if git_status.branch != branch_name:
            raise ValueError(f"Cannot submit managed work from {git_status.branch}; expected branch {branch_name}")

        changed = changed_files(self.root)
        if not changed:
            raise ValueError("Cannot submit managed work without changes")
        work_changes = [path for path in changed if path != manifest_rel]
        if not work_changes:
            raise ValueError("Cannot submit managed work with only Work manifest changes")

        manifest["status"] = "submitted"
        levels = manifest.get("managed_git_levels", [])
        if isinstance(levels, list):
            for level in levels:
                if isinstance(level, dict) and level.get("level") == 3:
                    level["enabled"] = True
        git["mode"] = "managed_submit"
        git["submitted_at"] = date.today().isoformat()
        manifest["git"] = git
        manifest["submission"] = {
            "mode": "local_commit",
            "pushed": False,
            "merged": False,
            "changed_files": changed,
            "work_changes": work_changes,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        message = f"P2P submit {work_id}: {change_id}"
        commit = commit_all(self.root, message)
        if commit is None:
            raise ValueError("Failed to create managed work submit commit")

        return WorkSubmit(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            commit=commit,
            changed_files=work_changes,
            path=work_dir.relative_to(self.root),
        )

    def review_work(self, work_id: str) -> WorkReview:
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "submitted":
            raise ValueError(f"Work item must be submitted before review. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot request managed work review outside a Git repository")
        if git_status.branch != branch_name:
            raise ValueError(
                f"Cannot request managed work review from {git_status.branch}; expected branch {branch_name}"
            )
        if not git_status.is_clean:
            raise ValueError("Cannot request managed work review with uncommitted changes")

        review_commit = head_commit(self.root)
        if review_commit is None:
            raise ValueError("Cannot resolve managed work review commit")

        manifest["status"] = "review_requested"
        levels = manifest.get("managed_git_levels", [])
        if isinstance(levels, list):
            for level in levels:
                if isinstance(level, dict) and level.get("level") == 4:
                    level["enabled"] = True
        git["mode"] = "managed_review"
        git["review_requested_at"] = date.today().isoformat()
        manifest["git"] = git
        manifest["review"] = {
            "mode": "local_review",
            "review_commit": review_commit,
            "pushed": False,
            "pull_request": None,
            "merged": False,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        metadata_commit = commit_all(self.root, f"P2P review {work_id}")
        if metadata_commit is None:
            raise ValueError("Failed to create managed work review metadata commit")

        return WorkReview(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            review_commit=review_commit,
            metadata_commit=metadata_commit,
            path=work_dir.relative_to(self.root),
        )

    def publish_work(self, work_id: str, remote: str = "origin") -> WorkPublish:
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "review_requested":
            raise ValueError(f"Work item must be review_requested before publish. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot publish managed work outside a Git repository")
        if git_status.branch != branch_name:
            raise ValueError(f"Cannot publish managed work from {git_status.branch}; expected branch {branch_name}")
        if not git_status.is_clean:
            raise ValueError("Cannot publish managed work with uncommitted changes")

        resolved_remote_url = remote_url(self.root, remote)
        if resolved_remote_url is None:
            raise ValueError(f"Cannot publish managed work: Git remote not found: {remote}")

        review = manifest.get("review", {})
        review_commit = str(review.get("review_commit") if isinstance(review, dict) else "")
        if not review_commit:
            raise ValueError("Invalid Work manifest: review.review_commit is required before publish")

        manifest["status"] = "published"
        git["mode"] = "managed_publish"
        git["published_at"] = date.today().isoformat()
        manifest["git"] = git
        manifest["publish"] = {
            "mode": "remote_branch",
            "remote": remote,
            "remote_url": resolved_remote_url,
            "remote_branch": branch_name,
            "review_commit": review_commit,
            "pull_request": None,
            "merged": False,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        publish_commit = commit_all(self.root, f"P2P publish {work_id}")
        if publish_commit is None:
            raise ValueError("Failed to create managed work publish metadata commit")
        if not push_branch(self.root, branch_name, remote):
            raise ValueError(f"Failed to push managed work branch to {remote}: {branch_name}")

        return WorkPublish(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            remote=remote,
            remote_url=resolved_remote_url,
            publish_commit=publish_commit,
            path=work_dir.relative_to(self.root),
        )

    def request_external_work_review(
        self,
        work_id: str,
        provider: str | None = None,
    ) -> WorkReviewRequest:
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "published":
            raise ValueError(f"Work item must be published before external review request. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot request external work review outside a Git repository")
        if git_status.branch != branch_name:
            raise ValueError(
                f"Cannot request external work review from {git_status.branch}; expected branch {branch_name}"
            )
        if not git_status.is_clean:
            raise ValueError("Cannot request external work review with uncommitted changes")

        publish = manifest.get("publish", {})
        if not isinstance(publish, dict):
            raise ValueError("Invalid Work manifest: publish metadata is required before external review request")
        remote = str(publish.get("remote") or "origin")
        resolved_remote_url = str(publish.get("remote_url") or "")
        if not resolved_remote_url:
            resolved_remote_url = remote_url(self.root, remote) or ""
        if not resolved_remote_url:
            raise ValueError(f"Cannot request external work review: Git remote not found: {remote}")

        profile = self.remote_profile()
        if profile.url:
            resolved_remote_url = profile.url
        selected_provider = (provider or profile.provider or "generic").strip().lower()
        if selected_provider == "local":
            selected_provider = "generic"
        if selected_provider not in {"generic", "github", "gitlab"}:
            raise ValueError("External review provider must be generic, github, or gitlab")

        suggested_next = _review_request_suggestion(
            provider=selected_provider,
            remote_url=resolved_remote_url,
            branch_name=branch_name,
        )
        manifest["external_review"] = {
            "mode": "provider_advisory",
            "provider": selected_provider,
            "remote": remote,
            "remote_url": resolved_remote_url,
            "remote_branch": branch_name,
            "opens_external_request": False,
            "requested_at": date.today().isoformat(),
            "suggested_next": suggested_next,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        metadata_commit = commit_all(self.root, f"P2P request review {work_id}")
        if metadata_commit is None:
            raise ValueError("Failed to create external review request metadata commit")

        return WorkReviewRequest(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            provider=selected_provider,
            remote=remote,
            remote_url=resolved_remote_url,
            metadata_commit=metadata_commit,
            suggested_next=suggested_next,
            path=work_dir.relative_to(self.root),
        )

    def accept_work(self, work_id: str) -> WorkAccept | WorkAcceptConflict:
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        local_manifest = _read_yaml_mapping(manifest_path, default={})
        git = local_manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")
        base_branch = str(git.get("base_branch") or "main")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot accept managed work outside a Git repository")
        if git_status.branch != base_branch:
            raise ValueError(f"Cannot accept managed work from {git_status.branch}; expected base branch {base_branch}")
        if not git_status.is_clean:
            raise ValueError("Cannot accept managed work with uncommitted changes")
        if not branch_exists(self.root, branch_name):
            raise ValueError(f"Managed work branch not found: {branch_name}")

        manifest_rel = manifest_path.relative_to(self.root).as_posix()
        branch_file = read_file_at_ref(self.root, branch_name, manifest_rel)
        if branch_file is None:
            raise ValueError(f"Managed work branch does not contain manifest: {manifest_rel}")
        try:
            branch_manifest = yaml.safe_load(branch_file.content) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid Work manifest on branch {branch_name}") from exc
        if not isinstance(branch_manifest, dict):
            raise ValueError(f"Invalid Work manifest on branch {branch_name}")
        status = str(branch_manifest.get("status") or "unknown")
        if status != "published":
            raise ValueError(f"Work item must be published before accept. Current status: {status}")

        if not merge_branch_no_commit(self.root, branch_name):
            conflicts = conflicted_files(self.root)
            if not conflicts:
                raise ValueError(f"Failed to merge managed work branch: {branch_name}")
            conflict_manifest = dict(branch_manifest)
            conflict_git = conflict_manifest.get("git", {})
            if not isinstance(conflict_git, dict):
                conflict_git = {}
            conflict_manifest["status"] = "merge_conflict"
            conflict_git["mode"] = "managed_accept_conflict"
            conflict_git["merge_conflict_at"] = date.today().isoformat()
            conflict_manifest["git"] = conflict_git
            conflict_manifest["merge_conflict"] = {
                "source_branch": branch_name,
                "base_branch": base_branch,
                "conflicted_files": conflicts,
                "continue_command": f"p2p work accept --continue {work_id}",
                "abort_command": f"p2p work accept --abort {work_id}",
            }
            manifest_path.write_text(_yaml_dump(conflict_manifest), encoding="utf-8")
            return WorkAcceptConflict(
                work_id=str(conflict_manifest.get("work_id") or work_id),
                branch_name=branch_name,
                base_branch=base_branch,
                conflicted_files=conflicts,
                path=work_dir.relative_to(self.root),
            )

        merged_manifest = _read_yaml_mapping(manifest_path, default={})
        merged_git = merged_manifest.get("git", {})
        if not isinstance(merged_git, dict):
            merged_git = {}
        merged_manifest["status"] = "accepted"
        levels = merged_manifest.get("managed_git_levels", [])
        if isinstance(levels, list):
            for level in levels:
                if isinstance(level, dict) and level.get("level") == 5:
                    level["enabled"] = True
        merged_git["mode"] = "managed_accept"
        merged_git["accepted_at"] = date.today().isoformat()
        merged_manifest["git"] = merged_git
        merged_manifest["acceptance"] = {
            "mode": "local_merge",
            "source_branch": branch_name,
            "merged_into": base_branch,
            "pushed": False,
            "cleanup": False,
        }
        manifest_path.write_text(_yaml_dump(merged_manifest), encoding="utf-8")

        merge_commit = commit_all(self.root, f"P2P accept {work_id}")
        if merge_commit is None:
            raise ValueError("Failed to create managed work accept merge commit")
        if not checkout_branch(self.root, base_branch):
            raise ValueError(f"Failed to stay on base branch after accept: {base_branch}")

        return WorkAccept(
            work_id=str(merged_manifest.get("work_id") or work_id),
            branch_name=branch_name,
            base_branch=base_branch,
            merge_commit=merge_commit,
            path=work_dir.relative_to(self.root),
        )

    def continue_accept_work(self, work_id: str) -> WorkAccept:
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "merge_conflict":
            raise ValueError(f"Work item must be merge_conflict before accept --continue. Current status: {status}")
        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot continue managed work accept outside a Git repository")
        if not merge_in_progress(self.root):
            raise ValueError("Cannot continue managed work accept: no merge is in progress")
        unresolved = [path for path in conflicted_files(self.root) if _file_has_conflict_markers(self.root / path)]
        if unresolved:
            raise ValueError("Cannot continue managed work accept with unresolved conflicts: " + ", ".join(unresolved))
        stage_all(self.root)
        conflicts = conflicted_files(self.root)
        if conflicts:
            raise ValueError("Cannot continue managed work accept with unresolved conflicts: " + ", ".join(conflicts))

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            git = {}
        conflict = manifest.get("merge_conflict", {})
        if not isinstance(conflict, dict):
            conflict = {}
        branch_name = str(conflict.get("source_branch") or git.get("branch_name") or "")
        base_branch = str(conflict.get("base_branch") or git.get("base_branch") or git_status.branch or "main")
        manifest["status"] = "accepted"
        levels = manifest.get("managed_git_levels", [])
        if isinstance(levels, list):
            for level in levels:
                if isinstance(level, dict) and level.get("level") == 5:
                    level["enabled"] = True
        git["mode"] = "managed_accept"
        git["accepted_at"] = date.today().isoformat()
        manifest["git"] = git
        manifest.pop("merge_conflict", None)
        manifest["acceptance"] = {
            "mode": "local_merge",
            "source_branch": branch_name,
            "merged_into": base_branch,
            "pushed": False,
            "cleanup": False,
            "resolved_conflict": True,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")
        merge_commit = commit_all(self.root, f"P2P accept {work_id}")
        if merge_commit is None:
            raise ValueError("Failed to create managed work accept merge commit")
        return WorkAccept(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            base_branch=base_branch,
            merge_commit=merge_commit,
            path=work_dir.relative_to(self.root),
        )

    def abort_accept_work(self, work_id: str) -> WorkDetail:
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "merge_conflict":
            raise ValueError(f"Work item must be merge_conflict before accept --abort. Current status: {status}")
        conflict = manifest.get("merge_conflict", {})
        if not isinstance(conflict, dict):
            conflict = {}
        manifest_rel = manifest_path.relative_to(self.root).as_posix()
        if merge_in_progress(self.root):
            restore_path(self.root, manifest_rel)
            if not abort_merge(self.root):
                raise ValueError("Failed to abort managed work merge")
        restored = _read_yaml_mapping(manifest_path, default=manifest)
        restored["status"] = "published"
        git = restored.get("git", {})
        if not isinstance(git, dict):
            git = {}
        git["mode"] = "managed_publish"
        git["accept_aborted_at"] = date.today().isoformat()
        restored["git"] = git
        restored.pop("merge_conflict", None)
        restored["acceptance_abort"] = {
            "source_branch": str(conflict.get("source_branch") or git.get("branch_name") or ""),
            "base_branch": str(conflict.get("base_branch") or git.get("base_branch") or "main"),
            "aborted": True,
        }
        manifest_path.write_text(_yaml_dump(restored), encoding="utf-8")
        if commit_all(self.root, f"P2P abort accept {work_id}") is None:
            raise ValueError("Failed to create managed work accept abort commit")
        return self.show_work(work_id)

    def finalize_work(self, work_id: str, remote: str = "origin") -> WorkFinalize:
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "accepted":
            raise ValueError(f"Work item must be accepted before finalize. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            git = {}
        acceptance = manifest.get("acceptance", {})
        if not isinstance(acceptance, dict):
            acceptance = {}
        base_branch = str(acceptance.get("merged_into") or git.get("base_branch") or "main")

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot finalize managed work outside a Git repository")
        if git_status.branch != base_branch:
            raise ValueError(f"Cannot finalize managed work from {git_status.branch}; expected base branch {base_branch}")
        if not git_status.is_clean:
            raise ValueError("Cannot finalize managed work with uncommitted changes")

        resolved_remote_url = remote_url(self.root, remote)
        if resolved_remote_url is None:
            raise ValueError(f"Cannot finalize managed work: Git remote not found: {remote}")

        manifest["status"] = "finalized"
        git["mode"] = "managed_finalize"
        git["finalized_at"] = date.today().isoformat()
        manifest["git"] = git
        acceptance["pushed"] = True
        manifest["acceptance"] = acceptance
        manifest["finalize"] = {
            "mode": "base_branch_push",
            "remote": remote,
            "remote_url": resolved_remote_url,
            "base_branch": base_branch,
            "cleanup": False,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        finalize_commit = commit_all(self.root, f"P2P finalize {work_id}")
        if finalize_commit is None:
            raise ValueError("Failed to create managed work finalize commit")
        if not push_branch(self.root, base_branch, remote):
            raise ValueError(f"Failed to push base branch to {remote}: {base_branch}")

        return WorkFinalize(
            work_id=str(manifest.get("work_id") or work_id),
            base_branch=base_branch,
            remote=remote,
            remote_url=resolved_remote_url,
            finalize_commit=finalize_commit,
            path=work_dir.relative_to(self.root),
        )

    def cleanup_work(self, work_id: str, delete_remote: bool = False, remote: str = "origin") -> WorkCleanup:
        work_dir = self._find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "finalized":
            raise ValueError(f"Work item must be finalized before cleanup. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            git = {}
        finalize = manifest.get("finalize", {})
        if not isinstance(finalize, dict):
            finalize = {}
        publish = manifest.get("publish", {})
        if not isinstance(publish, dict):
            publish = {}
        acceptance = manifest.get("acceptance", {})
        if not isinstance(acceptance, dict):
            acceptance = {}

        branch_name = str(
            acceptance.get("source_branch")
            or publish.get("remote_branch")
            or git.get("branch_name")
            or ""
        )
        if not branch_name:
            raise ValueError("Invalid Work manifest: managed branch is required before cleanup")
        base_branch = str(finalize.get("base_branch") or acceptance.get("merged_into") or git.get("base_branch") or "main")
        remote = str(finalize.get("remote") or publish.get("remote") or remote)

        git_status = get_git_status(self.root)
        if not git_status.is_repository:
            raise ValueError("Cannot cleanup managed work outside a Git repository")
        if git_status.branch != base_branch:
            raise ValueError(f"Cannot cleanup managed work from {git_status.branch}; expected base branch {base_branch}")
        if not git_status.is_clean:
            raise ValueError("Cannot cleanup managed work with uncommitted changes")
        if not branch_exists(self.root, branch_name):
            raise ValueError(f"Managed work branch not found: {branch_name}")

        resolved_remote_url = remote_url(self.root, remote)
        if resolved_remote_url is None:
            raise ValueError(f"Cannot cleanup managed work: Git remote not found: {remote}")

        if not delete_local_branch(self.root, branch_name):
            raise ValueError(f"Failed to delete local managed work branch: {branch_name}")
        remote_deleted = False
        if delete_remote:
            if not delete_remote_branch(self.root, branch_name, remote):
                raise ValueError(f"Failed to delete remote managed work branch from {remote}: {branch_name}")
            remote_deleted = True

        manifest["status"] = "cleaned"
        git["mode"] = "managed_cleanup"
        git["cleaned_at"] = date.today().isoformat()
        manifest["git"] = git
        finalize["cleanup"] = True
        manifest["finalize"] = finalize
        manifest["cleanup"] = {
            "mode": "branch_cleanup",
            "source_branch": branch_name,
            "base_branch": base_branch,
            "remote": remote,
            "remote_url": resolved_remote_url,
            "local_deleted": True,
            "remote_deleted": remote_deleted,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        cleanup_commit = commit_all(self.root, f"P2P cleanup {work_id}")
        if cleanup_commit is None:
            raise ValueError("Failed to create managed work cleanup commit")
        if not push_branch(self.root, base_branch, remote):
            raise ValueError(f"Failed to push cleanup metadata to {remote}: {base_branch}")

        return WorkCleanup(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            base_branch=base_branch,
            remote=remote,
            cleanup_commit=cleanup_commit,
            local_deleted=True,
            remote_deleted=remote_deleted,
            path=work_dir.relative_to(self.root),
        )

    def _scanned_work_items(self) -> list[dict[str, object]]:
        path = self.p2p_dir / "registries" / "work.yml"
        data = _read_yaml_mapping(path, default={"work_items": []})
        items = data.get("work_items", [])
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]

    def scan_work_branches(self) -> WorkScan:
        branches = list_local_work_branches(self.root)
        items: list[dict[str, object]] = []
        for branch in branches:
            manifest_paths = [
                path
                for path in list_files_at_ref(self.root, branch, ".p2p/work")
                if re.match(r"\.p2p/work/WORK-\d{3}/manifest\.yml$", path)
            ]
            for manifest_path in manifest_paths:
                git_file = read_file_at_ref(self.root, branch, manifest_path)
                if git_file is None:
                    continue
                try:
                    manifest = yaml.safe_load(git_file.content) or {}
                except yaml.YAMLError:
                    continue
                if not isinstance(manifest, dict):
                    continue
                source = manifest.get("source", {})
                handoff = manifest.get("handoff", {})
                git = manifest.get("git", {})
                items.append(
                    {
                        "work_id": str(manifest.get("work_id") or Path(manifest_path).parent.name),
                        "status": str(manifest.get("status") or "unknown"),
                        "change": str(source.get("change") if isinstance(source, dict) else "unknown"),
                        "target": str(handoff.get("target") if isinstance(handoff, dict) else "none"),
                        "branch": branch,
                        "branch_name": str(git.get("branch_name") if isinstance(git, dict) else branch),
                        "path": manifest_path,
                    }
                )
        registry_path = self.p2p_dir / "registries" / "work.yml"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            _yaml_dump({"scanned_branches": branches, "work_items": items}),
            encoding="utf-8",
        )
        return WorkScan(
            scanned_branches=branches,
            work_items=items,
            path=registry_path.relative_to(self.root),
        )

    def next_actions(self, limit: int | None = None) -> list[NextAction]:
        actions = self._dedupe_next_actions(
            self._active_choice_blocker_actions()
            + self._next_actions_from_project_file()
            + self._fallback_next_actions()
        )
        if limit is not None:
            return actions[: max(limit, 0)]
        return actions

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
        kind = kind.strip()
        if not kind:
            raise ValueError("Next action kind is required")
        reason = reason.strip()
        if not reason:
            raise ValueError("Next action reason is required")
        payload = self._read_next_actions_payload()
        records = payload.setdefault("next_actions", [])
        if not isinstance(records, list):
            raise ValueError("Invalid next-actions.yml: next_actions must be a list")
        existing_ids = {
            str(record.get("id") or "")
            for record in records
            if isinstance(record, dict)
        }
        selected_id = action_id.strip() if action_id else self._next_curated_next_action_id(records)
        if selected_id in existing_ids:
            raise ValueError(f"Next action already exists: {selected_id}")
        record = {
            "id": selected_id,
            "priority": priority.strip() or "medium",
            "kind": kind,
            "target": target.strip(),
            "reason": reason,
            "command": command.strip(),
        }
        records.append(record)
        self._write_next_actions_payload(payload)
        return self._next_action_from_record(record, self._next_actions_path(), len(records))

    def next_action_complete(self, action_id: str, reason: str) -> dict[str, object]:
        return self._close_next_action(action_id, "completed", reason)

    def next_action_retire(self, action_id: str, reason: str) -> dict[str, object]:
        return self._close_next_action(action_id, "retired", reason)

    def next_actions_refresh(self) -> dict[str, object]:
        payload = self._read_next_actions_payload()
        records = payload.setdefault("next_actions", [])
        if not isinstance(records, list):
            raise ValueError("Invalid next-actions.yml: next_actions must be a list")
        normalized = [
            self._normalize_next_action_record(record, index)
            for index, record in enumerate(records, start=1)
            if isinstance(record, dict)
        ]
        payload["next_actions"] = normalized
        self._write_next_actions_payload(payload)
        generated = self._dedupe_next_actions(self._active_choice_blocker_actions() + self._fallback_next_actions())
        return {
            "active_curated": len(normalized),
            "generated": len(generated),
            "path": str(self._next_actions_path().relative_to(self.root)),
        }

    def record_conflict(
        self,
        proposals: list[str],
        conflict_type: str,
        reason: str,
        winner: str | None,
    ) -> ConflictStatus:
        if len(proposals) < 2:
            raise ValueError("At least two proposals are required to record a conflict.")
        for proposal_id in proposals:
            self._find_proposal_dir(proposal_id)
        if winner is not None and winner not in proposals:
            raise ValueError("Conflict winner must be one of the conflicting proposals.")

        path = self.p2p_dir / "project" / "conflicts.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = _read_yaml_mapping(path, default={"conflicts": []})
        conflicts = data.setdefault("conflicts", [])
        if not isinstance(conflicts, list):
            raise ValueError("Invalid conflicts.yml: expected `conflicts` list.")
        conflict_id = f"CONFLICT-{len(conflicts) + 1:03d}"
        conflicts.append(
            {
                "id": conflict_id,
                "type": conflict_type,
                "proposals": proposals,
                "winner": winner,
                "rejected": [proposal for proposal in proposals if winner and proposal != winner],
                "reason": reason,
                "recorded_on": date.today().isoformat(),
            }
        )
        path.write_text(_yaml_dump(data), encoding="utf-8")
        return self.conflict_status()

    def conflict_status(self) -> ConflictStatus:
        path = self.p2p_dir / "project" / "conflicts.yml"
        data = _read_yaml_mapping(path, default={"conflicts": []})
        conflicts = data.get("conflicts", [])
        if not isinstance(conflicts, list):
            raise ValueError("Invalid conflicts.yml: expected `conflicts` list.")
        normalized = [conflict for conflict in conflicts if isinstance(conflict, dict)]
        return ConflictStatus(
            conflicts_count=len(normalized),
            conflicts=normalized,
            conflicts_file=path.relative_to(self.root),
        )

    def create_change_set(self, source: str, title: str | None = None) -> ChangeSetStatus:
        proposal_dir = self._find_proposal_dir(source)
        proposal_path = proposal_dir / "proposal.md"
        proposal_text = _read_optional(proposal_path)
        proposal_status = _read_proposal_status(proposal_path)
        if proposal_status != "accepted":
            raise ValueError(
                f"Cannot create Change Set. {source} is not accepted yet. "
                f"Current status: {proposal_status}"
            )

        change_id = self._next_change_id()
        proposal_title = _clean_proposal_title(_read_title(proposal_text) or source, source)
        change_title = title or proposal_title
        slug = _slugify(change_title)
        change_dir = self.p2p_dir / "changes" / f"{change_id}-{slug}"
        change_dir.mkdir(parents=True)

        files = {
            "change.md": _change_markdown(
                change_id=change_id,
                title=change_title,
                source_proposal=source,
                created_on=date.today().isoformat(),
                summary=_read_markdown_section(proposal_text, "Proposal") or "Not provided.",
                rationale=_read_markdown_section(proposal_text, "Context") or "Not provided.",
            ),
            "included-proposals.yml": _yaml_dump({"included_proposals": [source]}),
            "referenced-proposals.yml": _yaml_dump({"referenced_proposals": []}),
            "excluded-alternatives.yml": _yaml_dump({"excluded_alternatives": []}),
            "included-decisions.yml": _yaml_dump(
                {
                    "included_decisions": [
                        {
                            "proposal": source,
                            "decision_file": str((proposal_dir / "decision.md").relative_to(self.root)),
                        }
                    ]
                }
            ),
            "impact-map.yml": _read_optional(proposal_dir / "impact-map.yml")
            or _yaml_dump({"impact": {"proposal": source, "features": [], "commands": [], "files": []}}),
            "git-policy.yml": _yaml_dump(_metadata_only_git_policy()),
            "execution-plan.md": _read_optional(proposal_dir / "execution-plan.md")
            or f"# Execution Plan - {change_id}\n\nPending.\n",
            "tasks.yml": _read_optional(proposal_dir / "tasks.yml") or "tasks: []\n",
            "actions.yml": _yaml_dump({"actions": []}),
        }
        for filename, content in files.items():
            (change_dir / filename).write_text(content, encoding="utf-8")

        return ChangeSetStatus(
            change_id=change_id,
            title=change_title,
            status="proposed",
            path=change_dir.relative_to(self.root),
        )

    def change_set_statuses(self) -> list[ChangeSetStatus]:
        changes_dir = self.p2p_dir / "changes"
        statuses: list[ChangeSetStatus] = []
        for path in sorted(changes_dir.iterdir()) if changes_dir.exists() else []:
            if not path.is_dir():
                continue
            change_text = _read_optional(path / "change.md")
            frontmatter = _read_frontmatter(change_text)
            change_id = str(frontmatter.get("change_id") or "-".join(path.name.split("-", 2)[:2]))
            title = str(frontmatter.get("title") or _read_title(change_text) or path.name)
            status = str(frontmatter.get("status") or "unknown")
            statuses.append(
                ChangeSetStatus(
                    change_id=change_id,
                    title=title,
                    status=status,
                    path=path.relative_to(self.root),
                )
            )
        return statuses

    def change_set_policy(self, change_id: str) -> ChangeSetPolicy:
        change_dir = self._find_change_dir(change_id)
        data = _read_yaml_mapping(change_dir / "git-policy.yml", default=_metadata_only_git_policy())
        policy = data.get("git_policy", {})
        if not isinstance(policy, dict):
            raise ValueError("Invalid git-policy.yml: expected `git_policy` mapping.")
        commits = policy.get("commits", {})
        branches = policy.get("branches", {})
        tags = policy.get("tags", {})
        return ChangeSetPolicy(
            change_id=change_id,
            operation_level=str(policy.get("operation_level", "metadata_only")),
            auto_commit=bool(commits.get("auto_commit", False)) if isinstance(commits, dict) else False,
            auto_branch=bool(branches.get("auto_create", False)) if isinstance(branches, dict) else False,
            auto_tag=bool(tags.get("auto_create", False)) if isinstance(tags, dict) else False,
            reasons=[
                "MVP uses metadata_only managed Git policy.",
                "No Git commits, branches, tags, or merges are created automatically.",
            ],
        )

    def show_change_set(self, change_id: str) -> ChangeSetDetail:
        change_dir = self._find_change_dir(change_id)
        text = _read_optional(change_dir / "change.md")
        frontmatter = _read_frontmatter(text)
        return ChangeSetDetail(
            change_id=str(frontmatter.get("change_id") or change_id),
            title=str(frontmatter.get("title") or _read_title(text) or change_id),
            status=str(frontmatter.get("status") or "unknown"),
            path=change_dir.relative_to(self.root),
            summary=_read_markdown_section(text, "Summary") or "Not provided.",
            execution_domains=_string_list(frontmatter.get("execution_domains")),
            implementation_targets=_string_list(frontmatter.get("implementation_targets")),
            spec_targets=_string_list(frontmatter.get("spec_targets")),
            export_targets=_string_list(frontmatter.get("export_targets")),
            plan_ref=str(frontmatter.get("plan_ref") or "execution-plan.md"),
            tasks_ref=str(frontmatter.get("tasks_ref") or "tasks.yml"),
        )

    def update_change_set_status(self, change_id: str, new_status: str) -> ChangeSetStatus:
        change_dir = self._find_change_dir(change_id)
        change_path = change_dir / "change.md"
        text = _read_optional(change_path)
        frontmatter = _read_frontmatter(text)
        current_status = str(frontmatter.get("status") or "unknown")
        allowed = CHANGE_STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid Change Set transition: {current_status} -> {new_status}. "
                f"Allowed next: {', '.join(allowed) if allowed else 'none'}"
            )
        frontmatter["status"] = new_status
        updated = _replace_frontmatter(text, frontmatter)
        change_path.write_text(updated, encoding="utf-8")
        return ChangeSetStatus(
            change_id=str(frontmatter.get("change_id") or change_id),
            title=str(frontmatter.get("title") or change_id),
            status=new_status,
            path=change_dir.relative_to(self.root),
        )

    def change_set_tasks(self, change_id: str) -> ChangeSetTaskView:
        change_dir = self._find_change_dir(change_id)
        tasks_data = _read_yaml_mapping(change_dir / "tasks.yml", default={"tasks": []})
        actions_data = _read_yaml_mapping(change_dir / "actions.yml", default={"actions": []})
        tasks = tasks_data.get("tasks", [])
        actions = actions_data.get("actions", [])
        if not isinstance(tasks, list):
            raise ValueError("Invalid tasks.yml: expected `tasks` list.")
        if not isinstance(actions, list):
            raise ValueError("Invalid actions.yml: expected `actions` list.")
        return ChangeSetTaskView(
            change_id=change_id,
            tasks=[task for task in tasks if isinstance(task, dict)],
            actions=[action for action in actions if isinstance(action, dict)],
        )

    def refresh_registries(self) -> list[Path]:
        return self._registry_service().refresh()

    def registry_status(self) -> RegistryStatus:
        return self._registry_service().status()

    def show_registry(self, name: str) -> RegistryView:
        return self._registry_service().show(name)

    def create_intake_prompt(self, idea: str) -> IntakePrompt:
        intake_id = self._next_intake_id()
        intake_dir = self.p2p_dir / "intake" / intake_id
        intake_dir.mkdir(parents=True, exist_ok=False)

        registry_status = self.registry_status()
        context = self._intake_context(registry_status)
        input_path = intake_dir / "input.md"
        context_path = intake_dir / "context.md"
        prompt_path = intake_dir / "intake.prompt.md"

        input_path.write_text(f"# Intake Input - {intake_id}\n\n{idea.strip()}\n", encoding="utf-8")
        context_path.write_text(context, encoding="utf-8")
        prompt_path.write_text(
            _intake_prompt_markdown(intake_id=intake_id, idea=idea, context=context),
            encoding="utf-8",
        )
        (intake_dir / "related-proposals.yml").write_text(
            _yaml_dump({"related_proposals": []}),
            encoding="utf-8",
        )
        (intake_dir / "suggested-actions.yml").write_text(
            _yaml_dump(
                {
                    "suggested_actions": [
                        {
                            "type": "needs_analysis",
                            "target": None,
                            "rationale": "Import intake output to populate recommendations.",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (intake_dir / "recommendation.md").write_text(
            f"# Recommendation - {intake_id}\n\nPending.\n",
            encoding="utf-8",
        )
        return IntakePrompt(
            intake_id=intake_id,
            path=intake_dir.relative_to(self.root),
            prompt_path=prompt_path.relative_to(self.root),
        )

    def import_intake(self, intake_id: str, source: Path) -> list[Path]:
        intake_dir = self._find_intake_dir(intake_id)
        source = source.resolve()
        imported: list[Path] = []
        if source.is_dir():
            mappings = {
                "recommendation.md": None,
                "related-proposals.yml": "related_proposals",
                "suggested-actions.yml": "suggested_actions",
                "context.md": None,
            }
            for filename, key in mappings.items():
                source_path = source / filename
                if source_path.exists():
                    if key is not None:
                        _validate_yaml_key(source_path.read_text(encoding="utf-8"), key)
                    target = intake_dir / filename
                    shutil.copyfile(source_path, target)
                    imported.append(target.relative_to(self.root))
        elif source.is_file():
            target = intake_dir / "recommendation.md"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            imported.append(target.relative_to(self.root))
        else:
            raise ValueError(f"Intake source not found: {source}")
        if not imported:
            raise ValueError(f"No intake artifacts found in: {source}")
        return imported

    def intake_statuses(self) -> list[IntakeStatus]:
        intake_dir = self.p2p_dir / "intake"
        statuses: list[IntakeStatus] = []
        for path in sorted(intake_dir.iterdir()) if intake_dir.exists() else []:
            if not path.is_dir():
                continue
            recommendation = _read_optional(path / "recommendation.md")
            has_recommendation = _has_meaningful_intake_recommendation(recommendation)
            statuses.append(
                IntakeStatus(
                    intake_id=path.name,
                    status="analyzed" if has_recommendation else "pending",
                    path=path.relative_to(self.root),
                    recommendation=_read_title(recommendation) or "Recommendation pending",
                )
            )
        return statuses

    def create_intake_apply_plan(self, intake_id: str) -> IntakeApplyPlan:
        intake_dir = self._find_intake_dir(intake_id)
        suggested_path = intake_dir / "suggested-actions.yml"
        data = _read_yaml_mapping(suggested_path, default={"suggested_actions": []})
        suggested_actions = data.get("suggested_actions", [])
        if not isinstance(suggested_actions, list):
            raise ValueError("Invalid suggested-actions.yml: expected `suggested_actions` list.")

        plan_actions: list[dict[str, object]] = []
        for index, action in enumerate(suggested_actions, start=1):
            if not isinstance(action, dict):
                continue
            action_type = str(action.get("type") or "unknown")
            target = action.get("target")
            rationale = str(action.get("rationale") or "")
            support, status, command_preview, required_inputs = self._intake_apply_action_metadata(
                intake_id=intake_id,
                action_type=action_type,
                target=str(target) if target is not None else None,
                rationale=rationale,
            )
            plan_actions.append(
                {
                    "id": f"APPLY-{len(plan_actions) + 1:03d}",
                    "source_action_index": index,
                    "type": action_type,
                    "target": target,
                    "support": support,
                    "status": status,
                    "reason": rationale,
                    "command_preview": command_preview,
                    "required_inputs": required_inputs,
                }
            )

        plan_path = intake_dir / "apply-plan.yml"
        plan_path.write_text(
            _yaml_dump(
                {
                    "intake": intake_id,
                    "generated_on": date.today().isoformat(),
                    "apply_plan": plan_actions,
                }
            ),
            encoding="utf-8",
        )
        return IntakeApplyPlan(intake_id=intake_id, path=plan_path.relative_to(self.root), actions=plan_actions)

    def show_intake_apply_plan(self, intake_id: str) -> IntakeApplyPlan:
        intake_dir = self._find_intake_dir(intake_id)
        plan_path = intake_dir / "apply-plan.yml"
        if not plan_path.exists():
            raise ValueError("Intake apply plan not found. Run `p2p intake apply plan` first.")
        data = _read_yaml_mapping(plan_path, default={"apply_plan": []})
        actions = data.get("apply_plan", [])
        if not isinstance(actions, list):
            raise ValueError("Invalid apply-plan.yml: expected `apply_plan` list.")
        return IntakeApplyPlan(
            intake_id=intake_id,
            path=plan_path.relative_to(self.root),
            actions=[action for action in actions if isinstance(action, dict)],
        )

    def run_intake_apply_action(
        self,
        intake_id: str,
        action_id: str,
        options: list[str] | None = None,
    ) -> IntakeAppliedAction:
        intake_dir = self._find_intake_dir(intake_id)
        plan_path = intake_dir / "apply-plan.yml"
        if not plan_path.exists():
            raise ValueError("Intake apply plan not found. Run `p2p intake apply plan` first.")
        data = _read_yaml_mapping(plan_path, default={"apply_plan": []})
        plan_actions = data.get("apply_plan", [])
        if not isinstance(plan_actions, list):
            raise ValueError("Invalid apply-plan.yml: expected `apply_plan` list.")
        action = _find_apply_plan_action(plan_actions, action_id)
        if action is None:
            raise ValueError(f"Apply action not found: {action_id}")
        if action.get("status") == "applied":
            raise ValueError(f"Apply action already applied: {action_id}")

        action_type = str(action.get("type") or "")
        target = str(action.get("target") or "")
        reason = str(action.get("reason") or "")
        if action_type == "add_contribution":
            if not target.startswith("PROP-"):
                raise ValueError("add_contribution apply action requires a proposal target.")
            self.add_contribution(
                proposal_id=target,
                contribution_type=ContributionType.suggestion,
                text=reason or f"Applied from {intake_id}.",
                relevance_hint="medium",
                author=f"intake:{intake_id}",
            )
            command = f'p2p contribution add {target} "{reason}" --type suggestion --relevance medium'
        elif action_type == "open_choice":
            cleaned_options = [option.strip() for option in options or [] if option.strip()]
            if len(cleaned_options) < 2:
                raise ValueError("open_choice apply action requires at least two --option values.")
            related = [target] if target.startswith("PROP-") else []
            choice = self.create_choice(
                title=f"Intake {intake_id} choice for {target or 'project'}",
                options=cleaned_options,
                related=related,
                source=intake_id,
            )
            command = (
                "p2p choice create "
                f'--title "Intake {intake_id} choice for {target or "project"}" '
                + " ".join(f'--option "{option}"' for option in cleaned_options)
            )
            if related:
                command += f" --related {target}"
            command += f" --source {intake_id}"
            action["created_choice"] = choice.choice_id
        else:
            support = str(action.get("support") or "unsupported")
            raise ValueError(f"Apply action {action_id} is {support} and cannot be run by intake apply.")

        action["status"] = "applied"
        action["applied_on"] = date.today().isoformat()
        plan_path.write_text(_yaml_dump(data), encoding="utf-8")

        applied_path = intake_dir / "applied-actions.yml"
        applied_data = _read_yaml_mapping(applied_path, default={"applied_actions": []})
        applied_actions = applied_data.setdefault("applied_actions", [])
        if not isinstance(applied_actions, list):
            raise ValueError("Invalid applied-actions.yml: expected `applied_actions` list.")
        applied_id = f"APPLIED-{len(applied_actions) + 1:03d}"
        applied_record = {
            "id": applied_id,
            "intake": intake_id,
            "plan_action": action_id,
            "type": action_type,
            "target": target,
            "status": "applied",
            "command": command,
            "applied_on": date.today().isoformat(),
        }
        applied_actions.append(applied_record)
        applied_path.write_text(_yaml_dump(applied_data), encoding="utf-8")
        return IntakeAppliedAction(
            applied_id=applied_id,
            plan_action=action_id,
            action_type=action_type,
            target=target,
            command=command,
            path=applied_path.relative_to(self.root),
        )

    def create_choice(
        self,
        title: str,
        options: list[str],
        related: list[str] | None = None,
        source: str | None = None,
    ) -> ChoiceStatus:
        cleaned_options = [option.strip() for option in options if option.strip()]
        if len(cleaned_options) < 2:
            raise ValueError("At least two --option values are required.")
        related = related or []
        for proposal_id in related:
            if proposal_id.startswith("PROP-"):
                self._find_proposal_dir(proposal_id)

        choice_id = self._next_choice_id()
        title_slug = _slugify(title)
        choice_dir = self.p2p_dir / "choices" / f"{choice_id}-{title_slug}"
        choice_dir.mkdir(parents=True, exist_ok=False)
        now = date.today().isoformat()
        choice_frontmatter = _yaml_dump(
            {
                "choice_id": choice_id,
                "title": title,
                "status": "open",
                "created_at": now,
                "created_by": "local",
                "source": {"intake": source} if source else {},
                "related": {"proposals": related},
            }
        )
        (choice_dir / "choice.md").write_text(
            f"---\n{choice_frontmatter}---\n\n"
            f"# {choice_id} - {title}\n\n"
            "## Problem\n\n"
            "Pending.\n\n"
            "## Context\n\n"
            "Pending.\n\n"
            "## Governance Boundary\n\n"
            "This choice is advisory until decided through P2P governance.\n",
            encoding="utf-8",
        )
        (choice_dir / "options.yml").write_text(
            _yaml_dump(
                {
                    "options": [
                        {
                            "id": chr(ord("A") + index),
                            "title": option,
                            "status": "available",
                        }
                        for index, option in enumerate(cleaned_options)
                    ]
                }
            ),
            encoding="utf-8",
        )
        (choice_dir / "decision.md").write_text(
            f"# Decision - {choice_id}\n\n"
            "## Status\n\n"
            "`pending`\n\n"
            "## Selected Option\n\n"
            "Pending.\n\n"
            "## Reason\n\n"
            "Pending.\n\n"
            "## Decided By\n\n"
            "Pending.\n\n"
            "## Date\n\n"
            "Pending.\n",
            encoding="utf-8",
        )
        (choice_dir / "links.yml").write_text(
            _yaml_dump(
                {
                    "source": {"intake": source} if source else {},
                    "related_proposals": [
                        {"proposal": proposal_id, "relationship": "related_to", "rationale": ""}
                        for proposal_id in related
                    ],
                    "related_changes": [],
                }
            ),
            encoding="utf-8",
        )
        return ChoiceStatus(
            choice_id=choice_id,
            title=title,
            status="open",
            path=choice_dir.relative_to(self.root),
            selected_option=None,
        )

    def choice_statuses(self) -> list[ChoiceStatus]:
        choices_dir = self.p2p_dir / "choices"
        statuses: list[ChoiceStatus] = []
        for path in sorted(choices_dir.iterdir()) if choices_dir.exists() else []:
            if not path.is_dir():
                continue
            choice_text = _read_optional(path / "choice.md")
            frontmatter = _read_frontmatter(choice_text)
            decision_text = _read_optional(path / "decision.md")
            selected = _read_markdown_section(decision_text, "Selected Option")
            selected_option = None if selected in {None, "Pending."} else selected
            statuses.append(
                ChoiceStatus(
                    choice_id=str(frontmatter.get("choice_id") or "-".join(path.name.split("-", 2)[:2])),
                    title=str(frontmatter.get("title") or _read_title(choice_text) or path.name),
                    status=str(frontmatter.get("status") or "unknown"),
                    path=path.relative_to(self.root),
                    selected_option=selected_option,
                )
            )
        return statuses

    def show_choice(self, choice_id: str) -> ChoiceDetail:
        choice_dir = self._find_choice_dir(choice_id)
        choice_text = _read_optional(choice_dir / "choice.md")
        frontmatter = _read_frontmatter(choice_text)
        decision_text = _read_optional(choice_dir / "decision.md")
        selected = _read_markdown_section(decision_text, "Selected Option")
        selected_option = None if selected in {None, "Pending."} else selected
        options_data = _read_yaml_mapping(choice_dir / "options.yml", default={"options": []})
        links = _read_yaml_mapping(choice_dir / "links.yml", default={})
        return ChoiceDetail(
            choice_id=str(frontmatter.get("choice_id") or choice_id),
            title=str(frontmatter.get("title") or _read_title(choice_text) or choice_id),
            status=str(frontmatter.get("status") or "unknown"),
            path=choice_dir.relative_to(self.root),
            selected_option=selected_option,
            options=options_data.get("options", []) if isinstance(options_data.get("options"), list) else [],
            related_proposals=links.get("related_proposals", [])
            if isinstance(links.get("related_proposals"), list)
            else [],
            related_changes=links.get("related_changes", [])
            if isinstance(links.get("related_changes"), list)
            else [],
            blocks=links.get("blocks", []) if isinstance(links.get("blocks"), list) else [],
        )

    def discover_choices(self) -> list[ChoiceDiscoveryFinding]:
        findings: list[ChoiceDiscoveryFinding] = []
        project_choice_ids = {choice.choice_id for choice in self.choice_statuses()}

        for record in self._choice_registry_records():
            choice_id = str(record.get("id") or "")
            status = str(record.get("status") or "unknown")
            selected = record.get("selected_option")
            if choice_id.startswith("CHOICE-PROP-") and choice_id not in project_choice_ids:
                proposal_id = str(record.get("proposal") or choice_id.removeprefix("CHOICE-"))
                findings.append(
                    ChoiceDiscoveryFinding(
                        finding_id=f"DISCOVERY-{len(findings) + 1:03d}",
                        kind="proposal_local_choice_candidate",
                        target=choice_id,
                        severity="medium" if status in {"open", "draft", "pending"} and not selected else "low",
                        reason=(
                            f"{choice_id} is proposal-local vote metadata for {proposal_id}, "
                            "not a project choice managed by p2p choice commands."
                        ),
                        suggested_command=f"p2p proposal show {proposal_id}",
                    )
                )

        for choice in self.choice_statuses():
            detail = self.show_choice(choice.choice_id)
            active_blocks = [
                block for block in detail.blocks if isinstance(block, dict) and block.get("status", "active") == "active"
            ]
            if choice.status != "decided" and active_blocks:
                findings.append(
                    ChoiceDiscoveryFinding(
                        finding_id=f"DISCOVERY-{len(findings) + 1:03d}",
                        kind="active_choice_blocker",
                        target=choice.choice_id,
                        severity="high",
                        reason=f"{choice.choice_id} is not decided and has active blockers.",
                        suggested_command=f"p2p choice show {choice.choice_id}",
                    )
                )
            elif choice.status in {"open", "draft", "pending"}:
                findings.append(
                    ChoiceDiscoveryFinding(
                        finding_id=f"DISCOVERY-{len(findings) + 1:03d}",
                        kind="open_project_choice",
                        target=choice.choice_id,
                        severity="medium",
                        reason=f"{choice.choice_id} is a project choice without a final decision.",
                        suggested_command=f"p2p choice show {choice.choice_id}",
                    )
                )
        return findings

    def block_choice(
        self,
        choice_id: str,
        target: str,
        target_type: str,
        reason: str,
    ) -> ChoiceDetail:
        choice_dir = self._find_choice_dir(choice_id)
        if target_type == "change":
            self._find_change_dir(target)
        elif target_type == "proposal":
            self._find_proposal_dir(target)
        else:
            raise ValueError("target_type must be `change` or `proposal`.")
        links_path = choice_dir / "links.yml"
        links = _read_yaml_mapping(links_path, default={})
        blocks = links.setdefault("blocks", [])
        if not isinstance(blocks, list):
            raise ValueError("Invalid links.yml: expected `blocks` list.")
        for block in blocks:
            if (
                isinstance(block, dict)
                and block.get("target") == target
                and block.get("target_type") == target_type
                and block.get("status", "active") == "active"
            ):
                block["reason"] = reason
                block["recorded_on"] = date.today().isoformat()
                links_path.write_text(_yaml_dump(links), encoding="utf-8")
                return self.show_choice(choice_id)
        blocks.append(
            {
                "target": target,
                "target_type": target_type,
                "status": "active",
                "reason": reason,
                "recorded_on": date.today().isoformat(),
            }
        )
        links_path.write_text(_yaml_dump(links), encoding="utf-8")
        return self.show_choice(choice_id)

    def unblock_choice(self, choice_id: str, target: str, target_type: str) -> ChoiceDetail:
        choice_dir = self._find_choice_dir(choice_id)
        links_path = choice_dir / "links.yml"
        links = _read_yaml_mapping(links_path, default={})
        blocks = links.get("blocks", [])
        if not isinstance(blocks, list):
            raise ValueError("Invalid links.yml: expected `blocks` list.")
        changed = False
        for block in blocks:
            if (
                isinstance(block, dict)
                and block.get("target") == target
                and block.get("target_type") == target_type
                and block.get("status", "active") == "active"
            ):
                block["status"] = "inactive"
                block["cleared_on"] = date.today().isoformat()
                changed = True
        if not changed:
            raise ValueError(f"Active blocker not found for {target_type}: {target}")
        links_path.write_text(_yaml_dump(links), encoding="utf-8")
        return self.show_choice(choice_id)

    def decide_choice(
        self,
        choice_id: str,
        option: str,
        reason: str,
        decider: str,
    ) -> ChoiceStatus:
        choice_dir = self._find_choice_dir(choice_id)
        options_data = _read_yaml_mapping(choice_dir / "options.yml", default={"options": []})
        options = options_data.get("options", [])
        if not isinstance(options, list):
            raise ValueError("Invalid options.yml: expected `options` list.")
        selected = _find_choice_option(options, option)
        if selected is None:
            raise ValueError(f"Choice option not found: {option}")
        selected_id = str(selected.get("id"))
        selected_title = str(selected.get("title"))

        for option_item in options:
            if not isinstance(option_item, dict):
                continue
            option_item["status"] = "selected" if option_item.get("id") == selected_id else "not_selected"
        (choice_dir / "options.yml").write_text(_yaml_dump({"options": options}), encoding="utf-8")

        decision_text = (
            f"# Decision - {choice_id}\n\n"
            "## Status\n\n"
            "`decided`\n\n"
            "## Selected Option\n\n"
            f"{selected_id} - {selected_title}\n\n"
            "## Reason\n\n"
            f"{reason}\n\n"
            "## Decided By\n\n"
            f"{decider}\n\n"
            "## Date\n\n"
            f"{date.today().isoformat()}\n"
        )
        (choice_dir / "decision.md").write_text(decision_text, encoding="utf-8")

        choice_path = choice_dir / "choice.md"
        choice_text = _read_optional(choice_path)
        frontmatter = _read_frontmatter(choice_text)
        frontmatter["status"] = "decided"
        choice_path.write_text(_replace_frontmatter(choice_text, frontmatter), encoding="utf-8")

        return ChoiceStatus(
            choice_id=str(frontmatter.get("choice_id") or choice_id),
            title=str(frontmatter.get("title") or choice_id),
            status="decided",
            path=choice_dir.relative_to(self.root),
            selected_option=f"{selected_id} - {selected_title}",
        )

    def _accepted_proposals(self) -> list[dict[str, object]]:
        proposals_dir = self.p2p_dir / "proposals"
        accepted: list[dict[str, object]] = []
        for path in sorted(proposals_dir.iterdir()) if proposals_dir.exists() else []:
            if not path.is_dir():
                continue
            proposal_path = path / "proposal.md"
            status = _read_proposal_status(proposal_path)
            if status != "accepted":
                continue
            text = _read_optional(proposal_path)
            proposal_id = "-".join(path.name.split("-", 2)[:2])
            title = _clean_proposal_title(_read_title(text) or path.name, proposal_id)
            accepted.append(
                {
                    "proposal_id": proposal_id,
                    "title": title,
                    "status": status,
                    "feature_id": _slugify(title.replace(proposal_id, "", 1)),
                    "path": path,
                    "source": str(path.relative_to(self.root)),
                    "problem": _read_markdown_section(text, "Problem") or "Not provided.",
                    "goals": _read_markdown_section(text, "Goals") or "- Not provided.",
                    "non_goals": _read_markdown_section(text, "Non-Goals") or "- Not provided.",
                    "proposal": _read_markdown_section(text, "Proposal") or "Not provided.",
                    "decision": _read_optional(path / "decision.md"),
                }
            )
        return accepted

    def _proposal_registry_records(self) -> list[dict[str, object]]:
        proposals_dir = self.p2p_dir / "proposals"
        records: list[dict[str, object]] = []
        for path in sorted(proposals_dir.iterdir()) if proposals_dir.exists() else []:
            if not path.is_dir():
                continue
            proposal_id = "-".join(path.name.split("-", 2)[:2])
            proposal_text = _read_optional(path / "proposal.md")
            title = _clean_proposal_title(_read_title(proposal_text) or path.name, proposal_id)
            records.append(
                {
                    "id": proposal_id,
                    "title": title,
                    "status": _read_proposal_status(path / "proposal.md"),
                    "path": str(path.relative_to(self.root)),
                    "summary": _read_markdown_section(proposal_text, "Proposal") or "",
                    "decision_file": str((path / "decision.md").relative_to(self.root)),
                    "related_changes": self._changes_for_proposal(proposal_id),
                    "source_files": sorted(
                        file.name for file in path.iterdir() if file.is_file()
                    ),
                }
            )
        return records

    def _decision_registry_records(self, proposals: list[dict[str, object]]) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for proposal in proposals:
            decision_path = self.root / str(proposal["decision_file"])
            decision_text = _read_optional(decision_path)
            outcome = _read_markdown_section(decision_text, "Outcome")
            if not outcome:
                status = _read_markdown_section(decision_text, "Status")
                outcome = status.strip("`") if status else "pending"
            records.append(
                {
                    "proposal": proposal["id"],
                    "title": proposal["title"],
                    "outcome": outcome,
                    "status": proposal["status"],
                    "path": str(decision_path.relative_to(self.root)),
                    "reason": _read_markdown_section(decision_text, "Reason") or "",
                }
            )
        return records

    def _change_registry_records(self) -> list[dict[str, object]]:
        changes_dir = self.p2p_dir / "changes"
        records: list[dict[str, object]] = []
        for path in sorted(changes_dir.iterdir()) if changes_dir.exists() else []:
            if not path.is_dir():
                continue
            change_text = _read_optional(path / "change.md")
            frontmatter = _read_frontmatter(change_text)
            source = frontmatter.get("source", {})
            if not isinstance(source, dict):
                source = {}
            tasks_data = _read_yaml_mapping(path / "tasks.yml", default={"tasks": []})
            tasks = tasks_data.get("tasks", [])
            records.append(
                {
                    "id": str(frontmatter.get("change_id") or "-".join(path.name.split("-", 2)[:2])),
                    "title": str(frontmatter.get("title") or _read_title(change_text) or path.name),
                    "status": str(frontmatter.get("status") or "unknown"),
                    "path": str(path.relative_to(self.root)),
                    "included_proposals": source.get("accepted_proposals", []),
                    "referenced_proposals": _read_yaml_mapping(
                        path / "referenced-proposals.yml",
                        default={"referenced_proposals": []},
                    ).get("referenced_proposals", []),
                    "execution_domains": frontmatter.get("execution_domains", []),
                    "implementation_targets": frontmatter.get("implementation_targets", []),
                    "spec_targets": frontmatter.get("spec_targets", []),
                    "export_targets": frontmatter.get("export_targets", []),
                    "task_count": len(tasks) if isinstance(tasks, list) else 0,
                }
            )
        return records

    def _choice_registry_records(self) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        choices_dir = self.p2p_dir / "choices"
        for path in sorted(choices_dir.iterdir()) if choices_dir.exists() else []:
            if not path.is_dir():
                continue
            choice_text = _read_optional(path / "choice.md")
            frontmatter = _read_frontmatter(choice_text)
            options_data = _read_yaml_mapping(path / "options.yml", default={"options": []})
            options = options_data.get("options", [])
            decision_text = _read_optional(path / "decision.md")
            selected = _read_markdown_section(decision_text, "Selected Option")
            selected_option = None if selected in {None, "Pending."} else selected
            records.append(
                {
                    "id": str(frontmatter.get("choice_id") or "-".join(path.name.split("-", 2)[:2])),
                    "title": str(frontmatter.get("title") or _read_title(choice_text) or path.name),
                    "status": str(frontmatter.get("status") or "unknown"),
                    "options": [
                        option.get("id")
                        for option in options
                        if isinstance(option, dict) and option.get("id")
                    ]
                    if isinstance(options, list)
                    else [],
                    "selected_option": selected_option,
                    "path": str(path.relative_to(self.root)),
                }
            )

        proposals_dir = self.p2p_dir / "proposals"
        for path in sorted(proposals_dir.iterdir()) if proposals_dir.exists() else []:
            if not path.is_dir():
                continue
            votes_path = path / "votes.yml"
            if not votes_path.exists():
                continue
            proposal_id = "-".join(path.name.split("-", 2)[:2])
            data = _read_yaml_mapping(votes_path, default={})
            records.append(
                {
                    "id": f"CHOICE-{proposal_id}",
                    "proposal": proposal_id,
                    "status": data.get("status", "open"),
                    "options": sorted(
                        {
                            str(vote.get("choice"))
                            for vote in data.get("votes", [])
                            if isinstance(vote, dict) and vote.get("choice")
                        }
                    ),
                    "selected_option": data.get("result", {}).get("winner")
                    if isinstance(data.get("result"), dict)
                    else None,
                    "path": str(votes_path.relative_to(self.root)),
                }
            )
        return records

    def _relation_registry_records(
        self,
        proposals: list[dict[str, object]],
        changes: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for change in changes:
            for proposal_id in change.get("included_proposals", []):
                records.append(
                    {
                        "source": change["id"],
                        "target": proposal_id,
                        "type": "includes",
                        "rationale": "Change Set includes accepted proposal.",
                        "source_artifact": change["path"],
                    }
                )
            for proposal_id in change.get("referenced_proposals", []):
                records.append(
                    {
                        "source": change["id"],
                        "target": proposal_id,
                        "type": "references",
                        "rationale": "Change Set references proposal as context.",
                        "source_artifact": change["path"],
                    }
                )
        for proposal in proposals:
            for change_id in proposal.get("related_changes", []):
                records.append(
                    {
                        "source": proposal["id"],
                        "target": change_id,
                        "type": "implemented_by",
                        "rationale": "Proposal appears in Change Set source metadata.",
                        "source_artifact": proposal["path"],
                    }
                )
        return records

    def _artifact_registry_records(
        self,
        proposals: list[dict[str, object]],
        changes: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for proposal in proposals:
            proposal_dir = self.root / str(proposal["path"])
            for file in sorted(proposal_dir.iterdir()) if proposal_dir.exists() else []:
                if file.is_file():
                    records.append(
                        {
                            "path": str(file.relative_to(self.root)),
                            "artifact_type": file.name,
                            "owner_type": "proposal",
                            "owner": proposal["id"],
                            "generated": False,
                        }
                    )
        for change in changes:
            change_dir = self.root / str(change["path"])
            for file in sorted(change_dir.iterdir()) if change_dir.exists() else []:
                if file.is_file():
                    records.append(
                        {
                            "path": str(file.relative_to(self.root)),
                            "artifact_type": file.name,
                            "owner_type": "change",
                            "owner": change["id"],
                            "generated": False,
                        }
                    )
        return records

    def _readiness_registry_records(self, proposals: list[dict[str, object]]) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for proposal in proposals:
            readiness = self.read_proposal_readiness(str(proposal["id"]))
            records.append(
                {
                    "proposal": proposal["id"],
                    "title": proposal["title"],
                    "proposal_status": proposal["status"],
                    "status": readiness.status,
                    "profile_id": readiness.profile_id,
                    "profile_version": readiness.profile_version,
                    "computed_score": readiness.computed_score,
                    "computed_label": readiness.computed_label,
                    "confidence": readiness.confidence,
                    "failed_gates": readiness.failed_gates,
                    "missing": readiness.missing,
                    "suggested_next": readiness.suggested_next,
                    "path": str(readiness.path),
                }
            )
        return records

    def _changes_for_proposal(self, proposal_id: str) -> list[str]:
        related: list[str] = []
        for change in self._change_registry_records():
            included = change.get("included_proposals", [])
            if isinstance(included, list) and proposal_id in included:
                related.append(str(change["id"]))
        return related

    def _intake_context(self, registry_status: RegistryStatus) -> str:
        lines = [
            "# Intake Context",
            "",
            "## Registry Status",
            "",
            f"- Path: `{registry_status.registries_dir}`",
            f"- Stale: `{registry_status.stale}`",
            f"- Source proposals: {registry_status.proposals_count}",
            f"- Source changes: {registry_status.changes_count}",
            "",
        ]
        for registry_name in ("proposals", "changes", "decisions", "relations"):
            try:
                view = self.show_registry(registry_name)
            except ValueError:
                lines.extend([f"## {registry_name.title()} Registry", "", "Not generated yet.", ""])
                continue
            lines.extend([f"## {registry_name.title()} Registry", ""])
            for record in view.records[:30]:
                if registry_name in {"proposals", "changes"}:
                    lines.append(
                        f"- {record.get('id')}: {record.get('status')} - {record.get('title')}"
                    )
                elif registry_name == "decisions":
                    lines.append(
                        f"- {record.get('proposal')}: {record.get('outcome')} - {record.get('title')}"
                    )
                else:
                    lines.append(
                        f"- {record.get('source')} -> {record.get('target')} ({record.get('type')})"
                    )
            if not view.records:
                lines.append("- None.")
            lines.append("")
        overview = _read_optional(self.p2p_dir / "project" / "overview.md")
        if overview:
            lines.extend(["## Project Overview", "", overview.strip(), ""])
        return "\n".join(lines)

    def _project_brief_context(self, registry_status: RegistryStatus) -> str:
        lines = [
            "# Project Brief Context",
            "",
            "This context is generated by the CLI. Use it to write an operational synthesis, "
            "not to make governance decisions.",
            "",
            "## Registry Status",
            "",
            f"- Path: `{registry_status.registries_dir}`",
            f"- Stale: `{registry_status.stale}`",
            f"- Source proposals: {registry_status.proposals_count}",
            f"- Source changes: {registry_status.changes_count}",
            "",
        ]
        for registry_name in ("proposals", "changes", "choices", "decisions", "relations"):
            try:
                view = self.show_registry(registry_name)
            except ValueError:
                lines.extend([f"## {registry_name.title()} Registry", "", "Not generated yet.", ""])
                continue
            lines.extend([f"## {registry_name.title()} Registry", ""])
            if not view.records:
                lines.extend(["- None.", ""])
                continue
            for record in view.records[:50]:
                if registry_name == "proposals":
                    lines.append(
                        f"- {record.get('id')}: {record.get('status')} - {record.get('title')}"
                    )
                elif registry_name == "changes":
                    included = record.get("included_proposals", [])
                    included_text = ", ".join(str(item) for item in included) if isinstance(included, list) else ""
                    lines.append(
                        f"- {record.get('id')}: {record.get('status')} - "
                        f"{record.get('title')} (proposals: {included_text or 'none'})"
                    )
                elif registry_name == "choices":
                    selected = record.get("selected_option") or "not decided"
                    lines.append(
                        f"- {record.get('id')}: {record.get('status')} - "
                        f"{record.get('title')} -> {selected}"
                    )
                elif registry_name == "decisions":
                    lines.append(
                        f"- {record.get('proposal')}: {record.get('outcome')} - "
                        f"{record.get('title')}"
                    )
                else:
                    lines.append(
                        f"- {record.get('source')} -> {record.get('target')} ({record.get('type')})"
                    )
            lines.append("")

        project_files = {
            "Project Overview": self.p2p_dir / "project" / "overview.md",
            "Project Scope": self.p2p_dir / "project" / "scope.md",
            "Project Conflicts": self.p2p_dir / "project" / "conflicts.yml",
        }
        for title, path in project_files.items():
            content = _read_optional(path)
            if content:
                lines.extend([f"## {title}", "", content.strip(), ""])

        intake_statuses = self.intake_statuses()
        lines.extend(["## Intake Status", ""])
        if intake_statuses:
            for status in intake_statuses:
                lines.append(f"- {status.intake_id}: {status.status} - {status.recommendation}")
        else:
            lines.append("- None.")
        lines.append("")
        return "\n".join(lines)

    def _intake_apply_action_metadata(
        self,
        intake_id: str,
        action_type: str,
        target: str | None,
        rationale: str,
    ) -> tuple[str, str, str, list[str]]:
        if action_type == "add_contribution":
            command = (
                f'p2p contribution add {target or "PROP-000"} "{rationale}" '
                "--type suggestion --relevance medium"
            )
            return ("supported", "pending", command, [])
        if action_type == "open_choice":
            command = (
                "p2p choice create "
                f'--title "Intake {intake_id} choice for {target or "project"}" '
                '--option "..." --option "..."'
            )
            if target:
                command += f" --related {target}"
            command += f" --source {intake_id}"
            return ("requires_input", "pending", command, ["option", "option"])
        if action_type in {"accept", "reject", "defer"}:
            command = f"p2p proposal {action_type} {target or 'PROP-000'} --reason \"{rationale}\""
            return ("governance_only", "pending", command, [])
        if action_type in {"duplicate", "record_conflict"}:
            return ("preview_only", "pending", "Manual review required.", [])
        return ("unsupported", "pending", "Unsupported intake apply action.", [])

    def _next_actions_from_project_file(self) -> list[NextAction]:
        path = self._next_actions_path()
        if not path.exists():
            return []
        data = _read_yaml_mapping(path, default={"next_actions": []})
        records = data.get("next_actions", [])
        if not isinstance(records, list):
            return []
        actions: list[NextAction] = []
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                continue
            if str(record.get("status") or "active") != "active":
                continue
            actions.append(self._next_action_from_record(record, path, index))
        return actions

    def _next_actions_path(self) -> Path:
        return self.p2p_dir / "project" / "next-actions.yml"

    def _next_actions_log_path(self) -> Path:
        return self.p2p_dir / "project" / "next-actions-log.yml"

    def _read_next_actions_payload(self) -> dict[str, object]:
        path = self._next_actions_path()
        if not path.exists():
            return {"next_actions": []}
        return _read_yaml_mapping(path, default={"next_actions": []})

    def _write_next_actions_payload(self, payload: dict[str, object]) -> None:
        path = self._next_actions_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(payload), encoding="utf-8")

    def _next_action_from_record(self, record: dict[str, object], path: Path, index: int) -> NextAction:
        return NextAction(
            action_id=str(record.get("id") or f"NEXT-{index:03d}"),
            priority=str(record.get("priority") or "medium"),
            kind=str(record.get("kind") or "other"),
            target=str(record.get("target") or ""),
            reason=str(record.get("reason") or ""),
            command=str(record.get("command") or ""),
            source=str(path.relative_to(self.root)),
        )

    def _normalize_next_action_record(self, record: dict[str, object], index: int) -> dict[str, object]:
        return {
            "id": str(record.get("id") or f"NEXT-{index:03d}"),
            "priority": str(record.get("priority") or "medium"),
            "kind": str(record.get("kind") or "other"),
            "target": str(record.get("target") or ""),
            "reason": str(record.get("reason") or ""),
            "command": str(record.get("command") or ""),
        }

    def _next_curated_next_action_id(self, records: list[object]) -> str:
        max_id = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            match = re.fullmatch(r"NEXT-(\d{3})", str(record.get("id") or ""))
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"NEXT-{max_id + 1:03d}"

    def _close_next_action(self, action_id: str, status: str, reason: str) -> dict[str, object]:
        action_id = action_id.strip()
        reason = reason.strip()
        if not action_id:
            raise ValueError("Next action ID is required")
        if not reason:
            raise ValueError("Next action close reason is required")
        payload = self._read_next_actions_payload()
        records = payload.get("next_actions", [])
        if not isinstance(records, list):
            raise ValueError("Invalid next-actions.yml: next_actions must be a list")
        remaining: list[object] = []
        closed: dict[str, object] | None = None
        for index, record in enumerate(records, start=1):
            if isinstance(record, dict) and str(record.get("id") or f"NEXT-{index:03d}") == action_id:
                closed = self._normalize_next_action_record(record, index)
                continue
            remaining.append(record)
        if closed is None:
            raise ValueError(f"Next action not found: {action_id}")
        payload["next_actions"] = remaining
        self._write_next_actions_payload(payload)

        log_path = self._next_actions_log_path()
        log_payload = _read_yaml_mapping(log_path, default={"next_action_log": []}) if log_path.exists() else {"next_action_log": []}
        log_records = log_payload.setdefault("next_action_log", [])
        if not isinstance(log_records, list):
            raise ValueError("Invalid next-actions-log.yml: next_action_log must be a list")
        entry = {
            **closed,
            "status": status,
            "closed_reason": reason,
            "closed_on": date.today().isoformat(),
        }
        log_records.append(entry)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(_yaml_dump(log_payload), encoding="utf-8")
        return {
            "action": entry,
            "path": str(log_path.relative_to(self.root)),
        }

    def _dedupe_next_actions(self, actions: list[NextAction]) -> list[NextAction]:
        deduped: list[NextAction] = []
        seen: set[tuple[str, str]] = set()
        for action in actions:
            key = (action.kind, action.target)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(action)
        return deduped

    def _fallback_next_actions(self) -> list[NextAction]:
        actions: list[NextAction] = []
        registry_status = self.registry_status()
        if registry_status.stale:
            actions.append(
                NextAction(
                    action_id="NEXT-FALLBACK-001",
                    priority="high",
                    kind="refresh_registry",
                    target="registries",
                    reason="Generated registries are missing or stale.",
                    command="p2p registry refresh",
                    source="generated",
                )
            )

        terminal_change_statuses = {"completed", "cancelled", "superseded"}
        for change in self._change_registry_records():
            status = str(change.get("status") or "unknown")
            if status not in terminal_change_statuses:
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="high" if status in {"planned", "blocked"} else "medium",
                        kind="continue_change",
                        target=str(change.get("id") or ""),
                        reason=f"Change Set is {status}, not completed.",
                        command=f"p2p change tasks {change.get('id')}",
                        source="generated",
                    )
                )
                break

        for intake in self.intake_statuses():
            if intake.status == "pending":
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="medium",
                        kind="inspect_intake",
                        target=intake.intake_id,
                        reason="Intake record is pending analysis.",
                        command="p2p intake status",
                        source="generated",
                    )
                )
                break

        for proposal in self.proposal_summaries(status="draft"):
            readiness = self.read_proposal_readiness(proposal.proposal_id)
            if readiness.status == "not_assessed":
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="high",
                        kind="assess_proposal_readiness",
                        target=proposal.proposal_id,
                        reason="Draft proposal has no readiness assessment.",
                        command=f"p2p proposal readiness refresh {proposal.proposal_id}",
                        source="generated",
                    )
                )
                break
            if readiness.computed_score is not None and readiness.computed_score < 85:
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="medium",
                        kind="improve_proposal_readiness",
                        target=proposal.proposal_id,
                        reason=(
                            f"Draft proposal readiness is {readiness.computed_score}, "
                            "below the default strong threshold."
                        ),
                        command=f"p2p proposal readiness explain {proposal.proposal_id}",
                        source="generated",
                    )
                )
                break

        for proposal in self.proposal_summaries(status="draft"):
            has_readiness_action = any(
                action.target == proposal.proposal_id
                and action.kind in {"assess_proposal_readiness", "improve_proposal_readiness"}
                for action in actions
            )
            if has_readiness_action:
                continue
            actions.append(
                NextAction(
                    action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                    priority="medium",
                    kind="review_draft_proposal",
                    target=proposal.proposal_id,
                    reason="Draft proposal exists and has no owner decision yet.",
                    command=f"p2p proposal show {proposal.proposal_id}",
                    source="generated",
                )
            )
            break

        for choice in self._choice_registry_records():
            status = str(choice.get("status") or "unknown")
            selected = choice.get("selected_option")
            if status in {"open", "draft", "pending"} and not selected:
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="medium",
                        kind="resolve_choice",
                        target=str(choice.get("id") or choice.get("proposal") or ""),
                        reason=f"Choice is {status} and has no selected option.",
                        command="p2p registry show choices",
                        source="generated",
                    )
                )
                break

        if not actions:
            actions.append(
                NextAction(
                    action_id="NEXT-FALLBACK-001",
                    priority="low",
                    kind="review_project",
                    target="project",
                    reason="No stored next actions or obvious fallback actions were found.",
                    command="p2p project status",
                    source="generated",
                )
            )
        return actions

    def _active_choice_blocker_actions(self) -> list[NextAction]:
        actions: list[NextAction] = []
        for choice in self.choice_statuses():
            if choice.status == "decided":
                continue
            detail = self.show_choice(choice.choice_id)
            for block in detail.blocks:
                if not isinstance(block, dict) or block.get("status", "active") != "active":
                    continue
                target = str(block.get("target") or "")
                target_type = str(block.get("target_type") or "target")
                actions.append(
                    NextAction(
                        action_id=f"NEXT-BLOCKER-{len(actions) + 1:03d}",
                        priority="high",
                        kind="resolve_choice",
                        target=choice.choice_id,
                        reason=(
                            f"{choice.choice_id} blocks {target_type} {target}: "
                            f"{block.get('reason') or 'Decision required.'}"
                        ),
                        command=f"p2p choice show {choice.choice_id}",
                        source=str(detail.path / "links.yml"),
                    )
                )
        return actions

    def _next_proposal_id(self) -> str:
        return self._proposal_document_service().next_id()

    def _find_proposal_dir(self, proposal_id: str) -> Path:
        return self._proposal_document_service().find_dir(proposal_id)

    def _duplicate_proposal_ids(self) -> dict[str, list[Path]]:
        return self._proposal_document_service().duplicate_ids()

    def _proposal_branch_metadata(self, proposal_id: str) -> tuple[Path, dict[str, object], Path]:
        proposal_dir = self._find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        if not metadata_path.exists():
            raise ValueError(f"Managed proposal branch metadata not found for {proposal_id}. Run `p2p proposal branch {proposal_id}` first.")
        metadata = _read_yaml_mapping(metadata_path, default={})
        return proposal_dir, metadata, metadata_path

    def _proposal_branch_metadata_from_local_ref(self, proposal_id: str) -> tuple[str, dict[str, object], Path]:
        matches: list[tuple[str, dict[str, object], Path]] = []
        for branch in list_local_proposal_branches(self.root):
            for metadata_path in list_files_at_ref(self.root, branch, ".p2p/proposals"):
                if not metadata_path.endswith("/branch.yml"):
                    continue
                branch_file = read_file_at_ref(self.root, branch, metadata_path)
                if branch_file is None:
                    continue
                try:
                    metadata = yaml.safe_load(branch_file.content) or {}
                except yaml.YAMLError:
                    continue
                if not isinstance(metadata, dict):
                    continue
                if str(metadata.get("proposal_id") or "") == proposal_id:
                    matches.append((branch, metadata, Path(metadata_path)))
        if not matches:
            raise ValueError(f"Managed proposal branch metadata not found for {proposal_id}. Run `p2p proposal scan`.")
        if len(matches) > 1:
            branches = ", ".join(branch for branch, _, _ in matches)
            raise ValueError(f"Ambiguous managed proposal branches for {proposal_id}: {branches}")
        return matches[0]

    def _remote_proposal_ids(self, remote: str, base_branch: str) -> set[str]:
        proposal_ids: set[str] = set()
        for branch in list_remote_proposal_branches(self.root, remote):
            proposal_id = _proposal_id_from_branch_name(branch)
            if proposal_id:
                proposal_ids.add(proposal_id)

        remote_base = f"{remote}/{base_branch}"
        for path in list_files_at_ref(self.root, remote_base, ".p2p/proposals"):
            parts = Path(path).parts
            if len(parts) < 3:
                continue
            proposal_id = _proposal_id_from_dir_name(parts[2])
            if proposal_id:
                proposal_ids.add(proposal_id)
        return proposal_ids

    def _auto_renumber_proposal_branch(
        self,
        *,
        proposal_id: str,
        metadata: dict[str, object],
        remote_ids: set[str],
    ) -> tuple[str, Path, dict[str, object], Path]:
        old_dir = self._find_proposal_dir(proposal_id)
        proposal_text = _read_optional(old_dir / "proposal.md")
        title = _clean_proposal_title(_read_title(proposal_text) or proposal_id, proposal_id)
        actor_slug = str(metadata.get("actor_slug") or _slugify(str(metadata.get("actor") or "local")) or "local")
        base_commit = str(metadata.get("base_commit") or head_commit(self.root) or "")
        if not base_commit:
            raise ValueError("Cannot auto-renumber proposal branch without a base commit")

        new_id = self._next_available_proposal_id(remote_ids)
        title_slug = _slugify(title)
        new_dir = self.p2p_dir / "proposals" / f"{new_id}-{title_slug}"
        if new_dir.exists():
            raise ValueError(f"Cannot auto-renumber proposal branch; target proposal already exists: {new_id}")

        branch_hash16 = _branch_hash16(new_id, title, actor_slug, base_commit)
        new_branch_name = _proposal_branch_name(new_id, title, actor_slug, branch_hash16)
        if branch_exists(self.root, new_branch_name):
            raise ValueError(f"Cannot auto-renumber proposal branch; branch already exists: {new_branch_name}")

        shutil.move(str(old_dir), str(new_dir))
        for path in sorted(new_dir.iterdir()):
            if path.is_file() and path.suffix in {".md", ".yml", ".yaml"}:
                text = path.read_text(encoding="utf-8")
                path.write_text(text.replace(proposal_id, new_id), encoding="utf-8")

        metadata_path = new_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default=metadata)
        old_branch_name = str(metadata.get("branch_name") or "")
        metadata["proposal_id"] = new_id
        metadata["status"] = "branched"
        metadata["branch_name"] = new_branch_name
        metadata["branch_hash16"] = branch_hash16
        metadata["renumbered_from"] = proposal_id
        metadata["renumbered_at"] = date.today().isoformat()
        metadata["id_collision_check"] = {
            "remote_ids": sorted(remote_ids),
            "old_proposal_id": proposal_id,
            "new_proposal_id": new_id,
        }
        metadata["remote"] = None
        metadata["remote_url"] = None
        metadata["remote_branch"] = None
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")

        if old_branch_name and not rename_current_branch(self.root, new_branch_name):
            raise ValueError(f"Failed to rename managed proposal branch to {new_branch_name}")
        if commit_all(self.root, f"P2P proposal auto-renumber {proposal_id} to {new_id}") is None:
            raise ValueError("Failed to create managed proposal auto-renumber commit")
        return new_id, new_dir, metadata, metadata_path

    def _next_available_proposal_id(self, extra_ids: set[str] | None = None) -> str:
        used: set[int] = set()
        proposals_dir = self.p2p_dir / "proposals"
        for path in proposals_dir.iterdir() if proposals_dir.exists() else []:
            proposal_id = _proposal_id_from_dir_name(path.name)
            if proposal_id:
                used.add(int(proposal_id.removeprefix("PROP-")))
        for proposal_id in extra_ids or set():
            if re.match(r"^PROP-\d{3}$", proposal_id):
                used.add(int(proposal_id.removeprefix("PROP-")))
        next_id = max(used or {0}) + 1
        return f"PROP-{next_id:03d}"

    def _sync_remote(self, remote: str | None) -> str | None:
        if remote:
            return remote
        profile = self.remote_profile()
        return profile.remote

    def _require_sync_remote(self, status: SyncStatus) -> str:
        if not status.is_repository:
            raise ValueError("Cannot sync outside a Git repository")
        if not status.remote:
            raise ValueError("Cannot sync project without a configured Git remote")
        if status.remote_url is None:
            raise ValueError(f"Cannot sync project: Git remote not found: {status.remote}")
        return status.remote

    def _next_change_id(self) -> str:
        max_id = 0
        changes_dir = self.p2p_dir / "changes"
        for path in changes_dir.iterdir() if changes_dir.exists() else []:
            match = re.match(r"CHANGE-(\d{3})-", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"CHANGE-{max_id + 1:03d}"

    def _find_change_dir(self, change_id: str) -> Path:
        changes_dir = self.p2p_dir / "changes"
        if not changes_dir.exists():
            raise ValueError("No .p2p/changes directory found.")
        matches = [path for path in changes_dir.iterdir() if path.name.startswith(f"{change_id}-")]
        if not matches:
            raise ValueError(f"Change Set not found: {change_id}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous Change Set ID: {change_id}")
        return matches[0]

    def _next_intake_id(self) -> str:
        max_id = 0
        intake_dir = self.p2p_dir / "intake"
        for path in intake_dir.iterdir() if intake_dir.exists() else []:
            match = re.match(r"INTAKE-(\d{3})$", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"INTAKE-{max_id + 1:03d}"

    def _find_intake_dir(self, intake_id: str) -> Path:
        intake_dir = self.p2p_dir / "intake"
        if not intake_dir.exists():
            raise ValueError("No .p2p/intake directory found.")
        path = intake_dir / intake_id
        if not path.is_dir():
            raise ValueError(f"Intake not found: {intake_id}")
        return path

    def _next_choice_id(self) -> str:
        max_id = 0
        choices_dir = self.p2p_dir / "choices"
        for path in choices_dir.iterdir() if choices_dir.exists() else []:
            match = re.match(r"CHOICE-(\d{3})-", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"CHOICE-{max_id + 1:03d}"

    def _find_choice_dir(self, choice_id: str) -> Path:
        choices_dir = self.p2p_dir / "choices"
        if not choices_dir.exists():
            raise ValueError("No .p2p/choices directory found.")
        matches = [path for path in choices_dir.iterdir() if path.name.startswith(f"{choice_id}-")]
        if not matches:
            raise ValueError(f"Choice not found: {choice_id}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous Choice ID: {choice_id}")
        return matches[0]

    def _next_work_id(self) -> str:
        return self._work_planning_service().next_id()

    def _find_work_dir(self, work_id: str) -> Path:
        return self._work_planning_service().find_dir(work_id)


BUILT_IN_AGENT_ADAPTERS = ("generic", "codex", "claude", "cursor", "copilot", "gemini", "opencode")
AGENT_PROFILES = {*BUILT_IN_AGENT_ADAPTERS, "all"}
REPOSITORY_MODES = {"local", "cloud"}
PROJECT_DOMAIN_TEMPLATES = {"generic", "software", "grant_document", "board_game"}
PROJECT_DOMAINS = {"none", "custom", *PROJECT_DOMAIN_TEMPLATES}

_BUILT_IN_RUBRICS: dict[str, list[dict[str, object]]] = {
    "generic": [
        {
            "id": "problem_definition",
            "title": "Problem Definition",
            "keywords": ["problem", "need", "objective", "goal", "context"],
        },
        {
            "id": "scope_boundaries",
            "title": "Scope Boundaries",
            "keywords": ["scope", "non-goal", "boundary", "out of scope"],
        },
        {
            "id": "requirements",
            "title": "Requirements",
            "keywords": ["requirement", "criteria", "acceptance", "must"],
        },
        {
            "id": "risks_tradeoffs",
            "title": "Risks and Tradeoffs",
            "keywords": ["risk", "tradeoff", "alternative", "constraint"],
        },
        {
            "id": "validation_plan",
            "title": "Validation Plan",
            "keywords": ["test", "validation", "verify", "acceptance"],
        },
    ],
    "software": [
        {
            "id": "problem_definition",
            "title": "Problem Definition",
            "keywords": ["problem", "need", "objective", "goal", "context"],
        },
        {
            "id": "scope_boundaries",
            "title": "Scope Boundaries",
            "keywords": ["scope", "non-goal", "boundary", "out of scope"],
        },
        {
            "id": "user_workflows",
            "title": "User Roles and Workflows",
            "keywords": ["user", "workflow", "role", "journey", "onboarding"],
        },
        {
            "id": "functional_requirements",
            "title": "Functional Requirements",
            "keywords": ["feature", "command", "function", "requirement", "acceptance"],
        },
        {
            "id": "non_functional_requirements",
            "title": "Non-Functional Requirements",
            "keywords": ["performance", "reliability", "scalability", "maintainability", "compatibility"],
        },
        {
            "id": "security_privacy",
            "title": "Security and Privacy",
            "keywords": ["security", "privacy", "permission", "auth", "malicious", "sandbox"],
        },
        {
            "id": "data_model",
            "title": "Data Model",
            "keywords": ["data model", "schema", "yaml", "json", "storage", "registry"],
        },
        {
            "id": "integration_boundaries",
            "title": "Integration Boundaries",
            "keywords": ["integration", "mcp", "api", "adapter", "boundary", "interface"],
        },
        {
            "id": "deployment_operations",
            "title": "Deployment and Operations",
            "keywords": ["install", "packaging", "deploy", "release", "cloud", "local"],
        },
        {
            "id": "testing_strategy",
            "title": "Testing Strategy",
            "keywords": ["test", "pytest", "validation", "verify", "coverage"],
        },
        {
            "id": "ux_accessibility",
            "title": "UX and Accessibility",
            "keywords": ["ux", "usability", "accessibility", "wizard", "onboarding"],
        },
        {
            "id": "risks_tradeoffs",
            "title": "Risks and Tradeoffs",
            "keywords": ["risk", "tradeoff", "alternative", "constraint"],
        },
        {
            "id": "acceptance_criteria",
            "title": "Acceptance Criteria",
            "keywords": ["acceptance", "definition of done", "criteria", "done"],
        },
    ],
    "grant_document": [
        {
            "id": "call_requirements",
            "title": "Call Requirements",
            "keywords": ["call", "requirement", "eligibility", "deadline"],
        },
        {
            "id": "objectives",
            "title": "Objectives",
            "keywords": ["objective", "impact", "beneficiary", "goal"],
        },
        {
            "id": "budget",
            "title": "Budget",
            "keywords": ["budget", "cost", "funding", "expense"],
        },
        {
            "id": "evaluation_criteria",
            "title": "Evaluation Criteria",
            "keywords": ["evaluation", "score", "criteria", "award"],
        },
    ],
    "board_game": [
        {
            "id": "core_loop",
            "title": "Core Gameplay Loop",
            "keywords": ["turn", "round", "loop", "gameplay"],
        },
        {
            "id": "components",
            "title": "Components",
            "keywords": ["component", "card", "board", "token", "piece"],
        },
        {
            "id": "rules",
            "title": "Rules",
            "keywords": ["rule", "action", "phase", "win"],
        },
        {
            "id": "playtesting",
            "title": "Playtesting",
            "keywords": ["playtest", "balance", "test", "feedback"],
        },
    ],
}


def _normalize_agent_profile(profile: str) -> str:
    normalized = profile.strip().lower().replace("_", "-")
    if "," in normalized:
        parts = [item.strip() for item in normalized.split(",") if item.strip()]
        normalized_parts = [_normalize_agent_profile(item) for item in parts]
        if "all" in normalized_parts:
            return "all"
        return ",".join(sorted(set(normalized_parts)))
    aliases = {
        "claude-code": "claude",
        "anthropic": "claude",
        "openai-codex": "codex",
        "github-copilot": "copilot",
        "gemini-cli": "gemini",
        "open-code": "opencode",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in AGENT_PROFILES:
        valid = ", ".join([*BUILT_IN_AGENT_ADAPTERS, "all"])
        raise ValueError(f"Agent profile must be one of: {valid}")
    return normalized


def _expanded_agent_profiles(profile: str) -> list[str]:
    if "," in profile:
        expanded: set[str] = {"generic"}
        for item in profile.split(","):
            expanded.update(_expanded_agent_profiles(item))
        return sorted(expanded)
    if profile == "all":
        return list(BUILT_IN_AGENT_ADAPTERS)
    if profile == "generic":
        return ["generic"]
    return ["generic", profile]


def _remove_empty_parents(path: Path, *, stop_at: Path) -> None:
    path = path.resolve()
    stop_at = stop_at.resolve()
    while path != stop_at and stop_at in path.parents:
        try:
            path.rmdir()
        except OSError:
            return
        path = path.parent


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _managed_markdown_header(adapter: str, template_id: str) -> str:
    return (
        "<!--\n"
        "Managed by P2P Engine.\n"
        f"Adapter: {adapter}\n"
        f"Template: {template_id}\n"
        "Do not edit generated sections unless you accept drift.\n"
        "-->\n\n"
    )


READINESS_GAP_HANDLING_BLOCK = """When a proposal is weak, low-confidence, below target, or has failed readiness gates, do not stop at diagnosis.

For each failed gate or material gap:
1. explain why the gate failed in proposal-specific terms;
2. propose one to three concrete alternatives;
3. recommend one option when evidence supports a recommendation;
4. identify the owner decision required;
5. draft the exact artifact update that would close the gap;
6. ask for confirmation only where owner authority is required;
7. re-check or request readiness re-check after refinement."""


def _agent_adapter_capabilities(adapter_id: str) -> dict[str, object]:
    return {
        "mcp": "supported",
        "shell": "supported",
        "project_instructions": True,
        "skill": adapter_id in {"codex"},
    }


def _normalize_repository_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in REPOSITORY_MODES:
        raise ValueError("Repository mode must be local or cloud")
    return normalized


def _init_remote_profile_payload(
    root: Path,
    *,
    repository_mode: str,
    provider: str | None,
    remote: str,
    url: str | None,
) -> dict[str, object]:
    if repository_mode == "local":
        if provider or url:
            raise ValueError("Remote provider and URL options require --repository cloud")
        return {
            "mode": "local",
            "provider": "local",
            "remote": None,
            "url": None,
            "review_request": {
                "mode": "advisory",
                "opens_external_request": False,
            },
        }

    selected_provider = (provider or "generic").strip().lower()
    if selected_provider not in {"generic", "github", "gitlab"}:
        raise ValueError("Remote provider must be generic, github, or gitlab")
    selected_remote = (remote or "origin").strip()
    if not selected_remote:
        raise ValueError("Remote name is required for cloud-backed projects")
    resolved_url = url or remote_url(root, selected_remote)
    return {
        "mode": "remote",
        "provider": selected_provider,
        "remote": selected_remote,
        "url": resolved_url,
        "review_request": {
            "mode": "advisory",
            "opens_external_request": False,
        },
    }


def _normalize_project_domain(domain: str) -> str:
    normalized = domain.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "": "none",
        "no_template": "none",
        "no_domain": "none",
        "unresolved": "none",
        "blank": "none",
        "empty": "none",
        "custom_unresolved": "custom",
        "soft": "software",
        "software_development": "software",
        "grant": "grant_document",
        "bid": "grant_document",
        "tender": "grant_document",
        "game": "board_game",
        "boardgame": "board_game",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in PROJECT_DOMAINS:
        raise ValueError(
            "Project domain must be none, custom, generic, software, grant_document, or board_game"
        )
    return normalized


def _domain_state_payload(domain: str) -> dict[str, object]:
    domain = _normalize_project_domain(domain)
    if domain in PROJECT_DOMAIN_TEMPLATES:
        return {
            "version": "1.0",
            "status": "template_selected",
            "type": "template",
            "name": domain,
            "template": domain,
        }
    return {
        "version": "1.0",
        "status": "unresolved",
        "type": domain,
        "name": None,
        "template": None,
        "next_actions": [
            {
                "kind": "define_custom_domain" if domain == "custom" else "define_domain",
                "title": "Define the project domain with the user and agent",
            },
            {
                "kind": "define_domain_rubric",
                "title": "Define the project rubric and coverage criteria",
            },
        ],
    }


def _domain_setup_next_actions_payload(domain: str) -> dict[str, object]:
    domain = _normalize_project_domain(domain)
    label = "custom" if domain == "custom" else "project"
    return {
        "next_actions": [
            {
                "id": "NEXT-001",
                "priority": "high",
                "kind": "define_domain",
                "target": "project-domain",
                "reason": f"The {label} domain is unresolved and must be defined before maturity can be assessed.",
                "command": "p2p project show overview",
            },
            {
                "id": "NEXT-002",
                "priority": "high",
                "kind": "define_domain_rubric",
                "target": "project-rubric",
                "reason": "The project rubric is unresolved and has no enabled criteria.",
                "command": "p2p project rubrics show",
            },
        ]
    }


def _rubrics_payload(domain: str, rubric_enabled: dict[str, bool] | None = None) -> dict[str, object]:
    domain = _normalize_project_domain(domain)
    rubric_enabled = rubric_enabled or {}
    if domain not in PROJECT_DOMAIN_TEMPLATES:
        return {
            "version": "1.0",
            "domain": domain,
            "status": "unresolved",
            "template": None,
            "assessment_type": "project_definition_maturity",
            "scoring": {
                "covered": 100,
                "partial": 50,
                "missing": 0,
            },
            "criteria": [],
            "next_actions": [
                {
                    "kind": "define_domain",
                    "title": "Define the project domain with the user and agent",
                },
                {
                    "kind": "define_domain_rubric",
                    "title": "Define the project rubric and coverage criteria",
                },
            ],
        }
    return {
        "version": "1.0",
        "domain": domain,
        "status": "template_selected",
        "template": domain,
        "assessment_type": "project_definition_maturity",
        "scoring": {
            "covered": 100,
            "partial": 50,
            "missing": 0,
        },
        "criteria": [
            {
                "id": str(item["id"]),
                "title": str(item["title"]),
                "enabled": bool(rubric_enabled.get(str(item["id"]), True)),
                "required": True,
                "keywords": list(item.get("keywords", [])),
            }
            for item in _BUILT_IN_RUBRICS[domain]
        ],
    }


def _agent_instruction_files(
    project_name: str,
    profiles: list[str],
    repository_mode: str,
) -> dict[Path, str]:
    profiles = sorted(set(profiles))
    files = {Path("AGENTS.md"): _agents_markdown(project_name, profiles, repository_mode)}
    if "codex" in profiles:
        files[Path(".agents/skills/p2p-project/SKILL.md")] = _shared_p2p_project_skill(
            project_name,
            repository_mode,
        )
        files[Path(".codex/skills/p2p-project/SKILL.md")] = _codex_project_skill(
            project_name,
            repository_mode,
        )
    if "claude" in profiles:
        files[Path("CLAUDE.md")] = _claude_markdown(project_name, repository_mode)
    if "cursor" in profiles:
        files[Path(".cursor/rules/p2p.mdc")] = _cursor_rule(project_name, repository_mode)
    if "copilot" in profiles:
        files[Path(".github/copilot-instructions.md")] = _copilot_instructions(
            project_name,
            repository_mode,
        )
    if "gemini" in profiles:
        files[Path("GEMINI.md")] = _gemini_markdown(project_name, repository_mode)
    return files


def _agent_adapter_files(
    project_name: str,
    adapter_id: str,
    profiles: list[str],
    repository_mode: str,
) -> list[tuple[Path, str, bool, str]]:
    files: list[tuple[Path, str, bool, str]] = []
    if adapter_id == "generic":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path(".p2p/agent-policy.yml"), "generic-agent-policy-v1", True, "generic"))
    elif adapter_id == "codex":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path(".agents/skills/p2p-project/SKILL.md"), "codex-p2p-skill-v1", False, "codex"))
        files.append((Path(".codex/skills/p2p-project/SKILL.md"), "codex-legacy-p2p-skill-v1", False, "codex"))
    elif adapter_id == "claude":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path("CLAUDE.md"), "claude-md-v1", False, "claude"))
    elif adapter_id == "cursor":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path(".cursor/rules/p2p.mdc"), "cursor-p2p-rule-v1", False, "cursor"))
    elif adapter_id == "copilot":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path(".github/copilot-instructions.md"), "copilot-instructions-v1", False, "copilot"))
    elif adapter_id == "gemini":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
        files.append((Path("GEMINI.md"), "gemini-md-v1", False, "gemini"))
    elif adapter_id == "opencode":
        files.append((Path("AGENTS.md"), "generic-agents-md-v1", True, "generic"))
    return files


def _agent_policy(project_name: str, profiles: list[str], repository_mode: str) -> dict[str, object]:
    return {
        "p2p_agent_policy": {
            "version": "1.0",
            "project_name": project_name,
            "source_of_truth": "p2p_cli",
            "missing_primitive_behavior": "stop_and_report",
            "direct_p2p_file_edits": "forbidden",
            "owner_controls_governance": True,
        },
        "repository": {
            "mode": repository_mode,
            "cloud_is_advisory_until_configured": repository_mode == "cloud",
        },
        "agent_profiles": profiles,
        "runtime_bootstrap": {
            "discovery_order": [
                "p2p",
                ".venv/bin/p2p",
                "python -m p2p_engine",
                "available MCP tools",
            ],
            "doctor_commands": [
                "p2p doctor",
                "p2p agent doctor",
                ".venv/bin/p2p agent doctor",
                "python -m p2p_engine agent doctor",
            ],
            "when_unavailable": "stop_and_report_diagnostics",
        },
        "mcp": {
            "default_mode": "read_only",
            "write_tools_require_explicit_tool_schema": True,
            "missing_write_tool_behavior": "stop_and_report",
        },
        "owner_controlled_actions": [
            "proposal_accept",
            "proposal_reject",
            "proposal_defer",
            "choice_decide",
            "work_accept",
            "work_finalize",
            "work_cleanup",
            "proposal_branch_accept",
            "proposal_branch_reject",
            "proposal_branch_merge",
            "proposal_branch_finalize",
            "proposal_branch_remote_publish",
            "direct_git_merge",
            "raw_git_managed_branch",
            "raw_git_managed_sync",
        ],
        "proposal_readiness": {
            "inspect_before_acceptance_recommendation": True,
            "gap_handling": {
                "do_not_stop_at_diagnosis": True,
                "steps": [
                    "explain_failed_gate",
                    "propose_alternatives",
                    "recommend_when_supported",
                    "identify_owner_decision",
                    "draft_candidate_update",
                    "ask_only_for_owner_authority",
                    "recheck_readiness",
                ],
            },
            "commands": [
                "p2p proposal readiness show PROP-XXX",
                "p2p proposal readiness init PROP-XXX",
                "p2p proposal readiness refresh PROP-XXX",
                "p2p proposal readiness explain PROP-XXX",
            ],
            "mcp_tools": [
                "p2p_proposal_readiness_get",
                "p2p_proposal_readiness_init",
                "p2p_proposal_readiness_refresh",
                "p2p_proposal_readiness_explain",
                "p2p_proposal_readiness_list_gaps",
            ],
            "computed_score_is_advisory": True,
            "owner_override_must_not_falsify_computed_score": True,
        },
        "managed_git_collaboration": {
            "raw_git_for_managed_state": "forbidden_without_owner_escape_hatch",
            "inspect_before_branching": [
                "p2p status",
                "p2p sync status",
            ],
            "proposal_branch_commands": [
                "p2p proposal branch PROP-XXX --actor <actor>",
                "p2p proposal status PROP-XXX",
                "p2p proposal publish PROP-XXX",
                "p2p proposal publish PROP-XXX --auto-renumber",
                "p2p proposal request-review PROP-XXX",
                "p2p proposal scan",
                "p2p proposal retire-branch PROP-XXX --reason <reason>",
            ],
            "sync_commands": [
                "p2p sync status",
                "p2p sync fetch",
                "p2p sync pull",
                "p2p sync push",
            ],
            "mcp_tools": [
                "p2p_project_remote_configure",
                "p2p_consent_request",
                "p2p_sync_status",
                "p2p_sync_fetch",
                "p2p_sync_pull",
                "p2p_sync_push",
                "p2p_proposal_draft_commit",
                "p2p_proposal_branch",
                "p2p_proposal_branch_status",
                "p2p_proposal_publish",
                "p2p_proposal_request_review",
                "p2p_proposal_accept_branch",
                "p2p_proposal_reject_branch",
                "p2p_proposal_merge",
                "p2p_proposal_finalize",
                "p2p_proposal_cleanup",
                "p2p_proposal_branch_scan",
            ],
            "deferred_permission_gated_mcp_tools": [
                "p2p_proposal_retire_branch",
                "p2p_work_publish",
                "p2p_work_finalize",
            ],
        },
        "allowed_mutation_boundary": {
            "use_p2p_cli_commands": True,
            "use_mcp_write_tools_only_when_available": True,
            "invent_internal_p2p_files": False,
            "invent_ids_or_registry_entries": False,
            "write_decision_files_directly": False,
        },
        "explain_existing_artifacts": {
            "read_before_explaining": True,
            "allowed_sources": [
                "p2p context",
                "p2p proposal show",
                "p2p choice show",
                "p2p change show",
                "p2p work show",
                "equivalent MCP show/read tools",
            ],
            "avoid_memory_only_explanations": True,
        },
        "token_budget": {
            "compact_context_first": True,
            "default_command": "p2p context --budget small",
            "mcp_tool": "p2p_context",
            "read_details_only_by_id": True,
            "broad_scans_require_explicit_need": True,
            "advanced_token_estimation": "deferred",
        },
    }


def _agents_markdown(project_name: str, profiles: list[str], repository_mode: str) -> str:
    profile_text = ", ".join(profiles)
    return f"""{_managed_markdown_header("generic", "generic-agents-md-v1")}# Agent Instructions - {project_name}

This project uses P2P Engine.

## Source Of Truth

- Use the `p2p` CLI as the public write interface.
- Treat `.p2p/` as managed project state.
- Do not create, edit, rename, or delete files under `.p2p/` by hand unless the owner explicitly asks for a repair.
- Do not invent proposal IDs, choice IDs, change IDs, work IDs, registry entries, or internal P2P file layouts.

## Missing Primitive Rule

If the requested action cannot be performed with an available `p2p` command or an explicit MCP write tool, stop and report the limitation.

Do not satisfy the request by reverse-engineering `.p2p/` and writing files directly.

## Runtime Bootstrap

If `p2p` is not available on `PATH`, try this discovery order before stopping:

```bash
p2p doctor
.venv/bin/p2p agent doctor
python -m p2p_engine agent doctor
python -m p2p_engine.mcp.server --root /path/to/project
```

Use the first available P2P command as the write interface. If no CLI command or explicit MCP write tool is available, report the diagnostics and ask the owner to install P2P Engine or provide a runner/container with P2P installed. Do not edit `.p2p/` manually as a fallback.

## Governance Boundary

The owner controls governance decisions. Agents may draft, analyze, compare, and suggest actions, but must not decide on behalf of the owner.

Owner-controlled actions include:

- accepting, rejecting, or deferring proposals;
- deciding choices;
- accepting, finalizing, cleaning up, or merging managed work;
- accepting, rejecting, merging, or finalizing managed proposal branches;
- changing governance policy;
- creating direct Git merges into the main branch.

## Proposal Readiness

Before recommending proposal acceptance, inspect readiness with:

```bash
p2p proposal readiness show PROP-XXX
p2p proposal readiness init PROP-XXX
p2p proposal readiness refresh PROP-XXX
p2p proposal readiness explain PROP-XXX
```

If readiness is missing, weak, below target, or blocked by failed gates, ask focused owner questions and identify concrete missing artifacts before recommending acceptance. Readiness is advisory; the owner may still decide, but an owner override must be described separately from the computed score.

### Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

## Managed Git Collaboration

Do not run raw `git branch`, `git fetch`, `git pull`, `git push`, `git merge`, or provider PR/MR commands for managed P2P project state unless the owner explicitly authorizes an escape hatch.

Use P2P-managed commands instead:

```bash
p2p sync status
p2p sync fetch
p2p sync pull
p2p sync push
p2p proposal branch PROP-XXX --actor "name-or-agent"
p2p proposal status PROP-XXX
p2p proposal publish PROP-XXX
p2p proposal publish PROP-XXX --auto-renumber
p2p proposal request-review PROP-XXX
p2p proposal scan
p2p proposal retire-branch PROP-XXX --reason "..."
```

Before creating proposal or Work branches, inspect P2P state and sync state. Stop for owner approval before remote publication, accept, reject, merge, finalize, cleanup, or any operation marked owner-controlled by policy.

## MCP Boundary

Assume MCP tools are read-only unless the tool schema explicitly describes a write action.

When MCP is read-only, use it for status and inspection only. For mutations, use `p2p` CLI commands when available or explicit write-safe MCP tools such as `p2p_project_remote_configure`, `p2p_consent_request`, `p2p_proposal_draft_commit`, `p2p_proposal_branch`, and `p2p_sync_fetch` when their schema matches the requested action.

MCP may use implemented permission-gated repository tools only with a valid consent receipt. MCP must not retire or create provider PR/MR handoffs until those operations are explicitly implemented and authorized.

## Explaining Existing P2P Artifacts

Before explaining an existing proposal, choice, Change Set, or Work item, read it from P2P state first.

Use `p2p proposal show`, `p2p choice show`, `p2p change show`, `p2p work show`, or an equivalent MCP show/read tool. Do not explain existing P2P artifacts only from conversation memory.

## Token Budget Discipline

AI is expensive. CLI is cheap. Git is memory. `.p2p` is governance. Owner decides. Agent works in bounded sessions.

Before broad reads, use compact context:

```bash
p2p context --budget small
p2p context --target PROP-XXX --budget small
```

With MCP, use `p2p_context` first.

Read summaries first; read details only by explicit ID. Do not scan all `.p2p/`, all registries, all proposals, all source files, or Git history unless the task explicitly requires it or compact context is insufficient.

## Recommended Start

Run or request:

```bash
p2p status
p2p context --budget small
p2p registry refresh
p2p next
```

For a new idea, prefer:

```bash
p2p intake prompt "idea"
```

or, when the owner explicitly wants a new proposal:

```bash
p2p proposal create "Title" --problem "..." --goal "..." --proposal "..." --acceptance "..."
```

## Project Bootstrap

- Initial agent profiles: {profile_text}
- Repository mode: {repository_mode}
- Additional agent instructions can be added later with `p2p agent instructions refresh`.
"""


def _shared_p2p_project_skill(project_name: str, repository_mode: str) -> str:
    return f"""---
name: p2p-project
description: Use when working in this P2P-managed project. Enforces P2P Engine boundaries for any compatible project skill loader.
---

{_managed_markdown_header("codex", "codex-p2p-skill-v1")}\
# P2P Project Skill - {project_name}

Use P2P Engine as the source of truth for project governance and planning.

## Required Behavior

- Read `AGENTS.md` and `.p2p/agent-policy.yml` before modifying project state.
- Use `p2p` CLI commands or explicit MCP write tools for P2P mutations.
- If no CLI command or MCP write tool exists for the requested operation, stop and report the missing primitive.
- Do not edit `.p2p/` internals directly, invent IDs, or synthesize decision files.
- Do not accept, reject, defer, decide, merge, finalize, or cleanup without explicit owner instruction.
- Do not recommend proposal acceptance before checking readiness.
- Do not run raw Git commands for managed branch, sync, publish, or merge work unless the owner explicitly authorizes an escape hatch.
- Use compact context before broad file reads.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

Repository mode: `{repository_mode}`.
"""


def _codex_project_skill(project_name: str, repository_mode: str) -> str:
    return f"""---
name: p2p-project
description: Use when working in this P2P-managed project. Enforces P2P Engine boundaries for Codex.
---

{_managed_markdown_header("codex", "codex-legacy-p2p-skill-v1")}\
# P2P Project Skill - {project_name}

Use P2P Engine as the source of truth for project governance and planning.

## Required Behavior

- Read `AGENTS.md` and `.p2p/agent-policy.yml` before modifying project state.
- Use `p2p` CLI commands for P2P mutations.
- If `p2p` is not on `PATH`, try `.venv/bin/p2p`, then `python -m p2p_engine`, then available MCP tools. Use `p2p agent doctor` or equivalent diagnostics before stopping.
- Use MCP only within the tool schema; read-only MCP tools do not authorize filesystem writes.
- If no CLI command or MCP write tool exists for the requested operation, stop and report the missing primitive.
- Do not edit `.p2p/` internals directly, invent IDs, or synthesize decision files.
- Do not accept, reject, defer, decide, merge, finalize, or cleanup without explicit owner instruction.
- Do not recommend proposal acceptance before checking readiness or explicitly stating that readiness is missing.
- Do not run raw Git commands for managed branch, sync, publish, or merge work unless the owner explicitly authorizes an escape hatch.
- Use `p2p sync status` before managed branch work, `p2p proposal branch` for proposal branches, and `p2p proposal publish --auto-renumber` only when publish reports a recoverable proposal ID collision.
- Before explaining existing proposals, choices, Change Sets, or Work items, use the relevant `p2p ... show` command or equivalent MCP read tool.
- Use `p2p context --budget small` or MCP `p2p_context` before broad file reads.
- Do not scan all `.p2p/`, registries, source files, or Git history unless the task explicitly requires it.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

## Useful Commands

```bash
p2p status
p2p context --budget small
p2p registry refresh
p2p next
p2p proposal list
p2p proposal readiness show PROP-XXX
p2p proposal readiness init PROP-XXX
p2p proposal readiness refresh PROP-XXX
p2p proposal readiness explain PROP-XXX
p2p proposal branch PROP-XXX --actor "codex"
p2p proposal status PROP-XXX
p2p proposal publish PROP-XXX
p2p proposal publish PROP-XXX --auto-renumber
p2p proposal request-review PROP-XXX
p2p proposal scan
p2p sync status
p2p sync fetch
p2p sync pull
p2p sync push
p2p choice list
p2p change status
p2p work status
```

Repository mode: `{repository_mode}`.
"""


def _claude_markdown(project_name: str, repository_mode: str) -> str:
    return f"""{_managed_markdown_header("claude", "claude-md-v1")}# Claude Instructions - {project_name}

This repository is managed with P2P Engine.

Follow `AGENTS.md` and `.p2p/agent-policy.yml`.

Key rules:

- Use `p2p` CLI commands for P2P writes.
- Do not modify `.p2p/` internals directly.
- If a requested P2P action has no available command or MCP write tool, stop and explain the missing primitive.
- Do not make owner-controlled governance decisions unless the owner explicitly instructs the exact decision.
- Do not recommend proposal acceptance before checking readiness or explicitly stating that readiness is missing.
- Do not run raw Git commands for managed branch, sync, publish, or merge work unless the owner explicitly authorizes an escape hatch.
- Use `p2p sync status`, `p2p proposal branch`, `p2p proposal publish`, `p2p proposal request-review`, and `p2p proposal scan` for managed collaboration workflows.
- Treat MCP as read-only unless a tool explicitly declares a write operation.
- Before explaining existing proposals, choices, Change Sets, or Work items, read them with the relevant `p2p ... show` command or equivalent MCP read tool.
- Use `p2p context --budget small` or MCP `p2p_context` before broad file reads.
- Do not scan all `.p2p/`, registries, source files, or Git history unless the task explicitly requires it.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

Repository mode: `{repository_mode}`.
"""


def _cursor_rule(project_name: str, repository_mode: str) -> str:
    return f"""---
description: P2P Engine project governance and agent workflow rules
alwaysApply: true
---

{_managed_markdown_header("cursor", "cursor-p2p-rule-v1")}\
# Cursor P2P Rules - {project_name}

- Use `p2p` CLI commands or explicit MCP write tools for P2P mutations.
- Do not edit `.p2p/` internals directly.
- Do not make owner-controlled governance decisions without explicit owner instruction.
- Inspect proposal readiness before recommending acceptance.
- Use compact context before broad file reads.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

Repository mode: `{repository_mode}`.
"""


def _copilot_instructions(project_name: str, repository_mode: str) -> str:
    return f"""{_managed_markdown_header("copilot", "copilot-instructions-v1")}# GitHub Copilot Instructions - {project_name}

This repository is managed with P2P Engine.

- Use `p2p` CLI commands for P2P writes when shell access is available.
- Use explicit MCP write tools only when the tool schema supports the requested operation.
- Do not edit `.p2p/` internals directly.
- Do not invent proposal, choice, change, work, registry, or decision IDs.
- Owner-controlled governance decisions require explicit owner instruction.
- Inspect readiness before recommending proposal acceptance.
- Prefer compact context before broad reads.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

Repository mode: `{repository_mode}`.
"""


def _gemini_markdown(project_name: str, repository_mode: str) -> str:
    return f"""{_managed_markdown_header("gemini", "gemini-md-v1")}# Gemini Instructions - {project_name}

This repository is managed with P2P Engine.

- Use `p2p` CLI commands or explicit MCP write tools for P2P mutations.
- Do not edit `.p2p/` internals directly.
- If no write primitive exists, stop and report the limitation.
- The owner controls governance decisions.
- Inspect readiness before recommending proposal acceptance.
- Use compact context before broad file reads.

## Readiness Gap Handling

{READINESS_GAP_HANDLING_BLOCK}

Repository mode: `{repository_mode}`.
"""


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def _yaml_dump(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


PERMISSION_ROLES = {"owner", "maintainer", "contributor", "agent", "readonly"}
ACTOR_KINDS = {"person", "agent", "client"}
CONSENT_OPERATIONS = {
    "proposal_accept",
    "proposal_reject",
    "proposal_defer",
    "proposal_publish",
    "proposal_request_review",
    "proposal_retire_branch",
    "proposal_accept_branch",
    "proposal_reject_branch",
    "proposal_merge",
    "proposal_finalize",
    "proposal_cleanup",
    "sync_pull",
    "sync_push",
    "work_publish",
    "work_request_review",
    "work_accept",
    "work_finalize",
    "work_cleanup",
}


def _permissions_payload(owner_name: str | None, repository_mode: str) -> dict[str, object]:
    owner_id = _identity_slug(owner_name or "owner")
    owner_display = owner_name or "owner"
    return {
        "permissions": {
            "version": 1,
            "model": "role_plus_consent_receipt",
            "identity_strength": "project_declared",
            "repository_mode": repository_mode,
            "cloud_enforcement": [
                "git_provider_permissions",
                "branch_protection",
                "required_approvals",
                "token_scopes",
            ],
        },
        "identities": {
            owner_id: {
                "role": "owner",
                "kind": "person",
                "display_name": owner_display,
            },
            "contributor": {
                "role": "contributor",
                "kind": "person",
                "display_name": "contributor",
            },
        },
        "roles": {
            "owner": {
                "can_grant_consent": True,
                "can_manage_permissions": True,
            },
            "maintainer": {
                "can_request_privileged_operations": True,
            },
            "contributor": {
                "can_create_local_branches": True,
                "can_request_review": True,
            },
            "agent": {
                "can_use_safe_tools": True,
            },
            "readonly": {
                "can_read": True,
            },
        },
        "tool_classes": {
            "safe_read": {"consent_required": False},
            "write_safe_preparatory": {"consent_required": False, "audit_required": True},
            "privileged_publish": {"consent_required": True},
            "owner_controlled_governance": {"consent_required": True, "owner_required": True},
            "destructive_or_external": {"consent_required": True, "single_use_required": True},
        },
    }


def _identity_slug(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Actor identity is required")
    return _slugify(text)


def _normalize_permission_role(role: str) -> str:
    role = str(role or "").strip().lower()
    if role not in PERMISSION_ROLES:
        allowed = ", ".join(sorted(PERMISSION_ROLES))
        raise ValueError(f"Invalid permission role: {role}. Allowed: {allowed}")
    return role


def _normalize_actor_kind(kind: str) -> str:
    kind = str(kind or "").strip().lower()
    if kind not in ACTOR_KINDS:
        allowed = ", ".join(sorted(ACTOR_KINDS))
        raise ValueError(f"Invalid actor kind: {kind}. Allowed: {allowed}")
    return kind


def _normalize_consent_operation(operation: str) -> str:
    operation = str(operation or "").strip().lower().replace("-", "_")
    if operation not in CONSENT_OPERATIONS:
        allowed = ", ".join(sorted(CONSENT_OPERATIONS))
        raise ValueError(f"Invalid consent operation: {operation}. Allowed: {allowed}")
    return operation


def _normalize_consent_id(consent_id: str) -> str:
    consent_id = str(consent_id or "").strip().upper()
    if not re.match(r"^CONSENT-\d{3}$", consent_id):
        raise ValueError(f"Invalid consent ID: {consent_id}")
    return consent_id


def _consent_receipt_from_payload(payload: dict[str, object], path: Path) -> ConsentReceipt:
    return ConsentReceipt(
        consent_id=str(payload.get("consent_id") or ""),
        operation=str(payload.get("operation") or ""),
        target=str(payload.get("target") or ""),
        actor_id=str(payload.get("actor_id") or ""),
        approved_by=str(payload.get("approved_by") or ""),
        status=str(payload.get("status") or "unknown"),
        single_use=bool(payload.get("single_use")),
        expires_on=str(payload.get("expires_on")) if payload.get("expires_on") else None,
        path=path,
    )


def _definition_maturity_payload(maturity: ProjectDefinitionMaturity) -> dict[str, object]:
    return {
        "generated_on": maturity.generated_on,
        "assessment_type": "project_definition_maturity",
        "domain": maturity.domain,
        "score": maturity.score,
        "status": maturity.status,
        "criteria": maturity.criteria,
        "gaps": maturity.gaps,
        "suggested_actions": maturity.suggested_actions,
    }


def _relative_to_root(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _short_text(value: str, limit: int = 360) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _proposal_markdown(
    proposal_id: str,
    title: str,
    problem: str | None = None,
    context: str | None = None,
    goals: list[str] | None = None,
    non_goals: list[str] | None = None,
    proposal: str | None = None,
    acceptance_criteria: list[str] | None = None,
) -> str:
    return (
        f"# {proposal_id} - {title}\n\n"
        "## Status\n\n"
        "`draft`\n\n"
        "## Problem\n\n"
        f"{_paragraph(problem) or 'Pending.'}\n\n"
        "## Context\n\n"
        f"{_paragraph(context) or 'Pending.'}\n\n"
        "## Goals\n\n"
        f"{_bullets(goals) or '- Pending.'}\n\n"
        "## Non-Goals\n\n"
        f"{_bullets(non_goals) or '- Pending.'}\n\n"
        "## Proposal\n\n"
        f"{_paragraph(proposal) or 'Pending.'}\n\n"
        "## Acceptance Criteria\n\n"
        f"{_bullets(acceptance_criteria) or '- Pending.'}\n\n"
        "## Decision\n\n"
        "Pending.\n"
    )


def _validate_readiness_profile_payload(data: dict[str, object]) -> None:
    profile = data.get("readiness_profile")
    if not isinstance(profile, dict):
        raise ValueError("Readiness profile must define top-level `readiness_profile` mapping.")
    profile_id = str(profile.get("id") or "").strip()
    version = str(profile.get("version") or "").strip()
    if not profile_id:
        raise ValueError("Readiness profile missing id.")
    if not version:
        raise ValueError("Readiness profile missing version.")
    criteria = profile.get("criteria")
    if not isinstance(criteria, dict) or not criteria:
        raise ValueError("Readiness profile must define criteria.")
    total = 0
    for criterion, points in criteria.items():
        if not str(criterion).strip():
            raise ValueError("Readiness profile contains empty criterion name.")
        if not isinstance(points, int) or points <= 0:
            raise ValueError(f"Readiness criterion must have positive integer points: {criterion}")
        total += points
    if total != 100:
        raise ValueError(f"Readiness criteria must total 100 points, got {total}.")
    thresholds = profile.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("Readiness profile must define thresholds.")
    for label in READINESS_LABELS:
        value = thresholds.get(label)
        if not isinstance(value, int) or value < 0 or value > 100:
            raise ValueError(f"Readiness threshold must be 0-100 integer: {label}")
    tier_requirements = profile.get("tier_requirements") or {}
    if tier_requirements and not isinstance(tier_requirements, dict):
        raise ValueError("Readiness tier_requirements must be a mapping.")
    for tier, requirement in dict(tier_requirements).items():
        if tier not in READINESS_TIERS:
            raise ValueError(f"Invalid readiness tier: {tier}")
        if not isinstance(requirement, dict):
            raise ValueError(f"Readiness tier requirement must be a mapping: {tier}")
        confidence = requirement.get("required_confidence")
        if confidence is not None and confidence not in READINESS_CONFIDENCE_LEVELS:
            raise ValueError(f"Invalid readiness confidence for tier {tier}: {confidence}")
    caps = profile.get("artifact_quality_caps") or {}
    if caps and not isinstance(caps, dict):
        raise ValueError("Readiness artifact_quality_caps must be a mapping.")
    for state, cap in dict(caps).items():
        if state not in READINESS_ARTIFACT_QUALITY_STATES:
            raise ValueError(f"Invalid artifact quality state: {state}")
        if not isinstance(cap, dict):
            raise ValueError(f"Artifact quality cap must be a mapping: {state}")


def _validate_readiness_assessment_payload(data: dict[str, object]) -> None:
    readiness = data.get("readiness")
    if not isinstance(readiness, dict):
        raise ValueError("Readiness assessment must define top-level `readiness` mapping.")
    status = str(readiness.get("status") or "assessed")
    if status == "not_assessed":
        return
    profile_id = str(readiness.get("profile_id") or "").strip()
    profile_version = str(readiness.get("profile_version") or "").strip()
    if not profile_id:
        raise ValueError("Readiness assessment missing profile_id.")
    if not profile_version:
        raise ValueError("Readiness assessment missing profile_version.")
    if "computed_score" in readiness:
        score = readiness["computed_score"]
        if not isinstance(score, int) or score < 0 or score > 100:
            raise ValueError("Readiness computed_score must be an integer from 0 to 100.")
    label = readiness.get("computed_label")
    if label is not None and label not in READINESS_LABELS:
        raise ValueError(f"Invalid readiness computed_label: {label}")
    confidence = readiness.get("confidence")
    if confidence is not None and confidence not in READINESS_CONFIDENCE_LEVELS:
        raise ValueError(f"Invalid readiness confidence: {confidence}")
    tier = readiness.get("tier")
    if tier is not None and tier not in READINESS_TIERS:
        raise ValueError(f"Invalid readiness tier: {tier}")
    for key in ("failed_gates", "missing", "suggested_next", "confidence_reasons"):
        value = readiness.get(key, [])
        if value is not None and not isinstance(value, list):
            raise ValueError(f"Readiness field must be a list: {key}")
    criteria = readiness.get("criteria") or {}
    if criteria and not isinstance(criteria, dict):
        raise ValueError("Readiness criteria must be a mapping.")
    for criterion, assessment in dict(criteria).items():
        if not str(criterion).strip():
            raise ValueError("Readiness criteria contains empty criterion name.")
        if not isinstance(assessment, dict):
            raise ValueError(f"Readiness criterion assessment must be a mapping: {criterion}")
        artifact_quality = assessment.get("artifact_quality")
        if artifact_quality is not None and artifact_quality not in READINESS_ARTIFACT_QUALITY_STATES:
            raise ValueError(f"Invalid artifact quality for criterion {criterion}: {artifact_quality}")
        awarded = assessment.get("awarded_points")
        if awarded is not None and (not isinstance(awarded, int) or awarded < 0):
            raise ValueError(f"Readiness awarded_points must be a non-negative integer: {criterion}")


def _validate_agent_integrations_payload(data: dict[str, object]) -> None:
    if data.get("schema_version") != 1:
        raise ValueError("Agent integrations registry must use schema_version: 1.")
    if data.get("baseline_profile") != "generic":
        raise ValueError("Agent integrations registry baseline_profile must be generic.")
    forbidden = {"active_agent", "default_agent", "preferred_agent", "current_agent", "use", "switch"}
    for key in forbidden:
        if key in data:
            raise ValueError(f"Agent integrations registry must not define {key}.")
    adapters = data.get("adapters")
    if not isinstance(adapters, dict):
        raise ValueError("Agent integrations registry must define adapters mapping.")
    for adapter_id, adapter in adapters.items():
        if adapter_id not in BUILT_IN_AGENT_ADAPTERS:
            raise ValueError(f"Unknown agent adapter: {adapter_id}")
        if not isinstance(adapter, dict):
            raise ValueError(f"Agent adapter record must be a mapping: {adapter_id}")
        if adapter.get("status") != "installed":
            raise ValueError(f"Agent adapter status must be installed: {adapter_id}")
        files = adapter.get("files")
        if not isinstance(files, list):
            raise ValueError(f"Agent adapter files must be a list: {adapter_id}")
        for record in files:
            if not isinstance(record, dict):
                raise ValueError(f"Agent adapter file record must be a mapping: {adapter_id}")
            for required in ("path", "shared", "owner", "managed", "template_id", "sha256", "drift"):
                if required not in record:
                    raise ValueError(f"Agent adapter file record missing {required}: {adapter_id}")
            if record["owner"] not in BUILT_IN_AGENT_ADAPTERS:
                raise ValueError(f"Invalid agent adapter file owner: {record['owner']}")
            sha256 = str(record.get("sha256") or "")
            if sha256 and not re.fullmatch(r"[0-9a-f]{64}", sha256):
                raise ValueError(f"Invalid SHA-256 for agent adapter file: {record.get('path')}")
            if record.get("drift") not in {"clean", "missing", "drifted", "unmanaged"}:
                raise ValueError(f"Invalid drift state for agent adapter file: {record.get('path')}")


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _exploration_files(proposal_id: str) -> dict[str, str]:
    return {
        "exploration.md": f"# Exploration - {proposal_id}\n\nNot explored yet.\n",
        "findings.md": "findings: []\n",
        "alternatives.md": f"# Alternatives - {proposal_id}\n\nNone identified yet.\n",
        "open-questions.md": f"# Open Questions - {proposal_id}\n\nNone identified yet.\n",
        "risks.md": f"# Risks - {proposal_id}\n\nNone identified yet.\n",
        "assumptions.md": f"# Assumptions - {proposal_id}\n\nNone identified yet.\n",
        "suggested-scope.md": f"# Suggested Scope - {proposal_id}\n\nNot suggested yet.\n",
    }


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_yaml(path: Path, default: object) -> object:
    if not path.exists():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if data is not None else default


def _read_yaml_mapping(path: Path, default: dict[str, object]) -> dict[str, object]:
    data = _read_yaml(path, default)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML mapping: {path}")
    return data


def _read_proposal_status(path: Path) -> str:
    if not path.exists():
        return "unknown"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"## Status\s+`([^`]+)`", text)
    return match.group(1) if match else "unknown"


def _proposal_id_from_dir_name(name: str) -> str | None:
    match = re.match(r"^(PROP-\d{3})-", name)
    return match.group(1) if match else None


def _proposal_id_from_branch_name(name: str) -> str | None:
    match = re.match(r"^p2p/proposal/(PROP-\d{3})-", name)
    return match.group(1) if match else None


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


def _proposal_branch_name(proposal_id: str, title: str, actor_slug: str, branch_hash16: str) -> str:
    title_slug = _slugify(title)[:48].strip("-") or "proposal"
    return f"p2p/proposal/{proposal_id}-{title_slug}-{actor_slug}-{branch_hash16}"


def _branch_hash16(proposal_id: str, title: str, actor_slug: str, base_commit: str) -> str:
    source = f"{proposal_id}\n{title}\n{actor_slug}\n{base_commit}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def _proposal_branch_detail_from_metadata(
    proposal_id: str,
    metadata: dict[str, object],
    path: Path,
) -> ProposalBranchDetail:
    return ProposalBranchDetail(
        proposal_id=str(metadata.get("proposal_id") or proposal_id),
        status=str(metadata.get("status") or "unknown"),
        branch_name=str(metadata.get("branch_name") or ""),
        base_branch=str(metadata.get("base_branch") or ""),
        actor=str(metadata.get("actor") or ""),
        branch_hash16=str(metadata.get("branch_hash16") or ""),
        remote=str(metadata.get("remote")) if metadata.get("remote") else None,
        remote_url=str(metadata.get("remote_url")) if metadata.get("remote_url") else None,
        path=path,
        metadata=metadata,
    )


def _clean_proposal_title(title: str, proposal_id: str) -> str:
    cleaned = re.sub(rf"^{re.escape(proposal_id)}\s*[-—]\s*", "", title).strip()
    return cleaned or title


def _metadata_only_git_policy() -> dict[str, object]:
    return {
        "git_policy": {
            "mode": "managed",
            "operation_level": "metadata_only",
            "expose_git_details": False,
            "commits": {"auto_commit": False},
            "branches": {"auto_create": False},
            "tags": {"auto_create": False},
        }
    }


def _change_markdown(
    change_id: str,
    title: str,
    source_proposal: str,
    created_on: str,
    summary: str,
    rationale: str,
) -> str:
    frontmatter = _yaml_dump(
        {
            "change_id": change_id,
            "title": title,
            "status": "proposed",
            "created_at": created_on,
            "created_by": "local",
            "execution_domains": ["software"],
            "source": {"accepted_proposals": [source_proposal], "accepted_decisions": []},
            "implementation_targets": ["local_cli"],
            "spec_targets": ["p2p_spec"],
            "export_targets": ["openspec", "speckit"],
            "plan_ref": "execution-plan.md",
            "tasks_ref": "tasks.yml",
        }
    )
    return (
        f"---\n{frontmatter}---\n\n"
        f"# {change_id} - {title}\n\n"
        "## Summary\n\n"
        f"{summary}\n\n"
        "## Rationale\n\n"
        f"{rationale}\n\n"
        "## Scope\n\n"
        "### Included\n\n"
        "- Derived from accepted proposal scope.\n\n"
        "### Excluded\n\n"
        "- Automatic Git commits, branches, tags, or merges.\n\n"
        "## Deliverables\n\n"
        "- Change Set metadata.\n\n"
        "## Acceptance Criteria\n\n"
        "- Change Set metadata is present and reviewable.\n\n"
        "## Dependencies\n\n"
        "- None recorded.\n\n"
        "## Risks\n\n"
        "- Metadata may need manual refinement before implementation.\n\n"
        "## Related Choices\n\n"
        "- None recorded.\n"
    )


def _intake_prompt_markdown(intake_id: str, idea: str, context: str) -> str:
    return (
        f"# P2P Intake Prompt - {intake_id}\n\n"
        "You are helping classify a raw idea against the current P2P project memory.\n\n"
        "## Governance Boundary\n\n"
        "Do not accept, reject, defer, merge or supersede proposals. "
        "Recommend next actions only. Final decisions must be recorded through P2P governance commands.\n\n"
        "## Raw Idea\n\n"
        f"{idea.strip()}\n\n"
        "## Project Context\n\n"
        f"{context}\n\n"
        "## Required Output\n\n"
        "Return artifacts with these shapes:\n\n"
        "### recommendation.md\n\n"
        "- classify the idea as new, duplicate, overlap, alternative, conflict, or unclear;\n"
        "- explain the rationale;\n"
        "- recommend exactly one primary next action.\n\n"
        "### related-proposals.yml\n\n"
        "```yaml\n"
        "related_proposals:\n"
        "  - proposal: PROP-000\n"
        "    relationship: related_to\n"
        "    rationale: Short reason.\n"
        "```\n\n"
        "### suggested-actions.yml\n\n"
        "```yaml\n"
        "suggested_actions:\n"
        "  - type: create_proposal | add_contribution | open_choice | record_conflict | defer | duplicate\n"
        "    target: PROP-000\n"
        "    rationale: Short reason.\n"
        "```\n"
    )


def _software_spec_required_files() -> tuple[str, ...]:
    return (
        "index.md",
        "requirements.md",
        "design.md",
        "commands.yml",
        "data-model.yml",
        "acceptance.md",
        "provenance.yml",
    )


def _software_spec_export_targets() -> tuple[str, ...]:
    return ("generic", "openspec", "speckit")


def _software_spec_export_files(
    change_id: str,
    target: str,
    title: str,
    spec_dir: Path,
    software_spec_path: str,
    definition: dict[str, object],
) -> dict[str, str]:
    spec = {filename: _read_optional(spec_dir / filename) for filename in _software_spec_required_files()}
    if target == "generic":
        return {
            "project.md": _project_definition_markdown(definition),
            "propose.md": _generic_propose_markdown(definition),
        }
    if target == "openspec":
        return {
            "propose.md": _openspec_propose_markdown(definition),
        }
    if target == "speckit":
        return {
            "speckit.constitution.md": _speckit_constitution_markdown(definition),
            "speckit.specify.md": _speckit_specify_markdown(definition),
            "speckit.plan.md": _speckit_plan_prompt_markdown(definition),
        }
    raise ValueError(f"Unsupported software spec export target: {target}")


def _software_spec_export_artifacts(target: str) -> list[str]:
    if target == "generic":
        return [
            "project.md",
            "propose.md",
        ]
    if target == "openspec":
        return [
            "propose.md",
        ]
    if target == "speckit":
        return [
            "speckit.constitution.md",
            "speckit.specify.md",
            "speckit.plan.md",
        ]
    return []


def _software_spec_export_required_files(change_id: str, target: str, export_dir: Path) -> list[Path]:
    if target == "generic":
        return [
            Path("project.md"),
            Path("propose.md"),
        ]
    if target == "openspec":
        return [
            Path("propose.md"),
        ]
    if target == "speckit":
        return [
            Path("speckit.constitution.md"),
            Path("speckit.specify.md"),
            Path("speckit.plan.md"),
        ]
    raise ValueError(f"Unsupported software spec export target: {target}")


def _software_spec_export_show_file(target: str) -> str:
    if target == "generic":
        return "project.md"
    if target == "openspec":
        return "propose.md"
    if target == "speckit":
        return "speckit.constitution.md"
    return "index.md"


def _project_definition_required_sections() -> tuple[str, ...]:
    return (
        "Executive Summary",
        "Vision",
        "Domain",
        "Problem",
        "Goals",
        "Non-Goals / Exclusions",
        "Stakeholders / Users",
        "Workflows",
        "Accepted Decisions",
        "Requirements",
        "Constraints",
        "Assumptions",
        "Dependencies",
        "Operating Model / Architecture",
        "Data / Knowledge Model",
        "Priorities",
        "Success Criteria",
        "Validation / Evaluation Method",
        "Risks And Tradeoffs",
        "Open Questions",
        "Pending Proposals",
        "Source Traceability",
    )


def _speckit_feature_dir(change_id: str, export_dir: Path) -> Path:
    specs_dir = export_dir / "specs"
    if specs_dir.is_dir():
        candidates = sorted(path for path in specs_dir.iterdir() if path.is_dir())
        if len(candidates) == 1:
            return Path("specs") / candidates[0].name
        for candidate in candidates:
            if candidate.name.startswith(change_id.lower()):
                return Path("specs") / candidate.name
    return Path("specs") / f"{change_id.lower()}-slug"


def _definition_value(definition: dict[str, object], key: str, default: str = "NEEDS CLARIFICATION") -> str:
    value = definition.get(key)
    if value is None:
        return default
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or default
    text = str(value).strip()
    return text or default


def _definition_spec(definition: dict[str, object], filename: str) -> str:
    spec = definition.get("spec", {})
    if not isinstance(spec, dict):
        return ""
    return str(spec.get(filename) or "")


def _definition_accepted(definition: dict[str, object]) -> list[dict[str, object]]:
    accepted = definition.get("accepted_proposals", [])
    return accepted if isinstance(accepted, list) else []


def _definition_drafts(definition: dict[str, object]) -> list[ProposalSummary]:
    drafts = definition.get("draft_proposals", [])
    return drafts if isinstance(drafts, list) else []


def _accepted_bullets(definition: dict[str, object], key: str, limit: int | None = None) -> str:
    lines: list[str] = []
    for item in _definition_accepted(definition)[:limit]:
        if not isinstance(item, dict):
            continue
        value = str(item.get(key) or "").strip()
        proposal_id = str(item.get("proposal_id") or "PROP-???")
        title = str(item.get("title") or proposal_id)
        if value:
            lines.append(f"- **{proposal_id} {title}**: {value}")
    return "\n".join(lines) or "- NEEDS CLARIFICATION"


def _proposal_sources(definition: dict[str, object]) -> str:
    lines: list[str] = []
    for item in _definition_accepted(definition):
        if not isinstance(item, dict):
            continue
        proposal_id = str(item.get("proposal_id") or "PROP-???")
        title = str(item.get("title") or proposal_id)
        source = str(item.get("source") or "")
        lines.append(f"- `{proposal_id}` {title} — `{source}`")
    return "\n".join(lines) or "- No accepted proposals found."


def _pending_proposals(definition: dict[str, object]) -> str:
    lines = [f"- `{item.proposal_id}` {item.title}" for item in _definition_drafts(definition)]
    return "\n".join(lines) or "- None."


def _domain_sections(definition: dict[str, object]) -> str:
    domain = _definition_value(definition, "domain", "generic")
    if domain == "software":
        return (
            "## Software Domain Extension\n\n"
            "### Technical Architecture\n\n"
            f"{_strip_markdown_title(_definition_spec(definition, 'design.md')) or 'NEEDS CLARIFICATION'}\n\n"
            "### CLI/API/UI Surface\n\n"
            "```yaml\n"
            f"{_definition_spec(definition, 'commands.yml').strip() or 'commands: []'}\n"
            "\n```\n\n"
            "### Testing Strategy\n\n"
            f"{_strip_markdown_title(_definition_spec(definition, 'acceptance.md')) or 'NEEDS CLARIFICATION'}\n\n"
            "### Deployment / Operations\n\n"
            "NEEDS CLARIFICATION\n\n"
            "### Integration Boundaries\n\n"
            f"- Implementation targets: {_definition_value(definition, 'implementation_targets')}\n"
            f"- Spec targets: {_definition_value(definition, 'spec_targets')}\n"
            f"- Export targets: {_definition_value(definition, 'export_targets')}\n"
        )
    if domain == "board_game":
        return (
            "## Board Game Domain Extension\n\n"
            "### Core Loop\n\nNEEDS CLARIFICATION\n\n"
            "### Player Roles\n\nNEEDS CLARIFICATION\n\n"
            "### Components\n\nNEEDS CLARIFICATION\n\n"
            "### Rules\n\nNEEDS CLARIFICATION\n\n"
            "### Win / Loss Conditions\n\nNEEDS CLARIFICATION\n\n"
            "### Playtest Plan\n\nNEEDS CLARIFICATION\n"
        )
    if domain == "grant_document":
        return (
            "## Grant Document Domain Extension\n\n"
            "### Funding Objective\n\nNEEDS CLARIFICATION\n\n"
            "### Eligibility\n\nNEEDS CLARIFICATION\n\n"
            "### Evaluation Criteria\n\nNEEDS CLARIFICATION\n\n"
            "### Required Documents\n\nNEEDS CLARIFICATION\n\n"
            "### Budget Structure\n\nNEEDS CLARIFICATION\n\n"
            "### Timeline And Milestones\n\nNEEDS CLARIFICATION\n"
        )
    return "## Domain Extension\n\nNEEDS CLARIFICATION\n"


def _project_definition_markdown(definition: dict[str, object]) -> str:
    project_name = _definition_value(definition, "project_name", "Project")
    change_id = _definition_value(definition, "change_id")
    change_title = _definition_value(definition, "change_title")
    requirements = _strip_markdown_title(_definition_spec(definition, "requirements.md")) or "NEEDS CLARIFICATION"
    acceptance = _strip_markdown_title(_definition_spec(definition, "acceptance.md")) or "NEEDS CLARIFICATION"
    data_model = _definition_spec(definition, "data-model.yml").strip() or "entities: []"
    return (
        f"# {project_name} Project Definition\n\n"
        "This document is synthesized from accepted P2P memory. It is the canonical generic project export. "
        "Draft or undecided material is listed only as pending or missing information.\n\n"
        "## Executive Summary\n\n"
        f"{_definition_value(definition, 'change_summary')}\n\n"
        "## Vision\n\n"
        "Organize confused, distributed, and discontinuous project intent into a governed project definition that agents can use without rediscovering context from scratch.\n\n"
        "## Domain\n\n"
        f"{_definition_value(definition, 'domain')}\n\n"
        "## Problem\n\n"
        f"{_accepted_bullets(definition, 'problem', limit=8)}\n\n"
        "## Goals\n\n"
        f"{_accepted_bullets(definition, 'goals', limit=8)}\n\n"
        "## Non-Goals / Exclusions\n\n"
        f"{_accepted_bullets(definition, 'non_goals', limit=8)}\n\n"
        "## Stakeholders / Users\n\n"
        "- Humans supervise outputs and make governance decisions.\n"
        "- AI agents use P2P memory and exports as structured project cognition.\n"
        "- Downstream tools receive initialization prompts or documents, not synthetic ownership of P2P state.\n\n"
        "## Workflows\n\n"
        "- Capture rough ideas as intake, proposals, or contributions.\n"
        "- Decide accepted direction through owner-controlled P2P governance.\n"
        "- Derive Change Sets and exports from accepted memory.\n"
        "- Use target-specific outputs to initialize downstream agent workflows.\n\n"
        "## Accepted Decisions\n\n"
        f"{_accepted_bullets(definition, 'decision', limit=12)}\n\n"
        "## Requirements\n\n"
        f"{requirements}\n\n"
        "## Constraints\n\n"
        "- Exports must not invent requirements unsupported by accepted P2P artifacts.\n"
        "- Missing information must be marked as NEEDS CLARIFICATION.\n"
        "- Draft proposals must not be treated as accepted project truth.\n\n"
        "## Assumptions\n\n"
        "- Accepted P2P proposals and decisions are authoritative project memory.\n"
        "- Target-specific exports are initialization artifacts for agents or downstream tools.\n\n"
        "## Dependencies\n\n"
        f"- Source Change Set: `{change_id}` {change_title}\n"
        "- P2P software spec artifacts generated before export.\n"
        "- Downstream tools, if used, run outside P2P export.\n\n"
        "## Operating Model / Architecture\n\n"
        f"{_strip_markdown_title(_definition_spec(definition, 'design.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "## Data / Knowledge Model\n\n"
        "```yaml\n"
        f"{data_model}\n"
        "\n```\n\n"
        "## Priorities\n\n"
        "- Preserve accepted project intent and governance first.\n"
        "- Produce small agent-consumable outputs instead of downstream-shaped folders.\n"
        "- Keep target-specific exports derived from this project definition.\n\n"
        "## Success Criteria\n\n"
        f"{acceptance}\n\n"
        "## Validation / Evaluation Method\n\n"
        "- Validate required export files exist.\n"
        "- Validate required project definition sections exist.\n"
        "- Validate source traceability is present.\n\n"
        "## Risks And Tradeoffs\n\n"
        "- Removing folder-shaped exports may surprise users of the previous MVP export layout.\n"
        "- Agent-first documents require clear traceability to avoid over-synthesis.\n\n"
        "## Open Questions\n\n"
        "- Which legacy bundle outputs, if any, should remain available behind an explicit compatibility flag?\n\n"
        "## Pending Proposals\n\n"
        f"{_pending_proposals(definition)}\n\n"
        f"{_domain_sections(definition)}\n\n"
        "## Source Traceability\n\n"
        f"- Source Change Set: `{change_id}` {change_title}\n"
        f"{_proposal_sources(definition)}\n"
    )


def _generic_propose_markdown(definition: dict[str, object]) -> str:
    return (
        "# Generic Project Initialization Prompt\n\n"
        "Use the accompanying `project.md` as authoritative project context. "
        "Initialize or continue the project without inventing requirements beyond accepted P2P memory.\n\n"
        "## Prompt\n\n"
        f"Build or continue the project described in `project.md`: {_definition_value(definition, 'project_name', 'Project')}.\n\n"
        "Respect accepted decisions, constraints, non-goals, and source traceability. "
        "Mark missing details as NEEDS CLARIFICATION.\n"
    )


def _openspec_propose_markdown(definition: dict[str, object]) -> str:
    return (
        "# OpenSpec Proposal Input\n\n"
        "Use this as the proposal-oriented initialization input for OpenSpec or an OpenSpec-aware agent.\n\n"
        "## Problem\n\n"
        f"{_accepted_bullets(definition, 'problem', limit=6)}\n\n"
        "## Proposed Change\n\n"
        f"{_accepted_bullets(definition, 'proposal', limit=6)}\n\n"
        "## Scope\n\n"
        f"{_accepted_bullets(definition, 'goals', limit=6)}\n\n"
        "## Out Of Scope\n\n"
        f"{_accepted_bullets(definition, 'non_goals', limit=6)}\n\n"
        "## Impact\n\n"
        f"- Source Change Set: `{_definition_value(definition, 'change_id')}` {_definition_value(definition, 'change_title')}\n\n"
        "## Risks\n\n"
        "- NEEDS CLARIFICATION: confirm target-specific risks before implementation.\n\n"
        "## Acceptance Criteria\n\n"
        f"{_strip_markdown_title(_definition_spec(definition, 'acceptance.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "## Source Traceability\n\n"
        f"{_proposal_sources(definition)}\n"
    )


def _speckit_constitution_markdown(definition: dict[str, object]) -> str:
    return (
        "# Spec Kit Constitution Prompt\n\n"
        "Use this content with `/speckit.constitution`. Establish governing principles from accepted P2P memory.\n\n"
        "## Principles To Establish\n\n"
        "- Preserve accepted project intent and source traceability.\n"
        "- Do not treat draft P2P proposals as accepted requirements.\n"
        "- Mark missing information as NEEDS CLARIFICATION.\n"
        "- Humans supervise outcomes and make governance decisions.\n"
        "- Agents use P2P exports as structured cognition, not as authority to bypass governance.\n\n"
        "## Existing Governance Context\n\n"
        f"{_definition_value(definition, 'constitution', 'NEEDS CLARIFICATION')}\n\n"
        "## Decision Rules\n\n"
        f"{_definition_value(definition, 'decision_rules', 'NEEDS CLARIFICATION')}\n"
    )


def _speckit_specify_markdown(definition: dict[str, object]) -> str:
    return (
        "# Spec Kit Specify Prompt\n\n"
        "Use this content with `/speckit.specify`. Focus on what and why; do not select a tech stack here.\n\n"
        "## What To Build\n\n"
        f"{_accepted_bullets(definition, 'proposal', limit=8)}\n\n"
        "## Why\n\n"
        f"{_accepted_bullets(definition, 'problem', limit=8)}\n\n"
        "## Users And Workflows\n\n"
        "- Humans supervise and decide.\n"
        "- Agents use P2P memory to preserve project context and propose bounded changes.\n\n"
        "## Requirements\n\n"
        f"{_strip_markdown_title(_definition_spec(definition, 'requirements.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "## Success Criteria\n\n"
        f"{_strip_markdown_title(_definition_spec(definition, 'acceptance.md')) or 'NEEDS CLARIFICATION'}\n"
    )


def _speckit_plan_prompt_markdown(definition: dict[str, object]) -> str:
    return (
        "# Spec Kit Plan Prompt\n\n"
        "Use this content with `/speckit.plan`. Provide technical implementation choices derived from accepted P2P memory.\n\n"
        "## Architecture / Operating Model\n\n"
        f"{_strip_markdown_title(_definition_spec(definition, 'design.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "## Implementation Targets\n\n"
        f"{_definition_value(definition, 'implementation_targets')}\n\n"
        "## Data Model\n\n"
        "```yaml\n"
        f"{_definition_spec(definition, 'data-model.yml').strip() or 'entities: []'}\n"
        "\n```\n\n"
        "## Testing And Validation\n\n"
        f"{_strip_markdown_title(_definition_spec(definition, 'acceptance.md')) or 'NEEDS CLARIFICATION'}\n\n"
        "## Constraints\n\n"
        "- Preserve P2P provenance.\n"
        "- Do not introduce implementation scope not supported by accepted P2P memory.\n"
    )


def _generic_spec_export_index(change_id: str, title: str) -> str:
    return (
        f"# Generic Software Spec Export - {change_id} - {title}\n\n"
        "## Purpose\n\n"
        "This bundle exports the P2P-native software spec in a stable, tool-neutral shape. "
        "It preserves the core spec artifacts so downstream tooling can consume them without reading raw P2P proposal folders.\n\n"
        "## Source\n\n"
        f"- Change Set: `{change_id}`\n"
        f"- Software spec: `.p2p/outputs/software-spec/{change_id}/`\n\n"
        "## Artifacts\n\n"
        "- `requirements.md`\n"
        "- `design.md`\n"
        "- `commands.yml`\n"
        "- `data-model.yml`\n"
        "- `acceptance.md`\n"
        "- `provenance.yml`\n"
        "- `manifest.yml`\n"
    )


def _openspec_export_index(change_id: str, title: str) -> str:
    return (
        f"# OpenSpec Export - {change_id} - {title}\n\n"
        "## Purpose\n\n"
        "This bundle exports the P2P-native software spec into an OpenSpec-oriented layout. "
        "The MVP keeps the mapping conservative: requirements, design, and acceptance content are combined into `spec.md`, "
        "while structured command, data-model, and provenance artifacts remain explicit sidecar files.\n\n"
        "## Source\n\n"
        f"- Change Set: `{change_id}`\n"
        f"- Software spec: `.p2p/outputs/software-spec/{change_id}/`\n\n"
        "## Artifacts\n\n"
        "- `spec.md`\n"
        "- `commands.yml`\n"
        "- `data-model.yml`\n"
        "- `provenance.yml`\n"
        "- `manifest.yml`\n"
    )


def _openspec_spec_markdown(spec: dict[str, str]) -> str:
    return (
        "# OpenSpec-Oriented Specification\n\n"
        "This file is generated from the P2P-native software spec. It keeps the original sections visible "
        "so exporter refinement can happen without losing provenance.\n\n"
        "## Requirements\n\n"
        f"{_strip_markdown_title(spec['requirements.md'])}\n\n"
        "## Design\n\n"
        f"{_strip_markdown_title(spec['design.md'])}\n\n"
        "## Acceptance\n\n"
        f"{_strip_markdown_title(spec['acceptance.md'])}\n"
    )


def _speckit_export_index(change_id: str, title: str, feature_dir: str) -> str:
    return (
        f"# Spec Kit Export - {change_id} - {title}\n\n"
        "## Purpose\n\n"
        "This bundle maps the P2P-native software spec into a Spec Kit-oriented feature directory. "
        "The export is conservative: it creates the expected specification, planning, supporting design, and task artifacts, "
        "but it does not invoke Spec Kit commands or create Git branches.\n\n"
        "## Source\n\n"
        f"- Change Set: `{change_id}`\n"
        f"- Software spec: `.p2p/outputs/software-spec/{change_id}/`\n\n"
        "## Feature Directory\n\n"
        f"- `{feature_dir}/`\n\n"
        "## Artifacts\n\n"
        "- `spec.md`\n"
        "- `plan.md`\n"
        "- `research.md`\n"
        "- `data-model.md`\n"
        "- `quickstart.md`\n"
        "- `tasks.md`\n"
        "- `contracts/README.md`\n"
        "- `manifest.yml`\n"
    )


def _speckit_spec_markdown(change_id: str, title: str, spec: dict[str, str]) -> str:
    return (
        f"# Feature Specification: {title}\n\n"
        f"**Feature Branch**: `{change_id.lower()}-{_slugify(title)}`  \n"
        "**Created**: NEEDS CLARIFICATION  \n"
        "**Status**: Draft  \n"
        f"**Input**: P2P software spec from `{change_id}`\n\n"
        "## User Scenarios & Testing\n\n"
        "### Primary User Story\n\n"
        "As a P2P operator, I can export a governed P2P-native software spec into a Spec Kit-oriented feature directory so that downstream Spec Kit workflows can start from structured artifacts instead of raw proposal folders.\n\n"
        "### Acceptance Scenarios\n\n"
        f"{_strip_markdown_title(spec['acceptance.md'])}\n\n"
        "## Requirements\n\n"
        f"{_strip_markdown_title(spec['requirements.md'])}\n\n"
        "## Key Entities\n\n"
        "See `data-model.md` for the entity mapping derived from the P2P software spec.\n\n"
        "## Governance Boundary\n\n"
        "This file is exported from accepted P2P artifacts. Missing implementation details are marked as NEEDS CLARIFICATION and must be resolved through P2P governance before implementation."
    )


def _speckit_plan_markdown(change_id: str, title: str, spec: dict[str, str]) -> str:
    return (
        f"# Implementation Plan: {title}\n\n"
        f"Branch: `{change_id.lower()}-{_slugify(title)}` | Date: NEEDS CLARIFICATION | Spec: `spec.md`\n\n"
        "## Summary\n\n"
        f"Exported from the P2P-native software spec for `{change_id}`. The plan preserves the existing P2P design context and leaves unresolved technical choices as NEEDS CLARIFICATION.\n\n"
        "## Technical Context\n\n"
        "Language/Version: NEEDS CLARIFICATION  \n"
        "Primary Dependencies: NEEDS CLARIFICATION  \n"
        "Storage: files under `.p2p/`  \n"
        "Testing: pytest  \n"
        "Target Platform: local CLI  \n"
        "Project Type: cli/library  \n"
        "Performance Goals: NEEDS CLARIFICATION  \n"
        "Constraints: preserve P2P provenance; do not read raw proposal folders for downstream export  \n"
        "Scale/Scope: single Change Set export bundle\n\n"
        "## Constitution Check\n\n"
        "GATE: NEEDS CLARIFICATION - run inside an initialized Spec Kit project if constitutional gates are configured.\n\n"
        "## Project Structure\n\n"
        "### Documentation (this feature)\n\n"
        f"    specs/{change_id.lower()}-{_slugify(title)}/\n"
        "    ├── spec.md\n"
        "    ├── plan.md\n"
        "    ├── research.md\n"
        "    ├── data-model.md\n"
        "    ├── quickstart.md\n"
        "    ├── contracts/\n"
        "    └── tasks.md\n\n"
        "### Source Code (repository root)\n\n"
        "    src/\n"
        "    tests/\n\n"
        "Structure Decision: Use the existing local CLI/library repository structure.\n\n"
        "## Design Context\n\n"
        f"{_strip_markdown_title(spec['design.md'])}\n"
    )


def _speckit_research_markdown(change_id: str, title: str, spec: dict[str, str]) -> str:
    return (
        f"# Research: {title}\n\n"
        "## Decision: Export From P2P-Native Software Spec\n\n"
        f"Rationale: `{change_id}` has a normalized software spec with requirements, design, commands, data model, acceptance, and provenance. Exporting from that layer avoids coupling downstream tools to raw P2P proposal folders.\n\n"
        "Alternatives considered:\n\n"
        "- Export raw proposals directly: rejected because it bypasses the normalized spec layer.\n"
        "- Invoke Spec Kit directly: rejected for this MVP because the exporter should be deterministic and offline.\n"
        "- Generate a conservative Spec Kit-oriented directory: selected for traceability and low coupling.\n\n"
        "## Open Questions\n\n"
        "- NEEDS CLARIFICATION: Whether this bundle should be copied into a real `specs/` directory or consumed from `.p2p/outputs/spec-export/`.\n"
        "- NEEDS CLARIFICATION: Which Spec Kit integration should execute the generated artifacts.\n\n"
        "## Source Provenance\n\n"
        f"{_strip_markdown_title(spec['provenance.yml'])}\n"
    )


def _speckit_data_model_markdown(spec: dict[str, str]) -> str:
    return (
        "# Data Model\n\n"
        "The following structured entity model is copied from the P2P-native software spec.\n\n"
        "```yaml\n"
        f"{spec['data-model.yml'].strip()}\n"
        "\n```\n"
    )


def _speckit_quickstart_markdown(change_id: str) -> str:
    return (
        "# Quickstart\n\n"
        "## Validate Export Bundle\n\n"
        "```bash\n"
        f"p2p spec export --change {change_id} --target speckit\n"
        "p2p spec export-show "
        f"{change_id} --target speckit\n"
        "p2p spec export-status\n"
        "```\n\n"
        "## Use With Spec Kit\n\n"
        "1. Review `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`, and `tasks.md`.\n"
        "2. Resolve all NEEDS CLARIFICATION markers through P2P governance.\n"
        "3. Copy or adapt the feature directory into the Spec Kit `specs/` workspace if a real Spec Kit run is required.\n"
    )


def _speckit_tasks_markdown(change_id: str, spec: dict[str, str]) -> str:
    return (
        "# Tasks\n\n"
        f"Input: Design documents from `specs/{change_id.lower()}-*/`\n\n"
        "## Phase 1: Verification\n\n"
        "- [ ] T001 Review exported `spec.md` for unsupported requirements.\n"
        "- [ ] T002 Review `plan.md` and resolve NEEDS CLARIFICATION markers.\n"
        "- [ ] T003 Confirm `data-model.md` matches P2P provenance.\n"
        "- [ ] T004 Confirm `contracts/README.md` accurately describes available contracts.\n\n"
        "## Phase 2: Implementation Readiness\n\n"
        "- [ ] T005 Convert verified Spec Kit artifacts into implementation tasks in the target project.\n"
        "- [ ] T006 Run project tests after implementation.\n\n"
        "## P2P Acceptance Source\n\n"
        f"{_strip_markdown_title(spec['acceptance.md'])}\n"
    )


def _speckit_contracts_readme(change_id: str, spec: dict[str, str]) -> str:
    return (
        "# Contracts\n\n"
        "No API contract files are generated by this MVP. The command surface below is preserved as structured contract context from the P2P-native software spec.\n\n"
        "```yaml\n"
        f"{spec['commands.yml'].strip()}\n"
        "\n```\n\n"
        f"Source Change Set: `{change_id}`\n"
    )


def _software_spec_index_markdown(
    change_id: str,
    title: str,
    change_path: Path,
    summary: str,
    frontmatter: dict[str, object],
    included_proposals: list[str],
) -> str:
    return (
        f"# Software Spec - {change_id} - {title}\n\n"
        "## Summary\n\n"
        f"{summary}\n\n"
        "## Source\n\n"
        f"- Change Set: `{change_id}`\n"
        f"- Change path: `{change_path}`\n"
        f"- Included proposals: {', '.join(included_proposals) if included_proposals else 'none'}\n\n"
        "## Targets\n\n"
        f"- execution_domains: {', '.join(_string_list(frontmatter.get('execution_domains'))) or 'none'}\n"
        f"- implementation_targets: {', '.join(_string_list(frontmatter.get('implementation_targets'))) or 'none'}\n"
        f"- spec_targets: {', '.join(_string_list(frontmatter.get('spec_targets'))) or 'none'}\n"
        f"- export_targets: {', '.join(_string_list(frontmatter.get('export_targets'))) or 'none'}\n"
    )


def _software_spec_requirements_markdown(
    proposals: list[ProposalDetail],
    change_text: str,
) -> str:
    lines = ["# Requirements", "", "## Functional Requirements", ""]
    if proposals:
        for proposal in proposals:
            lines.extend(
                [
                    f"### {proposal.proposal_id} - {proposal.title}",
                    "",
                    proposal.proposal,
                    "",
                ]
            )
    else:
        lines.extend(["Not specified yet.", ""])
    lines.extend(
        [
            "## Non-Goals / Exclusions",
            "",
            _read_markdown_section(change_text, "Excluded") or "Not specified yet.",
            "",
            "## Constraints",
            "",
            "Do not treat raw proposal discussion as implementation requirements without accepted scope.",
            "",
            "## Open Questions",
            "",
            "Not specified yet.",
        ]
    )
    return "\n".join(lines) + "\n"


def _software_spec_design_markdown(frontmatter: dict[str, object], change_text: str) -> str:
    return (
        "# Design\n\n"
        "## Implementation Targets\n\n"
        f"{', '.join(_string_list(frontmatter.get('implementation_targets'))) or 'Not specified yet.'}\n\n"
        "## Data Flow\n\n"
        "Not specified yet.\n\n"
        "## CLI/API Surface\n\n"
        "Not specified yet.\n\n"
        "## Storage / Artifacts\n\n"
        f"{_read_markdown_section(change_text, 'Deliverables') or 'Not specified yet.'}\n"
    )


def _software_spec_commands(tasks: list[object]) -> list[dict[str, object]]:
    commands: list[dict[str, object]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        title = str(task.get("title") or "")
        if "command" in title.lower() or task.get("domain") == "software":
            commands.append(
                {
                    "name": title,
                    "purpose": str(task.get("deliverable") or task.get("description") or "Not specified yet."),
                    "status": str(task.get("status") or "unknown"),
                }
            )
    return commands


def _software_spec_entities(
    frontmatter: dict[str, object],
    proposals: list[ProposalDetail],
) -> list[dict[str, object]]:
    entities = [
        {
            "name": "ChangeSet",
            "description": "Operational package derived from accepted project intent.",
        },
        {
            "name": "SoftwareSpec",
            "description": "P2P-native normalized implementation-facing specification.",
        },
    ]
    for target in _string_list(frontmatter.get("export_targets")):
        entities.append({"name": f"ExportTarget:{target}", "description": "Downstream export target."})
    for proposal in proposals:
        entities.append({"name": proposal.proposal_id, "description": proposal.title})
    return entities


def _software_spec_acceptance_markdown(change_text: str, tasks: list[object]) -> str:
    lines = [
        "# Acceptance",
        "",
        "## Criteria",
        "",
        _read_markdown_section(change_text, "Acceptance Criteria") or "Not specified yet.",
        "",
        "## Tests / Verification",
        "",
    ]
    task_lines = []
    for task in tasks:
        if isinstance(task, dict):
            task_lines.append(f"- {task.get('id', '-')}: {task.get('title', 'Untitled')} ({task.get('status', 'unknown')})")
    lines.extend(task_lines or ["- Not specified yet."])
    lines.append("")
    return "\n".join(lines)


def _software_spec_refine_prompt(change: ChangeSetDetail, context: str) -> str:
    return (
        f"# P2P Software Spec Refinement Prompt - {change.change_id}\n\n"
        "You are refining a P2P-native software specification for implementation and downstream export.\n\n"
        "## Governance Boundary\n\n"
        "Do not add requirements that are not supported by accepted proposals, decisions, or the Change Set. "
        "Mark missing information as open questions instead of inventing it.\n\n"
        "## Required Output\n\n"
        "Return a directory containing exactly these artifacts:\n\n"
        "- index.md\n"
        "- requirements.md\n"
        "- design.md\n"
        "- commands.yml with top-level `commands`\n"
        "- data-model.yml with top-level `entities`\n"
        "- acceptance.md\n"
        "- provenance.yml with top-level `source`\n\n"
        "## Current Deterministic Spec Context\n\n"
        f"{context}\n"
    )


def _replace_status(path: Path, status: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated = re.sub(r"(## Status\s+)`[^`]+`", rf"\1`{status}`", text, count=1)
    path.write_text(updated, encoding="utf-8")


def _paragraph(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _bullets(values: list[str] | None) -> str | None:
    if not values:
        return None
    cleaned = [value.strip() for value in values if value.strip()]
    if not cleaned:
        return None
    return "\n".join(f"- {value}" for value in cleaned)


def _has_meaningful_content(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    placeholders = (
        "not explored yet.",
        "none identified yet.",
        "not suggested yet.",
        "findings: []",
    )
    lower = stripped.lower()
    return not any(placeholder in lower for placeholder in placeholders)


def _artifact_quality_state(path: Path, text: str) -> str:
    if not path.exists():
        return "missing"
    stripped = text.strip()
    if not stripped:
        return "placeholder"
    lower = stripped.lower()
    placeholders = (
        "not explored yet.",
        "none identified yet.",
        "not suggested yet.",
        "findings: []",
        "pending.",
    )
    if any(placeholder in lower for placeholder in placeholders):
        return "placeholder"
    content_lines = [
        line.strip()
        for line in stripped.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    content_text = " ".join(content_lines)
    if len(content_text) < 80:
        return "thin"
    return "meaningful"


def _has_meaningful_intake_recommendation(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return "pending." not in stripped.lower()


def _count_open_questions(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^(\d+\.|-|\*)\s+.+\?", stripped):
            count += 1
    return count


def _find_choice_option(options: list[object], value: str) -> dict[str, object] | None:
    normalized = value.strip().lower()
    for option in options:
        if not isinstance(option, dict):
            continue
        option_id = str(option.get("id", "")).strip().lower()
        option_title = str(option.get("title", "")).strip().lower()
        if normalized in {option_id, option_title}:
            return option
    return None


def _find_apply_plan_action(actions: list[object], action_id: str) -> dict[str, object] | None:
    for action in actions:
        if isinstance(action, dict) and action.get("id") == action_id:
            return action
    return None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _review_request_suggestion(provider: str, remote_url: str, branch_name: str) -> str:
    if provider == "github":
        web_url = _github_web_url(remote_url)
        if web_url:
            return f"Open a GitHub pull request from {branch_name}: {web_url}/compare/{branch_name}?expand=1"
        return f"Open a GitHub pull request from branch {branch_name}."
    if provider == "gitlab":
        web_url = _gitlab_web_url(remote_url)
        if web_url:
            return f"Open a GitLab merge request from {branch_name}: {web_url}/-/merge_requests/new?merge_request[source_branch]={branch_name}"
        return f"Open a GitLab merge request from branch {branch_name}."
    return f"Ask for external review of remote branch {branch_name} at {remote_url}."


def _github_web_url(remote_url: str) -> str | None:
    match = re.match(r"git@github\.com:(?P<owner>[^/]+)/(?P<repo>.+?)(?:\.git)?$", remote_url)
    if match:
        return f"https://github.com/{match.group('owner')}/{match.group('repo')}"
    match = re.match(r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>.+?)(?:\.git)?$", remote_url)
    if match:
        return f"https://github.com/{match.group('owner')}/{match.group('repo')}"
    return None


def _gitlab_web_url(remote_url: str) -> str | None:
    match = re.match(r"git@gitlab\.com:(?P<path>.+?)(?:\.git)?$", remote_url)
    if match:
        return f"https://gitlab.com/{match.group('path')}"
    match = re.match(r"https://gitlab\.com/(?P<path>.+?)(?:\.git)?$", remote_url)
    if match:
        return f"https://gitlab.com/{match.group('path')}"
    return None


def _file_has_conflict_markers(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return True
    return "<<<<<<<" in content or "=======" in content or ">>>>>>>" in content


def _vote_status_from_data(proposal_id: str, data: object) -> VoteStatus:
    if not isinstance(data, dict):
        raise ValueError("Invalid votes.yml: expected YAML mapping.")
    votes = data.get("votes", [])
    if not isinstance(votes, list):
        raise ValueError("Invalid votes.yml: expected `votes` list.")
    counts: dict[str, int] = {}
    for vote in votes:
        if not isinstance(vote, dict):
            continue
        choice = str(vote.get("choice", "")).strip()
        if choice:
            counts[choice] = counts.get(choice, 0) + 1
    winner = None
    tied = False
    if counts:
        highest = max(counts.values())
        winners = sorted(choice for choice, count in counts.items() if count == highest)
        tied = len(winners) > 1
        winner = None if tied else winners[0]
    return VoteStatus(
        proposal_id=proposal_id,
        counts=counts,
        total_votes=sum(counts.values()),
        winner=winner,
        tied=tied,
    )

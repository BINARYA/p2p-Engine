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
from p2p_engine.prompts.clarify import render_clarify_prompt
from p2p_engine.prompts.digest import render_digest_prompt
from p2p_engine.prompts.explore import render_explore_prompt
from p2p_engine.prompts.impact import render_impact_prompt
from p2p_engine.prompts.plan import render_plan_prompt
from p2p_engine.prompts.synthesize import render_synthesize_prompt
from p2p_engine.prompts.swot import render_swot_prompt
from p2p_engine.prompts.tasks import render_tasks_prompt
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

    def init_project(
        self,
        name: str,
        agent_profile: str = "generic",
        repository_mode: str = "local",
        project_domain: str = "none",
        rubric_enabled: dict[str, bool] | None = None,
        owner: str | None = None,
    ) -> list[Path]:
        agent_profile = _normalize_agent_profile(agent_profile)
        repository_mode = _normalize_repository_mode(repository_mode)
        project_domain = _normalize_project_domain(project_domain)
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
            self.p2p_dir / "project" / "rubrics.yml": _yaml_dump(
                _rubrics_payload(project_domain, rubric_enabled=rubric_enabled)
            ),
            self.p2p_dir / "project" / "permissions.yml": _yaml_dump(
                _permissions_payload(owner_name=owner, repository_mode=repository_mode)
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
        return AgentInstructionsResult(
            profile=profile,
            created=created,
            updated=updated,
            policy_path=relative_policy,
        )

    def permissions_show(self) -> dict[str, object]:
        path = self._permissions_path()
        if not path.exists():
            return _permissions_payload(owner_name=None, repository_mode=self._repository_mode(default="local"))
        return _read_yaml_mapping(path, default={})

    def permissions_actor_add(
        self,
        actor_id: str,
        role: str = "contributor",
        kind: str = "person",
        display_name: str | None = None,
    ) -> PermissionActor:
        actor_slug = _identity_slug(actor_id)
        role = _normalize_permission_role(role)
        kind = _normalize_actor_kind(kind)
        path = self._permissions_path()
        payload = self.permissions_show()
        identities = payload.setdefault("identities", {})
        if not isinstance(identities, dict):
            raise ValueError("Invalid permissions policy: identities must be a mapping")
        identities[actor_slug] = {
            "role": role,
            "kind": kind,
            "display_name": display_name or actor_id,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        return PermissionActor(
            actor_id=actor_slug,
            role=role,
            kind=kind,
            display_name=display_name or actor_id,
            path=path.relative_to(self.root),
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
        operation = _normalize_consent_operation(operation)
        target = target.strip()
        if not target:
            raise ValueError("Consent target is required")
        actor_slug = _identity_slug(actor_id)
        approved_by_slug = _identity_slug(approved_by)
        permissions = self.permissions_show()
        identities = permissions.get("identities", {})
        if not isinstance(identities, dict):
            raise ValueError("Invalid permissions policy: identities must be a mapping")
        if actor_slug not in identities:
            raise ValueError(f"Unknown consent actor: {actor_slug}. Add it with `p2p permissions actor add`.")
        if approved_by_slug not in identities:
            raise ValueError(f"Unknown consent approver: {approved_by_slug}. Add it with `p2p permissions actor add`.")
        approver = identities[approved_by_slug]
        if not isinstance(approver, dict) or str(approver.get("role") or "") != "owner":
            raise ValueError("Only an owner identity can approve consent receipts in the MVP")

        consent_id = self._next_consent_id()
        receipt_dir = self.p2p_dir / "consents" / consent_id
        receipt_dir.mkdir(parents=True, exist_ok=False)
        receipt = {
            "consent_id": consent_id,
            "status": "granted",
            "operation": operation,
            "target": target,
            "actor_id": actor_slug,
            "requested_by": actor_slug,
            "approved_by": approved_by_slug,
            "scope": scope or "single_target",
            "single_use": bool(single_use),
            "expires_on": expires_on,
            "created_at": date.today().isoformat(),
            "consumed_at": None,
            "revoked_at": None,
            "result": None,
            "provider": None,
        }
        path = receipt_dir / "consent.yml"
        path.write_text(_yaml_dump(receipt), encoding="utf-8")
        return _consent_receipt_from_payload(receipt, path.relative_to(self.root))

    def consent_show(self, consent_id: str) -> ConsentReceipt:
        path = self._consent_path(consent_id)
        if not path.exists():
            raise ValueError(f"Consent receipt not found: {consent_id}")
        payload = _read_yaml_mapping(path, default={})
        return _consent_receipt_from_payload(payload, path.relative_to(self.root))

    def consent_statuses(self) -> list[ConsentReceipt]:
        consents_dir = self.p2p_dir / "consents"
        if not consents_dir.exists():
            return []
        receipts: list[ConsentReceipt] = []
        for path in sorted(consents_dir.glob("CONSENT-*/consent.yml")):
            receipts.append(_consent_receipt_from_payload(_read_yaml_mapping(path, default={}), path.relative_to(self.root)))
        return receipts

    def consent_revoke(self, consent_id: str, reason: str = "") -> ConsentReceipt:
        path = self._consent_path(consent_id)
        if not path.exists():
            raise ValueError(f"Consent receipt not found: {consent_id}")
        payload = _read_yaml_mapping(path, default={})
        if str(payload.get("status") or "") == "consumed":
            raise ValueError(f"Cannot revoke consumed consent receipt: {consent_id}")
        payload["status"] = "revoked"
        payload["revoked_at"] = date.today().isoformat()
        payload["revocation_reason"] = reason or "Not provided."
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        return _consent_receipt_from_payload(payload, path.relative_to(self.root))

    def consent_validate(
        self,
        consent_id: str,
        *,
        operation: str,
        target: str,
        actor_id: str,
    ) -> ConsentReceipt:
        path = self._consent_path(consent_id)
        if not path.exists():
            raise ValueError(f"Consent receipt not found: {consent_id}")
        payload = _read_yaml_mapping(path, default={})
        expected_operation = _normalize_consent_operation(operation)
        expected_actor = _identity_slug(actor_id)
        if str(payload.get("status") or "") != "granted":
            raise ValueError(f"Consent receipt is not granted: {consent_id}")
        if str(payload.get("operation") or "") != expected_operation:
            raise ValueError(
                f"Consent receipt operation mismatch: expected {expected_operation}, got {payload.get('operation')}"
            )
        if str(payload.get("target") or "") != target:
            raise ValueError(f"Consent receipt target mismatch: expected {target}, got {payload.get('target')}")
        if str(payload.get("actor_id") or "") != expected_actor:
            raise ValueError(
                f"Consent receipt actor mismatch: expected {expected_actor}, got {payload.get('actor_id')}"
            )
        expires_on = payload.get("expires_on")
        if expires_on:
            try:
                expiry = date.fromisoformat(str(expires_on))
            except ValueError as exc:
                raise ValueError(f"Invalid consent expiry date: {expires_on}") from exc
            if expiry < date.today():
                payload["status"] = "expired"
                path.write_text(_yaml_dump(payload), encoding="utf-8")
                raise ValueError(f"Consent receipt expired: {consent_id}")
        return _consent_receipt_from_payload(payload, path.relative_to(self.root))

    def consent_consume(self, consent_id: str, *, result: dict[str, object]) -> ConsentReceipt:
        path = self._consent_path(consent_id)
        if not path.exists():
            raise ValueError(f"Consent receipt not found: {consent_id}")
        payload = _read_yaml_mapping(path, default={})
        if str(payload.get("status") or "") != "granted":
            raise ValueError(f"Consent receipt is not granted: {consent_id}")
        payload["status"] = "consumed"
        payload["consumed_at"] = date.today().isoformat()
        payload["result"] = result
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        return _consent_receipt_from_payload(payload, path.relative_to(self.root))

    def consent_mark_used_with_error(
        self,
        consent_id: str,
        *,
        error: str,
        result: dict[str, object] | None = None,
    ) -> ConsentReceipt:
        path = self._consent_path(consent_id)
        if not path.exists():
            raise ValueError(f"Consent receipt not found: {consent_id}")
        payload = _read_yaml_mapping(path, default={})
        if str(payload.get("status") or "") != "granted":
            return _consent_receipt_from_payload(payload, path.relative_to(self.root))
        payload["status"] = "used_with_error"
        payload["consumed_at"] = date.today().isoformat()
        payload["result"] = result or {}
        payload["error"] = error
        path.write_text(_yaml_dump(payload), encoding="utf-8")
        return _consent_receipt_from_payload(payload, path.relative_to(self.root))

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
        return self.p2p_dir / "project" / "permissions.yml"

    def _consent_path(self, consent_id: str) -> Path:
        consent_id = _normalize_consent_id(consent_id)
        return self.p2p_dir / "consents" / consent_id / "consent.yml"

    def _next_consent_id(self) -> str:
        consents_dir = self.p2p_dir / "consents"
        used: set[int] = set()
        if consents_dir.exists():
            for path in consents_dir.iterdir():
                if not path.is_dir():
                    continue
                match = re.match(r"^CONSENT-(\d{3})$", path.name)
                if match:
                    used.add(int(match.group(1)))
        return f"CONSENT-{max(used or {0}) + 1:03d}"

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
        project_file = self.p2p_dir / "project.yml"
        data = _read_yaml_mapping(project_file, default={})
        remote_data = data.get("remote", {})
        if not isinstance(remote_data, dict):
            remote_data = {}
        review_data = remote_data.get("review_request", {})
        if not isinstance(review_data, dict):
            review_data = {}
        mode = str(remote_data.get("mode") or "local")
        provider = str(remote_data.get("provider") or ("local" if mode == "local" else "generic"))
        remote = remote_data.get("remote")
        url = remote_data.get("url")
        return RemoteProjectProfile(
            mode=mode,
            provider=provider,
            remote=str(remote) if remote else None,
            url=str(url) if url else None,
            review_request_mode=str(review_data.get("mode") or "advisory"),
            opens_external_request=bool(review_data.get("opens_external_request", False)),
            path=project_file.relative_to(self.root),
        )

    def configure_remote_profile(
        self,
        *,
        mode: str,
        provider: str | None = None,
        remote: str = "origin",
        url: str | None = None,
    ) -> RemoteProjectProfile:
        mode = mode.strip().lower()
        if mode not in {"local", "remote"}:
            raise ValueError("Remote project mode must be local or remote")

        provider = (provider or ("local" if mode == "local" else "generic")).strip().lower()
        if provider not in {"local", "generic", "github", "gitlab"}:
            raise ValueError("Remote provider must be local, generic, github, or gitlab")
        if mode == "local":
            provider = "local"
            remote = ""
            url = None
        else:
            if provider == "local":
                raise ValueError("Remote-backed projects cannot use provider local")
            if not url:
                url = remote_url(self.root, remote)
            if not url:
                raise ValueError(f"Remote URL is required and Git remote was not found: {remote}")

        project_file = self.p2p_dir / "project.yml"
        data = _read_yaml_mapping(project_file, default={})
        data["remote"] = {
            "mode": mode,
            "provider": provider,
            "remote": remote or None,
            "url": url,
            "review_request": {
                "mode": "advisory",
                "opens_external_request": False,
            },
        }
        project_file.write_text(_yaml_dump(data), encoding="utf-8")
        return self.remote_profile()

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
            reason = "not a Git repository"
        elif profile.mode == "local" and remote is None and not profile.remote:
            can_sync = False
            reason = "project remote profile is local"
        elif not selected_remote:
            can_sync = False
            reason = "no Git remote configured"
        elif resolved_remote_url is None:
            can_sync = False
            reason = f"Git remote not found: {selected_remote}"

        return SyncStatus(
            is_repository=git_status.is_repository,
            branch=git_status.branch,
            is_clean=git_status.is_clean,
            mode=profile.mode,
            provider=profile.provider,
            remote=selected_remote,
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
        proposal_dir = self._find_proposal_dir(proposal_id)
        proposal_text = _read_optional(proposal_dir / "proposal.md")
        decision_text = _read_optional(proposal_dir / "decision.md")
        return ProposalDetail(
            proposal_id=proposal_id,
            title=_clean_proposal_title(_read_title(proposal_text) or proposal_id, proposal_id),
            status=_read_proposal_status(proposal_dir / "proposal.md"),
            path=proposal_dir.relative_to(self.root),
            problem=_read_markdown_section(proposal_text, "Problem") or "Not provided.",
            proposal=_read_markdown_section(proposal_text, "Proposal") or "Not provided.",
            decision_status=(_read_markdown_section(decision_text, "Status") or "pending").strip("`"),
            decision_reason=_read_markdown_section(decision_text, "Reason") or "Not provided.",
        )

    def branch_proposal(self, proposal_id: str, actor: str = "local") -> ProposalBranchDetail:
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

        base_branch = git_status.branch
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
            "base_branch": base_branch,
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
            if status not in {"granted", "consumed", "revoked", "expired", "used_with_error"}:
                add("P2P223_INVALID_CONSENT_STATUS", "error", consent_path, f"Invalid consent status: {status}")
            for required in ("target", "actor_id", "approved_by", "created_at"):
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

    def create_proposal(self, title: str) -> Proposal:
        return self.create_proposal_with_details(title=title)

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
        proposals_dir = self.p2p_dir / "proposals"
        proposals_dir.mkdir(parents=True, exist_ok=True)
        proposal_id = self._next_proposal_id()
        slug = _slugify(title)
        proposal_dir = proposals_dir / f"{proposal_id}-{slug}"
        proposal_dir.mkdir()

        files = {
            "proposal.md": _proposal_markdown(
                proposal_id=proposal_id,
                title=title,
                problem=problem,
                context=context,
                goals=goals,
                non_goals=non_goals,
                proposal=proposal,
                acceptance_criteria=acceptance_criteria,
            ),
            "contributions.yml": "contributions: []\n",
            "comments.yml": "comments: []\n",
            "ai-digest.md": f"# AI Digest - {proposal_id}\n\nNot generated yet.\n",
            "clarifications.md": f"# Clarifications - {proposal_id}\n\nNone recorded yet.\n",
            "decision.md": f"# Decision - {proposal_id}\n\n## Status\n\n`pending`\n",
            "execution-plan.md": f"# Execution Plan - {proposal_id}\n\nPending.\n",
            "tasks.yml": "tasks: []\n",
        }
        files.update(_exploration_files(proposal_id))
        for filename, content in files.items():
            (proposal_dir / filename).write_text(content, encoding="utf-8")

        return Proposal(
            proposal_id=proposal_id,
            title=title,
            slug=slug,
            status="draft",
            path=proposal_dir.relative_to(self.root),
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
        proposal_dir = self._find_proposal_dir(proposal_id)
        proposal_path = proposal_dir / "proposal.md"
        text = proposal_path.read_text(encoding="utf-8")
        replacements = {
            "Problem": _paragraph(problem),
            "Context": _paragraph(context),
            "Goals": _bullets(goals),
            "Non-Goals": _bullets(non_goals),
            "Proposal": _paragraph(proposal),
            "Acceptance Criteria": _bullets(acceptance_criteria),
        }
        for section, replacement in replacements.items():
            if replacement is not None:
                text = _replace_section(text, section, replacement)
        proposal_path.write_text(text, encoding="utf-8")
        return proposal_path.relative_to(self.root)

    def add_contribution(
        self,
        proposal_id: str,
        contribution_type: ContributionType,
        text: str,
        relevance_hint: str,
        author: str,
    ) -> Contribution:
        proposal_dir = self._find_proposal_dir(proposal_id)
        path = proposal_dir / "contributions.yml"
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {"contributions": []}
        contributions = data.setdefault("contributions", [])
        contribution_id = f"C{len(contributions) + 1:03d}"
        contribution = {
            "id": contribution_id,
            "type": contribution_type.value,
            "author": author,
            "relevance_hint": relevance_hint,
            "text": text,
        }
        contributions.append(contribution)
        path.write_text(_yaml_dump(data), encoding="utf-8")
        return Contribution(
            contribution_id=contribution_id,
            contribution_type=contribution_type,
            text=text,
            author=author,
            relevance_hint=relevance_hint,
        )

    def record_decision(
        self,
        proposal_id: str,
        outcome: DecisionOutcome,
        reason: str,
        approver: str,
    ) -> Decision:
        proposal_dir = self._find_proposal_dir(proposal_id)
        decided_on = date.today()
        content = (
            f"# Decision - {proposal_id}\n\n"
            "## Status\n\n"
            f"`{outcome.value}`\n\n"
            "## Outcome\n\n"
            f"{outcome.value}\n\n"
            "## Reason\n\n"
            f"{reason}\n\n"
            "## Date\n\n"
            f"{decided_on.isoformat()}\n\n"
            "## Approver\n\n"
            f"{approver}\n"
        )
        (proposal_dir / "decision.md").write_text(content, encoding="utf-8")
        _replace_status(proposal_dir / "proposal.md", outcome.value)
        return Decision(proposal_id, outcome, reason, approver, decided_on)

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
        project_dir = self.p2p_dir / "project"
        features_dir = project_dir / "features"
        exports_dir = project_dir / "exports"
        for directory in (
            project_dir,
            features_dir,
            exports_dir / "markdown",
            exports_dir / "openspec",
            exports_dir / "speckit",
        ):
            directory.mkdir(parents=True, exist_ok=True)

        accepted = self._accepted_proposals()
        project_name = self.status().project_name
        written: list[Path] = []

        files = {
            project_dir / "overview.md": _project_overview_markdown(project_name, accepted),
            project_dir / "problem.md": _project_problem_markdown(accepted),
            project_dir / "scope.md": _project_scope_markdown(accepted),
            project_dir / "project-swot.md": _project_swot_markdown(),
            project_dir / "decisions-map.yml": _yaml_dump(
                {
                    "decisions": [
                        {
                            "proposal": item["proposal_id"],
                            "title": item["title"],
                            "status": item["status"],
                            "feature": item["feature_id"],
                            "source": item["source"],
                        }
                        for item in accepted
                    ]
                }
            ),
        }
        for path, content in files.items():
            path.write_text(content, encoding="utf-8")
            written.append(path.relative_to(self.root))
        conflicts_path = project_dir / "conflicts.yml"
        if not conflicts_path.exists():
            conflicts_path.write_text(_yaml_dump({"conflicts": []}), encoding="utf-8")
            written.append(conflicts_path.relative_to(self.root))

        for item in accepted:
            feature_dir = features_dir / item["feature_id"]
            feature_dir.mkdir(parents=True, exist_ok=True)
            feature_files = {
                feature_dir / "feature.md": _feature_markdown(item),
                feature_dir / "tasks.yml": _read_optional(item["path"] / "tasks.yml") or "tasks: []\n",
                feature_dir / "actions.yml": _yaml_dump({"actions": []}),
            }
            for path, content in feature_files.items():
                path.write_text(content, encoding="utf-8")
                written.append(path.relative_to(self.root))
        return written

    def project_state_status(self) -> ProjectStateStatus:
        project_dir = self.p2p_dir / "project"
        features_dir = project_dir / "features"
        features = (
            sorted(path.name for path in features_dir.iterdir() if path.is_dir())
            if features_dir.exists()
            else []
        )
        next_actions = self.next_actions()
        return ProjectStateStatus(
            accepted_proposals=len(self._accepted_proposals()),
            features=features,
            project_dir=project_dir.relative_to(self.root),
            operational_brief_available=(project_dir / "operational-brief.md").exists(),
            next_actions_count=len(next_actions),
            first_next_action=next_actions[0] if next_actions else None,
        )

    def show_project_state(self, section: str) -> str:
        project_dir = self.p2p_dir / "project"
        section_map = {
            "overview": project_dir / "overview.md",
            "problem": project_dir / "problem.md",
            "scope": project_dir / "scope.md",
            "swot": project_dir / "project-swot.md",
        }
        path = section_map.get(section, project_dir / "features" / section / "feature.md")
        if not path.exists():
            raise ValueError(f"Project section not found: {section}")
        return path.read_text(encoding="utf-8")

    def create_project_brief_prompt(self) -> ProjectBriefPrompt:
        project_dir = self.p2p_dir / "project"
        project_dir.mkdir(parents=True, exist_ok=True)
        registry_status = self.registry_status()
        context = self._project_brief_context(registry_status)
        context_path = project_dir / "brief-context.md"
        prompt_path = project_dir / "brief.prompt.md"
        context_path.write_text(context, encoding="utf-8")
        prompt_path.write_text(_project_brief_prompt_markdown(context), encoding="utf-8")
        return ProjectBriefPrompt(
            context_path=context_path.relative_to(self.root),
            prompt_path=prompt_path.relative_to(self.root),
        )

    def import_project_brief(self, source: Path) -> list[Path]:
        project_dir = self.p2p_dir / "project"
        project_dir.mkdir(parents=True, exist_ok=True)
        source = source.resolve()
        imported: list[Path] = []
        if source.is_dir():
            mappings = {
                "operational-brief.md": None,
                "next-actions.yml": "next_actions",
            }
            for filename, key in mappings.items():
                source_path = source / filename
                if source_path.exists():
                    if key is not None:
                        _validate_yaml_key(source_path.read_text(encoding="utf-8"), key)
                    target = project_dir / filename
                    shutil.copyfile(source_path, target)
                    imported.append(target.relative_to(self.root))
        elif source.is_file():
            target = project_dir / "operational-brief.md"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            imported.append(target.relative_to(self.root))
        else:
            raise ValueError(f"Project brief source not found: {source}")
        if not imported:
            raise ValueError(f"No project brief artifacts found in: {source}")
        return imported

    def show_project_brief(self) -> str:
        path = self.p2p_dir / "project" / "operational-brief.md"
        if not path.exists():
            raise ValueError("Project brief not found. Run `p2p project brief import` first.")
        return path.read_text(encoding="utf-8")

    def refresh_project_assessment(self) -> ProjectAssessment:
        assessment = self._compute_project_assessment()
        path = self.p2p_dir / "project" / "assessment.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(_project_assessment_payload(assessment)), encoding="utf-8")
        return assessment

    def show_project_assessment(self) -> ProjectAssessment:
        path = self.p2p_dir / "project" / "assessment.yml"
        if not path.exists():
            raise ValueError("Project assessment not found. Run `p2p assess refresh` first.")
        data = _read_yaml_mapping(path, default={})
        completion = data.get("completion", {})
        maturity = data.get("maturity", {})
        if not isinstance(completion, dict):
            completion = {}
        if not isinstance(maturity, dict):
            maturity = {}
        factors = data.get("factors", [])
        gaps = data.get("gaps", [])
        suggested_actions = data.get("suggested_actions", [])
        return ProjectAssessment(
            path=path.relative_to(self.root),
            generated_on=str(data.get("generated_on") or ""),
            assessment_type=str(data.get("assessment_type") or "deterministic_readiness"),
            completion_score=int(completion.get("score") or 0),
            completion_status=str(completion.get("status") or "unknown"),
            confidence=str(completion.get("confidence") or "unknown"),
            factors=[item for item in factors if isinstance(item, dict)] if isinstance(factors, list) else [],
            gaps=[str(item) for item in gaps] if isinstance(gaps, list) else [],
            suggested_actions=[str(item) for item in suggested_actions]
            if isinstance(suggested_actions, list)
            else [],
            maturity_status=str(maturity.get("status") or "not_assessed"),
            maturity_score=maturity.get("score") if isinstance(maturity.get("score"), int) else None,
        )

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
        validation = self.validate()
        registry_status = self.registry_status()
        proposals = self.proposal_summaries()
        choices = self.choice_statuses()
        changes = self.change_set_statuses()
        works = self.work_summaries()
        project_status = self.project_state_status()
        next_actions = self.next_actions(limit=3)

        draft_proposals = [proposal for proposal in proposals if proposal.status == "draft"]
        accepted_proposals = [proposal for proposal in proposals if proposal.status == "accepted"]
        open_choices = [
            choice for choice in choices if choice.status in {"open", "draft", "pending"} and not choice.selected_option
        ]
        terminal_changes = {"completed", "cancelled", "superseded"}
        active_changes = [change for change in changes if change.status not in terminal_changes]
        blocked_changes = [change for change in changes if change.status == "blocked"]
        terminal_work = {"accepted", "finalized", "cleaned", "retired", "completed", "cancelled", "superseded"}
        active_work = [work for work in works if work.status not in terminal_work]

        factors: list[dict[str, object]] = []
        gaps: list[str] = []
        suggested_actions = [action.command for action in next_actions if action.command]

        def factor(
            factor_id: str,
            label: str,
            value: int | bool,
            impact: int,
            reason: str,
            gap: str | None = None,
        ) -> None:
            factors.append(
                {
                    "id": factor_id,
                    "label": label,
                    "value": value,
                    "impact": impact,
                    "reason": reason,
                }
            )
            if gap and impact < 0:
                gaps.append(gap)

        factor(
            "validation_errors",
            "Validation errors",
            validation.errors,
            -min(validation.errors * 30, 60),
            "Validation errors make project state unreliable.",
            "Resolve validation errors with `p2p validate`.",
        )
        factor(
            "validation_warnings",
            "Validation warnings",
            validation.warnings,
            -min(validation.warnings * 5, 20),
            "Validation warnings indicate recoverable project-state issues.",
            "Review validation warnings with `p2p validate`.",
        )
        factor(
            "stale_registries",
            "Registry freshness",
            registry_status.stale,
            -10 if registry_status.stale else 0,
            "Fresh registries are required for reliable assessment.",
            "Refresh registries with `p2p registry refresh`.",
        )
        factor(
            "draft_proposals",
            "Draft proposals",
            len(draft_proposals),
            -min(len(draft_proposals) * 4, 20),
            "Draft proposals still need owner review or refinement.",
            "Review draft proposals before treating project direction as settled.",
        )
        factor(
            "accepted_proposals",
            "Accepted proposals",
            len(accepted_proposals),
            0 if accepted_proposals else -15,
            "Accepted proposals define committed project direction.",
            "Accept at least one proposal when the project direction is clear.",
        )
        factor(
            "open_choices",
            "Open choices",
            len(open_choices),
            -min(len(open_choices) * 10, 30),
            "Open choices represent unresolved alternatives.",
            "Resolve or document open choices.",
        )
        factor(
            "active_changes",
            "Active Change Sets",
            len(active_changes),
            -min(len(active_changes) * 8, 24),
            "Active Change Sets still need lifecycle progress.",
            "Continue or complete active Change Sets.",
        )
        factor(
            "blocked_changes",
            "Blocked Change Sets",
            len(blocked_changes),
            -min(len(blocked_changes) * 12, 36),
            "Blocked Change Sets prevent implementation readiness.",
            "Resolve blockers before implementation.",
        )
        factor(
            "active_work",
            "Active Work items",
            len(active_work),
            -min(len(active_work) * 5, 20),
            "Active Work items still need review, acceptance, or cleanup.",
            "Finish or retire active Work items.",
        )
        factor(
            "operational_brief",
            "Operational brief",
            project_status.operational_brief_available,
            0 if project_status.operational_brief_available else -5,
            "An operational brief helps agents and owners understand current state.",
            "Refresh/import an operational brief.",
        )

        score = max(0, min(100, 100 + sum(int(item["impact"]) for item in factors)))
        if validation.errors:
            status = "blocked"
        elif not proposals:
            status = "not_started"
        elif score >= 85:
            status = "ready"
        elif score >= 60:
            status = "needs_review"
        else:
            status = "at_risk"

        if validation.errors or registry_status.stale:
            confidence = "low" if validation.errors else "medium"
        elif validation.warnings:
            confidence = "medium"
        else:
            confidence = "high"

        maturity_status = "not_assessed"
        maturity_score = None
        maturity_path = self.p2p_dir / "project" / "maturity-assessment.yml"
        if maturity_path.exists():
            maturity = self.show_definition_maturity()
            maturity_status = maturity.status
            maturity_score = maturity.score

        return ProjectAssessment(
            path=(self.p2p_dir / "project" / "assessment.yml").relative_to(self.root),
            generated_on=date.today().isoformat(),
            assessment_type="deterministic_readiness",
            completion_score=score,
            completion_status=status,
            confidence=confidence,
            factors=factors,
            gaps=gaps,
            suggested_actions=suggested_actions,
            maturity_status=maturity_status,
            maturity_score=maturity_score,
        )

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
        change_dir = self._find_change_dir(change_id)
        change_text = _read_optional(change_dir / "change.md")
        frontmatter = _read_frontmatter(change_text)
        title = str(frontmatter.get("title") or _read_title(change_text) or change_id)
        source = frontmatter.get("source", {})
        if not isinstance(source, dict):
            source = {}
        included_proposals = _string_list(source.get("accepted_proposals"))
        spec_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        spec_dir.mkdir(parents=True, exist_ok=True)

        proposal_details = [self.show_proposal(proposal_id) for proposal_id in included_proposals]
        tasks_data = _read_yaml_mapping(change_dir / "tasks.yml", default={"tasks": []})
        tasks = tasks_data.get("tasks", [])
        task_list = tasks if isinstance(tasks, list) else []

        files = {
            "index.md": _software_spec_index_markdown(
                change_id=change_id,
                title=title,
                change_path=change_dir.relative_to(self.root),
                summary=_read_markdown_section(change_text, "Summary") or "Not specified yet.",
                frontmatter=frontmatter,
                included_proposals=included_proposals,
            ),
            "requirements.md": _software_spec_requirements_markdown(proposal_details, change_text),
            "design.md": _software_spec_design_markdown(frontmatter, change_text),
            "commands.yml": _yaml_dump({"commands": _software_spec_commands(task_list)}),
            "data-model.yml": _yaml_dump({"entities": _software_spec_entities(frontmatter, proposal_details)}),
            "acceptance.md": _software_spec_acceptance_markdown(change_text, task_list),
            "provenance.yml": _yaml_dump(
                {
                    "source": {
                        "change": change_id,
                        "included_proposals": included_proposals,
                        "accepted_decisions": source.get("accepted_decisions", []),
                    },
                    "generated_from": [
                        str((change_dir / "change.md").relative_to(self.root)),
                        str((change_dir / "tasks.yml").relative_to(self.root)),
                        *[
                            str((self._find_proposal_dir(proposal_id) / "proposal.md").relative_to(self.root))
                            for proposal_id in included_proposals
                        ],
                    ],
                }
            ),
        }
        for filename, content in files.items():
            (spec_dir / filename).write_text(content, encoding="utf-8")
        return SoftwareSpecStatus(
            change_id=change_id,
            title=title,
            status="generated",
            path=spec_dir.relative_to(self.root),
        )

    def software_spec_statuses(self) -> list[SoftwareSpecStatus]:
        specs_dir = self.p2p_dir / "outputs" / "software-spec"
        statuses: list[SoftwareSpecStatus] = []
        for path in sorted(specs_dir.iterdir()) if specs_dir.exists() else []:
            if not path.is_dir():
                continue
            change_id = path.name
            title = change_id
            try:
                title = self.show_change_set(change_id).title
            except ValueError:
                index_title = _read_title(_read_optional(path / "index.md"))
                title = index_title or change_id
            required = _software_spec_required_files()
            status = "generated" if all((path / filename).exists() for filename in required) else "incomplete"
            statuses.append(
                SoftwareSpecStatus(
                    change_id=change_id,
                    title=title,
                    status=status,
                    path=path.relative_to(self.root),
                )
            )
        return statuses

    def show_software_spec(self, change_id: str) -> str:
        path = self.p2p_dir / "outputs" / "software-spec" / change_id / "index.md"
        if not path.exists():
            raise ValueError("Software spec not found. Run `p2p spec refresh --change CHANGE-XXX` first.")
        return path.read_text(encoding="utf-8")

    def create_software_spec_prompt(self, change_id: str) -> SoftwareSpecPrompt:
        self.refresh_software_spec(change_id)
        spec_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        change = self.show_change_set(change_id)
        prompt_path = spec_dir / "spec-refine.prompt.md"
        context = "\n\n".join(
            [
                _read_optional(spec_dir / "index.md"),
                _read_optional(spec_dir / "requirements.md"),
                _read_optional(spec_dir / "design.md"),
                _read_optional(spec_dir / "acceptance.md"),
            ]
        )
        prompt_path.write_text(_software_spec_refine_prompt(change, context), encoding="utf-8")
        return SoftwareSpecPrompt(change_id=change_id, prompt_path=prompt_path.relative_to(self.root))

    def import_software_spec(self, change_id: str, source: Path) -> list[Path]:
        source = source.resolve()
        if not source.is_dir():
            raise ValueError(f"Software spec source directory not found: {source}")
        required = _software_spec_required_files()
        for filename in required:
            if not (source / filename).exists():
                raise ValueError(f"Missing required software spec artifact: {filename}")
        _validate_yaml_key((source / "commands.yml").read_text(encoding="utf-8"), "commands")
        _validate_yaml_key((source / "data-model.yml").read_text(encoding="utf-8"), "entities")
        _validate_yaml_key((source / "provenance.yml").read_text(encoding="utf-8"), "source")

        target_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        target_dir.mkdir(parents=True, exist_ok=True)
        imported: list[Path] = []
        for filename in required:
            target = target_dir / filename
            shutil.copyfile(source / filename, target)
            imported.append(target.relative_to(self.root))
        return imported

    def export_software_spec(self, change_id: str, target: str) -> SoftwareSpecExportStatus:
        target = target.lower()
        if target not in _software_spec_export_targets():
            raise ValueError(f"Unsupported software spec export target: {target}")
        spec_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        if not spec_dir.is_dir():
            raise ValueError("Software spec not found. Run `p2p spec refresh --change CHANGE-XXX` first.")
        for filename in _software_spec_required_files():
            if not (spec_dir / filename).exists():
                raise ValueError(f"Missing required software spec artifact: {filename}")

        change = self.show_change_set(change_id)
        export_dir = self.p2p_dir / "outputs" / "spec-export" / change_id / target
        if export_dir.exists():
            shutil.rmtree(export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        files = _software_spec_export_files(
            change_id,
            target,
            change.title,
            spec_dir,
            str(spec_dir.relative_to(self.root)),
            self._project_definition(change_id, change, spec_dir),
        )
        for filename, content in files.items():
            output_path = export_dir / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")

        return SoftwareSpecExportStatus(
            change_id=change_id,
            target=target,
            title=change.title,
            status="exported",
            path=export_dir.relative_to(self.root),
        )

    def software_spec_export_statuses(self) -> list[SoftwareSpecExportStatus]:
        exports_dir = self.p2p_dir / "outputs" / "spec-export"
        statuses: list[SoftwareSpecExportStatus] = []
        for change_dir in sorted(exports_dir.iterdir()) if exports_dir.exists() else []:
            if not change_dir.is_dir():
                continue
            change_id = change_dir.name
            try:
                title = self.show_change_set(change_id).title
            except ValueError:
                title = change_id
            for target_dir in sorted(change_dir.iterdir()):
                if not target_dir.is_dir():
                    continue
                try:
                    required = _software_spec_export_required_files(change_id, target_dir.name, target_dir)
                except ValueError:
                    required = [Path("index.md")]
                status = "exported" if all((target_dir / path).exists() for path in required) else "incomplete"
                statuses.append(
                    SoftwareSpecExportStatus(
                        change_id=change_id,
                        target=target_dir.name,
                        title=title,
                        status=status,
                        path=target_dir.relative_to(self.root),
                    )
                )
        return statuses

    def show_software_spec_export(self, change_id: str, target: str) -> str:
        target = target.lower()
        export_dir = self.p2p_dir / "outputs" / "spec-export" / change_id / target
        path = export_dir / _software_spec_export_show_file(target)
        if not path.exists():
            raise ValueError("Software spec export not found. Run `p2p spec export --change CHANGE-XXX --target TARGET` first.")
        return path.read_text(encoding="utf-8")

    def validate_software_spec_export(self, change_id: str, target: str) -> SoftwareSpecExportValidation:
        target = target.lower()
        if target not in _software_spec_export_targets():
            raise ValueError(f"Unsupported software spec export target: {target}")
        export_dir = self.p2p_dir / "outputs" / "spec-export" / change_id / target
        if not export_dir.is_dir():
            raise ValueError("Software spec export not found. Run `p2p spec export --change CHANGE-XXX --target TARGET` first.")

        checked: list[Path] = []
        required = _software_spec_export_required_files(change_id, target, export_dir)
        for relative in required:
            path = export_dir / relative
            if not path.exists():
                raise ValueError(f"Missing required software spec export artifact: {relative}")
            checked.append(path.relative_to(self.root))

        if target == "generic":
            project_text = (export_dir / "project.md").read_text(encoding="utf-8")
            for section in _project_definition_required_sections():
                if not _markdown_has_section(project_text, section):
                    raise ValueError(f"Missing required project definition section: {section}")
            if "## Source Traceability" not in project_text:
                raise ValueError("Missing required project definition source traceability")

        return SoftwareSpecExportValidation(
            change_id=change_id,
            target=target,
            path=export_dir.relative_to(self.root),
            checked=checked,
        )

    def _project_definition(self, change_id: str, change: ChangeSetDetail, spec_dir: Path) -> dict[str, object]:
        project_data = _read_yaml_mapping(self.p2p_dir / "project.yml", default={})
        project = project_data.get("project", {})
        if not isinstance(project, dict):
            project = {}
        accepted = self._accepted_proposals()
        drafts = self.proposal_summaries("draft")
        source_spec = {filename: _read_optional(spec_dir / filename) for filename in _software_spec_required_files()}
        return {
            "project_name": str(project.get("name") or self.status().project_name),
            "domain": str(project.get("domain") or "generic"),
            "change_id": change_id,
            "change_title": change.title,
            "change_summary": change.summary,
            "execution_domains": change.execution_domains,
            "implementation_targets": change.implementation_targets,
            "spec_targets": change.spec_targets,
            "export_targets": change.export_targets,
            "accepted_proposals": accepted,
            "draft_proposals": drafts,
            "spec": source_spec,
            "constitution": _read_optional(self.p2p_dir / "governance" / "constitution.md"),
            "decision_rules": _read_optional(self.p2p_dir / "governance" / "decision-rules.md"),
            "rubrics": _read_optional(self.p2p_dir / "project" / "rubrics.yml"),
            "assessment": _read_optional(self.p2p_dir / "project" / "assessment.yml"),
            "maturity": _read_optional(self.p2p_dir / "project" / "maturity-assessment.yml"),
        }

    def create_work_plan(self, change_id: str, target: str) -> WorkDetail:
        target = target.lower()
        if target not in _software_spec_export_targets():
            raise ValueError(f"Unsupported work handoff target: {target}")
        validation = self.validate_software_spec_export(change_id, target)
        change_dir = self._find_change_dir(change_id)
        change_text = _read_optional(change_dir / "change.md")
        change_frontmatter = _read_frontmatter(change_text)
        source = change_frontmatter.get("source", {})
        if not isinstance(source, dict):
            source = {}
        work_id = self._next_work_id()
        work_dir = self.p2p_dir / "work" / work_id
        work_dir.mkdir(parents=True)
        branch_name = f"p2p/work/{work_id.lower()}-{change_id.lower()}-{target}"
        manifest = _work_manifest(
            work_id=work_id,
            change_id=change_id,
            target=target,
            branch_name=branch_name,
            export_path=str(validation.path),
            source_proposals=_string_list(source.get("accepted_proposals")),
            allowed_files=[str(path) for path in validation.checked],
        )
        (work_dir / "manifest.yml").write_text(_yaml_dump(manifest), encoding="utf-8")
        return self.show_work(work_id)

    def work_statuses(self) -> list[WorkStatus]:
        work_root = self.p2p_dir / "work"
        statuses: list[WorkStatus] = []
        for path in sorted(work_root.iterdir()) if work_root.exists() else []:
            if not path.is_dir():
                continue
            manifest = _read_yaml_mapping(path / "manifest.yml", default={})
            source = manifest.get("source", {})
            handoff = manifest.get("handoff", {})
            status = str(manifest.get("status") or "unknown")
            change_id = str(source.get("change") if isinstance(source, dict) else "unknown")
            target = str(handoff.get("target") if isinstance(handoff, dict) else "none")
            statuses.append(
                WorkStatus(
                    work_id=str(manifest.get("work_id") or path.name),
                    status=status,
                    change_id=change_id,
                    target=target,
                    path=path.relative_to(self.root),
                )
            )
        for item in self._scanned_work_items():
            statuses.append(
                WorkStatus(
                    work_id=str(item.get("work_id") or "unknown"),
                    status=str(item.get("status") or "unknown"),
                    change_id=str(item.get("change") or "unknown"),
                    target=str(item.get("target") or "none"),
                    path=Path(str(item.get("path") or ".")),
                )
            )
        return statuses

    def work_summaries(self) -> list[WorkSummary]:
        summaries: list[WorkSummary] = []
        work_root = self.p2p_dir / "work"
        for path in sorted(work_root.iterdir()) if work_root.exists() else []:
            if not path.is_dir():
                continue
            manifest = _read_yaml_mapping(path / "manifest.yml", default={})
            summaries.append(self._work_summary_from_manifest(manifest, path.relative_to(self.root), scanned=False))
        for item in self._scanned_work_items():
            summaries.append(self._work_summary_from_scan(item))
        return summaries

    def show_work(self, work_id: str) -> WorkDetail:
        work_dir = self._find_work_dir(work_id)
        manifest = _read_yaml_mapping(work_dir / "manifest.yml", default={})
        source = manifest.get("source", {})
        handoff = manifest.get("handoff", {})
        git = manifest.get("git", {})
        return WorkDetail(
            work_id=str(manifest.get("work_id") or work_id),
            status=str(manifest.get("status") or "unknown"),
            change_id=str(source.get("change") if isinstance(source, dict) else "unknown"),
            target=str(handoff.get("target") if isinstance(handoff, dict) else "none"),
            branch_name=str(git.get("branch_name") if isinstance(git, dict) else ""),
            path=work_dir.relative_to(self.root),
            manifest=manifest,
        )

    def _work_summary_from_manifest(
        self,
        manifest: dict[str, object],
        path: Path,
        *,
        scanned: bool,
    ) -> WorkSummary:
        source = manifest.get("source", {})
        handoff = manifest.get("handoff", {})
        git = manifest.get("git", {})
        publish = manifest.get("publish", {})
        acceptance = manifest.get("acceptance", {})
        status = str(manifest.get("status") or "unknown")
        work_id = str(manifest.get("work_id") or path.name)
        branch_name = str(git.get("branch_name") if isinstance(git, dict) else "")
        base_branch = str(git.get("base_branch") if isinstance(git, dict) else "main")
        remote = None
        if isinstance(publish, dict):
            remote_value = publish.get("remote")
            if remote_value:
                remote = str(remote_value)
        if status == "accepted" and isinstance(acceptance, dict):
            pushed = bool(acceptance.get("pushed"))
        else:
            pushed = bool(publish.get("remote_branch")) if isinstance(publish, dict) else False
        next_action, note = _work_next_action(
            work_id=work_id,
            status=status,
            base_branch=base_branch,
            pushed=pushed,
            accepted=bool(acceptance) if isinstance(acceptance, dict) else False,
            scanned=scanned,
        )
        return WorkSummary(
            work_id=work_id,
            status=status,
            change_id=str(source.get("change") if isinstance(source, dict) else "unknown"),
            target=str(handoff.get("target") if isinstance(handoff, dict) else "none"),
            branch_name=branch_name,
            base_branch=base_branch,
            remote=remote,
            next_action=next_action,
            note=note,
            path=path,
        )

    def _work_summary_from_scan(self, item: dict[str, object]) -> WorkSummary:
        work_id = str(item.get("work_id") or "unknown")
        status = str(item.get("status") or "unknown")
        branch_name = str(item.get("branch_name") or item.get("branch") or "")
        next_action, note = _work_next_action(
            work_id=work_id,
            status=status,
            base_branch="main",
            pushed=False,
            accepted=False,
            scanned=True,
        )
        return WorkSummary(
            work_id=work_id,
            status=status,
            change_id=str(item.get("change") or "unknown"),
            target=str(item.get("target") or "none"),
            branch_name=branch_name,
            base_branch="main",
            remote=None,
            next_action=next_action,
            note=note,
            path=Path(str(item.get("path") or ".")),
        )

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
        blocker_actions = self._active_choice_blocker_actions()
        actions = self._next_actions_from_project_file()
        if not actions:
            actions = self._fallback_next_actions()
        if blocker_actions:
            existing = {(action.kind, action.target) for action in blocker_actions}
            actions = blocker_actions + [
                action for action in actions if (action.kind, action.target) not in existing
            ]
        if limit is not None:
            return actions[: max(limit, 0)]
        return actions

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
        registries_dir = self.p2p_dir / "registries"
        registries_dir.mkdir(parents=True, exist_ok=True)

        duplicates = self._duplicate_proposal_ids()
        if duplicates:
            raise ValueError(_duplicate_proposal_ids_message(duplicates, self.root))

        proposals = self._proposal_registry_records()
        changes = self._change_registry_records()
        decisions = self._decision_registry_records(proposals)
        choices = self._choice_registry_records()
        relations = self._relation_registry_records(proposals, changes)
        artifacts = self._artifact_registry_records(proposals, changes)

        registry_files = {
            "proposals.yml": {
                "generated": True,
                "source": ".p2p/proposals",
                "proposals": proposals,
            },
            "decisions.yml": {
                "generated": True,
                "source": ".p2p/proposals/*/decision.md",
                "decisions": decisions,
            },
            "changes.yml": {
                "generated": True,
                "source": ".p2p/changes",
                "changes": changes,
            },
            "choices.yml": {
                "generated": True,
                "source": ".p2p/choices and proposal votes",
                "choices": choices,
            },
            "relations.yml": {
                "generated": True,
                "source": ".p2p proposal and change metadata",
                "relations": relations,
            },
            "artifacts.yml": {
                "generated": True,
                "source": ".p2p",
                "artifacts": artifacts,
            },
        }

        written: list[Path] = []
        for filename, data in registry_files.items():
            path = registries_dir / filename
            path.write_text(_yaml_dump(data), encoding="utf-8")
            written.append(path.relative_to(self.root))
        return written

    def registry_status(self) -> RegistryStatus:
        registries_dir = self.p2p_dir / "registries"
        expected = {
            "proposals.yml": "proposals",
            "decisions.yml": "decisions",
            "changes.yml": "changes",
            "choices.yml": "choices",
            "relations.yml": "relations",
            "artifacts.yml": "artifacts",
        }
        files: list[dict[str, object]] = []
        stale = False
        for filename, key in expected.items():
            path = registries_dir / filename
            exists = path.exists()
            count = 0
            generated = False
            if exists:
                data = _read_yaml_mapping(path, default={})
                generated = bool(data.get("generated", False))
                records = data.get(key, [])
                count = len(records) if isinstance(records, list) else 0
                if not generated:
                    stale = True
            else:
                stale = True
            files.append(
                {
                    "name": filename,
                    "exists": exists,
                    "generated": generated,
                    "records": count,
                }
            )

        proposals_count = len(self._proposal_registry_records())
        changes_count = len(self._change_registry_records())
        proposals_file = registries_dir / "proposals.yml"
        changes_file = registries_dir / "changes.yml"
        if proposals_file.exists():
            proposals_data = _read_yaml_mapping(proposals_file, default={})
            proposals_records = proposals_data.get("proposals", [])
            stale = stale or (
                isinstance(proposals_records, list) and len(proposals_records) != proposals_count
            )
        if changes_file.exists():
            changes_data = _read_yaml_mapping(changes_file, default={})
            changes_records = changes_data.get("changes", [])
            stale = stale or (
                isinstance(changes_records, list) and len(changes_records) != changes_count
            )

        return RegistryStatus(
            registries_dir=registries_dir.relative_to(self.root),
            files=files,
            proposals_count=proposals_count,
            changes_count=changes_count,
            stale=stale,
        )

    def show_registry(self, name: str) -> RegistryView:
        allowed = {
            "proposals": "proposals.yml",
            "decisions": "decisions.yml",
            "changes": "changes.yml",
            "choices": "choices.yml",
            "relations": "relations.yml",
            "artifacts": "artifacts.yml",
        }
        if name not in allowed:
            raise ValueError(f"Unsupported registry: {name}")
        path = self.p2p_dir / "registries" / allowed[name]
        if not path.exists():
            raise ValueError("Registry not found. Run `p2p registry refresh` first.")
        data = _read_yaml_mapping(path, default={})
        records = data.get(name, [])
        if not isinstance(records, list):
            raise ValueError(f"Invalid registry file: expected `{name}` list.")
        return RegistryView(
            name=name,
            path=path.relative_to(self.root),
            records=[record for record in records if isinstance(record, dict)],
        )

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
        path = self.p2p_dir / "project" / "next-actions.yml"
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
            action_id = str(record.get("id") or f"NEXT-{index:03d}")
            actions.append(
                NextAction(
                    action_id=action_id,
                    priority=str(record.get("priority") or "medium"),
                    kind=str(record.get("kind") or "other"),
                    target=str(record.get("target") or ""),
                    reason=str(record.get("reason") or ""),
                    command=str(record.get("command") or ""),
                    source=str(path.relative_to(self.root)),
                )
            )
        return actions

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
                    source="fallback",
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
                        source="fallback",
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
                        source="fallback",
                    )
                )
                break

        for proposal in self.proposal_summaries(status="draft"):
            actions.append(
                NextAction(
                    action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                    priority="medium",
                    kind="review_draft_proposal",
                    target=proposal.proposal_id,
                    reason="Draft proposal exists and has no owner decision yet.",
                    command=f"p2p proposal show {proposal.proposal_id}",
                    source="fallback",
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
                        source="fallback",
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
                    source="fallback",
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
        max_id = 0
        proposals_dir = self.p2p_dir / "proposals"
        for path in proposals_dir.iterdir() if proposals_dir.exists() else []:
            match = re.match(r"PROP-(\d{3})-", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"PROP-{max_id + 1:03d}"

    def _find_proposal_dir(self, proposal_id: str) -> Path:
        proposals_dir = self.p2p_dir / "proposals"
        if not proposals_dir.exists():
            raise ValueError("No .p2p/proposals directory found.")
        matches = [path for path in proposals_dir.iterdir() if path.name.startswith(f"{proposal_id}-")]
        if not matches:
            raise ValueError(f"Proposal not found: {proposal_id}")
        if len(matches) > 1:
            relative_paths = ", ".join(str(_relative_to_root(path, self.root)) for path in sorted(matches))
            raise ValueError(
                f"Ambiguous proposal ID: {proposal_id}. Matching proposal directories: {relative_paths}. "
                "Run `p2p validate` to inspect duplicate proposal IDs before continuing."
            )
        return matches[0]

    def _duplicate_proposal_ids(self) -> dict[str, list[Path]]:
        proposals_dir = self.p2p_dir / "proposals"
        grouped: dict[str, list[Path]] = {}
        for path in sorted(proposals_dir.iterdir()) if proposals_dir.exists() else []:
            if not path.is_dir():
                continue
            proposal_id = _proposal_id_from_dir_name(path.name)
            if proposal_id is None:
                continue
            grouped.setdefault(proposal_id, []).append(path)
        return {proposal_id: paths for proposal_id, paths in grouped.items() if len(paths) > 1}

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
        max_id = 0
        work_root = self.p2p_dir / "work"
        for path in work_root.iterdir() if work_root.exists() else []:
            match = re.match(r"WORK-(\d{3})$", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"WORK-{max_id + 1:03d}"

    def _find_work_dir(self, work_id: str) -> Path:
        work_root = self.p2p_dir / "work"
        if not work_root.exists():
            raise ValueError("No .p2p/work directory found.")
        path = work_root / work_id
        if not path.is_dir():
            raise ValueError(f"Work item not found: {work_id}")
        return path


AGENT_PROFILES = {"generic", "codex", "claude", "all"}
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
    aliases = {
        "claude-code": "claude",
        "anthropic": "claude",
        "openai-codex": "codex",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in AGENT_PROFILES:
        raise ValueError("Agent profile must be generic, codex, claude, or all")
    return normalized


def _expanded_agent_profiles(profile: str) -> list[str]:
    if profile == "all":
        return ["generic", "codex", "claude"]
    return [profile]


def _normalize_repository_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    aliases = {"remote": "cloud", "hosted": "cloud"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in REPOSITORY_MODES:
        raise ValueError("Repository mode must be local or cloud")
    return normalized


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
    files = {Path("AGENTS.md"): _agents_markdown(project_name, profiles, repository_mode)}
    if "codex" in profiles:
        files[Path(".codex/skills/p2p-project/SKILL.md")] = _codex_project_skill(
            project_name,
            repository_mode,
        )
    if "claude" in profiles:
        files[Path("CLAUDE.md")] = _claude_markdown(project_name, repository_mode)
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
                "p2p_sync_status",
                "p2p_sync_fetch",
                "p2p_sync_pull",
                "p2p_sync_push",
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
    return f"""# Agent Instructions - {project_name}

This project uses P2P Engine.

## Source Of Truth

- Use the `p2p` CLI as the public write interface.
- Treat `.p2p/` as managed project state.
- Do not create, edit, rename, or delete files under `.p2p/` by hand unless the owner explicitly asks for a repair.
- Do not invent proposal IDs, choice IDs, change IDs, work IDs, registry entries, or internal P2P file layouts.

## Missing Primitive Rule

If the requested action cannot be performed with an available `p2p` command or an explicit MCP write tool, stop and report the limitation.

Do not satisfy the request by reverse-engineering `.p2p/` and writing files directly.

## Governance Boundary

The owner controls governance decisions. Agents may draft, analyze, compare, and suggest actions, but must not decide on behalf of the owner.

Owner-controlled actions include:

- accepting, rejecting, or deferring proposals;
- deciding choices;
- accepting, finalizing, cleaning up, or merging managed work;
- accepting, rejecting, merging, or finalizing managed proposal branches;
- changing governance policy;
- creating direct Git merges into the main branch.

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

When MCP is read-only, use it for status and inspection only. For mutations, use `p2p` CLI commands when available or explicit write-safe MCP tools such as `p2p_proposal_branch` and `p2p_sync_fetch` when their schema matches the requested action.

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


def _codex_project_skill(project_name: str, repository_mode: str) -> str:
    return f"""---
name: p2p-project
description: Use when working in this P2P-managed project. Enforces P2P Engine boundaries for Codex.
---

# P2P Project Skill - {project_name}

Use P2P Engine as the source of truth for project governance and planning.

## Required Behavior

- Read `AGENTS.md` and `.p2p/agent-policy.yml` before modifying project state.
- Use `p2p` CLI commands for P2P mutations.
- Use MCP only within the tool schema; read-only MCP tools do not authorize filesystem writes.
- If no CLI command or MCP write tool exists for the requested operation, stop and report the missing primitive.
- Do not edit `.p2p/` internals directly, invent IDs, or synthesize decision files.
- Do not accept, reject, defer, decide, merge, finalize, or cleanup without explicit owner instruction.
- Do not run raw Git commands for managed branch, sync, publish, or merge work unless the owner explicitly authorizes an escape hatch.
- Use `p2p sync status` before managed branch work, `p2p proposal branch` for proposal branches, and `p2p proposal publish --auto-renumber` only when publish reports a recoverable proposal ID collision.
- Before explaining existing proposals, choices, Change Sets, or Work items, use the relevant `p2p ... show` command or equivalent MCP read tool.
- Use `p2p context --budget small` or MCP `p2p_context` before broad file reads.
- Do not scan all `.p2p/`, registries, source files, or Git history unless the task explicitly requires it.

## Useful Commands

```bash
p2p status
p2p context --budget small
p2p registry refresh
p2p next
p2p proposal list
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
    return f"""# Claude Instructions - {project_name}

This repository is managed with P2P Engine.

Follow `AGENTS.md` and `.p2p/agent-policy.yml`.

Key rules:

- Use `p2p` CLI commands for P2P writes.
- Do not modify `.p2p/` internals directly.
- If a requested P2P action has no available command or MCP write tool, stop and explain the missing primitive.
- Do not make owner-controlled governance decisions unless the owner explicitly instructs the exact decision.
- Do not run raw Git commands for managed branch, sync, publish, or merge work unless the owner explicitly authorizes an escape hatch.
- Use `p2p sync status`, `p2p proposal branch`, `p2p proposal publish`, `p2p proposal request-review`, and `p2p proposal scan` for managed collaboration workflows.
- Treat MCP as read-only unless a tool explicitly declares a write operation.
- Before explaining existing proposals, choices, Change Sets, or Work items, read them with the relevant `p2p ... show` command or equivalent MCP read tool.
- Use `p2p context --budget small` or MCP `p2p_context` before broad file reads.
- Do not scan all `.p2p/`, registries, source files, or Git history unless the task explicitly requires it.

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


def _project_assessment_payload(assessment: ProjectAssessment) -> dict[str, object]:
    return {
        "generated_on": assessment.generated_on,
        "assessment_type": assessment.assessment_type,
        "completion": {
            "score": assessment.completion_score,
            "status": assessment.completion_status,
            "confidence": assessment.confidence,
        },
        "maturity": {
            "status": assessment.maturity_status,
            "score": assessment.maturity_score,
        },
        "factors": assessment.factors,
        "gaps": assessment.gaps,
        "suggested_actions": assessment.suggested_actions,
    }


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


def _read_title(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return None


def _read_markdown_section(text: str, section: str) -> str | None:
    pattern = rf"## {re.escape(section)}\n\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        return None
    value = match.group(1).strip()
    if not value or value in {"Pending.", "- Pending."}:
        return None
    return value


def _markdown_has_section(text: str, section: str) -> bool:
    return re.search(rf"^## {re.escape(section)}\s*$", text, flags=re.MULTILINE) is not None


def _clean_proposal_title(title: str, proposal_id: str) -> str:
    cleaned = re.sub(rf"^{re.escape(proposal_id)}\s*[-—]\s*", "", title).strip()
    return cleaned or title


def _read_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _replace_frontmatter(text: str, frontmatter: dict[str, object]) -> str:
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            body = text[end + len("\n---\n") :]
    return f"---\n{_yaml_dump(frontmatter)}---\n{body}"


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


def _work_manifest(
    work_id: str,
    change_id: str,
    target: str,
    branch_name: str,
    export_path: str,
    source_proposals: list[str],
    allowed_files: list[str],
) -> dict[str, object]:
    return {
        "work_id": work_id,
        "status": "planned",
        "visibility": "internal_git",
        "created_at": date.today().isoformat(),
        "source": {
            "change": change_id,
            "proposals": source_proposals,
        },
        "handoff": {
            "target": target,
            "export_path": export_path,
            "export_validated": True,
        },
        "managed_git_levels": [
            {"level": 0, "name": "advisory", "enabled": True},
            {"level": 1, "name": "handoff_plan", "enabled": True},
            {"level": 2, "name": "managed_branch", "enabled": False},
            {"level": 3, "name": "managed_commit", "enabled": False},
            {"level": 4, "name": "managed_review", "enabled": False},
            {"level": 5, "name": "owner_controlled_merge", "enabled": False},
        ],
        "git": {
            "mode": "managed_branch_candidate",
            "base_branch": "main",
            "branch_name": branch_name,
            "base_commit": None,
            "head_commit": None,
        },
        "policy": {
            "expose_git_details": False,
            "auto_branch": False,
            "auto_commit": False,
            "auto_merge": False,
            "owner_approval_required": ["branch", "submit", "accept_merge"],
        },
        "allowed_files": allowed_files,
        "next_steps": [
            "Implement branch scan for p2p/work/* refs.",
            "Enable managed branch creation only after policy approval.",
            "Enable selected-file commits only after dirty worktree and recovery checks.",
            "Enable owner-controlled accept/merge only after review policy is defined.",
        ],
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


def _project_brief_prompt_markdown(context: str) -> str:
    return (
        "# P2P Operational Brief Prompt\n\n"
        "You are helping synthesize the current P2P project state into an operational brief.\n\n"
        "## Governance Boundary\n\n"
        "Do not accept, reject, defer, merge, supersede, or apply recommendations. "
        "Do not decide on behalf of the owner. Recommend next actions only and point to "
        "the P2P commands that would let the owner act explicitly.\n\n"
        "## Project Context\n\n"
        f"{context}\n\n"
        "## Required Output\n\n"
        "Return artifacts with these shapes:\n\n"
        "### operational-brief.md\n\n"
        "```markdown\n"
        "# Operational Brief\n\n"
        "## Where We Are\n"
        "Short synthesis of the current project state.\n\n"
        "## Accepted Direction\n"
        "Accepted decisions and constraints that shape the project.\n\n"
        "## Active Work\n"
        "Change Sets, draft proposals, pending intake, and work still moving.\n\n"
        "## Blockers / Inconsistencies\n"
        "Open choices, conflicts, stale registries, status mismatches, or missing artifacts.\n\n"
        "## Recommended Next Actions\n"
        "1. Action title\n"
        "   Reason: Why this matters now.\n"
        "   Command: p2p ...\n\n"
        "## Not Yet\n"
        "Useful but lower-priority directions.\n"
        "```\n\n"
        "### next-actions.yml\n\n"
        "```yaml\n"
        "next_actions:\n"
        "  - id: NEXT-001\n"
        "    priority: high | medium | low\n"
        "    kind: continue_change | resolve_choice | refresh_registry | inspect_intake | record_conflict | create_change | other\n"
        "    target: CHANGE-000\n"
        "    reason: Short reason.\n"
        "    command: p2p ...\n"
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


def _strip_markdown_title(content: str) -> str:
    lines = content.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        if lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip()


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


def _project_overview_markdown(project_name: str, accepted: list[dict[str, object]]) -> str:
    lines = [
        f"# Project State - {project_name}",
        "",
        "This file is generated by `p2p project refresh` from accepted proposals.",
        "",
        "## Accepted Proposals",
        "",
    ]
    if accepted:
        for item in accepted:
            lines.append(f"- {item['proposal_id']} - {item['title']}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Features", ""])
    if accepted:
        for item in accepted:
            lines.append(f"- `{item['feature_id']}` from {item['proposal_id']}")
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def _project_problem_markdown(accepted: list[dict[str, object]]) -> str:
    lines = ["# Project Problem", "", "Generated from accepted proposal problem statements.", ""]
    for item in accepted:
        lines.extend([f"## {item['proposal_id']} - {item['title']}", "", str(item["problem"]), ""])
    if not accepted:
        lines.append("No accepted proposals yet.\n")
    return "\n".join(lines)


def _project_scope_markdown(accepted: list[dict[str, object]]) -> str:
    lines = ["# Project Scope", "", "Generated from accepted proposal goals and non-goals.", ""]
    for item in accepted:
        lines.extend(
            [
                f"## {item['proposal_id']} - {item['title']}",
                "",
                "### Goals",
                "",
                str(item["goals"]),
                "",
                "### Non-Goals",
                "",
                str(item["non_goals"]),
                "",
            ]
        )
    if not accepted:
        lines.append("No accepted proposals yet.\n")
    return "\n".join(lines)


def _project_swot_markdown() -> str:
    return (
        "# Project SWOT\n\n"
        "Generated placeholder. Use `p2p swot prompt <PROP-ID>` for proposal-level SWOT "
        "and consolidate project-level findings here during project refresh evolution.\n"
    )


def _feature_markdown(item: dict[str, object]) -> str:
    return (
        f"# {item['title']}\n\n"
        "## Provenance\n\n"
        f"- Proposal: {item['proposal_id']}\n"
        f"- Source: {item['source']}\n\n"
        "## Problem\n\n"
        f"{item['problem']}\n\n"
        "## Proposal\n\n"
        f"{item['proposal']}\n\n"
        "## Decision\n\n"
        f"{str(item['decision']).strip() or 'Not provided.'}\n"
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


def _replace_section(text: str, section: str, replacement: str) -> str:
    pattern = rf"(## {re.escape(section)}\n\n)(.*?)(?=\n## |\Z)"
    return re.sub(pattern, lambda match: f"{match.group(1)}{replacement}\n", text, count=1, flags=re.DOTALL)


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


def _validate_tasks_yaml(content: str) -> None:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid tasks YAML: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise ValueError("Invalid tasks YAML: expected top-level `tasks` list.")


def _validate_yaml_key(content: str, key: str) -> None:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc
    if not isinstance(data, dict) or key not in data:
        raise ValueError(f"Invalid YAML: expected top-level `{key}` key.")


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


def _work_next_action(
    *,
    work_id: str,
    status: str,
    base_branch: str,
    pushed: bool,
    accepted: bool,
    scanned: bool,
) -> tuple[str, str]:
    if scanned:
        return "p2p work show {work_id}".format(work_id=work_id), "scanned from a managed branch registry"
    if status == "planned":
        return f"p2p work branch {work_id}", "create the managed implementation branch"
    if status == "retired":
        return "none", "retired"
    if status == "branched":
        return f"p2p work submit {work_id}", "submit actual work changes as a local commit"
    if status == "submitted":
        return f"p2p work review {work_id}", "request local owner review"
    if status == "review_requested":
        return f"p2p work publish {work_id}", "publish the managed branch to the remote"
    if status == "published":
        return f"checkout {base_branch}; p2p work accept {work_id}", "owner-controlled local merge"
    if status == "merge_conflict":
        return f"resolve conflicts; p2p work accept --continue {work_id}", "or abort with p2p work accept --abort"
    if status == "accepted":
        if accepted and not pushed:
            return "p2p work finalize {work_id}".format(work_id=work_id), "push the accepted base branch"
        return "none", "accepted"
    if status == "finalized":
        return "p2p work cleanup {work_id}".format(work_id=work_id), "delete finalized Work branches"
    if status == "cleaned":
        return "none", "cleaned"
    return "inspect", "unknown Work status"


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

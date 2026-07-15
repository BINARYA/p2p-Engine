from __future__ import annotations

import re
import hashlib
import os
from dataclasses import asdict
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Protocol, TypeVar

import yaml

from p2p_engine.core.project_verticals import (
    ActiveProjectVertical,
    CustomVerticalCandidate,
    ProjectDefinitionAssumption,
    ProjectDefinitionBlocker,
    ProjectDefinitionFieldValue,
    ProjectDefinitionHistoryEntry,
    ProjectDefinitionPatch,
    ProjectDefinitionPatchResult,
    ProjectDefinitionQuestion,
    ProjectDefinitionSectionState,
    ProjectDefinitionState,
    ProjectDefinitionView,
    ProjectReadinessReview,
    ProjectVerticalAddResult,
    ProjectVerticalContext,
    ProposalVerticalCoverage,
    ProposalVerticalCoverageSection,
    ProposalVerticalCoverageStatus,
    ProposalVerticalCoverageSuggestion,
    ResolvedVerticalPack,
    VerticalArtifact,
    VerticalCompletionPolicy,
    VerticalField,
    VerticalLock,
    VerticalLockStatus,
    VerticalListItem,
    VerticalManifest,
    VerticalModule,
    VerticalPack,
    VerticalPackSource,
    VerticalProfile,
    VerticalQuestion,
    VerticalRubric,
    VerticalSection,
    VerticalSectionReview,
    VerticalValidationIssue,
    VerticalValidationResult,
    VerticalMigrationCandidate,
    VerticalCoverageSuggestionSection,
)
from p2p_engine.core.mutation_preview import (
    MutationPreview,
    MutationPreviewService,
    MutationResult,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.foundation.files import relative_to_root, slugify, write_text_atomic, write_yaml_atomic, yaml_dump
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.services.lifecycle_authority import is_active_project_projection

VERTICAL_SCHEMA_VERSION = 1
ACTIVE_VERTICAL_SCHEMA_VERSION = 1
PROPOSAL_COVERAGE_SCHEMA_VERSION = 1
VERTICAL_LOCK_SCHEMA_VERSION = 1
PROJECT_DEFINITION_SCHEMA_VERSION = 1
BASE_PROJECT_VERTICAL_ID = "base_project"
EXPLICIT_SOURCE = "explicit"
PROJECT_LOCAL_SOURCE = "project_local"
INSTALLED_P2P_HOME_SOURCE = "installed_p2p_home"
INSTALLED_USER_SOURCE = "installed_user"
INTERNAL_SOURCE = "internal"
FALLBACK_SOURCE = "fallback"
PROJECT_DEFINITION_STATUSES = {"missing", "partial", "assumed", "complete", "blocked", "not_applicable"}
ASSUMPTION_STATUSES = {"to_validate", "validated", "rejected", "superseded"}

RELEVANCE_VALUES = {"direct", "indirect", "context", "unknown"}
QUESTION_PRIORITIES = {"high", "medium", "low"}
T = TypeVar("T")


class _ProposalSummaryLike(Protocol):
    proposal_id: str
    title: str
    status: str


def validate_vertical_pack_payload(payload: dict[str, object], *, target: str = "vertical") -> None:
    payload = _normalise_pack_payload(payload)
    issues = _vertical_pack_issues(payload)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        first = errors[0]
        raise ValueError(f"Invalid vertical pack {target}: {first.field}: {first.message}")


def validate_vertical_coverage_payload(payload: dict[str, object], *, target: str = "vertical-coverage") -> None:
    coverage = payload.get("vertical_coverage")
    if not isinstance(coverage, dict):
        raise ValueError(f"Invalid {target}: expected top-level `vertical_coverage` mapping.")
    proposal_id = str(coverage.get("proposal_id") or "").strip()
    vertical_id = str(coverage.get("vertical_id") or "").strip()
    sections = coverage.get("sections")
    if not proposal_id:
        raise ValueError(f"Invalid {target}: missing proposal_id.")
    if not vertical_id:
        raise ValueError(f"Invalid {target}: missing vertical_id.")
    if not isinstance(sections, list):
        raise ValueError(f"Invalid {target}: sections must be a list.")
    schema_version = coverage.get("schema_version", 1)
    if schema_version not in {1, 2}:
        raise ValueError(f"Invalid {target}: unsupported schema_version `{schema_version}`.")
    if schema_version == 2:
        unknown = set(coverage) - {"schema_version", "proposal_id", "vertical_id", "sections", "provenance"}
        if unknown:
            raise ValueError(f"Invalid {target}: unknown fields: {', '.join(sorted(unknown))}.")
        provenance = coverage.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError(f"Invalid {target}: schema v2 requires provenance mapping.")
        for field in ("actor", "authority", "source", "operation_id"):
            if not str(provenance.get(field) or "").strip():
                raise ValueError(f"Invalid {target}: provenance.{field} is required.")
    for index, item in enumerate(sections):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid {target}: sections[{index}] must be a mapping.")
        section_id = str(item.get("id") or "").strip()
        relevance = str(item.get("relevance") or "direct").strip()
        if not section_id:
            raise ValueError(f"Invalid {target}: sections[{index}].id is required.")
        if relevance not in RELEVANCE_VALUES:
            raise ValueError(f"Invalid {target}: sections[{index}].relevance must be one of {sorted(RELEVANCE_VALUES)}.")
        if schema_version == 2:
            unknown = set(item) - {"id", "relevance", "rationale", "source", "provenance"}
            if unknown:
                raise ValueError(f"Invalid {target}: sections[{index}] has unknown fields: {', '.join(sorted(unknown))}.")
            if not str(item.get("rationale") or "").strip():
                raise ValueError(f"Invalid {target}: sections[{index}].rationale is required.")
            if not str(item.get("source") or "").strip():
                raise ValueError(f"Invalid {target}: sections[{index}].source is required.")
            if not isinstance(item.get("provenance"), dict):
                raise ValueError(f"Invalid {target}: sections[{index}].provenance must be a mapping.")


class ProjectVerticalService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        proposal_summaries: Callable[[], list[_ProposalSummaryLike]],
        find_proposal_dir: Callable[[str], Path],
        atomic_writer: AtomicMutationWriter | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.proposal_summaries = proposal_summaries
        self.find_proposal_dir = find_proposal_dir
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=root, p2p_dir=p2p_dir)

    def list_verticals(self) -> list[VerticalListItem]:
        active = self.active_vertical()
        packs_by_id = self._available_packs_by_id()
        items: list[VerticalListItem] = []
        for vertical_id in sorted(packs_by_id):
            pack = packs_by_id[vertical_id]
            items.append(
                VerticalListItem(
                    vertical_id=pack.vertical_id,
                    name=pack.name,
                    version=pack.version,
                    source=pack.source,
                    active=pack.vertical_id == active.vertical_id and not active.fallback_used,
                    path=relative_to_root(pack.path, self.root) if pack.path else None,
                )
            )
        return items

    def show_vertical(self, vertical_id: str) -> VerticalPack:
        return self._load_available_pack(vertical_id)

    def validate_vertical(self, target: str) -> VerticalValidationResult:
        try:
            pack, payload = self._load_target_for_validation(target)
        except ValueError as exc:
            return VerticalValidationResult(
                target=target,
                valid=False,
                vertical_id="",
                source="unknown",
                issues=[VerticalValidationIssue("error", "target", str(exc))],
            )
        issues = [*_vertical_pack_issues(payload), *self._extension_issues(pack)]
        return VerticalValidationResult(
            target=target,
            valid=not any(issue.severity == "error" for issue in issues),
            vertical_id=pack.vertical_id,
            source=pack.source,
            issues=issues,
        )

    def propose_vertical(self, idea: str) -> CustomVerticalCandidate:
        text = idea.strip()
        if not text:
            raise ValueError("Project idea is required.")
        lower = text.lower()
        if any(token in lower for token in ("scatola", "box", "packaging", "confezione")):
            pack = _candidate_pack(
                vertical_id="packaging_or_physical_product_design",
                name="Packaging Or Physical Product Design",
                description="Design a box or packaging solution from concept to manufacturable specification.",
                sections=[
                    ("contained_product", "Contained Product And Use Case", "Define what the box contains and how it will be used."),
                    ("success_definition", "Meaning Of Perfect", "Clarify which tradeoffs define a perfect box."),
                    ("structure_materials", "Structure And Materials", "Define dimensions, materials, sustainability, and physical structure."),
                    ("prototype_testing", "Prototype And Tests", "Define prototype plan and validation checks."),
                ],
                questions=[
                    ("contained_product_main", "contained_product", "What must the box contain?"),
                    ("perfect_tradeoff_main", "success_definition", "Does perfect mean beautiful, resistant, cheap, sustainable, memorable, or a weighted combination?"),
                ],
                artifacts=[
                    ("packaging_brief", "Packaging Brief", ["contained_product", "success_definition"]),
                    ("prototype_test_checklist", "Prototype Test Checklist", ["prototype_testing"]),
                ],
            )
        elif any(token in lower for token in ("banca", "bank", "sociale", "impact", "impatto")):
            pack = _candidate_pack(
                vertical_id="social_impact_program_design",
                name="Social Impact Program Design",
                description="Design social impact initiatives that are measurable, governed, credible, and connected to stakeholder needs.",
                sections=[
                    ("social_impact_vision", "Social Impact Vision", "Define the social change the program should create."),
                    ("theory_of_change", "Theory Of Change", "Explain how activities create outcomes for beneficiaries."),
                    ("beneficiary_communities", "Beneficiary Communities", "Identify who benefits and why they are prioritized."),
                    ("measurement_reporting", "Measurement And Reporting", "Define outcome metrics, evidence, and reporting cadence."),
                ],
                questions=[
                    ("beneficiary_main", "beneficiary_communities", "Which community or population should benefit?"),
                    ("measurement_main", "measurement_reporting", "How will real impact be measured and how will social-washing be avoided?"),
                ],
                artifacts=[
                    ("social_impact_strategy_brief", "Social Impact Strategy Brief", ["social_impact_vision"]),
                    ("outcome_metric_framework", "Outcome Metric Framework", ["measurement_reporting"]),
                ],
            )
        else:
            base_slug = slugify(text, fallback="custom_project")
            vertical_id = f"{base_slug}_design"
            pack = _candidate_pack(
                vertical_id=vertical_id,
                name=_title_from_slug(vertical_id),
                description=f"Project-local custom vertical candidate for: {text}",
                sections=[
                    ("domain_context", "Domain Context", "Define the specific domain and why base_project is not enough."),
                    ("specific_capisaldi", "Specific Capisaldi", "Identify the domain-specific pillars to address."),
                    ("specific_artifacts", "Specific Artifacts", "Define artifacts expected from this kind of project."),
                ],
                questions=[
                    ("domain_context_main", "domain_context", "What makes this project different from a generic project?"),
                    ("capisaldi_main", "specific_capisaldi", "Which domain-specific pillars must be addressed first?"),
                ],
                artifacts=[
                    ("custom_vertical_brief", "Custom Vertical Brief", ["domain_context", "specific_capisaldi"]),
                ],
            )

        payload = {
            "vertical_candidate": {
                "schema_version": VERTICAL_SCHEMA_VERSION,
                "source_idea": text,
                "candidate": _pack_payload(pack)["vertical"],
                "rationale": {
                    "base_project_sections_reused": ["vision", "objective", "stakeholders", "scope", "risks", "definition_of_done"],
                    "vertical_specific_additions": [section.section_id for section in pack.sections],
                },
            }
        }
        return CustomVerticalCandidate(
            source_idea=text,
            pack=pack,
            base_project_sections_reused=["vision", "objective", "stakeholders", "scope", "risks", "definition_of_done"],
            vertical_specific_additions=[section.section_id for section in pack.sections],
            yaml_text=yaml_dump(payload),
        )

    def add_vertical(self, source: Path, *, activate: bool = False, actor: str = "local") -> ProjectVerticalAddResult:
        pack = self._load_pack_from_path(source)
        validate_vertical_pack_payload(_pack_payload(pack), target=str(source))
        target_dir = self._project_verticals_dir() / pack.vertical_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / "vertical.yml"
        self._atomic_write(target_path, yaml_dump(_pack_payload(pack)))
        activated = False
        if activate:
            self.select_vertical(pack.vertical_id, actor=actor)
            activated = True
        return ProjectVerticalAddResult(
            vertical_id=pack.vertical_id,
            path=relative_to_root(target_path, self.root),
            activated=activated,
        )

    def select_vertical(
        self,
        vertical_id: str,
        *,
        actor: str = "local",
        profile: str = "default",
        modules: list[str] | None = None,
    ) -> ActiveProjectVertical:
        candidate = self.render_migration_candidate(
            vertical_id,
            actor=actor,
            profile=profile,
            modules=modules,
        )
        self.validate_migration_candidate(candidate)
        sources = tuple(
            source_precondition(
                path,
                (self.root / path).read_bytes() if (self.root / path).exists() else None,
            )
            for path in sorted(candidate.candidate_files)
        )
        token = MutationPreviewService.token(
            operation_id=f"project-vertical-select:{vertical_id}",
            targets=tuple(candidate.candidate_files),
            sources=sources,
            candidate_semantics={
                path: yaml.safe_load(content.decode("utf-8"))
                for path, content in candidate.candidate_files.items()
            },
        )
        result = self.atomic_writer.apply(
            operation_id=f"project-vertical-select:{vertical_id}",
            candidates=candidate.candidate_files,
            sources=sources,
            preview_token=token,
            actor=actor,
        )
        if result.status != "applied":
            raise ValueError(result.message or f"Project vertical selection failed: {result.status}")
        return self.active_vertical()

    def render_migration_candidate(
        self,
        vertical_id: str,
        *,
        actor: str,
        profile: str = "default",
        modules: list[str] | None = None,
        audit_date: str | None = None,
        rubric_mapping: dict[str, str] | None = None,
    ) -> VerticalMigrationCandidate:
        resolved = self._resolve_available_pack(vertical_id)
        pack = resolved.pack
        selected_at = audit_date or date.today().isoformat()
        selected_modules = list(dict.fromkeys(modules if modules is not None else pack.modules))
        available_profiles = {"default", *pack.profiles, *(item.profile_id for item in pack.profile_specs)}
        if profile not in available_profiles:
            raise ValueError(f"Unknown vertical profile `{profile}` for `{vertical_id}`.")
        available_modules = {*pack.modules, *(item.module_id for item in pack.module_specs)}
        unknown_modules = sorted(set(selected_modules) - available_modules)
        if unknown_modules:
            raise ValueError(f"Unknown vertical module `{unknown_modules[0]}` for `{vertical_id}`.")
        active_payload = {
            "project_vertical": {
                "schema_version": ACTIVE_VERTICAL_SCHEMA_VERSION,
                "active_vertical_id": pack.vertical_id,
                "active_source": pack.source,
                "selected_at": selected_at,
                "selected_by": actor,
                "fallback_used": False,
            }
        }
        lock = VerticalLock(
            vertical_id=pack.vertical_id,
            name=pack.name,
            version=pack.version,
            pack_schema_version=pack.schema_version,
            source=resolved.source,
            checksum=resolved.checksum,
            compatibility=pack.compatibility,
            selected_at=selected_at,
            selected_by=actor,
            trust={"signed": False},
            path=relative_to_root(self._vertical_lock_path(), self.root),
        )
        definition = self._initial_definition_state(
            resolved,
            profile=profile,
            modules=selected_modules,
            actor=actor,
            audit_date=selected_at,
        )
        candidate_files = {
            self._active_vertical_path().relative_to(self.root).as_posix(): yaml_dump(active_payload).encode("utf-8"),
            self._vertical_lock_path().relative_to(self.root).as_posix(): yaml_dump(_vertical_lock_payload(lock)).encode("utf-8"),
            self._definition_state_path().relative_to(self.root).as_posix(): yaml_dump(_definition_state_payload(definition)).encode("utf-8"),
            (self.p2p_dir / "project" / "rubrics.yml").relative_to(self.root).as_posix(): yaml_dump(
                self._vertical_rubrics_payload(pack, rubric_mapping=rubric_mapping)
            ).encode("utf-8"),
        }
        return VerticalMigrationCandidate(
            vertical_id=pack.vertical_id,
            profile=profile,
            modules=tuple(selected_modules),
            checksum=resolved.checksum,
            candidate_files=candidate_files,
        )

    def validate_migration_candidate(self, candidate: VerticalMigrationCandidate) -> None:
        expected = {
            ".p2p/project/vertical.yml",
            ".p2p/project/vertical.lock.yml",
            ".p2p/project/definition.yml",
            ".p2p/project/rubrics.yml",
        }
        if set(candidate.candidate_files) != expected:
            raise ValueError("Vertical migration candidate must contain the complete four-artifact set.")
        payloads: dict[str, dict[str, object]] = {}
        for path, content in candidate.candidate_files.items():
            value = yaml.safe_load(content.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError(f"Vertical migration candidate must be a YAML mapping: {path}")
            payloads[path] = value
        active = payloads[".p2p/project/vertical.yml"].get("project_vertical")
        lock = payloads[".p2p/project/vertical.lock.yml"].get("project_vertical_lock")
        definition = _definition_state_from_payload(
            payloads[".p2p/project/definition.yml"],
            path=Path(".p2p/project/definition.yml"),
        )
        if not isinstance(active, dict) or active.get("active_vertical_id") != candidate.vertical_id:
            raise ValueError("Vertical migration active-state candidate is incoherent.")
        checksum = lock.get("checksum") if isinstance(lock, dict) else None
        if not isinstance(checksum, dict) or checksum.get("value") != candidate.checksum:
            raise ValueError("Vertical migration lock checksum is incoherent.")
        pack = self._load_available_pack(candidate.vertical_id)
        issues = self._definition_state_issues(definition, pack)
        if any(issue.severity == "error" for issue in issues):
            first = next(issue for issue in issues if issue.severity == "error")
            raise ValueError(f"Invalid vertical migration definition: {first.field}: {first.message}")
        rubrics = payloads[".p2p/project/rubrics.yml"].get("criteria")
        if not isinstance(rubrics, list):
            raise ValueError("Vertical migration rubric candidate must contain criteria.")

    def active_vertical(self) -> ActiveProjectVertical:
        path = self._active_vertical_path()
        if not path.exists():
            base = self._load_available_pack(BASE_PROJECT_VERTICAL_ID)
            return ActiveProjectVertical(
                vertical_id=BASE_PROJECT_VERTICAL_ID,
                source=base.source,
                path=relative_to_root(base.path, self.root) if base.path else None,
                fallback_used=True,
            )
        payload = _read_yaml_mapping(path)
        state = payload.get("project_vertical")
        if not isinstance(state, dict):
            raise ValueError(f"Invalid project vertical state: {path}")
        vertical_id = str(state.get("active_vertical_id") or "").strip()
        if not vertical_id:
            raise ValueError(f"Invalid project vertical state: missing active_vertical_id in {path}")
        if self._vertical_lock_path().exists():
            lock_status = self.vertical_lock_status()
            if lock_status.status != "valid":
                raise ValueError(
                    f"Active project vertical lock is {lock_status.status}: {lock_status.message} "
                    f"{lock_status.suggested_command}".strip()
                )
        pack = self._load_available_pack(vertical_id)
        return ActiveProjectVertical(
            vertical_id=vertical_id,
            source=str(state.get("active_source") or pack.source),
            path=relative_to_root(pack.path, self.root) if pack.path else None,
            selected_at=str(state.get("selected_at") or ""),
            selected_by=str(state.get("selected_by") or ""),
            fallback_used=bool(state.get("fallback_used") or False),
        )

    def vertical_lock_status(self) -> VerticalLockStatus:
        lock_path = self._vertical_lock_path()
        display_path = relative_to_root(lock_path, self.root)
        if not lock_path.exists():
            message = "Project vertical lockfile is missing."
            suggested = "p2p project vertical lock repair --actor owner"
            if not self._active_vertical_path().exists():
                message = "No active project vertical is selected; base_project fallback is in use."
                suggested = "p2p project vertical select base_project --actor owner"
            return VerticalLockStatus(
                status="missing",
                path=display_path,
                message=message,
                suggested_command=suggested,
            )
        try:
            locked = self._read_vertical_lock(lock_path)
        except ValueError as exc:
            return VerticalLockStatus(
                status="invalid",
                path=display_path,
                message=str(exc),
                suggested_command="p2p project vertical lock repair --actor owner",
            )
        try:
            resolved = self._resolve_available_pack(locked.vertical_id)
        except ValueError as exc:
            return VerticalLockStatus(
                status="missing_source",
                path=display_path,
                locked=locked,
                message=str(exc),
                suggested_command="p2p project vertical lock repair --actor owner",
            )
        if resolved.checksum != locked.checksum:
            return VerticalLockStatus(
                status="checksum_mismatch",
                path=display_path,
                locked=locked,
                resolved=resolved,
                message=f"Locked checksum {locked.checksum} does not match resolved checksum {resolved.checksum}.",
                suggested_command="p2p project vertical lock repair --actor owner",
            )
        return VerticalLockStatus(
            status="valid",
            path=display_path,
            locked=locked,
            resolved=resolved,
            message="Project vertical lock is valid.",
        )

    def repair_vertical_lock(self, *, actor: str = "local") -> VerticalLock:
        state_path = self._active_vertical_path()
        if not state_path.exists():
            raise ValueError("No active project vertical state exists. Select a vertical before repairing the lock.")
        payload = _read_yaml_mapping(state_path)
        state = payload.get("project_vertical")
        if not isinstance(state, dict):
            raise ValueError(f"Invalid project vertical state: {state_path}")
        vertical_id = str(state.get("active_vertical_id") or "").strip()
        if not vertical_id:
            raise ValueError(f"Invalid project vertical state: missing active_vertical_id in {state_path}")
        resolved = self._resolve_available_pack(vertical_id)
        return self._write_vertical_lock(resolved, actor=actor)

    def project_context(self) -> ProjectVerticalContext:
        active = self.active_vertical()
        lock_status = self.vertical_lock_status()
        definition = self.project_definition_view()
        rubrics = self._rubric_summary()
        definition_summary = self._definition_summary(definition)
        warnings: list[str] = []
        if active.fallback_used:
            warnings.append("base_project fallback is in use")
        if lock_status.status != "valid":
            warnings.append(lock_status.message)
        if definition.exists and not definition.valid:
            warnings.extend(issue.message for issue in definition.issues)
        state = definition.state
        return ProjectVerticalContext(
            active=active,
            lock_status=lock_status,
            selected_profile=state.profile if state else "default",
            enabled_modules=state.modules if state else [],
            rubric_summary=rubrics,
            definition_summary=definition_summary,
            warnings=warnings,
            next_suggested_action=state.next_suggested_action if state else {},
        )

    def list_sections(self, *, vertical_id: str | None = None) -> list[VerticalSection]:
        active = self.active_vertical()
        pack = self._load_available_pack(vertical_id or active.vertical_id)
        return sorted(pack.sections, key=lambda section: section.priority)

    def show_section(self, section_id: str, *, vertical_id: str | None = None) -> VerticalSection:
        normalized = section_id.strip()
        for section in self.list_sections(vertical_id=vertical_id):
            if section.section_id == normalized:
                return section
        raise ValueError(f"Unknown project vertical section `{section_id}`.")

    def project_definition_view(self) -> ProjectDefinitionView:
        path = self._definition_state_path()
        display_path = relative_to_root(path, self.root)
        if not path.exists():
            return ProjectDefinitionView(
                exists=False,
                valid=False,
                path=display_path,
                issues=[
                    VerticalValidationIssue(
                        "warning",
                        "project_definition",
                        "Project definition state is missing.",
                        "P2P_VERTICAL_DEFINITION_MISSING",
                    )
                ],
            )
        try:
            state = self._read_definition_state(path)
            active = self.active_vertical()
            pack = self._load_available_pack(active.vertical_id)
            issues = self._definition_state_issues(state, pack)
        except ValueError as exc:
            return ProjectDefinitionView(
                exists=True,
                valid=False,
                path=display_path,
                issues=[
                    VerticalValidationIssue(
                        "error",
                        "project_definition",
                        str(exc),
                        "P2P_VERTICAL_DEFINITION_INVALID",
                    )
                ],
            )
        return ProjectDefinitionView(
            exists=True,
            valid=not any(issue.severity == "error" for issue in issues),
            path=display_path,
            state=state,
            issues=issues,
        )

    def apply_definition_patch(self, patch_path: Path) -> ProjectDefinitionPatchResult:
        patch = self._read_definition_patch(patch_path)
        preview = self.preview_definition_patch(patch_path, actor=patch.actor)
        result = self.apply_definition_patch_previewed(
            patch_path,
            preview_token=preview.preview_token,
            actor=patch.actor,
            confirm=True,
        )
        if result.status != "applied":
            raise ValueError(result.message or f"Project definition update failed: {result.status}")
        path = self._definition_state_path()
        return ProjectDefinitionPatchResult(
            state=self._read_definition_state(path),
            path=relative_to_root(path, self.root),
            operations_applied=len(patch.operations),
        )

    def preview_definition_patch(self, patch_path: Path, *, actor: str) -> MutationPreview:
        patch = self._read_definition_patch(patch_path)
        if patch.actor != actor:
            raise ValueError("Project definition patch actor must match the preview actor.")
        state, pack = self._definition_patch_context()
        updated = self._apply_definition_patch(state, patch, pack)
        path = self._definition_state_path()
        relative = path.relative_to(self.root).as_posix()
        current_bytes = path.read_bytes()
        candidate_payload = _definition_state_payload(updated)
        semantic_candidate = _definition_semantic_payload(candidate_payload)
        authority = self._definition_actor_authority(actor)
        changed_sections = sorted(
            {
                str(operation.get("section_id") or "")
                for operation in patch.operations
                if str(operation.get("section_id") or "")
            }
        )
        return MutationPreviewService.build(
            operation_id="project-definition-update",
            targets=(relative,),
            actor=actor,
            authority=authority,
            sources=(source_precondition(relative, current_bytes),),
            candidate_semantics={relative: semantic_candidate},
            semantic_diff={
                relative: {
                    "operations": [str(item.get("op") or "") for item in patch.operations],
                    "changed_sections": changed_sections,
                    "before_semantic_sha256": semantic_sha256(
                        _definition_semantic_payload(_definition_state_payload(state))
                    ),
                    "candidate_semantic_sha256": semantic_sha256(semantic_candidate),
                }
            },
            blockers=() if authority == "owner_confirmed" else (authority,),
        )

    def apply_definition_patch_previewed(
        self,
        patch_path: Path,
        *,
        preview_token: str,
        actor: str,
        confirm: bool,
    ) -> MutationResult:
        preview = self.preview_definition_patch(patch_path, actor=actor)
        if not confirm:
            return MutationResult(
                status="blocked",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Explicit confirmation is required for project definition updates.",
            )
        if preview.preview_token != preview_token:
            return MutationResult(
                status="stale_preview",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Project definition source or patch changed after preview.",
            )
        if not preview.apply_allowed:
            return MutationResult(
                status="blocked",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Actor is not authorized to update the project definition.",
            )
        patch = self._read_definition_patch(patch_path)
        state, pack = self._definition_patch_context()
        updated = self._apply_definition_patch(state, patch, pack)
        relative = self._definition_state_path().relative_to(self.root).as_posix()
        return self.atomic_writer.apply(
            operation_id=preview.operation_id,
            candidates={relative: yaml_dump(_definition_state_payload(updated)).encode("utf-8")},
            sources=preview.source_preconditions,
            preview_token=preview.preview_token,
            actor=actor,
        )

    def _read_definition_patch(self, patch_path: Path) -> ProjectDefinitionPatch:
        source = patch_path if patch_path.is_absolute() else self.root / patch_path
        payload = _read_yaml_mapping(source)
        return _definition_patch_from_payload(payload, target=str(source))

    def _definition_patch_context(self) -> tuple[ProjectDefinitionState, VerticalPack]:
        view = self.project_definition_view()
        if not view.exists or view.state is None:
            raise ValueError("Project definition state is missing. Select a project vertical before updating it.")
        if not view.valid:
            first = view.issues[0] if view.issues else None
            raise ValueError(
                "Project definition state is invalid"
                + (f": {first.field}: {first.message}" if first else ".")
            )
        active = self.active_vertical()
        pack = self._load_available_pack(active.vertical_id)
        return view.state, pack

    def _definition_actor_authority(self, actor: str) -> str:
        path = self.p2p_dir / "project" / "permissions.yml"
        if not path.exists():
            return "owner_required"
        payload = _read_yaml_mapping(path)
        identities = payload.get("identities")
        if not isinstance(identities, dict):
            return "owner_required"
        identity = identities.get(slugify(actor))
        return "owner_confirmed" if isinstance(identity, dict) and identity.get("role") == "owner" else "owner_required"

    def read_proposal_vertical_coverage(self, proposal_id: str) -> ProposalVerticalCoverage | None:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "vertical-coverage.yml"
        if not path.exists():
            return None
        payload = _read_yaml_mapping(path)
        validate_vertical_coverage_payload(payload, target=str(path))
        coverage = payload["vertical_coverage"]
        assert isinstance(coverage, dict)
        schema_version = int(coverage.get("schema_version") or 1)
        provenance = coverage.get("provenance") if isinstance(coverage.get("provenance"), dict) else {}
        sections = [
            ProposalVerticalCoverageSection(
                section_id=str(item.get("id") or ""),
                relevance=str(item.get("relevance") or "direct"),
                rationale=str(item.get("rationale") or ""),
                source=str(item.get("source") or "declared"),
                provenance=item.get("provenance") if isinstance(item.get("provenance"), dict) else {},
            )
            for item in coverage.get("sections", [])
            if isinstance(item, dict)
        ]
        return ProposalVerticalCoverage(
            proposal_id=str(coverage.get("proposal_id") or proposal_id),
            vertical_id=str(coverage.get("vertical_id") or ""),
            sections=sections,
            path=relative_to_root(path, self.root),
            schema_version=schema_version,
            provenance=provenance,
            authority=str(provenance.get("authority") or "legacy_declared"),
        )

    def proposal_vertical_coverage_status(self, proposal_id: str) -> ProposalVerticalCoverageStatus:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "vertical-coverage.yml"
        relative = relative_to_root(path, self.root)
        if not path.exists():
            return ProposalVerticalCoverageStatus(
                proposal_id=proposal_id,
                state="absent_legacy",
                path=relative,
                message="Proposal has no declared vertical coverage.",
            )
        try:
            coverage = self.read_proposal_vertical_coverage(proposal_id)
            assert coverage is not None
            self.validate_proposal_vertical_coverage_candidate(proposal_id, _read_yaml_mapping(path))
        except ValueError as exc:
            return ProposalVerticalCoverageStatus(
                proposal_id=proposal_id,
                state="invalid",
                path=relative,
                message=str(exc),
            )
        active = self.active_vertical()
        if coverage.vertical_id != active.vertical_id:
            return ProposalVerticalCoverageStatus(
                proposal_id=proposal_id,
                state="vertical_mismatch",
                path=relative,
                coverage=coverage,
                message=f"Coverage vertical `{coverage.vertical_id}` differs from active `{active.vertical_id}`.",
            )
        return ProposalVerticalCoverageStatus(
            proposal_id=proposal_id,
            state="valid",
            path=relative,
            coverage=coverage,
        )

    def validate_proposal_vertical_coverage_candidate(
        self,
        proposal_id: str,
        payload: dict[str, object],
    ) -> None:
        validate_vertical_coverage_payload(payload, target=f"vertical coverage for {proposal_id}")
        coverage = payload["vertical_coverage"]
        assert isinstance(coverage, dict)
        if str(coverage.get("proposal_id") or "") != proposal_id:
            raise ValueError("Vertical coverage proposal_id does not match the target proposal.")
        vertical_id = str(coverage.get("vertical_id") or "")
        active = self.active_vertical()
        if vertical_id != active.vertical_id:
            raise ValueError(
                f"Vertical coverage must target active vertical `{active.vertical_id}`, not `{vertical_id}`."
            )
        pack = self._load_available_pack(vertical_id)
        valid_sections = {section.section_id for section in pack.sections}
        seen: set[str] = set()
        for item in coverage.get("sections", []):
            assert isinstance(item, dict)
            section_id = str(item.get("id") or "")
            if section_id not in valid_sections:
                raise ValueError(f"Unknown vertical section `{section_id}` for `{vertical_id}`.")
            if section_id in seen:
                raise ValueError(f"Duplicate vertical coverage section `{section_id}`.")
            seen.add(section_id)
        if not seen:
            raise ValueError("Vertical coverage must declare at least one reviewed section.")

    def suggest_proposal_vertical_coverage(self, proposal_id: str) -> ProposalVerticalCoverageSuggestion:
        proposal_dir = self.find_proposal_dir(proposal_id)
        active = self.active_vertical()
        pack = self._load_available_pack(active.vertical_id)
        source_weights = {
            "proposal.md": 3.0,
            "decision.md": 2.5,
            "suggested-scope.md": 2.0,
            "findings.md": 1.75,
            "execution-plan.md": 1.5,
        }
        source_texts: dict[str, str] = {}
        for filename in source_weights:
            path = proposal_dir / filename
            if path.exists():
                source_texts[filename] = path.read_text(encoding="utf-8").lower()
        terms_by_section = {
            section.section_id: _vertical_section_terms(section, pack)
            for section in pack.sections
        }
        term_frequency: dict[str, int] = {}
        for terms in terms_by_section.values():
            for term in terms:
                term_frequency[term] = term_frequency.get(term, 0) + 1
        candidates: list[VerticalCoverageSuggestionSection] = []
        suppressed: list[str] = []
        for section in pack.sections:
            evidence: list[dict[str, object]] = []
            score = 0.0
            for term in sorted(terms_by_section[section.section_id]):
                frequency = term_frequency.get(term, 1)
                if frequency > max(2, int(len(pack.sections) * 0.35)):
                    continue
                pattern = re.compile(r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])")
                for filename, text in source_texts.items():
                    count = len(pattern.findall(text))
                    if not count:
                        continue
                    phrase_bonus = 2.5 if " " in term else 1.0
                    weight = source_weights[filename] * phrase_bonus / frequency
                    contribution = min(count, 3) * weight
                    score += contribution
                    evidence.append(
                        {"path": (proposal_dir / filename).relative_to(self.root), "term": term, "matches": count, "weight": round(contribution, 3)}
                    )
            confidence = round(min(0.99, score / (score + 8.0)), 3) if score else 0.0
            phrase_evidence = any(" " in str(item.get("term") or "") for item in evidence)
            if confidence >= 0.55 and (phrase_evidence or len(evidence) >= 2):
                candidates.append(
                    VerticalCoverageSuggestionSection(
                        section_id=section.section_id,
                        confidence=confidence,
                        evidence=sorted(evidence, key=lambda item: (-float(item["weight"]), str(item["path"]), str(item["term"]))),
                        reasons=["section_specific_evidence", "heuristic_only_requires_review"],
                    )
                )
            else:
                suppressed.append(section.section_id)
        return ProposalVerticalCoverageSuggestion(
            proposal_id=proposal_id,
            vertical_id=active.vertical_id,
            policy_version=1,
            candidates=sorted(candidates, key=lambda item: (-item.confidence, item.section_id)),
            suppressed_sections=sorted(suppressed),
            source_paths=[relative_to_root(proposal_dir / name, self.root) for name in sorted(source_texts)],
        )

    def project_readiness_review(self, *, vertical_id: str | None = None) -> ProjectReadinessReview:
        active = self.active_vertical()
        pack = self._load_available_pack(vertical_id or active.vertical_id)
        fallback_used = active.fallback_used and vertical_id is None
        proposal_matches: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        heuristic_matches: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        proposal_statuses: dict[str, str] = {}
        mapped_proposals: set[str] = set()
        unmapped: list[str] = []

        for proposal in self.proposal_summaries():
            proposal_statuses[proposal.proposal_id] = proposal.status
            coverage = self.read_proposal_vertical_coverage(proposal.proposal_id)
            mapped_sections = (
                [section.section_id for section in coverage.sections]
                if coverage and coverage.vertical_id == pack.vertical_id
                else []
            )
            heuristic_sections = self._heuristic_sections_for_proposal(proposal, pack)
            for section_id in heuristic_sections:
                heuristic_matches.setdefault(section_id, []).append(proposal.proposal_id)
            if mapped_sections:
                mapped_proposals.add(proposal.proposal_id)
                for section_id in mapped_sections:
                    proposal_matches.setdefault(section_id, []).append(proposal.proposal_id)
            else:
                unmapped.append(proposal.proposal_id)

        section_reviews: list[VerticalSectionReview] = []
        missing_capisaldi: list[str] = []
        generated_questions: list[str] = []
        definition_view = self.project_definition_view()
        definition_sections = {
            item.section_id: item.status
            for item in definition_view.state.sections
        } if definition_view.valid and definition_view.state is not None else {}
        for section in sorted(pack.sections, key=lambda item: item.priority):
            proposals = sorted(dict.fromkeys(proposal_matches.get(section.section_id, [])))
            heuristic_proposals = sorted(dict.fromkeys(heuristic_matches.get(section.section_id, [])))
            definition_status = definition_sections.get(section.section_id, "not_initialized")
            if proposals:
                accepted = [
                    proposal_id for proposal_id in proposals
                    if is_active_project_projection(proposal_statuses.get(proposal_id, ""))
                ]
                status = "covered" if accepted else "partial"
            elif definition_status == "complete":
                status = "defined"
            elif definition_status == "not_applicable":
                status = "not_applicable"
            elif section.required:
                status = "missing"
            else:
                status = "not_applicable"
            gaps = []
            questions = []
            if not proposals and section.required and definition_status != "not_applicable":
                gaps.append("missing_proposal_coverage")
            if status == "partial":
                gaps.append("proposal_coverage_not_accepted")
            if section.required and definition_status not in {"complete", "not_applicable"}:
                gaps.append("project_definition_incomplete")
                missing_capisaldi.append(section.section_id)
                questions = [
                    question.question
                    for question in pack.questions
                    if question.section_id == section.section_id
                ][:3]
                generated_questions.extend(questions)
            section_reviews.append(
                VerticalSectionReview(
                    section_id=section.section_id,
                    title=section.title,
                    status=status,
                    proposals=proposals,
                    gaps=gaps,
                    risks=[],
                    questions=questions,
                    declared_proposals=proposals,
                    heuristic_proposals=heuristic_proposals,
                    definition_status=definition_status,
                )
            )

        suggested = []
        if fallback_used:
            suggested.append('p2p project vertical propose "<project idea>"')
        if missing_capisaldi:
            suggested.append("Complete project definition for missing vertical capisaldi.")
        if any(section.status == "defined" for section in section_reviews):
            suggested.append("Review whether definition-only sections need declared proposal evidence.")
        suggested.append("p2p project readiness review")
        return ProjectReadinessReview(
            active_vertical_id=pack.vertical_id,
            vertical_source=pack.source if not fallback_used else FALLBACK_SOURCE,
            fallback_used=fallback_used,
            sections=section_reviews,
            unmapped_proposals=sorted(unmapped),
            missing_capisaldi=missing_capisaldi,
            generated_questions=list(dict.fromkeys(generated_questions)),
            suggested_next=list(dict.fromkeys(suggested)),
            definition_valid=definition_view.valid,
            heuristic_mappings={
                section_id: sorted(dict.fromkeys(proposal_ids))
                for section_id, proposal_ids in heuristic_matches.items()
                if proposal_ids
            },
        )

    def validation_findings(self) -> list[tuple[str, str, Path, str, str]]:
        findings: list[tuple[str, str, Path, str, str]] = []
        for pack_path in sorted(self._project_vertical_pack_paths(self._project_verticals_dir())):
            try:
                pack = self._load_pack_from_path(pack_path.parent if pack_path.name == "manifest.yml" else pack_path)
                validate_vertical_pack_payload(_pack_payload(pack), target=str(pack_path))
            except ValueError as exc:
                findings.append(
                    (
                        "P2P250_INVALID_PROJECT_VERTICAL",
                        "error",
                        pack_path,
                        str(exc),
                        "p2p project vertical validate " + str(relative_to_root(pack_path, self.root)),
                    )
                )
        state_path = self._active_vertical_path()
        if state_path.exists():
            try:
                payload = _read_yaml_mapping(state_path)
                state = payload.get("project_vertical")
                if not isinstance(state, dict):
                    raise ValueError(f"Invalid project vertical state: {state_path}")
                vertical_id = str(state.get("active_vertical_id") or "").strip()
                if not vertical_id:
                    raise ValueError(f"Invalid project vertical state: missing active_vertical_id in {state_path}")
                self._load_available_pack(vertical_id)
            except ValueError as exc:
                findings.append(
                    (
                        "P2P251_INVALID_ACTIVE_VERTICAL",
                        "error",
                        state_path,
                        str(exc),
                        "p2p project vertical list",
                    )
                )
            lock_status = self.vertical_lock_status()
            if lock_status.status == "missing":
                findings.append(
                    (
                        "P2P253_PROJECT_VERTICAL_LOCK_MISSING",
                        "warning",
                        self._vertical_lock_path(),
                        lock_status.message,
                        lock_status.suggested_command,
                    )
                )
            elif lock_status.status != "valid":
                findings.append(
                    (
                        "P2P254_PROJECT_VERTICAL_LOCK_INVALID",
                        "error",
                        self._vertical_lock_path(),
                        lock_status.message,
                        lock_status.suggested_command,
                    )
                )
        definition = self.project_definition_view()
        if definition.exists and not definition.valid:
            for issue in definition.issues:
                findings.append(
                    (
                        issue.code or "P2P255_PROJECT_DEFINITION_INVALID",
                        issue.severity,
                        self._definition_state_path(),
                        issue.message,
                        "p2p project definition show",
                    )
                )
        for coverage_path in sorted(self.p2p_dir.glob("proposals/*/vertical-coverage.yml")):
            try:
                payload = _read_yaml_mapping(coverage_path)
                validate_vertical_coverage_payload(payload, target=str(coverage_path))
                self._validate_coverage_sections(payload, coverage_path)
            except ValueError as exc:
                findings.append(
                    (
                        "P2P252_INVALID_PROPOSAL_VERTICAL_COVERAGE",
                        "error",
                        coverage_path,
                        str(exc),
                        "",
                    )
                )
        return findings

    def _validate_coverage_sections(self, payload: dict[str, object], path: Path) -> None:
        coverage = payload.get("vertical_coverage")
        if not isinstance(coverage, dict):
            return
        vertical_id = str(coverage.get("vertical_id") or "")
        pack = self._load_available_pack(vertical_id)
        section_ids = {section.section_id for section in pack.sections}
        for item in coverage.get("sections", []):
            if isinstance(item, dict):
                section_id = str(item.get("id") or "")
                if section_id not in section_ids:
                    raise ValueError(f"Invalid proposal vertical coverage {path}: unknown section id `{section_id}` for vertical `{vertical_id}`.")

    def _extension_issues(self, pack: VerticalPack) -> list[VerticalValidationIssue]:
        if not pack.extends:
            return []
        if pack.extends in self._available_packs_by_id():
            return []
        return [
            VerticalValidationIssue(
                severity="error",
                field="vertical.extends",
                message=f"unknown base vertical `{pack.extends}`",
            )
        ]

    def _heuristic_sections_for_proposal(self, proposal: _ProposalSummaryLike, pack: VerticalPack) -> list[str]:
        base_section_ids: set[str] = set()
        if pack.extends:
            base = self._load_available_pack(pack.extends)
            base_section_ids = {section.section_id for section in base.sections}
        proposal_dir = self.find_proposal_dir(proposal.proposal_id)
        text = (
            _read_optional(proposal_dir / "proposal.md")
            + "\n"
            + _read_optional(proposal_dir / "decision.md")
            + "\n"
            + _read_optional(proposal_dir / "suggested-scope.md")
            + "\n"
            + _read_optional(proposal_dir / "risks.md")
        ).lower()
        mapped: list[str] = []
        for section in pack.sections:
            if section.section_id in base_section_ids:
                continue
            terms = {section.section_id.replace("_", " "), section.title.lower()}
            terms.update(_important_words(section.title))
            terms.update(_important_words(section.purpose))
            for rubric in pack.rubrics:
                if rubric.section_id == section.section_id:
                    terms.update(keyword.lower() for keyword in rubric.keywords)
            if any(term and term in text for term in terms):
                mapped.append(section.section_id)
        return mapped

    def _available_packs_by_id(self) -> dict[str, VerticalPack]:
        packs: dict[str, VerticalPack] = {}
        for pack in self._internal_packs():
            packs[pack.vertical_id] = pack
        for pack in self._installed_user_packs():
            packs[pack.vertical_id] = pack
        for pack in self._installed_p2p_home_packs():
            packs[pack.vertical_id] = pack
        for pack in self._project_local_packs():
            packs[pack.vertical_id] = pack
        return packs

    def _load_available_pack(self, vertical_id: str) -> VerticalPack:
        normalized = _normalize_vertical_id(vertical_id)
        packs = self._available_packs_by_id()
        if normalized in packs:
            return _compose_pack(packs[normalized], packs)
        raise ValueError(f"Unknown project vertical `{vertical_id}`. Run `p2p project vertical list`.")

    def _resolve_available_pack(self, vertical_id: str) -> ResolvedVerticalPack:
        pack = self._load_available_pack(vertical_id)
        source = _source_from_pack(pack, self.root)
        checksum = _pack_checksum(pack)
        return ResolvedVerticalPack(pack=pack, source=source, checksum=checksum)

    def _load_target(self, target: str) -> VerticalPack:
        path = Path(target)
        if path.exists():
            return self._load_pack_from_path(path, source=EXPLICIT_SOURCE)
        return self._load_available_pack(target)

    def _load_target_for_validation(self, target: str) -> tuple[VerticalPack, dict[str, object]]:
        path = Path(target)
        if path.exists():
            source = path if path.is_absolute() else self.root / path
            if source.is_dir() and (source / "manifest.yml").exists():
                payload = self._canonical_pack_payload(source)
                pack_path = source / "manifest.yml"
            else:
                pack_path = source / "vertical.yml" if source.is_dir() else source
                if not pack_path.exists():
                    raise ValueError(f"Vertical pack not found: {source}. Expected a vertical.yml file or pack directory.")
                payload = _read_yaml_mapping(pack_path)
            return _pack_from_payload(payload, source=EXPLICIT_SOURCE, path=pack_path), payload
        pack = self._load_available_pack(target)
        return pack, _pack_payload(pack)

    def _load_pack_from_path(self, pack_source: Path, *, source: str = PROJECT_LOCAL_SOURCE) -> VerticalPack:
        if not pack_source.is_absolute():
            pack_source = self.root / pack_source
        if pack_source.is_dir() and (pack_source / "manifest.yml").exists():
            payload = self._canonical_pack_payload(pack_source)
            path = pack_source / "manifest.yml"
        else:
            vertical_path = pack_source / "vertical.yml" if pack_source.is_dir() else pack_source
            if not vertical_path.exists():
                raise ValueError(f"Vertical pack not found: {pack_source}. Expected a vertical.yml file or pack directory.")
            payload = _read_yaml_mapping(vertical_path)
            path = vertical_path
        validate_vertical_pack_payload(payload, target=str(path))
        return _pack_from_payload(payload, source=source, path=path)

    def _project_local_packs(self) -> list[VerticalPack]:
        return self._packs_from_root(self._project_verticals_dir(), source=PROJECT_LOCAL_SOURCE)

    def _installed_p2p_home_packs(self) -> list[VerticalPack]:
        value = os.environ.get("P2P_HOME", "").strip()
        if not value:
            return []
        return self._packs_from_root(Path(value) / "verticals", source=INSTALLED_P2P_HOME_SOURCE)

    def _installed_user_packs(self) -> list[VerticalPack]:
        return self._packs_from_root(Path.home() / ".p2p" / "verticals", source=INSTALLED_USER_SOURCE)

    def _packs_from_root(self, root: Path, *, source: str) -> list[VerticalPack]:
        packs: list[VerticalPack] = []
        if not root.exists():
            return packs
        for pack_path in self._project_vertical_pack_paths(root):
            try:
                load_path = pack_path.parent if pack_path.name == "manifest.yml" else pack_path
                packs.append(self._load_pack_from_path(load_path, source=source))
            except ValueError:
                continue
        return packs

    def _project_vertical_pack_paths(self, root: Path) -> list[Path]:
        if not root.exists():
            return []
        paths: list[Path] = []
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            manifest = child / "manifest.yml"
            vertical = child / "vertical.yml"
            if manifest.exists():
                paths.append(manifest)
            elif vertical.exists():
                paths.append(vertical)
        return paths

    def _internal_packs(self) -> list[VerticalPack]:
        packs: list[VerticalPack] = []
        root = resources.files("p2p_engine.resources.verticals")
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            manifest = child / "manifest.yml"
            vertical = child / "vertical.yml"
            if manifest.is_file():
                payload = self._canonical_pack_payload(Path(str(child)))
                path = Path(str(manifest))
            elif vertical.is_file():
                payload = yaml.safe_load(vertical.read_text(encoding="utf-8"))
                path = Path(str(vertical))
            else:
                continue
            if not isinstance(payload, dict):
                continue
            validate_vertical_pack_payload(payload, target=child.name)
            packs.append(_pack_from_payload(payload, source=INTERNAL_SOURCE, path=path))
        return packs

    def _canonical_pack_payload(self, pack_root: Path) -> dict[str, object]:
        manifest = _unwrap_mapping(_read_yaml_mapping(pack_root / "manifest.yml"), "manifest")
        vertical = _unwrap_mapping(_read_yaml_mapping(pack_root / "vertical.yml"), "vertical")
        sections = [_unwrap_mapping(_read_yaml_mapping(path), "section") for path in sorted((pack_root / "sections").glob("*.yml"))]
        rubrics_payload = _read_yaml_mapping(pack_root / "rubrics.yml") if (pack_root / "rubrics.yml").exists() else {}
        rubrics = _unwrap_list(rubrics_payload, "rubrics")
        artifacts = _mapping_list(vertical.get("artifacts"))
        artifacts_dir = pack_root / "artifacts"
        if artifacts_dir.exists():
            artifacts.extend(_unwrap_mapping(_read_yaml_mapping(path), "artifact") for path in sorted(artifacts_dir.glob("*.yml")))
        profile_specs: list[dict[str, object]] = []
        profiles_dir = pack_root / "profiles"
        if profiles_dir.exists():
            profile_specs = [_unwrap_mapping(_read_yaml_mapping(path), "profile") for path in sorted(profiles_dir.glob("*.yml"))]
        module_specs: list[dict[str, object]] = []
        modules_dir = pack_root / "modules"
        if modules_dir.exists():
            module_specs = [_unwrap_mapping(_read_yaml_mapping(path), "module") for path in sorted(modules_dir.glob("*.yml"))]
        examples = [path.name for path in sorted((pack_root / "examples").glob("*")) if path.is_file()]
        vertical = dict(vertical)
        vertical["schema_version"] = vertical.get("schema_version") or manifest.get("schema_version") or VERTICAL_SCHEMA_VERSION
        vertical["id"] = vertical.get("id") or manifest.get("id")
        vertical["name"] = vertical.get("name") or manifest.get("name")
        vertical["version"] = vertical.get("version") or manifest.get("version")
        vertical["sections"] = sections or _mapping_list(vertical.get("sections"))
        vertical["rubrics"] = rubrics or _mapping_list(vertical.get("rubrics"))
        vertical["artifacts"] = artifacts
        vertical["profiles"] = list(
            dict.fromkeys(
                [
                    *([str(item) for item in vertical.get("profiles", [])] if isinstance(vertical.get("profiles"), list) else []),
                    *[str(item.get("id") or item.get("profile_id") or "") for item in profile_specs],
                ]
            )
        )
        vertical["modules"] = list(
            dict.fromkeys(
                [
                    *([str(item) for item in vertical.get("modules", [])] if isinstance(vertical.get("modules"), list) else []),
                    *[str(item.get("id") or item.get("module_id") or "") for item in module_specs],
                ]
            )
        )
        vertical["examples"] = list(
            dict.fromkeys(
                [
                    *([str(item) for item in vertical.get("examples", [])] if isinstance(vertical.get("examples"), list) else []),
                    *examples,
                ]
            )
        )
        vertical["manifest"] = manifest
        vertical["profile_specs"] = profile_specs
        vertical["module_specs"] = module_specs
        return {"vertical": vertical}

    def _project_verticals_dir(self) -> Path:
        return self.p2p_dir / "project" / "verticals"

    def _active_vertical_path(self) -> Path:
        return self.p2p_dir / "project" / "vertical.yml"

    def _vertical_lock_path(self) -> Path:
        return self.p2p_dir / "project" / "vertical.lock.yml"

    def _definition_state_path(self) -> Path:
        return self.p2p_dir / "project" / "definition.yml"

    def _write_vertical_lock(self, resolved: ResolvedVerticalPack, *, actor: str) -> VerticalLock:
        path = self._vertical_lock_path()
        lock = VerticalLock(
            vertical_id=resolved.pack.vertical_id,
            name=resolved.pack.name,
            version=resolved.pack.version,
            pack_schema_version=resolved.pack.schema_version,
            source=resolved.source,
            checksum=resolved.checksum,
            compatibility=resolved.pack.compatibility,
            selected_at=date.today().isoformat(),
            selected_by=actor,
            trust={"signed": False},
            path=relative_to_root(path, self.root),
        )
        write_yaml_atomic(path, _vertical_lock_payload(lock))
        return lock

    def _read_vertical_lock(self, path: Path) -> VerticalLock:
        payload = _read_yaml_mapping(path)
        lock = payload.get("project_vertical_lock")
        if not isinstance(lock, dict):
            raise ValueError(f"Invalid project vertical lock: expected project_vertical_lock mapping in {path}")
        source_payload = lock.get("source")
        if not isinstance(source_payload, dict):
            raise ValueError(f"Invalid project vertical lock: missing source mapping in {path}")
        checksum_payload = lock.get("checksum")
        if not isinstance(checksum_payload, dict):
            raise ValueError(f"Invalid project vertical lock: missing checksum mapping in {path}")
        vertical_id = str(lock.get("vertical_id") or "").strip()
        checksum = str(checksum_payload.get("value") or "").strip()
        if not vertical_id:
            raise ValueError(f"Invalid project vertical lock: missing vertical_id in {path}")
        if not checksum:
            raise ValueError(f"Invalid project vertical lock: missing checksum.value in {path}")
        return VerticalLock(
            vertical_id=vertical_id,
            name=str(lock.get("name") or vertical_id),
            version=str(lock.get("version") or ""),
            pack_schema_version=int(lock.get("pack_schema_version") or VERTICAL_SCHEMA_VERSION),
            source=VerticalPackSource(
                source_type=str(source_payload.get("type") or "unknown"),
                resolved_from=str(source_payload.get("resolved_from") or ""),
                path=Path(str(source_payload["path"])) if source_payload.get("path") else None,
                package=str(source_payload.get("package") or ""),
            ),
            checksum=checksum,
            compatibility=lock.get("compatibility") if isinstance(lock.get("compatibility"), dict) else {},
            selected_at=str((lock.get("selected") or {}).get("at") if isinstance(lock.get("selected"), dict) else ""),
            selected_by=str((lock.get("selected") or {}).get("by") if isinstance(lock.get("selected"), dict) else ""),
            trust=lock.get("trust") if isinstance(lock.get("trust"), dict) else {},
            path=relative_to_root(path, self.root),
        )

    def _write_initial_definition_state(
        self,
        resolved: ResolvedVerticalPack,
        *,
        profile: str,
        modules: list[str],
        actor: str,
    ) -> ProjectDefinitionState:
        state = self._initial_definition_state(resolved, profile=profile, modules=modules, actor=actor)
        path = self._definition_state_path()
        write_yaml_atomic(path, _definition_state_payload(state))
        return self._read_definition_state(path)

    def _initial_definition_state(
        self,
        resolved: ResolvedVerticalPack,
        *,
        profile: str,
        modules: list[str],
        actor: str,
        audit_date: str | None = None,
    ) -> ProjectDefinitionState:
        sections: list[ProjectDefinitionSectionState] = []
        for section in sorted(resolved.pack.sections, key=lambda item: item.priority):
            fields = _section_fields(section, resolved.pack)
            missing = [field.field_id for field in fields if field.required]
            questions = [
                ProjectDefinitionQuestion(
                    question_id=question.question_id,
                    field_id=_field_id_for_question(section, question),
                    question=question.question,
                )
                for question in resolved.pack.questions
                if question.section_id == section.section_id
            ]
            sections.append(
                ProjectDefinitionSectionState(
                    section_id=section.section_id,
                    status="missing" if section.required else "not_applicable",
                    missing_required_fields=missing,
                    open_questions=questions,
                )
            )
        next_action: dict[str, object] = {}
        for section in sections:
            if section.open_questions:
                question = section.open_questions[0]
                next_action = {
                    "kind": "ask_question",
                    "section_id": section.section_id,
                    "question_id": question.question_id,
                    "question": question.question,
                }
                break
        return ProjectDefinitionState(
            schema_version=PROJECT_DEFINITION_SCHEMA_VERSION,
            vertical_id=resolved.pack.vertical_id,
            vertical_version=resolved.pack.version,
            profile=profile or "default",
            modules=list(dict.fromkeys(modules)),
            lock_checksum=resolved.checksum,
            sections=sections,
            next_suggested_action=next_action,
            history=[
                ProjectDefinitionHistoryEntry(
                    at=audit_date or date.today().isoformat(),
                    actor=actor,
                    operation="initialize_definition_state",
                )
            ],
            path=relative_to_root(self._definition_state_path(), self.root),
        )

    def _read_definition_state(self, path: Path) -> ProjectDefinitionState:
        payload = _read_yaml_mapping(path)
        return _definition_state_from_payload(payload, path=relative_to_root(path, self.root))

    def _definition_state_issues(
        self,
        state: ProjectDefinitionState,
        pack: VerticalPack,
    ) -> list[VerticalValidationIssue]:
        issues: list[VerticalValidationIssue] = []
        section_ids = {section.section_id for section in pack.sections}
        field_ids_by_section = {section.section_id: {field.field_id for field in _section_fields(section, pack)} for section in pack.sections}
        if state.vertical_id != pack.vertical_id:
            issues.append(
                VerticalValidationIssue(
                    "error",
                    "project_definition.vertical_id",
                    f"definition vertical `{state.vertical_id}` does not match active vertical `{pack.vertical_id}`",
                    "P2P255_PROJECT_DEFINITION_INVALID",
                )
            )
        for section in state.sections:
            if section.section_id not in section_ids:
                issues.append(
                    VerticalValidationIssue(
                        "error",
                        f"sections.{section.section_id}",
                        f"unknown section `{section.section_id}`",
                        "P2P255_PROJECT_DEFINITION_INVALID",
                    )
                )
                continue
            if section.status not in PROJECT_DEFINITION_STATUSES:
                issues.append(
                    VerticalValidationIssue(
                        "error",
                        f"sections.{section.section_id}.status",
                        f"invalid status `{section.status}`",
                        "P2P255_PROJECT_DEFINITION_INVALID",
                    )
                )
            known_fields = field_ids_by_section[section.section_id]
            for field_id in [*section.fields.keys(), *section.missing_required_fields]:
                if field_id not in known_fields:
                    issues.append(
                        VerticalValidationIssue(
                            "error",
                            f"sections.{section.section_id}.fields.{field_id}",
                            f"unknown field `{field_id}`",
                            "P2P255_PROJECT_DEFINITION_INVALID",
                        )
                    )
            for assumption in section.assumptions:
                if assumption.status not in ASSUMPTION_STATUSES:
                    issues.append(
                        VerticalValidationIssue(
                            "error",
                            f"sections.{section.section_id}.assumptions.{assumption.assumption_id}",
                            f"invalid assumption status `{assumption.status}`",
                            "P2P255_PROJECT_DEFINITION_INVALID",
                        )
                    )
            if section.status == "complete" and section.missing_required_fields:
                pack_section = next(item for item in pack.sections if item.section_id == section.section_id)
                policy = pack_section.completion_policy or VerticalCompletionPolicy()
                if not policy.allow_assumed_completion:
                    issues.append(
                        VerticalValidationIssue(
                            "error",
                            f"sections.{section.section_id}.status",
                            "cannot mark section complete while required fields are missing",
                            "P2P255_PROJECT_DEFINITION_INVALID",
                        )
                    )
        return issues

    def _apply_definition_patch(
        self,
        state: ProjectDefinitionState,
        patch: ProjectDefinitionPatch,
        pack: VerticalPack,
    ) -> ProjectDefinitionState:
        sections = {section.section_id: _copy_section_state(section) for section in state.sections}
        pack_sections = {section.section_id: section for section in pack.sections}
        field_ids_by_section = {section.section_id: {field.field_id for field in _section_fields(section, pack)} for section in pack.sections}
        history = list(state.history)
        for operation in patch.operations:
            op = str(operation.get("op") or "").strip()
            section_id = str(operation.get("section_id") or "").strip()
            if op not in {
                "set_field",
                "clear_field",
                "set_section_status",
                "set_missing_required_fields",
                "add_assumption",
                "update_assumption_status",
                "add_open_question",
                "close_open_question",
                "add_blocker",
                "clear_blocker",
                "set_next_suggested_action",
            }:
                raise ValueError(f"Unsupported project definition patch operation `{op}`.")
            if op == "set_next_suggested_action":
                continue
            if section_id not in sections or section_id not in pack_sections:
                raise ValueError(f"Unknown project definition section `{section_id}`.")
            section = sections[section_id]
            known_fields = field_ids_by_section[section_id]
            if op == "set_field":
                field_id = str(operation.get("field_id") or "").strip()
                if field_id not in known_fields:
                    raise ValueError(f"Unknown field `{field_id}` for section `{section_id}`.")
                provenance = operation.get("provenance") if isinstance(operation.get("provenance"), dict) else {}
                source = str(provenance.get("source") or "patch")
                if _contains_path_escape(source):
                    raise ValueError("Unsafe provenance source in project definition patch.")
                section.fields[field_id] = ProjectDefinitionFieldValue(
                    field_id=field_id,
                    value=operation.get("value"),
                    source=source,
                    updated_at=date.today().isoformat(),
                )
                section.missing_required_fields = [item for item in section.missing_required_fields if item != field_id]
                if section.status == "missing":
                    section.status = "partial"
            elif op == "clear_field":
                field_id = str(operation.get("field_id") or "").strip()
                if field_id not in known_fields:
                    raise ValueError(f"Unknown field `{field_id}` for section `{section_id}`.")
                section.fields.pop(field_id, None)
                field = next(item for item in _section_fields(pack_sections[section_id], pack) if item.field_id == field_id)
                if field.required and field_id not in section.missing_required_fields:
                    section.missing_required_fields.append(field_id)
            elif op == "set_section_status":
                status = str(operation.get("status") or "").strip()
                if status not in PROJECT_DEFINITION_STATUSES:
                    raise ValueError(f"Invalid project definition section status `{status}`.")
                policy = pack_sections[section_id].completion_policy or VerticalCompletionPolicy()
                if status == "complete" and section.missing_required_fields and not policy.allow_assumed_completion:
                    raise ValueError(f"Cannot mark section `{section_id}` complete while required fields are missing.")
                section.status = status
            elif op == "set_missing_required_fields":
                values = operation.get("field_ids")
                if not isinstance(values, list):
                    raise ValueError("set_missing_required_fields requires field_ids list.")
                field_ids = [str(item).strip() for item in values if str(item).strip()]
                unknown = [field_id for field_id in field_ids if field_id not in known_fields]
                if unknown:
                    raise ValueError(f"Unknown required field `{unknown[0]}` for section `{section_id}`.")
                section.missing_required_fields = field_ids
            elif op == "add_assumption":
                status = str(operation.get("status") or "to_validate")
                if status not in ASSUMPTION_STATUSES:
                    raise ValueError(f"Invalid assumption status `{status}`.")
                text = str(operation.get("text") or "").strip()
                if not text:
                    raise ValueError("add_assumption requires text.")
                section.assumptions.append(
                    ProjectDefinitionAssumption(
                        assumption_id=f"A{len(section.assumptions) + 1:03d}",
                        text=text,
                        status=status,
                        field_id=str(operation.get("field_id") or ""),
                    )
                )
            elif op == "update_assumption_status":
                assumption_id = str(operation.get("assumption_id") or "").strip()
                status = str(operation.get("status") or "").strip()
                if status not in ASSUMPTION_STATUSES:
                    raise ValueError(f"Invalid assumption status `{status}`.")
                updated = False
                for index, assumption in enumerate(section.assumptions):
                    if assumption.assumption_id == assumption_id:
                        section.assumptions[index] = ProjectDefinitionAssumption(
                            assumption_id=assumption.assumption_id,
                            text=assumption.text,
                            status=status,
                            field_id=assumption.field_id,
                        )
                        updated = True
                        break
                if not updated:
                    raise ValueError(f"Unknown assumption `{assumption_id}` in section `{section_id}`.")
            elif op == "add_open_question":
                question = str(operation.get("question") or "").strip()
                if not question:
                    raise ValueError("add_open_question requires question.")
                field_id = str(operation.get("field_id") or "").strip()
                if field_id and field_id not in known_fields:
                    raise ValueError(f"Unknown field `{field_id}` for section `{section_id}`.")
                section.open_questions.append(
                    ProjectDefinitionQuestion(
                        question_id=f"Q{len(section.open_questions) + 1:03d}",
                        field_id=field_id,
                        question=question,
                    )
                )
            elif op == "close_open_question":
                question_id = str(operation.get("question_id") or "").strip()
                before = len(section.open_questions)
                section.open_questions = [item for item in section.open_questions if item.question_id != question_id]
                if len(section.open_questions) == before:
                    raise ValueError(f"Unknown open question `{question_id}` in section `{section_id}`.")
            elif op == "add_blocker":
                text = str(operation.get("text") or "").strip()
                if not text:
                    raise ValueError("add_blocker requires text.")
                section.blockers.append(ProjectDefinitionBlocker(blocker_id=f"B{len(section.blockers) + 1:03d}", text=text))
                section.status = "blocked"
            elif op == "clear_blocker":
                blocker_id = str(operation.get("blocker_id") or "").strip()
                before = len(section.blockers)
                section.blockers = [item for item in section.blockers if item.blocker_id != blocker_id]
                if len(section.blockers) == before:
                    raise ValueError(f"Unknown blocker `{blocker_id}` in section `{section_id}`.")
            history.append(
                ProjectDefinitionHistoryEntry(
                    at=date.today().isoformat(),
                    actor=patch.actor,
                    operation=op,
                    section_id=section_id,
                )
            )
        next_action = state.next_suggested_action
        for operation in patch.operations:
            if str(operation.get("op") or "") == "set_next_suggested_action":
                value = operation.get("value")
                if not isinstance(value, dict):
                    raise ValueError("set_next_suggested_action requires value mapping.")
                next_action = value
                history.append(
                    ProjectDefinitionHistoryEntry(
                        at=date.today().isoformat(),
                        actor=patch.actor,
                        operation="set_next_suggested_action",
                    )
                )
        updated = ProjectDefinitionState(
            schema_version=state.schema_version,
            vertical_id=state.vertical_id,
            vertical_version=state.vertical_version,
            profile=state.profile,
            modules=state.modules,
            lock_checksum=state.lock_checksum,
            sections=[sections[section.section_id] for section in state.sections],
            next_suggested_action=next_action,
            history=history,
            path=state.path,
        )
        issues = self._definition_state_issues(updated, pack)
        errors = [issue for issue in issues if issue.severity == "error"]
        if errors:
            first = errors[0]
            raise ValueError(f"Invalid project definition patch result: {first.field}: {first.message}")
        return updated

    def _rubric_summary(self) -> dict[str, object]:
        path = self.p2p_dir / "project" / "rubrics.yml"
        if not path.exists():
            return {"exists": False}
        payload = _read_yaml_mapping(path)
        criteria = payload.get("criteria")
        if not isinstance(criteria, list):
            criteria = []
        enabled = [item for item in criteria if isinstance(item, dict) and item.get("enabled") is not False]
        disabled = [item for item in criteria if isinstance(item, dict) and item.get("enabled") is False]
        return {
            "exists": True,
            "domain": str(payload.get("domain") or ""),
            "status": str(payload.get("status") or ""),
            "enabled": len(enabled),
            "disabled": len(disabled),
            "total": len([item for item in criteria if isinstance(item, dict)]),
        }

    def _vertical_rubrics_payload(
        self,
        pack: VerticalPack,
        *,
        rubric_mapping: dict[str, str] | None = None,
    ) -> dict[str, object]:
        path = self.p2p_dir / "project" / "rubrics.yml"
        mapping = rubric_mapping or {}
        new_ids = {rubric.rubric_id for rubric in pack.rubrics}
        unknown_targets = sorted(set(mapping.values()) - new_ids)
        if unknown_targets:
            raise ValueError(
                f"Rubric mapping targets unknown criterion `{unknown_targets[0]}` for vertical `{pack.vertical_id}`."
            )
        existing_enabled: dict[str, bool] = {}
        existing_criteria: list[dict[str, object]] = []
        if path.exists():
            payload = _read_yaml_mapping(path)
            criteria = payload.get("criteria")
            if isinstance(criteria, list):
                existing_criteria = [item for item in criteria if isinstance(item, dict)]
                for item in existing_criteria:
                    criterion_id = str(item.get("id") or "")
                    if criterion_id:
                        target_id = mapping.get(criterion_id, criterion_id)
                        if target_id in new_ids:
                            rubric = next(item for item in pack.rubrics if item.rubric_id == target_id)
                            collision = (
                                criterion_id == target_id
                                and criterion_id not in mapping
                                and (
                                    str(item.get("title") or "").strip() not in {"", rubric.title}
                                    or str(item.get("section_id") or "").strip() not in {"", rubric.section_id}
                                )
                            )
                            if collision:
                                raise ValueError(
                                    f"Rubric `{criterion_id}` collides semantically with the selected vertical; "
                                    "provide an explicit rubric mapping."
                                )
                            existing_enabled[target_id] = item.get("enabled") is not False
        criteria_payload: list[dict[str, object]] = [
            {
                "id": rubric.rubric_id,
                "title": rubric.title,
                "enabled": existing_enabled.get(rubric.rubric_id, True),
                "required": rubric.required,
                "section_id": rubric.section_id,
                "keywords": rubric.keywords,
                "source": "project_vertical",
                "vertical_id": pack.vertical_id,
            }
            for rubric in pack.rubrics
        ]
        for item in existing_criteria:
            criterion_id = str(item.get("id") or "")
            mapped_id = mapping.get(criterion_id, criterion_id)
            if criterion_id and mapped_id not in new_ids:
                orphan = dict(item)
                orphan["orphaned"] = True
                orphan["legacy_unmapped"] = True
                orphan["counts_toward_active_baseline"] = False
                orphan["enabled"] = item.get("enabled") is not False
                criteria_payload.append(orphan)
        active_criteria = [item for item in criteria_payload if item.get("counts_toward_active_baseline") is not False]
        return {
            "version": "1.0",
            "domain": f"project_vertical:{pack.vertical_id}",
            "status": "vertical_selected",
            "template": pack.vertical_id,
            "assessment_type": "project_definition_maturity",
            "scoring": {"covered": 100, "partial": 50, "missing": 0},
            "selected_scope": {
                "enabled": sum(1 for item in active_criteria if item.get("enabled") is not False),
                "disabled": sum(1 for item in active_criteria if item.get("enabled") is False),
                "total_default": len(pack.rubrics),
            },
            "criteria": criteria_payload,
        }

    def _write_vertical_rubrics(self, pack: VerticalPack) -> None:
        write_yaml_atomic(
            self.p2p_dir / "project" / "rubrics.yml",
            self._vertical_rubrics_payload(pack),
        )

    def _definition_summary(self, definition: ProjectDefinitionView) -> dict[str, object]:
        if not definition.exists or definition.state is None:
            return {"exists": False, "valid": definition.valid}
        counts: dict[str, int] = {}
        for section in definition.state.sections:
            counts[section.status] = counts.get(section.status, 0) + 1
        missing_fields = sum(len(section.missing_required_fields) for section in definition.state.sections)
        return {
            "exists": True,
            "valid": definition.valid,
            "vertical_id": definition.state.vertical_id,
            "sections": counts,
            "missing_required_fields": missing_fields,
        }

    def _atomic_write(self, path: Path, text: str) -> None:
        write_text_atomic(path, text)


def _pack_from_payload(payload: dict[str, object], *, source: str, path: Path | None) -> VerticalPack:
    payload = _normalise_pack_payload(payload)
    vertical = payload.get("vertical")
    if not isinstance(vertical, dict):
        raise ValueError("Vertical pack must define top-level `vertical` mapping.")
    sections = [
        VerticalSection(
            section_id=str(item.get("id") or ""),
            title=str(item.get("title") or item.get("id") or ""),
            purpose=str(item.get("purpose") or ""),
            required=bool(item.get("required", True)),
            priority=int(item.get("priority") or 100),
            fields=[
                VerticalField(
                    field_id=str(field.get("id") or field.get("field_id") or ""),
                    label=str(field.get("label") or field.get("title") or field.get("id") or field.get("field_id") or ""),
                    required=bool(field.get("required", True)),
                    question=str(field.get("question") or ""),
                    assisted_answer=str(field.get("assisted_answer") or ""),
                    completion_criteria=[str(value) for value in field.get("completion_criteria", []) if str(value).strip()]
                    if isinstance(field.get("completion_criteria"), list)
                    else [],
                    common_mistakes=[str(value) for value in field.get("common_mistakes", []) if str(value).strip()]
                    if isinstance(field.get("common_mistakes"), list)
                    else [],
                    suggested_artifacts=[str(value) for value in field.get("suggested_artifacts", []) if str(value).strip()]
                    if isinstance(field.get("suggested_artifacts"), list)
                    else [],
                    maturity_gates=[str(value) for value in field.get("maturity_gates", []) if str(value).strip()]
                    if isinstance(field.get("maturity_gates"), list)
                    else [],
                )
                for field in _mapping_list(item.get("fields"))
            ],
            completion_policy=_completion_policy_from_payload(item.get("completion_policy")),
        )
        for item in _mapping_list(vertical.get("sections"))
    ]
    rubrics = [
        VerticalRubric(
            rubric_id=str(item.get("id") or ""),
            title=str(item.get("title") or item.get("id") or ""),
            section_id=str(item.get("section_id") or ""),
            required=bool(item.get("required", True)),
            keywords=[str(keyword) for keyword in item.get("keywords", []) if str(keyword).strip()]
            if isinstance(item.get("keywords"), list)
            else [],
        )
        for item in _mapping_list(vertical.get("rubrics"))
    ]
    questions = [
        VerticalQuestion(
            question_id=str(item.get("id") or ""),
            section_id=str(item.get("section_id") or ""),
            question=str(item.get("question") or ""),
            priority=str(item.get("priority") or "medium"),
            rationale=str(item.get("rationale") or ""),
        )
        for item in _mapping_list(vertical.get("questions"))
    ]
    artifacts = [
        VerticalArtifact(
            artifact_id=str(item.get("id") or ""),
            title=str(item.get("title") or item.get("id") or ""),
            section_ids=[str(section_id) for section_id in item.get("section_ids", []) if str(section_id).strip()]
            if isinstance(item.get("section_ids"), list)
            else [],
            required=bool(item.get("required", False)),
        )
        for item in _mapping_list(vertical.get("artifacts"))
    ]
    manifest_payload = vertical.get("manifest") if isinstance(vertical.get("manifest"), dict) else {}
    profile_specs = [
        VerticalProfile(
            profile_id=str(item.get("id") or item.get("profile_id") or ""),
            title=str(item.get("title") or item.get("name") or item.get("id") or item.get("profile_id") or ""),
            description=str(item.get("description") or ""),
            enabled_modules=[str(value) for value in item.get("enabled_modules", []) if str(value).strip()]
            if isinstance(item.get("enabled_modules"), list)
            else [],
        )
        for item in _mapping_list(vertical.get("profile_specs"))
    ]
    module_specs = [
        VerticalModule(
            module_id=str(item.get("id") or item.get("module_id") or ""),
            title=str(item.get("title") or item.get("name") or item.get("id") or item.get("module_id") or ""),
            description=str(item.get("description") or ""),
            section_ids=[str(value) for value in item.get("section_ids", []) if str(value).strip()]
            if isinstance(item.get("section_ids"), list)
            else [],
        )
        for item in _mapping_list(vertical.get("module_specs"))
    ]
    compatibility = vertical.get("compatibility")
    if not isinstance(compatibility, dict):
        compatibility = manifest_payload.get("compatibility") if isinstance(manifest_payload, dict) else {}
    if not isinstance(compatibility, dict):
        compatibility = {}
    return VerticalPack(
        vertical_id=str(vertical.get("id") or ""),
        name=str(vertical.get("name") or vertical.get("id") or ""),
        version=str(vertical.get("version") or ""),
        description=str(vertical.get("description") or ""),
        extends=str(vertical.get("extends")) if vertical.get("extends") else None,
        source=source,
        path=path,
        sections=sections,
        rubrics=rubrics,
        questions=questions,
        artifacts=artifacts,
        profiles=[str(item) for item in vertical.get("profiles", []) if str(item).strip()] if isinstance(vertical.get("profiles"), list) else [],
        modules=[str(item) for item in vertical.get("modules", []) if str(item).strip()] if isinstance(vertical.get("modules"), list) else [],
        examples=[str(item) for item in vertical.get("examples", []) if str(item).strip()] if isinstance(vertical.get("examples"), list) else [],
        schema_version=int(vertical.get("schema_version") or VERTICAL_SCHEMA_VERSION),
        manifest=VerticalManifest(
            vertical_id=str(manifest_payload.get("id") or vertical.get("id") or ""),
            name=str(manifest_payload.get("name") or vertical.get("name") or vertical.get("id") or ""),
            version=str(manifest_payload.get("version") or vertical.get("version") or ""),
            schema_version=int(manifest_payload.get("schema_version") or VERTICAL_SCHEMA_VERSION),
            publisher=str(manifest_payload.get("publisher") or ""),
            source=str(manifest_payload.get("source") or ""),
            compatibility=compatibility,
        )
        if isinstance(manifest_payload, dict) and manifest_payload
        else None,
        profile_specs=profile_specs,
        module_specs=module_specs,
        compatibility=compatibility,
    )


def _pack_payload(pack: VerticalPack) -> dict[str, object]:
    return {
        "vertical": {
            "schema_version": VERTICAL_SCHEMA_VERSION,
            "id": pack.vertical_id,
            "name": pack.name,
            "version": pack.version,
            "description": pack.description,
            "extends": pack.extends,
            "sections": [
                {
                    "id": section.section_id,
                    "title": section.title,
                    "purpose": section.purpose,
                    "required": section.required,
                    "priority": section.priority,
                    "fields": [
                        {
                            "id": field.field_id,
                            "label": field.label,
                            "required": field.required,
                            "question": field.question,
                            "assisted_answer": field.assisted_answer,
                            "completion_criteria": field.completion_criteria,
                            "common_mistakes": field.common_mistakes,
                            "suggested_artifacts": field.suggested_artifacts,
                            "maturity_gates": field.maturity_gates,
                        }
                        for field in section.fields
                    ],
                    "completion_policy": {
                        "allow_assumed_completion": section.completion_policy.allow_assumed_completion,
                        "required_fields": section.completion_policy.required_fields,
                    }
                    if section.completion_policy
                    else {},
                }
                for section in pack.sections
            ],
            "rubrics": [
                {
                    "id": rubric.rubric_id,
                    "title": rubric.title,
                    "section_id": rubric.section_id,
                    "required": rubric.required,
                    "keywords": rubric.keywords,
                }
                for rubric in pack.rubrics
            ],
            "questions": [
                {
                    "id": question.question_id,
                    "section_id": question.section_id,
                    "priority": question.priority,
                    "question": question.question,
                    "rationale": question.rationale,
                }
                for question in pack.questions
            ],
            "artifacts": [
                {
                    "id": artifact.artifact_id,
                    "title": artifact.title,
                    "section_ids": artifact.section_ids,
                    "required": artifact.required,
                }
                for artifact in pack.artifacts
            ],
            "profiles": pack.profiles,
            "modules": pack.modules,
            "examples": pack.examples,
            "schema_version": pack.schema_version,
            "compatibility": pack.compatibility,
            "profile_specs": [
                {
                    "id": profile.profile_id,
                    "title": profile.title,
                    "description": profile.description,
                    "enabled_modules": profile.enabled_modules,
                }
                for profile in pack.profile_specs
            ],
            "module_specs": [
                {
                    "id": module.module_id,
                    "title": module.title,
                    "description": module.description,
                    "section_ids": module.section_ids,
                }
                for module in pack.module_specs
            ],
        }
    }


def _normalise_pack_payload(payload: dict[str, object]) -> dict[str, object]:
    if "vertical" in payload:
        return payload
    candidate = payload.get("vertical_candidate")
    if not isinstance(candidate, dict):
        return payload
    candidate_payload = candidate.get("candidate")
    if isinstance(candidate_payload, dict):
        return {"vertical": candidate_payload}
    return payload


def _completion_policy_from_payload(value: object) -> VerticalCompletionPolicy | None:
    if not isinstance(value, dict):
        return None
    required = value.get("required_fields", [])
    return VerticalCompletionPolicy(
        allow_assumed_completion=bool(value.get("allow_assumed_completion", False)),
        required_fields=[str(item) for item in required if str(item).strip()] if isinstance(required, list) else [],
    )


def _source_from_pack(pack: VerticalPack, root: Path) -> VerticalPackSource:
    path = pack.path
    resolved_from = ""
    if path is not None:
        resolved_from = str(relative_to_root(path, root))
    if pack.source == INTERNAL_SOURCE:
        resolved_from = f"p2p_engine.resources.verticals/{pack.vertical_id}"
    return VerticalPackSource(
        source_type=pack.source,
        resolved_from=resolved_from,
        path=relative_to_root(path, root) if path else None,
        package="p2p_engine" if pack.source == INTERNAL_SOURCE else "",
    )


def _pack_checksum(pack: VerticalPack) -> str:
    payload = _pack_payload(pack)
    text = yaml.safe_dump(payload, sort_keys=True, allow_unicode=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vertical_lock_payload(lock: VerticalLock) -> dict[str, object]:
    return {
        "project_vertical_lock": {
            "schema_version": VERTICAL_LOCK_SCHEMA_VERSION,
            "vertical_id": lock.vertical_id,
            "name": lock.name,
            "version": lock.version,
            "pack_schema_version": lock.pack_schema_version,
            "source": {
                "type": lock.source.source_type,
                "resolved_from": lock.source.resolved_from,
                "path": lock.source.path.as_posix() if lock.source.path else "",
                "package": lock.source.package,
            },
            "checksum": {"algorithm": "sha256", "value": lock.checksum},
            "compatibility": lock.compatibility,
            "selected": {"at": lock.selected_at, "by": lock.selected_by},
            "trust": lock.trust,
        }
    }


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


def _field_id_for_question(section: VerticalSection, question: VerticalQuestion) -> str:
    if section.fields:
        return section.fields[0].field_id
    return "summary"


def _definition_state_payload(state: ProjectDefinitionState) -> dict[str, object]:
    return {
        "project_definition": {
            "schema_version": state.schema_version,
            "vertical_id": state.vertical_id,
            "vertical_version": state.vertical_version,
            "profile": state.profile,
            "modules": state.modules,
            "lock": {"checksum": state.lock_checksum},
            "sections": [
                {
                    "id": section.section_id,
                    "status": section.status,
                    "fields": {
                        field_id: {
                            "value": field.value,
                            "source": field.source,
                            "updated_at": field.updated_at,
                        }
                        for field_id, field in section.fields.items()
                    },
                    "missing_required_fields": section.missing_required_fields,
                    "assumptions": [
                        {
                            "id": assumption.assumption_id,
                            "field_id": assumption.field_id,
                            "status": assumption.status,
                            "text": assumption.text,
                        }
                        for assumption in section.assumptions
                    ],
                    "open_questions": [
                        {
                            "id": question.question_id,
                            "field_id": question.field_id,
                            "status": question.status,
                            "question": question.question,
                        }
                        for question in section.open_questions
                    ],
                    "blockers": [
                        {
                            "id": blocker.blocker_id,
                            "status": blocker.status,
                            "text": blocker.text,
                        }
                        for blocker in section.blockers
                    ],
                }
                for section in state.sections
            ],
            "next_suggested_action": state.next_suggested_action,
            "history": [
                {
                    "at": item.at,
                    "actor": item.actor,
                    "operation": item.operation,
                    "section_id": item.section_id,
                }
                for item in state.history
            ],
        }
    }


def _definition_semantic_payload(payload: dict[str, object]) -> dict[str, object]:
    """Remove audit-only dates while retaining every governed definition value."""
    candidate = yaml.safe_load(yaml.safe_dump(payload, sort_keys=False))
    data = candidate.get("project_definition") if isinstance(candidate, dict) else None
    if not isinstance(data, dict):
        return candidate if isinstance(candidate, dict) else {}
    sections = data.get("sections")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            fields = section.get("fields")
            if isinstance(fields, dict):
                for field in fields.values():
                    if isinstance(field, dict):
                        field.pop("updated_at", None)
    history = data.get("history")
    if isinstance(history, list):
        for entry in history:
            if isinstance(entry, dict):
                entry.pop("at", None)
    return candidate


def _definition_state_from_payload(payload: dict[str, object], *, path: Path) -> ProjectDefinitionState:
    data = payload.get("project_definition")
    if not isinstance(data, dict):
        raise ValueError("Invalid project definition state: expected project_definition mapping.")
    sections: list[ProjectDefinitionSectionState] = []
    for item in data.get("sections", []) if isinstance(data.get("sections"), list) else []:
        if not isinstance(item, dict):
            continue
        fields_payload = item.get("fields")
        fields: dict[str, ProjectDefinitionFieldValue] = {}
        if isinstance(fields_payload, dict):
            for field_id, field_value in fields_payload.items():
                if isinstance(field_value, dict):
                    fields[str(field_id)] = ProjectDefinitionFieldValue(
                        field_id=str(field_id),
                        value=field_value.get("value"),
                        source=str(field_value.get("source") or ""),
                        updated_at=str(field_value.get("updated_at") or ""),
                    )
        assumptions = [
            ProjectDefinitionAssumption(
                assumption_id=str(assumption.get("id") or ""),
                field_id=str(assumption.get("field_id") or ""),
                status=str(assumption.get("status") or "to_validate"),
                text=str(assumption.get("text") or ""),
            )
            for assumption in _mapping_list(item.get("assumptions"))
        ]
        questions = [
            ProjectDefinitionQuestion(
                question_id=str(question.get("id") or ""),
                field_id=str(question.get("field_id") or ""),
                status=str(question.get("status") or "open"),
                question=str(question.get("question") or ""),
            )
            for question in _mapping_list(item.get("open_questions"))
        ]
        blockers = [
            ProjectDefinitionBlocker(
                blocker_id=str(blocker.get("id") or ""),
                status=str(blocker.get("status") or "open"),
                text=str(blocker.get("text") or ""),
            )
            for blocker in _mapping_list(item.get("blockers"))
        ]
        missing = item.get("missing_required_fields")
        sections.append(
            ProjectDefinitionSectionState(
                section_id=str(item.get("id") or ""),
                status=str(item.get("status") or "missing"),
                fields=fields,
                missing_required_fields=[str(value) for value in missing if str(value).strip()] if isinstance(missing, list) else [],
                assumptions=assumptions,
                open_questions=questions,
                blockers=blockers,
            )
        )
    history = [
        ProjectDefinitionHistoryEntry(
            at=str(item.get("at") or ""),
            actor=str(item.get("actor") or ""),
            operation=str(item.get("operation") or ""),
            section_id=str(item.get("section_id") or ""),
        )
        for item in _mapping_list(data.get("history"))
    ]
    lock_payload = data.get("lock") if isinstance(data.get("lock"), dict) else {}
    return ProjectDefinitionState(
        schema_version=int(data.get("schema_version") or PROJECT_DEFINITION_SCHEMA_VERSION),
        vertical_id=str(data.get("vertical_id") or ""),
        vertical_version=str(data.get("vertical_version") or ""),
        profile=str(data.get("profile") or "default"),
        modules=[str(item) for item in data.get("modules", []) if str(item).strip()] if isinstance(data.get("modules"), list) else [],
        lock_checksum=str(lock_payload.get("checksum") or ""),
        sections=sections,
        next_suggested_action=data.get("next_suggested_action") if isinstance(data.get("next_suggested_action"), dict) else {},
        history=history,
        path=path,
    )


def _definition_patch_from_payload(payload: dict[str, object], *, target: str) -> ProjectDefinitionPatch:
    data = payload.get("project_definition_patch")
    if not isinstance(data, dict):
        raise ValueError(f"Invalid project definition patch {target}: expected project_definition_patch mapping.")
    operations = data.get("operations")
    if not isinstance(operations, list):
        raise ValueError(f"Invalid project definition patch {target}: operations must be a list.")
    if not all(isinstance(item, dict) for item in operations):
        raise ValueError(f"Invalid project definition patch {target}: every operation must be a mapping.")
    actor = str(data.get("actor") or "").strip()
    if not actor:
        raise ValueError(f"Invalid project definition patch {target}: actor is required.")
    return ProjectDefinitionPatch(
        actor=actor,
        operations=[item for item in operations if isinstance(item, dict)],
        schema_version=int(data.get("schema_version") or PROJECT_DEFINITION_SCHEMA_VERSION),
    )


def _copy_section_state(section: ProjectDefinitionSectionState) -> ProjectDefinitionSectionState:
    return ProjectDefinitionSectionState(
        section_id=section.section_id,
        status=section.status,
        fields=dict(section.fields),
        missing_required_fields=list(section.missing_required_fields),
        assumptions=list(section.assumptions),
        open_questions=list(section.open_questions),
        blockers=list(section.blockers),
    )


def _unwrap_mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    return payload


def _unwrap_list(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    value = payload.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    nested = payload.get("vertical")
    if isinstance(nested, dict):
        value = nested.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _safety_issues(payload: dict[str, object]) -> list[VerticalValidationIssue]:
    issues: list[VerticalValidationIssue] = []
    hard_patterns = [
        r"ignore (the )?(system|developer|governance|safety)",
        r"override (the )?(system|developer|governance|safety)",
        r"bypass (owner|permission|consent|governance|safety)",
        r"force .*tool",
        r"execute (code|command|shell)",
        r"run (sudo|chmod|rm -rf|curl|wget)",
        r"change permissions?",
        r"\.\./",
    ]
    warning_patterns = [
        r"\byou must\b",
        r"\balways\b",
        r"\bnever\b",
    ]
    for field, text in _iter_text(payload):
        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in hard_patterns):
            issues.append(
                VerticalValidationIssue(
                    "error",
                    field,
                    "vertical pack content attempts to override instructions, execute code, change permissions, or escape paths",
                    "P2P_VERTICAL_UNSAFE_GUIDANCE",
                )
            )
        elif any(re.search(pattern, lowered) for pattern in warning_patterns) and "question" not in field:
            issues.append(
                VerticalValidationIssue(
                    "warning",
                    field,
                    "vertical pack content contains instruction-like wording; pack text is domain data only",
                    "P2P_VERTICAL_AMBIGUOUS_GUIDANCE",
                )
            )
    return issues


def _iter_text(value: object, prefix: str = "") -> list[tuple[str, str]]:
    if isinstance(value, dict):
        results: list[tuple[str, str]] = []
        for key, item in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            results.extend(_iter_text(item, next_prefix))
        return results
    if isinstance(value, list):
        results = []
        for index, item in enumerate(value):
            results.extend(_iter_text(item, f"{prefix}[{index}]"))
        return results
    if isinstance(value, str):
        return [(prefix, value)]
    return []


def _contains_path_escape(value: str) -> bool:
    return "../" in value or "..\\" in value


def _vertical_pack_issues(payload: dict[str, object]) -> list[VerticalValidationIssue]:
    issues: list[VerticalValidationIssue] = []

    def error(field: str, message: str, code: str = "P2P_VERTICAL_INVALID_PACK") -> None:
        issues.append(VerticalValidationIssue("error", field, message, code))

    def warning(field: str, message: str, code: str = "P2P_VERTICAL_PACK_WARNING") -> None:
        issues.append(VerticalValidationIssue("warning", field, message, code))

    vertical = payload.get("vertical")
    if not isinstance(vertical, dict):
        error("vertical", "expected mapping")
        return issues
    for field in ("id", "name", "version", "description"):
        if not str(vertical.get(field) or "").strip():
            error(f"vertical.{field}", "required")
    section_items = _mapping_list(vertical.get("sections"))
    if not section_items:
        error("vertical.sections", "at least one section is required")
    section_ids = _ids(section_items, "vertical.sections", error)
    for index, item in enumerate(section_items):
        for field in ("id", "title", "purpose"):
            if not str(item.get(field) or "").strip():
                error(f"vertical.sections[{index}].{field}", "required")
        field_items = _mapping_list(item.get("fields"))
        field_ids = _ids(field_items, f"vertical.sections[{index}].fields", error)
        for field_index, field_item in enumerate(field_items):
            for field_name in ("id", "label"):
                if not str(field_item.get(field_name) or field_item.get("field_id") or "").strip():
                    error(f"vertical.sections[{index}].fields[{field_index}].{field_name}", "required")
        completion_policy = item.get("completion_policy")
        if isinstance(completion_policy, dict):
            required_fields = completion_policy.get("required_fields", [])
            if required_fields and not isinstance(required_fields, list):
                error(f"vertical.sections[{index}].completion_policy.required_fields", "must be a list")
            elif isinstance(required_fields, list):
                for field_id in required_fields:
                    text = str(field_id)
                    if text not in field_ids:
                        error(
                            f"vertical.sections[{index}].completion_policy.required_fields",
                            f"unknown field `{text}`",
                        )
    rubric_items = _mapping_list(vertical.get("rubrics"))
    _ids(rubric_items, "vertical.rubrics", error)
    for index, item in enumerate(rubric_items):
        if not str(item.get("id") or "").strip():
            error(f"vertical.rubrics[{index}].id", "required")
        section_id = str(item.get("section_id") or "").strip()
        if not section_id:
            error(f"vertical.rubrics[{index}].section_id", "required")
        elif section_id not in section_ids:
            error(f"vertical.rubrics[{index}].section_id", f"unknown section `{section_id}`")
    if not rubric_items:
        error("vertical.rubrics", "at least one rubric is required")
    question_items = _mapping_list(vertical.get("questions"))
    _ids(question_items, "vertical.questions", error)
    for index, item in enumerate(question_items):
        if not str(item.get("id") or "").strip():
            error(f"vertical.questions[{index}].id", "required")
        section_id = str(item.get("section_id") or "").strip()
        if not section_id:
            error(f"vertical.questions[{index}].section_id", "required")
        elif section_id not in section_ids:
            error(f"vertical.questions[{index}].section_id", f"unknown section `{section_id}`")
        priority = str(item.get("priority") or "medium")
        if priority not in QUESTION_PRIORITIES:
            error(f"vertical.questions[{index}].priority", f"must be one of {sorted(QUESTION_PRIORITIES)}")
        if not str(item.get("question") or "").strip():
            error(f"vertical.questions[{index}].question", "required")
    if not question_items:
        error("vertical.questions", "at least one blocking question is required")
    artifact_items = _mapping_list(vertical.get("artifacts"))
    _ids(artifact_items, "vertical.artifacts", error)
    for index, item in enumerate(artifact_items):
        if not str(item.get("id") or "").strip():
            error(f"vertical.artifacts[{index}].id", "required")
        section_ids_value = item.get("section_ids", [])
        if not isinstance(section_ids_value, list):
            error(f"vertical.artifacts[{index}].section_ids", "must be a list")
            continue
        for section_id in section_ids_value:
            text = str(section_id)
            if text not in section_ids:
                error(f"vertical.artifacts[{index}].section_ids", f"unknown section `{text}`")
    if not artifact_items:
        error("vertical.artifacts", "at least one expected artifact is required")
    profile_items = _mapping_list(vertical.get("profile_specs"))
    _ids(profile_items, "vertical.profile_specs", error)
    module_items = _mapping_list(vertical.get("module_specs"))
    module_ids = _ids(module_items, "vertical.module_specs", error)
    for index, item in enumerate(module_items):
        for section_id in item.get("section_ids", []) if isinstance(item.get("section_ids"), list) else []:
            text = str(section_id)
            if text not in section_ids:
                error(f"vertical.module_specs[{index}].section_ids", f"unknown section `{text}`")
    for index, item in enumerate(profile_items):
        for module_id in item.get("enabled_modules", []) if isinstance(item.get("enabled_modules"), list) else []:
            text = str(module_id)
            if module_ids and text not in module_ids:
                error(f"vertical.profile_specs[{index}].enabled_modules", f"unknown module `{text}`")
    for safety_issue in _safety_issues(payload):
        if safety_issue.severity == "error":
            error(safety_issue.field, safety_issue.message, safety_issue.code)
        else:
            warning(safety_issue.field, safety_issue.message, safety_issue.code)
    return issues


def _compose_pack(pack: VerticalPack, packs: dict[str, VerticalPack]) -> VerticalPack:
    if not pack.extends:
        return pack
    base = packs.get(pack.extends)
    if base is None:
        raise ValueError(f"Unknown base vertical `{pack.extends}` for `{pack.vertical_id}`.")
    composed_base = _compose_pack(base, packs)
    return VerticalPack(
        vertical_id=pack.vertical_id,
        name=pack.name,
        version=pack.version,
        description=pack.description,
        extends=pack.extends,
        source=pack.source,
        path=pack.path,
        sections=_merge_by_id(composed_base.sections, pack.sections, lambda item: item.section_id),
        rubrics=_merge_by_id(composed_base.rubrics, pack.rubrics, lambda item: item.rubric_id),
        questions=_merge_by_id(composed_base.questions, pack.questions, lambda item: item.question_id),
        artifacts=_merge_by_id(composed_base.artifacts, pack.artifacts, lambda item: item.artifact_id),
        profiles=list(dict.fromkeys([*composed_base.profiles, *pack.profiles])),
        modules=list(dict.fromkeys([*composed_base.modules, *pack.modules])),
        examples=list(dict.fromkeys([*composed_base.examples, *pack.examples])),
        schema_version=pack.schema_version,
        manifest=pack.manifest,
        profile_specs=_merge_by_id(composed_base.profile_specs, pack.profile_specs, lambda item: item.profile_id),
        module_specs=_merge_by_id(composed_base.module_specs, pack.module_specs, lambda item: item.module_id),
        compatibility={**composed_base.compatibility, **pack.compatibility},
    )


def _merge_by_id(base: list[T], overlay: list[T], key: Callable[[T], str]) -> list[T]:
    merged: dict[str, T] = {}
    order: list[str] = []
    for item in [*base, *overlay]:
        item_id = key(item)
        if item_id not in merged:
            order.append(item_id)
        merged[item_id] = item
    return [merged[item_id] for item_id in order]


def _mapping_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _ids(items: list[dict[str, object]], field: str, error: Callable[[str, str], None]) -> set[str]:
    seen: set[str] = set()
    ids: set[str] = set()
    for index, item in enumerate(items):
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            continue
        if item_id in seen:
            error(f"{field}[{index}].id", f"duplicate id `{item_id}`")
        seen.add(item_id)
        ids.add(item_id)
    return ids


def _candidate_pack(
    *,
    vertical_id: str,
    name: str,
    description: str,
    sections: list[tuple[str, str, str]],
    questions: list[tuple[str, str, str]],
    artifacts: list[tuple[str, str, list[str]]],
) -> VerticalPack:
    vertical_sections = [
        VerticalSection(section_id=section_id, title=title, purpose=purpose, required=True, priority=(index + 1) * 10)
        for index, (section_id, title, purpose) in enumerate(sections)
    ]
    rubrics = [
        VerticalRubric(
            rubric_id=f"{section_id}_coverage",
            title=f"{title} Coverage",
            section_id=section_id,
            required=True,
            keywords=_important_words(title + " " + purpose),
        )
        for section_id, title, purpose in sections
    ]
    vertical_questions = [
        VerticalQuestion(
            question_id=question_id,
            section_id=section_id,
            question=question,
            priority="high",
            rationale="Needed to define the custom vertical candidate.",
        )
        for question_id, section_id, question in questions
    ]
    vertical_artifacts = [
        VerticalArtifact(artifact_id=artifact_id, title=title, section_ids=section_ids, required=True)
        for artifact_id, title, section_ids in artifacts
    ]
    return VerticalPack(
        vertical_id=vertical_id,
        name=name,
        version="0.1.0",
        description=description,
        extends=BASE_PROJECT_VERTICAL_ID,
        source="candidate",
        path=None,
        sections=vertical_sections,
        rubrics=rubrics,
        questions=vertical_questions,
        artifacts=vertical_artifacts,
    )


def _normalize_vertical_id(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        raise ValueError("Vertical ID is required.")
    return normalized


def _title_from_slug(value: str) -> str:
    return " ".join(part.capitalize() for part in value.replace("-", "_").split("_") if part)


def _important_words(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z_]{3,}", text.lower())
    stop = {
        "acceptance",
        "context",
        "criteria",
        "decision",
        "define",
        "from",
        "goals",
        "must",
        "pending",
        "problem",
        "project",
        "proposal",
        "should",
        "that",
        "this",
        "what",
        "which",
        "will",
        "with",
    }
    return [word.replace("_", " ") for word in words if word not in stop][:12]


def _vertical_section_terms(section: VerticalSection, pack: VerticalPack) -> set[str]:
    terms: set[str] = set()
    for raw in (section.title, section.purpose):
        normalized = " ".join(re.findall(r"[a-z0-9]+", raw.lower()))
        if 5 <= len(normalized) <= 80:
            terms.add(normalized)
        terms.update(_important_words(raw))
    for field in _section_fields(section, pack):
        for raw in (field.label, field.question):
            normalized = " ".join(re.findall(r"[a-z0-9]+", raw.lower()))
            if 5 <= len(normalized) <= 80:
                terms.add(normalized)
            terms.update(_important_words(raw))
    for rubric in pack.rubrics:
        if rubric.section_id != section.section_id:
            continue
        for raw in [rubric.title, *rubric.keywords]:
            normalized = " ".join(re.findall(r"[a-z0-9]+", raw.lower()))
            if len(normalized) >= 5:
                terms.add(normalized)
    return {term for term in terms if len(term) >= 5}


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"YAML document must be a mapping: {path}")
    return data


def dataclass_payload(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value

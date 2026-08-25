from __future__ import annotations

import re
import hashlib
import os
from dataclasses import asdict, replace
from datetime import date
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Protocol, TypeVar

import yaml

from p2p_engine.core.project_verticals import (
    ActiveProjectVertical,
    ProjectDefinitionAssumption,
    ProjectDefinitionBlocker,
    ProjectDefinitionCandidate,
    ProjectDefinitionFieldValue,
    ProjectDefinitionHistoryEntry,
    ProjectDefinitionOrphan,
    ProjectDefinitionPatch,
    ProjectDefinitionPatchResult,
    ProjectDefinitionSectionState,
    ProjectDefinitionState,
    ProjectDefinitionView,
    ProjectReadinessReview,
    ProjectVerticalContext,
    ProposalVerticalCoverage,
    ProposalVerticalCoverageSection,
    ProposalVerticalCoverageStatus,
    ProposalVerticalCoverageSuggestion,
    ResolvedVerticalPack,
    VerticalArtifact,
    VerticalCompletionPolicy,
    VerticalDependency,
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
    VerticalReadState,
    VerticalValidationIssue,
    VerticalValidationResult,
    VerticalMigrationCandidate,
    VerticalCoverageSuggestionSection,
)
from p2p_engine.core.project_domain import ProjectDomainRef, normalize_domain_tags
from p2p_engine.core.portable_verticals import VerticalCoordinate, is_semantic_version
from p2p_engine.core.mutation_preview import (
    MutationPreview,
    MutationPreviewService,
    MutationResult,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.project_readiness import (
    PROJECT_READINESS_GAP_POLICY_VERSION,
    PROJECT_READINESS_REVIEW_DETAIL_LIMIT,
    ProjectReadinessAssumptionSnapshot,
    ProjectReadinessDiagnostic,
    ProjectReadinessResult,
    ProjectReadinessQuestionSnapshot,
    ProjectReadinessSectionSnapshot,
    ProjectReadinessSnapshot,
)
from p2p_engine.core.project_questions import ProjectQuestionApplicability
from p2p_engine.core.project_structure import StructureField
from p2p_engine.foundation.files import relative_to_root, slugify, write_text_atomic, write_yaml_atomic, yaml_dump
from p2p_engine.foundation.yaml_loaders import load_yaml, load_yaml_mapping
from p2p_engine.services.project_readiness import (
    ProjectReadinessGapService,
    ProjectReadinessSourceAccess,
    ProjectReadinessSnapshotBuilder,
    readiness_snapshot_from_vertical_memory,
    unmapped_proposal_ids_from_vertical_memory,
)
from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.services.project_structure import ProjectStructureService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.services.lifecycle_authority import is_active_project_projection

VERTICAL_SCHEMA_VERSION = 3
ACTIVE_VERTICAL_SCHEMA_VERSION = 1
PROPOSAL_COVERAGE_SCHEMA_VERSION = 2
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
    issues = _vertical_pack_issues(payload)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        first = errors[0]
        if first.code == "P2P_VERTICAL_UNSUPPORTED_SCHEMA":
            raise ValueError(f"{first.code}: {first.message}")
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
    schema_version = coverage.get("schema_version")
    if schema_version != PROPOSAL_COVERAGE_SCHEMA_VERSION:
        raise ValueError(
            f"P2P_VERTICAL_COVERAGE_UNSUPPORTED_SCHEMA: {target} requires "
            f"schema_version {PROPOSAL_COVERAGE_SCHEMA_VERSION}; observed `{schema_version}`."
        )
    unknown = set(coverage) - {"schema_version", "proposal_id", "vertical_id", "sections", "provenance"}
    if unknown:
        raise ValueError(f"Invalid {target}: unknown fields: {', '.join(sorted(unknown))}.")
    provenance = coverage.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError(f"Invalid {target}: schema v3 requires provenance mapping.")
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
        readiness_source_reader: Callable[[Path], bytes] | None = None,
        definition_audit_date: Callable[[], str] | None = None,
        vertical_memory_view: Callable[[], object] | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.proposal_summaries = proposal_summaries
        self.find_proposal_dir = find_proposal_dir
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=root, p2p_dir=p2p_dir)
        self.readiness_source_reader = readiness_source_reader
        self.definition_audit_date = definition_audit_date or (lambda: date.today().isoformat())
        self.vertical_memory_view = vertical_memory_view

    def list_verticals(self) -> list[VerticalListItem]:
        active = self.active_vertical()
        packs_by_identity: dict[str, VerticalPack] = {}
        for pack in self._available_pack_inventory():
            packs_by_identity[pack.coordinate or pack.vertical_id] = pack
        items: list[VerticalListItem] = []
        for identity in sorted(packs_by_identity):
            pack = packs_by_identity[identity]
            items.append(
                VerticalListItem(
                    vertical_id=pack.vertical_id,
                    name=pack.name,
                    version=pack.version,
                    source=pack.source,
                    active=(
                        (pack.coordinate or pack.vertical_id) == (active.coordinate or active.vertical_id)
                        and not active.fallback_used
                    ),
                    path=relative_to_root(pack.path, self.root) if pack.path else None,
                    coordinate=pack.coordinate,
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

    def select_vertical(
        self,
        vertical_id: str,
        *,
        actor: str = "local",
        profile: str = "default",
        modules: list[str] | None = None,
        artifact_checksum: str = "",
    ) -> ActiveProjectVertical:
        candidate = self.render_migration_candidate(
            vertical_id,
            actor=actor,
            profile=profile,
            modules=modules,
            artifact_checksum=artifact_checksum,
        )
        self.validate_migration_candidate(candidate)
        sources = tuple(
            source_precondition(
                path,
                (self.root / path).read_bytes() if (self.root / path).exists() else None,
            )
            for path in sorted(candidate.candidate_files)
        )
        operation_reference = re.sub(r"[^A-Za-z0-9_-]", "-", vertical_id)
        token = MutationPreviewService.token(
            operation_id=f"project-vertical-select:{operation_reference}",
            targets=tuple(candidate.candidate_files),
            sources=sources,
            candidate_semantics={
                path: load_yaml(content)
                for path, content in candidate.candidate_files.items()
            },
        )
        result = self.atomic_writer.apply(
            operation_id=f"project-vertical-select:{operation_reference}",
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
        artifact_checksum: str = "",
        preserve_existing_rubrics: bool = True,
        reconcile_existing_questions: bool = True,
    ) -> VerticalMigrationCandidate:
        resolved = self._resolve_available_pack(vertical_id)
        pack = resolved.pack
        if not pack.sections:
            raise ValueError(
                "P2P_VERTICAL_NO_SECTIONS: a vertical needs at least one governed section before selection"
            )
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
                "active_vertical_coordinate": pack.coordinate,
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
            coordinate=pack.coordinate,
            dependencies=list(pack.manifest.dependencies) if pack.manifest else [],
            artifact_checksum=artifact_checksum,
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
                self._vertical_rubrics_payload(
                    pack,
                    rubric_mapping=rubric_mapping,
                    include_existing=preserve_existing_rubrics,
                )
            ).encode("utf-8"),
        }
        project_payload = _read_yaml_mapping(self.p2p_dir / "project.yml")
        project = project_payload.get("project")
        project_id = str(project.get("id") or "project") if isinstance(project, dict) else "project"
        question_service = ProjectQuestionStateService(root=self.root, p2p_dir=self.p2p_dir)
        current_questions = question_service.read_optional()
        if (
            reconcile_existing_questions
            and current_questions is not None
            and question_service.has_owner_evidence(current_questions)
        ):
            question_candidate = question_service.mark_reconciliation_required(
                current_questions,
                actor=actor,
                audit_at=selected_at,
            )
            reconciliation_required = True
        else:
            question_candidate = question_service.seed_from_definition(
                project_id=project_id,
                definition=definition,
                pack=pack,
                lock_checksum=resolved.checksum,
                actor=actor,
                audit_at=selected_at,
            ).artifact
            reconciliation_required = False
        candidate_files[".p2p/project/questions.yml"] = question_service.candidate_bytes(question_candidate)
        return VerticalMigrationCandidate(
            vertical_id=pack.vertical_id,
            profile=profile,
            modules=tuple(selected_modules),
            checksum=resolved.checksum,
            candidate_files=candidate_files,
            reconciliation_required=reconciliation_required,
            reference=pack.coordinate or pack.vertical_id,
        )

    def validate_migration_candidate(self, candidate: VerticalMigrationCandidate) -> None:
        expected = {
            ".p2p/project/vertical.yml",
            ".p2p/project/vertical.lock.yml",
            ".p2p/project/definition.yml",
            ".p2p/project/rubrics.yml",
        }
        allowed = (expected, {*expected, ".p2p/project/questions.yml"})
        if set(candidate.candidate_files) not in allowed:
            raise ValueError("Vertical migration candidate must contain the complete governed artifact set.")
        payloads: dict[str, dict[str, object]] = {}
        for path, content in candidate.candidate_files.items():
            value = load_yaml(content)
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
        pack = self._load_available_pack(candidate.reference or candidate.vertical_id)
        if pack.vertical_id != candidate.vertical_id:
            raise ValueError("Vertical migration target pack identity is incoherent.")
        active_coordinate = str(active.get("active_vertical_coordinate") or "")
        if pack.coordinate and active_coordinate != pack.coordinate:
            raise ValueError("Vertical migration active coordinate candidate is incoherent.")
        if not isinstance(lock, dict):
            raise ValueError("Vertical migration lock candidate is incoherent.")
        checksum = lock.get("checksum")
        if not isinstance(checksum, dict) or checksum.get("value") != candidate.checksum:
            raise ValueError("Vertical migration lock checksum is incoherent.")
        if str(lock.get("vertical_id") or "") != pack.vertical_id:
            raise ValueError("Vertical migration lock vertical id is incoherent.")
        if str(lock.get("version") or "") != pack.version:
            raise ValueError("Vertical migration lock version is incoherent.")
        if pack.coordinate and str(lock.get("coordinate") or "") != pack.coordinate:
            raise ValueError("Vertical migration lock coordinate is incoherent.")
        if definition.vertical_id != pack.vertical_id:
            raise ValueError("Vertical migration definition vertical id is incoherent.")
        if definition.vertical_version != pack.version:
            raise ValueError("Vertical migration definition version is incoherent.")
        if definition.lock_checksum != candidate.checksum:
            raise ValueError("Vertical migration definition lock checksum is incoherent.")
        issues = self._definition_state_issues(definition, pack)
        if any(issue.severity == "error" for issue in issues):
            first = next(issue for issue in issues if issue.severity == "error")
            raise ValueError(f"Invalid vertical migration definition: {first.field}: {first.message}")
        if ".p2p/project/questions.yml" in payloads:
            ProjectQuestionStateService(root=self.root, p2p_dir=self.p2p_dir).parse_payload(
                payloads[".p2p/project/questions.yml"],
                target=".p2p/project/questions.yml",
            )
        rubrics = payloads[".p2p/project/rubrics.yml"].get("criteria")
        if not isinstance(rubrics, list):
            raise ValueError("Vertical migration rubric candidate must contain criteria.")

    def active_vertical(self) -> ActiveProjectVertical:
        return self._active_vertical_and_pack()[0]

    def _active_vertical_and_pack(self) -> tuple[ActiveProjectVertical, VerticalPack]:
        path = self._active_vertical_path()
        if not path.exists():
            if self._uses_empty_starter():
                empty = _empty_starter_pack()
                return (
                    ActiveProjectVertical(
                        vertical_id="empty",
                        source="starter",
                        path=None,
                        fallback_used=False,
                        coordinate="",
                    ),
                    empty,
                )
            base = self._load_available_pack(BASE_PROJECT_VERTICAL_ID)
            return (
                ActiveProjectVertical(
                    vertical_id=BASE_PROJECT_VERTICAL_ID,
                    source=base.source,
                    path=relative_to_root(base.path, self.root) if base.path else None,
                    fallback_used=True,
                    coordinate=base.coordinate,
                ),
                base,
            )
        payload = _read_yaml_mapping(path)
        state = payload.get("project_vertical")
        if not isinstance(state, dict):
            raise ValueError(f"Invalid project vertical state: {path}")
        schema_version = state.get("schema_version")
        if schema_version != ACTIVE_VERTICAL_SCHEMA_VERSION:
            raise ValueError(
                "P2P_VERTICAL_ACTIVE_STATE_UNSUPPORTED_SCHEMA: active vertical state "
                f"requires schema_version {ACTIVE_VERTICAL_SCHEMA_VERSION}; observed "
                f"`{schema_version}`."
            )
        vertical_id = str(state.get("active_vertical_id") or "").strip()
        if not vertical_id:
            raise ValueError(f"Invalid project vertical state: missing active_vertical_id in {path}")
        pack: VerticalPack | None = None
        if self._vertical_lock_path().exists():
            lock_status = self.vertical_lock_status()
            if lock_status.status != "valid":
                raise ValueError(
                    f"Active project vertical lock is {lock_status.status}: {lock_status.message} "
                    f"{lock_status.suggested_command}".strip()
                )
            if lock_status.resolved is not None:
                pack = lock_status.resolved.pack
        if pack is None:
            reference = str(state.get("active_vertical_coordinate") or vertical_id)
            pack = self._load_available_pack(reference)
        active_coordinate = str(state.get("active_vertical_coordinate") or "").strip()
        if vertical_id != pack.vertical_id:
            raise ValueError(
                "P2P_VERTICAL_ACTIVE_STATE_MISMATCH: active vertical id "
                f"`{vertical_id}` does not match resolved `{pack.vertical_id}`"
            )
        if active_coordinate and active_coordinate != (pack.coordinate or ""):
            raise ValueError(
                "P2P_VERTICAL_ACTIVE_STATE_MISMATCH: active coordinate "
                f"`{active_coordinate}` does not match resolved `{pack.coordinate or pack.vertical_id}`"
            )
        reconciliation_required = self._question_reconciliation_required()
        return (
            ActiveProjectVertical(
                vertical_id=vertical_id,
                source=str(state.get("active_source") or pack.source),
                path=relative_to_root(pack.path, self.root) if pack.path else None,
                selected_at=str(state.get("selected_at") or ""),
                selected_by=str(state.get("selected_by") or ""),
                fallback_used=bool(state.get("fallback_used") or False),
                coordinate=pack.coordinate,
                reconciliation_required=reconciliation_required,
                reconciliation_command=(
                    "p2p project readiness questions reconcile-preview --actor <ACTOR>"
                    if reconciliation_required
                    else ""
                ),
            ),
            pack,
        )

    def _question_reconciliation_required(self) -> bool:
        artifact = ProjectQuestionStateService(root=self.root, p2p_dir=self.p2p_dir).read_optional()
        return bool(
            artifact
            and any(
                item.applicability == ProjectQuestionApplicability.RECONCILIATION_REQUIRED
                for item in artifact.questions
            )
        )

    def _uses_empty_starter(self) -> bool:
        source_path = self.p2p_dir / "project" / "structure-source.yml"
        if not source_path.is_file() or source_path.is_symlink():
            return False
        try:
            payload = _read_yaml_mapping(source_path)
        except (OSError, ValueError, yaml.YAMLError):
            return False
        state = payload.get("structure_source")
        source = state.get("source") if isinstance(state, dict) else None
        return bool(
            isinstance(source, dict)
            and source.get("kind") == "starter"
            and source.get("starter_id") == "empty"
        )

    def vertical_lock_status(self) -> VerticalLockStatus:
        lock_path = self._vertical_lock_path()
        display_path = relative_to_root(lock_path, self.root)
        if not lock_path.exists():
            if self._uses_empty_starter() and not self._active_vertical_path().exists():
                return VerticalLockStatus(
                    status="not_applicable",
                    path=display_path,
                    message="Empty starter has no vertical release lock.",
                )
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
            resolved = self._resolve_available_pack(locked.coordinate or locked.vertical_id)
        except ValueError as exc:
            return VerticalLockStatus(
                status="missing_source",
                path=display_path,
                locked=locked,
                message=str(exc),
                suggested_command="p2p project vertical lock repair --actor owner",
            )
        identity_mismatches: list[str] = []
        if locked.vertical_id != resolved.pack.vertical_id:
            identity_mismatches.append(
                f"vertical id `{locked.vertical_id}` != `{resolved.pack.vertical_id}`"
            )
        if locked.version and locked.version != resolved.pack.version:
            identity_mismatches.append(
                f"version `{locked.version}` != `{resolved.pack.version}`"
            )
        if locked.coordinate and locked.coordinate != (resolved.pack.coordinate or ""):
            identity_mismatches.append(
                f"coordinate `{locked.coordinate}` != `{resolved.pack.coordinate or resolved.pack.vertical_id}`"
            )
        if identity_mismatches:
            return VerticalLockStatus(
                status="identity_mismatch",
                path=display_path,
                locked=locked,
                resolved=resolved,
                message="Project vertical lock identity mismatch: " + "; ".join(identity_mismatches) + ".",
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
        reference = str(state.get("active_vertical_coordinate") or vertical_id).strip()
        resolved = self._resolve_available_pack(reference)
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
        pack = (
            self._load_available_pack(vertical_id)
            if vertical_id is not None
            else self._active_vertical_and_pack()[1]
        )
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
            pack = self._definition_validation_pack(state)
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

    @property
    def definition_path(self) -> Path:
        return self._definition_state_path()

    @property
    def active_vertical_path(self) -> Path:
        return self._active_vertical_path()

    @property
    def vertical_lock_path(self) -> Path:
        return self._vertical_lock_path()

    def parse_definition_bytes(self, content: bytes, *, path: Path | None = None) -> ProjectDefinitionState:
        try:
            payload = load_yaml(content)
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"Invalid project definition candidate: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Invalid project definition candidate: expected a YAML mapping")
        return _definition_state_from_payload(payload, path=path or self._definition_state_path())

    def pack_for_definition(self, state: ProjectDefinitionState) -> VerticalPack:
        pack = self._definition_validation_pack(state)
        issues = [item for item in self._definition_state_issues(state, pack) if item.severity == "error"]
        if issues:
            first = issues[0]
            raise ValueError(f"Project definition state is invalid: {first.field}: {first.message}")
        return pack

    def _definition_validation_pack(self, state: ProjectDefinitionState) -> VerticalPack:
        structure_path = self.p2p_dir / "project" / "structure.yml"
        if not structure_path.is_file() or structure_path.is_symlink():
            return self._active_vertical_and_pack()[1]
        structure = ProjectStructureService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        ).show()
        fields_by_section: dict[str, list[VerticalField]] = {}
        for field in structure.fields:
            if field.lifecycle != "active":
                continue
            fields_by_section.setdefault(field.section_id, []).append(
                VerticalField(
                    field_id=field.field_id,
                    label=field.label,
                    required=field.required,
                    question=field.description,
                )
            )
        return VerticalPack(
            vertical_id=state.vertical_id or structure.structure_id,
            name=structure.structure_id,
            version=state.vertical_version or "project-owned",
            description="Detached project-owned structure",
            extends=None,
            source="project_structure",
            path=None,
            sections=[
                VerticalSection(
                    section_id=item.section_id,
                    title=item.title,
                    purpose=item.description,
                    required=item.required,
                    priority=item.order,
                    fields=fields_by_section.get(item.section_id, []),
                )
                for item in structure.sections
                if item.lifecycle == "active"
            ],
            rubrics=[
                VerticalRubric(
                    rubric_id=item.criterion_id,
                    title=item.title,
                    section_id=item.section_id,
                    required=item.required,
                    keywords=list(item.keywords),
                )
                for item in structure.criteria
                if item.lifecycle == "active" and item.enabled
            ],
            questions=[
                VerticalQuestion(
                    question_id=item.question_id,
                    section_id=item.section_id,
                    question=item.prompt,
                    priority=item.priority,
                    rationale=item.rationale,
                )
                for item in structure.questions
                if item.lifecycle == "active"
            ],
            artifacts=[
                VerticalArtifact(
                    artifact_id=item.artifact_id,
                    title=item.title,
                    section_ids=list(item.section_ids),
                    required=item.required,
                )
                for item in structure.artifacts
            ],
        )

    def parse_vertical_lock_bytes(self, content: bytes, *, path: Path | None = None) -> VerticalLock:
        try:
            payload = load_yaml(content)
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"Invalid project vertical lock candidate: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Invalid project vertical lock candidate: expected a YAML mapping")
        return _vertical_lock_from_payload(path or self._vertical_lock_path(), payload, self.root)

    def validate_definition_state(self, state: ProjectDefinitionState, pack: VerticalPack) -> None:
        errors = [item for item in self._definition_state_issues(state, pack) if item.severity == "error"]
        if errors:
            first = errors[0]
            raise ValueError(f"Invalid project definition candidate: {first.field}: {first.message}")

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
        candidate = self.render_definition_candidate(
            state=state,
            patch=patch,
            pack=pack,
            audit_at=self.definition_audit_date(),
        )
        path = self._definition_state_path()
        relative = path.relative_to(self.root).as_posix()
        current_bytes = path.read_bytes()
        semantic_candidate = candidate.semantic_payload
        authority = self._definition_actor_authority(actor)
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
                    "changed_sections": list(candidate.changed_sections),
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
        candidate = self.render_definition_candidate(
            state=state,
            patch=patch,
            pack=pack,
            audit_at=self.definition_audit_date(),
        )
        relative = self._definition_state_path().relative_to(self.root).as_posix()
        return self.atomic_writer.apply(
            operation_id=preview.operation_id,
            candidates={relative: candidate.candidate_bytes},
            sources=preview.source_preconditions,
            preview_token=preview.preview_token,
            actor=actor,
        )

    def render_definition_candidate(
        self,
        *,
        state: ProjectDefinitionState,
        patch: ProjectDefinitionPatch,
        pack: VerticalPack,
        audit_at: str,
    ) -> ProjectDefinitionCandidate:
        updated = self._apply_definition_patch(state, patch, pack, audit_at=audit_at)
        payload = _definition_state_payload(updated)
        semantic_payload = _definition_semantic_payload(payload)
        operation_ids = tuple(str(item.get("op") or "") for item in patch.operations)
        changed_sections = tuple(
            sorted(
                {
                    str(item.get("section_id") or "")
                    for item in patch.operations
                    if str(item.get("section_id") or "")
                }
            )
        )
        return ProjectDefinitionCandidate(
            state=updated,
            payload=payload,
            semantic_payload=semantic_payload,
            candidate_bytes=yaml_dump(payload).encode("utf-8"),
            semantic_sha256=semantic_sha256(semantic_payload),
            operation_ids=operation_ids,
            changed_sections=changed_sections,
        )

    def _read_definition_patch(self, patch_path: Path) -> ProjectDefinitionPatch:
        source = patch_path if patch_path.is_absolute() else self.root / patch_path
        payload = _read_yaml_mapping(source)
        patch = _definition_patch_from_payload(payload, target=str(source))
        obsolete_question_operations = {
            str(item.get("op") or "")
            for item in patch.operations
            if str(item.get("op") or "") in {"add_open_question", "close_open_question"}
        }
        if obsolete_question_operations:
            raise ValueError(
                "P2P352_OBSOLETE_DEFINITION_QUESTION_OPERATION: the current workspace uses project-question "
                "commands; run `p2p project readiness questions status` instead."
            )
        return patch

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
        return view.state, self._definition_validation_pack(view.state)

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

    def read_proposal_vertical_coverage(
        self,
        proposal_id: str,
        *,
        proposal_dir: Path | None = None,
    ) -> ProposalVerticalCoverage | None:
        proposal_dir = proposal_dir or self.find_proposal_dir(proposal_id)
        path = proposal_dir / "vertical-coverage.yml"
        if not path.exists():
            return None
        payload = _read_yaml_mapping(path)
        return _proposal_vertical_coverage_from_payload(proposal_id, path, payload, self.root)

    def proposal_vertical_coverage_status(self, proposal_id: str) -> ProposalVerticalCoverageStatus:
        return self.proposal_vertical_coverage_statuses((proposal_id,))[proposal_id]

    def vertical_read_state(self) -> VerticalReadState:
        active, pack = self._active_vertical_and_pack()
        base_section_ids = (
            frozenset(
                section.section_id
                for section in self._load_available_pack(pack.extends).sections
            )
            if pack.extends
            else frozenset()
        )
        terms_by_section = {
            section.section_id: tuple(_vertical_section_terms(section, pack))
            for section in pack.sections
        }
        term_frequency: dict[str, int] = {}
        for terms in terms_by_section.values():
            for term in terms:
                term_frequency[term] = term_frequency.get(term, 0) + 1
        readiness_terms_by_section: dict[str, tuple[str, ...]] = {}
        for section in pack.sections:
            terms = {section.section_id.replace("_", " "), section.title.lower()}
            terms.update(_important_words(section.title))
            terms.update(_important_words(section.purpose))
            for rubric in pack.rubrics:
                if rubric.section_id == section.section_id:
                    terms.update(keyword.lower() for keyword in rubric.keywords)
            readiness_terms_by_section[section.section_id] = tuple(sorted(terms))
        return VerticalReadState(
            active=active,
            pack=pack,
            valid_section_ids=frozenset(terms_by_section),
            terms_by_section=MappingProxyType(terms_by_section),
            term_frequency=MappingProxyType(term_frequency),
            base_section_ids=base_section_ids,
            readiness_terms_by_section=MappingProxyType(readiness_terms_by_section),
        )

    def proposal_vertical_coverage_statuses(
        self,
        proposal_ids: tuple[str, ...] | list[str],
        *,
        state: VerticalReadState | None = None,
    ) -> dict[str, ProposalVerticalCoverageStatus]:
        read_state = state or self.vertical_read_state()
        selected = tuple(sorted(set(proposal_ids)))
        proposal_dirs = self._proposal_directories_for(selected)
        return {
            proposal_id: self._proposal_vertical_coverage_status(
                proposal_id,
                read_state,
                proposal_dir=proposal_dirs[proposal_id],
            )
            for proposal_id in selected
        }

    def _proposal_vertical_coverage_status(
        self,
        proposal_id: str,
        state: VerticalReadState,
        *,
        proposal_dir: Path | None = None,
    ) -> ProposalVerticalCoverageStatus:
        proposal_dir = proposal_dir or self.find_proposal_dir(proposal_id)
        path = proposal_dir / "vertical-coverage.yml"
        relative = relative_to_root(path, self.root)
        if not path.exists():
            return ProposalVerticalCoverageStatus(
                proposal_id=proposal_id,
                state="missing",
                path=relative,
                message="Proposal has no declared vertical coverage.",
            )
        try:
            payload = _read_yaml_mapping(path)
            coverage = _proposal_vertical_coverage_from_payload(
                proposal_id,
                path,
                payload,
                self.root,
            )
            self.validate_proposal_vertical_coverage_candidate(
                proposal_id,
                payload,
                active=state.active,
                pack=state.pack,
            )
        except ValueError as exc:
            return ProposalVerticalCoverageStatus(
                proposal_id=proposal_id,
                state="invalid",
                path=relative,
                message=str(exc),
            )
        if coverage.vertical_id != state.active.vertical_id:
            return ProposalVerticalCoverageStatus(
                proposal_id=proposal_id,
                state="vertical_mismatch",
                path=relative,
                coverage=coverage,
                message=(
                    f"Coverage vertical `{coverage.vertical_id}` differs from active "
                    f"`{state.active.vertical_id}`."
                ),
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
        *,
        active: ActiveProjectVertical | None = None,
        pack: VerticalPack | None = None,
    ) -> None:
        validate_vertical_coverage_payload(payload, target=f"vertical coverage for {proposal_id}")
        coverage = payload["vertical_coverage"]
        assert isinstance(coverage, dict)
        if str(coverage.get("proposal_id") or "") != proposal_id:
            raise ValueError("Vertical coverage proposal_id does not match the target proposal.")
        vertical_id = str(coverage.get("vertical_id") or "")
        if active is None or pack is None:
            resolved_active, resolved_pack = self._active_vertical_and_pack()
            active = active or resolved_active
            pack = pack or resolved_pack
        if vertical_id != active.vertical_id:
            raise ValueError(
                f"Vertical coverage must target active vertical `{active.vertical_id}`, not `{vertical_id}`."
            )
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
        return self.suggest_proposal_vertical_coverages((proposal_id,))[proposal_id]

    def suggest_proposal_vertical_coverages(
        self,
        proposal_ids: tuple[str, ...] | list[str],
        *,
        state: VerticalReadState | None = None,
    ) -> dict[str, ProposalVerticalCoverageSuggestion]:
        read_state = state or self.vertical_read_state()
        selected = tuple(sorted(set(proposal_ids)))
        proposal_dirs = self._proposal_directories_for(selected)
        patterns = {
            term: re.compile(r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])")
            for term in read_state.term_frequency
        }
        return {
            proposal_id: self._suggest_proposal_vertical_coverage(
                proposal_id,
                read_state,
                patterns,
                proposal_dir=proposal_dirs[proposal_id],
            )
            for proposal_id in selected
        }

    def _suggest_proposal_vertical_coverage(
        self,
        proposal_id: str,
        state: VerticalReadState,
        patterns: dict[str, re.Pattern[str]],
        *,
        proposal_dir: Path | None = None,
    ) -> ProposalVerticalCoverageSuggestion:
        proposal_dir = proposal_dir or self.find_proposal_dir(proposal_id)
        active = state.active
        pack = state.pack
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
        candidates: list[VerticalCoverageSuggestionSection] = []
        suppressed: list[str] = []
        for section in pack.sections:
            evidence: list[dict[str, object]] = []
            score = 0.0
            for term in state.terms_by_section[section.section_id]:
                frequency = state.term_frequency.get(term, 1)
                if frequency > max(2, int(len(pack.sections) * 0.35)):
                    continue
                pattern = patterns[term]
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

    def _proposal_directories_for(
        self,
        proposal_ids: tuple[str, ...],
    ) -> dict[str, Path]:
        requested = set(proposal_ids)
        if not requested:
            return {}
        proposals_dir = self.p2p_dir / "proposals"
        if not proposals_dir.exists():
            raise ValueError("No .p2p/proposals directory found.")
        result: dict[str, Path] = {}
        for path in sorted(proposals_dir.iterdir(), key=lambda item: item.name):
            if not path.is_dir() or path.is_symlink():
                continue
            parts = path.name.split("-", 2)
            if len(parts) < 2 or parts[0] != "PROP" or not parts[1].isdigit():
                continue
            proposal_id = f"PROP-{parts[1]}"
            if proposal_id not in requested:
                continue
            if proposal_id in result:
                raise ValueError(f"Ambiguous proposal ID: {proposal_id}")
            result[proposal_id] = path
        missing = tuple(sorted(requested - set(result)))
        if missing:
            raise ValueError(f"Proposal not found: {missing[0]}")
        return result

    def project_readiness_review(self, *, vertical_id: str | None = None) -> ProjectReadinessReview:
        snapshot = self.project_readiness_snapshot(vertical_id=vertical_id)
        readiness = ProjectReadinessGapService().classify(snapshot)
        section_reviews: list[VerticalSectionReview] = []
        missing_capisaldi: list[str] = []
        generated_questions: list[str] = []
        for section in snapshot.sections:
            proposals = list(section.declared_proposals)
            if section.active_declared_proposals:
                status = "covered"
            elif proposals:
                status = "partial"
            elif section.definition_status == "complete":
                status = "defined"
            elif section.definition_status == "not_applicable" or not section.required:
                status = "not_applicable"
            else:
                status = "missing"
            gaps: list[str] = []
            if not proposals and section.required and section.definition_status != "not_applicable":
                gaps.append("missing_proposal_coverage")
            if status == "partial":
                gaps.append("proposal_coverage_not_accepted")
            questions: list[str] = []
            if section.required and section.definition_status not in {"complete", "not_applicable"}:
                gaps.append("project_definition_incomplete")
                missing_capisaldi.append(section.section_id)
                questions = list(section.declared_questions[:3])
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
                    heuristic_proposals=list(section.heuristic_proposals),
                    definition_status=section.definition_status,
                )
            )

        generated_questions = list(dict.fromkeys(generated_questions))
        suggested: list[str] = []
        if snapshot.fallback_used:
            suggested.append("p2p project vertical list")
        if readiness.gaps:
            suggested.append(readiness.gaps[0].next_operation)
        if any(section.status == "defined" for section in section_reviews):
            suggested.append("Review whether definition-only sections need declared proposal evidence.")
        if not suggested:
            suggested.append("p2p project readiness review")
        detail_limit = PROJECT_READINESS_REVIEW_DETAIL_LIMIT
        return ProjectReadinessReview(
            active_vertical_id=snapshot.identity.vertical_id,
            vertical_source=snapshot.vertical_source,
            fallback_used=snapshot.fallback_used,
            sections=section_reviews,
            unmapped_proposals=list(snapshot.unmapped_proposals[:detail_limit]),
            missing_capisaldi=missing_capisaldi,
            generated_questions=generated_questions[:detail_limit],
            suggested_next=list(dict.fromkeys(suggested)),
            definition_valid=snapshot.definition_valid,
            heuristic_mappings={
                section.section_id: list(section.heuristic_proposals)
                for section in snapshot.sections
                if section.heuristic_proposals
            },
            snapshot_fingerprint=readiness.snapshot.fingerprint,
            gaps=list(readiness.gaps[:detail_limit]),
            gap_counts=dict(readiness.counts),
            diagnostics=list(readiness.diagnostics),
            unmapped_proposals_total=len(snapshot.unmapped_proposals),
            unmapped_proposals_truncated=len(snapshot.unmapped_proposals) > detail_limit,
            generated_questions_total=len(generated_questions),
            generated_questions_truncated=len(generated_questions) > detail_limit,
        )

    def project_readiness_result(self, *, vertical_id: str | None = None) -> ProjectReadinessResult:
        return ProjectReadinessGapService().classify(self.project_readiness_snapshot(vertical_id=vertical_id))

    def project_readiness_snapshot(self, *, vertical_id: str | None = None) -> ProjectReadinessSnapshot:
        if vertical_id is None and self.vertical_memory_view is not None:
            memory = self.vertical_memory_view()
            schema_path = self.p2p_dir / "project" / "workspace-schema.yml"
            permissions_path = self.p2p_dir / "project" / "permissions.yml"
            schema_content = schema_path.read_bytes() if schema_path.is_file() else None
            permissions_content = permissions_path.read_bytes() if permissions_path.is_file() else None
            schema_version, schema_state = self._readiness_workspace_schema_identity(
                schema_content
            )
            return readiness_snapshot_from_vertical_memory(
                memory,
                workspace_schema_version=schema_version,
                workspace_schema_state=schema_state,
                owner_available=self._readiness_owner_available(permissions_content),
                unmapped_proposals=unmapped_proposal_ids_from_vertical_memory(
                    memory,
                    (item.proposal_id for item in self.proposal_summaries()),
                ),
            )
        access = ProjectReadinessSourceAccess(root=self.root, reader=self.readiness_source_reader)
        active_path = self._active_vertical_path()
        active_content = access.read_optional(active_path)
        if active_content is None:
            active = ActiveProjectVertical(
                vertical_id=BASE_PROJECT_VERTICAL_ID,
                source=FALLBACK_SOURCE,
                path=None,
                fallback_used=True,
            )
        else:
            try:
                active_payload = load_yaml(active_content)
            except (UnicodeDecodeError, yaml.YAMLError) as exc:
                raise ValueError(f"Invalid project vertical state: {active_path}: {exc}") from exc
            if not isinstance(active_payload, dict) or not isinstance(active_payload.get("project_vertical"), dict):
                raise ValueError(f"Invalid project vertical state: {active_path}")
            active_state = active_payload["project_vertical"]
            assert isinstance(active_state, dict)
            active_id = str(active_state.get("active_vertical_id") or "").strip()
            if not active_id:
                raise ValueError(f"Invalid project vertical state: missing active_vertical_id in {active_path}")
            active = ActiveProjectVertical(
                vertical_id=active_id,
                source=str(active_state.get("active_source") or ""),
                path=None,
                selected_at=str(active_state.get("selected_at") or ""),
                selected_by=str(active_state.get("selected_by") or ""),
                fallback_used=bool(active_state.get("fallback_used") or False),
                coordinate=str(active_state.get("active_vertical_coordinate") or ""),
            )
        lock_path = self._vertical_lock_path()
        lock_content = access.read_optional(lock_path)
        parsed_lock: VerticalLock | None = None
        lock_error = ""
        if lock_content is not None:
            try:
                lock_payload = load_yaml(lock_content)
                if not isinstance(lock_payload, dict):
                    raise ValueError("expected a YAML mapping")
                parsed_lock = _vertical_lock_from_payload(lock_path, lock_payload, self.root)
            except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
                lock_error = str(exc)
        reference = vertical_id
        if reference is None:
            reference = (
                parsed_lock.coordinate
                if parsed_lock is not None and parsed_lock.coordinate
                else active.coordinate or active.vertical_id
            )
        pack = self._load_available_pack(reference)
        fallback_used = active.fallback_used and vertical_id is None
        proposal_matches: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        heuristic_matches: dict[str, list[str]] = {section.section_id: [] for section in pack.sections}
        proposal_statuses: dict[str, str] = {}
        mapped_proposals: set[str] = set()
        unmapped: list[str] = []
        source_hashes: dict[str, str] = {"vertical_pack": _pack_checksum(pack)}
        snapshot_diagnostics: list[ProjectReadinessDiagnostic] = []
        if active_content is not None:
            source_hashes[relative_to_root(active_path, self.root).as_posix()] = hashlib.sha256(
                active_content
            ).hexdigest()
        lock_checksum = ""
        if lock_content is not None:
            if lock_error:
                snapshot_diagnostics.append(
                    ProjectReadinessDiagnostic(
                        code="P2P254_PROJECT_VERTICAL_LOCK_INVALID",
                        severity="error",
                        message=lock_error,
                        suggested_command="p2p project vertical lock repair --actor owner",
                    )
                )
            elif parsed_lock is not None:
                lock_checksum = parsed_lock.checksum
                lock_mismatch = (
                    parsed_lock.vertical_id != pack.vertical_id
                    or parsed_lock.version != pack.version
                    or bool(parsed_lock.coordinate) != bool(pack.coordinate)
                    or (
                        bool(parsed_lock.coordinate)
                        and parsed_lock.coordinate != pack.coordinate
                    )
                    or parsed_lock.checksum != _pack_checksum(pack)
                )
                active_mismatch = vertical_id is None and (
                    active.vertical_id != pack.vertical_id
                    or (
                        bool(active.coordinate)
                        and active.coordinate != (pack.coordinate or "")
                    )
                )
                if lock_mismatch or active_mismatch:
                    snapshot_diagnostics.append(
                        ProjectReadinessDiagnostic(
                            code="P2P254_PROJECT_VERTICAL_LOCK_INVALID",
                            severity="error",
                            message="Project vertical active state or lock does not match the selected vertical pack.",
                            suggested_command="p2p project vertical lock repair --actor owner",
                        )
                    )
            source_hashes[relative_to_root(lock_path, self.root).as_posix()] = hashlib.sha256(
                lock_content
            ).hexdigest()

        base_section_ids: set[str] = set()
        if pack.extends:
            base_section_ids = {
                section.section_id for section in self._load_available_pack(pack.extends).sections
            }

        proposals_snapshot = list(self.proposal_summaries())
        for proposal in proposals_snapshot:
            proposal_statuses[proposal.proposal_id] = proposal.status
            proposal_dir = self.find_proposal_dir(proposal.proposal_id)
            coverage_path = proposal_dir / "vertical-coverage.yml"
            coverage_content = access.read_optional(coverage_path)
            if coverage_content is not None:
                source_hashes[relative_to_root(coverage_path, self.root).as_posix()] = hashlib.sha256(
                    coverage_content
                ).hexdigest()
            coverage = self._proposal_vertical_coverage_from_content(
                proposal.proposal_id,
                coverage_path,
                coverage_content,
            )
            mapped_sections = (
                [section.section_id for section in coverage.sections]
                if coverage and coverage.vertical_id == pack.vertical_id
                else []
            )
            text_parts: list[str] = []
            for filename in ("proposal.md", "decision.md", "suggested-scope.md", "risks.md"):
                path = proposal_dir / filename
                content = access.read_optional(path)
                if content is None:
                    continue
                source_hashes[relative_to_root(path, self.root).as_posix()] = hashlib.sha256(content).hexdigest()
                text_parts.append(content.decode("utf-8"))
            heuristic_sections = self._heuristic_sections_from_text(
                pack,
                "\n".join(text_parts).lower(),
                base_section_ids=base_section_ids,
            )
            for section_id in heuristic_sections:
                heuristic_matches.setdefault(section_id, []).append(proposal.proposal_id)
            if mapped_sections:
                mapped_proposals.add(proposal.proposal_id)
                for section_id in mapped_sections:
                    proposal_matches.setdefault(section_id, []).append(proposal.proposal_id)
            else:
                unmapped.append(proposal.proposal_id)

        definition_path = self._definition_state_path()
        definition_content = access.read_optional(definition_path)
        if definition_content is not None:
            source_hashes[relative_to_root(definition_path, self.root).as_posix()] = hashlib.sha256(
                definition_content
            ).hexdigest()
        definition_view = self._project_definition_view_from_content(pack, definition_content)
        definition_sections = {
            item.section_id: item
            for item in definition_view.state.sections
        } if definition_view.valid and definition_view.state is not None else {}
        section_snapshots: list[ProjectReadinessSectionSnapshot] = []
        for section in sorted(pack.sections, key=lambda item: item.priority):
            proposals = sorted(dict.fromkeys(proposal_matches.get(section.section_id, [])))
            heuristic_proposals = sorted(dict.fromkeys(heuristic_matches.get(section.section_id, [])))
            definition_section = definition_sections.get(section.section_id)
            definition_status = definition_section.status if definition_section else "not_initialized"
            active_proposals = tuple(
                proposal_id
                for proposal_id in proposals
                if is_active_project_projection(proposal_statuses.get(proposal_id, ""))
            )
            section_snapshots.append(
                ProjectReadinessSectionSnapshot(
                    section_id=section.section_id,
                    title=section.title,
                    required=section.required,
                    priority=section.priority,
                    definition_status=definition_status,
                    missing_required_fields=(
                        tuple(definition_section.missing_required_fields) if definition_section else ()
                    ),
                    assumptions=tuple(
                        ProjectReadinessAssumptionSnapshot(
                            assumption_id=item.assumption_id,
                            status=item.status,
                            field_id=item.field_id,
                        )
                        for item in (definition_section.assumptions if definition_section else [])
                    ),
                    open_blocker_ids=tuple(
                        item.blocker_id
                        for item in (definition_section.blockers if definition_section else [])
                        if item.status == "open"
                    ),
                    declared_proposals=tuple(proposals),
                    active_declared_proposals=active_proposals,
                    heuristic_proposals=tuple(heuristic_proposals),
                    declared_questions=tuple(
                        question.question for question in pack.questions if question.section_id == section.section_id
                    ),
                )
            )

        schema_content: bytes | None = None
        questions_content: bytes | None = None
        permissions_content: bytes | None = None
        for path in (
            self.p2p_dir / "project" / "workspace-schema.yml",
            self.p2p_dir / "project" / "questions.yml",
            self.p2p_dir / "project" / "permissions.yml",
        ):
            content = access.read_optional(path)
            if content is None:
                continue
            source_hashes[relative_to_root(path, self.root).as_posix()] = hashlib.sha256(content).hexdigest()
            if path.name == "workspace-schema.yml":
                schema_content = content
            elif path.name == "questions.yml":
                questions_content = content
            elif path.name == "permissions.yml":
                permissions_content = content
        if questions_content is not None:
            try:
                question_artifact = ProjectQuestionStateService(
                    root=self.root,
                    p2p_dir=self.p2p_dir,
                ).parse_bytes(questions_content, target=".p2p/project/questions.yml")
                question_by_section: dict[str, list[ProjectReadinessQuestionSnapshot]] = {}
                for question in question_artifact.questions:
                    question_by_section.setdefault(question.section_id, []).append(
                        ProjectReadinessQuestionSnapshot(
                            question_id=question.question_id,
                            revision=question.revision,
                            state=question.state.value,
                            target_kind=question.target.kind,
                            target_id=question.target.target_id,
                            applicability=(
                                "applicable"
                                if question.applicability.value == "active"
                                else question.applicability.value
                            ),
                        )
                    )
                section_snapshots = [
                    replace(
                        section,
                        question_states=tuple(
                            sorted(
                                question_by_section.get(section.section_id, []),
                                key=lambda item: item.question_id,
                            )
                        ),
                    )
                    for section in section_snapshots
                ]
            except ValueError as exc:
                snapshot_diagnostics.append(
                    ProjectReadinessDiagnostic(
                        code="P2P340_PROJECT_QUESTIONS_INVALID",
                        severity="error",
                        message=str(exc),
                        suggested_command="p2p project readiness questions status --format json",
                    )
                )
        source_hashes["proposal_summaries"] = semantic_sha256(
            [
                {"proposal_id": item.proposal_id, "title": item.title, "status": item.status}
                for item in sorted(proposals_snapshot, key=lambda value: value.proposal_id)
            ]
        )
        workspace_schema_version, workspace_schema_state = self._readiness_workspace_schema_identity(
            schema_content
        )
        owner_available = self._readiness_owner_available(permissions_content)
        profile = definition_view.state.profile if definition_view.state else "default"
        modules = definition_view.state.modules if definition_view.state else []
        diagnostics = tuple(snapshot_diagnostics) + tuple(
            ProjectReadinessDiagnostic(
                code=issue.code or "P2P255_PROJECT_DEFINITION_INVALID",
                severity=issue.severity,
                message=issue.message,
                suggested_command="p2p project definition show",
            )
            for issue in definition_view.issues
        )
        return ProjectReadinessSnapshotBuilder().build(
            workspace_schema_version=workspace_schema_version,
            workspace_schema_state=workspace_schema_state,
            vertical_id=pack.vertical_id,
            vertical_version=pack.version,
            vertical_lock_checksum=lock_checksum,
            profile=profile,
            modules=modules,
            source_hashes=source_hashes,
            policy_versions={"gap": PROJECT_READINESS_GAP_POLICY_VERSION, "snapshot": 1},
            definition_valid=definition_view.valid,
            definition_exists=definition_view.exists,
            fallback_used=fallback_used,
            vertical_source=pack.source if not fallback_used else FALLBACK_SOURCE,
            sections=section_snapshots,
            unmapped_proposals=unmapped,
            owner_available=owner_available,
            diagnostics=diagnostics,
        )

    def _project_definition_view_from_content(
        self,
        pack: VerticalPack,
        content: bytes | None,
    ) -> ProjectDefinitionView:
        path = self._definition_state_path()
        display_path = relative_to_root(path, self.root)
        if content is None:
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
            payload = load_yaml(content)
            if not isinstance(payload, dict):
                raise ValueError(f"Project definition must be a YAML mapping: {path}")
            state = _definition_state_from_payload(payload, path=path)
            issues = self._definition_state_issues(state, pack)
        except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
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

    def _proposal_vertical_coverage_from_content(
        self,
        proposal_id: str,
        path: Path,
        content: bytes | None,
    ) -> ProposalVerticalCoverage | None:
        if content is None:
            return None
        try:
            payload = load_yaml(content)
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"Invalid proposal vertical coverage {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid proposal vertical coverage {path}: expected a YAML mapping.")
        return _proposal_vertical_coverage_from_payload(proposal_id, path, payload, self.root)

    def _readiness_workspace_schema_identity(self, content: bytes | None) -> tuple[int, str]:
        if content is None:
            return 0, "missing"
        try:
            payload = load_yaml(content)
            if not isinstance(payload, dict):
                return -1, "invalid"
            schema = payload.get("workspace_schema")
            if not isinstance(schema, dict):
                return -1, "invalid"
            return int(schema.get("current_version")), "declared"
        except (UnicodeDecodeError, yaml.YAMLError, TypeError, ValueError):
            return -1, "invalid"

    def _readiness_owner_available(self, content: bytes | None) -> bool:
        if content is None:
            return False
        try:
            payload = load_yaml(content)
        except (UnicodeDecodeError, yaml.YAMLError):
            return False
        if not isinstance(payload, dict) or not isinstance(payload.get("identities"), dict):
            return False
        identities = payload["identities"]
        assert isinstance(identities, dict)
        return any(isinstance(item, dict) and item.get("role") == "owner" for item in identities.values())

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
                self._active_vertical_and_pack()
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
        active, active_pack = self._active_vertical_and_pack()
        pack = active_pack if vertical_id == active.vertical_id else self._load_available_pack(vertical_id)
        section_ids = {section.section_id for section in pack.sections}
        for item in coverage.get("sections", []):
            if isinstance(item, dict):
                section_id = str(item.get("id") or "")
                if section_id not in section_ids:
                    raise ValueError(f"Invalid proposal vertical coverage {path}: unknown section id `{section_id}` for vertical `{vertical_id}`.")

    def _extension_issues(self, pack: VerticalPack) -> list[VerticalValidationIssue]:
        if not pack.extends:
            return []
        try:
            self._load_available_pack(pack.extends)
        except ValueError:
            pass
        else:
            return []
        return [
            VerticalValidationIssue(
                severity="error",
                field="vertical.extends",
                message=f"unknown base vertical `{pack.extends}`",
            )
        ]

    def _heuristic_sections_for_proposal(self, proposal: _ProposalSummaryLike, pack: VerticalPack) -> list[str]:
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
        return self._heuristic_sections_from_text(pack, text)

    def _heuristic_sections_from_text(
        self,
        pack: VerticalPack,
        text: str,
        *,
        base_section_ids: set[str] | None = None,
    ) -> list[str]:
        if base_section_ids is None and pack.extends:
            base = self._load_available_pack(pack.extends)
            base_section_ids = {section.section_id for section in base.sections}
        base_section_ids = base_section_ids or set()
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

    def _available_pack_inventory(self) -> list[VerticalPack]:
        return [
            *self._internal_packs(),
            *self._installed_user_packs(),
            *self._installed_p2p_home_packs(),
            *self._project_local_packs(),
        ]

    def _load_available_pack(self, vertical_id: str) -> VerticalPack:
        pack = self._select_available_pack(vertical_id)
        return self._compose_available_pack(pack)

    def _select_available_pack(
        self,
        reference: str,
        *,
        stack: tuple[str, ...] = (),
    ) -> VerticalPack:
        requested = str(reference).strip()
        inventory = self._available_pack_inventory()
        if "/" in requested or "@" in requested:
            coordinate = str(VerticalCoordinate.parse(requested))
            candidates = [pack for pack in inventory if pack.coordinate == coordinate]
            if not candidates:
                raise ValueError(
                    "P2P_VERTICAL_NOT_FOUND: unknown project vertical "
                    f"`{reference}`; run `p2p project vertical list`"
                )
            semantic_checksums = {
                _pack_checksum(self._compose_available_pack(pack, stack=stack))
                for pack in candidates
            }
            if len(semantic_checksums) > 1:
                raise ValueError(
                    "P2P_VERTICAL_COORDINATE_CONFLICT: exact coordinate "
                    f"`{coordinate}` resolves to different semantic checksums"
                )
            return candidates[-1]

        exact_id = requested.lower()
        if not exact_id:
            raise ValueError("Vertical ID is required.")
        candidates = [pack for pack in inventory if pack.vertical_id == exact_id]
        if not candidates:
            normalized = _normalize_vertical_id(requested)
            candidates = [pack for pack in inventory if pack.vertical_id == normalized]
        if not candidates:
            raise ValueError(
                "P2P_VERTICAL_NOT_FOUND: unknown project vertical "
                f"`{reference}`; run `p2p project vertical list`"
            )
        coordinates = {pack.coordinate for pack in candidates}
        if len(coordinates) > 1:
            raise ValueError(
                "P2P_VERTICAL_AMBIGUOUS_REFERENCE: bare vertical reference "
                f"`{reference}` matches {', '.join(sorted(coordinates))}; use an exact coordinate"
            )
        return self._select_available_pack(next(iter(coordinates)), stack=stack)

    def _compose_available_pack(
        self,
        pack: VerticalPack,
        *,
        stack: tuple[str, ...] = (),
    ) -> VerticalPack:
        identity = pack.coordinate or pack.vertical_id
        if identity in stack:
            cycle = " -> ".join([*stack, identity])
            raise ValueError(f"P2P_VERTICAL_INHERITANCE_CYCLE: {cycle}")
        if not pack.extends:
            return pack
        next_stack = (*stack, identity)
        base = self._select_available_pack(pack.extends, stack=next_stack)
        composed_base = self._compose_available_pack(base, stack=next_stack)
        return _overlay_pack(composed_base, pack)

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

    def resolve_pack(self, reference: str) -> ResolvedVerticalPack:
        return self._resolve_available_pack(reference)

    def load_explicit_pack(self, source: Path) -> VerticalPack:
        return self._load_pack_from_path(source, source=EXPLICIT_SOURCE)

    def compose_explicit_pack(self, source: Path) -> VerticalPack:
        pack = self.load_explicit_pack(source)
        if not pack.extends:
            return pack
        base = self._load_available_pack(pack.extends)
        return _overlay_pack(base, pack)

    @staticmethod
    def serialized_pack(pack: VerticalPack) -> dict[str, object]:
        return _pack_payload(pack)

    @staticmethod
    def semantic_pack_checksum(pack: VerticalPack) -> str:
        return _pack_checksum(pack)

    def _load_target_for_validation(self, target: str) -> tuple[VerticalPack, dict[str, object]]:
        path = Path(target)
        if path.exists():
            source = path if path.is_absolute() else self.root / path
            if not source.is_dir() or source.is_symlink():
                raise ValueError(
                    "P2P_VERTICAL_CANONICAL_LAYOUT_REQUIRED: vertical packs must be "
                    "schema-3 directories"
                )
            if not (source / "manifest.yml").exists():
                raise ValueError(
                    "Canonical vertical pack is missing required paths: manifest.yml"
                )
            payload = self._canonical_pack_payload(source)
            pack_path = source / "manifest.yml"
            return _pack_from_payload(payload, source=EXPLICIT_SOURCE, path=pack_path), payload
        pack = self._load_available_pack(target)
        return pack, _pack_payload(pack)

    def _load_pack_from_path(self, pack_source: Path, *, source: str = PROJECT_LOCAL_SOURCE) -> VerticalPack:
        if not pack_source.is_absolute():
            pack_source = self.root / pack_source
        if not pack_source.is_dir() or pack_source.is_symlink():
            raise ValueError(
                "P2P_VERTICAL_CANONICAL_LAYOUT_REQUIRED: vertical packs must be schema-3 directories"
            )
        payload = self._canonical_pack_payload(pack_source)
        path = pack_source / "manifest.yml"
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
                packs.append(self._load_pack_from_path(pack_path.parent, source=source))
            except ValueError:
                continue
        return packs

    def _project_vertical_pack_paths(self, root: Path) -> list[Path]:
        if not root.exists():
            return []
        return sorted(
            [
            path
            for path in root.rglob("manifest.yml")
            if path.is_file()
            and not path.is_symlink()
            ],
            key=lambda item: item.as_posix(),
        )

    def _internal_packs(self) -> list[VerticalPack]:
        packs: list[VerticalPack] = []
        root = resources.files("p2p_engine.resources.verticals")
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            manifest = child / "manifest.yml"
            if not manifest.is_file():
                continue
            payload = self._canonical_pack_payload(Path(str(child)))
            path = Path(str(manifest))
            if not isinstance(payload, dict):
                continue
            validate_vertical_pack_payload(payload, target=child.name)
            packs.append(_pack_from_payload(payload, source=INTERNAL_SOURCE, path=path))
        return packs

    def _canonical_pack_payload(self, pack_root: Path) -> dict[str, object]:
        required = (
            pack_root / "manifest.yml",
            pack_root / "vertical.yml",
            pack_root / "sections",
            pack_root / "rubrics.yml",
        )
        missing = [path.name for path in required if not path.exists()]
        if missing:
            raise ValueError(
                "Canonical vertical pack is missing required paths: "
                + ", ".join(sorted(missing))
            )
        if not (pack_root / "sections").is_dir():
            raise ValueError("Canonical vertical pack `sections` must be a directory.")
        manifest = _unwrap_mapping(_read_yaml_mapping(pack_root / "manifest.yml"), "manifest")
        vertical = _unwrap_mapping(_read_yaml_mapping(pack_root / "vertical.yml"), "vertical")
        for field in ("schema_version", "id", "name", "version"):
            if field not in manifest or field not in vertical:
                raise ValueError(
                    f"P2P_VERTICAL_CANONICAL_LAYOUT_REQUIRED: `{field}` must be declared "
                    "in both manifest.yml and vertical.yml"
                )
            if manifest[field] != vertical[field]:
                raise ValueError(
                    f"P2P_VERTICAL_IDENTITY_MISMATCH: `{field}` differs between "
                    "manifest.yml and vertical.yml"
                )
        if manifest.get("extends") != vertical.get("extends"):
            raise ValueError(
                "P2P_VERTICAL_IDENTITY_MISMATCH: `extends` differs between "
                "manifest.yml and vertical.yml"
            )
        section_paths = sorted((pack_root / "sections").glob("*.yml"))
        if not section_paths:
            raise ValueError("Canonical vertical pack must define at least one split section.")
        if _mapping_list(vertical.get("sections")):
            raise ValueError(
                "Canonical vertical pack duplicates sections in vertical.yml and sections/."
            )
        if _mapping_list(vertical.get("rubrics")):
            raise ValueError(
                "Canonical vertical pack duplicates rubrics in vertical.yml and rubrics.yml."
            )
        sections = [
            _unwrap_mapping(_read_yaml_mapping(path), "section")
            for path in section_paths
        ]
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
            coordinate=resolved.pack.coordinate,
            dependencies=list(resolved.pack.manifest.dependencies) if resolved.pack.manifest else [],
        )
        write_yaml_atomic(path, _vertical_lock_payload(lock))
        return lock

    def _read_vertical_lock(self, path: Path) -> VerticalLock:
        payload = _read_yaml_mapping(path)
        return _vertical_lock_from_payload(path, payload, self.root)

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
        structure_id = ""
        structure_revision = 0
        structure_checksum = ""
        structure_path = self.p2p_dir / "project" / "structure.yml"
        if structure_path.is_file() and not structure_path.is_symlink():
            structure = ProjectStructureService(
                root=self.root,
                p2p_dir=self.p2p_dir,
            ).show(include_retired=True)
            structure_id = structure.structure_id
            structure_revision = structure.revision
            structure_checksum = structure.checksum
            fields_by_section: dict[str, list[StructureField]] = {}
            for field in structure.fields:
                if field.lifecycle == "active":
                    fields_by_section.setdefault(field.section_id, []).append(field)
            for section in sorted(
                (item for item in structure.sections if item.lifecycle == "active"),
                key=lambda item: (item.order, item.section_id),
            ):
                missing = [
                    field.field_id
                    for field in sorted(
                        fields_by_section.get(section.section_id, []),
                        key=lambda item: (item.order, item.field_id),
                    )
                    if field.required
                ]
                sections.append(
                    ProjectDefinitionSectionState(
                        section_id=section.section_id,
                        status="missing" if section.required else "not_applicable",
                        missing_required_fields=missing,
                    )
                )
        else:
            for section in sorted(resolved.pack.sections, key=lambda item: item.priority):
                fields = _section_fields(section, resolved.pack)
                missing = [field.field_id for field in fields if field.required]
                sections.append(
                    ProjectDefinitionSectionState(
                        section_id=section.section_id,
                        status="missing" if section.required else "not_applicable",
                        missing_required_fields=missing,
                    )
                )
        return ProjectDefinitionState(
            schema_version=PROJECT_DEFINITION_SCHEMA_VERSION,
            vertical_id=resolved.pack.vertical_id,
            vertical_version=resolved.pack.version,
            profile=profile or "default",
            modules=list(dict.fromkeys(modules)),
            lock_checksum=resolved.checksum,
            sections=sections,
            next_suggested_action={},
            history=[
                ProjectDefinitionHistoryEntry(
                    at=audit_date or date.today().isoformat(),
                    actor=actor,
                    operation="initialize_definition_state",
                )
            ],
            structure_id=structure_id,
            structure_revision=structure_revision,
            structure_checksum=structure_checksum,
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
        structure_path = self.p2p_dir / "project" / "structure.yml"
        uses_project_structure = structure_path.is_file() and not structure_path.is_symlink()
        if uses_project_structure:
            structure = ProjectStructureService(
                root=self.root,
                p2p_dir=self.p2p_dir,
            ).show()
            section_ids = set(structure.active_section_ids())
            field_ids_by_section = {section_id: set() for section_id in section_ids}
            for field in structure.fields:
                if field.lifecycle != "active" or field.section_id not in section_ids:
                    continue
                field_ids_by_section.setdefault(field.section_id, set()).add(field.field_id)
            if state.structure_id != structure.structure_id:
                issues.append(
                    VerticalValidationIssue(
                        "error",
                        "project_definition.structure.id",
                        "definition structure identity does not match the project-owned structure",
                        "P2P255_PROJECT_DEFINITION_INVALID",
                    )
                )
            if state.structure_revision > structure.revision:
                issues.append(
                    VerticalValidationIssue(
                        "error",
                        "project_definition.structure.revision",
                        "definition references a future structure revision",
                        "P2P255_PROJECT_DEFINITION_INVALID",
                    )
                )
            if (
                state.structure_revision == structure.revision
                and state.structure_checksum != structure.checksum
            ):
                issues.append(
                    VerticalValidationIssue(
                        "error",
                        "project_definition.structure.checksum",
                        "definition checksum does not match its project-structure revision",
                        "P2P255_PROJECT_DEFINITION_INVALID",
                    )
                )
        if state.schema_version != PROJECT_DEFINITION_SCHEMA_VERSION:
            issues.append(
                VerticalValidationIssue(
                    "error",
                    "project_definition.schema_version",
                    f"definition requires schema version {PROJECT_DEFINITION_SCHEMA_VERSION}",
                    "P2P_PROJECT_DEFINITION_UNSUPPORTED_SCHEMA",
                )
            )
        if not uses_project_structure and state.vertical_id != pack.vertical_id:
            issues.append(
                VerticalValidationIssue(
                    "error",
                    "project_definition.vertical_id",
                    f"definition vertical `{state.vertical_id}` does not match active vertical `{pack.vertical_id}`",
                    "P2P255_PROJECT_DEFINITION_INVALID",
                )
            )
        if not uses_project_structure and state.vertical_version != pack.version:
            issues.append(
                VerticalValidationIssue(
                    "error",
                    "project_definition.vertical_version",
                    f"definition version `{state.vertical_version}` does not match active version `{pack.version}`",
                    "P2P255_PROJECT_DEFINITION_INVALID",
                )
            )
        pack_checksum = _pack_checksum(pack) if not uses_project_structure else ""
        if not uses_project_structure and state.lock_checksum and state.lock_checksum != pack_checksum:
            issues.append(
                VerticalValidationIssue(
                    "error",
                    "project_definition.lock.checksum",
                    "definition lock checksum does not match the active vertical pack",
                    "P2P255_PROJECT_DEFINITION_INVALID",
                )
            )
        orphan_ids: set[str] = set()
        for orphan in state.orphans:
            if not orphan.orphan_id or not orphan.source_section_id:
                issues.append(
                    VerticalValidationIssue(
                        "error",
                        "project_definition.orphans",
                        "orphan id and source_section_id are required",
                        "P2P255_PROJECT_DEFINITION_INVALID",
                    )
                )
            elif orphan.orphan_id in orphan_ids:
                issues.append(
                    VerticalValidationIssue(
                        "error",
                        f"project_definition.orphans.{orphan.orphan_id}",
                        "duplicate orphan id",
                        "P2P255_PROJECT_DEFINITION_INVALID",
                    )
                )
            orphan_ids.add(orphan.orphan_id)
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
        *,
        audit_at: str | None = None,
    ) -> ProjectDefinitionState:
        audit_value = audit_at or self.definition_audit_date()
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
                    updated_at=audit_value,
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
                    at=audit_value,
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
                        at=audit_value,
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
            orphans=state.orphans,
            structure_id=state.structure_id,
            structure_revision=state.structure_revision,
            structure_checksum=state.structure_checksum,
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
            "structure_source": payload.get("structure_source"),
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
        include_existing: bool = True,
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
        if include_existing and path.exists():
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
                orphan["unmapped_from_previous_vertical"] = True
                orphan["counts_toward_active_baseline"] = False
                orphan["enabled"] = item.get("enabled") is not False
                criteria_payload.append(orphan)
        active_criteria = [item for item in criteria_payload if item.get("counts_toward_active_baseline") is not False]
        return {
            "version": "1.0",
            "structure_source": {
                "kind": "vertical_release",
                "coordinate": pack.coordinate,
            },
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
            target_kind=str((item.get("target") or {}).get("kind") or "")
            if isinstance(item.get("target"), dict)
            else "",
            target_id=str((item.get("target") or {}).get("id") or "")
            if isinstance(item.get("target"), dict)
            else "",
            answer_contract=dict(item.get("answer_contract") or {})
            if isinstance(item.get("answer_contract"), dict)
            else {},
            fallback_key=str(item.get("fallback_key") or ""),
            aliases=tuple(
                str(alias).strip()
                for alias in item.get("aliases", [])
                if str(alias).strip()
            )
            if isinstance(item.get("aliases"), list)
            else (),
            deferred_trigger=dict(item.get("deferred_trigger") or {})
            if isinstance(item.get("deferred_trigger"), dict)
            else {},
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
    dependency_payloads = _mapping_list(manifest_payload.get("dependencies"))
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
        schema_version=int(vertical.get("schema_version", 0)),
        manifest=VerticalManifest(
            vertical_id=str(manifest_payload.get("id") or vertical.get("id") or ""),
            name=str(manifest_payload.get("name") or vertical.get("name") or vertical.get("id") or ""),
            version=str(manifest_payload.get("version") or vertical.get("version") or ""),
            schema_version=int(manifest_payload.get("schema_version", 0)),
            publisher=str(manifest_payload.get("publisher") or ""),
            source=str(manifest_payload.get("source") or ""),
            compatibility=compatibility,
            license_id=str(manifest_payload.get("license") or ""),
            lineage={str(key): str(value) for key, value in manifest_payload.get("lineage", {}).items()}
            if isinstance(manifest_payload.get("lineage"), dict)
            else {},
            dependencies=[
                VerticalDependency(
                    coordinate=str(item.get("coordinate") or ""),
                    checksum=str(item.get("checksum") or ""),
                )
                for item in dependency_payloads
            ],
            primary_domain=(
                ProjectDomainRef.from_mapping(manifest_payload.get("primary_domain"))
                if manifest_payload.get("primary_domain") is not None
                else None
            ),
            domain_tags=normalize_domain_tags(manifest_payload.get("domain_tags", [])),
        )
        if isinstance(manifest_payload, dict) and manifest_payload
        else None,
        profile_specs=profile_specs,
        module_specs=module_specs,
        compatibility=compatibility,
    )


def _pack_payload(pack: VerticalPack) -> dict[str, object]:
    vertical_payload: dict[str, object] = {
            "schema_version": pack.schema_version,
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
            "questions": [_vertical_question_payload(question) for question in pack.questions],
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
    if pack.manifest is None:
        raise ValueError("P2P_VERTICAL_CANONICAL_LAYOUT_REQUIRED: schema-3 pack manifest is required")
    vertical_payload["manifest"] = {
            "schema_version": pack.manifest.schema_version,
            "publisher": pack.manifest.publisher,
            "id": pack.manifest.vertical_id,
            "name": pack.manifest.name,
            "version": pack.manifest.version,
            "license": pack.manifest.license_id,
            "source": pack.manifest.source,
            "extends": pack.extends,
            "lineage": pack.manifest.lineage,
            "dependencies": [
                {"coordinate": item.coordinate, "checksum": item.checksum}
                for item in pack.manifest.dependencies
            ],
            "compatibility": pack.manifest.compatibility,
            "primary_domain": (
                pack.manifest.primary_domain.to_dict()
                if pack.manifest.primary_domain is not None
                else None
            ),
            "domain_tags": list(pack.manifest.domain_tags),
    }
    return {
        "vertical": vertical_payload
    }


def _vertical_question_payload(question: VerticalQuestion) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": question.question_id,
        "section_id": question.section_id,
        "priority": question.priority,
        "question": question.question,
        "rationale": question.rationale,
    }
    if question.target_kind and question.target_id:
        payload["target"] = {"kind": question.target_kind, "id": question.target_id}
    if question.answer_contract:
        payload["answer_contract"] = question.answer_contract
    if question.fallback_key:
        payload["fallback_key"] = question.fallback_key
    if question.aliases:
        payload["aliases"] = list(question.aliases)
    if question.deferred_trigger:
        payload["deferred_trigger"] = question.deferred_trigger
    return payload


def _empty_starter_pack() -> VerticalPack:
    return VerticalPack(
        vertical_id="empty",
        name="Empty Starter",
        version="0",
        description="Project memory without project-specific structure.",
        extends=None,
        source="starter",
        path=None,
        sections=[],
        rubrics=[],
        questions=[],
        artifacts=[],
        schema_version=VERTICAL_SCHEMA_VERSION,
        manifest=None,
    )


def _looks_like_canonical_pack_dir(path: Path) -> bool:
    return (path / "sections").exists() or (path / "rubrics.yml").exists()


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
    payload: dict[str, object] = {
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
    lock_payload = payload["project_vertical_lock"]
    assert isinstance(lock_payload, dict)
    if lock.coordinate:
        lock_payload["coordinate"] = lock.coordinate
    if lock.artifact_checksum:
        lock_payload["artifact_checksum"] = {
            "algorithm": "sha256",
            "value": lock.artifact_checksum,
        }
    if lock.dependencies:
        lock_payload["dependencies"] = [
            {"coordinate": item.coordinate, "checksum": item.checksum}
            for item in lock.dependencies
        ]
    return payload


def _vertical_lock_from_payload(path: Path, payload: dict[str, object], root: Path) -> VerticalLock:
    lock = payload.get("project_vertical_lock")
    if not isinstance(lock, dict):
        raise ValueError(f"Invalid project vertical lock: expected project_vertical_lock mapping in {path}")
    schema_version = lock.get("schema_version")
    if schema_version != VERTICAL_LOCK_SCHEMA_VERSION:
        raise ValueError(
            "P2P_VERTICAL_LOCK_UNSUPPORTED_SCHEMA: project vertical lock requires "
            f"schema_version {VERTICAL_LOCK_SCHEMA_VERSION}; observed `{schema_version}`."
        )
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
    pack_schema_version = lock.get("pack_schema_version")
    if pack_schema_version != VERTICAL_SCHEMA_VERSION:
        display = "missing" if pack_schema_version is None else repr(pack_schema_version)
        raise ValueError(
            "P2P_VERTICAL_UNSUPPORTED_SCHEMA: project lock references pack schema "
            f"{display}; this runtime supports schema {VERTICAL_SCHEMA_VERSION} only "
            "and provides no in-runtime conversion"
        )
    coordinate = str(lock.get("coordinate") or "").strip()
    if not coordinate:
        raise ValueError(
            "P2P_VERTICAL_CANONICAL_LAYOUT_REQUIRED: project lock requires an exact coordinate"
        )
    VerticalCoordinate.parse(coordinate)
    selected = lock.get("selected") if isinstance(lock.get("selected"), dict) else {}
    artifact_checksum = lock.get("artifact_checksum")
    artifact_checksum_value = (
        str(artifact_checksum.get("value") or "")
        if isinstance(artifact_checksum, dict)
        else ""
    )
    return VerticalLock(
        vertical_id=vertical_id,
        name=str(lock.get("name") or vertical_id),
        version=str(lock.get("version") or ""),
        pack_schema_version=pack_schema_version,
        source=VerticalPackSource(
            source_type=str(source_payload.get("type") or "unknown"),
            resolved_from=str(source_payload.get("resolved_from") or ""),
            path=Path(str(source_payload["path"])) if source_payload.get("path") else None,
            package=str(source_payload.get("package") or ""),
        ),
        checksum=checksum,
        compatibility=lock.get("compatibility") if isinstance(lock.get("compatibility"), dict) else {},
        selected_at=str(selected.get("at") or ""),
        selected_by=str(selected.get("by") or ""),
        trust=lock.get("trust") if isinstance(lock.get("trust"), dict) else {},
        path=relative_to_root(path, root),
        coordinate=coordinate,
        artifact_checksum=artifact_checksum_value,
        dependencies=[
            VerticalDependency(
                coordinate=str(item.get("coordinate") or ""),
                checksum=str(item.get("checksum") or ""),
            )
            for item in _mapping_list(lock.get("dependencies"))
        ],
    )


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
            "structure": {
                "id": state.structure_id,
                "revision": state.structure_revision,
                "checksum": state.structure_checksum,
            },
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
            "orphans": [
                {
                    "id": item.orphan_id,
                    "source_vertical": item.source_vertical,
                    "source_section_id": item.source_section_id,
                    "source_field_id": item.source_field_id,
                    "value": item.value,
                    "source": item.source,
                    "updated_at": item.updated_at,
                    "reason": item.reason,
                    "target_vertical": item.target_vertical,
                }
                for item in state.orphans
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
    orphans = data.get("orphans")
    if isinstance(orphans, list):
        for orphan in orphans:
            if isinstance(orphan, dict):
                orphan.pop("updated_at", None)
    return candidate


def _definition_state_from_payload(payload: dict[str, object], *, path: Path) -> ProjectDefinitionState:
    data = payload.get("project_definition")
    if not isinstance(data, dict):
        raise ValueError("Invalid project definition state: expected project_definition mapping.")
    schema_version = data.get("schema_version")
    if schema_version != PROJECT_DEFINITION_SCHEMA_VERSION:
        raise ValueError(
            "P2P_PROJECT_DEFINITION_UNSUPPORTED_SCHEMA: project definition requires "
            f"schema_version {PROJECT_DEFINITION_SCHEMA_VERSION}; observed `{schema_version}`."
        )
    sections: list[ProjectDefinitionSectionState] = []
    for item in data.get("sections", []) if isinstance(data.get("sections"), list) else []:
        if not isinstance(item, dict):
            continue
        if "open_questions" in item:
            raise ValueError(
                "P2P354_OBSOLETE_DEFINITION_QUESTIONS: project definition sections must not contain "
                "open_questions; use .p2p/project/questions.yml."
            )
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
    orphans = [
        ProjectDefinitionOrphan(
            orphan_id=str(item.get("id") or ""),
            source_vertical=str(item.get("source_vertical") or ""),
            source_section_id=str(item.get("source_section_id") or ""),
            source_field_id=str(item.get("source_field_id") or ""),
            value=item.get("value"),
            source=str(item.get("source") or ""),
            updated_at=str(item.get("updated_at") or ""),
            reason=str(item.get("reason") or "unmapped"),
            target_vertical=str(item.get("target_vertical") or ""),
        )
        for item in _mapping_list(data.get("orphans"))
    ]
    lock_payload = data.get("lock") if isinstance(data.get("lock"), dict) else {}
    structure_payload = (
        data.get("structure") if isinstance(data.get("structure"), dict) else {}
    )
    return ProjectDefinitionState(
        schema_version=int(schema_version),
        vertical_id=str(data.get("vertical_id") or ""),
        vertical_version=str(data.get("vertical_version") or ""),
        profile=str(data.get("profile") or "default"),
        modules=[str(item) for item in data.get("modules", []) if str(item).strip()] if isinstance(data.get("modules"), list) else [],
        lock_checksum=str(lock_payload.get("checksum") or ""),
        sections=sections,
        next_suggested_action=data.get("next_suggested_action") if isinstance(data.get("next_suggested_action"), dict) else {},
        history=history,
        orphans=orphans,
        structure_id=str(structure_payload.get("id") or ""),
        structure_revision=int(structure_payload.get("revision") or 0),
        structure_checksum=str(structure_payload.get("checksum") or ""),
        path=path,
    )


def _definition_patch_from_payload(payload: dict[str, object], *, target: str) -> ProjectDefinitionPatch:
    data = payload.get("project_definition_patch")
    if not isinstance(data, dict):
        raise ValueError(f"Invalid project definition patch {target}: expected project_definition_patch mapping.")
    schema_version = data.get("schema_version")
    if schema_version != PROJECT_DEFINITION_SCHEMA_VERSION:
        raise ValueError(
            f"Invalid project definition patch {target}: schema_version must be "
            f"{PROJECT_DEFINITION_SCHEMA_VERSION}."
        )
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
        schema_version=int(schema_version),
    )


def _copy_section_state(section: ProjectDefinitionSectionState) -> ProjectDefinitionSectionState:
    return ProjectDefinitionSectionState(
        section_id=section.section_id,
        status=section.status,
        fields=dict(section.fields),
        missing_required_fields=list(section.missing_required_fields),
        assumptions=list(section.assumptions),
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
    schema_version = vertical.get("schema_version")
    if isinstance(schema_version, bool) or schema_version != VERTICAL_SCHEMA_VERSION:
        display = "missing" if schema_version is None else repr(schema_version)
        error(
            "vertical.schema_version",
            f"pack schema {display} is unsupported; this runtime supports schema "
            f"{VERTICAL_SCHEMA_VERSION} only and provides no in-runtime conversion",
            "P2P_VERTICAL_UNSUPPORTED_SCHEMA",
        )
    manifest = vertical.get("manifest")
    if not isinstance(manifest, dict):
        error("vertical.manifest", "schema version 3 requires a manifest mapping")
    else:
            allowed_manifest_fields = {
                "schema_version",
                "publisher",
                "id",
                "name",
                "version",
                "license",
                "source",
                "extends",
                "lineage",
                "dependencies",
                "compatibility",
                "primary_domain",
                "domain_tags",
            }
            unknown_fields = sorted(set(manifest) - allowed_manifest_fields)
            if unknown_fields:
                error(
                    "vertical.manifest",
                    f"unknown fields {unknown_fields}",
                    "P2P_VERTICAL_UNKNOWN_MANIFEST_FIELD",
                )
            for field in ("publisher", "id", "version", "license"):
                if not str(manifest.get(field) or "").strip():
                    error(f"vertical.manifest.{field}", "required for schema version 3")
            if manifest.get("schema_version") != 3:
                error("vertical.manifest.schema_version", "must be 3")
            if str(manifest.get("id") or "") != str(vertical.get("id") or ""):
                error("vertical.manifest.id", "must match vertical.id")
            if str(manifest.get("version") or "") != str(vertical.get("version") or ""):
                error("vertical.manifest.version", "must match vertical.version")
            publisher = str(manifest.get("publisher") or "")
            version = str(manifest.get("version") or "")
            if version and not is_semantic_version(version):
                error(
                    "vertical.manifest.version",
                    "must be a semantic version",
                    "P2P_VERTICAL_INVALID_SEMVER",
                )
            if publisher and vertical.get("id") and version:
                try:
                    VerticalCoordinate.parse(f"{publisher}/{vertical.get('id')}@{version}")
                except ValueError as exc:
                    error("vertical.manifest", str(exc), "P2P_VERTICAL_INVALID_COORDINATE")
            lineage = manifest.get("lineage", {})
            if not isinstance(lineage, dict):
                error("vertical.manifest.lineage", "must be a mapping")
            elif set(lineage) - {"forked_from", "previous_release"}:
                error(
                    "vertical.manifest.lineage",
                    "only forked_from and previous_release are supported",
                )
            else:
                for lineage_field in ("forked_from", "previous_release"):
                    if not lineage.get(lineage_field):
                        continue
                    try:
                        VerticalCoordinate.parse(str(lineage[lineage_field]))
                    except ValueError as exc:
                        error(f"vertical.manifest.lineage.{lineage_field}", str(exc))
            dependencies = manifest.get("dependencies", [])
            if not isinstance(dependencies, list):
                error("vertical.manifest.dependencies", "must be a list")
                dependencies = []
            seen_dependencies: set[str] = set()
            for index, dependency in enumerate(dependencies):
                if not isinstance(dependency, dict):
                    error(f"vertical.manifest.dependencies[{index}]", "must be a mapping")
                    continue
                coordinate = str(dependency.get("coordinate") or "")
                checksum = str(dependency.get("checksum") or "")
                try:
                    VerticalCoordinate.parse(coordinate)
                except ValueError as exc:
                    error(f"vertical.manifest.dependencies[{index}].coordinate", str(exc))
                if coordinate in seen_dependencies:
                    error(
                        f"vertical.manifest.dependencies[{index}].coordinate",
                        f"duplicate dependency `{coordinate}`",
                    )
                seen_dependencies.add(coordinate)
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", checksum):
                    error(
                        f"vertical.manifest.dependencies[{index}].checksum",
                        "must be sha256 followed by 64 lowercase hexadecimal characters",
                    )
            primary_domain = manifest.get("primary_domain")
            if primary_domain is not None:
                try:
                    ProjectDomainRef.from_mapping(primary_domain)
                except ValueError as exc:
                    error(
                        "vertical.manifest.primary_domain",
                        str(exc),
                        "P2P_VERTICAL_DOMAIN_METADATA_INVALID",
                    )
            try:
                normalize_domain_tags(manifest.get("domain_tags", []))
            except ValueError as exc:
                error(
                    "vertical.manifest.domain_tags",
                    str(exc),
                    "P2P_VERTICAL_DOMAIN_METADATA_INVALID",
                )
            extends = str(vertical.get("extends") or manifest.get("extends") or "")
            if extends:
                try:
                    VerticalCoordinate.parse(extends)
                except ValueError as exc:
                    error("vertical.extends", str(exc))
                if extends not in seen_dependencies:
                    error(
                        "vertical.extends",
                        "portable structural base must appear in dependencies",
                        "P2P_VERTICAL_MISSING_BASE_DEPENDENCY",
                    )
    section_items = _mapping_list(vertical.get("sections"))
    if not section_items:
        error(
            "vertical.sections",
            "at least one section is required",
            "P2P_VERTICAL_NO_SECTIONS",
        )
    section_ids = _ids(section_items, "vertical.sections", error)
    field_ids_by_section: dict[str, set[str]] = {}
    for index, item in enumerate(section_items):
        for field in ("id", "title", "purpose"):
            if not str(item.get(field) or "").strip():
                error(f"vertical.sections[{index}].{field}", "required")
        field_items = _mapping_list(item.get("fields"))
        field_ids = _ids(field_items, f"vertical.sections[{index}].fields", error)
        section_id = str(item.get("id") or "").strip()
        if section_id:
            field_ids_by_section[section_id] = field_ids
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
    declared_aliases: set[str] = set()
    answer_kinds = {
        "field_value",
        "section_disposition",
        "assumption_resolution",
        "blocker_resolution",
        "owner_decision_reference",
        "informational",
    }
    definition_operations = {
        "set_field",
        "set_section_status",
        "update_assumption_status",
        "clear_blocker",
    }
    for index, item in enumerate(question_items):
        question_id = str(item.get("id") or "").strip()
        if not question_id:
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
        target = item.get("target")
        if target not in (None, {}):
            if not isinstance(target, dict):
                error(f"vertical.questions[{index}].target", "must be a mapping")
            else:
                unknown_target = set(target) - {"kind", "id"}
                if unknown_target:
                    error(
                        f"vertical.questions[{index}].target",
                        f"unknown fields {sorted(unknown_target)}",
                    )
                target_kind = str(target.get("kind") or "").strip()
                target_id = str(target.get("id") or "").strip()
                if not target_kind or not target_id:
                    error(f"vertical.questions[{index}].target", "kind and id are both required")
                elif target_kind == "field" and target_id not in field_ids_by_section.get(section_id, set()):
                    error(
                        f"vertical.questions[{index}].target.id",
                        f"unknown field `{target_id}` for section `{section_id}`",
                    )
                elif target_kind == "section" and target_id != section_id:
                    error(
                        f"vertical.questions[{index}].target.id",
                        f"section target must match `{section_id}`",
                    )
                elif target_kind not in {"field", "section", "assumption", "blocker"}:
                    error(
                        f"vertical.questions[{index}].target.kind",
                        f"unsupported target kind `{target_kind}`",
                    )
        contract = item.get("answer_contract")
        if contract is not None:
            if not isinstance(contract, dict):
                error(f"vertical.questions[{index}].answer_contract", "must be a mapping")
            elif contract:
                unknown_contract = set(contract) - {
                    "kind",
                    "required_fields",
                    "allowed_definition_operations",
                    "allowed_values",
                }
                if unknown_contract:
                    error(
                        f"vertical.questions[{index}].answer_contract",
                        f"unknown fields {sorted(unknown_contract)}",
                    )
                kind = str(contract.get("kind") or "").strip()
                if kind not in answer_kinds:
                    error(
                        f"vertical.questions[{index}].answer_contract.kind",
                        f"must be one of {sorted(answer_kinds)}",
                    )
                for field in ("required_fields", "allowed_definition_operations"):
                    if not isinstance(contract.get(field), list):
                        error(f"vertical.questions[{index}].answer_contract.{field}", "must be a list")
                operations = contract.get("allowed_definition_operations")
                if isinstance(operations, list):
                    unknown_operations = {str(value) for value in operations} - definition_operations
                    if unknown_operations:
                        error(
                            f"vertical.questions[{index}].answer_contract.allowed_definition_operations",
                            f"unknown operations {sorted(unknown_operations)}",
                        )
                if "allowed_values" in contract and not isinstance(contract.get("allowed_values"), list):
                    error(
                        f"vertical.questions[{index}].answer_contract.allowed_values",
                        "must be a list",
                    )
        aliases = item.get("aliases", [])
        if not isinstance(aliases, list):
            error(f"vertical.questions[{index}].aliases", "must be a list")
        else:
            for alias in aliases:
                normalized_alias = str(alias).strip()
                if not normalized_alias:
                    error(f"vertical.questions[{index}].aliases", "aliases must be non-empty strings")
                elif normalized_alias == question_id or normalized_alias in declared_aliases:
                    error(
                        f"vertical.questions[{index}].aliases",
                        f"duplicate or self alias `{normalized_alias}`",
                    )
                declared_aliases.add(normalized_alias)
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


def _overlay_pack(composed_base: VerticalPack, pack: VerticalPack) -> VerticalPack:
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


def _normalize_vertical_id(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        raise ValueError("Vertical ID is required.")
    return normalized


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


def _proposal_vertical_coverage_from_payload(
    proposal_id: str,
    path: Path,
    payload: dict[str, object],
    root: Path,
) -> ProposalVerticalCoverage:
    validate_vertical_coverage_payload(payload, target=str(path))
    coverage = payload["vertical_coverage"]
    assert isinstance(coverage, dict)
    schema_version = int(coverage["schema_version"])
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
        path=relative_to_root(path, root),
        schema_version=schema_version,
        provenance=provenance,
        authority=str(provenance["authority"]),
    )


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    try:
        data = load_yaml_mapping(path.read_bytes())
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    except ValueError as exc:
        raise ValueError(f"YAML document must be a mapping: {path}") from exc
    return data


def dataclass_payload(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value


def project_definition_state_from_payload(
    payload: dict[str, object],
    *,
    path: Path,
) -> ProjectDefinitionState:
    return _definition_state_from_payload(payload, path=path)


def project_definition_state_payload(state: ProjectDefinitionState) -> dict[str, object]:
    return _definition_state_payload(state)

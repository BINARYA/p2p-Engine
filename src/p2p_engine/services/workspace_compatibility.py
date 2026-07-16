from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from p2p_engine import __version__
from p2p_engine.core.mutation_preview import canonical_json_bytes, semantic_sha256
from p2p_engine.core.project_metadata import ProjectMetadataPatch
from p2p_engine.core.workspace_schema import (
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    FINDING_COMPATIBLE,
    FINDING_DEGRADED,
    FINDING_ENGINE_PREREQUISITE_REQUIRED,
    FINDING_INVALID,
    FINDING_MIGRATION_REQUIRED,
    FINDING_OWNER_INPUT_REQUIRED,
    FINDING_REPOSITORY_CURATION_REQUIRED,
    FINDING_UNSUPPORTED,
    MIGRATION_STATUS_BLOCKED,
    MIGRATION_STATUS_NO_OP,
    OP_CREATE_CANONICAL,
    OP_NO_OP,
    OP_OWNER_INPUT,
    OP_PRESERVE_LEGACY,
    OP_REFRESH_DERIVED,
    WORKSPACE_SCHEMA_CONTRACT_VERSION,
    CompatibilityFinding,
    CompatibilitySnapshot,
    ArtifactInventoryEntry,
    MigrationOperation,
    MigrationPlan,
)
from p2p_engine.foundation.files import read_yaml_mapping, yaml_dump
from p2p_engine.services.project_maturity import domain_state_payload
from p2p_engine.services.candidate_workspace import CandidateWorkspaceView
from p2p_engine.services.project_metadata import ProjectMetadataService
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.workspace_migration_registry import WorkspaceMigrationRegistry
from p2p_engine.services.workspace_migration_handlers import TransitionPlanFragment
from p2p_engine.services.workspace_schema import WorkspaceSchemaService


WORKSPACE_PLANNER_VERSION = 1
SEMANTIC_AUDIT_TIMESTAMP = "__P2P_APPLY_AT__"
SEMANTIC_AUDIT_ACTOR = "__P2P_ACTOR__"

_OWNER_INPUT_KEYS = frozenset({"vertical", "owner", "metadata", "project_questions"})
_VERTICAL_INPUT_KEYS = frozenset({"id", "profile", "modules", "rubric_mapping"})
_OWNER_IDENTITY_KEYS = frozenset({"id", "name"})
_METADATA_INPUT_KEYS = frozenset({"status", "workflow_phase", "current_objective"})


class WorkspaceCompatibilityService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        schema_service: WorkspaceSchemaService | None = None,
        registry: WorkspaceMigrationRegistry | None = None,
        engine_version: str = __version__,
        runtime_status: Callable[[], Any] | None = None,
        vertical_context: Callable[[], Any] | None = None,
        decision_context_index: Callable[[], Any] | None = None,
        freshness_status: Callable[[], Any] | None = None,
        vertical_candidate_renderer: Callable[..., Any] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.registry = registry or WorkspaceMigrationRegistry()
        self.engine_version = engine_version
        self.schema_service = schema_service or WorkspaceSchemaService(
            root=self.root,
            p2p_dir=self.p2p_dir,
            registry=self.registry,
            engine_version=engine_version,
        )
        self.runtime_status = runtime_status
        self.vertical_context = vertical_context
        self.decision_context_index = decision_context_index
        self.freshness_status = freshness_status
        self.vertical_candidate_renderer = vertical_candidate_renderer or ProjectVerticalService(
            root=self.root,
            p2p_dir=self.p2p_dir,
            proposal_summaries=lambda: [],
            find_proposal_dir=lambda proposal_id: self.p2p_dir / "proposals" / proposal_id,
        ).render_migration_candidate
        self._captured_bytes: dict[str, bytes] = {}
        self._yaml_parse_count = 0

    def snapshot(self, *, active_transaction_id: str | None = None) -> CompatibilitySnapshot:
        self._captured_bytes = {}
        self._yaml_parse_count = 0
        inventory = self._inventory()
        schema_status = self.schema_service.status()
        project = self._captured_yaml(".p2p/project.yml")
        project_data = project.get("project") if isinstance(project, dict) else None
        project_id = str(project_data.get("id") or "") if isinstance(project_data, dict) else ""
        findings = self._snapshot_findings(
            schema_status,
            inventory,
            project,
            active_transaction_id=active_transaction_id,
        )
        self._invoke_existing_inspectors(findings)
        return CompatibilitySnapshot(
            schema_status=schema_status,
            project_id=project_id,
            inventory=inventory,
            findings=tuple(findings),
            source_access={
                "files_discovered": len(inventory),
                "files_read": len(self._captured_bytes),
                "bytes_read": sum(len(content) for content in self._captured_bytes.values()),
                "yaml_parses": self._yaml_parse_count,
                "files_written": 0,
            },
        )

    def plan(
        self,
        target_version: int = CURRENT_WORKSPACE_SCHEMA_VERSION,
        owner_inputs: Mapping[str, object] | None = None,
        *,
        active_transaction_id: str | None = None,
    ) -> MigrationPlan:
        normalized_inputs = normalize_owner_inputs(owner_inputs or {})
        snapshot = self.snapshot(active_transaction_id=active_transaction_id)
        source_version = snapshot.schema_status.current_version or 0
        if target_version < source_version:
            return self._unsupported_plan(
                source_version,
                target_version,
                normalized_inputs,
                "P2P310_UNSUPPORTED_DOWNGRADE",
                "Workspace schema downgrade is not supported.",
            )
        if target_version > CURRENT_WORKSPACE_SCHEMA_VERSION:
            return self._unsupported_plan(
                source_version,
                target_version,
                normalized_inputs,
                "P2P311_UNSUPPORTED_TARGET",
                f"Runtime supports workspace schema {CURRENT_WORKSPACE_SCHEMA_VERSION}.",
            )
        try:
            transitions = self.registry.resolve_path(source_version, target_version)
        except ValueError as exc:
            return self._unsupported_plan(
                source_version,
                target_version,
                normalized_inputs,
                "P2P312_MISSING_TRANSITION",
                str(exc),
            )
        if not transitions:
            operation = MigrationOperation(
                operation_id="workspace-schema-no-op",
                kind=OP_NO_OP,
                target=".p2p/project/workspace-schema.yml",
                reason="Workspace schema already matches the requested target.",
                migration_id="",
                write_class="read_only",
                canonical=True,
                before_exists=True,
                before_physical_sha256=self._hash_for(snapshot, ".p2p/project/workspace-schema.yml"),
                candidate_semantic_sha256=None,
                validator="WorkspaceSchemaService",
                rollback="none",
            )
            return self._finalize_plan(
                status=MIGRATION_STATUS_NO_OP,
                source_version=source_version,
                target_version=target_version,
                migrations=(),
                operations=(operation,),
                findings=(
                    CompatibilityFinding(
                        code="P2P320_WORKSPACE_SCHEMA_CURRENT",
                        classification=FINDING_COMPATIBLE,
                        message="Workspace schema is already current.",
                    ),
                ),
                owner_inputs=normalized_inputs,
                candidate_files={},
                applicable=True,
            )

        supports = tuple(item.runtime_support(self.engine_version) for item in transitions)
        findings = list(snapshot.findings)
        blocking_classes = {
            FINDING_INVALID,
            FINDING_OWNER_INPUT_REQUIRED,
            FINDING_REPOSITORY_CURATION_REQUIRED,
            FINDING_ENGINE_PREREQUISITE_REQUIRED,
            FINDING_UNSUPPORTED,
        }
        applicable = not any(item.classification in blocking_classes for item in findings)
        if not all(item.plan for item in supports):
            findings.append(
                CompatibilityFinding(
                    code="P2P321_MIGRATION_PLAN_RUNTIME_REQUIRED",
                    classification=FINDING_ENGINE_PREREQUISITE_REQUIRED,
                    message="The active runtime cannot plan every selected transition.",
                    recovery_action="Install a runtime satisfying the transition plan requirement.",
                )
            )
            applicable = False
        if not all(item.apply for item in supports):
            findings.append(
                CompatibilityFinding(
                    code="P2P322_MIGRATION_APPLY_RUNTIME_REQUIRED",
                    classification=FINDING_ENGINE_PREREQUISITE_REQUIRED,
                    message="The active runtime cannot apply every selected transition.",
                    recovery_action="Install a runtime satisfying the transition apply requirement.",
                )
            )
            applicable = False

        fragment = None
        for transition in transitions:
            handler = self.registry.handler_by_id(transition.migration_id)
            fragment = self._plan_with_handler(
                handler=handler,
                snapshot=snapshot,
                findings=fragment.findings if fragment is not None else findings,
                owner_inputs=normalized_inputs,
                applicable=fragment.applicable if fragment is not None else applicable,
                base_plan=fragment,
            )
            if not fragment.applicable:
                break
        assert fragment is not None
        return self._finalize_handler_plan(
            source_version=source_version,
            target_version=target_version,
            transitions=transitions,
            owner_inputs=normalized_inputs,
            fragment=fragment,
        )

    def _plan_with_handler(
        self,
        *,
        handler: Any,
        snapshot: CompatibilitySnapshot,
        findings: tuple[CompatibilityFinding, ...] | list[CompatibilityFinding],
        owner_inputs: Mapping[str, object],
        applicable: bool,
        base_plan: Any | None = None,
    ) -> Any:
        planner = getattr(handler, "plan", None)
        if not callable(planner):
            return TransitionPlanFragment(
                migration_id=handler.transition.migration_id,
                operations=(),
                candidate_files={},
                findings=(
                    CompatibilityFinding(
                        code="P2P312_MISSING_TRANSITION",
                        classification=FINDING_UNSUPPORTED,
                        message=(
                            f"Workspace migration handler `{handler.transition.migration_id}` "
                            "has no planner."
                        ),
                        migration_id=handler.transition.migration_id,
                    ),
                ),
                applicable=False,
            )
        arguments = {
            "context": self,
            "snapshot": snapshot,
            "findings": findings,
            "owner_inputs": owner_inputs,
            "applicable": applicable,
            "candidate_view": CandidateWorkspaceView(
                root=self.root,
                candidates=dict(base_plan.candidate_files) if base_plan is not None else {},
                preserved={path: content for path, content in self._captured_bytes.items()},
                owned_paths=(set(base_plan.candidate_files) if base_plan is not None else set()),
            ),
        }
        if base_plan is not None:
            arguments["base_plan"] = base_plan
        return planner(
            **arguments,
        )

    def _finalize_handler_plan(
        self,
        *,
        source_version: int,
        target_version: int,
        transitions: tuple[Any, ...],
        owner_inputs: Mapping[str, object],
        fragment: Any,
    ) -> MigrationPlan:
        return self._finalize_plan(
            status="applicable" if fragment.applicable else MIGRATION_STATUS_BLOCKED,
            source_version=source_version,
            target_version=target_version,
            migrations=transitions,
            operations=fragment.operations,
            findings=fragment.findings,
            owner_inputs=owner_inputs,
            candidate_files=dict(fragment.candidate_files),
            applicable=fragment.applicable,
        )

    def _inventory(self) -> tuple[ArtifactInventoryEntry, ...]:
        if not self.p2p_dir.exists():
            return ()
        entries: list[ArtifactInventoryEntry] = []
        for path in sorted(self.p2p_dir.rglob("*"), key=lambda item: item.as_posix()):
            relative = path.relative_to(self.root).as_posix()
            if relative == ".p2p/.internal" or relative.startswith(".p2p/.internal/"):
                continue
            if path.is_symlink():
                target = path.resolve(strict=False)
                classification = "invalid_symlink" if not target.is_relative_to(self.p2p_dir) else "symlink"
                entries.append(
                    ArtifactInventoryEntry(
                        path=relative,
                        classification=classification,
                        exists=True,
                        size=0,
                        physical_sha256="",
                    )
                )
                continue
            if not path.is_file():
                continue
            content = path.read_bytes()
            self._captured_bytes[relative] = content
            entries.append(
                ArtifactInventoryEntry(
                    path=relative,
                    classification=self._classify(relative),
                    exists=True,
                    size=len(content),
                    physical_sha256=hashlib.sha256(content).hexdigest(),
                    semantic_sha256=self._semantic_file_hash(relative, content),
                )
            )
        return tuple(entries)

    def _classify(self, path: str) -> str:
        if path.startswith(".p2p/registries/") or path.startswith(".p2p/project/features/"):
            return "derived"
        if path.startswith(".p2p/domain/"):
            return "legacy"
        canonical_prefixes = (
            ".p2p/project/",
            ".p2p/proposals/",
            ".p2p/governance/",
            ".p2p/templates/",
            ".p2p/config/",
            ".p2p/choices/",
            ".p2p/changes/",
            ".p2p/work/",
            ".p2p/consents/",
            ".p2p/intakes/",
        )
        if path == ".p2p/project.yml" or path.startswith(canonical_prefixes):
            return "canonical"
        if path in {".p2p/agent-policy.yml", ".p2p/agent-integrations.yml"}:
            return "canonical"
        return "unknown"

    def _snapshot_findings(
        self,
        schema_status: Any,
        inventory: tuple[ArtifactInventoryEntry, ...],
        project: Mapping[str, object],
        *,
        active_transaction_id: str | None,
    ) -> list[CompatibilityFinding]:
        findings: list[CompatibilityFinding] = []
        recovery = schema_status.recovery if isinstance(schema_status.recovery, Mapping) else {}
        recovery_transaction = str(recovery.get("transaction_id") or "")
        if recovery.get("required") and recovery_transaction != active_transaction_id:
            findings.append(
                CompatibilityFinding(
                    code="P2P337_WORKSPACE_MIGRATION_RECOVERY_REQUIRED",
                    classification=FINDING_INVALID,
                    message="An existing workspace migration must be recovered before another apply.",
                    path=".p2p/.internal/workspace-migrations",
                    recovery_action="p2p workspace migrate recovery status",
                )
            )
        if schema_status.migration_required:
            findings.append(
                CompatibilityFinding(
                    code="P2P324_WORKSPACE_MIGRATION_REQUIRED",
                    classification=FINDING_MIGRATION_REQUIRED,
                    message="Workspace schema is undeclared and has a registered migration path.",
                    recovery_action="p2p workspace migrate plan --to 1",
                    migration_id="workspace-legacy-to-v1",
                )
            )
        elif getattr(schema_status, "upgrade_available", False):
            findings.append(
                CompatibilityFinding(
                    code="P2P308_WORKSPACE_SCHEMA_UPGRADE_AVAILABLE",
                    classification=FINDING_MIGRATION_REQUIRED,
                    message=(
                        f"Workspace schema {schema_status.current_version} is valid and upgradeable "
                        f"to {schema_status.target_version}."
                    ),
                    recovery_action=(
                        f"p2p workspace migrate plan --to {schema_status.target_version} --format json"
                    ),
                    migration_id="workspace-v1-to-v2",
                )
            )
        for item in inventory:
            if item.classification == "invalid_symlink":
                findings.append(
                    CompatibilityFinding(
                        code="P2P325_WORKSPACE_PATH_ESCAPE",
                        classification=FINDING_INVALID,
                        message="Managed-root symlink resolves outside .p2p and cannot be migrated safely.",
                        path=item.path,
                    )
                )
            elif item.classification == "unknown":
                findings.append(
                    CompatibilityFinding(
                        code="P2P326_UNKNOWN_DURABLE_ARTIFACT",
                        classification=FINDING_DEGRADED,
                        message="Unknown durable artifact will be preserved without semantic claims.",
                        path=item.path,
                    )
                )
        if not project:
            findings.append(
                CompatibilityFinding(
                    code="P2P327_INVALID_PROJECT_MANIFEST",
                    classification=FINDING_INVALID,
                    message="Project manifest is missing or invalid.",
                    path=".p2p/project.yml",
                )
            )
        project_data = project.get("project") if isinstance(project, Mapping) else None
        domain = str(project_data.get("domain") or "") if isinstance(project_data, Mapping) else ""
        if domain == "software" and not (self.p2p_dir / "project" / "vertical.yml").exists():
            findings.append(
                CompatibilityFinding(
                    code="P2P332_SOFTWARE_VERTICAL_UNDECLARED",
                    classification=FINDING_DEGRADED,
                    message="Software-domain evidence exists but no project vertical is explicitly selected.",
                    path=".p2p/project/vertical.yml",
                    recovery_action="Supply an explicit vertical owner input to workspace migration planning.",
                )
            )
        permissions_path = self.p2p_dir / "project" / "permissions.yml"
        if permissions_path.exists():
            try:
                permissions = self._captured_yaml(".p2p/project/permissions.yml")
                PermissionsService(root=self.root, p2p_dir=self.p2p_dir).validate_policy_payload(
                    permissions,
                    require_single_owner=True,
                )
            except ValueError as exc:
                findings.append(
                    CompatibilityFinding(
                        code="P2P335_PERMISSION_OWNER_CONFLICT",
                        classification=FINDING_INVALID,
                        message=str(exc),
                        path=".p2p/project/permissions.yml",
                        recovery_action="Resolve permission identities before workspace migration.",
                    )
                )
        return findings

    def _invoke_existing_inspectors(self, findings: list[CompatibilityFinding]) -> None:
        for name, inspector in (
            ("runtime", self.runtime_status),
            ("vertical", self.vertical_context),
            ("decision_context", self.decision_context_index),
            ("freshness", self.freshness_status),
        ):
            if inspector is None:
                continue
            try:
                result = inspector()
                if name == "decision_context":
                    for diagnostic in getattr(result, "diagnostics", ()):
                        if getattr(diagnostic, "code", "") != "DC-RELATION-AMBIGUOUS-TYPE":
                            continue
                        findings.append(
                            CompatibilityFinding(
                                code="P2P329_AMBIGUOUS_RELATION_CURATION_REQUIRED",
                                classification=FINDING_REPOSITORY_CURATION_REQUIRED,
                                message=str(getattr(diagnostic, "message", "Ambiguous relation requires curation.")),
                                path=str(getattr(diagnostic, "source_path", "")),
                                recovery_action="Use impact preview/apply after owner semantic review.",
                            )
                        )
            except (OSError, ValueError) as exc:
                findings.append(
                    CompatibilityFinding(
                        code=f"P2P328_{name.upper()}_INSPECTION_FAILED",
                        classification=FINDING_INVALID,
                        message=f"Existing {name} inspector failed: {exc}",
                    )
                )

    def _required_owner_inputs(
        self,
        domain: str,
        owner_inputs: Mapping[str, object],
    ) -> tuple[tuple[str, str], ...]:
        missing: list[tuple[str, str]] = []
        if domain == "software" and not (self.p2p_dir / "project" / "vertical.yml").exists():
            vertical = owner_inputs.get("vertical")
            if not isinstance(vertical, dict) or not str(vertical.get("id") or "").strip():
                missing.append(("vertical.id", "Software workspace requires explicit vertical selection."))
        if not (self.p2p_dir / "project" / "permissions.yml").exists():
            owner = owner_inputs.get("owner")
            if not isinstance(owner, dict) or not str(owner.get("id") or owner.get("name") or "").strip():
                missing.append(("owner.id", "Permission migration requires one explicit owner identity."))
        return tuple(missing)

    def _plan_domain(
        self,
        snapshot: CompatibilitySnapshot,
        project: Mapping[str, object],
        domain: str,
        migration_id: str,
        candidates: dict[str, bytes],
        operations: list[MigrationOperation],
    ) -> None:
        target = ".p2p/project/domain.yml"
        if self._hash_for(snapshot, target) is not None:
            return
        if not domain:
            return
        payload = domain_state_payload(domain)
        payload["provenance"] = {"source": ".p2p/project.yml", "migration": migration_id}
        candidates[target] = yaml_dump(payload).encode("utf-8")
        operations.append(
            self._candidate_operation(
                snapshot,
                operation_id="materialize-domain",
                kind=OP_CREATE_CANONICAL,
                target=target,
                reason="Materialize explicit domain state from the valid project manifest.",
                migration_id=migration_id,
                candidate=payload,
                validator="ProjectMaturityService",
            )
        )

    def _plan_permissions(
        self,
        snapshot: CompatibilitySnapshot,
        project: Mapping[str, object],
        owner_inputs: Mapping[str, object],
        migration_id: str,
        candidates: dict[str, bytes],
        operations: list[MigrationOperation],
    ) -> None:
        target = ".p2p/project/permissions.yml"
        if self._hash_for(snapshot, target) is not None:
            return
        owner = owner_inputs.get("owner")
        if not isinstance(owner, dict):
            return
        owner_id = str(owner.get("id") or owner.get("name") or "").strip()
        if not owner_id:
            return
        repository = project.get("repository") if isinstance(project.get("repository"), Mapping) else {}
        repository_mode = str(repository.get("mode") or "local")
        legacy_roles = self._captured_yaml(".p2p/governance/roles.yml")
        payload = PermissionsService(root=self.root, p2p_dir=self.p2p_dir).render_migration_candidate(
            owner_id=owner_id,
            owner_name=str(owner.get("name") or owner_id),
            repository_mode=repository_mode,
            legacy_roles=legacy_roles,
            migration_id=migration_id,
        )
        candidates[target] = yaml_dump(payload).encode("utf-8")
        operations.append(
            self._candidate_operation(
                snapshot,
                operation_id="materialize-permissions",
                kind=OP_CREATE_CANONICAL,
                target=target,
                reason="Materialize explicit owner permission state.",
                migration_id=migration_id,
                candidate=payload,
                validator="PermissionsService",
            )
        )

    def _plan_metadata(
        self,
        snapshot: CompatibilitySnapshot,
        project: Mapping[str, object],
        owner_inputs: Mapping[str, object],
        migration_id: str,
        candidates: dict[str, bytes],
        operations: list[MigrationOperation],
    ) -> None:
        metadata = owner_inputs.get("metadata")
        if not isinstance(metadata, dict) or not metadata:
            return
        patch = ProjectMetadataPatch(
            actor=SEMANTIC_AUDIT_ACTOR,
            values={key: str(value) for key, value in metadata.items()},
        )
        candidate = ProjectMetadataService(root=self.root, p2p_dir=self.p2p_dir).render_candidate(
            project,
            patch,
            audit_at=SEMANTIC_AUDIT_TIMESTAMP,
        )
        target = ".p2p/project.yml"
        candidates[target] = yaml_dump(candidate).encode("utf-8")
        operations.append(
            self._candidate_operation(
                snapshot,
                operation_id="update-project-metadata",
                kind="update_canonical",
                target=target,
                reason="Apply the narrow owner-approved project metadata patch.",
                migration_id=migration_id,
                candidate=candidate,
                validator="ProjectMetadataService",
            )
        )

    def _plan_vertical(
        self,
        snapshot: CompatibilitySnapshot,
        owner_inputs: Mapping[str, object],
        domain: str,
        migration_id: str,
        candidates: dict[str, bytes],
        operations: list[MigrationOperation],
        findings: list[CompatibilityFinding],
    ) -> bool:
        vertical = owner_inputs.get("vertical")
        if isinstance(vertical, dict) and str(vertical.get("id") or "").strip():
            if self.vertical_candidate_renderer is None:
                findings.append(
                    CompatibilityFinding(
                        code="P2P333_VERTICAL_RENDERER_UNAVAILABLE",
                        classification=FINDING_ENGINE_PREREQUISITE_REQUIRED,
                        message="The workspace migration service has no vertical candidate renderer.",
                        recovery_action="Use the P2PWorkspace migration facade.",
                        migration_id=migration_id,
                    )
                )
                return False
            try:
                candidate = self.vertical_candidate_renderer(
                    str(vertical.get("id")),
                    actor=SEMANTIC_AUDIT_ACTOR,
                    profile=str(vertical.get("profile") or "default"),
                    modules=list(vertical.get("modules") or []),
                    audit_date=SEMANTIC_AUDIT_TIMESTAMP,
                    rubric_mapping=dict(vertical.get("rubric_mapping") or {}),
                )
            except (OSError, ValueError) as exc:
                findings.append(
                    CompatibilityFinding(
                        code="P2P334_INVALID_VERTICAL_MIGRATION_CANDIDATE",
                        classification=FINDING_INVALID,
                        message=str(exc),
                        recovery_action="Correct vertical/profile/module/rubric owner inputs and re-plan.",
                        migration_id=migration_id,
                    )
                )
                return False
            for index, target in enumerate(sorted(candidate.candidate_files)):
                content = candidate.candidate_files[target]
                payload = yaml.safe_load(content.decode("utf-8"))
                candidates[target] = content
                operations.append(
                    self._candidate_operation(
                        snapshot,
                        operation_id=(
                            "select-project-vertical"
                            if target == ".p2p/project/vertical.yml"
                            else f"select-project-vertical-{index + 1}"
                        ),
                        kind=OP_CREATE_CANONICAL if self._hash_for(snapshot, target) is None else "update_canonical",
                        target=target,
                        reason="Commit the complete owner-selected vertical candidate set.",
                        migration_id=migration_id,
                        candidate=payload,
                        validator="ProjectVerticalService",
                    )
                )
            return True
        elif domain == "software":
            return False
        return True

    def _plan_unknown_preservation(
        self,
        snapshot: CompatibilitySnapshot,
        migration_id: str,
        operations: list[MigrationOperation],
    ) -> None:
        for item in snapshot.inventory:
            if item.classification != "unknown":
                continue
            operations.append(
                MigrationOperation(
                    operation_id="preserve-" + item.path.replace("/", "-").replace(".", "-").strip("-"),
                    kind=OP_PRESERVE_LEGACY,
                    target=item.path,
                    reason="Unknown durable artifact is outside transition ownership and is preserved.",
                    migration_id=migration_id,
                    write_class="read_only",
                    canonical=False,
                    before_exists=True,
                    before_physical_sha256=item.physical_sha256,
                    candidate_semantic_sha256=item.semantic_sha256,
                    validator="none",
                    rollback="none",
                )
            )

    def _plan_derived_refresh(self, migration_id: str, operations: list[MigrationOperation]) -> None:
        operations.append(
            MigrationOperation(
                operation_id="refresh-derived-after-migration",
                kind=OP_REFRESH_DERIVED,
                target="derived-state",
                reason="Canonical migration invalidates dependent derived layers.",
                migration_id=migration_id,
                write_class="generated_export",
                canonical=False,
                before_exists=False,
                before_physical_sha256=None,
                candidate_semantic_sha256=None,
                validator="DerivedFreshnessService",
                rollback="rebuild after canonical commit",
                applicable=False,
            )
        )

    def _semantic_schema_payload(
        self,
        *,
        migration_id: str,
        source_version: int,
        target_version: int,
    ) -> dict[str, object]:
        return {
            "workspace_schema": {
                "contract_version": WORKSPACE_SCHEMA_CONTRACT_VERSION,
                "current_version": target_version,
                "baseline": "migrated_legacy",
                "initialized_at": SEMANTIC_AUDIT_TIMESTAMP,
                "initialized_by": SEMANTIC_AUDIT_ACTOR,
                "applied_migrations": [
                    {
                        "id": migration_id,
                        "from": "legacy_undeclared" if source_version == 0 else source_version,
                        "to": target_version,
                        "applied_at": SEMANTIC_AUDIT_TIMESTAMP,
                        "actor": SEMANTIC_AUDIT_ACTOR,
                        "plan_fingerprint_sha256": "__P2P_PLAN_FINGERPRINT__",
                    }
                ],
            }
        }

    def _candidate_operation(
        self,
        snapshot: CompatibilitySnapshot,
        *,
        operation_id: str,
        kind: str,
        target: str,
        reason: str,
        migration_id: str,
        candidate: object,
        validator: str,
        dependencies: tuple[str, ...] = (),
    ) -> MigrationOperation:
        before_hash = self._hash_for(snapshot, target)
        return MigrationOperation(
            operation_id=operation_id,
            kind=kind,
            target=target,
            reason=reason,
            migration_id=migration_id,
            write_class="p2p_canonical",
            canonical=True,
            before_exists=before_hash is not None,
            before_physical_sha256=before_hash,
            candidate_semantic_sha256=semantic_sha256(candidate),
            validator=validator,
            rollback="restore captured preimage or remove created target",
            dependencies=dependencies,
        )

    def _finalize_plan(
        self,
        *,
        status: str,
        source_version: int,
        target_version: int,
        migrations: tuple[Any, ...],
        operations: tuple[MigrationOperation, ...],
        findings: tuple[CompatibilityFinding, ...],
        owner_inputs: Mapping[str, object],
        candidate_files: Mapping[str, bytes],
        applicable: bool,
    ) -> MigrationPlan:
        migration_ids = tuple(item.migration_id for item in migrations)
        if migration_ids and candidate_files:
            self.registry.validate_candidate_ownership(migration_ids, candidate_files)
        fingerprint_payload = {
            "source_version": source_version,
            "target_version": target_version,
            "direction": "forward" if target_version >= source_version else "downgrade",
            "migration_ids": list(migration_ids),
            "operations": [item.to_dict() for item in operations],
            "owner_inputs": owner_inputs,
            "planner_version": WORKSPACE_PLANNER_VERSION,
        }
        fingerprint = hashlib.sha256(canonical_json_bytes(fingerprint_payload)).hexdigest()
        return MigrationPlan(
            status=status,
            source_version=source_version,
            target_version=target_version,
            direction="forward" if target_version >= source_version else "downgrade",
            migration_ids=migration_ids,
            operations=operations,
            findings=findings,
            owner_inputs=dict(owner_inputs),
            planner_version=WORKSPACE_PLANNER_VERSION,
            fingerprint_sha256=fingerprint,
            applicable=applicable,
            transition_support=tuple(item.runtime_support(self.engine_version) for item in migrations),
            candidate_files=dict(candidate_files),
        )

    def _unsupported_plan(
        self,
        source_version: int,
        target_version: int,
        owner_inputs: Mapping[str, object],
        code: str,
        message: str,
    ) -> MigrationPlan:
        finding = CompatibilityFinding(
            code=code,
            classification=FINDING_UNSUPPORTED,
            message=message,
            recovery_action="Select a supported forward target.",
        )
        return self._finalize_plan(
            status=MIGRATION_STATUS_BLOCKED,
            source_version=source_version,
            target_version=target_version,
            migrations=(),
            operations=(),
            findings=(finding,),
            owner_inputs=owner_inputs,
            candidate_files={},
            applicable=False,
        )

    def _captured_yaml(self, relative: str) -> dict[str, object]:
        content = self._captured_bytes.get(relative)
        if content is None:
            path = self.root / relative
            if not path.exists() or not path.is_file() or path.is_symlink():
                return {}
            content = path.read_bytes()
            self._captured_bytes[relative] = content
        self._yaml_parse_count += 1
        try:
            value = yaml.safe_load(content.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError):
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _hash_for(snapshot: CompatibilitySnapshot, path: str) -> str | None:
        return next(
            (item.physical_sha256 for item in snapshot.inventory if item.path == path),
            None,
        )

    @staticmethod
    def _semantic_file_hash(path: str, content: bytes) -> str | None:
        if path.endswith((".yml", ".yaml")):
            try:
                return semantic_sha256(yaml.safe_load(content.decode("utf-8")))
            except (UnicodeDecodeError, yaml.YAMLError):
                return None
        return hashlib.sha256(content).hexdigest()


def load_owner_input_patch(path: Path) -> dict[str, object]:
    payload = read_yaml_mapping(
        path,
        default={},
        error_message="Migration input patch must be a YAML mapping: {path}",
    )
    return normalize_owner_inputs(payload)


def normalize_owner_inputs(owner_inputs: Mapping[str, object]) -> dict[str, object]:
    unknown = set(owner_inputs) - _OWNER_INPUT_KEYS
    if unknown:
        raise ValueError(f"Unknown migration owner input fields: {', '.join(sorted(unknown))}")
    normalized: dict[str, object] = {}
    for key, allowed in (
        ("vertical", _VERTICAL_INPUT_KEYS),
        ("owner", _OWNER_IDENTITY_KEYS),
        ("metadata", _METADATA_INPUT_KEYS),
    ):
        value = owner_inputs.get(key)
        if value is None:
            continue
        if not isinstance(value, Mapping):
            raise ValueError(f"Migration owner input {key} must be a mapping")
        unknown_nested = set(value) - allowed
        if unknown_nested:
            raise ValueError(
                f"Unknown migration owner input fields for {key}: {', '.join(sorted(unknown_nested))}"
            )
        nested: dict[str, object] = {}
        for nested_key in sorted(value):
            nested_value = value[nested_key]
            if nested_key == "modules":
                if not isinstance(nested_value, list) or not all(
                    isinstance(item, str) and item.strip() for item in nested_value
                ):
                    raise ValueError("vertical.modules must be a sequence of non-empty strings")
                nested[nested_key] = sorted(set(item.strip() for item in nested_value))
                continue
            if nested_key == "rubric_mapping":
                if not isinstance(nested_value, Mapping):
                    raise ValueError("vertical.rubric_mapping must be a mapping of legacy ids to current ids")
                normalized_mapping: dict[str, str] = {}
                for source_id, target_id in sorted(nested_value.items(), key=lambda item: str(item[0])):
                    if not isinstance(source_id, str) or not source_id.strip():
                        raise ValueError("vertical.rubric_mapping keys must be non-empty strings")
                    if not isinstance(target_id, str) or not target_id.strip():
                        raise ValueError("vertical.rubric_mapping values must be non-empty strings")
                    _reject_unsafe_value("vertical.rubric_mapping", source_id)
                    _reject_unsafe_value("vertical.rubric_mapping", target_id)
                    normalized_mapping[source_id.strip()] = target_id.strip()
                nested[nested_key] = normalized_mapping
                continue
            if not isinstance(nested_value, str) or not nested_value.strip():
                raise ValueError(f"Migration owner input {key}.{nested_key} must be a non-empty string")
            normalized_text = nested_value.strip()
            _reject_unsafe_value(f"{key}.{nested_key}", normalized_text)
            nested[nested_key] = normalized_text
        normalized[key] = nested
    project_questions = owner_inputs.get("project_questions")
    if project_questions is not None:
        if not isinstance(project_questions, Mapping):
            raise ValueError("Migration owner input project_questions must be a mapping")
        unknown_question_fields = set(project_questions) - {"legacy_bindings"}
        if unknown_question_fields:
            raise ValueError(
                "Unknown migration owner input fields for project_questions: "
                + ", ".join(sorted(unknown_question_fields))
            )
        raw_bindings = project_questions.get("legacy_bindings")
        if not isinstance(raw_bindings, Mapping) or not raw_bindings:
            raise ValueError("project_questions.legacy_bindings must be a non-empty mapping")
        bindings: dict[str, dict[str, str]] = {}
        for source_key, raw_binding in sorted(raw_bindings.items(), key=lambda item: str(item[0])):
            if not isinstance(source_key, str) or not source_key.strip():
                raise ValueError("Legacy question binding keys must be non-empty section/question ids")
            _reject_unsafe_value("project_questions.legacy_bindings", source_key)
            if not isinstance(raw_binding, Mapping):
                raise ValueError(f"Legacy question binding `{source_key}` must be a mapping")
            unknown_binding = set(raw_binding) - {"target_kind", "target_id", "answer_contract"}
            if unknown_binding:
                raise ValueError(
                    f"Legacy question binding `{source_key}` contains forbidden fields: "
                    + ", ".join(sorted(unknown_binding))
                )
            normalized_binding: dict[str, str] = {}
            for field in ("target_kind", "target_id", "answer_contract"):
                value = raw_binding.get(field)
                if field == "answer_contract" and value is None:
                    continue
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"Legacy question binding `{source_key}` requires `{field}`")
                _reject_unsafe_value(f"project_questions.legacy_bindings.{field}", value)
                normalized_binding[field] = value.strip()
            bindings[source_key.strip()] = normalized_binding
        normalized["project_questions"] = {"legacy_bindings": bindings}
    return normalized


def _reject_unsafe_value(field: str, value: str) -> None:
    path = PurePosixPath(value)
    if value.startswith(("/", "~")) or ".." in path.parts or "\x00" in value:
        raise ValueError(f"Unsafe path/provenance value for {field}")

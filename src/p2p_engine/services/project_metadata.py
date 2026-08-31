from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from pathlib import Path

import yaml

from p2p_engine.core.mutation_preview import (
    MutationPreview,
    MutationPreviewService,
    MutationResult,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.project_metadata import (
    PROJECT_METADATA_ALLOWED_FIELDS,
    PROJECT_METADATA_POLICY_VERSION,
    ProjectMetadataPatch,
    ProjectMetadataView,
)
from p2p_engine.foundation.files import read_yaml_mapping, slugify, yaml_dump
from p2p_engine.services.workspace_transactions import AtomicMutationWriter, utc_now_iso


PROJECT_STATUSES = frozenset({"bootstrap_manual", "active", "paused", "maintenance", "archived"})
PROJECT_STATUS_TRANSITIONS = {
    "bootstrap_manual": frozenset({"bootstrap_manual", "active", "paused"}),
    "active": frozenset({"active", "paused", "maintenance", "archived"}),
    "paused": frozenset({"paused", "active", "maintenance", "archived"}),
    "maintenance": frozenset({"maintenance", "active", "paused", "archived"}),
    "archived": frozenset({"archived"}),
}
WORKFLOW_PHASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class ProjectMetadataService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        atomic_writer: AtomicMutationWriter | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.path = self.p2p_dir / "project.yml"
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=self.root, p2p_dir=self.p2p_dir)
        self.clock = clock

    def show(self) -> ProjectMetadataView:
        payload = self._read_project()
        return ProjectMetadataView(
            path=self.path.relative_to(self.root).as_posix(),
            values=self._values(payload),
            preserved_hashes=self._preserved_hashes(payload),
        )

    def parse_patch(self, patch_path: Path, *, actor: str) -> ProjectMetadataPatch:
        source = patch_path if patch_path.is_absolute() else self.root / patch_path
        payload = read_yaml_mapping(
            source,
            default={},
            error_message="Project metadata patch must be a YAML mapping: {path}",
        )
        data = payload.get("project_metadata_patch")
        if not isinstance(data, Mapping):
            raise ValueError("Project metadata patch requires `project_metadata_patch` mapping.")
        unknown = set(data) - {"policy_version", "actor", *PROJECT_METADATA_ALLOWED_FIELDS}
        if unknown:
            raise ValueError(f"Unsupported project metadata fields: {', '.join(sorted(unknown))}")
        patch_actor = str(data.get("actor") or "").strip()
        if patch_actor != actor:
            raise ValueError("Project metadata patch actor must match the requested actor.")
        policy_version = data.get("policy_version", PROJECT_METADATA_POLICY_VERSION)
        if policy_version != PROJECT_METADATA_POLICY_VERSION:
            raise ValueError(f"Unsupported project metadata policy version: {policy_version}")
        values: dict[str, str] = {}
        for field in PROJECT_METADATA_ALLOWED_FIELDS:
            if field not in data:
                continue
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Project metadata `{field}` must be a non-empty string.")
            values[field] = value.strip()
        if not values:
            raise ValueError("Project metadata patch has no allowed changes.")
        return ProjectMetadataPatch(actor=actor, values=values)

    def render_candidate(
        self,
        current: Mapping[str, object],
        patch: ProjectMetadataPatch,
        *,
        audit_at: str,
    ) -> dict[str, object]:
        candidate = yaml.safe_load(yaml.safe_dump(dict(current), sort_keys=False))
        if not isinstance(candidate, dict):
            raise ValueError("Project manifest must be a mapping.")
        project = candidate.get("project")
        workflow = candidate.get("workflow")
        if not isinstance(project, dict) or not isinstance(workflow, dict):
            raise ValueError("Project metadata requires mapping-shaped project and workflow sections.")
        before_status = str(project.get("status") or "")
        status = patch.values.get("status")
        if status is not None:
            self._validate_status_transition(before_status, status)
            project["status"] = status
        phase = patch.values.get("workflow_phase")
        if phase is not None:
            if not WORKFLOW_PHASE_PATTERN.fullmatch(phase):
                raise ValueError("workflow_phase must be a lower-case identifier of at most 64 characters.")
            workflow["current_phase"] = phase
        objective = patch.values.get("current_objective")
        if objective is not None:
            if len(objective) > 1000 or "\x00" in objective:
                raise ValueError("current_objective must be at most 1000 safe characters.")
            workflow["current_objective"] = objective
        audit = candidate.setdefault("metadata_audit", [])
        if not isinstance(audit, list):
            raise ValueError("Project metadata audit must be a sequence when present.")
        audit.append(
            {
                "policy_version": PROJECT_METADATA_POLICY_VERSION,
                "at": audit_at,
                "actor": patch.actor,
                "changed_fields": sorted(patch.values),
            }
        )
        self.validate_candidate(current, candidate, patch)
        return candidate

    def validate_candidate(
        self,
        current: Mapping[str, object],
        candidate: Mapping[str, object],
        patch: ProjectMetadataPatch,
    ) -> None:
        unknown = set(patch.values) - set(PROJECT_METADATA_ALLOWED_FIELDS)
        if unknown:
            raise ValueError(f"Unsupported project metadata fields: {', '.join(sorted(unknown))}")
        for protected in ("runtime_contract", "storage", "ai"):
            if current.get(protected) != candidate.get(protected):
                raise ValueError(f"Project metadata patch cannot change protected `{protected}` configuration.")
        current_project = current.get("project")
        candidate_project = candidate.get("project")
        if not isinstance(current_project, Mapping) or not isinstance(candidate_project, Mapping):
            raise ValueError("Project manifest project section must be a mapping.")
        for protected in ("id", "uuid", "name", "version", "domain", "meaning"):
            if current_project.get(protected) != candidate_project.get(protected):
                raise ValueError(f"Project metadata patch cannot change project.{protected}.")

    def preview(self, patch_path: Path, *, actor: str) -> MutationPreview:
        patch = self.parse_patch(patch_path, actor=actor)
        current = self._read_project()
        candidate = self.render_candidate(current, patch, audit_at="__P2P_APPLY_AT__")
        relative = self.path.relative_to(self.root).as_posix()
        current_bytes = self.path.read_bytes()
        authority = self._authority(actor)
        semantic_candidate = self._semantic_candidate(candidate)
        before = self._values(current)
        after = self._values(candidate)
        return MutationPreviewService.build(
            operation_id="project-metadata-update",
            targets=(relative,),
            actor=actor,
            authority=authority,
            sources=(source_precondition(relative, current_bytes),),
            candidate_semantics={relative: semantic_candidate},
            semantic_diff={
                relative: {
                    field: {"before": before.get(field, ""), "after": after.get(field, "")}
                    for field in sorted(patch.values)
                    if before.get(field, "") != after.get(field, "")
                }
            },
            blockers=() if authority == "owner_confirmed" else (authority,),
        )

    def apply(
        self,
        patch_path: Path,
        *,
        preview_token: str,
        actor: str,
        confirm: bool,
    ) -> MutationResult:
        preview = self.preview(patch_path, actor=actor)
        if not confirm:
            return self._blocked(preview, actor, "Explicit confirmation is required for project metadata updates.")
        if preview.preview_token != preview_token:
            return MutationResult(
                status="stale_preview",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Project metadata source or patch changed after preview.",
            )
        if not preview.apply_allowed:
            return self._blocked(preview, actor, "Actor is not authorized to update project metadata.")
        patch = self.parse_patch(patch_path, actor=actor)
        current = self._read_project()
        candidate = self.render_candidate(current, patch, audit_at=self.clock())
        relative = self.path.relative_to(self.root).as_posix()
        return self.atomic_writer.apply(
            operation_id=preview.operation_id,
            candidates={relative: yaml_dump(candidate).encode("utf-8")},
            sources=preview.source_preconditions,
            preview_token=preview.preview_token,
            actor=actor,
        )

    def _read_project(self) -> dict[str, object]:
        if not self.path.exists():
            raise ValueError("Project manifest is missing.")
        return read_yaml_mapping(
            self.path,
            default={},
            error_message="Project manifest must be a YAML mapping: {path}",
        )

    def _validate_status_transition(self, current: str, candidate: str) -> None:
        if candidate not in PROJECT_STATUSES:
            raise ValueError(f"Unsupported project status `{candidate}`.")
        allowed = PROJECT_STATUS_TRANSITIONS.get(current, PROJECT_STATUSES)
        if candidate not in allowed:
            raise ValueError(f"Invalid project status transition `{current}` -> `{candidate}`.")

    def _authority(self, actor: str) -> str:
        path = self.p2p_dir / "project" / "permissions.yml"
        if not path.exists():
            return "owner_required"
        payload = read_yaml_mapping(path, default={})
        identities = payload.get("identities")
        identity = identities.get(slugify(actor)) if isinstance(identities, Mapping) else None
        return "owner_confirmed" if isinstance(identity, Mapping) and identity.get("role") == "owner" else "owner_required"

    @staticmethod
    def _values(payload: Mapping[str, object]) -> dict[str, str]:
        project = payload.get("project") if isinstance(payload.get("project"), Mapping) else {}
        workflow = payload.get("workflow") if isinstance(payload.get("workflow"), Mapping) else {}
        return {
            "status": str(project.get("status") or ""),
            "workflow_phase": str(workflow.get("current_phase") or ""),
            "current_objective": str(workflow.get("current_objective") or workflow.get("next_goal") or ""),
        }

    @staticmethod
    def _preserved_hashes(payload: Mapping[str, object]) -> dict[str, str]:
        return {
            key: semantic_sha256(payload.get(key))
            for key in ("runtime_contract", "remote", "repository")
        }

    @staticmethod
    def _semantic_candidate(candidate: Mapping[str, object]) -> dict[str, object]:
        normalized = yaml.safe_load(yaml.safe_dump(dict(candidate), sort_keys=False))
        audit = normalized.get("metadata_audit") if isinstance(normalized, dict) else None
        if isinstance(audit, list):
            for item in audit:
                if isinstance(item, dict):
                    item.pop("at", None)
        return normalized if isinstance(normalized, dict) else {}

    @staticmethod
    def _blocked(preview: MutationPreview, actor: str, message: str) -> MutationResult:
        return MutationResult(
            status="blocked",
            operation_id=preview.operation_id,
            preview_token=preview.preview_token,
            actor=actor,
            message=message,
        )

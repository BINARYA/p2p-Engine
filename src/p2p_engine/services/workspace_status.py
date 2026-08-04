from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from p2p_engine.core.workspace_reads import (
    FastFreshnessSummary,
    PublicReadCostPolicy,
    ReadCostClass,
)
from p2p_engine.foundation.files import read_yaml_mapping_or_default
from p2p_engine.foundation.yaml_loaders import load_yaml_mapping
from p2p_engine.core.proposal_decision_events import ProposalDecisionLifecycleView
from p2p_engine.foundation.markdown import read_title
from p2p_engine.services.lifecycle_authority import proposal_display_status
from p2p_engine.services.workspace_reads import WorkspaceReadContext


_T = TypeVar("_T")


def _provide(
    context: WorkspaceReadContext | None,
    name: str,
    arguments: tuple[object, ...],
    factory: Callable[[], _T],
) -> _T:
    if context is None:
        return factory()
    return context.provide(name, arguments, factory)


@dataclass(frozen=True)
class ProposalSummary:
    proposal_id: str
    slug: str
    status: str
    title: str = ""
    effective_state: str = "unknown"
    head_event_type: str | None = None
    head_event_id: str | None = None
    event_count: int = 0
    authority_resolution: str = "invalid"
    ever_active: bool = False
    active: bool = False
    proposal_binding_status: str = "unavailable"
    decision_semantic_sha256: str | None = None


@dataclass(frozen=True)
class WorkspaceStatus:
    root: Path
    project_name: str
    proposals: list[ProposalSummary]
    workspace_schema: dict[str, object] | None = None
    derived_freshness: dict[str, object] | None = None


@dataclass(frozen=True)
class WorkspaceCheck:
    ok: bool
    missing: list[Path]


_NO_DEEP = (
    "complete_validation",
    "complete_freshness",
    "decision_context_full",
    "publication_build",
    "software_spec_build",
)

PUBLIC_READ_COST_POLICIES: tuple[PublicReadCostPolicy, ...] = (
    PublicReadCostPolicy("status", ReadCostClass.FAST, ("schema_preflight", "lifecycle_batch", "fast_freshness"), _NO_DEEP),
    PublicReadCostPolicy("proposal_list", ReadCostClass.FAST, ("registry", "lifecycle_batch"), _NO_DEEP),
    PublicReadCostPolicy("project_progress", ReadCostClass.FAST, ("vertical_memory", "readiness"), _NO_DEEP),
    PublicReadCostPolicy("context_small", ReadCostClass.FAST, ("registry", "vertical_memory", "readiness", "next"), _NO_DEEP),
    PublicReadCostPolicy("context_targeted", ReadCostClass.TARGETED, ("registry", "vertical_memory", "decision_context", "next"), ("publication_build", "software_spec_build")),
    PublicReadCostPolicy("next", ReadCostClass.FAST, ("schema_preflight", "registry", "vertical_memory", "readiness", "lifecycle_batch"), _NO_DEEP),
    PublicReadCostPolicy("validate", ReadCostClass.DEEP, ("complete_validation",)),
    PublicReadCostPolicy("project_freshness", ReadCostClass.DEEP, ("complete_freshness",)),
)


def public_read_cost_policy(operation: str) -> PublicReadCostPolicy:
    try:
        return next(item for item in PUBLIC_READ_COST_POLICIES if item.operation == operation)
    except StopIteration as exc:
        raise ValueError(f"Unknown public read operation: {operation}") from exc


class FastFreshnessService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        schema_preflight: Callable[[], Any],
        registry_status: Callable[..., Any],
        vertical_memory_status: Callable[..., Any],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.schema_preflight = schema_preflight
        self.registry_status = registry_status
        self.vertical_memory_status = vertical_memory_status

    def status(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> FastFreshnessSummary:
        schema = _provide(read_context, "schema_preflight", (), self.schema_preflight)
        registry = _provide(
            read_context,
            "registry_status",
            (),
            lambda: self.registry_status(read_context=read_context)
            if read_context is not None
            else self.registry_status(),
        )
        memory = _provide(
            read_context,
            "vertical_memory_status",
            (),
            lambda: self.vertical_memory_status(read_context=read_context),
        )
        schema_state = str(getattr(schema, "state", "unknown"))
        registry_state = str(getattr(registry, "state", "unknown"))
        memory_state = str(getattr(memory, "state", "unknown"))
        projection_state = self._project_projection_state(memory, read_context=read_context)
        assessment_state = self._required_output_state(
            self.p2p_dir / "project" / "assessment.yml",
            read_context=read_context,
        )
        attention = tuple(
            name
            for name, state, current_values in (
                ("workspace_schema", schema_state, {"compatible", "current"}),
                ("registry_bundle", registry_state, {"current"}),
                ("vertical_project_memory", memory_state, {"current"}),
                ("project_projections", projection_state, {"current_basis"}),
                ("assessment", assessment_state, {"present"}),
            )
            if state not in current_values
        )
        commands = {
            "vertical_project_memory": "p2p project refresh",
            "project_projections": "p2p project refresh",
            "assessment": "p2p assess refresh",
        }
        next_node = next((item for item in attention if item in commands), "")
        return FastFreshnessSummary(
            status="attention" if attention else "current",
            schema_state=schema_state,
            registry_state=registry_state,
            vertical_memory_state=memory_state,
            project_projection_state=projection_state,
            attention=attention,
            next_node=next_node,
            next_command=commands.get(next_node, "p2p project freshness"),
        )

    def _required_output_state(
        self,
        path: Path,
        *,
        read_context: WorkspaceReadContext | None,
    ) -> str:
        if read_context is not None:
            return "present" if read_context.documents.capture(path).exists else "missing"
        return "present" if path.is_file() and not path.is_symlink() else "missing"

    def _project_projection_state(
        self,
        memory: object,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> str:
        path = self.p2p_dir / "project" / "projection-manifest.yml"
        if read_context is not None:
            document = read_context.documents.capture(path)
            if not document.exists:
                return "missing"
            payload = load_yaml_mapping(read_context.documents.bytes(path))
        elif not path.is_file() or path.is_symlink():
            return "missing"
        else:
            payload = read_yaml_mapping_or_default(path)
        data = payload.get("project_projection")
        if not isinstance(data, Mapping) or int(data.get("manifest_version") or 0) != 1:
            return "invalid"
        memory_fingerprint = str(getattr(memory, "source_fingerprint_sha256", ""))
        recorded = str(data.get("vertical_memory_source_fingerprint_sha256") or "")
        if not memory_fingerprint or recorded != memory_fingerprint:
            return "stale_basis"
        return "current_basis"


class WorkspaceStatusService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        workspace_schema_status: Callable[[], Any] | None = None,
        workspace_schema_preflight: Callable[[], Any] | None = None,
        fast_freshness_status: Callable[..., FastFreshnessSummary] | None = None,
        derived_freshness_status: Callable[[], Any] | None = None,
        registry_status: Callable[..., Any] | None = None,
        proposal_decision_lifecycles: (
            Callable[..., Mapping[str, ProposalDecisionLifecycleView]] | None
        ) = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.workspace_schema_status = workspace_schema_status
        self.workspace_schema_preflight = workspace_schema_preflight
        self.fast_freshness_status = fast_freshness_status
        self.derived_freshness_status = derived_freshness_status
        self.registry_status = registry_status
        self.proposal_decision_lifecycles = proposal_decision_lifecycles

    def status(
        self,
        *,
        deep: bool = False,
        read_context: WorkspaceReadContext | None = None,
    ) -> WorkspaceStatus:
        project_name = "Unknown"
        project_file = self.p2p_dir / "project.yml"
        project_document = (
            read_context.documents.capture(project_file)
            if read_context is not None
            else None
        )
        if (project_document is not None and project_document.exists) or (
            project_document is None and project_file.exists()
        ):
            data = (
                load_yaml_mapping(read_context.documents.bytes(project_file))
                if read_context is not None
                else load_yaml_mapping(project_file.read_bytes())
            )
            project = data.get("project", {})
            if isinstance(project, dict):
                project_name = project.get("name", project_name)

        proposals = self._read_proposal_summaries(
            read_context=read_context,
            use_registry=False,
        )
        return WorkspaceStatus(
            root=self.root,
            project_name=project_name,
            proposals=proposals,
            workspace_schema=self._schema_summary(deep=deep, read_context=read_context),
            derived_freshness=self._freshness_summary(deep=deep, read_context=read_context),
        )

    def _read_proposal_summaries(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
        use_registry: bool = True,
    ) -> list[ProposalSummary]:
        registry_proposals = (
            self._current_registry_proposals(read_context)
            if use_registry
            else None
        )
        if registry_proposals is not None:
            return registry_proposals
        proposals: list[ProposalSummary] = []
        lifecycles = (
            self.proposal_decision_lifecycles(read_context=read_context)
            if self.proposal_decision_lifecycles is not None
            else {}
        )
        proposals_dir = self.p2p_dir / "proposals"
        if proposals_dir.exists():
            paths = (
                read_context.documents.discover(
                    proposals_dir,
                    policy="workspace-status-proposals-v1",
                    predicate=lambda path: path.is_dir(),
                )
                if read_context is not None
                else sorted(proposals_dir.iterdir())
            )
            for path in paths:
                if not path.is_dir():
                    continue
                proposal_id = "-".join(path.name.split("-", 2)[:2])
                lifecycle = lifecycles.get(proposal_id)
                proposal_path = path / "proposal.md"
                proposal_text = (
                    read_context.documents.text(proposal_path)
                    if read_context is not None
                    and read_context.documents.capture(proposal_path).exists
                    else _read_optional(proposal_path)
                    if read_context is None
                    else ""
                )
                projected_status = _proposal_status_from_text(proposal_text)
                effective_state = (
                    lifecycle.effective_state.value
                    if lifecycle is not None
                    else projected_status
                )
                status = (
                    proposal_display_status(
                        lifecycle,
                        undecided_fallback=projected_status,
                    )
                    if lifecycle is not None
                    else projected_status
                )
                proposals.append(
                    ProposalSummary(
                        proposal_id=proposal_id,
                        slug=path.name,
                        status=status,
                        title=_clean_proposal_title(
                            read_title(proposal_text) or path.name,
                            proposal_id,
                        ),
                        effective_state=effective_state,
                        head_event_type=(
                            lifecycle.head_event_type.value
                            if lifecycle is not None
                            and lifecycle.head_event_type is not None
                            else None
                        ),
                        head_event_id=(
                            lifecycle.head_event_id
                            if lifecycle is not None
                            else None
                        ),
                        event_count=(
                            lifecycle.event_count
                            if lifecycle is not None
                            else 0
                        ),
                        authority_resolution=(
                            lifecycle.authority_resolution.value
                            if lifecycle is not None
                            else "invalid"
                        ),
                        ever_active=(
                            lifecycle.ever_active
                            if lifecycle is not None
                            else False
                        ),
                        active=(
                            lifecycle.active
                            if lifecycle is not None
                            else False
                        ),
                        proposal_binding_status=(
                            lifecycle.proposal_binding_status.value
                            if lifecycle is not None
                            else "unavailable"
                        ),
                        decision_semantic_sha256=(
                            lifecycle.decision_semantic_sha256
                            if lifecycle is not None
                            else None
                        ),
                    )
                )
        return proposals

    def _current_registry_proposals(
        self,
        read_context: WorkspaceReadContext | None,
    ) -> list[ProposalSummary] | None:
        if read_context is None or self.registry_status is None:
            return None
        status = _provide(
            read_context,
            "registry_status",
            (),
            lambda: self.registry_status(read_context=read_context),
        )
        if str(getattr(status, "state", "")) != "current":
            return None
        path = self.p2p_dir / "registries" / "proposals.yml"
        try:
            payload = read_context.documents.yaml(path)
        except (FileNotFoundError, ValueError):
            return None
        if not isinstance(payload, Mapping):
            return None
        records = payload.get("proposals")
        if not isinstance(records, list):
            return None
        proposals = [
            _proposal_summary_from_registry(record)
            for record in records
            if isinstance(record, Mapping)
        ]
        return sorted(proposals, key=lambda item: item.proposal_id)

    def proposal_summaries(
        self,
        status: str | None = None,
        *,
        read_context: WorkspaceReadContext | None = None,
        prefer_registry: bool = True,
    ) -> list[ProposalSummary]:
        proposals = self._read_proposal_summaries(
            read_context=read_context,
            use_registry=prefer_registry,
        )
        if status is None:
            return proposals
        return [proposal for proposal in proposals if proposal.status == status]

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

    def _schema_summary(
        self,
        *,
        deep: bool,
        read_context: WorkspaceReadContext | None = None,
    ) -> dict[str, object] | None:
        provider = (
            self.workspace_schema_status
            if deep or self.workspace_schema_preflight is None
            else self.workspace_schema_preflight
        )
        if provider is None:
            return None
        status = _provide(
            read_context,
            "schema_deep_status" if deep else "schema_preflight",
            (),
            provider,
        )
        recovery = getattr(status, "recovery", {})
        return {
            "state": str(getattr(status, "state", "unknown")),
            "layout_status": str(getattr(status, "layout_status", "unknown")),
            "alignment_status": str(
                getattr(status, "alignment_status", "not_run" if not deep else "unknown")
            ),
            "current_version": getattr(status, "current_version", None),
            "target_version": getattr(status, "target_version", None),
            "recovery_required": bool(
                recovery.get("required", False) if isinstance(recovery, Mapping) else False
            ),
            "verification": "deep" if deep else "fast_checked",
        }

    def _freshness_summary(
        self,
        *,
        deep: bool,
        read_context: WorkspaceReadContext | None = None,
    ) -> dict[str, object] | None:
        if not deep:
            if self.fast_freshness_status is not None:
                status = (
                    self.fast_freshness_status(read_context=read_context)
                    if read_context is not None
                    else self.fast_freshness_status()
                )
                return status.to_dict()
            return {
                "status": "not_run",
                "attention_nodes": 0,
                "next_node": "",
                "next_command": "p2p project freshness",
                "verification": "not_run",
            }
        if self.derived_freshness_status is None:
            return None
        status = self.derived_freshness_status()
        nodes = tuple(getattr(status, "nodes", ()))
        rebuild_plan = tuple(getattr(status, "rebuild_plan", ()))
        return {
            "status": str(getattr(status, "status", "unknown")),
            "attention_nodes": sum(
                1
                for node in nodes
                if str(getattr(node, "status", "")) != "current"
            ),
            "next_node": str(getattr(rebuild_plan[0], "node_id", "")) if rebuild_plan else "",
            "next_command": str(getattr(rebuild_plan[0], "command", "")) if rebuild_plan else "",
            "verification": "deep",
        }


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_proposal_status(path: Path) -> str:
    return _proposal_status_from_text(_read_optional(path))


def _proposal_status_from_text(text: str) -> str:
    match = re.search(r"## Status\s+`([^`]+)`", text)
    return match.group(1) if match else "unknown"


def _clean_proposal_title(title: str, proposal_id: str) -> str:
    cleaned = re.sub(rf"^{re.escape(proposal_id)}\s*[-—]\s*", "", title).strip()
    return cleaned or title


def _proposal_summary_from_registry(record: Mapping[str, object]) -> ProposalSummary:
    proposal_id = str(record.get("id") or "")
    path = Path(str(record.get("path") or proposal_id))
    head_event_type = str(record.get("head_event_type") or "") or None
    head_event_id = str(record.get("head_event_id") or "") or None
    decision_semantic_sha256 = (
        str(record.get("decision_semantic_sha256") or "") or None
    )
    raw_event_count = record.get("event_count")
    event_count = (
        raw_event_count
        if isinstance(raw_event_count, int) and not isinstance(raw_event_count, bool)
        else 0
    )
    return ProposalSummary(
        proposal_id=proposal_id,
        slug=path.name,
        status=str(record.get("status") or "unknown"),
        title=str(record.get("title") or path.name),
        effective_state=str(record.get("effective_state") or "unknown"),
        head_event_type=head_event_type,
        head_event_id=head_event_id,
        event_count=event_count,
        authority_resolution=str(record.get("authority_resolution") or "invalid"),
        ever_active=bool(record.get("ever_active", False)),
        active=bool(record.get("active", False)),
        proposal_binding_status=str(
            record.get("proposal_binding_status") or "unavailable"
        ),
        decision_semantic_sha256=decision_semantic_sha256,
    )

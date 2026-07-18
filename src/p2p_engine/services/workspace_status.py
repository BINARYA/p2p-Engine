from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from p2p_engine.core.proposal_decision_events import ProposalDecisionLifecycleView
from p2p_engine.foundation.markdown import read_title
from p2p_engine.services.lifecycle_authority import proposal_display_status


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


class WorkspaceStatusService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        workspace_schema_status: Callable[[], Any] | None = None,
        derived_freshness_status: Callable[[], Any] | None = None,
        proposal_decision_lifecycles: (
            Callable[[], Mapping[str, ProposalDecisionLifecycleView]] | None
        ) = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.workspace_schema_status = workspace_schema_status
        self.derived_freshness_status = derived_freshness_status
        self.proposal_decision_lifecycles = proposal_decision_lifecycles

    def status(self) -> WorkspaceStatus:
        project_name = "Unknown"
        project_file = self.p2p_dir / "project.yml"
        if project_file.exists():
            data = yaml.safe_load(project_file.read_text(encoding="utf-8")) or {}
            project = data.get("project", {})
            if isinstance(project, dict):
                project_name = project.get("name", project_name)

        proposals = self._read_proposal_summaries()
        return WorkspaceStatus(
            root=self.root,
            project_name=project_name,
            proposals=proposals,
            workspace_schema=self._schema_summary(),
            derived_freshness=self._freshness_summary(),
        )

    def _read_proposal_summaries(self) -> list[ProposalSummary]:
        proposals: list[ProposalSummary] = []
        lifecycles = (
            self.proposal_decision_lifecycles()
            if self.proposal_decision_lifecycles is not None
            else {}
        )
        proposals_dir = self.p2p_dir / "proposals"
        if proposals_dir.exists():
            for path in sorted(proposals_dir.iterdir()):
                if not path.is_dir():
                    continue
                proposal_id = "-".join(path.name.split("-", 2)[:2])
                lifecycle = lifecycles.get(proposal_id)
                projected_status = _read_proposal_status(path / "proposal.md")
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
                            read_title(_read_optional(path / "proposal.md")) or path.name,
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

    def proposal_summaries(self, status: str | None = None) -> list[ProposalSummary]:
        proposals = self._read_proposal_summaries()
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

    def _schema_summary(self) -> dict[str, object] | None:
        if self.workspace_schema_status is None:
            return None
        status = self.workspace_schema_status()
        recovery = getattr(status, "recovery", {})
        return {
            "state": str(getattr(status, "state", "unknown")),
            "layout_status": str(getattr(status, "layout_status", "unknown")),
            "alignment_status": str(getattr(status, "alignment_status", "unknown")),
            "current_version": getattr(status, "current_version", None),
            "target_version": getattr(status, "target_version", None),
            "migration_required": bool(getattr(status, "migration_required", False)),
            "recovery_required": bool(
                recovery.get("required", False) if isinstance(recovery, Mapping) else False
            ),
        }

    def _freshness_summary(self) -> dict[str, object] | None:
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
                if str(getattr(node, "status", "")) not in {"current", "current_legacy_fallback"}
            ),
            "next_node": str(getattr(rebuild_plan[0], "node_id", "")) if rebuild_plan else "",
            "next_command": str(getattr(rebuild_plan[0], "command", "")) if rebuild_plan else "",
        }


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_proposal_status(path: Path) -> str:
    if not path.exists():
        return "unknown"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"## Status\s+`([^`]+)`", text)
    return match.group(1) if match else "unknown"


def _clean_proposal_title(title: str, proposal_id: str) -> str:
    cleaned = re.sub(rf"^{re.escape(proposal_id)}\s*[-—]\s*", "", title).strip()
    return cleaned or title

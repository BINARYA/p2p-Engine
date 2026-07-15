from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from p2p_engine.foundation.markdown import read_title


@dataclass(frozen=True)
class ProposalSummary:
    proposal_id: str
    slug: str
    status: str
    title: str = ""


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
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.workspace_schema_status = workspace_schema_status
        self.derived_freshness_status = derived_freshness_status

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
        proposals_dir = self.p2p_dir / "proposals"
        if proposals_dir.exists():
            for path in sorted(proposals_dir.iterdir()):
                if not path.is_dir():
                    continue
                proposal_id = "-".join(path.name.split("-", 2)[:2])
                status = _read_proposal_status(path / "proposal.md")
                proposals.append(
                    ProposalSummary(
                        proposal_id=proposal_id,
                        slug=path.name,
                        status=status,
                        title=_clean_proposal_title(
                            read_title(_read_optional(path / "proposal.md")) or path.name,
                            proposal_id,
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

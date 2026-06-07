from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class WorkspaceCheck:
    ok: bool
    missing: list[Path]


class WorkspaceStatusService:
    def __init__(self, *, root: Path, p2p_dir: Path) -> None:
        self.root = root
        self.p2p_dir = p2p_dir

    def status(self) -> WorkspaceStatus:
        project_name = "Unknown"
        project_file = self.p2p_dir / "project.yml"
        if project_file.exists():
            data = yaml.safe_load(project_file.read_text(encoding="utf-8")) or {}
            project = data.get("project", {})
            if isinstance(project, dict):
                project_name = project.get("name", project_name)

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
        return WorkspaceStatus(root=self.root, project_name=project_name, proposals=proposals)

    def proposal_summaries(self, status: str | None = None) -> list[ProposalSummary]:
        proposals = self.status().proposals
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

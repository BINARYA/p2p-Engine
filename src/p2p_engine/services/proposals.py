from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from p2p_engine.core.contribution import Contribution, ContributionType, parse_contribution_type
from p2p_engine.core.proposal import Proposal
from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    relative_to_root as _relative_to_root,
    slugify as _slugify,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.markdown import read_markdown_section, read_title, replace_section


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
class ProposalContributionList:
    proposal_id: str
    path: Path
    contributions: list[Contribution]


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_proposal_status(path: Path) -> str:
    if not path.exists():
        return "unknown"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"## Status\s+`([^`]+)`", text)
    return match.group(1) if match else "unknown"


def _proposal_id_from_dir_name(name: str) -> str | None:
    match = re.match(r"^(PROP-\d{3})-", name)
    return match.group(1) if match else None


def _clean_proposal_title(title: str, proposal_id: str) -> str:
    cleaned = re.sub(rf"^{re.escape(proposal_id)}\s*[-—]\s*", "", title).strip()
    return cleaned or title


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


class ProposalDocumentService:
    def __init__(self, *, root: Path, p2p_dir: Path) -> None:
        self.root = root
        self.p2p_dir = p2p_dir

    def create(self, title: str) -> Proposal:
        return self.create_with_details(title=title)

    def create_with_details(
        self,
        *,
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
        proposal_id = self.next_id()
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
        for filename, content in files.items():
            (proposal_dir / filename).write_text(content, encoding="utf-8")

        return Proposal(
            proposal_id=proposal_id,
            title=title,
            slug=slug,
            status="draft",
            path=proposal_dir.relative_to(self.root),
        )

    def show(self, proposal_id: str) -> ProposalDetail:
        proposal_dir = self.find_dir(proposal_id)
        proposal_text = _read_optional(proposal_dir / "proposal.md")
        decision_text = _read_optional(proposal_dir / "decision.md")
        return ProposalDetail(
            proposal_id=proposal_id,
            title=_clean_proposal_title(read_title(proposal_text) or proposal_id, proposal_id),
            status=_read_proposal_status(proposal_dir / "proposal.md"),
            path=proposal_dir.relative_to(self.root),
            problem=read_markdown_section(proposal_text, "Problem") or "Not provided.",
            proposal=read_markdown_section(proposal_text, "Proposal") or "Not provided.",
            decision_status=(read_markdown_section(decision_text, "Status") or "pending").strip("`"),
            decision_reason=read_markdown_section(decision_text, "Reason") or "Not provided.",
        )

    def update(
        self,
        proposal_id: str,
        problem: str | None = None,
        context: str | None = None,
        goals: list[str] | None = None,
        non_goals: list[str] | None = None,
        proposal: str | None = None,
        acceptance_criteria: list[str] | None = None,
    ) -> Path:
        proposal_dir = self.find_dir(proposal_id)
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
                text = replace_section(text, section, replacement)
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
        proposal_dir = self.find_dir(proposal_id)
        path = proposal_dir / "contributions.yml"
        data = _read_yaml_mapping(path, default={"contributions": []})
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

    def list_contributions(self, proposal_id: str) -> ProposalContributionList:
        proposal_dir = self.find_dir(proposal_id)
        path = proposal_dir / "contributions.yml"
        data = _read_yaml_mapping(path, default={"contributions": []})
        raw_contributions = data.get("contributions") or []
        if not isinstance(raw_contributions, list):
            raise ValueError("Invalid contributions.yml: expected top-level contributions list.")
        contributions: list[Contribution] = []
        for item in raw_contributions:
            if not isinstance(item, dict):
                continue
            contribution_type = parse_contribution_type(item.get("type"))
            contributions.append(
                Contribution(
                    contribution_id=str(item.get("id") or ""),
                    contribution_type=contribution_type,
                    text=str(item.get("text") or ""),
                    author=str(item.get("author") or ""),
                    relevance_hint=str(item.get("relevance_hint") or ""),
                )
            )
        return ProposalContributionList(proposal_id=proposal_id, path=path.relative_to(self.root), contributions=contributions)

    def next_id(self) -> str:
        max_id = 0
        proposals_dir = self.p2p_dir / "proposals"
        for path in proposals_dir.iterdir() if proposals_dir.exists() else []:
            match = re.match(r"PROP-(\d{3})-", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"PROP-{max_id + 1:03d}"

    def find_dir(self, proposal_id: str) -> Path:
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

    def duplicate_ids(self) -> dict[str, list[Path]]:
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

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from p2p_engine.core.contribution import Contribution, ContributionType, parse_contribution_type
from p2p_engine.core.proposal import Proposal
from p2p_engine.core.proposal_decision_events import ProposalDecisionLifecycleView
from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    relative_to_root as _relative_to_root,
    slugify as _slugify,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.markdown import read_markdown_section, read_title, replace_section
from p2p_engine.services.lifecycle_authority import proposal_display_status
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    proposal_semantic_sha256,
)


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
    effective_state: str = "unknown"
    head_event_type: str | None = None
    head_event_id: str | None = None
    event_count: int = 0
    authority_resolution: str = "invalid"
    ever_active: bool = False
    active: bool = False
    proposal_binding_status: str = "unavailable"
    decision_semantic_sha256: str | None = None
    proposal_semantic_sha256: str | None = None
    lifecycle_diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProposalContributionList:
    proposal_id: str
    path: Path
    contributions: list[Contribution]


@dataclass(frozen=True)
class ProposalCreatePlan:
    proposal: Proposal
    files: dict[str, str]


@dataclass(frozen=True)
class ProposalUpdatePlan:
    proposal_id: str
    path: Path
    before: bytes
    after: bytes
    updated_sections: list[str]


@dataclass(frozen=True)
class ContributionAddPlan:
    proposal_id: str
    path: Path
    before: bytes | None
    after: bytes
    contribution: Contribution


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
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        lifecycle_status: (
            Callable[[str], ProposalDecisionLifecycleView] | None
        ) = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.lifecycle_status = lifecycle_status

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
        plan = self.create_plan_with_details(
            title=title,
            problem=problem,
            context=context,
            goals=goals,
            non_goals=non_goals,
            proposal=proposal,
            acceptance_criteria=acceptance_criteria,
        )
        proposal_dir = self.root / plan.proposal.path
        proposal_dir.mkdir(parents=True, exist_ok=False)
        for filename, content in plan.files.items():
            (proposal_dir / filename).write_text(content, encoding="utf-8")

        return plan.proposal

    def create_plan_with_details(
        self,
        *,
        title: str,
        problem: str | None = None,
        context: str | None = None,
        goals: list[str] | None = None,
        non_goals: list[str] | None = None,
        proposal: str | None = None,
        acceptance_criteria: list[str] | None = None,
    ) -> ProposalCreatePlan:
        proposals_dir = self.p2p_dir / "proposals"
        proposal_id = self.next_id()
        slug = _slugify(title)
        proposal_dir = proposals_dir / f"{proposal_id}-{slug}"

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
        if self._workspace_schema_version() >= 3:
            files["decision-events.yml"] = ProposalDecisionLedgerCodec().dumps(
                ProposalDecisionLedgerCodec().empty(proposal_id)
            ).decode("ascii")

        proposal_record = Proposal(
            proposal_id=proposal_id,
            title=title,
            slug=slug,
            status="draft",
            path=proposal_dir.relative_to(self.root),
        )
        return ProposalCreatePlan(
            proposal=proposal_record,
            files=files,
        )

    def _workspace_schema_version(self) -> int:
        path = self.p2p_dir / "project" / "workspace-schema.yml"
        if not path.exists():
            return 0
        try:
            payload = _read_yaml_mapping(path, default={})
        except (OSError, ValueError, yaml.YAMLError):
            return 0
        raw = payload.get("workspace_schema")
        version = raw.get("current_version") if isinstance(raw, dict) else 0
        return version if isinstance(version, int) and not isinstance(version, bool) else 0

    def show(self, proposal_id: str) -> ProposalDetail:
        proposal_dir = self.find_dir(proposal_id)
        proposal_text = _read_optional(proposal_dir / "proposal.md")
        decision_text = _read_optional(proposal_dir / "decision.md")
        lifecycle = (
            self.lifecycle_status(proposal_id)
            if self.lifecycle_status is not None
            else None
        )
        effective_state = (
            lifecycle.effective_state.value
            if lifecycle is not None
            else _read_proposal_status(proposal_dir / "proposal.md")
        )
        projected_status = _read_proposal_status(proposal_dir / "proposal.md")
        display_status = (
            proposal_display_status(
                lifecycle,
                undecided_fallback=projected_status,
            )
            if lifecycle is not None
            else projected_status
        )
        return ProposalDetail(
            proposal_id=proposal_id,
            title=_clean_proposal_title(read_title(proposal_text) or proposal_id, proposal_id),
            status=display_status,
            path=proposal_dir.relative_to(self.root),
            problem=read_markdown_section(proposal_text, "Problem") or "Not provided.",
            proposal=read_markdown_section(proposal_text, "Proposal") or "Not provided.",
            decision_status=(read_markdown_section(decision_text, "Status") or "pending").strip("`"),
            decision_reason=read_markdown_section(decision_text, "Reason") or "Not provided.",
            effective_state=effective_state,
            head_event_type=(
                lifecycle.head_event_type.value
                if lifecycle is not None and lifecycle.head_event_type is not None
                else None
            ),
            head_event_id=lifecycle.head_event_id if lifecycle is not None else None,
            event_count=lifecycle.event_count if lifecycle is not None else 0,
            authority_resolution=(
                lifecycle.authority_resolution.value
                if lifecycle is not None
                else "invalid"
            ),
            ever_active=lifecycle.ever_active if lifecycle is not None else False,
            active=lifecycle.active if lifecycle is not None else False,
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
            proposal_semantic_sha256=(
                lifecycle.proposal_semantic_sha256
                if lifecycle is not None
                else None
            ),
            lifecycle_diagnostics=(
                lifecycle.diagnostics if lifecycle is not None else ()
            ),
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
        plan = self.update_plan(
            proposal_id,
            problem=problem,
            context=context,
            goals=goals,
            non_goals=non_goals,
            proposal=proposal,
            acceptance_criteria=acceptance_criteria,
            require_changes=False,
        )
        proposal_path = self.root / plan.path
        proposal_path.write_bytes(plan.after)
        return plan.path

    def update_plan(
        self,
        proposal_id: str,
        problem: str | None = None,
        context: str | None = None,
        goals: list[str] | None = None,
        non_goals: list[str] | None = None,
        proposal: str | None = None,
        acceptance_criteria: list[str] | None = None,
        *,
        require_changes: bool = False,
    ) -> ProposalUpdatePlan:
        proposal_dir = self.find_dir(proposal_id)
        proposal_path = proposal_dir / "proposal.md"
        before = proposal_path.read_bytes()
        text = before.decode("utf-8")
        replacements = {
            "problem": ("Problem", _paragraph(problem)),
            "context": ("Context", _paragraph(context)),
            "goals": ("Goals", _bullets(goals)),
            "non_goals": ("Non-Goals", _bullets(non_goals)),
            "proposal": ("Proposal", _paragraph(proposal)),
            "acceptance_criteria": (
                "Acceptance Criteria",
                _bullets(acceptance_criteria),
            ),
        }
        updated_sections: list[str] = []
        for key, (section, replacement) in replacements.items():
            if replacement is not None:
                text = replace_section(text, section, replacement)
                updated_sections.append(key)
        if require_changes and not updated_sections:
            raise ValueError(
                "P2P_PROPOSAL_EMPTY_UPDATE: provide at least one proposal section to update"
            )
        if self.lifecycle_status is not None:
            lifecycle = self.lifecycle_status(proposal_id)
            if lifecycle.effective_state.value not in {"undecided", "deferred"}:
                before_sha = proposal_semantic_sha256(
                    proposal_id,
                    before.decode("utf-8"),
                )
                after_sha = proposal_semantic_sha256(proposal_id, text)
                if before_sha != after_sha:
                    raise ValueError(
                        "P2P377_DECISION_PROPOSAL_BINDING_DIVERGED: a decided "
                        "proposal cannot be changed in place; create a linked "
                        "proposal for revised semantics"
                    )
        return ProposalUpdatePlan(
            proposal_id=proposal_id,
            path=proposal_path.relative_to(self.root),
            before=before,
            after=text.encode("utf-8"),
            updated_sections=updated_sections,
        )

    def add_contribution(
        self,
        proposal_id: str,
        contribution_type: ContributionType,
        text: str,
        relevance_hint: str,
        author: str,
    ) -> Contribution:
        plan = self.add_contribution_plan(
            proposal_id,
            contribution_type,
            text=text,
            relevance_hint=relevance_hint,
            author=author,
        )
        (self.root / plan.path).write_bytes(plan.after)
        return plan.contribution

    def add_contribution_plan(
        self,
        proposal_id: str,
        contribution_type: ContributionType,
        text: str,
        relevance_hint: str,
        author: str,
    ) -> ContributionAddPlan:
        proposal_dir = self.find_dir(proposal_id)
        path = proposal_dir / "contributions.yml"
        before = path.read_bytes() if path.exists() else None
        data = _read_yaml_mapping(path, default={"contributions": []})
        contributions = data.setdefault("contributions", [])
        if not isinstance(contributions, list):
            raise ValueError("Invalid contributions.yml: expected top-level contributions list.")
        contribution_id = f"C{len(contributions) + 1:03d}"
        payload = {
            "id": contribution_id,
            "type": contribution_type.value,
            "author": author,
            "relevance_hint": relevance_hint,
            "text": text,
        }
        contributions.append(payload)
        contribution = Contribution(
            contribution_id=contribution_id,
            contribution_type=contribution_type,
            text=text,
            author=author,
            relevance_hint=relevance_hint,
        )
        return ContributionAddPlan(
            proposal_id=proposal_id,
            path=path.relative_to(self.root),
            before=before,
            after=_yaml_dump(data).encode("utf-8"),
            contribution=contribution,
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

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    slugify as _foundation_slugify,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.markdown import (
    read_frontmatter,
    read_markdown_section,
    read_title,
    replace_frontmatter,
)


CHANGE_STATUS_TRANSITIONS = {
    "proposed": ["planned", "cancelled", "superseded"],
    "planned": ["implementation_ready", "blocked", "cancelled", "superseded"],
    "implementation_ready": ["in_progress", "blocked", "cancelled", "superseded"],
    "in_progress": ["in_review", "blocked", "cancelled", "superseded"],
    "blocked": ["planned", "implementation_ready", "in_progress", "cancelled", "superseded"],
    "in_review": ["completed", "in_progress", "blocked"],
    "completed": [],
    "cancelled": [],
    "superseded": [],
}


@dataclass(frozen=True)
class ChangeSetStatus:
    change_id: str
    title: str
    status: str
    path: Path


@dataclass(frozen=True)
class ChangeSetPolicy:
    change_id: str
    operation_level: str
    auto_commit: bool
    auto_branch: bool
    auto_tag: bool
    reasons: list[str]


@dataclass(frozen=True)
class ChangeSetDetail:
    change_id: str
    title: str
    status: str
    path: Path
    summary: str
    execution_domains: list[str]
    implementation_targets: list[str]
    spec_targets: list[str]
    export_targets: list[str]
    plan_ref: str
    tasks_ref: str


@dataclass(frozen=True)
class ChangeSetTaskView:
    change_id: str
    tasks: list[dict[str, object]]
    actions: list[dict[str, object]]


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _slugify(value: str) -> str:
    return _foundation_slugify(value, fallback="item")


def _clean_proposal_title(title: str, proposal_id: str) -> str:
    cleaned = re.sub(rf"^{re.escape(proposal_id)}\s*[-—]\s*", "", title).strip()
    return cleaned or title


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _read_proposal_status(path: Path) -> str:
    text = _read_optional(path)
    status = read_markdown_section(text, "Status")
    if status:
        return status.strip().strip("`")
    return "draft"


def _metadata_only_git_policy() -> dict[str, object]:
    return {
        "git_policy": {
            "mode": "managed",
            "operation_level": "metadata_only",
            "expose_git_details": False,
            "commits": {"auto_commit": False},
            "branches": {"auto_create": False},
            "tags": {"auto_create": False},
        }
    }


def _change_markdown(
    change_id: str,
    title: str,
    source_proposal: str,
    created_on: str,
    summary: str,
    rationale: str,
) -> str:
    frontmatter = _yaml_dump(
        {
            "change_id": change_id,
            "title": title,
            "status": "proposed",
            "created_at": created_on,
            "created_by": "local",
            "execution_domains": ["software"],
            "source": {"accepted_proposals": [source_proposal], "accepted_decisions": []},
            "implementation_targets": ["local_cli"],
            "spec_targets": ["p2p_spec"],
            "export_targets": ["openspec", "speckit"],
            "plan_ref": "execution-plan.md",
            "tasks_ref": "tasks.yml",
        }
    )
    return (
        f"---\n{frontmatter}---\n\n"
        f"# {change_id} - {title}\n\n"
        "## Summary\n\n"
        f"{summary}\n\n"
        "## Rationale\n\n"
        f"{rationale}\n\n"
        "## Scope\n\n"
        "### Included\n\n"
        "- Derived from accepted proposal scope.\n\n"
        "### Excluded\n\n"
        "- Automatic Git commits, branches, tags, or merges.\n\n"
        "## Deliverables\n\n"
        "- Change Set metadata.\n\n"
        "## Acceptance Criteria\n\n"
        "- Change Set metadata is present and reviewable.\n\n"
        "## Dependencies\n\n"
        "- None recorded.\n\n"
        "## Risks\n\n"
        "- Metadata may need manual refinement before implementation.\n\n"
        "## Related Choices\n\n"
        "- None recorded.\n"
    )


class ChangeSetLifecycleService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_proposal_dir: Callable[[str], Path],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir

    def create(self, source: str, title: str | None = None) -> ChangeSetStatus:
        proposal_dir = self.find_proposal_dir(source)
        proposal_path = proposal_dir / "proposal.md"
        proposal_text = _read_optional(proposal_path)
        proposal_status = _read_proposal_status(proposal_path)
        if proposal_status != "accepted":
            raise ValueError(
                f"Cannot create Change Set. {source} is not accepted yet. "
                f"Current status: {proposal_status}"
            )

        change_id = self.next_id()
        proposal_title = _clean_proposal_title(read_title(proposal_text) or source, source)
        change_title = title or proposal_title
        slug = _slugify(change_title)
        change_dir = self.p2p_dir / "changes" / f"{change_id}-{slug}"
        change_dir.mkdir(parents=True)

        files = {
            "change.md": _change_markdown(
                change_id=change_id,
                title=change_title,
                source_proposal=source,
                created_on=date.today().isoformat(),
                summary=read_markdown_section(proposal_text, "Proposal") or "Not provided.",
                rationale=read_markdown_section(proposal_text, "Context") or "Not provided.",
            ),
            "included-proposals.yml": _yaml_dump({"included_proposals": [source]}),
            "referenced-proposals.yml": _yaml_dump({"referenced_proposals": []}),
            "excluded-alternatives.yml": _yaml_dump({"excluded_alternatives": []}),
            "included-decisions.yml": _yaml_dump(
                {
                    "included_decisions": [
                        {
                            "proposal": source,
                            "decision_file": str((proposal_dir / "decision.md").relative_to(self.root)),
                        }
                    ]
                }
            ),
            "impact-map.yml": _read_optional(proposal_dir / "impact-map.yml")
            or _yaml_dump({"impact": {"proposal": source, "features": [], "commands": [], "files": []}}),
            "git-policy.yml": _yaml_dump(_metadata_only_git_policy()),
            "execution-plan.md": _read_optional(proposal_dir / "execution-plan.md")
            or f"# Execution Plan - {change_id}\n\nPending.\n",
            "tasks.yml": _read_optional(proposal_dir / "tasks.yml") or "tasks: []\n",
            "actions.yml": _yaml_dump({"actions": []}),
        }
        for filename, content in files.items():
            (change_dir / filename).write_text(content, encoding="utf-8")

        return ChangeSetStatus(
            change_id=change_id,
            title=change_title,
            status="proposed",
            path=change_dir.relative_to(self.root),
        )

    def statuses(self) -> list[ChangeSetStatus]:
        changes_dir = self.p2p_dir / "changes"
        statuses: list[ChangeSetStatus] = []
        for path in sorted(changes_dir.iterdir()) if changes_dir.exists() else []:
            if not path.is_dir():
                continue
            change_text = _read_optional(path / "change.md")
            frontmatter = read_frontmatter(change_text)
            change_id = str(frontmatter.get("change_id") or "-".join(path.name.split("-", 2)[:2]))
            title = str(frontmatter.get("title") or read_title(change_text) or path.name)
            status = str(frontmatter.get("status") or "unknown")
            statuses.append(
                ChangeSetStatus(
                    change_id=change_id,
                    title=title,
                    status=status,
                    path=path.relative_to(self.root),
                )
            )
        return statuses

    def policy(self, change_id: str) -> ChangeSetPolicy:
        change_dir = self.find_dir(change_id)
        data = _read_yaml_mapping(change_dir / "git-policy.yml", default=_metadata_only_git_policy())
        policy = data.get("git_policy", {})
        if not isinstance(policy, dict):
            raise ValueError("Invalid git-policy.yml: expected `git_policy` mapping.")
        commits = policy.get("commits", {})
        branches = policy.get("branches", {})
        tags = policy.get("tags", {})
        return ChangeSetPolicy(
            change_id=change_id,
            operation_level=str(policy.get("operation_level", "metadata_only")),
            auto_commit=bool(commits.get("auto_commit", False)) if isinstance(commits, dict) else False,
            auto_branch=bool(branches.get("auto_create", False)) if isinstance(branches, dict) else False,
            auto_tag=bool(tags.get("auto_create", False)) if isinstance(tags, dict) else False,
            reasons=[
                "MVP uses metadata_only managed Git policy.",
                "No Git commits, branches, tags, or merges are created automatically.",
            ],
        )

    def show(self, change_id: str) -> ChangeSetDetail:
        change_dir = self.find_dir(change_id)
        text = _read_optional(change_dir / "change.md")
        frontmatter = read_frontmatter(text)
        return ChangeSetDetail(
            change_id=str(frontmatter.get("change_id") or change_id),
            title=str(frontmatter.get("title") or read_title(text) or change_id),
            status=str(frontmatter.get("status") or "unknown"),
            path=change_dir.relative_to(self.root),
            summary=read_markdown_section(text, "Summary") or "Not provided.",
            execution_domains=_string_list(frontmatter.get("execution_domains")),
            implementation_targets=_string_list(frontmatter.get("implementation_targets")),
            spec_targets=_string_list(frontmatter.get("spec_targets")),
            export_targets=_string_list(frontmatter.get("export_targets")),
            plan_ref=str(frontmatter.get("plan_ref") or "execution-plan.md"),
            tasks_ref=str(frontmatter.get("tasks_ref") or "tasks.yml"),
        )

    def update_status(self, change_id: str, new_status: str) -> ChangeSetStatus:
        change_dir = self.find_dir(change_id)
        change_path = change_dir / "change.md"
        text = _read_optional(change_path)
        frontmatter = read_frontmatter(text)
        current_status = str(frontmatter.get("status") or "unknown")
        allowed = CHANGE_STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid Change Set transition: {current_status} -> {new_status}. "
                f"Allowed next: {', '.join(allowed) if allowed else 'none'}"
            )
        frontmatter["status"] = new_status
        updated = replace_frontmatter(text, frontmatter)
        change_path.write_text(updated, encoding="utf-8")
        return ChangeSetStatus(
            change_id=str(frontmatter.get("change_id") or change_id),
            title=str(frontmatter.get("title") or change_id),
            status=new_status,
            path=change_dir.relative_to(self.root),
        )

    def tasks(self, change_id: str) -> ChangeSetTaskView:
        change_dir = self.find_dir(change_id)
        tasks_data = _read_yaml_mapping(change_dir / "tasks.yml", default={"tasks": []})
        actions_data = _read_yaml_mapping(change_dir / "actions.yml", default={"actions": []})
        tasks = tasks_data.get("tasks", [])
        actions = actions_data.get("actions", [])
        if not isinstance(tasks, list):
            raise ValueError("Invalid tasks.yml: expected `tasks` list.")
        if not isinstance(actions, list):
            raise ValueError("Invalid actions.yml: expected `actions` list.")
        return ChangeSetTaskView(
            change_id=change_id,
            tasks=[task for task in tasks if isinstance(task, dict)],
            actions=[action for action in actions if isinstance(action, dict)],
        )

    def next_id(self) -> str:
        max_id = 0
        changes_dir = self.p2p_dir / "changes"
        for path in changes_dir.iterdir() if changes_dir.exists() else []:
            match = re.match(r"CHANGE-(\d{3})-", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"CHANGE-{max_id + 1:03d}"

    def find_dir(self, change_id: str) -> Path:
        changes_dir = self.p2p_dir / "changes"
        if not changes_dir.exists():
            raise ValueError("No .p2p/changes directory found.")
        matches = [path for path in changes_dir.iterdir() if path.name.startswith(f"{change_id}-")]
        if not matches:
            raise ValueError(f"Change Set not found: {change_id}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous Change Set ID: {change_id}")
        return matches[0]

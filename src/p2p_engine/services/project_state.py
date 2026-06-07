from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from p2p_engine.foundation.files import yaml_dump as _yaml_dump


class RegistryStatusLike(Protocol):
    registries_dir: Path
    stale: bool
    proposals_count: int
    changes_count: int


@dataclass(frozen=True)
class ProjectStateStatus:
    accepted_proposals: int
    features: list[str]
    project_dir: Path
    operational_brief_available: bool
    next_actions_count: int
    first_next_action: object | None


@dataclass(frozen=True)
class ProjectBriefPrompt:
    context_path: Path
    prompt_path: Path


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


class ProjectStateService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        accepted_proposals: Callable[[], list[dict[str, object]]],
        project_name: Callable[[], str],
        next_actions: Callable[[], list[object]],
        registry_status: Callable[[], RegistryStatusLike],
        project_brief_context: Callable[[RegistryStatusLike], str],
        validate_yaml_key: Callable[[str, str], None],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.accepted_proposals = accepted_proposals
        self.project_name = project_name
        self.next_actions = next_actions
        self.registry_status = registry_status
        self.project_brief_context = project_brief_context
        self.validate_yaml_key = validate_yaml_key

    def refresh(self) -> list[Path]:
        project_dir = self.p2p_dir / "project"
        features_dir = project_dir / "features"
        exports_dir = project_dir / "exports"
        for directory in (
            project_dir,
            features_dir,
            exports_dir / "markdown",
            exports_dir / "openspec",
            exports_dir / "speckit",
        ):
            directory.mkdir(parents=True, exist_ok=True)

        accepted = self.accepted_proposals()
        project_name = self.project_name()
        written: list[Path] = []

        files = {
            project_dir / "overview.md": project_overview_markdown(project_name, accepted),
            project_dir / "problem.md": project_problem_markdown(accepted),
            project_dir / "scope.md": project_scope_markdown(accepted),
            project_dir / "project-swot.md": project_swot_markdown(),
            project_dir / "decisions-map.yml": _yaml_dump(
                {
                    "decisions": [
                        {
                            "proposal": item["proposal_id"],
                            "title": item["title"],
                            "status": item["status"],
                            "feature": item["feature_id"],
                            "source": item["source"],
                        }
                        for item in accepted
                    ]
                }
            ),
        }
        for path, content in files.items():
            path.write_text(content, encoding="utf-8")
            written.append(path.relative_to(self.root))
        conflicts_path = project_dir / "conflicts.yml"
        if not conflicts_path.exists():
            conflicts_path.write_text(_yaml_dump({"conflicts": []}), encoding="utf-8")
            written.append(conflicts_path.relative_to(self.root))

        for item in accepted:
            feature_dir = features_dir / str(item["feature_id"])
            feature_dir.mkdir(parents=True, exist_ok=True)
            feature_files = {
                feature_dir / "feature.md": feature_markdown(item),
                feature_dir / "tasks.yml": _read_optional(Path(item["path"]) / "tasks.yml") or "tasks: []\n",
                feature_dir / "actions.yml": _yaml_dump({"actions": []}),
            }
            for path, content in feature_files.items():
                path.write_text(content, encoding="utf-8")
                written.append(path.relative_to(self.root))
        return written

    def status(self) -> ProjectStateStatus:
        project_dir = self.p2p_dir / "project"
        features_dir = project_dir / "features"
        features = sorted(path.name for path in features_dir.iterdir() if path.is_dir()) if features_dir.exists() else []
        next_actions = self.next_actions()
        return ProjectStateStatus(
            accepted_proposals=len(self.accepted_proposals()),
            features=features,
            project_dir=project_dir.relative_to(self.root),
            operational_brief_available=(project_dir / "operational-brief.md").exists(),
            next_actions_count=len(next_actions),
            first_next_action=next_actions[0] if next_actions else None,
        )

    def show(self, section: str) -> str:
        project_dir = self.p2p_dir / "project"
        section_map = {
            "overview": project_dir / "overview.md",
            "problem": project_dir / "problem.md",
            "scope": project_dir / "scope.md",
            "swot": project_dir / "project-swot.md",
        }
        path = section_map.get(section, project_dir / "features" / section / "feature.md")
        if not path.exists():
            raise ValueError(f"Project section not found: {section}")
        return path.read_text(encoding="utf-8")

    def create_brief_prompt(self) -> ProjectBriefPrompt:
        project_dir = self.p2p_dir / "project"
        project_dir.mkdir(parents=True, exist_ok=True)
        context = self.project_brief_context(self.registry_status())
        context_path = project_dir / "brief-context.md"
        prompt_path = project_dir / "brief.prompt.md"
        context_path.write_text(context, encoding="utf-8")
        prompt_path.write_text(project_brief_prompt_markdown(context), encoding="utf-8")
        return ProjectBriefPrompt(
            context_path=context_path.relative_to(self.root),
            prompt_path=prompt_path.relative_to(self.root),
        )

    def import_brief(self, source: Path) -> list[Path]:
        project_dir = self.p2p_dir / "project"
        project_dir.mkdir(parents=True, exist_ok=True)
        source = source.resolve()
        imported: list[Path] = []
        if source.is_dir():
            mappings = {
                "operational-brief.md": None,
                "next-actions.yml": "next_actions",
            }
            for filename, key in mappings.items():
                source_path = source / filename
                if source_path.exists():
                    if key is not None:
                        self.validate_yaml_key(source_path.read_text(encoding="utf-8"), key)
                    target = project_dir / filename
                    shutil.copyfile(source_path, target)
                    imported.append(target.relative_to(self.root))
        elif source.is_file():
            target = project_dir / "operational-brief.md"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            imported.append(target.relative_to(self.root))
        else:
            raise ValueError(f"Project brief source not found: {source}")
        if not imported:
            raise ValueError(f"No project brief artifacts found in: {source}")
        return imported

    def show_brief(self) -> str:
        path = self.p2p_dir / "project" / "operational-brief.md"
        if not path.exists():
            raise ValueError("Project brief not found. Run `p2p project brief import` first.")
        return path.read_text(encoding="utf-8")


def project_overview_markdown(project_name: str, accepted: list[dict[str, object]]) -> str:
    lines = [
        f"# Project State - {project_name}",
        "",
        "This file is generated by `p2p project refresh` from accepted proposals.",
        "",
        "## Accepted Proposals",
        "",
    ]
    if accepted:
        for item in accepted:
            lines.append(f"- {item['proposal_id']} - {item['title']}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Features", ""])
    if accepted:
        for item in accepted:
            lines.append(f"- `{item['feature_id']}` from {item['proposal_id']}")
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def project_problem_markdown(accepted: list[dict[str, object]]) -> str:
    lines = ["# Project Problem", "", "Generated from accepted proposal problem statements.", ""]
    for item in accepted:
        lines.extend([f"## {item['proposal_id']} - {item['title']}", "", str(item["problem"]), ""])
    if not accepted:
        lines.append("No accepted proposals yet.\n")
    return "\n".join(lines)


def project_scope_markdown(accepted: list[dict[str, object]]) -> str:
    lines = ["# Project Scope", "", "Generated from accepted proposal goals and non-goals.", ""]
    for item in accepted:
        lines.extend(
            [
                f"## {item['proposal_id']} - {item['title']}",
                "",
                "### Goals",
                "",
                str(item["goals"]),
                "",
                "### Non-Goals",
                "",
                str(item["non_goals"]),
                "",
            ]
        )
    if not accepted:
        lines.append("No accepted proposals yet.\n")
    return "\n".join(lines)


def project_swot_markdown() -> str:
    return (
        "# Project SWOT\n\n"
        "Generated placeholder. Use `p2p swot prompt <PROP-ID>` for proposal-level SWOT "
        "and consolidate project-level findings here during project refresh evolution.\n"
    )


def feature_markdown(item: dict[str, object]) -> str:
    return (
        f"# {item['title']}\n\n"
        "## Provenance\n\n"
        f"- Proposal: {item['proposal_id']}\n"
        f"- Source: {item['source']}\n\n"
        "## Problem\n\n"
        f"{item['problem']}\n\n"
        "## Proposal\n\n"
        f"{item['proposal']}\n\n"
        "## Decision\n\n"
        f"{str(item['decision']).strip() or 'Not provided.'}\n"
    )


def project_brief_prompt_markdown(context: str) -> str:
    return (
        "# P2P Operational Brief Prompt\n\n"
        "You are helping synthesize the current P2P project state into an operational brief.\n\n"
        "## Governance Boundary\n\n"
        "Do not accept, reject, defer, merge, supersede, or apply recommendations. "
        "Do not decide on behalf of the owner. Recommend next actions only and point to "
        "the P2P commands that would let the owner act explicitly.\n\n"
        "## Project Context\n\n"
        f"{context}\n\n"
        "## Required Output\n\n"
        "Return artifacts with these shapes:\n\n"
        "### operational-brief.md\n\n"
        "```markdown\n"
        "# Operational Brief\n\n"
        "## Where We Are\n"
        "Short synthesis of the current project state.\n\n"
        "## Accepted Direction\n"
        "Accepted decisions and constraints that shape the project.\n\n"
        "## Active Work\n"
        "Change Sets, draft proposals, pending intake, and work still moving.\n\n"
        "## Blockers / Inconsistencies\n"
        "Open choices, conflicts, stale registries, status mismatches, or missing artifacts.\n\n"
        "## Recommended Next Actions\n"
        "1. Action title\n"
        "   Reason: Why this matters now.\n"
        "   Command: p2p ...\n\n"
        "## Not Yet\n"
        "Useful but lower-priority directions.\n"
        "```\n\n"
        "### next-actions.yml\n\n"
        "```yaml\n"
        "next_actions:\n"
        "  - id: NEXT-001\n"
        "    priority: high | medium | low\n"
        "    kind: continue_change | resolve_choice | refresh_registry | inspect_intake | record_conflict | create_change | other\n"
        "    target: CHANGE-000\n"
        "    reason: Short reason.\n"
        "    command: p2p ...\n"
        "```\n"
    )

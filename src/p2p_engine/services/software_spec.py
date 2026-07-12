from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from p2p_engine.foundation.files import (
    read_yaml_mapping_or_default as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.markdown import read_frontmatter, read_markdown_section, read_title
from p2p_engine.foundation.validators import validate_yaml_key


@dataclass(frozen=True)
class SoftwareSpecStatus:
    change_id: str
    title: str
    status: str
    path: Path
    lifecycle: Any | None = None


@dataclass(frozen=True)
class SoftwareSpecPrompt:
    change_id: str
    prompt_path: Path


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


class SoftwareSpecService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_change_dir: Callable[[str], Path],
        show_proposal: Callable[[str], Any],
        show_change_set: Callable[[str], Any],
        find_proposal_dir: Callable[[str], Path],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_change_dir = find_change_dir
        self.show_proposal = show_proposal
        self.show_change_set = show_change_set
        self.find_proposal_dir = find_proposal_dir

    def required_files(self) -> tuple[str, ...]:
        return (
            "index.md",
            "requirements.md",
            "design.md",
            "commands.yml",
            "data-model.yml",
            "acceptance.md",
            "provenance.yml",
        )

    def refresh(self, change_id: str) -> SoftwareSpecStatus:
        change_dir = self.find_change_dir(change_id)
        change_text = _read_optional(change_dir / "change.md")
        frontmatter = read_frontmatter(change_text)
        title = str(frontmatter.get("title") or read_title(change_text) or change_id)
        source = frontmatter.get("source", {})
        if not isinstance(source, dict):
            source = {}
        included_proposals = _string_list(source.get("accepted_proposals"))
        spec_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        spec_dir.mkdir(parents=True, exist_ok=True)

        proposal_details = [self.show_proposal(proposal_id) for proposal_id in included_proposals]
        tasks_data = _read_yaml_mapping(change_dir / "tasks.yml", default={"tasks": []})
        tasks = tasks_data.get("tasks", [])
        task_list = tasks if isinstance(tasks, list) else []

        files = {
            "index.md": self._index_markdown(
                change_id=change_id,
                title=title,
                change_path=change_dir.relative_to(self.root),
                summary=read_markdown_section(change_text, "Summary") or "Not specified yet.",
                frontmatter=frontmatter,
                included_proposals=included_proposals,
            ),
            "requirements.md": self._requirements_markdown(proposal_details, change_text),
            "design.md": self._design_markdown(frontmatter, change_text),
            "commands.yml": _yaml_dump({"commands": self._commands(task_list)}),
            "data-model.yml": _yaml_dump({"entities": self._entities(frontmatter, proposal_details)}),
            "acceptance.md": self._acceptance_markdown(change_text, task_list),
            "provenance.yml": _yaml_dump(
                {
                    "source": {
                        "change": change_id,
                        "included_proposals": included_proposals,
                        "accepted_decisions": source.get("accepted_decisions", []),
                    },
                    "generated_from": [
                        str((change_dir / "change.md").relative_to(self.root)),
                        str((change_dir / "tasks.yml").relative_to(self.root)),
                        *[
                            str((self.find_proposal_dir(proposal_id) / "proposal.md").relative_to(self.root))
                            for proposal_id in included_proposals
                        ],
                    ],
                }
            ),
        }
        for filename, content in files.items():
            (spec_dir / filename).write_text(content, encoding="utf-8")
        return SoftwareSpecStatus(
            change_id=change_id,
            title=title,
            status="generated",
            path=spec_dir.relative_to(self.root),
        )

    def statuses(self) -> list[SoftwareSpecStatus]:
        specs_dir = self.p2p_dir / "outputs" / "software-spec"
        statuses: list[SoftwareSpecStatus] = []
        for path in sorted(specs_dir.iterdir()) if specs_dir.exists() else []:
            if not path.is_dir():
                continue
            change_id = path.name
            title = change_id
            try:
                title = self.show_change_set(change_id).title
            except ValueError:
                index_title = read_title(_read_optional(path / "index.md"))
                title = index_title or change_id
            status = "generated" if all((path / filename).exists() for filename in self.required_files()) else "incomplete"
            statuses.append(
                SoftwareSpecStatus(
                    change_id=change_id,
                    title=title,
                    status=status,
                    path=path.relative_to(self.root),
                )
            )
        return statuses

    def show(self, change_id: str) -> str:
        path = self.p2p_dir / "outputs" / "software-spec" / change_id / "index.md"
        if not path.exists():
            raise ValueError("Software spec not found. Run `p2p spec refresh --change CHANGE-XXX` first.")
        return path.read_text(encoding="utf-8")

    def create_prompt(self, change_id: str) -> SoftwareSpecPrompt:
        self.refresh(change_id)
        spec_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        change = self.show_change_set(change_id)
        prompt_path = spec_dir / "spec-refine.prompt.md"
        context = "\n\n".join(
            [
                _read_optional(spec_dir / "index.md"),
                _read_optional(spec_dir / "requirements.md"),
                _read_optional(spec_dir / "design.md"),
                _read_optional(spec_dir / "acceptance.md"),
            ]
        )
        prompt_path.write_text(self._refine_prompt(change, context), encoding="utf-8")
        return SoftwareSpecPrompt(change_id=change_id, prompt_path=prompt_path.relative_to(self.root))

    def import_spec(self, change_id: str, source: Path) -> list[Path]:
        source = source.resolve()
        if not source.is_dir():
            raise ValueError(f"Software spec source directory not found: {source}")
        for filename in self.required_files():
            if not (source / filename).exists():
                raise ValueError(f"Missing required software spec artifact: {filename}")
        validate_yaml_key((source / "commands.yml").read_text(encoding="utf-8"), "commands")
        validate_yaml_key((source / "data-model.yml").read_text(encoding="utf-8"), "entities")
        validate_yaml_key((source / "provenance.yml").read_text(encoding="utf-8"), "source")

        target_dir = self.p2p_dir / "outputs" / "software-spec" / change_id
        target_dir.mkdir(parents=True, exist_ok=True)
        imported: list[Path] = []
        for filename in self.required_files():
            target = target_dir / filename
            shutil.copyfile(source / filename, target)
            imported.append(target.relative_to(self.root))
        return imported

    def _index_markdown(
        self,
        *,
        change_id: str,
        title: str,
        change_path: Path,
        summary: str,
        frontmatter: dict[str, object],
        included_proposals: list[str],
    ) -> str:
        return (
            f"# Software Spec - {change_id} - {title}\n\n"
            "## Summary\n\n"
            f"{summary}\n\n"
            "## Source\n\n"
            f"- Change Set: `{change_id}`\n"
            f"- Change path: `{change_path}`\n"
            f"- Included proposals: {', '.join(included_proposals) if included_proposals else 'none'}\n\n"
            "## Targets\n\n"
            f"- execution_domains: {', '.join(_string_list(frontmatter.get('execution_domains'))) or 'none'}\n"
            f"- implementation_targets: {', '.join(_string_list(frontmatter.get('implementation_targets'))) or 'none'}\n"
            f"- spec_targets: {', '.join(_string_list(frontmatter.get('spec_targets'))) or 'none'}\n"
            f"- export_targets: {', '.join(_string_list(frontmatter.get('export_targets'))) or 'none'}\n"
        )

    def _requirements_markdown(self, proposals: list[Any], change_text: str) -> str:
        lines = ["# Requirements", "", "## Functional Requirements", ""]
        if proposals:
            for proposal in proposals:
                lines.extend([f"### {proposal.proposal_id} - {proposal.title}", "", proposal.proposal, ""])
        else:
            lines.extend(["Not specified yet.", ""])
        lines.extend(
            [
                "## Non-Goals / Exclusions",
                "",
                read_markdown_section(change_text, "Excluded") or "Not specified yet.",
                "",
                "## Constraints",
                "",
                "Do not treat raw proposal discussion as implementation requirements without accepted scope.",
                "",
                "## Open Questions",
                "",
                "Not specified yet.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _design_markdown(self, frontmatter: dict[str, object], change_text: str) -> str:
        return (
            "# Design\n\n"
            "## Implementation Targets\n\n"
            f"{', '.join(_string_list(frontmatter.get('implementation_targets'))) or 'Not specified yet.'}\n\n"
            "## Data Flow\n\n"
            "Not specified yet.\n\n"
            "## CLI/API Surface\n\n"
            "Not specified yet.\n\n"
            "## Storage / Artifacts\n\n"
            f"{read_markdown_section(change_text, 'Deliverables') or 'Not specified yet.'}\n"
        )

    def _commands(self, tasks: list[object]) -> list[dict[str, object]]:
        commands: list[dict[str, object]] = []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            title = str(task.get("title") or "")
            if "command" in title.lower() or task.get("domain") == "software":
                commands.append(
                    {
                        "name": title,
                        "purpose": str(task.get("deliverable") or task.get("description") or "Not specified yet."),
                        "status": str(task.get("status") or "unknown"),
                    }
                )
        return commands

    def _entities(self, frontmatter: dict[str, object], proposals: list[Any]) -> list[dict[str, object]]:
        entities = [
            {"name": "ChangeSet", "description": "Operational package derived from accepted project intent."},
            {"name": "SoftwareSpec", "description": "P2P-native normalized implementation-facing specification."},
        ]
        for target in _string_list(frontmatter.get("export_targets")):
            entities.append({"name": f"ExportTarget:{target}", "description": "Downstream export target."})
        for proposal in proposals:
            entities.append({"name": proposal.proposal_id, "description": proposal.title})
        return entities

    def _acceptance_markdown(self, change_text: str, tasks: list[object]) -> str:
        lines = [
            "# Acceptance",
            "",
            "## Criteria",
            "",
            read_markdown_section(change_text, "Acceptance Criteria") or "Not specified yet.",
            "",
            "## Tests / Verification",
            "",
        ]
        task_lines = []
        for task in tasks:
            if isinstance(task, dict):
                task_lines.append(f"- {task.get('id', '-')}: {task.get('title', 'Untitled')} ({task.get('status', 'unknown')})")
        lines.extend(task_lines or ["- Not specified yet."])
        lines.append("")
        return "\n".join(lines)

    def _refine_prompt(self, change: Any, context: str) -> str:
        return (
            f"# P2P Software Spec Refinement Prompt - {change.change_id}\n\n"
            "You are refining a P2P-native software specification for implementation and downstream export.\n\n"
            "## Governance Boundary\n\n"
            "Do not add requirements that are not supported by accepted proposals, decisions, or the Change Set. "
            "Mark missing information as open questions instead of inventing it.\n\n"
            "## Required Output\n\n"
            "Return a directory containing exactly these artifacts:\n\n"
            "- index.md\n"
            "- requirements.md\n"
            "- design.md\n"
            "- commands.yml with top-level `commands`\n"
            "- data-model.yml with top-level `entities`\n"
            "- acceptance.md\n"
            "- provenance.yml with top-level `source`\n\n"
            "## Current Deterministic Spec Context\n\n"
            f"{context}\n"
        )

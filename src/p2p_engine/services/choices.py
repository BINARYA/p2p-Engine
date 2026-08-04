from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

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


@dataclass(frozen=True)
class ChoiceStatus:
    choice_id: str
    title: str
    status: str
    path: Path
    selected_option: str | None


@dataclass(frozen=True)
class ChoiceDetail:
    choice_id: str
    title: str
    status: str
    path: Path
    selected_option: str | None
    options: list[dict[str, object]]
    related_proposals: list[dict[str, object]]
    related_changes: list[dict[str, object]]
    blocks: list[dict[str, object]]


@dataclass(frozen=True)
class ChoiceDiscoveryFinding:
    finding_id: str
    kind: str
    target: str
    severity: str
    reason: str
    suggested_command: str


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _slugify(value: str) -> str:
    return _foundation_slugify(value, fallback="item")


def _find_choice_option(options: list[object], value: str) -> dict[str, object] | None:
    wanted = value.strip().lower()
    for option in options:
        if not isinstance(option, dict):
            continue
        option_id = str(option.get("id") or "").lower()
        title = str(option.get("title") or "").lower()
        if wanted in {option_id, title}:
            return option
    return None


class ChoiceLifecycleService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_proposal_dir: Callable[[str], Path],
        find_change_dir: Callable[[str], Path],
        choice_registry_records: Callable[[], list[dict[str, object]]],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir
        self.find_change_dir = find_change_dir
        self.choice_registry_records = choice_registry_records

    def create(
        self,
        title: str,
        options: list[str],
        related: list[str] | None = None,
        source: str | None = None,
    ) -> ChoiceStatus:
        cleaned_options = [option.strip() for option in options if option.strip()]
        if len(cleaned_options) < 2:
            raise ValueError("At least two --option values are required.")
        related = related or []
        for proposal_id in related:
            if proposal_id.startswith("PROP-"):
                self.find_proposal_dir(proposal_id)

        choice_id = self._next_id()
        title_slug = _slugify(title)
        choice_dir = self.p2p_dir / "choices" / f"{choice_id}-{title_slug}"
        choice_dir.mkdir(parents=True, exist_ok=False)
        now = date.today().isoformat()
        choice_frontmatter = _yaml_dump(
            {
                "choice_id": choice_id,
                "title": title,
                "status": "open",
                "created_at": now,
                "created_by": "local",
                "source": {"intake": source} if source else {},
                "related": {"proposals": related},
            }
        )
        (choice_dir / "choice.md").write_text(
            f"---\n{choice_frontmatter}---\n\n"
            f"# {choice_id} - {title}\n\n"
            "## Problem\n\n"
            "Pending.\n\n"
            "## Context\n\n"
            "Pending.\n\n"
            "## Governance Boundary\n\n"
            "This choice is advisory until decided through P2P governance.\n",
            encoding="utf-8",
        )
        (choice_dir / "options.yml").write_text(
            _yaml_dump(
                {
                    "options": [
                        {
                            "id": chr(ord("A") + index),
                            "title": option,
                            "status": "available",
                        }
                        for index, option in enumerate(cleaned_options)
                    ]
                }
            ),
            encoding="utf-8",
        )
        (choice_dir / "decision.md").write_text(
            f"# Decision - {choice_id}\n\n"
            "## Status\n\n"
            "`pending`\n\n"
            "## Selected Option\n\n"
            "Pending.\n\n"
            "## Reason\n\n"
            "Pending.\n\n"
            "## Decided By\n\n"
            "Pending.\n\n"
            "## Date\n\n"
            "Pending.\n",
            encoding="utf-8",
        )
        (choice_dir / "links.yml").write_text(
            _yaml_dump(
                {
                    "source": {"intake": source} if source else {},
                    "related_proposals": [
                        {"proposal": proposal_id, "relationship": "references", "rationale": ""}
                        for proposal_id in related
                    ],
                    "related_changes": [],
                }
            ),
            encoding="utf-8",
        )
        return ChoiceStatus(
            choice_id=choice_id,
            title=title,
            status="open",
            path=choice_dir.relative_to(self.root),
            selected_option=None,
        )

    def statuses(self) -> list[ChoiceStatus]:
        choices_dir = self.p2p_dir / "choices"
        statuses: list[ChoiceStatus] = []
        for path in sorted(choices_dir.iterdir()) if choices_dir.exists() else []:
            if not path.is_dir():
                continue
            choice_text = _read_optional(path / "choice.md")
            frontmatter = read_frontmatter(choice_text)
            decision_text = _read_optional(path / "decision.md")
            selected = read_markdown_section(decision_text, "Selected Option")
            selected_option = None if selected in {None, "Pending."} else selected
            statuses.append(
                ChoiceStatus(
                    choice_id=str(frontmatter.get("choice_id") or "-".join(path.name.split("-", 2)[:2])),
                    title=str(frontmatter.get("title") or read_title(choice_text) or path.name),
                    status=str(frontmatter.get("status") or "unknown"),
                    path=path.relative_to(self.root),
                    selected_option=selected_option,
                )
            )
        return statuses

    def show(self, choice_id: str) -> ChoiceDetail:
        choice_dir = self._find_dir(choice_id)
        choice_text = _read_optional(choice_dir / "choice.md")
        frontmatter = read_frontmatter(choice_text)
        decision_text = _read_optional(choice_dir / "decision.md")
        selected = read_markdown_section(decision_text, "Selected Option")
        selected_option = None if selected in {None, "Pending."} else selected
        options_data = _read_yaml_mapping(choice_dir / "options.yml", default={"options": []})
        links = _read_yaml_mapping(choice_dir / "links.yml", default={})
        return ChoiceDetail(
            choice_id=str(frontmatter.get("choice_id") or choice_id),
            title=str(frontmatter.get("title") or read_title(choice_text) or choice_id),
            status=str(frontmatter.get("status") or "unknown"),
            path=choice_dir.relative_to(self.root),
            selected_option=selected_option,
            options=options_data.get("options", []) if isinstance(options_data.get("options"), list) else [],
            related_proposals=links.get("related_proposals", [])
            if isinstance(links.get("related_proposals"), list)
            else [],
            related_changes=links.get("related_changes", [])
            if isinstance(links.get("related_changes"), list)
            else [],
            blocks=links.get("blocks", []) if isinstance(links.get("blocks"), list) else [],
        )

    def discover(self) -> list[ChoiceDiscoveryFinding]:
        findings: list[ChoiceDiscoveryFinding] = []
        project_choice_ids = {choice.choice_id for choice in self.statuses()}

        for record in self.choice_registry_records():
            choice_id = str(record.get("id") or "")
            status = str(record.get("status") or "unknown")
            selected = record.get("selected_option")
            if choice_id.startswith("CHOICE-PROP-") and choice_id not in project_choice_ids:
                proposal_id = str(record.get("proposal") or choice_id.removeprefix("CHOICE-"))
                findings.append(
                    ChoiceDiscoveryFinding(
                        finding_id=f"DISCOVERY-{len(findings) + 1:03d}",
                        kind="proposal_local_choice_candidate",
                        target=choice_id,
                        severity="medium" if status in {"open", "draft", "pending"} and not selected else "low",
                        reason=(
                            f"{choice_id} is proposal-local vote metadata for {proposal_id}, "
                            "not a project choice managed by p2p choice commands."
                        ),
                        suggested_command=f"p2p proposal show {proposal_id}",
                    )
                )

        for choice in self.statuses():
            detail = self.show(choice.choice_id)
            active_blocks = [
                block for block in detail.blocks if isinstance(block, dict) and block.get("status", "active") == "active"
            ]
            if choice.status != "decided" and active_blocks:
                findings.append(
                    ChoiceDiscoveryFinding(
                        finding_id=f"DISCOVERY-{len(findings) + 1:03d}",
                        kind="active_choice_blocker",
                        target=choice.choice_id,
                        severity="high",
                        reason=f"{choice.choice_id} is not decided and has active blockers.",
                        suggested_command=f"p2p choice show {choice.choice_id}",
                    )
                )
            elif choice.status in {"open", "draft", "pending"}:
                findings.append(
                    ChoiceDiscoveryFinding(
                        finding_id=f"DISCOVERY-{len(findings) + 1:03d}",
                        kind="open_project_choice",
                        target=choice.choice_id,
                        severity="medium",
                        reason=f"{choice.choice_id} is a project choice without a final decision.",
                        suggested_command=f"p2p choice show {choice.choice_id}",
                    )
                )
        return findings

    def block(
        self,
        choice_id: str,
        target: str,
        target_type: str,
        reason: str,
    ) -> ChoiceDetail:
        choice_dir = self._find_dir(choice_id)
        if target_type == "change":
            self.find_change_dir(target)
        elif target_type == "proposal":
            self.find_proposal_dir(target)
        else:
            raise ValueError("target_type must be `change` or `proposal`.")
        links_path = choice_dir / "links.yml"
        links = _read_yaml_mapping(links_path, default={})
        blocks = links.setdefault("blocks", [])
        if not isinstance(blocks, list):
            raise ValueError("Invalid links.yml: expected `blocks` list.")
        for block in blocks:
            if (
                isinstance(block, dict)
                and block.get("target") == target
                and block.get("target_type") == target_type
                and block.get("status", "active") == "active"
            ):
                block["reason"] = reason
                block["recorded_on"] = date.today().isoformat()
                links_path.write_text(_yaml_dump(links), encoding="utf-8")
                return self.show(choice_id)
        blocks.append(
            {
                "target": target,
                "target_type": target_type,
                "status": "active",
                "reason": reason,
                "recorded_on": date.today().isoformat(),
            }
        )
        links_path.write_text(_yaml_dump(links), encoding="utf-8")
        return self.show(choice_id)

    def unblock(self, choice_id: str, target: str, target_type: str) -> ChoiceDetail:
        choice_dir = self._find_dir(choice_id)
        links_path = choice_dir / "links.yml"
        links = _read_yaml_mapping(links_path, default={})
        blocks = links.get("blocks", [])
        if not isinstance(blocks, list):
            raise ValueError("Invalid links.yml: expected `blocks` list.")
        changed = False
        for block in blocks:
            if (
                isinstance(block, dict)
                and block.get("target") == target
                and block.get("target_type") == target_type
                and block.get("status", "active") == "active"
            ):
                block["status"] = "inactive"
                block["cleared_on"] = date.today().isoformat()
                changed = True
        if not changed:
            raise ValueError(f"Active blocker not found for {target_type}: {target}")
        links_path.write_text(_yaml_dump(links), encoding="utf-8")
        return self.show(choice_id)

    def decide(
        self,
        choice_id: str,
        option: str,
        reason: str,
        decider: str,
    ) -> ChoiceStatus:
        choice_dir = self._find_dir(choice_id)
        options_data = _read_yaml_mapping(choice_dir / "options.yml", default={"options": []})
        options = options_data.get("options", [])
        if not isinstance(options, list):
            raise ValueError("Invalid options.yml: expected `options` list.")
        selected = _find_choice_option(options, option)
        if selected is None:
            raise ValueError(f"Choice option not found: {option}")
        selected_id = str(selected.get("id"))
        selected_title = str(selected.get("title"))

        for option_item in options:
            if not isinstance(option_item, dict):
                continue
            option_item["status"] = "selected" if option_item.get("id") == selected_id else "not_selected"
        (choice_dir / "options.yml").write_text(_yaml_dump({"options": options}), encoding="utf-8")

        decision_text = (
            f"# Decision - {choice_id}\n\n"
            "## Status\n\n"
            "`decided`\n\n"
            "## Selected Option\n\n"
            f"{selected_id} - {selected_title}\n\n"
            "## Reason\n\n"
            f"{reason}\n\n"
            "## Decided By\n\n"
            f"{decider}\n\n"
            "## Date\n\n"
            f"{date.today().isoformat()}\n"
        )
        (choice_dir / "decision.md").write_text(decision_text, encoding="utf-8")

        choice_path = choice_dir / "choice.md"
        choice_text = _read_optional(choice_path)
        frontmatter = read_frontmatter(choice_text)
        frontmatter["status"] = "decided"
        choice_path.write_text(replace_frontmatter(choice_text, frontmatter), encoding="utf-8")

        return ChoiceStatus(
            choice_id=str(frontmatter.get("choice_id") or choice_id),
            title=str(frontmatter.get("title") or choice_id),
            status="decided",
            path=choice_dir.relative_to(self.root),
            selected_option=f"{selected_id} - {selected_title}",
        )

    def _next_id(self) -> str:
        choices_dir = self.p2p_dir / "choices"
        max_id = 0
        for path in sorted(choices_dir.iterdir()) if choices_dir.exists() else []:
            if not path.is_dir():
                continue
            match = re.match(r"CHOICE-(\d{3})-", path.name)
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"CHOICE-{max_id + 1:03d}"

    def _find_dir(self, choice_id: str) -> Path:
        choices_dir = self.p2p_dir / "choices"
        for path in sorted(choices_dir.iterdir()) if choices_dir.exists() else []:
            if path.is_dir() and path.name.startswith(f"{choice_id}-"):
                return path
        raise ValueError(f"Choice not found: {choice_id}")

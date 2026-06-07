from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from p2p_engine.foundation.validators import (
    validate_tasks_yaml,
    validate_yaml_key,
)
from p2p_engine.prompts.clarify import render_clarify_prompt
from p2p_engine.prompts.digest import render_digest_prompt
from p2p_engine.prompts.explore import render_explore_prompt
from p2p_engine.prompts.impact import render_impact_prompt
from p2p_engine.prompts.plan import render_plan_prompt
from p2p_engine.prompts.swot import render_swot_prompt
from p2p_engine.prompts.synthesize import render_synthesize_prompt
from p2p_engine.prompts.tasks import render_tasks_prompt

PromptKind = Literal["explore", "digest", "clarify", "synthesize", "plan", "tasks", "swot", "impact"]
ImportKind = Literal["clarify", "synthesize", "plan", "tasks"]

EXPLORATION_ARTIFACTS = (
    "exploration.md",
    "findings.md",
    "alternatives.md",
    "open-questions.md",
    "risks.md",
    "assumptions.md",
    "suggested-scope.md",
)


@dataclass(frozen=True)
class ExplorationArtifactStatus:
    filename: str
    exists: bool
    has_content: bool
    quality_state: str


@dataclass(frozen=True)
class ExplorationStatus:
    proposal_id: str
    artifacts: list[ExplorationArtifactStatus]
    unresolved_questions: int
    suggested_next_command: str


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _has_meaningful_content(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    placeholders = (
        "not explored yet.",
        "none identified yet.",
        "not suggested yet.",
        "findings: []",
    )
    lower = stripped.lower()
    return not any(placeholder in lower for placeholder in placeholders)


def _artifact_quality_state(path: Path, text: str) -> str:
    if not path.exists():
        return "missing"
    stripped = text.strip()
    if not stripped:
        return "placeholder"
    lower = stripped.lower()
    placeholders = (
        "not explored yet.",
        "none identified yet.",
        "not suggested yet.",
        "findings: []",
        "pending.",
    )
    if any(placeholder in lower for placeholder in placeholders):
        return "placeholder"
    content_lines = [
        line.strip()
        for line in stripped.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    content_text = " ".join(content_lines)
    if len(content_text) < 80:
        return "thin"
    return "meaningful"


def _count_open_questions(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^(\d+\.|-|\*)\s+.+\?", stripped):
            count += 1
    return count


class ProposalArtifactService:
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

    def generate_prompt(self, proposal_id: str, kind: PromptKind) -> Path:
        proposal_dir = self.find_proposal_dir(proposal_id)
        renderers = {
            "explore": render_explore_prompt,
            "digest": render_digest_prompt,
            "clarify": render_clarify_prompt,
            "synthesize": render_synthesize_prompt,
            "plan": render_plan_prompt,
            "tasks": render_tasks_prompt,
            "swot": render_swot_prompt,
            "impact": render_impact_prompt,
        }
        output_dir = self.p2p_dir / "prompts" / proposal_id
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{kind}.prompt.md"
        path.write_text(renderers[kind](self._prompt_context(proposal_id, proposal_dir)), encoding="utf-8")
        return path.relative_to(self.root)

    def import_exploration(self, proposal_id: str, source: Path) -> list[Path]:
        proposal_dir = self.find_proposal_dir(proposal_id)
        source = source.resolve()
        imported: list[Path] = []
        if source.is_dir():
            for filename in EXPLORATION_ARTIFACTS:
                source_path = source / filename
                if source_path.exists():
                    target = proposal_dir / filename
                    shutil.copyfile(source_path, target)
                    imported.append(target.relative_to(self.root))
        elif source.is_file():
            target = proposal_dir / "exploration.md"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            imported.append(target.relative_to(self.root))
        else:
            raise ValueError(f"Exploration source not found: {source}")
        if not imported:
            raise ValueError(f"No exploration artifacts found in: {source}")
        return imported

    def exploration_status(self, proposal_id: str) -> ExplorationStatus:
        proposal_dir = self.find_proposal_dir(proposal_id)
        artifacts: list[ExplorationArtifactStatus] = []
        for filename in EXPLORATION_ARTIFACTS:
            path = proposal_dir / filename
            text = _read_optional(path)
            artifacts.append(
                ExplorationArtifactStatus(
                    filename=filename,
                    exists=path.exists(),
                    has_content=_has_meaningful_content(text),
                    quality_state=_artifact_quality_state(path, text),
                )
            )
        questions_text = _read_optional(proposal_dir / "open-questions.md")
        unresolved = _count_open_questions(questions_text)
        missing = [artifact for artifact in artifacts if not artifact.has_content]
        suggested = (
            f"p2p explore prompt {proposal_id}"
            if missing
            else f"p2p clarify prompt {proposal_id}"
        )
        return ExplorationStatus(
            proposal_id=proposal_id,
            artifacts=artifacts,
            unresolved_questions=unresolved,
            suggested_next_command=suggested,
        )

    def import_artifact(self, proposal_id: str, kind: ImportKind, source: Path) -> Path:
        proposal_dir = self.find_proposal_dir(proposal_id)
        source = source.resolve()
        if not source.is_file():
            raise ValueError(f"Import source not found: {source}")

        target_name = {
            "clarify": "clarifications.md",
            "synthesize": "proposal.md",
            "plan": "execution-plan.md",
            "tasks": "tasks.yml",
        }[kind]
        content = source.read_text(encoding="utf-8")
        if kind == "tasks":
            validate_tasks_yaml(content)
        target = proposal_dir / target_name
        target.write_text(content, encoding="utf-8")
        return target.relative_to(self.root)

    def import_impact(self, proposal_id: str, source: Path) -> list[Path]:
        proposal_dir = self.find_proposal_dir(proposal_id)
        source = source.resolve()
        imported: list[Path] = []
        if source.is_dir():
            mappings = {
                "impact-map.yml": "impact",
                "related-proposals.yml": "related_proposals",
                "conflict-analysis.yml": "conflicts",
            }
            for filename, key in mappings.items():
                source_path = source / filename
                if source_path.exists():
                    validate_yaml_key(source_path.read_text(encoding="utf-8"), key)
                    target = proposal_dir / filename
                    shutil.copyfile(source_path, target)
                    imported.append(target.relative_to(self.root))
        elif source.is_file():
            validate_yaml_key(source.read_text(encoding="utf-8"), "impact")
            target = proposal_dir / "impact-map.yml"
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            imported.append(target.relative_to(self.root))
        else:
            raise ValueError(f"Impact source not found: {source}")
        if not imported:
            raise ValueError(f"No impact artifacts found in: {source}")
        return imported

    def _prompt_context(self, proposal_id: str, proposal_dir: Path) -> dict[str, str]:
        return {
            "proposal_id": proposal_id,
            "proposal": _read_optional(proposal_dir / "proposal.md"),
            "contributions": _read_optional(proposal_dir / "contributions.yml"),
            "comments": _read_optional(proposal_dir / "comments.yml"),
            "clarifications": _read_optional(proposal_dir / "clarifications.md"),
            "decision": _read_optional(proposal_dir / "decision.md"),
            "votes": _read_optional(proposal_dir / "votes.yml"),
            "swot_analysis": _read_optional(proposal_dir / "swot-analysis.md"),
            "exploration": _read_optional(proposal_dir / "exploration.md"),
            "findings": _read_optional(proposal_dir / "findings.md"),
            "alternatives": _read_optional(proposal_dir / "alternatives.md"),
            "open_questions": _read_optional(proposal_dir / "open-questions.md"),
            "risks": _read_optional(proposal_dir / "risks.md"),
            "assumptions": _read_optional(proposal_dir / "assumptions.md"),
            "suggested_scope": _read_optional(proposal_dir / "suggested-scope.md"),
            "governance": _read_optional(self.p2p_dir / "governance" / "governance.yml"),
            "roles": _read_optional(self.p2p_dir / "governance" / "roles.yml"),
            "decision_precedents": _read_optional(
                self.p2p_dir / "governance" / "decision-precedents.yml"
            ),
            "project_overview": _read_optional(self.p2p_dir / "project" / "overview.md"),
            "project_decisions": _read_optional(self.p2p_dir / "project" / "decisions-map.yml"),
            "project_conflicts": _read_optional(self.p2p_dir / "project" / "conflicts.yml"),
            "constitution": _read_optional(self.p2p_dir / "governance" / "constitution.md"),
            "decision_rules": _read_optional(self.p2p_dir / "governance" / "decision-rules.md"),
            "relevance_criteria": _read_optional(self.p2p_dir / "governance" / "relevance-criteria.md"),
        }

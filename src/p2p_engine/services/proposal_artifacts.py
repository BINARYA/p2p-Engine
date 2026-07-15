from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from p2p_engine.core.decision_context import (
    ContextBudget,
    DecisionContextIndex,
    RetrievalRequest,
)
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
from p2p_engine.services.decision_context_rendering import render_nearby_decision_context
from p2p_engine.services.decision_context_retrieval import DecisionContextRetrievalService

PromptKind = Literal["explore", "digest", "clarify", "synthesize", "plan", "tasks", "swot", "impact"]
ImportKind = Literal["clarify", "synthesize", "plan", "tasks"]
ArtifactImportKind = Literal["explore", "impact", "clarify", "synthesize", "plan", "tasks"]
ArtifactImportInputMode = Literal["source", "content", "artifacts"]

EXPLORATION_ARTIFACTS = (
    "exploration.md",
    "findings.md",
    "alternatives.md",
    "open-questions.md",
    "risks.md",
    "assumptions.md",
    "suggested-scope.md",
)

IMPACT_ARTIFACTS = {
    "impact-map.yml": "impact",
    "related-proposals.yml": "related_proposals",
    "conflict-analysis.yml": "conflicts",
}

GENERATED_ARTIFACT_TARGETS = {
    "clarify": "clarifications.md",
    "synthesize": "proposal.md",
    "plan": "execution-plan.md",
    "tasks": "tasks.yml",
}


@dataclass(frozen=True)
class ArtifactImportItem:
    path: Path
    filename: str
    validated: bool


@dataclass(frozen=True)
class ArtifactImportResult:
    proposal_id: str
    kind: ArtifactImportKind
    input_mode: ArtifactImportInputMode
    imported: list[ArtifactImportItem]
    artifact_state_updated: bool = False


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
        decision_context_index: Callable[[], DecisionContextIndex],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir
        self.decision_context_index = decision_context_index

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
        context = self._prompt_context(proposal_id, proposal_dir)
        if kind in {"explore", "impact", "synthesize"}:
            index = self.decision_context_index()
            packet = DecisionContextRetrievalService().retrieve(
                index,
                RetrievalRequest(budget=ContextBudget.MEDIUM, target_id=proposal_id),
            )
            context["nearby_decision_context"] = render_nearby_decision_context(
                packet,
                phase=kind,
                index=index if kind == "impact" else None,
                target_id=proposal_id if kind == "impact" else "",
            )
        rendered = renderers[kind](context)
        output_dir = self.p2p_dir / "prompts" / proposal_id
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{kind}.prompt.md"
        path.write_text(rendered, encoding="utf-8")
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

        target_name = GENERATED_ARTIFACT_TARGETS[kind]
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
            for filename, key in IMPACT_ARTIFACTS.items():
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

    def import_content(
        self,
        proposal_id: str,
        kind: ArtifactImportKind,
        *,
        source: Path | None = None,
        content: str | None = None,
        artifacts: dict[str, str] | None = None,
    ) -> ArtifactImportResult:
        input_mode = _artifact_import_input_mode(source=source, content=content, artifacts=artifacts)
        if input_mode == "source":
            return self._import_source(proposal_id, kind, source)
        proposal_dir = self.find_proposal_dir(proposal_id)
        if input_mode == "content":
            return self._import_payload_content(proposal_id, proposal_dir, kind, content)
        return self._import_payload_artifacts(proposal_id, proposal_dir, kind, artifacts)

    def _import_source(
        self,
        proposal_id: str,
        kind: ArtifactImportKind,
        source: Path | None,
    ) -> ArtifactImportResult:
        if source is None:
            raise ValueError("Import source is required for source input mode.")
        if kind == "explore":
            imported = self.import_exploration(proposal_id, source)
            return _artifact_import_result(proposal_id, kind, "source", imported, validated=False)
        if kind == "impact":
            imported = self.import_impact(proposal_id, source)
            return _artifact_import_result(proposal_id, kind, "source", imported, validated=True)
        imported_path = self.import_artifact(proposal_id, kind, source)
        return _artifact_import_result(
            proposal_id,
            kind,
            "source",
            [imported_path],
            validated=kind == "tasks",
        )

    def _import_payload_content(
        self,
        proposal_id: str,
        proposal_dir: Path,
        kind: ArtifactImportKind,
        content: str | None,
    ) -> ArtifactImportResult:
        if content is None:
            raise ValueError("Import content is required for content input mode.")
        target_name = _content_target(kind)
        _validate_content(kind, target_name, content)
        target = proposal_dir / target_name
        target.write_text(content, encoding="utf-8")
        return _artifact_import_result(
            proposal_id,
            kind,
            "content",
            [target.relative_to(self.root)],
            validated=_is_validated_target(kind, target_name),
        )

    def _import_payload_artifacts(
        self,
        proposal_id: str,
        proposal_dir: Path,
        kind: ArtifactImportKind,
        artifacts: dict[str, str] | None,
    ) -> ArtifactImportResult:
        if kind not in ("explore", "impact"):
            raise ValueError(f"Artifact payload import is not supported for import kind: {kind}")
        if not artifacts:
            raise ValueError("Artifact payload must include at least one artifact.")
        allowed = set(EXPLORATION_ARTIFACTS) if kind == "explore" else set(IMPACT_ARTIFACTS)
        unexpected = sorted(filename for filename in artifacts if filename not in allowed)
        if unexpected:
            raise ValueError(
                f"Unsupported {kind} artifact filename: {unexpected[0]}. "
                f"Allowed: {', '.join(sorted(allowed))}"
            )
        if kind == "impact":
            for filename, artifact_content in artifacts.items():
                validate_yaml_key(artifact_content, IMPACT_ARTIFACTS[filename])

        ordered_filenames = EXPLORATION_ARTIFACTS if kind == "explore" else tuple(IMPACT_ARTIFACTS)
        imported: list[Path] = []
        for filename in ordered_filenames:
            if filename not in artifacts:
                continue
            target = proposal_dir / filename
            target.write_text(artifacts[filename], encoding="utf-8")
            imported.append(target.relative_to(self.root))
        return _artifact_import_result(proposal_id, kind, "artifacts", imported, validated=kind == "impact")

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
            "constitution": _read_optional(self.p2p_dir / "governance" / "constitution.md"),
            "decision_rules": _read_optional(self.p2p_dir / "governance" / "decision-rules.md"),
            "relevance_criteria": _read_optional(self.p2p_dir / "governance" / "relevance-criteria.md"),
        }


def _artifact_import_input_mode(
    *,
    source: Path | None,
    content: str | None,
    artifacts: dict[str, str] | None,
) -> ArtifactImportInputMode:
    modes: list[ArtifactImportInputMode] = []
    if source is not None:
        modes.append("source")
    if content is not None:
        modes.append("content")
    if artifacts is not None:
        modes.append("artifacts")
    if len(modes) != 1:
        raise ValueError("Provide exactly one artifact import input: source, content, or artifacts.")
    return modes[0]


def _content_target(kind: ArtifactImportKind) -> str:
    if kind == "explore":
        return "exploration.md"
    if kind == "impact":
        return "impact-map.yml"
    return GENERATED_ARTIFACT_TARGETS[kind]


def _validate_content(kind: ArtifactImportKind, target_name: str, content: str) -> None:
    if kind == "impact":
        validate_yaml_key(content, "impact")
    elif kind == "tasks":
        validate_tasks_yaml(content)
    elif target_name in IMPACT_ARTIFACTS:
        validate_yaml_key(content, IMPACT_ARTIFACTS[target_name])


def _is_validated_target(kind: ArtifactImportKind, target_name: str) -> bool:
    return kind in ("impact", "tasks") or target_name in IMPACT_ARTIFACTS


def _artifact_import_result(
    proposal_id: str,
    kind: ArtifactImportKind,
    input_mode: ArtifactImportInputMode,
    paths: list[Path],
    *,
    validated: bool,
) -> ArtifactImportResult:
    return ArtifactImportResult(
        proposal_id=proposal_id,
        kind=kind,
        input_mode=input_mode,
        imported=[
            ArtifactImportItem(path=path, filename=path.name, validated=validated)
            for path in paths
        ],
    )

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

import yaml

from p2p_engine.core.decision_context import (
    ContextBudget,
    DecisionContextIndex,
    RetrievalRequest,
)
from p2p_engine.core.mutation_preview import (
    MutationPreview,
    MutationPreviewService,
    MutationResult,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.proposal_decision_events import ProposalDecisionLifecycleView
from p2p_engine.foundation.validators import (
    validate_tasks_yaml,
    validate_yaml_key,
)
from p2p_engine.foundation.yaml_loaders import load_yaml
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
from p2p_engine.services.decision_context_topology import classify_relation_term
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.proposal_artifact_state import ProposalArtifactStateService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter

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
        atomic_writer: AtomicMutationWriter | None = None,
        vertical_service: ProjectVerticalService | None = None,
        artifact_state_service: ProposalArtifactStateService | None = None,
        proposal_lifecycle_status: (
            Callable[[str], ProposalDecisionLifecycleView] | None
        ) = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir
        self.decision_context_index = decision_context_index
        self.atomic_writer = atomic_writer or AtomicMutationWriter(root=root, p2p_dir=p2p_dir)
        self.vertical_service = vertical_service or ProjectVerticalService(
            root=root,
            p2p_dir=p2p_dir,
            proposal_summaries=lambda: [],
            find_proposal_dir=find_proposal_dir,
        )
        self.artifact_state_service = artifact_state_service or ProposalArtifactStateService(
            root=root,
            find_proposal_dir=find_proposal_dir,
        )
        self.proposal_lifecycle_status = proposal_lifecycle_status

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
        artifacts = load_impact_artifacts(source)
        if not artifacts:
            raise ValueError(f"No impact artifacts found in: {source}")
        return self._atomic_impact_import(proposal_id, proposal_dir, artifacts)

    def preview_impact(
        self,
        proposal_id: str,
        artifacts: dict[str, str],
        *,
        actor: str,
    ) -> MutationPreview:
        proposal_dir = self.find_proposal_dir(proposal_id)
        parsed = self._validate_impact_set(proposal_id, artifacts)
        targets = tuple((proposal_dir / filename).relative_to(self.root).as_posix() for filename in sorted(artifacts))
        sources = []
        semantic_diff: dict[str, object] = {}
        candidate_semantics: dict[str, object] = {}
        for filename in sorted(artifacts):
            target = proposal_dir / filename
            relative = target.relative_to(self.root).as_posix()
            current = target.read_bytes() if target.exists() else None
            sources.append(source_precondition(relative, current))
            candidate_semantics[relative] = parsed[filename]
            semantic_diff[relative] = {
                "before_exists": current is not None,
                "before_semantic_sha256": _yaml_semantic_hash(current),
                "candidate_semantic_sha256": semantic_sha256(parsed[filename]),
            }
        authority = self._impact_authority(proposal_id, proposal_dir, actor)
        blockers = () if authority in {"owner_confirmed", "known_actor"} else (authority,)
        return MutationPreviewService.build(
            operation_id=f"proposal-impact:{proposal_id}",
            targets=targets,
            actor=actor,
            authority=authority,
            sources=sources,
            candidate_semantics=candidate_semantics,
            semantic_diff=semantic_diff,
            blockers=blockers,
        )

    def apply_impact(
        self,
        proposal_id: str,
        artifacts: dict[str, str],
        *,
        preview_token: str,
        actor: str,
        confirm: bool,
    ) -> MutationResult:
        preview = self.preview_impact(proposal_id, artifacts, actor=actor)
        if not confirm:
            return MutationResult(
                status="blocked",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Explicit confirmation is required for impact correction.",
            )
        if preview.preview_token != preview_token:
            return MutationResult(
                status="stale_preview",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Impact sources or candidate semantics changed after preview.",
            )
        if not preview.apply_allowed:
            return MutationResult(
                status="blocked",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Actor is not authorized to replace committed impact evidence.",
            )
        proposal_dir = self.find_proposal_dir(proposal_id)
        candidates = {
            (proposal_dir / filename).relative_to(self.root).as_posix(): content.encode("utf-8")
            for filename, content in artifacts.items()
        }
        return self.atomic_writer.apply(
            operation_id=preview.operation_id,
            candidates=candidates,
            sources=preview.source_preconditions,
            preview_token=preview.preview_token,
            actor=actor,
        )

    def preview_vertical_coverage(
        self,
        proposal_id: str,
        payload: dict[str, object],
        *,
        actor: str,
    ) -> MutationPreview:
        authority = self._coverage_authority(actor)
        candidate = self._coverage_candidate_payload(
            proposal_id,
            payload,
            actor=actor,
            authority=authority,
            imported_at="__P2P_APPLY_AT__",
        )
        self.vertical_service.validate_proposal_vertical_coverage_candidate(proposal_id, candidate)
        proposal_dir = self.find_proposal_dir(proposal_id)
        coverage_path = proposal_dir / "vertical-coverage.yml"
        state_path = proposal_dir / "artifact-state.yml"
        coverage_relative = coverage_path.relative_to(self.root).as_posix()
        state_relative = state_path.relative_to(self.root).as_posix()
        state_candidate = self.artifact_state_service.render_satisfied_artifact_candidate(
            proposal_id,
            "vertical_coverage",
            actor=actor,
            source="vertical_coverage_import",
            reason="Owner-reviewed vertical coverage was imported.",
            updated_at="__P2P_APPLY_AT__",
            owner_confirmed=authority == "owner_confirmed",
        )
        current_coverage = coverage_path.read_bytes() if coverage_path.exists() else None
        current_state = state_path.read_bytes() if state_path.exists() else None
        candidate_semantics = {
            coverage_relative: _without_audit_timestamps(candidate),
            state_relative: _without_audit_timestamps(state_candidate),
        }
        before_sections = _coverage_section_ids(_yaml_mapping_or_empty(current_coverage))
        candidate_sections = _coverage_section_ids(candidate)
        return MutationPreviewService.build(
            operation_id=f"proposal-vertical-coverage:{proposal_id}",
            targets=(coverage_relative, state_relative),
            actor=actor,
            authority=authority,
            sources=(
                source_precondition(coverage_relative, current_coverage),
                source_precondition(state_relative, current_state),
            ),
            candidate_semantics=candidate_semantics,
            semantic_diff={
                coverage_relative: {
                    "before_sections": before_sections,
                    "candidate_sections": candidate_sections,
                    "added_sections": sorted(set(candidate_sections) - set(before_sections)),
                    "removed_sections": sorted(set(before_sections) - set(candidate_sections)),
                    "replacement": True,
                },
                state_relative: {
                    "artifact_id": "vertical_coverage",
                    "candidate_status": "satisfied",
                    "candidate_confirmation": (
                        "owner_confirmed" if authority == "owner_confirmed" else "agent_proposed"
                    ),
                },
            },
            blockers=() if authority == "owner_confirmed" else (authority,),
        )

    def apply_vertical_coverage(
        self,
        proposal_id: str,
        payload: dict[str, object],
        *,
        preview_token: str,
        actor: str,
        confirm: bool,
    ) -> MutationResult:
        preview = self.preview_vertical_coverage(proposal_id, payload, actor=actor)
        if not confirm:
            return MutationResult(
                status="blocked",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Explicit confirmation is required for vertical coverage import.",
            )
        if preview.preview_token != preview_token:
            return MutationResult(
                status="stale_preview",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Vertical coverage sources, active vertical, or candidate changed after preview.",
            )
        if not preview.apply_allowed:
            return MutationResult(
                status="blocked",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=actor,
                message="Actor is not authorized to import declared vertical coverage.",
            )
        authority = self._coverage_authority(actor)
        imported_at = _utc_now()
        coverage = self._coverage_candidate_payload(
            proposal_id,
            payload,
            actor=actor,
            authority=authority,
            imported_at=imported_at,
        )
        self.vertical_service.validate_proposal_vertical_coverage_candidate(proposal_id, coverage)
        state = self.artifact_state_service.render_satisfied_artifact_candidate(
            proposal_id,
            "vertical_coverage",
            actor=actor,
            source="vertical_coverage_import",
            reason="Owner-reviewed vertical coverage was imported.",
            updated_at=imported_at,
            owner_confirmed=True,
        )
        proposal_dir = self.find_proposal_dir(proposal_id)
        candidates = {
            (proposal_dir / "vertical-coverage.yml").relative_to(self.root).as_posix(): yaml.safe_dump(
                coverage, sort_keys=False, allow_unicode=False
            ).encode("utf-8"),
            (proposal_dir / "artifact-state.yml").relative_to(self.root).as_posix(): yaml.safe_dump(
                state, sort_keys=False, allow_unicode=False
            ).encode("utf-8"),
        }
        return self.atomic_writer.apply(
            operation_id=preview.operation_id,
            candidates=candidates,
            sources=preview.source_preconditions,
            preview_token=preview.preview_token,
            actor=actor,
        )

    def _coverage_candidate_payload(
        self,
        proposal_id: str,
        payload: dict[str, object],
        *,
        actor: str,
        authority: str,
        imported_at: str,
    ) -> dict[str, object]:
        candidate = yaml.safe_load(yaml.safe_dump(payload, sort_keys=False))
        if not isinstance(candidate, dict):
            raise ValueError("Vertical coverage payload must be a mapping.")
        coverage = candidate.get("vertical_coverage")
        if not isinstance(coverage, dict):
            raise ValueError("Vertical coverage payload requires vertical_coverage mapping.")
        if coverage.get("schema_version", 2) != 2:
            raise ValueError("New vertical coverage imports require schema_version 2.")
        coverage["schema_version"] = 2
        if str(coverage.get("proposal_id") or "") != proposal_id:
            raise ValueError("Vertical coverage proposal_id does not match the target proposal.")
        provenance = coverage.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError("Vertical coverage import requires provenance mapping.")
        supplied_actor = str(provenance.get("actor") or "")
        if supplied_actor and supplied_actor != actor:
            raise ValueError("Vertical coverage provenance actor must match the requested actor.")
        provenance.update(
            {
                "operation_id": f"proposal-vertical-coverage:{proposal_id}",
                "actor": actor,
                "authority": authority,
                "imported_at": imported_at,
            }
        )
        return candidate

    def _coverage_authority(self, actor: str) -> str:
        return "owner_confirmed" if _actor_role(self.p2p_dir / "project" / "permissions.yml", actor) == "owner" else "owner_required"

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
        if kind == "impact":
            paths = self._atomic_impact_import(
                proposal_id,
                proposal_dir,
                {target_name: content},
            )
            return _artifact_import_result(
                proposal_id,
                kind,
                "content",
                paths,
                validated=True,
            )
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
            return _artifact_import_result(
                proposal_id,
                kind,
                "artifacts",
                self._atomic_impact_import(proposal_id, proposal_dir, artifacts),
                validated=True,
            )

        ordered_filenames = EXPLORATION_ARTIFACTS if kind == "explore" else tuple(IMPACT_ARTIFACTS)
        imported: list[Path] = []
        for filename in ordered_filenames:
            if filename not in artifacts:
                continue
            target = proposal_dir / filename
            target.write_text(artifacts[filename], encoding="utf-8")
            imported.append(target.relative_to(self.root))
        return _artifact_import_result(proposal_id, kind, "artifacts", imported, validated=kind == "impact")

    def _atomic_impact_import(
        self,
        proposal_id: str,
        proposal_dir: Path,
        artifacts: dict[str, str],
    ) -> list[Path]:
        self._validate_impact_set(proposal_id, artifacts)
        existing = [proposal_dir / filename for filename in artifacts if (proposal_dir / filename).exists()]
        if existing and self._impact_requires_owner(proposal_id, proposal_dir):
            raise ValueError(
                "Committed impact correction requires impact preview/apply with actor and confirmation."
            )
        targets = {
            (proposal_dir / filename).relative_to(self.root).as_posix(): content.encode("utf-8")
            for filename, content in artifacts.items()
        }
        sources = tuple(
            source_precondition(relative, (self.root / relative).read_bytes() if (self.root / relative).exists() else None)
            for relative in sorted(targets)
        )
        result = self.atomic_writer.apply(
            operation_id=f"proposal-impact-import:{proposal_id}",
            candidates=targets,
            sources=sources,
            preview_token=MutationPreviewService.token(
                operation_id=f"proposal-impact-import:{proposal_id}",
                targets=tuple(targets),
                sources=sources,
                candidate_semantics={path: load_yaml(content) for path, content in targets.items()},
            ),
            actor="compatible-import",
        )
        if result.status != "applied":
            raise ValueError(result.message or f"Impact import failed: {result.status}")
        return [
            (proposal_dir / filename).relative_to(self.root)
            for filename in IMPACT_ARTIFACTS
            if filename in artifacts
        ]

    def _validate_impact_set(self, proposal_id: str, artifacts: dict[str, str]) -> dict[str, object]:
        if not artifacts:
            raise ValueError("Impact artifact set must include at least one artifact.")
        unexpected = sorted(set(artifacts) - set(IMPACT_ARTIFACTS))
        if unexpected:
            raise ValueError(f"Unsupported impact artifact filename: {unexpected[0]}")
        parsed: dict[str, object] = {}
        for filename in sorted(artifacts):
            content = artifacts[filename]
            validate_yaml_key(content, IMPACT_ARTIFACTS[filename])
            value = load_yaml(content)
            if not isinstance(value, dict):
                raise ValueError(f"Impact artifact must be a YAML mapping: {filename}")
            parsed[filename] = value
        related = parsed.get("related-proposals.yml")
        if isinstance(related, dict):
            payload = related.get("related_proposals")
            if isinstance(payload, dict):
                payload = payload.get("items")
            if payload is None:
                payload = []
            if not isinstance(payload, list):
                raise ValueError("related_proposals must be a sequence or an items mapping")
            for index, item in enumerate(payload):
                if not isinstance(item, dict):
                    raise ValueError(f"related_proposals[{index}] must be a mapping")
                target = str(item.get("proposal") or item.get("proposal_id") or item.get("id") or "").strip()
                if not re.fullmatch(r"PROP-[0-9]+", target):
                    raise ValueError(f"related_proposals[{index}] target must be a proposal id")
                self.find_proposal_dir(target)
                relation = str(item.get("relationship") or item.get("relation") or item.get("type") or "related")
                policy = classify_relation_term(relation)
                if policy["category"] in {"ambiguous", "invalid"}:
                    raise ValueError(
                        f"related_proposals[{index}] relation {relation!r} is {policy['category']} and requires curation"
                    )
        return parsed

    def _impact_authority(
        self,
        proposal_id: str,
        proposal_dir: Path,
        actor: str,
    ) -> str:
        role = _actor_role(self.p2p_dir / "project" / "permissions.yml", actor)
        if self._impact_requires_owner(proposal_id, proposal_dir):
            return "owner_confirmed" if role == "owner" else "owner_required"
        return "known_actor" if role else "actor_unknown"

    def _impact_requires_owner(
        self,
        proposal_id: str,
        proposal_dir: Path,
    ) -> bool:
        if self.proposal_lifecycle_status is not None:
            lifecycle = self.proposal_lifecycle_status(proposal_id)
            return lifecycle.active or lifecycle.ever_active
        return _proposal_lifecycle_status(proposal_dir) in {
            "accepted",
            "accepted_with_changes",
        }

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


def load_impact_artifacts(source: Path) -> dict[str, str]:
    source = source.resolve()
    artifacts: dict[str, str] = {}
    if source.is_dir():
        for filename in IMPACT_ARTIFACTS:
            source_path = source / filename
            if source_path.exists():
                artifacts[filename] = source_path.read_text(encoding="utf-8")
    elif source.is_file():
        artifacts["impact-map.yml"] = source.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Impact source not found: {source}")
    return artifacts


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


def _yaml_semantic_hash(content: bytes | None) -> str | None:
    if content is None:
        return None
    try:
        return semantic_sha256(load_yaml(content))
    except (UnicodeDecodeError, yaml.YAMLError):
        return None


def _proposal_lifecycle_status(proposal_dir: Path) -> str:
    path = proposal_dir / "proposal.md"
    if not path.exists():
        return "unknown"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^## Status\s*\n+\s*`?([^`\n]+)`?", text, flags=re.MULTILINE)
    return match.group(1).strip().lower().replace("-", "_") if match else "unknown"


def _actor_role(path: Path, actor: str) -> str:
    if not actor:
        return ""
    if not path.exists():
        # Match PermissionsService.show() for legacy workspaces whose explicit
        # policy has not yet been materialized by schema migration.
        return "owner" if actor == "owner" else ""
    try:
        payload = load_yaml(path.read_bytes())
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return ""
    identities = payload.get("identities") if isinstance(payload, dict) else None
    identity = identities.get(actor) if isinstance(identities, dict) else None
    return str(identity.get("role") or "") if isinstance(identity, dict) else ""


def _yaml_mapping_or_empty(content: bytes | None) -> dict[str, object]:
    if content is None:
        return {}
    try:
        payload = load_yaml(content)
    except (UnicodeDecodeError, yaml.YAMLError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _coverage_section_ids(payload: dict[str, object]) -> list[str]:
    coverage = payload.get("vertical_coverage")
    sections = coverage.get("sections") if isinstance(coverage, dict) else None
    if not isinstance(sections, list):
        return []
    return sorted(
        str(item.get("id") or "")
        for item in sections
        if isinstance(item, dict) and str(item.get("id") or "")
    )


def _without_audit_timestamps(payload: dict[str, object]) -> dict[str, object]:
    candidate = yaml.safe_load(yaml.safe_dump(payload, sort_keys=False))

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key in ("at", "updated_at", "initialized_at", "created_at", "imported_at"):
                value.pop(key, None)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(candidate)
    return candidate if isinstance(candidate, dict) else {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

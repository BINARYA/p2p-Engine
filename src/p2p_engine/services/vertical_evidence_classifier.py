from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from p2p_engine.core.project_questions import ProjectQuestionArtifact
from p2p_engine.core.project_verticals import (
    ProjectDefinitionState,
    ResolvedVerticalPack,
    VerticalLock,
)
from p2p_engine.core.vertical_transition_impact import EvidenceCounts, SourceStateImpact
from p2p_engine.foundation.yaml_loaders import UNIQUE_LOADER_CONTRACT, load_yaml
from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.services.project_verticals import ProjectVerticalService


@dataclass(frozen=True)
class VerticalEvidenceSnapshot:
    definition: ProjectDefinitionState | None
    questions: ProjectQuestionArtifact | None
    rubrics: tuple[Mapping[str, object], ...]
    lock: VerticalLock | None
    resolved: ResolvedVerticalPack | None
    source_state: SourceStateImpact


class VerticalEvidenceClassifier:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        vertical_service: ProjectVerticalService,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.vertical_service = vertical_service

    def capture(self) -> VerticalEvidenceSnapshot:
        lock_status = self.vertical_service.vertical_lock_status()
        definition_path = self.p2p_dir / "project" / "definition.yml"
        if lock_status.status != "valid" and definition_path.exists():
            raise ValueError(
                "P2P_VERTICAL_SOURCE_LOCK_INVALID: current project vertical lock is not valid"
            )
        definition_view = self.vertical_service.project_definition_view()
        if definition_view.exists and (not definition_view.valid or definition_view.state is None):
            raise ValueError(
                "P2P_VERTICAL_SOURCE_STATE_INVALID: current project definition is invalid"
            )
        definition = definition_view.state
        if lock_status.status == "valid":
            lock = lock_status.locked
            resolved = lock_status.resolved
        else:
            lock = None
            resolved = None

        question_service = ProjectQuestionStateService(root=self.root, p2p_dir=self.p2p_dir)
        questions = question_service.read_optional()
        rubrics = self._read_rubrics()
        counts = EvidenceCounts(
            definition_fields=self._definition_field_count(definition),
            assumptions=sum(len(section.assumptions) for section in definition.sections) if definition else 0,
            blockers=sum(len(section.blockers) for section in definition.sections) if definition else 0,
            definition_orphans=len(definition.orphans) if definition else 0,
            owner_question_evidence=self._owner_question_evidence_count(questions),
            rubric_customizations=self._rubric_customization_count(rubrics, resolved),
        )
        return VerticalEvidenceSnapshot(
            definition=definition,
            questions=questions,
            rubrics=rubrics,
            lock=lock,
            resolved=resolved,
            source_state=SourceStateImpact(evidence=counts),
        )

    @staticmethod
    def _definition_field_count(state: ProjectDefinitionState | None) -> int:
        if state is None:
            return 0
        return sum(
            1
            for section in state.sections
            for field in section.fields.values()
            if _is_meaningful(field.value)
        )

    @staticmethod
    def _owner_question_evidence_count(artifact: ProjectQuestionArtifact | None) -> int:
        if artifact is None:
            return 0
        owner_states = {"answered", "applied", "deferred", "muted"}
        return sum(
            1
            for question in artifact.questions
            if question.answers or question.applications or question.state.value in owner_states
        )

    @staticmethod
    def _rubric_customization_count(
        criteria: tuple[Mapping[str, object], ...],
        resolved: ResolvedVerticalPack | None,
    ) -> int:
        if not criteria:
            return 0
        baseline = {
            rubric.rubric_id: {
                "title": rubric.title,
                "section_id": rubric.section_id,
                "required": rubric.required,
                "keywords": list(rubric.keywords),
                "enabled": True,
            }
            for rubric in resolved.pack.rubrics
        } if resolved is not None else {}
        customized = 0
        for item in criteria:
            rubric_id = str(item.get("id") or "")
            expected = baseline.get(rubric_id)
            if expected is None:
                customized += 1
                continue
            actual = {
                "title": str(item.get("title") or ""),
                "section_id": str(item.get("section_id") or ""),
                "required": item.get("required") is not False,
                "keywords": [str(value) for value in item.get("keywords", [])]
                if isinstance(item.get("keywords"), list)
                else [],
                "enabled": item.get("enabled") is not False,
            }
            if item.get("orphaned") is True or actual != expected:
                customized += 1
        return customized

    def _read_rubrics(self) -> tuple[Mapping[str, object], ...]:
        path = self.p2p_dir / "project" / "rubrics.yml"
        if not path.exists():
            raise ValueError("P2P_VERTICAL_SOURCE_RUBRICS_INVALID: rubric artifact is missing")
        try:
            payload = load_yaml(path.read_bytes(), loader_contract=UNIQUE_LOADER_CONTRACT)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"P2P_VERTICAL_SOURCE_RUBRICS_INVALID: {exc}") from exc
        if not isinstance(payload, Mapping) or not isinstance(payload.get("criteria"), list):
            raise ValueError("P2P_VERTICAL_SOURCE_RUBRICS_INVALID: criteria must be a sequence")
        criteria = payload["criteria"]
        assert isinstance(criteria, list)
        if any(not isinstance(item, Mapping) for item in criteria):
            raise ValueError("P2P_VERTICAL_SOURCE_RUBRICS_INVALID: criterion must be a mapping")
        return tuple(dict(item) for item in criteria if isinstance(item, Mapping))


def _is_meaningful(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True

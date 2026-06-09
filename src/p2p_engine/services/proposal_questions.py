from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from p2p_engine.core.proposal_questions import (
    ProposalQuestion,
    ProposalQuestionApplyPlanItem,
    ProposalQuestionApplySummary,
    ProposalQuestionGroup,
    ProposalQuestionOperation,
    ProposalQuestionPriority,
    ProposalQuestionState,
    ProposalQuestionStateView,
)
from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)

QUESTION_SCHEMA_VERSION = 1
QUESTION_STATE_FILENAME = "questions.yml"


class ProposalQuestionService:
    def __init__(self, *, root: Path, find_proposal_dir: Callable[[str], Path]) -> None:
        self.root = root
        self.find_proposal_dir = find_proposal_dir

    def read(self, proposal_id: str) -> ProposalQuestionStateView:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / QUESTION_STATE_FILENAME
        if not path.exists():
            return ProposalQuestionStateView(
                proposal_id=proposal_id,
                status="not_initialized",
                path=path.relative_to(self.root),
                schema_version=None,
                groups=[],
                questions=[],
            )
        payload = _read_yaml_mapping(path, default={})
        validate_proposal_questions_payload(payload)
        state = payload["proposal_questions"]
        groups = [_group_from_payload(item) for item in state.get("groups") or []]
        questions = [_question_from_payload(item) for item in state.get("questions") or []]
        return ProposalQuestionStateView(
            proposal_id=proposal_id,
            status="initialized",
            path=path.relative_to(self.root),
            schema_version=int(state["schema_version"]),
            groups=groups,
            questions=questions,
        )

    def initialize(self, proposal_id: str, *, actor: str = "local") -> ProposalQuestionStateView:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / QUESTION_STATE_FILENAME
        if path.exists():
            return self.read(proposal_id)
        today = date.today().isoformat()
        self._write_payload(
            path,
            {
                "proposal_questions": {
                    "schema_version": QUESTION_SCHEMA_VERSION,
                    "proposal_id": proposal_id,
                    "initialized_at": today,
                    "updated_at": today,
                    "updated_by": actor,
                    "groups": [],
                    "questions": [],
                }
            },
        )
        return self.read(proposal_id)

    def add(
        self,
        proposal_id: str,
        *,
        gap: str,
        question: str,
        priority: ProposalQuestionPriority = ProposalQuestionPriority.medium,
        rationale: str = "",
        group_id: str = "",
        actor: str = "local",
    ) -> ProposalQuestionOperation:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / QUESTION_STATE_FILENAME
        payload = self._payload_or_initialized(proposal_id, actor=actor)
        state = payload["proposal_questions"]
        questions = _question_payloads(state)
        groups = _group_payloads(state)
        today = date.today().isoformat()
        resolved_group_id = group_id or self._ensure_group(groups, gap=gap, priority=priority, rationale=rationale, today=today)
        question_id = _next_id("Q", [str(item.get("id") or "") for item in questions])
        item = {
            "id": question_id,
            "group_id": resolved_group_id,
            "gap": _required_text(gap, "gap"),
            "criterion": gap,
            "priority": priority.value,
            "state": ProposalQuestionState.to_answer.value,
            "question": _required_text(question, "question"),
            "rationale": rationale,
            "answer": "",
            "answer_source": "",
            "answered_at": "",
            "asked_count": 0,
            "last_asked_at": "",
            "derived_from": [],
            "superseded_by": "",
            "muted_reason": "",
            "deferred_reason": "",
            "applied_to_proposal": False,
            "applied_at": "",
            "audit": {
                "created_by": actor,
                "created_at": today,
                "updated_by": actor,
                "updated_at": today,
            },
        }
        questions.append(item)
        self._touch_and_write(path, payload, actor=actor)
        return ProposalQuestionOperation(
            proposal_id=proposal_id,
            path=path.relative_to(self.root),
            question=_question_from_payload(item),
            message="Question added.",
        )

    def answer(
        self,
        proposal_id: str,
        question_id: str,
        answer: str,
        *,
        source: str = "owner",
        actor: str = "local",
        replace: bool = False,
    ) -> ProposalQuestionOperation:
        payload, path, item = self._payload_and_question(proposal_id, question_id)
        if str(item.get("answer") or "").strip() and not replace:
            raise ValueError(f"Question already has an answer: {question_id}. Use replace=True or create a follow-up question.")
        today = date.today().isoformat()
        item["answer"] = _required_text(answer, "answer")
        item["answer_source"] = source
        item["answered_at"] = today
        item["state"] = ProposalQuestionState.answered.value
        _touch_item(item, actor=actor, today=today)
        self._touch_and_write(path, payload, actor=actor)
        return ProposalQuestionOperation(proposal_id, path.relative_to(self.root), _question_from_payload(item), "Question answered.")

    def set_state(
        self,
        proposal_id: str,
        question_id: str,
        state: ProposalQuestionState,
        *,
        reason: str = "",
        actor: str = "local",
    ) -> ProposalQuestionOperation:
        payload, path, item = self._payload_and_question(proposal_id, question_id)
        today = date.today().isoformat()
        item["state"] = state.value
        if state == ProposalQuestionState.defer:
            item["deferred_reason"] = reason
        if state == ProposalQuestionState.muted:
            item["muted_reason"] = reason
        if state == ProposalQuestionState.applied:
            item["applied_to_proposal"] = True
            item["applied_at"] = today
        _touch_item(item, actor=actor, today=today)
        self._touch_and_write(path, payload, actor=actor)
        return ProposalQuestionOperation(proposal_id, path.relative_to(self.root), _question_from_payload(item), f"Question state set to {state.value}.")

    def supersede(
        self,
        proposal_id: str,
        question_id: str,
        superseded_by: str,
        *,
        actor: str = "local",
    ) -> ProposalQuestionOperation:
        payload, path, item = self._payload_and_question(proposal_id, question_id)
        # Validate the replacement exists before mutating the old question.
        replacement = None
        for candidate in _question_payloads(payload["proposal_questions"]):
            if str(candidate.get("id") or "") == superseded_by:
                replacement = candidate
                break
        if replacement is None:
            raise ValueError(f"Superseding question not found for {proposal_id}: {superseded_by}")
        today = date.today().isoformat()
        item["state"] = ProposalQuestionState.superseded.value
        item["superseded_by"] = superseded_by
        derived_from = replacement.setdefault("derived_from", [])
        if isinstance(derived_from, list) and question_id not in derived_from:
            derived_from.append(question_id)
        _touch_item(item, actor=actor, today=today)
        _touch_item(replacement, actor=actor, today=today)
        self._touch_and_write(path, payload, actor=actor)
        return ProposalQuestionOperation(
            proposal_id,
            path.relative_to(self.root),
            _question_from_payload(item),
            f"Question superseded by {superseded_by}.",
        )

    def group_state(
        self,
        proposal_id: str,
        group_id: str,
        state: ProposalQuestionState,
        *,
        actor: str = "local",
    ) -> ProposalQuestionStateView:
        if state not in {ProposalQuestionState.to_answer, ProposalQuestionState.defer, ProposalQuestionState.muted}:
            raise ValueError("Group state must be one of: to_answer, defer, muted.")
        payload = self._payload_or_initialized(proposal_id, actor=actor)
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / QUESTION_STATE_FILENAME
        groups = _group_payloads(payload["proposal_questions"])
        matched = False
        today = date.today().isoformat()
        for group in groups:
            if str(group.get("id") or "") == group_id:
                group["state"] = state.value
                group["updated_at"] = today
                group["updated_by"] = actor
                matched = True
        if not matched:
            raise ValueError(f"Question group not found for {proposal_id}: {group_id}")
        self._touch_and_write(path, payload, actor=actor)
        return self.read(proposal_id)

    def next_question(self, proposal_id: str, *, include_muted: bool = False, include_deferred: bool = False) -> ProposalQuestion | None:
        view = self.read(proposal_id)
        group_states = {group.group_id: group.state for group in view.groups}
        candidates: list[ProposalQuestion] = []
        for question in view.questions:
            if question.state != ProposalQuestionState.to_answer:
                continue
            group_state = group_states.get(question.group_id)
            if group_state == ProposalQuestionState.muted and not include_muted:
                continue
            if group_state == ProposalQuestionState.defer and not include_deferred:
                continue
            candidates.append(question)
        if not candidates:
            return None
        priority_rank = {
            ProposalQuestionPriority.high: 0,
            ProposalQuestionPriority.medium: 1,
            ProposalQuestionPriority.low: 2,
        }
        return sorted(candidates, key=lambda item: (priority_rank[item.priority], item.question_id))[0]

    def reassess(self, proposal_id: str) -> ProposalQuestionStateView:
        # MVP reassessment is deterministic normalization: invalid stale records are
        # rejected by validation, and next-question selection derives from state.
        return self.read(proposal_id)

    def apply_summary(self, proposal_id: str, *, actor: str = "local") -> ProposalQuestionApplySummary:
        view = self.read(proposal_id)
        applicable = [question for question in view.questions if question.state == ProposalQuestionState.answered and question.answer.strip() and not question.applied_to_proposal]
        if not applicable:
            return ProposalQuestionApplySummary(
                proposal_id=proposal_id,
                path=view.path,
                applied_questions=[],
                update_plan=[],
                summary="No answered unapplied proposal questions.",
            )
        payload = self._payload_or_initialized(proposal_id, actor=actor)
        state = payload["proposal_questions"]
        questions_by_id = {str(item.get("id") or ""): item for item in _question_payloads(state)}
        update_plan: list[ProposalQuestionApplyPlanItem] = []
        today = date.today().isoformat()
        for question in applicable:
            plan = _apply_plan_for_question(question)
            item = questions_by_id[question.question_id]
            item["apply_plan"] = [
                {
                    "artifact": plan_item.artifact,
                    "action": plan_item.action,
                    "status": plan_item.status,
                    "reason": plan_item.reason,
                }
                for plan_item in plan
            ]
            item["state"] = ProposalQuestionState.applied.value
            item["applied_to_proposal"] = True
            item["applied_at"] = today
            _touch_item(item, actor=actor, today=today)
            update_plan.extend(plan)
        proposal_dir = self.find_proposal_dir(proposal_id)
        self._touch_and_write(proposal_dir / QUESTION_STATE_FILENAME, payload, actor=actor)
        lines = [
            "Answered proposal questions applied to artifact update plan:",
            *[f"- {question.question_id} ({question.gap}): {question.answer}" for question in applicable],
            "Artifact update plan:",
            *[f"- {item.artifact}: {item.action} [{item.status}] {item.reason}" for item in update_plan],
        ]
        return ProposalQuestionApplySummary(
            proposal_id=proposal_id,
            path=view.path,
            applied_questions=applicable,
            update_plan=update_plan,
            summary="\n".join(lines),
        )

    def import_payload(self, proposal_id: str, source: Path, *, actor: str = "local") -> ProposalQuestionStateView:
        self.find_proposal_dir(proposal_id)
        payload = _read_yaml_mapping(source, default={})
        validate_proposal_questions_payload(payload)
        state = payload["proposal_questions"]
        if str(state.get("proposal_id") or "") != proposal_id:
            raise ValueError(f"Question import proposal_id does not match target: {proposal_id}")
        path = self.find_proposal_dir(proposal_id) / QUESTION_STATE_FILENAME
        self._touch_and_write(path, payload, actor=actor)
        return self.read(proposal_id)

    def _payload_or_initialized(self, proposal_id: str, *, actor: str) -> dict[str, Any]:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / QUESTION_STATE_FILENAME
        if not path.exists():
            self.initialize(proposal_id, actor=actor)
        payload = _read_yaml_mapping(path, default={})
        validate_proposal_questions_payload(payload)
        return payload

    def _payload_and_question(self, proposal_id: str, question_id: str) -> tuple[dict[str, Any], Path, dict[str, Any]]:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / QUESTION_STATE_FILENAME
        if not path.exists():
            raise ValueError(f"No question state exists for proposal {proposal_id}. Run `p2p proposal questions init {proposal_id}`.")
        payload = _read_yaml_mapping(path, default={})
        validate_proposal_questions_payload(payload)
        for item in _question_payloads(payload["proposal_questions"]):
            if str(item.get("id") or "") == question_id:
                return payload, path, item
        raise ValueError(f"Question not found for {proposal_id}: {question_id}")

    def _ensure_group(
        self,
        groups: list[dict[str, Any]],
        *,
        gap: str,
        priority: ProposalQuestionPriority,
        rationale: str,
        today: str,
    ) -> str:
        for group in groups:
            if str(group.get("gap") or "") == gap and str(group.get("state") or "") in {"to_answer", "defer", "muted"}:
                return str(group["id"])
        group_id = _next_id("QG", [str(item.get("id") or "") for item in groups])
        groups.append(
            {
                "id": group_id,
                "gap": gap,
                "state": ProposalQuestionState.to_answer.value,
                "priority": priority.value,
                "rationale": rationale,
                "created_at": today,
                "updated_at": today,
            }
        )
        return group_id

    def _touch_and_write(self, path: Path, payload: dict[str, Any], *, actor: str) -> None:
        state = payload["proposal_questions"]
        state["updated_at"] = date.today().isoformat()
        state["updated_by"] = actor
        self._write_payload(path, payload)

    def _write_payload(self, path: Path, payload: dict[str, Any]) -> None:
        validate_proposal_questions_payload(payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(_yaml_dump(payload), encoding="utf-8")
        temp.replace(path)


def validate_proposal_questions_payload(data: dict[str, object]) -> None:
    state = data.get("proposal_questions")
    if not isinstance(state, dict):
        raise ValueError("Proposal questions must define top-level `proposal_questions` mapping.")
    if state.get("schema_version") != QUESTION_SCHEMA_VERSION:
        raise ValueError(f"Unsupported proposal questions schema_version: {state.get('schema_version')}")
    if not str(state.get("proposal_id") or "").strip():
        raise ValueError("Proposal questions missing proposal_id.")
    groups = state.get("groups", [])
    questions = state.get("questions", [])
    if not isinstance(groups, list):
        raise ValueError("Proposal questions groups must be a list.")
    if not isinstance(questions, list):
        raise ValueError("Proposal questions questions must be a list.")
    group_ids: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("Proposal question group must be a mapping.")
        group_id = str(group.get("id") or "").strip()
        if not group_id:
            raise ValueError("Proposal question group missing id.")
        if group_id in group_ids:
            raise ValueError(f"Duplicate proposal question group id: {group_id}")
        group_ids.add(group_id)
        _parse_state(group.get("state"), field=f"group {group_id} state")
        _parse_priority(group.get("priority"), field=f"group {group_id} priority")
    question_ids: set[str] = set()
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("Proposal question must be a mapping.")
        question_id = str(question.get("id") or "").strip()
        if not question_id:
            raise ValueError("Proposal question missing id.")
        if question_id in question_ids:
            raise ValueError(f"Duplicate proposal question id: {question_id}")
        question_ids.add(question_id)
        group_id = str(question.get("group_id") or "").strip()
        if group_id and group_id not in group_ids:
            raise ValueError(f"Proposal question {question_id} references unknown group: {group_id}")
        for field in ("gap", "criterion", "question"):
            if not str(question.get(field) or "").strip():
                raise ValueError(f"Proposal question {question_id} missing {field}.")
        _parse_state(question.get("state"), field=f"question {question_id} state")
        _parse_priority(question.get("priority"), field=f"question {question_id} priority")
        if not isinstance(question.get("derived_from", []), list):
            raise ValueError(f"Proposal question {question_id} derived_from must be a list.")
        if not isinstance(question.get("asked_count", 0), int) or int(question.get("asked_count", 0)) < 0:
            raise ValueError(f"Proposal question {question_id} asked_count must be a non-negative integer.")
        if not isinstance(question.get("applied_to_proposal", False), bool):
            raise ValueError(f"Proposal question {question_id} applied_to_proposal must be boolean.")
        apply_plan = question.get("apply_plan", [])
        if not isinstance(apply_plan, list):
            raise ValueError(f"Proposal question {question_id} apply_plan must be a list.")
        for plan_item in apply_plan:
            if not isinstance(plan_item, dict):
                raise ValueError(f"Proposal question {question_id} apply_plan item must be a mapping.")
            for field in ("artifact", "action", "status", "reason"):
                if not str(plan_item.get(field) or "").strip():
                    raise ValueError(f"Proposal question {question_id} apply_plan item missing {field}.")


def _group_payloads(state: dict[str, Any]) -> list[dict[str, Any]]:
    groups = state.setdefault("groups", [])
    if not isinstance(groups, list):
        raise ValueError("Proposal questions groups must be a list.")
    return groups


def _question_payloads(state: dict[str, Any]) -> list[dict[str, Any]]:
    questions = state.setdefault("questions", [])
    if not isinstance(questions, list):
        raise ValueError("Proposal questions questions must be a list.")
    return questions


def _group_from_payload(item: dict[str, Any]) -> ProposalQuestionGroup:
    return ProposalQuestionGroup(
        group_id=str(item.get("id") or ""),
        gap=str(item.get("gap") or ""),
        state=_parse_state(item.get("state"), field="group state"),
        priority=_parse_priority(item.get("priority"), field="group priority"),
        rationale=str(item.get("rationale") or ""),
    )


def _question_from_payload(item: dict[str, Any]) -> ProposalQuestion:
    audit = item.get("audit") if isinstance(item.get("audit"), dict) else {}
    return ProposalQuestion(
        question_id=str(item.get("id") or ""),
        group_id=str(item.get("group_id") or ""),
        gap=str(item.get("gap") or ""),
        criterion=str(item.get("criterion") or ""),
        priority=_parse_priority(item.get("priority"), field="question priority"),
        state=_parse_state(item.get("state"), field="question state"),
        question=str(item.get("question") or ""),
        rationale=str(item.get("rationale") or ""),
        answer=str(item.get("answer") or ""),
        answer_source=str(item.get("answer_source") or ""),
        answered_at=str(item.get("answered_at") or ""),
        asked_count=int(item.get("asked_count") or 0),
        last_asked_at=str(item.get("last_asked_at") or ""),
        derived_from=[str(value) for value in item.get("derived_from") or []],
        superseded_by=str(item.get("superseded_by") or ""),
        muted_reason=str(item.get("muted_reason") or ""),
        deferred_reason=str(item.get("deferred_reason") or ""),
        applied_to_proposal=bool(item.get("applied_to_proposal") or False),
        applied_at=str(item.get("applied_at") or ""),
        apply_plan=[
            ProposalQuestionApplyPlanItem(
                artifact=str(plan_item.get("artifact") or ""),
                action=str(plan_item.get("action") or ""),
                status=str(plan_item.get("status") or ""),
                reason=str(plan_item.get("reason") or ""),
            )
            for plan_item in item.get("apply_plan") or []
            if isinstance(plan_item, dict)
        ],
        created_by=str(audit.get("created_by") or ""),
        created_at=str(audit.get("created_at") or ""),
        updated_by=str(audit.get("updated_by") or ""),
        updated_at=str(audit.get("updated_at") or ""),
    )


def _touch_item(item: dict[str, Any], *, actor: str, today: str) -> None:
    audit = item.setdefault("audit", {})
    if isinstance(audit, dict):
        audit["updated_by"] = actor
        audit["updated_at"] = today


def _parse_state(value: object, *, field: str) -> ProposalQuestionState:
    try:
        return ProposalQuestionState(str(value or ProposalQuestionState.to_answer.value))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ProposalQuestionState)
        raise ValueError(f"Invalid proposal question {field}: {value}. Allowed: {allowed}") from exc


def _parse_priority(value: object, *, field: str) -> ProposalQuestionPriority:
    try:
        return ProposalQuestionPriority(str(value or ProposalQuestionPriority.medium.value))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ProposalQuestionPriority)
        raise ValueError(f"Invalid proposal question {field}: {value}. Allowed: {allowed}") from exc


def _required_text(value: str, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"Proposal question {field} is required.")
    return cleaned


def _apply_plan_for_question(question: ProposalQuestion) -> list[ProposalQuestionApplyPlanItem]:
    artifacts = _affected_artifacts(question)
    return [
        ProposalQuestionApplyPlanItem(
            artifact=artifact,
            action=_action_for_artifact(artifact),
            status="deferred",
            reason="Use the matching p2p update/import command to persist this answer into the artifact.",
        )
        for artifact in artifacts
    ]


def _affected_artifacts(question: ProposalQuestion) -> list[str]:
    text = " ".join([question.gap, question.criterion, question.question, question.answer]).lower()
    artifacts: list[str] = ["proposal.md"]
    mappings = [
        (("alternative", "alternatives"), "alternatives.md"),
        (("tradeoff", "finding", "findings"), "findings.md"),
        (("risk", "risks"), "risks.md"),
        (("assumption", "assumptions"), "assumptions.md"),
        (("question", "owner"), "open-questions.md"),
        (("scope", "non-goal", "goal"), "suggested-scope.md"),
        (("impact", "overlap", "duplicate", "aggregation", "merge"), "impact-map.yml"),
        (("acceptance", "criteria"), "proposal.md"),
        (("readiness", "confidence", "gate"), "readiness.yml"),
    ]
    for keywords, artifact in mappings:
        if any(keyword in text for keyword in keywords) and artifact not in artifacts:
            artifacts.append(artifact)
    return artifacts


def _action_for_artifact(artifact: str) -> str:
    actions = {
        "proposal.md": "update_proposal_sections",
        "alternatives.md": "import_exploration_artifact",
        "findings.md": "import_exploration_artifact",
        "risks.md": "import_exploration_artifact",
        "assumptions.md": "import_exploration_artifact",
        "open-questions.md": "import_exploration_artifact",
        "suggested-scope.md": "import_exploration_artifact",
        "impact-map.yml": "import_impact_artifact",
        "readiness.yml": "run_readiness_assess",
    }
    return actions.get(artifact, "review_artifact")


def _next_id(prefix: str, existing_ids: list[str]) -> str:
    max_id = 0
    for value in existing_ids:
        if value.startswith(prefix):
            suffix = value[len(prefix) :]
            if suffix.isdigit():
                max_id = max(max_id, int(suffix))
    return f"{prefix}{max_id + 1:03d}"

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from p2p_engine.core.decision_context import (
    Activation,
    Authority,
    DecisionContextIndex,
    NodeType,
    RecordKind,
    RelationType,
)
from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)


@dataclass(frozen=True)
class NextAction:
    action_id: str
    priority: str
    kind: str
    target: str
    reason: str
    command: str
    source: str


class NextActionService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        registry_status: Callable[[], Any],
        change_registry_records: Callable[[], list[dict[str, object]]],
        intake_statuses: Callable[[], list[Any]],
        proposal_summaries: Callable[..., list[Any]],
        read_proposal_readiness: Callable[[str], Any],
        decision_context_index: Callable[[], DecisionContextIndex],
        show_choice: Callable[[str], Any],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.registry_status = registry_status
        self.change_registry_records = change_registry_records
        self.intake_statuses = intake_statuses
        self.proposal_summaries = proposal_summaries
        self.read_proposal_readiness = read_proposal_readiness
        self.decision_context_index = decision_context_index
        self.show_choice = show_choice

    def list(
        self,
        limit: int | None = None,
        *,
        context_snapshot: Mapping[str, object] | None = None,
    ) -> list[NextAction]:
        index = self._index(context_snapshot)
        actions = self._dedupe(
            self._active_choice_blocker_actions(index)
            + self._active_curated_actions()
            + self._fallback_actions(context_snapshot, index)
        )
        if limit is not None:
            return actions[: max(limit, 0)]
        return actions

    def add(
        self,
        *,
        kind: str,
        target: str,
        reason: str,
        command: str = "",
        priority: str = "medium",
        action_id: str | None = None,
    ) -> NextAction:
        kind = kind.strip()
        if not kind:
            raise ValueError("Next action kind is required")
        reason = reason.strip()
        if not reason:
            raise ValueError("Next action reason is required")
        payload = self._read_payload()
        records = payload.setdefault("next_actions", [])
        if not isinstance(records, list):
            raise ValueError("Invalid next-actions.yml: next_actions must be a list")
        existing_ids = {
            str(record.get("id") or "")
            for record in records
            if isinstance(record, dict)
        }
        selected_id = action_id.strip() if action_id else self._next_curated_id(records)
        if selected_id in existing_ids:
            raise ValueError(f"Next action already exists: {selected_id}")
        record = {
            "id": selected_id,
            "priority": priority.strip() or "medium",
            "kind": kind,
            "target": target.strip(),
            "reason": reason,
            "command": command.strip(),
        }
        records.append(record)
        self._write_payload(payload)
        return self._from_record(record, self._path(), len(records))

    def complete(self, action_id: str, reason: str) -> dict[str, object]:
        return self._close(action_id, "completed", reason)

    def retire(self, action_id: str, reason: str) -> dict[str, object]:
        return self._close(action_id, "retired", reason)

    def refresh(self) -> dict[str, object]:
        payload = self._read_payload()
        records = payload.setdefault("next_actions", [])
        if not isinstance(records, list):
            raise ValueError("Invalid next-actions.yml: next_actions must be a list")
        normalized = [
            self._normalize_record(record, index)
            for index, record in enumerate(records, start=1)
            if isinstance(record, dict)
        ]
        payload["next_actions"] = normalized
        self._write_payload(payload)
        index = self.decision_context_index()
        generated = self._dedupe(
            self._active_choice_blocker_actions(index) + self._fallback_actions(None, index)
        )
        return {
            "active_curated": len(normalized),
            "generated": len(generated),
            "path": str(self._path().relative_to(self.root)),
        }

    def _active_curated_actions(self) -> list[NextAction]:
        path = self._path()
        if not path.exists():
            return []
        data = _read_yaml_mapping(path, default={"next_actions": []})
        records = data.get("next_actions", [])
        if not isinstance(records, list):
            return []
        actions: list[NextAction] = []
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                continue
            if str(record.get("status") or "active") != "active":
                continue
            actions.append(self._from_record(record, path, index))
        return actions

    def _path(self) -> Path:
        return self.p2p_dir / "project" / "next-actions.yml"

    def _log_path(self) -> Path:
        return self.p2p_dir / "project" / "next-actions-log.yml"

    def _read_payload(self) -> dict[str, object]:
        path = self._path()
        if not path.exists():
            return {"next_actions": []}
        return _read_yaml_mapping(path, default={"next_actions": []})

    def _write_payload(self, payload: dict[str, object]) -> None:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_yaml_dump(payload), encoding="utf-8")

    def _from_record(self, record: dict[str, object], path: Path, index: int) -> NextAction:
        return NextAction(
            action_id=str(record.get("id") or f"NEXT-{index:03d}"),
            priority=str(record.get("priority") or "medium"),
            kind=str(record.get("kind") or "other"),
            target=str(record.get("target") or ""),
            reason=str(record.get("reason") or ""),
            command=str(record.get("command") or ""),
            source=str(path.relative_to(self.root)),
        )

    def _normalize_record(self, record: dict[str, object], index: int) -> dict[str, object]:
        return {
            "id": str(record.get("id") or f"NEXT-{index:03d}"),
            "priority": str(record.get("priority") or "medium"),
            "kind": str(record.get("kind") or "other"),
            "target": str(record.get("target") or ""),
            "reason": str(record.get("reason") or ""),
            "command": str(record.get("command") or ""),
        }

    def _next_curated_id(self, records: list[object]) -> str:
        max_id = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            match = re.fullmatch(r"NEXT-(\d{3})", str(record.get("id") or ""))
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"NEXT-{max_id + 1:03d}"

    def _close(self, action_id: str, status: str, reason: str) -> dict[str, object]:
        action_id = action_id.strip()
        reason = reason.strip()
        if not action_id:
            raise ValueError("Next action ID is required")
        if not reason:
            raise ValueError("Next action close reason is required")
        payload = self._read_payload()
        records = payload.get("next_actions", [])
        if not isinstance(records, list):
            raise ValueError("Invalid next-actions.yml: next_actions must be a list")
        remaining: list[object] = []
        closed: dict[str, object] | None = None
        for index, record in enumerate(records, start=1):
            if isinstance(record, dict) and str(record.get("id") or f"NEXT-{index:03d}") == action_id:
                closed = self._normalize_record(record, index)
                continue
            remaining.append(record)
        if closed is None:
            raise ValueError(f"Next action not found: {action_id}")
        payload["next_actions"] = remaining
        self._write_payload(payload)

        log_path = self._log_path()
        log_payload = (
            _read_yaml_mapping(log_path, default={"next_action_log": []})
            if log_path.exists()
            else {"next_action_log": []}
        )
        log_records = log_payload.setdefault("next_action_log", [])
        if not isinstance(log_records, list):
            raise ValueError("Invalid next-actions-log.yml: next_action_log must be a list")
        entry = {
            **closed,
            "status": status,
            "closed_reason": reason,
            "closed_on": date.today().isoformat(),
        }
        log_records.append(entry)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(_yaml_dump(log_payload), encoding="utf-8")
        return {
            "action": entry,
            "path": str(log_path.relative_to(self.root)),
        }

    def _dedupe(self, actions: list[NextAction]) -> list[NextAction]:
        deduped: list[NextAction] = []
        seen: set[tuple[str, str]] = set()
        for action in actions:
            key = (action.kind, action.target)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(action)
        return deduped

    def _fallback_actions(
        self,
        context_snapshot: Mapping[str, object] | None = None,
        index: DecisionContextIndex | None = None,
    ) -> list[NextAction]:
        index = index or self._index(context_snapshot)
        actions: list[NextAction] = []
        registry_status = (
            context_snapshot.get("registry_status")
            if context_snapshot is not None
            else None
        ) or self.registry_status()
        if registry_status.stale:
            actions.append(
                NextAction(
                    action_id="NEXT-FALLBACK-001",
                    priority="high",
                    kind="refresh_registry",
                    target="registries",
                    reason="Generated registries are missing or stale.",
                    command="p2p registry refresh",
                    source="generated",
                )
            )

        terminal_change_statuses = {"completed", "cancelled", "superseded"}
        changes = (
            _snapshot_sequence(context_snapshot, "change_statuses")
            if context_snapshot is not None
            else self.change_registry_records()
        )
        change_nodes = {
            node.node_id for node in index.nodes if node.node_type == NodeType.CHANGE
        }
        included_proposals = _active_change_proposals(index)
        for change in changes:
            status = str(_field(change, "status") or "unknown")
            change_id = str(_field(change, "id", "change_id") or "")
            if status not in terminal_change_statuses and change_id in change_nodes:
                linked = included_proposals.get(change_id, ())
                relation_context = (
                    f" Included proposals: {', '.join(linked)}."
                    if linked
                    else ""
                )
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="high" if status in {"planned", "blocked"} else "medium",
                        kind="continue_change",
                        target=change_id,
                        reason=f"Change Set is {status}, not completed.{relation_context}",
                        command=f"p2p change tasks {change_id}",
                        source="generated",
                    )
                )
                break

        for intake in self.intake_statuses():
            if intake.status == "pending":
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="medium",
                        kind="inspect_intake",
                        target=intake.intake_id,
                        reason="Intake record is pending analysis.",
                        command="p2p intake status",
                        source="generated",
                    )
                )
                break

        draft_proposals = (
            [
                proposal
                for proposal in _snapshot_sequence(context_snapshot, "proposal_summaries")
                if str(_field(proposal, "status") or "") == "draft"
            ]
            if context_snapshot is not None
            else self.proposal_summaries(status="draft")
        )
        for proposal in draft_proposals:
            readiness = self.read_proposal_readiness(proposal.proposal_id)
            if readiness.status == "not_assessed":
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="high",
                        kind="assess_proposal_readiness",
                        target=proposal.proposal_id,
                        reason="Draft proposal has no readiness assessment.",
                        command=f"p2p proposal readiness refresh {proposal.proposal_id}",
                        source="generated",
                    )
                )
                break
            if readiness.computed_score is not None and readiness.computed_score < 85:
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="medium",
                        kind="improve_proposal_readiness",
                        target=proposal.proposal_id,
                        reason=(
                            f"Draft proposal readiness is {readiness.computed_score}, "
                            "below the default strong threshold."
                        ),
                        command=f"p2p proposal readiness explain {proposal.proposal_id}",
                        source="generated",
                    )
                )
                break

        for proposal in draft_proposals:
            has_readiness_action = any(
                action.target == proposal.proposal_id
                and action.kind in {"assess_proposal_readiness", "improve_proposal_readiness"}
                for action in actions
            )
            if has_readiness_action:
                continue
            actions.append(
                NextAction(
                    action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                    priority="medium",
                    kind="review_draft_proposal",
                    target=proposal.proposal_id,
                    reason="Draft proposal exists and has no owner decision yet.",
                    command=f"p2p proposal show {proposal.proposal_id}",
                    source="generated",
                )
            )
            break

        blocked_choices = {
            relation.source_id
            for relation in index.relations
            if relation.source_type == NodeType.CHOICE
            and relation.relation_type == RelationType.BLOCKS
            and relation.activation == Activation.ACTIVE
        }
        for choice_id in _open_project_choice_ids(index):
            if choice_id in blocked_choices:
                continue
            actions.append(
                NextAction(
                    action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                    priority="medium",
                    kind="resolve_choice",
                    target=choice_id,
                    reason="Project choice is open and has no selected option.",
                    command=f"p2p choice show {choice_id}",
                    source="generated",
                )
            )
            break

        if not actions:
            actions.append(
                NextAction(
                    action_id="NEXT-FALLBACK-001",
                    priority="low",
                    kind="review_project",
                    target="project",
                    reason="No stored next actions or obvious fallback actions were found.",
                    command="p2p project status",
                    source="generated",
                )
            )
        return actions

    def _active_choice_blocker_actions(
        self,
        index: DecisionContextIndex,
    ) -> list[NextAction]:
        actions: list[NextAction] = []
        open_choices = set(_open_project_choice_ids(index))
        evidence_map = index.evidence_map()
        relations = sorted(
            (
                relation
                for relation in index.relations
                if relation.source_type == NodeType.CHOICE
                and relation.source_id in open_choices
                and relation.relation_type == RelationType.BLOCKS
                and relation.activation == Activation.ACTIVE
            ),
            key=lambda item: (item.source_id, item.target_type.value, item.target_id),
        )
        for relation in relations:
            detail = self.show_choice(relation.source_id)
            block = next(
                (
                    item
                    for item in detail.blocks
                    if isinstance(item, dict)
                    and str(item.get("target") or "") == relation.target_id
                    and str(item.get("target_type") or "") == relation.target_type.value
                    and item.get("status", "active") == "active"
                ),
                {},
            )
            source = "generated"
            for evidence_id in relation.evidence_ids:
                evidence = evidence_map.get(evidence_id)
                if evidence is not None:
                    source = evidence.source_path
                    break
            actions.append(
                NextAction(
                    action_id=f"NEXT-BLOCKER-{len(actions) + 1:03d}",
                    priority="high",
                    kind="resolve_choice",
                    target=relation.source_id,
                    reason=(
                        f"{relation.source_id} blocks {relation.target_type.value} "
                        f"{relation.target_id}: {block.get('reason') or 'Decision required.'}"
                    ),
                    command=f"p2p choice show {relation.source_id}",
                    source=source,
                )
            )
        return actions

    def _index(
        self,
        context_snapshot: Mapping[str, object] | None,
    ) -> DecisionContextIndex:
        if context_snapshot is not None:
            value = context_snapshot.get("decision_context_index")
            if isinstance(value, DecisionContextIndex):
                return value
        return self.decision_context_index()


def _snapshot_sequence(
    snapshot: Mapping[str, object] | None,
    key: str,
) -> list[Any]:
    value = snapshot.get(key, ()) if snapshot is not None else ()
    return list(value) if isinstance(value, (tuple, list)) else []


def _field(value: object, *names: str) -> object:
    for name in names:
        if isinstance(value, Mapping):
            if name in value:
                return value[name]
        elif hasattr(value, name):
            return getattr(value, name)
    return None


def _open_project_choice_ids(index: DecisionContextIndex) -> tuple[str, ...]:
    choices = sorted(
        node.node_id for node in index.nodes if node.node_type == NodeType.CHOICE
    )
    decided = {
        record.owner_id
        for record in index.records
        if record.owner_type == NodeType.CHOICE
        and record.kind == RecordKind.DECISION_STATE
        and record.authority == Authority.DECIDED_PROJECT_CHOICE
        and record.activation == Activation.ACTIVE
    }
    return tuple(choice_id for choice_id in choices if choice_id not in decided)


def _active_change_proposals(
    index: DecisionContextIndex,
) -> dict[str, tuple[str, ...]]:
    related: dict[str, set[str]] = {}
    for relation in index.relations:
        if (
            relation.source_type == NodeType.CHANGE
            and relation.target_type == NodeType.PROPOSAL
            and relation.relation_type == RelationType.INCLUDES
            and relation.activation == Activation.ACTIVE
        ):
            related.setdefault(relation.source_id, set()).add(relation.target_id)
    return {
        change_id: tuple(sorted(proposals))
        for change_id, proposals in sorted(related.items())
    }

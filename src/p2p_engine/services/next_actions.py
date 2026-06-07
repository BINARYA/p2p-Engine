from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

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
        choice_registry_records: Callable[[], list[dict[str, object]]],
        choice_statuses: Callable[[], list[Any]],
        show_choice: Callable[[str], Any],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.registry_status = registry_status
        self.change_registry_records = change_registry_records
        self.intake_statuses = intake_statuses
        self.proposal_summaries = proposal_summaries
        self.read_proposal_readiness = read_proposal_readiness
        self.choice_registry_records = choice_registry_records
        self.choice_statuses = choice_statuses
        self.show_choice = show_choice

    def list(self, limit: int | None = None) -> list[NextAction]:
        actions = self._dedupe(
            self._active_choice_blocker_actions()
            + self._active_curated_actions()
            + self._fallback_actions()
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
        generated = self._dedupe(self._active_choice_blocker_actions() + self._fallback_actions())
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

    def _fallback_actions(self) -> list[NextAction]:
        actions: list[NextAction] = []
        registry_status = self.registry_status()
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
        for change in self.change_registry_records():
            status = str(change.get("status") or "unknown")
            if status not in terminal_change_statuses:
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="high" if status in {"planned", "blocked"} else "medium",
                        kind="continue_change",
                        target=str(change.get("id") or ""),
                        reason=f"Change Set is {status}, not completed.",
                        command=f"p2p change tasks {change.get('id')}",
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

        for proposal in self.proposal_summaries(status="draft"):
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

        for proposal in self.proposal_summaries(status="draft"):
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

        for choice in self.choice_registry_records():
            status = str(choice.get("status") or "unknown")
            selected = choice.get("selected_option")
            if status in {"open", "draft", "pending"} and not selected:
                actions.append(
                    NextAction(
                        action_id=f"NEXT-FALLBACK-{len(actions) + 1:03d}",
                        priority="medium",
                        kind="resolve_choice",
                        target=str(choice.get("id") or choice.get("proposal") or ""),
                        reason=f"Choice is {status} and has no selected option.",
                        command="p2p registry show choices",
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

    def _active_choice_blocker_actions(self) -> list[NextAction]:
        actions: list[NextAction] = []
        for choice in self.choice_statuses():
            if choice.status == "decided":
                continue
            detail = self.show_choice(choice.choice_id)
            for block in detail.blocks:
                if not isinstance(block, dict) or block.get("status", "active") != "active":
                    continue
                target = str(block.get("target") or "")
                target_type = str(block.get("target_type") or "target")
                actions.append(
                    NextAction(
                        action_id=f"NEXT-BLOCKER-{len(actions) + 1:03d}",
                        priority="high",
                        kind="resolve_choice",
                        target=choice.choice_id,
                        reason=(
                            f"{choice.choice_id} blocks {target_type} {target}: "
                            f"{block.get('reason') or 'Decision required.'}"
                        ),
                        command=f"p2p choice show {choice.choice_id}",
                        source=str(detail.path / "links.yml"),
                    )
                )
        return actions

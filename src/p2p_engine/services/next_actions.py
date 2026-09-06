from __future__ import annotations

import inspect
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, TypeVar

from p2p_engine.core.choices import is_active_choice_state
from p2p_engine.core.decision_context import (
    Activation,
    Authority,
    DecisionContextIndex,
    NodeType,
    RecordKind,
    RelationType,
)
from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.project_readiness import ProjectReadinessGapKind, ProjectReadinessResult
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionDependencyKind,
    ProposalDecisionDependencyStatus,
    ProposalDecisionEventType,
    ProposalDecisionImpactSeverity,
    ProposalDecisionImpactSnapshot,
    ProposalDecisionLifecycleView,
)
from p2p_engine.core.vertical_memory import VerticalProjectMemoryView
from p2p_engine.foundation.files import (
    read_yaml_mapping as _read_yaml_mapping,
)
from p2p_engine.foundation.files import (
    yaml_dump as _yaml_dump,
)
from p2p_engine.services.changes import (
    CHANGE_TERMINAL_STATUSES,
    change_next_action_status_rank,
)
from p2p_engine.services.workspace_reads import WorkspaceReadContext

_T = TypeVar("_T")


def _provide(
    context: WorkspaceReadContext | None,
    name: str,
    arguments: Sequence[object],
    factory: Callable[[], _T],
) -> _T:
    if context is None:
        return factory()
    return context.provide(name, arguments, factory)


def _call_with_read_context(
    provider: Callable[..., _T],
    context: WorkspaceReadContext | None,
) -> _T:
    if context is not None and "read_context" in inspect.signature(provider).parameters:
        return provider(read_context=context)
    return provider()

_REMEDIATION_EVENT_TYPES = frozenset(
    {
        ProposalDecisionEventType.revoked,
        ProposalDecisionEventType.superseded,
        ProposalDecisionEventType.split,
        ProposalDecisionEventType.merged_into_other,
        ProposalDecisionEventType.reinstated,
    }
)
_REMEDIATION_KIND_RANK = {
    kind: index
    for index, kind in enumerate(ProposalDecisionDependencyKind)
}
_REMEDIATION_STATUS_RANK = {
    ProposalDecisionDependencyStatus.active: 0,
    ProposalDecisionDependencyStatus.current: 1,
    ProposalDecisionDependencyStatus.completed: 2,
    ProposalDecisionDependencyStatus.generated: 3,
    ProposalDecisionDependencyStatus.stale: 4,
    ProposalDecisionDependencyStatus.unknown: 5,
    ProposalDecisionDependencyStatus.historical: 6,
    ProposalDecisionDependencyStatus.terminal: 7,
}


@dataclass(frozen=True)
class NextAction:
    action_id: str
    priority: str
    kind: str
    target: str
    reason: str
    command: str
    source: str


@dataclass(frozen=True)
class NextActionInputs:
    schema_preflight: object | None
    registry_status: object
    vertical_memory_status: object | None
    vertical_memory: VerticalProjectMemoryView | None
    readiness: ProjectReadinessResult | None
    proposal_lifecycles: Mapping[str, ProposalDecisionLifecycleView]
    proposal_summaries: tuple[object, ...]
    choice_statuses: tuple[object, ...]
    change_statuses: tuple[object, ...]
    intake_statuses: tuple[object, ...]
    decision_context: DecisionContextIndex | None = None
    fast_freshness: object | None = None

    def to_snapshot(self) -> dict[str, object]:
        return {
            "workspace_schema_status": self.schema_preflight,
            "registry_status": self.registry_status,
            "vertical_memory_status": self.vertical_memory_status,
            "vertical_memory": self.vertical_memory,
            "project_readiness_result": self.readiness,
            "proposal_decision_lifecycles": self.proposal_lifecycles,
            "proposal_summaries": self.proposal_summaries,
            "choice_statuses": self.choice_statuses,
            "change_statuses": self.change_statuses,
            "intake_statuses": self.intake_statuses,
            "decision_context_index": self.decision_context,
            "derived_freshness_status": self.fast_freshness,
        }


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
        choice_statuses: Callable[[], list[Any]] | None = None,
        workspace_schema_status: Callable[[], Any] | None = None,
        workspace_schema_preflight: Callable[[], Any] | None = None,
        derived_freshness_status: Callable[..., Any] | None = None,
        fast_freshness_status: Callable[..., Any] | None = None,
        project_readiness_result: Callable[[], ProjectReadinessResult] | None = None,
        proposal_decision_lifecycles: (
            Callable[..., Mapping[str, ProposalDecisionLifecycleView]] | None
        ) = None,
        proposal_decision_impact: (
            Callable[
                [
                    str,
                    ProposalDecisionEventType,
                    ProposalDecisionLifecycleView,
                    object | None,
                ],
                ProposalDecisionImpactSnapshot,
            ]
            | None
        ) = None,
        vertical_memory_status: Callable[..., object] | None = None,
        vertical_memory_view: Callable[..., VerticalProjectMemoryView] | None = None,
        readiness_from_vertical_memory: (
            Callable[..., ProjectReadinessResult]
            | None
        ) = None,
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
        self.choice_statuses = choice_statuses
        self.workspace_schema_status = workspace_schema_status
        self.workspace_schema_preflight = workspace_schema_preflight
        self.derived_freshness_status = derived_freshness_status
        self.fast_freshness_status = fast_freshness_status
        self.project_readiness_result = project_readiness_result
        self.proposal_decision_lifecycles = proposal_decision_lifecycles
        self.proposal_decision_impact = proposal_decision_impact
        self.vertical_memory_status = vertical_memory_status
        self.vertical_memory_view = vertical_memory_view
        self.readiness_from_vertical_memory = readiness_from_vertical_memory

    def list(
        self,
        limit: int | None = None,
        *,
        context_snapshot: Mapping[str, object] | None = None,
        read_context: WorkspaceReadContext | None = None,
    ) -> list[NextAction]:
        if context_snapshot is None:
            context_snapshot = self._assemble_inputs(read_context).to_snapshot()
        index = self._index(context_snapshot, allow_build=False)
        freshness = self._freshness(context_snapshot, index)
        actions = self._dedupe(
            self._workspace_alignment_actions(context_snapshot, freshness)
            + self._active_choice_blocker_actions(index, context_snapshot)
            + self._active_curated_actions()
            + self._decision_remediation_actions(freshness, context_snapshot)
            + self._project_readiness_actions(context_snapshot)
            + self._fallback_actions(context_snapshot, index)
        )
        if limit is not None:
            return actions[: max(limit, 0)]
        return actions

    def _assemble_inputs(
        self,
        read_context: WorkspaceReadContext | None = None,
    ) -> NextActionInputs:
        schema = (
            _provide(
                read_context,
                "schema_preflight",
                (),
                self.workspace_schema_preflight,
            )
            if self.workspace_schema_preflight is not None
            else _provide(
                read_context,
                "schema_deep_status",
                (),
                self.workspace_schema_status,
            )
            if self.workspace_schema_status is not None
            else None
        )
        registry = _provide(
            read_context,
            "registry_status",
            (),
            lambda: self.registry_status(read_context=read_context)
            if read_context is not None
            else self.registry_status(),
        )
        memory_status = (
            _provide(
                read_context,
                "vertical_memory_status",
                (),
                lambda: self.vertical_memory_status(read_context=read_context),
            )
            if self.vertical_memory_status is not None
            else None
        )
        memory: VerticalProjectMemoryView | None = None
        if self.vertical_memory_view is not None:
            try:
                memory = _provide(
                    read_context,
                    "vertical_memory",
                    (True, False),
                    lambda: self.vertical_memory_view(read_context=read_context),
                )
            except ValueError:
                memory = None
        proposals = _provide(
            read_context,
            "proposal_summaries",
            (),
            lambda: tuple(
                _call_with_read_context(self.proposal_summaries, read_context)
            ),
        )
        readiness = (
            _provide(
                read_context,
                "project_readiness",
                (memory.source_fingerprint_sha256,),
                lambda: self.readiness_from_vertical_memory(
                    memory,
                    proposals,
                    read_context=read_context,
                ),
            )
            if memory is not None and self.readiness_from_vertical_memory is not None
            else _provide(
                read_context,
                "project_readiness",
                (),
                self.project_readiness_result,
            )
            if memory is not None and self.project_readiness_result is not None
            else None
        )
        lifecycles = (
            self.proposal_decision_lifecycles(read_context=read_context)
            if self.proposal_decision_lifecycles is not None
            else {}
        )
        fast_freshness = (
            _provide(
                read_context,
                "fast_freshness",
                (),
                lambda: self.fast_freshness_status(read_context=read_context),
            )
            if self.fast_freshness_status is not None
            else None
        )
        return NextActionInputs(
            schema_preflight=schema,
            registry_status=registry,
            vertical_memory_status=memory_status,
            vertical_memory=memory,
            readiness=readiness,
            proposal_lifecycles=lifecycles,
            proposal_summaries=proposals,
            choice_statuses=_provide(
                read_context,
                "choice_statuses",
                (),
                lambda: tuple(self.choice_statuses() if self.choice_statuses else ()),
            ),
            change_statuses=_provide(
                read_context,
                "change_statuses",
                (),
                lambda: tuple(self.change_registry_records()),
            ),
            intake_statuses=_provide(
                read_context,
                "intake_statuses",
                (),
                lambda: tuple(self.intake_statuses()),
            ),
            fast_freshness=fast_freshness,
        )

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
        generated = self._generated_actions(None, index)
        return {
            "active_curated": len(normalized),
            "generated": len(generated),
            "path": str(self._path().relative_to(self.root)),
        }

    def _generated_actions(
        self,
        context_snapshot: Mapping[str, object] | None,
        index: DecisionContextIndex | None,
    ) -> list[NextAction]:
        freshness = self._freshness(context_snapshot, index)
        return self._dedupe(
            self._workspace_alignment_actions(context_snapshot, freshness)
            + self._active_choice_blocker_actions(index, context_snapshot)
            + self._decision_remediation_actions(freshness, context_snapshot)
            + self._project_readiness_actions(context_snapshot)
            + self._fallback_actions(context_snapshot, index)
        )

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

    def _decision_remediation_actions(
        self,
        freshness_status_snapshot: object | None,
        context_snapshot: Mapping[str, object] | None = None,
    ) -> list[NextAction]:
        if (
            self.proposal_decision_lifecycles is None
            or self.proposal_decision_impact is None
        ):
            return []
        ranked: list[tuple[int, int, str, NextAction]] = []
        lifecycle_snapshot = (
            context_snapshot.get("proposal_decision_lifecycles")
            if context_snapshot is not None
            else None
        )
        lifecycles = (
            lifecycle_snapshot
            if isinstance(lifecycle_snapshot, Mapping)
            else self.proposal_decision_lifecycles()
        )
        decision_freshness = (
            freshness_status_snapshot
            if hasattr(freshness_status_snapshot, "nodes")
            else None
        )
        for proposal_id, lifecycle in sorted(lifecycles.items()):
            event_type = lifecycle.head_event_type
            head_event_id = lifecycle.head_event_id
            if event_type not in _REMEDIATION_EVENT_TYPES or not head_event_id:
                continue
            snapshot = self.proposal_decision_impact(
                proposal_id,
                event_type,
                lifecycle,
                decision_freshness,
            )
            if not snapshot.complete:
                continue
            for item in snapshot.items:
                if item.dependency_status in {
                    ProposalDecisionDependencyStatus.terminal,
                    ProposalDecisionDependencyStatus.historical,
                }:
                    continue
                identity = semantic_sha256(
                    {
                        "proposal_id": proposal_id,
                        "head_event_id": head_event_id,
                        "dependency_kind": item.dependency_kind.value,
                        "dependency_id": item.dependency_id,
                    }
                )
                state = (
                    "reinstated"
                    if event_type == ProposalDecisionEventType.reinstated
                    else "revoked"
                    if event_type == ProposalDecisionEventType.revoked
                    else "replaced"
                )
                action = NextAction(
                    action_id=f"NEXT-DECISION-{identity[:24].upper()}",
                    priority=_impact_priority(item.severity),
                    kind=item.remediation_kind,
                    target=item.dependency_id,
                    reason=(
                        f"Source decision {proposal_id} is {state}; dependent "
                        f"{item.dependency_kind.value} {item.dependency_id} "
                        "requires separate review. No rollback or technical "
                        "restoration is implied."
                    ),
                    command=item.remediation_command,
                    source=f"generated:{proposal_id}:{head_event_id}",
                )
                ranked.append(
                    (
                        _REMEDIATION_KIND_RANK[item.dependency_kind],
                        _REMEDIATION_STATUS_RANK[item.dependency_status],
                        action.action_id,
                        action,
                    )
                )
        return [entry[-1] for entry in sorted(ranked)]

    def _workspace_alignment_actions(
        self,
        context_snapshot: Mapping[str, object] | None,
        freshness_status_snapshot: object | None,
    ) -> list[NextAction]:
        schema = (
            context_snapshot.get("workspace_schema_status")
            if context_snapshot is not None
            else None
        )
        if schema is None and self.workspace_schema_preflight is not None:
            schema = self.workspace_schema_preflight()
        elif schema is None and self.workspace_schema_status is not None:
            schema = self.workspace_schema_status()
        if schema is not None:
            recovery = getattr(schema, "recovery", {})
            recovery_required = bool(getattr(schema, "recovery_required", False)) or (
                isinstance(recovery, Mapping) and bool(recovery.get("required", False))
            )
            if recovery_required:
                return [
                    NextAction(
                        action_id="NEXT-WORKSPACE-RECOVERY",
                        priority="critical",
                        kind="recover_workspace_transaction",
                        target=str(recovery.get("transaction_id") or "workspace"),
                        reason="An interrupted workspace transaction requires recovery before governed writes.",
                        command="p2p workspace transaction status",
                        source="generated",
                    )
                ]
            if getattr(schema, "layout_status", "unsupported") != "current":
                return [
                    NextAction(
                        action_id="NEXT-WORKSPACE-SCHEMA-UNSUPPORTED",
                        priority="critical",
                        kind="inspect_unsupported_workspace_schema",
                        target="workspace",
                        reason=(
                            "This runtime supports workspace schema v4 only and cannot convert "
                            "the detected workspace."
                        ),
                        command="p2p workspace schema status --format json",
                        source="generated",
                    )
                ]

        memory_status = (
            context_snapshot.get("vertical_memory_status")
            if context_snapshot is not None
            else None
        )
        memory_available = (
            context_snapshot is not None
            and isinstance(context_snapshot.get("vertical_memory"), VerticalProjectMemoryView)
        )
        if (
            memory_status is not None
            and str(getattr(memory_status, "state", "unknown")) != "current"
            and not memory_available
        ):
            state = str(getattr(memory_status, "state", "unknown"))
            return [
                NextAction(
                    action_id="NEXT-VERTICAL-PROJECT-MEMORY",
                    priority="high" if state in {"stale", "invalid", "unsupported"} else "medium",
                    kind="refresh_project_memory",
                    target="vertical_project_memory",
                    reason=(
                        f"Vertical project memory is {state}; current consumers are using "
                        "canonical fallback or cannot obtain structured project state."
                    ),
                    command="p2p project refresh",
                    source="generated",
                )
            ]

        freshness = freshness_status_snapshot
        if freshness is None or str(getattr(freshness, "status", "")) == "current":
            return []
        fast_attention = tuple(getattr(freshness, "attention", ()))
        registry = (
            context_snapshot.get("registry_status")
            if context_snapshot is not None
            else None
        )
        registry_current = str(getattr(registry, "state", "unknown")) == "current"
        fast_next_node = ""
        fast_next_command = ""
        if registry_current and str(
            getattr(freshness, "project_projection_state", "unknown")
        ) != "current_basis":
            fast_next_node = "project_projections"
            fast_next_command = "p2p project refresh"
        elif (
            registry_current
            and str(getattr(memory_status, "state", "unknown")) == "current"
            and "assessment" in fast_attention
        ):
            fast_next_node = "assessment"
            fast_next_command = "p2p assess refresh"
        if fast_next_node:
            return [
                NextAction(
                    action_id="NEXT-DERIVED-FRESHNESS",
                    priority="high",
                    kind="refresh_derived_state",
                    target=fast_next_node,
                    reason="Derived project state is stale or incomplete according to fast freshness checks.",
                    command=fast_next_command,
                    source="generated",
                )
            ]
        rebuild = tuple(getattr(freshness, "rebuild_plan", ()))
        actionable = next(
            (
                item
                for item in rebuild
                if str(getattr(item, "node_id", "")) != "registries"
                if not tuple(getattr(item, "blocked_by", ()))
                and str(getattr(item, "command", "")).strip()
            ),
            None,
        )
        if actionable is None:
            return []
        action_class = str(getattr(actionable, "action_class", ""))
        return [
            NextAction(
                action_id="NEXT-DERIVED-FRESHNESS",
                priority="high" if action_class == "deterministic" else "medium",
                kind="refresh_derived_state" if action_class == "deterministic" else "review_derived_state",
                target=str(getattr(actionable, "node_id", "derived-state")),
                reason="Derived project state is stale or incomplete according to the freshness graph.",
                command=str(getattr(actionable, "command", "")),
                source="generated",
            )
        ]

    def _fallback_actions(
        self,
        context_snapshot: Mapping[str, object] | None = None,
        index: DecisionContextIndex | None = None,
    ) -> list[NextAction]:
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

        changes = (
            _snapshot_sequence(context_snapshot, "change_statuses")
            if context_snapshot is not None
            else self.change_registry_records()
        )
        included_proposals = _active_change_proposals(index) if index is not None else {}
        active_changes: list[tuple[int, str, str]] = []
        for change in changes:
            status = str(_field(change, "status") or "unknown").strip().lower()
            change_id = str(_field(change, "id", "change_id") or "").strip()
            if not change_id or status in CHANGE_TERMINAL_STATUSES:
                continue
            active_changes.append(
                (
                    change_next_action_status_rank(status),
                    change_id,
                    status,
                )
            )
            if index is None:
                included = _field(change, "included_proposals")
                if isinstance(included, (tuple, list)):
                    included_proposals[change_id] = tuple(
                        sorted({str(item) for item in included if str(item)})
                    )
        for _, change_id, status in sorted(
            active_changes,
            key=lambda item: (item[0], item[1]),
        ):
            linked = included_proposals.get(change_id, ())
            relation_context = (
                f" Included proposals: {', '.join(linked)}."
                if linked
                else ""
            )
            actions.append(
                NextAction(
                    action_id=f"NEXT-CHANGE-{change_id.upper()}",
                    priority="high" if status in {"planned", "blocked"} else "medium",
                    kind="continue_change",
                    target=change_id,
                    reason=f"Change Set is {status}, not completed.{relation_context}",
                    command=f"p2p change tasks {change_id}",
                    source="generated",
                )
            )

        intakes = (
            _snapshot_sequence(context_snapshot, "intake_statuses")
            if context_snapshot is not None
            else self.intake_statuses()
        )
        for intake in intakes:
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

        if index is not None:
            blocked_choices = {
                relation.source_id
                for relation in index.relations
                if relation.source_type == NodeType.CHOICE
                and relation.relation_type == RelationType.BLOCKS
                and relation.activation == Activation.ACTIVE
            }
            open_choice_ids = _open_project_choice_ids(index)
        else:
            blocked_choices = set()
            statuses = (
                _snapshot_sequence(context_snapshot, "choice_statuses")
                if context_snapshot is not None
                else self.choice_statuses()
                if self.choice_statuses is not None
                else []
            )
            open_choice_ids = tuple(
                sorted(
                    str(_field(item, "choice_id") or "")
                    for item in statuses
                    if str(_field(item, "choice_id") or "")
                    and not _field(item, "selected_option")
                    and is_active_choice_state(_field(item, "status"))
                )
            )
        for choice_id in open_choice_ids:
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

    def _project_readiness_actions(
        self,
        context_snapshot: Mapping[str, object] | None,
    ) -> list[NextAction]:
        result = (
            context_snapshot.get("project_readiness_result")
            if context_snapshot is not None
            else None
        )
        if result is None and self.project_readiness_result is not None:
            result = self.project_readiness_result()
        if not isinstance(result, ProjectReadinessResult):
            return []
        actions: list[NextAction] = []
        ordered_gaps = sorted(
            result.gaps,
            key=lambda gap: (0 if gap.question_id else 1, *gap.tie_break),
        )
        for gap in ordered_gaps:
            if gap.kind == ProjectReadinessGapKind.UNMAPPED_PROPOSAL_COVERAGE:
                continue
            if gap.kind == ProjectReadinessGapKind.COMPATIBILITY_BLOCKER:
                kind = (
                    "project_schema_recreation"
                    if gap.target_kind == "workspace_schema"
                    else "project_question_reconcile"
                )
            elif gap.kind == ProjectReadinessGapKind.ANSWERED_NOT_APPLIED:
                kind = "project_question_apply"
            elif gap.question_id:
                kind = "project_question_answer"
            else:
                kind = "project_definition_gap"
            target = gap.question_id or gap.gap_id
            actions.append(
                NextAction(
                    action_id=f"NEXT-READINESS-{gap.gap_id.removeprefix('PGAP-').upper()}",
                    priority=(
                        "critical"
                        if gap.severity.value == "blocker"
                        else "high"
                        if gap.severity.value == "high"
                        else "medium"
                    ),
                    kind=kind,
                    target=target,
                    reason=gap.rationale,
                    command=gap.next_operation,
                    source="project_readiness",
                )
            )
            if len(actions) >= 10:
                break
        return actions

    def _active_choice_blocker_actions(
        self,
        index: DecisionContextIndex | None,
        context_snapshot: Mapping[str, object] | None = None,
    ) -> list[NextAction]:
        if index is None:
            statuses = (
                _snapshot_sequence(context_snapshot, "choice_statuses")
                if context_snapshot is not None
                else self.choice_statuses()
                if self.choice_statuses is not None
                else []
            )
            actions: list[NextAction] = []
            for status in sorted(statuses, key=lambda item: str(_field(item, "choice_id") or "")):
                choice_id = str(_field(status, "choice_id") or "")
                selected = _field(status, "selected_option")
                if not choice_id or selected or not is_active_choice_state(_field(status, "status")):
                    continue
                detail = self.show_choice(choice_id)
                for block in getattr(detail, "blocks", ()):
                    if not isinstance(block, dict) or block.get("status", "active") != "active":
                        continue
                    target = str(block.get("target") or "")
                    target_type = str(block.get("target_type") or "item")
                    actions.append(
                        NextAction(
                            action_id=f"NEXT-BLOCKER-{len(actions) + 1:03d}",
                            priority="high",
                            kind="resolve_choice",
                            target=choice_id,
                            reason=(
                                f"{choice_id} blocks {target_type} {target}: "
                                f"{block.get('reason') or 'Decision required.'}"
                            ),
                            command=f"p2p choice show {choice_id}",
                            source=str(getattr(detail, "path", "generated")),
                        )
                    )
            return actions
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
        *,
        allow_build: bool = True,
    ) -> DecisionContextIndex | None:
        if context_snapshot is not None:
            value = context_snapshot.get("decision_context_index")
            if isinstance(value, DecisionContextIndex):
                return value
        return self.decision_context_index() if allow_build else None

    def _freshness(
        self,
        context_snapshot: Mapping[str, object] | None,
        index: DecisionContextIndex | None,
    ) -> object | None:
        if context_snapshot is not None:
            freshness = context_snapshot.get("derived_freshness_status")
            if freshness is not None:
                return freshness
        if (
            self.derived_freshness_status is None
            or (context_snapshot is not None and context_snapshot.get("derived_freshness_not_requested"))
        ):
            return None
        if index is None:
            return None
        return self.derived_freshness_status(
            decision_context_index_snapshot=index,
        )


def _snapshot_sequence(
    snapshot: Mapping[str, object] | None,
    key: str,
) -> list[Any]:
    value = snapshot.get(key, ()) if snapshot is not None else ()
    return list(value) if isinstance(value, (tuple, list)) else []


def _impact_priority(severity: ProposalDecisionImpactSeverity) -> str:
    if severity in {
        ProposalDecisionImpactSeverity.blocker,
        ProposalDecisionImpactSeverity.high,
    }:
        return "high"
    if severity == ProposalDecisionImpactSeverity.medium:
        return "medium"
    return "low"


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
    terminal = {
        record.owner_id
        for record in index.records
        if record.owner_type == NodeType.CHOICE
        and record.kind == RecordKind.DECISION_STATE
        and str(record.text).strip().casefold()
        in {"decided", "withdrawn", "superseded"}
    }
    return tuple(choice_id for choice_id in choices if choice_id not in decided | terminal)


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

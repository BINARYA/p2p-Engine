from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import inspect
import json
from pathlib import Path
from typing import Protocol, TypeVar

from p2p_engine.core.decision_context import (
    ContextBudget,
    DecisionContextIndex,
    DecisionContextPacket,
    RetrievalRequest,
)
from p2p_engine.services.changes import CHANGE_TERMINAL_STATUSES
from p2p_engine.services.decision_context_retrieval import DecisionContextRetrievalService
from p2p_engine.services.lifecycle_authority import is_active_project_projection
from p2p_engine.core.vertical_memory import VerticalProjectMemoryView
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


class _ValidationLike(Protocol):
    ok: bool
    errors: list[str]
    warnings: list[str]


class _RegistryStatusLike(Protocol):
    stale: bool


class _ProjectStateLike(Protocol):
    accepted_proposals: int
    operational_brief_available: bool


class _ProposalSummaryLike(Protocol):
    proposal_id: str
    slug: str
    status: str
    title: str


class _ProposalDetailLike(Protocol):
    proposal_id: str
    status: str
    title: str
    decision_status: str
    path: Path
    problem: str
    proposal: str


class _ChoiceStatusLike(Protocol):
    choice_id: str
    status: str
    title: str
    selected_option: str | None
    path: Path


class _ChoiceDetailLike(Protocol):
    choice_id: str
    status: str
    title: str
    selected_option: str | None
    options: list[dict[str, object]]
    path: Path


class _ChangeStatusLike(Protocol):
    change_id: str
    status: str
    title: str
    path: Path


class _ChangeDetailLike(Protocol):
    change_id: str
    status: str
    title: str
    path: Path
    summary: str


class _WorkSummaryLike(Protocol):
    work_id: str


class _WorkDetailLike(Protocol):
    work_id: str
    status: str
    change_id: str
    target: str
    path: Path


class _NextActionLike(Protocol):
    action_id: str
    priority: str
    kind: str
    target: str
    reason: str
    command: str


class _ArtifactRecordLike(Protocol):
    artifact_id: str
    filename: str
    expectation: object
    status: object
    reason: str
    confirmation: object


class _ArtifactStateLike(Protocol):
    status: str
    artifacts: list[_ArtifactRecordLike]
    suggested_next: list[str]


@dataclass(frozen=True)
class _SkippedValidation:
    ok: bool = True
    errors: int = 0
    warnings: int = 0


class _InteractionStyleScaleLike(Protocol):
    value: int
    label: str
    description: str


class _InteractionStyleLike(Protocol):
    configured: bool
    source: str
    path: Path
    technical_verbosity: _InteractionStyleScaleLike
    formality: _InteractionStyleScaleLike
    assertiveness: _InteractionStyleScaleLike


@dataclass(frozen=True)
class ContextPacket:
    budget: str
    target: str | None
    current_state: dict[str, object]
    next_actions: list[dict[str, object]]
    relevant_artifacts: list[dict[str, object]]
    allowed_commands: list[str]
    do_not_read: list[str]
    bounded_next_step: str
    notes: list[str]
    nearby_context: DecisionContextPacket | None = None


class ContextPacketService:
    def __init__(
        self,
        *,
        project_name: Callable[..., str],
        validate: Callable[..., _ValidationLike],
        registry_status: Callable[[], _RegistryStatusLike],
        project_state_status: Callable[..., _ProjectStateLike],
        proposal_summaries: Callable[..., list[_ProposalSummaryLike]],
        show_proposal: Callable[[str], _ProposalDetailLike],
        choice_statuses: Callable[[], list[_ChoiceStatusLike]],
        show_choice: Callable[[str], _ChoiceDetailLike],
        change_set_statuses: Callable[[], list[_ChangeStatusLike]],
        show_change_set: Callable[[str], _ChangeDetailLike],
        work_summaries: Callable[[], list[_WorkSummaryLike]],
        show_work: Callable[[str], _WorkDetailLike],
        next_actions: Callable[..., list[_NextActionLike]],
        decision_context_index: Callable[..., DecisionContextIndex] | None = None,
        proposal_artifacts: Callable[[str], _ArtifactStateLike] | None = None,
        interaction_style: Callable[[], _InteractionStyleLike] | None = None,
        workspace_schema_status: Callable[[], object] | None = None,
        workspace_schema_preflight: Callable[[], object] | None = None,
        derived_freshness_status: Callable[..., object] | None = None,
        fast_freshness_status: Callable[..., object] | None = None,
        vertical_memory_status: Callable[..., object] | None = None,
        vertical_memory_view: Callable[..., VerticalProjectMemoryView] | None = None,
        readiness_from_vertical_memory: (
            Callable[..., object] | None
        ) = None,
    ) -> None:
        self.project_name = project_name
        self.validate = validate
        self.registry_status = registry_status
        self.project_state_status = project_state_status
        self.proposal_summaries = proposal_summaries
        self.show_proposal = show_proposal
        self.choice_statuses = choice_statuses
        self.show_choice = show_choice
        self.change_set_statuses = change_set_statuses
        self.show_change_set = show_change_set
        self.work_summaries = work_summaries
        self.show_work = show_work
        self.next_actions = next_actions
        self.decision_context_index = decision_context_index
        self.proposal_artifacts = proposal_artifacts
        self.interaction_style = interaction_style
        self.workspace_schema_status = workspace_schema_status
        self.workspace_schema_preflight = workspace_schema_preflight
        self.derived_freshness_status = derived_freshness_status
        self.fast_freshness_status = fast_freshness_status
        self.vertical_memory_status = vertical_memory_status
        self.vertical_memory_view = vertical_memory_view
        self.readiness_from_vertical_memory = readiness_from_vertical_memory

    def context_packet(
        self,
        budget: str = "small",
        target: str | None = None,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> ContextPacket:
        budget = budget.strip().lower()
        if budget not in {"small", "medium"}:
            raise ValueError("Context budget must be small or medium")
        normalized_target = target.strip().upper() if target else None
        project_name = _provide(
            read_context,
            "project_name",
            (),
            lambda: _call_with_read_context(self.project_name, read_context),
        )
        registry_status = _provide(
            read_context,
            "registry_status",
            (),
            lambda: _call_with_read_context(self.registry_status, read_context),
        )
        validation = (
            _SkippedValidation()
            if budget == "small"
            else _provide(
                read_context,
                "complete_validation",
                (),
                lambda: self.validate(registry_status_snapshot=registry_status),
            )
        )
        proposals = _provide(
            read_context,
            "proposal_summaries",
            (),
            lambda: tuple(
                _call_with_read_context(self.proposal_summaries, read_context)
            ),
        )
        choices = _provide(
            read_context,
            "choice_statuses",
            (),
            lambda: tuple(self.choice_statuses()),
        )
        changes = _provide(
            read_context,
            "change_statuses",
            (),
            lambda: tuple(self.change_set_statuses()),
        )
        works = _provide(
            read_context,
            "work_summaries",
            (),
            lambda: tuple(self.work_summaries()),
        )
        memory_status = (
            _provide(
                read_context,
                "vertical_memory_status",
                (),
                lambda: _call_with_read_context(
                    self.vertical_memory_status,
                    read_context,
                ),
            )
            if self.vertical_memory_status
            else None
        )
        memory: VerticalProjectMemoryView | None = None
        memory_error = ""
        if self.vertical_memory_view is not None:
            try:
                memory = _provide(
                    read_context,
                    "vertical_memory",
                    (True, False),
                    lambda: _call_with_read_context(
                        self.vertical_memory_view,
                        read_context,
                    ),
                )
            except ValueError as exc:
                memory_error = str(exc)
        memory_context = _vertical_memory_context(memory, budget=budget)
        relevant_artifacts = (
            [self._context_artifact(normalized_target, budget)]
            if normalized_target
            else self._default_context_artifacts(proposals, choices, changes)
        )
        if memory_context is not None:
            if normalized_target:
                if normalized_target.startswith("PROP-"):
                    relevant_artifacts[0]["vertical_sections"] = _target_vertical_sections(
                        memory,
                        normalized_target,
                    )
            else:
                relevant_artifacts.insert(
                    0,
                    {
                        "type": "vertical_project_memory",
                        "id": memory.vertical_id,
                        "status": memory.source,
                        "source_fingerprint_sha256": memory.source_fingerprint_sha256,
                        "sections": memory_context["sections"],
                        "pagination": memory_context["pagination"],
                        "command": "p2p project memory show",
                    },
                )
                relevant_artifacts = relevant_artifacts[:5]
        context_snapshot = {
            "registry_status": registry_status,
            "proposal_summaries": proposals,
            "choice_statuses": choices,
            "change_statuses": changes,
        }
        if memory_status is not None:
            context_snapshot["vertical_memory_status"] = memory_status
        if memory is not None:
            context_snapshot["vertical_memory"] = memory
            if self.readiness_from_vertical_memory is not None:
                context_snapshot["project_readiness_result"] = (
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
                )
        decision_index = (
            _provide(
                read_context,
                "decision_context",
                (),
                lambda: _call_with_read_context(
                    self.decision_context_index,
                    read_context,
                ),
            )
            if normalized_target
            and normalized_target.startswith("PROP-")
            and self.decision_context_index
            else None
        )
        if decision_index is not None:
            context_snapshot["decision_context_index"] = decision_index
        schema_status = (
            _provide(
                read_context,
                "schema_preflight",
                (),
                self.workspace_schema_preflight,
            )
            if budget == "small" and self.workspace_schema_preflight
            else _provide(
                read_context,
                "schema_deep_status",
                (),
                self.workspace_schema_status,
            )
            if self.workspace_schema_status
            else None
        )
        freshness_status = (
            self.derived_freshness_status(
                registry_status_snapshot=registry_status,
                decision_context_index_snapshot=decision_index,
                proposal_summaries_snapshot=proposals,
            )
            if budget != "small" and self.derived_freshness_status
            else None
        )
        fast_freshness = (
            _provide(
                read_context,
                "fast_freshness",
                (),
                lambda: _call_with_read_context(
                    self.fast_freshness_status,
                    read_context,
                ),
            )
            if budget == "small" and self.fast_freshness_status
            else None
        )
        if schema_status is not None:
            context_snapshot["workspace_schema_status"] = schema_status
        if freshness_status is not None:
            context_snapshot["derived_freshness_status"] = freshness_status
        elif budget == "small":
            context_snapshot["derived_freshness_not_requested"] = True
            if fast_freshness is not None:
                context_snapshot["fast_freshness_status"] = fast_freshness
        next_actions = _provide(
            read_context,
            "next_actions",
            (3,),
            lambda: self.next_actions(
                limit=3,
                context_snapshot=context_snapshot,
                read_context=read_context,
            ),
        )
        project_status = self.project_state_status(
            accepted_proposals_count=len(
                [proposal for proposal in proposals if is_active_project_projection(proposal.status)]
            ),
            next_actions_snapshot=next_actions,
        )

        current_state = {
            "project": project_name,
            "validation": {
                "ok": validation.ok,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
            "verification": {
                "registry_sources": str(
                    getattr(registry_status, "verification", {}).get(
                        "sources",
                        "unknown",
                    )
                    if isinstance(getattr(registry_status, "verification", {}), Mapping)
                    else "unknown"
                ),
                "validation": "not_run" if budget == "small" else "complete",
                "freshness": "not_run" if budget == "small" else "complete",
                "decision_context": (
                    "targeted" if decision_index is not None else "not_requested"
                ),
                "vertical_memory": (
                    "unavailable"
                    if memory is None
                    else "current"
                    if memory.source == "materialized"
                    else "rebuilt_in_memory"
                    if memory.source == "canonical_fallback"
                    else memory.source
                ),
                "readiness": (
                    "not_run"
                    if "project_readiness_result" not in context_snapshot
                    else "current"
                    if memory is not None and memory.source == "materialized"
                    else "rebuilt_in_memory"
                ),
            },
            "registries_stale": registry_status.stale,
            "accepted_proposals": project_status.accepted_proposals,
            "proposals": len(proposals),
            "draft_proposals": len([proposal for proposal in proposals if proposal.status == "draft"]),
            "choices": len(choices),
            "open_choices": len(
                [
                    choice
                    for choice in choices
                    if choice.status in {"open", "draft", "pending"} and not choice.selected_option
                ]
            ),
            "changes": len(changes),
            "active_changes": len(
                [
                    change
                    for change in changes
                    if change.status not in CHANGE_TERMINAL_STATUSES
                ]
            ),
            "work_items": len(works),
            "operational_brief_available": project_status.operational_brief_available,
        }
        if memory_context is not None:
            current_state["project_memory"] = memory_context
            if normalized_target and normalized_target.startswith("PROP-"):
                current_state["target_vertical_sections"] = _target_vertical_sections(
                    memory,
                    normalized_target,
                )
        elif self.vertical_memory_view is not None:
            current_state["project_memory"] = {
                "state": "unavailable",
                "reason": memory_error,
                "command": "p2p project refresh",
            }
        if self.interaction_style is not None:
            current_state["interaction_style"] = _interaction_style_summary(self.interaction_style())
        if schema_status is not None:
            recovery = getattr(schema_status, "recovery", {})
            current_state["workspace_schema"] = {
                "state": getattr(schema_status, "state", "unknown"),
                "layout_status": getattr(schema_status, "layout_status", "unknown"),
                "alignment_status": getattr(schema_status, "alignment_status", "unknown"),
                "current_version": getattr(schema_status, "current_version", None),
                "target_version": getattr(schema_status, "target_version", None),
                "recovery_required": bool(
                    getattr(schema_status, "recovery_required", False)
                    or (recovery.get("required", False) if isinstance(recovery, dict) else False)
                ),
            }
        if freshness_status is not None:
            nodes = tuple(getattr(freshness_status, "nodes", ()))
            current_state["derived_freshness"] = {
                "status": getattr(freshness_status, "status", "unknown"),
                "attention_nodes": sum(
                    1
                    for node in nodes
                    if getattr(node, "status", "") != "current"
                ),
            }
        elif fast_freshness is not None:
            current_state["derived_freshness"] = fast_freshness.to_dict()

        nearby_context = None
        if (
            normalized_target
            and normalized_target.startswith("PROP-")
            and decision_index is not None
        ):
            nearby_context = DecisionContextRetrievalService().retrieve(
                decision_index,
                RetrievalRequest(
                    budget=ContextBudget(budget),
                    target_id=normalized_target,
                ),
            )
        allowed_commands = self._context_allowed_commands(normalized_target)
        bounded_next_step = (
            allowed_commands[0]
            if normalized_target and allowed_commands
            else next_actions[0].command
            if next_actions and next_actions[0].command
            else "p2p next --top 1"
        )
        notes = [
            "Read compact context first; read full artifacts only by explicit ID.",
            "Owner-controlled governance decisions still require explicit owner instruction.",
        ]
        if budget == "small":
            notes.append("Small budget omits full document bodies and favors IDs, statuses, paths, and commands.")
        if memory_error:
            notes.append(f"Vertical project memory is unavailable: {memory_error}")

        return ContextPacket(
            budget=budget,
            target=normalized_target,
            current_state=current_state,
            next_actions=[
                {
                    "id": action.action_id,
                    "priority": action.priority,
                    "kind": action.kind,
                    "target": action.target,
                    "reason": action.reason,
                    "command": action.command,
                }
                for action in next_actions
            ],
            relevant_artifacts=relevant_artifacts,
            allowed_commands=allowed_commands,
            do_not_read=[
                "Do not scan all .p2p/ directories.",
                "Do not read all registries when this context packet is sufficient.",
                "Do not read all proposal, choice, change, or work files without a target ID.",
                "Do not inspect source code unless the task explicitly requires implementation details.",
                "Do not explain saved P2P artifacts from conversation memory; use show/context commands.",
            ],
            bounded_next_step=bounded_next_step,
            notes=notes,
            nearby_context=nearby_context,
        )

    def _default_context_artifacts(
        self,
        proposals: Sequence[_ProposalSummaryLike],
        choices: Sequence[_ChoiceStatusLike],
        changes: Sequence[_ChangeStatusLike],
    ) -> list[dict[str, object]]:
        artifacts: list[dict[str, object]] = []
        for proposal in [item for item in proposals if item.status == "draft"][:3]:
            artifacts.append(
                {
                    "type": "proposal",
                    "id": proposal.proposal_id,
                    "status": proposal.status,
                    "title": proposal.title,
                    "path": proposal.slug,
                    "command": f"p2p proposal show {proposal.proposal_id}",
                }
            )
        for choice in choices[:3]:
            if choice.status in {"open", "draft", "pending"} and not choice.selected_option:
                artifacts.append(
                    {
                        "type": "choice",
                        "id": choice.choice_id,
                        "status": choice.status,
                        "title": choice.title,
                        "path": choice.path,
                        "command": f"p2p choice show {choice.choice_id}",
                    }
                )
        for change in changes[:3]:
            if change.status not in CHANGE_TERMINAL_STATUSES:
                artifacts.append(
                    {
                        "type": "change",
                        "id": change.change_id,
                        "status": change.status,
                        "title": change.title,
                        "path": change.path,
                        "command": f"p2p change show {change.change_id}",
                    }
                )
        return artifacts[:5]

    def _context_artifact(self, target: str, budget: str) -> dict[str, object]:
        if target.startswith("PROP-"):
            detail = self.show_proposal(target)
            artifact: dict[str, object] = {
                "type": "proposal",
                "id": detail.proposal_id,
                "status": detail.status,
                "title": detail.title,
                "decision_status": detail.decision_status,
                "path": detail.path,
                "command": f"p2p proposal show {detail.proposal_id}",
            }
            if budget == "medium":
                artifact["problem"] = _short_text(detail.problem)
                artifact["proposal"] = _short_text(detail.proposal)
            if self.proposal_artifacts is not None:
                artifact["artifact_coverage"] = _artifact_coverage_summary(self.proposal_artifacts(detail.proposal_id))
            return artifact
        if target.startswith("CHANGE-"):
            detail = self.show_change_set(target)
            artifact = {
                "type": "change",
                "id": detail.change_id,
                "status": detail.status,
                "title": detail.title,
                "path": detail.path,
                "command": f"p2p change show {detail.change_id}",
            }
            if budget == "medium":
                artifact["summary"] = _short_text(detail.summary)
            return artifact
        if target.startswith("CHOICE-"):
            detail = self.show_choice(target)
            return {
                "type": "choice",
                "id": detail.choice_id,
                "status": detail.status,
                "title": detail.title,
                "selected_option": detail.selected_option,
                "options_count": len(detail.options),
                "path": detail.path,
                "command": f"p2p choice show {detail.choice_id}",
            }
        if target.startswith("WORK-"):
            detail = self.show_work(target)
            return {
                "type": "work",
                "id": detail.work_id,
                "status": detail.status,
                "change_id": detail.change_id,
                "target": detail.target,
                "path": detail.path,
                "command": f"p2p work show {detail.work_id}",
            }
        raise ValueError("Context target must start with PROP-, CHANGE-, CHOICE-, or WORK-")

    def _context_allowed_commands(self, target: str | None) -> list[str]:
        commands = [
            "p2p context --budget small",
            "p2p next --top 1",
            "p2p validate",
            "p2p assess show",
            "p2p project interaction-style show",
        ]
        if target is None:
            commands.extend(
                [
                    "p2p proposal list",
                    "p2p choice list",
                    "p2p change status",
                    "p2p work status",
                ]
            )
            return commands
        if target.startswith("PROP-"):
            return [f"p2p proposal show {target}", f"p2p context --target {target} --budget medium", *commands]
        if target.startswith("CHANGE-"):
            return [f"p2p change show {target}", f"p2p context --target {target} --budget medium", *commands]
        if target.startswith("CHOICE-"):
            return [f"p2p choice show {target}", f"p2p context --target {target} --budget medium", *commands]
        if target.startswith("WORK-"):
            return [f"p2p work show {target}", f"p2p context --target {target} --budget medium", *commands]
        return commands


def _interaction_style_summary(view: _InteractionStyleLike) -> dict[str, object]:
    return {
        "configured": view.configured,
        "source": view.source,
        "path": view.path,
        "technical_verbosity": {
            "value": view.technical_verbosity.value,
            "label": view.technical_verbosity.label,
        },
        "formality": {
            "value": view.formality.value,
            "label": view.formality.label,
        },
        "assertiveness": {
            "value": view.assertiveness.value,
            "label": view.assertiveness.label,
        },
        "command": "p2p project interaction-style show",
        "update_command": "p2p project interaction-style set --technical-verbosity 2 --formality 2 --assertiveness 0",
        "does_not_affect": [
            "governance_authority",
            "readiness_scores",
            "validation_truth",
            "permissions",
            "consent",
            "factual_claims",
        ],
    }


def _short_text(value: str, limit: int = 360) -> str | None:
    stripped = str(value or "").strip()
    if not stripped or stripped.lower() == "pending.":
        return None
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3].rstrip() + "..."


def _artifact_coverage_summary(view: _ArtifactStateLike) -> dict[str, object]:
    gaps: list[dict[str, object]] = []
    for record in getattr(view, "artifacts"):
        status = _enum_value(getattr(record, "status"))
        expectation = _enum_value(getattr(record, "expectation"))
        if status in {"unknown", "missing", "weak", "deferred"} and expectation in {"required", "required_when_applicable"}:
            gaps.append(_artifact_gap(record, status=status, expectation=expectation))
        elif status == "not_applicable":
            gaps.append(_artifact_gap(record, status=status, expectation=expectation))
    return {
        "status": getattr(view, "status"),
        "gaps": gaps,
        "suggested_next": list(getattr(view, "suggested_next")),
    }


def _artifact_gap(record: _ArtifactRecordLike, *, status: str, expectation: str) -> dict[str, object]:
    return {
        "artifact": getattr(record, "artifact_id"),
        "filename": getattr(record, "filename"),
        "expectation": expectation,
        "status": status,
        "reason": getattr(record, "reason"),
        "confirmation": _enum_value(getattr(record, "confirmation")),
    }


def _vertical_memory_context(
    view: VerticalProjectMemoryView | None,
    *,
    budget: str,
) -> dict[str, object] | None:
    if view is None:
        return None
    max_sections = 8 if budget == "small" else 24
    max_contributions = 3 if budget == "small" else 8
    byte_budget = 12 * 1024 if budget == "small" else 32 * 1024
    ordered = sorted(
        view.sections,
        key=lambda section: (
            0 if section.required else 1,
            0
            if any(
                str(item.get("kind") or "") == "conflict"
                and str(item.get("status") or "") == "unresolved"
                for item in section.conflicts
            )
            else 1,
            0 if section.questions else 1,
            section.priority,
            section.section_id,
        ),
    )
    summaries: list[dict[str, object]] = []
    for section in ordered:
        active = section.active_contributions[:max_contributions]
        summary = {
            "section_id": section.section_id,
            "title": section.title,
            "required": section.required,
            "priority": section.priority,
            "definition_status": str(section.definition.get("status") or "missing"),
            "active_contribution_count": len(section.active_contributions),
            "active_proposals": [item.proposal_id for item in active],
            "active_contributions_truncated": len(section.active_contributions) > len(active),
            "historical_contribution_count": len(section.historical_contributions),
            "open_questions": [
                str(item.get("id") or "")
                for item in section.questions
                if str(item.get("state") or "") in {"to_answer", "answered"}
            ][:max_contributions],
            "unresolved_conflicts": [
                str(item.get("id") or "")
                for item in section.conflicts
                if str(item.get("kind") or "") == "conflict"
                and str(item.get("status") or "") == "unresolved"
            ][:max_contributions],
            "source_references": sorted({item.source_path for item in active}),
        }
        candidate = [*summaries, summary]
        if len(candidate) > max_sections:
            break
        if len(json.dumps(candidate, sort_keys=True, default=str).encode("utf-8")) > byte_budget:
            break
        summaries.append(summary)
    total_contributions = sum(
        len(section.active_contributions) + len(section.historical_contributions)
        for section in view.sections
    )
    return {
        "state": view.source,
        "vertical_id": view.vertical_id,
        "vertical_version": view.vertical_version,
        "source_fingerprint_sha256": view.source_fingerprint_sha256,
        "section_count": len(view.sections),
        "contribution_count": total_contributions,
        "unmapped_active_proposals": len(view.unmapped_active_proposals),
        "sections": summaries,
        "pagination": {
            "total": len(view.sections),
            "returned": len(summaries),
            "truncated": len(summaries) < len(view.sections),
        },
        "command": "p2p project memory show",
    }


def _target_vertical_sections(
    view: VerticalProjectMemoryView | None,
    proposal_id: str,
) -> list[dict[str, object]]:
    if view is None:
        return []
    sections: list[dict[str, object]] = []
    for section in view.sections:
        active = [
            item for item in section.active_contributions if item.proposal_id == proposal_id
        ]
        historical = [
            item for item in section.historical_contributions if item.proposal_id == proposal_id
        ]
        if not active and not historical:
            continue
        contributions = [*active, *historical]
        sections.append(
            {
                "section_id": section.section_id,
                "title": section.title,
                "activation": "active" if active else "historical",
                "contribution_ids": [item.contribution_id for item in contributions],
                "source_references": sorted({item.source_path for item in contributions}),
            }
        )
    return sections


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value or ""))

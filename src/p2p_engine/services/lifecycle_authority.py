from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Callable, Iterable
from pathlib import Path
from types import MappingProxyType

from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAuthorityInterval,
    ProposalDecisionAuthorityResolution,
    ProposalDecisionBindingStatus,
    ProposalDecisionEffectiveState,
    ProposalDecisionEvent,
    ProposalDecisionEventType,
    ProposalDecisionLedger,
    ProposalDecisionLifecycleView,
)
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    projection_binding_status,
    proposal_semantic_sha256,
    render_decision_projection,
    render_proposal_projection,
)
from p2p_engine.services.workspace_reads import WorkspaceReadContext


PROPOSAL_LIFECYCLE_AUTHORITY_POLICY_VERSION = 2


@dataclass(frozen=True)
class ProposalLifecycleAuthority:
    status: str
    committed: bool
    active_projection: bool
    reason: str


_POLICY = {
    "accepted": ProposalLifecycleAuthority("accepted", True, True, "unconditional_acceptance"),
    "accepted_with_changes": ProposalLifecycleAuthority(
        "accepted_with_changes", True, True, "conditional_acceptance"
    ),
    "split": ProposalLifecycleAuthority("split", True, False, "lineage_replaced_by_split_targets"),
    "merged_into_other": ProposalLifecycleAuthority(
        "merged_into_other", True, False, "lineage_replaced_by_merge_target"
    ),
    "superseded": ProposalLifecycleAuthority("superseded", True, False, "historical_superseded_authority"),
    "revoked": ProposalLifecycleAuthority("revoked", True, False, "historical_revoked_authority"),
    "withdrawn": ProposalLifecycleAuthority("withdrawn", False, False, "historical_never_active"),
}


_ALLOWED_TRANSITIONS: dict[
    ProposalDecisionEffectiveState,
    frozenset[ProposalDecisionEventType],
] = {
    ProposalDecisionEffectiveState.undecided: frozenset(
        {
            ProposalDecisionEventType.accepted,
            ProposalDecisionEventType.accepted_with_changes,
            ProposalDecisionEventType.deferred,
            ProposalDecisionEventType.withdrawn,
            ProposalDecisionEventType.rejected,
            ProposalDecisionEventType.split,
            ProposalDecisionEventType.merged_into_other,
        }
    ),
    ProposalDecisionEffectiveState.deferred: frozenset(
        {
            ProposalDecisionEventType.accepted,
            ProposalDecisionEventType.accepted_with_changes,
            ProposalDecisionEventType.withdrawn,
            ProposalDecisionEventType.rejected,
            ProposalDecisionEventType.split,
            ProposalDecisionEventType.merged_into_other,
        }
    ),
    ProposalDecisionEffectiveState.accepted: frozenset(
        {
            ProposalDecisionEventType.revoked,
            ProposalDecisionEventType.superseded,
            ProposalDecisionEventType.split,
            ProposalDecisionEventType.merged_into_other,
        }
    ),
    ProposalDecisionEffectiveState.accepted_with_changes: frozenset(
        {
            ProposalDecisionEventType.revoked,
            ProposalDecisionEventType.superseded,
            ProposalDecisionEventType.split,
            ProposalDecisionEventType.merged_into_other,
        }
    ),
    ProposalDecisionEffectiveState.revoked: frozenset(
        {ProposalDecisionEventType.reinstated}
    ),
    ProposalDecisionEffectiveState.withdrawn: frozenset(),
    ProposalDecisionEffectiveState.rejected: frozenset(),
    ProposalDecisionEffectiveState.superseded: frozenset(),
    ProposalDecisionEffectiveState.split: frozenset(),
    ProposalDecisionEffectiveState.merged_into_other: frozenset(),
}


def transition_allowed(
    current: ProposalDecisionEffectiveState,
    requested: ProposalDecisionEventType,
) -> bool:
    return requested in _ALLOWED_TRANSITIONS[current]


def require_transition(
    current: ProposalDecisionEffectiveState,
    requested: ProposalDecisionEventType,
) -> None:
    if transition_allowed(current, requested):
        return
    raise ValueError(
        "P2P363_DECISION_TRANSITION_INVALID: "
        f"cannot apply `{requested.value}` from `{current.value}`"
    )


def effective_state_for_event(
    event_type: ProposalDecisionEventType,
    *,
    restored_state: ProposalDecisionEffectiveState | None = None,
) -> ProposalDecisionEffectiveState:
    if event_type == ProposalDecisionEventType.reinstated:
        if restored_state not in {
            ProposalDecisionEffectiveState.accepted,
            ProposalDecisionEffectiveState.accepted_with_changes,
        }:
            raise ValueError(
                "P2P368_DECISION_REINSTATEMENT_MISMATCH: reinstatement must restore "
                "accepted or accepted_with_changes"
            )
        return restored_state
    return ProposalDecisionEffectiveState(event_type.value)


def lifecycle_from_ledger(
    ledger: ProposalDecisionLedger,
    *,
    binding_status: ProposalDecisionBindingStatus = ProposalDecisionBindingStatus.current,
    current_proposal_semantic_sha256: str | None = None,
    diagnostics: tuple[str, ...] = (),
) -> ProposalDecisionLifecycleView:
    intervals: list[ProposalDecisionAuthorityInterval] = []
    open_index: int | None = None
    active_event: ProposalDecisionEvent | None = None
    event_by_id = {event.event_id: event for event in ledger.events}
    for event in ledger.events:
        if event.event_type in {
            ProposalDecisionEventType.accepted,
            ProposalDecisionEventType.accepted_with_changes,
        }:
            active_event = event
            intervals.append(
                ProposalDecisionAuthorityInterval(
                    opened_by_event_id=event.event_id,
                    active_event_id=event.event_id,
                    decision_semantic_sha256=event.decision_semantic_sha256,
                    effective_state=event.effective_state,
                    opened_on=event.decided_on,
                )
            )
            open_index = len(intervals) - 1
        elif event.event_type in {
            ProposalDecisionEventType.revoked,
            ProposalDecisionEventType.superseded,
            ProposalDecisionEventType.split,
            ProposalDecisionEventType.merged_into_other,
        }:
            if open_index is not None:
                intervals[open_index] = replace(
                    intervals[open_index],
                    closed_by_event_id=event.event_id,
                    closed_on=event.decided_on,
                )
                open_index = None
            active_event = None
        elif event.event_type == ProposalDecisionEventType.reinstated:
            affected = event.affected_decision.event_id
            restored = event_by_id.get(affected or "")
            if restored is None or restored.event_type not in {
                ProposalDecisionEventType.accepted,
                ProposalDecisionEventType.accepted_with_changes,
            }:
                raise ValueError(
                    "P2P368_DECISION_REINSTATEMENT_MISMATCH: referenced active event "
                    "is missing or incompatible"
                )
            active_event = event
            intervals.append(
                ProposalDecisionAuthorityInterval(
                    opened_by_event_id=event.event_id,
                    active_event_id=restored.event_id,
                    decision_semantic_sha256=restored.decision_semantic_sha256,
                    effective_state=restored.effective_state,
                    opened_on=event.decided_on,
                )
            )
            open_index = len(intervals) - 1
    current_event = ledger.events[-1] if ledger.events else None
    active = ledger.effective_state in {
        ProposalDecisionEffectiveState.accepted,
        ProposalDecisionEffectiveState.accepted_with_changes,
    }
    committed = bool(ledger.events) and ledger.effective_state not in {
        ProposalDecisionEffectiveState.undecided,
        ProposalDecisionEffectiveState.deferred,
        ProposalDecisionEffectiveState.withdrawn,
        ProposalDecisionEffectiveState.rejected,
    }
    controlling = active_event if active else current_event
    reconsideration_command = decision_reconsideration_command(
        ledger.proposal_id,
        ledger.effective_state,
    )
    lifecycle_diagnostics = diagnostics
    if reconsideration_command:
        lifecycle_diagnostics = tuple(
            dict.fromkeys(
                (
                    *diagnostics,
                    "P2P378_DECISION_RECONSIDERATION_REQUIRES_NEW_PROPOSAL",
                )
            )
        )
    return ProposalDecisionLifecycleView(
        proposal_id=ledger.proposal_id,
        source_model="decision_event_ledger_v3",
        authority_resolution=ledger.authority_resolution,
        effective_state=ledger.effective_state,
        head_event_type=current_event.event_type if current_event else None,
        head_event_id=ledger.head_event_id,
        event_count=len(ledger.events),
        committed=committed,
        active=active,
        ever_active=bool(intervals),
        decision_semantic_sha256=(
            controlling.decision_semantic_sha256 if controlling else None
        ),
        proposal_semantic_sha256=current_proposal_semantic_sha256,
        proposal_binding_status=binding_status,
        intervals=tuple(intervals),
        lineage=current_event.lineage if current_event else None or _empty_lineage(),
        diagnostics=lifecycle_diagnostics,
        current_event=current_event,
        suggested_next_command=reconsideration_command,
    )


def _empty_lineage():
    from p2p_engine.core.proposal_decision_events import ProposalDecisionLineage

    return ProposalDecisionLineage()


def decision_reconsideration_command(
    proposal_id: str,
    state: ProposalDecisionEffectiveState,
) -> str | None:
    if state not in {
        ProposalDecisionEffectiveState.rejected,
        ProposalDecisionEffectiveState.withdrawn,
    }:
        return None
    return f'p2p proposal create "Reconsidered direction for {proposal_id}"'


class ProposalLifecycleAuthorityService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_proposal_dir: Callable[[str], Path],
        workspace_schema_status: Callable[[], object],
        workspace_schema_preflight: Callable[[], object] | None = None,
        codec: ProposalDecisionLedgerCodec | None = None,
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir
        self.workspace_schema_status = workspace_schema_status
        self.workspace_schema_preflight = workspace_schema_preflight
        self.codec = codec or ProposalDecisionLedgerCodec()

    def status(
        self,
        proposal_id: str,
        *,
        strict: bool = False,
        schema_snapshot: object | None = None,
        proposal_dir: Path | None = None,
        read_context: WorkspaceReadContext | None = None,
    ) -> ProposalDecisionLifecycleView:
        schema = schema_snapshot or self._schema_snapshot(read_context=read_context)
        current_version = getattr(schema, "current_version", None)
        layout_status = str(getattr(schema, "layout_status", "invalid"))
        recovery = getattr(schema, "recovery", {})
        if isinstance(recovery, dict) and recovery.get("required"):
            return self._unresolved(
                proposal_id,
                "workspace_recovery",
                "P2P307_WORKSPACE_TRANSACTION_RECOVERY_REQUIRED",
                strict=strict,
            )
        if layout_status in {"ahead", "invalid", "unsupported", "incomplete"}:
            return self._unresolved(
                proposal_id,
                "unsupported_workspace",
                "P2P376_DECISION_FUTURE_CONTRACT",
                strict=strict,
            )
        proposal_dir = proposal_dir or self.find_proposal_dir(proposal_id)
        if current_version == 4 and layout_status == "current":
            return self._v3_status(
                proposal_id,
                proposal_dir,
                strict=strict,
                read_context=read_context,
            )
        return self._unresolved(
            proposal_id,
            "unsupported_workspace",
            "P2P375_DECISION_SCHEMA_V4_REQUIRED",
            strict=strict,
        )

    def capture_all(
        self,
        *,
        strict: bool = False,
        read_context: WorkspaceReadContext | None = None,
    ) -> dict[str, ProposalDecisionLifecycleView]:
        return self.evaluate_many(None, strict=strict, read_context=read_context)

    def evaluate_many(
        self,
        proposal_ids: Iterable[str] | None,
        *,
        strict: bool = False,
        schema_snapshot: object | None = None,
        read_context: WorkspaceReadContext | None = None,
    ) -> dict[str, ProposalDecisionLifecycleView]:
        selected_ids = (
            None
            if proposal_ids is None
            else tuple(sorted(set(proposal_ids)))
        )
        if read_context is not None:
            cached = read_context.provide(
                "proposal_lifecycle_batch",
                (selected_ids, strict),
                lambda: MappingProxyType(
                    self._evaluate_many(
                        selected_ids,
                        strict=strict,
                        schema_snapshot=schema_snapshot,
                        read_context=read_context,
                    )
                ),
            )
            return dict(cached)
        return self._evaluate_many(
            selected_ids,
            strict=strict,
            schema_snapshot=schema_snapshot,
            read_context=None,
        )

    def _evaluate_many(
        self,
        proposal_ids: tuple[str, ...] | None,
        *,
        strict: bool,
        schema_snapshot: object | None,
        read_context: WorkspaceReadContext | None,
    ) -> dict[str, ProposalDecisionLifecycleView]:
        schema = schema_snapshot or self._schema_snapshot(read_context=read_context)
        directories = self._proposal_directories(read_context=read_context)
        selected = sorted(directories) if proposal_ids is None else list(proposal_ids)
        result: dict[str, ProposalDecisionLifecycleView] = {}
        for proposal_id in selected:
            proposal_dir = directories.get(proposal_id)
            if proposal_dir is None:
                result[proposal_id] = self._unresolved(
                    proposal_id,
                    "proposal_directory",
                    f"Proposal not found: {proposal_id}",
                    strict=strict,
                )
                continue
            result[proposal_id] = self.status(
                proposal_id,
                strict=strict,
                schema_snapshot=schema,
                proposal_dir=proposal_dir,
                read_context=read_context,
            )
        return result

    def _proposal_directories(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> dict[str, Path]:
        proposals_dir = self.p2p_dir / "proposals"
        result: dict[str, Path] = {}
        if not proposals_dir.exists():
            return result
        paths = (
            read_context.documents.discover(
                proposals_dir,
                policy="proposal-directories-v1",
                predicate=lambda item: item.is_dir(),
            )
            if read_context is not None
            else tuple(sorted(proposals_dir.iterdir(), key=lambda item: item.name))
        )
        for path in paths:
            if not path.is_dir():
                continue
            parts = path.name.split("-", 2)
            if len(parts) < 2 or parts[0] != "PROP" or not parts[1].isdigit():
                continue
            proposal_id = f"PROP-{parts[1]}"
            if proposal_id in result:
                raise ValueError(f"Ambiguous proposal ID: {proposal_id}")
            result[proposal_id] = path
        return result

    def _schema_snapshot(
        self,
        *,
        read_context: WorkspaceReadContext | None = None,
    ) -> object:
        if read_context is not None:
            read_context.record_schema_preflight()
        return (
            self.workspace_schema_preflight()
            if self.workspace_schema_preflight is not None
            else self.workspace_schema_status()
        )

    def _v3_status(
        self,
        proposal_id: str,
        proposal_dir: Path,
        *,
        strict: bool,
        read_context: WorkspaceReadContext | None = None,
    ) -> ProposalDecisionLifecycleView:
        ledger_path = proposal_dir / "decision-events.yml"
        if not ledger_path.exists():
            return self._unresolved(
                proposal_id,
                "decision_event_ledger_v3",
                "P2P361_DECISION_LEDGER_INVALID: missing decision-events.yml",
                strict=strict,
            )
        try:
            ledger_bytes = (
                read_context.documents.bytes(ledger_path)
                if read_context is not None
                else ledger_path.read_bytes()
            )
            if read_context is not None:
                read_context.record_ledger_parse(
                    ledger_path.relative_to(self.root).as_posix()
                )
            ledger = self.codec.loads(
                ledger_bytes,
                expected_proposal_id=proposal_id,
            )
            proposal_path = proposal_dir / "proposal.md"
            proposal_text = (
                read_context.documents.text(proposal_path)
                if read_context is not None
                else proposal_path.read_text(encoding="utf-8")
            )
            current_semantic = proposal_semantic_sha256(proposal_id, proposal_text)
            binding = projection_binding_status(
                proposal_id,
                proposal_text,
                ledger.events[-1] if ledger.events else None,
            )
            diagnostics: list[str] = []
            expected_proposal = render_proposal_projection(
                proposal_text,
                ledger.effective_state,
            )
            if expected_proposal != proposal_text:
                diagnostics.append("P2P362_DECISION_PROJECTION_DIVERGENCE: proposal.md")
            decision_path = proposal_dir / "decision.md"
            decision_text = (
                (
                    read_context.documents.text(decision_path)
                    if read_context is not None
                    else decision_path.read_text(encoding="utf-8")
                )
                if decision_path.exists()
                else ""
            )
            expected_decision = render_decision_projection(
                proposal_id,
                ledger.events[-1] if ledger.events else None,
                empty_state=ledger.effective_state,
            )
            if expected_decision != decision_text:
                diagnostics.append("P2P362_DECISION_PROJECTION_DIVERGENCE: decision.md")
            if binding == ProposalDecisionBindingStatus.diverged:
                diagnostics.append("P2P377_DECISION_PROPOSAL_BINDING_DIVERGED")
            return lifecycle_from_ledger(
                ledger,
                binding_status=binding,
                current_proposal_semantic_sha256=current_semantic,
                diagnostics=tuple(diagnostics),
            )
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return self._unresolved(
                proposal_id,
                "decision_event_ledger_v3",
                str(exc),
                strict=strict,
            )

    @staticmethod
    def _unresolved(
        proposal_id: str,
        source_model: str,
        diagnostic: str,
        *,
        strict: bool,
    ) -> ProposalDecisionLifecycleView:
        if strict:
            raise ValueError(diagnostic)
        return ProposalDecisionLifecycleView(
            proposal_id=proposal_id,
            source_model=source_model,
            authority_resolution=ProposalDecisionAuthorityResolution.invalid,
            effective_state=ProposalDecisionEffectiveState.undecided,
            head_event_type=None,
            head_event_id=None,
            event_count=0,
            committed=False,
            active=False,
            ever_active=False,
            decision_semantic_sha256=None,
            proposal_semantic_sha256=None,
            proposal_binding_status=ProposalDecisionBindingStatus.unavailable,
            diagnostics=(diagnostic,),
        )


def proposal_lifecycle_authority(status: str) -> ProposalLifecycleAuthority:
    normalized = str(status or "unknown").strip().lower().replace("-", "_").replace(" ", "_")
    return _POLICY.get(
        normalized,
        ProposalLifecycleAuthority(normalized or "unknown", False, False, "not_committed"),
    )


def is_committed_proposal(status: str) -> bool:
    return proposal_lifecycle_authority(status).committed


def is_active_project_projection(status: str) -> bool:
    return proposal_lifecycle_authority(status).active_projection


def proposal_display_status(
    lifecycle: ProposalDecisionLifecycleView,
    *,
    undecided_fallback: str,
) -> str:
    if lifecycle.effective_state == ProposalDecisionEffectiveState.undecided:
        return undecided_fallback
    return lifecycle.effective_state.value

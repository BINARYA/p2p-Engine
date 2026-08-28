from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import date
from pathlib import Path

import yaml

from p2p_engine.core.authority import (
    AuthorityContext,
    AuthorityEvidence,
    AuthorityMode,
    authority_context_from_evidence,
)
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.mutation_preview import (
    MutationPreview,
    MutationPreviewService,
    MutationResult,
    SourcePrecondition,
    semantic_sha256,
    source_precondition,
)
from p2p_engine.core.mutation_receipts import MutationReceipt
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAffectedDecision,
    ProposalDecisionApplyResult,
    ProposalDecisionAuthorityResolution,
    ProposalDecisionBindingStatus,
    ProposalDecisionCondition,
    ProposalDecisionEffectiveState,
    ProposalDecisionEvent,
    ProposalDecisionEventType,
    ProposalDecisionHistoryPage,
    ProposalDecisionImpactBinding,
    ProposalDecisionLedger,
    ProposalDecisionLifecycleView,
    ProposalDecisionLineage,
    ProposalDecisionLineageKind,
    ProposalDecisionPreview,
    ProposalDecisionReadinessBinding,
    ProposalDecisionRequest,
)
from p2p_engine.foundation.processes import pid_is_running
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.lifecycle_authority import (
    ProposalLifecycleAuthorityService,
    effective_state_for_event,
    lifecycle_from_ledger,
    require_transition,
)
from p2p_engine.services.authority import ProjectAuthorityService
from p2p_engine.services.mutation_receipts import MutationReceiptService
from p2p_engine.services.permissions import PermissionsService
from p2p_engine.services.proposal_decision_ledger import (
    OPERATION_KEY_PREFIX,
    ProposalDecisionLedgerCodec,
    decision_semantic_sha256,
    normalize_scalar,
    operation_key,
    projection_binding_status,
    proposal_semantic_sha256,
    render_decision_projection,
    render_proposal_projection,
    validate_conditions,
    validate_lineage,
)
from p2p_engine.services.readiness import ReadinessService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter


DECISION_MUTATION_OPERATION = "proposal-decision-apply"
DECISION_PREVIEW_POLICY_VERSION = 1
MAX_HISTORY_LIMIT = 100
_DECISION_TRANSACTION_PREFIX = "mutation-proposal-decision-apply-"
_DECISION_LOCK_WAIT_SECONDS = 5.0
_OPERATION_KEY = re.compile(r"^P2POP-[0-9a-f]{24}$")
_CURSOR = re.compile(r"^PDC-(\d+)-([0-9a-f]{16})$")
_IMPACT_EVENTS = frozenset(
    {
        ProposalDecisionEventType.revoked,
        ProposalDecisionEventType.superseded,
        ProposalDecisionEventType.split,
        ProposalDecisionEventType.merged_into_other,
        ProposalDecisionEventType.reinstated,
    }
)
_ACTIVE_EVENTS = frozenset(
    {
        ProposalDecisionEventType.accepted,
        ProposalDecisionEventType.accepted_with_changes,
        ProposalDecisionEventType.reinstated,
    }
)
_ACTIVE_TO_INACTIVE = frozenset(
    {
        ProposalDecisionEventType.revoked,
        ProposalDecisionEventType.superseded,
        ProposalDecisionEventType.split,
        ProposalDecisionEventType.merged_into_other,
    }
)
_TERMINAL_LINEAGE_STATES = frozenset(
    {
        ProposalDecisionEffectiveState.withdrawn,
        ProposalDecisionEffectiveState.rejected,
        ProposalDecisionEffectiveState.superseded,
        ProposalDecisionEffectiveState.split,
        ProposalDecisionEffectiveState.merged_into_other,
    }
)

ImpactProvider = Callable[
    [str, ProposalDecisionEventType, ProposalDecisionLifecycleView],
    Mapping[str, object],
]
DecisionScopeGate = Callable[[str], Sequence[SourcePrecondition] | None]


class ProposalDecisionService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_proposal_dir: Callable[[str], Path],
        workspace_schema_status: Callable[[], object] | None = None,
        permissions: PermissionsService | None = None,
        authority: ProjectAuthorityService | None = None,
        receipts: MutationReceiptService | None = None,
        lifecycle: ProposalLifecycleAuthorityService | None = None,
        atomic_writer: AtomicMutationWriter | None = None,
        readiness: ReadinessService | None = None,
        impact_provider: ImpactProvider | None = None,
        decision_scope_gate: DecisionScopeGate | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.p2p_dir = p2p_dir.resolve()
        self.find_proposal_dir = find_proposal_dir
        self.workspace_schema_status = (
            workspace_schema_status or self._default_schema_status
        )
        self.codec = ProposalDecisionLedgerCodec()
        self.permissions = permissions or PermissionsService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.authority = authority or ProjectAuthorityService(
            root=self.root,
            p2p_dir=self.p2p_dir,
            permissions=self.permissions,
        )
        self.receipts = receipts or MutationReceiptService(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.lifecycle = lifecycle or ProposalLifecycleAuthorityService(
            root=self.root,
            p2p_dir=self.p2p_dir,
            find_proposal_dir=find_proposal_dir,
            workspace_schema_status=self.workspace_schema_status,
            codec=self.codec,
        )
        self.atomic_writer = atomic_writer or AtomicMutationWriter(
            root=self.root,
            p2p_dir=self.p2p_dir,
        )
        self.readiness = readiness
        self.impact_provider = impact_provider
        self.decision_scope_gate = decision_scope_gate
        self.clock = clock or (lambda: date.today().isoformat())

    def status(
        self,
        proposal_id: str,
        *,
        strict: bool = False,
    ) -> ProposalDecisionLifecycleView:
        return self.lifecycle.status(proposal_id, strict=strict)

    def history(
        self,
        proposal_id: str,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> ProposalDecisionHistoryPage:
        if isinstance(limit, bool) or not 1 <= limit <= MAX_HISTORY_LIMIT:
            raise ValueError(
                f"Decision history limit must be between 1 and {MAX_HISTORY_LIMIT}."
            )
        ledger = self._read_ledger(proposal_id)
        offset = self._history_offset(
            proposal_id,
            ledger.head_event_id,
            cursor,
        )
        items = ledger.events[offset : offset + limit]
        next_offset = offset + len(items)
        next_cursor = (
            self._history_cursor(proposal_id, ledger.head_event_id, next_offset)
            if next_offset < len(ledger.events)
            else None
        )
        return ProposalDecisionHistoryPage(
            proposal_id=proposal_id,
            head_event_id=ledger.head_event_id,
            items=items,
            total_count=len(ledger.events),
            returned_count=len(items),
            next_cursor=next_cursor,
        )

    def request(
        self,
        *,
        proposal_id: str,
        event_type: ProposalDecisionEventType,
        reason: str,
        actor_id: str,
        executor_actor_id: str | None = None,
        executor_kind: str = "person",
        channel: str = "cli",
        decided_on: str = "",
        operation_key_value: str = "",
        source_head_event_id: str | None = None,
        conditions: tuple[ProposalDecisionCondition, ...] = (),
        lineage: ProposalDecisionLineage = ProposalDecisionLineage(),
        affected_event_id: str | None = None,
        revocation_event_id: str | None = None,
        impact_preview_token: str | None = None,
        drift_acknowledged: bool = False,
        readiness_override: bool = False,
        consent_id: str | None = None,
        consent_sha256: str | None = None,
        authority_context: AuthorityContext | None = None,
    ) -> ProposalDecisionRequest:
        return ProposalDecisionRequest(
            proposal_id=proposal_id,
            event_type=event_type,
            reason=reason,
            actor_id=actor_id,
            executor_actor_id=executor_actor_id or actor_id,
            executor_kind=executor_kind,
            channel=channel,
            decided_on=decided_on,
            operation_key=operation_key_value,
            source_head_event_id=source_head_event_id,
            conditions=conditions,
            lineage=lineage,
            affected_event_id=affected_event_id,
            revocation_event_id=revocation_event_id,
            impact_preview_token=impact_preview_token,
            drift_acknowledged=drift_acknowledged,
            readiness_override=readiness_override,
            consent_id=consent_id,
            consent_sha256=consent_sha256,
            authority_context=authority_context,
        )

    def preview(self, request: ProposalDecisionRequest) -> ProposalDecisionPreview:
        return self._preview(request)

    def _preview(
        self,
        request: ProposalDecisionRequest,
    ) -> ProposalDecisionPreview:
        self._require_schema_v4()
        snapshot = self._capture(request.proposal_id)
        ledger = snapshot["ledger"]
        proposal_text = snapshot["proposal_bytes"].decode("utf-8")
        assert isinstance(ledger, ProposalDecisionLedger)
        lifecycle = self._lifecycle_from_snapshot(
            request.proposal_id,
            ledger,
            proposal_text,
            snapshot["decision_bytes"],
        )
        if lifecycle.authority_resolution != ProposalDecisionAuthorityResolution.resolved:
            raise ValueError(
                "P2P361_DECISION_LEDGER_INVALID: decision authority is unresolved"
            )
        descriptor = self.authority.codec.descriptor_from_bytes(
            snapshot["authority_bytes"]
        )
        permission_payload = (
            self._permission_payload(snapshot["permissions_bytes"])
            if descriptor.mode == AuthorityMode.local_policy
            else None
        )
        required_capabilities = ["proposal.decide"]
        if request.readiness_override:
            required_capabilities.append("proposal.readiness.override")
        authority_context, authority = self.authority.resolve(
            supplied_context=request.authority_context,
            subject_id=request.actor_id,
            executor_id=request.executor_actor_id,
            executor_kind=request.executor_kind,
            required_capabilities=required_capabilities,
            channel=request.channel,
            permission_payload=permission_payload,
            consent_id=request.consent_id,
            consent_sha256=request.consent_sha256,
        )
        if request.readiness_override:
            override_claim = authority_context.claim_for(
                "proposal.readiness.override"
            )
            if override_claim is None or override_claim.basis.value != "root_authority":
                raise ValueError(
                    "P2P_AUTHORIZATION_DENIED: readiness override requires "
                    "root proposal.readiness.override authority"
                )
        request = replace(
            request,
            actor_id=authority_context.subject.identity_id,
            executor_actor_id=authority_context.executor.identity_id,
            executor_kind=authority_context.executor.kind.value,
            authority_context=authority_context,
        )
        normalized = self._normalize_request(
            request,
            source_head_event_id=ledger.head_event_id,
        )
        require_transition(lifecycle.effective_state, normalized.event_type)
        decision_scope_sources: tuple[SourcePrecondition, ...] = ()
        if (
            normalized.event_type in _ACTIVE_EVENTS
            and self.decision_scope_gate is not None
        ):
            decision_scope_sources = tuple(
                self.decision_scope_gate(normalized.proposal_id) or ()
            )
        self._validate_binding(lifecycle, normalized)
        self._validate_lineage(normalized)
        affected = self._affected_decision(
            normalized,
            ledger,
            lifecycle,
        )
        effective_state = self._effective_state(normalized, ledger, affected)
        proposal_sha = proposal_semantic_sha256(
            normalized.proposal_id,
            proposal_text,
        )
        decision_sha = self._decision_sha(
            normalized,
            effective_state,
            proposal_sha,
            affected,
        )
        impact, impact_binding, impact_sources = self._impact(
            normalized,
            lifecycle,
        )
        readiness_binding, readiness_candidate = self._readiness_candidate(
            normalized,
            snapshot,
        )
        request_semantics = self._request_semantics(
            normalized,
            authority=authority,
            impact=impact,
            readiness_candidate=readiness_candidate,
            readiness_binding=readiness_binding,
        )
        request_sha = semantic_sha256(request_semantics)
        placeholder_event = self.codec.build_event(
            proposal_id=normalized.proposal_id,
            event_type=normalized.event_type,
            effective_state=effective_state,
            rationale=normalized.reason,
            conditions=normalized.conditions,
            decided_on=normalized.decided_on,
            authority=authority,
            predecessor=ledger.events[-1] if ledger.events else None,
            proposal_semantic_sha256=proposal_sha,
            decision_semantic_sha256=decision_sha,
            affected_decision=affected,
            lineage=normalized.lineage,
            impact=impact_binding,
            readiness=readiness_binding,
            preview_token="0" * 64,
            request_fingerprint_sha256=request_sha,
            operation_key=normalized.operation_key,
        )
        sources = self._source_preconditions(
            snapshot,
            impact_sources,
            include_readiness=readiness_candidate is not None,
            receipt_path=self.receipts.relative_path(normalized.operation_key),
            additional_sources=decision_scope_sources,
        )
        canonical_targets = self._target_paths(
            normalized.proposal_id,
            include_readiness=readiness_candidate is not None,
        )
        targets = (
            *canonical_targets,
            self.receipts.relative_path(normalized.operation_key),
        )
        token_context = {
            "proposal_id": normalized.proposal_id,
            "operation_key": normalized.operation_key,
            "event_type": normalized.event_type.value,
            "source_head_event_id": ledger.head_event_id,
            "proposal_semantic_sha256": proposal_sha,
            "authority_context_sha256": authority.authority_context_sha256,
            "authority_id": authority.authority_id,
            "authority_generation": authority.authority_generation,
            "subject_id": authority.subject.identity_id,
            "executor_id": authority.executor.identity_id,
            "lineage_sha256": semantic_sha256(normalized.lineage.to_dict()),
            "impact_source_fingerprint_sha256": (
                impact_binding.source_fingerprint_sha256
            ),
            "request_fingerprint_sha256": request_sha,
            "decision_date": normalized.decided_on,
        }
        mutation = MutationPreviewService.build(
            operation_id=DECISION_MUTATION_OPERATION,
            targets=targets,
            actor=authority.executor.identity_id,
            authority="typed_authority_context",
            sources=sources,
            candidate_semantics={
                "event": self._event_token_semantics(placeholder_event),
                "ledger": {
                    "proposal_id": ledger.proposal_id,
                    "before_head": ledger.head_event_id,
                    "after_count": len(ledger.events) + 1,
                    "effective_state": effective_state.value,
                },
                "projections": {
                    "proposal_status": effective_state.value,
                    "decision_event_type": normalized.event_type.value,
                },
                "readiness": (
                    self._bytes_sha256(readiness_candidate)
                    if readiness_candidate is not None
                    else None
                ),
            },
            semantic_diff={
                "proposal_id": normalized.proposal_id,
                "before_state": lifecycle.effective_state.value,
                "after_state": effective_state.value,
                "before_head_event_id": ledger.head_event_id,
                "event_type": normalized.event_type.value,
                "impact_total_count": impact_binding.total_count,
                "proposal_binding_status": lifecycle.proposal_binding_status.value,
            },
            token_context=token_context,
            policy_version=DECISION_PREVIEW_POLICY_VERSION,
        )
        event = self.codec.build_event(
            proposal_id=normalized.proposal_id,
            event_type=normalized.event_type,
            effective_state=effective_state,
            rationale=normalized.reason,
            conditions=normalized.conditions,
            decided_on=normalized.decided_on,
            authority=authority,
            predecessor=ledger.events[-1] if ledger.events else None,
            proposal_semantic_sha256=proposal_sha,
            decision_semantic_sha256=decision_sha,
            affected_decision=affected,
            lineage=normalized.lineage,
            impact=impact_binding,
            readiness=readiness_binding,
            preview_token=mutation.preview_token,
            request_fingerprint_sha256=request_sha,
            operation_key=normalized.operation_key,
        )
        candidate_ledger = self.codec.append(ledger, event)
        proposal_candidate = render_proposal_projection(
            proposal_text,
            candidate_ledger.effective_state,
        ).encode("utf-8")
        decision_candidate = render_decision_projection(
            normalized.proposal_id,
            event,
        ).encode("utf-8")
        candidate_bytes = {
            canonical_targets[0]: self.codec.dumps(candidate_ledger),
            canonical_targets[1]: proposal_candidate,
            canonical_targets[2]: decision_candidate,
        }
        if readiness_candidate is not None:
            candidate_bytes[canonical_targets[3]] = readiness_candidate
        candidate_lifecycle = lifecycle_from_ledger(
            candidate_ledger,
            binding_status=ProposalDecisionBindingStatus.current,
            current_proposal_semantic_sha256=proposal_sha,
        )
        self._validate_candidate(
            normalized.proposal_id,
            candidate_bytes,
            candidate_ledger,
        )
        return ProposalDecisionPreview(
            request=normalized,
            mutation=mutation,
            event=event,
            ledger=candidate_ledger,
            lifecycle=candidate_lifecycle,
            impact=impact,
            candidate_bytes=candidate_bytes,
        )

    def apply(
        self,
        request: ProposalDecisionRequest,
        *,
        preview_token: str,
        confirm: bool,
    ) -> ProposalDecisionApplyResult:
        return self._apply(
            request,
            preview_token=preview_token,
            confirm=confirm,
        )

    def _apply(
        self,
        request: ProposalDecisionRequest,
        *,
        preview_token: str,
        confirm: bool,
    ) -> ProposalDecisionApplyResult:
        self._wait_for_competing_decision_mutation()
        if not confirm:
            self._require_schema_v4()
            preview = self._preview(request)
            return ProposalDecisionApplyResult(
                status="blocked",
                event=preview.event,
                lifecycle=preview.lifecycle,
                mutation=MutationResult(
                    status="blocked",
                    operation_id=DECISION_MUTATION_OPERATION,
                    preview_token=preview.mutation.preview_token,
                    actor=request.executor_actor_id,
                    message="Explicit confirmation is required.",
                ),
            )
        retry = self._exact_retry(request, preview_token)
        if retry is not None:
            return retry
        current_head = self._read_ledger(request.proposal_id).head_event_id
        if request.source_head_event_id != current_head:
            raise ValueError(
                "P2P367_DECISION_CONCURRENT_HEAD: ledger head changed after preview"
            )
        try:
            self._require_schema_v4()
        except ValueError as exc:
            if not str(exc).startswith("P2P307_WORKSPACE_TRANSACTION_RECOVERY_REQUIRED"):
                raise
            self._wait_for_competing_decision_mutation()
            retry = self._exact_retry(request, preview_token)
            if retry is not None:
                return retry
            latest = self._read_ledger(request.proposal_id)
            if latest.head_event_id != request.source_head_event_id:
                raise ValueError(
                    "P2P367_DECISION_CONCURRENT_HEAD: another decision event won "
                    "while the schema gate observed its transaction cleanup"
                ) from None
            # The recovery snapshot may have observed another writer while its
            # lock or journal was being removed. Re-evaluate current state
            # before classifying the condition as interrupted recovery.
            self._require_schema_v4()
        try:
            preview = self._preview(request)
        except ValueError:
            retry = self._exact_retry(request, preview_token)
            if retry is not None:
                return retry
            latest = self._read_ledger(request.proposal_id)
            if latest.head_event_id != request.source_head_event_id:
                raise ValueError(
                    "P2P367_DECISION_CONCURRENT_HEAD: ledger head changed "
                    "while rebuilding the lock-bound preview"
                ) from None
            raise
        if preview.mutation.preview_token != preview_token:
            return ProposalDecisionApplyResult(
                status="stale_preview",
                event=preview.event,
                lifecycle=preview.lifecycle,
                mutation=MutationResult(
                    status="stale_preview",
                    operation_id=DECISION_MUTATION_OPERATION,
                    preview_token=preview.mutation.preview_token,
                    actor=preview.request.executor_actor_id,
                    message=(
                        "P2P365_DECISION_STALE_PREVIEW: decision sources or "
                        "request changed after preview"
                    ),
                ),
            )
        receipt_path, receipt_content, _receipt = self.receipts.prepare(
            idempotency_key=preview.request.operation_key,
            operation="proposal_decision_apply",
            actor=preview.event.authority.executor.identity_id,
            request_fingerprint_sha256=(
                preview.event.mutation.request_fingerprint_sha256
            ),
            preview_token=preview.mutation.preview_token,
            result={
                "operation": "proposal_decision_apply",
                "status": "applied",
                "proposal_id": preview.request.proposal_id,
                "event": preview.event.to_dict(),
                "lifecycle": preview.lifecycle.to_dict(),
                "changed_paths": sorted(preview.candidate_bytes),
            },
            candidates=preview.candidate_bytes,
            authority=preview.event.authority,
        )
        result = self.atomic_writer.apply(
            operation_id=DECISION_MUTATION_OPERATION,
            candidates={
                **preview.candidate_bytes,
                receipt_path: receipt_content,
            },
            sources=preview.mutation.source_preconditions,
            preview_token=preview.mutation.preview_token,
            actor=preview.request.executor_actor_id,
            candidate_validator=lambda view: self._validate_candidate_view(
                preview.request.proposal_id,
                view,
                preview.candidate_bytes,
            ),
            lock_wait_timeout=_DECISION_LOCK_WAIT_SECONDS,
        )
        if result.status == "applied":
            return ProposalDecisionApplyResult(
                status="applied",
                event=preview.event,
                lifecycle=preview.lifecycle,
                mutation=result,
            )
        retry = self._exact_retry(request, preview_token)
        if retry is not None:
            return retry
        latest = self._read_ledger(request.proposal_id)
        if latest.head_event_id != request.source_head_event_id:
            raise ValueError(
                "P2P367_DECISION_CONCURRENT_HEAD: another decision event won "
                "the lock-protected commit"
            )
        return ProposalDecisionApplyResult(
            status=result.status,
            event=preview.event,
            lifecycle=preview.lifecycle,
            mutation=result,
        )

    def record(
        self,
        proposal_id: str,
        outcome: DecisionOutcome,
        reason: str,
        approver: str,
        *,
        decided_on: str = "",
        operation_key_value: str = "",
        source_head_event_id: str | None = None,
        preview_token: str = "",
        confirm: bool = False,
        readiness_override: bool = False,
    ) -> ProposalDecisionPreview | ProposalDecisionApplyResult:
        try:
            event_type = ProposalDecisionEventType(outcome.value)
        except ValueError as exc:
            raise ValueError(
                f"Decision outcome `{outcome.value}` requires the generic decision "
                "preview command with explicit lineage or references."
            ) from exc
        request = self.request(
            proposal_id=proposal_id,
            event_type=event_type,
            reason=reason,
            actor_id=approver,
            decided_on=decided_on,
            operation_key_value=operation_key_value,
            source_head_event_id=source_head_event_id,
            readiness_override=readiness_override,
        )
        if not preview_token:
            return self.preview(request)
        return self.apply(
            request,
            preview_token=preview_token,
            confirm=confirm,
        )

    def projection_repair_preview(
        self,
        proposal_id: str,
        *,
        actor_id: str,
        executor_actor_id: str | None = None,
    ) -> MutationPreview:
        self._require_schema_v4()
        snapshot = self._capture(proposal_id)
        ledger = snapshot["ledger"]
        assert isinstance(ledger, ProposalDecisionLedger)
        if (
            ledger.authority_resolution
            != ProposalDecisionAuthorityResolution.resolved
        ):
            raise ValueError(
                "P2P372_DECISION_REPAIR_UNSAFE: ledger authority "
                "must be resolved"
            )
        permission_payload = self._permission_payload(snapshot["permissions_bytes"])
        executor_id = executor_actor_id or actor_id
        executor_kind = self.permissions.resolve_actor_payload(
            executor_id,
            permission_payload,
        ).kind
        request = ProposalDecisionRequest(
            proposal_id=proposal_id,
            event_type=ProposalDecisionEventType.deferred,
            reason="Projection repair.",
            actor_id=actor_id,
            executor_actor_id=executor_id,
            executor_kind=executor_kind,
        )
        owner, executor = self._resolve_authority(request, permission_payload)
        proposal_dir = snapshot["proposal_dir"]
        assert isinstance(proposal_dir, Path)
        proposal_path = self._relative(proposal_dir / "proposal.md")
        decision_path = self._relative(proposal_dir / "decision.md")
        ledger_path = self._relative(proposal_dir / "decision-events.yml")
        proposal_text = snapshot["proposal_bytes"].decode("utf-8")
        proposal_candidate = render_proposal_projection(
            proposal_text,
            ledger.effective_state,
        ).encode("utf-8")
        decision_candidate = render_decision_projection(
            proposal_id,
            ledger.events[-1] if ledger.events else None,
            empty_state=ledger.effective_state,
        ).encode("utf-8")
        candidates: dict[str, bytes] = {}
        if proposal_candidate != snapshot["proposal_bytes"]:
            candidates[proposal_path] = proposal_candidate
        if decision_candidate != snapshot["decision_bytes"]:
            candidates[decision_path] = decision_candidate
        sources = (
            source_precondition(ledger_path, snapshot["ledger_bytes"]),
            source_precondition(proposal_path, snapshot["proposal_bytes"]),
            source_precondition(decision_path, snapshot["decision_bytes"]),
            source_precondition(
                self._relative(self.permissions.path()),
                snapshot["permissions_bytes"],
            ),
        )
        blockers = (
            ()
            if candidates
            else ("P2P372_DECISION_REPAIR_UNSAFE: projections are current",)
        )
        return MutationPreviewService.build(
            operation_id="proposal-decision-projection-repair",
            targets=tuple(candidates),
            actor=executor.actor_id,
            authority="owner_confirmed",
            sources=sources,
            candidate_semantics={
                path: self._bytes_sha256(content)
                for path, content in sorted(candidates.items())
            },
            semantic_diff={
                "proposal_id": proposal_id,
                "head_event_id": ledger.head_event_id,
                "repaired_paths": sorted(candidates),
            },
            token_context={
                "proposal_id": proposal_id,
                "head_event_id": ledger.head_event_id,
                "permission_policy_sha256": semantic_sha256(permission_payload),
                "owner_id": owner.actor_id,
                "executor_actor_id": executor.actor_id,
            },
            blockers=blockers,
        )

    def projection_repair_apply(
        self,
        proposal_id: str,
        *,
        actor_id: str,
        executor_actor_id: str | None = None,
        preview_token: str,
        confirm: bool,
    ) -> MutationResult:
        preview = self.projection_repair_preview(
            proposal_id,
            actor_id=actor_id,
            executor_actor_id=executor_actor_id,
        )
        if not confirm:
            return self._mutation_blocked(
                preview,
                "Explicit confirmation is required for projection repair.",
            )
        if preview.preview_token != preview_token:
            return MutationResult(
                status="stale_preview",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=preview.actor,
                message="P2P365_DECISION_STALE_PREVIEW: projection sources changed.",
            )
        if not preview.apply_allowed:
            return self._mutation_blocked(preview, preview.blockers[0])
        snapshot = self._capture(proposal_id)
        ledger = snapshot["ledger"]
        assert isinstance(ledger, ProposalDecisionLedger)
        proposal_dir = snapshot["proposal_dir"]
        assert isinstance(proposal_dir, Path)
        proposal_path = self._relative(proposal_dir / "proposal.md")
        decision_path = self._relative(proposal_dir / "decision.md")
        proposal_text = snapshot["proposal_bytes"].decode("utf-8")
        rendered = {
            proposal_path: render_proposal_projection(
                proposal_text,
                ledger.effective_state,
            ).encode("utf-8"),
            decision_path: render_decision_projection(
                proposal_id,
                ledger.events[-1] if ledger.events else None,
                empty_state=ledger.effective_state,
            ).encode("utf-8"),
        }
        candidates = {
            path: content
            for path, content in rendered.items()
            if path in preview.targets
        }
        return self.atomic_writer.apply(
            operation_id=preview.operation_id,
            candidates=candidates,
            sources=preview.source_preconditions,
            preview_token=preview.preview_token,
            actor=preview.actor,
            candidate_validator=lambda view: self._validate_projection_repair_view(
                proposal_id,
                view,
            ),
        )

    def ledger_repair_preview(
        self,
        proposal_id: str,
        *,
        candidate_path: Path,
        actor_id: str,
        executor_actor_id: str | None = None,
    ) -> MutationPreview:
        self._require_schema_v4()
        candidate_path = candidate_path.resolve()
        if (
            not candidate_path.exists()
            or not candidate_path.is_file()
            or candidate_path.is_symlink()
        ):
            raise ValueError(
                "P2P372_DECISION_REPAIR_UNSAFE: candidate must be a "
                "regular file"
            )
        proposal_dir = self.find_proposal_dir(proposal_id)
        live_path = proposal_dir / "decision-events.yml"
        proposal_path = proposal_dir / "proposal.md"
        decision_path = proposal_dir / "decision.md"
        live_bytes = live_path.read_bytes()
        proposal_bytes = proposal_path.read_bytes()
        decision_bytes = (
            decision_path.read_bytes() if decision_path.exists() else None
        )
        candidate_bytes = candidate_path.read_bytes()
        candidate = self.codec.loads(
            candidate_bytes,
            expected_proposal_id=proposal_id,
        )
        prefix = self.codec.recover_valid_event_prefix(
            live_bytes,
            expected_proposal_id=proposal_id,
        )
        if len(candidate.events) < len(prefix) or candidate.events[: len(prefix)] != prefix:
            raise ValueError(
                "P2P372_DECISION_REPAIR_UNSAFE: candidate changes, "
                "reorders or removes the maximal valid event prefix"
            )
        permission_bytes = self.permissions.path().read_bytes()
        permission_payload = self._permission_payload(permission_bytes)
        executor_id = executor_actor_id or actor_id
        executor_kind = self.permissions.resolve_actor_payload(
            executor_id,
            permission_payload,
        ).kind
        request = ProposalDecisionRequest(
            proposal_id=proposal_id,
            event_type=ProposalDecisionEventType.deferred,
            reason="Ledger repair.",
            actor_id=actor_id,
            executor_actor_id=executor_id,
            executor_kind=executor_kind,
        )
        owner, executor = self._resolve_authority(request, permission_payload)
        target = self._relative(live_path)
        proposal_target = self._relative(proposal_path)
        decision_target = self._relative(decision_path)
        proposal_candidate = render_proposal_projection(
            proposal_bytes.decode("utf-8"),
            candidate.effective_state,
        ).encode("utf-8")
        decision_candidate = render_decision_projection(
            proposal_id,
            candidate.events[-1] if candidate.events else None,
            empty_state=candidate.effective_state,
        ).encode("utf-8")
        return MutationPreviewService.build(
            operation_id="proposal-decision-ledger-repair",
            targets=(target, proposal_target, decision_target),
            actor=executor.actor_id,
            authority="owner_confirmed",
            sources=(
                source_precondition(target, live_bytes),
                source_precondition(proposal_target, proposal_bytes),
                source_precondition(decision_target, decision_bytes),
                source_precondition(
                    self._relative(self.permissions.path()),
                    permission_bytes,
                ),
            ),
            candidate_semantics={
                target: {
                    "candidate_sha256": self._bytes_sha256(candidate_bytes),
                    "event_count": len(candidate.events),
                    "head_event_id": candidate.head_event_id,
                    "preserved_prefix_count": len(prefix),
                },
                proposal_target: self._bytes_sha256(proposal_candidate),
                decision_target: self._bytes_sha256(decision_candidate),
            },
            semantic_diff={
                "proposal_id": proposal_id,
                "candidate_path": candidate_path.as_posix(),
                "preserved_prefix_count": len(prefix),
                "candidate_event_count": len(candidate.events),
            },
            token_context={
                "proposal_id": proposal_id,
                "permission_policy_sha256": semantic_sha256(permission_payload),
                "owner_id": owner.actor_id,
                "executor_actor_id": executor.actor_id,
                "candidate_physical_sha256": self._bytes_sha256(candidate_bytes),
            },
        )

    def ledger_repair_apply(
        self,
        proposal_id: str,
        *,
        candidate_path: Path,
        actor_id: str,
        executor_actor_id: str | None = None,
        preview_token: str,
        confirm: bool,
    ) -> MutationResult:
        preview = self.ledger_repair_preview(
            proposal_id,
            candidate_path=candidate_path,
            actor_id=actor_id,
            executor_actor_id=executor_actor_id,
        )
        if not confirm:
            return self._mutation_blocked(
                preview,
                "Explicit confirmation is required for ledger repair.",
            )
        if preview.preview_token != preview_token:
            return MutationResult(
                status="stale_preview",
                operation_id=preview.operation_id,
                preview_token=preview.preview_token,
                actor=preview.actor,
                message="P2P365_DECISION_STALE_PREVIEW: repair source changed.",
            )
        candidate_bytes = candidate_path.resolve().read_bytes()
        candidate = self.codec.loads(
            candidate_bytes,
            expected_proposal_id=proposal_id,
        )
        proposal_dir = self.find_proposal_dir(proposal_id)
        proposal_target = self._relative(proposal_dir / "proposal.md")
        decision_target = self._relative(proposal_dir / "decision.md")
        ledger_target = self._relative(proposal_dir / "decision-events.yml")
        proposal_text = (proposal_dir / "proposal.md").read_text(encoding="utf-8")
        candidates = {
            ledger_target: candidate_bytes,
            proposal_target: render_proposal_projection(
                proposal_text,
                candidate.effective_state,
            ).encode("utf-8"),
            decision_target: render_decision_projection(
                proposal_id,
                candidate.events[-1] if candidate.events else None,
                empty_state=candidate.effective_state,
            ).encode("utf-8"),
        }
        return self.atomic_writer.apply(
            operation_id=preview.operation_id,
            candidates=candidates,
            sources=preview.source_preconditions,
            preview_token=preview.preview_token,
            actor=preview.actor,
            candidate_validator=lambda view: self._validate_candidate_view(
                proposal_id,
                view,
                candidates,
            ),
        )

    def _capture(self, proposal_id: str) -> dict[str, object]:
        proposal_dir = self.find_proposal_dir(proposal_id)
        ledger_path = proposal_dir / "decision-events.yml"
        proposal_path = proposal_dir / "proposal.md"
        decision_path = proposal_dir / "decision.md"
        permission_path = self.permissions.path()
        authority_path = self.authority.path
        if not ledger_path.exists():
            raise ValueError(
                "P2P361_DECISION_LEDGER_INVALID: missing decision-events.yml"
            )
        ledger_bytes = ledger_path.read_bytes()
        proposal_bytes = proposal_path.read_bytes()
        decision_bytes = decision_path.read_bytes() if decision_path.exists() else None
        permission_bytes = (
            permission_path.read_bytes() if permission_path.exists() else None
        )
        if not authority_path.is_file() or authority_path.is_symlink():
            raise ValueError(
                "P2P_AUTHORITY_CONTEXT_INVALID: project authority descriptor is missing"
            )
        authority_bytes = authority_path.read_bytes()
        descriptor = self.authority.codec.descriptor_from_bytes(authority_bytes)
        if descriptor.mode == AuthorityMode.local_policy and permission_bytes is None:
            raise ValueError(
                "P2P364_DECISION_OWNER_REQUIRED: project permissions are missing"
            )
        readiness_path = proposal_dir / "readiness.yml"
        return {
            "proposal_dir": proposal_dir,
            "ledger": self.codec.loads(
                ledger_bytes,
                expected_proposal_id=proposal_id,
            ),
            "ledger_bytes": ledger_bytes,
            "proposal_bytes": proposal_bytes,
            "decision_bytes": decision_bytes,
            "permissions_bytes": permission_bytes,
            "authority_bytes": authority_bytes,
            "authority_mode": descriptor.mode.value,
            "readiness_bytes": (
                readiness_path.read_bytes() if readiness_path.exists() else None
            ),
        }

    def _validate_projection_repair_view(self, proposal_id: str, view) -> None:
        ledger_path, proposal_path, decision_path = self._target_paths(
            proposal_id,
            include_readiness=False,
        )
        self._validate_candidate(
            proposal_id,
            {
                ledger_path: view.read_bytes(ledger_path),
                proposal_path: view.read_bytes(proposal_path),
                decision_path: view.read_bytes(decision_path),
            },
        )

    @staticmethod
    def _mutation_blocked(
        preview: MutationPreview,
        message: str,
    ) -> MutationResult:
        return MutationResult(
            status="blocked",
            operation_id=preview.operation_id,
            preview_token=preview.preview_token,
            actor=preview.actor,
            message=message,
        )

    def _normalize_request(
        self,
        request: ProposalDecisionRequest,
        *,
        source_head_event_id: str | None,
    ) -> ProposalDecisionRequest:
        reason = normalize_scalar(request.reason, "reason", 64 * 1024)
        decided_on = request.decided_on or self.clock()
        try:
            date.fromisoformat(decided_on)
        except ValueError as exc:
            raise ValueError(
                "P2P361_DECISION_LEDGER_INVALID: decided_on must be YYYY-MM-DD"
            ) from exc
        validate_conditions(
            request.conditions,
            required=(
                request.event_type
                == ProposalDecisionEventType.accepted_with_changes
            ),
        )
        validate_lineage(
            request.lineage,
            proposal_id=request.proposal_id,
            event_type=request.event_type,
        )
        if (
            request.readiness_override
            and request.event_type != ProposalDecisionEventType.accepted
        ):
            raise ValueError(
                "P2P364_DECISION_OWNER_REQUIRED: readiness override is valid only "
                "for accepted decisions"
            )
        if (
            request.source_head_event_id is not None
            and request.source_head_event_id != source_head_event_id
        ):
            raise ValueError(
                "P2P367_DECISION_CONCURRENT_HEAD: submitted source head does not "
                "match the current ledger"
            )
        base = replace(
            request,
            reason=reason,
            decided_on=decided_on,
            source_head_event_id=source_head_event_id,
        )
        generated_key = operation_key(
            self._operation_semantics(base),
            source_head_event_id,
        )
        selected_key = request.operation_key or generated_key
        if not _OPERATION_KEY.fullmatch(selected_key):
            raise ValueError(
                f"P2P361_DECISION_LEDGER_INVALID: operation key must use "
                f"{OPERATION_KEY_PREFIX}<24 lowercase hex>"
            )
        return replace(base, operation_key=selected_key)

    def _resolve_authority(
        self,
        request: ProposalDecisionRequest,
        permission_payload: Mapping[str, object],
    ):
        owner = self.permissions.resolve_actor_payload(
            request.actor_id,
            permission_payload,
        )
        if owner.role != "owner":
            raise ValueError(
                "P2P364_DECISION_OWNER_REQUIRED: proposal decision apply requires "
                "a current project owner"
            )
        executor = self.permissions.resolve_actor_payload(
            request.executor_actor_id,
            permission_payload,
        )
        if executor.kind != request.executor_kind:
            raise ValueError(
                "P2P364_DECISION_OWNER_REQUIRED: executor kind does not match "
                "project permissions"
            )
        return owner, executor

    def _validate_binding(
        self,
        lifecycle: ProposalDecisionLifecycleView,
        request: ProposalDecisionRequest,
    ) -> None:
        if (
            request.event_type in _ACTIVE_EVENTS
            and lifecycle.proposal_binding_status
            != ProposalDecisionBindingStatus.current
        ):
            raise ValueError(
                "P2P377_DECISION_PROPOSAL_BINDING_DIVERGED: activating decisions "
                "require current proposal semantics"
            )
        if (
            request.event_type in _ACTIVE_TO_INACTIVE
            and lifecycle.proposal_binding_status
            == ProposalDecisionBindingStatus.diverged
            and not request.drift_acknowledged
        ):
            raise ValueError(
                "P2P377_DECISION_PROPOSAL_BINDING_DIVERGED: explicit drift "
                "acknowledgement is required"
            )
        if (
            lifecycle.proposal_binding_status
            == ProposalDecisionBindingStatus.unavailable
        ):
            raise ValueError(
                "P2P377_DECISION_PROPOSAL_BINDING_DIVERGED: proposal semantics "
                "are unavailable"
            )

    def _validate_lineage(self, request: ProposalDecisionRequest) -> None:
        if request.lineage.kind is None:
            return
        for target in request.lineage.targets:
            self.find_proposal_dir(target)
            lifecycle = self.lifecycle.status(target, strict=True)
            if lifecycle.effective_state in _TERMINAL_LINEAGE_STATES:
                raise ValueError(
                    "P2P369_DECISION_LINEAGE_INVALID: target "
                    f"`{target}` is terminally incompatible "
                    f"({lifecycle.effective_state.value})"
                )

    def _affected_decision(
        self,
        request: ProposalDecisionRequest,
        ledger: ProposalDecisionLedger,
        lifecycle: ProposalDecisionLifecycleView,
    ) -> ProposalDecisionAffectedDecision:
        by_id = {item.event_id: item for item in ledger.events}
        if request.event_type in _ACTIVE_TO_INACTIVE and lifecycle.active:
            active_id = (
                lifecycle.intervals[-1].active_event_id
                if lifecycle.intervals
                else ""
            )
            active = by_id.get(active_id)
            if active is None:
                raise ValueError(
                    "P2P361_DECISION_LEDGER_INVALID: active decision event is missing"
                )
            if request.affected_event_id and request.affected_event_id != active.event_id:
                raise ValueError(
                    "P2P368_DECISION_REINSTATEMENT_MISMATCH: affected decision "
                    "reference does not match current authority"
                )
            return ProposalDecisionAffectedDecision(
                event_id=active.event_id,
                decision_semantic_sha256=active.decision_semantic_sha256,
            )
        if request.event_type == ProposalDecisionEventType.reinstated:
            active = by_id.get(request.affected_event_id or "")
            revocation = by_id.get(request.revocation_event_id or "")
            if (
                active is None
                or active.event_type
                not in {
                    ProposalDecisionEventType.accepted,
                    ProposalDecisionEventType.accepted_with_changes,
                }
                or revocation is None
                or revocation.event_type != ProposalDecisionEventType.revoked
                or revocation.event_id != ledger.head_event_id
                or revocation.affected_decision.event_id != active.event_id
            ):
                raise ValueError(
                    "P2P368_DECISION_REINSTATEMENT_MISMATCH: explicit prior active "
                    "and revocation event references are required"
                )
            return ProposalDecisionAffectedDecision(
                event_id=active.event_id,
                decision_semantic_sha256=active.decision_semantic_sha256,
                revocation_event_id=revocation.event_id,
            )
        if request.affected_event_id or request.revocation_event_id:
            raise ValueError(
                "P2P368_DECISION_REINSTATEMENT_MISMATCH: event does not accept "
                "affected decision references"
            )
        return ProposalDecisionAffectedDecision()

    @staticmethod
    def _effective_state(
        request: ProposalDecisionRequest,
        ledger: ProposalDecisionLedger,
        affected: ProposalDecisionAffectedDecision,
    ) -> ProposalDecisionEffectiveState:
        if request.event_type != ProposalDecisionEventType.reinstated:
            return effective_state_for_event(request.event_type)
        restored = next(
            item for item in ledger.events if item.event_id == affected.event_id
        )
        return effective_state_for_event(
            request.event_type,
            restored_state=restored.effective_state,
        )

    @staticmethod
    def _decision_sha(
        request: ProposalDecisionRequest,
        effective_state: ProposalDecisionEffectiveState,
        proposal_sha: str,
        affected: ProposalDecisionAffectedDecision,
    ) -> str:
        if request.event_type in _ACTIVE_TO_INACTIVE or (
            request.event_type == ProposalDecisionEventType.reinstated
        ):
            if affected.decision_semantic_sha256 is None:
                raise ValueError(
                    "P2P361_DECISION_LEDGER_INVALID: affected decision fingerprint "
                    "is required"
                )
            return affected.decision_semantic_sha256
        return decision_semantic_sha256(
            proposal_sha256=proposal_sha,
            outcome=effective_state,
            rationale=request.reason,
            conditions=request.conditions,
        )

    def _impact(
        self,
        request: ProposalDecisionRequest,
        lifecycle: ProposalDecisionLifecycleView,
    ) -> tuple[
        Mapping[str, object],
        ProposalDecisionImpactBinding,
        Mapping[str, bytes | None],
    ]:
        if request.event_type not in _IMPACT_EVENTS:
            return {}, ProposalDecisionImpactBinding(), {}
        if self.impact_provider is None:
            raise ValueError(
                "P2P370_DECISION_IMPACT_INCOMPLETE: no complete impact provider "
                "is configured"
            )
        impact = dict(
            self.impact_provider(
                request.proposal_id,
                request.event_type,
                lifecycle,
            )
        )
        if impact.get("complete") is not True:
            raise ValueError(
                "P2P370_DECISION_IMPACT_INCOMPLETE: dependency capture is incomplete"
            )
        fingerprint = str(
            impact.get("source_fingerprint_sha256")
            or semantic_sha256(impact.get("items") or [])
        )
        total = impact.get("total_count", 0)
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise ValueError(
                "P2P370_DECISION_IMPACT_INCOMPLETE: invalid total_count"
            )
        sources = impact.get("source_bytes") or {}
        if not isinstance(sources, Mapping) or any(
            not isinstance(path, str)
            or (content is not None and not isinstance(content, bytes))
            for path, content in sources.items()
        ):
            raise ValueError(
                "P2P370_DECISION_IMPACT_INCOMPLETE: invalid impact source capture"
            )
        preview_token = str(
            impact.get("preview_token")
            or semantic_sha256(
                {
                    "proposal_id": request.proposal_id,
                    "event_type": request.event_type.value,
                    "source_fingerprint_sha256": fingerprint,
                }
            )
        )
        if request.impact_preview_token and request.impact_preview_token != preview_token:
            raise ValueError(
                "P2P365_DECISION_STALE_PREVIEW: impact preview token changed"
            )
        return (
            {key: value for key, value in impact.items() if key != "source_bytes"},
            ProposalDecisionImpactBinding(
                required=True,
                preview_token=preview_token,
                source_fingerprint_sha256=fingerprint,
                total_count=total,
            ),
            {str(path): content for path, content in sources.items()},
        )

    def _readiness_candidate(
        self,
        request: ProposalDecisionRequest,
        snapshot: Mapping[str, object],
    ) -> tuple[ProposalDecisionReadinessBinding, bytes | None]:
        if not request.readiness_override:
            return ProposalDecisionReadinessBinding(), None
        if self.readiness is None:
            raise ValueError(
                "P2P364_DECISION_OWNER_REQUIRED: readiness override service is "
                "not configured"
            )
        candidate = self.readiness.render_override_candidate(
            request.proposal_id,
            reason=request.reason,
            approver=request.actor_id,
            recorded_on=request.decided_on,
        )
        source = snapshot.get("readiness_bytes")
        return (
            ProposalDecisionReadinessBinding(
                source_fingerprint_sha256=semantic_sha256(
                    {
                        "before": (
                            self._bytes_sha256(source)
                            if isinstance(source, bytes)
                            else None
                        ),
                        "candidate": self._bytes_sha256(candidate),
                    }
                ),
                owner_override=True,
            ),
            candidate,
        )

    def _source_preconditions(
        self,
        snapshot: Mapping[str, object],
        impact_sources: Mapping[str, bytes | None],
        *,
        include_readiness: bool,
        receipt_path: str,
        additional_sources: Sequence[SourcePrecondition] = (),
    ) -> tuple[SourcePrecondition, ...]:
        proposal_dir = snapshot["proposal_dir"]
        assert isinstance(proposal_dir, Path)
        values: dict[str, bytes | None] = {
            self._relative(proposal_dir / "decision-events.yml"): snapshot[
                "ledger_bytes"
            ],
            self._relative(proposal_dir / "proposal.md"): snapshot["proposal_bytes"],
            self._relative(proposal_dir / "decision.md"): snapshot["decision_bytes"],
            self._relative(self.authority.path): snapshot["authority_bytes"],
            receipt_path: None,
        }
        if snapshot.get("authority_mode") == AuthorityMode.local_policy.value:
            values[self._relative(self.permissions.path())] = snapshot[
                "permissions_bytes"
            ]
        if include_readiness or snapshot.get("readiness_bytes") is not None:
            values[self._relative(proposal_dir / "readiness.yml")] = snapshot[
                "readiness_bytes"
            ]
        for path, content in impact_sources.items():
            if path in values and values[path] != content:
                raise ValueError(
                    f"P2P370_DECISION_IMPACT_INCOMPLETE: conflicting capture for {path}"
                )
            values[path] = content
        captured: dict[str, SourcePrecondition] = {}
        for path, content in sorted(values.items()):
            item = source_precondition(path, content)
            captured[item.path] = item
        for item in additional_sources:
            existing = captured.get(item.path)
            if existing is not None and existing != item:
                raise ValueError(
                    "P2P_PROJECT_MEMORY_SCOPE_STALE: conflicting decision source "
                    f"capture for {item.path}"
                )
            captured[item.path] = item
        return tuple(captured[path] for path in sorted(captured))

    def _target_paths(
        self,
        proposal_id: str,
        *,
        include_readiness: bool,
    ) -> tuple[str, ...]:
        proposal_dir = self.find_proposal_dir(proposal_id)
        targets = (
            self._relative(proposal_dir / "decision-events.yml"),
            self._relative(proposal_dir / "proposal.md"),
            self._relative(proposal_dir / "decision.md"),
        )
        if include_readiness:
            return (*targets, self._relative(proposal_dir / "readiness.yml"))
        return targets

    def _validate_candidate(
        self,
        proposal_id: str,
        candidates: Mapping[str, bytes],
        expected_ledger: ProposalDecisionLedger | None = None,
    ) -> None:
        ledger_path, proposal_path, decision_path = self._target_paths(
            proposal_id,
            include_readiness=False,
        )
        ledger = self.codec.loads(
            candidates[ledger_path],
            expected_proposal_id=proposal_id,
        )
        if expected_ledger is not None and ledger != expected_ledger:
            raise ValueError(
                "P2P361_DECISION_LEDGER_INVALID: candidate ledger changed after render"
            )
        proposal_text = candidates[proposal_path].decode("utf-8")
        decision_text = candidates[decision_path].decode("utf-8")
        if (
            render_proposal_projection(proposal_text, ledger.effective_state)
            != proposal_text
        ):
            raise ValueError(
                "P2P362_DECISION_PROJECTION_DIVERGENCE: proposal candidate"
            )
        expected_decision = render_decision_projection(
            proposal_id,
            ledger.events[-1] if ledger.events else None,
            empty_state=ledger.effective_state,
        )
        if expected_decision != decision_text:
            raise ValueError(
                "P2P362_DECISION_PROJECTION_DIVERGENCE: decision candidate"
            )

    def _validate_candidate_view(
        self,
        proposal_id: str,
        view,
        candidate_bytes: Mapping[str, bytes],
    ) -> None:
        targets = self._target_paths(
            proposal_id,
            include_readiness=False,
        )
        captured = {path: view.read_bytes(path) for path in targets}
        self._validate_candidate(proposal_id, captured)
        for path in candidate_bytes:
            if path not in targets:
                view.read_bytes(path)

    def _exact_retry(
        self,
        request: ProposalDecisionRequest,
        preview_token: str,
    ) -> ProposalDecisionApplyResult | None:
        if not request.operation_key:
            return None

        def read_retry_state() -> tuple[
            ProposalDecisionLedger,
            ProposalDecisionEvent | None,
            MutationReceipt | None,
        ]:
            ledger = self._read_ledger(request.proposal_id)
            matching_event = next(
                (
                    event
                    for event in ledger.events
                    if event.operation_key == request.operation_key
                ),
                None,
            )
            receipt_state = self.receipts.read(
                idempotency_key=request.operation_key
            )
            return ledger, matching_event, receipt_state

        try:
            ledger, matching, receipt = read_retry_state()
        except ValueError as exc:
            if not str(exc).startswith("P2P_IDEMPOTENCY_INCOMPLETE_TRANSACTION:"):
                raise
            self._wait_for_competing_decision_mutation()
            ledger, matching, receipt = read_retry_state()
        if matching is None:
            if receipt is not None:
                raise ValueError(
                    "P2P_IDEMPOTENCY_CONFLICT: operation key belongs to another mutation"
                )
            token_owner = next(
                (
                    event
                    for event in ledger.events
                    if event.mutation.preview_token == preview_token
                ),
                None,
            )
            if token_owner is not None:
                raise ValueError(
                    "P2P366_DECISION_REPLAY_MISMATCH: preview token belongs to "
                    "another operation"
                )
            return None
        if receipt is None or receipt.operation != "proposal_decision_apply":
            raise ValueError(
                "P2P_IDEMPOTENCY_RECEIPT_CORRUPT: committed decision receipt is missing"
            )
        receipt_event = receipt.result.get("event")
        if (
            not isinstance(receipt_event, Mapping)
            or receipt_event.get("event_id") != matching.event_id
            or receipt.authority != matching.authority.to_dict()
        ):
            raise ValueError(
                "P2P_IDEMPOTENCY_RECEIPT_CORRUPT: decision event and receipt diverge"
            )
        normalized = self._normalize_retry_request(request)
        evidence = matching.authority
        if request.authority_context is not None:
            if (
                request.authority_context.digest_sha256
                != evidence.authority_context_sha256
            ):
                raise ValueError(
                    "P2P_IDEMPOTENCY_CONFLICT: operation key is already bound "
                    "to different authority evidence"
                )
            retry_context = request.authority_context
        else:
            if evidence.mode != AuthorityMode.local_policy:
                raise ValueError(
                    "P2P366_DECISION_REPLAY_MISMATCH: external decision replay "
                    "requires the original authority context"
                )
            retry_context = authority_context_from_evidence(evidence)
        if (
            request.actor_id != evidence.subject.identity_id
            or request.executor_actor_id != evidence.executor.identity_id
            or request.executor_kind != evidence.executor.kind.value
        ):
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is already bound to "
                "a different subject or executor"
            )
        normalized = replace(normalized, authority_context=retry_context)
        impact = {
            "source_fingerprint_sha256": matching.impact.source_fingerprint_sha256,
            "preview_token": matching.impact.preview_token,
            "total_count": matching.impact.total_count,
            "complete": True,
        }
        request_semantics = self._request_semantics(
            normalized,
            authority=evidence,
            impact=impact if matching.impact.required else {},
            readiness_candidate=None,
            readiness_binding=matching.readiness,
        )
        expected_request_sha = semantic_sha256(request_semantics)
        if (
            matching.mutation.request_fingerprint_sha256 != expected_request_sha
            or matching.mutation.preview_token != preview_token
        ):
            raise ValueError(
                "P2P_IDEMPOTENCY_CONFLICT: operation key is already bound "
                "to different decision semantics"
            )
        lifecycle = lifecycle_from_ledger(ledger)
        return ProposalDecisionApplyResult(
            status="already_applied",
            event=matching,
            lifecycle=lifecycle,
            mutation=MutationResult(
                status="already_applied",
                operation_id=DECISION_MUTATION_OPERATION,
                preview_token=preview_token,
                actor=request.executor_actor_id,
                message="Exact decision operation was already committed.",
            ),
        )

    def _normalize_retry_request(
        self,
        request: ProposalDecisionRequest,
    ) -> ProposalDecisionRequest:
        if not request.decided_on:
            raise ValueError(
                "P2P366_DECISION_REPLAY_MISMATCH: exact retry requires the "
                "decision date returned by preview"
            )
        return replace(
            request,
            reason=normalize_scalar(request.reason, "reason", 64 * 1024),
        )

    @staticmethod
    def _operation_semantics(
        request: ProposalDecisionRequest,
    ) -> dict[str, object]:
        return {
            "proposal_id": request.proposal_id,
            "event_type": request.event_type.value,
            "reason": request.reason,
            "actor_id": request.actor_id,
            "executor_actor_id": request.executor_actor_id,
            "executor_kind": request.executor_kind,
            "channel": request.channel,
            "decided_on": request.decided_on,
            "source_head_event_id": request.source_head_event_id,
            "conditions": [item.to_dict() for item in request.conditions],
            "lineage": request.lineage.to_dict(),
            "affected_event_id": request.affected_event_id,
            "revocation_event_id": request.revocation_event_id,
            "drift_acknowledged": request.drift_acknowledged,
            "readiness_override": request.readiness_override,
            "consent_id": request.consent_id,
            "consent_sha256": request.consent_sha256,
            "authority_context_sha256": (
                request.authority_context.digest_sha256
                if request.authority_context is not None
                else None
            ),
        }

    def _request_semantics(
        self,
        request: ProposalDecisionRequest,
        *,
        authority: AuthorityEvidence,
        impact: Mapping[str, object],
        readiness_candidate: bytes | None,
        readiness_binding: ProposalDecisionReadinessBinding | None = None,
    ) -> dict[str, object]:
        binding = readiness_binding or ProposalDecisionReadinessBinding(
            source_fingerprint_sha256=(
                self._bytes_sha256(readiness_candidate)
                if readiness_candidate is not None
                else None
            ),
            owner_override=request.readiness_override,
        )
        return {
            **self._operation_semantics(request),
            "operation_key": request.operation_key,
            "authority": authority.to_dict(),
            "impact": {
                key: impact.get(key)
                for key in (
                    "source_fingerprint_sha256",
                    "preview_token",
                    "total_count",
                )
            }
            if impact
            else {},
            "readiness": binding.to_dict(),
        }

    @staticmethod
    def _event_token_semantics(
        event: ProposalDecisionEvent,
    ) -> dict[str, object]:
        payload = event.to_dict(include_hash=False)
        mutation = payload.get("mutation")
        if isinstance(mutation, dict):
            mutation = dict(mutation)
            mutation["preview_token"] = "<bound-after-preview>"
            payload["mutation"] = mutation
        payload.pop("event_id", None)
        return payload

    def _lifecycle_from_snapshot(
        self,
        proposal_id: str,
        ledger: ProposalDecisionLedger,
        proposal_text: str,
        decision_bytes: object,
    ) -> ProposalDecisionLifecycleView:
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
        decision_text = (
            decision_bytes.decode("utf-8")
            if isinstance(decision_bytes, bytes)
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

    def _read_ledger(self, proposal_id: str) -> ProposalDecisionLedger:
        proposal_dir = self.find_proposal_dir(proposal_id)
        path = proposal_dir / "decision-events.yml"
        if not path.exists():
            raise ValueError(
                "P2P361_DECISION_LEDGER_INVALID: missing decision-events.yml"
            )
        return self.codec.loads(
            path.read_bytes(),
            expected_proposal_id=proposal_id,
        )

    def _require_schema_v4(self) -> None:
        status = self.workspace_schema_status()
        version = getattr(status, "current_version", None)
        layout = str(getattr(status, "layout_status", "invalid"))
        recovery = getattr(status, "recovery", {})
        active_decision_mutation = (
            isinstance(recovery, Mapping)
            and self._active_decision_mutation(recovery)
        )
        if (
            isinstance(recovery, Mapping)
            and recovery.get("required")
            and not active_decision_mutation
        ):
            raise ValueError(
                "P2P307_WORKSPACE_TRANSACTION_RECOVERY_REQUIRED: recover the active "
                "workspace transaction before decision mutation"
            )
        if version != 4 or layout != "current":
            raise ValueError(
                "P2P375_DECISION_SCHEMA_V4_REQUIRED: proposal decision "
                "event writes require workspace schema v4; this runtime provides no "
                "in-runtime conversion. Run `p2p workspace schema status --format json`."
            )

    def _wait_for_competing_decision_mutation(self) -> None:
        deadline = time.monotonic() + _DECISION_LOCK_WAIT_SECONDS
        while True:
            lock = self.atomic_writer.lock_service.status()
            if lock.state == "absent":
                return
            if not lock.transaction_id.startswith(_DECISION_TRANSACTION_PREFIX):
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.01, remaining))

    def _default_schema_status(self):
        path = self.p2p_dir / "project" / "workspace-schema.yml"
        version = None
        if path.exists():
            payload = load_yaml(path.read_bytes())
            raw = payload.get("workspace_schema") if isinstance(payload, dict) else None
            version = raw.get("current_version") if isinstance(raw, dict) else None
        return type(
            "WorkspaceSchema",
            (),
            {
                "current_version": version,
                "layout_status": "current" if version == 4 else "unsupported",
                "recovery": {},
            },
        )()

    @staticmethod
    def _active_decision_mutation(recovery: Mapping[str, object]) -> bool:
        transaction_id = str(recovery.get("transaction_id") or "")
        lock = recovery.get("lock")
        if (
            not transaction_id.startswith(_DECISION_TRANSACTION_PREFIX)
            or not isinstance(lock, Mapping)
        ):
            return False
        pid = lock.get("pid")
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            return False
        return pid_is_running(pid)

    @staticmethod
    def _permission_payload(content: object) -> dict[str, object]:
        if not isinstance(content, bytes):
            raise ValueError(
                "P2P364_DECISION_OWNER_REQUIRED: project permissions are missing"
            )
        try:
            payload = load_yaml(content)
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(
                "P2P364_DECISION_OWNER_REQUIRED: project permissions are invalid"
            ) from exc
        if not isinstance(payload, dict):
            raise ValueError(
                "P2P364_DECISION_OWNER_REQUIRED: project permissions are invalid"
            )
        return payload

    def _relative(self, path: Path) -> str:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError(f"Unsafe decision source outside project root: {path}")
        return resolved.relative_to(self.root).as_posix()

    @staticmethod
    def _bytes_sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _history_cursor(
        proposal_id: str,
        head_event_id: str | None,
        offset: int,
    ) -> str:
        binding = semantic_sha256(
            {
                "policy_version": DECISION_PREVIEW_POLICY_VERSION,
                "proposal_id": proposal_id,
                "head_event_id": head_event_id,
                "offset": offset,
            }
        )[:16]
        return f"PDC-{offset}-{binding}"

    @classmethod
    def _history_offset(
        cls,
        proposal_id: str,
        head_event_id: str | None,
        cursor: str | None,
    ) -> int:
        if cursor is None:
            return 0
        match = _CURSOR.fullmatch(cursor)
        if match is None:
            raise ValueError("Invalid decision history cursor.")
        offset = int(match.group(1))
        if cls._history_cursor(proposal_id, head_event_id, offset) != cursor:
            raise ValueError(
                "Decision history cursor is stale or belongs to another proposal."
            )
        return offset

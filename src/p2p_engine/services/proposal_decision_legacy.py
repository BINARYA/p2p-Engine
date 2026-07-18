from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAuthorityResolution,
    ProposalDecisionBindingStatus,
    ProposalDecisionEffectiveState,
    ProposalDecisionLegacyEvidence,
    ProposalDecisionLifecycleView,
)
from p2p_engine.foundation.markdown import read_markdown_section
from p2p_engine.services.lifecycle_authority import (
    decision_reconsideration_command,
    proposal_lifecycle_authority,
)
from p2p_engine.services.proposal_decision_ledger import legacy_scalar


_DECIDED_STATES = frozenset(
    {
        "accepted",
        "accepted_with_changes",
        "deferred",
        "withdrawn",
        "rejected",
        "revoked",
        "superseded",
        "split",
        "merged_into_other",
    }
)
_PENDING_STATES = frozenset({"", "draft", "pending", "undecided"})


@dataclass(frozen=True)
class LegacyProposalDecisionSnapshot:
    proposal_id: str
    proposal_path: str
    decision_path: str
    proposal_bytes: bytes | None
    decision_bytes: bytes | None
    proposal_status: str
    decision_status: str
    outcome: str
    reason: str
    approver: str
    decided_on: str
    aligned: bool
    authority_fields_complete: bool
    diagnostics: tuple[str, ...]

    @property
    def normalized_state(self) -> str:
        if self.aligned and self.proposal_status in _DECIDED_STATES:
            return self.proposal_status
        if (
            self.proposal_status in _PENDING_STATES
            and self.decision_status in _PENDING_STATES
        ):
            return "undecided"
        return "unknown_legacy"


class ProposalDecisionLegacyAdapter:
    def capture(
        self,
        *,
        proposal_id: str,
        proposal_path: Path,
        decision_path: Path,
        root: Path,
    ) -> LegacyProposalDecisionSnapshot:
        proposal_bytes = proposal_path.read_bytes() if proposal_path.exists() else None
        decision_bytes = decision_path.read_bytes() if decision_path.exists() else None
        return self.capture_bytes(
            proposal_id=proposal_id,
            proposal_path=_relative(proposal_path, root),
            decision_path=_relative(decision_path, root),
            proposal_bytes=proposal_bytes,
            decision_bytes=decision_bytes,
        )

    def capture_bytes(
        self,
        *,
        proposal_id: str,
        proposal_path: str,
        decision_path: str,
        proposal_bytes: bytes | None,
        decision_bytes: bytes | None,
    ) -> LegacyProposalDecisionSnapshot:
        proposal_text = _decode(proposal_bytes)
        decision_text = _decode(decision_bytes)
        proposal_status = _status(proposal_text, default="draft")
        decision_status = _status(decision_text, default="pending")
        outcome = _section(decision_text, "Outcome") or decision_status
        reason = _section(decision_text, "Reason")
        approver = _section(decision_text, "Approver") or _section(decision_text, "Owner")
        decided_on = _section(decision_text, "Date")
        diagnostics: list[str] = []
        if proposal_bytes is None:
            diagnostics.append("P2P101_MISSING_PROPOSAL_FILE")
        if proposal_text is None and proposal_bytes is not None:
            diagnostics.append("P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED")
        if decision_text is None and decision_bytes is not None:
            diagnostics.append("P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED")
        aligned = _legacy_aligned(proposal_status, decision_status, outcome)
        if not aligned and not (
            proposal_status in _PENDING_STATES
            and decision_status in _PENDING_STATES
        ):
            diagnostics.append("P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED")
        authority_fields_complete = bool(reason and approver and decided_on)
        if aligned and proposal_status in _DECIDED_STATES and not authority_fields_complete:
            diagnostics.append("P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED")
        return LegacyProposalDecisionSnapshot(
            proposal_id=proposal_id,
            proposal_path=proposal_path,
            decision_path=decision_path,
            proposal_bytes=proposal_bytes,
            decision_bytes=decision_bytes,
            proposal_status=proposal_status,
            decision_status=decision_status,
            outcome=outcome,
            reason=reason,
            approver=approver,
            decided_on=decided_on,
            aligned=aligned,
            authority_fields_complete=authority_fields_complete,
            diagnostics=tuple(dict.fromkeys(diagnostics)),
        )

    def lifecycle(self, snapshot: LegacyProposalDecisionSnapshot) -> ProposalDecisionLifecycleView:
        normalized = snapshot.normalized_state
        if normalized == "unknown_legacy":
            return ProposalDecisionLifecycleView(
                proposal_id=snapshot.proposal_id,
                source_model="legacy_projection_v2",
                authority_resolution=ProposalDecisionAuthorityResolution.unknown_legacy,
                effective_state=ProposalDecisionEffectiveState.unknown_legacy,
                head_event_type=None,
                head_event_id=None,
                event_count=0,
                committed=False,
                active=False,
                ever_active=False,
                decision_semantic_sha256=None,
                proposal_semantic_sha256=None,
                proposal_binding_status=ProposalDecisionBindingStatus.unavailable,
                diagnostics=snapshot.diagnostics,
            )
        state = ProposalDecisionEffectiveState(normalized)
        policy = proposal_lifecycle_authority(snapshot.proposal_status)
        ever_active = state in {
            ProposalDecisionEffectiveState.accepted,
            ProposalDecisionEffectiveState.accepted_with_changes,
            ProposalDecisionEffectiveState.revoked,
            ProposalDecisionEffectiveState.superseded,
            ProposalDecisionEffectiveState.split,
            ProposalDecisionEffectiveState.merged_into_other,
        }
        reconsideration_command = decision_reconsideration_command(
            snapshot.proposal_id,
            state,
        )
        diagnostics = snapshot.diagnostics
        if reconsideration_command:
            diagnostics = tuple(
                dict.fromkeys(
                    (
                        *diagnostics,
                        "P2P378_DECISION_RECONSIDERATION_REQUIRES_NEW_PROPOSAL",
                    )
                )
            )
        return ProposalDecisionLifecycleView(
            proposal_id=snapshot.proposal_id,
            source_model="legacy_projection_v2",
            authority_resolution=(
                ProposalDecisionAuthorityResolution.resolved
                if snapshot.normalized_state == "undecided"
                or snapshot.authority_fields_complete
                else ProposalDecisionAuthorityResolution.unknown_legacy
            ),
            effective_state=state,
            head_event_type=None,
            head_event_id=None,
            event_count=0,
            committed=policy.committed,
            active=policy.active_projection,
            ever_active=ever_active,
            decision_semantic_sha256=None,
            proposal_semantic_sha256=None,
            proposal_binding_status=ProposalDecisionBindingStatus.current,
            diagnostics=diagnostics,
            suggested_next_command=reconsideration_command,
        )

    def legacy_evidence(
        self,
        snapshot: LegacyProposalDecisionSnapshot,
        *,
        migration_id: str = "workspace-v2-to-v3",
    ) -> ProposalDecisionLegacyEvidence:
        values: dict[str, object] = {}
        truncated: list[str] = []
        for key, value in (
            ("proposal_status", snapshot.proposal_status),
            ("decision_status", snapshot.decision_status),
            ("outcome", snapshot.outcome),
            ("reason", snapshot.reason or "unknown_legacy"),
            ("approver", snapshot.approver or "unknown_legacy"),
            ("decided_on", snapshot.decided_on or "unknown_legacy"),
        ):
            preserved, was_truncated = legacy_scalar(value)
            values[key] = preserved
            if was_truncated:
                truncated.append(key)
        source_sha256: dict[str, str] = {}
        if snapshot.proposal_bytes is not None:
            source_sha256["proposal.md"] = _sha256(snapshot.proposal_bytes)
        if snapshot.decision_bytes is not None:
            source_sha256["decision.md"] = _sha256(snapshot.decision_bytes)
        diagnostics = snapshot.diagnostics or (
            "P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED",
        )
        return ProposalDecisionLegacyEvidence(
            migration_id=migration_id,
            source_paths=(snapshot.proposal_path, snapshot.decision_path),
            source_sha256=source_sha256,
            values=values,
            diagnostics=diagnostics,
            truncated_fields=tuple(truncated),
        )


def _legacy_aligned(proposal_status: str, decision_status: str, outcome: str) -> bool:
    if proposal_status in _PENDING_STATES and decision_status in _PENDING_STATES:
        return True
    return (
        proposal_status in _DECIDED_STATES
        and proposal_status == decision_status
        and outcome in {proposal_status, ""}
    )


def _decode(content: bytes | None) -> str | None:
    if content is None:
        return ""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _status(text: str | None, *, default: str) -> str:
    value = _section(text, "Status")
    return _normalize_state(value or default)


def _section(text: str | None, section: str) -> str:
    if text is None:
        return ""
    return (read_markdown_section(text, section) or "").strip().strip("`")


def _normalize_state(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest()

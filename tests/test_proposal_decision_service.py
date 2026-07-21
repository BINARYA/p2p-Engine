from __future__ import annotations

import hashlib
import multiprocessing
import os
from pathlib import Path

import pytest
import yaml

from p2p_engine.core.mutation_preview import semantic_sha256
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAuthorityResolution,
    ProposalDecisionCondition,
    ProposalDecisionEffectiveState,
    ProposalDecisionEventType,
    ProposalDecisionLedger,
    ProposalDecisionLegacyEvidence,
    ProposalDecisionRequest,
)
from p2p_engine.services.proposal_decision_ledger import (
    ProposalDecisionLedgerCodec,
    render_decision_projection,
    render_proposal_projection,
)
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace(root: Path) -> tuple[P2PWorkspace, str, Path]:
    workspace = P2PWorkspace(root)
    workspace.init_project("Decision Service", owner="owner")
    proposal = workspace.create_proposal("Governed decision")
    return workspace, proposal.proposal_id, root / proposal.path


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative == ".p2p/.internal" or relative.startswith(".p2p/.internal/"):
            continue
        digest.update(relative.encode("utf-8"))
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _preview(
    workspace: P2PWorkspace,
    proposal_id: str,
    event_type: ProposalDecisionEventType = ProposalDecisionEventType.accepted,
    *,
    reason: str = "Ready.",
    **values,
):
    service = workspace._proposal_decision_service()
    request = service.request(
        proposal_id=proposal_id,
        event_type=event_type,
        reason=reason,
        actor_id="owner",
        **values,
    )
    return service.preview(request)


def _apply(workspace: P2PWorkspace, preview):
    return workspace._proposal_decision_service().apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )


def _complete_impact(*args):
    del args
    return {
        "complete": True,
        "items": [],
        "total_count": 0,
        "source_fingerprint_sha256": semantic_sha256([]),
        "source_bytes": {},
    }


def _seed_unknown_legacy(
    proposal_id: str,
    proposal_dir: Path,
) -> ProposalDecisionLedger:
    ledger = ProposalDecisionLedger(
        contract_version=1,
        proposal_id=proposal_id,
        authority_resolution=ProposalDecisionAuthorityResolution.unknown_legacy,
        effective_state=ProposalDecisionEffectiveState.unknown_legacy,
        head_event_id=None,
        legacy_evidence=(
            ProposalDecisionLegacyEvidence(
                migration_id="workspace-v2-to-v3",
                source_paths=("proposal.md", "decision.md"),
                source_sha256={"proposal.md": "a" * 64, "decision.md": "b" * 64},
                values={
                    "proposal_status": "accepted",
                    "approver": "unknown_legacy",
                },
                diagnostics=("P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED",),
            ),
        ),
    )
    (proposal_dir / "decision-events.yml").write_bytes(
        ProposalDecisionLedgerCodec().dumps(ledger)
    )
    proposal_text = (proposal_dir / "proposal.md").read_text(encoding="utf-8")
    (proposal_dir / "proposal.md").write_text(
        render_proposal_projection(proposal_text, ledger.effective_state),
        encoding="utf-8",
    )
    (proposal_dir / "decision.md").write_text(
        render_decision_projection(
            proposal_id,
            None,
            empty_state=ledger.effective_state,
        ),
        encoding="utf-8",
    )
    return ledger


def _apply_in_process(
    root: str,
    request: ProposalDecisionRequest,
    preview_token: str,
    start: object,
    output: object,
) -> None:
    start.wait(timeout=10)
    workspace = P2PWorkspace(Path(root))
    try:
        result = workspace._proposal_decision_service().apply(
            request,
            preview_token=preview_token,
            confirm=True,
        )
        output.put(("result", result.status))
    except Exception as exc:  # noqa: BLE001 - process boundary returns diagnostics
        output.put(("error", str(exc)))


def _concurrent_apply_results(
    root: Path,
    requests: tuple[tuple[ProposalDecisionRequest, str], ...],
) -> list[tuple[str, str]]:
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    output = context.Queue()
    processes = [
        context.Process(
            target=_apply_in_process,
            args=(str(root), request, preview_token, start, output),
        )
        for request, preview_token in requests
    ]
    for process in processes:
        process.start()
    start.set()
    results = [output.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    return results


def test_preview_is_read_only_and_returns_complete_apply_ingredients(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    before = _tree_digest(tmp_path)

    preview = _preview(workspace, proposal_id)

    assert _tree_digest(tmp_path) == before
    assert preview.request.decided_on
    assert preview.request.operation_key.startswith("P2POP-")
    assert preview.request.source_head_event_id is None
    assert preview.mutation.apply_allowed is True
    assert preview.mutation.confirmation_required is True
    assert preview.event.event_type == ProposalDecisionEventType.accepted
    assert preview.lifecycle.effective_state == ProposalDecisionEffectiveState.accepted
    assert len(preview.candidate_bytes) == 3


def test_apply_atomically_appends_event_and_projects_current_state(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    preview = _preview(workspace, proposal_id)

    result = _apply(workspace, preview)

    assert result.status == "applied"
    ledger = ProposalDecisionLedgerCodec().loads(
        (proposal_dir / "decision-events.yml").read_bytes(),
        expected_proposal_id=proposal_id,
    )
    assert ledger.events == (result.event,)
    assert ledger.head_event_id == result.event.event_id
    assert "## Status\n\n`accepted`" in (
        proposal_dir / "proposal.md"
    ).read_text(encoding="utf-8")
    decision = (proposal_dir / "decision.md").read_text(encoding="utf-8")
    assert f"## Ledger Head\n\n{result.event.event_id}" in decision
    assert "## Canonical Source\n\ndecision-events.yml" in decision


def test_apply_without_confirmation_and_stale_preview_write_nothing(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    preview = _preview(workspace, proposal_id)
    before = {path: path.read_bytes() for path in proposal_dir.iterdir()}

    blocked = service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=False,
    )
    stale = service.apply(
        preview.request,
        preview_token="f" * 64,
        confirm=True,
    )

    assert blocked.status == "blocked"
    assert stale.status == "stale_preview"
    assert {path: path.read_bytes() for path in proposal_dir.iterdir()} == before


def test_exact_retry_returns_existing_event_without_new_write(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    preview = _preview(workspace, proposal_id)
    first = _apply(workspace, preview)
    before = _tree_digest(tmp_path)

    retry = _apply(workspace, preview)

    assert retry.status == "already_applied"
    assert retry.event.event_id == first.event.event_id
    assert _tree_digest(tmp_path) == before
    ledger = ProposalDecisionLedgerCodec().loads(
        (proposal_dir / "decision-events.yml").read_bytes(),
        expected_proposal_id=proposal_id,
    )
    assert len(ledger.events) == 1


def test_exact_retry_uses_preview_date_when_clock_moves_to_next_day(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    service.clock = lambda: "2026-07-17"
    preview = _preview(workspace, proposal_id)
    first = _apply(workspace, preview)
    service.clock = lambda: "2026-07-18"
    before = _tree_digest(tmp_path)

    retry = _apply(workspace, preview)

    assert first.event.decided_on == "2026-07-17"
    assert retry.status == "already_applied"
    assert retry.event.event_id == first.event.event_id
    assert _tree_digest(tmp_path) == before
    ledger = ProposalDecisionLedgerCodec().loads(
        (proposal_dir / "decision-events.yml").read_bytes(),
        expected_proposal_id=proposal_id,
    )
    assert len(ledger.events) == 1


def test_reused_operation_key_with_changed_semantics_is_rejected(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    preview = _preview(workspace, proposal_id)
    _apply(workspace, preview)
    conflicting = service.request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.accepted,
        reason="Different reason.",
        actor_id="owner",
        decided_on=preview.request.decided_on,
        operation_key_value=preview.request.operation_key,
        source_head_event_id=preview.request.source_head_event_id,
    )
    before = _tree_digest(tmp_path)

    with pytest.raises(ValueError, match="P2P366_DECISION_REPLAY_MISMATCH"):
        service.apply(
            conflicting,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )

    assert _tree_digest(tmp_path) == before


def test_two_previews_from_same_head_produce_one_commit_and_one_head_conflict(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    accepted = _preview(workspace, proposal_id, reason="Accept.")
    rejected = _preview(
        workspace,
        proposal_id,
        ProposalDecisionEventType.rejected,
        reason="Reject.",
    )

    assert _apply(workspace, accepted).status == "applied"
    before = _tree_digest(tmp_path)
    with pytest.raises(ValueError, match="P2P367_DECISION_CONCURRENT_HEAD"):
        _apply(workspace, rejected)
    assert _tree_digest(tmp_path) == before


def test_same_request_commit_during_preview_rebuild_becomes_exact_retry(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    preview = _preview(workspace, proposal_id)
    service = workspace._proposal_decision_service()
    original_preview = service._preview
    committed = False

    def preview_after_competing_commit(*args, **kwargs):
        nonlocal committed
        if not committed:
            committed = True
            competing = P2PWorkspace(tmp_path)._proposal_decision_service()
            assert (
                competing.apply(
                    preview.request,
                    preview_token=preview.mutation.preview_token,
                    confirm=True,
                ).status
                == "applied"
            )
        return original_preview(*args, **kwargs)

    service._preview = preview_after_competing_commit  # type: ignore[method-assign]

    result = service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "already_applied"


def test_conflicting_commit_during_preview_rebuild_becomes_head_conflict(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    accepted = _preview(workspace, proposal_id, reason="Accept.")
    rejected = _preview(
        workspace,
        proposal_id,
        ProposalDecisionEventType.rejected,
        reason="Reject.",
    )
    service = workspace._proposal_decision_service()
    original_preview = service._preview
    committed = False

    def preview_after_competing_commit(*args, **kwargs):
        nonlocal committed
        if not committed:
            committed = True
            competing = P2PWorkspace(tmp_path)._proposal_decision_service()
            assert (
                competing.apply(
                    accepted.request,
                    preview_token=accepted.mutation.preview_token,
                    confirm=True,
                ).status
                == "applied"
            )
        return original_preview(*args, **kwargs)

    service._preview = preview_after_competing_commit  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="P2P367_DECISION_CONCURRENT_HEAD"):
        service.apply(
            rejected.request,
            preview_token=rejected.mutation.preview_token,
            confirm=True,
        )


def test_schema_recovery_race_after_conflicting_commit_becomes_head_conflict(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    accepted = _preview(workspace, proposal_id, reason="Accept.")
    rejected = _preview(
        workspace,
        proposal_id,
        ProposalDecisionEventType.rejected,
        reason="Reject.",
    )
    service = workspace._proposal_decision_service()
    original_schema_gate = service._require_schema_v3
    committed = False

    def schema_gate_after_competing_commit() -> None:
        nonlocal committed
        if not committed:
            committed = True
            competing = P2PWorkspace(tmp_path)._proposal_decision_service()
            assert (
                competing.apply(
                    accepted.request,
                    preview_token=accepted.mutation.preview_token,
                    confirm=True,
                ).status
                == "applied"
            )
            raise ValueError(
                "P2P307_WORKSPACE_MIGRATION_RECOVERY_REQUIRED: "
                "simulated transaction cleanup race"
            )
        original_schema_gate()

    service._require_schema_v3 = schema_gate_after_competing_commit  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="P2P367_DECISION_CONCURRENT_HEAD"):
        service.apply(
            rejected.request,
            preview_token=rejected.mutation.preview_token,
            confirm=True,
        )

    ledger = ProposalDecisionLedgerCodec().loads(
        (proposal_dir / "decision-events.yml").read_bytes(),
        expected_proposal_id=proposal_id,
    )
    assert len(ledger.events) == 1


def test_schema_gate_distinguishes_live_decision_lock_from_stale_recovery(
    tmp_path: Path,
) -> None:
    workspace, _, _ = _workspace(tmp_path)
    service = workspace._proposal_decision_service()

    def status_for(pid: int):
        return type(
            "WorkspaceSchema",
            (),
            {
                "current_version": 3,
                "layout_status": "current",
                "recovery": {
                    "required": True,
                    "transaction_id": (
                        "mutation-proposal-decision-apply-test-transaction"
                    ),
                    "lock": {"pid": pid},
                },
            },
        )()

    service.workspace_schema_status = lambda: status_for(os.getpid())
    service._require_schema_v3()

    service.workspace_schema_status = lambda: status_for(2**31 - 1)
    with pytest.raises(
        ValueError,
        match="P2P307_WORKSPACE_MIGRATION_RECOVERY_REQUIRED",
    ):
        service._require_schema_v3()


def test_separate_process_same_request_has_one_commit_and_one_exact_retry(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    preview = _preview(workspace, proposal_id)

    results = _concurrent_apply_results(
        tmp_path,
        (
            (preview.request, preview.mutation.preview_token),
            (preview.request, preview.mutation.preview_token),
        ),
    )

    assert sorted(results) == [
        ("result", "already_applied"),
        ("result", "applied"),
    ]
    ledger = ProposalDecisionLedgerCodec().loads(
        (proposal_dir / "decision-events.yml").read_bytes(),
        expected_proposal_id=proposal_id,
    )
    assert len(ledger.events) == 1


def test_separate_process_conflicting_requests_have_one_winner(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    accepted = _preview(workspace, proposal_id, reason="Accept.")
    rejected = _preview(
        workspace,
        proposal_id,
        ProposalDecisionEventType.rejected,
        reason="Reject.",
    )

    results = _concurrent_apply_results(
        tmp_path,
        (
            (accepted.request, accepted.mutation.preview_token),
            (rejected.request, rejected.mutation.preview_token),
        ),
    )

    assert [kind for kind, _ in results].count("result") == 1
    assert [kind for kind, _ in results].count("error") == 1
    assert any(
        "P2P367_DECISION_CONCURRENT_HEAD" in message
        for kind, message in results
        if kind == "error"
    ), results
    ledger = ProposalDecisionLedgerCodec().loads(
        (proposal_dir / "decision-events.yml").read_bytes(),
        expected_proposal_id=proposal_id,
    )
    assert len(ledger.events) == 1


def test_accepted_decision_cannot_be_overwritten_as_rejected(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    _apply(workspace, _preview(workspace, proposal_id))
    before = {path: path.read_bytes() for path in proposal_dir.iterdir()}

    with pytest.raises(ValueError, match="P2P363_DECISION_TRANSITION_INVALID"):
        _preview(
            workspace,
            proposal_id,
            ProposalDecisionEventType.rejected,
            reason="Changed our mind.",
        )

    assert {path: path.read_bytes() for path in proposal_dir.iterdir()} == before


def test_non_owner_preview_is_rejected_without_writes(tmp_path: Path) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    request = service.request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.accepted,
        reason="Contributor attempt.",
        actor_id="contributor",
    )
    before = _tree_digest(tmp_path)

    with pytest.raises(ValueError, match="P2P364_DECISION_OWNER_REQUIRED"):
        service.preview(request)

    assert _tree_digest(tmp_path) == before


def test_structured_conditions_are_preserved_and_required(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    with pytest.raises(ValueError, match="requires at least one structured condition"):
        _preview(
            workspace,
            proposal_id,
            ProposalDecisionEventType.accepted_with_changes,
        )

    preview = _preview(
        workspace,
        proposal_id,
        ProposalDecisionEventType.accepted_with_changes,
        conditions=(
            ProposalDecisionCondition(
                condition_id="COND-001",
                text="Complete the compatibility documentation.",
            ),
        ),
    )
    result = _apply(workspace, preview)

    assert result.event.conditions == preview.request.conditions
    assert result.lifecycle.effective_state == (
        ProposalDecisionEffectiveState.accepted_with_changes
    )


def test_readiness_override_is_previewed_and_committed_in_same_transaction(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    preview = _preview(
        workspace,
        proposal_id,
        readiness_override=True,
        reason="Owner accepts below target.",
    )
    readiness_path = proposal_dir / "readiness.yml"

    assert not readiness_path.exists()
    assert any(path.endswith("/readiness.yml") for path in preview.mutation.targets)
    result = _apply(workspace, preview)

    assert result.status == "applied"
    assert result.event.readiness.owner_override is True
    readiness = readiness_path.read_text(encoding="utf-8")
    assert "owner_override: true" in readiness
    assert "override_approver: owner" in readiness


@pytest.mark.parametrize(
    "failed_suffix",
    ("decision-events.yml", "decision.md", "proposal.md", "readiness.yml"),
)
def test_failure_after_each_replacement_rolls_back_all_decision_bytes(
    tmp_path: Path,
    failed_suffix: str,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    service = workspace._proposal_decision_service()

    def fail(stage: str, target: str) -> None:
        if stage == "after_replace" and target.endswith(failed_suffix):
            raise RuntimeError("injected decision failure")

    service.atomic_writer = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=fail,
    )
    preview = _preview(
        workspace,
        proposal_id,
        readiness_override=True,
    )
    before = {path: path.read_bytes() for path in proposal_dir.iterdir()}

    result = _apply(workspace, preview)

    assert result.status == "rolled_back"
    assert {path: path.read_bytes() for path in proposal_dir.iterdir()} == before
    assert not (proposal_dir / "readiness.yml").exists()


def test_revocation_and_reinstatement_preserve_active_decision_identity(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    service.impact_provider = _complete_impact
    accepted = _preview(workspace, proposal_id)
    _apply(workspace, accepted)
    revoked = _preview(
        workspace,
        proposal_id,
        ProposalDecisionEventType.revoked,
        reason="Accepted direction is invalid.",
    )
    revoked_result = _apply(workspace, revoked)

    reinstated = _preview(
        workspace,
        proposal_id,
        ProposalDecisionEventType.reinstated,
        reason="The original direction is valid again.",
        affected_event_id=accepted.event.event_id,
        revocation_event_id=revoked.event.event_id,
    )
    reinstated_result = _apply(workspace, reinstated)

    assert revoked_result.lifecycle.active is False
    assert revoked_result.lifecycle.ever_active is True
    assert reinstated_result.lifecycle.active is True
    assert reinstated_result.event.decision_semantic_sha256 == (
        accepted.event.decision_semantic_sha256
    )
    assert reinstated_result.event.affected_decision.revocation_event_id == (
        revoked.event.event_id
    )


def test_history_cursor_is_bounded_and_bound_to_current_head(tmp_path: Path) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    service.impact_provider = _complete_impact
    accepted = _preview(workspace, proposal_id)
    _apply(workspace, accepted)
    revoked = _preview(
        workspace,
        proposal_id,
        ProposalDecisionEventType.revoked,
        reason="Revoke.",
    )
    _apply(workspace, revoked)

    first = service.history(proposal_id, limit=1)
    second = service.history(
        proposal_id,
        limit=1,
        cursor=first.next_cursor,
    )

    assert first.total_count == 2
    assert first.returned_count == 1
    assert first.next_cursor is not None
    assert second.items[0].event_id == revoked.event.event_id
    tampered_cursor = first.next_cursor[:-1] + (
        "0" if first.next_cursor[-1] != "0" else "1"
    )
    with pytest.raises(ValueError, match="stale or belongs"):
        service.history(
            proposal_id,
            limit=1,
            cursor=tampered_cursor,
        )


def test_projection_repair_changes_only_divergent_projection(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    _apply(workspace, _preview(workspace, proposal_id))
    proposal_path = proposal_dir / "proposal.md"
    decision_path = proposal_dir / "decision.md"
    proposal_before = proposal_path.read_bytes()
    decision_path.write_text("corrupt projection\n", encoding="utf-8")
    service = workspace._proposal_decision_service()

    preview = service.projection_repair_preview(
        proposal_id,
        actor_id="owner",
    )
    result = service.projection_repair_apply(
        proposal_id,
        actor_id="owner",
        preview_token=preview.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert preview.targets == (
        decision_path.relative_to(tmp_path).as_posix(),
    )
    assert proposal_path.read_bytes() == proposal_before
    assert "## Canonical Source\n\ndecision-events.yml" in decision_path.read_text(
        encoding="utf-8"
    )
    current = service.projection_repair_preview(
        proposal_id,
        actor_id="owner",
    )
    assert current.apply_allowed is False


@pytest.mark.parametrize(
    ("event_type", "conditions", "expected_state", "expected_active"),
    (
        (
            ProposalDecisionEventType.accepted,
            (),
            ProposalDecisionEffectiveState.accepted,
            True,
        ),
        (
            ProposalDecisionEventType.accepted_with_changes,
            (
                ProposalDecisionCondition(
                    condition_id="COND-001",
                    text="Complete the owner-confirmed condition.",
                ),
            ),
            ProposalDecisionEffectiveState.accepted_with_changes,
            True,
        ),
        (
            ProposalDecisionEventType.deferred,
            (),
            ProposalDecisionEffectiveState.deferred,
            False,
        ),
        (
            ProposalDecisionEventType.withdrawn,
            (),
            ProposalDecisionEffectiveState.withdrawn,
            False,
        ),
        (
            ProposalDecisionEventType.rejected,
            (),
            ProposalDecisionEffectiveState.rejected,
            False,
        ),
    ),
)
def test_legacy_resolution_preserves_evidence_for_each_owner_outcome(
    tmp_path: Path,
    event_type: ProposalDecisionEventType,
    conditions: tuple[ProposalDecisionCondition, ...],
    expected_state: ProposalDecisionEffectiveState,
    expected_active: bool,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    codec = ProposalDecisionLedgerCodec()
    ledger = _seed_unknown_legacy(proposal_id, proposal_dir)
    service = workspace._proposal_decision_service()
    request = service.request(
        proposal_id=proposal_id,
        event_type=event_type,
        reason="Current owner establishes authority now.",
        actor_id="owner",
        decided_on="2026-07-17",
        conditions=conditions,
    )

    with pytest.raises(ValueError, match="P2P360_DECISION_LEGACY"):
        service.preview(request)
    preview = service.legacy_resolution_preview(request)
    result = service.legacy_resolution_apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    repaired = codec.loads(
        (proposal_dir / "decision-events.yml").read_bytes(),
        expected_proposal_id=proposal_id,
    )
    assert repaired.legacy_evidence == ledger.legacy_evidence
    assert repaired.events[0].migration is not None
    assert repaired.events[0].migration.migration_id == "legacy-owner-resolution"
    assert repaired.events[0].decided_on == "2026-07-17"
    assert repaired.authority_resolution == ProposalDecisionAuthorityResolution.resolved
    assert result.lifecycle.effective_state == expected_state
    assert result.lifecycle.active is expected_active
    if expected_active:
        assert result.lifecycle.intervals[0].opened_on == "2026-07-17"
    else:
        assert result.lifecycle.intervals == ()


def test_ledger_repair_rejects_removed_valid_history_and_restores_exact_candidate(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    service.impact_provider = _complete_impact
    accepted = _preview(workspace, proposal_id)
    _apply(workspace, accepted)
    one_event_bytes = (proposal_dir / "decision-events.yml").read_bytes()
    revoked = _preview(
        workspace,
        proposal_id,
        ProposalDecisionEventType.revoked,
        reason="Revoke for repair fixture.",
    )
    _apply(workspace, revoked)
    two_event_bytes = (proposal_dir / "decision-events.yml").read_bytes()
    removed_path = tmp_path / "removed-history.yml"
    removed_path.write_bytes(one_event_bytes)

    with pytest.raises(ValueError, match="maximal valid event prefix"):
        service.ledger_repair_preview(
            proposal_id,
            candidate_path=removed_path,
            actor_id="owner",
        )

    payload = yaml.safe_load(two_event_bytes.decode("utf-8"))
    payload["proposal_decision_ledger"]["events"][-1]["event_sha256"] = "0" * 64
    (proposal_dir / "decision-events.yml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    exact_path = tmp_path / "exact-restoration.yml"
    exact_path.write_bytes(two_event_bytes)
    preview = service.ledger_repair_preview(
        proposal_id,
        candidate_path=exact_path,
        actor_id="owner",
    )
    result = service.ledger_repair_apply(
        proposal_id,
        candidate_path=exact_path,
        actor_id="owner",
        preview_token=preview.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert (proposal_dir / "decision-events.yml").read_bytes() == two_event_bytes
    assert service.status(proposal_id, strict=True).effective_state == (
        ProposalDecisionEffectiveState.revoked
    )


def test_ledger_repair_accepts_a_valid_suffix_without_rewriting_prefix(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    service.impact_provider = _complete_impact
    _apply(workspace, _preview(workspace, proposal_id))
    prefix_bytes = (proposal_dir / "decision-events.yml").read_bytes()
    _apply(
        workspace,
        _preview(
            workspace,
            proposal_id,
            ProposalDecisionEventType.revoked,
            reason="Revoke for valid suffix fixture.",
        ),
    )
    suffix_bytes = (proposal_dir / "decision-events.yml").read_bytes()
    suffix_path = tmp_path / "valid-suffix.yml"
    suffix_path.write_bytes(suffix_bytes)
    prefix = ProposalDecisionLedgerCodec().loads(
        prefix_bytes,
        expected_proposal_id=proposal_id,
    )
    (proposal_dir / "decision-events.yml").write_bytes(prefix_bytes)
    proposal_text = (proposal_dir / "proposal.md").read_text(encoding="utf-8")
    (proposal_dir / "proposal.md").write_text(
        render_proposal_projection(proposal_text, prefix.effective_state),
        encoding="utf-8",
    )
    (proposal_dir / "decision.md").write_text(
        render_decision_projection(proposal_id, prefix.events[-1]),
        encoding="utf-8",
    )

    preview = service.ledger_repair_preview(
        proposal_id,
        candidate_path=suffix_path,
        actor_id="owner",
    )
    result = service.ledger_repair_apply(
        proposal_id,
        candidate_path=suffix_path,
        actor_id="owner",
        preview_token=preview.preview_token,
        confirm=True,
    )

    repaired = ProposalDecisionLedgerCodec().loads(
        (proposal_dir / "decision-events.yml").read_bytes(),
        expected_proposal_id=proposal_id,
    )
    assert result.status == "applied"
    assert repaired.events[:1] == prefix.events
    assert len(repaired.events) == 2
    assert repaired.effective_state == ProposalDecisionEffectiveState.revoked


def test_ledger_repair_rejects_a_valid_candidate_with_changed_prefix(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    _apply(workspace, _preview(workspace, proposal_id, reason="Live acceptance."))
    candidate_root = tmp_path / "candidate-workspace"
    candidate_workspace, candidate_id, candidate_dir = _workspace(candidate_root)
    candidate_service = candidate_workspace._proposal_decision_service()
    candidate_service.impact_provider = _complete_impact
    _apply(
        candidate_workspace,
        _preview(
            candidate_workspace,
            candidate_id,
            reason="Different candidate acceptance.",
        ),
    )
    _apply(
        candidate_workspace,
        _preview(
            candidate_workspace,
            candidate_id,
            ProposalDecisionEventType.revoked,
            reason="Candidate revocation.",
        ),
    )

    with pytest.raises(ValueError, match="maximal valid event prefix"):
        workspace._proposal_decision_service().ledger_repair_preview(
            proposal_id,
            candidate_path=candidate_dir / "decision-events.yml",
            actor_id="owner",
        )


@pytest.mark.parametrize(
    ("mutation", "expected_diagnostic"),
    (
        ("reordered", "P2P361_DECISION_LEDGER_INVALID"),
        ("broken_continuity", "P2P361_DECISION_LEDGER_INVALID"),
        ("future_contract", "P2P376_DECISION_FUTURE_CONTRACT"),
    ),
)
def test_ledger_repair_rejects_structurally_unsafe_candidates(
    tmp_path: Path,
    mutation: str,
    expected_diagnostic: str,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    service.impact_provider = _complete_impact
    _apply(workspace, _preview(workspace, proposal_id))
    _apply(
        workspace,
        _preview(
            workspace,
            proposal_id,
            ProposalDecisionEventType.revoked,
            reason="Revoke for unsafe repair fixture.",
        ),
    )
    payload = yaml.safe_load(
        (proposal_dir / "decision-events.yml").read_text(encoding="utf-8")
    )
    ledger = payload["proposal_decision_ledger"]
    if mutation == "reordered":
        ledger["events"].reverse()
    elif mutation == "broken_continuity":
        ledger["events"][1]["predecessor"]["event_id"] = "PDE-" + "0" * 24
    else:
        ledger["contract_version"] = 99
    candidate_path = tmp_path / f"{mutation}.yml"
    candidate_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=expected_diagnostic):
        service.ledger_repair_preview(
            proposal_id,
            candidate_path=candidate_path,
            actor_id="owner",
        )

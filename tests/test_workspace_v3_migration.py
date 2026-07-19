from __future__ import annotations

import copy
import hashlib
from datetime import date
from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionAuthorityResolution,
    ProposalDecisionEffectiveState,
    ProposalDecisionEventType,
)
from p2p_engine.foundation.markdown import replace_section
from p2p_engine.services.proposal_decision_ledger import ProposalDecisionLedgerCodec
from p2p_engine.services.proposal_decisions import decision_markdown
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.workspace_migration_fixtures import initialize_legacy_workspace


class SimulatedCrash(BaseException):
    pass


def _workspace_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative == ".p2p/.internal" or relative.startswith(".p2p/.internal/"):
            continue
        digest.update(relative.encode("utf-8"))
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _set_schema_version(root: Path, version: int) -> None:
    schema_path = root / ".p2p" / "project" / "workspace-schema.yml"
    payload = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    payload["workspace_schema"]["current_version"] = version
    payload["workspace_schema"]["baseline"] = "initialized_current"
    payload["workspace_schema"]["applied_migrations"] = []
    schema_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _v2_workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Schema v2 fixture", owner="owner")
    _set_schema_version(root, 2)
    return workspace


def _legacy_proposal(
    workspace: P2PWorkspace,
    *,
    title: str,
    proposal_status: str = "draft",
    decision_status: str = "pending",
    outcome: str | None = None,
    reason: str = "",
    approver: str = "",
    decided_on: str = "",
) -> tuple[str, Path]:
    proposal = workspace.create_proposal(title)
    proposal_dir = workspace.root / proposal.path
    proposal_path = proposal_dir / "proposal.md"
    proposal_path.write_text(
        replace_section(
            proposal_path.read_text(encoding="utf-8"),
            "Status",
            f"`{proposal_status}`",
        ),
        encoding="utf-8",
    )
    if (
        decision_status != "pending"
        or outcome is not None
        or reason
        or approver
        or decided_on
    ):
        sections = [
            f"# Decision - {proposal.proposal_id}",
            "",
            "## Status",
            "",
            f"`{decision_status}`",
            "",
            "## Outcome",
            "",
            outcome if outcome is not None else decision_status,
            "",
            "## Reason",
            "",
            reason,
            "",
            "## Date",
            "",
            decided_on,
            "",
            "## Approver",
            "",
            approver,
            "",
        ]
        (proposal_dir / "decision.md").write_text(
            "\n".join(sections),
            encoding="utf-8",
        )
    return proposal.proposal_id, proposal_dir


def _aligned_proposal(
    workspace: P2PWorkspace,
    outcome: DecisionOutcome | str,
    *,
    title: str | None = None,
) -> tuple[str, Path]:
    outcome_value = outcome.value if isinstance(outcome, DecisionOutcome) else outcome
    proposal = workspace.create_proposal(title or f"Legacy {outcome_value}")
    proposal_dir = workspace.root / proposal.path
    proposal_path = proposal_dir / "proposal.md"
    proposal_path.write_text(
        replace_section(
            proposal_path.read_text(encoding="utf-8"),
            "Status",
            f"`{outcome_value}`",
        ),
        encoding="utf-8",
    )
    _legacy_proposal_decision = (
        decision_markdown(
            proposal_id=proposal.proposal_id,
            outcome=outcome,
            reason=f"Legacy {outcome_value} rationale.",
            approver="owner",
            decided_on=date(2026, 7, 17),
        )
        if isinstance(outcome, DecisionOutcome)
        else (
            f"# Decision - {proposal.proposal_id}\n\n"
            "## Status\n\n"
            f"`{outcome_value}`\n\n"
            "## Outcome\n\n"
            f"{outcome_value}\n\n"
            "## Reason\n\n"
            f"Legacy {outcome_value} rationale.\n\n"
            "## Date\n\n"
            "2026-07-17\n\n"
            "## Approver\n\n"
            "owner\n"
        )
    )
    (proposal_dir / "decision.md").write_text(
        _legacy_proposal_decision,
        encoding="utf-8",
    )
    return proposal.proposal_id, proposal_dir


def _canonical_targets(plan) -> list[str]:
    return [item.target for item in plan.operations if item.canonical]


def test_v2_to_v3_plan_is_read_only_deterministic_and_schema_last(
    tmp_path: Path,
) -> None:
    workspace = _v2_workspace(tmp_path)
    proposal_id, proposal_dir = _aligned_proposal(
        workspace,
        DecisionOutcome.accepted,
    )
    before = _workspace_digest(tmp_path)

    first = workspace.workspace_migration_plan(3)
    second = workspace.workspace_migration_plan(3)

    expected_prefix = proposal_dir.relative_to(tmp_path).as_posix()
    assert first.applicable is True
    assert first.migration_ids == ("workspace-v2-to-v3",)
    assert first.fingerprint_sha256 == second.fingerprint_sha256
    assert first.candidate_files == second.candidate_files
    assert _workspace_digest(tmp_path) == before
    assert _canonical_targets(first) == [
        f"{expected_prefix}/decision-events.yml",
        f"{expected_prefix}/proposal.md",
        f"{expected_prefix}/decision.md",
        ".p2p/project/workspace-schema.yml",
    ]
    assert first.operations[-2].target == ".p2p/project/workspace-schema.yml"
    assert first.operations[-1].kind == "refresh_derived"
    assert proposal_id in first.candidate_files[
        f"{expected_prefix}/decision-events.yml"
    ].decode("utf-8")


@pytest.mark.parametrize(
    ("outcome", "event_type", "effective_state"),
    (
        (
            DecisionOutcome.accepted,
            ProposalDecisionEventType.accepted,
            ProposalDecisionEffectiveState.accepted,
        ),
        (
            DecisionOutcome.deferred,
            ProposalDecisionEventType.deferred,
            ProposalDecisionEffectiveState.deferred,
        ),
        (
            "withdrawn",
            ProposalDecisionEventType.withdrawn,
            ProposalDecisionEffectiveState.withdrawn,
        ),
        (
            DecisionOutcome.rejected,
            ProposalDecisionEventType.rejected,
            ProposalDecisionEffectiveState.rejected,
        ),
    ),
)
def test_v2_to_v3_migrates_supported_aligned_decision_with_provenance(
    tmp_path: Path,
    outcome: DecisionOutcome | str,
    event_type: ProposalDecisionEventType,
    effective_state: ProposalDecisionEffectiveState,
) -> None:
    workspace = _v2_workspace(tmp_path)
    proposal_id, proposal_dir = _aligned_proposal(workspace, outcome)

    plan = workspace.workspace_migration_plan(3)
    ledger_path = (
        proposal_dir.relative_to(tmp_path).as_posix() + "/decision-events.yml"
    )
    ledger = ProposalDecisionLedgerCodec().loads(
        plan.candidate_files[ledger_path],
        expected_proposal_id=proposal_id,
    )

    assert ledger.authority_resolution == ProposalDecisionAuthorityResolution.resolved
    assert ledger.effective_state == effective_state
    assert len(ledger.events) == 1
    event = ledger.events[0]
    assert event.event_type == event_type
    assert event.authority.owner_id == "owner"
    assert event.migration is not None
    assert event.migration.migration_id == "workspace-v2-to-v3"
    outcome_value = outcome.value if isinstance(outcome, DecisionOutcome) else outcome
    assert event.migration.preserved_values["reason"] == (
        f"Legacy {outcome_value} rationale."
    )
    assert set(event.migration.source_sha256) == {"proposal.md", "decision.md"}


def test_v2_to_v3_pending_proposal_gets_empty_resolved_ledger(
    tmp_path: Path,
) -> None:
    workspace = _v2_workspace(tmp_path)
    proposal_id, proposal_dir = _legacy_proposal(
        workspace,
        title="Pending legacy",
    )

    plan = workspace.workspace_migration_plan(3)
    ledger = ProposalDecisionLedgerCodec().loads(
        plan.candidate_files[
            proposal_dir.relative_to(tmp_path).as_posix() + "/decision-events.yml"
        ],
        expected_proposal_id=proposal_id,
    )

    assert ledger.authority_resolution == ProposalDecisionAuthorityResolution.resolved
    assert ledger.effective_state == ProposalDecisionEffectiveState.undecided
    assert ledger.events == ()
    assert ledger.legacy_evidence == ()


@pytest.mark.parametrize(
    "legacy_values",
    (
        {
            "proposal_status": "accepted",
            "decision_status": "rejected",
            "outcome": "rejected",
            "reason": "Sources disagree.",
            "approver": "owner",
            "decided_on": "2026-07-17",
        },
        {
            "proposal_status": "accepted",
            "decision_status": "accepted",
            "outcome": "accepted",
            "reason": "",
            "approver": "owner",
            "decided_on": "2026-07-17",
        },
        {
            "proposal_status": "unsupported",
            "decision_status": "unsupported",
            "outcome": "unsupported",
            "reason": "Unknown token.",
            "approver": "owner",
            "decided_on": "2026-07-17",
        },
        {
            "proposal_status": "accepted_with_changes",
            "decision_status": "accepted_with_changes",
            "outcome": "accepted_with_changes",
            "reason": "Legacy source has no structured conditions.",
            "approver": "owner",
            "decided_on": "2026-07-17",
        },
    ),
)
def test_v2_to_v3_preserves_unusable_legacy_authority_without_fabricating_event(
    tmp_path: Path,
    legacy_values: dict[str, str],
) -> None:
    workspace = _v2_workspace(tmp_path)
    proposal_id, proposal_dir = _legacy_proposal(
        workspace,
        title="Unresolved legacy",
        **legacy_values,
    )

    plan = workspace.workspace_migration_plan(3)
    ledger = ProposalDecisionLedgerCodec().loads(
        plan.candidate_files[
            proposal_dir.relative_to(tmp_path).as_posix() + "/decision-events.yml"
        ],
        expected_proposal_id=proposal_id,
    )

    assert plan.applicable is True
    assert ledger.authority_resolution == ProposalDecisionAuthorityResolution.unknown_legacy
    assert ledger.effective_state == ProposalDecisionEffectiveState.unknown_legacy
    assert ledger.events == ()
    assert len(ledger.legacy_evidence) == 1
    evidence = ledger.legacy_evidence[0]
    assert evidence.values["proposal_status"] == legacy_values["proposal_status"]
    assert evidence.values["decision_status"] == legacy_values["decision_status"]
    assert set(evidence.source_sha256) == {"proposal.md", "decision.md"}
    assert any(
        item.code == "P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED"
        for item in plan.findings
    )


def test_attestation_template_is_read_only_and_separates_manual_review(
    tmp_path: Path,
) -> None:
    workspace = _v2_workspace(tmp_path)
    accepted_id, _ = _legacy_proposal(
        workspace,
        title="Legacy accepted by local",
        proposal_status="accepted",
        decision_status="accepted",
        outcome="accepted",
        reason="Reviewed legacy rationale.",
        approver="local",
        decided_on="2026-07-17",
    )
    conditional_id, _ = _legacy_proposal(
        workspace,
        title="Legacy conditional",
        proposal_status="accepted_with_changes",
        decision_status="accepted_with_changes",
        outcome="accepted_with_changes",
        reason="Conditions must be reconstructed explicitly.",
        approver="local",
        decided_on="2026-07-17",
    )
    superseded_id, _ = _legacy_proposal(
        workspace,
        title="Legacy superseded",
        proposal_status="superseded",
        decision_status="superseded",
        outcome="superseded",
        reason="Historical lineage is required.",
        approver="local",
        decided_on="2026-07-17",
    )
    before = _workspace_digest(tmp_path)

    template = workspace.workspace_migration_attestation_template(
        target_version=3,
        owner_id="owner",
    )

    assert _workspace_digest(tmp_path) == before
    assert template.status == "review_required"
    assert template.included_proposal_ids == (accepted_id,)
    attestations = template.owner_input["proposal_decisions"][
        "authority_attestations"
    ]
    assert list(attestations) == [accepted_id]
    reasons = {
        item["proposal_id"]: item["reason"] for item in template.manual_review
    }
    assert reasons == {
        conditional_id: "structured_conditions_required",
        superseded_id: "historical_lineage_required",
    }


def test_v2_to_v3_owner_attestation_creates_source_bound_initial_event(
    tmp_path: Path,
) -> None:
    workspace = _v2_workspace(tmp_path)
    proposal_id, proposal_dir = _legacy_proposal(
        workspace,
        title="Legacy accepted by local",
        proposal_status="accepted",
        decision_status="accepted",
        outcome="accepted",
        reason="Reviewed legacy rationale.",
        approver="local",
        decided_on="2026-07-17",
    )
    base_plan = workspace.workspace_migration_plan(3)
    owner_input = workspace.workspace_migration_attestation_template(
        target_version=3,
        owner_id="owner",
    ).owner_input

    plan = workspace.workspace_migration_plan(3, dict(owner_input))
    ledger_path = (
        proposal_dir.relative_to(tmp_path).as_posix() + "/decision-events.yml"
    )
    ledger = ProposalDecisionLedgerCodec().loads(
        plan.candidate_files[ledger_path],
        expected_proposal_id=proposal_id,
    )

    assert plan.applicable is True
    assert plan.fingerprint_sha256 != base_plan.fingerprint_sha256
    assert ledger.authority_resolution == ProposalDecisionAuthorityResolution.resolved
    assert ledger.effective_state == ProposalDecisionEffectiveState.accepted
    event = ledger.events[0]
    assert event.authority.owner_id == "owner"
    assert event.authority.channel == "workspace_migration_owner_attestation"
    assert event.migration is not None
    assert event.migration.preserved_values["approver"] == "local"
    assert event.migration.preserved_values["owner_attestation"][
        "legacy_approver"
    ] == "local"

    omitted = workspace.workspace_migration_apply(
        target_version=3,
        owner_inputs={},
        plan_fingerprint=plan.fingerprint_sha256,
        actor="owner",
        confirm=True,
    )
    assert omitted.status == "stale_plan"
    assert not (proposal_dir / "decision-events.yml").exists()

    applied = workspace.workspace_migration_apply(
        target_version=3,
        owner_inputs=dict(owner_input),
        plan_fingerprint=plan.fingerprint_sha256,
        actor="owner",
        confirm=True,
    )
    assert applied.status == "applied"
    assert workspace.workspace_schema_status().current_version == 3


@pytest.mark.parametrize("mutation", ("owner", "status", "hash"))
def test_v2_to_v3_attestation_mismatch_blocks_plan(
    tmp_path: Path,
    mutation: str,
) -> None:
    workspace = _v2_workspace(tmp_path)
    _, proposal_dir = _legacy_proposal(
        workspace,
        title="Attestation mismatch",
        proposal_status="accepted",
        decision_status="accepted",
        outcome="accepted",
        reason="Reviewed legacy rationale.",
        approver="local",
        decided_on="2026-07-17",
    )
    owner_input = copy.deepcopy(
        workspace.workspace_migration_attestation_template(
            target_version=3,
            owner_id="owner",
        ).owner_input
    )
    attestation = next(
        iter(
            owner_input["proposal_decisions"]["authority_attestations"].values()
        )
    )
    if mutation == "owner":
        attestation["owner_id"] = "contributor"
    elif mutation == "status":
        attestation["legacy_status"] = "rejected"
    else:
        attestation["source_sha256"]["decision.md"] = "f" * 64

    plan = workspace.workspace_migration_plan(3, owner_input)

    assert plan.applicable is False
    assert any(
        item.code == "P2P390_MIGRATION_ATTESTATION_INVALID"
        for item in plan.findings
    )
    assert not (proposal_dir / "decision-events.yml").exists()
    assert workspace.workspace_schema_status().current_version == 2


def test_v2_to_v3_conditional_attestation_requires_and_preserves_conditions(
    tmp_path: Path,
) -> None:
    workspace = _v2_workspace(tmp_path)
    proposal_id, proposal_dir = _legacy_proposal(
        workspace,
        title="Legacy conditional",
        proposal_status="accepted_with_changes",
        decision_status="accepted_with_changes",
        outcome="accepted_with_changes",
        reason="Owner reconstructed explicit conditions.",
        approver="davide",
        decided_on="2026-07-17",
    )
    proposal_bytes = (proposal_dir / "proposal.md").read_bytes()
    decision_bytes = (proposal_dir / "decision.md").read_bytes()
    owner_input = {
        "proposal_decisions": {
            "attestation_contract_version": 1,
            "authority_attestations": {
                proposal_id: {
                    "owner_id": "owner",
                    "legacy_status": "accepted_with_changes",
                    "legacy_approver": "davide",
                    "decided_on": "2026-07-17",
                    "source_sha256": {
                        "proposal.md": hashlib.sha256(proposal_bytes).hexdigest(),
                        "decision.md": hashlib.sha256(decision_bytes).hexdigest(),
                    },
                    "conditions": [
                        {
                            "id": "C001",
                            "text": "Preserve this explicit acceptance condition.",
                        }
                    ],
                }
            },
        }
    }

    plan = workspace.workspace_migration_plan(3, owner_input)
    ledger = ProposalDecisionLedgerCodec().loads(
        plan.candidate_files[
            proposal_dir.relative_to(tmp_path).as_posix() + "/decision-events.yml"
        ],
        expected_proposal_id=proposal_id,
    )

    assert plan.applicable is True
    assert (
        ledger.effective_state
        == ProposalDecisionEffectiveState.accepted_with_changes
    )
    assert [item.to_dict() for item in ledger.events[0].conditions] == [
        {
            "id": "C001",
            "text": "Preserve this explicit acceptance condition.",
        }
    ]


def test_v2_to_v3_source_edit_after_attestation_blocks_apply(
    tmp_path: Path,
) -> None:
    workspace = _v2_workspace(tmp_path)
    _, proposal_dir = _legacy_proposal(
        workspace,
        title="Stale attestation",
        proposal_status="accepted",
        decision_status="accepted",
        outcome="accepted",
        reason="Reviewed legacy rationale.",
        approver="local",
        decided_on="2026-07-17",
    )
    owner_input = workspace.workspace_migration_attestation_template(
        target_version=3,
        owner_id="owner",
    ).owner_input
    plan = workspace.workspace_migration_plan(3, dict(owner_input))
    decision_path = proposal_dir / "decision.md"
    decision_path.write_bytes(decision_path.read_bytes() + b"\n")

    result = workspace.workspace_migration_apply(
        target_version=3,
        owner_inputs=dict(owner_input),
        plan_fingerprint=plan.fingerprint_sha256,
        actor="owner",
        confirm=True,
    )

    assert result.status == "blocked"
    assert not (proposal_dir / "decision-events.yml").exists()
    assert workspace.workspace_schema_status().current_version == 2


def test_v2_to_v3_lock_time_source_change_returns_stale_plan(
    tmp_path: Path,
) -> None:
    workspace = _v2_workspace(tmp_path)
    _, proposal_dir = _legacy_proposal(
        workspace,
        title="Lock-time staleness",
        proposal_status="accepted",
        decision_status="accepted",
        outcome="accepted",
        reason="Reviewed legacy rationale.",
        approver="local",
        decided_on="2026-07-17",
    )
    owner_input = workspace.workspace_migration_attestation_template(
        target_version=3,
        owner_id="owner",
    ).owner_input
    reviewed_plan = workspace.workspace_migration_plan(3, dict(owner_input))
    compatibility = workspace._workspace_compatibility_service()
    original_plan = compatibility.plan
    calls = 0

    def plan_then_change_source(*args, **kwargs):
        nonlocal calls
        result = original_plan(*args, **kwargs)
        calls += 1
        if calls == 1:
            decision_path = proposal_dir / "decision.md"
            decision_path.write_bytes(decision_path.read_bytes() + b"\n")
        return result

    compatibility.plan = plan_then_change_source  # type: ignore[method-assign]

    result = workspace.workspace_migration_apply(
        target_version=3,
        owner_inputs=dict(owner_input),
        plan_fingerprint=reviewed_plan.fingerprint_sha256,
        actor="owner",
        confirm=True,
    )

    assert result.status == "stale_plan"
    assert not (proposal_dir / "decision-events.yml").exists()
    assert workspace.workspace_schema_status().current_version == 2
    assert workspace.workspace_migration_recovery_status().required is False


def test_schema_v2_validation_preserves_unknown_legacy_diagnostic_identity(
    tmp_path: Path,
) -> None:
    workspace = _v2_workspace(tmp_path)
    proposal_id, proposal_dir = _legacy_proposal(
        workspace,
        title="Incomplete legacy authority",
        proposal_status="accepted",
        decision_status="accepted",
        outcome="accepted",
        reason="Legacy rationale.",
        approver="owner",
    )

    result = workspace.validate()
    finding = next(
        item
        for item in result.findings
        if item.code == "P2P360_DECISION_LEGACY_AUTHORITY_UNRESOLVED"
    )

    assert finding.severity == "error"
    assert finding.path == (
        proposal_dir.relative_to(tmp_path) / "decision.md"
    )
    assert finding.suggested_command == (
        "p2p workspace migrate plan --to 3 --format json"
    )
    assert not any(
        item.code == "P2P361_DECISION_LEDGER_INVALID"
        and proposal_id in item.suggested_command
        for item in result.findings
    )


def test_v2_to_v3_apply_is_atomic_and_post_apply_is_no_op(tmp_path: Path) -> None:
    workspace = _v2_workspace(tmp_path)
    proposal_id, proposal_dir = _aligned_proposal(
        workspace,
        DecisionOutcome.accepted,
    )
    plan = workspace.workspace_migration_plan(3)

    result = workspace.workspace_migration_apply(
        target_version=3,
        owner_inputs={},
        plan_fingerprint=plan.fingerprint_sha256,
        actor="owner",
        confirm=True,
    )

    assert result.status == "applied"
    assert result.changed_paths[-1] == ".p2p/project/workspace-schema.yml"
    assert workspace.workspace_schema_status().current_version == 3
    assert workspace.workspace_schema_status().state == "current"
    ledger = ProposalDecisionLedgerCodec().loads(
        (proposal_dir / "decision-events.yml").read_bytes(),
        expected_proposal_id=proposal_id,
    )
    assert ledger.effective_state == ProposalDecisionEffectiveState.accepted
    assert workspace.workspace_migration_plan(3).status == "no_op"


@pytest.mark.parametrize(
    "failed_suffix",
    (
        "decision-events.yml",
        "proposal.md",
        "decision.md",
        "workspace-schema.yml",
    ),
)
def test_v2_to_v3_failure_after_each_replace_restores_exact_v2_bytes(
    tmp_path: Path,
    failed_suffix: str,
) -> None:
    workspace = _v2_workspace(tmp_path)
    _, proposal_dir = _aligned_proposal(workspace, DecisionOutcome.accepted)
    tracked = (
        proposal_dir / "proposal.md",
        proposal_dir / "decision.md",
        tmp_path / ".p2p" / "project" / "workspace-schema.yml",
    )
    originals = {path: path.read_bytes() for path in tracked}

    def fail(stage: str, target: str) -> None:
        if stage == "after_replace" and target.endswith(failed_suffix):
            raise RuntimeError("injected schema-v3 failure")

    migration = workspace._workspace_migration_service()
    migration.failure_injector = fail
    plan = workspace.workspace_migration_plan(3)
    result = workspace.workspace_migration_apply(
        target_version=3,
        owner_inputs={},
        plan_fingerprint=plan.fingerprint_sha256,
        actor="owner",
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert not (proposal_dir / "decision-events.yml").exists()
    assert {path: path.read_bytes() for path in tracked} == originals
    assert workspace.workspace_migration_recovery_status().required is False


def test_v2_to_v3_interrupted_transaction_can_be_resumed(tmp_path: Path) -> None:
    workspace = _v2_workspace(tmp_path)
    _, proposal_dir = _aligned_proposal(workspace, DecisionOutcome.accepted)

    def crash(stage: str, target: str) -> None:
        if stage == "after_replace" and target.endswith("decision-events.yml"):
            raise SimulatedCrash()

    migration = workspace._workspace_migration_service()
    migration.failure_injector = crash
    plan = workspace.workspace_migration_plan(3)
    with pytest.raises(SimulatedCrash):
        workspace.workspace_migration_apply(
            target_version=3,
            owner_inputs={},
            plan_fingerprint=plan.fingerprint_sha256,
            actor="owner",
            confirm=True,
        )

    recovery = workspace.workspace_migration_recovery_status()
    resumed = workspace.workspace_migration_resume(
        transaction_id=recovery.transaction_id,
        actor="owner",
        confirm=True,
    )

    assert resumed.status == "applied"
    assert (proposal_dir / "decision-events.yml").exists()
    assert workspace.workspace_schema_status().current_version == 3
    assert workspace.workspace_migration_recovery_status().required is False


def test_composed_legacy_to_v3_keeps_adjacent_migration_history(
    tmp_path: Path,
) -> None:
    initialize_legacy_workspace(tmp_path, owner="owner")
    workspace = P2PWorkspace(tmp_path)
    plan = workspace.workspace_migration_plan(
        3,
        owner_inputs={
            "vertical": {"id": "base_project"},
            "owner": {"id": "owner", "name": "owner"},
        },
    )

    assert plan.applicable is True
    assert plan.migration_ids == (
        "workspace-legacy-to-v1",
        "workspace-v1-to-v2",
        "workspace-v2-to-v3",
    )
    schema = yaml.safe_load(
        plan.candidate_files[".p2p/project/workspace-schema.yml"]
    )
    history = schema["workspace_schema"]["applied_migrations"]
    assert [(item["from"], item["to"]) for item in history] == [
        ("legacy_undeclared", 1),
        (1, 2),
        (2, 3),
    ]

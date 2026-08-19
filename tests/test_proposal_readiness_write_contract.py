from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import p2p_engine.storage.filesystem as filesystem_module
from p2p_engine.cli import app
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.readiness import default_readiness_profile_payload
from p2p_engine.services.mutation_receipts import MutationReceiptService
from p2p_engine.services.workspace_transactions import (
    AtomicMutationWriter,
    WorkspaceTransactionLockService,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data, cli_error


runner = CliRunner()


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _workspace_with_proposal(root: Path) -> tuple[P2PWorkspace, str]:
    workspace = P2PWorkspace(root)
    workspace.init_project(
        "Readiness Write Contract",
        owner="owner",
        vertical_id="base_project",
    )
    proposal = workspace.create_proposal_with_details(
        title="Receipt-backed readiness",
        problem="WaveKit needs a retry-safe proposal readiness mutation.",
        context="A worker may lose the command response after state is committed.",
        goals=["Return a typed readiness result with a durable receipt."],
        non_goals=["Do not decide the proposal."],
        proposal="Assess current proposal evidence in one atomic transaction.",
        acceptance_criteria=["Exact retry returns the original applied result."],
    )
    return workspace, proposal.proposal_id


def _assess_json(root: Path, proposal_id: str, key: str, *, actor: str = "wavekit"):
    return runner.invoke(
        app,
        [
            "proposal",
            "readiness",
            "assess",
            proposal_id,
            "--actor",
            actor,
            "--operation-key",
            key,
            "--format",
            "json",
            "--root",
            str(root),
        ],
    )


def test_readiness_assess_json_writes_receipt_and_replays_without_writes(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    key = "wavekit:readiness:00000000-0000-4000-8000-000000000001"

    result = _assess_json(tmp_path, proposal_id, key)

    assert result.exit_code == 0, result.output
    data = cli_data(result, operation="proposal.readiness.assess")
    assessment = data["proposal_readiness_assess"]
    readiness = assessment["readiness"]
    assert assessment["proposal_id"] == proposal_id
    assert readiness["status"] == "assessed"
    assert readiness["freshness"] == "current"
    assert readiness["assessment_policy_version"] == 1
    assert len(readiness["source_fingerprint_sha256"]) == 64
    assert data["mutation"]["status"] == "applied"
    assert data["mutation"]["operation_id"] == "proposal.readiness.assess"

    status = workspace.mutation_status(idempotency_key=key)
    assert status.state == "applied"
    assert status.operation == "proposal_readiness_assess"
    assert status.result["readiness"]["source_fingerprint_sha256"] == readiness[
        "source_fingerprint_sha256"
    ]
    before = _hash_tree(tmp_path)

    replay = _assess_json(tmp_path, proposal_id, key)

    assert replay.exit_code == 0, replay.output
    replay_data = cli_data(replay, operation="proposal.readiness.assess")
    assert replay_data["mutation"]["status"] == "already_applied"
    assert replay_data["proposal_readiness_assess"] == assessment
    assert _hash_tree(tmp_path) == before


def test_readiness_assess_json_matches_observed_golden_contract(
    tmp_path: Path,
) -> None:
    _workspace, proposal_id = _workspace_with_proposal(tmp_path)
    result = _assess_json(tmp_path, proposal_id, "wavekit:readiness:golden")
    assert result.exit_code == 0, result.output
    observed = json.loads(result.stdout)
    fingerprint = observed["data"]["proposal_readiness_assess"]["readiness"][
        "source_fingerprint_sha256"
    ]
    assert len(fingerprint) == 64
    observed["data"]["proposal_readiness_assess"]["readiness"][
        "source_fingerprint_sha256"
    ] = "<sha256>"
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "cli_contract"
        / "proposal-readiness-assess-v1.json"
    )
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert observed == expected


def test_readiness_assess_exact_retry_survives_later_evidence_drift(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    key = "wavekit:readiness:00000000-0000-4000-8000-000000000002"
    applied = _assess_json(tmp_path, proposal_id, key)
    assert applied.exit_code == 0, applied.output
    original = cli_data(applied, operation="proposal.readiness.assess")
    proposal_path = tmp_path / workspace.show_proposal(proposal_id).path / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8")
        + "\nAdditional evidence added after the successful assessment.\n",
        encoding="utf-8",
    )

    detail = workspace.proposal_detail_contract(proposal_id)
    assert detail["readiness"]["freshness"] == "stale"
    assert (
        detail["readiness"]["source_fingerprint_sha256"]
        != detail["readiness"]["current_source_fingerprint_sha256"]
    )
    assert workspace.mutation_status(idempotency_key=key).state == "applied"
    before_retry = _hash_tree(tmp_path)

    replay = _assess_json(tmp_path, proposal_id, key)

    assert replay.exit_code == 0, replay.output
    replay_data = cli_data(replay, operation="proposal.readiness.assess")
    assert replay_data["mutation"]["status"] == "already_applied"
    assert replay_data["proposal_readiness_assess"] == original[
        "proposal_readiness_assess"
    ]
    assert _hash_tree(tmp_path) == before_retry


def test_readiness_assess_json_rejects_divergent_key_reuse_without_writes(
    tmp_path: Path,
) -> None:
    _workspace, proposal_id = _workspace_with_proposal(tmp_path)
    key = "wavekit:readiness:00000000-0000-4000-8000-000000000003"
    first = _assess_json(tmp_path, proposal_id, key)
    assert first.exit_code == 0, first.output
    before = _hash_tree(tmp_path)

    conflict = _assess_json(tmp_path, proposal_id, key, actor="different-actor")

    assert conflict.exit_code == 3
    error = cli_error(conflict, operation="proposal.readiness.assess")
    assert error["code"] == "P2P_IDEMPOTENCY_CONFLICT"
    assert _hash_tree(tmp_path) == before


def test_readiness_assess_json_requires_operation_key(tmp_path: Path) -> None:
    _workspace, proposal_id = _workspace_with_proposal(tmp_path)

    result = runner.invoke(
        app,
        [
            "proposal",
            "readiness",
            "assess",
            proposal_id,
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    error = cli_error(result, operation="proposal.readiness.assess")
    assert error["code"] == "P2P_IDEMPOTENCY_KEY_REQUIRED"


def test_readiness_assess_json_rejects_oversized_operation_key(
    tmp_path: Path,
) -> None:
    _workspace, proposal_id = _workspace_with_proposal(tmp_path)

    result = _assess_json(tmp_path, proposal_id, "x" * 257)

    assert result.exit_code == 2
    assert cli_error(result)["code"] == "P2P_IDEMPOTENCY_KEY_INVALID"


def test_readiness_assess_json_reports_missing_proposal_without_writes(
    tmp_path: Path,
) -> None:
    _workspace, _proposal_id = _workspace_with_proposal(tmp_path)
    before = _hash_tree(tmp_path)

    result = _assess_json(
        tmp_path,
        "PROP-999",
        "wavekit:readiness:00000000-0000-4000-8000-000000000010",
    )

    assert result.exit_code == 2
    assert cli_error(result)["code"] == "P2P_PROPOSAL_NOT_FOUND"
    assert _hash_tree(tmp_path) == before


def test_readiness_assess_json_reports_busy_workspace_without_writes(
    tmp_path: Path,
) -> None:
    _workspace, proposal_id = _workspace_with_proposal(tmp_path)
    lock = WorkspaceTransactionLockService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
    )
    acquired = lock.acquire("readiness-busy-test", owner="other-writer")
    try:
        result = _assess_json(
            tmp_path,
            proposal_id,
            "wavekit:readiness:00000000-0000-4000-8000-000000000011",
        )
    finally:
        lock.release(acquired.transaction_id)

    assert result.exit_code == 3
    assert cli_error(result)["code"] == (
        "P2P_PROPOSAL_READINESS_ASSESS_BUSY_LOCKED"
    )
    assert P2PWorkspace(tmp_path).read_proposal_readiness(proposal_id).status == (
        "not_assessed"
    )
    assert P2PWorkspace(tmp_path).mutation_status(
        idempotency_key="wavekit:readiness:00000000-0000-4000-8000-000000000011"
    ).state == "not_found"


def test_readiness_assess_json_rejects_invalid_canonical_source(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    workspace.initialize_proposal_questions(proposal_id)
    questions_path = tmp_path / workspace.show_proposal(proposal_id).path / "questions.yml"
    questions_path.write_bytes(b"proposal_questions: [invalid")
    before = _hash_tree(tmp_path)

    result = _assess_json(
        tmp_path,
        proposal_id,
        "wavekit:readiness:00000000-0000-4000-8000-000000000012",
    )

    assert result.exit_code == 2
    assert cli_error(result)["code"] == "P2P_READINESS_SOURCE_INVALID"
    assert _hash_tree(tmp_path) == before


def test_readiness_plan_and_freshness_reads_do_not_write(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    before_missing_read = _hash_tree(tmp_path)
    missing = workspace.read_proposal_readiness(proposal_id)
    assert missing.freshness == "not_assessed"
    assert _hash_tree(tmp_path) == before_missing_read
    before_plan = _hash_tree(tmp_path)

    plan = workspace._readiness_service().plan_assessment(proposal_id)

    assert _hash_tree(tmp_path) == before_plan
    source_paths = {item.path for item in plan.source_preconditions}
    assert any(path.endswith("/proposal.md") for path in source_paths)
    assert any(path.endswith("/questions.yml") for path in source_paths)
    assert any(path.endswith("/artifact-state.yml") for path in source_paths)
    assert any(path.endswith("/readiness.yml") for path in source_paths)
    assert any("readiness-profiles" in path for path in source_paths)

    workspace.assess_proposal_readiness(proposal_id)
    before_read = _hash_tree(tmp_path)
    readiness = workspace.read_proposal_readiness(proposal_id)
    detail = workspace.proposal_detail_contract(proposal_id)

    assert readiness.freshness == "current"
    assert detail["readiness"]["freshness"] == "current"
    assert _hash_tree(tmp_path) == before_read

    proposal_path = tmp_path / workspace.show_proposal(proposal_id).path / "proposal.md"
    proposal_path.write_bytes(proposal_path.read_bytes() + b"\nNew evidence.\n")
    before_stale_read = _hash_tree(tmp_path)
    stale = workspace.read_proposal_readiness(proposal_id)
    assert stale.freshness == "stale"
    assert _hash_tree(tmp_path) == before_stale_read


def test_readiness_fingerprint_ignores_unrelated_files(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    workspace.assess_proposal_readiness(proposal_id)
    before = workspace.read_proposal_readiness(proposal_id)
    unrelated = tmp_path / workspace.show_proposal(proposal_id).path / "notes.tmp"

    unrelated.write_text("Not an assessment input.\n", encoding="utf-8")
    after = workspace.read_proposal_readiness(proposal_id)

    assert before.source_fingerprint_sha256 == after.current_source_fingerprint_sha256
    assert after.freshness == "current"


@pytest.mark.parametrize(
    "source_suffix",
    [
        "readiness-profiles/default-readiness-v0.1.yml",
        "proposal.md",
        "suggested-scope.md",
        "alternatives.md",
        "findings.md",
        "risks.md",
        "assumptions.md",
        "execution-plan.md",
        "impact-map.yml",
        "questions.yml",
        "artifact-state.yml",
    ],
)
def test_each_declared_readiness_source_makes_assessment_stale(
    tmp_path: Path,
    source_suffix: str,
) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    workspace.initialize_proposal_questions(proposal_id)
    workspace.assess_proposal_readiness(proposal_id)
    plan = workspace._readiness_service().plan_assessment(proposal_id)
    source = next(
        item for item in plan.source_preconditions if item.path.endswith(source_suffix)
    )
    path = tmp_path / source.path
    marker = b"\n# Changed readiness source.\n" if path.suffix == ".yml" else b"\nChanged evidence.\n"
    path.write_bytes((path.read_bytes() if path.exists() else b"") + marker)

    readiness = workspace.read_proposal_readiness(proposal_id)

    assert readiness.freshness == "stale"
    assert (
        readiness.source_fingerprint_sha256
        != readiness.current_source_fingerprint_sha256
    )


def test_readiness_assessment_preserves_owner_override(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    workspace.assess_proposal_readiness(proposal_id)
    workspace.record_proposal_readiness_override(
        proposal_id,
        "Owner accepts the documented residual risk.",
        "owner",
    )

    result = _assess_json(
        tmp_path,
        proposal_id,
        "wavekit:readiness:00000000-0000-4000-8000-000000000004",
    )

    assert result.exit_code == 0, result.output
    readiness_path = tmp_path / workspace.show_proposal(proposal_id).path / "readiness.yml"
    readiness = yaml.safe_load(readiness_path.read_text(encoding="utf-8"))["readiness"]
    assert readiness["owner_override"] is True
    assert readiness["effective_status"] == "forced_ready"
    assert readiness["effective_score"] == 100
    assert readiness["override_reason"] == "Owner accepts the documented residual risk."
    assert readiness["override_approver"] == "owner"


def test_readiness_assessment_uses_selected_existing_profile(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    profile_payload = default_readiness_profile_payload()
    profile_payload["readiness_profile"]["id"] = "custom-readiness"
    profile_payload["readiness_profile"]["version"] = "1.0"
    profile_path = (
        tmp_path
        / ".p2p"
        / "config"
        / "readiness-profiles"
        / "custom-readiness.yml"
    )
    profile_path.write_text(
        yaml.safe_dump(profile_payload, sort_keys=False),
        encoding="utf-8",
    )
    workspace.write_proposal_readiness(
        proposal_id,
        {
            "status": "assessed",
            "profile_id": "custom-readiness",
            "profile_version": "1.0",
            "computed_score": 0,
            "computed_label": "weak",
            "confidence": "low",
            "failed_gates": [],
            "missing": [],
            "suggested_next": [],
            "criteria": {},
        },
    )

    plan = workspace._readiness_service().plan_assessment(proposal_id)

    assert plan.profile_id == "custom-readiness"
    assert plan.profile_version == "1.0"
    assert any(item.path.endswith("custom-readiness.yml") for item in plan.source_preconditions)


def test_readiness_receipt_corruption_and_postcondition_drift_fail_closed(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    key = "wavekit:readiness:00000000-0000-4000-8000-000000000005"
    applied = _assess_json(tmp_path, proposal_id, key)
    assert applied.exit_code == 0, applied.output
    readiness_path = tmp_path / workspace.show_proposal(proposal_id).path / "readiness.yml"
    readiness_path.write_bytes(readiness_path.read_bytes() + b"\n")

    assert workspace.mutation_status(idempotency_key=key).state == "postcondition_drift"
    drifted = _assess_json(tmp_path, proposal_id, key)
    assert drifted.exit_code == 3
    assert cli_error(drifted)["code"] == "P2P_IDEMPOTENCY_POSTCONDITION_DRIFT"

    service = MutationReceiptService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    receipt_path = tmp_path / service.relative_path(key)
    receipt_path.write_bytes(b"not: [valid")
    corrupt = _assess_json(tmp_path, proposal_id, key)
    assert corrupt.exit_code == 1
    assert cli_error(corrupt)["code"] == "P2P_IDEMPOTENCY_RECEIPT_CORRUPT"
    assert key not in corrupt.output


@pytest.mark.parametrize(
    "failure_stage,target_suffix",
    [
        ("before_journal", ""),
        ("after_replace", "mutation-receipts"),
        ("after_replace", "readiness.yml"),
    ],
)
def test_readiness_and_receipt_roll_back_together_on_injected_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
    target_suffix: str,
) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    key = "wavekit:readiness:00000000-0000-4000-8000-000000000006"
    readiness_path = tmp_path / workspace.show_proposal(proposal_id).path / "readiness.yml"
    original_writer = AtomicMutationWriter

    def fail(stage: str, target: str) -> None:
        if stage == failure_stage and (not target_suffix or target_suffix in target):
            raise RuntimeError("injected readiness failure")

    class InjectedWriter(AtomicMutationWriter):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs, failure_injector=fail)

    monkeypatch.setattr(filesystem_module, "AtomicMutationWriter", InjectedWriter)
    result = _assess_json(tmp_path, proposal_id, key)
    monkeypatch.setattr(filesystem_module, "AtomicMutationWriter", original_writer)

    assert result.exit_code == 1
    assert cli_error(result)["code"] == "P2P_PROPOSAL_READINESS_ASSESS_FAILED"
    assert not readiness_path.exists()
    assert workspace.mutation_status(idempotency_key=key).state == "not_found"


def test_readiness_source_change_before_commit_fails_without_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    key = "wavekit:readiness:00000000-0000-4000-8000-000000000007"
    proposal_path = tmp_path / workspace.show_proposal(proposal_id).path / "proposal.md"

    def change_source(stage: str, _target: str) -> None:
        if stage == "after_source_recheck":
            proposal_path.write_bytes(proposal_path.read_bytes() + b"\nConcurrent change.\n")

    class SourceChangingWriter(AtomicMutationWriter):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs, failure_injector=change_source)

    monkeypatch.setattr(
        filesystem_module,
        "AtomicMutationWriter",
        SourceChangingWriter,
    )
    result = _assess_json(tmp_path, proposal_id, key)

    assert result.exit_code == 3
    assert cli_error(result)["code"] == (
        "P2P_PROPOSAL_READINESS_ASSESS_SOURCE_PRECONDITION_CHANGED"
    )
    assert workspace.read_proposal_readiness(proposal_id).status == "not_assessed"
    assert workspace.mutation_status(idempotency_key=key).state == "not_found"


def test_interrupted_readiness_receipt_reports_recovery_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    key = "wavekit:readiness:00000000-0000-4000-8000-000000000009"

    def interrupt_receipt(stage: str, target: str) -> None:
        if stage == "after_replace" and "mutation-receipts" in target:
            (tmp_path / target).write_bytes(b"external interruption")
            raise RuntimeError("injected interrupted receipt")

    class InterruptedWriter(AtomicMutationWriter):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs, failure_injector=interrupt_receipt)

    monkeypatch.setattr(filesystem_module, "AtomicMutationWriter", InterruptedWriter)
    result = _assess_json(tmp_path, proposal_id, key)

    assert result.exit_code == 3
    assert cli_error(result)["code"] == (
        "P2P_PROPOSAL_READINESS_ASSESS_RECOVERY_REQUIRED"
    )
    status = workspace.mutation_status(idempotency_key=key)
    assert status.state == "incomplete"
    assert status.recovery_required is True


def test_readiness_invalid_source_fails_read_without_writes(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    workspace.initialize_proposal_questions(proposal_id)
    workspace.assess_proposal_readiness(proposal_id)
    questions_path = tmp_path / workspace.show_proposal(proposal_id).path / "questions.yml"
    questions_path.write_bytes(b"proposal_questions: [invalid")
    before = _hash_tree(tmp_path)

    with pytest.raises(ValueError, match="P2P_READINESS_SOURCE_INVALID"):
        workspace.read_proposal_readiness(proposal_id)

    assert _hash_tree(tmp_path) == before


def test_mcp_readiness_assessment_matches_cli_and_detail_semantics(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace_with_proposal(tmp_path)
    cli_result = _assess_json(
        tmp_path,
        proposal_id,
        "wavekit:readiness:00000000-0000-4000-8000-000000000008",
    )
    assert cli_result.exit_code == 0, cli_result.output
    cli_readiness = cli_data(
        cli_result,
        operation="proposal.readiness.assess",
    )["proposal_readiness_assess"]["readiness"]

    mcp_result = call_tool(
        "p2p_proposal_readiness_assess",
        {"root": str(tmp_path), "proposal_id": proposal_id, "actor": "agent"},
    )
    detail = workspace.proposal_detail_contract(proposal_id)["readiness"]

    for field in (
        "status",
        "profile_id",
        "profile_version",
        "computed_score",
        "computed_label",
        "confidence",
        "failed_gates",
        "missing",
        "suggested_next",
        "owner_question_state",
        "freshness",
        "assessment_policy_version",
        "source_fingerprint_sha256",
    ):
        assert mcp_result["readiness"][field] == cli_readiness[field]
        assert detail[field] == cli_readiness[field]
    assert mcp_result["governance"] == {
        "owner_decision_required": False,
        "decision_made": False,
        "override_applied": False,
    }


def test_project_readiness_surfaces_remain_derived_and_read_only(
    tmp_path: Path,
) -> None:
    workspace, _proposal_id = _workspace_with_proposal(tmp_path)
    before = _hash_tree(tmp_path)

    snapshot = workspace.project_snapshot()
    progress = workspace.project_progress()
    review = workspace.review_project_readiness()

    assert snapshot["readiness"]["definition"]["axis_id"] == (
        "definition_completeness"
    )
    assert progress.definition.axis_id == "definition_completeness"
    assert review.snapshot_fingerprint
    assert _hash_tree(tmp_path) == before

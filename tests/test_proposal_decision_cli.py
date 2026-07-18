from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.services.proposal_decision_ledger import ProposalDecisionLedgerCodec


runner = CliRunner()


def _project(root: Path) -> Path:
    assert runner.invoke(
        app,
        ["init", "Decision CLI", "--owner", "owner", "--root", str(root)],
    ).exit_code == 0
    assert runner.invoke(
        app,
        ["proposal", "create", "Two Phase Decision", "--root", str(root)],
    ).exit_code == 0
    return (
        root
        / ".p2p"
        / "proposals"
        / "PROP-001-two-phase-decision"
    )


def _record_preview(root: Path, *, override: bool = False) -> dict[str, object]:
    arguments = [
        "decision",
        "record",
        "PROP-001",
        "--outcome",
        "accepted",
        "--reason",
        "The owner accepts the governed direction.",
        "--approver",
        "owner",
        "--format",
        "json",
        "--root",
        str(root),
    ]
    if override:
        arguments.insert(-4, "--override-readiness")
    result = runner.invoke(app, arguments)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _record_apply(
    root: Path,
    preview: dict[str, object],
    *,
    override: bool = False,
):
    request = preview["request"]
    mutation = preview["preview"]
    arguments = [
        "decision",
        "record",
        "PROP-001",
        "--outcome",
        "accepted",
        "--reason",
        "The owner accepts the governed direction.",
        "--approver",
        "owner",
        "--decided-on",
        request["decided_on"],
        "--operation-key",
        request["operation_key"],
        "--preview-token",
        mutation["preview_token"],
        "--confirm",
        "--format",
        "json",
        "--root",
        str(root),
    ]
    if request["source_head_event_id"]:
        arguments.extend(
            ["--source-head-event-id", request["source_head_event_id"]]
        )
    if override:
        arguments.insert(-4, "--override-readiness")
    return runner.invoke(app, arguments)


def test_compatibility_record_is_two_phase_and_json_is_retry_complete(
    tmp_path: Path,
) -> None:
    proposal_dir = _project(tmp_path)
    ledger_path = proposal_dir / "decision-events.yml"
    before = ledger_path.read_bytes()

    preview = _record_preview(tmp_path)

    assert preview["status"] == "preview_required"
    assert preview["request"]["decided_on"]
    assert preview["request"]["operation_key"].startswith("P2POP-")
    assert preview["preview"]["preview_token"]
    assert ledger_path.read_bytes() == before

    applied = _record_apply(tmp_path, preview)
    assert applied.exit_code == 0, applied.output
    payload = json.loads(applied.output)
    ledger = ProposalDecisionLedgerCodec().loads(
        ledger_path.read_bytes(),
        expected_proposal_id="PROP-001",
    )

    assert payload["status"] == "applied"
    assert len(ledger.events) == 1
    assert ledger.events[0].operation_key == preview["request"]["operation_key"]


def test_status_history_and_stale_apply_have_stable_exit_semantics(
    tmp_path: Path,
) -> None:
    proposal_dir = _project(tmp_path)
    preview = _record_preview(tmp_path)
    stale_arguments = [
        "decision",
        "record",
        "PROP-001",
        "--outcome",
        "accepted",
        "--reason",
        "The owner accepts the governed direction.",
        "--approver",
        "owner",
        "--decided-on",
        preview["request"]["decided_on"],
        "--operation-key",
        preview["request"]["operation_key"],
        "--preview-token",
        "f" * 64,
        "--confirm",
        "--format",
        "json",
        "--root",
        str(tmp_path),
    ]
    before = (proposal_dir / "decision-events.yml").read_bytes()

    stale = runner.invoke(app, stale_arguments)

    assert stale.exit_code == 1
    assert json.loads(stale.output)["status"] == "stale_preview"
    assert (proposal_dir / "decision-events.yml").read_bytes() == before
    assert _record_apply(tmp_path, preview).exit_code == 0

    status = runner.invoke(
        app,
        [
            "decision",
            "status",
            "PROP-001",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    history = runner.invoke(
        app,
        [
            "decision",
            "history",
            "PROP-001",
            "--limit",
            "1",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert json.loads(status.output)["effective_state"] == "accepted"
    assert json.loads(history.output)["returned_count"] == 1


def test_readiness_override_is_not_written_before_matching_apply(
    tmp_path: Path,
) -> None:
    proposal_dir = _project(tmp_path)
    readiness_path = proposal_dir / "readiness.yml"

    preview = _record_preview(tmp_path, override=True)

    assert preview["request"]["readiness_override"] is True
    assert not readiness_path.exists()
    applied = _record_apply(tmp_path, preview, override=True)
    assert applied.exit_code == 0, applied.output
    readiness = yaml.safe_load(readiness_path.read_text(encoding="utf-8"))
    assert readiness["readiness"]["owner_override"] is True


def test_generic_cli_apply_and_projection_repair_use_public_two_phase_contract(
    tmp_path: Path,
) -> None:
    proposal_dir = _project(tmp_path)
    reason = "Accept the proposal with a documented condition."
    preview_result = runner.invoke(
        app,
        [
            "decision",
            "preview",
            "PROP-001",
            "--event-type",
            "accepted_with_changes",
            "--reason",
            reason,
            "--actor",
            "owner",
            "--condition",
            "COND-001=Complete the compatibility review.",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert preview_result.exit_code == 0, preview_result.output
    preview = json.loads(preview_result.output)
    request = preview["request"]
    token = preview["preview"]["preview_token"]

    applied = runner.invoke(
        app,
        [
            "decision",
            "apply",
            "PROP-001",
            "--event-type",
            "accepted_with_changes",
            "--reason",
            reason,
            "--actor",
            "owner",
            "--condition",
            "COND-001=Complete the compatibility review.",
            "--decided-on",
            request["decided_on"],
            "--operation-key",
            request["operation_key"],
            "--preview-token",
            token,
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert applied.exit_code == 0, applied.output
    assert json.loads(applied.output)["status"] == "applied"

    impact = runner.invoke(
        app,
        [
            "decision",
            "impact",
            "PROP-001",
            "--event-type",
            "revoked",
            "--limit",
            "1",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert impact.exit_code == 0, impact.output
    impact_payload = json.loads(impact.output)
    assert impact_payload["completeness"] == "complete"
    assert "source_fingerprint_sha256" in impact_payload

    decision_path = proposal_dir / "decision.md"
    decision_path.write_text("corrupt projection\n", encoding="utf-8")
    repair_preview_result = runner.invoke(
        app,
        [
            "decision",
            "projection-repair-preview",
            "PROP-001",
            "--actor",
            "owner",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert repair_preview_result.exit_code == 0, repair_preview_result.output
    repair_preview = json.loads(repair_preview_result.output)

    repaired = runner.invoke(
        app,
        [
            "decision",
            "projection-repair-apply",
            "PROP-001",
            "--actor",
            "owner",
            "--preview-token",
            repair_preview["preview_token"],
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert repaired.exit_code == 0, repaired.output
    assert json.loads(repaired.output)["status"] == "applied"
    assert "## Canonical Source\n\ndecision-events.yml" in (
        decision_path.read_text(encoding="utf-8")
    )

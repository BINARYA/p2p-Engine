from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace

def _workspace(root: Path) -> tuple[P2PWorkspace, str]:
    workspace = P2PWorkspace(root)
    workspace.init_project("Decision MCP", owner="owner")
    workspace.permissions_actor_add(
        "decision-agent",
        role="contributor",
        kind="agent",
    )
    proposal = workspace.create_proposal("MCP two phase")
    workspace.assign_proposal_memory_scope(
        proposal_id=proposal.proposal_id,
        kind="project_global",
        section_ids=[],
        operation_key="mcp-decision-test-scope-12345678",
        expected_memory_revision=workspace.project_memory_revision(),
        expected_structure_revision=workspace.project_structure().revision,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    return workspace, proposal.proposal_id


def _preview(root: Path, proposal_id: str) -> dict[str, object]:
    result = call_tool(
        "p2p_proposal_decision_preview",
        {
            "root": str(root),
            "proposal_id": proposal_id,
            "event_type": "accepted",
            "reason": "The owner approved the MCP decision.",
            "owner_id": "owner",
            "actor_id": "decision-agent",
            "executor_kind": "agent",
        },
    )
    return result["proposal_decision_preview"]


def _apply_arguments(
    root: Path,
    preview: dict[str, object],
    consent_id: str,
) -> dict[str, object]:
    request = preview["request"]
    return {
        "root": str(root),
        "proposal_id": request["proposal_id"],
        "event_type": request["event_type"],
        "reason": request["reason"],
        "owner_id": "owner",
        "actor_id": "decision-agent",
        "executor_kind": "agent",
        "decided_on": request["decided_on"],
        "operation_key": request["operation_key"],
        "source_head_event_id": request["source_head_event_id"],
        "preview_token": preview["preview"]["preview_token"],
        "confirm": True,
        "consent_id": consent_id,
    }


def test_mcp_decision_apply_binds_consent_owner_executor_and_retry(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    preview = _preview(tmp_path, proposal_id)
    token = preview["preview"]["preview_token"]
    receipt = workspace.consent_grant(
        "proposal_decision_apply",
        f"{proposal_id}@{token}",
        "decision-agent",
        approved_by="owner",
    )

    first = call_tool(
        "p2p_proposal_decision_apply",
        _apply_arguments(tmp_path, preview, receipt.consent_id),
    )

    assert first["proposal_decision"]["status"] == "applied"
    assert first["proposal_decision"]["event"]["authority"]["subject"]["id"] == "owner"
    assert (
        first["proposal_decision"]["event"]["authority"]["executor"]["id"]
        == "decision-agent"
    )
    assert first["consent"]["status"] == "consumed"
    assert first["governance"]["subject_id"] == "owner"
    assert first["governance"]["executor_id"] == "decision-agent"

    retry = call_tool(
        "p2p_proposal_decision_apply",
        _apply_arguments(tmp_path, preview, receipt.consent_id),
    )
    assert retry["governance"]["replayed"] is True
    assert workspace.proposal_decision_status(proposal_id).event_count == 1


def test_mcp_decision_apply_rejects_wrong_token_bound_consent_without_write(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    preview = _preview(tmp_path, proposal_id)
    receipt = workspace.consent_grant(
        "proposal_decision_apply",
        f"{proposal_id}@{'f' * 64}",
        "decision-agent",
        approved_by="owner",
    )

    with pytest.raises(ValueError, match="target mismatch"):
        call_tool(
            "p2p_proposal_decision_apply",
            _apply_arguments(tmp_path, preview, receipt.consent_id),
        )

    assert workspace.proposal_decision_status(proposal_id).event_count == 0
    assert workspace.consent_show(receipt.consent_id).status == "granted"


def test_mcp_decision_apply_rechecks_consent_approver_role(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    preview = _preview(tmp_path, proposal_id)
    token = preview["preview"]["preview_token"]
    receipt = workspace.consent_grant(
        "proposal_decision_apply",
        f"{proposal_id}@{token}",
        "decision-agent",
        approved_by="owner",
    )
    workspace.permissions_actor_add(
        "replacement-owner",
        role="owner",
        kind="person",
    )
    workspace.permissions_actor_add(
        "owner",
        role="contributor",
        kind="person",
    )

    with pytest.raises(ValueError, match="no longer a current project owner"):
        call_tool(
            "p2p_proposal_decision_apply",
            _apply_arguments(tmp_path, preview, receipt.consent_id),
        )

    assert workspace.proposal_decision_status(proposal_id).event_count == 0
    assert workspace.consent_show(receipt.consent_id).status == "granted"


@pytest.mark.parametrize(
    ("field", "changed_value"),
    (
        ("operation_key", "P2POP-" + "0" * 24),
        ("event_id", "PDE-" + "0" * 24),
    ),
)
def test_consumed_consent_retry_rejects_tampered_event_binding(
    tmp_path: Path,
    field: str,
    changed_value: str,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    preview = _preview(tmp_path, proposal_id)
    token = preview["preview"]["preview_token"]
    receipt = workspace.consent_grant(
        "proposal_decision_apply",
        f"{proposal_id}@{token}",
        "decision-agent",
        approved_by="owner",
    )
    arguments = _apply_arguments(tmp_path, preview, receipt.consent_id)
    call_tool("p2p_proposal_decision_apply", arguments)
    receipt_path = tmp_path / workspace.consent_show(receipt.consent_id).path
    payload = yaml.safe_load(receipt_path.read_text(encoding="utf-8"))
    payload["result"]["event"][field] = changed_value
    receipt_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="committed decision result"):
        call_tool("p2p_proposal_decision_apply", arguments)

    assert workspace.proposal_decision_status(proposal_id).event_count == 1


def test_legacy_mcp_accept_consent_can_only_return_a_bound_preview(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    legacy = workspace.consent_grant(
        "proposal_accept",
        proposal_id,
        "decision-agent",
        approved_by="owner",
    )

    result = call_tool(
        "p2p_proposal_accept",
        {
            "root": str(tmp_path),
            "proposal_id": proposal_id,
            "actor_id": "decision-agent",
            "owner_id": "owner",
            "executor_kind": "agent",
            "consent_id": legacy.consent_id,
            "reason": "Legacy consent must not write a v3 event.",
        },
    )

    assert result["status"] == "preview_required"
    assert result["required_consent"]["operation"] == "proposal_decision_apply"
    assert workspace.proposal_decision_status(proposal_id).event_count == 0
    assert workspace.consent_show(legacy.consent_id).status == "granted"


def test_mcp_status_impact_and_projection_repair_share_lifecycle_authority(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    preview = _preview(tmp_path, proposal_id)
    decision_token = preview["preview"]["preview_token"]
    decision_consent = workspace.consent_grant(
        "proposal_decision_apply",
        f"{proposal_id}@{decision_token}",
        "decision-agent",
        approved_by="owner",
    )
    call_tool(
        "p2p_proposal_decision_apply",
        _apply_arguments(
            tmp_path,
            preview,
            decision_consent.consent_id,
        ),
    )

    status = call_tool(
        "p2p_proposal_decision_status",
        {"root": str(tmp_path), "proposal_id": proposal_id},
    )["proposal_decision"]
    impact = call_tool(
        "p2p_proposal_decision_impact",
        {
            "root": str(tmp_path),
            "proposal_id": proposal_id,
            "event_type": "revoked",
            "limit": 1,
        },
    )["proposal_decision_impact"]
    assert status["effective_state"] == "accepted"
    assert status["head_event_id"]
    assert impact["completeness"] == "complete"

    proposal_dir = workspace._proposal_document_service().find_dir(proposal_id)
    decision_path = proposal_dir / "decision.md"
    decision_path.write_text("corrupt projection\n", encoding="utf-8")
    repair_preview = call_tool(
        "p2p_proposal_decision_projection_repair_preview",
        {
            "root": str(tmp_path),
            "proposal_id": proposal_id,
            "owner_id": "owner",
            "actor_id": "decision-agent",
        },
    )["proposal_decision_projection_repair_preview"]
    repair_token = repair_preview["preview_token"]
    repair_consent = workspace.consent_grant(
        "proposal_decision_apply",
        f"{proposal_id}@{repair_token}",
        "decision-agent",
        approved_by="owner",
    )

    repaired = call_tool(
        "p2p_proposal_decision_projection_repair_apply",
        {
            "root": str(tmp_path),
            "proposal_id": proposal_id,
            "owner_id": "owner",
            "actor_id": "decision-agent",
            "preview_token": repair_token,
            "confirm": True,
            "consent_id": repair_consent.consent_id,
        },
    )

    assert (
        repaired["proposal_decision_projection_repair"]["status"]
        == "applied"
    )
    assert "## Canonical Source\n\ndecision-events.yml" in (
        decision_path.read_text(encoding="utf-8")
    )

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data
from tests.proposal_decision_fixtures import record_decision


runner = CliRunner()


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _initialized_workspace(root: Path, *, vertical_id: str = "base_project") -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Snapshot Project", owner="owner", vertical_id=vertical_id)
    return workspace


def test_project_snapshot_handles_project_without_proposals(tmp_path: Path) -> None:
    workspace = _initialized_workspace(tmp_path)
    before = _hash_tree(tmp_path)

    snapshot = workspace.project_snapshot()

    assert _hash_tree(tmp_path) == before
    assert snapshot["contract_version"] == "p2p-project-snapshot/v1"
    assert snapshot["project"]["name"] == "Snapshot Project"
    assert snapshot["runtime"]["compatible"] is True
    assert snapshot["workspace_schema"]["current_version"] == 4
    assert snapshot["transactions"]["required"] is False
    assert snapshot["structure"]["contract"] == "p2p-project-structure/v1"
    assert snapshot["structure"]["revision"] == 1
    assert snapshot["structure"]["active_section_count"] >= 1
    assert snapshot["vertical"]["active"]["vertical_id"] == "base_project"
    assert snapshot["sections"]["total"] >= 1
    assert snapshot["proposals"]["total"] == 0
    assert snapshot["decisions"]["total"] == 0
    assert snapshot["readiness"]["definition"]["axis_id"] == "definition_completeness"
    assert "publication" in snapshot["outputs"]


def test_project_snapshot_counts_decisions_and_truncates_collections(tmp_path: Path) -> None:
    workspace = _initialized_workspace(tmp_path, vertical_id="software_project")
    first = workspace.create_proposal_with_details(
        "Data model evidence",
        problem="The project needs an explicit data model.",
        proposal="Define the domain entities and lifecycle.",
    )
    second = workspace.create_proposal_with_details(
        "Runtime evidence",
        problem="The runtime contract needs to be explicit.",
        proposal="Define runtime compatibility checks.",
    )
    record_decision(
        workspace,
        first.proposal_id,
        DecisionOutcome.accepted,
        "The proposal defines committed evidence.",
        "owner",
    )

    snapshot = workspace.project_snapshot(limit=1)

    assert snapshot["vertical"]["active"]["vertical_id"] == "software_project"
    assert snapshot["sections"]["returned"] == 1
    assert snapshot["sections"]["truncated"] is True
    assert snapshot["proposals"]["total"] == 2
    assert snapshot["proposals"]["returned"] == 1
    assert snapshot["proposals"]["truncated"] is True
    assert snapshot["proposals"]["counts"]["by_effective_state"]["accepted"] == 1
    assert snapshot["decisions"]["total"] == 1
    assert snapshot["decisions"]["counts"]["by_effective_state"]["accepted"] == 1
    assert snapshot["decisions"]["items"][0]["proposal_id"] == first.proposal_id
    assert second.proposal_id not in {
        item["proposal_id"] for item in snapshot["decisions"]["items"]
    }
    assert snapshot["limits"]["proposal_summaries"] == 1


def test_project_snapshot_reports_schema_and_recovery_attention(tmp_path: Path) -> None:
    workspace = _initialized_workspace(tmp_path)
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    payload = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    payload["workspace_schema"]["current_version"] = 2
    schema_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    lock_path = tmp_path / ".p2p" / ".internal" / "workspace-transactions" / "apply.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        yaml.safe_dump(
            {
                "transaction_id": "snapshot-test",
                "pid": os.getpid(),
                "acquired_at": "2026-07-15T00:00:00Z",
                "owner": "test",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    snapshot = workspace.project_snapshot()

    assert snapshot["workspace_schema"]["layout_status"] == "unsupported"
    assert snapshot["workspace_schema"]["current_version"] == 2
    assert snapshot["transactions"]["required"] is True
    assert snapshot["transactions"]["transaction_id"] == "snapshot-test"
    assert snapshot["transactions"]["lock"]["state"] == "active"


def test_project_snapshot_cli_json_matches_service(tmp_path: Path) -> None:
    workspace = _initialized_workspace(tmp_path)
    workspace.create_proposal_with_details(
        "CLI Proposal",
        problem="The CLI needs a JSON snapshot.",
        proposal="Expose project snapshot as JSON.",
    )

    result = runner.invoke(
        app,
        ["project", "snapshot", "--format", "json", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    payload = cli_data(result, operation="project.snapshot")["project_snapshot"]
    service_payload = workspace.project_snapshot()
    assert payload["project"]["name"] == service_payload["project"]["name"]
    assert payload["proposals"]["total"] == 1
    assert payload["limits"]["default_limit"] == 20

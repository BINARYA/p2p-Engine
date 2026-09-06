from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.choice_reads import (
    CHOICE_DETAIL_CONTRACT,
    CHOICE_LIST_CONTRACT,
    ChoicePageMetadata,
    validate_choice_read_page,
)
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.project_application import open_project_application
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data
from tests.filesystem_assertions import assert_no_workspace_mutation

RUNNER = CliRunner()


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Choice read contracts", project_domain="software")
    return workspace


def _create_choice(workspace: P2PWorkspace, title: str, *, related: list[str] | None = None) -> None:
    workspace.create_choice(
        title,
        ["Keep current", "Adopt replacement"],
        related=related,
        problem=f"Choose the governed direction for {title}.",
        context="The project needs one complete and stable decision frame.",
        governance_boundary="The project owner decides after reviewing both options.",
    )


@pytest.mark.unit
def test_choice_read_page_contract_validates_exact_bounds() -> None:
    assert ChoicePageMetadata.build(
        limit=50,
        offset=0,
        returned=1,
        has_more=True,
    ).to_dict() == {
        "limit": 50,
        "offset": 0,
        "returned": 1,
        "has_more": True,
        "next_offset": 1,
    }
    for limit in (0, 101):
        with pytest.raises(ValueError, match="P2P_CHOICE_READ_LIMIT_INVALID"):
            validate_choice_read_page(limit=limit, offset=0)
    with pytest.raises(ValueError, match="P2P_CHOICE_READ_OFFSET_INVALID"):
        validate_choice_read_page(limit=50, offset=-1)


@pytest.mark.unit
def test_choice_application_reads_are_complete_bounded_and_non_mutating(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    for index in range(3):
        workspace.create_proposal(f"Related proposal {index}")
    _create_choice(workspace, "Runtime strategy", related=["PROP-001", "PROP-002", "PROP-003"])
    application = open_project_application(tmp_path)

    with assert_no_workspace_mutation(tmp_path):
        listed = application.choice_list_read(limit=1, offset=0).to_dict()
        detail = application.choice_detail_read("CHOICE-001", limit=1, offset=0).to_dict()

    assert listed["contract"] == CHOICE_LIST_CONTRACT
    assert set(listed) == {"contract", "items", "page"}
    assert listed["page"] == {
        "limit": 1,
        "offset": 0,
        "returned": 1,
        "has_more": False,
        "next_offset": None,
    }
    summary = listed["items"][0]
    assert set(summary) == {
        "choice_id",
        "title",
        "state",
        "terminal",
        "definition_contract",
        "definition_completeness",
        "definition_digest",
        "seal_status",
        "integrity_status",
        "selected_option",
        "replacement_choice_id",
    }
    assert summary["state"] == "open"
    assert summary["definition_completeness"] == "complete"
    assert "path" not in summary

    assert detail["contract"] == CHOICE_DETAIL_CONTRACT
    assert set(detail) == {
        "contract",
        "choice_id",
        "definition",
        "lifecycle",
        "integrity",
        "relations",
    }
    assert set(detail["definition"]) == {
        "source_contract",
        "completeness",
        "digest",
        "choice_id",
        "title",
        "problem",
        "context",
        "governance_boundary",
        "options",
    }
    assert set(detail["lifecycle"]) == {
        "source_contract",
        "state",
        "terminal",
        "selected_option",
        "terminal_event",
        "replacement_choice_id",
    }
    assert detail["choice_id"] == "CHOICE-001"
    assert detail["definition"]["problem"] == (
        "Choose the governed direction for Runtime strategy."
    )
    assert detail["definition"]["context"] == (
        "The project needs one complete and stable decision frame."
    )
    assert detail["definition"]["governance_boundary"] == (
        "The project owner decides after reviewing both options."
    )
    assert detail["relations"]["page"]["has_more"] is True
    assert detail["relations"]["page"]["next_offset"] == 1
    assert detail["relations"]["items"][0]["kind"] == "related_proposal"
    assert ".p2p" not in json.dumps(detail, sort_keys=True)


@pytest.mark.unit
def test_choice_list_contract_normalizes_all_terminal_states(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    for title in ("Open frame", "Decided frame", "Withdrawn frame", "Historical frame"):
        _create_choice(workspace, title)
    service.decide("CHOICE-002", option="B", reason="Adopt it.", decider="owner")
    service.withdraw(
        "CHOICE-003",
        reason="No longer needed.",
        actor_id="owner",
        operation_key="choice-read-withdrawn",
    )
    service.supersede(
        "CHOICE-004",
        replacement_choice_id="CHOICE-001",
        reason="The first frame is now authoritative.",
        actor_id="owner",
        operation_key="choice-read-superseded",
    )

    payload = service.list_read(limit=100).to_dict()
    items = {item["choice_id"]: item for item in payload["items"]}

    assert [item["choice_id"] for item in payload["items"]] == [
        "CHOICE-001",
        "CHOICE-002",
        "CHOICE-003",
        "CHOICE-004",
    ]
    assert items["CHOICE-001"]["state"] == "open"
    assert items["CHOICE-002"]["selected_option"] == {
        "id": "B",
        "title": "Adopt replacement",
    }
    assert items["CHOICE-003"]["selected_option"] is None
    assert items["CHOICE-004"]["selected_option"] is None
    assert items["CHOICE-004"]["replacement_choice_id"] == "CHOICE-001"
    assert all(item["terminal"] for item in items.values() if item["state"] != "open")

    _create_choice(workspace, "Second historical frame")
    service.supersede(
        "CHOICE-005",
        replacement_choice_id="CHOICE-001",
        reason="The first frame also replaces this history.",
        actor_id="owner",
        operation_key="choice-read-second-superseded",
    )
    workspace.create_proposal("Blocking proposal")
    workspace.block_choice(
        "CHOICE-001",
        "PROP-001",
        "proposal",
        "Resolve the proposal first.",
    )
    replacement = service.detail_read("CHOICE-001").to_dict()
    inverse = [
        relation
        for relation in replacement["relations"]["items"]
        if relation["kind"] == "supersedes"
    ]
    assert inverse == [
        {
            "kind": "supersedes",
            "target_type": "choice",
            "target_id": "CHOICE-004",
            "relationship": None,
            "rationale": None,
            "status": None,
            "reason": None,
            "recorded_on": None,
            "cleared_on": None,
            "cleared_by": None,
            "clearing_reason": None,
            "derived": True,
        },
        {
            "kind": "supersedes",
            "target_type": "choice",
            "target_id": "CHOICE-005",
            "relationship": None,
            "rationale": None,
            "status": None,
            "reason": None,
            "recorded_on": None,
            "cleared_on": None,
            "cleared_by": None,
            "clearing_reason": None,
            "derived": True,
        },
    ]
    assert [item["kind"] for item in replacement["relations"]["items"]] == [
        "blocks",
        "supersedes",
        "supersedes",
    ]


@pytest.mark.unit
def test_choice_detail_contract_does_not_fabricate_legacy_definition(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace, "Legacy frame")
    choice_dir = next((tmp_path / ".p2p" / "choices").glob("CHOICE-001-*"))
    (choice_dir / "lifecycle.yml").unlink()
    choice_path = choice_dir / "choice.md"
    choice_path.write_text(
        choice_path.read_text(encoding="utf-8").replace(
            "The project needs one complete and stable decision frame.",
            "Pending.",
        ),
        encoding="utf-8",
    )
    options_path = choice_dir / "options.yml"
    options = yaml.safe_load(options_path.read_text(encoding="utf-8"))
    for option in options["options"]:
        option["status"] = "available"
    options_path.write_text(yaml.safe_dump(options, sort_keys=False), encoding="utf-8")

    with assert_no_workspace_mutation(tmp_path):
        payload = workspace._choice_lifecycle_service().detail_read("CHOICE-001").to_dict()

    assert payload["definition"]["source_contract"] == "legacy"
    assert payload["definition"]["completeness"] == "incomplete"
    assert payload["definition"]["digest"] is None
    assert payload["definition"]["problem"] is None
    assert payload["definition"]["context"] is None
    assert payload["lifecycle"]["source_contract"] == "legacy"
    assert payload["integrity"] == {
        "seal_status": "incomplete_unsealed",
        "integrity_status": "unsealed",
    }


@pytest.mark.cli
def test_choice_cli_list_and_show_return_versioned_json(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace, "Deployment strategy")

    listed = RUNNER.invoke(
        app,
        ["choice", "list", "--limit", "1", "--format", "json", "--root", str(tmp_path)],
    )
    shown = RUNNER.invoke(
        app,
        [
            "choice",
            "show",
            "CHOICE-001",
            "--limit",
            "1",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert listed.exit_code == 0, listed.output
    assert shown.exit_code == 0, shown.output
    assert json.loads(listed.stdout)["operation"] == "choice.list"
    assert json.loads(shown.stdout)["operation"] == "choice.show"
    assert cli_data(listed)["choice_list"]["contract"] == CHOICE_LIST_CONTRACT
    assert cli_data(shown)["choice_detail"]["contract"] == CHOICE_DETAIL_CONTRACT


@pytest.mark.cli
def test_choice_cli_json_errors_are_stable_and_single_document(tmp_path: Path) -> None:
    _workspace(tmp_path)
    invalid_page = RUNNER.invoke(
        app,
        ["choice", "list", "--limit", "101", "--format", "json", "--root", str(tmp_path)],
    )
    missing = RUNNER.invoke(
        app,
        [
            "choice",
            "show",
            "CHOICE-999",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    invalid_payload = json.loads(invalid_page.stdout)
    missing_payload = json.loads(missing.stdout)
    assert invalid_page.exit_code == 2
    assert invalid_payload["error"]["code"] == "P2P_CLI_INVALID_REQUEST"
    assert missing.exit_code == 2
    assert missing_payload["operation"] == "choice.show"
    assert missing_payload["error"]["code"] == "P2P_CHOICE_NOT_FOUND"
    assert "\x1b" not in invalid_page.stdout + missing.stdout


@pytest.mark.cli
def test_choice_cli_integrity_failure_is_stable_json(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace, "Corrupt frame")
    choice_dir = next((tmp_path / ".p2p" / "choices").glob("CHOICE-001-*"))
    lifecycle_path = choice_dir / "lifecycle.yml"
    lifecycle = yaml.safe_load(lifecycle_path.read_text(encoding="utf-8"))
    lifecycle["choice_lifecycle"]["unexpected"] = True
    lifecycle_path.write_text(yaml.safe_dump(lifecycle, sort_keys=False), encoding="utf-8")

    result = RUNNER.invoke(
        app,
        [
            "choice",
            "show",
            "CHOICE-001",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["operation"] == "choice.show"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "P2P_CHOICE_LIFECYCLE_INVALID"
    assert payload["data"] is None
    assert "\x1b" not in result.stdout


@pytest.mark.cli
@pytest.mark.parametrize(
    ("command", "expected_exit"),
    (
        (["choice", "list", "--limit", "0", "--format", "json"], 2),
        (["choice", "list", "--limit", "1", "--format", "json"], 0),
        (["choice", "list", "--limit", "50", "--format", "json"], 0),
        (["choice", "list", "--limit", "100", "--format", "json"], 0),
        (["choice", "list", "--limit", "101", "--format", "json"], 2),
        (["choice", "list", "--offset", "-1", "--format", "json"], 2),
    ),
)
def test_choice_cli_list_pins_page_boundaries(
    tmp_path: Path,
    command: list[str],
    expected_exit: int,
) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace, "Boundary frame")

    result = RUNNER.invoke(app, [*command, "--root", str(tmp_path)])

    assert result.exit_code == expected_exit
    payload = json.loads(result.stdout)
    assert payload["ok"] is (expected_exit == 0)
    if expected_exit == 0:
        assert payload["data"]["choice_list"]["contract"] == CHOICE_LIST_CONTRACT
    else:
        assert payload["error"]["code"] == "P2P_CLI_INVALID_REQUEST"


@pytest.mark.cli
@pytest.mark.mcp
def test_choice_cli_and_mcp_share_semantic_projection_and_keep_aliases(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _create_choice(workspace, "Shared read projection")
    cli_list = RUNNER.invoke(
        app,
        ["choice", "list", "--format", "json", "--root", str(tmp_path)],
    )
    cli_detail = RUNNER.invoke(
        app,
        ["choice", "show", "CHOICE-001", "--format", "json", "--root", str(tmp_path)],
    )
    mcp_list = call_tool("p2p_choice_list", {"root": str(tmp_path)})
    mcp_detail = call_tool(
        "p2p_choice_show",
        {"root": str(tmp_path), "choice_id": "CHOICE-001"},
    )

    assert cli_data(cli_list)["choice_list"] == mcp_list["choice_list"]
    assert cli_data(cli_detail)["choice_detail"] == mcp_detail["choice_detail"]
    assert mcp_list["choices"][0]["status"] == "open"
    assert set(mcp_list["choices"][0]) == {
        "choice_id",
        "title",
        "status",
        "path",
        "selected_option",
        "terminal",
        "seal_status",
        "integrity_status",
        "definition_digest",
        "replacement_choice_id",
    }
    assert mcp_list["choices"][0]["path"].startswith(".p2p/choices/")
    assert mcp_detail["choice"]["status"] == "open"
    assert mcp_detail["choice"]["options"][0] == {
        "id": "A",
        "title": "Keep current",
    }
    assert set(mcp_detail["choice"]) == {
        "choice_id",
        "title",
        "status",
        "path",
        "selected_option",
        "options",
        "related_proposals",
        "related_changes",
        "blocks",
        "terminal",
        "seal_status",
        "integrity_status",
        "definition_digest",
        "terminal_event",
        "replacement_choice_id",
        "supersedes",
    }


@pytest.mark.cli
@pytest.mark.mcp
def test_choice_cli_and_mcp_match_for_every_lifecycle_state_and_page(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    for title in ("Open", "Decided", "Withdrawn", "Superseded"):
        _create_choice(workspace, title)
    service.decide("CHOICE-002", option="A", reason="Keep it.", decider="owner")
    service.withdraw(
        "CHOICE-003",
        reason="No longer relevant.",
        actor_id="owner",
        operation_key="choice-parity-withdrawn",
    )
    service.supersede(
        "CHOICE-004",
        replacement_choice_id="CHOICE-001",
        reason="Use the new frame.",
        actor_id="owner",
        operation_key="choice-parity-superseded",
    )

    cli_list = RUNNER.invoke(
        app,
        [
            "choice",
            "list",
            "--limit",
            "2",
            "--offset",
            "1",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    mcp_list = call_tool(
        "p2p_choice_list",
        {"root": str(tmp_path), "limit": 2, "offset": 1},
    )
    assert cli_data(cli_list)["choice_list"] == mcp_list["choice_list"]

    for choice_id in ("CHOICE-001", "CHOICE-002", "CHOICE-003", "CHOICE-004"):
        cli_detail = RUNNER.invoke(
            app,
            [
                "choice",
                "show",
                choice_id,
                "--limit",
                "1",
                "--offset",
                "0",
                "--format",
                "json",
                "--root",
                str(tmp_path),
            ],
        )
        mcp_detail = call_tool(
            "p2p_choice_show",
            {
                "root": str(tmp_path),
                "choice_id": choice_id,
                "limit": 1,
                "offset": 0,
            },
        )
        assert cli_data(cli_detail)["choice_detail"] == mcp_detail["choice_detail"]

    with pytest.raises(ValueError, match="P2P_CHOICE_READ_LIMIT_INVALID"):
        call_tool(
            "p2p_choice_list",
            {"root": str(tmp_path), "limit": 101, "offset": 0},
        )

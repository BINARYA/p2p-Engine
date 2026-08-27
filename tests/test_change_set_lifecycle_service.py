from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Demo Project")
    workspace.create_proposal("Draft Work")
    return workspace


def _accepted_workspace(root: Path) -> P2PWorkspace:
    workspace = _workspace(root)
    record_decision(workspace, "PROP-001", DecisionOutcome.accepted, "Ready for operational work.", "owner")
    return workspace


def test_change_set_lifecycle_service_creates_shows_and_lists_change(tmp_path: Path) -> None:
    workspace = _accepted_workspace(tmp_path)
    service = workspace._change_set_lifecycle_service()

    created = service.create("PROP-001")
    shown = service.show("CHANGE-001")
    statuses = service.statuses()

    assert created.change_id == "CHANGE-001"
    assert created.status == "proposed"
    assert shown.title == "Draft Work"
    assert shown.implementation_targets == ["local_cli"]
    assert statuses[0].change_id == "CHANGE-001"
    change_text = (tmp_path / ".p2p" / "changes" / "CHANGE-001-draft-work" / "change.md").read_text(
        encoding="utf-8"
    )
    assert "operation_level" not in change_text
    assert "implementation_targets:" in change_text


def test_change_set_lifecycle_service_reads_tasks(tmp_path: Path) -> None:
    workspace = _accepted_workspace(tmp_path)
    service = workspace._change_set_lifecycle_service()
    service.create("PROP-001")
    change_dir = tmp_path / ".p2p" / "changes" / "CHANGE-001-draft-work"
    (change_dir / "tasks.yml").write_text(
        "tasks:\n  - id: T001\n    status: pending\n    title: Do work\n",
        encoding="utf-8",
    )
    (change_dir / "actions.yml").write_text(
        "actions:\n  - id: A001\n    title: Verify\n    checked: true\n",
        encoding="utf-8",
    )

    tasks = service.tasks("CHANGE-001")

    assert tasks.tasks[0]["id"] == "T001"
    assert tasks.actions[0]["checked"] is True


def test_change_set_lifecycle_service_updates_status_with_transition_rules(tmp_path: Path) -> None:
    workspace = _accepted_workspace(tmp_path)
    service = workspace._change_set_lifecycle_service()
    service.create("PROP-001")

    planned = service.update_status("CHANGE-001", "planned")

    assert planned.status == "planned"
    with pytest.raises(ValueError, match="Invalid Change Set transition"):
        service.update_status("CHANGE-001", "completed")


def test_change_set_lifecycle_service_validates_error_paths(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._change_set_lifecycle_service()

    with pytest.raises(ValueError, match="no current active decision authority"):
        service.create("PROP-001")

    record_decision(workspace, "PROP-001", DecisionOutcome.accepted, "Ready.", "owner")
    service.create("PROP-001")
    change_dir = tmp_path / ".p2p" / "changes" / "CHANGE-001-draft-work"

    (change_dir / "tasks.yml").write_text("tasks: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected `tasks` list"):
        service.tasks("CHANGE-001")

    (change_dir / "tasks.yml").write_text("tasks: []\n", encoding="utf-8")
    (change_dir / "actions.yml").write_text("actions: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected `actions` list"):
        service.tasks("CHANGE-001")

    with pytest.raises(ValueError, match="Change Set not found"):
        service.find_dir("CHANGE-999")


def test_change_set_lifecycle_service_find_dir_detects_ambiguous_ids(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    changes_dir = tmp_path / ".p2p" / "changes"
    (changes_dir / "CHANGE-001-a").mkdir(parents=True)
    (changes_dir / "CHANGE-001-b").mkdir(parents=True)

    with pytest.raises(ValueError, match="Ambiguous Change Set ID"):
        workspace._change_set_lifecycle_service().find_dir("CHANGE-001")

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Demo Project", project_domain="software")
    return workspace


def _accepted_change_workspace(root: Path) -> P2PWorkspace:
    workspace = _workspace(root)
    workspace.create_proposal("Governance Model")
    record_decision(workspace, "PROP-001", DecisionOutcome.accepted, "Needed.", "owner")
    workspace.create_change_set("PROP-001", "Governance Model")
    workspace.update_change_set_status("CHANGE-001", "planned")
    return workspace


def test_choice_lifecycle_service_creates_lists_and_shows_choice(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Prompt Workflow")
    service = workspace._choice_lifecycle_service()

    created = service.create(
        "Initial AI Strategy",
        ["Prompt-only first", "Direct AI now"],
        related=["PROP-001"],
        source="INTAKE-001",
    )
    statuses = service.statuses()
    detail = service.show(created.choice_id)

    assert created.choice_id == "CHOICE-001"
    assert created.status == "open"
    assert statuses[0].title == "Initial AI Strategy"
    assert detail.options[0]["id"] == "A"
    assert detail.related_proposals[0]["proposal"] == "PROP-001"
    assert (tmp_path / ".p2p" / "choices" / "CHOICE-001-initial-ai-strategy" / "choice.md").exists()


def test_choice_lifecycle_service_discovers_advisory_findings(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.create_proposal("Governance Model")
    workspace.record_vote("PROP-001", choice="A", reason="Prefer A", voter="owner", role="owner")
    workspace._choice_lifecycle_service().create(
        "Governance Scope",
        ["Minimal governance", "Full governance"],
        related=["PROP-001"],
    )

    findings = workspace._choice_lifecycle_service().discover()

    assert [finding.kind for finding in findings] == [
        "proposal_local_choice_candidate",
        "open_project_choice",
    ]
    assert findings[0].target == "CHOICE-PROP-001"
    assert findings[1].target == "CHOICE-001"


def test_choice_lifecycle_service_blocks_and_unblocks_choice(tmp_path: Path) -> None:
    workspace = _accepted_change_workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    service.create("Governance Scope", ["Minimal governance", "Full governance"], related=["PROP-001"])

    blocked = service.block(
        "CHOICE-001",
        target="CHANGE-001",
        target_type="change",
        reason="Governance scope must be decided first.",
    )
    unblocked = service.unblock("CHOICE-001", target="CHANGE-001", target_type="change")

    assert blocked.blocks[0]["status"] == "active"
    assert unblocked.blocks[0]["status"] == "inactive"
    assert "cleared_on" in unblocked.blocks[0]


def test_choice_lifecycle_service_decides_choice(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()
    service.create("Initial AI Strategy", ["Prompt-only first", "Direct AI now"])

    decided = service.decide("CHOICE-001", option="B", reason="Use direct AI now.", decider="owner")
    detail = service.show("CHOICE-001")
    options = yaml.safe_load(
        (tmp_path / ".p2p" / "choices" / "CHOICE-001-initial-ai-strategy" / "options.yml").read_text(
            encoding="utf-8"
        )
    )

    assert decided.status == "decided"
    assert decided.selected_option == "B - Direct AI now"
    assert detail.selected_option == "B - Direct AI now"
    assert options["options"][1]["status"] == "selected"


def test_choice_lifecycle_service_validates_error_paths(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._choice_lifecycle_service()

    with pytest.raises(ValueError, match="At least two --option values"):
        service.create("Invalid Choice", ["Only one"])

    service.create("Initial AI Strategy", ["Prompt-only first", "Direct AI now"])

    with pytest.raises(ValueError, match="target_type must be"):
        service.block("CHOICE-001", target="PROP-999", target_type="invalid", reason="Invalid target.")

    choice_dir = tmp_path / ".p2p" / "choices" / "CHOICE-001-initial-ai-strategy"
    (choice_dir / "links.yml").write_text("blocks: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected `blocks` list"):
        service.unblock("CHOICE-001", target="PROP-001", target_type="proposal")

    (choice_dir / "links.yml").write_text("related_proposals: []\nrelated_changes: []\n", encoding="utf-8")
    (choice_dir / "options.yml").write_text("options: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected `options` list"):
        service.decide("CHOICE-001", option="A", reason="Invalid options.", decider="owner")

    (choice_dir / "options.yml").write_text("options:\n  - id: A\n    title: Prompt-only first\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Choice option not found"):
        service.decide("CHOICE-001", option="Z", reason="Missing option.", decider="owner")

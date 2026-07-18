from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.registries import RegistryService
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


def _service(tmp_path, *, proposals=None, changes=None):
    proposals_records = proposals if proposals is not None else [{"id": "PROP-001", "title": "Registry", "status": "draft"}]
    changes_records = changes if changes is not None else [{"id": "CHANGE-001", "title": "Registry", "status": "proposed"}]

    return RegistryService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        duplicate_proposal_ids=lambda: {},
        duplicate_message=lambda duplicates: "duplicate proposals",
        proposal_records=lambda: proposals_records,
        change_records=lambda: changes_records,
        decision_records=lambda proposals_arg: [
            {"proposal": item["id"], "title": item["title"], "outcome": "pending"} for item in proposals_arg
        ],
        choice_records=lambda: [{"id": "CHOICE-001", "status": "open"}],
        relation_records=lambda proposals_arg, changes_arg: [
            {"source": changes_arg[0]["id"], "target": proposals_arg[0]["id"], "type": "includes"}
        ],
        artifact_records=lambda proposals_arg, changes_arg: [
            {"path": ".p2p/proposals/PROP-001/proposal.md", "owner": proposals_arg[0]["id"]}
        ],
        readiness_records=lambda proposals_arg: [
            {"proposal": proposals_arg[0]["id"], "status": "not_assessed"}
        ],
    )


def test_registry_service_refresh_writes_existing_registry_shape(tmp_path) -> None:
    service = _service(tmp_path)

    written = service.refresh()

    assert written == [
        Path(".p2p/registries/proposals.yml"),
        Path(".p2p/registries/decisions.yml"),
        Path(".p2p/registries/changes.yml"),
        Path(".p2p/registries/choices.yml"),
        Path(".p2p/registries/relations.yml"),
        Path(".p2p/registries/artifacts.yml"),
        Path(".p2p/registries/readiness.yml"),
    ]
    proposals = yaml.safe_load((tmp_path / ".p2p" / "registries" / "proposals.yml").read_text(encoding="utf-8"))
    decisions = yaml.safe_load((tmp_path / ".p2p" / "registries" / "decisions.yml").read_text(encoding="utf-8"))
    readiness = yaml.safe_load((tmp_path / ".p2p" / "registries" / "readiness.yml").read_text(encoding="utf-8"))
    assert proposals["generated"] is True
    assert proposals["source"] == ".p2p/proposals"
    assert proposals["proposals"][0]["id"] == "PROP-001"
    assert "decision-events.yml" in decisions["source"]
    assert "schema-v2 decision.md" in decisions["source"]
    assert readiness["source"] == ".p2p/proposals/*/readiness.yml"
    assert readiness["readiness"][0]["status"] == "not_assessed"


def test_registry_service_status_detects_missing_and_count_drift(tmp_path) -> None:
    service = _service(tmp_path)

    missing = service.status()
    service.refresh()
    fresh = service.status()
    drifted = _service(
        tmp_path,
        proposals=[
            {"id": "PROP-001", "title": "Registry", "status": "draft"},
            {"id": "PROP-002", "title": "New", "status": "draft"},
        ],
    ).status()

    assert missing.stale is True
    assert all(file["exists"] is False for file in missing.files)
    assert fresh.stale is False
    assert fresh.proposals_count == 1
    assert fresh.changes_count == 1
    assert drifted.stale is True
    assert drifted.proposals_count == 2


def test_registry_service_show_validates_name_file_and_shape(tmp_path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="Unsupported registry: unknown"):
        service.show("unknown")
    with pytest.raises(ValueError, match="Registry not found"):
        service.show("proposals")

    service.refresh()
    view = service.show("proposals")
    (tmp_path / ".p2p" / "registries" / "choices.yml").write_text("generated: true\nchoices: nope\n", encoding="utf-8")

    assert view.name == "proposals"
    assert view.records[0]["id"] == "PROP-001"
    with pytest.raises(ValueError, match="Invalid registry file"):
        service.show("choices")


def test_workspace_registry_facade_delegates(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Registry Facade")
    proposal = workspace.create_proposal("Registry Proposal")
    record_decision(workspace, proposal.proposal_id, DecisionOutcome.accepted, "Ready.", "owner")
    workspace.create_change_set(proposal.proposal_id)

    missing = workspace.registry_status()
    written = workspace.refresh_registries()
    status = workspace.registry_status()
    view = workspace.show_registry("proposals")

    assert missing.stale is True
    assert Path(".p2p/registries/proposals.yml") in written
    assert status.stale is False
    assert status.proposals_count == 1
    assert view.records[0]["id"] == "PROP-001"

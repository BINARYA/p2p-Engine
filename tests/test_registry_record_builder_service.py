from pathlib import Path

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


def _workspace_with_records(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Registry Records")
    proposal = workspace.create_proposal_with_details(
        "Registry Proposal",
        problem="Problem text.",
        goals=["Goal one."],
        non_goals=["Non goal."],
        proposal="Proposal text.",
    )
    record_decision(workspace, proposal.proposal_id, DecisionOutcome.accepted, "Approved.", "owner")
    change = workspace.create_change_set(proposal.proposal_id)
    workspace._choice_lifecycle_service().create("Registry Choice", ["A", "B"], related=[proposal.proposal_id])
    workspace.record_vote(proposal.proposal_id, choice="A", reason="A wins", voter="owner", role="owner")
    workspace.refresh_proposal_readiness(proposal.proposal_id)
    change_dir = root / ".p2p" / "changes" / "CHANGE-001-registry-proposal"
    (change_dir / "referenced-proposals.yml").write_text(
        "referenced_proposals:\n  - PROP-999\n",
        encoding="utf-8",
    )
    return workspace


def test_registry_record_builder_builds_accepted_and_proposal_records(tmp_path: Path) -> None:
    workspace = _workspace_with_records(tmp_path)
    service = workspace._registry_record_builder_service()

    accepted = service.accepted_proposals()
    proposals = service.proposal_records()

    assert accepted[0]["proposal_id"] == "PROP-001"
    assert accepted[0]["feature_id"] == "registry-proposal"
    assert accepted[0]["problem"] == "Problem text."
    assert accepted[0]["proposal"] == "Proposal text."
    assert proposals[0]["id"] == "PROP-001"
    assert proposals[0]["status"] == "accepted"
    assert proposals[0]["related_changes"] == ["CHANGE-001"]
    assert "proposal.md" in proposals[0]["source_files"]


def test_proposal_records_build_change_index_once_per_operation(tmp_path: Path) -> None:
    workspace = _workspace_with_records(tmp_path)
    service = workspace._registry_record_builder_service()
    original = service.change_records
    calls = 0

    def counted_changes():
        nonlocal calls
        calls += 1
        return original()

    service.change_records = counted_changes  # type: ignore[method-assign]

    proposals = service.proposal_records()

    assert calls == 1
    assert proposals[0]["related_changes"] == ["CHANGE-001"]


def test_registry_record_builder_builds_decision_and_readiness_records(tmp_path: Path) -> None:
    workspace = _workspace_with_records(tmp_path)
    service = workspace._registry_record_builder_service()
    proposals = service.proposal_records()

    decisions = service.decision_records(proposals)
    readiness = service.readiness_records(proposals)

    assert decisions[0]["proposal"] == "PROP-001"
    assert decisions[0]["outcome"] == "accepted"
    assert decisions[0]["reason"] == "Approved."
    assert readiness[0]["proposal"] == "PROP-001"
    assert readiness[0]["status"] in {"assessed", "not_assessed"}
    assert readiness[0]["path"] == ".p2p/proposals/PROP-001-registry-proposal/readiness.yml"


def test_registry_record_builder_builds_change_records_and_lookup(tmp_path: Path) -> None:
    workspace = _workspace_with_records(tmp_path)
    service = workspace._registry_record_builder_service()

    changes = service.change_records()

    assert changes[0]["id"] == "CHANGE-001"
    assert changes[0]["included_proposals"] == ["PROP-001"]
    assert changes[0]["referenced_proposals"] == ["PROP-999"]
    assert changes[0]["task_count"] == 0
    assert service.changes_for_proposal("PROP-001") == ["CHANGE-001"]


def test_registry_record_builder_builds_choice_records_from_choices_and_votes(tmp_path: Path) -> None:
    workspace = _workspace_with_records(tmp_path)
    service = workspace._registry_record_builder_service()

    choices = service.choice_records()
    choice_by_id = {choice["id"]: choice for choice in choices}

    assert choice_by_id["CHOICE-001"]["options"] == ["A", "B"]
    assert choice_by_id["CHOICE-PROP-001"]["proposal"] == "PROP-001"
    assert choice_by_id["CHOICE-PROP-001"]["options"] == ["A"]
    assert choice_by_id["CHOICE-PROP-001"]["selected_option"] == "A"


def test_registry_record_builder_builds_relation_and_artifact_records(tmp_path: Path) -> None:
    workspace = _workspace_with_records(tmp_path)
    service = workspace._registry_record_builder_service()
    proposals = service.proposal_records()
    changes = service.change_records()

    relations = service.relation_records(proposals, changes)
    artifacts = service.artifact_records(proposals, changes)

    assert {"source": "CHANGE-001", "target": "PROP-001", "type": "includes", "rationale": "Change Set includes accepted proposal.", "source_artifact": ".p2p/changes/CHANGE-001-registry-proposal"} in relations
    assert {"source": "CHANGE-001", "target": "PROP-999", "type": "references", "rationale": "Change Set references proposal as context.", "source_artifact": ".p2p/changes/CHANGE-001-registry-proposal"} in relations
    assert any(artifact["owner_type"] == "proposal" and artifact["artifact_type"] == "proposal.md" for artifact in artifacts)
    assert any(artifact["owner_type"] == "change" and artifact["artifact_type"] == "change.md" for artifact in artifacts)

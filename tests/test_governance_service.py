from pathlib import Path

import pytest
import yaml

from p2p_engine.storage.filesystem import P2PWorkspace


def _load_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_governance_service_initializes_files_and_status(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    service = workspace._governance_service()

    written = service.init_governance("owner_decides")
    status = service.governance_status()

    assert written == [
        Path(".p2p/governance/governance.yml"),
        Path(".p2p/governance/roles.yml"),
        Path(".p2p/governance/decision-precedents.yml"),
    ]
    assert status.mode == "owner_decides"
    assert status.roles_count == 1
    assert status.precedents_count == 0
    assert status.governance_file == Path(".p2p/governance/governance.yml")


def test_governance_service_rejects_invalid_mode(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    with pytest.raises(ValueError, match="Unsupported governance mode"):
        workspace._governance_service().init_governance("unknown")


def test_governance_service_records_vote_counts_and_result(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Governance Project")
    proposal = workspace.create_proposal("Vote Target")
    service = workspace._governance_service()

    first = service.record_vote(proposal.proposal_id, choice="A", reason="Prefer A", voter="owner", role="owner")
    second = service.record_vote(
        proposal.proposal_id,
        choice="A",
        reason="Still prefer A",
        voter="maintainer",
        role="maintainer",
    )

    votes = _load_yaml(tmp_path / proposal.path / "votes.yml")
    result = votes["result"]
    assert isinstance(result, dict)
    assert first.counts == {"A": 1}
    assert second.counts == {"A": 2}
    assert second.total_votes == 2
    assert second.winner == "A"
    assert second.tied is False
    assert result["winner"] == "A"
    assert result["tied"] is False


def test_governance_service_reports_tied_vote_status(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Governance Project")
    proposal = workspace.create_proposal("Tie Target")
    service = workspace._governance_service()

    service.record_vote(proposal.proposal_id, choice="A", reason="A", voter="one", role="owner")
    status = service.record_vote(proposal.proposal_id, choice="B", reason="B", voter="two", role="owner")

    assert status.counts == {"A": 1, "B": 1}
    assert status.total_votes == 2
    assert status.winner is None
    assert status.tied is True


def test_governance_service_rejects_malformed_votes_yaml(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Governance Project")
    proposal = workspace.create_proposal("Malformed Vote Target")
    votes_file = tmp_path / proposal.path / "votes.yml"
    votes_file.write_text("votes: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="expected `votes` list"):
        workspace._governance_service().vote_status(proposal.proposal_id)


def test_governance_service_records_precedents_and_requires_proposal(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Governance Project")
    proposal = workspace.create_proposal("Precedent Target")
    service = workspace._governance_service()

    first = service.record_precedent(proposal.proposal_id, "First precedent", "Reason 1")
    second = service.record_precedent(proposal.proposal_id, "Second precedent", "Reason 2")
    precedents = _load_yaml(tmp_path / ".p2p" / "governance" / "decision-precedents.yml")

    assert first == Path(".p2p/governance/decision-precedents.yml")
    assert second == Path(".p2p/governance/decision-precedents.yml")
    assert [item["id"] for item in precedents["precedents"]] == ["DP001", "DP002"]
    with pytest.raises(ValueError, match="Proposal not found"):
        service.record_precedent("PROP-999", "Missing", "No proposal")

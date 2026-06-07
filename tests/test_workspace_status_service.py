from pathlib import Path

from p2p_engine.services.workspace_status import WorkspaceStatusService
from p2p_engine.storage.filesystem import P2PWorkspace


def test_workspace_status_service_reads_project_and_proposals(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    proposal_dir = p2p_dir / "proposals" / "PROP-001-demo"
    proposal_dir.mkdir(parents=True)
    (p2p_dir / "project.yml").write_text("project:\n  name: Demo Project\n", encoding="utf-8")
    (proposal_dir / "proposal.md").write_text(
        "# PROP-001 - Demo Proposal\n\n"
        "## Status `accepted`\n\n"
        "## Problem\n\n"
        "Need a proposal.\n",
        encoding="utf-8",
    )
    service = WorkspaceStatusService(root=tmp_path, p2p_dir=p2p_dir)

    status = service.status()
    accepted = service.proposal_summaries("accepted")

    assert status.project_name == "Demo Project"
    assert status.proposals[0].proposal_id == "PROP-001"
    assert status.proposals[0].slug == "PROP-001-demo"
    assert status.proposals[0].status == "accepted"
    assert status.proposals[0].title == "Demo Proposal"
    assert accepted == status.proposals
    assert service.proposal_summaries("draft") == []


def test_workspace_status_service_reports_missing_required_paths(tmp_path: Path) -> None:
    service = WorkspaceStatusService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    check = service.check()

    assert check.ok is False
    assert Path(".p2p/project.yml") in check.missing
    assert Path(".p2p/proposals") in check.missing


def test_workspace_status_facade_delegates(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Facade Project")
    workspace.create_proposal_with_details(
        title="Facade Proposal",
        problem="Need a facade check.",
        proposal="Keep compatibility.",
        acceptance_criteria=["Status remains visible."],
    )

    status = workspace.status()
    summaries = workspace.proposal_summaries("draft")
    check = workspace.check()

    assert status.project_name == "Facade Project"
    assert summaries[0].proposal_id == "PROP-001"
    assert summaries[0].title == "Facade Proposal"
    assert check.ok is True

from pathlib import Path

import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.changes import ChangeSetLifecycleService
from p2p_engine.services.project_maturity import ProjectMaturityService
from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.storage.filesystem import P2PWorkspace


def _service(workspace: P2PWorkspace) -> ProjectMaturityService:
    proposal_documents = ProposalDocumentService(root=workspace.root, p2p_dir=workspace.p2p_dir)
    changes = ChangeSetLifecycleService(
        root=workspace.root,
        p2p_dir=workspace.p2p_dir,
        find_proposal_dir=proposal_documents.find_dir,
    )
    return ProjectMaturityService(
        root=workspace.root,
        p2p_dir=workspace.p2p_dir,
        proposal_summaries=workspace.proposal_summaries,
        find_proposal_dir=proposal_documents.find_dir,
        change_set_statuses=workspace.change_set_statuses,
        find_change_dir=changes.find_dir,
    )


def test_project_maturity_service_initializes_rubrics_and_domain_state(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    service = _service(workspace)

    rubrics = service.init_project_rubrics("software", force=True)
    domain = yaml.safe_load((tmp_path / ".p2p" / "project" / "domain.yml").read_text(encoding="utf-8"))
    project = yaml.safe_load((tmp_path / ".p2p" / "project.yml").read_text(encoding="utf-8"))

    assert rubrics.domain == "software"
    assert rubrics.status == "template_selected"
    assert any(criterion["id"] == "security_privacy" for criterion in rubrics.criteria)
    assert domain["template"] == "software"
    assert project["project"]["domain"] == "software"


def test_project_maturity_service_preview_is_read_only(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    rubrics_path = tmp_path / ".p2p" / "project" / "rubrics.yml"
    before = rubrics_path.read_text(encoding="utf-8")

    preview = _service(workspace).init_project_rubrics_preview("software")

    assert any(criterion["id"] == "security_privacy" for criterion in preview)
    assert rubrics_path.read_text(encoding="utf-8") == before


def test_project_maturity_service_scores_accepted_evidence(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project", project_domain="software")
    proposal = workspace.create_proposal_with_details(
        title="Security Model",
        problem="Security and privacy need explicit permission boundaries.",
        proposal="Define auth, sandbox permissions, and privacy expectations.",
    )
    workspace.record_decision(proposal.proposal_id, DecisionOutcome.accepted, "Needed.", "owner")

    maturity = _service(workspace).refresh_definition_maturity()
    security = next(criterion for criterion in maturity.criteria if criterion["id"] == "security_privacy")

    assert maturity.domain == "software"
    assert maturity.score > 0
    assert security["status"] == "covered"
    assert security["score"] == 100
    assert (tmp_path / ".p2p" / "project" / "maturity-assessment.yml").exists()


def test_project_maturity_service_reports_unresolved_rubrics(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")

    maturity = _service(workspace).refresh_definition_maturity()

    assert maturity.status == "rubric_missing"
    assert maturity.score == 0
    assert "Project definition rubric is unresolved or has no enabled criteria." in maturity.gaps
    assert "Define the project domain with the user and agent." in maturity.suggested_actions

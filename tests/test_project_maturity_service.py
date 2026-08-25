from pathlib import Path

import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.changes import ChangeSetLifecycleService
from p2p_engine.services.project_maturity import ProjectMaturityService
from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


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


def test_project_maturity_service_initializes_generic_rubrics_without_changing_domain(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project", project_domain="gardening")
    service = _service(workspace)

    rubrics = service.init_project_rubrics("generic", force=True)
    domain = yaml.safe_load((tmp_path / ".p2p" / "project" / "domain.yml").read_text(encoding="utf-8"))
    project = yaml.safe_load((tmp_path / ".p2p" / "project.yml").read_text(encoding="utf-8"))

    assert rubrics.structure_source == "generic"
    assert rubrics.status == "starter_selected"
    assert any(criterion["id"] == "vision_clarity" for criterion in rubrics.criteria)
    assert domain["project_domain"]["descriptor"]["key"] == "gardening"
    assert "domain" not in project["project"]


def test_project_maturity_service_preview_is_read_only(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project")
    rubrics_path = tmp_path / ".p2p" / "project" / "rubrics.yml"
    before = rubrics_path.read_text(encoding="utf-8")

    preview = _service(workspace).init_project_rubrics_preview("generic")

    assert any(criterion["id"] == "vision_clarity" for criterion in preview)
    assert rubrics_path.read_text(encoding="utf-8") == before


def test_project_maturity_service_scores_accepted_evidence(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project", project_domain="software", starter_id="generic")
    proposal = workspace.create_proposal_with_details(
        title="Security Model",
        problem="Security and privacy risks need explicit permission boundaries.",
        proposal="Define auth, sandbox permissions, and privacy expectations.",
    )
    record_decision(workspace, proposal.proposal_id, DecisionOutcome.accepted, "Needed.", "owner")

    maturity = _service(workspace).refresh_definition_maturity()
    risks = next(criterion for criterion in maturity.criteria if criterion["id"] == "risk_coverage")

    assert maturity.structure_source == "binarya/base_project@2.0.0"
    assert maturity.score > 0
    assert risks["status"] == "covered"
    assert risks["score"] == 100
    assert (tmp_path / ".p2p" / "project" / "maturity-assessment.yml").exists()


def test_project_maturity_service_reports_unresolved_rubrics(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo Project", starter_id="empty")

    maturity = _service(workspace).refresh_definition_maturity()

    assert maturity.status == "rubric_missing"
    assert maturity.score == 0
    assert "Project definition rubric is unresolved or has no enabled criteria." in maturity.gaps
    assert "Select a vertical release or edit the project structure." in maturity.suggested_actions


def test_vertical_rubric_generation_preserves_enabled_flags_and_maturity_scope(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Vertical Rubrics")
    workspace.select_project_vertical("base_project", actor="owner")
    rubrics_path = tmp_path / ".p2p" / "project" / "rubrics.yml"
    rubrics = yaml.safe_load(rubrics_path.read_text(encoding="utf-8"))
    rubrics["criteria"][0]["enabled"] = False
    rubrics_path.write_text(yaml.safe_dump(rubrics, sort_keys=False), encoding="utf-8")

    workspace.select_project_vertical("base_project", actor="owner")
    refreshed = yaml.safe_load(rubrics_path.read_text(encoding="utf-8"))
    maturity = _service(workspace).refresh_definition_maturity()

    assert refreshed["criteria"][0]["enabled"] is False
    assert refreshed["selected_scope"]["disabled"] == 1
    assert maturity.disabled_criteria_count == 1
    assert maturity.total_default_criteria_count == refreshed["selected_scope"]["total_default"]
    assert maturity.scope_label == "selected_project_rubric"

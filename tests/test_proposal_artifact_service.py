from pathlib import Path

import pytest

from p2p_engine.storage.filesystem import P2PWorkspace


def test_proposal_artifact_service_generates_prompt_with_context(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal_with_details(
        "Prompt Target",
        problem="The problem is concrete.",
        proposal="Use a dedicated service.",
    )
    service = workspace._proposal_artifact_service()

    path = service.generate_prompt(proposal.proposal_id, "digest")
    content = (tmp_path / path).read_text(encoding="utf-8")

    assert path == Path(".p2p/prompts/PROP-001/digest.prompt.md")
    assert "The problem is concrete." in content
    assert "## Governance Context" in content


def test_proposal_artifact_service_imports_exploration_file_and_reports_status(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("Exploration Target")
    source = tmp_path / "exploration-output.md"
    source.write_text("# Exploration\n\nConcrete output.\n", encoding="utf-8")
    service = workspace._proposal_artifact_service()

    imported = service.import_exploration(proposal.proposal_id, source)
    status = service.exploration_status(proposal.proposal_id)
    exploration = next(artifact for artifact in status.artifacts if artifact.filename == "exploration.md")

    assert imported == [proposal.path / "exploration.md"]
    assert exploration.exists is True
    assert exploration.has_content is True
    assert exploration.quality_state == "thin"
    assert status.suggested_next_command == "p2p explore prompt PROP-001"


def test_proposal_artifact_service_imports_exploration_directory_and_rejects_empty(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("Exploration Directory Target")
    source = tmp_path / "exploration"
    source.mkdir()
    (source / "findings.md").write_text("# Findings\n\nMeaningful finding.\n", encoding="utf-8")
    empty = tmp_path / "empty"
    empty.mkdir()
    service = workspace._proposal_artifact_service()

    imported = service.import_exploration(proposal.proposal_id, source)

    assert imported == [proposal.path / "findings.md"]
    with pytest.raises(ValueError, match="No exploration artifacts found"):
        service.import_exploration(proposal.proposal_id, empty)


def test_proposal_artifact_service_imports_generated_artifacts_and_validates_tasks(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("Generated Artifact Target")
    clarify = tmp_path / "clarify.md"
    clarify.write_text("# Clarify\n\nQuestion answered.\n", encoding="utf-8")
    tasks = tmp_path / "tasks.yml"
    tasks.write_text("tasks: []\n", encoding="utf-8")
    invalid_tasks = tmp_path / "invalid-tasks.yml"
    invalid_tasks.write_text("not_tasks: []\n", encoding="utf-8")
    service = workspace._proposal_artifact_service()

    clarify_path = service.import_artifact(proposal.proposal_id, "clarify", clarify)
    tasks_path = service.import_artifact(proposal.proposal_id, "tasks", tasks)

    assert clarify_path == proposal.path / "clarifications.md"
    assert tasks_path == proposal.path / "tasks.yml"
    with pytest.raises(ValueError, match="Invalid tasks YAML"):
        service.import_artifact(proposal.proposal_id, "tasks", invalid_tasks)


def test_proposal_artifact_service_imports_impact_artifacts_and_validates_keys(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Artifact Project")
    proposal = workspace.create_proposal("Impact Target")
    service = workspace._proposal_artifact_service()
    impact = tmp_path / "impact.yml"
    impact.write_text("impact: []\n", encoding="utf-8")
    source_dir = tmp_path / "impact-dir"
    source_dir.mkdir()
    (source_dir / "impact-map.yml").write_text("impact: []\n", encoding="utf-8")
    (source_dir / "related-proposals.yml").write_text("related_proposals: []\n", encoding="utf-8")
    invalid = tmp_path / "invalid-impact.yml"
    invalid.write_text("wrong: []\n", encoding="utf-8")

    file_imported = service.import_impact(proposal.proposal_id, impact)
    dir_imported = service.import_impact(proposal.proposal_id, source_dir)

    assert file_imported == [proposal.path / "impact-map.yml"]
    assert proposal.path / "impact-map.yml" in dir_imported
    assert proposal.path / "related-proposals.yml" in dir_imported
    with pytest.raises(ValueError, match="expected top-level `impact` key"):
        service.import_impact(proposal.proposal_id, invalid)

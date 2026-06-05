from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.software_spec import SoftwareSpecService
from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace_with_change(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Demo Project")
    workspace.create_proposal_with_details(
        title="Spec Work",
        problem="Need implementation-facing specs.",
        proposal="Generate a deterministic software spec.",
        acceptance_criteria=["Spec artifacts exist."],
    )
    workspace.record_decision(
        "PROP-001",
        DecisionOutcome.accepted,
        reason="Needed before export.",
        approver="owner",
    )
    workspace.create_change_set("PROP-001")
    return workspace


def _service(workspace: P2PWorkspace) -> SoftwareSpecService:
    return SoftwareSpecService(
        root=workspace.root,
        p2p_dir=workspace.p2p_dir,
        find_change_dir=workspace._find_change_dir,
        show_proposal=workspace.show_proposal,
        show_change_set=workspace.show_change_set,
        find_proposal_dir=workspace._find_proposal_dir,
    )


def test_software_spec_service_refresh_status_show_prompt_and_import(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)

    refreshed = service.refresh("CHANGE-001")

    assert refreshed.change_id == "CHANGE-001"
    assert refreshed.status == "generated"
    assert refreshed.path == Path(".p2p/outputs/software-spec/CHANGE-001")

    spec_dir = tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001"
    for filename in service.required_files():
        assert (spec_dir / filename).exists()
    assert "Software Spec - CHANGE-001 - Spec Work" in service.show("CHANGE-001")
    assert service.statuses()[0].status == "generated"

    prompt = service.create_prompt("CHANGE-001")
    assert prompt.prompt_path == Path(".p2p/outputs/software-spec/CHANGE-001/spec-refine.prompt.md")
    assert "P2P Software Spec Refinement Prompt" in (tmp_path / prompt.prompt_path).read_text(encoding="utf-8")

    refined_dir = tmp_path / "refined"
    refined_dir.mkdir()
    for filename in ("index.md", "requirements.md", "design.md", "acceptance.md"):
        (refined_dir / filename).write_text(f"# {filename}\n\nRefined.\n", encoding="utf-8")
    (refined_dir / "commands.yml").write_text("commands: []\n", encoding="utf-8")
    (refined_dir / "data-model.yml").write_text("entities: []\n", encoding="utf-8")
    (refined_dir / "provenance.yml").write_text("source:\n  change: CHANGE-001\n", encoding="utf-8")

    imported = service.import_spec("CHANGE-001", refined_dir)

    assert Path(".p2p/outputs/software-spec/CHANGE-001/index.md") in imported
    assert "Refined." in service.show("CHANGE-001")


def test_software_spec_service_import_validation_errors(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)
    service = _service(workspace)
    source = tmp_path / "broken"
    source.mkdir()

    with pytest.raises(ValueError, match="Missing required software spec artifact: index.md"):
        service.import_spec("CHANGE-001", source)

    for filename in service.required_files():
        (source / filename).write_text("# ok\n", encoding="utf-8")
    (source / "commands.yml").write_text("other: []\n", encoding="utf-8")
    (source / "data-model.yml").write_text("entities: []\n", encoding="utf-8")
    (source / "provenance.yml").write_text("source: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid YAML: expected top-level `commands` key."):
        service.import_spec("CHANGE-001", source)

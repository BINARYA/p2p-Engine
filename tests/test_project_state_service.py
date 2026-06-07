from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.project_state import ProjectStateService
from p2p_engine.storage.filesystem import P2PWorkspace


@dataclass(frozen=True)
class _NextAction:
    action_id: str
    priority: str
    kind: str
    target: str


@dataclass(frozen=True)
class _RegistryStatus:
    registries_dir: Path
    stale: bool
    proposals_count: int
    changes_count: int


def _accepted(tmp_path):
    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-001-project-state"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_dir.joinpath("tasks.yml").write_text("tasks:\n  - id: T001\n", encoding="utf-8")
    return [
        {
            "proposal_id": "PROP-001",
            "title": "Project State",
            "status": "accepted",
            "feature_id": "project-state",
            "source": ".p2p/proposals/PROP-001-project-state",
            "path": proposal_dir,
            "problem": "The project needs generated state.",
            "goals": "- Keep state visible.",
            "non_goals": "- Do not decide for the owner.",
            "proposal": "Generate project state artifacts.",
            "decision": "# Decision - PROP-001\n\n## Status\n\n`accepted`\n",
        }
    ]


def _service(tmp_path):
    return ProjectStateService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        accepted_proposals=lambda: _accepted(tmp_path),
        project_name=lambda: "Demo Project",
        next_actions=lambda: [_NextAction("NEXT-001", "high", "create_change", "PROP-001")],
        registry_status=lambda: _RegistryStatus(Path(".p2p/registries"), False, 1, 1),
        project_brief_context=lambda status: f"# Project Brief Context\n\n- Path: `{status.registries_dir}`\n",
        validate_yaml_key=lambda content, key: None if f"{key}:" in content else (_ for _ in ()).throw(ValueError(key)),
    )


def test_project_state_service_refresh_writes_project_and_feature_artifacts(tmp_path) -> None:
    service = _service(tmp_path)

    written = service.refresh()

    assert Path(".p2p/project/overview.md") in written
    assert Path(".p2p/project/features/project-state/feature.md") in written
    overview = (tmp_path / ".p2p" / "project" / "overview.md").read_text(encoding="utf-8")
    feature = (tmp_path / ".p2p" / "project" / "features" / "project-state" / "feature.md").read_text(
        encoding="utf-8"
    )
    tasks = (tmp_path / ".p2p" / "project" / "features" / "project-state" / "tasks.yml").read_text(
        encoding="utf-8"
    )
    assert "# Project State - Demo Project" in overview
    assert "PROP-001 - Project State" in overview
    assert "Generate project state artifacts." in feature
    assert "id: T001" in tasks
    assert (tmp_path / ".p2p" / "project" / "conflicts.yml").exists()


def test_project_state_service_status_and_show(tmp_path) -> None:
    service = _service(tmp_path)
    service.refresh()

    status = service.status()
    overview = service.show("overview")
    feature = service.show("project-state")

    assert status.accepted_proposals == 1
    assert status.features == ["project-state"]
    assert status.operational_brief_available is False
    assert status.next_actions_count == 1
    assert status.first_next_action is not None
    assert "# Project State - Demo Project" in overview
    assert "# Project State" in feature
    with pytest.raises(ValueError, match="Project section not found: missing"):
        service.show("missing")


def test_project_state_service_brief_prompt_import_and_show(tmp_path) -> None:
    service = _service(tmp_path)

    prompt = service.create_brief_prompt()
    output_dir = tmp_path / "brief-output"
    output_dir.mkdir()
    output_dir.joinpath("operational-brief.md").write_text("# Operational Brief\n\nReady.\n", encoding="utf-8")
    output_dir.joinpath("next-actions.yml").write_text("next_actions:\n  - id: NEXT-001\n", encoding="utf-8")
    imported = service.import_brief(output_dir)
    shown = service.show_brief()

    assert prompt.context_path == Path(".p2p/project/brief-context.md")
    assert prompt.prompt_path == Path(".p2p/project/brief.prompt.md")
    assert "P2P Operational Brief Prompt" in (tmp_path / prompt.prompt_path).read_text(encoding="utf-8")
    assert Path(".p2p/project/operational-brief.md") in imported
    assert Path(".p2p/project/next-actions.yml") in imported
    assert "Ready." in shown

    single = tmp_path / "brief.md"
    single.write_text("# Operational Brief\n\nSingle file.\n", encoding="utf-8")
    assert service.import_brief(single) == [Path(".p2p/project/operational-brief.md")]
    assert "Single file." in service.show_brief()
    with pytest.raises(ValueError, match="Project brief source not found"):
        service.import_brief(tmp_path / "missing")


def test_workspace_project_state_facade_delegates(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Project State Facade")
    proposal = workspace.create_proposal("Facade State")
    workspace.record_decision(proposal.proposal_id, DecisionOutcome.accepted, "Ready.", "owner")

    written = workspace.refresh_project_state()
    status = workspace.project_state_status()
    overview = workspace.show_project_state("overview")
    prompt = workspace.create_project_brief_prompt()

    assert Path(".p2p/project/overview.md") in written
    assert status.accepted_proposals == 1
    assert "Facade State" in overview
    assert prompt.prompt_path == Path(".p2p/project/brief.prompt.md")

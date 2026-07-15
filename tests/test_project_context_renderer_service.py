from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from p2p_engine.services.project_contexts import ProjectContextRendererService


@dataclass(frozen=True)
class _RegistryStatus:
    registries_dir: Path
    stale: bool = False
    proposals_count: int = 1
    changes_count: int = 1


@dataclass(frozen=True)
class _RegistryView:
    records: list[dict[str, object]]


@dataclass(frozen=True)
class _IntakeStatus:
    intake_id: str
    status: str
    recommendation: str


def _service(tmp_path: Path, registries: dict[str, list[dict[str, object]]], intake=None) -> ProjectContextRendererService:
    def show_registry(name: str) -> _RegistryView:
        if name not in registries:
            raise ValueError(f"Registry not found: {name}")
        return _RegistryView(registries[name])

    return ProjectContextRendererService(
        p2p_dir=tmp_path / ".p2p",
        show_registry=show_registry,
        intake_statuses=lambda: intake or [],
    )


def test_project_context_renderer_never_falls_back_to_registry_order_for_intake(tmp_path: Path) -> None:
    project_dir = tmp_path / ".p2p" / "project"
    project_dir.mkdir(parents=True)
    (project_dir / "overview.md").write_text("# Overview\n\nCurrent project.", encoding="utf-8")
    service = _service(
        tmp_path,
        {
            "proposals": [{"id": "PROP-001", "status": "draft", "title": "Draft"}],
            "changes": [],
            "decisions": [{"proposal": "PROP-001", "outcome": "accepted", "title": "Draft"}],
        },
    )

    context = service.render_intake_context(_RegistryStatus(Path(".p2p/registries")))

    assert "# Intake Context" in context
    assert "- Path: `.p2p/registries`" in context
    assert "PROP-001: draft - Draft" not in context
    assert "No registry-order fallback is used." in context
    assert "## Project Overview\n\n# Overview\n\nCurrent project." in context


def test_project_context_renderer_renders_project_brief_context_with_project_files_and_intake(tmp_path: Path) -> None:
    project_dir = tmp_path / ".p2p" / "project"
    project_dir.mkdir(parents=True)
    (project_dir / "overview.md").write_text("# Overview\n\nCurrent project.", encoding="utf-8")
    (project_dir / "scope.md").write_text("# Scope\n\nCurrent scope.", encoding="utf-8")
    (project_dir / "conflicts.yml").write_text("conflicts: []\n", encoding="utf-8")
    service = _service(
        tmp_path,
        {
            "proposals": [{"id": "PROP-001", "status": "accepted", "title": "Accepted"}],
            "changes": [{"id": "CHANGE-001", "status": "proposed", "title": "Change", "included_proposals": ["PROP-001"]}],
            "choices": [{"id": "CHOICE-001", "status": "open", "title": "Choice", "selected_option": None}],
            "decisions": [{"proposal": "PROP-001", "outcome": "accepted", "title": "Accepted"}],
            "relations": [],
        },
        intake=[_IntakeStatus("INTAKE-001", "imported", "create proposal")],
    )

    context = service.render_project_brief_context(_RegistryStatus(Path(".p2p/registries")))

    assert "# Project Brief Context" in context
    assert "not to make governance decisions." in context
    assert "- CHANGE-001: proposed - Change (proposals: PROP-001)" in context
    assert "- CHOICE-001: open - Choice -> not decided" in context
    assert "## Project Overview\n\n# Overview\n\nCurrent project." in context
    assert "## Project Scope\n\n# Scope\n\nCurrent scope." in context
    assert "## Project Conflicts\n\nconflicts: []" in context
    assert "- INTAKE-001: imported - create proposal" in context


def test_project_context_renderer_formats_choice_selected_option_and_missing_changes(tmp_path: Path) -> None:
    service = _service(
        tmp_path,
        {
            "proposals": [],
            "choices": [{"id": "CHOICE-002", "status": "decided", "title": "Choice", "selected_option": "B"}],
            "decisions": [],
            "relations": [],
        },
    )

    context = service.render_project_brief_context(_RegistryStatus(Path(".p2p/registries")))

    assert "## Changes Registry\n\nNot generated yet." in context
    assert "- CHOICE-002: decided - Choice -> B" in context
    assert "## Intake Status\n\n- None." in context

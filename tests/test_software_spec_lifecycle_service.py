from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.foundation.markdown import read_frontmatter, replace_frontmatter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


def _workspace_with_change(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Lifecycle Demo")
    workspace.create_proposal_with_details(
        title="Spec Work",
        problem="Need governed implementation specs.",
        proposal="Generate a P2P-native software spec.",
        acceptance_criteria=["Spec lifecycle preflight passes."],
    )
    record_decision(workspace, "PROP-001", DecisionOutcome.accepted, reason="Ready.", approver="owner")
    workspace.create_change_set("PROP-001")
    return workspace


def _change_path(root: Path) -> Path:
    return root / ".p2p" / "changes" / "CHANGE-001-spec-work" / "change.md"


def _replace_change_source(root: Path, source: dict[str, object]) -> None:
    path = _change_path(root)
    text = path.read_text(encoding="utf-8")
    frontmatter = read_frontmatter(text)
    frontmatter["source"] = source
    path.write_text(replace_frontmatter(text, frontmatter), encoding="utf-8")


def test_lifecycle_routes_are_deterministic_without_writes(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Route Demo")

    chat = workspace.software_spec_lifecycle("chat_exploration")
    exact = workspace.software_spec_lifecycle("exact_file_request")

    assert chat.intent == "chat_exploration"
    assert chat.writes_state is False
    assert chat.write_class == "chat_only"
    assert exact.canonical_status == "not_p2p_governed_unless_imported_or_declared"
    assert not (tmp_path / ".p2p" / "outputs").exists()


def test_lifecycle_preflight_accepts_governed_source_with_advisories(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)

    view = workspace.software_spec_lifecycle("implementation_spec", change_id="CHANGE-001")

    assert view.blockers == []
    assert {item.code for item in view.advisories} >= {
        "software_vertical_not_active",
        "project_definition_missing",
    }
    assert f"p2p spec refresh --change {view.change_id}" in view.suggested_commands


def test_lifecycle_preflight_blocks_missing_change_and_ungoverned_source(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)

    missing = workspace.software_spec_lifecycle("implementation_spec", change_id="CHANGE-999")
    assert missing.blockers[0].code == "change_not_found"

    _replace_change_source(tmp_path, {"accepted_proposals": []})
    ungoverned = workspace.software_spec_lifecycle("implementation_spec", change_id="CHANGE-001")

    assert ungoverned.blockers[0].code == "missing_governed_source"
    with pytest.raises(ValueError, match="missing_governed_source"):
        workspace.refresh_software_spec("CHANGE-001")
    assert not (tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001").exists()


def test_lifecycle_preflight_blocks_non_accepted_source_and_choice_blocker(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)
    workspace.create_proposal_with_details(
        title="Draft Source",
        problem="Draft proposal should not drive implementation specs.",
    )
    _replace_change_source(tmp_path, {"accepted_proposals": ["PROP-002"]})

    draft_source = workspace.software_spec_lifecycle("implementation_spec", change_id="CHANGE-001")

    assert draft_source.blockers[0].code == "source_decision_inactive"

    _replace_change_source(tmp_path, {"accepted_proposals": ["PROP-001"]})
    choice = workspace.create_choice("Architecture Choice", ["A", "B"])
    workspace.block_choice(choice.choice_id, "CHANGE-001", "change", "Architecture must be decided first.")

    blocked = workspace.software_spec_lifecycle("implementation_spec", change_id="CHANGE-001")

    assert any(item.code == "blocking_choice_unresolved" for item in blocked.blockers)


def test_lifecycle_allows_refresh_and_export_with_advisory_only_state(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)

    spec = workspace.refresh_software_spec("CHANGE-001")
    export = workspace.export_software_spec("CHANGE-001", "generic")

    assert spec.status == "generated"
    assert spec.lifecycle is not None
    assert export.status == "exported"
    assert export.lifecycle is not None
    assert (tmp_path / ".p2p" / "outputs" / "software-spec" / "CHANGE-001").exists()
    assert (tmp_path / ".p2p" / "outputs" / "spec-export" / "CHANGE-001" / "generic").exists()


def test_software_vertical_definition_reduces_inactive_advisory(tmp_path: Path) -> None:
    workspace = _workspace_with_change(tmp_path)
    workspace.select_project_vertical("software_project", actor="owner")

    view = workspace.software_spec_lifecycle("implementation_spec", change_id="CHANGE-001")

    assert "software_vertical_not_active" not in {item.code for item in view.advisories}
    assert any(item.code == "project_definition_incomplete" for item in view.advisories)


def test_project_definition_patch_can_fill_required_software_fields(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Software Definition Demo", vertical_id="software_project")
    definition = workspace.project_definition_view()

    assert definition.state is not None
    objective = next(section for section in definition.state.sections if section.section_id == "system_objective")
    assert objective.missing_required_fields == ["objective", "success_signal"]

    patch = tmp_path / "software-definition-patch.yml"
    patch.write_text(
        yaml.safe_dump(
            {
                "project_definition_patch": {
                    "schema_version": 1,
                    "actor": "owner",
                    "operations": [
                        {
                            "op": "set_field",
                            "section_id": "system_objective",
                            "field_id": "objective",
                            "value": "Ship governed software specs.",
                        },
                        {
                            "op": "set_field",
                            "section_id": "system_objective",
                            "field_id": "success_signal",
                            "value": "Spec refresh and export pass preflight.",
                        },
                    ],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = workspace.update_project_definition(patch)
    updated = next(section for section in result.state.sections if section.section_id == "system_objective")

    assert updated.missing_required_fields == []

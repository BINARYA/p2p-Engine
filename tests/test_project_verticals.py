from __future__ import annotations

from importlib import resources
from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.storage.filesystem import P2PWorkspace

runner = CliRunner()


def test_project_verticals_list_internal_packs_and_fallback_base(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Vertical Demo")

    verticals = workspace.project_verticals()
    active = workspace.active_project_vertical()
    ids = {vertical.vertical_id for vertical in verticals}

    assert active.vertical_id == "base_project"
    assert active.fallback_used is True
    assert {"base_project", "packaging_or_physical_product_design", "social_impact_program_design"} <= ids


def test_project_vertical_show_composes_base_project_sections(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Vertical Demo")

    pack = workspace.show_project_vertical("social_impact_program_design")
    section_ids = [section.section_id for section in pack.sections]

    assert pack.extends == "base_project"
    assert "vision" in section_ids
    assert "theory_of_change" in section_ids


def test_project_vertical_candidate_can_be_added_and_selected(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Vertical Demo")
    candidate = workspace.propose_project_vertical("progettare la scatola perfetta")
    candidate_path = tmp_path / "candidate.yml"
    candidate_path.write_text(candidate.yaml_text, encoding="utf-8")

    added = workspace.add_project_vertical(candidate_path, activate=True, actor="owner")
    active = workspace.active_project_vertical()

    assert added.vertical_id == "packaging_or_physical_product_design"
    assert added.activated is True
    assert active.vertical_id == "packaging_or_physical_product_design"
    assert active.source == "project_local"
    assert active.fallback_used is False


def test_project_vertical_project_local_pack_overrides_internal(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Vertical Demo")
    candidate = workspace.propose_project_vertical("progettare la scatola perfetta")
    payload = yaml.safe_load(candidate.yaml_text)
    payload["vertical_candidate"]["candidate"]["name"] = "Local Packaging Override"
    candidate_path = tmp_path / "candidate.yml"
    candidate_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    workspace.add_project_vertical(candidate_path)
    pack = workspace.show_project_vertical("packaging_or_physical_product_design")

    assert pack.name == "Local Packaging Override"
    assert pack.source == "project_local"


def test_project_vertical_validation_reports_duplicate_ids(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Vertical Demo")
    invalid_path = tmp_path / "invalid.yml"
    invalid_path.write_text(
        "vertical:\n"
        "  schema_version: 1\n"
        "  id: duplicate_demo\n"
        "  name: Duplicate Demo\n"
        "  version: 1.0.0\n"
        "  description: Invalid duplicate section demo.\n"
        "  sections:\n"
        "    - {id: same, title: Same, purpose: First}\n"
        "    - {id: same, title: Same Again, purpose: Second}\n"
        "  rubrics:\n"
        "    - {id: coverage, title: Coverage, section_id: same}\n"
        "  questions:\n"
        "    - {id: question, section_id: same, question: 'What is needed?'}\n"
        "  artifacts:\n"
        "    - {id: brief, title: Brief, section_ids: [same]}\n",
        encoding="utf-8",
    )

    result = workspace.validate_project_vertical(str(invalid_path))

    assert result.valid is False
    assert any("duplicate id" in issue.message for issue in result.issues)


def test_project_readiness_review_uses_declared_coverage_and_reports_missing_sections(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Impact Demo", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Impact Measurement",
            "--problem",
            "The bank needs credible social impact metrics.",
            "--proposal",
            "Define outcome metrics and reporting cadence.",
            "--acceptance",
            "Metrics are recorded.",
            "--root",
            str(tmp_path),
        ],
    )
    runner.invoke(app, ["proposal", "accept", "PROP-001", "--reason", "Ready.", "--root", str(tmp_path)])
    runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Unrelated Draft",
            "--problem",
            "A separate operational note.",
            "--root",
            str(tmp_path),
        ],
    )
    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-001-impact-measurement"
    (proposal_dir / "vertical-coverage.yml").write_text(
        "vertical_coverage:\n"
        "  schema_version: 1\n"
        "  proposal_id: PROP-001\n"
        "  vertical_id: social_impact_program_design\n"
        "  sections:\n"
        "    - id: measurement_reporting\n"
        "      relevance: direct\n"
        "      rationale: The proposal defines metrics and reporting cadence.\n",
        encoding="utf-8",
    )
    workspace = P2PWorkspace(tmp_path)
    workspace.select_project_vertical("social_impact_program_design", actor="owner")

    review = workspace.review_project_readiness()
    sections = {section.section_id: section for section in review.sections}

    assert review.active_vertical_id == "social_impact_program_design"
    assert sections["measurement_reporting"].status == "covered"
    assert "PROP-001" in sections["measurement_reporting"].proposals
    assert "theory_of_change" in review.missing_capisaldi
    assert "PROP-002" in review.unmapped_proposals
    assert review.generated_questions


def test_project_vertical_cli_and_validation_flow(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Vertical CLI Demo", "--root", str(tmp_path)])

    listed = runner.invoke(app, ["project", "vertical", "list", "--root", str(tmp_path)])
    assert listed.exit_code == 0
    assert "Project verticals" in listed.output
    assert "fallback_used: true" in listed.output

    shown = runner.invoke(app, ["project", "vertical", "show", "base_project", "--root", str(tmp_path)])
    assert shown.exit_code == 0
    assert "Project vertical" in shown.output
    assert "vision" in shown.output

    validated = runner.invoke(app, ["project", "vertical", "validate", "base_project", "--root", str(tmp_path)])
    assert validated.exit_code == 0
    assert "Project vertical valid" in validated.output

    proposed = runner.invoke(
        app,
        ["project", "vertical", "propose", "progettare la scatola perfetta", "--root", str(tmp_path)],
    )
    assert proposed.exit_code == 0
    assert "Custom vertical candidate" in proposed.output
    assert "packaging_or_physical_product_design" in proposed.output

    review = runner.invoke(app, ["project", "readiness", "review", "--root", str(tmp_path)])
    assert review.exit_code == 0
    assert "Project readiness review" in review.output
    assert "fallback_used: true" in review.output
    assert "Generated questions:" in review.output


def test_project_validation_reports_invalid_vertical_coverage_section(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "Impact Demo", "--root", str(tmp_path)])
    runner.invoke(app, ["proposal", "create", "Invalid Coverage", "--root", str(tmp_path)])
    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-001-invalid-coverage"
    (proposal_dir / "vertical-coverage.yml").write_text(
        "vertical_coverage:\n"
        "  schema_version: 1\n"
        "  proposal_id: PROP-001\n"
        "  vertical_id: social_impact_program_design\n"
        "  sections:\n"
        "    - id: no_such_section\n"
        "      relevance: direct\n"
        "      rationale: Invalid on purpose.\n",
        encoding="utf-8",
    )

    result = P2PWorkspace(tmp_path).validate()

    assert result.ok is False
    assert any(finding.code == "P2P252_INVALID_PROPOSAL_VERTICAL_COVERAGE" for finding in result.findings)


def test_project_vertical_resources_are_packaged() -> None:
    root = resources.files("p2p_engine.resources.verticals")

    assert root.joinpath("base_project", "vertical.yml").is_file()
    assert root.joinpath("social_impact_program_design", "vertical.yml").is_file()

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "verify-release-artifacts.py"
)
SPEC = importlib.util.spec_from_file_location("verify_release_artifacts", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_release_matrix_uses_pytest_from_the_active_python_environment() -> None:
    workflow_path = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"
    )
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    test_matrix = workflow["jobs"]["test-matrix"]
    assert test_matrix["env"]["PYTEST_BIN"] == "pytest"
    assert test_matrix["strategy"]["matrix"]["python-version"] == ["3.11", "3.14"]


def test_release_verifier_requires_all_canonical_bundled_vertical_members() -> None:
    required = MODULE._vertical_pack_required_members("p2p_engine")

    for vertical_id, sections in MODULE.BUNDLED_VERTICAL_PACK_SECTIONS.items():
        root = f"p2p_engine/resources/verticals/{vertical_id}"
        assert f"{root}/manifest.yml" in required
        assert f"{root}/vertical.yml" in required
        assert f"{root}/rubrics.yml" in required
        assert {f"{root}/sections/{section}" for section in sections} <= required


def test_release_verifier_requires_decision_lifecycle_runtime_members() -> None:
    assert {
        "p2p_engine/core/proposal_decision_events.py",
        "p2p_engine/services/proposal_decision_ledger.py",
    } <= MODULE.DECISION_LIFECYCLE_WHEEL_MEMBERS
    assert {
        "src/p2p_engine/core/proposal_decision_events.py",
        "src/p2p_engine/services/proposal_decision_ledger.py",
        "tests/test_proposal_decision_service.py",
    } <= MODULE.DECISION_LIFECYCLE_SDIST_MEMBERS


def test_release_verifier_requires_current_schema_runtime_and_regression_members() -> None:
    assert {
        "p2p_engine/cli_commands/workspace_schema.py",
        "p2p_engine/cli_commands/workspace_transactions.py",
        "p2p_engine/core/workspace_schema.py",
        "p2p_engine/services/workspace_transactions.py",
        "p2p_engine/storage/filesystem.py",
    } <= MODULE.CURRENT_SCHEMA_WHEEL_MEMBERS
    assert {
        "src/p2p_engine/services/workspace_schema.py",
        "tests/test_cli_workspace_transactions.py",
        "tests/test_mutation_preview_and_writer.py",
        "tests/test_workspace_schema_service.py",
    } <= MODULE.CURRENT_SCHEMA_SDIST_MEMBERS


@pytest.mark.parametrize(
    "missing",
    [
        "p2p_engine/resources/verticals/base_project/manifest.yml",
        "p2p_engine/resources/verticals/software_project/rubrics.yml",
        (
            "p2p_engine/resources/verticals/"
            "social_impact_program_design/sections/010-social_impact_vision.yml"
        ),
    ],
)
def test_release_verifier_reports_missing_canonical_vertical_member(
    missing: str,
) -> None:
    required = MODULE._vertical_pack_required_members("p2p_engine")

    with pytest.raises(ValueError, match=missing):
        MODULE._require(required - {missing}, required, target="wheel")


@pytest.mark.parametrize(
    "missing",
    [
        "p2p_engine/core/proposal_decision_events.py",
        "p2p_engine/services/proposal_decision_ledger.py",
    ],
)
def test_release_verifier_reports_missing_decision_lifecycle_member(
    missing: str,
) -> None:
    required = MODULE.DECISION_LIFECYCLE_WHEEL_MEMBERS

    with pytest.raises(ValueError, match=missing):
        MODULE._require(required - {missing}, required, target="wheel")

from __future__ import annotations

import argparse
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


def test_release_candidate_matrix_uses_supported_isolated_python_versions() -> None:
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "release-candidate.yml"
    )
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    test_matrix = workflow["jobs"]["source-matrix"]
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
    assert "p2p_engine/services/proposal_decision_legacy.py" not in (
        MODULE.DECISION_LIFECYCLE_WHEEL_MEMBERS
    )


def test_release_verifier_requires_current_agent_surface_members() -> None:
    assert {
        "p2p_engine/services/agent_capabilities.py",
        "p2p_engine/services/agent_templates.py",
        "p2p_engine/services/public_surface_inventory.py",
    } <= MODULE.CURRENT_SURFACE_WHEEL_MEMBERS
    assert {
        "tests/test_current_only_surface.py",
        "tests/test_public_surface_inventory.py",
        "tests/test_version_consistency.py",
    } <= MODULE.CURRENT_SURFACE_SDIST_MEMBERS


def test_release_verifier_requires_uv_installation_contract_members() -> None:
    assert {
        "p2p_engine/cli_commands/doctor.py",
        "p2p_engine/services/installation_guidance.py",
        "p2p_engine/services/mcp_hints.py",
        "p2p_engine/services/runtime_contract.py",
    } <= MODULE.UV_INSTALLATION_WHEEL_MEMBERS
    assert {
        "docs/INSTALL.md",
        "docs/MCP.md",
        "scripts/test-uv-installed.py",
        "tests/test_uv_installation_harness.py",
    } <= MODULE.UV_INSTALLATION_SDIST_MEMBERS


def test_release_verifier_requires_license_and_release_documentation() -> None:
    source = Path(__file__).resolve().parents[1]
    assert (source / "LICENSE").is_file()
    assert (source / "docs" / "releases" / "0.5.0.md").is_file()
    contract = MODULE._project_metadata_contract()
    assert contract.license_expression == "GPL-3.0-or-later"
    assert contract.authors == ("mrjungle",)
    assert contract.maintainers == ("mrjungle",)


def test_release_verifier_rejects_wrong_license_expression_in_metadata() -> None:
    metadata = b"\n".join(
        (
            b"Metadata-Version: 2.4",
            b"Name: p2p-engine",
            b"Version: 0.5.0",
            b"Requires-Python: >=3.11",
            b"License-Expression: GPL-3.0-only",
            b"Author: mrjungle",
            b"Maintainer: mrjungle",
            b"License-File: LICENSE",
            b"",
        )
    )

    with pytest.raises(ValueError, match="License-Expression"):
        MODULE._verify_core_metadata(metadata, version="0.5.0", target="wheel")


def test_release_verifier_requires_convergence_gate_members() -> None:
    assert {
        "p2p_engine/core/release_contracts.py",
        "p2p_engine/services/release_convergence.py",
        "p2p_engine/resources/contracts/__init__.py",
        "p2p_engine/resources/contracts/wavekit-cli-fixtures-v1.json",
    } <= MODULE.RELEASE_CONVERGENCE_WHEEL_MEMBERS
    assert {
        "src/p2p_engine/core/release_contracts.py",
        "src/p2p_engine/services/release_convergence.py",
        "src/p2p_engine/resources/contracts/wavekit-cli-fixtures-v1.json",
        "scripts/verify-convergence-gate.py",
        "docs/development/project-structure-surface-convergence.md",
        "tests/test_release_convergence.py",
    } <= MODULE.RELEASE_CONVERGENCE_SDIST_MEMBERS


def test_release_verifier_requires_typed_vertical_transition_contract() -> None:
    assert {
        "p2p_engine/core/vertical_transition_impact.py",
        "p2p_engine/core/vertical_transition_plan.py",
        "p2p_engine/services/vertical_evidence_classifier.py",
        "p2p_engine/services/vertical_transition_analysis.py",
        "p2p_engine/services/vertical_transition_materialization.py",
    } <= MODULE.TYPED_VERTICAL_TRANSITION_WHEEL_MEMBERS
    assert {
        "docs/development/wavekit-vertical-transition-handoff.md",
        "tests/fixtures/vertical_transition/manifest-v1.json",
        "tests/test_vertical_transition_impact.py",
    } <= MODULE.TYPED_VERTICAL_TRANSITION_SDIST_MEMBERS


def test_release_verifier_requires_external_canonical_archive_tooling() -> None:
    source = Path(__file__).resolve().parents[1] / "scripts" / "verify-release-artifacts.py"
    text = source.read_text(encoding="utf-8")

    assert '"scripts/archive-project-state.py"' in text
    assert '"tests/test_archive_project_state_script.py"' in text


def test_release_verifier_rejects_discarded_runtime_surface_content() -> None:
    with pytest.raises(ValueError, match="proposal_decision_legacy"):
        MODULE._reject_discarded_surface(
            b"from p2p_engine.services.proposal_decision_legacy import Adapter\n",
            member="p2p_engine/example.py",
            target="wheel",
        )


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"/home/release-user/private/file\n", "POSIX home path"),
        (b"C:\\Users\\release-user\\private.txt\n", "Windows home path"),
        (b"\\\\server\\share\\private.txt\n", "UNC path"),
        (b"-----BEGIN PRIVATE KEY-----\n", "private key"),
        (b"p2p_sync_status\n", "removed product surface"),
    ],
)
def test_release_text_scan_rejects_private_or_removed_content(
    content: bytes,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        MODULE._scan_text_member(content, member="example.txt", target="sdist")


def test_release_text_scan_returns_only_used_narrow_exception() -> None:
    used = MODULE._scan_text_member(
        b"negative assertion: p2p_sync_status is absent\n",
        member="tests/negative.py",
        target="sdist",
        allowed_removed_tokens={"p2p_sync_status"},
    )

    assert used == {"p2p_sync_status"}


@pytest.mark.parametrize(
    "member",
    [
        "/home/release-user/project.py",
        "../outside.py",
        "package/../../outside.py",
        ".git/config",
        "package/__pycache__/module.pyc",
        "package/module.pyo",
    ],
)
def test_release_member_normalization_rejects_unsafe_paths(member: str) -> None:
    with pytest.raises(ValueError, match="unsafe|forbidden"):
        MODULE._normalized_members([member], archive_root=None)


def test_release_verifier_rejects_unused_or_missing_allowlist_entries() -> None:
    with pytest.raises(ValueError, match="allowlist member is absent"):
        MODULE._require_used_allowlist(
            {"present.py"},
            {"absent.py": {"historical-token"}},
            {},
            label="historical",
        )

    with pytest.raises(ValueError, match="unused historical allowlist"):
        MODULE._require_used_allowlist(
            {"present.py"},
            {"present.py": {"historical-token"}},
            {"present.py": set()},
            label="historical",
        )


def test_release_verifier_accepts_used_historical_exception() -> None:
    MODULE._require_used_allowlist(
        {"history.md"},
        {"history.md": {"legacy-name"}},
        {"history.md": {"legacy-name"}},
        label="historical",
    )


def test_release_verifier_rejects_mismatched_metadata_version() -> None:
    with pytest.raises(ValueError, match="wheel version 0.4.6 does not match 0.5.0"):
        MODULE._require_version("0.4.6", "0.5.0", target="wheel")


def test_release_verifier_rejects_extra_output_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "p2p_engine-0.5.0-py3-none-any.whl",
        "p2p_engine-0.5.0.tar.gz",
        "old-candidate.whl",
    ):
        (tmp_path / name).write_bytes(b"synthetic")
    monkeypatch.setattr(
        MODULE,
        "_parse_args",
        lambda: argparse.Namespace(dist=tmp_path, version="0.5.0"),
    )

    with pytest.raises(SystemExit, match="unexpected release artifacts: old-candidate.whl"):
        MODULE.main()


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


def test_release_verifier_requires_project_structure_contract_members() -> None:
    assert {
        "p2p_engine/cli_commands/project_structure.py",
        "p2p_engine/core/project_structure_export.py",
        "p2p_engine/core/project_structure.py",
        "p2p_engine/core/project_structure_replacement.py",
        "p2p_engine/core/project_structure_retirement.py",
        "p2p_engine/mcp/catalog/project.py",
        "p2p_engine/mcp/handlers/project.py",
        "p2p_engine/services/project_structure.py",
        "p2p_engine/services/project_structure_export.py",
        "p2p_engine/services/project_structure_replacement.py",
        "p2p_engine/services/project_structure_retirement.py",
    } <= MODULE.PROJECT_STRUCTURE_WHEEL_MEMBERS
    assert {
        "docs/CLI-CONTRACT.md",
        "docs/CLI-GUIDE.md",
        "docs/MCP.md",
        "docs/WORKSPACE-SCHEMA.md",
        "tests/test_project_structure.py",
        "tests/test_project_structure_export.py",
        "tests/test_project_structure_replacement.py",
        "tests/test_skeleton.py",
    } <= MODULE.PROJECT_STRUCTURE_SDIST_MEMBERS


def test_release_verifier_requires_project_memory_contract_members() -> None:
    assert {
        "p2p_engine/cli_commands/project_memory.py",
        "p2p_engine/core/project_memory.py",
        "p2p_engine/mcp/catalog/project.py",
        "p2p_engine/mcp/handlers/project.py",
        "p2p_engine/services/project_memory.py",
    } <= MODULE.PROJECT_MEMORY_WHEEL_MEMBERS
    assert {
        "docs/CLI-GUIDE.md",
        "docs/MCP.md",
        "tests/fixtures/project_memory/current-contract-v1.json",
        "tests/test_project_memory_classification.py",
        "tests/test_skeleton.py",
    } <= MODULE.PROJECT_MEMORY_SDIST_MEMBERS


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

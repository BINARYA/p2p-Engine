from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine import __version__
from p2p_engine.cli import app
from p2p_engine.cli_contract import CLI_CONTRACT_VERSION
from p2p_engine.core.release_contracts import current_contract_versions
from p2p_engine.core.vertical_registry import VERTICAL_REGISTRY_PROTOCOL_VERSION
from p2p_engine.mcp.registry import tool_definitions
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.public_surface_inventory import public_surface_snapshot
from p2p_engine.services.release_convergence import (
    CONVERGENCE_GATE_CONTRACT,
    RELEASE_LINE,
    WAVEKIT_CLI_FIXTURE_BUNDLE_CONTRACT,
    convergence_gate_payload,
    fixture_commands,
    issue_codes,
    load_packaged_wavekit_cli_fixture_bundle,
    obsolete_reference_allowlist,
    validate_convergence_inventory,
    validate_wavekit_cli_fixture_bundle,
    wavekit_cli_fixture_bundle,
)
from p2p_engine.storage.filesystem import P2PWorkspace

ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def _envelope(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    assert isinstance(payload, dict)
    assert payload["contract_version"] == CLI_CONTRACT_VERSION
    assert payload["ok"] is True
    return payload


@pytest.mark.cli
@pytest.mark.mcp
def test_version_status_and_mcp_schema_status_share_contract_tuple(
    tmp_path: Path,
) -> None:
    P2PWorkspace(tmp_path).init_project(
        "Convergence tuple",
        owner="owner",
        starter_id="generic",
    )
    expected = current_contract_versions()

    version = _envelope(RUNNER.invoke(app, ["version", "--format", "json"]).stdout)
    status = _envelope(
        RUNNER.invoke(
            app,
            ["status", "--format", "json", "--root", str(tmp_path)],
        ).stdout
    )
    mcp_status = call_tool("p2p_workspace_schema_status", {"root": str(tmp_path)})

    assert version["operation"] == "version"
    assert version["data"] == expected
    assert status["operation"] == "status"
    assert status["data"]["contract_versions"] == expected
    assert status["data"]["workspace_status"]["workspace_schema"]["current_version"] == 4
    assert mcp_status["contract_versions"] == expected
    assert mcp_status["mutation_performed"] is False


@pytest.mark.unit
def test_convergence_inventory_maps_surfaces_capabilities_and_deferrals() -> None:
    payload = convergence_gate_payload()
    operations = {
        str(item["operation"]): item
        for item in payload["operation_inventory"]
    }
    snapshot = public_surface_snapshot()

    assert payload["contract_version"] == CONVERGENCE_GATE_CONTRACT
    assert payload["release_line"] == RELEASE_LINE == __version__ == "0.6.0"
    assert issue_codes(validate_convergence_inventory()) == ()
    assert payload["issues"] == []
    assert payload["public_surface"]["semantic_sha256"] == snapshot.semantic_sha256
    resources = set(payload["packaged_resource_inventory"]["packaged_resources"])
    assert "p2p_engine/resources/verticals/board_game_design" in resources
    assert "p2p_engine/resources/verticals/grant_document_design" in resources
    assert (
        "p2p_engine/resources/contracts/wavekit-cli-fixtures-v1.json"
        in resources
    )
    assert operations["project.vertical.export"]["capability"] == "project.vertical.export"
    assert operations["project.vertical.export"]["mcp_parity"] == (
        "cli_apply_mcp_read_only_deferral"
    )
    assert operations["project.structure.replace"]["capability"] == (
        "project.structure.replace"
    )
    assert operations["project.structure.replace"]["mcp_parity"] == (
        "cli_apply_mcp_read_only_deferral"
    )
    assert operations["project.structure.merge_restore"]["deferred"] is True
    assert operations["project.structure.merge_restore"]["mcp_parity"] == (
        "deferred_after_0.5.0"
    )
    assert operations["proposal.create"]["capability"] == "proposal.create"
    assert operations["proposal.update"]["capability"] == "proposal.update"
    assert operations["proposal.contribution.add"]["capability"] == (
        "proposal.contribution.add"
    )
    assert operations["project.vertical.install"]["capability"] == (
        "project.vertical.install"
    )
    assert operations["project.vertical.adopt"]["capability"] == (
        "project.vertical.adopt"
    )
    assert operations["project.vertical.migrate"]["capability"] == (
        "project.vertical.migrate"
    )
    for operation, trace in operations.items():
        if trace["deferred"]:
            continue
        assert trace["fixture_group"], operation
        assert trace["tests"], operation
        assert "WaveKit role" not in trace["hosted_boundary"]


@pytest.mark.smoke
def test_packaged_wavekit_cli_fixture_bundle_is_sanitized_and_current() -> None:
    expected = wavekit_cli_fixture_bundle()
    packaged = load_packaged_wavekit_cli_fixture_bundle()
    commands = set(fixture_commands(packaged))
    command_text = "\n".join(sorted(commands))
    serialized = json.dumps(packaged, sort_keys=True)

    assert packaged == expected
    assert packaged["contract_version"] == WAVEKIT_CLI_FIXTURE_BUNDLE_CONTRACT
    assert packaged["engine_version"] == __version__
    assert validate_wavekit_cli_fixture_bundle(packaged) == ()
    assert "p2p version --format json" in commands
    assert "p2p status --format json" in commands
    assert "p2p project vertical export eligibility --format json" in commands
    assert "p2p project structure replace apply COORDINATE" in serialized
    assert "p2p vertical domain list --registry REGISTRY --format json" in commands
    assert (
        "p2p vertical search software --registry REGISTRY --domain DOMAIN-ID --format json"
        in commands
    )
    assert packaged["registry_v2"] == {
        "protocol_version": VERTICAL_REGISTRY_PROTOCOL_VERSION,
        "protocol_v1_behavior": "deterministic_rejection",
        "domain_filtering": "exact_external_id_only",
        "mutation_performed": False,
    }
    assert packaged["authority"]["wavekit_membership_role_required"] is False
    assert packaged["authority"]["mutable_owner_identity_is_project_authority"] is False
    for forbidden in ("/home/", "/Users/", "/tmp/", "davide", "matteo"):
        assert forbidden not in serialized
    for forbidden in ("secret", "password", "token:"):
        assert forbidden not in command_text


@pytest.mark.mcp
def test_mcp_catalog_has_read_only_deferrals_for_export_and_replacement() -> None:
    names = {definition["name"] for definition in tool_definitions()}

    assert "p2p_project_structure_export_eligibility" in names
    assert "p2p_project_structure_export_preview" in names
    assert "p2p_project_structure_export_apply" not in names
    assert "p2p_project_structure_replacement_inspect" in names
    assert "p2p_project_structure_replacement_preview" in names
    assert "p2p_project_structure_replacement_apply" not in names


@pytest.mark.unit
def test_docs_release_notes_and_allowlist_record_clean_break() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    convergence_doc = (
        ROOT / "docs" / "development" / "project-structure-surface-convergence.md"
    ).read_text(encoding="utf-8")
    allowed = {item["path"]: item["reason"] for item in obsolete_reference_allowlist()}

    assert "## 0.5.1 - 2026-08-28" in changelog
    assert "workspace schema 4" in changelog
    assert "portable vertical schema 3" in changelog
    normalized_changelog = " ".join(changelog.split())
    assert (
        "does not provide in-runtime migration, conversion or compatibility aliases"
        in normalized_changelog
    )
    assert "project.vertical.export" in convergence_doc
    assert "project.structure.replace" in convergence_doc
    assert "project.structure.merge_restore" in convergence_doc
    assert "p2p-vertical-registry/v2" in convergence_doc
    assert "protocol-v1" in convergence_doc
    assert "WaveKit-facing CLI fixture bundle" in convergence_doc
    assert "P2P Engine `0.5.1`" in convergence_doc
    assert allowed["CHANGELOG.md"]
    assert set(allowed) == {
        "CHANGELOG.md",
        "tests/fixtures/vertical_transition/legacy-0.4.7-characterization.json",
    }


@pytest.mark.unit
def test_release_workflow_runs_installed_wheel_smoke_after_artifact_verification() -> None:
    candidate = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "release-candidate.yml").read_text(
            encoding="utf-8"
        )
    )
    release = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    )
    source_matrix = candidate["jobs"]["source-matrix"]
    artifact = candidate["jobs"]["artifact"]
    commands = "\n".join(str(step.get("run", "")) for step in artifact["steps"])

    assert source_matrix["strategy"]["matrix"]["python-version"] == ["3.12"]
    assert artifact["needs"] == "source-matrix"
    assert "build-release-candidate.sh" in commands
    assert "twine check" in commands
    assert "test-installed.sh --wheel" in commands
    assert commands.index("build-release-candidate.sh") < commands.index("twine check")
    assert commands.index("twine check") < commands.index("test-installed.sh --wheel")
    assert release["jobs"]["candidate"]["uses"] == (
        "./.github/workflows/release-candidate.yml"
    )
    assert all("dist/" not in str(step.get("run", "")) for step in source_matrix["steps"])


@pytest.mark.unit
def test_registry_v1_references_are_non_runtime_and_current_client_is_v2_only() -> None:
    catalog_source = (
        ROOT / "src" / "p2p_engine" / "services" / "vertical_catalog.py"
    ).read_text(encoding="utf-8")
    fixture = load_packaged_wavekit_cli_fixture_bundle()

    assert VERTICAL_REGISTRY_PROTOCOL_VERSION == "p2p-vertical-registry/v2"
    assert "p2p-vertical-registry/v1" not in catalog_source
    assert fixture["registry_v2"]["protocol_version"] == VERTICAL_REGISTRY_PROTOCOL_VERSION
    assert fixture["registry_v2"]["protocol_v1_behavior"] == "deterministic_rejection"

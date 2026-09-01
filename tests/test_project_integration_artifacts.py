from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.project_integration import PROJECT_INTEGRATION_CONTRACT
from p2p_engine.mcp.registry import TOOL_NAMES
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.project_application import ProjectApplicationService
from p2p_engine.services.project_integration import ProjectIntegrationService
from tests.cli_assertions import cli_data

runner = CliRunner()


def _workspace(root: Path, *, agent: str = "generic") -> ProjectApplicationService:
    workspace = ProjectApplicationService(root)
    workspace.init_project("Integration Artifacts", agent_profile=agent, owner="owner")
    return workspace


def _manifest(root: Path) -> dict[str, object]:
    value = yaml.safe_load(
        (root / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_clean_init_versions_every_artifact_and_keeps_backend_invisible(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, agent="codex")

    status = workspace.project_integration_status()
    manifest = _manifest(tmp_path)
    integration = manifest["integration"]
    assert isinstance(integration, dict)

    assert status["state"] == "current"
    assert status["active_profile"] == "standalone"
    assert status["backend_exposed"] is False
    assert integration["contract_version"] == PROJECT_INTEGRATION_CONTRACT
    assert set(integration["versions"]) == {
        "runtime",
        "local_memory",
        "domain",
        "bundle",
        "sync",
        "integration",
    }
    assert integration["versions"]["sync"]["status"] == "unavailable"
    assert integration["mcp_host_configuration"]["mutation_via_mcp"] is False
    paths = {item["path"] for item in integration["artifacts"]}
    assert {
        "AGENTS.md",
        "P2P-INTEGRATION.md",
        "P2P-SETUP.md",
        ".p2p/agent-policy.yml",
        ".agents/skills/p2p-project/SKILL.md",
    } <= paths
    rendered = "\n".join(
        (tmp_path / path).read_text(encoding="utf-8")
        for path in paths
        if not path.startswith(".p2p/")
    )
    assert "Integration contract: p2p-project-integration/v1" in rendered
    assert "Access profile: standalone" in rendered
    assert "storage_adapter" not in rendered
    assert "sqlite-project-state" not in rendered


def test_install_adopts_verified_preintegration_artifacts(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    manifest_path = tmp_path / ".p2p" / "agent-integrations.yml"
    policy_path = tmp_path / ".p2p" / "agent-policy.yml"
    guide_path = tmp_path / "P2P-INTEGRATION.md"
    setup_path = tmp_path / "P2P-SETUP.md"
    manifest = _manifest(tmp_path)
    manifest.pop("integration")
    guide_path.unlink()
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    assert isinstance(policy, dict)
    policy.pop("project_integration")
    policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    policy_digest = hashlib.sha256(policy_path.read_bytes()).hexdigest()
    adapters = manifest["adapters"]
    assert isinstance(adapters, dict)
    for adapter in adapters.values():
        assert isinstance(adapter, dict)
        files = adapter["files"]
        assert isinstance(files, list)
        adapter["files"] = [
            item for item in files if item["path"] != "P2P-INTEGRATION.md"
        ]
        for item in adapter["files"]:
            if item["path"] == ".p2p/agent-policy.yml":
                item["sha256"] = policy_digest
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    setup_path.write_text(
        "<!-- P2P: generated-runtime-setup schema=1 "
        "source=.p2p/project/runtime.yml -->\n\n# P2P Setup\n",
        encoding="utf-8",
    )

    installed = workspace.install_project_integration(
        profile="standalone",
        agent_target="generic",
    )

    assert installed.status == "applied"
    assert workspace.project_integration_status()["state"] == "current"
    assert guide_path.is_file()
    assert "integration=p2p-project-integration/v1" in setup_path.read_text(
        encoding="utf-8"
    ).splitlines()[0]


def test_profile_matrix_rejects_future_profiles_without_writes(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    with pytest.raises(ValueError, match="P2P_INTEGRATION_PROFILE_UNSUPPORTED"):
        workspace.transition_project_integration(profile="linked-local")
    with pytest.raises(ValueError, match="P2P_INTEGRATION_PROFILE_UNSUPPORTED"):
        workspace.transition_project_integration(profile="remote-only")

    after = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before
    profiles = {item["profile"]: item for item in workspace.project_integration_status()["profiles"]}
    assert profiles["standalone"]["supported"] is True
    assert profiles["linked-local"]["supported"] is False
    assert profiles["remote-only"]["supported"] is False


def test_managed_section_round_trip_preserves_user_bytes_exactly(tmp_path: Path) -> None:
    original = b"# Local agent rules\r\nKeep this byte-for-byte.\r\n"
    (tmp_path / "AGENTS.md").write_bytes(original)
    workspace = _workspace(tmp_path)

    installed = workspace.install_project_integration(profile="standalone")
    with_section = (tmp_path / "AGENTS.md").read_bytes()

    assert installed.status == "applied"
    assert with_section.startswith(original)
    assert with_section.count(b"P2P:BEGIN managed-section") == 1
    assert workspace.refresh_project_integration().status == "no-change"

    removed = workspace.remove_project_integration()

    assert removed.status == "applied"
    assert (tmp_path / "AGENTS.md").read_bytes() == original
    assert not (tmp_path / "P2P-INTEGRATION.md").exists()
    assert workspace.canonical_memory_snapshot().semantic_state_digest


def test_marker_corruption_and_managed_section_edit_fail_closed(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# User rules\n", encoding="utf-8")
    workspace = _workspace(tmp_path)
    workspace.install_project_integration(profile="standalone")
    agents = tmp_path / "AGENTS.md"
    agents.write_bytes(
        agents.read_bytes()
        + b"<!-- P2P:BEGIN managed-section id=p2p-project-access -->\n"
    )

    status = workspace.project_integration_status()
    blocked = workspace.refresh_project_integration()

    assert status["state"] == "conflicting"
    assert blocked.status == "blocked"
    assert blocked.artifacts[0].state == "conflicting"


def test_edit_inside_valid_managed_section_is_preserved_and_blocks_refresh(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# User rules\n", encoding="utf-8")
    workspace = _workspace(tmp_path)
    workspace.install_project_integration(profile="standalone")
    agents = tmp_path / "AGENTS.md"
    edited = agents.read_bytes().replace(
        b"Offline reads and governed local mutations are supported.",
        b"Locally edited managed instruction.",
    )
    agents.write_bytes(edited)

    status = workspace.project_integration_status()
    result = workspace.refresh_project_integration()

    assert status["state"] == "conflicting"
    assert result.status == "blocked"
    assert result.artifacts[0].state == "user-modified"
    assert agents.read_bytes() == edited


def test_deleted_artifact_is_reported_and_reconstructed(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    guide = tmp_path / "P2P-INTEGRATION.md"
    guide.unlink()

    assert workspace.project_integration_status()["state"] == "missing"

    refreshed = workspace.refresh_project_integration()

    assert refreshed.status == "applied"
    assert guide.exists()
    assert workspace.project_integration_status()["state"] == "current"


def test_newer_contract_is_preserved_and_not_overwritten(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    manifest_path = tmp_path / ".p2p" / "agent-integrations.yml"
    manifest = _manifest(tmp_path)
    manifest["integration"]["contract_version"] = "p2p-project-integration/v99"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    before = manifest_path.read_bytes()

    assert workspace.project_integration_status()["state"] == "unsupported"
    with pytest.raises(ValueError, match="P2P_INTEGRATION_CONTRACT_UNSUPPORTED"):
        workspace.refresh_project_integration()
    assert manifest_path.read_bytes() == before


def test_partial_transition_failure_rolls_back_all_artifacts(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    compatibility = workspace.adapter.compatibility_target()
    manifest_path = tmp_path / ".p2p" / "agent-integrations.yml"
    manifest = _manifest(tmp_path)
    manifest["integration"]["versions"]["runtime"]["version"] = "0.0.0"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    before = manifest_path.read_bytes()

    def fail_after_replace(stage: str, _target: str) -> None:
        if stage == "after_replace":
            raise RuntimeError("simulated interruption")

    service = ProjectIntegrationService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        agent_instructions=compatibility._agent_instruction_service(),
        runtime_contract=compatibility._runtime_contract_service(),
        failure_injector=fail_after_replace,
    )

    result = service.refresh()

    assert result.status == "rolled_back"
    assert manifest_path.read_bytes() == before


def test_partial_transition_conflict_leaves_recoverable_external_target_journal(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    compatibility = workspace.adapter.compatibility_target()
    manifest_path = tmp_path / ".p2p" / "agent-integrations.yml"
    manifest = _manifest(tmp_path)
    manifest["integration"]["versions"]["runtime"]["version"] = "0.0.0"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    guide_path = tmp_path / "P2P-INTEGRATION.md"
    guide_path.unlink()
    original = manifest_path.read_bytes()

    def conflict_after_replace(stage: str, target: str) -> None:
        if stage == "after_replace" and target == "P2P-INTEGRATION.md":
            path = tmp_path / target
            path.write_bytes(path.read_bytes() + b"\nexternal edit\n")
            raise RuntimeError("simulated interrupted transition with concurrent edit")

    service = ProjectIntegrationService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        agent_instructions=compatibility._agent_instruction_service(),
        runtime_contract=compatibility._runtime_contract_service(),
        failure_injector=conflict_after_replace,
    )

    result = service.refresh()
    recovery = workspace.workspace_transaction_recovery_status()

    assert result.status == "recovery_required"
    assert result.recovery_required is True
    assert recovery.required is True
    assert recovery.available_actions == ("rollback", "resume")
    transaction_dir = (
        tmp_path
        / ".p2p"
        / ".internal"
        / "workspace-transactions"
        / "transactions"
        / recovery.transaction_id
    )
    target = "P2P-INTEGRATION.md"
    guide_path.write_bytes((transaction_dir / "candidates" / target).read_bytes())

    rolled_back = workspace.rollback_workspace_transaction(
        transaction_id=recovery.transaction_id,
        actor="owner",
        confirm=True,
    )

    assert rolled_back.status == "rolled_back"
    assert manifest_path.read_bytes() == original
    assert not guide_path.exists()
    assert workspace.workspace_transaction_recovery_status().required is False


def test_integration_lifecycle_does_not_mutate_canonical_state(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, agent="all")
    identity = workspace.project_identity().to_dict()
    revision = workspace.project_state_revision().to_dict()
    snapshot = workspace.canonical_memory_snapshot()
    authority = workspace.project_authority().to_dict()

    removed = workspace.remove_project_integration()
    installed = workspace.install_project_integration(
        profile="standalone",
        agent_target="all",
    )
    after = workspace.canonical_memory_snapshot()

    assert removed.status == "applied"
    assert installed.status == "applied"
    assert workspace.project_identity().to_dict() == identity
    assert workspace.project_state_revision().to_dict() == revision
    assert after.semantic_state_digest == snapshot.semantic_state_digest
    assert after.source_revision == snapshot.source_revision
    assert workspace.project_authority().to_dict() == authority


def test_secret_shaped_rendered_content_is_rejected(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    compatibility = workspace.adapter.compatibility_target()
    service = compatibility._project_integration_service()
    original_renderer = service.agent_instructions.instruction_files
    service.agent_instructions.instruction_files = lambda *args: {
        **original_renderer(*args),
        Path("SECRET.md"): "api_key=do-not-render\n",
    }

    with pytest.raises(ValueError, match="P2P_INTEGRATION_SECRET_REJECTED"):
        service.refresh()
    assert not (tmp_path / "SECRET.md").exists()


def test_cli_contract_and_mcp_status_are_read_only(tmp_path: Path) -> None:
    _workspace(tmp_path)

    cli_result = runner.invoke(
        app,
        ["integration", "status", "--root", str(tmp_path), "--format", "json"],
    )
    mcp_result = call_tool("p2p_integration_status", {"root": str(tmp_path)})

    assert cli_result.exit_code == 0
    assert cli_data(cli_result)["state"] == "current"
    assert mcp_result["project_integration"]["state"] == "current"
    assert mcp_result["mutation_performed"] is False
    assert "p2p_integration_status" in TOOL_NAMES
    assert not {
        "p2p_agent_instructions_refresh",
        "p2p_agent_install",
        "p2p_agent_update",
        "p2p_agent_uninstall",
    } & set(TOOL_NAMES)


def test_rendering_is_deterministic_and_contains_no_secret_values(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    _workspace(first_root, agent="all")
    _workspace(second_root, agent="all")

    first_manifest = _manifest(first_root)
    second_manifest = _manifest(second_root)
    first_paths = [item["path"] for item in first_manifest["integration"]["artifacts"]]
    second_paths = [item["path"] for item in second_manifest["integration"]["artifacts"]]

    assert first_paths == second_paths
    for path in first_paths:
        first = (first_root / path).read_bytes()
        second = (second_root / path).read_bytes()
        assert hashlib.sha256(first).digest() == hashlib.sha256(second).digest()
        lowered = first.lower()
        assert b"authorization: bearer " not in lowered
        assert b"api_key=" not in lowered
        assert b"access_token=" not in lowered
        assert b"private_key=" not in lowered

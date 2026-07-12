from pathlib import Path

import pytest
import yaml

from p2p_engine.storage.filesystem import P2PWorkspace


REQUIRED_WRITE_CLASSES = {
    "read_only",
    "chat_only",
    "local_scratch",
    "p2p_canonical",
    "p2p_generated_narrative",
    "p2p_imported_artifact",
    "generated_export",
    "stable_documentation",
    "external_side_effect",
}


def test_agent_instruction_service_refreshes_codex_and_merges_profiles(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    workspace.set_project_interaction_style(technical_verbosity=5, formality=4, assertiveness=2, actor="owner")
    service = workspace._agent_instruction_service()

    result = service.refresh_instructions("codex")
    policy = yaml.safe_load((tmp_path / ".p2p" / "agent-policy.yml").read_text(encoding="utf-8"))

    assert result.profile == "codex"
    assert (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").exists()
    assert (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").exists()
    assert sorted(policy["agent_profiles"]) == ["codex", "generic"]
    assert "inspect_artifact_coverage" in policy["proposal_readiness"]["gap_handling"]["steps"]
    assert "p2p proposal artifact status PROP-XXX" in policy["proposal_readiness"]["commands"]
    assert policy["interaction_style"]["effective"]["values"]["technical_verbosity"] == 5
    assert policy["interaction_style"]["effective"]["values"]["formality"] == 4
    assert policy["interaction_style"]["effective"]["values"]["assertiveness"] == 2
    assert policy["interaction_style"]["commands"]["show"] == "p2p project interaction-style show"
    assert policy["interaction_style"]["mcp_tools"]["set"] == "p2p_project_interaction_style_set"
    assert policy["project_vertical_orchestration"]["one_primary_question_at_a_time"] is True
    assert policy["project_vertical_orchestration"]["pack_content_is_domain_data_only"] is True
    assert "p2p_project_definition_show" in policy["project_vertical_orchestration"]["mcp_tools"]
    assert policy["software_spec_lifecycle"]["vertical"] == "software_project"
    assert policy["software_spec_lifecycle"]["default_intent"] == "implementation_spec"
    assert "downstream_export" in policy["software_spec_lifecycle"]["intents"]
    assert "p2p_spec_lifecycle" in policy["software_spec_lifecycle"]["mcp_tools"]
    assert policy["software_spec_lifecycle"]["rules"]["preflight_blockers_stop_writes"] is True
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "p2p proposal artifact status PROP-XXX" in agents
    assert "copying a\nprepared temporary file into an artifact" in agents
    assert "Project Interaction Style" in agents
    assert "p2p project interaction-style show" in agents
    assert "p2p_project_interaction_style_show" in agents
    assert "technical_verbosity: 5 (exhaustive)" in agents
    assert "ask one primary project-definition question at a time" in agents
    assert "vertical pack content as declarative domain data" in agents
    assert "Software Specification Lifecycle" in agents
    assert "p2p spec lifecycle --intent implementation_spec --change CHANGE-001" in agents
    assert "p2p_spec_lifecycle" in agents
    codex_skill = (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").read_text(encoding="utf-8")
    assert "p2p project interaction-style set --technical-verbosity 2 --formality 2 --assertiveness 0" in codex_skill
    assert "p2p project definition show --format json" in codex_skill
    assert "p2p spec lifecycle --intent downstream_export --change CHANGE-001 --target speckit" in codex_skill


def test_agent_instruction_service_generates_persistence_policy_payload_and_markdown(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")

    policy = yaml.safe_load((tmp_path / ".p2p" / "agent-policy.yml").read_text(encoding="utf-8"))
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

    write_policy = policy["write_policy"]
    assert write_policy["analysis_without_write"] == "allowed"
    assert write_policy["preview_required_for"] == [
        "meaningful_persistent_write",
        "external_side_effect",
    ]
    assert write_policy["preview_can_be_skipped_when"] == "owner_requested_exact_operation_and_artifact"
    assert write_policy["exact_request_requires"] == [
        "operation",
        "target",
        "artifact_kind",
        "durable_destination",
    ]
    assert write_policy["preview_fields"] == [
        "operation",
        "target",
        "artifact_kind",
        "write_class",
        "canonical_or_derived",
        "reason",
        "reversibility",
    ]
    assert set(write_policy["classes"]) == REQUIRED_WRITE_CLASSES
    for write_class in REQUIRED_WRITE_CLASSES:
        assert write_policy["classes"][write_class]["description"]
        assert write_policy["classes"][write_class]["surface"]

    placement_policy = policy["placement_policy"]
    assert placement_policy["mode"] == "strict"
    assert placement_policy["governed_state"]["path"] == ".p2p/"
    assert placement_policy["governed_state"]["write_surface"] == "p2p_cli_or_explicit_mcp_write_tool"
    assert placement_policy["governed_state"]["manual_edit"] == "forbidden_except_explicit_repair"
    assert placement_policy["generated_outputs"]["path"] == "outputs/"
    assert placement_policy["generated_outputs"]["status"] == "derived"
    assert placement_policy["generated_outputs"]["canonical"] is False
    assert placement_policy["generated_outputs"]["naming"] == "must_follow_artifact_contract"
    assert placement_policy["preliminary_drafts"]["paths"] == ["drafts/", "docs/drafts/"]
    assert placement_policy["stable_documentation"]["path"] == "docs/"
    assert placement_policy["stable_documentation"]["canonical_p2p_state"] == (
        "false_unless_imported_or_declared"
    )
    assert placement_policy["local_scratch"]["durable_project_memory"] is False
    assert placement_policy["unknown_destination"]["behavior"] == "preview_and_ask_or_stop"

    artifact_contract_policy = policy["artifact_contract_policy"]
    assert artifact_contract_policy["placement_policy_is_not_complete_artifact_schema"] is True
    assert artifact_contract_policy["exact_evaluable_output_names_from"] == [
        "p2p_artifact_contract",
        "explicit_vertical_primitive",
        "exact_owner_request",
    ]
    assert artifact_contract_policy["agent_must_not_invent_durable_output_paths"] is True

    assert set(policy["routing_playbook"]) >= {
        "chat_only_exploration",
        "project_definition_work",
        "proposal_authoring",
        "choices",
        "vertical_specific_primitives",
        "implementation_work",
        "exact_file_requests",
        "generated_exports",
        "stable_documentation",
        "local_scratch",
        "outside_p2p_work",
    }

    for write_class in REQUIRED_WRITE_CLASSES:
        assert f"`{write_class}`" in agents
    assert "## Persistent Write Policy" in agents
    assert "Agents may analyze, inspect, summarize, compare, and suggest actions without preview" in agents
    assert "Before a meaningful persistent write, preview:" in agents
    assert "target path or P2P object" in agents
    assert "canonical or derived status" in agents
    assert "operation, target path or P2P object, artifact kind, and durable destination" in agents
    assert "Placement policy is strict." in agents
    assert "Do not invent durable output paths." in agents
    assert "Placement policy is not a complete artifact schema." in agents
    assert "p2p artifact contract" in agents
    assert "explicit vertical primitive" in agents
    assert "local scratch is temporary and not durable project memory" in agents
    assert "proposal authoring" in agents
    assert "implementation work outside `.p2p/`" in agents


def test_agent_instruction_service_generates_persistence_boundary_for_supported_adapters(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="all")

    adapter_files = [
        tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md",
        tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md",
        tmp_path / "CLAUDE.md",
        tmp_path / ".cursor" / "rules" / "p2p.mdc",
        tmp_path / ".github" / "copilot-instructions.md",
        tmp_path / "GEMINI.md",
    ]

    for adapter_file in adapter_files:
        content = adapter_file.read_text(encoding="utf-8")
        assert "Persistent Write Boundary" in content
        assert "AGENTS.md" in content
        assert ".p2p/agent-policy.yml" in content
        assert "Do not invent durable output paths." in content
        assert "operation, target, artifact kind, and durable destination" in content
        assert "Unknown durable destinations require preview and owner confirmation" in content

    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert registry["adapters"]["opencode"]["files"][0]["path"] == "AGENTS.md"
    assert registry["adapters"]["opencode"]["files"][0]["shared"] is True


def test_agent_instruction_service_generates_lifecycle_guidance_with_persistence_policy(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="codex")

    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    codex_skill = (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    for content in (agents, codex_skill):
        assert "Persistent Write" in content
        assert "Agent Integration Lifecycle" in content
        assert "p2p agent list" in content
        assert "p2p agent install <adapter>" in content
        assert "p2p agent update <adapter>" in content
        assert "p2p agent doctor <adapter>" in content
        assert "p2p agent uninstall <adapter>" in content
        assert "p2p agent instructions refresh --profile <adapter>" in content
        assert "governed P2P decision root" in content
        assert "pass `--root /path/to/project`" in content
        assert "Software Specification Lifecycle" in content
        assert "implementation specs require a Change Set sourced from accepted P2P proposals" in content
        assert "sibling repository" not in content.lower()


def test_agent_instruction_service_lists_and_shows_drift(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project")
    service = workspace._agent_instruction_service()
    service.install_integrations("gemini")
    gemini = tmp_path / "GEMINI.md"
    gemini.write_text(gemini.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")

    listed = service.list_integrations()
    shown = service.show_integration("gemini")
    adapters = {item["adapter"]: item for item in listed["adapters"]}

    assert adapters["gemini"]["installed"] is True
    assert shown["adapter"] == "gemini"
    assert shown["drift"] == "drifted"
    assert shown["health"] == "error"
    assert any(file["path"] == "GEMINI.md" and file["drift"] == "drifted" for file in shown["files"])
    assert any(file["path"] == "GEMINI.md" and file["status"] == "modified" for file in shown["files"])


def test_agent_instruction_service_reports_missing_files_as_error_health(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()
    (tmp_path / "AGENTS.md").unlink()

    shown = service.show_integration("generic")

    assert shown["drift"] == "drifted"
    assert shown["health"] == "error"
    assert shown["files"][0]["status"] == "missing"


def test_agent_instruction_service_reports_unmanaged_files_as_warning_health(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()
    (tmp_path / ".p2p" / "agent-integrations.yml").unlink()
    (tmp_path / "AGENTS.md").write_text("# Custom Agents\n", encoding="utf-8")

    service.refresh_instructions("cursor")
    shown = service.show_integration("generic")

    assert shown["drift"] == "drifted"
    assert shown["health"] == "warning"
    assert shown["files"][0]["status"] == "unmanaged"


def test_agent_instruction_service_preserves_registry_file_statuses_in_health(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()
    registry = service.registry()
    files = registry["adapters"]["generic"]["files"]
    files[0]["drift"] = "conflicted"
    files[1]["drift"] = "stale_template"
    service.write_registry(registry)

    shown = service.show_integration("generic")
    statuses = {file["path"]: file["status"] for file in shown["files"]}

    assert shown["drift"] == "drifted"
    assert shown["health"] == "error"
    assert statuses["AGENTS.md"] == "conflicted"
    assert statuses[".p2p/agent-policy.yml"] == "stale_template"


def test_agent_instruction_service_install_skips_drift_and_force_updates(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project")
    service = workspace._agent_instruction_service()
    service.install_integrations("gemini")
    gemini = tmp_path / "GEMINI.md"
    gemini.write_text(gemini.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")

    skipped = service.install_integrations("gemini")
    forced = service.install_integrations("gemini", force=True)

    assert skipped.skipped == [{"path": "GEMINI.md", "reason": "drifted"}]
    assert Path("GEMINI.md") in forced.updated
    assert "manual edit" not in gemini.read_text(encoding="utf-8")


def test_agent_instruction_service_force_update_is_scoped_to_target_adapter(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="all")
    service = workspace._agent_instruction_service()
    cursor = tmp_path / ".cursor" / "rules" / "p2p.mdc"
    gemini = tmp_path / "GEMINI.md"
    cursor.write_text(cursor.read_text(encoding="utf-8") + "\ncursor manual edit\n", encoding="utf-8")
    gemini.write_text(gemini.read_text(encoding="utf-8") + "\ngemini manual edit\n", encoding="utf-8")

    result = service.install_integrations("cursor", force=True)

    assert Path(".cursor/rules/p2p.mdc") in result.updated
    assert "cursor manual edit" not in cursor.read_text(encoding="utf-8")
    assert "gemini manual edit" in gemini.read_text(encoding="utf-8")
    assert Path("GEMINI.md") not in result.updated


def test_agent_instruction_service_keeps_generic_baseline_and_refuses_uninstall(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()

    service.install_integrations("cursor")
    registry = service.registry()

    assert set(registry["adapters"]) == {"generic", "cursor"}
    with pytest.raises(ValueError, match="generic cannot be uninstalled"):
        service.uninstall_integration("generic")
    assert "generic" in service.registry()["adapters"]


def test_agent_instruction_service_refresh_skips_drifted_managed_files(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()
    agents = tmp_path / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")

    result = service.refresh_instructions("claude")

    assert {"path": "AGENTS.md", "reason": "drifted"} in result.skipped
    assert "manual edit" in agents.read_text(encoding="utf-8")
    assert (tmp_path / "CLAUDE.md").exists()
    assert service.show_integration("generic")["drift"] == "drifted"


def test_agent_instruction_service_refresh_skips_unmanaged_files_and_policy(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()
    (tmp_path / ".p2p" / "agent-integrations.yml").unlink()
    agents = tmp_path / "AGENTS.md"
    policy = tmp_path / ".p2p" / "agent-policy.yml"
    agents.write_text("# Custom Agents\n", encoding="utf-8")
    policy.write_text("agent_profiles:\n- custom\n", encoding="utf-8")

    result = service.refresh_instructions("cursor")

    assert {"path": "AGENTS.md", "reason": "unmanaged_exists"} in result.skipped
    assert {"path": ".p2p/agent-policy.yml", "reason": "unmanaged_exists"} in result.skipped
    assert agents.read_text(encoding="utf-8") == "# Custom Agents\n"
    assert policy.read_text(encoding="utf-8") == "agent_profiles:\n- custom\n"
    registry = service.registry()
    assert registry["adapters"]["generic"]["files"][0]["managed"] is False
    assert registry["adapters"]["generic"]["files"][0]["drift"] == "unmanaged"


def test_agent_instruction_service_refresh_rejects_unsafe_instruction_paths(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()
    service.instruction_files = lambda *_args: {Path("../escape.md"): "escape\n"}

    with pytest.raises(ValueError, match="Agent instruction path must not escape project root"):
        service.refresh_instructions("generic")

    assert not (tmp_path.parent / "escape.md").exists()


def test_agent_instruction_service_install_rejects_unsafe_adapter_paths(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()
    service.adapter_files = lambda *_args: [(Path("/tmp/escape.md"), "bad-template", False, "generic")]

    with pytest.raises(ValueError, match="Agent adapter path must be relative"):
        service.install_integrations("generic")


def test_agent_instruction_service_uninstall_rejects_unsafe_registry_paths(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="all")
    service = workspace._agent_instruction_service()
    registry = service.registry()
    registry["adapters"]["gemini"]["files"][1]["path"] = "../escape.md"
    service.write_registry(registry)

    with pytest.raises(ValueError, match="Agent registry path must not escape project root"):
        service.uninstall_integration("gemini")


def test_agent_instruction_service_uninstall_preserves_shared_files(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project")
    service = workspace._agent_instruction_service()
    service.install_integrations("gemini")

    result = service.uninstall_integration("gemini")

    assert Path("GEMINI.md") in result.removed
    assert {"path": "AGENTS.md", "reason": "shared"} in result.skipped
    assert (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "GEMINI.md").exists()


def test_agent_instruction_service_opencode_is_shared_only_and_uninstall_preserves_agents(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()

    service.install_integrations("opencode")
    shown = service.show_integration("opencode")
    result = service.uninstall_integration("opencode")
    listed = {item["adapter"]: item for item in service.list_integrations()["adapters"]}

    assert shown["installed"] is True
    assert shown["files"] == [
        {
            "path": "AGENTS.md",
            "shared": True,
            "owner": "generic",
            "managed": True,
            "template_id": "generic-agents-md-v1",
            "sha256": shown["files"][0]["sha256"],
            "drift": "clean",
            "status": "clean",
        }
    ]
    assert result.removed == []
    assert {"path": "AGENTS.md", "reason": "shared"} in result.skipped
    assert (tmp_path / "AGENTS.md").exists()
    assert listed["opencode"]["installed"] is False


def test_agent_instruction_service_doctor_reports_clean_and_missing_file_health(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()

    clean = service.doctor("generic")
    (tmp_path / "AGENTS.md").unlink()
    broken = service.doctor("generic")

    assert clean.health == "clean"
    assert clean.findings == []
    assert broken.health == "error"
    assert broken.findings[0].code == "P2P_AGENT_FILE_MISSING"
    assert broken.findings[0].path == Path("AGENTS.md")

import hashlib
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
    assert (tmp_path / ".agents" / "skills" / "p2p-project-curator" / "SKILL.md").exists()
    assert not (tmp_path / ".codex" / "skills").exists()
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
    assert policy["project_vertical_orchestration"]["project_structure_is_live_authority"] is True
    assert "p2p_project_structure_add_section" in policy["project_vertical_orchestration"]["mcp_tools"]
    assert "p2p_project_memory_classification" in policy["project_vertical_orchestration"]["mcp_tools"]
    assert "p2p_proposal_scope_set" in policy["project_vertical_orchestration"]["mcp_tools"]
    assert policy["project_vertical_orchestration"]["proposal_creation_scope"] == "unassigned"
    assert policy["project_vertical_orchestration"]["authority_creating_decision_requires_explicit_scope"] is True
    assert policy["project_vertical_orchestration"]["classification_changes_readiness"] is False
    assert policy["project_vertical_orchestration"]["classification_authorizes_decision"] is False
    assert policy["software_spec_lifecycle"]["vertical"] == "software_project"
    assert policy["software_spec_lifecycle"]["default_intent"] == "implementation_spec"
    assert "downstream_export" in policy["software_spec_lifecycle"]["intents"]
    assert "p2p_spec_lifecycle" in policy["software_spec_lifecycle"]["mcp_tools"]
    assert policy["software_spec_lifecycle"]["rules"]["preflight_blockers_stop_writes"] is True
    assert policy["runtime_bootstrap"]["contract_path"] == ".p2p/project/runtime.yml"
    assert policy["runtime_bootstrap"]["status_command"] == "p2p runtime status"
    assert (
        policy["runtime_bootstrap"]["workspace_schema_status_command"]
        == "p2p workspace schema status"
    )
    assert policy["runtime_bootstrap"]["workspace_schema_policy"] == "current_only_v4"
    assert (
        policy["runtime_bootstrap"]["workspace_recovery_status_command"]
        == "p2p workspace transaction status"
    )
    assert policy["runtime_bootstrap"]["workspace_recovery_apply_surface"] == "owner_confirmed_cli_only"
    assert policy["runtime_bootstrap"]["manual_workspace_schema_repair"] == "forbidden"
    assert "legacy_undeclared" not in policy["runtime_bootstrap"]
    assert policy["runtime_bootstrap"]["environment_mutation"] == "owner_explicit_action_required"
    assert policy["runtime_bootstrap"]["recommended_installation_manager"] == "uv_tool"
    assert policy["runtime_bootstrap"]["runtime_environment_location"] == "outside_project_root"
    assert policy["runtime_bootstrap"]["autonomous_installation"] == "forbidden"
    assert ".venv/Scripts/p2p.exe" in policy["runtime_bootstrap"]["discovery_order"]
    integration = policy["project_integration"]
    assert integration["drift_status_command"] == "p2p drift status --root . --format json"
    assert integration["drift_diff_command"] == "p2p drift diff --root . --format json"
    assert integration["drift_block_behavior"] == "stop_writes_and_request_owner_recovery"
    assert integration["drift_apply_surface"] == "owner_confirmed_cli_only"
    assert integration["raw_drift_upload"] is False
    assert integration["git_reconciliation"] is False
    assert integration["drift_mcp_surfaces"] == [
        "p2p_replica_drift_status",
        "p2p_replica_drift_diff",
    ]
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Linked Replica Drift And Recovery" in agents
    assert "stop every project write and automatic catch-up" in agents
    assert "MCP and the web UI cannot apply" in agents
    assert policy["mcp"]["protocol_native_payloads"] is True
    assert policy["mcp"]["uses_p2p_cli_v1_envelope"] is False
    source_control = policy["source_control_boundary"]
    assert source_control["runtime_owns_source_control"] is False
    assert source_control["repository_operations_are_external"] is True
    assert source_control["accepted_proposal_implies_implementation"] is False
    assert source_control["completed_work_implies_implementation"] is False
    worker_contract = policy["wavekit_cli_worker_contract"]
    assert worker_contract["transport"] == "cli_json"
    assert worker_contract["contract_version"] == "p2p-cli/v1"
    assert worker_contract["operation_key_format"] == "wavekit:<uuid>"
    assert worker_contract["status_command"] == (
        "p2p mutation status --operation-key wavekit:<uuid> --format json"
    )
    assert worker_contract["mcp_stdio_transport"] == (
        "agent_tool_surface_not_worker_retry_boundary"
    )
    assert (
        "p2p proposal readiness assess PROP-XXX --actor ACTOR --format json "
        "--operation-key wavekit:<uuid>"
        in worker_contract["write_commands"]
    )
    assert "p2p status --format json" in worker_contract["preflight_commands"]
    assert "p2p project structure show --format json" in worker_contract["read_commands"]
    assert "p2p project domain show --format json" in worker_contract["read_commands"]
    assert (
        "p2p project vertical export eligibility --format json"
        in worker_contract["read_commands"]
    )
    assert "p2p project memory classification --format json" in worker_contract["read_commands"]
    assert (
        "p2p vertical domain list --registry REGISTRY --format json"
        in worker_contract["registry_v2_read_commands"]
    )
    assert any(
        command.startswith("p2p project structure replace apply")
        for command in worker_contract["write_commands"]
    )
    assert any(
        command.startswith("p2p project vertical export apply")
        for command in worker_contract["write_commands"]
    )
    assert any(
        command.startswith("p2p project structure add-section")
        for command in worker_contract["write_commands"]
    )
    assert "p2p choice list --format json" in worker_contract["read_commands"]
    assert any(
        command.startswith("p2p choice transition-preview")
        for command in worker_contract["write_commands"]
    )
    assert any(
        command.startswith("p2p choice transition-apply")
        for command in worker_contract["write_commands"]
    )
    assert policy["proposal_readiness"]["freshness_states"] == [
        "not_assessed",
        "current",
        "stale",
    ]
    decision_policy = policy["proposal_decision_lifecycle"]
    assert decision_policy["canonical_schema_v4_artifact"] == "decision-events.yml"
    assert decision_policy["write_protocol"] == "preview_then_exact_apply"
    assert decision_policy["reject_means_never_active"] is True
    assert decision_policy["revoke_preserves_accepted_history"] is True
    assert decision_policy["dependent_lifecycle_mutation"] == "forbidden"
    assert decision_policy["mcp"]["consent_target"] == "PROP-XXX@preview-token"
    assert "legacy_unbound_consent_can_write" not in decision_policy["mcp"]
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
    assert "Project runtime compatibility is declared by `.p2p/project/runtime.yml`" in agents
    assert "p2p runtime status --format json" in agents
    assert "p2p workspace schema status" in agents
    assert "p2p workspace transaction status" in agents
    assert "transaction locks, journals or candidates by hand" in agents
    assert "legacy_undeclared" not in agents
    assert "ask the owner for explicit environment action" in agents
    assert "WaveKit CLI Worker Contract" in agents
    assert "p2p status --format json" in agents
    assert "p2p project snapshot --format json" in agents
    assert "p2p project vertical export eligibility --format json" in agents
    assert "p2p vertical domain list --registry REGISTRY --format json" in agents
    assert "p2p proposal create \"Title\" --format json --operation-key wavekit:<uuid>" in agents
    assert "p2p mutation status --operation-key wavekit:<uuid> --format json" in agents
    assert "proposal_detail.readiness.freshness" in agents
    assert (
        "p2p proposal readiness assess PROP-XXX --actor ACTOR --format json "
        "--operation-key wavekit:<uuid>"
        in agents
    )
    assert "MCP responses are protocol-native" in agents
    assert "P2P Engine does not create branches, commits, tags, pull requests" in agents
    assert "never proves that implementation work was performed" in agents
    assert "Proposal Decision Lifecycle" in agents
    assert "Reject only a proposal that was never active" in agents
    assert "p2p_proposal_decision_apply" in agents
    assert "Standalone Vertical Registry And Drafts" in agents
    assert "p2p vertical login <name>" in agents
    assert "p2p vertical draft create --empty" in agents
    assert "p2p vertical draft update <draft-id> --document <draft.yml>" in agents
    assert "--idempotency-key <operation-id>" in agents
    codex_skill = (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").read_text(encoding="utf-8")
    assert "p2p project definition show --format json" in codex_skill
    assert "WaveKit CLI Worker Contract" in codex_skill
    assert "p2p proposal contribution list PROP-XXX --type suggestion --format json" in codex_skill
    assert "p2p spec lifecycle --intent downstream_export --change CHANGE-001 --target speckit" in codex_skill
    assert "Proposal Decision Lifecycle" in codex_skill
    assert "proposal_decision_apply" in codex_skill
    curator_skill = (
        tmp_path / ".agents" / "skills" / "p2p-project-curator" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "name: p2p-project-curator" in curator_skill
    assert "P2P Project Curator" in curator_skill
    assert "p2p project publish prepare" in curator_skill
    assert "references/editorial-workflow.md" in curator_skill
    assert "references/publication-contracts.md" in curator_skill
    assert "Do not expose internal IDs" in curator_skill
    contracts = (
        tmp_path
        / ".agents"
        / "skills"
        / "p2p-project-curator"
        / "references"
        / "publication-contracts.md"
    ).read_text(encoding="utf-8")
    assert "`curator_packet_sha256`" in contracts
    assert "prepared packet file exactly as instructed" in contracts
    assert "prepared evidence semantic hash" in contracts
    assert "outline_ids: [OUT-001]" in contracts
    assert "rubric_version: publication-editorial-rubric-v2" in contracts
    assert "model_sha256: <physical hash of completed candidate model>" in contracts
    assert "evidence:" in contracts
    assert "every other outline heading exactly once as an H2 or H3" in contracts
    assert "do not transliterate diacritics" in contracts
    assert "translate generic descriptive terms consistently" in contracts
    rubric = (
        tmp_path
        / ".agents"
        / "skills"
        / "p2p-project-curator"
        / "references"
        / "editorial-rubric.md"
    ).read_text(encoding="utf-8")
    assert "citation erasure" in rubric.lower()
    assert "at least 4" in rubric


def test_agent_instruction_service_registers_project_curator_codex_outputs(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="codex")

    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    codex_files = {
        str(file["path"]): file
        for file in registry["adapters"]["codex"]["files"]
    }

    modern = codex_files[".agents/skills/p2p-project-curator/SKILL.md"]
    assert modern["template_id"] == "codex-p2p-project-curator-skill-v3"
    assert modern["owner"] == "codex"
    assert modern["shared"] is False
    assert modern["managed"] is True
    assert modern["drift"] == "clean"
    assert modern["template_generation_id"].startswith("agent-template-generation-v7:")
    assert len(str(modern["sha256"])) == 64
    reference_paths = {
        path
        for path in codex_files
        if "p2p-project-curator/references/" in path
    }
    assert len(reference_paths) == 4
    assert all(codex_files[path]["managed"] is True for path in reference_paths)


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
        assert "P2P Engine does not create branches, commits, tags, pull requests" in content
        assert "do not prove implementation" in content
        assert "Choice definitions are immutable after creation" in content
        assert "decided, withdrawn, or superseded" in content
        assert "create a new Choice" in content

    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert registry["adapters"]["opencode"]["files"][0]["path"] == "AGENTS.md"
    assert registry["adapters"]["opencode"]["files"][0]["shared"] is True


def test_agent_instruction_service_generates_lifecycle_guidance_with_persistence_policy(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="codex")

    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    codex_skill = (tmp_path / ".agents" / "skills" / "p2p-project" / "SKILL.md").read_text(
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


def test_agent_instruction_service_embeds_curator_guidance_for_claude_without_codex_skills(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="claude")

    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Project Publication Curator" in claude
    assert "p2p project publish prepare" in claude
    assert "autonomous project documents" in claude
    assert "must not infer\nimplementation state" in claude
    assert not (tmp_path / ".agents" / "skills" / "p2p-project-curator" / "SKILL.md").exists()
    assert not (tmp_path / ".codex" / "skills" / "p2p-project-curator" / "SKILL.md").exists()

    registry = yaml.safe_load((tmp_path / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8"))
    assert set(registry["adapters"]) == {"generic", "claude"}


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
    next(item for item in files if item["path"] == "AGENTS.md")["drift"] = "conflicted"
    next(item for item in files if item["path"] == ".p2p/agent-policy.yml")[
        "template_generation_id"
    ] = "agent-template-generation-v1"
    service.write_registry(registry)

    shown = service.show_integration("generic")
    statuses = {file["path"]: file["status"] for file in shown["files"]}

    assert shown["drift"] == "drifted"
    assert shown["health"] == "error"
    assert statuses["AGENTS.md"] == "conflicted"
    assert statuses[".p2p/agent-policy.yml"] == "template_obsolete"


def test_agent_instruction_service_detects_obsolete_generation_with_matching_hash(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="generic")
    service = workspace._agent_instruction_service()
    registry = service.registry()
    record = registry["adapters"]["generic"]["files"][0]
    record["template_generation_id"] = "agent-template-generation-v1"
    service.write_registry(registry)

    shown = service.show_integration("generic")
    doctor = service.doctor("generic")

    agents = next(item for item in shown["files"] if item["path"] == "AGENTS.md")
    assert agents["content_status"] == "clean"
    assert agents["generation_status"] == "obsolete"
    assert agents["status"] == "template_obsolete"
    assert doctor.health == "warning"
    assert any(finding.code == "P2P_AGENT_TEMPLATE_OBSOLETE" for finding in doctor.findings)


def test_agent_update_removes_clean_superseded_codex_skill_paths(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="codex")
    service = workspace._agent_instruction_service()
    obsolete = tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md"
    obsolete.parent.mkdir(parents=True)
    obsolete.write_text("old generated skill\n", encoding="utf-8")
    registry = service.registry()
    registry["adapters"]["codex"]["files"].append(
        {
            "path": ".codex/skills/p2p-project/SKILL.md",
            "shared": False,
            "owner": "codex",
            "managed": True,
            "template_id": "codex-legacy-p2p-skill-v1",
            "sha256": hashlib.sha256(obsolete.read_bytes()).hexdigest(),
            "drift": "clean",
        }
    )
    service.write_registry(registry)

    result = service.install_integrations("codex")

    assert Path(".codex/skills/p2p-project/SKILL.md") in result.removed
    assert not obsolete.exists()
    assert all(
        not str(item["path"]).startswith(".codex/skills/")
        for item in service.show_integration("codex")["files"]
    )


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


def test_agent_instruction_service_keeps_other_installed_adapters_clean_on_update(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="codex")
    service = workspace._agent_instruction_service()
    service.install_integrations("claude")

    service.install_integrations("codex")
    service.install_integrations("claude")

    assert service.doctor("codex").health == "clean"
    assert service.doctor("claude").health == "clean"


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
            "template_id": "generic-agents-md-v2",
            "template_generation_id": shown["files"][0]["template_generation_id"],
            "sha256": shown["files"][0]["sha256"],
            "drift": "clean",
            "status": "clean",
            "content_status": "clean",
            "generation_status": "current",
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


def test_curator_reference_set_is_repaired_and_uninstalled_as_one_resource_set(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project", agent_profile="codex")
    service = workspace._agent_instruction_service()
    missing = (
        tmp_path
        / ".agents"
        / "skills"
        / "p2p-project-curator"
        / "references"
        / "vertical-interpretation.md"
    )
    missing.unlink()

    broken = service.doctor("codex")
    repaired = service.install_integrations("codex")
    clean = service.doctor("codex")
    removed = service.uninstall_integration("codex")

    assert broken.health == "error"
    assert any(finding.path == missing.relative_to(tmp_path) for finding in broken.findings)
    assert missing.relative_to(tmp_path) in repaired.created
    assert clean.health == "clean"
    assert len([path for path in removed.removed if "p2p-project-curator" in path.as_posix()]) == 5
    assert not (tmp_path / ".agents" / "skills" / "p2p-project-curator").exists()

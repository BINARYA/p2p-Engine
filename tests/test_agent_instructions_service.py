from pathlib import Path

import yaml

from p2p_engine.storage.filesystem import P2PWorkspace


def test_agent_instruction_service_refreshes_codex_and_merges_profiles(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Agent Project")
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
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "p2p proposal artifact status PROP-XXX" in agents
    assert "copying a\nprepared temporary file into an artifact" in agents
    assert "Project Interaction Style" in agents
    assert "p2p project interaction-style show" in agents
    assert "p2p_project_interaction_style_show" in agents
    assert "technical_verbosity: 5 (exhaustive)" in agents
    codex_skill = (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").read_text(encoding="utf-8")
    assert "p2p project interaction-style set --technical-verbosity 2 --formality 2 --assertiveness 0" in codex_skill


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
    assert any(file["path"] == "GEMINI.md" and file["drift"] == "drifted" for file in shown["files"])


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

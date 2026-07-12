from pathlib import Path

import pytest
import yaml

from p2p_engine.storage.filesystem import P2PWorkspace


def _load_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_project_initialization_service_creates_default_workspace(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    service = workspace._project_initialization_service()

    created = service.init_project("Demo Project", agent_profile="codex")

    assert Path(".p2p/project.yml") in created
    assert Path(".p2p/project/domain.yml") in created
    assert Path(".p2p/project/rubrics.yml") in created
    assert Path(".p2p/project/permissions.yml") in created
    assert Path(".p2p/config/readiness-profiles/default-readiness-v0.1.yml") in created
    assert Path(".p2p/proposals") in created
    assert Path(".p2p/prompts") in created
    assert Path("AGENTS.md") in created
    assert (tmp_path / ".codex" / "skills" / "p2p-project" / "SKILL.md").exists()

    project = _load_yaml(tmp_path / ".p2p" / "project.yml")
    project_data = project["project"]
    repository = project["repository"]
    remote = project["remote"]
    assert isinstance(project_data, dict)
    assert isinstance(repository, dict)
    assert isinstance(remote, dict)
    assert project_data["id"] == "demo-project"
    assert project_data["domain"] == "none"
    assert repository["mode"] == "local"
    assert remote["mode"] == "local"


def test_project_initialization_detected_agent_reports_selection_without_persisting_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P2P_CURRENT_AGENT", "codex")
    workspace = P2PWorkspace(tmp_path)

    result = workspace.init_project_with_summary("Detected Project")

    assert Path("AGENTS.md") in result.created
    assert result.agent_selection.selection_source == "detected"
    assert result.agent_selection.detected_adapter == "codex"
    assert result.agent_selection.effective_adapters == ["generic", "codex"]
    registry = _load_yaml(tmp_path / ".p2p" / "agent-integrations.yml")
    assert set(registry["adapters"]) == {"generic", "codex"}
    assert "detected_adapter" not in registry
    assert "current_agent" not in registry
    project_text = (tmp_path / ".p2p" / "project.yml").read_text(encoding="utf-8")
    assert "detected_adapter" not in project_text
    assert "current_agent" not in project_text


def test_project_initialization_compat_facade_still_returns_created_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P2P_CURRENT_AGENT", "codex")
    workspace = P2PWorkspace(tmp_path)

    created = workspace.init_project("Compat Project")

    assert isinstance(created, list)
    assert Path("AGENTS.md") in created
    assert Path(".codex/skills/p2p-project/SKILL.md") in created


def test_project_initialization_summary_includes_mcp_hint_and_gitignore_hygiene(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    result = workspace.init_project_with_summary("Root Hygiene Project", agent_profile="generic")

    assert result.mcp_hint.server_name == "p2p-root-hygiene-project"
    assert result.mcp_hint.server_command[-2:] == ["--root", str(tmp_path)]
    assert result.gitignore_hygiene.status == "applied"
    assert Path(".gitignore") in result.created
    assert (tmp_path / ".gitignore").exists()


def test_project_initialization_compat_facade_includes_gitignore_path_once(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    created = workspace.init_project("Compat Hygiene Project", agent_profile="generic")
    second_created = workspace.init_project("Compat Hygiene Project", agent_profile="generic")

    assert isinstance(created, list)
    assert Path(".gitignore") in created
    assert created.count(Path(".gitignore")) == 1
    assert second_created == []


def test_existing_broad_agent_install_is_not_narrowed_by_refresh_or_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Broad Project", agent_profile="all")
    monkeypatch.setenv("P2P_CURRENT_AGENT", "codex")

    workspace.refresh_agent_instructions("codex")
    workspace.install_agent_integrations("codex")

    registry = _load_yaml(tmp_path / ".p2p" / "agent-integrations.yml")
    assert set(registry["adapters"]) == {
        "generic",
        "codex",
        "claude",
        "cursor",
        "copilot",
        "gemini",
        "opencode",
    }


def test_project_initialization_service_software_domain_uses_template_rubrics(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    workspace._project_initialization_service().init_project("Software Project", project_domain="software")

    domain = _load_yaml(tmp_path / ".p2p" / "project" / "domain.yml")
    rubrics = _load_yaml(tmp_path / ".p2p" / "project" / "rubrics.yml")
    assert domain["name"] == "software"
    assert domain["status"] == "template_selected"
    assert rubrics["domain"] == "software"
    assert rubrics["status"] == "template_selected"
    assert not (tmp_path / ".p2p" / "project" / "next-actions.yml").exists()


def test_project_initialization_service_unresolved_domain_creates_next_actions(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    workspace._project_initialization_service().init_project("Custom Project", project_domain="custom")

    domain = _load_yaml(tmp_path / ".p2p" / "project" / "domain.yml")
    rubrics = _load_yaml(tmp_path / ".p2p" / "project" / "rubrics.yml")
    next_actions = _load_yaml(tmp_path / ".p2p" / "project" / "next-actions.yml")
    assert domain["type"] == "custom"
    assert domain["status"] == "unresolved"
    assert rubrics["status"] == "unresolved"
    assert next_actions["next_actions"][0]["id"] == "NEXT-001"


def test_project_initialization_service_owner_and_cloud_remote_payload(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    workspace._project_initialization_service().init_project(
        "Remote Project",
        repository_mode="cloud",
        owner="Davide",
        remote_provider="github",
        remote_name="upstream",
        remote_url_value="https://example.test/org/repo.git",
    )

    project = _load_yaml(tmp_path / ".p2p" / "project.yml")
    permissions = _load_yaml(tmp_path / ".p2p" / "project" / "permissions.yml")
    remote = project["remote"]
    repository = project["repository"]
    identities = permissions["identities"]
    assert isinstance(remote, dict)
    assert isinstance(repository, dict)
    assert isinstance(identities, dict)
    assert repository["mode"] == "cloud"
    assert remote["mode"] == "remote"
    assert remote["provider"] == "github"
    assert remote["remote"] == "upstream"
    assert remote["url"] == "https://example.test/org/repo.git"
    assert identities["davide"]["display_name"] == "Davide"
    assert identities["davide"]["role"] == "owner"


def test_project_initialization_service_is_idempotent_and_preserves_existing_files(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    service = workspace._project_initialization_service()

    service.init_project("Demo Project")
    governance_file = tmp_path / ".p2p" / "governance" / "constitution.md"
    governance_file.write_text("# Constitution\n\nLocal content.\n", encoding="utf-8")

    created = service.init_project("Demo Project")

    assert created == []
    assert governance_file.read_text(encoding="utf-8") == "# Constitution\n\nLocal content.\n"


def test_workspace_init_can_select_vertical_without_section_interview(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    created = workspace.init_project(
        "Vertical Init",
        vertical_id="base_project",
        profile="default",
        modules=["roadmap"],
        owner="Davide",
    )

    assert Path(".p2p/project/vertical.yml") in created
    assert Path(".p2p/project/vertical.lock.yml") in created
    assert Path(".p2p/project/definition.yml") in created
    definition = _load_yaml(tmp_path / ".p2p" / "project" / "definition.yml")
    assert definition["project_definition"]["profile"] == "default"
    assert definition["project_definition"]["modules"] == ["roadmap"]
    assert "sections" in definition["project_definition"]

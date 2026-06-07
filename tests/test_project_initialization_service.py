from pathlib import Path

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

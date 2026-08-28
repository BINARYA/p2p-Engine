from __future__ import annotations

import tomllib
from pathlib import Path

from p2p_engine import __version__ as P2P_ENGINE_VERSION
from p2p_engine.services.agent_templates import agent_policy, agents_markdown, claude_markdown
from p2p_engine.services.runtime_contract import RuntimeContractService

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_primary_installation_docs_are_uv_first_and_version_pinned() -> None:
    readme = _read("README.md")
    install = _read("docs/INSTALL.md")

    for text in (readme, install):
        assert "uv tool install --managed-python --python 3.12 --no-config" in text
        assert f"p2p_engine-{P2P_ENGINE_VERSION}-py3-none-any.whl" in text
        assert "project-local install from the GitHub Release wheel" not in text
        assert "normal workflow is to install P2P Engine into the target project's own" not in text
    assert "pip/Virtualenv Fallback" in install
    assert "not yet qualified on a public Python index" in install
    assert "uv tool install p2p-engine==<VERSION>" in install


def test_installation_docs_cover_lifecycle_security_network_and_boundaries() -> None:
    install = _read("docs/INSTALL.md")
    normalized = " ".join(install.split())

    required = (
        "uv tool uninstall p2p-engine",
        "--force",
        "roll back",
        "SHA256SUMS",
        "gh attestation verify",
        "HTTP_PROXY",
        "SSL_CERT_FILE",
        "--offline",
        "cleaned cache",
        "do not delete `.p2p`",
        "P2P Engine does not import uv",
        "standalone compiled executable",
    )
    for fragment in required:
        assert fragment in normalized


def test_mcp_docs_use_absolute_command_arrays_and_exact_version_escape_hatch() -> None:
    mcp = _read("docs/MCP.md")
    normalized = " ".join(mcp.split())

    assert "/absolute/path/reported/by/p2p-doctor/python" in mcp
    assert "command: /absolute/path/to/uv" in mcp
    assert "--isolated" in mcp
    assert "p2p-mcp-server, --root" in mcp
    assert "MCP neither installs/reconciles persistent runtimes" in normalized
    assert "project-local virtualenv form" not in mcp


def test_generated_agent_guidance_requires_owner_action_and_preserves_fallbacks() -> None:
    policy = agent_policy("Demo", ["generic"])["runtime_bootstrap"]
    generic = agents_markdown("Demo", ["generic"])
    claude = claude_markdown("Demo")

    assert policy["recommended_installation_manager"] == "uv_tool"
    assert policy["environment_mutation"] == "owner_explicit_action_required"
    assert policy["autonomous_installation"] == "forbidden"
    assert ".venv/Scripts/p2p.exe" in policy["discovery_order"]
    for generated in (generic, claude):
        assert "use `p2p` on `PATH` as the normal command" in generated
        assert "never install uv, Python or P2P Engine" in generated
        assert "never edit runtime/schema state" in generated
        assert "uv tool install" not in generated


def test_managed_setup_is_deterministic_and_does_not_change_runtime_schema(tmp_path: Path) -> None:
    service = RuntimeContractService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    first = service.render_setup_guide()
    second = service.render_setup_guide()
    contract = service.default_contract_payload()

    assert first == second
    assert "explicit owner approval" in first
    assert "uvx --isolated" in first
    assert contract["runtime"]["p2p"] == {
        "requires": f"=={P2P_ENGINE_VERSION}",
        "recommended": P2P_ENGINE_VERSION,
    }
    forbidden = {"installer", "source", "url", "wheel", "sha256"}
    assert forbidden.isdisjoint(contract["runtime"]["p2p"])


def test_obsolete_primary_virtualenv_phrases_do_not_return() -> None:
    maintained = "\n".join(
        _read(path)
        for path in (
            "README.md",
            "docs/INSTALL.md",
            "docs/MCP.md",
            "docs/CLI-GUIDE.md",
            "docs/AGENT-INTEGRATION.md",
            "docs/TUTORIAL.md",
        )
    )

    prohibited = (
        "The normal workflow is to install P2P Engine into the target project's own virtualenv",
        "Prefer the project-local virtualenv form",
        "The example assumes P2P Engine is installed in the project-local `.venv`",
        "It also contains the `.venv` with the `p2p` runtime",
        "preferred server command uses `/path/to/project/.venv/bin/python",
    )
    for phrase in prohibited:
        assert phrase not in maintained

    # Remaining `.venv` references are contributor, explicit fallback or historical release text.
    assert ". .venv/bin/activate" in _read("CONTRIBUTING.md")
    assert "pip/Virtualenv Fallback" in _read("docs/INSTALL.md")
    assert "existing pip/virtualenv fallback" in _read("docs/MCP.md")


def test_uv_is_not_a_runtime_dependency_or_import_requirement() -> None:
    project = tomllib.loads(_read("pyproject.toml"))["project"]
    dependencies = [str(item).lower() for item in project["dependencies"]]
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src" / "p2p_engine").rglob("*.py")
    )

    assert not any(item == "uv" or item.startswith("uv[") for item in dependencies)
    assert "import uv" not in source
    assert "from uv" not in source

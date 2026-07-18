from __future__ import annotations

from pathlib import Path


DOCS_ROOT = Path(__file__).resolve().parents[1] / "docs"


def _read_doc(name: str) -> str:
    return (DOCS_ROOT / name).read_text(encoding="utf-8")


def test_docs_prefer_project_local_mcp_python_and_keep_path_fallback() -> None:
    text = "\n".join(
        [
            _read_doc("MCP.md"),
            _read_doc("INSTALL.md"),
            _read_doc("AGENT-INTEGRATION.md"),
        ]
    )

    assert ".venv/bin/python" in text
    assert "-m p2p_engine.mcp.server" in text or '"p2p_engine.mcp.server"' in text
    assert "p2p-mcp-server" in text


def test_docs_do_not_describe_root_as_sibling_repository_support() -> None:
    text = "\n".join(
        [
            _read_doc("MCP.md"),
            _read_doc("INSTALL.md"),
            _read_doc("AGENT-INTEGRATION.md"),
            _read_doc("CLI-GUIDE.md"),
        ]
    ).lower()

    assert "sibling repository" not in text
    assert "sibling repo" not in text


def test_docs_distinguish_software_spec_handoff_from_project_export() -> None:
    cli_guide = " ".join(_read_doc("CLI-GUIDE.md").split())
    glossary = _read_doc("GLOSSARY.md")

    assert "compatibility/software-oriented workflow" in cli_guide
    assert "not the default project definition export" in cli_guide
    assert "software-spec handoff" in glossary
    assert "`p2p project export`" in glossary


def test_docs_capture_canonical_pack_freshness_and_next_action_contracts() -> None:
    cli_guide = _read_doc("CLI-GUIDE.md")
    mcp_guide = " ".join(_read_doc("MCP.md").split())
    development = _read_doc("DEVELOPMENT-GUIDELINES.md")

    assert "`vertical.yml` contains metadata only" in cli_guide
    assert "`current_legacy`" in cli_guide
    assert "`NEXT-CHANGE-<CHANGE-ID>`" in cli_guide
    assert "truncates only the final composed and" in mcp_guide
    assert "exact source and candidate bytes, not mtimes" in mcp_guide
    assert "atomic complete-set writes" in development


def test_docs_and_templates_describe_two_phase_decision_lifecycle() -> None:
    cli_guide = _read_doc("CLI-GUIDE.md")
    mcp_guide = _read_doc("MCP.md")
    glossary = _read_doc("GLOSSARY.md")
    migration = _read_doc("WORKSPACE-MIGRATION.md")
    tutorial = _read_doc("TUTORIAL.md")
    install = _read_doc("INSTALL.md")
    template_source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "p2p_engine"
        / "services"
        / "agent_templates.py"
    ).read_text(encoding="utf-8")

    assert "p2p decision preview PROP-001" in cli_guide
    assert "p2p decision apply PROP-001" in cli_guide
    assert "Rejection is an initial decision" in cli_guide
    assert "Revocation closes the authority" in cli_guide
    assert "`PROP-XXX@preview-token`" in mcp_guide
    assert "old unbound consent cannot write" in mcp_guide
    assert "## Decision Event Ledger" in glossary
    assert "`workspace-v2-to-v3`" in migration
    assert "p2p decision preview PROP-001" in tutorial
    assert "p2p decision preview PROP-001" in install
    assert "PROPOSAL_DECISION_LIFECYCLE_BLOCK" in template_source
    assert "Legacy MCP" in template_source
    assert "p2p proposal accept PROP-001 --reason" not in tutorial
    assert "p2p proposal accept PROP-001 --reason" not in install
    assert "deprecated" not in glossary.lower()

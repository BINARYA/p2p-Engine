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

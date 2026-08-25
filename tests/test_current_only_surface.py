from __future__ import annotations

from pathlib import Path

import yaml

from p2p_engine import __version__
from p2p_engine.storage.filesystem import P2PWorkspace


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "p2p_engine"
MAINTAINED_DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    ROOT / "docs" / "INSTALL.md",
    ROOT / "docs" / "CLI-GUIDE.md",
    ROOT / "docs" / "CLI-CONTRACT.md",
    ROOT / "docs" / "MCP.md",
    ROOT / "docs" / "AGENT-INTEGRATION.md",
    ROOT / "docs" / "WORKSPACE-SCHEMA.md",
)
HISTORICAL_DOCUMENT_ALLOWLIST = {
    ROOT / "docs" / "development" / "cli-primitive-inventory.md",
    ROOT / "docs" / "development" / "codebase-architecture-review.md",
}
DISCARDED_SURFACE_TOKENS = (
    "legacy_undeclared",
    "absent_legacy",
    "legacy_absent",
    "legacy_unverifiable",
    "current_legacy",
    "unknown_legacy",
    "unknown_origin",
    "legacy_mtime_fallback",
    "current_legacy_fallback",
    "workspace migrate",
    "legacy-resolution",
    "mark-legacy",
    "proposal_decision_legacy",
    "codex-legacy",
)


def _hits(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return {token for token in DISCARDED_SURFACE_TOKENS if token in text}


def test_runtime_package_has_no_discarded_compatibility_entry_points() -> None:
    offenders = {
        path.relative_to(ROOT).as_posix(): sorted(_hits(path))
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file() and path.suffix in {".py", ".md", ".yml", ".yaml"} and _hits(path)
    }

    assert offenders == {}


def test_maintained_documents_and_adapters_have_no_discarded_surfaces() -> None:
    adapter_documents = tuple(
        path for path in (ROOT / ".agents").rglob("*") if path.is_file()
    )
    offenders = {
        path.relative_to(ROOT).as_posix(): sorted(_hits(path))
        for path in (*MAINTAINED_DOCUMENTS, *adapter_documents)
        if _hits(path)
    }

    assert offenders == {}
    codex_skills = ROOT / ".codex" / "skills"
    assert not codex_skills.exists() or not any(path.is_file() for path in codex_skills.rglob("*"))


def test_obsolete_command_evidence_is_confined_to_reviewed_historical_docs() -> None:
    offenders = {
        path
        for path in (ROOT / "docs").rglob("*.md")
        if _hits(path)
    }

    assert offenders == HISTORICAL_DOCUMENT_ALLOWLIST
    for path in offenders:
        opening = path.read_text(encoding="utf-8")[:1500].lower()
        assert "fotografia" in opening or "storica" in opening


def test_checked_in_examples_use_only_current_workspace_and_agent_contracts() -> None:
    for name in ("board-game-project", "minimal-software-project"):
        root = ROOT / "examples" / name
        schema = yaml.safe_load(
            (root / ".p2p" / "project" / "workspace-schema.yml").read_text(encoding="utf-8")
        )["workspace_schema"]
        runtime = yaml.safe_load(
            (root / ".p2p" / "project" / "runtime.yml").read_text(encoding="utf-8")
        )["runtime"]["p2p"]
        integration = yaml.safe_load(
            (root / ".p2p" / "agent-integrations.yml").read_text(encoding="utf-8")
        )

        assert schema["current_version"] == 4
        assert runtime == {"requires": f"=={__version__}", "recommended": __version__}
        assert integration["adapters"]["codex"]["status"] == "installed"
        assert not (root / ".codex" / "skills").exists()
        assert P2PWorkspace(root).validate().findings == []

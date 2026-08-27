from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "p2p_engine"
MAINTAINED_DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "ROADMAP.md",
    ROOT / "docs" / "INSTALL.md",
    ROOT / "docs" / "CLI-GUIDE.md",
    ROOT / "docs" / "CLI-CONTRACT.md",
    ROOT / "docs" / "MCP.md",
    ROOT / "docs" / "AGENT-INTEGRATION.md",
    ROOT / "docs" / "WORKSPACE-SCHEMA.md",
)
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


def test_maintained_docs_have_no_obsolete_command_evidence() -> None:
    offenders = {
        path
        for path in (ROOT / "docs").rglob("*.md")
        if _hits(path)
    }

    assert offenders == set()


def test_local_history_and_generated_project_artifacts_are_ignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/specs/" in ignore
    assert "/outputs/" in ignore
    assert "/drafts/" in ignore
    assert "/examples/*/" in ignore
    assert "/.p2p/" in ignore
    assert "/.agents/" in ignore
    assert "/.cursor/" in ignore
    assert (ROOT / "examples" / "README.md").is_file()
    assert not (ROOT / "examples" / "board-game-project").exists()
    assert not (ROOT / "examples" / "minimal-software-project").exists()
    assert not (ROOT / "docs" / "vision").exists()


def test_acceptance_walkthroughs_assign_scope_before_decision_preview() -> None:
    for path in (ROOT / "docs" / "TUTORIAL.md", ROOT / "docs" / "INSTALL.md"):
        text = path.read_text(encoding="utf-8")
        proposal = text.index("p2p proposal show PROP-001")
        scope = text.index("p2p proposal scope set PROP-001", proposal)
        decision = text.index("p2p decision preview PROP-001", scope)

        assert proposal < scope < decision
        assert "--kind project_global" in text[scope:decision]


def test_unreleased_install_guides_do_not_claim_the_0_5_asset_exists() -> None:
    unavailable_asset = (
        "https://github.com/BINARYA/p2p-Engine/releases/download/"
        "v0.5.0/p2p_engine-0.5.0-py3-none-any.whl"
    )

    assert unavailable_asset not in (ROOT / "README.md").read_text(encoding="utf-8")
    assert unavailable_asset not in (ROOT / "docs" / "INSTALL.md").read_text(
        encoding="utf-8"
    )


def test_current_cli_examples_match_non_git_runtime_contracts() -> None:
    guide = (ROOT / "docs" / "CLI-GUIDE.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "CLI-CONTRACT.md").read_text(encoding="utf-8")

    assert "Managed branch accept/reject commands" not in guide
    assert 'p2p work retire WORK-001 --reason "' in guide
    export_apply = next(
        line
        for line in contract.splitlines()
        if line.startswith("p2p project vertical export apply ")
    )
    assert "--idempotency-key" in export_apply
    assert "--operation-key" not in export_apply

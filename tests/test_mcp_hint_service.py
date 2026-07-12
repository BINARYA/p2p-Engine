from __future__ import annotations

from pathlib import Path

from p2p_engine.services.mcp_hints import build_mcp_hint, render_shell_command


def test_mcp_hint_derives_stable_server_name_from_project_identity(tmp_path: Path) -> None:
    hint = build_mcp_hint(tmp_path, project_name="P2P My Project!")

    assert hint.server_name == "p2p-my-project"


def test_mcp_hint_falls_back_to_directory_name_for_server_slug(tmp_path: Path) -> None:
    root = tmp_path / "Fallback Project"

    hint = build_mcp_hint(root, project_name="")

    assert hint.server_name == "p2p-fallback-project"


def test_mcp_hint_server_slug_handles_punctuation_spaces_and_uppercase(tmp_path: Path) -> None:
    hint = build_mcp_hint(tmp_path, project_name="  ACME: Launch Plan!!!  ")

    assert hint.server_name == "p2p-acme-launch-plan"


def test_mcp_hint_uses_project_local_python_module_command(tmp_path: Path) -> None:
    project_python = tmp_path / ".venv" / "bin" / "python"
    project_python.parent.mkdir(parents=True)
    project_python.write_text("#!/usr/bin/env python\n", encoding="utf-8")

    hint = build_mcp_hint(tmp_path, project_name="Demo Project")

    assert hint.project_python == project_python
    assert hint.project_python_exists is True
    assert hint.server_command == [
        str(project_python),
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        str(tmp_path),
    ]
    assert hint.codex_command == ["codex", "mcp", "add", "p2p-demo-project", "--", *hint.server_command]


def test_mcp_hint_retains_short_path_fallback_command(tmp_path: Path) -> None:
    hint = build_mcp_hint(tmp_path, project_name="Demo Project")

    assert hint.fallback_command == ["p2p-mcp-server", "--root", str(tmp_path)]


def test_mcp_hint_missing_project_python_is_not_hidden(tmp_path: Path) -> None:
    hint = build_mcp_hint(tmp_path, project_name="Demo Project")

    assert hint.project_python_exists is False
    assert hint.notes
    assert "not found" in hint.notes[0]
    assert "p2p-mcp-server" in " ".join(hint.fallback_command)


def test_mcp_hint_rendering_quotes_paths_with_spaces_and_shell_characters(tmp_path: Path) -> None:
    root = tmp_path / "Project With Spaces & Symbols"
    hint = build_mcp_hint(root, project_name="Demo Project")

    rendered = render_shell_command(hint.codex_command)

    assert f"'{hint.project_python}'" in rendered
    assert f"'{hint.root}'" in rendered

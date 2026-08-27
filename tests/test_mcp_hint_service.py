from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.services.mcp_hints import (
    build_mcp_hint,
    mcp_client_config,
    render_shell_command,
)


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


def test_mcp_hint_prefers_running_importable_runtime(tmp_path: Path) -> None:
    running_python = tmp_path / "uv tools" / "pýthon"
    running_python.parent.mkdir()
    running_python.write_text("#!/usr/bin/env python\n", encoding="utf-8")

    hint = build_mcp_hint(
        tmp_path,
        project_name="Demo Project",
        running_python=running_python,
        running_runtime_importable=True,
        which=lambda _command: None,
    )

    assert hint.invocation_mode == "running-runtime"
    assert hint.server_command == [
        str(running_python.resolve()),
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        str(tmp_path),
    ]
    assert hint.codex_command == ["codex", "mcp", "add", "p2p-demo-project", "--", *hint.server_command]


def test_mcp_hint_preserves_uv_tool_interpreter_symlink(tmp_path: Path) -> None:
    base_python = tmp_path / "managed-python" / "python"
    base_python.parent.mkdir()
    base_python.touch()
    tool_python = tmp_path / "uv-tools" / "p2p-engine" / "bin" / "python"
    tool_python.parent.mkdir(parents=True)
    tool_python.symlink_to(base_python)

    hint = build_mcp_hint(
        tmp_path / "project",
        running_python=tool_python,
        running_runtime_importable=True,
        which=lambda _command: None,
    )

    assert hint.server_command[0] == str(tool_python.absolute())
    assert hint.server_command[0] != str(base_python.resolve())


def test_mcp_hint_retains_short_path_fallback_only_when_resolvable(tmp_path: Path) -> None:
    server = tmp_path / "tool bin" / "p2p-mcp-server"
    server.parent.mkdir()
    server.touch()
    hint = build_mcp_hint(
        tmp_path,
        project_name="Demo Project",
        running_runtime_importable=False,
        which=lambda command: str(server) if command == "p2p-mcp-server" else None,
    )

    assert hint.fallback_command == ["p2p-mcp-server", "--root", str(tmp_path)]
    assert hint.server_command[0] == str(server.resolve())


def test_mcp_hint_missing_project_python_is_not_hidden(tmp_path: Path) -> None:
    hint = build_mcp_hint(
        tmp_path,
        project_name="Demo Project",
        running_runtime_importable=False,
        which=lambda _command: None,
    )

    assert hint.project_python_exists is False
    assert hint.notes
    assert hint.fallback_command == []
    assert hint.server_command == []
    assert hint.codex_command == []
    assert "No executable" in hint.notes[0]


def test_mcp_hint_supports_existing_windows_virtualenv_fallback(tmp_path: Path) -> None:
    project_python = tmp_path / ".venv" / "Scripts" / "python.exe"
    project_python.parent.mkdir(parents=True)
    project_python.touch()

    hint = build_mcp_hint(
        tmp_path,
        running_runtime_importable=False,
        which=lambda _command: None,
    )

    assert hint.project_python == project_python
    assert hint.invocation_mode == "project-venv"
    assert hint.project_venv_command[0] == str(project_python)


def test_mcp_hint_provides_absolute_exact_version_uv_command(tmp_path: Path) -> None:
    uv = tmp_path / "uv bin" / "uv.exe"
    uv.parent.mkdir()
    uv.touch()

    hint = build_mcp_hint(
        tmp_path,
        recommended_version="0.5.0",
        running_runtime_importable=False,
        which=lambda command: str(uv) if command == "uv" else None,
    )

    assert hint.invocation_mode == "uv-exact"
    assert hint.exact_version_command[0] == str(uv.resolve())
    assert "--isolated" in hint.exact_version_command
    assert hint.exact_version_command[-2:] == ["--root", str(tmp_path)]
    running_config = mcp_client_config(hint)
    exact_config = mcp_client_config(hint, exact_version=True)
    assert running_config == {
        "command": str(uv.resolve()),
        "args": hint.server_command[1:],
    }
    assert exact_config["command"] == str(uv.resolve())
    assert exact_config["args"] == hint.exact_version_command[1:]


def test_mcp_client_config_rejects_unavailable_invocation(tmp_path: Path) -> None:
    hint = build_mcp_hint(
        tmp_path,
        running_runtime_importable=False,
        which=lambda _command: None,
    )

    with pytest.raises(ValueError, match="No executable MCP invocation"):
        mcp_client_config(hint)


def test_mcp_hint_rendering_quotes_paths_with_spaces_and_shell_characters(tmp_path: Path) -> None:
    root = tmp_path / "Project With Spaces & Symbols"
    running_python = tmp_path / "Runtime With Spaces" / "python"
    running_python.parent.mkdir()
    running_python.touch()
    hint = build_mcp_hint(
        root,
        project_name="Demo Project",
        running_python=running_python,
        running_runtime_importable=True,
        which=lambda _command: None,
    )

    rendered = render_shell_command(hint.codex_command)

    assert f"'{running_python.resolve()}'" in rendered
    assert f"'{hint.root}'" in rendered

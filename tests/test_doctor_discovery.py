from __future__ import annotations

from pathlib import Path

from p2p_engine.cli_commands.doctor import discover_runtime


def _which(mapping: dict[str, str]):
    return lambda command: mapping.get(command)


def test_doctor_prefers_resolved_p2p_on_path(tmp_path: Path) -> None:
    executable = tmp_path / "tool bin" / "p2p"
    executable.parent.mkdir()
    executable.touch()

    result = discover_runtime(tmp_path, which=_which({"p2p": str(executable)}))

    assert result.p2p_path == executable.resolve()
    assert result.recommended_command == (str(executable.resolve()),)


def test_doctor_uses_running_importable_runtime_without_project_venv(tmp_path: Path) -> None:
    running_python = tmp_path / "uv tools" / "pýthon"
    running_python.parent.mkdir()
    running_python.touch()

    result = discover_runtime(
        tmp_path / "Prøject With Spaces",
        which=_which({}),
        running_python=running_python,
        package_importable=True,
        mcp_importable=True,
    )

    assert result.local_venv_p2p is None
    assert result.recommended_command == (
        str(running_python.resolve()),
        "-m",
        "p2p_engine",
    )


def test_doctor_preserves_uv_tool_python_symlink(tmp_path: Path) -> None:
    managed = tmp_path / "managed" / "python"
    managed.parent.mkdir()
    managed.touch()
    tool_python = tmp_path / "tools" / "p2p-engine" / "bin" / "python"
    tool_python.parent.mkdir(parents=True)
    tool_python.symlink_to(managed)

    result = discover_runtime(
        tmp_path / "project",
        which=_which({}),
        running_python=tool_python,
        package_importable=True,
        mcp_importable=True,
    )

    assert result.running_python == tool_python.absolute()
    assert result.running_python != managed.resolve()


def test_doctor_recognizes_existing_windows_virtualenv_fallback(tmp_path: Path) -> None:
    local_p2p = tmp_path / ".venv" / "Scripts" / "p2p.exe"
    local_p2p.parent.mkdir(parents=True)
    local_p2p.touch()

    result = discover_runtime(
        tmp_path,
        which=_which({}),
        running_python=tmp_path / "missing-python.exe",
        package_importable=False,
        mcp_importable=False,
    )

    assert result.local_venv_p2p == local_p2p
    assert result.recommended_command == (str(local_p2p),)


def test_doctor_does_not_recommend_nonexistent_paths(tmp_path: Path) -> None:
    result = discover_runtime(
        tmp_path,
        which=_which({}),
        running_python=tmp_path / "old-system-python",
        package_importable=False,
        mcp_importable=False,
    )

    assert result.p2p_path is None
    assert result.local_venv_p2p is None
    assert result.recommended_command == ()


def test_doctor_reports_absolute_uv_launcher_for_gui_safe_guidance(tmp_path: Path) -> None:
    uv = tmp_path / "uv bin" / "uv.exe"
    uv.parent.mkdir()
    uv.touch()

    result = discover_runtime(
        tmp_path,
        which=_which({"uv": str(uv)}),
        package_importable=False,
        mcp_importable=False,
        running_python=tmp_path / "missing",
    )

    assert result.uv_path == uv.resolve()

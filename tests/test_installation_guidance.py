from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.services.installation_guidance import (
    P2P_MANAGED_PYTHON,
    exact_version_invocation,
    future_index_invocation,
    github_release_wheel_url,
    persistent_install_invocation,
    project_cli_candidates,
    project_python_candidates,
    standalone_binary_invocation,
    verified_local_wheel_install_invocation,
)


def test_github_release_source_is_exact_and_maintained() -> None:
    url = github_release_wheel_url("0.5.0")

    assert url == (
        "https://github.com/BINARYA/p2p-Engine/releases/download/v0.5.0/"
        "p2p_engine-0.5.0-py3-none-any.whl"
    )
    assert "main" not in url


@pytest.mark.parametrize(
    "version",
    ["", "main", "0.5.0/../../main", "0.5.0+project-url", "v0.5.0"],
)
def test_release_source_rejects_mutable_or_project_supplied_values(version: str) -> None:
    with pytest.raises(ValueError):
        github_release_wheel_url(version)


def test_persistent_tool_command_forces_managed_python_and_exact_wheel() -> None:
    invocation = persistent_install_invocation("0.5.0", force=True)

    assert invocation.mode == "uv-persistent"
    assert invocation.source == "github-release-wheel"
    assert invocation.command[:3] == ["uv", "tool", "install"]
    assert invocation.command[-1].endswith("/p2p_engine-0.5.0-py3-none-any.whl")
    assert ["--managed-python", "--python", P2P_MANAGED_PYTHON] == invocation.command[3:6]
    assert "--force" in invocation.command
    assert "--system" not in invocation.command


def test_verified_local_wheel_requires_one_existing_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "p2p_engine-0.5.0-py3-none-any.whl"
    wheel.write_bytes(b"candidate")

    invocation = verified_local_wheel_install_invocation(wheel)

    assert invocation.mode == "verified-local-wheel"
    assert invocation.command[-1] == str(wheel.resolve())
    with pytest.raises(ValueError):
        verified_local_wheel_install_invocation(tmp_path)
    with pytest.raises(ValueError):
        verified_local_wheel_install_invocation(tmp_path / "missing.whl")


def test_exact_version_commands_cover_cli_and_mcp_without_shell_activation() -> None:
    cli = exact_version_invocation("0.5.0", "p2p", "runtime", "status")
    mcp = exact_version_invocation(
        "0.5.0",
        "p2p-mcp-server",
        "--root",
        "/project with spaces",
        uv_executable="/opt/uv bin/uvx",
        uvx=True,
    )

    assert cli.command[:4] == ["uv", "tool", "run", "--isolated"]
    assert "p2p" in cli.command
    assert mcp.command[0] == "/opt/uv bin/uvx"
    assert "--isolated" in mcp.command
    assert mcp.command[-2:] == ["--root", "/project with spaces"]


def test_unpublished_index_and_standalone_binary_are_explicitly_unavailable() -> None:
    public_index = future_index_invocation("0.5.0")
    binary = standalone_binary_invocation()

    assert public_index.available is False
    assert public_index.command == []
    assert public_index.source == "public-index-future"
    assert binary.available is False
    assert "does not currently publish" in binary.reason


def test_virtualenv_candidates_include_posix_and_windows_layouts(tmp_path: Path) -> None:
    cli = [path.relative_to(tmp_path).as_posix() for path in project_cli_candidates(tmp_path)]
    python = [
        path.relative_to(tmp_path).as_posix() for path in project_python_candidates(tmp_path)
    ]

    assert ".venv/bin/p2p" in cli
    assert ".venv/Scripts/p2p.exe" in cli
    assert ".venv/bin/python" in python
    assert ".venv/Scripts/python.exe" in python

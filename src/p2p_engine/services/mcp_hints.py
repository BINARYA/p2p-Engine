from __future__ import annotations

import importlib.util
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from p2p_engine import __version__ as P2P_ENGINE_VERSION
from p2p_engine.services.installation_guidance import (
    exact_version_invocation,
    first_existing,
    project_python_candidates,
    render_shell_command,
)

__all__ = [
    "McpHint",
    "build_mcp_hint",
    "mcp_client_config",
    "mcp_server_name",
    "render_shell_command",
]


@dataclass(frozen=True)
class McpHint:
    server_name: str
    root: Path
    project_python: Path
    project_python_exists: bool
    server_command: list[str]
    server_executable: str | None
    server_args: list[str]
    codex_command: list[str]
    fallback_command: list[str]
    project_venv_command: list[str]
    exact_version_command: list[str]
    invocation_mode: str
    notes: list[str]

def mcp_server_name(project_name: str | None, *, fallback_name: str) -> str:
    source = project_name if project_name and project_name.strip() else fallback_name
    slug = _slugify(source)
    if slug == "p2p":
        slug = _slugify(fallback_name)
    if slug.startswith("p2p-"):
        slug = slug.removeprefix("p2p-")
    return f"p2p-{slug or 'project'}"


def build_mcp_hint(
    root: Path,
    *,
    project_name: str | None = None,
    recommended_version: str = P2P_ENGINE_VERSION,
    running_python: str | Path | None = None,
    running_runtime_importable: bool | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> McpHint:
    resolved_root = Path(root).resolve()
    python_candidates = project_python_candidates(resolved_root)
    existing_project_python = first_existing(python_candidates)
    project_python = existing_project_python or python_candidates[0]
    project_python_exists = existing_project_python is not None
    server_name = mcp_server_name(project_name, fallback_name=resolved_root.name)

    # Keep a virtualenv/uv-tool interpreter path intact. Resolving its symlink
    # can escape the environment and point at a managed base Python that cannot
    # import the tool's packages.
    selected_python = Path(running_python or sys.executable).expanduser().absolute()
    if running_runtime_importable is None:
        running_runtime_importable = importlib.util.find_spec("p2p_engine.mcp.server") is not None
    path_server = which("p2p-mcp-server")
    uv_path = which("uv")
    uvx_path = which("uvx")

    fallback_command = (
        ["p2p-mcp-server", "--root", str(resolved_root)] if path_server else []
    )
    project_venv_command = (
        [
            str(existing_project_python),
            "-m",
            "p2p_engine.mcp.server",
            "--root",
            str(resolved_root),
        ]
        if existing_project_python is not None
        else []
    )
    exact_version_command: list[str] = []
    if uv_path:
        exact_version_command = exact_version_invocation(
            recommended_version,
            "p2p-mcp-server",
            "--root",
            str(resolved_root),
            uv_executable=str(Path(uv_path).resolve()),
        ).command
    elif uvx_path:
        exact_version_command = exact_version_invocation(
            recommended_version,
            "p2p-mcp-server",
            "--root",
            str(resolved_root),
            uv_executable=str(Path(uvx_path).resolve()),
            uvx=True,
        ).command

    notes: list[str] = []
    if running_runtime_importable and selected_python.is_file():
        invocation_mode = "running-runtime"
        server_command = [
            str(selected_python),
            "-m",
            "p2p_engine.mcp.server",
            "--root",
            str(resolved_root),
        ]
    elif path_server:
        invocation_mode = "path"
        server_command = [str(Path(path_server).resolve()), "--root", str(resolved_root)]
        notes.append("Used the p2p-mcp-server executable resolved from PATH.")
    elif project_venv_command:
        invocation_mode = "project-venv"
        server_command = list(project_venv_command)
        notes.append("Used an existing project virtualenv as a supported fallback.")
    elif exact_version_command:
        invocation_mode = "uv-exact"
        server_command = list(exact_version_command)
        notes.append("Used the exact recommended version through the available uv launcher.")
    else:
        invocation_mode = "unavailable"
        server_command = []
        notes.append(
            "No executable P2P MCP runtime was found. Stop and ask the owner to install "
            "P2P Engine or provide an approved runner."
        )

    if not project_python_exists:
        notes.append(
            "No existing project-local POSIX or Windows virtualenv was found; none is required "
            "for the recommended uv tool installation."
        )
    return McpHint(
        server_name=server_name,
        root=resolved_root,
        project_python=project_python,
        project_python_exists=project_python_exists,
        server_command=server_command,
        server_executable=server_command[0] if server_command else None,
        server_args=list(server_command[1:]),
        codex_command=(
            ["codex", "mcp", "add", server_name, "--", *server_command]
            if server_command
            else []
        ),
        fallback_command=fallback_command,
        project_venv_command=project_venv_command,
        exact_version_command=exact_version_command,
        invocation_mode=invocation_mode,
        notes=notes,
    )


def mcp_client_config(hint: McpHint, *, exact_version: bool = False) -> dict[str, object]:
    command = hint.exact_version_command if exact_version else hint.server_command
    if not command:
        raise ValueError("No executable MCP invocation is available for client configuration.")
    return {"command": command[0], "args": list(command[1:])}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "project"

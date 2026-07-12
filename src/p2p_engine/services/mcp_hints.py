from __future__ import annotations

import re
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class McpHint:
    server_name: str
    root: Path
    project_python: Path
    project_python_exists: bool
    server_command: list[str]
    codex_command: list[str]
    fallback_command: list[str]
    notes: list[str]


def mcp_server_name(project_name: str | None, *, fallback_name: str) -> str:
    source = project_name if project_name and project_name.strip() else fallback_name
    slug = _slugify(source)
    if slug == "p2p":
        slug = _slugify(fallback_name)
    if slug.startswith("p2p-"):
        slug = slug.removeprefix("p2p-")
    return f"p2p-{slug or 'project'}"


def build_mcp_hint(root: Path, *, project_name: str | None = None) -> McpHint:
    resolved_root = Path(root).resolve()
    project_python = resolved_root / ".venv" / "bin" / "python"
    project_python_exists = project_python.exists()
    server_name = mcp_server_name(project_name, fallback_name=resolved_root.name)
    server_command = [
        str(project_python),
        "-m",
        "p2p_engine.mcp.server",
        "--root",
        str(resolved_root),
    ]
    fallback_command = ["p2p-mcp-server", "--root", str(resolved_root)]
    notes: list[str] = []
    if not project_python_exists:
        notes.append(
            f"Project-local Python was not found at {project_python}. "
            "Use this as the conventional project virtualenv command, or use the PATH fallback."
        )
    return McpHint(
        server_name=server_name,
        root=resolved_root,
        project_python=project_python,
        project_python_exists=project_python_exists,
        server_command=server_command,
        codex_command=["codex", "mcp", "add", server_name, "--", *server_command],
        fallback_command=fallback_command,
        notes=notes,
    )


def render_shell_command(command: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in command)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "project"

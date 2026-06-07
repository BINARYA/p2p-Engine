from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.storage.git import get_git_status


def register_doctor_commands(app: typer.Typer, agent_app: typer.Typer) -> None:
    @app.command("doctor")
    def doctor(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Diagnose P2P CLI, project, Git, and MCP runtime readiness."""
        _print_doctor(root, agent_mode=False)

    @agent_app.command("doctor")
    def agent_doctor(
        target: str | None = typer.Argument(None, help="Optional agent adapter id or all"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Diagnose agent runtime readiness and recovery steps."""
        _print_doctor(root, agent_mode=True)
        if target:
            console.print("Agent integration doctor")
            workspace = workspace_for(root)
            if target == "all":
                result = workspace.agent_integrations_list()
                for adapter in result["adapters"]:
                    console.print(
                        f"  {adapter['adapter']}: installed={str(adapter['installed']).lower()} "
                        f"drift={adapter['drift']}"
                    )
                return
            try:
                result = workspace.agent_integration_show(target)
            except ValueError as exc:
                fail(str(exc))
            console.print(f"  {result['adapter']}: installed={str(result['installed']).lower()} drift={result['drift']}")
            for record in result.get("files", []):
                console.print(f"    {record['path']}: {record.get('drift')}")


def _print_doctor(root: Path, *, agent_mode: bool) -> None:
    resolved_root = root.resolve()
    p2p_path = shutil.which("p2p")
    local_p2p = resolved_root / ".venv" / "bin" / "p2p"
    package_importable = importlib.util.find_spec("p2p_engine") is not None
    mcp_importable = importlib.util.find_spec("p2p_engine.mcp.server") is not None
    git_status = get_git_status(resolved_root)
    project_exists = (resolved_root / ".p2p" / "project.yml").exists()

    console.print("P2P doctor")
    console.print(f"  root: {resolved_root}")
    console.print(f"  project: {str(project_exists).lower()}")
    console.print(f"  p2p_on_path: {str(bool(p2p_path)).lower()}")
    console.print(f"  p2p_path: {p2p_path or 'none'}")
    console.print(f"  local_venv_p2p: {local_p2p if local_p2p.exists() else 'none'}")
    console.print(f"  python: {sys.executable}")
    console.print(f"  package_importable: {str(package_importable).lower()}")
    console.print(f"  python_module_cli: python -m p2p_engine")
    console.print(f"  mcp_server_importable: {str(mcp_importable).lower()}")
    console.print(f"  mcp_server_module: python -m p2p_engine.mcp.server --root {resolved_root}")
    console.print(f"  git_repository: {str(git_status.is_repository).lower()}")
    console.print(f"  git_branch: {git_status.branch or 'none'}")
    console.print(f"  git_clean: {str(git_status.is_clean).lower()}")

    if project_exists:
        status = workspace_for(resolved_root).sync_status()
        console.print(f"  repository_mode: {status.mode}")
        console.print(f"  sync_ready: {str(status.can_sync).lower()}")
        console.print(f"  sync_reason: {status.reason}")
    else:
        console.print("  repository_mode: unknown")
        console.print("  sync_ready: false")
        console.print("  sync_reason: no .p2p/project.yml found")

    command = _recommended_p2p_command(resolved_root, p2p_path, local_p2p, package_importable)
    console.print("Recovery")
    console.print(f"  recommended_p2p_command: {command}")
    console.print("  discovery_order: p2p -> .venv/bin/p2p -> python -m p2p_engine -> MCP")
    if agent_mode:
        console.print(
            "  missing_primitive_rule: if no CLI or explicit MCP write tool is available, "
            "stop and report these diagnostics instead of editing .p2p by hand"
        )
    if command != "unavailable":
        console.print(f"  suggested_start: {command} status")
        console.print(f"  suggested_context: {command} context --budget small")
        console.print(f"  suggested_validate: {command} validate")
    elif mcp_importable:
        console.print(
            "  suggested_mcp: configure a local stdio MCP client with "
            f"python -m p2p_engine.mcp.server --root {resolved_root}"
        )
    else:
        console.print("  suggested_install: install P2P Engine or use the project owner provided runner image")


def _recommended_p2p_command(
    root: Path,
    p2p_path: str | None,
    local_p2p: Path,
    package_importable: bool,
) -> str:
    if p2p_path:
        return "p2p"
    if local_p2p.exists():
        return str(local_p2p)
    if package_importable:
        return "python -m p2p_engine"
    return "unavailable"

from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import typer

from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.services.installation_guidance import (
    exact_version_invocation,
    first_existing,
    project_cli_candidates,
    render_shell_command,
)


@dataclass(frozen=True)
class DoctorRuntimeDiscovery:
    p2p_path: Path | None
    local_venv_p2p: Path | None
    running_python: Path
    running_runtime_importable: bool
    mcp_server_importable: bool
    uv_path: Path | None
    uvx_path: Path | None
    recommended_command: tuple[str, ...]


def discover_runtime(
    root: Path,
    *,
    which: Callable[[str], str | None] = shutil.which,
    running_python: str | Path | None = None,
    package_importable: bool | None = None,
    mcp_importable: bool | None = None,
) -> DoctorRuntimeDiscovery:
    resolved_root = Path(root).resolve()
    # Do not follow a virtualenv interpreter symlink into its base Python: the
    # displayed command must preserve the environment that imports P2P Engine.
    selected_python = Path(running_python or sys.executable).expanduser().absolute()
    if package_importable is None:
        package_importable = importlib.util.find_spec("p2p_engine") is not None
    if mcp_importable is None:
        mcp_importable = importlib.util.find_spec("p2p_engine.mcp.server") is not None

    p2p_resolved = which("p2p")
    uv_resolved = which("uv")
    uvx_resolved = which("uvx")
    p2p_path = Path(p2p_resolved).resolve() if p2p_resolved else None
    local_p2p = first_existing(project_cli_candidates(resolved_root))
    uv_path = Path(uv_resolved).resolve() if uv_resolved else None
    uvx_path = Path(uvx_resolved).resolve() if uvx_resolved else None

    if p2p_path is not None:
        command = (str(p2p_path),)
    elif package_importable and selected_python.is_file():
        command = (str(selected_python), "-m", "p2p_engine")
    elif local_p2p is not None:
        command = (str(local_p2p),)
    else:
        command = ()

    return DoctorRuntimeDiscovery(
        p2p_path=p2p_path,
        local_venv_p2p=local_p2p,
        running_python=selected_python,
        running_runtime_importable=bool(package_importable),
        mcp_server_importable=bool(mcp_importable),
        uv_path=uv_path,
        uvx_path=uvx_path,
        recommended_command=command,
    )


def register_doctor_commands(app: typer.Typer, agent_app: typer.Typer) -> None:
    @app.command("doctor")
    def doctor(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Diagnose P2P CLI, project, and MCP runtime readiness."""
        _print_doctor(root, agent_mode=False)

    @agent_app.command("doctor")
    def agent_doctor(
        target: str | None = typer.Argument(None, help="Optional agent adapter id or all"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Diagnose agent runtime readiness and recovery steps."""
        _print_doctor(root, agent_mode=True)
        workspace = workspace_for(root)
        try:
            result = workspace.agent_doctor(target or "all")
        except ValueError as exc:
            fail(str(exc))
        console.print("Agent integration doctor")
        console.print(f"  target: {result.target}")
        console.print(f"  health: {result.health}")
        console.print(f"  registry: {result.registry_path}")
        if result.findings:
            console.print("  findings:")
            for finding in result.findings:
                console.print(
                    f"    {finding.severity.upper()} {finding.code} "
                    f"{finding.adapter} {finding.path}: {finding.message}"
                )
                if finding.suggested_command:
                    console.print(f"      suggested: {finding.suggested_command}")
        else:
            console.print("  findings: none")
        if result.health == "error":
            raise typer.Exit(code=1)


def _print_doctor(root: Path, *, agent_mode: bool) -> None:
    resolved_root = root.resolve()
    discovery = discover_runtime(resolved_root)
    project_exists = (resolved_root / ".p2p" / "project.yml").exists()

    console.print("P2P doctor")
    console.print(f"  root: {resolved_root}")
    console.print(f"  project: {str(project_exists).lower()}")
    console.print(f"  p2p_on_path: {str(discovery.p2p_path is not None).lower()}")
    console.print(f"  p2p_path: {discovery.p2p_path or 'none'}")
    console.print(f"  local_venv_p2p: {discovery.local_venv_p2p or 'none'}")
    console.print(f"  running_python: {discovery.running_python}")
    console.print(
        "  running_runtime_importable: "
        f"{str(discovery.running_runtime_importable).lower()}"
    )
    console.print(f"  package_importable: {str(discovery.running_runtime_importable).lower()}")
    console.print(
        "  python_module_cli: "
        f"{render_shell_command([str(discovery.running_python), '-m', 'p2p_engine'])}"
    )
    console.print(f"  mcp_server_importable: {str(discovery.mcp_server_importable).lower()}")
    console.print(
        "  mcp_server_module: "
        f"{render_shell_command([str(discovery.running_python), '-m', 'p2p_engine.mcp.server', '--root', str(resolved_root)])}"
    )
    console.print(f"  uv_on_path: {str(discovery.uv_path is not None).lower()}")
    console.print(f"  uv_path: {discovery.uv_path or 'none'}")
    if project_exists:
        workspace = workspace_for(resolved_root)
        try:
            schema = workspace.workspace_schema_status()
        except (OSError, ValueError) as exc:
            console.print("  workspace_schema_state: inspection_failed")
            console.print(f"  workspace_schema_reason: {exc}")
        else:
            console.print(f"  workspace_schema_state: {schema.state}")
            console.print(f"  workspace_layout_status: {schema.layout_status}")
            console.print(f"  workspace_alignment_status: {schema.alignment_status}")
            console.print(
                "  workspace_schema_supported: "
                f"{str(schema.layout_status == 'current').lower()}"
            )
            console.print(
                "  workspace_recovery_required: "
                f"{str(bool(schema.recovery.get('required', False))).lower()}"
            )
        try:
            freshness = workspace.project_freshness()
        except (OSError, ValueError) as exc:
            console.print("  derived_freshness: inspection_failed")
            console.print(f"  derived_freshness_reason: {exc}")
        else:
            console.print(f"  derived_freshness: {freshness.status}")
    else:
        console.print("  workspace_schema_state: unavailable")
        console.print("  derived_freshness: unavailable")

    command = (
        render_shell_command(discovery.recommended_command)
        if discovery.recommended_command
        else "unavailable"
    )
    console.print("Recovery")
    console.print(f"  recommended_p2p_command: {command}")
    console.print(
        "  discovery_order: p2p on PATH -> running P2P runtime -> existing project "
        "virtualenv fallback -> exact uv runtime -> MCP"
    )
    if agent_mode:
        console.print(
            "  missing_primitive_rule: if no CLI or explicit MCP write tool is available, "
            "stop and report these diagnostics instead of editing .p2p by hand"
        )
    if command != "unavailable":
        console.print(f"  suggested_start: {command} status")
        console.print(f"  suggested_context: {command} context --budget small")
        console.print(f"  suggested_validate: {command} validate")
    elif discovery.mcp_server_importable:
        console.print(
            "  suggested_mcp: configure a local stdio MCP client with "
            f"{render_shell_command([str(discovery.running_python), '-m', 'p2p_engine.mcp.server', '--root', str(resolved_root)])}"
        )
    else:
        console.print(
            "  suggested_install: ask the owner to follow P2P-SETUP.md or the official "
            "installation guide; do not install or edit .p2p automatically"
        )

    if project_exists:
        try:
            runtime_status = workspace_for(resolved_root).runtime_status()
        except (OSError, ValueError):
            runtime_status = None
        if runtime_status is not None and not runtime_status.compatible and runtime_status.recommended:
            uv_launcher = discovery.uv_path or discovery.uvx_path
            if uv_launcher is not None:
                exact = exact_version_invocation(
                    runtime_status.recommended,
                    "p2p",
                    "runtime",
                    "status",
                    "--root",
                    str(resolved_root),
                    uv_executable=str(uv_launcher),
                    uvx=discovery.uv_path is None,
                )
                console.print(
                    "  exact_version_owner_command: "
                    f"{render_shell_command(exact.command)}"
                )
            else:
                console.print(
                    "  exact_version_owner_command: unavailable (uv is not on PATH; ask the "
                    "owner to install it or use the documented pip/venv fallback)"
                )

from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_prompt_commands(
    explore_app: typer.Typer,
    digest_app: typer.Typer,
    clarify_app: typer.Typer,
    synthesize_app: typer.Typer,
    plan_app: typer.Typer,
    tasks_app: typer.Typer,
    swot_app: typer.Typer,
) -> None:
    @explore_app.command("prompt")
    def explore_prompt(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate an exploration prompt file."""
        _generate_prompt(proposal_id, "explore", root)

    @explore_app.command("import")
    def explore_import(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Exploration output file or artifact directory"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Import exploration output into P2P artifacts."""
        try:
            imported = workspace_for(root).import_exploration(proposal_id, source)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Exploration imported.[/green]")
        for path in imported:
            console.print(f"  updated {path}")

    @explore_app.command("status")
    def explore_status(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show exploration artifact status."""
        try:
            status = workspace_for(root).exploration_status(proposal_id)
        except ValueError as exc:
            fail(str(exc))
        console.print(f"Exploration status for [bold]{status.proposal_id}[/bold]")
        console.print("")
        console.print("Artifacts:")
        for artifact in status.artifacts:
            marker = "[green]✓[/green]" if artifact.has_content else "[red]✗[/red]"
            console.print(f"  {marker} {artifact.filename}  {artifact.quality_state}")
        console.print("")
        console.print(f"Open questions: {status.unresolved_questions} unresolved")
        console.print("")
        console.print("Suggested next command:")
        console.print(f"  {status.suggested_next_command}")

    @digest_app.command("prompt")
    def digest_prompt(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate a digest prompt file."""
        _generate_prompt(proposal_id, "digest", root)

    @clarify_app.command("prompt")
    def clarify_prompt(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate a clarification prompt file."""
        _generate_prompt(proposal_id, "clarify", root)

    @clarify_app.command("import")
    def clarify_import(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Clarification output file"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Import clarification output into clarifications.md."""
        _import_artifact(proposal_id, "clarify", source, root)

    @synthesize_app.command("prompt")
    def synthesize_prompt(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate a proposal synthesis prompt file."""
        _generate_prompt(proposal_id, "synthesize", root)

    @synthesize_app.command("import")
    def synthesize_import(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Synthesized proposal.md output file"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Import synthesized proposal output into proposal.md."""
        _import_artifact(proposal_id, "synthesize", source, root)

    @plan_app.command("prompt")
    def plan_prompt(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate an execution plan prompt file."""
        _generate_prompt(proposal_id, "plan", root)

    @plan_app.command("import")
    def plan_import(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Execution plan output file"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Import execution plan output into execution-plan.md."""
        _import_artifact(proposal_id, "plan", source, root)

    @tasks_app.command("prompt")
    def tasks_prompt(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate a tasks prompt file."""
        _generate_prompt(proposal_id, "tasks", root)

    @tasks_app.command("import")
    def tasks_import(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        source: Path = typer.Argument(..., help="Tasks YAML output file"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Import tasks output into tasks.yml."""
        _import_artifact(proposal_id, "tasks", source, root)

    @swot_app.command("prompt")
    def swot_prompt(
        proposal_id: str = typer.Argument(..., help="Proposal ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate a governance SWOT prompt file."""
        _generate_prompt(proposal_id, "swot", root)


def _generate_prompt(proposal_id: str, prompt_type: str, root: Path) -> None:
    try:
        path = workspace_for(root).generate_prompt(proposal_id, prompt_type)
    except ValueError as exc:
        fail(str(exc))
    console.print(f"[green]Generated[/green] {path}")


def _import_artifact(proposal_id: str, artifact_type: str, source: Path, root: Path) -> None:
    try:
        path = workspace_for(root).import_artifact(proposal_id, artifact_type, source)
    except ValueError as exc:
        fail(str(exc))
    console.print(f"[green]Imported[/green] {path}")

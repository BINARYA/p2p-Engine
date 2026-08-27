from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from pathlib import Path

import typer

from p2p_engine.cli_contract import print_json
from p2p_engine.cli_shared import console, fail, yaml_dump_for_cli
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.release_contracts import current_contract_versions


def register_project_status_commands(
    app: typer.Typer,
    assess_app: typer.Typer,
    assess_maturity_app: typer.Typer,
) -> None:
    @app.command()
    def status(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show project and proposal status."""
        workspace = workspace_for(root)
        summary = workspace.status()
        if output_format == "json":
            print_json(
                {
                    "workspace_status": _validation_result_to_dict(summary),
                    "contract_versions": current_contract_versions(),
                }
            )
            return
        if output_format != "text":
            fail("Status format must be text or json")
        console.print(f"Project: [bold]{summary.project_name}[/bold]")
        console.print(f"Workspace: {summary.root}")
        if summary.workspace_schema is not None:
            schema = summary.workspace_schema
            console.print(
                "Workspace schema: "
                f"{schema['state']} layout={schema['layout_status']} "
                f"alignment={schema['alignment_status']} "
                f"version={schema['current_version']} target={schema['target_version']}"
            )
        if summary.derived_freshness is not None:
            freshness = summary.derived_freshness
            console.print(
                "Derived freshness: "
                f"{freshness['status']} attention_nodes={freshness['attention_nodes']} "
                f"verification={freshness.get('verification', 'unknown')}"
            )
        if not summary.proposals:
            console.print("Proposals: none")
            return
        console.print("Proposals:")
        for proposal in summary.proposals:
            console.print(f"  {proposal.proposal_id}  {proposal.slug}  {proposal.status}")

    @app.command("context")
    def context(
        budget: str = typer.Option("small", "--budget", help="Context budget: small or medium"),
        target: str | None = typer.Option(None, "--target", help="Optional PROP/CHANGE/CHOICE/WORK ID"),
        output_format: str = typer.Option("text", "--format", help="Output format: text, json, or yaml"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show a compact, token-aware context packet for agents."""
        try:
            packet = workspace_for(root).context_packet(budget=budget, target=target)
        except ValueError as exc:
            fail(str(exc))
        if output_format == "yaml":
            typer.echo(yaml_dump_for_cli(_validation_result_to_dict(packet)))
        elif output_format == "json":
            print_json(_validation_result_to_dict(packet))
        elif output_format == "text":
            _print_context_packet(packet)
        else:
            fail("Context format must be text, json, or yaml")

    @app.command()
    def check(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Validate the minimal P2P workspace structure."""
        result = workspace_for(root).check()
        if result.ok:
            console.print("[green]Workspace OK.[/green]")
            return
        console.print("[red]Workspace incomplete.[/red]")
        for path in result.missing:
            console.print(f"  missing {path}")
        raise typer.Exit(code=1)

    @app.command()
    def validate(
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Run read-only structural and semantic validation."""
        try:
            result = workspace_for(root).validate()
        except ValueError as exc:
            fail(str(exc))
        if output_format == "json":
            print_json(_validation_result_to_dict(result))
        elif output_format == "text":
            console.print("Validation")
            console.print(f"  errors: {result.errors}")
            console.print(f"  warnings: {result.warnings}")
            console.print(f"  infos: {result.infos}")
            if not result.findings:
                console.print("  findings: none")
            else:
                console.print("Findings:")
                for finding in result.findings:
                    console.print(
                        f"  {finding.severity.upper()} {finding.code} {finding.path}"
                    )
                    console.print(f"    {finding.message}")
                    if finding.suggested_command:
                        console.print(f"    command: {finding.suggested_command}")
        else:
            fail("Validation format must be text or json")
        if result.errors:
            raise typer.Exit(code=1)

    @assess_app.command("refresh")
    def assess_refresh(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Generate a deterministic readiness assessment."""
        try:
            assessment = workspace_for(root).refresh_project_assessment()
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Project assessment refreshed.[/green]")
        _print_assessment_summary(assessment)

    @assess_app.command("show")
    def assess_show(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show the stored project readiness assessment."""
        try:
            assessment = workspace_for(root).show_project_assessment()
        except ValueError as exc:
            fail(str(exc))
        _print_assessment_summary(assessment)

    @assess_maturity_app.command("refresh")
    def assess_maturity_refresh(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Generate project definition maturity from configured rubrics."""
        try:
            maturity = workspace_for(root).refresh_definition_maturity()
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Project definition maturity refreshed.[/green]")
        _print_definition_maturity(maturity)

    @assess_maturity_app.command("show")
    def assess_maturity_show(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show stored project definition maturity."""
        try:
            maturity = workspace_for(root).show_definition_maturity()
        except ValueError as exc:
            fail(str(exc))
        _print_definition_maturity(maturity)


def _print_context_packet(packet: object) -> None:
    console.print("P2P compact context")
    console.print(f"  budget: {packet.budget}")
    console.print(f"  target: {packet.target or 'none'}")
    console.print("Current state:")
    for key, value in packet.current_state.items():
        if isinstance(value, dict):
            console.print(f"  {key}:")
            for child_key, child_value in value.items():
                console.print(f"    {child_key}: {child_value}")
        else:
            console.print(f"  {key}: {value}")
    console.print("Next actions:")
    if not packet.next_actions:
        console.print("  none")
    for action in packet.next_actions:
        console.print(
            f"  {action.get('id')} {action.get('priority')} {action.get('kind')} "
            f"{action.get('target') or ''}".rstrip()
        )
        console.print(f"    command: {action.get('command') or 'none'}")
    console.print("Relevant artifacts:")
    if not packet.relevant_artifacts:
        console.print("  none")
    for artifact in packet.relevant_artifacts:
        title = artifact.get("title") or artifact.get("change_id") or artifact.get("target") or ""
        console.print(
            f"  {artifact.get('type')} {artifact.get('id')} "
            f"{artifact.get('status')} {title}".rstrip()
        )
        console.print(f"    path: {artifact.get('path')}")
        console.print(f"    command: {artifact.get('command')}")
    if packet.nearby_context is not None:
        nearby = packet.nearby_context
        console.print("Nearby decision context:")
        console.print(f"  completeness: {nearby.completeness.value}")
        if not nearby.hits:
            console.print(f"  none: {nearby.empty_reason or 'no relevant context'}")
        for hit in nearby.hits:
            strongest = hit.reasons[0] if hit.reasons else None
            console.print(
                f"  {hit.owner_type.value} {hit.owner_id} score={hit.score}"
            )
            if strongest is not None:
                console.print(f"    {strongest.signal}: {strongest.detail}")
        if nearby.truncation.truncated:
            console.print("  truncated: true")
    console.print("Allowed commands:")
    for command in packet.allowed_commands:
        console.print(f"  - {command}")
    console.print("Do not read:")
    for item in packet.do_not_read:
        console.print(f"  - {item}")
    console.print(f"Bounded next step: {packet.bounded_next_step}")


def _validation_result_to_dict(result: object) -> object:
    if isinstance(result, Enum):
        return result.value
    if hasattr(result, "__dataclass_fields__"):
        return {
            key: _validation_result_to_dict(getattr(result, key))
            for key in result.__dataclass_fields__
        }
    if isinstance(result, Path):
        return result.as_posix()
    if isinstance(result, (list, tuple, set, frozenset)):
        return [_validation_result_to_dict(item) for item in result]
    if isinstance(result, Mapping):
        return {str(key): _validation_result_to_dict(value) for key, value in result.items()}
    return result


def _print_assessment_summary(assessment: object) -> None:
    console.print("Project readiness assessment")
    console.print(f"  path: {assessment.path}")
    console.print(f"  generated_on: {assessment.generated_on}")
    console.print(f"  assessment_type: {assessment.assessment_type}")
    console.print(
        "  completion: "
        f"{assessment.completion_score}/100 "
        f"{assessment.completion_status} "
        f"(confidence: {assessment.confidence})"
    )
    console.print(
        "  maturity: "
        f"{assessment.maturity_score if assessment.maturity_score is not None else 'n/a'} "
        f"{assessment.maturity_status}"
    )
    if assessment.gaps:
        console.print("  gaps:")
        for gap in assessment.gaps:
            console.print(f"    - {gap}")
    else:
        console.print("  gaps: none")
    if assessment.suggested_actions:
        console.print("  suggested actions:")
        for command in assessment.suggested_actions:
            console.print(f"    - {command}")
    else:
        console.print("  suggested actions: none")


def _print_definition_maturity(maturity: object) -> None:
    console.print("Project definition maturity")
    console.print(f"  path: {maturity.path}")
    console.print(f"  generated_on: {maturity.generated_on}")
    console.print(f"  structure source: {maturity.structure_source}")
    console.print(f"  score: {maturity.score}/100")
    console.print(f"  status: {maturity.status}")
    console.print("Criteria:")
    for criterion in maturity.criteria:
        console.print(
            f"  {criterion.get('id')}  {criterion.get('status')}  "
            f"{criterion.get('score')}/100  {criterion.get('title')}"
        )
        evidence = criterion.get("evidence", [])
        if isinstance(evidence, list) and evidence:
            first = evidence[0]
            if isinstance(first, dict):
                console.print(
                    f"    evidence: {first.get('type')} {first.get('id')} "
                    f"{first.get('state')}"
                )
    if maturity.gaps:
        console.print("Gaps:")
        for gap in maturity.gaps:
            console.print(f"  - {gap}")
    else:
        console.print("Gaps: none")
    if maturity.suggested_actions:
        console.print("Suggested actions:")
        for action in maturity.suggested_actions:
            console.print(f"  - {action}")

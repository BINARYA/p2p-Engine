from __future__ import annotations

import json
import shlex
from pathlib import Path

import typer
import yaml
from rich.console import Console

from p2p_engine.core.contribution import ContributionType
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace, WorkAcceptConflict

app = typer.Typer(help="P2P Engine CLI")
proposal_app = typer.Typer(help="Manage proposals")
proposal_contribution_app = typer.Typer(help="Manage proposal contributions")
contribution_app = typer.Typer(help="Manage contributions")
decision_app = typer.Typer(help="Record decisions")
explore_app = typer.Typer(help="Explore rough proposals")
digest_app = typer.Typer(help="Generate digest prompts")
clarify_app = typer.Typer(help="Generate clarification prompts")
synthesize_app = typer.Typer(help="Generate and import proposal synthesis")
plan_app = typer.Typer(help="Generate plan prompts")
tasks_app = typer.Typer(help="Generate task prompts")
governance_app = typer.Typer(help="Manage governance artifacts")
swot_app = typer.Typer(help="Generate SWOT prompts")
vote_app = typer.Typer(help="Record and inspect governance votes")
precedent_app = typer.Typer(help="Record governance decision precedents")
project_app = typer.Typer(help="Manage rationalized project state")
project_brief_app = typer.Typer(help="Generate and import operational project briefs")
project_remote_app = typer.Typer(help="Manage project remote profile")
impact_app = typer.Typer(help="Analyze proposal impact")
conflict_app = typer.Typer(help="Record and inspect project conflicts")
change_app = typer.Typer(help="Manage operational Change Set metadata")
spec_app = typer.Typer(help="Generate and refine P2P-native software specs")
registry_app = typer.Typer(help="Manage generated project registries")
intake_app = typer.Typer(help="Analyze raw ideas against project context")
intake_apply_app = typer.Typer(help="Plan and run controlled intake applications")
choice_app = typer.Typer(help="Manage project choices")
work_app = typer.Typer(help="Manage P2P work manifests")
agent_app = typer.Typer(help="Manage agent-facing project instructions")
agent_instructions_app = typer.Typer(help="Generate and refresh agent instructions")
assess_app = typer.Typer(help="Assess project readiness and maturity")

proposal_app.add_typer(proposal_contribution_app, name="contribution")
app.add_typer(proposal_app, name="proposal")
app.add_typer(contribution_app, name="contribution")
app.add_typer(decision_app, name="decision")
app.add_typer(explore_app, name="explore")
app.add_typer(digest_app, name="digest")
app.add_typer(clarify_app, name="clarify")
app.add_typer(synthesize_app, name="synthesize")
app.add_typer(plan_app, name="plan")
app.add_typer(tasks_app, name="tasks")
app.add_typer(governance_app, name="governance")
app.add_typer(swot_app, name="swot")
app.add_typer(vote_app, name="vote")
app.add_typer(precedent_app, name="precedent")
app.add_typer(project_app, name="project")
app.add_typer(impact_app, name="impact")
app.add_typer(conflict_app, name="conflict")
app.add_typer(change_app, name="change")
app.add_typer(spec_app, name="spec")
app.add_typer(registry_app, name="registry")
app.add_typer(intake_app, name="intake")
app.add_typer(choice_app, name="choice")
app.add_typer(work_app, name="work")
app.add_typer(agent_app, name="agent")
app.add_typer(assess_app, name="assess")
project_app.add_typer(project_brief_app, name="brief")
project_app.add_typer(project_remote_app, name="remote")
intake_app.add_typer(intake_apply_app, name="apply")
agent_app.add_typer(agent_instructions_app, name="instructions")

console = Console()


def _fail(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=1)


def _workspace(root: Path) -> P2PWorkspace:
    return P2PWorkspace(root)


def _yaml_dump_for_cli(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


@app.command()
def init(
    name: str | None = typer.Argument(None, help="Project name"),
    agent: str = typer.Option(
        "generic",
        "--agent",
        help="Initial agent profile: generic, codex, claude, or all",
    ),
    repository: str = typer.Option(
        "local",
        "--repository",
        help="Repository mode: local or cloud",
    ),
    mcp_hint: bool | None = typer.Option(
        None,
        "--mcp-hint/--no-mcp-hint",
        help="Show an MCP setup command after initialization",
    ),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Initialize a P2P workspace."""
    if name is None:
        console.print("[bold]P2P project initialization[/bold]")
        name = typer.prompt("Project name", default=root.resolve().name)
        agent = _prompt_choice(
            "Initial agent profile",
            choices=("generic", "codex", "claude", "all"),
            default=agent,
        )
        repository = _prompt_choice(
            "Repository mode",
            choices=("local", "cloud"),
            default=repository,
        )
        if mcp_hint is None:
            mcp_hint = typer.confirm("Show MCP setup hint?", default=True)
    else:
        mcp_hint = bool(mcp_hint)

    workspace = _workspace(root)
    try:
        created = workspace.init_project(
            name=name,
            agent_profile=agent,
            repository_mode=repository,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]P2P workspace initialized.[/green]")
    for path in created:
        console.print(f"  created {path}")
    _print_init_next_steps(root.resolve(), agent, show_mcp_hint=mcp_hint)


def _prompt_choice(prompt: str, choices: tuple[str, ...], default: str) -> str:
    normalized_default = default.strip().lower()
    if normalized_default not in choices:
        normalized_default = choices[0]
    choices_text = "/".join(choices)
    while True:
        value = typer.prompt(f"{prompt} ({choices_text})", default=normalized_default)
        normalized = value.strip().lower()
        if normalized in choices:
            return normalized
        console.print(f"[red]Invalid value:[/red] {value}. Choose one of: {choices_text}")


def _print_init_next_steps(root: Path, agent: str, show_mcp_hint: bool = False) -> None:
    console.print("Next steps:")
    console.print("  1. p2p registry refresh")
    console.print("  2. p2p status")
    console.print("  3. p2p next")
    console.print("  4. Create or intake the first idea with p2p proposal create or p2p intake prompt")
    if show_mcp_hint:
        server_name = f"p2p-{root.name}"
        console.print("MCP setup hint:")
        console.print(
            "  "
            + " ".join(
                [
                    "codex",
                    "mcp",
                    "add",
                    shlex.quote(server_name),
                    "--",
                    "p2p-mcp-server",
                    "--root",
                    shlex.quote(str(root)),
                ]
            )
        )
        if agent != "codex":
            console.print("  Use the same stdio command in other MCP clients.")


@agent_instructions_app.command("refresh")
def agent_instructions_refresh(
    profile: str = typer.Option(
        "generic",
        "--profile",
        "--agent",
        help="Agent profile to add or refresh: generic, codex, claude, or all",
    ),
    repository: str | None = typer.Option(
        None,
        "--repository",
        help="Repository mode override: local or cloud",
    ),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Refresh agent-safe project instructions without removing other profiles."""
    try:
        result = _workspace(root).refresh_agent_instructions(
            profile=profile,
            repository_mode=repository,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Agent instructions refreshed.[/green]")
    console.print(f"  profile: {result.profile}")
    console.print(f"  policy: {result.policy_path}")
    if result.created:
        console.print("  created:")
        for path in result.created:
            console.print(f"    {path}")
    if result.updated:
        console.print("  updated:")
        for path in result.updated:
            console.print(f"    {path}")
    if not result.created and not result.updated:
        console.print("  no changes")


@app.command()
def status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Show project and proposal status."""
    workspace = _workspace(root)
    summary = workspace.status()
    console.print(f"Project: [bold]{summary.project_name}[/bold]")
    console.print(f"Workspace: {summary.root}")
    if not summary.proposals:
        console.print("Proposals: none")
        return
    console.print("Proposals:")
    for proposal in summary.proposals:
        console.print(f"  {proposal.proposal_id}  {proposal.slug}  {proposal.status}")


@app.command("next")
def next_action(
    top: int | None = typer.Option(None, "--top", min=1, help="Limit the number of actions shown"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show advisory next actions."""
    try:
        actions = _workspace(root).next_actions(limit=top)
    except ValueError as exc:
        _fail(str(exc))
    console.print("Next actions")
    if not actions:
        console.print("  none")
        return
    for index, action in enumerate(actions, start=1):
        target = f"  target: {action.target}" if action.target else "  target: none"
        console.print(f"{index}. {action.action_id}  {action.priority}  {action.kind}")
        console.print(target)
        console.print(f"  reason: {action.reason}")
        console.print(f"  command: {action.command or 'none'}")
        console.print(f"  source: {action.source}")


@app.command()
def check(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Validate the minimal P2P workspace structure."""
    result = _workspace(root).check()
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
        result = _workspace(root).validate()
    except ValueError as exc:
        _fail(str(exc))
    if output_format == "json":
        console.print(json.dumps(_validation_result_to_dict(result), indent=2))
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
        _fail("Validation format must be text or json")
    if result.errors:
        raise typer.Exit(code=1)


def _validation_result_to_dict(result: object) -> object:
    if hasattr(result, "__dataclass_fields__"):
        return {
            key: _validation_result_to_dict(getattr(result, key))
            for key in result.__dataclass_fields__
        }
    if isinstance(result, Path):
        return result.as_posix()
    if isinstance(result, list):
        return [_validation_result_to_dict(item) for item in result]
    if isinstance(result, dict):
        return {str(key): _validation_result_to_dict(value) for key, value in result.items()}
    return result


@assess_app.command("refresh")
def assess_refresh(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Generate a deterministic readiness assessment."""
    try:
        assessment = _workspace(root).refresh_project_assessment()
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Project assessment refreshed.[/green]")
    _print_assessment_summary(assessment)


@assess_app.command("show")
def assess_show(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Show the stored project readiness assessment."""
    try:
        assessment = _workspace(root).show_project_assessment()
    except ValueError as exc:
        _fail(str(exc))
    _print_assessment_summary(assessment)


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


@proposal_app.command("create")
def proposal_create(
    title: str = typer.Argument(..., help="Proposal title"),
    problem: str | None = typer.Option(None, "--problem", help="Problem statement"),
    context: str | None = typer.Option(None, "--context", help="Proposal context"),
    goal: list[str] | None = typer.Option(None, "--goal", help="Goal. Can be repeated."),
    non_goal: list[str] | None = typer.Option(None, "--non-goal", help="Non-goal. Can be repeated."),
    proposal_text: str | None = typer.Option(None, "--proposal", help="Proposed direction"),
    acceptance: list[str] | None = typer.Option(
        None,
        "--acceptance",
        help="Acceptance criterion. Can be repeated.",
    ),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Create a proposal scaffold."""
    workspace = _workspace(root)
    try:
        proposal = workspace.create_proposal_with_details(
            title=title,
            problem=problem,
            context=context,
            goals=goal,
            non_goals=non_goal,
            proposal=proposal_text,
            acceptance_criteria=acceptance,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Proposal created.[/green]")
    console.print(f"  id: {proposal.proposal_id}")
    console.print(f"  slug: {proposal.slug}")
    console.print(f"  path: {proposal.path}")


@proposal_app.command("update")
def proposal_update(
    proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
    problem: str | None = typer.Option(None, "--problem", help="Problem statement"),
    context: str | None = typer.Option(None, "--context", help="Proposal context"),
    goal: list[str] | None = typer.Option(None, "--goal", help="Goal. Can be repeated."),
    non_goal: list[str] | None = typer.Option(None, "--non-goal", help="Non-goal. Can be repeated."),
    proposal_text: str | None = typer.Option(None, "--proposal", help="Proposed direction"),
    acceptance: list[str] | None = typer.Option(
        None,
        "--acceptance",
        help="Acceptance criterion. Can be repeated.",
    ),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Update structured sections in proposal.md."""
    try:
        path = _workspace(root).update_proposal(
            proposal_id=proposal_id,
            problem=problem,
            context=context,
            goals=goal,
            non_goals=non_goal,
            proposal=proposal_text,
            acceptance_criteria=acceptance,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Updated[/green] {path}")


@proposal_app.command("list")
def proposal_list(
    status_filter: str | None = typer.Option(None, "--status", help="Filter by proposal status"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """List proposals with stable, agent-friendly output."""
    proposals = _workspace(root).proposal_summaries(status=status_filter)
    console.print("Proposals")
    if not proposals:
        console.print("  none")
        return
    for proposal in proposals:
        console.print(f"  {proposal.proposal_id}  {proposal.status}  {proposal.title}")


@proposal_app.command("show")
def proposal_show(
    proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show a compact proposal summary."""
    try:
        proposal = _workspace(root).show_proposal(proposal_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"{proposal.proposal_id} - [bold]{proposal.title}[/bold]")
    console.print(f"  status: {proposal.status}")
    console.print(f"  path: {proposal.path}")
    console.print("")
    console.print("Problem:")
    console.print(proposal.problem)
    console.print("")
    console.print("Proposal:")
    console.print(proposal.proposal)
    console.print("")
    console.print("Decision:")
    console.print(f"  status: {proposal.decision_status}")
    console.print(f"  reason: {proposal.decision_reason}")


def _record_proposal_decision(
    proposal_id: str,
    outcome: DecisionOutcome,
    reason: str,
    approver: str,
    root: Path,
) -> None:
    workspace = _workspace(root)
    try:
        decision = workspace.record_decision(
            proposal_id=proposal_id,
            outcome=outcome,
            reason=reason,
            approver=approver,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Proposal decision recorded.[/green]")
    console.print(f"  proposal: {proposal_id}")
    console.print(f"  outcome: {decision.outcome.value}")


@proposal_app.command("accept")
def proposal_accept(
    proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
    reason: str = typer.Option(..., "--reason", help="Decision reason"),
    approver: str = typer.Option("local", "--approver", help="Decision approver"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Accept a proposal."""
    _record_proposal_decision(proposal_id, DecisionOutcome.accepted, reason, approver, root)


@proposal_app.command("reject")
def proposal_reject(
    proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
    reason: str = typer.Option(..., "--reason", help="Decision reason"),
    approver: str = typer.Option("local", "--approver", help="Decision approver"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Reject a proposal."""
    _record_proposal_decision(proposal_id, DecisionOutcome.rejected, reason, approver, root)


@proposal_app.command("defer")
def proposal_defer(
    proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
    reason: str = typer.Option(..., "--reason", help="Decision reason"),
    approver: str = typer.Option("local", "--approver", help="Decision approver"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Defer a proposal."""
    _record_proposal_decision(proposal_id, DecisionOutcome.deferred, reason, approver, root)


@contribution_app.command("add")
def contribution_add(
    proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
    text: str = typer.Argument(..., help="Contribution text"),
    contribution_type: ContributionType = typer.Option(
        ContributionType.suggestion,
        "--type",
        help="Contribution type",
    ),
    relevance: str = typer.Option("medium", "--relevance", help="Relevance hint"),
    author: str = typer.Option("local", "--author", help="Contribution author"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Append a contribution to a proposal."""
    workspace = _workspace(root)
    try:
        contribution = workspace.add_contribution(
            proposal_id=proposal_id,
            contribution_type=contribution_type,
            text=text,
            relevance_hint=relevance,
            author=author,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Contribution added.[/green]")
    console.print(f"  id: {contribution.contribution_id}")
    console.print(f"  proposal: {proposal_id}")


@proposal_contribution_app.command("add")
def proposal_contribution_add(
    proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
    text: str = typer.Argument(..., help="Contribution text"),
    contribution_type: ContributionType = typer.Option(
        ContributionType.suggestion,
        "--type",
        help="Contribution type",
    ),
    relevance: str = typer.Option("medium", "--relevance", help="Relevance hint"),
    author: str = typer.Option("local", "--author", help="Contribution author"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Append a contribution to a proposal."""
    contribution_add(
        proposal_id=proposal_id,
        text=text,
        contribution_type=contribution_type,
        relevance=relevance,
        author=author,
        root=root,
    )


@decision_app.command("record")
def decision_record(
    proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
    outcome: DecisionOutcome = typer.Option(..., "--outcome", help="Decision outcome"),
    reason: str = typer.Option(..., "--reason", help="Decision reason"),
    approver: str = typer.Option("local", "--approver", help="Decision approver"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Record a decision for a proposal."""
    workspace = _workspace(root)
    try:
        decision = workspace.record_decision(
            proposal_id=proposal_id,
            outcome=outcome,
            reason=reason,
            approver=approver,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Decision recorded.[/green]")
    console.print(f"  proposal: {proposal_id}")
    console.print(f"  outcome: {decision.outcome.value}")


@explore_app.command("prompt")
def explore_prompt(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Generate an exploration prompt file."""
    try:
        path = _workspace(root).generate_prompt(proposal_id, "explore")
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Generated[/green] {path}")


@explore_app.command("import")
def explore_import(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    source: Path = typer.Argument(..., help="Exploration output file or artifact directory"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Import exploration output into P2P artifacts."""
    try:
        imported = _workspace(root).import_exploration(proposal_id, source)
    except ValueError as exc:
        _fail(str(exc))
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
        status = _workspace(root).exploration_status(proposal_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"Exploration status for [bold]{status.proposal_id}[/bold]")
    console.print("")
    console.print("Artifacts:")
    for artifact in status.artifacts:
        marker = "[green]✓[/green]" if artifact.has_content else "[red]✗[/red]"
        console.print(f"  {marker} {artifact.filename}")
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
    try:
        path = _workspace(root).generate_prompt(proposal_id, "digest")
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Generated[/green] {path}")


@clarify_app.command("prompt")
def clarify_prompt(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Generate a clarification prompt file."""
    try:
        path = _workspace(root).generate_prompt(proposal_id, "clarify")
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Generated[/green] {path}")


@clarify_app.command("import")
def clarify_import(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    source: Path = typer.Argument(..., help="Clarification output file"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Import clarification output into clarifications.md."""
    try:
        path = _workspace(root).import_artifact(proposal_id, "clarify", source)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Imported[/green] {path}")


@synthesize_app.command("prompt")
def synthesize_prompt(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Generate a proposal synthesis prompt file."""
    try:
        path = _workspace(root).generate_prompt(proposal_id, "synthesize")
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Generated[/green] {path}")


@synthesize_app.command("import")
def synthesize_import(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    source: Path = typer.Argument(..., help="Synthesized proposal.md output file"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Import synthesized proposal output into proposal.md."""
    try:
        path = _workspace(root).import_artifact(proposal_id, "synthesize", source)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Imported[/green] {path}")


@plan_app.command("prompt")
def plan_prompt(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Generate an execution plan prompt file."""
    try:
        path = _workspace(root).generate_prompt(proposal_id, "plan")
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Generated[/green] {path}")


@plan_app.command("import")
def plan_import(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    source: Path = typer.Argument(..., help="Execution plan output file"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Import execution plan output into execution-plan.md."""
    try:
        path = _workspace(root).import_artifact(proposal_id, "plan", source)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Imported[/green] {path}")


@tasks_app.command("prompt")
def tasks_prompt(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Generate a tasks prompt file."""
    try:
        path = _workspace(root).generate_prompt(proposal_id, "tasks")
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Generated[/green] {path}")


@tasks_app.command("import")
def tasks_import(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    source: Path = typer.Argument(..., help="Tasks YAML output file"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Import tasks output into tasks.yml."""
    try:
        path = _workspace(root).import_artifact(proposal_id, "tasks", source)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Imported[/green] {path}")


@governance_app.command("init")
def governance_init(
    mode: str = typer.Option(
        "owner_decides",
        "--mode",
        help="Governance mode: owner_decides, open_consensus, or exclusive_vote",
    ),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Initialize file-based governance artifacts."""
    try:
        created = _workspace(root).init_governance(mode)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Governance initialized.[/green]")
    for path in created:
        console.print(f"  updated {path}")


@governance_app.command("status")
def governance_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Show governance mode and audit artifacts."""
    status = _workspace(root).governance_status()
    console.print("Governance status")
    console.print(f"  mode: {status.mode}")
    console.print(f"  roles: {status.roles_count}")
    console.print(f"  precedents: {status.precedents_count}")
    console.print(f"  file: {status.governance_file}")


@swot_app.command("prompt")
def swot_prompt(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Generate a governance SWOT prompt file."""
    try:
        path = _workspace(root).generate_prompt(proposal_id, "swot")
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Generated[/green] {path}")


@vote_app.command("record")
def vote_record(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    choice: str = typer.Option(..., "--choice", help="Chosen alternative ID or label"),
    reason: str = typer.Option(..., "--reason", help="Reason for the vote"),
    voter: str = typer.Option("local", "--voter", help="Voter identifier"),
    role: str = typer.Option("contributor", "--role", help="Governance role"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Record a governance vote in votes.yml."""
    try:
        status = _workspace(root).record_vote(
            proposal_id=proposal_id,
            choice=choice,
            reason=reason,
            voter=voter,
            role=role,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Vote recorded.[/green]")
    console.print(f"  proposal: {status.proposal_id}")
    console.print(f"  total votes: {status.total_votes}")
    if status.tied:
        console.print("  current result: tied")
    elif status.winner:
        console.print(f"  current winner: {status.winner}")
    else:
        console.print("  current winner: none")


@vote_app.command("status")
def vote_status(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show vote counts for a proposal."""
    try:
        status = _workspace(root).vote_status(proposal_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"Vote status for [bold]{status.proposal_id}[/bold]")
    if not status.counts:
        console.print("  votes: none")
        return
    for choice, count in sorted(status.counts.items()):
        console.print(f"  {choice}: {count}")
    if status.tied:
        console.print("  result: tied")
    elif status.winner:
        console.print(f"  result: {status.winner}")


@precedent_app.command("record")
def precedent_record(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    title: str = typer.Option(..., "--title", help="Precedent title"),
    reason: str = typer.Option(..., "--reason", help="Why this should prevent repeated debate"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Record a reusable decision precedent."""
    try:
        path = _workspace(root).record_precedent(proposal_id, title, reason)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Precedent recorded[/green] {path}")


@project_app.command("refresh")
def project_refresh(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Refresh .p2p/project from accepted proposals."""
    try:
        written = _workspace(root).refresh_project_state()
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Project state refreshed.[/green]")
    for path in written:
        console.print(f"  updated {path}")


@project_app.command("status")
def project_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Show rationalized project state status."""
    status = _workspace(root).project_state_status()
    console.print("Project state")
    console.print(f"  directory: {status.project_dir}")
    console.print(f"  accepted proposals: {status.accepted_proposals}")
    if not status.features:
        console.print("  features: none")
    else:
        console.print("  features:")
        for feature in status.features:
            console.print(f"    - {feature}")
    console.print("  operational:")
    console.print(
        "    brief: "
        + ("available" if status.operational_brief_available else "missing")
    )
    console.print(f"    next actions: {status.next_actions_count}")
    if status.first_next_action:
        console.print(
            "    first next: "
            f"{status.first_next_action.action_id} "
            f"{status.first_next_action.priority} "
            f"{status.first_next_action.kind} "
            f"{status.first_next_action.target}"
        )
        console.print(f"    command: {status.first_next_action.command or 'none'}")


@project_app.command("show")
def project_show(
    section: str = typer.Argument("overview", help="overview, problem, scope, swot, or feature id"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Print a generated project-state section."""
    try:
        content = _workspace(root).show_project_state(section)
    except ValueError as exc:
        _fail(str(exc))
    console.print(content)


@project_remote_app.command("show")
def project_remote_show(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Show local/remote project profile."""
    try:
        profile = _workspace(root).remote_profile()
    except ValueError as exc:
        _fail(str(exc))
    console.print("Project remote profile")
    console.print(f"  mode: {profile.mode}")
    console.print(f"  provider: {profile.provider}")
    console.print(f"  remote: {profile.remote or 'none'}")
    console.print(f"  url: {profile.url or 'none'}")
    console.print(f"  review_request: {profile.review_request_mode}")
    console.print(f"  opens_external_request: {str(profile.opens_external_request).lower()}")
    console.print(f"  path: {profile.path}")


@project_remote_app.command("configure")
def project_remote_configure(
    mode: str = typer.Option(..., "--mode", help="Project remote mode: local or remote"),
    provider: str | None = typer.Option(None, "--provider", help="Provider: generic, github, or gitlab"),
    remote: str = typer.Option("origin", "--remote", help="Git remote name for remote-backed projects"),
    url: str | None = typer.Option(None, "--url", help="Remote repository URL"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Configure local/remote project profile without creating provider resources."""
    try:
        profile = _workspace(root).configure_remote_profile(
            mode=mode,
            provider=provider,
            remote=remote,
            url=url,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Project remote profile configured.[/green]")
    console.print(f"  mode: {profile.mode}")
    console.print(f"  provider: {profile.provider}")
    console.print(f"  remote: {profile.remote or 'none'}")
    console.print(f"  url: {profile.url or 'none'}")
    console.print("  creates_remote_repository: false")
    console.print("  opens_external_request: false")


@project_brief_app.command("prompt")
def project_brief_prompt(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Create an operational brief prompt from project state and registries."""
    try:
        prompt = _workspace(root).create_project_brief_prompt()
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Project brief prompt created.[/green]")
    console.print(f"  context: {prompt.context_path}")
    console.print(f"  prompt: {prompt.prompt_path}")


@project_brief_app.command("import")
def project_brief_import(
    source: Path = typer.Argument(..., help="File or directory containing operational brief output"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Import a human or AI operational project brief."""
    try:
        imported = _workspace(root).import_project_brief(source)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Project brief imported.[/green]")
    for path in imported:
        console.print(f"  updated {path}")


@project_brief_app.command("show")
def project_brief_show(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Print the stored operational project brief."""
    try:
        content = _workspace(root).show_project_brief()
    except ValueError as exc:
        _fail(str(exc))
    console.print(content)


@impact_app.command("prompt")
def impact_prompt(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Generate an impact-analysis prompt file."""
    try:
        path = _workspace(root).generate_prompt(proposal_id, "impact")
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"[green]Generated[/green] {path}")


@impact_app.command("import")
def impact_import(
    proposal_id: str = typer.Argument(..., help="Proposal ID"),
    source: Path = typer.Argument(..., help="Impact output file or artifact directory"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Import impact artifacts into a proposal."""
    try:
        imported = _workspace(root).import_impact(proposal_id, source)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Impact imported.[/green]")
    for path in imported:
        console.print(f"  updated {path}")


@conflict_app.command("record")
def conflict_record(
    proposal_ids: list[str] = typer.Argument(..., help="Two or more proposal IDs"),
    conflict_type: str = typer.Option("overlaps", "--type", help="Conflict relationship type"),
    reason: str = typer.Option(..., "--reason", help="Why these proposals conflict or overlap"),
    winner: str | None = typer.Option(None, "--winner", help="Winning proposal if decided"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Record conflict memory in .p2p/project/conflicts.yml."""
    try:
        status = _workspace(root).record_conflict(
            proposals=proposal_ids,
            conflict_type=conflict_type,
            reason=reason,
            winner=winner,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Conflict recorded.[/green]")
    console.print(f"  conflicts: {status.conflicts_count}")
    console.print(f"  file: {status.conflicts_file}")


@conflict_app.command("status")
def conflict_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Show recorded project conflicts."""
    try:
        status = _workspace(root).conflict_status()
    except ValueError as exc:
        _fail(str(exc))
    console.print("Project conflicts")
    console.print(f"  file: {status.conflicts_file}")
    if not status.conflicts:
        console.print("  conflicts: none")
        return
    for conflict in status.conflicts:
        proposals = ", ".join(str(item) for item in conflict.get("proposals", []))
        console.print(f"  {conflict.get('id')}: {conflict.get('type')} [{proposals}]")


@change_app.command("create")
def change_create(
    source: str = typer.Option(..., "--from", help="Accepted proposal ID, e.g. PROP-013"),
    title: str | None = typer.Option(None, "--title", help="Optional Change Set title"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Create metadata-only Change Set from accepted project intent."""
    try:
        change = _workspace(root).create_change_set(source=source, title=title)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Change Set created.[/green]")
    console.print(f"  id: {change.change_id}")
    console.print(f"  status: {change.status}")
    console.print(f"  path: {change.path}")


@change_app.command("status")
def change_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """List Change Sets and lifecycle states."""
    changes = _workspace(root).change_set_statuses()
    console.print("Change Sets")
    if not changes:
        console.print("  none")
        return
    for change in changes:
        console.print(f"  {change.change_id}  {change.status}  {change.title}")


@change_app.command("policy")
def change_policy(
    change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show managed Git policy for a Change Set."""
    try:
        policy = _workspace(root).change_set_policy(change_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"Git policy for [bold]{policy.change_id}[/bold]")
    console.print(f"  operation_level: {policy.operation_level}")
    console.print(f"  auto_commit: {policy.auto_commit}")
    console.print(f"  auto_branch: {policy.auto_branch}")
    console.print(f"  auto_tag: {policy.auto_tag}")
    console.print("  reasons:")
    for reason in policy.reasons:
        console.print(f"    - {reason}")


@change_app.command("show")
def change_show(
    change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show a Change Set summary."""
    try:
        change = _workspace(root).show_change_set(change_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"{change.change_id} - [bold]{change.title}[/bold]")
    console.print(f"  status: {change.status}")
    console.print(f"  path: {change.path}")
    console.print(f"  execution_domains: {', '.join(change.execution_domains) or 'none'}")
    console.print(f"  implementation_targets: {', '.join(change.implementation_targets) or 'none'}")
    console.print(f"  spec_targets: {', '.join(change.spec_targets) or 'none'}")
    console.print(f"  export_targets: {', '.join(change.export_targets) or 'none'}")
    console.print(f"  plan: {change.plan_ref}")
    console.print(f"  tasks: {change.tasks_ref}")
    console.print("")
    console.print(change.summary)


@change_app.command("set-status")
def change_set_status(
    change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
    status: str = typer.Argument(..., help="New lifecycle status"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Update a Change Set lifecycle status."""
    try:
        change = _workspace(root).update_change_set_status(change_id, status)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Change Set status updated.[/green]")
    console.print(f"  id: {change.change_id}")
    console.print(f"  status: {change.status}")


@change_app.command("tasks")
def change_tasks(
    change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show Change Set tasks and actions."""
    try:
        view = _workspace(root).change_set_tasks(change_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"Tasks for [bold]{view.change_id}[/bold]")
    if not view.tasks:
        console.print("  tasks: none")
    else:
        for task in view.tasks:
            console.print(f"  {task.get('id', '-')}: {task.get('status', 'unknown')}  {task.get('title', '')}")
    if not view.actions:
        console.print("  actions: none")
    else:
        console.print("Actions:")
        for action in view.actions:
            checked = "x" if action.get("checked") else " "
            console.print(
                f"  [{checked}] {action.get('id', '-')}: {action.get('title', '')}",
                markup=False,
            )


@spec_app.command("refresh")
def spec_refresh(
    change: str = typer.Option(..., "--change", help="Change Set ID, e.g. CHANGE-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Generate a deterministic P2P-native software spec from a Change Set."""
    try:
        status = _workspace(root).refresh_software_spec(change)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Software spec refreshed.[/green]")
    console.print(f"  change: {status.change_id}")
    console.print(f"  status: {status.status}")
    console.print(f"  path: {status.path}")


@spec_app.command("status")
def spec_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """List generated software specs."""
    specs = _workspace(root).software_spec_statuses()
    console.print("Software Specs")
    if not specs:
        console.print("  none")
        return
    for spec in specs:
        console.print(f"  {spec.change_id}  {spec.status}  {spec.title}")


@spec_app.command("show")
def spec_show(
    change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show a generated software spec index."""
    try:
        content = _workspace(root).show_software_spec(change_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print(content)


@spec_app.command("prompt")
def spec_prompt(
    change: str = typer.Option(..., "--change", help="Change Set ID, e.g. CHANGE-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Generate a prompt for AI/human software spec refinement."""
    try:
        prompt = _workspace(root).create_software_spec_prompt(change)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Software spec prompt created.[/green]")
    console.print(f"  change: {prompt.change_id}")
    console.print(f"  prompt: {prompt.prompt_path}")


@spec_app.command("import")
def spec_import(
    change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
    source: Path = typer.Argument(..., help="Directory containing refined software spec artifacts"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Import a validated refined software spec."""
    try:
        imported = _workspace(root).import_software_spec(change_id, source)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Software spec imported.[/green]")
    for path in imported:
        console.print(f"  updated {path}")


@spec_app.command("export")
def spec_export(
    change: str = typer.Option(..., "--change", help="Change Set ID, e.g. CHANGE-001"),
    target: str = typer.Option(..., "--target", help="Export target: generic, openspec, or speckit"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Export a P2P-native software spec to a downstream bundle."""
    try:
        status = _workspace(root).export_software_spec(change, target)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Software spec exported.[/green]")
    console.print(f"  change: {status.change_id}")
    console.print(f"  target: {status.target}")
    console.print(f"  status: {status.status}")
    console.print(f"  path: {status.path}")


@spec_app.command("export-status")
def spec_export_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """List generated software spec export bundles."""
    exports = _workspace(root).software_spec_export_statuses()
    console.print("Software Spec Exports")
    if not exports:
        console.print("  none")
        return
    for export in exports:
        console.print(f"  {export.change_id}  {export.target}  {export.status}  {export.title}")


@spec_app.command("export-show")
def spec_export_show(
    change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
    target: str = typer.Option(..., "--target", help="Export target: generic, openspec, or speckit"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show a software spec export index."""
    try:
        content = _workspace(root).show_software_spec_export(change_id, target)
    except ValueError as exc:
        _fail(str(exc))
    console.print(content)


@spec_app.command("export-validate")
def spec_export_validate(
    change_id: str = typer.Argument(..., help="Change Set ID, e.g. CHANGE-001"),
    target: str = typer.Option(..., "--target", help="Export target: generic, openspec, or speckit"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Validate an existing software spec export bundle."""
    try:
        validation = _workspace(root).validate_software_spec_export(change_id, target)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Software spec export valid.[/green]")
    console.print(f"  change: {validation.change_id}")
    console.print(f"  target: {validation.target}")
    console.print(f"  path: {validation.path}")
    console.print("  checked:")
    for path in validation.checked:
        console.print(f"    ✓ {path}")


@work_app.command("plan")
def work_plan(
    change: str = typer.Option(..., "--change", help="Change Set ID, e.g. CHANGE-001"),
    target: str = typer.Option(..., "--target", help="Validated export target: generic, openspec, or speckit"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Create a P2P Work handoff manifest without creating Git branches or commits."""
    try:
        work = _workspace(root).create_work_plan(change, target)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Work plan created.[/green]")
    console.print(f"  work: {work.work_id}")
    console.print(f"  status: {work.status}")
    console.print(f"  change: {work.change_id}")
    console.print(f"  target: {work.target}")
    console.print(f"  branch: {work.branch_name}")
    console.print(f"  path: {work.path}")


@work_app.command("list")
def work_list(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """List P2P Work manifests."""
    works = _workspace(root).work_statuses()
    console.print("Work items")
    if not works:
        console.print("  none")
        return
    for work in works:
        console.print(f"  {work.work_id}  {work.status}  {work.change_id}  {work.target}")


@work_app.command("status")
def work_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Show an operational read-only summary of P2P Work items."""
    works = _workspace(root).work_summaries()
    console.print("Work status")
    if not works:
        console.print("  none")
        return
    for work in works:
        console.print(f"{work.work_id}  {work.status}")
        console.print(f"  change: {work.change_id}")
        console.print(f"  target: {work.target}")
        console.print(f"  branch: {work.branch_name or 'none'}")
        console.print(f"  base: {work.base_branch}")
        if work.remote:
            console.print(f"  remote: {work.remote}")
        console.print(f"  next: {work.next_action}")
        console.print(f"  note: {work.note}")


@work_app.command("scan")
def work_scan(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Scan local P2P-managed work branches without checkout."""
    scan = _workspace(root).scan_work_branches()
    console.print("Work branch scan")
    console.print(f"  branches: {len(scan.scanned_branches)}")
    console.print(f"  work_items: {len(scan.work_items)}")
    console.print(f"  registry: {scan.path}")
    for item in scan.work_items:
        console.print(
            f"  {item.get('work_id')}  {item.get('status')}  {item.get('change')}  "
            f"{item.get('target')}  {item.get('branch')}"
        )


@work_app.command("branch")
def work_branch(
    work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Create and switch to the P2P-managed branch for a planned Work item."""
    try:
        branch = _workspace(root).branch_work(work_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Managed work branch created.[/green]")
    console.print(f"  work: {branch.work_id}")
    console.print(f"  branch: {branch.branch_name}")
    console.print(f"  base: {branch.base_branch}")
    console.print(f"  base_commit: {branch.base_commit}")
    console.print(f"  path: {branch.path}")
    console.print("  commits: disabled")
    console.print("  merge: owner-controlled")


@work_app.command("retire")
def work_retire(
    work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
    reason: str = typer.Option(..., "--reason", help="Why this planned Work item is obsolete"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Retire an obsolete planned Work manifest without touching Git branches."""
    try:
        retired = _workspace(root).retire_work(work_id, reason)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Managed work retired.[/green]")
    console.print(f"  work: {retired.work_id}")
    console.print(f"  status: {retired.status}")
    console.print(f"  reason: {retired.reason}")
    console.print(f"  path: {retired.path}")
    console.print("  git: unchanged")


@work_app.command("submit")
def work_submit(
    work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Create a local managed submit commit for a branched Work item."""
    try:
        submit = _workspace(root).submit_work(work_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Managed work submitted.[/green]")
    console.print(f"  work: {submit.work_id}")
    console.print(f"  branch: {submit.branch_name}")
    console.print(f"  commit: {submit.commit}")
    console.print(f"  changed_files: {len(submit.changed_files)}")
    for path in submit.changed_files:
        console.print(f"    {path}")
    console.print("  push: disabled")
    console.print("  merge: owner-controlled")


@work_app.command("review")
def work_review(
    work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Request local owner review for a submitted Work item."""
    try:
        review = _workspace(root).review_work(work_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Managed work review requested.[/green]")
    console.print(f"  work: {review.work_id}")
    console.print(f"  branch: {review.branch_name}")
    console.print(f"  review_commit: {review.review_commit}")
    console.print(f"  metadata_commit: {review.metadata_commit}")
    console.print("  push: disabled")
    console.print("  pull_request: disabled")
    console.print("  merge: owner-controlled")


@work_app.command("publish")
def work_publish(
    work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
    remote: str = typer.Option("origin", "--remote", help="Git remote to publish the managed branch to"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Publish a reviewed managed Work branch to a remote without opening a PR or merging."""
    try:
        publish = _workspace(root).publish_work(work_id, remote)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Managed work published.[/green]")
    console.print(f"  work: {publish.work_id}")
    console.print(f"  branch: {publish.branch_name}")
    console.print(f"  remote: {publish.remote}")
    console.print(f"  remote_url: {publish.remote_url}")
    console.print(f"  publish_commit: {publish.publish_commit}")
    console.print("  pull_request: disabled")
    console.print("  merge: owner-controlled")


@work_app.command("request-review")
def work_request_review(
    work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
    provider: str | None = typer.Option(None, "--provider", help="External provider: generic, github, or gitlab"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Record provider-agnostic external review handoff for a published Work item."""
    try:
        review = _workspace(root).request_external_work_review(work_id, provider)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]External review request recorded.[/green]")
    console.print(f"  work: {review.work_id}")
    console.print(f"  branch: {review.branch_name}")
    console.print(f"  provider: {review.provider}")
    console.print(f"  remote: {review.remote}")
    console.print(f"  remote_url: {review.remote_url}")
    console.print(f"  metadata_commit: {review.metadata_commit}")
    console.print("  opens_external_request: false")
    console.print("  merge: owner-controlled")
    console.print(f"  suggested_next: {review.suggested_next}")


@work_app.command("accept")
def work_accept(
    work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
    continue_: bool = typer.Option(False, "--continue", help="Continue accept after manual conflict resolution"),
    abort: bool = typer.Option(False, "--abort", help="Abort a conflicted accept merge"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Accept a published Work item by merging its managed branch into the base branch locally."""
    if continue_ and abort:
        _fail("Use either --continue or --abort, not both.")
    try:
        if continue_:
            accept = _workspace(root).continue_accept_work(work_id)
        elif abort:
            work = _workspace(root).abort_accept_work(work_id)
            console.print("[yellow]Managed work accept aborted.[/yellow]")
            console.print(f"  work: {work.work_id}")
            console.print(f"  status: {work.status}")
            console.print(f"  branch: {work.branch_name}")
            return
        else:
            accept = _workspace(root).accept_work(work_id)
    except ValueError as exc:
        _fail(str(exc))
    if isinstance(accept, WorkAcceptConflict):
        console.print("[yellow]Managed work accept blocked by merge conflicts.[/yellow]")
        console.print(f"  work: {accept.work_id}")
        console.print(f"  source_branch: {accept.branch_name}")
        console.print(f"  base: {accept.base_branch}")
        console.print("  conflicts:")
        for path in accept.conflicted_files:
            console.print(f"    {path}")
        console.print(f"  continue: p2p work accept --continue {accept.work_id}")
        console.print(f"  abort: p2p work accept --abort {accept.work_id}")
        raise typer.Exit(1)
    console.print("[green]Managed work accepted.[/green]")
    console.print(f"  work: {accept.work_id}")
    console.print(f"  source_branch: {accept.branch_name}")
    console.print(f"  merged_into: {accept.base_branch}")
    console.print(f"  merge_commit: {accept.merge_commit}")
    console.print("  push: disabled")
    console.print("  cleanup: disabled")


@work_app.command("finalize")
def work_finalize(
    work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
    remote: str = typer.Option("origin", "--remote", help="Git remote to push the base branch to"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Finalize an accepted Work item by pushing the base branch to a remote."""
    try:
        finalize = _workspace(root).finalize_work(work_id, remote)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Managed work finalized.[/green]")
    console.print(f"  work: {finalize.work_id}")
    console.print(f"  base_branch: {finalize.base_branch}")
    console.print(f"  remote: {finalize.remote}")
    console.print(f"  remote_url: {finalize.remote_url}")
    console.print(f"  finalize_commit: {finalize.finalize_commit}")
    console.print("  cleanup: disabled")


@work_app.command("cleanup")
def work_cleanup(
    work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
    delete_remote: bool = typer.Option(False, "--remote", help="Also delete the remote managed Work branch"),
    remote: str = typer.Option("origin", "--remote-name", help="Git remote used for cleanup metadata and optional branch deletion"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Clean up finalized managed Work branches."""
    try:
        cleanup = _workspace(root).cleanup_work(work_id, delete_remote=delete_remote, remote=remote)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Managed work cleaned.[/green]")
    console.print(f"  work: {cleanup.work_id}")
    console.print(f"  branch: {cleanup.branch_name}")
    console.print(f"  base_branch: {cleanup.base_branch}")
    console.print(f"  remote: {cleanup.remote}")
    console.print(f"  cleanup_commit: {cleanup.cleanup_commit}")
    console.print(f"  local_deleted: {str(cleanup.local_deleted).lower()}")
    console.print(f"  remote_deleted: {str(cleanup.remote_deleted).lower()}")


@work_app.command("show")
def work_show(
    work_id: str = typer.Argument(..., help="Work ID, e.g. WORK-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show a P2P Work manifest."""
    try:
        work = _workspace(root).show_work(work_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"{work.work_id} - {work.status}")
    console.print(f"  change: {work.change_id}")
    console.print(f"  target: {work.target}")
    console.print(f"  branch: {work.branch_name}")
    console.print(f"  path: {work.path}")
    console.print(_yaml_dump_for_cli(work.manifest))


@registry_app.command("refresh")
def registry_refresh(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Regenerate typed project registries from P2P source artifacts."""
    try:
        written = _workspace(root).refresh_registries()
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Registries refreshed.[/green]")
    for path in written:
        console.print(f"  updated {path}")


@registry_app.command("status")
def registry_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Show generated registry availability and basic freshness checks."""
    try:
        status = _workspace(root).registry_status()
    except ValueError as exc:
        _fail(str(exc))
    console.print("Registry status")
    console.print(f"  path: {status.registries_dir}")
    console.print(f"  source proposals: {status.proposals_count}")
    console.print(f"  source changes: {status.changes_count}")
    console.print(f"  stale: {status.stale}")
    console.print("  files:")
    for file in status.files:
        marker = "✓" if file["exists"] and file["generated"] else "✗"
        console.print(f"    {marker} {file['name']} ({file['records']} records)")


@registry_app.command("show")
def registry_show(
    name: str = typer.Argument(..., help="Registry name: proposals, decisions, changes, choices, relations, artifacts"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show a generated registry."""
    try:
        view = _workspace(root).show_registry(name)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"Registry: [bold]{view.name}[/bold]")
    console.print(f"  path: {view.path}")
    if not view.records:
        console.print("  records: none")
        return
    for record in view.records:
        if view.name in {"proposals", "changes"}:
            console.print(
                f"  {record.get('id', '-')}: {record.get('status', 'unknown')}  {record.get('title', '')}"
            )
        elif view.name == "decisions":
            console.print(
                f"  {record.get('proposal', '-')}: {record.get('outcome', 'unknown')}  {record.get('title', '')}"
            )
        elif view.name == "relations":
            console.print(
                f"  {record.get('source', '-')} -> {record.get('target', '-')}  {record.get('type', '')}"
            )
        elif view.name == "choices":
            selected = f" -> {record.get('selected_option')}" if record.get("selected_option") else ""
            title = record.get("title") or record.get("proposal", "")
            console.print(f"  {record.get('id', '-')}: {record.get('status', 'unknown')}  {title}{selected}")
        elif view.name == "artifacts":
            console.print(
                f"  {record.get('owner_type', '-')}/{record.get('owner', '-')}: {record.get('path', '')}"
            )
        else:
            console.print(f"  {record}")


@intake_app.command("prompt")
def intake_prompt(
    idea: str = typer.Argument(..., help="Raw idea or observation to analyze"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Create an intake prompt backed by generated project registries."""
    try:
        prompt = _workspace(root).create_intake_prompt(idea)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Intake prompt created.[/green]")
    console.print(f"  id: {prompt.intake_id}")
    console.print(f"  path: {prompt.path}")
    console.print(f"  prompt: {prompt.prompt_path}")


@intake_app.command("import")
def intake_import(
    intake_id: str = typer.Argument(..., help="Intake ID, e.g. INTAKE-001"),
    source: Path = typer.Argument(..., help="File or directory containing intake output"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Import human or AI intake analysis output."""
    try:
        imported = _workspace(root).import_intake(intake_id, source)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Intake imported.[/green]")
    for path in imported:
        console.print(f"  updated {path}")


@intake_app.command("status")
def intake_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """List intake records and analysis state."""
    try:
        statuses = _workspace(root).intake_statuses()
    except ValueError as exc:
        _fail(str(exc))
    console.print("Intake records")
    if not statuses:
        console.print("  none")
        return
    for status in statuses:
        console.print(f"  {status.intake_id}  {status.status}  {status.path}")


@intake_apply_app.command("plan")
def intake_apply_plan(
    intake_id: str = typer.Argument(..., help="Intake ID, e.g. INTAKE-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Create a controlled intake apply plan."""
    try:
        plan = _workspace(root).create_intake_apply_plan(intake_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Intake apply plan created.[/green]")
    console.print(f"  intake: {plan.intake_id}")
    console.print(f"  path: {plan.path}")
    console.print(f"  actions: {len(plan.actions)}")


@intake_apply_app.command("show")
def intake_apply_show(
    intake_id: str = typer.Argument(..., help="Intake ID, e.g. INTAKE-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show a controlled intake apply plan."""
    try:
        plan = _workspace(root).show_intake_apply_plan(intake_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"Intake apply plan {plan.intake_id}")
    console.print(f"  path: {plan.path}")
    if not plan.actions:
        console.print("  actions: none")
        return
    for action in plan.actions:
        console.print(
            f"  {action.get('id')}  {action.get('status')}  "
            f"{action.get('support')}  {action.get('type')} -> {action.get('target')}"
        )
        console.print(f"    reason: {action.get('reason') or ''}")
        console.print(f"    command: {action.get('command_preview') or 'none'}")


@intake_apply_app.command("run")
def intake_apply_run(
    intake_id: str = typer.Argument(..., help="Intake ID, e.g. INTAKE-001"),
    action: str = typer.Option(..., "--action", help="Apply action ID, e.g. APPLY-001"),
    option: list[str] | None = typer.Option(None, "--option", help="Choice option. Can be repeated."),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Run one explicit supported intake apply action."""
    try:
        applied = _workspace(root).run_intake_apply_action(intake_id, action, option)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Intake apply action applied.[/green]")
    console.print(f"  id: {applied.applied_id}")
    console.print(f"  action: {applied.plan_action}")
    console.print(f"  type: {applied.action_type}")
    console.print(f"  target: {applied.target}")
    console.print(f"  log: {applied.path}")


@choice_app.command("create")
def choice_create(
    title: str = typer.Option(..., "--title", help="Choice title"),
    option: list[str] = typer.Option(..., "--option", help="Choice option. Can be repeated."),
    related: list[str] | None = typer.Option(None, "--related", help="Related proposal ID. Can be repeated."),
    source: str | None = typer.Option(None, "--source", help="Source artifact, e.g. INTAKE-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Create a project choice with multiple options."""
    try:
        choice = _workspace(root).create_choice(
            title=title,
            options=option,
            related=related,
            source=source,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Choice created.[/green]")
    console.print(f"  id: {choice.choice_id}")
    console.print(f"  status: {choice.status}")
    console.print(f"  path: {choice.path}")


@choice_app.command("list")
def choice_list(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """List project choices."""
    try:
        choices = _workspace(root).choice_statuses()
    except ValueError as exc:
        _fail(str(exc))
    console.print("Choices")
    if not choices:
        console.print("  none")
        return
    for choice in choices:
        selected = f" -> {choice.selected_option}" if choice.selected_option else ""
        console.print(f"  {choice.choice_id}  {choice.status}  {choice.title}{selected}")


@choice_app.command("status")
def choice_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """List project choices and proposal-local choice candidates."""
    workspace = _workspace(root)
    try:
        choices = workspace.choice_statuses()
        findings = workspace.discover_choices()
    except ValueError as exc:
        _fail(str(exc))
    console.print("Choice status")
    console.print("  project choices:")
    if choices:
        for choice in choices:
            selected = f" -> {choice.selected_option}" if choice.selected_option else ""
            console.print(f"    {choice.choice_id}  {choice.status}  {choice.title}{selected}")
    else:
        console.print("    none")
    candidates = [finding for finding in findings if finding.kind == "proposal_local_choice_candidate"]
    console.print("  proposal-local candidates:")
    if candidates:
        for finding in candidates:
            console.print(f"    {finding.target}  {finding.severity}  {finding.reason}")
    else:
        console.print("    none")


@choice_app.command("show")
def choice_show(
    choice_id: str = typer.Argument(..., help="Choice ID, e.g. CHOICE-001"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Show project choice details."""
    try:
        choice = _workspace(root).show_choice(choice_id)
    except ValueError as exc:
        _fail(str(exc))
    console.print(f"{choice.choice_id} - [bold]{choice.title}[/bold]")
    console.print(f"  status: {choice.status}")
    console.print(f"  path: {choice.path}")
    console.print(f"  selected: {choice.selected_option or 'none'}")
    console.print("  options:")
    if choice.options:
        for option in choice.options:
            console.print(
                f"    {option.get('id', '-')}: {option.get('status', 'unknown')}  {option.get('title', '')}"
            )
    else:
        console.print("    none")
    console.print("  blocks:")
    active_blocks = [
        block
        for block in choice.blocks
        if isinstance(block, dict) and block.get("status", "active") == "active"
    ]
    if active_blocks:
        for block in active_blocks:
            console.print(
                f"    {block.get('target_type', 'target')} {block.get('target', '-')}  "
                f"{block.get('status', 'active')}  {block.get('reason', '')}"
            )
    else:
        console.print("    none")


@choice_app.command("discover")
def choice_discover(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
    """Discover advisory choice findings without modifying state."""
    try:
        findings = _workspace(root).discover_choices()
    except ValueError as exc:
        _fail(str(exc))
    console.print("Choice discovery")
    if not findings:
        console.print("  none")
        return
    for finding in findings:
        console.print(f"  {finding.finding_id}  {finding.severity}  {finding.kind}  {finding.target}")
        console.print(f"    reason: {finding.reason}")
        console.print(f"    command: {finding.suggested_command}")


@choice_app.command("block")
def choice_block(
    choice_id: str = typer.Argument(..., help="Choice ID, e.g. CHOICE-001"),
    change: str | None = typer.Option(None, "--change", help="Change Set blocked by this choice"),
    proposal: str | None = typer.Option(None, "--proposal", help="Proposal blocked by this choice"),
    reason: str = typer.Option(..., "--reason", help="Why the choice blocks the target"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Record an explicit active choice blocker."""
    if bool(change) == bool(proposal):
        _fail("Provide exactly one of --change or --proposal.")
    target = change or proposal or ""
    target_type = "change" if change else "proposal"
    try:
        choice = _workspace(root).block_choice(choice_id, target, target_type, reason)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Choice blocker recorded.[/green]")
    console.print(f"  choice: {choice.choice_id}")
    console.print(f"  {target_type}: {target}")


@choice_app.command("unblock")
def choice_unblock(
    choice_id: str = typer.Argument(..., help="Choice ID, e.g. CHOICE-001"),
    change: str | None = typer.Option(None, "--change", help="Change Set to unblock"),
    proposal: str | None = typer.Option(None, "--proposal", help="Proposal to unblock"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Deactivate an explicit choice blocker."""
    if bool(change) == bool(proposal):
        _fail("Provide exactly one of --change or --proposal.")
    target = change or proposal or ""
    target_type = "change" if change else "proposal"
    try:
        choice = _workspace(root).unblock_choice(choice_id, target, target_type)
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Choice blocker cleared.[/green]")
    console.print(f"  choice: {choice.choice_id}")
    console.print(f"  {target_type}: {target}")


@choice_app.command("decide")
def choice_decide(
    choice_id: str = typer.Argument(..., help="Choice ID, e.g. CHOICE-001"),
    option: str = typer.Option(..., "--option", help="Option ID or title to select"),
    reason: str = typer.Option(..., "--reason", help="Decision rationale"),
    decider: str = typer.Option("local", "--decider", help="Decision actor"),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Decide a project choice."""
    try:
        choice = _workspace(root).decide_choice(
            choice_id=choice_id,
            option=option,
            reason=reason,
            decider=decider,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]Choice decided.[/green]")
    console.print(f"  id: {choice.choice_id}")
    console.print(f"  status: {choice.status}")
    console.print(f"  selected: {choice.selected_option}")


if __name__ == "__main__":
    app()

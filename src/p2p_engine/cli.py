from __future__ import annotations

import shlex
from pathlib import Path

import typer

from p2p_engine.cli_commands.agents import register_agent_commands
from p2p_engine.cli_commands.collaboration import register_collaboration_commands
from p2p_engine.cli_commands.doctor import register_doctor_commands
from p2p_engine.cli_commands.next_actions import register_next_commands
from p2p_engine.cli_commands.project_ops import register_project_ops_commands
from p2p_engine.cli_commands.project_status import register_project_status_commands
from p2p_engine.cli_commands.prompts import register_prompt_commands
from p2p_engine.cli_commands.proposals import register_proposal_commands
from p2p_engine.cli_commands.work_specs import register_work_spec_commands
from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail as _fail
from p2p_engine.cli_shared import workspace as _workspace
from p2p_engine.storage.filesystem import P2PWorkspace

app = typer.Typer(help="P2P Engine CLI")
proposal_app = typer.Typer(help="Manage proposals")
proposal_readiness_app = typer.Typer(help="Inspect proposal readiness")
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
project_rubrics_app = typer.Typer(help="Manage project definition rubrics")
impact_app = typer.Typer(help="Analyze proposal impact")
conflict_app = typer.Typer(help="Record and inspect project conflicts")
change_app = typer.Typer(help="Manage operational Change Set metadata")
spec_app = typer.Typer(help="Generate and refine P2P-native software specs")
registry_app = typer.Typer(help="Manage generated project registries")
intake_app = typer.Typer(help="Analyze raw ideas against project context")
intake_apply_app = typer.Typer(help="Plan and run controlled intake applications")
choice_app = typer.Typer(help="Manage project choices")
work_app = typer.Typer(help="Manage P2P work manifests")
sync_app = typer.Typer(help="Synchronize P2P projects through managed Git operations")
permissions_app = typer.Typer(help="Manage project-declared permission identities")
permissions_actor_app = typer.Typer(help="Manage permission actors")
consent_app = typer.Typer(help="Manage permission-gated consent receipts")
agent_app = typer.Typer(help="Manage agent-facing project instructions")
agent_instructions_app = typer.Typer(help="Generate and refresh agent instructions")
assess_app = typer.Typer(help="Assess project readiness and maturity")
assess_maturity_app = typer.Typer(help="Assess project definition maturity")
next_app = typer.Typer(help="Manage advisory next actions", invoke_without_command=True)

proposal_app.add_typer(proposal_readiness_app, name="readiness")
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
app.add_typer(sync_app, name="sync")
app.add_typer(permissions_app, name="permissions")
app.add_typer(consent_app, name="consent")
app.add_typer(agent_app, name="agent")
app.add_typer(assess_app, name="assess")
app.add_typer(next_app, name="next")
project_app.add_typer(project_brief_app, name="brief")
project_app.add_typer(project_remote_app, name="remote")
project_app.add_typer(project_rubrics_app, name="rubrics")
assess_app.add_typer(assess_maturity_app, name="maturity")
intake_app.add_typer(intake_apply_app, name="apply")
agent_app.add_typer(agent_instructions_app, name="instructions")
permissions_app.add_typer(permissions_actor_app, name="actor")

register_doctor_commands(app, agent_app)
register_agent_commands(agent_app, agent_instructions_app)
register_next_commands(next_app)
register_project_status_commands(app, assess_app, assess_maturity_app)
register_proposal_commands(
    proposal_app,
    proposal_readiness_app,
    proposal_contribution_app,
    contribution_app,
    decision_app,
)
register_prompt_commands(
    explore_app,
    digest_app,
    clarify_app,
    synthesize_app,
    plan_app,
    tasks_app,
    swot_app,
)
register_project_ops_commands(
    project_app,
    project_remote_app,
    project_rubrics_app,
    project_brief_app,
    sync_app,
    permissions_app,
    permissions_actor_app,
    consent_app,
)
register_work_spec_commands(change_app, spec_app, work_app)
register_collaboration_commands(
    governance_app,
    vote_app,
    precedent_app,
    impact_app,
    conflict_app,
    registry_app,
    intake_app,
    intake_apply_app,
    choice_app,
)


@app.command()
def init(
    name: str | None = typer.Argument(None, help="Project name"),
    agent: list[str] | None = typer.Option(
        None,
        "--agent",
        help="Initial agent adapter. Repeat for a narrowed install set. Defaults to all built-in adapters.",
    ),
    repository: str = typer.Option(
        "local",
        "--repository",
        help="Repository mode: local or cloud",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Cloud remote provider: generic, github, or gitlab",
    ),
    remote: str = typer.Option(
        "origin",
        "--remote",
        help="Git remote name for cloud-backed projects",
    ),
    remote_url: str | None = typer.Option(
        None,
        "--remote-url",
        help="Remote repository URL for cloud-backed projects",
    ),
    domain: str = typer.Option(
        "none",
        "--domain",
        help="Domain template: none, custom, generic, software, grant_document, or board_game",
    ),
    owner: str | None = typer.Option(
        None,
        "--owner",
        help="Project owner display name. Defaults to generic owner.",
    ),
    mcp_hint: bool | None = typer.Option(
        None,
        "--mcp-hint/--no-mcp-hint",
        help="Show an MCP setup command after initialization",
    ),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Initialize a P2P workspace."""
    rubric_enabled: dict[str, bool] | None = None
    if name is None:
        console.print("[bold]P2P project initialization[/bold]")
        name = typer.prompt("Project name", default=root.resolve().name)
        selected_agent = _prompt_choice(
            "Initial agent profile",
            choices=("all", "generic", "codex", "claude", "cursor", "copilot", "gemini", "opencode"),
            default=(agent[0] if agent else "all"),
        )
        agent = [selected_agent]
        repository = _prompt_choice(
            "Repository mode",
            choices=("local", "cloud"),
            default=repository,
        )
        domain = _prompt_choice(
            "Domain template",
            choices=("none", "custom", "generic", "software", "grant_document", "board_game"),
            default=domain,
        )
        rubric_enabled = _prompt_rubric_selection(domain)
        if mcp_hint is None:
            mcp_hint = typer.confirm("Show MCP setup hint?", default=True)
    else:
        mcp_hint = bool(mcp_hint)

    workspace = _workspace(root)
    agent_profile = "all" if not agent else ("all" if "all" in agent else ",".join(agent))
    try:
        created = workspace.init_project(
            name=name,
            agent_profile=agent_profile,
            repository_mode=repository,
            project_domain=domain,
            rubric_enabled=rubric_enabled,
            owner=owner,
            remote_provider=provider,
            remote_name=remote,
            remote_url_value=remote_url,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]P2P workspace initialized.[/green]")
    for path in created:
        console.print(f"  created {path}")
    _print_init_remote_status(workspace)
    _print_init_next_steps(root.resolve(), agent_profile, show_mcp_hint=mcp_hint)


def _print_init_remote_status(workspace: P2PWorkspace) -> None:
    profile = workspace.remote_profile()
    if profile.mode == "local":
        return
    status = workspace.sync_status()
    console.print("Remote profile")
    console.print(f"  mode: {profile.mode}")
    console.print(f"  provider: {profile.provider}")
    console.print(f"  remote: {profile.remote or 'none'}")
    console.print(f"  profile_url: {profile.url or 'none'}")
    console.print(f"  git_remote_url: {status.remote_url or 'none'}")
    console.print(f"  can_sync: {str(status.can_sync).lower()}")
    console.print(f"  reason: {status.reason}")


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


def _prompt_rubric_selection(domain: str) -> dict[str, bool] | None:
    preview = P2PWorkspace(Path.cwd()).init_project_rubrics_preview(domain)
    if not preview:
        console.print("Project definition rubric criteria: unresolved")
        console.print("Define the domain and rubric with the user and agent after initialization.")
        return None
    console.print("Project definition rubric criteria:")
    for criterion in preview:
        console.print(f"  - {criterion['id']}: {criterion['title']}")
    if not typer.confirm("Customize rubric criteria?", default=False):
        return None
    selected: dict[str, bool] = {}
    for criterion in preview:
        selected[str(criterion["id"])] = typer.confirm(
            f"Enable {criterion['title']}?",
            default=True,
        )
    enabled_count = sum(1 for enabled in selected.values() if enabled)
    disabled_count = len(selected) - enabled_count
    console.print(f"Rubric selection: {enabled_count} enabled, {disabled_count} disabled")
    return selected


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


if __name__ == "__main__":
    app()

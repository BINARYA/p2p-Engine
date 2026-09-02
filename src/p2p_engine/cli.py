from __future__ import annotations

from pathlib import Path

import typer
from rich.markup import escape

from p2p_engine import __version__
from p2p_engine.cli_commands.agents import register_agent_commands
from p2p_engine.cli_commands.authority_transfer import register_authority_transfer_commands
from p2p_engine.cli_commands.collaboration import register_collaboration_commands
from p2p_engine.cli_commands.doctor import register_doctor_commands
from p2p_engine.cli_commands.linked_replica import register_linked_replica_commands
from p2p_engine.cli_commands.mutations import register_mutation_commands
from p2p_engine.cli_commands.next_actions import register_next_commands
from p2p_engine.cli_commands.project_authority import register_project_authority_commands
from p2p_engine.cli_commands.project_domain import register_project_domain_commands
from p2p_engine.cli_commands.project_identity import register_project_identity_commands
from p2p_engine.cli_commands.project_integration import register_project_integration_commands
from p2p_engine.cli_commands.project_memory import register_project_memory_commands
from p2p_engine.cli_commands.project_ops import register_project_ops_commands
from p2p_engine.cli_commands.project_readiness import register_project_readiness_commands
from p2p_engine.cli_commands.project_status import register_project_status_commands
from p2p_engine.cli_commands.project_structure import register_project_structure_commands
from p2p_engine.cli_commands.prompts import register_prompt_commands
from p2p_engine.cli_commands.proposals import register_proposal_commands
from p2p_engine.cli_commands.runtime import register_runtime_commands
from p2p_engine.cli_commands.verticals import register_vertical_commands
from p2p_engine.cli_commands.work_specs import register_work_spec_commands
from p2p_engine.cli_commands.workspace_schema import register_workspace_schema_commands
from p2p_engine.cli_commands.workspace_transactions import register_workspace_transaction_commands
from p2p_engine.cli_contract import (
    VersionedJSONTyperGroup,
    print_json,
    success_envelope,
)
from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail as _fail
from p2p_engine.cli_shared import workspace as _workspace
from p2p_engine.core.portable_verticals import VerticalCoordinate
from p2p_engine.core.release_contracts import current_contract_versions
from p2p_engine.services.agent_selection import AgentProfileSelection, select_agent_profile
from p2p_engine.services.authority import AuthorityContractCodec
from p2p_engine.services.mcp_hints import McpHint, render_shell_command

_VERSION_TEXT_LABELS = {
    "workspace_schema_version": "workspace schema",
    "vertical_pack_schema_version": "vertical pack schema",
    "portable_package_format_version": "portable package format",
}

app = typer.Typer(help="P2P Engine CLI", cls=VersionedJSONTyperGroup)
proposal_app = typer.Typer(help="Manage proposals")
proposal_readiness_app = typer.Typer(help="Inspect proposal readiness")
proposal_questions_app = typer.Typer(help="Manage proposal readiness questions")
proposal_artifact_app = typer.Typer(help="Manage proposal artifact coverage state")
proposal_contribution_app = typer.Typer(help="Manage proposal contributions")
proposal_scope_app = typer.Typer(help="Inspect and assign explicit project-memory scope")
contribution_app = typer.Typer(help="Manage contributions")
decision_app = typer.Typer(help="Inspect, preview, apply, and repair proposal decisions")
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
project_authority_app = typer.Typer(help="Inspect and rotate project authority")
project_domain_app = typer.Typer(help="Inspect and change project subject classification")
project_structure_app = typer.Typer(help="Inspect and edit the project-owned structure")
project_memory_app = typer.Typer(help="Inspect project-memory organization against structure")
project_authority_rotate_app = typer.Typer(help="Preview, apply, and inspect authority rotation")
project_brief_app = typer.Typer(help="Generate and import operational project briefs")
project_rubrics_app = typer.Typer(help="Manage project definition rubrics")
project_definition_app = typer.Typer(help="Manage project definition state")
project_interaction_style_app = typer.Typer(help="Manage project interaction style")
project_vertical_app = typer.Typer(help="Manage project vertical packs")
project_readiness_app = typer.Typer(help="Review project readiness against project-owned structure")
project_readiness_questions_app = typer.Typer(help="Manage persistent project-readiness questions")
impact_app = typer.Typer(help="Analyze proposal impact")
conflict_app = typer.Typer(help="Record and inspect project conflicts")
change_app = typer.Typer(help="Manage operational Change Set metadata")
spec_app = typer.Typer(help="Generate and refine P2P-native software specs")
registry_app = typer.Typer(help="Manage generated project registries")
intake_app = typer.Typer(help="Analyze raw ideas against project context")
intake_apply_app = typer.Typer(help="Plan and run controlled intake applications")
choice_app = typer.Typer(help="Manage project choices")
work_app = typer.Typer(help="Manage P2P work manifests")
permissions_app = typer.Typer(help="Manage project-declared permission identities")
permissions_actor_app = typer.Typer(help="Manage permission actors")
consent_app = typer.Typer(help="Manage permission-gated consent receipts")
agent_app = typer.Typer(help="Manage agent-facing project instructions")
agent_instructions_app = typer.Typer(help="Generate and refresh agent instructions")
integration_app = typer.Typer(help="Manage versioned project integration artifacts")
assess_app = typer.Typer(help="Assess project readiness and maturity")
assess_maturity_app = typer.Typer(help="Assess project definition maturity")
next_app = typer.Typer(help="Manage advisory next actions", invoke_without_command=True)
runtime_app = typer.Typer(help="Inspect project runtime compatibility")
workspace_app = typer.Typer(help="Inspect the current workspace contract and transactions")
workspace_schema_app = typer.Typer(help="Inspect workspace schema state")
workspace_transaction_app = typer.Typer(help="Inspect and recover atomic workspace transactions")
vertical_app = typer.Typer(help="Discover, obtain and author exact vertical releases")
mutation_app = typer.Typer(help="Inspect durable idempotent mutation outcomes")
auth_app = typer.Typer(help="Manage personal WaveKit authentication")
wavekit_app = typer.Typer(help="Clone and operate WaveKit-linked local replicas")

proposal_app.add_typer(proposal_readiness_app, name="readiness")
proposal_app.add_typer(proposal_questions_app, name="questions")
proposal_app.add_typer(proposal_artifact_app, name="artifact")
proposal_app.add_typer(proposal_contribution_app, name="contribution")
proposal_app.add_typer(proposal_scope_app, name="scope")
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
app.add_typer(permissions_app, name="permissions")
app.add_typer(consent_app, name="consent")
app.add_typer(agent_app, name="agent")
app.add_typer(integration_app, name="integration")
app.add_typer(assess_app, name="assess")
app.add_typer(next_app, name="next")
app.add_typer(runtime_app, name="runtime")
app.add_typer(workspace_app, name="workspace")
app.add_typer(vertical_app, name="vertical")
app.add_typer(mutation_app, name="mutation")
app.add_typer(auth_app, name="auth")
app.add_typer(wavekit_app, name="wavekit")
workspace_app.add_typer(workspace_schema_app, name="schema")
workspace_app.add_typer(workspace_transaction_app, name="transaction")
project_app.add_typer(project_brief_app, name="brief")
project_app.add_typer(project_rubrics_app, name="rubrics")
project_app.add_typer(project_definition_app, name="definition")
project_app.add_typer(project_interaction_style_app, name="interaction-style")
project_app.add_typer(project_vertical_app, name="vertical")
project_app.add_typer(project_readiness_app, name="readiness")
project_app.add_typer(project_authority_app, name="authority")
project_app.add_typer(project_domain_app, name="domain")
project_app.add_typer(project_structure_app, name="structure")
project_app.add_typer(project_memory_app, name="memory")
project_readiness_app.add_typer(project_readiness_questions_app, name="questions")
assess_app.add_typer(assess_maturity_app, name="maturity")
intake_app.add_typer(intake_apply_app, name="apply")
agent_app.add_typer(agent_instructions_app, name="instructions")
permissions_app.add_typer(permissions_actor_app, name="actor")

register_doctor_commands(app, agent_app)
register_vertical_commands(vertical_app)
register_agent_commands(agent_app, agent_instructions_app)
register_project_integration_commands(integration_app)
register_next_commands(next_app)
register_runtime_commands(runtime_app)
register_workspace_schema_commands(workspace_schema_app)
register_workspace_transaction_commands(workspace_transaction_app)
register_mutation_commands(mutation_app)
register_authority_transfer_commands(auth_app, project_app)
register_linked_replica_commands(wavekit_app)
register_project_status_commands(app, assess_app, assess_maturity_app)
register_project_identity_commands(project_app)
register_proposal_commands(
    proposal_app,
    proposal_readiness_app,
    proposal_questions_app,
    proposal_artifact_app,
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
    project_memory_app,
    project_rubrics_app,
    project_definition_app,
    project_interaction_style_app,
    project_vertical_app,
    project_readiness_app,
    project_brief_app,
    permissions_app,
    permissions_actor_app,
    consent_app,
)
register_project_readiness_commands(
    project_readiness_app,
    project_readiness_questions_app,
)
register_project_authority_commands(
    project_authority_app,
    project_authority_rotate_app,
)
register_project_domain_commands(project_domain_app)
register_project_structure_commands(project_structure_app)
register_project_memory_commands(proposal_scope_app, project_memory_app)
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
def version(
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
) -> None:
    """Show the installed engine and public contract versions."""
    normalized = output_format.strip().lower()
    if normalized not in {"text", "json"}:
        raise typer.BadParameter("Output format must be text or json.")
    data = current_contract_versions()
    if normalized == "json":
        print_json(success_envelope("version", data))
        return
    console.print(f"P2P Engine {__version__}")
    for key, value in data.items():
        if key == "engine_version":
            continue
        label = _VERSION_TEXT_LABELS.get(key, key.replace("_", " "))
        console.print(f"  {label}: {value}")


@app.command()
def init(
    name: str | None = typer.Argument(None, help="Project name"),
    agent: list[str] | None = typer.Option(
        None,
        "--agent",
        help="Initial agent adapter. Repeat for a narrowed install set. Omit to use adaptive detection.",
    ),
    domain: str | None = typer.Option(
        None,
        "--domain",
        help="Optional free project subject classification key; never selects structure",
    ),
    domain_name: str = typer.Option(
        "",
        "--domain-name",
        help="Display name for --domain; defaults to a title derived from its key",
    ),
    domain_source: str = typer.Option(
        "local",
        "--domain-source",
        help="Domain source classification: local, external, imported, or system",
    ),
    domain_external_ref: str | None = typer.Option(
        None,
        "--domain-external-ref",
        help="Optional opaque provider reference; required for external domain source",
    ),
    starter: str | None = typer.Option(
        None,
        "--starter",
        help="Built-in structure starter: generic or empty",
    ),
    owner: str | None = typer.Option(
        None,
        "--owner",
        help="Project owner display name. Defaults to generic owner.",
    ),
    storage_adapter: str | None = typer.Option(
        None,
        "--storage-adapter",
        help=(
            "Project storage adapter. New projects default to filesystem; "
            "existing projects reopen their recorded adapter automatically."
        ),
    ),
    vertical: str | None = typer.Option(
        None,
        "--vertical",
        help="Exact publisher/id@version vertical release used as the structure source",
    ),
    vertical_pack: Path | None = typer.Option(
        None,
        "--vertical-pack",
        help="Local portable vertical archive installed and selected during initialization",
    ),
    expected_checksum: str = typer.Option(
        "",
        "--expected-checksum",
        help="Expected SHA-256 for --vertical-pack",
    ),
    pull: bool = typer.Option(
        False,
        "--pull",
        help="Explicitly allow retrieval of a missing exact --vertical release",
    ),
    vertical_registry: str = typer.Option(
        "",
        "--registry",
        help="Configured registry used only together with --vertical and --pull",
    ),
    profile: str = typer.Option(
        "default",
        "--profile",
        help="Optional project definition profile when --vertical is used",
    ),
    module: list[str] | None = typer.Option(
        None,
        "--module",
        help="Optional project vertical module. Repeat to enable multiple modules.",
    ),
    mcp_hint: bool | None = typer.Option(
        None,
        "--mcp-hint/--no-mcp-hint",
        help="Show an MCP setup command after initialization",
    ),
    operation_key: str = typer.Option(
        "",
        "--operation-key",
        help="Opaque caller-supplied operation key for JSON initialization retries",
    ),
    authority_context: Path | None = typer.Option(
        None,
        "--authority-context",
        help=(
            "Allowlisted JSON AuthorityContext for external-attestation "
            "initialization; valid only with --format json"
        ),
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text or json",
    ),
    root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
) -> None:
    """Initialize a P2P workspace."""
    normalized_output = output_format.strip().lower()
    if normalized_output not in {"text", "json"}:
        raise typer.BadParameter("Output format must be text or json.")
    json_output = normalized_output == "json"
    if json_output and name is None:
        _fail("P2P_INIT_NON_INTERACTIVE_REQUIRED: JSON init requires a project name")
    if json_output and not operation_key.strip():
        _fail("P2P_IDEMPOTENCY_KEY_REQUIRED: JSON init requires --operation-key")
    if operation_key.strip() and not json_output:
        _fail("P2P_INIT_OPERATION_KEY_REQUIRES_JSON: --operation-key requires --format json")
    if authority_context is not None and not json_output:
        _fail(
            "P2P_AUTHORITY_CONTEXT_INVALID: --authority-context requires --format json"
        )
    parsed_authority_context = None
    if authority_context is not None:
        try:
            parsed_authority_context = AuthorityContractCodec().context_from_path(
                authority_context
            )
        except ValueError as exc:
            _fail(str(exc))
    if json_output and not (starter or vertical or vertical_pack is not None):
        _fail(
            "P2P_STRUCTURE_SOURCE_REQUIRED: JSON init requires --starter, --vertical, or --vertical-pack"
        )
    if starter and (vertical or vertical_pack is not None):
        _fail(
            "P2P_STRUCTURE_SOURCE_CONFLICT: --starter is mutually exclusive with --vertical and --vertical-pack"
        )
    rubric_enabled: dict[str, bool] | None = None
    if name is None:
        console.print("[bold]P2P project initialization[/bold]")
        name = typer.prompt("Project name", default=root.resolve().name)
        provided_agent_option = bool(agent)
        default_agent = agent[0] if agent else select_agent_profile(None).effective_profile
        selected_agent = _prompt_choice(
            "Initial agent profile",
            choices=_agent_prompt_choices(default_agent),
            default=default_agent,
        )
        agent = [selected_agent] if provided_agent_option or selected_agent != default_agent else None
        domain = typer.prompt("Domain key (optional)", default=domain or "").strip() or None
        starter = _prompt_choice(
            "Structure starter",
            choices=("generic", "empty"),
            default=starter or "generic",
        )
        rubric_enabled = _prompt_rubric_selection("generic") if starter == "generic" else None
        if mcp_hint is None:
            mcp_hint = typer.confirm("Show MCP setup hint?", default=True)
    else:
        mcp_hint = bool(mcp_hint)

    if starter and (vertical or vertical_pack is not None):
        _fail(
            "P2P_STRUCTURE_SOURCE_CONFLICT: --starter is mutually exclusive with --vertical and --vertical-pack"
        )
    if vertical_pack is not None and (pull or vertical_registry):
        _fail(
            "P2P_VERTICAL_INIT_CONFLICT: --vertical-pack is mutually exclusive with --pull and --registry"
        )
    if pull and not vertical:
        _fail("P2P_VERTICAL_INIT_CONFLICT: --pull requires --vertical")
    if vertical_registry and not pull:
        _fail("P2P_VERTICAL_INIT_CONFLICT: --registry requires --pull during init")
    if expected_checksum and vertical_pack is None:
        _fail("P2P_VERTICAL_INIT_CONFLICT: --expected-checksum requires --vertical-pack")

    vertical_pack_closure: list[tuple[Path, str]] | None = None
    if vertical:
        try:
            exact_coordinate = str(VerticalCoordinate.parse(vertical))
        except ValueError as exc:
            _fail(str(exc))
        else:
            from p2p_engine.services.vertical_catalog import (
                VerticalCatalogService,
                VerticalPullService,
            )

            try:
                try:
                    _workspace(root)._project_vertical_service().resolve_pack(
                        exact_coordinate
                    )
                except ValueError as exc:
                    if not str(exc).startswith("P2P_VERTICAL_NOT_FOUND:"):
                        raise
                    catalog = VerticalCatalogService(root)
                    try:
                        selected = catalog.resolve(exact_coordinate)
                    except ValueError as catalog_exc:
                        if not str(catalog_exc).startswith("P2P_VERTICAL_NOT_FOUND:"):
                            raise
                        if not pull:
                            raise
                        pulled = VerticalPullService().pull(
                            exact_coordinate,
                            registry=vertical_registry,
                        )
                        selected_release = next(
                            item
                            for item in pulled.releases
                            if item.release.coordinate == exact_coordinate
                        )
                        selected = catalog.resolve(selected_release.release.coordinate)
                    if selected.artifact_path is not None:
                        closure = catalog.installation_closure(selected)
                        vertical_pack_closure = [
                            (item.artifact_path, item.release.artifact.sha256)
                            for item in closure
                        ]
                        vertical = None
            except ValueError as exc:
                _fail(str(exc))

    workspace = _workspace(root)
    agent_profile = None if not agent else ("all" if "all" in agent else ",".join(agent))
    try:
        if json_output:
            assert name is not None
            payload = workspace.init_project_with_operation_key(
                name=name,
                operation_key=operation_key,
                agent_profile=agent_profile,
                project_domain=domain,
                project_domain_name=domain_name,
                project_domain_source=domain_source,
                project_domain_external_ref=domain_external_ref,
                starter_id=starter,
                rubric_enabled=rubric_enabled,
                owner=owner,
                vertical_id=vertical,
                profile=profile,
                modules=module,
                vertical_pack=vertical_pack,
                expected_checksum=expected_checksum,
                vertical_pack_closure=vertical_pack_closure,
                authority_context=parsed_authority_context,
                storage_adapter=storage_adapter,
            )
            print_json(payload)
            return
        result = workspace.init_project_with_summary(
            name=name,
            agent_profile=agent_profile,
            project_domain=domain,
            project_domain_name=domain_name,
            project_domain_source=domain_source,
            project_domain_external_ref=domain_external_ref,
            starter_id=starter,
            rubric_enabled=rubric_enabled,
            owner=owner,
            vertical_id=vertical,
            profile=profile,
            modules=module,
            vertical_pack=vertical_pack,
            expected_checksum=expected_checksum,
            vertical_pack_closure=vertical_pack_closure,
            authority_context=parsed_authority_context,
            storage_adapter=storage_adapter,
        )
    except ValueError as exc:
        _fail(str(exc))
    console.print("[green]P2P workspace initialized.[/green]")
    for path in result.created:
        console.print(f"  created {path}")
    for warning in result.warnings:
        console.print(f"  warning: {escape(warning)}")
    _print_init_agent_selection(result.agent_selection)
    _print_init_mcp_setup(result.mcp_hint, show_mcp_hint=mcp_hint)
    _print_init_next_steps()


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


def _agent_prompt_choices(default: str) -> tuple[str, ...]:
    base = ("all", "generic", "codex", "claude", "cursor", "copilot", "gemini", "opencode")
    normalized_default = default.strip().lower()
    if normalized_default not in base:
        return base
    return (normalized_default, *[choice for choice in base if choice != normalized_default])


def _print_init_agent_selection(selection: AgentProfileSelection) -> None:
    console.print("Agent integrations")
    console.print(f"  Selection source: {selection.selection_source}")
    if selection.detected_adapter:
        console.print(f"  Detected current client: {selection.detected_adapter}")
        console.print(f"  This does not make {selection.detected_adapter} the project identity.")
    if selection.warning:
        console.print(f"  Warning: {selection.warning}")
    if selection.effective_profile == "all":
        console.print("  footprint: all installs every built-in adapter integration.")
    console.print(f"  Installed adapters: {', '.join(selection.effective_adapters)}")
    console.print("  Lifecycle commands:")
    console.print("    p2p agent list")
    console.print("    p2p agent install <adapter>")
    console.print("    p2p agent update <adapter>")
    console.print("    p2p agent doctor <adapter>")
    console.print("    p2p agent uninstall <adapter>")
    console.print("    p2p agent instructions refresh --profile <adapter>")


def _prompt_rubric_selection(starter: str) -> dict[str, bool] | None:
    preview = _workspace(Path.cwd()).init_project_rubrics_preview(starter)
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


def _print_init_mcp_setup(hint: McpHint, show_mcp_hint: bool = False) -> None:
    if not show_mcp_hint:
        return
    console.print("MCP setup hint")
    console.print(f"  root: {hint.root}")
    console.print("  `--root` points to the governed P2P decision root used for decisions and state.")
    console.print("  Codex registration:")
    console.print(
        f"    {render_shell_command(hint.codex_command) if hint.codex_command else 'unavailable'}"
    )
    console.print("  Generic stdio server command:")
    console.print(
        f"    {render_shell_command(hint.server_command) if hint.server_command else 'unavailable'}"
    )
    for note in hint.notes:
        console.print(f"  note: {note}")
    if hint.fallback_command:
        console.print("  PATH fallback:")
        console.print(f"    {render_shell_command(hint.fallback_command)}")
    if hint.project_venv_command:
        console.print("  Existing project virtualenv fallback:")
        console.print(f"    {render_shell_command(hint.project_venv_command)}")
    if hint.exact_version_command:
        console.print("  Exact-version owner-run alternative:")
        console.print(f"    {render_shell_command(hint.exact_version_command)}")


def _print_init_next_steps() -> None:
    console.print("Next steps:")
    console.print("  1. p2p registry refresh")
    console.print("  2. p2p status")
    console.print("  3. p2p next")
    console.print("  4. Create or intake the first idea with p2p proposal create or p2p intake prompt")


if __name__ == "__main__":
    app()

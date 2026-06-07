from __future__ import annotations

from pathlib import Path

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.cli_shared import yaml_dump_for_cli


def register_project_ops_commands(
    project_app: typer.Typer,
    project_remote_app: typer.Typer,
    project_rubrics_app: typer.Typer,
    project_brief_app: typer.Typer,
    sync_app: typer.Typer,
    permissions_app: typer.Typer,
    permissions_actor_app: typer.Typer,
    consent_app: typer.Typer,
) -> None:
    @project_app.command("refresh")
    def project_refresh(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Refresh .p2p/project from accepted proposals."""
        try:
            written = workspace_for(root).refresh_project_state()
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Project state refreshed.[/green]")
        for path in written:
            console.print(f"  updated {path}")

    @project_app.command("status")
    def project_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show rationalized project state status."""
        status = workspace_for(root).project_state_status()
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
            content = workspace_for(root).show_project_state(section)
        except ValueError as exc:
            fail(str(exc))
        console.print(content)

    @project_remote_app.command("show")
    def project_remote_show(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show local/remote project profile."""
        try:
            profile = workspace_for(root).remote_profile()
        except ValueError as exc:
            fail(str(exc))
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
            profile = workspace_for(root).configure_remote_profile(
                mode=mode,
                provider=provider,
                remote=remote,
                url=url,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Project remote profile configured.[/green]")
        console.print(f"  mode: {profile.mode}")
        console.print(f"  provider: {profile.provider}")
        console.print(f"  remote: {profile.remote or 'none'}")
        console.print(f"  url: {profile.url or 'none'}")
        console.print("  creates_remote_repository: false")
        console.print("  opens_external_request: false")

    @sync_app.command("status")
    def sync_status(
        remote: str | None = typer.Option(None, "--remote", help="Override configured Git remote"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show managed Git synchronization status."""
        try:
            status = workspace_for(root).sync_status(remote)
        except ValueError as exc:
            fail(str(exc))
        console.print("Sync status")
        console.print(f"  repository: {str(status.is_repository).lower()}")
        console.print(f"  branch: {status.branch or 'none'}")
        console.print(f"  clean: {str(status.is_clean).lower()}")
        console.print(f"  mode: {status.mode}")
        console.print(f"  provider: {status.provider}")
        console.print(f"  remote: {status.remote or 'none'}")
        console.print(f"  profile_url: {status.profile_url or 'none'}")
        console.print(f"  remote_url: {status.remote_url or 'none'}")
        console.print(f"  can_sync: {str(status.can_sync).lower()}")
        console.print(f"  reason: {status.reason}")

    @sync_app.command("fetch")
    def sync_fetch(
        remote: str | None = typer.Option(None, "--remote", help="Override configured Git remote"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Fetch configured remote refs through P2P validation."""
        try:
            result = workspace_for(root).sync_fetch(remote)
        except ValueError as exc:
            fail(str(exc))
        _print_sync_result(result)

    @sync_app.command("pull")
    def sync_pull(
        remote: str | None = typer.Option(None, "--remote", help="Override configured Git remote"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Fast-forward pull the current branch through P2P validation."""
        try:
            result = workspace_for(root).sync_pull(remote)
        except ValueError as exc:
            fail(str(exc))
        _print_sync_result(result)

    @sync_app.command("push")
    def sync_push(
        remote: str | None = typer.Option(None, "--remote", help="Override configured Git remote"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Push the current branch through P2P validation."""
        try:
            result = workspace_for(root).sync_push(remote)
        except ValueError as exc:
            fail(str(exc))
        _print_sync_result(result)

    @permissions_app.command("show")
    def permissions_show(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show project-declared permission identities and roles."""
        try:
            permissions = workspace_for(root).permissions_show()
        except ValueError as exc:
            fail(str(exc))
        console.print(yaml_dump_for_cli(permissions).rstrip())

    @permissions_actor_app.command("add")
    def permissions_actor_add(
        actor_id: str = typer.Argument(..., help="Actor identity, e.g. lorenzo"),
        role: str = typer.Option("contributor", "--role", help="Role: owner, maintainer, contributor, agent, readonly"),
        kind: str = typer.Option("person", "--kind", help="Actor kind: person, agent, client"),
        display_name: str | None = typer.Option(None, "--display-name", help="Human-readable actor name"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Add or update a project-declared actor identity."""
        try:
            actor = workspace_for(root).permissions_actor_add(actor_id, role=role, kind=kind, display_name=display_name)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Permission actor recorded.[/green]")
        console.print(f"  actor: {actor.actor_id}")
        console.print(f"  role: {actor.role}")
        console.print(f"  kind: {actor.kind}")
        console.print(f"  display_name: {actor.display_name}")
        console.print(f"  path: {actor.path}")

    @consent_app.command("grant")
    def consent_grant(
        operation: str = typer.Argument(..., help="Privileged operation, e.g. proposal_publish"),
        target: str = typer.Argument(..., help="Operation target, e.g. PROP-001"),
        actor: str = typer.Option(..., "--actor", help="Actor receiving consent"),
        approved_by: str = typer.Option("owner", "--approved-by", help="Owner identity approving consent"),
        expires_on: str | None = typer.Option(None, "--expires-on", help="Optional ISO date expiry"),
        single_use: bool = typer.Option(True, "--single-use/--multi-use", help="Whether consent is consumed once"),
        scope: str | None = typer.Option(None, "--scope", help="Optional consent scope label"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Grant a bounded consent receipt for a future privileged operation."""
        try:
            consent = workspace_for(root).consent_grant(
                operation,
                target,
                actor,
                approved_by=approved_by,
                expires_on=expires_on,
                single_use=single_use,
                scope=scope,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Consent granted.[/green]")
        _print_consent(consent)

    @consent_app.command("show")
    def consent_show(
        consent_id: str = typer.Argument(..., help="Consent ID, e.g. CONSENT-001"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show one consent receipt."""
        try:
            consent = workspace_for(root).consent_show(consent_id)
        except ValueError as exc:
            fail(str(exc))
        _print_consent(consent)

    @consent_app.command("status")
    def consent_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """List consent receipts."""
        try:
            receipts = workspace_for(root).consent_statuses()
        except ValueError as exc:
            fail(str(exc))
        console.print("Consent receipts")
        if not receipts:
            console.print("  none")
            return
        for receipt in receipts:
            console.print(f"  {receipt.consent_id}  {receipt.status}  {receipt.operation}  {receipt.target}  {receipt.actor_id}")

    @consent_app.command("revoke")
    def consent_revoke(
        consent_id: str = typer.Argument(..., help="Consent ID, e.g. CONSENT-001"),
        reason: str = typer.Option("", "--reason", help="Revocation reason"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Revoke a non-consumed consent receipt."""
        try:
            consent = workspace_for(root).consent_revoke(consent_id, reason)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Consent revoked.[/green]")
        _print_consent(consent)

    @project_rubrics_app.command("init")
    def project_rubrics_init(
        domain: str = typer.Option(
            "generic",
            "--domain",
            help="none, custom, generic, software, grant_document, or board_game",
        ),
        force: bool = typer.Option(False, "--force", help="Replace existing project rubrics"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Create or replace project definition maturity rubrics."""
        try:
            rubrics = workspace_for(root).init_project_rubrics(domain=domain, force=force)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Project rubrics initialized.[/green]")
        console.print(f"  path: {rubrics.path}")
        console.print(f"  domain: {rubrics.domain}")
        console.print(f"  status: {rubrics.status}")
        console.print(f"  criteria: {len(rubrics.criteria)}")

    @project_rubrics_app.command("show")
    def project_rubrics_show(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show configured project definition maturity rubrics."""
        try:
            rubrics = workspace_for(root).show_project_rubrics()
        except ValueError as exc:
            fail(str(exc))
        console.print("Project rubrics")
        console.print(f"  path: {rubrics.path}")
        console.print(f"  domain: {rubrics.domain}")
        console.print(f"  status: {rubrics.status}")
        if not rubrics.criteria:
            console.print("Criteria: unresolved")
            return
        console.print("Criteria:")
        for criterion in rubrics.criteria:
            enabled = "enabled" if criterion.get("enabled") is not False else "disabled"
            console.print(f"  {criterion.get('id')}  {enabled}  {criterion.get('title')}")

    @project_brief_app.command("prompt")
    def project_brief_prompt(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Create an operational brief prompt from project state and registries."""
        try:
            prompt = workspace_for(root).create_project_brief_prompt()
        except ValueError as exc:
            fail(str(exc))
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
            imported = workspace_for(root).import_project_brief(source)
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Project brief imported.[/green]")
        for path in imported:
            console.print(f"  updated {path}")

    @project_brief_app.command("show")
    def project_brief_show(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Print the stored operational project brief."""
        try:
            content = workspace_for(root).show_project_brief()
        except ValueError as exc:
            fail(str(exc))
        console.print(content)


def _print_sync_result(result: object) -> None:
    console.print(f"[green]Sync {getattr(result, 'status')}.[/green]")
    console.print(f"  action: {getattr(result, 'action')}")
    console.print(f"  branch: {getattr(result, 'branch') or 'none'}")
    console.print(f"  remote: {getattr(result, 'remote')}")
    console.print(f"  remote_url: {getattr(result, 'remote_url')}")


def _print_consent(consent: object) -> None:
    console.print(f"  consent: {getattr(consent, 'consent_id')}")
    console.print(f"  status: {getattr(consent, 'status')}")
    console.print(f"  operation: {getattr(consent, 'operation')}")
    console.print(f"  target: {getattr(consent, 'target')}")
    console.print(f"  actor: {getattr(consent, 'actor_id')}")
    console.print(f"  approved_by: {getattr(consent, 'approved_by')}")
    console.print(f"  single_use: {str(getattr(consent, 'single_use')).lower()}")
    console.print(f"  expires_on: {getattr(consent, 'expires_on') or 'none'}")
    console.print(f"  path: {getattr(consent, 'path')}")

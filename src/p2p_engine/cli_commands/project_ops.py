from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import typer

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.cli_shared import yaml_dump_for_cli


def register_project_ops_commands(
    project_app: typer.Typer,
    project_remote_app: typer.Typer,
    project_rubrics_app: typer.Typer,
    project_definition_app: typer.Typer,
    project_interaction_style_app: typer.Typer,
    project_vertical_app: typer.Typer,
    project_readiness_app: typer.Typer,
    project_brief_app: typer.Typer,
    sync_app: typer.Typer,
    permissions_app: typer.Typer,
    permissions_actor_app: typer.Typer,
    consent_app: typer.Typer,
) -> None:
    project_publish_app = typer.Typer(help="Prepare and inspect canonical human project publication output")
    project_vertical_lock_app = typer.Typer(help="Inspect and repair project vertical lock state")
    project_app.add_typer(project_publish_app, name="publish")
    project_vertical_app.add_typer(project_vertical_lock_app, name="lock")

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

    @project_app.command("export")
    def project_export(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Export the visible human-facing project definition to outputs/latest/project.md."""
        try:
            result = workspace_for(root).export_visible_project_definition()
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Project definition exported.[/green]")
        console.print(f"  latest: {result.latest_path}")
        console.print(f"  exports: {result.exports_dir}")
        console.print(f"  archived: {result.archived_path or 'none'}")

    @project_app.command("export-status")
    def project_export_status(root: Path = typer.Option(Path.cwd(), "--root", help="Project root")) -> None:
        """Show visible project definition export status."""
        status = workspace_for(root).visible_project_definition_export_status()
        console.print("Project definition export")
        console.print(f"  latest: {status.latest_path}")
        console.print(f"  latest_exists: {str(status.latest_exists).lower()}")
        console.print(f"  exports: {status.exports_dir}")
        if not status.review_paths:
            console.print("  reviews: none")
        else:
            console.print("  reviews:")
            for path in status.review_paths:
                console.print(f"    - {path}")

    @project_publish_app.command("prepare")
    def project_publish_prepare(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Prepare canonical human project publication inputs."""
        try:
            result = workspace_for(root).prepare_project_publication()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_prepare": result})
            return
        console.print("[green]Project publication prepared.[/green]")
        console.print(f"  latest: {result.latest_path}")
        console.print(f"  exported: {str(result.exported).lower()}")
        console.print(f"  reused_export: {str(result.reused_export).lower()}")
        console.print(f"  archived: {result.archived_path or 'none'}")
        console.print(f"  profile: {result.profile_path}")
        console.print(f"  curator_input: {result.curator_input_path}")
        console.print(f"  manifest: {result.manifest_path}")
        console.print(f"  source_fingerprint_sha256: {result.source_fingerprint_sha256}")
        console.print(f"  source_sha256: {result.source_sha256}")
        if result.stale_downstream:
            console.print("  stale_downstream:")
            for stage in result.stale_downstream:
                console.print(f"    - {stage}")
        else:
            console.print("  stale_downstream: none")

    @project_publish_app.command("import")
    def project_publish_import(
        source: Path = typer.Argument(..., help="Curated Markdown draft to import"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Import externally curated Markdown as the canonical publication draft."""
        try:
            result = workspace_for(root).import_project_publication(source)
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_import": result})
            return
        console.print("[green]Project publication imported.[/green]")
        console.print(f"  curated: {result.curated_path}")
        console.print(f"  imported_from: {result.imported_from}")
        console.print(f"  manifest: {result.manifest_path}")
        console.print(f"  curated_sha256: {result.curated_sha256}")
        console.print(f"  source_fingerprint_sha256: {result.source_fingerprint_sha256}")
        console.print(f"  source_sha256: {result.source_sha256}")
        console.print(f"  profile_sha256: {result.profile_sha256}")

    @project_publish_app.command("validate")
    def project_publish_validate(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Validate canonical human project publication Markdown."""
        try:
            result = workspace_for(root).validate_project_publication()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_validation": result})
            if result.status == "failed":
                raise typer.Exit(1)
            return
        console.print("Project publication validation")
        console.print(f"  status: {result.status}")
        console.print(f"  input: {result.input}")
        console.print(f"  curated_sha256: {result.curated_sha256 or 'none'}")
        console.print(f"  profile: {result.profile}")
        console.print(f"  profile_sha256: {result.profile_sha256 or 'none'}")
        if not result.findings:
            console.print("  findings: none")
        else:
            console.print("  findings:")
            for finding in result.findings:
                line = f" line={finding.line}" if finding.line is not None else ""
                console.print(f"    - {finding.severity} {finding.code}{line}: {finding.message}")
        if result.status == "failed":
            raise typer.Exit(1)

    @project_publish_app.command("render")
    def project_publish_render(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Render validated canonical publication Markdown to draft PDF."""
        try:
            result = workspace_for(root).render_project_publication()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_render": result})
            return
        console.print("[green]Project publication PDF rendered.[/green]")
        console.print(f"  path: {result.path}")
        console.print(f"  sha256: {result.sha256}")
        console.print(f"  curated_sha256: {result.curated_sha256}")
        console.print(f"  validation_sha256: {result.validation_sha256}")
        console.print(f"  theme: {result.theme}")
        console.print(f"  renderer: {result.renderer}")

    @project_publish_app.command("review")
    def project_publish_review(
        review_status: str = typer.Option(..., "--status", help="approved or changes_requested"),
        reviewer: str = typer.Option("owner", "--reviewer", help="Reviewer identity"),
        note: list[str] | None = typer.Option(None, "--note", help="Review note; may be repeated"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Record owner review for the current Markdown/PDF publication package."""
        try:
            result = workspace_for(root).review_project_publication(
                status=review_status,
                reviewer=reviewer,
                notes=note,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_review": result})
            return
        console.print("[green]Project publication review recorded.[/green]")
        console.print(f"  status: {result.status}")
        console.print(f"  review: {result.review_path}")
        console.print(f"  reviewer: {result.reviewer}")
        console.print(f"  curated_sha256: {result.curated_sha256}")
        console.print(f"  pdf_sha256: {result.pdf_sha256}")

    @project_publish_app.command("status")
    def project_publish_status(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show canonical human project publication pipeline status."""
        status = workspace_for(root).project_publication_status()
        if _wants_json(output_format):
            _print_json({"publication_status": status})
            return
        console.print("Project publication")
        console.print(f"  manifest: {status.manifest_path}")
        console.print(f"  source_fingerprint_sha256: {status.source_fingerprint_sha256}")
        console.print(f"  approved_for_publication: {str(status.approved_for_publication).lower()}")
        console.print(f"  validation_status: {status.validation_status}")
        console.print(f"  render_status: {status.render_status}")
        console.print(f"  review_status: {status.review_status}")
        console.print("  stages:")
        for stage in status.stages:
            reason = f" ({stage.reason})" if stage.reason else ""
            console.print(
                f"    - {stage.name}: {stage.status}{reason} "
                f"path={stage.path} exists={str(stage.exists).lower()}"
            )

    @project_interaction_style_app.command("show")
    def project_interaction_style_show(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show effective project interaction style."""
        try:
            view = workspace_for(root).project_interaction_style()
        except ValueError as exc:
            fail(str(exc))
        _print_interaction_style(view)

    @project_interaction_style_app.command("set")
    def project_interaction_style_set(
        technical_verbosity: int | None = typer.Option(
            None,
            "--technical-verbosity",
            help="Technical detail level from 0 to 5",
        ),
        formality: int | None = typer.Option(None, "--formality", help="Formality level from 0 to 5"),
        assertiveness: int | None = typer.Option(None, "--assertiveness", help="Follow-up pressure from 0 to 5"),
        actor: str = typer.Option("local", "--actor", help="Actor updating the project interaction style"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Set one or more project interaction style values."""
        try:
            view = workspace_for(root).set_project_interaction_style(
                technical_verbosity=technical_verbosity,
                formality=formality,
                assertiveness=assertiveness,
                actor=actor,
            )
        except ValueError as exc:
            fail(str(exc))
        console.print("[green]Project interaction style updated.[/green]")
        _print_interaction_style(view)

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

    @project_vertical_app.command("list")
    def project_vertical_list(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """List available project vertical packs."""
        try:
            verticals = workspace_for(root).project_verticals()
            active = workspace_for(root).active_project_vertical()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"verticals": verticals, "active": active})
            return
        console.print("Project verticals")
        console.print(f"  active: {active.vertical_id}")
        console.print(f"  fallback_used: {str(active.fallback_used).lower()}")
        if not verticals:
            console.print("  none")
            return
        for vertical in verticals:
            active_marker = "*" if vertical.active else " "
            console.print(
                f"  {active_marker} {vertical.vertical_id}  {vertical.source}  "
                f"{vertical.version}  {vertical.name}"
            )

    @project_vertical_app.command("show")
    def project_vertical_show(
        vertical_id: str = typer.Argument(..., help="Vertical ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show a project vertical pack."""
        try:
            pack = workspace_for(root).show_project_vertical(vertical_id)
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"vertical": pack})
            return
        _print_vertical_pack(pack)

    @project_vertical_app.command("validate")
    def project_vertical_validate(
        target: str = typer.Argument(..., help="Vertical ID, vertical.yml path, or pack directory"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Validate a project vertical pack or known vertical ID."""
        result = workspace_for(root).validate_project_vertical(target)
        if _wants_json(output_format):
            _print_json({"validation": result})
            if not result.valid:
                raise typer.Exit(1)
            return
        console.print("Project vertical valid" if result.valid else "Project vertical invalid")
        console.print(f"  target: {result.target}")
        console.print(f"  vertical: {result.vertical_id or 'unknown'}")
        console.print(f"  source: {result.source}")
        if not result.issues:
            console.print("  issues: none")
        else:
            console.print("  issues:")
            for issue in result.issues:
                console.print(f"    - {issue.severity} {issue.field}: {issue.message}")
        if not result.valid:
            raise typer.Exit(1)

    @project_vertical_app.command("propose")
    def project_vertical_propose(
        idea: str = typer.Argument(..., help="Project idea used to generate a candidate vertical"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Generate an importable custom vertical candidate without persisting it."""
        try:
            candidate = workspace_for(root).propose_project_vertical(idea)
        except ValueError as exc:
            fail(str(exc))
        console.print("Custom vertical candidate")
        console.print(f"  source_idea: {candidate.source_idea}")
        console.print(f"  id: {candidate.pack.vertical_id}")
        console.print(f"  name: {candidate.pack.name}")
        console.print("  import: save the YAML under a review path, then run p2p project vertical add <path>")
        console.print("")
        console.print(candidate.yaml_text.rstrip())

    @project_vertical_app.command("add")
    def project_vertical_add(
        source: Path = typer.Argument(..., help="vertical.yml path or pack directory"),
        activate: bool = typer.Option(False, "--activate", help="Select this vertical after adding it"),
        actor: str = typer.Option("local", "--actor", help="Actor recorded if --activate is used"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Add a project-local vertical pack."""
        try:
            result = workspace_for(root).add_project_vertical(source, activate=activate, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"vertical_add": result})
            return
        console.print("[green]Project vertical added.[/green]")
        console.print(f"  id: {result.vertical_id}")
        console.print(f"  path: {result.path}")
        console.print(f"  activated: {str(result.activated).lower()}")

    @project_vertical_app.command("select")
    def project_vertical_select(
        vertical_id: str = typer.Argument(..., help="Vertical ID"),
        actor: str = typer.Option("local", "--actor", help="Actor selecting the vertical"),
        profile: str = typer.Option("default", "--profile", help="Project definition profile"),
        module: list[str] | None = typer.Option(None, "--module", help="Enabled module. Repeat for multiple modules."),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Select the active project vertical."""
        try:
            active = workspace_for(root).select_project_vertical(
                vertical_id,
                actor=actor,
                profile=profile,
                modules=module,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"active": active, "lock": workspace_for(root).project_vertical_lock_status(), "definition": workspace_for(root).project_definition_view()})
            return
        console.print("[green]Project vertical selected.[/green]")
        console.print(f"  id: {active.vertical_id}")
        console.print(f"  source: {active.source}")
        console.print(f"  selected_by: {active.selected_by or actor}")
        console.print(f"  fallback_used: {str(active.fallback_used).lower()}")

    @project_vertical_lock_app.command("show")
    def project_vertical_lock_show(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show project vertical lock status."""
        try:
            status = workspace_for(root).project_vertical_lock_status()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"lock_status": status})
            return
        console.print("Project vertical lock")
        console.print(f"  status: {status.status}")
        console.print(f"  path: {status.path}")
        console.print(f"  message: {status.message}")
        if status.locked:
            console.print(f"  vertical: {status.locked.vertical_id}")
            console.print(f"  checksum: {status.locked.checksum}")
        if status.suggested_command:
            console.print(f"  suggested: {status.suggested_command}")

    @project_vertical_lock_app.command("repair")
    def project_vertical_lock_repair(
        actor: str = typer.Option("local", "--actor", help="Actor repairing the lock"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Repair or create the project vertical lockfile from active vertical state."""
        try:
            lock = workspace_for(root).repair_project_vertical_lock(actor=actor)
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"lock": lock})
            return
        console.print("[green]Project vertical lock repaired.[/green]")
        console.print(f"  vertical: {lock.vertical_id}")
        console.print(f"  checksum: {lock.checksum}")
        console.print(f"  selected_by: {lock.selected_by}")

    @project_app.command("context")
    def project_context(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show JSON-ready project vertical context for agents."""
        try:
            context = workspace_for(root).project_vertical_context()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"project_context": context})
            return
        console.print("Project context")
        console.print(f"  active_vertical: {context.active.vertical_id}")
        console.print(f"  lock_status: {context.lock_status.status}")
        console.print(f"  selected_profile: {context.selected_profile}")
        console.print(f"  enabled_modules: {', '.join(context.enabled_modules) if context.enabled_modules else 'none'}")
        console.print(f"  warnings: {len(context.warnings)}")

    @project_app.command("sections")
    def project_sections(
        vertical: str | None = typer.Option(None, "--vertical", help="Vertical ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """List sections for the active or specified project vertical."""
        try:
            sections = workspace_for(root).project_vertical_sections(vertical)
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"sections": sections})
            return
        console.print("Project vertical sections")
        for section in sections:
            console.print(f"  - {section.section_id}  required={str(section.required).lower()}  {section.title}")

    @project_app.command("section")
    def project_section(
        section_id: str = typer.Argument(..., help="Section ID"),
        vertical: str | None = typer.Option(None, "--vertical", help="Vertical ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show one section for the active or specified project vertical."""
        try:
            section = workspace_for(root).project_vertical_section(section_id, vertical)
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"section": section})
            return
        console.print("Project vertical section")
        console.print(f"  id: {section.section_id}")
        console.print(f"  title: {section.title}")
        console.print(f"  required: {str(section.required).lower()}")
        console.print(f"  purpose: {section.purpose}")

    @project_readiness_app.command("review")
    def project_readiness_review(
        vertical: str | None = typer.Option(None, "--vertical", help="Review against a specific vertical ID"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Review project readiness against the active project vertical."""
        try:
            review = workspace_for(root).review_project_readiness(vertical)
        except ValueError as exc:
            fail(str(exc))
        console.print("Project readiness review")
        console.print(f"  active_vertical: {review.active_vertical_id}")
        console.print(f"  source: {review.vertical_source}")
        console.print(f"  fallback_used: {str(review.fallback_used).lower()}")
        console.print("Sections:")
        for section in review.sections:
            proposals = ", ".join(section.proposals) if section.proposals else "none"
            console.print(f"  - {section.section_id}  {section.status}  proposals: {proposals}")
        console.print("Missing capisaldi:")
        if review.missing_capisaldi:
            for section_id in review.missing_capisaldi:
                console.print(f"  - {section_id}")
        else:
            console.print("  none")
        console.print("Unmapped proposals:")
        if review.unmapped_proposals:
            for proposal_id in review.unmapped_proposals:
                console.print(f"  - {proposal_id}")
        else:
            console.print("  none")
        console.print("Generated questions:")
        if review.generated_questions:
            for question in review.generated_questions:
                console.print(f"  - {question}")
        else:
            console.print("  none")
        console.print("Suggested next:")
        for command in review.suggested_next:
            console.print(f"  - {command}")

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
    def project_rubrics_show(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show configured project definition maturity rubrics."""
        try:
            rubrics = workspace_for(root).show_project_rubrics()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"rubrics": rubrics})
            return
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

    @project_definition_app.command("show")
    def project_definition_show(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show durable project definition state."""
        try:
            view = workspace_for(root).project_definition_view()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"definition": view})
            return
        console.print("Project definition state")
        console.print(f"  exists: {str(view.exists).lower()}")
        console.print(f"  valid: {str(view.valid).lower()}")
        console.print(f"  path: {view.path}")
        if view.state:
            console.print(f"  vertical: {view.state.vertical_id}")
            console.print(f"  profile: {view.state.profile}")
            console.print(f"  sections: {len(view.state.sections)}")
        if view.issues:
            console.print("Issues:")
            for issue in view.issues:
                console.print(f"  - {issue.severity} {issue.field}: {issue.message}")

    @project_definition_app.command("update")
    def project_definition_update(
        patch: Path = typer.Argument(..., help="Patch YAML file"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Apply a structured project definition patch."""
        try:
            result = workspace_for(root).update_project_definition(patch)
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"definition_update": result})
            return
        console.print("[green]Project definition updated.[/green]")
        console.print(f"  path: {result.path}")
        console.print(f"  operations_applied: {result.operations_applied}")

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


def _print_interaction_style(view: object) -> None:
    console.print("Project interaction style")
    console.print(f"  scope: {getattr(view, 'scope')}")
    console.print(f"  configured: {str(getattr(view, 'configured')).lower()}")
    console.print(f"  source: {getattr(view, 'source')}")
    for name in ("technical_verbosity", "formality", "assertiveness"):
        scale = getattr(view, name)
        console.print(f"  {name}: {scale.value}  {scale.label}")
        console.print(f"    {scale.description}")
    updated_at = getattr(view, "updated_at", "")
    updated_by = getattr(view, "updated_by", "")
    if updated_at:
        console.print(f"  updated_at: {updated_at}")
    if updated_by:
        console.print(f"  updated_by: {updated_by}")
    console.print(f"  path: {getattr(view, 'path')}")


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


def _print_vertical_pack(pack: object) -> None:
    console.print("Project vertical")
    console.print(f"  id: {getattr(pack, 'vertical_id')}")
    console.print(f"  name: {getattr(pack, 'name')}")
    console.print(f"  version: {getattr(pack, 'version')}")
    console.print(f"  source: {getattr(pack, 'source')}")
    console.print(f"  extends: {getattr(pack, 'extends') or 'none'}")
    console.print(f"  path: {getattr(pack, 'path') or 'none'}")
    console.print("Sections:")
    for section in getattr(pack, "sections"):
        console.print(f"  - {section.section_id}  required={str(section.required).lower()}  {section.title}")
    console.print("Rubrics:")
    for rubric in getattr(pack, "rubrics"):
        console.print(f"  - {rubric.rubric_id}  section={rubric.section_id}  {rubric.title}")
    console.print("Questions:")
    for question in getattr(pack, "questions"):
        console.print(f"  - {question.question_id}  section={question.section_id}  {question.question}")
    console.print("Artifacts:")
    for artifact in getattr(pack, "artifacts"):
        sections = ", ".join(artifact.section_ids) if artifact.section_ids else "none"
        console.print(f"  - {artifact.artifact_id}  sections={sections}  {artifact.title}")


def _wants_json(output_format: str) -> bool:
    normalized = output_format.strip().lower()
    if normalized not in {"text", "json"}:
        raise typer.BadParameter("Output format must be text or json.")
    return normalized == "json"


def _print_json(payload: object) -> None:
    print(json.dumps(_to_jsonable(payload), sort_keys=True))


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value

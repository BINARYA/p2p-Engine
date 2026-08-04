from __future__ import annotations

from pathlib import Path
import zipfile

import typer
import yaml

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import fail
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.cli_shared import yaml_dump_for_cli
from p2p_engine.cli_contract import error_envelope, print_json, success_envelope
from p2p_engine.foundation.yaml_loaders import load_yaml


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
    project_vertical_install_app = typer.Typer(help="Preview and apply portable vertical installation")
    project_vertical_adopt_app = typer.Typer(help="Preview and apply vertical adoption for an empty definition")
    project_vertical_migrate_app = typer.Typer(help="Preview and apply evidence-preserving vertical migration")
    project_metadata_app = typer.Typer(help="Inspect and update bounded project metadata")
    project_memory_app = typer.Typer(help="Inspect vertical-aware derived project memory")
    project_app.add_typer(project_publish_app, name="publish")
    project_app.add_typer(project_metadata_app, name="metadata")
    project_app.add_typer(project_memory_app, name="memory")
    project_vertical_app.add_typer(project_vertical_lock_app, name="lock")
    project_vertical_app.add_typer(project_vertical_install_app, name="install")
    project_vertical_app.add_typer(project_vertical_adopt_app, name="adopt")
    project_vertical_app.add_typer(project_vertical_migrate_app, name="migrate")

    @project_memory_app.command("status")
    def project_memory_status(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show vertical project-memory materialization and freshness."""
        try:
            status = workspace_for(root).vertical_project_memory_status()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"project_memory_status": status})
            return
        console.print("Project memory")
        console.print(f"  state: {status.state}")
        console.print(f"  reason: {status.reason}")
        console.print(f"  vertical: {status.vertical_id or 'unknown'}")
        console.print(f"  sections: {status.section_count}")
        console.print(f"  outputs: {status.output_count}")
        if status.source_fingerprint_sha256:
            console.print(f"  source fingerprint: {status.source_fingerprint_sha256}")
        if status.changed_scopes:
            console.print(f"  changed scopes: {', '.join(status.changed_scopes)}")
        console.print(f"  refresh: {status.refresh_command}")

    @project_memory_app.command("show")
    def project_memory_show(
        section: str | None = typer.Option(None, "--section", help="Exact vertical section ID"),
        include_history: bool = typer.Option(False, "--include-history", help="Include historical contributions"),
        limit: int = typer.Option(20, "--limit", min=1, max=100),
        cursor: str = typer.Option("", "--cursor"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show aggregate or exact-section vertical project memory."""
        try:
            result = workspace_for(root).show_vertical_project_memory(
                section_id=section,
                include_history=include_history,
                limit=limit,
                cursor=cursor,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"project_memory": result})
            return
        if section is None:
            console.print("Project memory")
            console.print(f"  vertical: {result.vertical_id} {result.vertical_version}")
            console.print(f"  source: {result.source}")
            console.print(f"  sections: {len(result.sections)}")
            console.print(f"  unmapped active proposals: {result.total}")
            for item in result.sections:
                console.print(
                    f"  {item.get('id')}: {item.get('active_contributions')} active, "
                    f"{item.get('historical_contributions')} historical"
                )
            if result.next_cursor:
                console.print(f"  next cursor: {result.next_cursor}")
            return
        console.print(f"Project memory section: {result.section_id}")
        console.print(f"  total: {result.total}")
        console.print(f"  returned: {result.returned}")
        console.print(f"  truncated: {str(result.truncated).lower()}")
        if result.next_cursor:
            console.print(f"  next cursor: {result.next_cursor}")
        for item in result.items:
            console.print(
                f"  {item.get('proposal_id', '-')}: {item.get('activation', 'unknown')} "
                f"{item.get('title', '')}"
            )

    @project_metadata_app.command("show")
    def project_metadata_show(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show bounded project metadata and protected configuration hashes."""
        try:
            view = workspace_for(root).project_metadata_view()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"project_metadata": view})
            return
        console.print("Project metadata")
        for field, value in view.values.items():
            console.print(f"  {field}: {value or 'not set'}")

    @project_metadata_app.command("preview")
    def project_metadata_preview(
        patch: Path = typer.Argument(..., help="Project metadata patch YAML"),
        actor: str = typer.Option(..., "--actor", help="Owner identity reviewing the patch"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Preview a bounded project metadata update without writing."""
        try:
            preview = workspace_for(root).preview_project_metadata_update(patch, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"project_metadata_preview": preview})
            return
        console.print("Project metadata update preview")
        console.print(f"  token: {preview.preview_token}")
        console.print(f"  authority: {preview.authority}")
        console.print(f"  applicable: {str(preview.apply_allowed).lower()}")

    @project_metadata_app.command("apply")
    def project_metadata_apply(
        patch: Path = typer.Argument(..., help="Project metadata patch YAML supplied again"),
        preview_token: str = typer.Option(..., "--preview-token", help="Token returned by metadata preview"),
        actor: str = typer.Option(..., "--actor", help="Owner identity applying the patch"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm the reviewed update"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Apply a matching owner-confirmed project metadata update."""
        try:
            result = workspace_for(root).apply_project_metadata_update(
                patch,
                preview_token=preview_token,
                actor=actor,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"project_metadata_apply": result})
            return
        console.print("Project metadata update")
        console.print(f"  status: {result.status}")
        console.print(f"  token: {result.preview_token}")
        if result.message:
            console.print(f"  message: {result.message}")

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

    @project_app.command("progress")
    def project_progress(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        include_heuristics: bool = typer.Option(
            False,
            "--include-heuristics",
            help="Compute advisory legacy proposal-to-section suggestions.",
        ),
    ) -> None:
        """Show independent project-definition and declared-evidence progress axes."""
        try:
            progress = workspace_for(root).project_progress(
                include_heuristics=include_heuristics,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"project_progress": progress})
            return
        console.print("Project progress")
        console.print(f"  vertical: {progress.vertical_id}")
        for axis in (progress.definition, progress.evidence):
            percentage = "not available" if axis.ratio.percentage is None else f"{axis.ratio.percentage:.2f}%"
            console.print(f"  {axis.axis_id}: {axis.status} {axis.ratio.numerator}/{axis.ratio.denominator} ({percentage})")
            console.print(f"    basis: {axis.basis}")

    @project_app.command("freshness")
    def project_freshness(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Inspect derived-state dependencies and ordered rebuild actions without writing."""
        try:
            freshness = workspace_for(root).project_freshness()
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"project_freshness": freshness})
            return
        console.print("Project derived freshness")
        console.print(f"  status: {freshness.status}")
        for node in freshness.nodes:
            console.print(f"  {node.node_id}: {node.status}")
        if freshness.rebuild_plan:
            console.print("Rebuild plan:")
            for action in freshness.rebuild_plan:
                console.print(f"  {action.order}. {action.node_id} [{action.action_class}] {action.command or action.missing_primitive}")

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
        language: str = typer.Option("en", "--language", help="Publication language tag"),
        output_name: str = typer.Option("project", "--output-name", help="Publication output slug"),
        contributions: str = typer.Option(
            "auto",
            "--contributions",
            help="Contribution chapter policy: auto, include, or omit",
        ),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Prepare canonical human project publication inputs."""
        try:
            result = workspace_for(root).prepare_project_publication(
                language=language,
                output_name=output_name,
                contributions=contributions,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_prepare": result})
            return
        console.print("[green]Project publication prepared.[/green]")
        console.print(f"  edition: {result.edition.edition_key}")
        console.print(f"  language: {result.edition.language}")
        console.print(f"  latest: {result.latest_path}")
        console.print(f"  exported: {str(result.exported).lower()}")
        console.print(f"  reused_export: {str(result.reused_export).lower()}")
        console.print(f"  archived: {result.archived_path or 'none'}")
        console.print(f"  profile: {result.profile_path}")
        console.print(f"  evidence: {result.evidence_path}")
        console.print(f"  curator_input: {result.curator_input_path}")
        console.print(f"  manifest: {result.manifest_path}")
        console.print(f"  candidate_markdown: {result.candidate_markdown_path}")
        console.print(f"  candidate_model: {result.candidate_model_path}")
        console.print(f"  candidate_evidence: {result.candidate_evidence_path}")
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
        model: Path | None = typer.Option(None, "--model", help="Curated project-model YAML candidate"),
        evidence_accounting: Path | None = typer.Option(
            None,
            "--evidence-accounting",
            help="Curated evidence-accounting YAML candidate",
        ),
        language: str = typer.Option("en", "--language", help="Publication language tag"),
        output_name: str = typer.Option("project", "--output-name", help="Publication output slug"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Import externally curated Markdown as the canonical publication draft."""
        try:
            result = workspace_for(root).import_project_publication(
                source,
                model=model,
                evidence_accounting=evidence_accounting,
                language=language,
                output_name=output_name,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_import": result})
            return
        console.print("[green]Project publication imported.[/green]")
        console.print(f"  edition: {result.edition.edition_key}")
        console.print(f"  language: {result.edition.language}")
        console.print(f"  curated: {result.curated_path}")
        console.print(f"  model: {result.model_path}")
        console.print(f"  evidence_accounting: {result.evidence_accounting_path}")
        console.print(f"  imported_from: {result.imported_from}")
        console.print(f"  model_imported_from: {result.model_imported_from}")
        console.print(f"  evidence_imported_from: {result.evidence_imported_from}")
        console.print(f"  manifest: {result.manifest_path}")
        console.print(f"  curated_sha256: {result.curated_sha256}")
        console.print(f"  source_fingerprint_sha256: {result.source_fingerprint_sha256}")
        console.print(f"  source_sha256: {result.source_sha256}")
        console.print(f"  profile_sha256: {result.profile_sha256}")

    @project_publish_app.command("validate")
    def project_publish_validate(
        language: str = typer.Option("en", "--language", help="Publication language tag"),
        output_name: str = typer.Option("project", "--output-name", help="Publication output slug"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Validate canonical human project publication Markdown."""
        try:
            result = workspace_for(root).validate_project_publication(
                language=language,
                output_name=output_name,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_validation": result})
            if result.status == "failed":
                raise typer.Exit(1)
            return
        console.print("Project publication validation")
        console.print(f"  edition: {result.edition.edition_key}")
        console.print(f"  language: {result.edition.language}")
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
        language: str = typer.Option("en", "--language", help="Publication language tag"),
        output_name: str = typer.Option("project", "--output-name", help="Publication output slug"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Render validated canonical publication Markdown to draft PDF."""
        try:
            result = workspace_for(root).render_project_publication(
                language=language,
                output_name=output_name,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_render": result})
            return
        console.print("[green]Project publication PDF rendered.[/green]")
        console.print(f"  edition: {result.edition_key}")
        console.print(f"  language: {result.language}")
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
        language: str = typer.Option("en", "--language", help="Publication language tag"),
        output_name: str = typer.Option("project", "--output-name", help="Publication output slug"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Record owner review for the current Markdown/PDF publication package."""
        try:
            result = workspace_for(root).review_project_publication(
                status=review_status,
                reviewer=reviewer,
                notes=note,
                language=language,
                output_name=output_name,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_review": result})
            return
        console.print("[green]Project publication review recorded.[/green]")
        console.print(f"  edition: {result.edition.edition_key}")
        console.print(f"  language: {result.edition.language}")
        console.print(f"  status: {result.status}")
        console.print(f"  review: {result.review_path}")
        console.print(f"  reviewer: {result.reviewer}")
        console.print(f"  curated_sha256: {result.curated_sha256}")
        console.print(f"  pdf_sha256: {result.pdf_sha256}")

    @project_publish_app.command("status")
    def project_publish_status(
        language: str = typer.Option("en", "--language", help="Publication language tag"),
        output_name: str = typer.Option("project", "--output-name", help="Publication output slug"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Show canonical human project publication pipeline status."""
        try:
            status = workspace_for(root).project_publication_status(
                language=language,
                output_name=output_name,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"publication_status": status})
            return
        console.print("Project publication")
        console.print(f"  edition: {status.edition.edition_key}")
        console.print(f"  language: {status.edition.language}")
        console.print(f"  manifest: {status.manifest_path}")
        console.print(f"  source_fingerprint_sha256: {status.source_fingerprint_sha256}")
        console.print(f"  approved_for_publication: {str(status.approved_for_publication).lower()}")
        console.print(f"  validation_status: {status.validation_status}")
        console.print(f"  render_status: {status.render_status}")
        console.print(f"  review_status: {status.review_status}")
        if status.diagnostics:
            console.print("  diagnostics:")
            for item in status.diagnostics:
                console.print(f"    - {item.code}: {item.message} path={item.path}")
        console.print("  stages:")
        for stage in status.stages:
            reason = f" ({stage.reason})" if stage.reason else ""
            console.print(
                f"    - {stage.name}: {stage.status}{reason} "
                f"path={stage.path} exists={str(stage.exists).lower()}"
            )

    @project_publish_app.command("list")
    def project_publish_list(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """List committed publication editions without rebuilding publication state."""
        result = workspace_for(root).project_publication_editions()
        if _wants_json(output_format):
            _print_json({"publication_editions": result})
            return
        console.print("Project publication editions")
        console.print(f"  catalog: {result.catalog_path}")
        console.print(f"  legacy_status: {result.legacy_status}")
        if result.diagnostics:
            console.print("  diagnostics:")
            for item in result.diagnostics:
                console.print(f"    - {item.code}: {item.message} path={item.path}")
        if not result.editions:
            console.print("  editions: none")
            return
        console.print("  editions:")
        for item in result.editions:
            console.print(
                f"    - {item.edition.edition_key}: validation={item.validation_status} "
                f"render={item.render_status} review={item.review_status}"
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
            if _wants_json(output_format):
                _fail_operation("vertical_show", exc, output_format)
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
        source = Path(target)
        source = source if source.is_absolute() else root / source
        if _is_portable_vertical_target(source):
            result = workspace_for(root).validate_portable_vertical(source)
            validation = {
                "target": result.target,
                "valid": result.valid,
                "coordinate": result.pack.coordinate,
                "artifact_checksum": result.artifact_checksum,
                "semantic_checksum": result.semantic_checksum,
                "issues": result.issues,
            }
            if _wants_json(output_format):
                _print_json({"validation": validation})
                if not result.valid:
                    raise typer.Exit(1)
                return
            console.print("Project vertical valid" if result.valid else "Project vertical invalid")
            console.print(f"  target: {result.target}")
            console.print(f"  coordinate: {result.pack.coordinate or 'unknown'}")
            for issue in result.issues:
                console.print(f"  {issue.severity} {issue.code}: {issue.message}")
            if not result.valid:
                raise typer.Exit(1)
            return
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

    @project_vertical_app.command("schema")
    def project_vertical_schema(
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Show the portable vertical-pack authoring schema and safety limits."""
        schema = workspace_for(root).portable_vertical_schema()
        if _wants_json(output_format):
            _print_json(_operation_success("vertical_schema", schema))
            return
        console.print("Portable project vertical schema")
        console.print(f"  schema_version: {schema['schema_version']}")
        console.print(f"  coordinate: {schema['coordinate']}")
        console.print(f"  network_access: {str(schema['network_access']).lower()}")
        console.print(f"  max_entries: {schema['limits']['max_entries']}")

    @project_vertical_app.command("scaffold")
    def project_vertical_scaffold(
        target: Path = typer.Argument(..., help="New canonical pack directory"),
        publisher: str = typer.Option(..., "--publisher", help="Coordinate publisher"),
        vertical_id: str = typer.Option(..., "--id", help="Vertical ID"),
        version: str = typer.Option("0.1.0", "--version", help="Semantic version"),
        name: str = typer.Option("", "--name", help="Display name"),
        license_id: str = typer.Option(..., "--license", help="License identifier"),
        extends: str = typer.Option("", "--extends", help="Exact installed base coordinate"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Create a local schema-version-2 vertical authoring scaffold."""
        try:
            result = workspace_for(root).scaffold_portable_vertical(
                target,
                publisher=publisher,
                vertical_id=vertical_id,
                version=version,
                name=name,
                license_id=license_id,
                extends=extends,
            )
        except ValueError as exc:
            _fail_operation("vertical_scaffold", exc, output_format)
        data = _portable_inspection_payload(result, view="declared")
        if _wants_json(output_format):
            _print_json(_operation_success("vertical_scaffold", data))
            return
        console.print("[green]Portable vertical scaffold created.[/green]")
        console.print(f"  coordinate: {result.pack.coordinate}")
        console.print(f"  target: {target}")

    @project_vertical_app.command("inspect")
    def project_vertical_inspect(
        target: Path = typer.Argument(..., help="Pack directory or portable archive"),
        view: str = typer.Option("effective", "--view", help="View: declared or effective"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Inspect declared or inheritance-composed portable pack content."""
        try:
            result = workspace_for(root).inspect_portable_vertical(target, view=view)
        except ValueError as exc:
            _fail_operation("vertical_inspect", exc, output_format)
        data = _portable_inspection_payload(result, view=view)
        if _wants_json(output_format):
            _print_json(_operation_success("vertical_inspect", data))
            return
        console.print("Portable vertical inspection")
        console.print(f"  coordinate: {result.pack.coordinate}")
        console.print(f"  view: {view}")
        console.print(f"  semantic_checksum: {result.semantic_checksum}")
        if result.artifact_checksum:
            console.print(f"  artifact_checksum: {result.artifact_checksum}")

    @project_vertical_app.command("package")
    def project_vertical_package(
        source: Path = typer.Argument(..., help="Canonical schema-version-2 pack directory"),
        output: Path = typer.Option(..., "--output", help="Portable archive path"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Build a deterministic local portable vertical archive."""
        try:
            result = workspace_for(root).package_portable_vertical(source, output=output)
        except ValueError as exc:
            _fail_operation("vertical_package", exc, output_format)
        if _wants_json(output_format):
            _print_json(_operation_success("vertical_package", result))
            return
        console.print("[green]Portable vertical packaged.[/green]")
        console.print(f"  coordinate: {result.coordinate}")
        console.print(f"  output: {result.path}")
        console.print(f"  artifact_checksum: {result.artifact_checksum}")
        console.print(f"  semantic_checksum: {result.semantic_checksum}")

    @project_vertical_install_app.command("preview")
    def project_vertical_install_preview(
        artifact: Path = typer.Argument(..., help="Portable vertical archive"),
        expected_checksum: str = typer.Option(..., "--expected-checksum", help="Expected artifact SHA-256"),
        actor: str = typer.Option("local", "--actor", help="Requesting actor"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Preview a state-bound, offline portable-pack installation."""
        try:
            result = workspace_for(root).preview_portable_vertical_install(
                artifact,
                expected_checksum=expected_checksum,
                actor=actor,
            )
        except ValueError as exc:
            _fail_operation("vertical_install_preview", exc, output_format)
        _print_lifecycle_preview(result, operation="vertical_install_preview", output_format=output_format)

    @project_vertical_install_app.command("apply")
    def project_vertical_install_apply(
        artifact: Path = typer.Argument(..., help="Portable vertical archive"),
        expected_checksum: str = typer.Option(..., "--expected-checksum", help="Expected artifact SHA-256"),
        token: str = typer.Option(..., "--token", help="Current preview token"),
        idempotency_key: str = typer.Option(
            ...,
            "--idempotency-key",
            help="Opaque caller-supplied operation key",
        ),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm the governed mutation"),
        actor: str = typer.Option(..., "--actor", help="Applying actor"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Apply a previously previewed portable-pack installation."""
        try:
            result = workspace_for(root).apply_portable_vertical_install(
                artifact,
                expected_checksum=expected_checksum,
                preview_token=token,
                confirmed=confirm,
                actor=actor,
                idempotency_key=idempotency_key,
            )
        except ValueError as exc:
            _fail_operation("vertical_install_apply", exc, output_format)
        _print_lifecycle_result(result, operation="vertical_install_apply", output_format=output_format)

    @project_vertical_adopt_app.command("preview")
    def project_vertical_adopt_preview(
        coordinate: str = typer.Argument(..., help="Exact installed vertical coordinate"),
        actor: str = typer.Option("local", "--actor", help="Requesting actor"),
        profile: str = typer.Option("default", "--profile", help="Definition profile"),
        module: list[str] | None = typer.Option(None, "--module", help="Enabled module; repeat as needed"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Preview exact vertical adoption for a project without definition evidence."""
        try:
            result = workspace_for(root).preview_project_vertical_adoption(
                coordinate,
                actor=actor,
                profile=profile,
                modules=module,
            )
        except ValueError as exc:
            _fail_operation("vertical_adopt_preview", exc, output_format)
        _print_lifecycle_preview(result, operation="vertical_adopt_preview", output_format=output_format)

    @project_vertical_adopt_app.command("apply")
    def project_vertical_adopt_apply(
        coordinate: str = typer.Argument(..., help="Exact installed vertical coordinate"),
        token: str = typer.Option(..., "--token", help="Current preview token"),
        idempotency_key: str = typer.Option(
            ...,
            "--idempotency-key",
            help="Opaque caller-supplied operation key",
        ),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm the governed mutation"),
        actor: str = typer.Option(..., "--actor", help="Applying actor"),
        profile: str = typer.Option("default", "--profile", help="Definition profile"),
        module: list[str] | None = typer.Option(None, "--module", help="Enabled module; repeat as needed"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Apply a previously previewed exact vertical adoption."""
        try:
            result = workspace_for(root).apply_project_vertical_adoption(
                coordinate,
                preview_token=token,
                confirmed=confirm,
                actor=actor,
                idempotency_key=idempotency_key,
                profile=profile,
                modules=module,
            )
        except ValueError as exc:
            _fail_operation("vertical_adopt_apply", exc, output_format)
        _print_lifecycle_result(result, operation="vertical_adopt_apply", output_format=output_format)

    @project_vertical_migrate_app.command("preview")
    def project_vertical_migrate_preview(
        coordinate: str = typer.Argument(..., help="Exact installed target vertical coordinate"),
        mapping: Path | None = typer.Option(None, "--mapping", help="Exact field/rubric mapping YAML or JSON"),
        actor: str = typer.Option("local", "--actor", help="Requesting actor"),
        profile: str = typer.Option("default", "--profile", help="Definition profile"),
        module: list[str] | None = typer.Option(None, "--module", help="Enabled module; repeat as needed"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Preview evidence-preserving migration to an exact vertical."""
        try:
            result = workspace_for(root).preview_project_vertical_migration(
                coordinate,
                actor=actor,
                mapping=_load_vertical_mapping(mapping, root=root),
                profile=profile,
                modules=module,
            )
        except ValueError as exc:
            _fail_operation("vertical_migrate_preview", exc, output_format)
        _print_lifecycle_preview(result, operation="vertical_migrate_preview", output_format=output_format)

    @project_vertical_migrate_app.command("apply")
    def project_vertical_migrate_apply(
        coordinate: str = typer.Argument(..., help="Exact installed target vertical coordinate"),
        mapping: Path | None = typer.Option(None, "--mapping", help="Exact field/rubric mapping YAML or JSON"),
        token: str = typer.Option(..., "--token", help="Current preview token"),
        idempotency_key: str = typer.Option(
            ...,
            "--idempotency-key",
            help="Opaque caller-supplied operation key",
        ),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm the governed mutation"),
        actor: str = typer.Option(..., "--actor", help="Applying actor"),
        profile: str = typer.Option("default", "--profile", help="Definition profile"),
        module: list[str] | None = typer.Option(None, "--module", help="Enabled module; repeat as needed"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("json", "--format", help="Output format: text or json"),
    ) -> None:
        """Apply a previously previewed evidence-preserving vertical migration."""
        try:
            result = workspace_for(root).apply_project_vertical_migration(
                coordinate,
                preview_token=token,
                confirmed=confirm,
                actor=actor,
                idempotency_key=idempotency_key,
                mapping=_load_vertical_mapping(mapping, root=root),
                profile=profile,
                modules=module,
            )
        except ValueError as exc:
            _fail_operation("vertical_migrate_apply", exc, output_format)
        _print_lifecycle_result(result, operation="vertical_migrate_apply", output_format=output_format)

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

    @project_definition_app.command("preview")
    def project_definition_preview(
        patch: Path = typer.Argument(..., help="Patch YAML file"),
        actor: str = typer.Option(..., "--actor", help="Owner identity reviewing the patch"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Validate and preview a project definition patch without writing."""
        try:
            preview = workspace_for(root).preview_project_definition_update(patch, actor=actor)
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"definition_preview": preview})
            return
        console.print("Project definition update preview")
        console.print(f"  token: {preview.preview_token}")
        console.print(f"  authority: {preview.authority}")
        console.print(f"  applicable: {str(preview.apply_allowed).lower()}")
        console.print(f"  source: {preview.source_preconditions[0].physical_sha256 or 'missing'}")
        console.print(f"  candidate: {preview.candidate_semantic_hashes.get(preview.targets[0], '')}")

    @project_definition_app.command("apply")
    def project_definition_apply(
        patch: Path = typer.Argument(..., help="Patch YAML file supplied again at apply time"),
        preview_token: str = typer.Option(..., "--preview-token", help="Token returned by definition preview"),
        actor: str = typer.Option(..., "--actor", help="Owner identity applying the patch"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm the reviewed semantic update"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    ) -> None:
        """Apply a matching, owner-confirmed project definition preview."""
        try:
            result = workspace_for(root).apply_project_definition_update(
                patch,
                preview_token=preview_token,
                actor=actor,
                confirm=confirm,
            )
        except ValueError as exc:
            fail(str(exc))
        if _wants_json(output_format):
            _print_json({"definition_apply": result})
            return
        console.print("Project definition update")
        console.print(f"  status: {result.status}")
        console.print(f"  token: {result.preview_token}")
        if result.message:
            console.print(f"  message: {result.message}")

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


def _portable_inspection_payload(result: object, *, view: str) -> dict[str, object]:
    return {
        "target": getattr(result, "target"),
        "view": view,
        "coordinate": getattr(getattr(result, "pack"), "coordinate"),
        "artifact_checksum": getattr(result, "artifact_checksum"),
        "semantic_checksum": getattr(result, "semantic_checksum"),
        "entries": list(getattr(result, "entries")),
        "pack": (
            getattr(result, "declared_payload")
            if view == "declared"
            else getattr(result, "effective_payload")
        ),
    }


def _print_lifecycle_preview(result: object, *, operation: str, output_format: str) -> None:
    data = result.to_dict()
    if _wants_json(output_format):
        _print_json(_operation_success(operation, data))
        return
    console.print("Project vertical mutation preview")
    console.print(f"  operation: {getattr(result, 'operation')}")
    console.print(f"  coordinate: {getattr(result, 'coordinate')}")
    console.print(f"  apply_allowed: {str(getattr(result, 'apply_allowed')).lower()}")
    preview = getattr(result, "preview")
    if preview is not None:
        console.print(f"  preview_token: {preview.preview_token}")
    for blocker in getattr(result, "blockers"):
        console.print(f"  blocker: {blocker}")


def _print_lifecycle_result(result: object, *, operation: str, output_format: str) -> None:
    data = result.to_dict()
    if _wants_json(output_format):
        _print_json(_operation_success(operation, data))
        return
    status = getattr(result, "mutation").status
    console.print(f"[green]Project vertical mutation {status}.[/green]")
    console.print(f"  operation: {getattr(result, 'operation')}")
    console.print(f"  coordinate: {getattr(result, 'coordinate')}")
    console.print(f"  changed_paths: {len(getattr(result, 'mutation').changed_paths)}")


def _load_vertical_mapping(path: Path | None, *, root: Path) -> dict[str, object]:
    if path is None:
        return {}
    source = path if path.is_absolute() else root / path
    if not source.is_file() or source.is_symlink():
        raise ValueError(f"P2P_VERTICAL_INVALID_MAPPING: mapping file not found: {source}")
    payload = load_yaml(source.read_bytes())
    if not isinstance(payload, dict):
        raise ValueError("P2P_VERTICAL_INVALID_MAPPING: mapping document must be a mapping")
    nested = payload.get("vertical_migration")
    return nested if isinstance(nested, dict) else payload


def _is_portable_vertical_target(source: Path) -> bool:
    if source.is_file():
        return zipfile.is_zipfile(source)
    manifest_path = source / "manifest.yml"
    if not source.is_dir() or not manifest_path.is_file():
        return False
    try:
        payload = load_yaml(manifest_path.read_bytes())
    except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError):
        return False
    manifest = payload.get("manifest") if isinstance(payload, dict) else None
    return isinstance(manifest, dict) and manifest.get("schema_version") == 2


def _operation_success(operation: str, data: object) -> dict[str, object]:
    return success_envelope(operation, data)


def _fail_operation(operation: str, exc: ValueError, output_format: str) -> None:
    if _wants_json(output_format):
        message = str(exc)
        prefix = message.split(":", 1)[0]
        code = prefix if prefix.startswith("P2P_") else "P2P_VERTICAL_OPERATION_FAILED"
        _print_json(error_envelope(operation, code=code, message=message))
        raise typer.Exit(1)
    fail(str(exc))


def _wants_json(output_format: str) -> bool:
    normalized = output_format.strip().lower()
    if normalized not in {"text", "json"}:
        raise typer.BadParameter("Output format must be text or json.")
    return normalized == "json"


def _print_json(payload: object) -> None:
    print_json(payload)

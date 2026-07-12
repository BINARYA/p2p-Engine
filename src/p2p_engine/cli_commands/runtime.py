from __future__ import annotations

import json
from pathlib import Path

import typer

from p2p_engine.cli_shared import console, fail
from p2p_engine.cli_shared import workspace as workspace_for


def register_runtime_commands(runtime_app: typer.Typer) -> None:
    contract_app = typer.Typer(help="Preview and apply runtime contract updates")
    runtime_app.add_typer(contract_app, name="contract")

    @runtime_app.command("status")
    def status(
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Show read-only P2P Engine runtime compatibility status."""
        try:
            runtime_status = workspace_for(root).runtime_status()
        except ValueError as exc:
            fail(str(exc))
        if output_format == "json":
            console.print(json.dumps(runtime_status.to_dict(), indent=2))
        elif output_format == "text":
            console.print("Runtime")
            console.print(f"  state: {runtime_status.state}")
            console.print(f"  contract: {runtime_status.contract_path}")
            console.print(f"  current_version: {runtime_status.current_version or 'unknown'}")
            console.print(f"  requires: {runtime_status.requires or 'none'}")
            console.print(f"  recommended: {runtime_status.recommended or 'none'}")
            console.print(f"  compatible: {str(runtime_status.compatible).lower()}")
            if runtime_status.findings:
                console.print("Findings:")
                for finding in runtime_status.findings:
                    console.print(f"  {finding.severity.upper()} {finding.code} {finding.path}")
                    console.print(f"    {finding.message}")
                    if finding.suggested_command:
                        console.print(f"    command: {finding.suggested_command}")
        else:
            fail("Runtime status format must be text or json")

    @contract_app.command("preview")
    def contract_preview(
        requires: str = typer.Option(..., "--requires", help="Proposed compatible runtime range"),
        recommended: str = typer.Option(..., "--recommended", help="Proposed recommended runtime version"),
        reason: str = typer.Option("", "--reason", help="Structured reason for strong impacts"),
        decision: str = typer.Option("", "--decision", help="Optional existing decision reference"),
        actor: str = typer.Option("owner", "--actor", help="Actor used for apply-authority diagnostics"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Preview a runtime contract update without mutating project state."""
        try:
            preview = workspace_for(root).runtime_contract_update_preview(
                requires=requires,
                recommended=recommended,
                reason=reason,
                decision=decision,
                actor=actor,
            )
        except ValueError as exc:
            fail(str(exc))
        _print_contract_payload(preview.to_dict(), output_format=output_format, title="Runtime contract preview")

    @contract_app.command("apply")
    def contract_apply(
        requires: str = typer.Option(..., "--requires", help="Proposed compatible runtime range"),
        recommended: str = typer.Option(..., "--recommended", help="Proposed recommended runtime version"),
        expected_state_token: str = typer.Option("", "--expected-state-token", help="Token returned by preview"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm the governed runtime contract update"),
        reason: str = typer.Option("", "--reason", help="Structured reason for strong impacts"),
        decision: str = typer.Option("", "--decision", help="Optional existing decision reference"),
        actor: str = typer.Option("owner", "--actor", help="Actor applying the update"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Apply a previewed runtime contract update."""
        try:
            result = workspace_for(root).runtime_contract_update_apply(
                requires=requires,
                recommended=recommended,
                expected_state_token=expected_state_token,
                confirm=confirm,
                reason=reason,
                decision=decision,
                actor=actor,
            )
        except ValueError as exc:
            fail(str(exc))
        _print_contract_payload(result.to_dict(), output_format=output_format, title="Runtime contract apply")

    @contract_app.command("adopt")
    def contract_adopt(
        requires: str = typer.Option(..., "--requires", help="Adopted compatible runtime range"),
        recommended: str = typer.Option(..., "--recommended", help="Adopted recommended runtime version"),
        confirm: bool = typer.Option(False, "--confirm", help="Confirm the legacy runtime contract adoption"),
        actor: str = typer.Option("owner", "--actor", help="Actor applying the adoption"),
        output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Adopt a runtime contract for a legacy undeclared project."""
        try:
            result = workspace_for(root).runtime_contract_adopt(
                requires=requires,
                recommended=recommended,
                confirm=confirm,
                actor=actor,
            )
        except ValueError as exc:
            fail(str(exc))
        _print_contract_payload(result.to_dict(), output_format=output_format, title="Runtime contract adopt")


def _print_contract_payload(payload: dict[str, object], *, output_format: str, title: str) -> None:
    if output_format == "json":
        console.out(json.dumps(payload, indent=2), highlight=False)
        return
    if output_format != "text":
        fail("Runtime contract format must be text or json")
    proposed = payload.get("proposed_contract", {})
    authority = payload.get("authority", {})
    setup_guide = payload.get("setup_guide", {})
    console.print(title)
    console.print(f"  status: {payload.get('status')}")
    console.print(f"  current_state: {payload.get('current_state')}")
    if isinstance(proposed, dict):
        console.print(f"  requires: {proposed.get('requires') or 'none'}")
        console.print(f"  recommended: {proposed.get('recommended') or 'none'}")
        if "valid" in proposed:
            console.print(f"  proposed_valid: {str(proposed.get('valid')).lower()}")
    labels = payload.get("impact_labels", [])
    if isinstance(labels, list) and labels:
        console.print("  impact_labels: " + ", ".join(str(label) for label in labels))
    else:
        console.print("  impact_labels: none")
    console.print(f"  reason_required: {str(payload.get('reason_required', False)).lower()}")
    console.print(f"  confirmation_required: {str(payload.get('confirmation_required', False)).lower()}")
    if isinstance(setup_guide, dict):
        console.print(f"  setup_guide_state: {setup_guide.get('state') or 'unknown'}")
        console.print(f"  setup_guide_action: {setup_guide.get('planned_action') or 'none'}")
    if isinstance(authority, dict) and authority:
        console.print(f"  apply_authorized: {str(authority.get('apply_authorized')).lower()}")
        console.print(f"  authority_status: {authority.get('status')}")
    token = payload.get("expected_state_token")
    if token:
        console.print(f"  expected_state_token: {token}")
    if payload.get("blocked_reason"):
        console.print(f"  blocked_reason: {payload.get('blocked_reason')}")
    files = payload.get("files_changed", [])
    if isinstance(files, list) and files:
        console.print("Files:")
        for path in files:
            console.print(f"  - {path}")

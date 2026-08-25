from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Mapping

import typer
import yaml

from p2p_engine.cli_shared import console
from p2p_engine.cli_shared import workspace as workspace_for
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.proposal_decision_diagnostics import (
    proposal_decision_diagnostic,
)
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionCondition,
    ProposalDecisionEventType,
    ProposalDecisionLineage,
    ProposalDecisionLineageKind,
    ProposalDecisionRequest,
)
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.authority import AuthorityContractCodec
from p2p_engine.storage.filesystem import P2PWorkspace


def register_proposal_decision_commands(
    proposal_app: typer.Typer,
    decision_app: typer.Typer,
) -> None:
    @proposal_app.command("accept")
    def proposal_accept(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        reason: str = typer.Option(..., "--reason", help="Decision reason"),
        approver: str = typer.Option("owner", "--approver", help="Decision owner"),
        override_readiness: bool = typer.Option(
            False,
            "--override-readiness",
            help="Include an owner readiness override in the decision transaction.",
        ),
        preview_token: str = typer.Option("", "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        decided_on: str = typer.Option("", "--decided-on"),
        operation_key: str = typer.Option("", "--operation-key"),
        source_head_event_id: str = typer.Option("", "--source-head-event-id"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Preview or apply proposal acceptance."""
        workspace = workspace_for(root)
        if not override_readiness:
            _warn_if_readiness_is_weak(
                workspace,
                proposal_id,
                output_format=output_format,
            )
        _convenience_decision(
            workspace,
            proposal_id=proposal_id,
            outcome=DecisionOutcome.accepted,
            reason=reason,
            approver=approver,
            readiness_override=override_readiness,
            preview_token=preview_token,
            confirm=confirm,
            decided_on=decided_on,
            operation_key=operation_key,
            source_head_event_id=source_head_event_id,
            output_format=output_format,
        )

    @proposal_app.command("reject")
    def proposal_reject(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        reason: str = typer.Option(..., "--reason", help="Decision reason"),
        approver: str = typer.Option("owner", "--approver", help="Decision owner"),
        preview_token: str = typer.Option("", "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        decided_on: str = typer.Option("", "--decided-on"),
        operation_key: str = typer.Option("", "--operation-key"),
        source_head_event_id: str = typer.Option("", "--source-head-event-id"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Preview or apply initial proposal rejection."""
        _convenience_decision(
            workspace_for(root),
            proposal_id=proposal_id,
            outcome=DecisionOutcome.rejected,
            reason=reason,
            approver=approver,
            preview_token=preview_token,
            confirm=confirm,
            decided_on=decided_on,
            operation_key=operation_key,
            source_head_event_id=source_head_event_id,
            output_format=output_format,
        )

    @proposal_app.command("defer")
    def proposal_defer(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        reason: str = typer.Option(..., "--reason", help="Decision reason"),
        approver: str = typer.Option("owner", "--approver", help="Decision owner"),
        preview_token: str = typer.Option("", "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        decided_on: str = typer.Option("", "--decided-on"),
        operation_key: str = typer.Option("", "--operation-key"),
        source_head_event_id: str = typer.Option("", "--source-head-event-id"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root", help="Project root"),
    ) -> None:
        """Preview or apply proposal deferral."""
        _convenience_decision(
            workspace_for(root),
            proposal_id=proposal_id,
            outcome=DecisionOutcome.deferred,
            reason=reason,
            approver=approver,
            preview_token=preview_token,
            confirm=confirm,
            decided_on=decided_on,
            operation_key=operation_key,
            source_head_event_id=source_head_event_id,
            output_format=output_format,
        )

    @decision_app.command("status")
    def decision_status(
        proposal_id: str = typer.Argument(...),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        workspace = workspace_for(root)
        _read_operation(
            lambda: workspace.proposal_decision_status(proposal_id).to_dict(),
            title="Decision status",
            output_format=output_format,
        )

    @decision_app.command("history")
    def decision_history(
        proposal_id: str = typer.Argument(...),
        limit: int = typer.Option(20, "--limit", min=1),
        cursor: str = typer.Option("", "--cursor"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        workspace = workspace_for(root)
        _read_operation(
            lambda: workspace.proposal_decision_history(
                proposal_id,
                limit=limit,
                cursor=cursor or None,
            ).to_dict(),
            title="Decision history",
            output_format=output_format,
        )

    @decision_app.command("impact")
    def decision_impact(
        proposal_id: str = typer.Argument(...),
        event_type: ProposalDecisionEventType = typer.Option(..., "--event-type"),
        source_head_event_id: str = typer.Option("", "--source-head-event-id"),
        limit: int = typer.Option(20, "--limit", min=1),
        cursor: str = typer.Option("", "--cursor"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        workspace = workspace_for(root)

        def operation() -> dict[str, object]:
            snapshot = workspace.proposal_decision_impact(
                proposal_id,
                event_type=event_type,
                source_head_event_id=source_head_event_id or None,
            )
            page = workspace.proposal_decision_impact_page(
                snapshot,
                limit=limit,
                cursor=cursor or None,
            )
            return {
                **page.to_dict(),
                "event_type": event_type.value,
                "source_fingerprint_sha256": snapshot.source_fingerprint_sha256,
                "preview_token": snapshot.preview_token,
                "kind_counts": dict(snapshot.kind_counts),
                "status_counts": dict(snapshot.status_counts),
            }

        _read_operation(
            operation,
            title="Decision impact",
            output_format=output_format,
        )

    @decision_app.command("preview")
    def decision_preview(
        proposal_id: str = typer.Argument(...),
        event_type: ProposalDecisionEventType = typer.Option(..., "--event-type"),
        reason: str = typer.Option(..., "--reason"),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        decided_on: str = typer.Option("", "--decided-on"),
        operation_key: str = typer.Option("", "--operation-key"),
        source_head_event_id: str = typer.Option("", "--source-head-event-id"),
        condition: list[str] | None = typer.Option(None, "--condition"),
        conditions_file: Path | None = typer.Option(None, "--conditions-file"),
        lineage_kind: str = typer.Option("", "--lineage-kind"),
        lineage_target: list[str] | None = typer.Option(None, "--lineage-target"),
        affected_event_id: str = typer.Option("", "--affected-event-id"),
        revocation_event_id: str = typer.Option("", "--revocation-event-id"),
        impact_preview_token: str = typer.Option("", "--impact-preview-token"),
        acknowledge_drift: bool = typer.Option(False, "--acknowledge-drift"),
        override_readiness: bool = typer.Option(False, "--override-readiness"),
        authority_context: Path | None = typer.Option(
            None,
            "--authority-context",
            help="Exact typed AuthorityContext JSON",
        ),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        workspace = workspace_for(root)
        _mutation_operation(
            lambda: workspace.preview_proposal_decision(
                _decision_request(
                    proposal_id=proposal_id,
                    event_type=event_type,
                    reason=reason,
                    actor=actor,
                    executor_actor=executor_actor,
                    executor_kind=executor_kind,
                    decided_on=decided_on,
                    operation_key=operation_key,
                    source_head_event_id=source_head_event_id,
                    condition=condition,
                    conditions_file=conditions_file,
                    lineage_kind=lineage_kind,
                    lineage_target=lineage_target,
                    affected_event_id=affected_event_id,
                    revocation_event_id=revocation_event_id,
                    impact_preview_token=impact_preview_token,
                    acknowledge_drift=acknowledge_drift,
                    override_readiness=override_readiness,
                    authority_context=authority_context,
                )
            ),
            title="Decision preview",
            output_format=output_format,
            preview=True,
        )

    @decision_app.command("apply")
    def decision_apply(
        proposal_id: str = typer.Argument(...),
        event_type: ProposalDecisionEventType = typer.Option(..., "--event-type"),
        reason: str = typer.Option(..., "--reason"),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        executor_kind: str = typer.Option("person", "--executor-kind"),
        decided_on: str = typer.Option(..., "--decided-on"),
        operation_key: str = typer.Option(..., "--operation-key"),
        source_head_event_id: str = typer.Option("", "--source-head-event-id"),
        condition: list[str] | None = typer.Option(None, "--condition"),
        conditions_file: Path | None = typer.Option(None, "--conditions-file"),
        lineage_kind: str = typer.Option("", "--lineage-kind"),
        lineage_target: list[str] | None = typer.Option(None, "--lineage-target"),
        affected_event_id: str = typer.Option("", "--affected-event-id"),
        revocation_event_id: str = typer.Option("", "--revocation-event-id"),
        impact_preview_token: str = typer.Option("", "--impact-preview-token"),
        acknowledge_drift: bool = typer.Option(False, "--acknowledge-drift"),
        override_readiness: bool = typer.Option(False, "--override-readiness"),
        authority_context: Path | None = typer.Option(
            None,
            "--authority-context",
            help="Exact typed AuthorityContext JSON used by preview",
        ),
        preview_token: str = typer.Option(..., "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        workspace = workspace_for(root)
        _mutation_operation(
            lambda: workspace.apply_proposal_decision(
                _decision_request(
                    proposal_id=proposal_id,
                    event_type=event_type,
                    reason=reason,
                    actor=actor,
                    executor_actor=executor_actor,
                    executor_kind=executor_kind,
                    decided_on=decided_on,
                    operation_key=operation_key,
                    source_head_event_id=source_head_event_id,
                    condition=condition,
                    conditions_file=conditions_file,
                    lineage_kind=lineage_kind,
                    lineage_target=lineage_target,
                    affected_event_id=affected_event_id,
                    revocation_event_id=revocation_event_id,
                    impact_preview_token=impact_preview_token,
                    acknowledge_drift=acknowledge_drift,
                    override_readiness=override_readiness,
                    authority_context=authority_context,
                ),
                preview_token=preview_token,
                confirm=confirm,
            ),
            title="Decision apply",
            output_format=output_format,
        )

    @decision_app.command("record")
    def decision_record(
        proposal_id: str = typer.Argument(..., help="Proposal ID, e.g. PROP-001"),
        outcome: DecisionOutcome = typer.Option(..., "--outcome"),
        reason: str = typer.Option(..., "--reason"),
        approver: str = typer.Option("owner", "--approver"),
        preview_token: str = typer.Option("", "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        decided_on: str = typer.Option("", "--decided-on"),
        operation_key: str = typer.Option("", "--operation-key"),
        source_head_event_id: str = typer.Option("", "--source-head-event-id"),
        override_readiness: bool = typer.Option(False, "--override-readiness"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        """Convenience command using the current two-phase decision service."""
        _convenience_decision(
            workspace_for(root),
            proposal_id=proposal_id,
            outcome=outcome,
            reason=reason,
            approver=approver,
            readiness_override=override_readiness,
            preview_token=preview_token,
            confirm=confirm,
            decided_on=decided_on,
            operation_key=operation_key,
            source_head_event_id=source_head_event_id,
            output_format=output_format,
        )

    @decision_app.command("projection-repair-preview")
    def projection_repair_preview(
        proposal_id: str = typer.Argument(...),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        workspace = workspace_for(root)
        _mutation_operation(
            lambda: workspace.preview_proposal_decision_projection_repair(
                proposal_id,
                actor_id=actor,
                executor_actor_id=executor_actor or None,
            ),
            title="Projection repair preview",
            output_format=output_format,
            preview=True,
        )

    @decision_app.command("projection-repair-apply")
    def projection_repair_apply(
        proposal_id: str = typer.Argument(...),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        preview_token: str = typer.Option(..., "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        workspace = workspace_for(root)
        _mutation_operation(
            lambda: workspace.apply_proposal_decision_projection_repair(
                proposal_id,
                actor_id=actor,
                executor_actor_id=executor_actor or None,
                preview_token=preview_token,
                confirm=confirm,
            ),
            title="Projection repair apply",
            output_format=output_format,
        )

    @decision_app.command("ledger-repair-preview")
    def ledger_repair_preview(
        proposal_id: str = typer.Argument(...),
        candidate: Path = typer.Option(..., "--candidate"),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        workspace = workspace_for(root)
        _mutation_operation(
            lambda: workspace.preview_proposal_decision_ledger_repair(
                proposal_id,
                candidate_path=candidate,
                actor_id=actor,
                executor_actor_id=executor_actor or None,
            ),
            title="Ledger repair preview",
            output_format=output_format,
            preview=True,
        )

    @decision_app.command("ledger-repair-apply")
    def ledger_repair_apply(
        proposal_id: str = typer.Argument(...),
        candidate: Path = typer.Option(..., "--candidate"),
        actor: str = typer.Option("owner", "--actor"),
        executor_actor: str = typer.Option("", "--executor-actor"),
        preview_token: str = typer.Option(..., "--preview-token"),
        confirm: bool = typer.Option(False, "--confirm"),
        output_format: str = typer.Option("text", "--format", help="text or json"),
        root: Path = typer.Option(Path.cwd(), "--root"),
    ) -> None:
        workspace = workspace_for(root)
        _mutation_operation(
            lambda: workspace.apply_proposal_decision_ledger_repair(
                proposal_id,
                candidate_path=candidate,
                actor_id=actor,
                executor_actor_id=executor_actor or None,
                preview_token=preview_token,
                confirm=confirm,
            ),
            title="Ledger repair apply",
            output_format=output_format,
        )

def _convenience_decision(
    workspace: P2PWorkspace,
    *,
    proposal_id: str,
    outcome: DecisionOutcome,
    reason: str,
    approver: str,
    preview_token: str,
    confirm: bool,
    decided_on: str,
    operation_key: str,
    source_head_event_id: str,
    output_format: str,
    readiness_override: bool = False,
) -> None:
    _mutation_operation(
        lambda: workspace.record_decision(
            proposal_id=proposal_id,
            outcome=outcome,
            reason=reason,
            approver=approver,
            preview_token=preview_token,
            confirm=confirm,
            decided_on=decided_on,
            operation_key=operation_key,
            source_head_event_id=source_head_event_id or None,
            readiness_override=readiness_override,
        ),
        title="Proposal decision",
        output_format=output_format,
        preview=not preview_token,
    )


def _decision_request(
    *,
    proposal_id: str,
    event_type: ProposalDecisionEventType,
    reason: str,
    actor: str,
    executor_actor: str = "",
    executor_kind: str = "person",
    decided_on: str = "",
    operation_key: str = "",
    source_head_event_id: str = "",
    condition: list[str] | None = None,
    conditions_file: Path | None = None,
    lineage_kind: str = "",
    lineage_target: list[str] | None = None,
    affected_event_id: str = "",
    revocation_event_id: str = "",
    impact_preview_token: str = "",
    acknowledge_drift: bool = False,
    override_readiness: bool = False,
    authority_context: Path | None = None,
) -> ProposalDecisionRequest:
    conditions = _conditions(condition or [], conditions_file)
    kind = None
    if lineage_kind:
        try:
            kind = ProposalDecisionLineageKind(lineage_kind)
        except ValueError as exc:
            raise ValueError(
                "Lineage kind must be supersedes, split, or merged_into."
            ) from exc
    return ProposalDecisionRequest(
        proposal_id=proposal_id,
        event_type=event_type,
        reason=reason,
        actor_id=actor,
        executor_actor_id=executor_actor or actor,
        executor_kind=executor_kind,
        channel="cli",
        decided_on=decided_on,
        operation_key=operation_key,
        source_head_event_id=source_head_event_id or None,
        conditions=conditions,
        lineage=ProposalDecisionLineage(
            kind=kind,
            targets=tuple(lineage_target or ()),
        ),
        affected_event_id=affected_event_id or None,
        revocation_event_id=revocation_event_id or None,
        impact_preview_token=impact_preview_token or None,
        drift_acknowledged=acknowledge_drift,
        readiness_override=override_readiness,
        authority_context=(
            AuthorityContractCodec().context_from_path(authority_context)
            if authority_context is not None
            else None
        ),
    )


def _conditions(
    inline: list[str],
    path: Path | None,
) -> tuple[ProposalDecisionCondition, ...]:
    values: list[ProposalDecisionCondition] = []
    for item in inline:
        condition_id, separator, text = item.partition("=")
        if not separator or not condition_id.strip() or not text.strip():
            raise ValueError(
                "Each --condition must use the form CONDITION-ID=condition text."
            )
        values.append(
            ProposalDecisionCondition(condition_id.strip(), text.strip())
        )
    if path is not None:
        try:
            payload = load_yaml(path.read_bytes())
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"Cannot read conditions file: {exc}") from exc
        if isinstance(payload, Mapping):
            payload = payload.get("conditions")
        if not isinstance(payload, list):
            raise ValueError(
                "Conditions file must contain a list or a `conditions` list."
            )
        for item in payload:
            if not isinstance(item, Mapping):
                raise ValueError("Each file-backed condition must be a mapping.")
            condition_id = str(item.get("id") or "").strip()
            text = str(item.get("text") or "").strip()
            if not condition_id or not text:
                raise ValueError("Each file-backed condition requires id and text.")
            values.append(ProposalDecisionCondition(condition_id, text))
    return tuple(values)


def _warn_if_readiness_is_weak(
    workspace: P2PWorkspace,
    proposal_id: str,
    *,
    output_format: str,
) -> None:
    if output_format.strip().lower() == "json":
        return
    try:
        readiness = workspace.read_proposal_readiness(proposal_id)
    except ValueError:
        return
    if (
        readiness.status == "not_assessed"
        or readiness.computed_score is None
        or readiness.computed_score < 85
        or bool(readiness.failed_gates)
    ):
        console.print(
            "[yellow]Warning: proposal readiness is below the decision target. "
            "Use --override-readiness to bind an owner override atomically.[/yellow]"
        )


def _read_operation(
    operation: Callable[[], dict[str, object]],
    *,
    title: str,
    output_format: str,
) -> None:
    try:
        payload = operation()
    except ValueError as exc:
        _emit_error(exc, output_format=output_format, operation=title)
    _emit_payload(title, payload, output_format)


def _mutation_operation(
    operation: Callable[[], object],
    *,
    title: str,
    output_format: str,
    preview: bool = False,
) -> None:
    try:
        result = operation()
    except ValueError as exc:
        _emit_error(exc, output_format=output_format, operation=title)
    payload = result.to_dict()
    if preview:
        payload = {"status": "preview_required", **payload}
    _emit_payload(title, payload, output_format)
    status = str(payload.get("status") or "")
    if not preview and status not in {"applied", "already_applied"}:
        raise typer.Exit(code=1)


def _emit_payload(
    title: str,
    payload: Mapping[str, object],
    output_format: str,
) -> None:
    normalized = output_format.strip().lower()
    if normalized == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if normalized != "text":
        raise typer.BadParameter("Output format must be text or json.")
    console.print(title)
    for key in (
        "status",
        "proposal_id",
        "effective_state",
        "head_event_type",
        "head_event_id",
        "event_count",
        "total_count",
        "returned_count",
        "next_cursor",
        "preview_token",
    ):
        if payload.get(key) not in (None, ""):
            console.print(f"  {key}: {payload[key]}")
    request = payload.get("request")
    if isinstance(request, Mapping):
        for key in (
            "proposal_id",
            "event_type",
            "decided_on",
            "operation_key",
            "source_head_event_id",
        ):
            if request.get(key) not in (None, ""):
                console.print(f"  {key}: {request[key]}")
    preview = payload.get("preview")
    if isinstance(preview, Mapping) and preview.get("preview_token"):
        console.print(f"  preview_token: {preview['preview_token']}")
    lifecycle = payload.get("lifecycle")
    if isinstance(lifecycle, Mapping):
        console.print(f"  effective_state: {lifecycle.get('effective_state')}")
        console.print(f"  head_event_id: {lifecycle.get('head_event_id')}")
    items = payload.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, Mapping):
                console.print(
                    "  - "
                    + " | ".join(
                        str(item.get(key))
                        for key in ("event_type", "decided_on", "event_id")
                        if item.get(key)
                    )
                )


def _emit_error(
    error: ValueError,
    *,
    output_format: str,
    operation: str,
) -> None:
    message = str(error)
    match = re.search(r"\b(P2P[0-9]{3}_[A-Z0-9_]+)\b", message)
    definition = proposal_decision_diagnostic(message)
    payload = {
        "status": "error",
        "code": match.group(1) if match else "P2P_DECISION_ERROR",
        "operation": operation,
        "message": message,
        "mutation_performed": False,
        "recovery": definition.recovery if definition is not None else "",
    }
    if output_format.strip().lower() == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=1)

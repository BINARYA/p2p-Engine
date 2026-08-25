from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from p2p_engine.core.authority import AuthorityMode
from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionCondition,
    ProposalDecisionEventType,
    ProposalDecisionLineage,
    ProposalDecisionLineageKind,
    ProposalDecisionRequest,
)
from p2p_engine.mcp.consent_audit import consume_consent_with_audit
from p2p_engine.mcp.handlers.common import required, to_jsonable
from p2p_engine.foundation.yaml_loaders import load_yaml
from p2p_engine.services.authority import AuthorityContractCodec
from p2p_engine.storage.filesystem import P2PWorkspace


_PREFIX = "p2p_proposal_decision_"


def handle_proposal_decision_tool(
    workspace: P2PWorkspace,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, object] | None:
    if not name.startswith(_PREFIX):
        return None
    proposal_id = required(arguments, "proposal_id")
    if name == f"{_PREFIX}status":
        return {"proposal_decision": workspace.proposal_decision_status(proposal_id).to_dict()}
    if name == f"{_PREFIX}history":
        return {
            "proposal_decision_history": workspace.proposal_decision_history(
                proposal_id,
                limit=_bounded_limit(arguments),
                cursor=_optional_text(arguments, "cursor"),
            ).to_dict()
        }
    if name == f"{_PREFIX}impact":
        event_type = _event_type(arguments)
        snapshot = workspace.proposal_decision_impact(
            proposal_id,
            event_type=event_type,
            source_head_event_id=_optional_text(
                arguments,
                "source_head_event_id",
            ),
        )
        page = workspace.proposal_decision_impact_page(
            snapshot,
            limit=_bounded_limit(arguments),
            cursor=_optional_text(arguments, "cursor"),
        )
        return {
            "proposal_decision_impact": {
                **page.to_dict(),
                "event_type": event_type.value,
                "source_fingerprint_sha256": snapshot.source_fingerprint_sha256,
                "preview_token": snapshot.preview_token,
                "kind_counts": dict(snapshot.kind_counts),
                "status_counts": dict(snapshot.status_counts),
            }
        }
    if name == f"{_PREFIX}preview":
        return {
            "proposal_decision_preview": workspace.preview_proposal_decision(
                _request(arguments)
            ).to_dict()
        }
    if name == f"{_PREFIX}apply":
        request = _request(arguments)
        return _apply_with_consent(
            workspace,
            arguments,
            proposal_id=proposal_id,
            apply=lambda: workspace.apply_proposal_decision(
                request,
                preview_token=required(arguments, "preview_token"),
                confirm=_required_true(arguments, "confirm"),
            ),
            external_authority=(
                request.authority_context is not None
                and request.authority_context.mode
                == AuthorityMode.external_attestation
            ),
        )
    if name == f"{_PREFIX}projection_repair_preview":
        return {
            "proposal_decision_projection_repair_preview": (
                workspace.preview_proposal_decision_projection_repair(
                    proposal_id,
                    actor_id=required(arguments, "owner_id"),
                    executor_actor_id=required(arguments, "actor_id"),
                ).to_dict()
            )
        }
    if name == f"{_PREFIX}projection_repair_apply":
        return _apply_with_consent(
            workspace,
            arguments,
            proposal_id=proposal_id,
            apply=lambda: workspace.apply_proposal_decision_projection_repair(
                proposal_id,
                actor_id=required(arguments, "owner_id"),
                executor_actor_id=required(arguments, "actor_id"),
                preview_token=required(arguments, "preview_token"),
                confirm=_required_true(arguments, "confirm"),
            ),
            wrapper="proposal_decision_projection_repair",
        )
    if name == f"{_PREFIX}ledger_repair_preview":
        return {
            "proposal_decision_ledger_repair_preview": (
                workspace.preview_proposal_decision_ledger_repair(
                    proposal_id,
                    candidate_path=_candidate_path(workspace, arguments),
                    actor_id=required(arguments, "owner_id"),
                    executor_actor_id=required(arguments, "actor_id"),
                ).to_dict()
            )
        }
    if name == f"{_PREFIX}ledger_repair_apply":
        return _apply_with_consent(
            workspace,
            arguments,
            proposal_id=proposal_id,
            apply=lambda: workspace.apply_proposal_decision_ledger_repair(
                proposal_id,
                candidate_path=_candidate_path(workspace, arguments),
                actor_id=required(arguments, "owner_id"),
                executor_actor_id=required(arguments, "actor_id"),
                preview_token=required(arguments, "preview_token"),
                confirm=_required_true(arguments, "confirm"),
            ),
            wrapper="proposal_decision_ledger_repair",
        )
    return None


def convenience_preview(
    workspace: P2PWorkspace,
    arguments: dict[str, Any],
    *,
    event_type: ProposalDecisionEventType,
) -> dict[str, object]:
    values = dict(arguments)
    values["event_type"] = event_type.value
    values.setdefault("owner_id", _project_owner_id(workspace))
    preview = workspace.preview_proposal_decision(_request(values))
    return {
        "status": "preview_required",
        "required_consent": {
            "operation": "proposal_decision_apply",
            "target": (
                f"{preview.request.proposal_id}@"
                f"{preview.mutation.preview_token}"
            ),
        },
        "proposal_decision_preview": preview.to_dict(),
        "governance": {
            "owner_decision_required": True,
            "decision_made": False,
        },
    }


def _project_owner_id(workspace: P2PWorkspace) -> str:
    permissions = workspace.permissions_show()
    identities = permissions.get("identities")
    if not isinstance(identities, Mapping):
        raise ValueError(
            "P2P364_DECISION_OWNER_REQUIRED: project permissions do not "
            "declare an owner."
        )
    owners = sorted(
        str(actor_id)
        for actor_id, identity in identities.items()
        if isinstance(identity, Mapping) and identity.get("role") == "owner"
    )
    if len(owners) != 1:
        raise ValueError(
            "P2P364_DECISION_OWNER_REQUIRED: decision convenience preview "
            "requires exactly one declared project owner."
        )
    return owners[0]


def _request(
    arguments: Mapping[str, Any],
) -> ProposalDecisionRequest:
    owner_id = required(arguments, "owner_id")
    actor_id = required(arguments, "actor_id")
    return ProposalDecisionRequest(
        proposal_id=required(arguments, "proposal_id"),
        event_type=_event_type(arguments),
        reason=required(arguments, "reason"),
        actor_id=owner_id,
        executor_actor_id=actor_id,
        executor_kind=str(arguments.get("executor_kind") or "person"),
        channel="mcp",
        decided_on=str(arguments.get("decided_on") or ""),
        operation_key=str(arguments.get("operation_key") or ""),
        source_head_event_id=_optional_text(arguments, "source_head_event_id"),
        conditions=_conditions(arguments),
        lineage=_lineage(arguments),
        affected_event_id=_optional_text(arguments, "affected_event_id"),
        revocation_event_id=_optional_text(arguments, "revocation_event_id"),
        impact_preview_token=_optional_text(arguments, "impact_preview_token"),
        drift_acknowledged=_bool(arguments, "drift_acknowledged"),
        readiness_override=_bool(arguments, "readiness_override"),
        authority_context=(
            AuthorityContractCodec().context_from_mapping(
                _authority_context_mapping(arguments)
            )
            if arguments.get("authority_context") is not None
            else None
        ),
    )


def _apply_with_consent(
    workspace: P2PWorkspace,
    arguments: Mapping[str, Any],
    *,
    proposal_id: str,
    apply: Callable[[], object],
    wrapper: str = "proposal_decision",
    external_authority: bool = False,
) -> dict[str, object]:
    preview_token = required(arguments, "preview_token")
    actor_id = required(arguments, "actor_id")
    consent_id = required(arguments, "consent_id")
    target = f"{proposal_id}@{preview_token}"
    receipt = workspace.consent_show(consent_id)
    event_binding_required = wrapper == "proposal_decision"
    operation_key = (
        required(arguments, "operation_key")
        if event_binding_required
        else None
    )
    if receipt.status == "consumed":
        stored = _consent_result(workspace, receipt.path)
        _validate_consumed_receipt(
            receipt,
            stored,
            actor_id=actor_id,
            target=target,
            preview_token=preview_token,
            proposal_id=proposal_id,
            operation_key=operation_key,
            event_binding_required=event_binding_required,
        )
        return {
            wrapper: stored,
            "consent": to_jsonable(receipt),
            "governance": {
                "owner_decision_required": True,
                "decision_made": True,
                "replayed": True,
            },
        }
    try:
        workspace.consent_validate(
            consent_id,
            operation="proposal_decision_apply",
            target=target,
            actor_id=actor_id,
        )
    except ValueError as exc:
        raise ValueError(
            f"P2P374_DECISION_CONSENT_MISMATCH: {exc}"
        ) from exc
    if not external_authority:
        _validate_current_consent_approver(workspace, receipt)
    before_head = workspace.proposal_decision_status(proposal_id).head_event_id
    try:
        result = apply()
    except ValueError as exc:
        after_head = workspace.proposal_decision_status(proposal_id).head_event_id
        if before_head != after_head:
            workspace.consent_mark_used_with_error(
                consent_id,
                error=str(exc),
                result={
                    "operation": "proposal_decision_apply",
                    "target": target,
                    "actor_id": actor_id,
                    "head_before": before_head,
                    "head_after": after_head,
                },
            )
        raise
    payload = result.to_dict()
    status = str(payload.get("status") or "")
    if status not in {"applied", "already_applied"}:
        return {
            wrapper: payload,
            "consent": to_jsonable(receipt),
            "governance": {
                "owner_decision_required": True,
                "decision_made": False,
            },
        }
    binding = {
        **payload,
        "operation": "proposal_decision_apply",
        "target": target,
        "actor_id": actor_id,
        "preview_token": preview_token,
    }
    consumed = consume_consent_with_audit(
        workspace,
        consent_id,
        result=binding,
    )
    event = payload.get("event")
    event_mapping = event if isinstance(event, Mapping) else {}
    authority = event_mapping.get("authority")
    authority_mapping = authority if isinstance(authority, Mapping) else {}
    subject = authority_mapping.get("subject")
    executor = authority_mapping.get("executor")
    subject_mapping = subject if isinstance(subject, Mapping) else {}
    executor_mapping = executor if isinstance(executor, Mapping) else {}
    return {
        wrapper: payload,
        "consent": to_jsonable(consumed),
        "governance": {
            "owner_decision_required": True,
            "decision_made": True,
            "subject_id": subject_mapping.get("id"),
            "executor_id": executor_mapping.get("id"),
            "authority_id": authority_mapping.get("authority_id"),
            "authority_mode": authority_mapping.get("mode"),
        },
    }


def _authority_context_mapping(
    arguments: Mapping[str, Any],
) -> Mapping[str, object]:
    value = arguments.get("authority_context")
    if not isinstance(value, Mapping):
        raise ValueError("authority_context must be an object")
    return value


def _validate_consumed_receipt(
    receipt: object,
    result: Mapping[str, object],
    *,
    actor_id: str,
    target: str,
    preview_token: str,
    proposal_id: str,
    operation_key: str | None,
    event_binding_required: bool,
) -> None:
    invalid = (
        getattr(receipt, "operation", "") != "proposal_decision_apply"
        or getattr(receipt, "target", "") != target
        or getattr(receipt, "actor_id", "") != actor_id
        or result.get("target") != target
        or result.get("actor_id") != actor_id
        or result.get("preview_token") != preview_token
        or str(result.get("status") or "") not in {"applied", "already_applied"}
    )
    if event_binding_required:
        event = result.get("event")
        lifecycle = result.get("lifecycle")
        event_mapping = event if isinstance(event, Mapping) else {}
        lifecycle_mapping = lifecycle if isinstance(lifecycle, Mapping) else {}
        mutation = event_mapping.get("mutation")
        mutation_mapping = mutation if isinstance(mutation, Mapping) else {}
        event_id = str(event_mapping.get("event_id") or "")
        invalid = invalid or (
            event_mapping.get("proposal_id") != proposal_id
            or event_mapping.get("operation_key") != operation_key
            or mutation_mapping.get("preview_token") != preview_token
            or not event_id
            or lifecycle_mapping.get("head_event_id") != event_id
        )
    if invalid:
        raise ValueError(
            "P2P374_DECISION_CONSENT_MISMATCH: consumed consent receipt does "
            "not match the committed decision result."
        )


def _validate_current_consent_approver(
    workspace: P2PWorkspace,
    receipt: object,
) -> None:
    permissions = workspace.permissions_show()
    identities = permissions.get("identities")
    approver_id = str(getattr(receipt, "approved_by", "") or "")
    approver = (
        identities.get(approver_id)
        if isinstance(identities, Mapping)
        else None
    )
    if not isinstance(approver, Mapping) or approver.get("role") != "owner":
        raise ValueError(
            "P2P374_DECISION_CONSENT_MISMATCH: consent approver is no longer "
            "a current project owner."
        )


def _consent_result(
    workspace: P2PWorkspace,
    relative_path: Path,
) -> Mapping[str, object]:
    payload = load_yaml((workspace.root / relative_path).read_bytes())
    if not isinstance(payload, Mapping):
        return {}
    result = payload.get("result")
    return result if isinstance(result, Mapping) else {}


def _event_type(arguments: Mapping[str, Any]) -> ProposalDecisionEventType:
    try:
        return ProposalDecisionEventType(required(arguments, "event_type"))
    except ValueError as exc:
        raise ValueError("Invalid proposal decision event type.") from exc


def _conditions(
    arguments: Mapping[str, Any],
) -> tuple[ProposalDecisionCondition, ...]:
    raw = arguments.get("conditions") or []
    if not isinstance(raw, list):
        raise ValueError("Expected list argument: conditions")
    values: list[ProposalDecisionCondition] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("Each decision condition must be an object.")
        values.append(
            ProposalDecisionCondition(
                condition_id=required(item, "id"),
                text=required(item, "text"),
            )
        )
    return tuple(values)


def _lineage(arguments: Mapping[str, Any]) -> ProposalDecisionLineage:
    raw = arguments.get("lineage")
    if raw is None:
        return ProposalDecisionLineage()
    if not isinstance(raw, Mapping):
        raise ValueError("Expected object argument: lineage")
    kind_value = raw.get("kind")
    kind = (
        ProposalDecisionLineageKind(str(kind_value))
        if kind_value not in (None, "")
        else None
    )
    targets = raw.get("targets") or []
    if not isinstance(targets, list):
        raise ValueError("Expected list argument: lineage.targets")
    return ProposalDecisionLineage(
        kind=kind,
        targets=tuple(str(item) for item in targets),
    )


def _bounded_limit(arguments: Mapping[str, Any]) -> int:
    value = arguments.get("limit", 20)
    if isinstance(value, bool):
        raise ValueError("Limit must be an integer.")
    try:
        limit = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Limit must be an integer.") from exc
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100.")
    return limit


def _required_true(arguments: Mapping[str, Any], name: str) -> bool:
    if not _bool(arguments, name):
        return False
    return True


def _bool(arguments: Mapping[str, Any], name: str) -> bool:
    value = arguments.get(name)
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _optional_text(arguments: Mapping[str, Any], name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _candidate_path(
    workspace: P2PWorkspace,
    arguments: Mapping[str, Any],
) -> Path:
    path = Path(required(arguments, "candidate_path"))
    return path if path.is_absolute() else workspace.root / path

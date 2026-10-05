from __future__ import annotations

from pathlib import Path

from p2p_engine.cli_contract import contract_failure, print_json
from p2p_engine.cli_shared import workspace
from p2p_engine.core.authority import AuthorityMode
from p2p_engine.services.authority import AuthorityContractCodec


def question_error_message(error: ValueError) -> str:
    """Map reused legacy diagnostics to the current machine error namespace."""
    text = str(error)
    codes = {
        "P2P340_": "P2P_QUESTION_INVALID",
        "P2P341_": "P2P_QUESTION_NOT_FOUND",
        "P2P342_": "P2P_QUESTION_TRANSITION_INVALID",
        "P2P343_": "P2P_AUTHORIZATION_DENIED",
        "P2P345_": "P2P_QUESTION_REVISION_CONFLICT",
        "P2P347_": "P2P_QUESTION_PRECONDITION_FAILED",
        "P2P349_": "P2P_QUESTION_CURSOR_STALE",
        "P2P353_": "P2P_QUESTION_LIMIT_INVALID",
    }
    for prefix, code in codes.items():
        if text.startswith(prefix):
            return f"{code}: {text.partition(':')[2].strip()}"
    return text


def keyed_question_mode(
    *,
    output_format: str,
    operation_key: str,
    authority_context: Path | None,
    executor: str,
    root: Path | None = None,
    executor_kind: str = "person",
) -> bool:
    keyed = bool(operation_key or authority_context or executor or executor_kind != "person")
    if keyed and output_format.strip().lower() != "json":
        contract_failure(
            "P2P_QUESTION_JSON_REQUIRED: typed keyed question operations require --format json"
        )
    if keyed and not operation_key.strip():
        contract_failure(
            "P2P_IDEMPOTENCY_KEY_REQUIRED: typed question operations require --operation-key"
        )
    if not keyed and output_format == "json" and root is not None:
        authority = workspace(root).question_contract_service().authority
        if (
            authority.path.exists()
            and authority.read_descriptor().mode == AuthorityMode.external_attestation
        ):
            contract_failure(
                "P2P_AUTHORITY_CONTEXT_REQUIRED: hosted question JSON mutations require a key and exact authority context"
            )
    return keyed


def emit_question_mutation(
    *,
    root: Path,
    scope: str,
    leaf: str,
    actor: str,
    operation_key: str,
    executor: str,
    executor_kind: str,
    authority_context: Path | None,
    **request: object,
) -> None:
    try:
        context = (
            AuthorityContractCodec().context_from_path(authority_context)
            if authority_context
            else None
        )
        result = (
            workspace(root)
            .question_contract_service()
            .mutate(
                scope=scope,
                leaf=leaf,
                operation_key=operation_key,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                authority_context=context,
                **request,
            )
        )
    except ValueError as exc:
        contract_failure(question_error_message(exc))
    print_json(result)


def emit_question_preview(
    *,
    root: Path,
    leaf: str,
    actor: str,
    operation_key: str,
    executor: str,
    executor_kind: str,
    authority_context: Path | None,
    question_ids: list[str] | None = None,
) -> None:
    try:
        context = (
            AuthorityContractCodec().context_from_path(authority_context)
            if authority_context
            else None
        )
        result = (
            workspace(root)
            .question_contract_service()
            .preview(
                leaf=leaf,
                operation_key=operation_key,
                actor_id=actor,
                executor_id=executor or actor,
                executor_kind=executor_kind,
                authority_context=context,
                question_ids=question_ids or (),
            )
        )
    except ValueError as exc:
        contract_failure(question_error_message(exc))
    print_json(result)

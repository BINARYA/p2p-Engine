from __future__ import annotations

import json
import os
import re
import sys
import traceback
from contextlib import redirect_stdout
from contextvars import ContextVar
from dataclasses import asdict, is_dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from typer.core import TyperGroup

try:  # Typer 0.27 vendors Click; older supported Typer versions do not.
    from typer import _click as _click
except ImportError:  # pragma: no cover - exercised by older dependency sets.
    import click as _click  # type: ignore[no-redef]


CLI_CONTRACT_VERSION = "p2p-cli/v1"
EXIT_INTERNAL = 1
EXIT_INVALID_REQUEST = 2
EXIT_CONFLICT = 3
EXIT_AUTHORIZATION = 4
EXIT_UNAVAILABLE = 5

_JSON_MODE: ContextVar[bool] = ContextVar("p2p_cli_json_mode", default=False)
_LINKED_FRESHNESS: ContextVar[object | None] = ContextVar(
    "p2p_cli_linked_freshness", default=None
)
_STABLE_CODE = re.compile(r"^\s*(P2P_[A-Z0-9_]+)\s*:")
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class CliContractFailure(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: object | None = None,
        exit_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code or stable_error_code(message)
        self.details = {} if details is None else details
        self.exit_code = exit_code or exit_code_for_error(self.code)


class VersionedJSONTyperGroup(TyperGroup):
    """Apply the versioned transport contract at the outer CLI boundary."""

    def main(
        self,
        args: list[str] | tuple[str, ...] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: Any,
    ) -> Any:
        raw_args = list(args) if args is not None else list(sys.argv[1:])
        command_path, command = resolve_command(self, raw_args)
        freshness_token = _LINKED_FRESHNESS.set(None)
        worker_envelope = any(
            item == "--replication-command-envelope"
            or item.startswith("--replication-command-envelope=")
            for item in raw_args
        )
        if worker_envelope and not json_requested(raw_args, command):
            payload = error_envelope(
                ".".join(command_path) or "cli",
                code="P2P_REPLICATION_WORKER_JSON_REQUIRED",
                message=(
                    "The worker-only replication envelope requires the versioned JSON boundary."
                ),
            )
            try:
                return _emit_failure(payload, EXIT_INVALID_REQUEST, standalone_mode)
            finally:
                _LINKED_FRESHNESS.reset(freshness_token)
        if not json_requested(raw_args, command):
            try:
                return super().main(
                    args=args,
                    prog_name=prog_name,
                    complete_var=complete_var,
                    standalone_mode=standalone_mode,
                    windows_expand_args=windows_expand_args,
                    **extra,
                )
            finally:
                _LINKED_FRESHNESS.reset(freshness_token)

        operation = ".".join(command_path) or "cli"
        output = StringIO()
        token = _JSON_MODE.set(True)
        explicit_exit_code: int | None = None
        replication_receipt = None
        linked_freshness = None
        try:
            with redirect_stdout(output):
                result = super().main(
                    args=args,
                    prog_name=prog_name,
                    complete_var=complete_var,
                    standalone_mode=False,
                    windows_expand_args=windows_expand_args,
                    **extra,
                )
                if isinstance(result, int) and result != 0:
                    explicit_exit_code = result
        except CliContractFailure as exc:
            payload = error_envelope(
                operation,
                code=exc.code,
                message=str(exc),
                details=exc.details,
            )
            return _emit_failure(payload, exc.exit_code, standalone_mode)
        except _click.exceptions.ClickException as exc:
            payload = error_envelope(
                operation,
                code="P2P_CLI_INVALID_REQUEST",
                message=exc.format_message(),
                details=_click_error_details(exc),
            )
            return _emit_failure(payload, EXIT_INVALID_REQUEST, standalone_mode)
        except _click.exceptions.Exit as exc:
            return _handle_explicit_exit(
                output.getvalue(),
                operation=operation,
                original_exit_code=exc.exit_code,
                standalone_mode=standalone_mode,
            )
        except Exception as exc:  # noqa: BLE001 - this is the public transport boundary.
            if os.environ.get("P2P_CLI_DEBUG") == "1":
                traceback.print_exc(file=sys.stderr)
            payload = error_envelope(
                operation,
                code="P2P_CLI_INTERNAL_ERROR",
                message="Unexpected internal CLI failure.",
                details={"exception_type": type(exc).__name__},
            )
            return _emit_failure(payload, EXIT_INTERNAL, standalone_mode)
        finally:
            from p2p_engine.services.project_replication import (
                current_replication_receipt,
                set_replication_command,
            )

            replication_receipt = current_replication_receipt()
            linked_freshness = _LINKED_FRESHNESS.get()
            set_replication_command(None)
            _JSON_MODE.reset(token)
            _LINKED_FRESHNESS.reset(freshness_token)

        if explicit_exit_code is not None:
            return _handle_explicit_exit(
                output.getvalue(),
                operation=operation,
                original_exit_code=explicit_exit_code,
                standalone_mode=standalone_mode,
            )
        try:
            payload = _decode_handler_output(output.getvalue(), operation=operation)
        except CliContractFailure as exc:
            failure = error_envelope(
                operation,
                code=exc.code,
                message=str(exc),
                details=exc.details,
            )
            return _emit_failure(failure, exc.exit_code, standalone_mode)
        if is_envelope(payload):
            normalized = normalize_envelope(payload, operation=operation)
        else:
            normalized = success_envelope(operation, payload)
        # The receipt is produced by the same lock-protected filesystem commit
        # as a WaveKit-bound domain mutation.  Attach it only at the outer JSON
        # boundary; normal CLI payloads and agent-facing MCP remain unchanged.
        if replication_receipt is not None and normalized.get("ok") is True:
            data = normalized.get("data")
            if isinstance(data, dict):
                data = dict(data)
                data["replication_receipt"] = replication_receipt.to_dict()
            else:
                data = {
                    "result": data,
                    "replication_receipt": replication_receipt.to_dict(),
                }
            normalized = {**normalized, "data": data}
        if linked_freshness is not None and normalized.get("ok") is True:
            to_dict = getattr(linked_freshness, "to_dict", None)
            freshness_payload = to_dict() if callable(to_dict) else linked_freshness
            data = normalized.get("data")
            if isinstance(data, dict):
                data = dict(data)
                data.setdefault("linked_replica_freshness", freshness_payload)
            else:
                data = {
                    "result": data,
                    "linked_replica_freshness": freshness_payload,
                }
            normalized = {**normalized, "data": data}
        print_json(normalized)
        return result


def success_envelope(
    operation: str,
    data: object,
    *,
    warnings: list[object] | None = None,
) -> dict[str, object]:
    return {
        "contract_version": CLI_CONTRACT_VERSION,
        "ok": True,
        "operation": operation,
        "data": data,
        "warnings": list(warnings or []),
        "error": None,
    }


def error_envelope(
    operation: str,
    *,
    code: str,
    message: str,
    details: object | None = None,
    warnings: list[object] | None = None,
) -> dict[str, object]:
    return {
        "contract_version": CLI_CONTRACT_VERSION,
        "ok": False,
        "operation": operation,
        "data": None,
        "warnings": list(warnings or []),
        "error": {
            "code": code,
            "message": message,
            "details": {} if details is None else details,
        },
    }


def json_text(payload: object) -> str:
    return json.dumps(to_jsonable(payload), sort_keys=True)


def print_json(payload: object) -> None:
    print(json_text(payload))


def json_mode_active() -> bool:
    return _JSON_MODE.get()


def set_linked_freshness(value: object | None) -> None:
    """Attach one linked preflight result to the current CLI response."""
    _LINKED_FRESHNESS.set(value)


def contract_failure(
    message: str,
    *,
    code: str | None = None,
    details: object | None = None,
    exit_code: int | None = None,
) -> None:
    raise CliContractFailure(
        message,
        code=code,
        details=details,
        exit_code=exit_code,
    )


def stable_error_code(message: str, *, fallback: str = "P2P_CLI_OPERATION_FAILED") -> str:
    match = _STABLE_CODE.match(message)
    return match.group(1) if match else fallback


def exit_code_for_error(code: str) -> int:
    normalized = code.upper()
    if normalized.startswith("P2P_CLI_") and any(
        marker in normalized for marker in ("INVALID", "MISSING", "USAGE")
    ):
        return EXIT_INVALID_REQUEST
    if any(marker in normalized for marker in ("AUTH", "PERMISSION", "FORBIDDEN", "CONSENT")):
        return EXIT_AUTHORIZATION
    if any(marker in normalized for marker in ("UNAVAILABLE", "TRANSPORT", "NETWORK", "REGISTRY_IO")):
        return EXIT_UNAVAILABLE
    if any(
        marker in normalized
        for marker in (
            "CONFLICT",
            "PRECONDITION",
            "MISMATCH",
            "DRIFT",
            "STALE",
            "LOCKED",
            "UNSUPPORTED_SCHEMA",
            "RECOVERY_REQUIRED",
        )
    ):
        return EXIT_CONFLICT
    if any(marker in normalized for marker in ("EMPTY", "INVALID", "MISSING", "NOT_FOUND", "REQUIRED")):
        return EXIT_INVALID_REQUEST
    return EXIT_INTERNAL


def resolve_command(root: object, args: list[str]) -> tuple[tuple[str, ...], object]:
    current = root
    remaining = list(args)
    path: list[str] = []
    while True:
        commands = getattr(current, "commands", None)
        if not isinstance(commands, dict) or not commands:
            return tuple(path), current
        match_index = next(
            (index for index, value in enumerate(remaining) if value in commands),
            None,
        )
        if match_index is None:
            return tuple(path), current
        name = remaining[match_index]
        path.append(name)
        current = commands[name]
        remaining = remaining[match_index + 1 :]


def json_requested(args: list[str], command: object) -> bool:
    if any(value in {"--help", "-h"} for value in args):
        return False
    for index, value in enumerate(args):
        if value == "--format" and index + 1 < len(args):
            return args[index + 1].strip().lower() == "json"
        if value.startswith("--format="):
            return value.partition("=")[2].strip().lower() == "json"
    for parameter in getattr(command, "params", ()):
        if "--format" in getattr(parameter, "opts", ()):
            return str(getattr(parameter, "default", "")).strip().lower() == "json"
    return False


def json_command_inventory(root: object) -> dict[str, str]:
    inventory: dict[str, str] = {}
    stack: list[tuple[tuple[str, ...], object]] = [((), root)]
    while stack:
        path, command = stack.pop()
        for parameter in getattr(command, "params", ()):
            if "--format" in getattr(parameter, "opts", ()):
                inventory[".".join(path)] = str(getattr(parameter, "default", "text"))
                break
        commands = getattr(command, "commands", None)
        if isinstance(commands, dict):
            stack.extend(((*path, name), child) for name, child in commands.items())
    return dict(sorted(inventory.items()))


def is_envelope(payload: object) -> bool:
    return isinstance(payload, dict) and {
        "contract_version",
        "ok",
        "operation",
        "data",
        "warnings",
        "error",
    }.issubset(payload)


def normalize_envelope(payload: dict[str, object], *, operation: str) -> dict[str, object]:
    warnings = payload.get("warnings")
    normalized_warnings = list(warnings) if isinstance(warnings, list) else []
    if payload.get("ok") is True:
        return success_envelope(operation, payload.get("data"), warnings=normalized_warnings)
    error = payload.get("error")
    error_payload = error if isinstance(error, dict) else {}
    return error_envelope(
        operation,
        code=str(error_payload.get("code") or "P2P_CLI_OPERATION_FAILED"),
        message=str(error_payload.get("message") or "CLI operation failed."),
        details=error_payload.get("details"),
        warnings=normalized_warnings,
    )


def _decode_handler_output(raw: str, *, operation: str) -> object:
    stripped = raw.strip()
    if not stripped:
        raise CliContractFailure(
            "JSON command produced no payload.",
            code="P2P_CLI_INVALID_JSON_OUTPUT",
            details={"operation": operation},
            exit_code=EXIT_INTERNAL,
        )
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise CliContractFailure(
            "JSON command produced non-JSON output.",
            code="P2P_CLI_INVALID_JSON_OUTPUT",
            details={"operation": operation, "line": exc.lineno, "column": exc.colno},
            exit_code=EXIT_INTERNAL,
        ) from exc


def _handle_explicit_exit(
    raw: str,
    *,
    operation: str,
    original_exit_code: int,
    standalone_mode: bool,
) -> Any:
    stripped = raw.strip()
    if stripped:
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            decoded = None
        if is_envelope(decoded):
            payload = normalize_envelope(decoded, operation=operation)
            error = payload.get("error")
            code = str(error.get("code")) if isinstance(error, dict) else "P2P_CLI_OPERATION_FAILED"
            return _emit_failure(payload, exit_code_for_error(code), standalone_mode)
        if isinstance(decoded, dict):
            code, message = _structured_failure_identity(decoded)
            payload = error_envelope(
                operation,
                code=code,
                message=message,
                details={"result": decoded},
            )
            return _emit_failure(payload, exit_code_for_error(code), standalone_mode)
    message = _plain_error_message(stripped) or "CLI operation failed."
    code = stable_error_code(message)
    payload = error_envelope(operation, code=code, message=message)
    exit_code = exit_code_for_error(code)
    if code == "P2P_CLI_OPERATION_FAILED" and original_exit_code not in {0, 1}:
        exit_code = original_exit_code
    return _emit_failure(payload, exit_code, standalone_mode)


def _emit_failure(payload: dict[str, object], exit_code: int, standalone_mode: bool) -> Any:
    print_json(payload)
    if standalone_mode:
        raise SystemExit(exit_code)
    raise _click.exceptions.Exit(exit_code)


def _click_error_details(exc: object) -> dict[str, object]:
    details: dict[str, object] = {"error_type": type(exc).__name__}
    parameter_hint = getattr(exc, "param_hint", None)
    if parameter_hint:
        details["parameter"] = parameter_hint
    context = getattr(exc, "ctx", None)
    command_path = getattr(context, "command_path", None)
    if command_path:
        details["command_path"] = command_path
    return details


def _plain_error_message(raw: str) -> str:
    value = _ANSI_ESCAPE.sub("", raw).strip()
    if value.lower().startswith("error:"):
        value = value.split(":", 1)[1].strip()
    return value


def _structured_failure_identity(payload: dict[str, object]) -> tuple[str, str]:
    candidates: list[dict[str, object]] = []
    direct_error = payload.get("error")
    if isinstance(direct_error, dict):
        candidates.append(direct_error)
    findings = payload.get("findings")
    if isinstance(findings, list):
        candidates.extend(
            item
            for item in findings
            if isinstance(item, dict) and str(item.get("severity", "error")) == "error"
        )
    errors = payload.get("errors")
    if isinstance(errors, list):
        candidates.extend(item for item in errors if isinstance(item, dict))
    for candidate in candidates:
        code = str(candidate.get("code") or candidate.get("error_code") or "").strip()
        message = str(candidate.get("message") or candidate.get("reason") or "").strip()
        if code:
            return code, message or "CLI operation failed."
    status = str(payload.get("status") or payload.get("state") or "").strip()
    code = stable_error_code(status)
    message = str(payload.get("message") or payload.get("reason") or "CLI operation failed.")
    return code, message


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value

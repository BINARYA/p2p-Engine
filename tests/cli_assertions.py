from __future__ import annotations

import json
from typing import Any

from p2p_engine.cli_contract import CLI_CONTRACT_VERSION


TRANSPORT_FIELDS = {
    "contract_version",
    "ok",
    "operation",
    "data",
    "warnings",
    "error",
}


def cli_envelope(result: Any, *, operation: str | None = None) -> dict[str, Any]:
    payload = json.loads(result.stdout)
    assert set(payload) == TRANSPORT_FIELDS
    assert payload["contract_version"] == CLI_CONTRACT_VERSION
    assert isinstance(payload["warnings"], list)
    if operation is not None:
        assert payload["operation"] == operation
    return payload


def cli_data(result: Any, *, operation: str | None = None) -> Any:
    payload = cli_envelope(result, operation=operation)
    assert payload["ok"] is True
    assert payload["error"] is None
    return payload["data"]


def cli_error(result: Any, *, operation: str | None = None) -> dict[str, Any]:
    payload = cli_envelope(result, operation=operation)
    assert payload["ok"] is False
    assert payload["data"] is None
    error = payload["error"]
    assert isinstance(error, dict)
    assert {"code", "message", "details"} == set(error)
    return error


def cli_failure_result(result: Any, *, operation: str | None = None) -> Any:
    error = cli_error(result, operation=operation)
    details = error["details"]
    assert isinstance(details, dict)
    assert "result" in details
    return details["result"]

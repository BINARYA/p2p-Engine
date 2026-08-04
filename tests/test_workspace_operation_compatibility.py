from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from p2p_engine.services.workspace_operation_compatibility import (
    WorkspaceOperationCompatibilityService,
)
from p2p_engine.storage.filesystem import P2PWorkspace


def _unsupported_status(tmp_path: Path):
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Unsupported operation", owner="owner")
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    payload = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    payload["workspace_schema"]["current_version"] = 2
    schema_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return workspace.workspace_schema_status()


def test_every_literal_facade_write_operation_is_classified() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src" / "p2p_engine" / "storage" / "filesystem.py").read_text(
        encoding="utf-8"
    )
    used = set(re.findall(r'_ensure_runtime_write_allowed\("([^"]+)"\)', source))
    classified = WorkspaceOperationCompatibilityService().operation_ids

    assert used
    assert used <= classified


def test_current_schema_allows_every_classified_operation(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Current operation", owner="owner")
    status = workspace.workspace_schema_status()
    service = WorkspaceOperationCompatibilityService()

    results = [service.check(operation_id, status) for operation_id in service.operation_ids]

    assert results
    assert all(result.allowed for result in results)
    assert all(result.required_minimum == 3 for result in results)
    assert all(result.required_maximum == 3 for result in results)


def test_non_current_schema_blocks_every_classified_write(tmp_path: Path) -> None:
    service = WorkspaceOperationCompatibilityService()
    status = _unsupported_status(tmp_path)

    results = [service.check(operation_id, status) for operation_id in service.operation_ids]

    assert results
    assert all(not result.allowed for result in results)
    assert all(not result.recoverable for result in results)
    assert all(result.diagnostic_code == "P2P_WORKSPACE_UNSUPPORTED_SCHEMA" for result in results)
    with pytest.raises(ValueError, match="P2P_WORKSPACE_UNSUPPORTED_SCHEMA"):
        results[0].require_allowed()


def test_unknown_write_operation_fails_closed(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Unknown operation", owner="owner")

    result = WorkspaceOperationCompatibilityService().check(
        "future_unclassified_write",
        workspace.workspace_schema_status(),
    )

    assert result.allowed is False
    assert result.recoverable is False
    with pytest.raises(ValueError, match="Unknown governed-write operation ids fail closed"):
        result.require_allowed()


def test_current_schema_rejects_definition_embedded_question_operations(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Current Definition",
        owner="owner",
        vertical_id="binarya/base_project@2.0.0",
    )
    patch = tmp_path / "legacy-question-patch.yml"
    patch.write_text(
        "project_definition_patch:\n"
        "  schema_version: 1\n"
        "  actor: owner\n"
        "  operations:\n"
        "    - op: add_open_question\n"
        "      section_id: vision\n"
        "      question: Legacy question\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=(
            "P2P352_LEGACY_DEFINITION_QUESTION_OPERATION.*"
            "p2p project readiness questions status"
        ),
    ):
        workspace.preview_project_definition_update(patch, actor="owner")

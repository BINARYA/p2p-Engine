from __future__ import annotations

import re
from pathlib import Path

import pytest

from p2p_engine.core.workspace_schema import (
    ALIGNMENT_DEGRADED,
    LAYOUT_AHEAD,
    WorkspaceSchemaStatus,
)
from p2p_engine.services.workspace_operation_compatibility import (
    WorkspaceOperationCompatibilityService,
)
from p2p_engine.storage.filesystem import P2PWorkspace


def _v1_status(tmp_path: Path):
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("V1 Operation", owner="owner")
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    payload = schema_path.read_text(encoding="utf-8").replace("current_version: 2", "current_version: 1")
    schema_path.write_text(payload, encoding="utf-8")
    (tmp_path / ".p2p" / "project" / "questions.yml").unlink()
    return workspace.workspace_schema_status()


def test_every_literal_facade_write_operation_is_classified() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src" / "p2p_engine" / "storage" / "filesystem.py").read_text(encoding="utf-8")
    used = set(re.findall(r'_ensure_runtime_write_allowed\("([^"]+)"\)', source))
    classified = WorkspaceOperationCompatibilityService().operation_ids

    assert used
    assert used <= classified


def test_v1_safe_operation_remains_allowed_and_v2_operation_is_actionable(tmp_path: Path) -> None:
    service = WorkspaceOperationCompatibilityService()
    status = _v1_status(tmp_path)

    assert service.check("proposal_create", status).allowed is True
    blocked = service.check("project_questions_answer", status)

    assert blocked.allowed is False
    assert blocked.required_minimum == 2
    assert "migrate plan --to 2" in blocked.suggested_command
    with pytest.raises(ValueError, match="P2P348_WORKSPACE_OPERATION_SCHEMA_REQUIRED"):
        blocked.require_allowed()


def test_unknown_write_operation_fails_closed(tmp_path: Path) -> None:
    result = WorkspaceOperationCompatibilityService().check("future_unclassified_write", _v1_status(tmp_path))

    assert result.allowed is False
    assert result.recoverable is False
    with pytest.raises(ValueError, match="Unknown governed-write operation ids fail closed"):
        result.require_allowed()


def test_v1_only_runtime_fixture_blocks_every_write_to_schema_v2_ahead() -> None:
    status = WorkspaceSchemaStatus(
        schema_path=".p2p/project/workspace-schema.yml",
        state="ahead_of_runtime",
        layout_status=LAYOUT_AHEAD,
        alignment_status=ALIGNMENT_DEGRADED,
        current_version=2,
        target_version=1,
    )

    blocked = WorkspaceOperationCompatibilityService().check("proposal_create", status)

    assert blocked.allowed is False
    assert blocked.recoverable is False
    assert "ahead" in blocked.reason
    assert blocked.suggested_command == "p2p workspace schema status --format json"
    with pytest.raises(ValueError, match="only current or explicitly upgradeable"):
        blocked.require_allowed()


def test_schema_v2_rejects_definition_embedded_question_operations(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("V2 Definition", owner="owner", vertical_id="base_project")
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

    with pytest.raises(ValueError, match="P2P352_LEGACY_DEFINITION_QUESTION_OPERATION"):
        workspace.preview_project_definition_update(patch, actor="owner")

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.workspace_schema import (
    ALIGNMENT_DEGRADED,
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    LAYOUT_CURRENT,
    LAYOUT_INVALID,
    LAYOUT_UNSUPPORTED,
)
from p2p_engine.services.workspace_schema import WorkspaceSchemaService
from p2p_engine.storage.filesystem import P2PWorkspace


def _write_schema(root: Path, workspace_schema: dict[str, object]) -> Path:
    path = root / ".p2p" / "project" / "workspace-schema.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"workspace_schema": workspace_schema}, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_missing_schema_is_unsupported_and_inspection_is_read_only(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    p2p_dir.mkdir()
    before = _tree_bytes(tmp_path)

    status = WorkspaceSchemaService(root=tmp_path, p2p_dir=p2p_dir).status()

    assert status.state == "unsupported_missing"
    assert status.layout_status == LAYOUT_UNSUPPORTED
    assert status.alignment_status == ALIGNMENT_DEGRADED
    assert status.inspectable is False
    assert "migration_required" not in status.to_dict()
    assert "upgrade_available" not in status.to_dict()
    assert status.findings[0].code == "P2P_WORKSPACE_UNSUPPORTED_SCHEMA"
    assert _tree_bytes(tmp_path) == before


def test_fresh_initialization_writes_current_schema(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    created = workspace.init_project("Current Project", owner="Davide")

    assert Path(".p2p/project/workspace-schema.yml") in created
    status = workspace.workspace_schema_status()
    assert status.state == "current"
    assert status.layout_status == LAYOUT_CURRENT
    assert status.schema is not None
    assert status.schema.baseline == "initialized_current"
    assert status.schema.initialized_by == "Davide"
    assert status.schema.current_version == CURRENT_WORKSPACE_SCHEMA_VERSION
    assert (tmp_path / ".p2p" / "project" / "questions.yml").exists()


def test_reinitializing_workspace_does_not_silently_recreate_missing_schema(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Unsupported Project")
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    schema_path.unlink()

    with pytest.raises(ValueError, match="P2P_WORKSPACE_UNSUPPORTED_SCHEMA"):
        workspace.init_project("Unsupported Project")

    assert not schema_path.exists()
    assert workspace.workspace_schema_status().layout_status == LAYOUT_UNSUPPORTED


def test_schema_parser_rejects_obsolete_history_and_unknown_fields(tmp_path: Path) -> None:
    base: dict[str, object] = {
        "contract_version": 1,
        "current_version": 3,
        "baseline": "initialized_current",
        "initialized_at": "2026-07-15",
        "initialized_by": "owner",
        "applied_migrations": [
            {
                "id": "bad-transition",
                "from": 2,
                "to": 2,
                "applied_at": "2026-07-15",
                "actor": "owner",
                "plan_fingerprint_sha256": "abc",
            }
        ],
    }
    _write_schema(tmp_path, base)
    service = WorkspaceSchemaService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    assert service.status().layout_status == LAYOUT_INVALID

    base.pop("applied_migrations")
    base["unknown"] = True
    _write_schema(tmp_path, base)
    assert service.status().layout_status == LAYOUT_INVALID


@pytest.mark.parametrize(
    ("contract_version", "schema_version"),
    [(2, 3), (1, 1), (1, 2), (1, 4)],
)
def test_every_non_current_contract_is_unsupported(
    tmp_path: Path,
    contract_version: int,
    schema_version: int,
) -> None:
    _write_schema(
        tmp_path,
        {
            "contract_version": contract_version,
            "current_version": schema_version,
            "baseline": "initialized_current",
            "initialized_at": "2026-07-15",
            "initialized_by": "owner",
        },
    )

    status = WorkspaceSchemaService(root=tmp_path, p2p_dir=tmp_path / ".p2p").status()

    assert status.layout_status == LAYOUT_UNSUPPORTED
    assert status.findings[0].code == "P2P_WORKSPACE_UNSUPPORTED_SCHEMA"
    assert "no in-runtime conversion" in status.findings[0].message


def test_unsupported_schema_blocks_governed_writes_without_mutation(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Current")
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    payload = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    payload["workspace_schema"]["current_version"] = 2
    schema_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    before = _tree_bytes(tmp_path)

    with pytest.raises(ValueError, match="P2P_WORKSPACE_UNSUPPORTED_SCHEMA"):
        workspace.create_proposal_with_details(
            "Blocked",
            problem="Unsupported schema must not mutate.",
            proposal="Reject the write.",
        )

    assert _tree_bytes(tmp_path) == before


def test_current_runtime_rejects_historical_audit_entries(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Historical audit")
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    payload = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    payload["workspace_schema"]["applied_migrations"] = []
    schema_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    before = _tree_bytes(tmp_path)

    status = workspace.workspace_schema_status()

    assert status.layout_status == LAYOUT_INVALID
    assert _tree_bytes(tmp_path) == before


def test_global_validation_reports_unsupported_schema_as_error(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Unsupported Validation")
    (tmp_path / ".p2p" / "project" / "workspace-schema.yml").unlink()

    result = workspace.validate()

    matching = [
        item for item in result.findings if item.code == "P2P_WORKSPACE_UNSUPPORTED_SCHEMA"
    ]
    assert len(matching) == 1
    assert matching[0].severity == "error"


def test_current_schema_validation_requires_valid_question_authority(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Question Validation",
        owner="owner",
        vertical_id="binarya/base_project@2.0.0",
    )
    questions_path = tmp_path / ".p2p" / "project" / "questions.yml"
    original = questions_path.read_bytes()

    questions_path.unlink()
    missing = workspace.validate()
    assert any(
        item.code == "P2P305_WORKSPACE_LAYOUT_MISSING"
        and item.path == Path(".p2p/project/questions.yml")
        for item in missing.findings
    )

    questions_path.write_bytes(original + b"unknown: true\n")
    malformed = workspace.validate()
    assert any(item.code == "P2P340_PROJECT_QUESTIONS_INVALID" for item in malformed.findings)


def test_current_schema_rejects_competing_definition_questions(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Definition Authority",
        owner="owner",
        vertical_id="binarya/base_project@2.0.0",
    )
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"
    payload = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
    payload["project_definition"]["sections"][0]["open_questions"] = [
        {"id": "Q001", "question": "Legacy?", "field_id": "summary", "status": "open"}
    ]
    definition_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    status = workspace.workspace_schema_status()

    assert any(
        item.code == "P2P354_EMBEDDED_PROJECT_QUESTIONS_PRESENT"
        for item in status.findings
    )


@pytest.mark.service
def test_schema_preflight_does_not_validate_every_proposal_ledger(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Preflight", owner="owner")
    proposal = workspace.create_proposal_with_details(
        "Broken ledger",
        problem="Exercise preflight separation.",
        proposal="Keep preflight bounded.",
    )
    proposal_dir = workspace._proposal_document_service().find_dir(proposal.proposal_id)
    (proposal_dir / "decision-events.yml").write_text("invalid: [\n", encoding="utf-8")

    preflight = workspace.workspace_schema_preflight()
    deep = workspace.workspace_schema_status()

    assert preflight.layout_status == LAYOUT_CURRENT
    assert preflight.current_version == CURRENT_WORKSPACE_SCHEMA_VERSION
    assert not hasattr(preflight, "findings")
    assert any(item.code == "P2P361_DECISION_LEDGER_INVALID" for item in deep.findings)

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.workspace_schema import (
    ALIGNMENT_DEGRADED,
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    LAYOUT_AHEAD,
    LAYOUT_CURRENT,
    LAYOUT_INVALID,
    LAYOUT_LEGACY,
    LAYOUT_UNSUPPORTED,
    LAYOUT_UPGRADEABLE,
)
from p2p_engine.services.workspace_migration_registry import (
    MigrationTransition,
    WorkspaceMigrationRegistry,
)
from p2p_engine.services.workspace_schema import WorkspaceSchemaService
from p2p_engine.storage.filesystem import P2PWorkspace


def _write_schema(root: Path, workspace_schema: dict[str, object]) -> Path:
    path = root / ".p2p" / "project" / "workspace-schema.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"workspace_schema": workspace_schema}, sort_keys=False), encoding="utf-8")
    return path


def test_schema_status_distinguishes_legacy_without_writing(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    p2p_dir.mkdir()
    before = tuple(sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")))

    status = WorkspaceSchemaService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        engine_version="0.2.0",
    ).status()

    after = tuple(sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")))
    assert status.state == "legacy_undeclared"
    assert status.layout_status == LAYOUT_LEGACY
    assert status.alignment_status == ALIGNMENT_DEGRADED
    assert status.transition_support is not None
    assert status.transition_support.apply is True
    assert after == before


def test_fresh_initialization_writes_current_schema_last(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    created = workspace.init_project("Current Project", owner="Davide")

    assert Path(".p2p/project/workspace-schema.yml") in created
    status = workspace.workspace_schema_status()
    assert status.state == "current"
    assert status.layout_status == LAYOUT_CURRENT
    assert status.schema is not None
    assert status.schema.baseline == "initialized_current"
    assert status.schema.initialized_by == "Davide"
    assert status.schema.applied_migrations == ()
    assert status.schema.current_version == CURRENT_WORKSPACE_SCHEMA_VERSION
    assert (tmp_path / ".p2p" / "project" / "questions.yml").exists()


def test_reinitializing_legacy_workspace_does_not_adopt_current_schema(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Legacy Project")
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    schema_path.unlink()

    workspace.init_project("Legacy Project")

    assert not schema_path.exists()
    assert workspace.workspace_schema_status().layout_status == LAYOUT_LEGACY


def test_schema_parser_rejects_unknown_and_non_contiguous_history(tmp_path: Path) -> None:
    base: dict[str, object] = {
        "contract_version": 1,
        "current_version": 1,
        "baseline": "migrated_legacy",
        "initialized_at": "2026-07-15",
        "initialized_by": "owner",
        "applied_migrations": [
            {
                "id": "workspace-legacy-to-v1",
                "from": 1,
                "to": 1,
                "applied_at": "2026-07-15",
                "actor": "owner",
                "plan_fingerprint_sha256": "abc",
            }
        ],
    }
    _write_schema(tmp_path, base)
    service = WorkspaceSchemaService(root=tmp_path, p2p_dir=tmp_path / ".p2p", engine_version="0.2.0")

    assert service.status().layout_status == LAYOUT_INVALID

    base["unknown"] = True
    _write_schema(tmp_path, base)
    assert service.status().layout_status == LAYOUT_INVALID


def test_schema_status_distinguishes_unsupported_contract_and_ahead_layout(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "contract_version": 2,
        "current_version": 1,
        "baseline": "initialized_current",
        "initialized_at": "2026-07-15",
        "initialized_by": "owner",
        "applied_migrations": [],
    }
    _write_schema(tmp_path, payload)
    service = WorkspaceSchemaService(root=tmp_path, p2p_dir=tmp_path / ".p2p", engine_version="0.2.0")
    assert service.status().layout_status == LAYOUT_UNSUPPORTED

    payload["contract_version"] = 1
    payload["current_version"] = CURRENT_WORKSPACE_SCHEMA_VERSION + 1
    _write_schema(tmp_path, payload)
    assert service.status().layout_status == LAYOUT_AHEAD


def test_declared_v1_is_valid_upgradeable_and_not_globally_blocked(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Upgradeable")
    payload = workspace.workspace_schema_status().schema
    assert payload is not None
    raw = payload.to_payload()["workspace_schema"]
    raw["current_version"] = 1
    raw["baseline"] = "initialized_current"
    (tmp_path / ".p2p" / "project" / "questions.yml").unlink()
    _write_schema(tmp_path, raw)

    status = workspace.workspace_schema_status()

    assert status.state == "upgrade_available"
    assert status.layout_status == LAYOUT_UPGRADEABLE
    assert status.alignment_status != ALIGNMENT_DEGRADED
    assert status.migration_required is False
    assert status.upgrade_available is True
    assert status.transition_support is not None
    assert status.transition_support.plan is True


def test_schema_history_rejects_unknown_migration(tmp_path: Path) -> None:
    payload = {
        "contract_version": 1,
        "current_version": 1,
        "baseline": "migrated_legacy",
        "initialized_at": "2026-07-15",
        "initialized_by": "owner",
        "applied_migrations": [
            {
                "id": "unknown",
                "from": "legacy_undeclared",
                "to": 1,
                "applied_at": "2026-07-15",
                "actor": "owner",
                "plan_fingerprint_sha256": "abc",
            }
        ],
    }
    _write_schema(tmp_path, payload)
    service = WorkspaceSchemaService(root=tmp_path, p2p_dir=tmp_path / ".p2p", engine_version="0.2.0")
    assert "Unknown workspace migration id" in service.status().findings[0].message


def test_registry_rejects_non_adjacent_duplicate_and_unknown_capability() -> None:
    with pytest.raises(ValueError, match="adjacent"):
        WorkspaceMigrationRegistry(
            [MigrationTransition("bad", 0, 2, ">=0.2", ">=0.2", ">=0.2", ())],
            current_version=2,
        )

    duplicate = MigrationTransition("same", 0, 1, ">=0.2", ">=0.2", ">=0.2", ())
    with pytest.raises(ValueError, match="Duplicate"):
        WorkspaceMigrationRegistry([duplicate, duplicate])

    with pytest.raises(ValueError, match="Unknown workspace migration capabilities"):
        WorkspaceMigrationRegistry(
            [MigrationTransition("bad", 0, 1, ">=0.2", ">=0.2", ">=0.2", ("magic",))]
        )


def test_default_registry_resolves_adjacent_planning_handlers_and_enforces_ownership() -> None:
    registry = WorkspaceMigrationRegistry()

    handlers = registry.resolve_handlers(0, 2)

    assert [handler.planner_key for handler in handlers] == [
        "legacy_to_v1",
        "v1_to_v2_project_questions",
    ]
    assert all(callable(getattr(handler, "plan", None)) for handler in handlers)
    with pytest.raises(ValueError, match="does not own"):
        handlers[1].validate_candidate_targets([".p2p/project/permissions.yml"])
    with pytest.raises(ValueError, match="No selected.*owns"):
        registry.validate_candidate_ownership(
            ["workspace-v1-to-v2"],
            [".p2p/project/permissions.yml"],
        )


def test_default_registry_runtime_matrix_does_not_advertise_v2_to_the_v1_runtime() -> None:
    registry = WorkspaceMigrationRegistry()
    legacy = registry.transition_by_id("workspace-legacy-to-v1")
    v2 = registry.transition_by_id("workspace-v1-to-v2")

    assert legacy.runtime_support("0.2.0").apply is True
    assert legacy.runtime_support("0.3.0").apply is True
    assert v2.runtime_support("0.2.0").inspect is False
    assert v2.runtime_support("0.2.0").plan is False
    assert v2.runtime_support("0.2.0").apply is False
    assert v2.runtime_support("0.3.0").inspect is True
    assert v2.runtime_support("0.3.0").plan is True
    assert v2.runtime_support("0.3.0").apply is True


def test_global_validation_adds_legacy_schema_finding_without_error(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Legacy Validation")
    (tmp_path / ".p2p" / "project" / "workspace-schema.yml").unlink()

    result = workspace.validate()

    matching = [item for item in result.findings if item.code == "P2P300_WORKSPACE_SCHEMA_LEGACY_UNDECLARED"]
    assert len(matching) == 1
    assert matching[0].severity == "info"


def test_schema_v2_global_validation_requires_valid_question_authority(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Question Validation", owner="owner", vertical_id="base_project")
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


def test_schema_v2_global_validation_rejects_competing_definition_questions(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Definition Authority", owner="owner", vertical_id="base_project")
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"
    payload = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
    payload["project_definition"]["sections"][0]["open_questions"] = [
        {"id": "Q001", "question": "Legacy?", "field_id": "summary", "status": "open"}
    ]
    definition_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    result = workspace.validate()

    assert any(item.code == "P2P354_LEGACY_PROJECT_QUESTIONS_PRESENT" for item in result.findings)

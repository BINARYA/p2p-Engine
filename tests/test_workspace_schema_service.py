from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.workspace_schema import (
    ALIGNMENT_DEGRADED,
    LAYOUT_AHEAD,
    LAYOUT_CURRENT,
    LAYOUT_INVALID,
    LAYOUT_LEGACY,
    LAYOUT_UNSUPPORTED,
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
    payload["current_version"] = 2
    _write_schema(tmp_path, payload)
    assert service.status().layout_status == LAYOUT_AHEAD


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


def test_global_validation_adds_legacy_schema_finding_without_error(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Legacy Validation")
    (tmp_path / ".p2p" / "project" / "workspace-schema.yml").unlink()

    result = workspace.validate()

    matching = [item for item in result.findings if item.code == "P2P300_WORKSPACE_SCHEMA_LEGACY_UNDECLARED"]
    assert len(matching) == 1
    assert matching[0].severity == "info"

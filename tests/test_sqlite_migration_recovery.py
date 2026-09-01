from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from p2p_engine.core.project_state_storage import (
    ProjectStorageError,
    ProjectStorageErrorCode,
)
from p2p_engine.core.workspace_schema import LOCK_ABSENT
from p2p_engine.services.project_application import open_project_application
from p2p_engine.services.workspace_transactions import WorkspaceTransactionLockService
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.sqlite_adapter import SQLiteMigrationPort
from p2p_engine.storage.sqlite_project_state import SQLiteProjectStateRepository
from p2p_engine.storage.sqlite_recovery import SQLiteRecoveryCoordinator
from p2p_engine.storage.sqlite_schema import (
    SQLITE_DATABASE_PATH,
    SQLITE_MAINTENANCE_MARKER,
    SQLITE_SCHEMA_VERSION,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _initialize_preversioned(root: Path) -> tuple[str, str]:
    P2PWorkspace(root).init_project(
        "SQLite migration hard-crash recovery",
        owner="owner",
        agent_profile="generic",
        storage_adapter="sqlite",
    )
    snapshot = open_project_application(root).canonical_memory_snapshot()
    with sqlite3.connect(root / SQLITE_DATABASE_PATH) as connection:
        connection.execute("DELETE FROM schema_migrations")
        connection.execute("PRAGMA user_version = 0")
    return snapshot.project_uuid, snapshot.semantic_state_digest


def _run_crashing_migration(root: Path, stage: str) -> None:
    program = """
import os
import sys
from pathlib import Path

from p2p_engine.storage.sqlite_adapter import SQLiteMigrationPort
from p2p_engine.storage.sqlite_project_state import SQLiteProjectStateRepository

root = Path(sys.argv[1])
failure_stage = sys.argv[2]

def crash(stage: str) -> None:
    if stage == failure_stage:
        os._exit(91)

SQLiteMigrationPort(SQLiteProjectStateRepository(root)).migrate_to_current(
    backup_path=root / 'migration-source.p2pbackup',
    actor='owner',
    failure_injector=crash,
)
raise AssertionError('migration did not crash at the requested stage')
"""
    environment = dict(os.environ)
    source_root = str(_REPOSITORY_ROOT / "src")
    current_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        source_root
        if not current_pythonpath
        else os.pathsep.join((source_root, current_pythonpath))
    )
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(program), str(root), stage],
        cwd=_REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 91, (completed.stdout, completed.stderr)


def _database_state(root: Path) -> tuple[int, str, int]:
    with sqlite3.connect(root / SQLITE_DATABASE_PATH) as connection:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        maintenance = str(
            connection.execute(
                "SELECT maintenance_state FROM storage_metadata WHERE singleton = 1"
            ).fetchone()[0]
        )
        migrations = int(
            connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]
        )
    return version, maintenance, migrations


@pytest.mark.parametrize(
    "stage",
    (
        "after_migration_marker",
        "after_migration_fence",
        "after_migration_recovery",
        "after_migration_backup",
        "before_migration_commit",
        "after_migration_commit",
        "after_migration_verification",
        "before_migration_finalize",
    ),
)
def test_hard_exit_migration_rolls_back_through_public_recovery(
    tmp_path: Path,
    stage: str,
) -> None:
    project_uuid, semantic_digest = _initialize_preversioned(tmp_path)
    _run_crashing_migration(tmp_path, stage)

    marker_path = tmp_path / SQLITE_MAINTENANCE_MARKER
    payload = json.loads(marker_path.read_text(encoding="utf-8"))
    assert payload["contract"] == "p2p-sqlite-maintenance/v2"
    assert payload["operation"] == "schema-migration"
    assert payload["source_schema_version"] == 0
    assert payload["target_schema_version"] == SQLITE_SCHEMA_VERSION
    assert not Path(payload["stage"]).is_absolute()
    assert not Path(payload["recovery"]).is_absolute()

    coordinator = SQLiteRecoveryCoordinator(tmp_path)
    status = coordinator.status()
    assert status.state == "recovery_required"
    assert status.applicable is True
    assert status.operation == "schema-migration"
    assert status.source_project_uuid == project_uuid
    assert status.source_semantic_state_digest == semantic_digest

    result = coordinator.apply(
        recovery_id=status.recovery_id,
        recovery_token=status.recovery_token,
        actor="owner",
        action="rollback",
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert result.operation == "schema-migration"
    assert _database_state(tmp_path) == (0, "ready", 0)
    assert SQLiteProjectStateRepository(tmp_path).snapshot().semantic_state_digest == (
        semantic_digest
    )
    assert coordinator.status().state == "clean"
    assert WorkspaceTransactionLockService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
    ).status().state == LOCK_ABSENT

    replay = coordinator.apply(
        recovery_id=status.recovery_id,
        recovery_token=status.recovery_token,
        actor="owner",
        action="rollback",
        confirm=True,
    )
    assert replay.replayed is True

    migration = SQLiteMigrationPort(SQLiteProjectStateRepository(tmp_path))
    assert migration.migrate_to_current(
        backup_path=tmp_path / f"migration-retry-{stage}.p2pbackup",
        actor="owner",
    ) == "migrated"
    assert _database_state(tmp_path) == (SQLITE_SCHEMA_VERSION, "ready", 1)


def test_migration_recovery_requires_current_source_owner(tmp_path: Path) -> None:
    _initialize_preversioned(tmp_path)
    migration = SQLiteMigrationPort(SQLiteProjectStateRepository(tmp_path))

    def fail_after_recovery(stage: str) -> None:
        if stage == "after_migration_recovery":
            raise OSError(stage)

    with pytest.raises(OSError):
        migration.migrate_to_current(
            backup_path=tmp_path / "migration-owner.p2pbackup",
            actor="owner",
            failure_injector=fail_after_recovery,
        )

    coordinator = SQLiteRecoveryCoordinator(tmp_path)
    status = coordinator.status()
    with pytest.raises(ProjectStorageError) as raised:
        coordinator.apply(
            recovery_id=status.recovery_id,
            recovery_token=status.recovery_token,
            actor="contributor",
            action="rollback",
            confirm=True,
        )
    assert raised.value.code == ProjectStorageErrorCode.recovery_required
    assert coordinator.status().state == "recovery_required"

    coordinator.apply(
        recovery_id=status.recovery_id,
        recovery_token=status.recovery_token,
        actor="owner",
        action="rollback",
        confirm=True,
    )
    assert _database_state(tmp_path) == (0, "ready", 0)


def test_migration_call_rejects_non_owner_before_publishing_marker(
    tmp_path: Path,
) -> None:
    _initialize_preversioned(tmp_path)
    migration = SQLiteMigrationPort(SQLiteProjectStateRepository(tmp_path))

    with pytest.raises(ValueError, match="requires role `owner`"):
        migration.migrate_to_current(
            backup_path=tmp_path / "unauthorized.p2pbackup",
            actor="contributor",
        )

    assert not (tmp_path / SQLITE_MAINTENANCE_MARKER).exists()
    assert _database_state(tmp_path) == (0, "ready", 0)

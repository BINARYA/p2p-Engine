from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from dataclasses import replace
from pathlib import Path

import pytest

from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    ProjectStateMutation,
    ProjectStorageError,
    ProjectStorageErrorCode,
    ProjectStorageManifest,
)
from p2p_engine.foundation.files import write_bytes_atomic
from p2p_engine.services.project_application import (
    open_project_application,
    project_memory_recovery_apply,
    project_memory_recovery_status,
)
from p2p_engine.services.workspace_transactions import WorkspaceTransactionLockService
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.project_storage import (
    PROJECT_STORAGE_MANIFEST_PATH,
    ProjectStorageManifestStore,
)
from p2p_engine.storage.sqlite_initialization import SQLITE_ACTIVATION_MARKER
from p2p_engine.storage.sqlite_project_state import snapshot_digest
from p2p_engine.storage.sqlite_schema import (
    SQLITE_ADAPTER,
    SQLITE_DATABASE_PATH,
    SQLITE_MAINTENANCE_MARKER,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _initialize(root: Path, *, adapter: str = SQLITE_ADAPTER):
    P2PWorkspace(root).init_project(
        "SQLite hard crash recovery",
        owner="owner",
        agent_profile="generic",
        storage_adapter=adapter,
    )
    return open_project_application(root)


def _run_crashing_child(script: str, *arguments: object) -> None:
    environment = dict(os.environ)
    source_root = str(_REPOSITORY_ROOT / "src")
    current_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        source_root
        if not current_pythonpath
        else os.pathsep.join((source_root, current_pythonpath))
    )
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script), *(str(item) for item in arguments)],
        cwd=_REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 91, (completed.stdout, completed.stderr)


def _change_definition(app, operation_id: str):
    snapshot = app.canonical_memory_snapshot()
    entities = []
    for entity in snapshot.entities:
        if entity.technical_id != "project:definition":
            entities.append(entity)
            continue
        payload = dict(entity.payload)
        document = payload["document"]
        if isinstance(document, dict):
            document = {**document, "hard_crash_test": operation_id}
        else:
            document = f"{document}\n\n{operation_id}\n"
        payload["document"] = document
        entities.append(
            replace(
                entity,
                payload=payload,
                entity_version=entity.entity_version + 1,
            )
        )
    provisional = replace(
        snapshot,
        entities=tuple(entities),
        semantic_state_digest="0" * 64,
        source_revision={"kind": "local", "value": "0" * 64},
    )
    digest = snapshot_digest(provisional)
    target = replace(
        provisional,
        semantic_state_digest=digest,
        source_revision={"kind": "local", "value": digest},
    )
    with app.project_state_unit_of_work() as unit:
        unit.stage(
            ProjectStateMutation(
                operation_id=operation_id,
                actor="owner",
                expected_revision=app.project_state_revision(),
                target=target,
            )
        )
        unit.commit()
    return target


def _recover(root: Path):
    status = project_memory_recovery_status(root)
    assert status.state == "recovery_required"
    assert status.applicable is True
    result = project_memory_recovery_apply(
        root,
        recovery_id=status.recovery_id,
        recovery_token=status.recovery_token,
        actor="owner",
        confirm=True,
    )
    assert result.status == "rolled_back"
    assert project_memory_recovery_status(root).state == "clean"
    return result


@pytest.mark.parametrize(
    "failure_stage",
    (
        "after_restore_marker",
        "after_restore_stage",
        "after_restore_old_database_move",
        "after_restore_activation",
        "after_restore_receipt",
    ),
)
def test_restore_os_exit_is_explicitly_rolled_back(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    app = _initialize(tmp_path)
    archive = tmp_path / "restore-target.p2pbundle"
    app.canonical_bundle_export(archive)
    source = _change_definition(app, f"source-before-{failure_stage}")
    source_identity = app.project_identity()

    _run_crashing_child(
        """
        import os
        import sys
        from pathlib import Path
        from p2p_engine.services.project_application import open_project_application
        from p2p_engine.storage.sqlite_adapter import SQLiteBackupPort

        root, archive, stage = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
        app = open_project_application(root)
        def inject(current):
            if current == stage:
                os._exit(91)
        port = SQLiteBackupPort(app.adapter.repository, failure_injector=inject)
        key = f"hard-exit-restore-{stage}"
        preview = port.restore_preview(source=archive, operation_key=key, actor="owner")
        port.restore_apply(
            source=archive,
            operation_key=key,
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )
        """,
        tmp_path,
        archive,
        failure_stage,
    )

    _recover(tmp_path)
    reopened = open_project_application(tmp_path)
    assert reopened.project_identity() == source_identity
    assert reopened.canonical_memory_snapshot().semantic_state_digest == (
        source.semantic_state_digest
    )
    assert not (tmp_path / SQLITE_MAINTENANCE_MARKER).exists()


@pytest.mark.parametrize(
    "failure_stage",
    (
        "after_identity_stage",
        "after_identity_fence",
        "after_identity_backup",
        "after_identity_old_database_move",
        "after_identity_activation",
        "after_identity_manifest",
        "after_identity_auxiliary",
    ),
)
def test_identity_os_exit_restores_database_manifest_and_agent_surfaces(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    app = _initialize(tmp_path)
    before = app.canonical_memory_snapshot()
    identity = app.project_identity()
    manifest = (tmp_path / PROJECT_STORAGE_MANIFEST_PATH).read_bytes()
    surfaces = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in (
            tmp_path / "AGENTS.md",
            tmp_path / "P2P-SETUP.md",
            *(tmp_path / ".agents").rglob("*"),
        )
        if path.is_file() and not path.is_symlink()
    }

    _run_crashing_child(
        """
        import os
        import sys
        from pathlib import Path
        from p2p_engine.services.project_application import open_project_application

        root, stage = Path(sys.argv[1]), sys.argv[2]
        app = open_project_application(root)
        arguments = {
            "operation_key": f"hard-exit-identity-{stage}",
            "actor_id": "owner",
            "executor_id": "owner",
            "executor_kind": "person",
        }
        preview = app.preview_project_identity_derivation(**arguments)
        def inject(current):
            if current == stage:
                os._exit(91)
        app.adapter.repository.failure_injector = inject
        app.apply_project_identity_derivation(
            **arguments,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )
        """,
        tmp_path,
        failure_stage,
    )

    _recover(tmp_path)
    reopened = open_project_application(tmp_path)
    assert reopened.project_identity() == identity
    assert reopened.canonical_memory_snapshot().semantic_state_digest == (
        before.semantic_state_digest
    )
    assert (tmp_path / PROJECT_STORAGE_MANIFEST_PATH).read_bytes() == manifest
    assert {
        relative: (tmp_path / relative).read_bytes() for relative in surfaces
    } == surfaces
    assert not list((tmp_path / ".p2p/local").glob("sqlite-identity-*.stage"))


@pytest.mark.parametrize(
    "failure_stage",
    (
        "before_schema",
        "before_schema_commit",
        "after_sqlite_stage",
        "after_canonical_detach",
        "after_sqlite_activation",
        "after_activation_manifest",
    ),
)
def test_initial_activation_os_exit_restores_filesystem_authority(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    app = _initialize(tmp_path, adapter=FILESYSTEM_ADAPTER)
    before = app.canonical_memory_snapshot()
    identity = app.project_identity()
    write_bytes_atomic(
        tmp_path / PROJECT_STORAGE_MANIFEST_PATH,
        ProjectStorageManifestStore.render(
            ProjectStorageManifest(
                project_uuid=identity.project_uuid.value,
                adapter=SQLITE_ADAPTER,
            )
        ),
    )

    _run_crashing_child(
        """
        import os
        import sys
        from pathlib import Path
        from p2p_engine.storage.sqlite_initialization import activate_sqlite_from_filesystem

        root, stage = Path(sys.argv[1]), sys.argv[2]
        def inject(current):
            if current == stage:
                os._exit(91)
        activate_sqlite_from_filesystem(root, failure_injector=inject)
        """,
        tmp_path,
        failure_stage,
    )

    with pytest.raises(ProjectStorageError) as fenced:
        open_project_application(tmp_path)
    assert fenced.value.code == ProjectStorageErrorCode.recovery_required
    _recover(tmp_path)
    reopened = open_project_application(tmp_path)
    assert reopened.storage_selection().adapter == FILESYSTEM_ADAPTER
    assert reopened.canonical_memory_snapshot() == before
    assert not (tmp_path / SQLITE_DATABASE_PATH).exists()
    assert not (tmp_path / SQLITE_ACTIVATION_MARKER).exists()
    lock = WorkspaceTransactionLockService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    assert lock.status().state == "absent"


@pytest.mark.parametrize("recovery_stage", ("after_rollback", "after_completion"))
def test_recovery_os_exit_converges_on_next_owner_apply(
    tmp_path: Path,
    recovery_stage: str,
) -> None:
    app = _initialize(tmp_path)
    archive = tmp_path / "restore-target.p2pbundle"
    app.canonical_bundle_export(archive)
    source = _change_definition(app, f"source-before-recovery-{recovery_stage}")
    _run_crashing_child(
        """
        import os
        import sys
        from pathlib import Path
        from p2p_engine.services.project_application import open_project_application
        from p2p_engine.storage.sqlite_adapter import SQLiteBackupPort

        root, archive = Path(sys.argv[1]), Path(sys.argv[2])
        app = open_project_application(root)
        def inject(current):
            if current == "after_restore_old_database_move":
                os._exit(91)
        port = SQLiteBackupPort(app.adapter.repository, failure_injector=inject)
        preview = port.restore_preview(
            source=archive,
            operation_key="hard-exit-before-recovery",
            actor="owner",
        )
        port.restore_apply(
            source=archive,
            operation_key="hard-exit-before-recovery",
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )
        """,
        tmp_path,
        archive,
    )
    status = project_memory_recovery_status(tmp_path)

    _run_crashing_child(
        """
        import os
        import sys
        from pathlib import Path
        from p2p_engine.storage.sqlite_recovery import SQLiteRecoveryCoordinator

        root, recovery_id, token, stage = (
            Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
        )
        coordinator = SQLiteRecoveryCoordinator(root)
        if stage == "after_rollback":
            original = coordinator._rollback_database_maintenance
            def wrapped(marker, source):
                original(marker, source)
                os._exit(91)
            coordinator._rollback_database_maintenance = wrapped
        else:
            original = coordinator._write_completion
            def wrapped(marker, result):
                original(marker, result)
                os._exit(91)
            coordinator._write_completion = wrapped
        coordinator.apply(
            recovery_id=recovery_id,
            recovery_token=token,
            actor="owner",
            action="rollback",
            confirm=True,
        )
        """,
        tmp_path,
        status.recovery_id,
        status.recovery_token,
        recovery_stage,
    )

    result = _recover(tmp_path)
    assert result.semantic_state_digest == source.semantic_state_digest
    replay = project_memory_recovery_apply(
        tmp_path,
        recovery_id=status.recovery_id,
        recovery_token=status.recovery_token,
        actor="owner",
        confirm=True,
    )
    assert replay.replayed is True

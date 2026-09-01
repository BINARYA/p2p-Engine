from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.core.project_state_storage import (
    FILESYSTEM_ADAPTER,
    ProjectStateMutation,
    ProjectStorageError,
    ProjectStorageErrorCode,
)
from p2p_engine.services.project_application import (
    open_project_application,
    project_memory_recovery_status,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.sqlite_driver import SQLiteConnectionFactory
from p2p_engine.storage.sqlite_schema import (
    SQLITE_ACTIVATION_MARKER,
    SQLITE_ADAPTER,
    SQLITE_DATABASE_PATH,
    SQLITE_MAINTENANCE_MARKER,
)


def _initialize_sqlite(root: Path) -> None:
    P2PWorkspace(root).init_project(
        "SQLite authoritative path safety",
        owner="owner",
        agent_profile="generic",
        storage_adapter=SQLITE_ADAPTER,
    )
    assert open_project_application(root).storage_selection().adapter == SQLITE_ADAPTER


def _assert_reopen_rejected(root: Path) -> ProjectStorageError:
    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(root)
    assert raised.value.code in {
        ProjectStorageErrorCode.integrity_failure,
        ProjectStorageErrorCode.manifest_invalid,
    }
    return raised.value


def _symlink_or_skip(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:  # pragma: no cover - depends on Windows runner policy.
        pytest.skip(f"symlink creation is unavailable: {exc}")


def test_reopen_rejects_symlinked_storage_manifest(tmp_path: Path) -> None:
    _initialize_sqlite(tmp_path)
    manifest = tmp_path / ".p2p/local/storage.yml"
    external = tmp_path / "external-storage.yml"
    manifest.replace(external)
    _symlink_or_skip(manifest, external)

    error = _assert_reopen_rejected(tmp_path)

    assert "unsafe" in error.safe_message.lower()


def test_reopen_rejects_symlinked_database_leaf(tmp_path: Path) -> None:
    _initialize_sqlite(tmp_path)
    database = tmp_path / SQLITE_DATABASE_PATH
    external = tmp_path / "external.sqlite3"
    database.replace(external)
    _symlink_or_skip(database, external)

    error = _assert_reopen_rejected(tmp_path)

    assert "database" in error.safe_message.lower()


def test_reopen_rejects_symlinked_authoritative_parent(tmp_path: Path) -> None:
    _initialize_sqlite(tmp_path)
    local = tmp_path / ".p2p/local"
    external = tmp_path / "external-local"
    local.replace(external)
    _symlink_or_skip(local, external, directory=True)

    error = _assert_reopen_rejected(tmp_path)

    assert "manifest" in error.safe_message.lower()


def test_reopen_rejects_non_directory_manifest_parent(tmp_path: Path) -> None:
    _initialize_sqlite(tmp_path)
    local = tmp_path / ".p2p/local"
    displaced = tmp_path / "displaced-local"
    local.replace(displaced)
    local.write_text("not a directory\n", encoding="utf-8")

    error = _assert_reopen_rejected(tmp_path)

    assert "manifest" in error.safe_message.lower()
    assert "not a directory" in error.diagnostic.lower()


def test_reopen_rejects_simulated_windows_database_reparse_point(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import path_safety

    _initialize_sqlite(tmp_path)
    database = tmp_path / SQLITE_DATABASE_PATH
    original = path_safety.is_link_or_reparse_point
    monkeypatch.setattr(
        path_safety,
        "is_link_or_reparse_point",
        lambda path: path == database or original(path),
    )

    error = _assert_reopen_rejected(tmp_path)

    assert "database" in error.safe_message.lower()
    assert "reparse" in error.diagnostic.lower()


def test_connection_factory_rejects_database_outside_declared_project_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.sqlite3"
    outside.write_bytes(b"not opened")
    factory = SQLiteConnectionFactory(outside, project_root=root)

    with pytest.raises(ProjectStorageError) as raised:
        with factory.connect(writable=False):
            pass

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert "outside" in raised.value.diagnostic.lower()


def test_connection_factory_rejects_symlinked_parent_for_writes(tmp_path: Path) -> None:
    root = tmp_path / "project"
    external = tmp_path / "external"
    root.mkdir()
    external.mkdir()
    linked = root / ".p2p"
    _symlink_or_skip(linked, external, directory=True)
    factory = SQLiteConnectionFactory(
        linked / "local/project.sqlite3",
        project_root=root,
    )

    with pytest.raises(ProjectStorageError) as raised:
        factory.prepare_parent()

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert "symlink" in raised.value.diagnostic.lower()
    assert not (external / "local").exists()


def test_connection_factory_rejects_non_directory_database_parent(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    p2p = root / ".p2p"
    p2p.write_text("not a directory\n", encoding="utf-8")
    factory = SQLiteConnectionFactory(
        p2p / "local/project.sqlite3",
        project_root=root,
    )

    with pytest.raises(ProjectStorageError) as raised:
        factory.prepare_parent()

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert "not a directory" in raised.value.diagnostic.lower()


@pytest.mark.parametrize("adapter", (FILESYSTEM_ADAPTER, SQLITE_ADAPTER))
def test_broken_activation_marker_symlink_fences_every_backend(
    tmp_path: Path,
    adapter: str,
) -> None:
    P2PWorkspace(tmp_path).init_project(
        "SQLite activation marker safety",
        owner="owner",
        agent_profile="generic",
        storage_adapter=adapter,
    )
    marker = tmp_path / SQLITE_ACTIVATION_MARKER
    _symlink_or_skip(marker, tmp_path / "missing-activation-marker.json")

    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)

    assert raised.value.code == ProjectStorageErrorCode.recovery_required


@pytest.mark.parametrize(
    "marker_relative",
    (SQLITE_ACTIVATION_MARKER, SQLITE_MAINTENANCE_MARKER),
)
def test_simulated_windows_reparse_marker_fences_new_project_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    marker_relative: str,
) -> None:
    from p2p_engine.storage import project_storage as storage_module

    _initialize_sqlite(tmp_path)
    marker = tmp_path / marker_relative
    original = storage_module.is_link_or_reparse_point
    monkeypatch.setattr(
        storage_module,
        "is_link_or_reparse_point",
        lambda path: path == marker or original(path),
    )

    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)

    assert raised.value.code == ProjectStorageErrorCode.recovery_required


def test_simulated_windows_reparse_maintenance_marker_fences_open_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.storage import sqlite_project_state as state_module

    _initialize_sqlite(tmp_path)
    app = open_project_application(tmp_path)
    unit = app.project_state_unit_of_work()
    unit.stage(
        ProjectStateMutation(
            operation_id="simulated-reparse-marker-writer",
            actor="owner",
            expected_revision=app.project_state_revision(),
            target=app.canonical_memory_snapshot(),
        )
    )
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    original = state_module.is_link_or_reparse_point
    monkeypatch.setattr(
        state_module,
        "is_link_or_reparse_point",
        lambda path: path == marker or original(path),
    )

    with pytest.raises(ProjectStorageError) as raised:
        unit.commit()

    assert raised.value.code == ProjectStorageErrorCode.recovery_required


def test_recovery_status_reports_simulated_windows_reparse_marker_as_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from p2p_engine.services import project_application as application_module
    from p2p_engine.storage import sqlite_recovery as recovery_module

    _initialize_sqlite(tmp_path)
    marker = tmp_path / SQLITE_MAINTENANCE_MARKER
    application_probe = application_module.is_link_or_reparse_point
    recovery_probe = recovery_module._is_link_or_reparse_point
    monkeypatch.setattr(
        application_module,
        "is_link_or_reparse_point",
        lambda path: path == marker or application_probe(path),
    )
    monkeypatch.setattr(
        recovery_module,
        "_is_link_or_reparse_point",
        lambda path: path == marker or recovery_probe(path),
    )

    status = project_memory_recovery_status(tmp_path)

    assert status.state == "invalid_marker"


def test_read_only_sqlite_uri_preserves_literal_question_mark_in_project_path(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project?literal"
    truncated_sibling = tmp_path / "project"

    _initialize_sqlite(root)
    reopened = open_project_application(root)

    assert reopened.storage_selection().adapter == SQLITE_ADAPTER
    assert reopened.canonical_memory_snapshot().project_uuid
    assert not truncated_sibling.exists()


def test_maintenance_marker_never_falls_back_to_initialization_without_manifest(
    tmp_path: Path,
) -> None:
    _initialize_sqlite(tmp_path)
    (tmp_path / ".p2p/local/storage.yml").unlink()
    (tmp_path / SQLITE_MAINTENANCE_MARKER).write_text("{}\n", encoding="utf-8")

    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)

    assert raised.value.code == ProjectStorageErrorCode.recovery_required
    assert (tmp_path / SQLITE_DATABASE_PATH).is_file()


def test_sqlite_database_without_manifest_is_never_treated_as_a_new_project(
    tmp_path: Path,
) -> None:
    _initialize_sqlite(tmp_path)
    (tmp_path / ".p2p/local/storage.yml").unlink()

    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)

    assert raised.value.code == ProjectStorageErrorCode.configuration_contradiction
    assert (tmp_path / SQLITE_DATABASE_PATH).is_file()


def test_sqlite_reopen_rejects_casefolded_alias_of_canonical_filesystem_state(
    tmp_path: Path,
) -> None:
    _initialize_sqlite(tmp_path)
    alias = tmp_path / ".p2p/PROJECT/PERMISSIONS.YML"
    alias.parent.mkdir(parents=True)
    alias.write_text("permissions: {}\n", encoding="utf-8")

    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)

    assert raised.value.code == ProjectStorageErrorCode.configuration_contradiction

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from p2p_engine.core.canonical_memory import ManagedBlob, semantic_sha256
from p2p_engine.core.project_state_storage import (
    ProjectStateMutation,
    ProjectStorageError,
    ProjectStorageErrorCode,
)
from p2p_engine.services.project_application import open_project_application
from p2p_engine.storage import sqlite_project_state as sqlite_state_module
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.sqlite_adapter import _install_blob_payloads
from p2p_engine.storage.sqlite_project_state import (
    SQLiteBlobStore,
    install_sqlite_blob_bytes,
    snapshot_digest,
    sqlite_blob_path,
)
from p2p_engine.storage.sqlite_schema import SQLITE_ADAPTER


def _initialize(root: Path):
    P2PWorkspace(root).init_project(
        "SQLite blob safety",
        owner="owner",
        agent_profile="generic",
        storage_adapter=SQLITE_ADAPTER,
    )
    return open_project_application(root)


def _target_with_blob(snapshot, content: bytes):
    raw_digest = hashlib.sha256(content).hexdigest()
    digest = f"sha256:{raw_digest}"
    first = next(
        entity
        for entity in snapshot.entities
        if isinstance(entity.payload.get("document"), dict)
    )
    payload = dict(first.payload)
    document = dict(payload["document"])
    document["sqlite_blob_safety"] = {
        "kind": "managed_blob",
        "digest": digest,
    }
    payload["document"] = document
    entities = tuple(
        replace(entity, payload=payload)
        if entity.technical_id == first.technical_id
        else entity
        for entity in snapshot.entities
    )
    blob = ManagedBlob(
        digest=digest,
        size=len(content),
        storage_locator=f".p2p/blobs/sha256/{raw_digest[:2]}/{raw_digest}",
    )
    provisional = replace(
        snapshot,
        entities=entities,
        blobs=(blob,),
        blob_manifest_digest=semantic_sha256([blob.to_dict()]),
        semantic_state_digest="0" * 64,
        source_revision={"kind": "local", "value": "0" * 64},
    )
    state_digest = snapshot_digest(provisional)
    return (
        replace(
            provisional,
            semantic_state_digest=state_digest,
            source_revision={"kind": "local", "value": state_digest},
        ),
        digest,
    )


def _commit_blob(app, content: bytes):
    target, digest = _target_with_blob(app.canonical_memory_snapshot(), content)
    with app.project_state_unit_of_work() as unit:
        unit.stage(
            ProjectStateMutation(
                operation_id=f"sqlite-blob-{digest[-12:]}",
                actor="owner",
                expected_revision=app.project_state_revision(),
                target=target,
                blob_payloads={digest: content},
            )
        )
        unit.commit()
    return digest


def test_blob_store_rejects_a_simulated_reparse_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _initialize(tmp_path)
    content = b"managed blob behind a reparse parent\n"
    digest = _commit_blob(app, content)
    blob_path = sqlite_blob_path(tmp_path.resolve(), digest)
    unsafe_parent = blob_path.parent
    original = sqlite_state_module._is_link_or_reparse_point

    def simulated_reparse(path: Path) -> bool:
        return path == unsafe_parent or original(path)

    monkeypatch.setattr(
        sqlite_state_module,
        "_is_link_or_reparse_point",
        simulated_reparse,
    )
    blobs = SQLiteBlobStore(app.adapter.repository)

    with pytest.raises(ProjectStorageError) as has_error:
        blobs.has(digest)
    with pytest.raises(ProjectStorageError) as read_error:
        blobs.read(digest)

    assert has_error.value.code == ProjectStorageErrorCode.integrity_failure
    assert read_error.value.code == ProjectStorageErrorCode.integrity_failure
    assert blob_path.read_bytes() == content


def test_materialization_refuses_a_simulated_reparse_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _initialize(tmp_path)
    before = app.canonical_memory_snapshot()
    content = b"new blob must not enter an unsafe parent\n"
    target, digest = _target_with_blob(before, content)
    unsafe_parent = sqlite_blob_path(tmp_path.resolve(), digest).parent
    original = sqlite_state_module._is_link_or_reparse_point

    monkeypatch.setattr(
        sqlite_state_module,
        "_is_link_or_reparse_point",
        lambda path: path == unsafe_parent or original(path),
    )
    unit = app.project_state_unit_of_work()
    unit.stage(
        ProjectStateMutation(
            operation_id="sqlite-unsafe-blob-parent",
            actor="owner",
            expected_revision=app.project_state_revision(),
            target=target,
            blob_payloads={digest: content},
        )
    )

    with pytest.raises(ProjectStorageError) as raised:
        unit.commit()

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert app.canonical_memory_snapshot().semantic_state_digest == before.semantic_state_digest
    assert not sqlite_blob_path(tmp_path.resolve(), digest).exists()


def test_restore_install_refuses_a_non_directory_blob_parent(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    (root / ".p2p").mkdir()
    (root / ".p2p/blobs").write_bytes(b"not a directory\n")
    content = b"restore payload\n"
    digest = f"sha256:{hashlib.sha256(content).hexdigest()}"

    with pytest.raises(ProjectStorageError) as raised:
        _install_blob_payloads(root, {digest: content})

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert (root / ".p2p/blobs").read_bytes() == b"not a directory\n"


def test_restore_install_does_not_replace_a_simulated_reparse_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path.resolve()
    content = b"stable content-addressed payload\n"
    digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
    assert install_sqlite_blob_bytes(root, digest, content)
    blob_path = sqlite_blob_path(root, digest)
    original = sqlite_state_module._is_link_or_reparse_point

    monkeypatch.setattr(
        sqlite_state_module,
        "_is_link_or_reparse_point",
        lambda path: path == blob_path or original(path),
    )

    with pytest.raises(ProjectStorageError) as raised:
        _install_blob_payloads(root, {digest: content})

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert blob_path.read_bytes() == content


def test_restore_install_does_not_follow_a_blob_symlink(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    content = b"expected restore payload\n"
    digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
    blob_path = sqlite_blob_path(root, digest)
    blob_path.parent.mkdir(parents=True)
    external = tmp_path / "outside-managed-blob"
    external.write_bytes(b"must remain unchanged\n")
    try:
        blob_path.symlink_to(external)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable on this platform: {exc}")

    with pytest.raises(ProjectStorageError) as raised:
        _install_blob_payloads(root, {digest: content})

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert blob_path.is_symlink()
    assert external.read_bytes() == b"must remain unchanged\n"


def test_physical_backup_does_not_follow_a_blob_symlink(tmp_path: Path) -> None:
    app = _initialize(tmp_path)
    content = b"backup must read only the managed blob\n"
    digest = _commit_blob(app, content)
    blob_path = sqlite_blob_path(tmp_path.resolve(), digest)
    external = tmp_path / "outside-managed-blob"
    external.write_bytes(content)
    blob_path.unlink()
    try:
        blob_path.symlink_to(external)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable on this platform: {exc}")
    output = tmp_path / "unsafe-backup.p2pbackup"

    with pytest.raises(ProjectStorageError) as raised:
        app.canonical_memory_backup(output)

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert not output.exists()
    assert blob_path.is_symlink()
    assert external.read_bytes() == content


def test_physical_backup_does_not_follow_the_storage_manifest_symlink(
    tmp_path: Path,
) -> None:
    app = _initialize(tmp_path)
    manifest = tmp_path / ".p2p/local/storage.yml"
    external = tmp_path / "outside-storage.yml"
    manifest.replace(external)
    try:
        manifest.symlink_to(external)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable on this platform: {exc}")
    output = tmp_path / "unsafe-manifest-backup.p2pbackup"

    with pytest.raises(ProjectStorageError) as raised:
        app.canonical_memory_backup(output)

    assert raised.value.code == ProjectStorageErrorCode.integrity_failure
    assert not output.exists()
    assert manifest.is_symlink()
    assert external.is_file()


def test_blob_publication_syncs_each_new_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path.resolve()
    (root / ".p2p").mkdir()
    content = b"durable managed blob\n"
    digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
    calls: list[Path] = []

    monkeypatch.setattr(
        sqlite_state_module,
        "sync_directory",
        lambda path: calls.append(path) or True,
    )

    assert install_sqlite_blob_bytes(root, digest, content)

    blob_path = sqlite_blob_path(root, digest)
    assert blob_path.read_bytes() == content
    assert root / ".p2p" in calls
    assert root / ".p2p/blobs" in calls
    assert root / ".p2p/blobs/sha256" in calls
    assert blob_path.parent in calls

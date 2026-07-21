from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.services.workspace_reads import WorkspaceDocumentStore


@pytest.mark.unit
def test_document_store_captures_missing_file_without_reading_it(tmp_path: Path) -> None:
    store = WorkspaceDocumentStore(tmp_path)

    document = store.capture("missing.yml")

    assert document.exists is False
    assert document.relative_path == "missing.yml"
    assert store.counters.source_reads == {}
    with pytest.raises(FileNotFoundError, match="missing.yml"):
        store.bytes("missing.yml")


@pytest.mark.adapter
def test_document_store_keeps_request_private_bytes_and_detects_later_change(
    tmp_path: Path,
) -> None:
    path = tmp_path / "value.yml"
    path.write_text("value: one\n", encoding="utf-8")
    store = WorkspaceDocumentStore(tmp_path)

    captured = store.bytes(path)
    path.write_text("value: two\n", encoding="utf-8")

    assert store.bytes(path) == captured == b"value: one\n"
    assert store.counters.source_reads["value.yml"] == 1
    result = store.finalize()
    assert result.status == "concurrent_change"
    assert result.changed_paths == ("value.yml",)


@pytest.mark.adapter
def test_new_document_store_observes_new_revision_after_process_restart(
    tmp_path: Path,
) -> None:
    path = tmp_path / "value.yml"
    path.write_text("value: one\n", encoding="utf-8")
    assert WorkspaceDocumentStore(tmp_path).text(path) == "value: one\n"

    path.write_text("value: two\n", encoding="utf-8")

    assert WorkspaceDocumentStore(tmp_path).text(path) == "value: two\n"


@pytest.mark.adapter
def test_recursive_discovery_is_sorted_and_detects_removal(tmp_path: Path) -> None:
    root = tmp_path / "items"
    (root / "z").mkdir(parents=True)
    (root / "a").mkdir()
    (root / "z/last.yml").write_text("value: last\n", encoding="utf-8")
    removed = root / "a/first.yml"
    removed.write_text("value: first\n", encoding="utf-8")
    store = WorkspaceDocumentStore(tmp_path)

    paths = store.discover(
        root,
        policy="yaml-recursive-v1",
        predicate=lambda path: path.is_file() and path.suffix == ".yml",
        recursive=True,
    )
    removed.unlink()

    assert [path.relative_to(tmp_path).as_posix() for path in paths] == [
        "items/a/first.yml",
        "items/z/last.yml",
    ]
    result = store.finalize()
    assert result.status == "concurrent_change"
    assert result.changed_directories == ("items:yaml-recursive-v1",)

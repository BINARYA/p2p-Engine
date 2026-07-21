from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from p2p_engine.services.workspace_reads import WorkspaceReadContext
from p2p_engine.storage.filesystem import P2PWorkspace


@pytest.mark.unit
def test_read_context_is_lazy_and_memoizes_argument_sensitive_provider(tmp_path: Path) -> None:
    context = WorkspaceReadContext(tmp_path)
    calls: list[str] = []

    first = context.provide("value", ("a",), lambda: calls.append("a") or ("a",))
    repeated = context.provide("value", ("a",), lambda: calls.append("duplicate") or ())
    second = context.provide("value", ("b",), lambda: calls.append("b") or ("b",))

    assert first is repeated
    assert second == ("b",)
    assert calls == ["a", "b"]
    assert context.counters.provider_calls["value"] == 3
    assert context.counters.provider_cache_hits["value"] == 1
    with pytest.raises(FrozenInstanceError):
        context.counters.schema_preflights = 1  # type: ignore[misc]


@pytest.mark.adapter
def test_document_store_reads_and_parses_selected_path_once(tmp_path: Path) -> None:
    path = tmp_path / "data.yml"
    path.write_text("value: 1\n", encoding="utf-8")
    context = WorkspaceReadContext(tmp_path)

    first = context.documents.yaml(path)
    second = context.documents.yaml(path)

    assert first is second
    assert context.counters.source_reads["data.yml"] == 1
    assert context.counters.source_hashes["data.yml"] == 1
    assert context.counters.yaml_parses["data.yml:safe-v1"] == 1
    assert context.finalize().current is True


@pytest.mark.adapter
def test_document_store_isolates_loader_contracts_and_rejects_root_escape(tmp_path: Path) -> None:
    path = tmp_path / "data.yml"
    path.write_text("value: 1\n", encoding="utf-8")
    context = WorkspaceReadContext(tmp_path)

    context.documents.yaml(path)

    assert context.documents.yaml(path, loader_contract="unique-v1") == {"value": 1}
    assert context.counters.yaml_parses["data.yml:safe-v1"] == 1
    assert context.counters.yaml_parses["data.yml:unique-v1"] == 1
    with pytest.raises(ValueError, match="escapes root"):
        context.documents.capture(tmp_path.parent / "outside.yml")


@pytest.mark.adapter
def test_read_context_detects_same_size_content_and_discovery_changes(tmp_path: Path) -> None:
    directory = tmp_path / "items"
    directory.mkdir()
    path = directory / "one.txt"
    path.write_text("one", encoding="utf-8")
    context = WorkspaceReadContext(tmp_path)
    context.documents.capture(path)
    context.documents.discover(directory, policy="items-v1")

    path.write_text("two", encoding="utf-8")
    (directory / "two.txt").write_text("new", encoding="utf-8")
    result = context.finalize()

    assert result.status == "concurrent_change"
    assert result.diagnostic_code == "P2P_READ_CONCURRENT_CHANGE"
    assert result.changed_paths == ("items/one.txt",)
    assert result.changed_directories == ("items:items-v1",)


@pytest.mark.adapter
def test_discovery_rejects_symlinks(tmp_path: Path) -> None:
    directory = tmp_path / "items"
    directory.mkdir()
    target = tmp_path / "target"
    target.write_text("value", encoding="utf-8")
    (directory / "link").symlink_to(target)

    with pytest.raises(ValueError, match="rejects symlink"):
        WorkspaceReadContext(tmp_path).documents.discover(directory, policy="items-v1")


@pytest.mark.adapter
def test_discovery_finalization_reuses_original_predicate(tmp_path: Path) -> None:
    directory = tmp_path / "items"
    directory.mkdir()
    (directory / "selected.yml").write_text("value: 1\n", encoding="utf-8")
    ignored = directory / "ignored.txt"
    ignored.write_text("old", encoding="utf-8")
    context = WorkspaceReadContext(tmp_path)

    context.documents.discover(
        directory,
        policy="yaml-v1",
        predicate=lambda path: path.suffix == ".yml",
    )
    ignored.write_text("new", encoding="utf-8")

    assert context.finalize().current is True


@pytest.mark.adapter
def test_recursive_discovery_detects_nested_add_remove_and_rename(tmp_path: Path) -> None:
    directory = tmp_path / "items"
    nested = directory / "nested"
    nested.mkdir(parents=True)
    original = nested / "one.yml"
    original.write_text("value: one\n", encoding="utf-8")
    context = WorkspaceReadContext(tmp_path)

    discovered = context.documents.discover(
        directory,
        policy="yaml-tree-v1",
        predicate=lambda path: path.is_file() and path.suffix == ".yml",
        recursive=True,
    )
    original.rename(nested / "renamed.yml")
    (nested / "added.yml").write_text("value: added\n", encoding="utf-8")

    assert [path.name for path in discovered] == ["one.yml"]
    result = context.finalize()
    assert result.status == "concurrent_change"
    assert result.changed_directories == ("items:yaml-tree-v1",)


@pytest.mark.adapter
def test_workspace_consistent_read_retries_once_and_discards_first_result(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("one", encoding="utf-8")
    workspace = P2PWorkspace(tmp_path)
    attempts = 0

    def operation(context: WorkspaceReadContext) -> str:
        nonlocal attempts
        attempts += 1
        value = context.documents.text(source)
        if attempts == 1:
            source.write_text("two", encoding="utf-8")
        return value

    assert workspace.read_consistently(operation) == "two"
    assert attempts == 2


@pytest.mark.adapter
def test_workspace_consistent_read_reports_second_concurrent_change(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("one", encoding="utf-8")
    workspace = P2PWorkspace(tmp_path)

    def operation(context: WorkspaceReadContext) -> str:
        value = context.documents.text(source)
        source.write_text(value + "x", encoding="utf-8")
        return value

    with pytest.raises(ValueError, match="P2P_READ_CONCURRENT_CHANGE"):
        workspace.read_consistently(operation)


@pytest.mark.adapter
def test_read_context_rejects_active_mutation_lock(tmp_path: Path) -> None:
    lock = tmp_path / ".p2p" / ".internal" / "workspace-migrations" / "apply.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("transaction_id: active\n", encoding="utf-8")
    context = WorkspaceReadContext(tmp_path)

    context.provide("value", (), lambda: "value")
    result = context.finalize()

    assert result.status == "concurrent_change"
    assert result.changed_paths == (".p2p/.internal/workspace-migrations/apply.lock",)


@pytest.mark.adapter
def test_read_context_can_observe_stable_lock_for_recovery_diagnostics(
    tmp_path: Path,
) -> None:
    lock = tmp_path / ".p2p" / ".internal" / "workspace-migrations" / "apply.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("transaction_id: active\n", encoding="utf-8")
    context = WorkspaceReadContext(
        tmp_path,
        allow_existing_migration_lock=True,
    )

    context.provide("value", (), lambda: "value")

    assert context.finalize().status == "current"

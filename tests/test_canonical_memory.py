from __future__ import annotations

import hashlib
import json
import shutil
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.canonical_memory import canonical_json_bytes, normalize_semantic_value
from p2p_engine.mcp.registry import TOOL_NAMES
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.agent_templates import agent_instruction_files
from p2p_engine.services.canonical_memory import (
    BundleLimits,
    CanonicalBundleCodec,
    CanonicalMemoryService,
    _deterministic_zip,
)
from p2p_engine.storage.canonical_memory import FilesystemCanonicalMemoryStore
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data
from tests.filesystem_assertions import assert_no_workspace_mutation

runner = CliRunner()


def _workspace(root: Path, *, name: str = "Canonical Memory") -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project(name, owner="owner")
    return workspace


def _portable_document(root: Path, name: str, value: object) -> Path:
    path = root / ".p2p" / "governance" / f"{name}.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _bundle_entries(raw: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(BytesIO(raw), "r") as archive:
        return {item.filename: archive.read(item) for item in archive.infolist()}


def _bundle_with_changed_entry(raw: bytes, name: str, content: bytes) -> bytes:
    entries = _bundle_entries(raw)
    entries[name] = content
    checksum_name = "p2p-project-bundle/checksums.json"
    checksums = {
        "contract": "p2p-project-bundle-checksums/v1",
        "entries": {
            path: {"sha256": hashlib.sha256(value).hexdigest(), "size": len(value)}
            for path, value in sorted(entries.items())
            if path != checksum_name
        },
    }
    entries[checksum_name] = canonical_json_bytes(checksums)
    return _deterministic_zip(entries)


def _add_managed_blob(root: Path, content: bytes = b"portable blob\n") -> str:
    digest = hashlib.sha256(content).hexdigest()
    target = root / ".p2p" / "blobs" / "sha256" / digest[:2] / digest
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    _portable_document(
        root,
        "blob-reference",
        {
            "evidence": {"kind": "managed_blob", "digest": f"sha256:{digest}"},
            "canonical_relations": [
                {"id": "blob-evidence-project", "type": "supports", "target": "project:manifest"}
            ],
        },
    )
    return digest


def test_inventory_freezes_portable_local_derived_integration_and_external_boundaries(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    (tmp_path / ".p2p/personal/settings.yml").parent.mkdir(parents=True)
    (tmp_path / ".p2p/personal/settings.yml").write_text(
        "access_token: local-only\n", encoding="utf-8"
    )
    (tmp_path / ".p2p/external/reference.md").parent.mkdir(parents=True)
    (tmp_path / ".p2p/external/reference.md").write_text("outside\n", encoding="utf-8")
    (tmp_path / ".p2p/project/overview.md").write_text("derived\n", encoding="utf-8")
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs/private.md").write_text("never bundled\n", encoding="utf-8")
    (tmp_path / "source.py").write_text("print('never bundled')\n", encoding="utf-8")

    inventory = workspace.canonical_memory_inspect()
    by_path = {item.locator: item for item in inventory.artifacts}

    assert inventory.blockers == ()
    assert by_path[".p2p/project/identity.yml"].classification == "canonical_project"
    assert by_path[".p2p/local/replica.yml"].classification == "replica_local"
    assert by_path[".p2p/project/overview.md"].classification == "derived_projection"
    assert by_path[".p2p/agent-policy.yml"].classification == "integration_artifact"
    assert by_path[".p2p/personal/settings.yml"].classification == "personal_configuration"
    assert by_path[".p2p/external/reference.md"].classification == "external_material"
    assert all(
        "specs" not in item.locator and "source.py" not in item.locator
        for item in inventory.artifacts
    )

    metadata = workspace.canonical_bundle_metadata()
    encoded = json.dumps(metadata.to_dict(), sort_keys=True)
    assert "local-only" not in encoded
    assert "private.md" not in encoded
    assert "source.py" not in encoded


def test_inventory_fails_closed_for_unknown_secret_and_symlink(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    unknown = tmp_path / ".p2p/mystery.bin"
    unknown.write_bytes(b"unknown")
    secret = _portable_document(tmp_path, "unsafe", {"api_key": "forbidden"})
    symlink = tmp_path / ".p2p/project/unsafe-link.yml"
    symlink.symlink_to(secret)

    inventory = workspace.canonical_memory_inspect()
    blockers = {item.locator: item.reason for item in inventory.blockers}
    assert ".p2p/mystery.bin" in blockers
    assert "secret-shaped" in blockers[".p2p/governance/unsafe.yml"]
    assert "Symlinks" in blockers[".p2p/project/unsafe-link.yml"]
    with pytest.raises(ValueError, match="P2P_CANONICAL_MEMORY_UNCLASSIFIED"):
        workspace.canonical_memory_snapshot()


def test_inventory_fails_closed_for_cyclic_yaml(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    cyclic = tmp_path / ".p2p/governance/cyclic.yml"
    cyclic.parent.mkdir(parents=True, exist_ok=True)
    cyclic.write_text("cycle: &cycle\n  - *cycle\n", encoding="utf-8")

    blockers = {item.locator: item.reason for item in workspace.canonical_memory_inspect().blockers}
    assert "cyclic sequences" in blockers[".p2p/governance/cyclic.yml"]


def test_canonicalization_and_bundle_bytes_are_cross_platform_deterministic(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    workspace = _workspace(root)
    path = _portable_document(root, "unicode", {"z": "cafe\u0301\r\nline", "a": 1})
    first_snapshot = workspace.canonical_memory_snapshot()
    first = workspace.canonical_bundle_metadata()
    first_archive = root / "first.p2pbundle"
    second_archive = root / "second.p2pbundle"
    workspace.canonical_bundle_export(first_archive)

    path.write_text("a: 1\r\nz: 'caf\u00e9\r\n\r\n  line'\r\n", encoding="utf-8", newline="")
    second_snapshot = P2PWorkspace(root).canonical_memory_snapshot()
    second = P2PWorkspace(root).canonical_bundle_metadata()
    P2PWorkspace(root).canonical_bundle_export(second_archive)

    assert normalize_semantic_value("cafe\u0301\r\nline") == "caf\u00e9\nline"
    assert first_snapshot.semantic_state_digest == second_snapshot.semantic_state_digest
    assert first.archive_sha256 == second.archive_sha256
    assert first_archive.read_bytes() == second_archive.read_bytes()


def test_bundle_transfers_complete_deduplicated_managed_blobs(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    digest = _add_managed_blob(tmp_path)
    snapshot = workspace.canonical_memory_snapshot()
    archive = tmp_path / "memory.p2pbundle"
    exported = workspace.canonical_bundle_export(archive)
    decoded = CanonicalBundleCodec().decode_bundle(archive)

    assert [item.digest for item in snapshot.blobs] == [f"sha256:{digest}"]
    assert [item.relation_id for item in snapshot.relations] == ["blob-evidence-project"]
    assert decoded.blob_bytes[f"sha256:{digest}"] == b"portable blob\n"
    assert exported.manifest.blob_count == 1
    names = [name for name in _bundle_entries(archive.read_bytes()) if "/blobs/" in name]
    assert names == [f"p2p-project-bundle/blobs/sha256/{digest[:2]}/{digest}"]


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("missing", "P2P_BUNDLE_CHECKSUMS_INVALID|P2P_MANAGED_BLOB_MISSING"),
        ("extra", "P2P_BUNDLE_CHECKSUMS_INVALID|P2P_MANAGED_BLOB_EXTRA"),
        ("corrupt", "P2P_BUNDLE_CHECKSUM_MISMATCH|P2P_MANAGED_BLOB_DIGEST_MISMATCH"),
    ],
)
def test_bundle_rejects_missing_extra_and_corrupt_blobs(
    tmp_path: Path, mutation: str, error: str
) -> None:
    workspace = _workspace(tmp_path)
    digest = _add_managed_blob(tmp_path)
    raw, _manifest = CanonicalBundleCodec().encode_bundle(
        FilesystemCanonicalMemoryStore(tmp_path), workspace.canonical_memory_snapshot()
    )
    entries = _bundle_entries(raw)
    blob_name = f"p2p-project-bundle/blobs/sha256/{digest[:2]}/{digest}"
    if mutation == "missing":
        del entries[blob_name]
    elif mutation == "extra":
        extra_digest = "f" * 64
        entries[f"p2p-project-bundle/blobs/sha256/ff/{extra_digest}"] = b"extra"
    else:
        entries[blob_name] = b"corrupt"
    tampered = _deterministic_zip(entries)
    with pytest.raises(ValueError, match=error):
        CanonicalBundleCodec().decode_bundle(tampered)


def test_bundle_rejects_unsafe_duplicate_unsupported_and_broken_relation_archives(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    raw, _manifest = CanonicalBundleCodec().encode_bundle(
        FilesystemCanonicalMemoryStore(tmp_path), workspace.canonical_memory_snapshot()
    )

    entries = _bundle_entries(raw)
    entries["../escape"] = b"unsafe"
    with pytest.raises(ValueError, match="P2P_BUNDLE_UNSAFE_ENTRY"):
        CanonicalBundleCodec().decode_bundle(_deterministic_zip(entries))

    duplicate = BytesIO()
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(duplicate, "w") as archive:
            archive.writestr("duplicate", b"one")
            archive.writestr("duplicate", b"two")
    with pytest.raises(ValueError, match="P2P_BUNDLE_DUPLICATE_ENTRY"):
        CanonicalBundleCodec().decode_bundle(duplicate.getvalue())

    entries = _bundle_entries(raw)
    manifest_name = "p2p-project-bundle/manifest.json"
    manifest = json.loads(entries[manifest_name])
    manifest["bundle_schema"] = "p2p-project-bundle/v999"
    unsupported = _bundle_with_changed_entry(raw, manifest_name, canonical_json_bytes(manifest))
    with pytest.raises(ValueError, match="P2P_BUNDLE_SCHEMA_UNSUPPORTED"):
        CanonicalBundleCodec().decode_bundle(unsupported)

    manifest = json.loads(_bundle_entries(raw)[manifest_name])
    manifest["project_uuid"] = str(uuid.uuid4())
    identity_mismatch = _bundle_with_changed_entry(
        raw, manifest_name, canonical_json_bytes(manifest)
    )
    with pytest.raises(ValueError, match="P2P_BUNDLE_IDENTITY_MISMATCH"):
        CanonicalBundleCodec().decode_bundle(identity_mismatch)

    manifest = json.loads(_bundle_entries(raw)[manifest_name])
    manifest["source_revision"] = {"kind": "wavekit", "value": "a" * 64}
    wavekit_source = _bundle_with_changed_entry(raw, manifest_name, canonical_json_bytes(manifest))
    assert CanonicalBundleCodec().decode_bundle(wavekit_source).manifest.source_revision == {
        "kind": "wavekit",
        "value": "a" * 64,
    }

    relation_name = "p2p-project-bundle/relations.jsonl"
    broken_relation = {
        "relation_type": "references",
        "relation_id": "broken-1",
        "source_entity": "missing:source",
        "target_entity": "missing:target",
        "payload": {},
    }
    broken = _bundle_with_changed_entry(raw, relation_name, canonical_json_bytes(broken_relation))
    with pytest.raises(ValueError, match="P2P_CANONICAL_RELATION_BROKEN"):
        CanonicalBundleCodec().decode_bundle(broken)

    with pytest.raises(ValueError, match="P2P_BUNDLE_LIMIT_EXCEEDED"):
        CanonicalBundleCodec(limits=BundleLimits(max_archive_bytes=len(raw) - 1)).decode_bundle(raw)
    with pytest.raises(ValueError, match="P2P_BUNDLE_LIMIT_EXCEEDED"):
        CanonicalBundleCodec(limits=BundleLimits(max_entities=1)).encode_bundle(
            FilesystemCanonicalMemoryStore(tmp_path), workspace.canonical_memory_snapshot()
        )
    limited_service = CanonicalMemoryService(
        root=tmp_path,
        codec=CanonicalBundleCodec(limits=BundleLimits(max_entries=1)),
    )
    limited_archive = tmp_path / "limited.p2pbundle"
    limited_archive.write_bytes(raw)
    limited_result = limited_service.verify_archive(limited_archive)
    assert limited_result.status == "invalid"
    assert "P2P_BUNDLE_LIMIT_EXCEEDED" in limited_result.issues[0]


def test_bundle_preserves_typed_project_lineage(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    source_uuid = workspace.project_identity().project_uuid.value
    preview = workspace.preview_project_identity_derivation(
        operation_key="canonical-lineage-derive-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    workspace.apply_project_identity_derivation(
        operation_key="canonical-lineage-derive-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    snapshot = P2PWorkspace(tmp_path).canonical_memory_snapshot()
    archive = tmp_path / "lineage.p2pbundle"
    P2PWorkspace(tmp_path).canonical_bundle_export(archive)
    decoded = CanonicalBundleCodec().decode_bundle(archive)
    assert len(snapshot.lineage) == 1
    assert snapshot.lineage[0]["source_project_uuid"] == source_uuid
    assert decoded.snapshot.lineage == snapshot.lineage

    lineage_name = "p2p-project-bundle/lineage.jsonl"
    inconsistent = _bundle_with_changed_entry(archive.read_bytes(), lineage_name, b"")
    with pytest.raises(ValueError, match="identity entity and lineage stream disagree"):
        CanonicalBundleCodec().decode_bundle(inconsistent)


def test_bundle_restore_round_trip_is_atomic_idempotent_and_preserves_local_state(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    before = workspace.canonical_memory_snapshot()
    replica = (tmp_path / ".p2p/local/replica.yml").read_bytes()
    agents = (tmp_path / "AGENTS.md").read_bytes()
    archive = tmp_path / "baseline.p2pbundle"
    workspace.canonical_bundle_export(archive)
    extra = _portable_document(tmp_path, "temporary", {"temporary": True})
    assert (
        P2PWorkspace(tmp_path).canonical_memory_snapshot().semantic_state_digest
        != before.semantic_state_digest
    )

    operation_key = "memory-restore-roundtrip-12345678"
    preview = P2PWorkspace(tmp_path).canonical_memory_restore_preview(
        source=archive, operation_key=operation_key, actor="owner"
    )
    result = P2PWorkspace(tmp_path).canonical_memory_restore_apply(
        source=archive,
        operation_key=operation_key,
        actor="owner",
        preview_token=preview.preview_token,
        confirm=True,
    )
    replay = P2PWorkspace(tmp_path).canonical_memory_restore_apply(
        source=archive,
        operation_key=operation_key,
        actor="owner",
        preview_token=preview.preview_token,
        confirm=True,
    )

    assert not extra.exists()
    assert result.semantic_state_digest == before.semantic_state_digest
    assert replay.replayed is True
    assert (tmp_path / ".p2p/local/replica.yml").read_bytes() == replica
    assert (tmp_path / "AGENTS.md").read_bytes() == agents
    assert Path(result.backup_path).is_file()
    assert P2PWorkspace(tmp_path).canonical_memory_recovery_status().state == "clean"
    with pytest.raises(ValueError, match="Unknown project actor"):
        P2PWorkspace(tmp_path).canonical_memory_restore_apply(
            source=archive,
            operation_key=operation_key,
            actor="intruder",
            preview_token=preview.preview_token,
            confirm=True,
        )


def test_physical_backup_restores_exact_replica_state(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    replica_path = tmp_path / ".p2p/local/scratch.yml"
    replica_path.write_text("local_state: before\n", encoding="utf-8")
    before = replica_path.read_bytes()
    backup = tmp_path / "exact.p2pbackup"
    result = workspace.canonical_memory_backup(backup)
    assert result.coordinated is True
    closed_backup = tmp_path / "closed.p2pbackup"
    closed = workspace.canonical_memory_backup(closed_backup, coordinated=False)
    assert closed.coordinated is False
    assert closed_backup.read_bytes() == backup.read_bytes()
    replica_path.write_text("local_state: after\n", encoding="utf-8")

    preview = P2PWorkspace(tmp_path).canonical_memory_restore_preview(
        source=backup, operation_key="physical-restore-12345678", actor="owner"
    )
    P2PWorkspace(tmp_path).canonical_memory_restore_apply(
        source=backup,
        operation_key="physical-restore-12345678",
        actor="owner",
        preview_token=preview.preview_token,
        confirm=True,
    )
    assert replica_path.read_bytes() == before
    assert P2PWorkspace(tmp_path).canonical_archive_verify(backup).valid


def test_restore_fault_after_active_move_rolls_back_and_keeps_verified_backup(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    archive = tmp_path / "baseline.p2pbundle"
    workspace.canonical_bundle_export(archive)
    _portable_document(tmp_path, "new-state", {"revision": 2})
    active_digest = P2PWorkspace(tmp_path).canonical_memory_snapshot().semantic_state_digest

    def fail(stage: str) -> None:
        if stage == "after_active_move":
            raise RuntimeError("injected crash")

    service = CanonicalMemoryService(root=tmp_path, failure_injector=fail)
    preview = service.restore_preview(
        source=archive, operation_key="fault-injection-restore-12345678", actor="owner"
    )
    with pytest.raises(RuntimeError, match="injected crash"):
        service.restore_apply(
            source=archive,
            operation_key="fault-injection-restore-12345678",
            actor="owner",
            preview_token=preview.preview_token,
            confirm=True,
        )

    recovered = P2PWorkspace(tmp_path)
    assert recovered.canonical_memory_snapshot().semantic_state_digest == active_digest
    backups = list((tmp_path / ".p2p-backups").glob("*.p2pbackup"))
    assert len(backups) == 1
    assert recovered.canonical_archive_verify(backups[0]).valid
    assert recovered.canonical_memory_recovery_status().state == "clean"


def test_adapter_contract_is_storage_neutral_and_views_and_receipts_are_non_semantic(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path)
    store = FilesystemCanonicalMemoryStore(tmp_path)
    codec = CanonicalBundleCodec()
    expected = codec.snapshot(store)

    class MemoryPort:
        def inventory(self):
            return store.inventory()

        def project_identity(self):
            return store.project_identity()

        def read_entities(self, inventory):
            return store.read_entities(inventory)

        def read_relations(self, entities):
            return store.read_relations(entities)

        def read_blobs(self, inventory):
            return store.read_blobs(inventory)

        def read_blob_bytes(self, blob):
            return store.read_blob_bytes(blob)

    assert codec.snapshot(MemoryPort()).semantic_state_digest == expected.semantic_state_digest
    shutil.rmtree(tmp_path / ".p2p/.internal/mutation-receipts", ignore_errors=True)
    (tmp_path / ".p2p/project/overview.md").write_text("rebuilt view\n", encoding="utf-8")
    assert (
        P2PWorkspace(tmp_path).canonical_memory_snapshot().semantic_state_digest
        == expected.semantic_state_digest
    )
    assert P2PWorkspace(tmp_path).validate().ok


def test_cli_mcp_and_generated_agent_contracts_are_storage_neutral(tmp_path: Path) -> None:
    _workspace(tmp_path)
    with assert_no_workspace_mutation(tmp_path):
        inspect_result = runner.invoke(
            app,
            ["project", "memory", "inspect", "--format", "json", "--root", str(tmp_path)],
        )
        verify_result = runner.invoke(
            app,
            ["project", "memory", "verify", "--format", "json", "--root", str(tmp_path)],
        )
        metadata = call_tool("p2p_project_bundle_export_metadata", {"root": str(tmp_path)})
        mcp_inspect = call_tool("p2p_canonical_memory_inspect", {"root": str(tmp_path)})
        mcp_verify = call_tool("p2p_canonical_memory_verify", {"root": str(tmp_path)})

    assert cli_data(inspect_result)["canonical_memory"] == mcp_inspect["canonical_memory"]
    assert cli_data(verify_result)["memory_verification"] == mcp_verify["memory_verification"]
    assert metadata["bundle_export"]["manifest"]["bundle_schema"] == "p2p-project-bundle/v1"
    assert all("restore" not in name for name in TOOL_NAMES if "canonical_memory" in name)
    assert "p2p_project_memory_restore_apply" not in TOOL_NAMES

    instructions = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    policy = yaml.safe_load((tmp_path / ".p2p/agent-policy.yml").read_text(encoding="utf-8"))
    assert "Canonical Project Memory and Bundles" in instructions
    assert "must never infer, inspect, or modify filesystem" in instructions
    assert policy["canonical_project_memory"]["backend_private_access"] == "forbidden"
    assert policy["canonical_project_memory"]["mcp_restore"] is False
    rendered = agent_instruction_files(
        "Canonical Memory",
        ["generic", "codex", "claude", "cursor", "copilot", "gemini", "opencode"],
    )
    assert rendered
    covered = {
        str(path)
        for path, content in rendered.items()
        if "Canonical Project Memory and Bundles" in content
    }
    assert covered == {
        "AGENTS.md",
        ".agents/skills/p2p-project/SKILL.md",
        "CLAUDE.md",
        ".cursor/rules/p2p.mdc",
        ".github/copilot-instructions.md",
        "GEMINI.md",
    }

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.services.project_application import ProjectApplicationService

runner = CliRunner()


def _source_bundle(tmp_path: Path):
    source = tmp_path / "source"
    workspace = ProjectApplicationService(source)
    workspace.init_project("Transferred project", starter_id="empty")
    snapshot = workspace.canonical_memory_snapshot()
    bundle = tmp_path / "project.p2pbundle"
    exported = workspace.canonical_bundle_export(bundle)
    return snapshot, bundle, exported


def test_materialize_bundle_creates_equivalent_new_root_and_replays(tmp_path: Path) -> None:
    snapshot, bundle, exported = _source_bundle(tmp_path)
    target = tmp_path / "server-staging"
    workspace = ProjectApplicationService(target)

    result = workspace.canonical_bundle_materialize(
        source=bundle,
        operation_key="wavekit:transfer:one",
        actor="wavekit-worker",
        expected_project_uuid=snapshot.project_uuid,
        expected_archive_sha256=exported.archive_sha256,
        confirm=True,
    )
    replay = ProjectApplicationService(target).canonical_bundle_materialize(
        source=bundle,
        operation_key="wavekit:transfer:one",
        actor="wavekit-worker",
        expected_project_uuid=snapshot.project_uuid,
        expected_archive_sha256=exported.archive_sha256,
        confirm=True,
    )
    materialized = ProjectApplicationService(target).canonical_memory_snapshot()
    source_identity = ProjectApplicationService(tmp_path / "source").project_identity()
    target_identity = ProjectApplicationService(target).project_identity()

    assert result.status == "materialized"
    assert result.replayed is False
    assert replay.replayed is True
    assert materialized.project_uuid == snapshot.project_uuid
    assert materialized.semantic_state_digest == snapshot.semantic_state_digest
    assert materialized.blob_manifest_digest == snapshot.blob_manifest_digest
    assert target_identity.project_uuid == source_identity.project_uuid
    assert target_identity.replica_id != source_identity.replica_id
    assert target_identity.remote_binding is None

    with pytest.raises(
        ValueError,
        match="P2P_BUNDLE_MATERIALIZATION_RECEIPT_CORRUPT",
    ):
        ProjectApplicationService(target).canonical_bundle_materialize(
            source=bundle,
            operation_key="wavekit:transfer:one",
            actor="another-worker",
            expected_project_uuid=snapshot.project_uuid,
            expected_archive_sha256=exported.archive_sha256,
            confirm=True,
        )


def test_materialize_bundle_rejects_unconfirmed_mismatch_and_nonempty_target(
    tmp_path: Path,
) -> None:
    snapshot, bundle, exported = _source_bundle(tmp_path)

    with pytest.raises(ValueError, match="P2P_CONFIRMATION_REQUIRED"):
        ProjectApplicationService(tmp_path / "unconfirmed").canonical_bundle_materialize(
            source=bundle,
            operation_key="wavekit:transfer:unconfirmed",
            actor="wavekit-worker",
            expected_project_uuid=snapshot.project_uuid,
            expected_archive_sha256=exported.archive_sha256,
            confirm=False,
        )
    with pytest.raises(ValueError, match="P2P_BUNDLE_CHECKSUM_MISMATCH"):
        ProjectApplicationService(tmp_path / "mismatch").canonical_bundle_materialize(
            source=bundle,
            operation_key="wavekit:transfer:mismatch",
            actor="wavekit-worker",
            expected_project_uuid=snapshot.project_uuid,
            expected_archive_sha256="0" * 64,
            confirm=True,
        )

    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    (nonempty / "user-owned.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(ValueError, match="P2P_BUNDLE_MATERIALIZATION_TARGET_NOT_EMPTY"):
        ProjectApplicationService(nonempty).canonical_bundle_materialize(
            source=bundle,
            operation_key="wavekit:transfer:nonempty",
            actor="wavekit-worker",
            expected_project_uuid=snapshot.project_uuid,
            expected_archive_sha256=exported.archive_sha256,
            confirm=True,
        )
    assert (nonempty / "user-owned.txt").read_text(encoding="utf-8") == "preserve"


def test_bundle_materialize_cli_has_strict_json_contract(tmp_path: Path) -> None:
    snapshot, bundle, exported = _source_bundle(tmp_path)
    target = tmp_path / "cli-target"

    result = runner.invoke(
        app,
        [
            "project",
            "memory",
            "bundle-materialize",
            str(bundle),
            "--root",
            str(target),
            "--operation-key",
            "wavekit:transfer:cli",
            "--expected-project-uuid",
            snapshot.project_uuid,
            "--expected-bundle-digest",
            exported.archive_sha256,
            "--actor",
            "wavekit-worker",
            "--confirm",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["operation"] == "project.memory.bundle-materialize"
    materialized = payload["data"]["bundle_materialization"]
    assert materialized["contract"] == "p2p-bundle-materialization/v1"
    assert materialized["project_uuid"] == snapshot.project_uuid
    assert materialized["archive_sha256"] == exported.archive_sha256

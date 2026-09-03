from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.services.project_application import ProjectApplicationService

runner = CliRunner()


def _project_with_blob(root: Path) -> tuple[ProjectApplicationService, str, bytes]:
    application = ProjectApplicationService(root)
    application.init_project("Snapshot source", starter_id="empty")
    content = b"managed snapshot evidence\n"
    digest = hashlib.sha256(content).hexdigest()
    blob = root / ".p2p" / "blobs" / "sha256" / digest[:2] / digest
    blob.parent.mkdir(parents=True)
    blob.write_bytes(content)
    reference = root / ".p2p" / "governance" / "snapshot-evidence.yml"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_text(
        yaml.safe_dump(
            {
                "evidence": {
                    "kind": "managed_blob",
                    "digest": f"sha256:{digest}",
                },
                "canonical_relations": [
                    {
                        "id": "snapshot-evidence-project",
                        "type": "supports",
                        "target": "project:manifest",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return application, digest, content


def test_server_snapshot_export_is_complete_backend_neutral_and_path_free(
    tmp_path: Path,
) -> None:
    application, digest, content = _project_with_blob(tmp_path / "project")
    output = tmp_path / "replica-snapshot"

    result = application.linked_replica_server_snapshot_export(output)
    payload = result.to_dict()

    assert payload["contract"] == "p2p-linked-replica-server-snapshot/v1"
    assert payload["status"] == "exported"
    assert payload["bundle_artifact"] == "project.p2pbundle"
    assert payload["blobs"] == [
        {
            "digest": f"sha256:{digest}",
            "size": len(content),
            "media_type": "application/octet-stream",
            "artifact": f"blobs/{digest}",
        }
    ]
    bundle = output / "project.p2pbundle"
    assert hashlib.sha256(bundle.read_bytes()).hexdigest() == payload["bundle_digest"]
    assert (output / "blobs" / digest).read_bytes() == content
    assert str(tmp_path) not in json.dumps(payload)


def test_server_snapshot_export_refuses_existing_or_project_local_target(
    tmp_path: Path,
) -> None:
    application, _digest, _content = _project_with_blob(tmp_path / "project")
    existing = tmp_path / "existing"
    existing.mkdir()

    with pytest.raises(ValueError, match="OUTPUT_EXISTS"):
        application.linked_replica_server_snapshot_export(existing)
    with pytest.raises(ValueError, match="OUTPUT_INVALID"):
        application.linked_replica_server_snapshot_export(
            tmp_path / "project" / "snapshot"
        )


def test_server_snapshot_export_cli_has_strict_json_contract(tmp_path: Path) -> None:
    _application, digest, content = _project_with_blob(tmp_path / "project")
    output = tmp_path / "cli-snapshot"

    result = runner.invoke(
        app,
        [
            "project",
            "memory",
            "snapshot-export",
            "--root",
            str(tmp_path / "project"),
            "--output-directory",
            str(output),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["operation"] == "project.memory.snapshot-export"
    snapshot = payload["data"]["replica_snapshot_export"]
    assert snapshot["contract"] == "p2p-linked-replica-server-snapshot/v1"
    assert snapshot["blobs"][0]["digest"] == f"sha256:{digest}"
    assert (output / snapshot["blobs"][0]["artifact"]).read_bytes() == content


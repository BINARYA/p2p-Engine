from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.services.agent_capabilities import standalone_vertical_guidance
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.vertical_drafts import VerticalDraftService
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data

runner = CliRunner()


@pytest.fixture
def portable_release(tmp_path: Path) -> tuple[Path, str, str]:
    authoring = P2PWorkspace(tmp_path / "authoring")
    source = tmp_path / "artifact-source"
    authoring.scaffold_portable_vertical(
        source,
        publisher="test",
        vertical_id="artifact_boundary",
        version="1.0.0",
        name="Artifact Boundary",
        license_id="MIT",
    )
    dependency_coordinate = "binarya/base_project@2.0.0"
    dependency_identity = ProjectVerticalService.semantic_pack_identity(
        authoring.show_project_vertical(dependency_coordinate)
    )
    manifest_path = source / "manifest.yml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["manifest"]["lineage"] = {
        "forked_from": "upstream/artifact_boundary@0.9.0",
        "previous_release": "test/artifact_boundary@0.9.0",
    }
    manifest["manifest"]["dependencies"] = [
        {
            "coordinate": dependency_coordinate,
            "checksum": f"sha256:{dependency_identity.digest}",
            "semantic_identity": dependency_identity.to_dict(),
        }
    ]
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    examples = source / "examples"
    examples.mkdir()
    (examples / "usage.md").write_text(
        "# Documentary example\n\nThis remains part of the artifact bytes.\n",
        encoding="utf-8",
    )
    archive = tmp_path / "artifact-boundary.p2pv"
    packaged = authoring.package_portable_vertical(source, output=archive)
    return archive, packaged.artifact_checksum, packaged.coordinate


@pytest.mark.cli
def test_direct_inspect_is_read_only_and_offline_init_does_not_import_release_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    portable_release: tuple[Path, str, str],
) -> None:
    archive, artifact_checksum, coordinate = portable_release
    user_home = tmp_path / "p2p-home"
    inspection_root = tmp_path / "inspection-root"
    project_root = tmp_path / "project"
    monkeypatch.setenv("P2P_HOME", str(user_home))

    inspected = runner.invoke(
        app,
        [
            "vertical",
            "inspect",
            str(archive),
            "--root",
            str(inspection_root),
            "--format",
            "json",
        ],
    )

    assert inspected.exit_code == 0, inspected.stdout
    inspection = cli_data(inspected)
    assert inspection["coordinate"] == coordinate
    assert inspection["artifact_checksum"] == artifact_checksum
    assert not inspection_root.exists()
    assert not user_home.exists()

    initialized = runner.invoke(
        app,
        [
            "init",
            "Direct artifact project",
            "--vertical-pack",
            str(archive),
            "--expected-checksum",
            artifact_checksum,
            "--owner",
            "owner",
            "--operation-key",
            "issue-11-direct-artifact-init",
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )

    assert initialized.exit_code == 0, initialized.stdout
    assert P2PWorkspace(project_root).active_project_vertical().coordinate == coordinate
    assert not (user_home / "vertical-drafts").exists()
    assert not (user_home / "cache" / "verticals").exists()


@pytest.mark.service
def test_draft_from_release_is_a_fresh_clone_not_an_exact_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P2P_HOME", str(tmp_path / "p2p-home"))
    service = VerticalDraftService(
        tmp_path / "project",
        id_factory=lambda: "VDRAFT-1234567890ABCDEF",
    )

    created = service.create_from(
        "binarya/software_project@2.0.0",
        version="2.0.1",
    ).draft

    assert created.state.draft_id == "VDRAFT-1234567890ABCDEF"
    assert created.state.revision == 1
    assert created.state.origin.kind == "clone"
    assert created.state.origin.coordinate == "binarya/software_project@2.0.0"
    assert created.state.document["identity"]["version"] == "2.0.1"
    assert created.state.document["lineage"] == {
        "forked_from": None,
        "previous_release": None,
    }
    assert created.state.document["source_attribution"]["origin_coordinate"] == (
        "binarya/software_project@2.0.0"
    )
    assert created.evidence.materialization is None
    assert created.evidence.validation is None
    assert created.evidence.package is None

    document = dict(created.state.document)
    document["description"] = "Edited derivative"
    updated = service.update(
        created.state.draft_id,
        document,
        expected_revision=created.state.revision,
    ).draft

    assert updated.state.revision == 2
    assert updated.state.origin.kind == "clone"
    assert updated.evidence.materialization is None
    assert updated.evidence.validation is None
    assert updated.evidence.package is None


@pytest.mark.cli
def test_public_guidance_names_clone_and_does_not_advertise_exact_import() -> None:
    help_result = runner.invoke(app, ["vertical", "draft", "create", "--help"])

    assert help_result.exit_code == 0, help_result.stdout
    assert "clone/derive one exact local release" in help_result.stdout.lower()
    assert "exact-import" not in help_result.stdout.lower()

    guidance = standalone_vertical_guidance().lower()
    assert "lossless portable release" in guidance
    assert "clone/derivation" in guidance
    assert "not a lossless import or restore" in guidance
    assert "exact-import" not in guidance

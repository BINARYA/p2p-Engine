from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.project_verticals import VerticalDependency
from p2p_engine.core.release_contracts import current_contract_versions
from p2p_engine.core.vertical_provenance import (
    PORTABLE_VERTICAL_PROVENANCE_CONTRACT,
    PROVENANCE_STATUS_CALCULATED,
    PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED,
    PROVENANCE_STATUS_UNAVAILABLE,
    PROVENANCE_STATUS_VERIFIABLE_WHEN_AVAILABLE,
    PROVENANCE_STATUS_VERIFIED_AGAINST_REFERENCE,
    build_portable_vertical_provenance,
    verify_dependency_target_identity,
)
from p2p_engine.core.vertical_semantic_identity import VerticalSemanticIdentity
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data

runner = CliRunner()


def _packaged_vertical(tmp_path: Path) -> tuple[P2PWorkspace, Path, Path]:
    workspace = P2PWorkspace(tmp_path)
    source = tmp_path / "portable-provenance"
    workspace.scaffold_portable_vertical(
        source,
        publisher="acme",
        vertical_id="portable_provenance",
        version="1.2.3",
        name="Portable Provenance",
        license_id="MIT",
    )
    manifest_path = source / "manifest.yml"
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["manifest"]["source"] = "draft"
    payload["manifest"]["lineage"] = {
        "forked_from": "upstream/base@1.0.0",
        "previous_release": "acme/portable_provenance@1.2.2",
    }
    manifest_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    archive = tmp_path / "portable-provenance.p2pv"
    workspace.package_portable_vertical(source, output=archive)
    return workspace, source, archive


def test_portable_provenance_classifies_calculations_and_declarations(
    tmp_path: Path,
) -> None:
    workspace, _source, archive = _packaged_vertical(tmp_path)

    inspection = workspace.inspect_portable_vertical(archive, view="effective")
    provenance = inspection.provenance

    assert provenance is not None
    payload = provenance.to_dict()
    assert payload["contract_version"] == PORTABLE_VERTICAL_PROVENANCE_CONTRACT
    subject = payload["subject"]
    assert subject["coordinate"] == "acme/portable_provenance@1.2.3"
    assert subject["schema_version"] == 3
    assert subject["package_version"] == 1
    assert subject["artifact"] == {
        "identity": {"algorithm": "sha256", "digest": inspection.artifact_checksum},
        "status": PROVENANCE_STATUS_CALCULATED,
    }
    assert subject["semantic"] == {
        "identity": inspection.semantic_identity.to_dict(),
        "status": PROVENANCE_STATUS_CALCULATED,
    }
    assert payload["claims"] == {
        "publisher": {
            "value": "acme",
            "status": PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED,
        },
        "license": {
            "value": "MIT",
            "status": PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED,
        },
        "construction_source": {
            "value": "draft",
            "status": PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED,
        },
    }
    assert payload["lineage"] == [
        {
            "relation": "forked_from",
            "coordinate": "upstream/base@1.0.0",
            "status": PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED,
        },
        {
            "relation": "previous_release",
            "coordinate": "acme/portable_provenance@1.2.2",
            "status": PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED,
        },
    ]


def test_directory_has_no_artifact_identity_but_has_calculated_semantic_identity(
    tmp_path: Path,
) -> None:
    workspace, source, _archive = _packaged_vertical(tmp_path)

    provenance = workspace.inspect_portable_vertical(source).provenance

    assert provenance is not None
    assert provenance.subject.artifact.status == PROVENANCE_STATUS_UNAVAILABLE
    assert provenance.subject.artifact.identity is None
    assert provenance.subject.semantic.status == PROVENANCE_STATUS_CALCULATED


def test_dependency_edge_stays_declarative_when_target_identity_matches() -> None:
    expected = VerticalSemanticIdentity.v1("a" * 64)
    dependency = VerticalDependency(
        coordinate="upstream/base@1.0.0",
        checksum=f"sha256:{expected.digest}",
        semantic_identity=expected,
    )
    provenance = build_portable_vertical_provenance(
        coordinate="acme/child@1.0.0",
        schema_version=3,
        package_version=1,
        artifact_checksum="b" * 64,
        semantic_identity=VerticalSemanticIdentity.v1("c" * 64),
        publisher="acme",
        license_id="MIT",
        construction_source="draft",
        lineage={},
        dependencies=[dependency],
    )
    declared = provenance.dependencies[0]
    assert declared.to_dict() == {
        "relation": {
            "coordinate": "upstream/base@1.0.0",
            "status": PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED,
        },
        "target_semantic_identity": {
            "identity": expected.to_dict(),
            "status": PROVENANCE_STATUS_VERIFIABLE_WHEN_AVAILABLE,
        },
    }

    compared = verify_dependency_target_identity(declared, expected)

    assert declared.relation_status == PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED
    assert declared.target_identity_status == PROVENANCE_STATUS_VERIFIABLE_WHEN_AVAILABLE
    assert compared.relation_status == PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED
    assert (
        compared.target_identity_status
        == PROVENANCE_STATUS_VERIFIED_AGAINST_REFERENCE
    )
    with pytest.raises(ValueError, match="P2P_VERTICAL_SEMANTIC_IDENTITY_MISMATCH"):
        verify_dependency_target_identity(
            declared,
            VerticalSemanticIdentity.v1("d" * 64),
        )


def test_exact_artifact_copy_preserves_portable_provenance_across_host_locations(
    tmp_path: Path,
) -> None:
    workspace, _source, archive = _packaged_vertical(tmp_path)
    baseline = workspace.inspect_portable_vertical(archive).provenance
    assert baseline is not None
    baseline_payload = baseline.to_dict()

    for label in ("registry", "wavekit", "peer", "receiving-local"):
        destination = tmp_path / label / archive.name
        destination.parent.mkdir()
        shutil.copyfile(archive, destination)
        observed = workspace.inspect_portable_vertical(destination).provenance
        assert observed is not None
        assert destination.read_bytes() == archive.read_bytes()
        assert observed.to_dict() == baseline_payload

    serialized = json.dumps(baseline_payload, sort_keys=True)
    for contextual_key in (
        "registry_url",
        "uploader_identity",
        "moderation",
        "receipt",
        "wavekit_project_id",
        "source_attribution",
    ):
        assert contextual_key not in serialized


def test_resolvable_lineage_parent_does_not_upgrade_declarative_relation(
    tmp_path: Path,
) -> None:
    workspace, _source, child_archive = _packaged_vertical(tmp_path)
    parent_source = tmp_path / "parent"
    workspace.scaffold_portable_vertical(
        parent_source,
        publisher="upstream",
        vertical_id="base",
        version="1.0.0",
        name="Base",
        license_id="MIT",
    )
    workspace.package_portable_vertical(
        parent_source,
        output=tmp_path / "parent.p2pv",
    )

    provenance = workspace.inspect_portable_vertical(child_archive).provenance

    assert provenance is not None
    fork = next(item for item in provenance.lineage if item.relation == "forked_from")
    assert fork.coordinate == "upstream/base@1.0.0"
    assert fork.status == PROVENANCE_STATUS_DECLARATIVE_UNVERIFIED


def test_invalid_lineage_fails_before_provenance_is_reported(tmp_path: Path) -> None:
    workspace, source, _archive = _packaged_vertical(tmp_path)
    manifest_path = source / "manifest.yml"
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["manifest"]["lineage"]["forked_from"] = "not-a-coordinate"
    manifest_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    validation = workspace.validate_portable_vertical(source)

    assert validation.valid is False
    assert validation.provenance is None
    assert "P2P_VERTICAL_INVALID_COORDINATE" in validation.issues[0].message


@pytest.mark.cli
def test_both_portable_inspect_commands_expose_the_same_additive_provenance(
    tmp_path: Path,
) -> None:
    _workspace, _source, archive = _packaged_vertical(tmp_path)

    public_result = runner.invoke(
        app,
        ["vertical", "inspect", str(archive), "--root", str(tmp_path), "--format", "json"],
    )
    project_result = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "inspect",
            str(archive),
            "--root",
            str(tmp_path),
            "--format",
            "json",
        ],
    )

    assert public_result.exit_code == 0
    assert project_result.exit_code == 0
    public = cli_data(public_result)
    project = cli_data(project_result)
    assert public["provenance"] == project["provenance"]
    assert public["artifact_checksum"] == project["artifact_checksum"]
    assert public["semantic_identity"] == project["semantic_identity"]
    assert {"target", "coordinate", "artifact_checksum", "semantic_checksum", "pack"} <= set(
        public
    )


def test_release_contract_inventory_advertises_portable_provenance() -> None:
    assert (
        current_contract_versions()["portable_vertical_provenance_contract"]
        == PORTABLE_VERTICAL_PROVENANCE_CONTRACT
    )

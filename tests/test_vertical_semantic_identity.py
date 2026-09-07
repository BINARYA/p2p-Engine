from __future__ import annotations

import base64
import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.project_structure import StructureOrigin
from p2p_engine.core.vertical_drafts import VerticalDraftOrigin
from p2p_engine.core.vertical_registry import (
    VerticalRelease,
    VerticalReleaseArtifact,
    VerticalReleaseDependency,
    VerticalUserPaths,
)
from p2p_engine.core.vertical_semantic_identity import (
    VERTICAL_SEMANTIC_CHECKSUM_CONTRACT,
    VerticalSemanticComparison,
    VerticalSemanticIdentity,
    calculate_vertical_semantic_identity,
    compare_vertical_semantic_identities,
    registry_v2_semantic_identity,
    supported_vertical_semantic_contracts,
    verify_vertical_semantic_identity,
)
from p2p_engine.services.project_verticals import (
    ProjectVerticalService,
    vertical_semantic_canonical_bytes_v1,
    vertical_semantic_identity_v1,
    vertical_semantic_projection_v1,
)
from p2p_engine.services.vertical_catalog import VerticalCacheService
from p2p_engine.services.vertical_packages import PortableVerticalPackageService
from p2p_engine.services.vertical_registry import _parse_capabilities, parse_vertical_release
from p2p_engine.mcp.handlers.project import handle_project_tool
from p2p_engine.storage.filesystem import P2PWorkspace

FIXTURE = Path(__file__).parent / "fixtures" / "vertical_semantic_checksum" / "v1"
RUNNER = CliRunner()


def _pack():
    source = FIXTURE / "input"
    service = ProjectVerticalService(
        root=source.parent,
        p2p_dir=source.parent / ".unused-p2p",
        proposal_summaries=lambda: [],
        find_proposal_dir=lambda value: source.parent / value,
    )
    return service.load_explicit_pack(source)


def test_v067_static_golden_vector_freezes_projection_bytes_and_digest() -> None:
    expected = json.loads((FIXTURE / "expected.json").read_text(encoding="utf-8"))
    pack = _pack()

    projection = vertical_semantic_projection_v1(pack)
    canonical = vertical_semantic_canonical_bytes_v1(pack)
    identity = vertical_semantic_identity_v1(pack)

    assert projection == expected["expected_projection"]
    assert base64.b64encode(canonical).decode("ascii") == expected["expected_canonical_base64"]
    assert identity.to_dict() == {
        "contract": VERTICAL_SEMANTIC_CHECKSUM_CONTRACT,
        "algorithm": "sha256",
        "digest": expected["expected_sha256"],
    }
    assert canonical.endswith(b"\n")
    assert b"\r\n" not in canonical


def test_v1_calculator_does_not_delegate_to_compatibility_projection(monkeypatch) -> None:
    import p2p_engine.services.project_verticals as project_verticals

    monkeypatch.setattr(
        project_verticals,
        "_pack_payload",
        lambda _pack: pytest.fail("v1 must not use the mutable compatibility facade"),
    )
    assert vertical_semantic_identity_v1(_pack()).contract == VERTICAL_SEMANTIC_CHECKSUM_CONTRACT


def test_naming_v1_does_not_change_v067_portable_artifact_bytes(tmp_path: Path) -> None:
    expected = json.loads((FIXTURE / "expected.json").read_text(encoding="utf-8"))
    source = FIXTURE / "input"
    vertical_service = ProjectVerticalService(
        root=source.parent,
        p2p_dir=source.parent / ".unused-p2p",
        proposal_summaries=lambda: [],
        find_proposal_dir=lambda value: source.parent / value,
    )
    package_service = PortableVerticalPackageService(
        root=source.parent,
        p2p_dir=source.parent / ".unused-p2p",
        vertical_service=vertical_service,
    )
    result = package_service.package(source, output=tmp_path / "candidate.p2pv")
    assert result.artifact_checksum == expected["expected_artifact_sha256"]
    assert result.size == expected["expected_artifact_size"]


def test_identity_is_strict_and_v1_fixes_sha256() -> None:
    digest = "a" * 64
    assert VerticalSemanticIdentity.v1(digest).digest == digest
    with pytest.raises(ValueError, match="lowercase"):
        VerticalSemanticIdentity.v1("A" * 64)
    with pytest.raises(ValueError, match="requires algorithm sha256"):
        VerticalSemanticIdentity(VERTICAL_SEMANTIC_CHECKSUM_CONTRACT, "sha512", digest)
    with pytest.raises(ValueError, match="must be 64"):
        VerticalSemanticIdentity.v1("sha256:" + digest)


def test_comparison_has_equal_different_and_incomparable_outcomes() -> None:
    left = VerticalSemanticIdentity.v1("a" * 64)
    assert compare_vertical_semantic_identities(left, left) is VerticalSemanticComparison.EQUAL
    assert compare_vertical_semantic_identities(
        left, VerticalSemanticIdentity.v1("b" * 64)
    ) is VerticalSemanticComparison.DIFFERENT
    unknown = VerticalSemanticIdentity("example-semantic/v2", "sha256", "a" * 64)
    assert compare_vertical_semantic_identities(left, unknown) is VerticalSemanticComparison.INCOMPARABLE


def test_dispatch_calculate_verify_and_supported_contracts() -> None:
    pack = _pack()
    identity = calculate_vertical_semantic_identity(
        pack,
        contract=VERTICAL_SEMANTIC_CHECKSUM_CONTRACT,
        v1_calculator=vertical_semantic_identity_v1,
    )
    assert supported_vertical_semantic_contracts() == (VERTICAL_SEMANTIC_CHECKSUM_CONTRACT,)
    verify_vertical_semantic_identity(identity, identity)
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        calculate_vertical_semantic_identity(
            pack, contract="example-semantic/v2", v1_calculator=vertical_semantic_identity_v1
        )
    with pytest.raises(ValueError, match="MISMATCH"):
        verify_vertical_semantic_identity(identity, replace(identity, digest="b" * 64))


def test_registry_v2_scalar_only_is_v1_and_dual_shape_must_agree() -> None:
    digest = "c" * 64
    expected = VerticalSemanticIdentity.v1(digest)
    assert registry_v2_semantic_identity(digest) == expected
    assert registry_v2_semantic_identity(digest, expected.to_dict()) == expected
    with pytest.raises(ValueError, match="CONFLICT"):
        registry_v2_semantic_identity(
            digest, VerticalSemanticIdentity.v1("d" * 64).to_dict()
        )
    with pytest.raises(ValueError, match="unsupported"):
        registry_v2_semantic_identity(
            digest,
            {"contract": "example-semantic/v2", "algorithm": "sha256", "digest": digest},
        )


def test_artifact_and_vertical_semantic_identities_cannot_be_substituted() -> None:
    identity = vertical_semantic_identity_v1(_pack())
    with pytest.raises(ValueError, match="unknown fields"):
        VerticalSemanticIdentity.from_mapping(
            {**identity.to_dict(), "artifact_sha256": identity.digest}
        )


def test_schema3_dependency_structured_identity_is_additive_to_frozen_v1(
    tmp_path: Path,
) -> None:
    source = tmp_path / "pack"
    shutil.copytree(FIXTURE / "input", source)
    manifest_path = source / "manifest.yml"
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    dependency = payload["manifest"]["dependencies"][0]
    dependency["semantic_identity"] = VerticalSemanticIdentity.v1(
        dependency["checksum"].removeprefix("sha256:")
    ).to_dict()
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    service = ProjectVerticalService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        proposal_summaries=lambda: [],
        find_proposal_dir=lambda value: tmp_path / value,
    )

    identity = service.semantic_pack_identity(service.load_explicit_pack(source))

    expected = json.loads((FIXTURE / "expected.json").read_text(encoding="utf-8"))
    assert identity.digest == expected["expected_sha256"]


def test_schema3_dependency_rejects_conflicting_structured_identity(
    tmp_path: Path,
) -> None:
    source = tmp_path / "pack"
    shutil.copytree(FIXTURE / "input", source)
    manifest_path = source / "manifest.yml"
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["manifest"]["dependencies"][0]["semantic_identity"] = (
        VerticalSemanticIdentity.v1("2" * 64).to_dict()
    )
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    vertical_service = ProjectVerticalService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        proposal_summaries=lambda: [],
        find_proposal_dir=lambda value: tmp_path / value,
    )
    package_service = PortableVerticalPackageService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        vertical_service=vertical_service,
    )

    inspection = package_service.validate(source)

    assert not inspection.valid
    assert "P2P_VERTICAL_SEMANTIC_IDENTITY_CONFLICT" in inspection.issues[0].message


def _registry_release(digest: str) -> dict[str, object]:
    return {
        "coordinate": "baseline/fixture@1.0.0",
        "name": "Fixture",
        "description": "Registry compatibility fixture",
        "visibility": "public",
        "semantic_checksum": digest,
        "schema_version": 3,
        "artifact": {
            "url": "/fixture.p2pv",
            "sha256": "e" * 64,
            "size": 10,
        },
        "dependencies": [
            {
                "coordinate": "baseline/base@1.0.0",
                "semantic_checksum": "f" * 64,
            }
        ],
    }


def test_registry_v2_release_is_strictly_additive_and_legacy_scalar_stays_valid() -> None:
    payload = _registry_release("a" * 64)
    legacy = parse_vertical_release(payload, registry="wavekit")
    assert legacy.semantic_identity == VerticalSemanticIdentity.v1("a" * 64)
    assert legacy.dependencies[0].semantic_identity == VerticalSemanticIdentity.v1("f" * 64)

    dual = {
        **payload,
        "semantic_identity": legacy.semantic_identity.to_dict(),
        "dependencies": [
            {
                **payload["dependencies"][0],
                "semantic_identity": legacy.dependencies[0].semantic_identity.to_dict(),
            }
        ],
    }
    assert parse_vertical_release(dual, registry="wavekit").semantic_identity == legacy.semantic_identity


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: (
            payload.update(
                semantic_identity=VerticalSemanticIdentity.v1("a" * 64).to_dict()
            ),
            payload.pop("semantic_checksum"),
        ),
        lambda payload: payload.update(
            semantic_identity=VerticalSemanticIdentity.v1("b" * 64).to_dict()
        ),
        lambda payload: payload.update(
            semantic_identity={
                "contract": VERTICAL_SEMANTIC_CHECKSUM_CONTRACT,
                "algorithm": "sha512",
                "digest": "a" * 64,
            }
        ),
        lambda payload: payload.update(
            semantic_identity={
                "contract": "example-semantic/v2",
                "algorithm": "sha256",
                "digest": "a" * 64,
            }
        ),
    ],
)
def test_registry_v2_rejects_structured_only_conflicting_and_unsupported_shapes(mutate) -> None:
    payload = _registry_release("a" * 64)
    mutate(payload)
    with pytest.raises(ValueError):
        parse_vertical_release(payload, registry="wavekit")


def test_registry_capability_advertisement_is_optional_and_not_a_required_field() -> None:
    payload = {
        "protocol_version": "p2p-vertical-registry/v2",
        "api_base": "/api/v2",
        "max_artifact_bytes": 1024,
        "endpoints": {
            "domains": "domains",
            "domain": "domains/{domain_id}",
            "search": "search",
            "releases": "releases",
            "release": "releases/{publisher}/{vertical_id}/{version}",
        },
        "required_fields": [],
    }
    assert _parse_capabilities(payload).semantic_checksum_contracts == (
        VERTICAL_SEMANTIC_CHECKSUM_CONTRACT,
    )
    payload["semantic_checksum_contracts"] = [VERTICAL_SEMANTIC_CHECKSUM_CONTRACT]
    assert _parse_capabilities(payload).to_dict()["semantic_checksum_contracts"] == [
        VERTICAL_SEMANTIC_CHECKSUM_CONTRACT
    ]
    payload["required_fields"] = ["semantic_identity"]
    with pytest.raises(ValueError, match="unsupported required"):
        _parse_capabilities(payload)


def test_vertical_lock_writes_contract_and_legacy_read_does_not_rewrite(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Semantic lock")
    lock_path = tmp_path / ".p2p" / "project" / "vertical.lock.yml"
    current = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    checksum = current["project_vertical_lock"]["checksum"]
    assert checksum["contract"] == VERTICAL_SEMANTIC_CHECKSUM_CONTRACT
    assert checksum["algorithm"] == "sha256"

    checksum.pop("contract")
    lock_path.write_text(yaml.safe_dump(current, sort_keys=False), encoding="utf-8")
    before = lock_path.read_bytes()
    status = workspace.project_vertical_lock_status()
    assert status.status == "valid"
    assert status.locked.semantic_identity == VerticalSemanticIdentity.v1(
        status.locked.checksum
    )
    assert lock_path.read_bytes() == before


def test_legacy_structure_and_draft_origins_normalize_to_v1_in_memory() -> None:
    digest = "7" * 64
    structure = StructureOrigin.from_mapping(
        {
            "kind": "vertical_release",
            "identity": "baseline/fixture@1.0.0",
            "checksum": digest,
            "external_ref": None,
            "applied_at": "2026-09-07T00:00:00Z",
            "applied_by": "owner",
        }
    )
    draft = VerticalDraftOrigin(
        kind="clone",
        coordinate="baseline/fixture@1.0.0",
        semantic_checksum=digest,
    )
    assert structure.semantic_identity == VerticalSemanticIdentity.v1(digest)
    assert draft.semantic_identity == VerticalSemanticIdentity.v1(digest)


def test_legacy_registry_cache_normalizes_to_v1_without_read_time_rewrite(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "source.p2pv"
    artifact.write_bytes(b"portable fixture")
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    release = VerticalRelease(
        coordinate="baseline/fixture@1.0.0",
        name="Fixture",
        description="",
        visibility="public",
        semantic_checksum="8" * 64,
        schema_version=3,
        artifact=VerticalReleaseArtifact(
            url="/fixture.p2pv",
            sha256=artifact_digest,
            size=artifact.stat().st_size,
        ),
        dependencies=(
            VerticalReleaseDependency(
                coordinate="baseline/base@1.0.0",
                semantic_checksum="9" * 64,
            ),
        ),
        registry="wavekit",
    )
    cache = VerticalCacheService(
        paths=VerticalUserPaths(tmp_path / "data", tmp_path / "cache")
    )
    directory = cache.release_directory("wavekit", release.coordinate)
    cache.write_candidate(directory, release, artifact)
    metadata_path = directory / "metadata.yml"
    legacy = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    release_payload = legacy["vertical_cache"]["release"]
    release_payload.pop("semantic_identity")
    release_payload["dependencies"][0].pop("semantic_identity")
    metadata_path.write_text(yaml.safe_dump(legacy, sort_keys=False), encoding="utf-8")
    before = metadata_path.read_bytes()

    cached = cache.read("wavekit", release.coordinate)

    assert cached.release.semantic_identity == VerticalSemanticIdentity.v1("8" * 64)
    assert cached.release.dependencies[0].semantic_identity == VerticalSemanticIdentity.v1(
        "9" * 64
    )
    assert metadata_path.read_bytes() == before


def _workspace_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_cli_unknown_parent_contract_is_stable_json_failure_without_mutation(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Semantic CLI")
    before = _workspace_snapshot(tmp_path)

    result = RUNNER.invoke(
        app,
        [
            "project",
            "vertical",
            "export",
            "preview",
            "--publisher",
            "baseline",
            "--id",
            "derived",
            "--version",
            "1.0.0",
            "--name",
            "Derived",
            "--license",
            "GPL-3.0-or-later",
            "--primary-domain-key",
            "software",
            "--primary-domain-name",
            "Software",
            "--lineage-mode",
            "derived",
            "--parent-coordinate",
            "baseline/parent@1.0.0",
            "--parent-semantic-checksum",
            "a" * 64,
            "--parent-semantic-contract",
            "example-semantic/v2",
            "--parent-semantic-algorithm",
            "sha256",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["error"]["code"] == "P2P_VERTICAL_SEMANTIC_CONTRACT_UNSUPPORTED"
    assert "Traceback" not in result.stdout
    assert _workspace_snapshot(tmp_path) == before


def test_mcp_malformed_parent_identity_fails_without_mutation(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Semantic MCP")
    before = _workspace_snapshot(tmp_path)

    with pytest.raises(ValueError, match="P2P_VERTICAL_SEMANTIC_IDENTITY_INVALID"):
        handle_project_tool(
            workspace,
            "p2p_project_structure_export_preview",
            {
                "publisher": "baseline",
                "vertical_id": "derived",
                "version": "1.0.0",
                "name": "Derived",
                "license": "GPL-3.0-or-later",
                "primary_domain": {"key": "software", "name": "Software"},
                "lineage_mode": "derived",
                "parent_coordinate": "baseline/parent@1.0.0",
                "parent_semantic_checksum": "a" * 64,
                "parent_semantic_identity": ["not", "a", "mapping"],
            },
        )

    assert _workspace_snapshot(tmp_path) == before

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Mapping

import pytest
from typer.testing import CliRunner

from p2p_engine.adapters.credential_store import MemoryCredentialStore
from p2p_engine.cli import app
from p2p_engine.core.vertical_registry import (
    RegistryCredential,
    VerticalReleaseArtifact,
    VerticalUserPaths,
)
from p2p_engine.services.vertical_catalog import VerticalCacheService, VerticalCatalogService
from p2p_engine.services.vertical_draft_lifecycle import VerticalDraftLifecycleService
from p2p_engine.services.vertical_draft_materializer import (
    VerticalDraftMaterializer,
    vertical_draft_roundtrip_shape,
)
from p2p_engine.services.vertical_drafts import (
    VerticalDraftService,
    normalize_vertical_draft_document,
)
from p2p_engine.services.vertical_registry import (
    VerticalRegistryClient,
    VerticalRegistryConfigurationService,
)
from p2p_engine.services.project_verticals import ProjectVerticalService
from p2p_engine.services.vertical_packages import PortableVerticalPackageService
from p2p_engine.mcp.handlers.proposals import handle_proposal_tool
from p2p_engine.storage.filesystem import P2PWorkspace


runner = CliRunner()
PROTOCOL = "p2p-vertical-registry/v1"
FIXTURES = Path(__file__).parent / "fixtures" / "vertical_drafts"


def _services(tmp_path: Path):
    paths = VerticalUserPaths(tmp_path / "user-data", tmp_path / "user-cache")
    cache = VerticalCacheService(paths=paths)
    catalog = VerticalCatalogService(tmp_path / "project", cache=cache)
    drafts = VerticalDraftService(
        tmp_path / "project",
        catalog=catalog,
        draft_root=paths.vertical_drafts_root,
        id_factory=lambda: "VDRAFT-1234567890ABCDEF",
    )
    lifecycle = VerticalDraftLifecycleService(
        tmp_path / "project",
        drafts=drafts,
        cache=cache,
    )
    return drafts, lifecycle, cache


def _clone(drafts: VerticalDraftService):
    return drafts.create_from(
        "binarya/software_project@2.0.0",
        version="2.0.1",
        previous_release="binarya/software_project@2.0.0",
    )


def _package(tmp_path: Path, drafts, lifecycle):
    created = _clone(drafts)
    draft_id = created.draft.state.draft_id
    lifecycle.materialize(draft_id, tmp_path / "materialized")
    validated = lifecycle.validate(draft_id)
    assert validated.draft.evidence.validation["valid"] is True
    packaged = lifecycle.package(draft_id, tmp_path / "release.p2pv")
    return draft_id, packaged


@pytest.mark.service
def test_empty_draft_is_deterministic_outside_project_memory_and_has_no_placeholder(
    tmp_path: Path,
) -> None:
    drafts, _lifecycle, _cache = _services(tmp_path)

    created = drafts.create_empty()
    inspected = drafts.inspect(created.draft.state.draft_id)

    assert inspected.state.document_hash == created.draft.state.document_hash
    assert inspected.state.document["sections"] == []
    assert inspected.assessment.readiness == 0
    assert inspected.assessment.publishable is False
    assert "Custom Overview" not in json.dumps(inspected.state.document)
    assert ".p2p" not in inspected.state.path.parts
    assert any(
        item.code == "P2P_VERTICAL_NO_SECTIONS"
        for item in inspected.assessment.diagnostics
    )


@pytest.mark.service
def test_clone_lineage_roundtrip_update_conflict_and_evidence_invalidation(
    tmp_path: Path,
) -> None:
    drafts, lifecycle, _cache = _services(tmp_path)
    draft_id, packaged = _package(tmp_path, drafts, lifecycle)
    before = (packaged.draft.state.path / "draft.yml").read_bytes()
    document = dict(packaged.draft.state.document)
    document["description"] = "A revised WaveKit software vertical."

    updated = drafts.update(
        draft_id,
        document,
        expected_revision=packaged.draft.state.revision,
    )

    assert updated.draft.state.revision == 2
    assert updated.draft.state.document["lineage"]["previous_release"]["coordinate"] == (
        "binarya/software_project@2.0.0"
    )
    assert updated.draft.state.document["lineage"]["forked_from"] is None
    assert updated.draft.state.document["extends"] is None
    assert updated.draft.evidence.materialization is None
    assert updated.draft.evidence.validation is None
    assert updated.draft.evidence.package is None

    current_bytes = (updated.draft.state.path / "draft.yml").read_bytes()
    assert current_bytes != before
    with pytest.raises(ValueError, match="P2P_VERTICAL_DRAFT_CONFLICT"):
        drafts.update(draft_id, document, expected_revision=1)
    assert (updated.draft.state.path / "draft.yml").read_bytes() == current_bytes


@pytest.mark.service
def test_concurrent_draft_updates_allow_at_most_one_revision_winner(tmp_path: Path) -> None:
    drafts, _lifecycle, _cache = _services(tmp_path)
    created = _clone(drafts)
    draft_id = created.draft.state.draft_id

    def update(description: str) -> str:
        document = dict(created.draft.state.document)
        document["description"] = description
        try:
            drafts.update(draft_id, document, expected_revision=1)
            return "updated"
        except ValueError as exc:
            return str(exc).split(":", 1)[0]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(update, ("First", "Second")))

    assert results.count("updated") == 1
    assert set(results) <= {
        "updated",
        "P2P_VERTICAL_DRAFT_BUSY",
        "P2P_VERTICAL_DRAFT_CONFLICT",
    }
    assert drafts.inspect(draft_id).state.revision == 2


@pytest.mark.unit
def test_normalized_document_enforces_section_field_text_and_total_byte_limits() -> None:
    base = VerticalDraftService.empty_document()
    too_many_sections = {
        **base,
        "sections": [
            {"id": f"section_{index}", "title": "Section", "purpose": "Purpose", "fields": []}
            for index in range(129)
        ],
    }
    too_many_fields = {
        **base,
        "sections": [
            {
                "id": "section",
                "title": "Section",
                "purpose": "Purpose",
                "fields": [
                    {"id": f"field_{index}", "label": "Field"}
                    for index in range(1_025)
                ],
            }
        ],
    }
    oversized_text = {**base, "description": "x" * 32_769}
    oversized_document = {
        **base,
        "compatibility": {f"key_{index}": "x" * 300 for index in range(4_000)},
    }

    for document in (
        too_many_sections,
        too_many_fields,
        oversized_text,
        oversized_document,
    ):
        with pytest.raises(ValueError, match="P2P_VERTICAL_DRAFT_LIMIT"):
            normalize_vertical_draft_document(document)


@pytest.mark.integration
def test_materialize_package_and_local_add_are_roundtrippable_and_idempotent(
    tmp_path: Path,
) -> None:
    drafts, lifecycle, cache = _services(tmp_path)
    draft_id, packaged = _package(tmp_path, drafts, lifecycle)
    first_bytes = (tmp_path / "release.p2pv").read_bytes()
    second = lifecycle.package(draft_id, tmp_path / "release-again.p2pv")

    assert (tmp_path / "release-again.p2pv").read_bytes() == first_bytes
    materialized = VerticalDraftMaterializer.normalized_from_materialized(
        P2PWorkspace(tmp_path / "project"),
        tmp_path / "materialized",
    )
    assert vertical_draft_roundtrip_shape(materialized) == vertical_draft_roundtrip_shape(
        second.draft.state.document
    )

    added = lifecycle.add_local(draft_id)
    repeated = lifecycle.add_local(draft_id)
    assert added.draft.evidence.local_adds[-1]["status"] == "added"
    assert repeated.draft.evidence.local_adds[-1]["status"] == "already_present"
    cached = cache.read("local", "binarya/software_project@2.0.1")
    assert cached is not None
    conflicting_artifact = tmp_path / "conflicting.p2pv"
    conflicting_artifact.write_bytes(b"different immutable bytes")
    conflicting_release = replace(
        cached.release,
        artifact=VerticalReleaseArtifact(
            url=conflicting_artifact.name,
            sha256=hashlib.sha256(conflicting_artifact.read_bytes()).hexdigest(),
            size=conflicting_artifact.stat().st_size,
        ),
    )
    with pytest.raises(ValueError, match="P2P_REGISTRY_IMMUTABILITY_VIOLATION"):
        cache.add_local(conflicting_release, conflicting_artifact)
    inspected = VerticalCatalogService(
        tmp_path / "project",
        cache=cache,
    ).inspect_cached(
        VerticalCatalogService(tmp_path / "project", cache=cache).resolve(
            "binarya/software_project@2.0.1"
        )
    )
    assert inspected.pack.coordinate == "binarya/software_project@2.0.1"


class _PublicationTransport:
    def __init__(self) -> None:
        self.published: list[dict[str, object]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        token: str = "",
        form: Mapping[str, str] | None = None,
        max_bytes: int = 1_048_576,
    ) -> object:
        assert method == "GET"
        return {
            "vertical_registry": {
                "protocol_version": PROTOCOL,
                "api_base": "/api/vertical-registry/v1",
                "max_artifact_bytes": 8_388_608,
                "endpoints": {
                    "search": "releases/search",
                    "releases": "releases",
                    "release": "releases/{publisher}/{vertical_id}/{version}",
                    "publish": "releases/publish",
                },
            }
        }

    def publish_artifact(
        self,
        url: str,
        artifact: Path,
        *,
        metadata: Mapping[str, object],
        token: str,
        idempotency_key: str,
        max_artifact_bytes: int,
        max_response_bytes: int,
    ) -> object:
        assert token == "registry-secret"
        release = metadata["release"]
        self.published.append(
            {
                "url": url,
                "metadata": metadata,
                "idempotency_key": idempotency_key,
                "bytes": artifact.read_bytes(),
            }
        )
        return {
            "vertical_publication": {
                "protocol_version": PROTOCOL,
                "receipt": {
                    "receipt_id": "PUB-001",
                    "status": "published",
                    "coordinate": release["coordinate"],
                    "artifact_checksum": release["artifact"]["sha256"],
                    "visibility": release["visibility"],
                },
            }
        }


@pytest.mark.integration
def test_publication_requires_auth_records_redacted_failure_and_exact_receipt(
    tmp_path: Path,
) -> None:
    paths = VerticalUserPaths(tmp_path / "user-data", tmp_path / "user-cache")
    configuration = VerticalRegistryConfigurationService(paths=paths)
    configuration.add("wavekit", "https://registry.example.test", make_default=True)
    transport = _PublicationTransport()
    credentials = MemoryCredentialStore()
    client = VerticalRegistryClient(
        configuration=configuration,
        transport=transport,
        credentials=credentials,
    )
    cache = VerticalCacheService(paths=paths)
    catalog = VerticalCatalogService(tmp_path / "project", cache=cache)
    drafts = VerticalDraftService(
        tmp_path / "project",
        catalog=catalog,
        draft_root=paths.vertical_drafts_root,
        id_factory=lambda: "VDRAFT-1234567890ABCDEF",
    )
    lifecycle = VerticalDraftLifecycleService(
        tmp_path / "project",
        drafts=drafts,
        cache=cache,
        client=client,
    )
    draft_id, _packaged = _package(tmp_path, drafts, lifecycle)

    with pytest.raises(ValueError, match="P2P_REGISTRY_AUTH_REQUIRED"):
        lifecycle.publish(draft_id, registry="wavekit", idempotency_key="wavekit-op-1")
    failure = drafts.inspect(draft_id).evidence.last_publication_failure
    assert failure["code"] == "P2P_REGISTRY_AUTH_REQUIRED"
    assert "registry-secret" not in json.dumps(failure)

    credentials.set(
        "wavekit",
        RegistryCredential(access_token="registry-secret", expires_at=4_000_000_000),
    )
    published = lifecycle.publish(
        draft_id,
        registry="wavekit",
        idempotency_key="wavekit-op-1",
    )

    receipt = published.draft.evidence.publications[-1]
    assert receipt["receipt_id"] == "PUB-001"
    assert receipt["revision"] == published.draft.state.revision
    assert receipt["document_hash"] == published.draft.state.document_hash
    assert transport.published[0]["bytes"] == (tmp_path / "release.p2pv").read_bytes()
    assert transport.published[0]["metadata"]["lineage"]["previous_release"][
        "coordinate"
    ] == "binarya/software_project@2.0.0"
    assert {
        field: receipt[field]
        for field in ("registry", "receipt_id", "status", "coordinate", "visibility")
    } == _fixture("publication-v1.json")


@pytest.mark.cli
def test_draft_cli_create_and_inspect_use_versioned_json_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P2P_HOME", str(tmp_path / "p2p-home"))
    created = runner.invoke(
        app,
        [
            "vertical",
            "draft",
            "create",
            "--empty",
            "--root",
            str(tmp_path / "project"),
            "--format",
            "json",
        ],
    )
    assert created.exit_code == 0, created.stdout
    payload = json.loads(created.stdout)
    assert payload["operation"] == "vertical.draft.create"
    assert payload["data"]["draft"]["document"]["sections"] == []
    draft_id = payload["data"]["draft"]["draft_id"]

    inspected = runner.invoke(
        app,
        [
            "vertical",
            "draft",
            "inspect",
            draft_id,
            "--root",
            str(tmp_path / "project"),
            "--format",
            "json",
        ],
    )
    assert inspected.exit_code == 0, inspected.stdout
    inspected_payload = json.loads(inspected.stdout)
    assert inspected_payload["operation"] == "vertical.draft.inspect"
    assert inspected_payload["data"]["draft"]["revision"] == 1


@pytest.mark.service
def test_proposal_guard_runs_before_id_allocation_or_artifact_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("No target section")
    service = workspace._project_vertical_service()
    monkeypatch.setattr(service, "list_sections", lambda **_kwargs: [])
    proposals_root = tmp_path / ".p2p" / "proposals"
    before = tuple(proposals_root.iterdir())

    with pytest.raises(ValueError, match="P2P_VERTICAL_NO_TARGET_SECTION"):
        workspace.create_proposal("Must be blocked")

    assert tuple(proposals_root.iterdir()) == before


@pytest.mark.integration
def test_zero_section_artifact_cannot_be_installed(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path / "project")
    workspace.init_project("Zero section install")
    archive = tmp_path / "zero-sections.p2pv"
    archive.write_bytes(
        PortableVerticalPackageService.archive_bytes(
            {
                "manifest.yml": b"manifest:\n  schema_version: 2\n  publisher: test\n  id: empty\n  name: Empty\n  version: 1.0.0\n  license: MIT\n  dependencies: []\n",
                "vertical.yml": b"vertical:\n  schema_version: 2\n  id: empty\n  name: Empty\n  version: 1.0.0\n  description: Empty vertical\n",
                "rubrics.yml": b"rubrics: []\n",
            }
        )
    )
    before = tuple((tmp_path / "project" / ".p2p" / "verticals").rglob("*"))

    with pytest.raises(ValueError, match="P2P_VERTICAL_NO_SECTIONS"):
        workspace.preview_portable_vertical_install(
            archive,
            expected_checksum="0" * 64,
        )

    assert tuple((tmp_path / "project" / ".p2p" / "verticals").rglob("*")) == before


@pytest.mark.integration
def test_no_target_section_guard_is_shared_by_cli_and_mcp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    workspace = P2PWorkspace(root)
    workspace.init_project("Shared proposal guard")
    monkeypatch.setattr(ProjectVerticalService, "list_sections", lambda *_args, **_kwargs: [])

    cli = runner.invoke(
        app,
        ["proposal", "create", "CLI blocked", "--root", str(root)],
    )
    assert cli.exit_code != 0
    assert "P2P_VERTICAL_NO_TARGET_SECTION" in cli.stdout

    with pytest.raises(ValueError, match="P2P_VERTICAL_NO_TARGET_SECTION"):
        handle_proposal_tool(
            workspace,
            "p2p_proposal_create",
            {"title": "MCP blocked"},
        )


@pytest.mark.service
def test_wavekit_payload_projections_match_golden_contracts(tmp_path: Path) -> None:
    drafts, lifecycle, _cache = _services(tmp_path)
    empty = drafts.create_empty().draft
    create_projection = {
        "contract_version": empty.state.document["contract_version"],
        "draft_id": empty.state.draft_id,
        "origin": empty.state.origin.kind,
        "revision": empty.state.revision,
        "readiness": empty.assessment.readiness,
        "sections": empty.state.document["sections"],
    }
    inspect_projection = {
        "draft_contract": empty.state.to_dict()["contract_version"],
        "document_contract": empty.state.document["contract_version"],
        "evidence_contract": empty.evidence.to_dict()["contract_version"],
        "diagnostic_codes": sorted({item.code for item in empty.assessment.diagnostics}),
        "publishable": empty.assessment.publishable,
    }
    assert create_projection == _fixture("create-v1.json")
    assert inspect_projection == _fixture("inspect-v1.json")

    clone_document = _clone_document(tmp_path)
    updated = drafts.update(
        empty.state.draft_id,
        clone_document,
        expected_revision=1,
    ).draft
    update_projection = {
        "revision": updated.state.revision,
        "description": updated.state.document["description"],
        "materialization": updated.evidence.materialization,
        "validation": updated.evidence.validation,
        "package": updated.evidence.package,
        "local_adds": list(updated.evidence.local_adds),
        "publications": list(updated.evidence.publications),
    }
    assert update_projection == _fixture("update-v1.json")

    lifecycle.materialize(updated.state.draft_id, tmp_path / "golden-materialized")
    validated = lifecycle.validate(updated.state.draft_id).draft.evidence.validation
    assert {
        "coordinate": validated["coordinate"],
        "valid": validated["valid"],
        "readiness": validated["readiness"],
        "diagnostics": validated["diagnostics"],
    } == _fixture("validation-v1.json")


def _clone_document(tmp_path: Path) -> dict[str, object]:
    service = VerticalDraftService(
        tmp_path / "project",
        draft_root=tmp_path / "clone-drafts",
        id_factory=lambda: "VDRAFT-FEDCBA0987654321",
    )
    document = service.create_from(
        "binarya/software_project@2.0.0",
        version="2.0.1",
        previous_release="binarya/software_project@2.0.0",
    ).draft.state.document
    document["description"] = "A revised WaveKit software vertical."
    return document


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

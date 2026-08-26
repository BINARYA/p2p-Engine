from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.authority import (
    AuthorityBasis,
    AuthorityClaim,
    AuthorityContext,
    AuthorityIdentity,
    AuthorityIdentityKind,
    AuthorityMode,
    AuthorityProjectBinding,
)
from p2p_engine.core.project_structure_export import (
    PROJECT_STRUCTURE_EXPORT_CAPABILITY,
    PROJECT_STRUCTURE_EXPORT_OPERATION,
    PROJECT_STRUCTURE_EXPORT_RESULT_CONTRACT,
)
from p2p_engine.mcp.registry import TOOL_NAMES
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.project_structure_export import _draft_id_for_operation
from p2p_engine.services.vertical_drafts import VerticalDraftService
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data


runner = CliRunner()


def _workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    starter: str = "generic",
    vertical_id: str = "",
) -> P2PWorkspace:
    monkeypatch.setenv("P2P_HOME", str(tmp_path / "p2p-home"))
    root = tmp_path / "project"
    workspace = P2PWorkspace(root)
    kwargs: dict[str, object] = {"owner": "owner"}
    if vertical_id:
        kwargs["vertical_id"] = vertical_id
    else:
        kwargs["starter_id"] = starter
    workspace.init_project("Structure Export", **kwargs)
    return workspace


def _domain() -> dict[str, object]:
    return {
        "key": "software",
        "name": "Software",
        "source": "local",
        "external_ref": None,
    }


def _preview(workspace: P2PWorkspace, *, lineage_mode: str = "independent"):
    return workspace.preview_project_structure_export(
        publisher="acme",
        vertical_id="exported_structure",
        version="1.0.0",
        name="Exported Structure",
        license_id="MIT",
        primary_domain=_domain(),
        domain_tags=["software", "delivery"],
        lineage_mode=lineage_mode,
        actor_id="owner",
        executor_id="owner",
    )


def _apply(
    workspace: P2PWorkspace,
    preview,
    tmp_path: Path,
    *,
    operation_key: str = "structure-export-op-1",
):
    return workspace.apply_project_structure_export(
        publisher="acme",
        vertical_id="exported_structure",
        version="1.0.0",
        name="Exported Structure",
        license_id="MIT",
        primary_domain=_domain(),
        domain_tags=["software", "delivery"],
        lineage_mode=preview.lineage["mode"],
        expected_structure_revision=preview.source.revision,
        expected_structure_checksum=preview.source.checksum,
        preview_token=preview.preview.preview_token,
        operation_key=operation_key,
        materialization_target=tmp_path / "build" / "exported-structure",
        package_output=tmp_path / "dist" / "exported-structure.p2pv",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _external_context(capability: str = PROJECT_STRUCTURE_EXPORT_CAPABILITY) -> AuthorityContext:
    return AuthorityContext(
        mode=AuthorityMode.external_attestation,
        project_authority=AuthorityProjectBinding(
            authority_id="hosted-authority-01",
            generation=1,
            provider_id="hosted-provider",
            provider_policy_version="project-capabilities-v1",
        ),
        subject=AuthorityIdentity("hosted-owner-01", AuthorityIdentityKind.user),
        executor=AuthorityIdentity("hosted-client-01", AuthorityIdentityKind.client),
        authorization_decision_id="export-authz-01",
        authorized_at="2026-08-26T12:00:00Z",
        claims=(
            AuthorityClaim(
                capability=capability,
                basis=AuthorityBasis.root_authority,
                authority_generation=1,
            ),
        ),
    )


@pytest.mark.service
@pytest.mark.smoke
def test_active_structure_exports_offline_without_changing_source_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    structure_before = workspace.project_structure(include_retired=True).to_storage_dict()
    readiness_before = workspace.project_readiness_result().to_dict()

    preview = _preview(workspace)
    result = _apply(workspace, preview, tmp_path)

    assert preview.apply_allowed is True
    assert result.status == "applied"
    assert result.to_dict()["contract"] == PROJECT_STRUCTURE_EXPORT_RESULT_CONTRACT
    assert result.to_dict()["remote_publication"] is False
    assert result.to_dict()["publisher_ownership_granted"] is False
    assert "local_paths" not in result.to_dict()
    assert workspace.project_structure(include_retired=True).to_storage_dict() == structure_before
    assert workspace.project_readiness_result().to_dict() == readiness_before
    assert result.authority.claims[0].capability == PROJECT_STRUCTURE_EXPORT_CAPABILITY
    assert (workspace.root / result.marker_path).is_file()
    assert (tmp_path / "dist" / "exported-structure.p2pv").is_file()
    inspection = workspace.inspect_portable_vertical(
        tmp_path / "dist" / "exported-structure.p2pv",
        view="declared",
    )
    assert inspection.valid is True
    assert inspection.pack.coordinate == "acme/exported_structure@1.0.0"
    assert inspection.semantic_checksum == result.semantic_checksum


@pytest.mark.service
def test_independent_export_preserves_attribution_without_social_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(
        tmp_path,
        monkeypatch,
        vertical_id="binarya/software_project@2.0.0",
    )

    preview = _preview(workspace, lineage_mode="independent")

    assert preview.lineage["mode"] == "independent"
    assert preview.draft_document["lineage"]["forked_from"] is None
    attribution = preview.draft_document["source_attribution"]
    assert attribution["project_structure_origin"]["kind"] == "vertical_release"
    assert attribution["legal_attribution_preserved"] is True


@pytest.mark.service
def test_derived_export_records_exact_parent_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(
        tmp_path,
        monkeypatch,
        vertical_id="binarya/software_project@2.0.0",
    )
    origin = workspace.project_structure(include_retired=True).origin

    preview = _preview(workspace, lineage_mode="derived")

    assert preview.apply_allowed is True
    assert preview.lineage["forked_from"] == {
        "coordinate": origin.identity,
        "semantic_checksum": origin.checksum,
    }
    assert preview.draft_document["lineage"]["forked_from"] == preview.lineage["forked_from"]


@pytest.mark.service
def test_empty_structure_and_stale_apply_fail_without_partial_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty = _workspace(tmp_path / "empty", monkeypatch, starter="empty")
    empty_preview = _preview(empty)
    assert empty_preview.apply_allowed is False
    assert any("P2P_STRUCTURE_EXPORT_EMPTY" in item for item in empty_preview.blockers)

    workspace = _workspace(tmp_path / "stale", monkeypatch, starter="empty")
    workspace.change_project_structure(
        operation="add_section",
        operation_key="stale-add-first",
        expected_revision=1,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        request={"title": "Alpha", "description": "Alpha section.", "required": True},
    )
    preview = _preview(workspace)
    workspace.change_project_structure(
        operation="add_section",
        operation_key="stale-add-second",
        expected_revision=2,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        request={"title": "Beta", "description": "Beta section.", "required": True},
    )

    with pytest.raises(ValueError, match="P2P_STRUCTURE_EXPORT_STALE_SOURCE"):
        _apply(workspace, preview, tmp_path / "stale")

    assert not (tmp_path / "stale" / "dist" / "exported-structure.p2pv").exists()
    drafts_root = tmp_path / "stale" / "p2p-home" / "vertical-drafts"
    assert not drafts_root.exists()


@pytest.mark.service
def test_export_rejects_existing_deterministic_draft_version_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    preview = _preview(workspace)
    operation_key = "draft-version-collision-key"
    draft_id = _draft_id_for_operation(operation_key)
    drafts = VerticalDraftService(workspace.root, id_factory=lambda: draft_id)
    drafts.create_empty(
        publisher="acme",
        vertical_id="exported_structure",
        version="9.9.9",
        name="Conflicting Draft",
        license_id="MIT",
    )

    with pytest.raises(ValueError, match="P2P_STRUCTURE_EXPORT_DRAFT_CONFLICT"):
        _apply(workspace, preview, tmp_path, operation_key=operation_key)

    assert not (tmp_path / "dist" / "exported-structure.p2pv").exists()


@pytest.mark.service
def test_export_replay_is_idempotent_and_does_not_duplicate_drafts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    preview = _preview(workspace)

    first = _apply(workspace, preview, tmp_path, operation_key="export-replay-key")
    second = _apply(workspace, preview, tmp_path, operation_key="export-replay-key")

    assert second.status == "already_applied"
    assert second.draft_id == first.draft_id
    assert second.artifact_checksum == first.artifact_checksum
    drafts = list((tmp_path / "p2p-home" / "vertical-drafts").iterdir())
    assert [path.name for path in drafts] == [first.draft_id]


@pytest.mark.service
def test_export_receipt_binds_external_authority_without_publisher_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("P2P_HOME", str(tmp_path / "p2p-home"))
    workspace = P2PWorkspace(tmp_path / "project")
    workspace.init_project(
        "Hosted Structure Export",
        starter_id="generic",
        authority_context=_external_context("project.initialize"),
    )
    context = _external_context()
    preview = workspace.preview_project_structure_export(
        publisher="acme",
        vertical_id="hosted_export",
        version="1.0.0",
        name="Hosted Export",
        license_id="MIT",
        primary_domain=_domain(),
        lineage_mode="independent",
        actor_id=context.subject.identity_id,
        executor_id=context.executor.identity_id,
    )

    result = workspace.apply_project_structure_export(
        publisher="acme",
        vertical_id="hosted_export",
        version="1.0.0",
        name="Hosted Export",
        license_id="MIT",
        primary_domain=_domain(),
        lineage_mode="independent",
        expected_structure_revision=preview.source.revision,
        expected_structure_checksum=preview.source.checksum,
        preview_token=preview.preview.preview_token,
        operation_key="hosted-export-key",
        materialization_target=tmp_path / "build" / "hosted-export",
        package_output=tmp_path / "dist" / "hosted-export.p2pv",
        confirm=True,
        actor_id=context.subject.identity_id,
        executor_id=context.executor.identity_id,
        executor_kind=context.executor.kind.value,
        authority_context=context,
        channel="cli",
    )

    payload = result.to_dict()
    assert payload["receipt"]["capability"] == PROJECT_STRUCTURE_EXPORT_CAPABILITY
    assert result.authority.authority_context_sha256 == context.digest_sha256
    assert result.authority.claims[0].capability == PROJECT_STRUCTURE_EXPORT_CAPABILITY
    assert payload["remote_publication"] is False
    assert payload["publisher_ownership_granted"] is False


@pytest.mark.mcp
def test_mcp_export_eligibility_preview_are_read_only_and_apply_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    before = _snapshot(workspace.root)

    eligibility = call_tool(
        "p2p_project_structure_export_eligibility",
        {"root": str(workspace.root)},
    )
    preview = call_tool(
        "p2p_project_structure_export_preview",
        {
            "root": str(workspace.root),
            "publisher": "acme",
            "vertical_id": "mcp_export",
            "version": "1.0.0",
            "name": "MCP Export",
            "license": "MIT",
            "primary_domain": _domain(),
            "lineage_mode": "independent",
        },
    )

    assert eligibility["mutation_performed"] is False
    assert preview["mutation_performed"] is False
    assert _snapshot(workspace.root) == before
    assert "p2p_project_structure_export_apply" not in TOOL_NAMES
    assert "p2p_project_structure_export_package" not in TOOL_NAMES


@pytest.mark.cli
def test_cli_export_preview_and_apply_use_versioned_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path, monkeypatch)

    preview_result = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "export",
            "preview",
            "--publisher",
            "acme",
            "--id",
            "cli_export",
            "--version",
            "1.0.0",
            "--name",
            "CLI Export",
            "--license",
            "MIT",
            "--primary-domain-key",
            "software",
            "--primary-domain-name",
            "Software",
            "--lineage-mode",
            "independent",
            "--root",
            str(workspace.root),
            "--format",
            "json",
        ],
    )
    assert preview_result.exit_code == 0, preview_result.stdout
    preview = cli_data(preview_result, operation="project.vertical.export.preview")[
        "project_structure_export_preview"
    ]

    apply_result = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "export",
            "apply",
            "--target",
            str(tmp_path / "build" / "cli-export"),
            "--output",
            str(tmp_path / "dist" / "cli-export.p2pv"),
            "--publisher",
            "acme",
            "--id",
            "cli_export",
            "--version",
            "1.0.0",
            "--name",
            "CLI Export",
            "--license",
            "MIT",
            "--primary-domain-key",
            "software",
            "--primary-domain-name",
            "Software",
            "--lineage-mode",
            "independent",
            "--expected-structure-revision",
            str(preview["source"]["revision"]),
            "--expected-structure-checksum",
            preview["source"]["checksum"],
            "--token",
            preview["preview"]["preview_token"],
            "--idempotency-key",
            "cli-export-key",
            "--confirm",
            "--root",
            str(workspace.root),
            "--format",
            "json",
        ],
    )
    assert apply_result.exit_code == 0, apply_result.stdout
    payload = cli_data(apply_result, operation="project.vertical.export.apply")[
        "project_structure_export"
    ]
    assert payload["operation"] == PROJECT_STRUCTURE_EXPORT_OPERATION
    assert payload["package"]["coordinate"] == "acme/cli_export@1.0.0"
    assert "local_paths" not in payload

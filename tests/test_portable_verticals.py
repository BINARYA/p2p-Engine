from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.services.vertical_lifecycle import VerticalLifecycleService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace


runner = CliRunner()


def _portable_pack(
    workspace: P2PWorkspace,
    root: Path,
    *,
    vertical_id: str,
    version: str,
    field_id: str = "summary",
) -> tuple[Path, str, str]:
    source = root / f"{vertical_id}-{version}"
    inspection = workspace.scaffold_portable_vertical(
        source,
        publisher="test",
        vertical_id=vertical_id,
        version=version,
        name=vertical_id.replace("_", " ").title(),
        license_id="MIT",
    )
    if field_id != "summary":
        section_path = source / "sections" / "custom_overview.yml"
        payload = yaml.safe_load(section_path.read_text(encoding="utf-8"))
        payload["section"]["fields"][0]["id"] = field_id
        section_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    archive = root / f"{vertical_id}-{version}.p2pv"
    packaged = workspace.package_portable_vertical(source, output=archive)
    return archive, packaged.artifact_checksum, inspection.pack.coordinate


@pytest.mark.service
def test_portable_package_is_deterministic_and_installs_side_by_side(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    first, checksum, coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="portable_demo",
        version="1.0.0",
    )
    second = tmp_path / "portable-demo-copy.p2pv"
    repackaged = authoring.package_portable_vertical(
        tmp_path / "portable_demo-1.0.0",
        output=second,
    )

    assert first.read_bytes() == second.read_bytes()
    assert checksum == repackaged.artifact_checksum

    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project("Portable project")
    preview = project.preview_portable_vertical_install(
        first,
        expected_checksum=checksum,
        actor="owner",
    )

    assert preview.apply_allowed is True
    assert not (project_root / preview.impact["install_prefix"]).exists()
    applied = project.apply_portable_vertical_install(
        first,
        expected_checksum=checksum,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
    )

    assert applied.mutation.status == "applied"
    assert project.show_project_vertical(coordinate).coordinate == coordinate

    v2, checksum_v2, coordinate_v2 = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="portable_demo",
        version="2.0.0",
    )
    preview_v2 = project.preview_portable_vertical_install(
        v2,
        expected_checksum=checksum_v2,
        actor="owner",
    )
    project.apply_portable_vertical_install(
        v2,
        expected_checksum=checksum_v2,
        preview_token=preview_v2.preview.preview_token,
        confirmed=True,
        actor="owner",
    )

    assert project.show_project_vertical(coordinate).version == "1.0.0"
    assert project.show_project_vertical(coordinate_v2).version == "2.0.0"
    listed = {item.coordinate for item in project.project_verticals()}
    assert {coordinate, coordinate_v2} <= listed


@pytest.mark.service
def test_portable_archive_rejects_path_traversal_without_project_writes(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.p2pv"
    with zipfile.ZipFile(archive, "w") as value:
        value.writestr("../outside.yml", "unsafe: true\n")

    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    result = project.validate_portable_vertical(archive)

    assert result.valid is False
    assert result.issues[0].code == "P2P_VERTICAL_UNSAFE_ARTIFACT"
    assert not project_root.exists()
    assert not (tmp_path / "outside.yml").exists()


@pytest.mark.service
def test_portable_install_rolls_back_a_partial_write(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, _ = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="rollback_demo",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project("Rollback project")

    def fail_after_first_replace(stage: str, target: str) -> None:
        if stage == "after_replace":
            raise RuntimeError(f"injected failure after {target}")

    lifecycle = VerticalLifecycleService(
        root=project_root,
        p2p_dir=project_root / ".p2p",
        vertical_service=project._project_vertical_service(),
        package_service=project._portable_vertical_package_service(),
        atomic_writer=AtomicMutationWriter(
            root=project_root,
            p2p_dir=project_root / ".p2p",
            failure_injector=fail_after_first_replace,
        ),
    )
    preview = lifecycle.install_preview(archive, expected_checksum=checksum, actor="owner")

    with pytest.raises(ValueError, match="P2P_VERTICAL_APPLY_FAILED"):
        lifecycle.install_apply(
            archive,
            expected_checksum=checksum,
            preview_token=preview.preview.preview_token,
            confirmed=True,
            actor="owner",
        )

    install_root = project_root / preview.impact["install_prefix"]
    assert not install_root.exists() or not any(path.is_file() for path in install_root.rglob("*"))


@pytest.mark.service
def test_adoption_rejects_stale_preview_and_requires_confirmation(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="adopt_demo",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project("Adopt project")
    install = project.preview_portable_vertical_install(archive, expected_checksum=checksum, actor="owner")
    project.apply_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        preview_token=install.preview.preview_token,
        confirmed=True,
        actor="owner",
    )
    adoption = project.preview_project_vertical_adoption(coordinate, actor="owner")

    with pytest.raises(ValueError, match="P2P_VERTICAL_CONFIRMATION_REQUIRED"):
        project.apply_project_vertical_adoption(
            coordinate,
            preview_token=adoption.preview.preview_token,
            confirmed=False,
            actor="owner",
        )

    active_path = project_root / ".p2p" / "project" / "vertical.yml"
    active_path.write_text(
        "project_vertical:\n"
        "  schema_version: 1\n"
        "  active_vertical_id: base_project\n"
        "  active_source: internal\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="P2P_VERTICAL_STALE_PREVIEW"):
        project.apply_project_vertical_adoption(
            coordinate,
            preview_token=adoption.preview.preview_token,
            confirmed=True,
            actor="owner",
        )


@pytest.mark.service
def test_migration_preserves_exact_mapping_and_materializes_unmapped_orphan(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    source_archive, source_checksum, source_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="migration_source",
        version="1.0.0",
    )
    target_archive, target_checksum, target_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="migration_target",
        version="2.0.0",
        field_id="renamed_summary",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project("Migration project")
    for archive, checksum in (
        (source_archive, source_checksum),
        (target_archive, target_checksum),
    ):
        install = project.preview_portable_vertical_install(archive, expected_checksum=checksum, actor="owner")
        project.apply_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            preview_token=install.preview.preview_token,
            confirmed=True,
            actor="owner",
        )
    adoption = project.preview_project_vertical_adoption(source_coordinate, actor="owner")
    project.apply_project_vertical_adoption(
        source_coordinate,
        preview_token=adoption.preview.preview_token,
        confirmed=True,
        actor="owner",
    )
    patch = tmp_path / "definition-patch.yml"
    patch.write_text(
        "project_definition_patch:\n"
        "  schema_version: 1\n"
        "  actor: owner\n"
        "  operations:\n"
        "    - op: set_field\n"
        "      section_id: custom_overview\n"
        "      field_id: summary\n"
        "      value: preserved evidence\n"
        "      source: owner\n",
        encoding="utf-8",
    )
    project.update_project_definition(patch)

    mapped = project.preview_project_vertical_migration(
        target_coordinate,
        actor="owner",
        mapping={
            "field_mapping": {
                "custom_overview.summary": "custom_overview.renamed_summary",
            }
        },
    )
    assert mapped.impact["orphaned_values"] == 0
    assert mapped.impact["preserved_fields"] == [
        {
            "from": "custom_overview.summary",
            "to": "custom_overview.renamed_summary",
        }
    ]

    orphaned = project.preview_project_vertical_migration(target_coordinate, actor="owner")
    assert orphaned.impact["orphaned_values"] == 1
    project.apply_project_vertical_migration(
        target_coordinate,
        preview_token=orphaned.preview.preview_token,
        confirmed=True,
        actor="owner",
    )
    state = project.project_definition_view().state

    assert state is not None
    assert state.vertical_id == "migration_target"
    assert len(state.orphans) == 1
    assert state.orphans[0].value == "preserved evidence"
    assert state.orphans[0].source_field_id == "summary"


@pytest.mark.service
def test_init_preflights_portable_checksum_before_creating_workspace(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="init_demo",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)

    with pytest.raises(ValueError, match="P2P_VERTICAL_CHECKSUM_MISMATCH"):
        project.init_project_with_summary(
            "Invalid init",
            vertical_pack=archive,
            expected_checksum="0" * 64,
        )

    assert not (project_root / ".p2p").exists()

    project.init_project_with_summary(
        "Valid init",
        vertical_pack=archive,
        expected_checksum=checksum,
        owner="owner",
    )
    lock = project.project_vertical_lock_status()

    assert project.active_project_vertical().vertical_id == "init_demo"
    assert lock.status == "valid"
    assert lock.locked is not None
    assert lock.locked.coordinate == coordinate
    assert lock.locked.artifact_checksum == checksum


@pytest.mark.cli
def test_portable_cli_uses_stable_json_envelope(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["project", "vertical", "schema", "--root", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["operation"] == "vertical_schema"
    assert payload["error"] is None
    assert payload["data"]["schema_version"] == 2


@pytest.mark.cli
def test_portable_cli_install_and_adopt_preview_apply_contract(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="cli_demo",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    P2PWorkspace(project_root).init_project("CLI project")

    bad = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "install",
            "preview",
            str(archive),
            "--expected-checksum",
            "0" * 64,
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )
    assert bad.exit_code == 1
    assert json.loads(bad.stdout)["error"]["code"] == "P2P_VERTICAL_CHECKSUM_MISMATCH"

    install_preview = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "install",
            "preview",
            str(archive),
            "--expected-checksum",
            checksum,
            "--actor",
            "owner",
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )
    install_payload = json.loads(install_preview.stdout)
    install_token = install_payload["data"]["preview"]["preview_token"]
    installed = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "install",
            "apply",
            str(archive),
            "--expected-checksum",
            checksum,
            "--token",
            install_token,
            "--confirm",
            "--actor",
            "owner",
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )
    assert installed.exit_code == 0
    assert json.loads(installed.stdout)["data"]["mutation"]["status"] == "applied"

    adopt_preview = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "adopt",
            "preview",
            coordinate,
            "--actor",
            "owner",
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )
    adopt_payload = json.loads(adopt_preview.stdout)
    adopt_token = adopt_payload["data"]["preview"]["preview_token"]
    adopted = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "adopt",
            "apply",
            coordinate,
            "--token",
            adopt_token,
            "--confirm",
            "--actor",
            "owner",
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )

    assert adopted.exit_code == 0
    adopted_payload = json.loads(adopted.stdout)
    assert adopted_payload["ok"] is True
    assert adopted_payload["operation"] == "vertical_adopt_apply"

    patch = tmp_path / "cli-definition-patch.yml"
    patch.write_text(
        "project_definition_patch:\n"
        "  schema_version: 1\n"
        "  actor: owner\n"
        "  operations:\n"
        "    - op: set_field\n"
        "      section_id: custom_overview\n"
        "      field_id: summary\n"
        "      value: CLI evidence\n"
        "      source: owner\n",
        encoding="utf-8",
    )
    project = P2PWorkspace(project_root)
    project.update_project_definition(patch)
    target_archive, target_checksum, target_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="cli_target",
        version="2.0.0",
        field_id="renamed_summary",
    )
    target_install = project.preview_portable_vertical_install(
        target_archive,
        expected_checksum=target_checksum,
        actor="owner",
    )
    project.apply_portable_vertical_install(
        target_archive,
        expected_checksum=target_checksum,
        preview_token=target_install.preview.preview_token,
        confirmed=True,
        actor="owner",
    )
    mapping = tmp_path / "cli-mapping.yml"
    mapping.write_text(
        "vertical_migration:\n"
        "  field_mapping:\n"
        "    custom_overview.summary: custom_overview.renamed_summary\n",
        encoding="utf-8",
    )
    migrate_preview = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "migrate",
            "preview",
            target_coordinate,
            "--mapping",
            str(mapping),
            "--actor",
            "owner",
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )
    migrate_payload = json.loads(migrate_preview.stdout)
    migrate_token = migrate_payload["data"]["preview"]["preview_token"]
    migrated = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "migrate",
            "apply",
            target_coordinate,
            "--mapping",
            str(mapping),
            "--token",
            migrate_token,
            "--confirm",
            "--actor",
            "owner",
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )

    assert migrated.exit_code == 0
    migrated_payload = json.loads(migrated.stdout)
    assert migrated_payload["ok"] is True
    assert migrated_payload["operation"] == "vertical_migrate_apply"

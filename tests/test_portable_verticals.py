from __future__ import annotations

from pathlib import Path
import shutil
import zipfile

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.services.vertical_lifecycle import VerticalLifecycleService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data, cli_envelope, cli_error


runner = CliRunner()


def _portable_pack(
    workspace: P2PWorkspace,
    root: Path,
    *,
    vertical_id: str,
    version: str,
    field_id: str = "summary",
    section_id: str = "custom_overview",
    question_id: str = "custom_overview_question",
    rubric_id: str = "custom_overview_coverage",
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
    section_path = source / "sections" / "custom_overview.yml"
    section_payload = yaml.safe_load(section_path.read_text(encoding="utf-8"))
    section_payload["section"]["id"] = section_id
    section_payload["section"]["fields"][0]["id"] = field_id
    target_section_path = source / "sections" / f"{section_id}.yml"
    if target_section_path != section_path:
        section_path.rename(target_section_path)
    target_section_path.write_text(
        yaml.safe_dump(section_payload, sort_keys=False),
        encoding="utf-8",
    )
    vertical_path = source / "vertical.yml"
    vertical_payload = yaml.safe_load(vertical_path.read_text(encoding="utf-8"))
    vertical_payload["vertical"]["questions"][0]["id"] = question_id
    vertical_payload["vertical"]["questions"][0]["section_id"] = section_id
    vertical_payload["vertical"]["artifacts"][0]["section_ids"] = [section_id]
    vertical_path.write_text(yaml.safe_dump(vertical_payload, sort_keys=False), encoding="utf-8")
    rubrics_path = source / "rubrics.yml"
    rubrics_payload = yaml.safe_load(rubrics_path.read_text(encoding="utf-8"))
    rubrics_payload["rubrics"][0]["id"] = rubric_id
    rubrics_payload["rubrics"][0]["section_id"] = section_id
    rubrics_path.write_text(yaml.safe_dump(rubrics_payload, sort_keys=False), encoding="utf-8")
    archive = root / f"{vertical_id}-{version}.p2pv"
    packaged = workspace.package_portable_vertical(source, output=archive)
    return archive, packaged.artifact_checksum, inspection.pack.coordinate


def _workspace_file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _transition_plan(
    preview,
    *,
    targets: dict[str, str] | None = None,
) -> dict[str, object]:
    target_refs = targets or {}
    decisions: list[dict[str, object]] = []
    for required in preview.impact.required_decisions.items:
        target_ref = target_refs.get(required.source.ref)
        decision: dict[str, object] = {
            "id": required.decision_id,
            "action": "map" if target_ref else "preserve_as_orphan",
            "source": required.source.to_dict(),
        }
        if target_ref:
            decision["target"] = {
                "kind": required.source.kind.value,
                "ref": target_ref,
            }
        decisions.append(decision)
    return {
        "vertical_transition_plan": {
            "schema_version": 1,
            "contract_version": "p2p-vertical-transition-plan/v1",
            "analysis_fingerprint_sha256": preview.impact.analysis_fingerprint_sha256,
            "decisions": decisions,
        }
    }


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
    project.init_project("Portable project", starter_id="empty")
    preview = project.preview_portable_vertical_install(
        first,
        expected_checksum=checksum,
        actor="owner",
    )

    assert preview.apply_allowed is True
    assert not (
        project_root / ".p2p/project/verticals/_portable/test/portable_demo/1.0.0"
    ).exists()
    applied = project.apply_portable_vertical_install(
        first,
        expected_checksum=checksum,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"install:{checksum}",
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
        idempotency_key=f"install:{checksum_v2}",
    )

    assert project.show_project_vertical(coordinate).version == "1.0.0"
    assert project.show_project_vertical(coordinate_v2).version == "2.0.0"
    listed = {item.coordinate for item in project.project_verticals()}
    assert {coordinate, coordinate_v2} <= listed


@pytest.mark.service
@pytest.mark.cli
def test_install_receipt_supports_exact_replay_status_redaction_and_drift_detection(
    tmp_path: Path,
) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, _coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="receipt-install",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project("Receipt install", owner="owner", starter_id="empty")
    preview = project.preview_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        actor="owner",
    )
    key = "wavekit-operation-3f8cb243-f831-47d4-a61e-20b35da3b526"

    applied = project.apply_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=key,
    )
    after_apply = _workspace_file_snapshot(project_root)

    replayed = project.apply_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=key,
    )
    repeated = project.apply_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=key,
    )

    assert applied.mutation.status == "applied"
    assert applied.postconditions == {
        "installed_coordinate": preview.coordinate,
        "installed_semantic_checksum": preview.impact.target.semantic_checksum,
        "installed_artifact_checksum": preview.impact.target.artifact_checksum,
    }
    assert replayed.mutation.status == repeated.mutation.status == "already_applied"
    assert replayed.postconditions == applied.postconditions
    assert replayed.mutation.changed_paths == ()
    assert _workspace_file_snapshot(project_root) == after_apply

    receipts = list(
        (project_root / ".p2p" / ".internal" / "mutation-receipts").glob("*.yml")
    )
    assert len(receipts) == 1
    assert key not in receipts[0].as_posix()
    assert key.encode("utf-8") not in receipts[0].read_bytes()

    status = project.mutation_status(idempotency_key=key)
    assert status.state == "applied"
    assert status.operation == "install"
    assert status.postconditions_match is True
    assert status.result["semantic_postconditions"] == applied.postconditions
    assert key not in str(status.to_dict())

    cli_status = runner.invoke(
        app,
        [
            "mutation",
            "status",
            "--idempotency-key",
            key,
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )
    assert cli_status.exit_code == 0
    assert cli_data(cli_status)["state"] == "applied"
    assert key not in cli_status.stdout

    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        project.apply_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            preview_token=preview.preview.preview_token,
            confirmed=True,
            actor="other-owner",
            idempotency_key=key,
        )
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        project.apply_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            preview_token="different-preview-token",
            confirmed=True,
            actor="owner",
            idempotency_key=key,
        )

    assert "changed_paths" not in status.result
    drift_path = (
        project_root
        / ".p2p/project/verticals/_portable/test/receipt-install/1.0.0/manifest.yml"
    )
    drift_path.write_bytes(drift_path.read_bytes() + b"\n")
    assert project.mutation_status(idempotency_key=key).state == "postcondition_drift"
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_POSTCONDITION_DRIFT"):
        project.apply_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            preview_token=preview.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key=key,
        )


@pytest.mark.service
def test_adopt_receipt_replays_before_current_state_is_recomputed(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="receipt-adopt",
        version="1.0.0",
    )
    project = P2PWorkspace(tmp_path / "project")
    project.init_project("Receipt adoption", owner="owner", starter_id="empty")
    install = project.preview_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        actor="owner",
    )
    project.apply_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        preview_token=install.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"install:{checksum}",
    )
    preview = project.preview_project_vertical_adoption(coordinate, actor="owner")
    key = "wavekit-adopt-operation"
    applied = project.apply_project_vertical_adoption(
        coordinate,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=key,
    )
    after_apply = _workspace_file_snapshot(project.root)

    replayed = project.apply_project_vertical_adoption(
        coordinate,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=key,
    )

    assert applied.mutation.status == "applied"
    assert replayed.mutation.status == "already_applied"
    assert _workspace_file_snapshot(project.root) == after_apply
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        project.apply_project_vertical_adoption(
            coordinate,
            preview_token=preview.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key=key,
            profile="different-profile",
        )
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        project.apply_project_vertical_adoption(
            "test/different-coordinate@1.0.0",
            preview_token=preview.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key=key,
        )


@pytest.mark.service
def test_migrate_receipt_replays_exact_mapping_and_rejects_changed_mapping(
    tmp_path: Path,
) -> None:
    authoring = P2PWorkspace(tmp_path)
    source_archive, source_checksum, source_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="receipt-migrate-source",
        version="1.0.0",
    )
    target_archive, target_checksum, target_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="receipt-migrate-target",
        version="2.0.0",
        field_id="renamed_summary",
    )
    project = P2PWorkspace(tmp_path / "project")
    project.init_project("Receipt migration", owner="owner", starter_id="empty")
    for archive, checksum in (
        (source_archive, source_checksum),
        (target_archive, target_checksum),
    ):
        install = project.preview_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            actor="owner",
        )
        project.apply_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            preview_token=install.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key=f"install:{checksum}",
        )
    adoption = project.preview_project_vertical_adoption(source_coordinate, actor="owner")
    project.apply_project_vertical_adoption(
        source_coordinate,
        preview_token=adoption.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"adopt:{source_coordinate}",
    )
    patch = tmp_path / "receipt-migration-patch.yml"
    patch.write_text(
        "project_definition_patch:\n"
        "  schema_version: 1\n"
        "  actor: owner\n"
        "  operations:\n"
        "    - op: set_field\n"
        "      section_id: custom_overview\n"
        "      field_id: summary\n"
        "      value: durable evidence\n"
        "      source: owner\n",
        encoding="utf-8",
    )
    project.update_project_definition(patch)
    analysis = project.preview_project_vertical_migration(
        target_coordinate,
        actor="owner",
    )
    mapping = _transition_plan(
        analysis,
        targets={
            "definition_field:custom_overview.summary": (
                "definition_field:custom_overview.renamed_summary"
            ),
        },
    )
    preview = project.preview_project_vertical_migration(
        target_coordinate,
        actor="owner",
        mapping=mapping,
    )
    key = "wavekit-migrate-operation"
    applied = project.apply_project_vertical_migration(
        target_coordinate,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=key,
        mapping=mapping,
    )
    after_apply = _workspace_file_snapshot(project.root)

    replayed = project.apply_project_vertical_migration(
        target_coordinate,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=key,
        mapping=mapping,
    )

    assert applied.mutation.status == "applied"
    assert replayed.mutation.status == "already_applied"
    assert _workspace_file_snapshot(project.root) == after_apply
    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        project.apply_project_vertical_migration(
            target_coordinate,
            preview_token=preview.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key=key,
            mapping={},
        )


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
    project.init_project("Rollback project", starter_id="empty")

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
            idempotency_key=f"failure-install:{checksum}",
        )

    install_root = project_root / ".p2p/project/verticals/_portable/test/rollback_demo/1.0.0"
    assert not install_root.exists() or not any(path.is_file() for path in install_root.rglob("*"))
    assert project.mutation_status(idempotency_key=f"failure-install:{checksum}").state == "not_found"


@pytest.mark.service
def test_adopt_and_migrate_receipts_roll_back_with_domain_state_on_write_failure(
    tmp_path: Path,
) -> None:
    authoring = P2PWorkspace(tmp_path)
    source_archive, source_checksum, source_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="failure-source",
        version="1.0.0",
    )
    target_archive, target_checksum, target_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="failure-target",
        version="2.0.0",
        field_id="renamed_summary",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project("Receipt failure rollback", owner="owner", starter_id="empty")
    for archive, checksum in (
        (source_archive, source_checksum),
        (target_archive, target_checksum),
    ):
        install = project.preview_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            actor="owner",
        )
        project.apply_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            preview_token=install.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key=f"install:{checksum}",
        )

    def failing_writer() -> AtomicMutationWriter:
        replacements = 0

        def fail_after_domain_write(stage: str, _target: str) -> None:
            nonlocal replacements
            if stage == "after_replace":
                replacements += 1
                if replacements == 2:
                    raise RuntimeError("injected lifecycle failure")

        return AtomicMutationWriter(
            root=project_root,
            p2p_dir=project_root / ".p2p",
            failure_injector=fail_after_domain_write,
        )

    lifecycle = project._vertical_lifecycle_service()
    adoption = project.preview_project_vertical_adoption(source_coordinate, actor="owner")
    before_adopt = _workspace_file_snapshot(project_root)
    lifecycle.atomic_writer = failing_writer()
    with pytest.raises(ValueError, match="P2P_VERTICAL_APPLY_FAILED"):
        project.apply_project_vertical_adoption(
            source_coordinate,
            preview_token=adoption.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key="failed-adopt",
        )
    assert _workspace_file_snapshot(project_root) == before_adopt
    assert project.mutation_status(idempotency_key="failed-adopt").state == "not_found"

    lifecycle.atomic_writer = AtomicMutationWriter(
        root=project_root,
        p2p_dir=project_root / ".p2p",
    )
    project.apply_project_vertical_adoption(
        source_coordinate,
        preview_token=adoption.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key="successful-adopt",
    )
    patch = tmp_path / "failure-migration-patch.yml"
    patch.write_text(
        "project_definition_patch:\n"
        "  schema_version: 1\n"
        "  actor: owner\n"
        "  operations:\n"
        "    - op: set_field\n"
        "      section_id: custom_overview\n"
        "      field_id: summary\n"
        "      value: evidence\n"
        "      source: owner\n",
        encoding="utf-8",
    )
    project.update_project_definition(patch)
    analysis = project.preview_project_vertical_migration(
        target_coordinate,
        actor="owner",
    )
    mapping = _transition_plan(
        analysis,
        targets={
            "definition_field:custom_overview.summary": (
                "definition_field:custom_overview.renamed_summary"
            ),
        },
    )
    migration = project.preview_project_vertical_migration(
        target_coordinate,
        actor="owner",
        mapping=mapping,
    )
    before_migrate = _workspace_file_snapshot(project_root)
    lifecycle.atomic_writer = failing_writer()
    with pytest.raises(ValueError, match="P2P_VERTICAL_APPLY_FAILED"):
        project.apply_project_vertical_migration(
            target_coordinate,
            preview_token=migration.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key="failed-migrate",
            mapping=mapping,
        )
    assert _workspace_file_snapshot(project_root) == before_migrate
    assert project.mutation_status(idempotency_key="failed-migrate").state == "not_found"


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
    project.init_project("Adopt project", starter_id="empty")
    install = project.preview_portable_vertical_install(archive, expected_checksum=checksum, actor="owner")
    project.apply_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        preview_token=install.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"install:{checksum}",
    )
    adoption = project.preview_project_vertical_adoption(coordinate, actor="owner")

    with pytest.raises(ValueError, match="P2P_VERTICAL_CONFIRMATION_REQUIRED"):
        project.apply_project_vertical_adoption(
            coordinate,
            preview_token=adoption.preview.preview_token,
            confirmed=False,
            actor="owner",
            idempotency_key=f"adopt:{coordinate}",
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
            idempotency_key=f"adopt:{coordinate}",
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
    project.init_project("Migration project", starter_id="empty")
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
            idempotency_key=f"install:{checksum}",
        )
    adoption = project.preview_project_vertical_adoption(source_coordinate, actor="owner")
    project.apply_project_vertical_adoption(
        source_coordinate,
        preview_token=adoption.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"adopt:{source_coordinate}",
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

    analysis = project.preview_project_vertical_migration(
        target_coordinate,
        actor="owner",
    )
    assert analysis.apply_allowed is False
    assert analysis.preview is None
    assert analysis.impact.required_decisions.total == 1
    mapped_plan = _transition_plan(
        analysis,
        targets={
            "definition_field:custom_overview.summary": (
                "definition_field:custom_overview.renamed_summary"
            ),
        },
    )
    mapped = project.preview_project_vertical_migration(
        target_coordinate,
        actor="owner",
        mapping=mapped_plan,
    )
    transition = mapped.impact.evidence_transitions.items[0]
    assert transition.disposition.value == "mapped"
    assert transition.target is not None
    assert transition.target.ref == "definition_field:custom_overview.renamed_summary"

    orphan_plan = _transition_plan(analysis)
    orphaned = project.preview_project_vertical_migration(
        target_coordinate,
        actor="owner",
        mapping=orphan_plan,
    )
    assert orphaned.impact.evidence_transitions.items[0].disposition.value == "preserve_as_orphan"
    project.apply_project_vertical_migration(
        target_coordinate,
        preview_token=orphaned.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"migrate:{target_coordinate}",
        mapping=orphan_plan,
    )
    state = project.project_definition_view().state

    assert state is not None
    assert state.vertical_id == "migration_target"
    assert len(state.orphans) == 1
    assert state.orphans[0].value == "preserved evidence"
    assert state.orphans[0].source_field_id == "summary"


@pytest.mark.service
def test_migration_materializes_mixed_evidence_in_its_own_memory_family(
    tmp_path: Path,
) -> None:
    authoring = P2PWorkspace(tmp_path)
    source_archive, source_checksum, source_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="mixed-source",
        version="1.0.0",
    )
    target_archive, target_checksum, target_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="mixed-target",
        version="2.0.0",
        section_id="target_overview",
        question_id="target_overview_question",
        rubric_id="target_overview_coverage",
    )
    project = P2PWorkspace(tmp_path / "mixed-project")
    project.init_project("Mixed migration", owner="owner", starter_id="empty")
    for archive, checksum in (
        (source_archive, source_checksum),
        (target_archive, target_checksum),
    ):
        install = project.preview_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            actor="owner",
        )
        project.apply_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            preview_token=install.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key=f"install:{checksum}",
        )
    adoption = project.preview_project_vertical_adoption(source_coordinate, actor="owner")
    project.apply_project_vertical_adoption(
        source_coordinate,
        preview_token=adoption.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key="mixed-adopt",
    )

    private_value = "MIXED-PRIVATE-DEFINITION-VALUE"
    patch = tmp_path / "mixed-patch.yml"
    patch.write_text(
        yaml.safe_dump(
            {
                "project_definition_patch": {
                    "schema_version": 1,
                    "actor": "owner",
                    "operations": [
                        {
                            "op": "set_field",
                            "section_id": "custom_overview",
                            "field_id": "summary",
                            "value": private_value,
                            "source": "owner",
                        },
                        {
                            "op": "add_assumption",
                            "section_id": "custom_overview",
                            "text": "Mixed assumption",
                        },
                        {
                            "op": "add_blocker",
                            "section_id": "custom_overview",
                            "text": "Mixed blocker",
                        },
                    ],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    project.update_project_definition(patch)
    rubrics_path = project.p2p_dir / "project" / "rubrics.yml"
    rubrics_payload = yaml.safe_load(rubrics_path.read_text(encoding="utf-8"))
    rubrics_payload["criteria"][0]["enabled"] = False
    rubrics_path.write_text(yaml.safe_dump(rubrics_payload, sort_keys=False), encoding="utf-8")
    question = project.next_project_question()
    assert question is not None
    source_question_id = question.question_id
    project.defer_project_question(
        question.question_id,
        actor="owner",
        expected_revision=question.revision,
        reason="Mixed owner evidence",
    )

    analysis = project.preview_project_vertical_migration(target_coordinate, actor="owner")
    assert analysis.impact.questions.created.total == 1
    target_question_ref = analysis.impact.questions.created.items[0]
    target_question_id = target_question_ref.split(":", 1)[1]
    target_refs: dict[str, str] = {}
    for required in analysis.impact.required_decisions.items:
        source_ref = required.source.ref
        if source_ref.startswith("definition_field:"):
            target_refs[source_ref] = "definition_field:target_overview.summary"
        elif source_ref.startswith("definition_assumption:"):
            target_refs[source_ref] = (
                "definition_assumption:target_overview/" + source_ref.rsplit("/", 1)[1]
            )
        elif source_ref.startswith("definition_blocker:"):
            target_refs[source_ref] = (
                "definition_blocker:target_overview/" + source_ref.rsplit("/", 1)[1]
            )
        elif source_ref.startswith("rubric:"):
            target_refs[source_ref] = "rubric:target_overview_coverage"
        elif source_ref.startswith("question:"):
            target_refs[source_ref] = target_question_ref
    assert {item.source.kind.value for item in analysis.impact.required_decisions.items} == {
        "definition_field",
        "definition_assumption",
        "definition_blocker",
        "rubric",
        "question",
    }
    plan = _transition_plan(analysis, targets=target_refs)
    preview = project.preview_project_vertical_migration(
        target_coordinate,
        actor="owner",
        mapping=plan,
    )
    assert preview.apply_allowed is True
    project.apply_project_vertical_migration(
        target_coordinate,
        preview_token=preview.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key="mixed-migrate",
        mapping=plan,
    )

    state = project.project_definition_view().state
    assert state is not None
    section = next(item for item in state.sections if item.section_id == "target_overview")
    assert section.fields["summary"].value == private_value
    assert [item.text for item in section.assumptions] == ["Mixed assumption"]
    assert [item.text for item in section.blockers] == ["Mixed blocker"]
    assert state.orphans == []
    final_rubrics = yaml.safe_load(rubrics_path.read_text(encoding="utf-8"))["criteria"]
    target_rubric = next(item for item in final_rubrics if item["id"] == "target_overview_coverage")
    assert target_rubric["enabled"] is False
    final_questions = project.project_questions()
    questions_by_id = {item.question_id: item for item in final_questions.questions}
    assert questions_by_id[target_question_id].state.value == "deferred"
    assert questions_by_id[source_question_id].state.value == "superseded"
    assert private_value not in rubrics_path.read_text(encoding="utf-8")
    assert private_value not in (
        project.p2p_dir / "project" / "questions.yml"
    ).read_text(encoding="utf-8")


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


@pytest.mark.service
@pytest.mark.smoke
def test_hyphenated_portable_init_converges_all_active_reads(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="test-vertical",
        version="0.1.0",
    )
    project = P2PWorkspace(tmp_path / "project")

    project.init_project_with_summary(
        "Hyphenated portable init",
        vertical_pack=archive,
        expected_checksum=checksum,
        owner="owner",
    )

    active = project.active_project_vertical()
    lock = project.project_vertical_lock_status()
    definition = project.project_definition_view()
    readiness = project.project_readiness_snapshot()

    assert active.vertical_id == "test-vertical"
    assert active.coordinate == coordinate
    assert lock.status == "valid"
    assert lock.locked is not None and lock.locked.coordinate == coordinate
    assert definition.valid is True
    assert definition.state is not None
    assert definition.state.vertical_id == "test-vertical"
    assert definition.state.vertical_version == "0.1.0"
    assert project.project_vertical_sections()[0].section_id == "custom_overview"
    assert readiness.identity.vertical_id == "test-vertical"
    assert readiness.identity.vertical_version == "0.1.0"
    assert project.validate().ok is True


@pytest.mark.cli
def test_cli_init_with_hyphenated_portable_pack_converges_immediately(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="cli-init-vertical",
        version="1.0.0",
    )
    project_root = tmp_path / "project"

    result = runner.invoke(
        app,
        [
            "init",
            "CLI portable init",
            "--vertical-pack",
            str(archive),
            "--expected-checksum",
            checksum,
            "--owner",
            "owner",
            "--root",
            str(project_root),
        ],
    )

    assert result.exit_code == 0
    project = P2PWorkspace(project_root)
    assert project.active_project_vertical().coordinate == coordinate
    assert project.project_definition_view().valid is True
    assert project.project_vertical_lock_status().status == "valid"
    assert project.validate().ok is True


@pytest.mark.service
@pytest.mark.smoke
def test_portable_bare_id_is_ambiguous_and_exact_versions_remain_operable(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    v1, checksum_v1, coordinate_v1 = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="versioned-vertical",
        version="1.0.0",
    )
    v2, checksum_v2, coordinate_v2 = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="versioned-vertical",
        version="2.0.0",
    )
    project = P2PWorkspace(tmp_path / "project")
    project.init_project("Versioned portable project", starter_id="empty")
    for archive, checksum in ((v1, checksum_v1), (v2, checksum_v2)):
        preview = project.preview_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            actor="owner",
        )
        project.apply_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            preview_token=preview.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key=f"install:{checksum}",
        )

    with pytest.raises(ValueError, match="P2P_VERTICAL_AMBIGUOUS_REFERENCE"):
        project.show_project_vertical("versioned-vertical")

    assert project.show_project_vertical(coordinate_v1).version == "1.0.0"
    assert project.show_project_vertical(coordinate_v2).version == "2.0.0"

    adoption = project.preview_project_vertical_adoption(coordinate_v1, actor="owner")
    project.apply_project_vertical_adoption(
        coordinate_v1,
        preview_token=adoption.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"adopt:{coordinate_v1}",
    )
    patch = tmp_path / "versioned-definition-patch.yml"
    patch.write_text(
        "project_definition_patch:\n"
        "  schema_version: 1\n"
        "  actor: owner\n"
        "  operations:\n"
        "    - op: set_field\n"
        "      section_id: custom_overview\n"
        "      field_id: summary\n"
        "      value: preserved across versions\n"
        "      provenance:\n"
        "        source: owner\n",
        encoding="utf-8",
    )
    project.update_project_definition(patch)
    migration = project.preview_project_vertical_migration(coordinate_v2, actor="owner")
    project.apply_project_vertical_migration(
        coordinate_v2,
        preview_token=migration.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"migrate:{coordinate_v2}",
    )

    definition = project.project_definition_view()
    assert project.active_project_vertical().coordinate == coordinate_v2
    assert project.project_vertical_lock_status().status == "valid"
    assert definition.valid is True
    assert definition.state is not None
    assert definition.state.vertical_version == "2.0.0"
    assert definition.state.sections[0].fields["summary"].value == "preserved across versions"
    assert project.project_readiness_snapshot().identity.vertical_version == "2.0.0"
    assert project.validate().ok is True


@pytest.mark.cli
@pytest.mark.service
def test_exact_coordinate_equivalence_preserves_precedence_and_conflict_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="coordinate-conflict",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project("Coordinate conflict", starter_id="empty")
    install = project.preview_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        actor="owner",
    )
    project.apply_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        preview_token=install.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"install:{checksum}",
    )
    project_pack = (
        project_root
        / ".p2p"
        / "project"
        / "verticals"
        / "_portable"
        / "test"
        / "coordinate-conflict"
        / "1.0.0"
    )
    home = tmp_path / "home"
    user_pack = home / ".p2p" / "verticals" / "coordinate-conflict-copy"
    shutil.copytree(project_pack, user_pack)
    monkeypatch.setenv("HOME", str(home))

    equivalent = project.show_project_vertical(coordinate)
    assert equivalent.source == "project_local"

    section_path = user_pack / "sections" / "custom_overview.yml"
    section_payload = yaml.safe_load(section_path.read_text(encoding="utf-8"))
    section_payload["section"]["purpose"] = "Conflicting semantic content."
    section_path.write_text(yaml.safe_dump(section_payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="P2P_VERTICAL_COORDINATE_CONFLICT"):
        project.show_project_vertical(coordinate)

    result = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "show",
            coordinate,
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 3
    assert cli_error(result)["code"] == "P2P_VERTICAL_COORDINATE_CONFLICT"


@pytest.mark.service
@pytest.mark.parametrize("drift", ["version", "checksum"])
def test_portable_definition_identity_drift_fails_closed(tmp_path: Path, drift: str) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, _ = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="drift-vertical",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project_with_summary(
        "Portable drift",
        vertical_pack=archive,
        expected_checksum=checksum,
        owner="owner",
    )
    definition_path = project_root / ".p2p" / "project" / "definition.yml"
    payload = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
    if drift == "version":
        payload["project_definition"]["vertical_version"] = "9.9.9"
        expected_field = "project_definition.vertical_version"
    else:
        payload["project_definition"]["lock"]["checksum"] = "0" * 64
        expected_field = "project_definition.lock.checksum"
    definition_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    definition = project.project_definition_view()
    validation = project.validate()

    assert definition.valid is False
    assert any(issue.field == expected_field for issue in definition.issues)
    assert validation.ok is False
    assert any(finding.code == "P2P255_PROJECT_DEFINITION_INVALID" for finding in validation.findings)


@pytest.mark.service
@pytest.mark.parametrize(
    "drift",
    ["active_id", "active_coordinate", "lock_id", "lock_version", "lock_checksum"],
)
def test_portable_active_or_lock_identity_drift_fails_without_read_writes(
    tmp_path: Path,
    drift: str,
) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, _ = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="identity-drift",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project_with_summary(
        "Portable identity drift",
        vertical_pack=archive,
        expected_checksum=checksum,
        owner="owner",
    )
    project_dir = project_root / ".p2p" / "project"
    if drift in {"active_id", "active_coordinate"}:
        path = project_dir / "vertical.yml"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if drift == "active_id":
            payload["project_vertical"]["active_vertical_id"] = "other"
        else:
            payload["project_vertical"]["active_vertical_coordinate"] = "test/other@1.0.0"
    else:
        path = project_dir / "vertical.lock.yml"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if drift == "lock_id":
            payload["project_vertical_lock"]["vertical_id"] = "other"
        elif drift == "lock_version":
            payload["project_vertical_lock"]["version"] = "2.0.0"
        else:
            payload["project_vertical_lock"]["checksum"]["value"] = "0" * 64
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    before = {
        item.relative_to(project_root).as_posix(): item.read_bytes()
        for item in project_dir.rglob("*")
        if item.is_file()
    }

    with pytest.raises(ValueError):
        project.active_project_vertical()
    validation = project.validate()
    after = {
        item.relative_to(project_root).as_posix(): item.read_bytes()
        for item in project_dir.rglob("*")
        if item.is_file()
    }

    assert validation.ok is False
    assert any(finding.code == "P2P251_INVALID_ACTIVE_VERTICAL" for finding in validation.findings)
    assert after == before


@pytest.mark.service
def test_vertical_candidate_rejects_exact_identity_drift_before_writing(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="candidate-drift",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project("Candidate drift", starter_id="empty")
    install = project.preview_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        actor="owner",
    )
    project.apply_portable_vertical_install(
        archive,
        expected_checksum=checksum,
        preview_token=install.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"install:{checksum}",
    )
    service = project._project_vertical_service()
    candidate = service.render_migration_candidate(coordinate, actor="owner")
    active_payload = yaml.safe_load(candidate.candidate_files[".p2p/project/vertical.yml"])
    active_payload["project_vertical"]["active_vertical_coordinate"] = "test/other@1.0.0"
    candidate.candidate_files[".p2p/project/vertical.yml"] = yaml.safe_dump(
        active_payload,
        sort_keys=False,
    ).encode("utf-8")
    before = {
        item.relative_to(project_root).as_posix(): item.read_bytes()
        for item in (project_root / ".p2p" / "project").rglob("*")
        if item.is_file()
    }

    with pytest.raises(ValueError, match="active coordinate candidate is incoherent"):
        service.validate_migration_candidate(candidate)

    after = {
        item.relative_to(project_root).as_posix(): item.read_bytes()
        for item in (project_root / ".p2p" / "project").rglob("*")
        if item.is_file()
    }
    assert after == before


@pytest.mark.cli
def test_cli_validates_schema_v3_directory_with_exact_extends(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    base_archive, base_checksum, base_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="portable-base",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project("Portable derived validation", starter_id="empty")
    install = project.preview_portable_vertical_install(
        base_archive,
        expected_checksum=base_checksum,
        actor="owner",
    )
    project.apply_portable_vertical_install(
        base_archive,
        expected_checksum=base_checksum,
        preview_token=install.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key=f"install:{base_checksum}",
    )
    derived = tmp_path / "portable-derived"
    project.scaffold_portable_vertical(
        derived,
        publisher="test",
        vertical_id="portable-derived",
        version="1.0.0",
        name="Portable Derived",
        license_id="MIT",
        extends=base_coordinate,
    )
    derived_archive = tmp_path / "portable-derived.p2pv"
    project.package_portable_vertical(derived, output=derived_archive)

    result = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "validate",
            str(derived),
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    validation = cli_data(result)["validation"]
    assert validation["valid"] is True
    assert validation["coordinate"] == "test/portable-derived@1.0.0"

    archive_result = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "validate",
            str(derived_archive),
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )
    assert archive_result.exit_code == 0
    archive_validation = cli_data(archive_result)["validation"]
    assert archive_validation["valid"] is True
    assert archive_validation["coordinate"] == "test/portable-derived@1.0.0"


@pytest.mark.cli
def test_portable_cli_uses_stable_json_envelope(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["project", "vertical", "schema", "--root", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0
    payload = cli_envelope(result)
    assert payload["ok"] is True
    assert payload["operation"] == "project.vertical.schema"
    assert payload["error"] is None
    assert payload["data"]["schema_version"] == 3


@pytest.mark.cli
def test_portable_cli_reports_ambiguous_bare_reference_as_json_error(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    archives = [
        _portable_pack(
            authoring,
            tmp_path,
            vertical_id="cli-ambiguous",
            version=version,
        )
        for version in ("1.0.0", "2.0.0")
    ]
    project_root = tmp_path / "project"
    project = P2PWorkspace(project_root)
    project.init_project("CLI ambiguous reference", starter_id="empty")
    for archive, checksum, _ in archives:
        preview = project.preview_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            actor="owner",
        )
        project.apply_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            preview_token=preview.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key=f"install:{checksum}",
        )

    result = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "show",
            "cli-ambiguous",
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 1
    payload = cli_envelope(result)
    assert payload["ok"] is False
    assert payload["operation"] == "project.vertical.show"
    assert payload["error"]["code"] == "P2P_VERTICAL_AMBIGUOUS_REFERENCE"


@pytest.mark.cli
def test_portable_cli_install_and_adopt_preview_apply_contract(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    archive, checksum, coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="cli-demo",
        version="1.0.0",
    )
    project_root = tmp_path / "project"
    P2PWorkspace(project_root).init_project("CLI project", starter_id="empty")

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
    assert bad.exit_code == 3
    assert cli_error(bad)["code"] == "P2P_VERTICAL_CHECKSUM_MISMATCH"

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
    install_payload = cli_data(install_preview)
    install_token = install_payload["preview"]["preview_token"]
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
            "--idempotency-key",
            "cli-install-operation",
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
    assert cli_data(installed)["mutation"]["status"] == "applied"

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
    adopt_payload = cli_data(adopt_preview)
    adopt_token = adopt_payload["preview"]["preview_token"]
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
            "--idempotency-key",
            "cli-adopt-operation",
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
    adopted_payload = cli_envelope(adopted)
    assert adopted_payload["ok"] is True
    assert adopted_payload["operation"] == "project.vertical.adopt.apply"

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
        vertical_id="cli-target",
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
        idempotency_key=f"install:{target_checksum}",
    )
    analysis_result = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "migrate",
            "preview",
            target_coordinate,
            "--actor",
            "owner",
            "--root",
            str(project_root),
            "--format",
            "json",
        ],
    )
    analysis_payload = cli_data(analysis_result)
    assert "CLI evidence" not in analysis_result.stdout
    text_analysis_result = runner.invoke(
        app,
        [
            "project",
            "vertical",
            "migrate",
            "preview",
            target_coordinate,
            "--actor",
            "owner",
            "--root",
            str(project_root),
        ],
    )
    assert text_analysis_result.exit_code == 0
    assert "CLI evidence" not in text_analysis_result.stdout
    assert ".p2p/" not in text_analysis_result.stdout
    required = analysis_payload["impact"]["required_decisions"]["items"]
    assert len(required) == 1
    mapping_payload = {
        "vertical_transition_plan": {
            "schema_version": 1,
            "contract_version": "p2p-vertical-transition-plan/v1",
            "analysis_fingerprint_sha256": analysis_payload["impact"][
                "analysis_fingerprint_sha256"
            ],
            "decisions": [
                {
                    "id": required[0]["id"],
                    "action": "map",
                    "source": required[0]["source"],
                    "target": {
                        "kind": "definition_field",
                        "ref": "definition_field:custom_overview.renamed_summary",
                    },
                }
            ],
        }
    }
    mapping = tmp_path / "cli-mapping.yml"
    mapping.write_text(yaml.safe_dump(mapping_payload, sort_keys=False), encoding="utf-8")
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
    migrate_payload = cli_data(migrate_preview)
    migrate_token = migrate_payload["preview"]["preview_token"]
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
            "--idempotency-key",
            "cli-migrate-operation",
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
    migrated_payload = cli_envelope(migrated)
    assert migrated_payload["ok"] is True
    assert migrated_payload["operation"] == "project.vertical.migrate.apply"

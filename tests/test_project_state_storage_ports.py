from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml

import p2p_engine
from p2p_engine.cli_contract import CLI_CONTRACT_VERSION
from p2p_engine.core.project_state_storage import (
    ProjectStateMutation,
    ProjectStateQuery,
    ProjectStateRevision,
    ProjectStorageError,
    ProjectStorageErrorCode,
)
from p2p_engine.services.canonical_memory import CanonicalBundleCodec
from p2p_engine.services.project_application import (
    ProjectApplicationService,
    open_project_application,
)
from p2p_engine.services.workspace_transactions import WorkspaceTransactionLockService
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.project_storage import (
    PROJECT_STORAGE_MANIFEST_PATH,
    ProjectStorageManifestStore,
)


def _project(root: Path, *, name: str = "Storage ports") -> ProjectApplicationService:
    P2PWorkspace(root).init_project(name, owner="owner", agent_profile="generic")
    return open_project_application(root)


def test_init_writes_replica_local_manifest_and_reopens_selected_adapter(
    tmp_path: Path,
) -> None:
    app = _project(tmp_path)
    manifest = ProjectStorageManifestStore(tmp_path).load()

    assert app.storage_selection().to_dict() == {
        "contract": "p2p-project-storage/v1",
        "project_uuid": manifest.project_uuid,
        "adapter": "filesystem",
        "schema_version": 1,
        "source": "replica_local_manifest",
        "persistent": True,
        "warnings": [],
    }
    assert manifest.project_uuid == app.project_identity().project_uuid.value
    assert app.storage_capabilities.to_dict()["atomic_multi_entity_writes"] is True


def test_manifest_is_excluded_from_bundle_and_included_in_physical_backup(
    tmp_path: Path,
) -> None:
    app = _project(tmp_path)
    bundle = app.adapter.snapshots.export_bundle()
    backup = app.adapter.backups.create_backup()

    with ZipFile(BytesIO(bundle.content), "r") as archive:
        bundle_entries = set(archive.namelist())
    decoded_bundle = CanonicalBundleCodec().decode_bundle(bundle.content)
    decoded_backup = CanonicalBundleCodec().decode_physical_backup(backup.content)

    assert decoded_bundle.snapshot.semantic_state_digest == bundle.semantic_state_digest
    assert PROJECT_STORAGE_MANIFEST_PATH not in {
        entity.storage_locator for entity in decoded_bundle.snapshot.entities
    }
    assert all("storage.yml" not in name for name in bundle_entries)
    assert PROJECT_STORAGE_MANIFEST_PATH in decoded_backup.files
    assert decoded_backup.semantic_state_digest == bundle.semantic_state_digest


def test_legacy_open_is_non_writing_and_explicit_init_adopts_manifest(tmp_path: Path) -> None:
    _project(tmp_path, name="Legacy storage")
    manifest_path = tmp_path / PROJECT_STORAGE_MANIFEST_PATH
    manifest_path.unlink()

    legacy = open_project_application(tmp_path)

    assert legacy.storage_selection().source == "validated_legacy_filesystem"
    assert legacy.storage_selection().persistent is False
    assert not manifest_path.exists()

    created = legacy.init_project(
        "Legacy storage",
        owner="owner",
        agent_profile="generic",
        storage_adapter="filesystem",
    )

    assert Path(PROJECT_STORAGE_MANIFEST_PATH) in created
    assert open_project_application(tmp_path).storage_selection().persistent is True


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda payload: payload["project_storage"].update({"adapter": "unknown"}),
            ProjectStorageErrorCode.adapter_unavailable,
        ),
        (
            lambda payload: payload["project_storage"].update({"schema_version": 99}),
            ProjectStorageErrorCode.manifest_invalid,
        ),
        (
            lambda payload: payload["project_storage"].update(
                {"project_uuid": "00000000-0000-0000-0000-000000000001"}
            ),
            ProjectStorageErrorCode.identity_mismatch,
        ),
    ],
)
def test_manifest_selection_rejects_unavailable_schema_and_identity_mismatch(
    tmp_path: Path,
    mutate,
    code: ProjectStorageErrorCode,
) -> None:
    _project(tmp_path)
    path = tmp_path / PROJECT_STORAGE_MANIFEST_PATH
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)

    assert raised.value.code == code
    assert str(tmp_path) not in str(raised.value)


def test_filesystem_selection_rejects_contradictory_backend_artifact(tmp_path: Path) -> None:
    _project(tmp_path)
    (tmp_path / ".p2p/local/project.sqlite3").write_bytes(b"not a database")

    with pytest.raises(ProjectStorageError) as raised:
        open_project_application(tmp_path)

    assert raised.value.code == ProjectStorageErrorCode.configuration_contradiction


def test_sqlite_adapter_is_explicitly_initialized_without_dual_writing(
    tmp_path: Path,
) -> None:
    P2PWorkspace(tmp_path).init_project(
        "SQLite adapter",
        owner="owner",
        storage_adapter="sqlite",
    )
    reopened = open_project_application(tmp_path)

    assert reopened.storage_selection().adapter == "sqlite"
    assert not (tmp_path / ".p2p/project.yml").exists()
    assert (tmp_path / ".p2p/local/project.sqlite3").is_file()


def test_identity_derivation_updates_storage_binding_in_same_mutation(tmp_path: Path) -> None:
    app = _project(tmp_path, name="Derived storage identity")
    preview = app.preview_project_identity_derivation(
        operation_key="derive-storage-contract-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )

    result = app.apply_project_identity_derivation(
        operation_key="derive-storage-contract-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    reopened = open_project_application(tmp_path)

    assert result.status == "applied"
    assert PROJECT_STORAGE_MANIFEST_PATH in result.mutation.changed_paths
    assert app.storage_selection().manifest.project_uuid == result.current.project_uuid.value
    assert app.project_identity() == result.current
    assert reopened.storage_selection().manifest.project_uuid == (
        reopened.project_identity().project_uuid.value
    )


def test_initialization_refreshes_storage_binding_without_reopening(tmp_path: Path) -> None:
    app = open_project_application(tmp_path)

    app.init_project(
        "Fresh storage binding",
        owner="owner",
        storage_adapter="filesystem",
    )

    assert app.storage_selection().persistent is True
    assert app.storage_selection().manifest.project_uuid == (
        app.project_identity().project_uuid.value
    )


def test_shared_repository_contract_supports_typed_query_and_stable_revision(
    tmp_path: Path,
) -> None:
    app = _project(tmp_path)
    before = app.project_state_revision()
    records = app.query_project_state(
        ProjectStateQuery(entity_types=("p2p.project.manifest",))
    )

    assert isinstance(before, ProjectStateRevision)
    assert len(records) == 1
    assert records[0].ref.entity_type == "p2p.project.manifest"
    assert app.project_state_entity(records[0].ref) == records[0]
    assert app.project_state_revision() == before


def test_unit_of_work_commits_two_entities_atomically_and_returns_receipt(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    app = _project(source, name="Atomic storage")
    shutil.copytree(source, target)
    (target / ".p2p/governance/constitution.md").write_text(
        "# Constitution\n\nAccepted.\n", encoding="utf-8"
    )
    (target / ".p2p/governance/decision-rules.md").write_text(
        "# Decision Rules\n\nAccepted.\n", encoding="utf-8"
    )
    target_snapshot = open_project_application(target).canonical_memory_snapshot()
    before = app.project_state_revision()

    with app.project_state_unit_of_work() as unit:
        unit.stage(
            ProjectStateMutation(
                operation_id="contract-two-entity",
                actor="owner",
                expected_revision=before,
                target=target_snapshot,
                receipt_id="receipt-contract-two-entity",
            )
        )
        result = unit.commit()

    assert result.receipt_id == "receipt-contract-two-entity"
    assert len(result.changed_entities) == 2
    assert (source / ".p2p/governance/constitution.md").read_text(encoding="utf-8") == (
        "# Constitution\n\nAccepted.\n"
    )
    assert (source / ".p2p/governance/decision-rules.md").read_text(encoding="utf-8") == (
        "# Decision Rules\n\nAccepted.\n"
    )
    assert result.revision.sha256 == target_snapshot.semantic_state_digest


def test_unit_of_work_rollback_stale_revision_and_bounded_writer_error(tmp_path: Path) -> None:
    app = _project(tmp_path)
    snapshot = app.canonical_memory_snapshot()
    revision = app.project_state_revision()

    unit = app.project_state_unit_of_work()
    unit.stage(
        ProjectStateMutation(
            operation_id="contract-rollback",
            actor="owner",
            expected_revision=revision,
            target=snapshot,
        )
    )
    unit.rollback()
    assert app.project_state_revision() == revision

    (tmp_path / ".p2p/governance/constitution.md").write_text(
        "# Constitution\n\nChanged outside the stale command.\n", encoding="utf-8"
    )
    with pytest.raises(ProjectStorageError) as stale:
        app.project_state_unit_of_work().stage(
            ProjectStateMutation(
                operation_id="contract-stale",
                actor="owner",
                expected_revision=revision,
                target=snapshot,
            )
        )
    assert stale.value.code == ProjectStorageErrorCode.stale_revision

    current = app.canonical_memory_snapshot()
    lock = WorkspaceTransactionLockService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    lock.acquire("contract-held-writer", owner="other-writer")
    try:
        blocked_unit = app.project_state_unit_of_work()
        blocked_unit.stage(
            ProjectStateMutation(
                operation_id="contract-bounded-writer",
                actor="owner",
                expected_revision=ProjectStateRevision(current.semantic_state_digest),
                target=current,
                lock_wait_timeout=0.01,
            )
        )
        with pytest.raises(ProjectStorageError) as blocked:
            blocked_unit.commit()
        assert blocked.value.code == ProjectStorageErrorCode.busy
    finally:
        lock.release("contract-held-writer")


def test_bundle_and_agent_guidance_are_backend_neutral(tmp_path: Path) -> None:
    app = _project(tmp_path, name="Neutral guidance")
    instruction_paths = (
        Path("AGENTS.md"),
        Path(".p2p/agent-policy.yml"),
        Path(".p2p/agent-integrations.yml"),
    )
    before = {path: (tmp_path / path).read_bytes() for path in instruction_paths}
    first_bundle = app.adapter.snapshots.export_bundle()
    (tmp_path / PROJECT_STORAGE_MANIFEST_PATH).unlink()

    legacy = open_project_application(tmp_path)
    legacy.refresh_agent_instructions(profile="generic")
    second_bundle = legacy.adapter.snapshots.export_bundle()
    after = {path: (tmp_path / path).read_bytes() for path in instruction_paths}

    assert before == after
    assert first_bundle.content == second_bundle.content
    assert all(b"storage.yml" not in content for content in after.values())
    assert b"SQLite, journal, WAL, or backend-private storage directly" in after[
        Path("AGENTS.md")
    ]


def test_cli_and_mcp_depend_on_application_boundary_not_filesystem_adapter() -> None:
    root = Path(__file__).resolve().parents[1] / "src/p2p_engine"
    presentation = [root / "cli.py", root / "cli_shared.py", *sorted((root / "mcp").rglob("*.py"))]

    for path in presentation:
        source = path.read_text(encoding="utf-8")
        assert "from p2p_engine.storage.filesystem import" not in source, path
        assert "import p2p_engine.storage.filesystem" not in source, path

    for path in sorted((root / "core").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "p2p_engine.storage" not in source, path

    core_source = (root / "core/project_state_storage.py").read_text(encoding="utf-8")
    assert "pathlib" not in core_source
    assert "sqlite" not in core_source.lower()
    assert "yaml" not in core_source.lower()


def test_storage_ports_are_internal_and_cli_json_remains_server_boundary() -> None:
    assert CLI_CONTRACT_VERSION == "p2p-cli/v1"
    assert not hasattr(p2p_engine, "ProjectApplicationService")
    assert not hasattr(p2p_engine, "ProjectStateAdapter")

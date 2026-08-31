from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.project_identity import (
    AuthorityEpoch,
    CopyIntent,
    EntityVersion,
    LineageRelation,
    LineageVisibility,
    ProjectIdentity,
    ProjectLineage,
    ProjectMode,
    ProjectUuid,
    RemoteProjectRevision,
    ReplicaId,
    SourceMemoryRevision,
    project_identity_from_mapping,
)
from p2p_engine.mcp.registry import tool_definitions
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.project_identity import ProjectIdentityService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.storage.project_identity import FilesystemProjectIdentityStore
from tests.cli_assertions import cli_data
from tests.filesystem_assertions import assert_no_workspace_mutation

runner = CliRunner()


def _workspace(root: Path, *, name: str = "Identity Project") -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project(name, owner="owner")
    return workspace


def _legacy_workspace(root: Path) -> P2PWorkspace:
    _workspace(root, name="Legacy Identity")
    (root / ".p2p/project/identity.yml").unlink()
    (root / ".p2p/local/replica.yml").unlink()
    manifest_path = root / ".p2p/project.yml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    del manifest["project"]["uuid"]
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return P2PWorkspace(root)


def _derive_preview(workspace: P2PWorkspace, key: str = "derive-project-12345678"):
    return workspace.preview_project_identity_derivation(
        operation_key=key,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )


def test_identity_types_are_canonical_and_revision_namespaces_do_not_mix() -> None:
    project_uuid = ProjectUuid.new()
    assert str(UUID(project_uuid.value)) == project_uuid.value
    assert project_uuid != ProjectUuid.new()

    assert RemoteProjectRevision(2).compare(RemoteProjectRevision(1)) == 1
    assert EntityVersion(2).compare(EntityVersion(2)) == 0
    assert AuthorityEpoch(1).compare(AuthorityEpoch(2)) == -1
    with pytest.raises(ValueError, match="P2P_PROJECT_REVISION_NAMESPACE_MISMATCH"):
        RemoteProjectRevision(1).compare(EntityVersion(1))
    with pytest.raises(ValueError, match="P2P_PROJECT_IDENTITY_INVALID"):
        project_identity_from_mapping(
            {
                "contract": "p2p-project-identity/v1",
                "policy_version": True,
                "project_uuid": project_uuid.value,
                "display_name": "Invalid policy",
                "mode": "standalone",
                "remote_binding": None,
                "replica_id": ReplicaId.new().value,
                "lineage": [],
            }
        )


def test_initialization_assigns_path_and_name_independent_identity(tmp_path: Path) -> None:
    first = _workspace(tmp_path / "one", name="Same Name").project_identity()
    second = _workspace(tmp_path / "two", name="Same Name").project_identity()

    assert first.project_uuid != second.project_uuid
    assert first.project_uuid.value != "same-name"
    assert first.replica_id != second.replica_id
    assert first.mode == ProjectMode.standalone


def test_reinitialization_rename_move_backup_and_restore_preserve_uuid(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    workspace = _workspace(source, name="Before Rename")
    initial = workspace.project_identity()

    renamed = initial.with_display_name("After Rename")
    assert renamed.project_uuid == initial.project_uuid
    assert renamed.replica_id == initial.replica_id
    assert renamed.display_name == "After Rename"

    moved = tmp_path / "moved"
    shutil.copytree(source, moved)
    restored = P2PWorkspace(moved).project_identity()
    assert restored.project_uuid == initial.project_uuid
    assert restored.replica_id == initial.replica_id


def test_transition_matrix_and_future_lifecycle_contracts_are_explicit(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    identity = workspace.project_identity()
    matrix = {item["operation"]: item for item in workspace.project_identity_transition_matrix()}

    assert set(matrix) == {
        "init",
        "rename",
        "move",
        "backup",
        "restore",
        "share",
        "clone",
        "copy",
        "derive",
        "suspend",
        "detach",
    }
    assert matrix["derive"]["project_uuid"] == "new"
    assert matrix["rename"]["project_uuid"] == "preserve"

    transfer = workspace.project_transfer_identity_contract(
        server_instance_id="wavekit-prod-1", remote_project_id="remote-42"
    )
    clone = workspace.project_replica_identity_contract(
        move=False, operation_key="clone-replica-12345678"
    )
    move = workspace.project_replica_identity_contract(
        move=True, operation_key="move-replica-12345678"
    )
    detach = workspace.project_detach_identity_contract(operation_key="detach-project-12345678")

    assert transfer.project_uuid == identity.project_uuid
    assert clone.project_uuid == identity.project_uuid
    assert clone.target_replica_id != identity.replica_id
    assert move.target_replica_id == identity.replica_id
    assert detach.detached_project_uuid != identity.project_uuid
    assert detach.source_project_uuid == identity.project_uuid


@pytest.mark.parametrize("store_type", [FilesystemProjectIdentityStore], ids=["filesystem"])
def test_identity_adapter_contract_round_trips_without_storage_locators(
    tmp_path: Path,
    store_type,
) -> None:
    workspace = _workspace(tmp_path)
    store = store_type(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    identity = workspace.project_identity()

    assert store.load() == identity
    canonical = store.identity_bytes(identity).decode("ascii")
    replica = store.replica_bytes(identity).decode("ascii")
    forbidden = (str(tmp_path), "filesystem", "sqlite", "git", "token", "password")
    assert all(item.lower() not in (canonical + replica).lower() for item in forbidden)


def test_identity_store_rejects_uuid_name_and_replica_mismatch(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    identity = workspace.project_identity()
    manifest_path = tmp_path / ".p2p/project.yml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["project"]["uuid"] = ProjectUuid.new().value
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="P2P_PROJECT_IDENTITY_MISMATCH"):
        workspace.project_identity()

    manifest["project"]["uuid"] = identity.project_uuid.value
    manifest["project"]["name"] = "Contradictory Name"
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="P2P_PROJECT_IDENTITY_MISMATCH"):
        P2PWorkspace(tmp_path).project_identity()


def test_identity_store_rejects_duplicate_unknown_secret_and_cyclic_lineage(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    identity = workspace.project_identity()
    path = tmp_path / ".p2p/project/identity.yml"
    original = path.read_text(encoding="utf-8")

    path.write_text(original + "project_identity: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="P2P_PROJECT_IDENTITY_INVALID"):
        P2PWorkspace(tmp_path).project_identity()

    payload = yaml.safe_load(original)
    payload["project_identity"]["access_token"] = "forbidden-secret"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="fields are not exact"):
        P2PWorkspace(tmp_path).project_identity()

    payload = yaml.safe_load(original)
    payload["project_identity"]["lineage"] = [
        {
            "relation": LineageRelation.derived_from.value,
            "source_project_uuid": identity.project_uuid.value,
            "source_revision": {
                "namespace": "source_memory",
                "sha256": "0" * 64,
            },
            "visibility": LineageVisibility.preserved.value,
        }
    ]
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="P2P_PROJECT_LINEAGE_CYCLE"):
        P2PWorkspace(tmp_path).project_identity()

    payload = yaml.safe_load(original)
    payload["project_identity"]["policy_version"] = True
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported identity policy version"):
        P2PWorkspace(tmp_path).project_identity()


def test_identity_less_project_requires_explicit_backup_protected_adoption(
    tmp_path: Path,
) -> None:
    workspace = _legacy_workspace(tmp_path)
    status = workspace.project_identity_status()
    assert status.state == "adoption_required"
    with pytest.raises(ValueError, match="P2P_PROJECT_IDENTITY_ADOPTION_REQUIRED"):
        workspace.create_proposal("Blocked before adoption")

    preview = workspace.preview_project_identity_adoption(
        operation_key="adopt-legacy-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    manifest_before = (tmp_path / ".p2p/project.yml").read_bytes()
    result = workspace.apply_project_identity_adoption(
        operation_key="adopt-legacy-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert workspace.project_identity_status().state == "valid"
    assert (tmp_path / preview.backup_path).read_bytes() == manifest_before
    replay = workspace.apply_project_identity_adoption(
        operation_key="adopt-legacy-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    assert replay.status == "already_applied"


def test_adoption_rejects_stale_preview_without_mutating_identity(tmp_path: Path) -> None:
    workspace = _legacy_workspace(tmp_path)
    preview = workspace.preview_project_identity_adoption(
        operation_key="adopt-stale-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )

    result = workspace.apply_project_identity_adoption(
        operation_key="adopt-stale-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        preview_token="0" * 64,
        confirm=True,
    )

    assert result.status == "stale_preview"
    assert workspace.project_identity_status().state == "adoption_required"
    assert preview.candidate.project_uuid == result.current.project_uuid


def test_derivation_is_atomic_idempotent_and_preserves_optional_lineage(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    previous = workspace.project_identity()
    preview = _derive_preview(workspace)
    result = workspace.apply_project_identity_derivation(
        operation_key="derive-project-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert result.current.project_uuid != previous.project_uuid
    assert result.current.replica_id != previous.replica_id
    assert result.current.remote_binding is None
    assert result.current.mode == ProjectMode.standalone
    assert result.current.lineage[-1].source_project_uuid == previous.project_uuid
    replay = workspace.apply_project_identity_derivation(
        operation_key="derive-project-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    assert replay.status == "already_applied"
    assert replay.previous == previous


def test_derivation_can_drop_lineage_and_rejects_operation_key_reuse(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    key = "derive-without-lineage-12345678"
    preview = workspace.preview_project_identity_derivation(
        operation_key=key,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        retain_lineage=False,
    )
    result = workspace.apply_project_identity_derivation(
        operation_key=key,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
        retain_lineage=False,
    )
    assert result.current.lineage == ()

    with pytest.raises(ValueError, match="P2P_IDEMPOTENCY_CONFLICT"):
        workspace.apply_project_identity_derivation(
            operation_key=key,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
            preview_token=preview.mutation.preview_token,
            confirm=True,
            retain_lineage=True,
        )


def test_derivation_failure_after_replace_rolls_back_all_identity_files(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    paths = [
        tmp_path / ".p2p/project.yml",
        tmp_path / ".p2p/project/identity.yml",
        tmp_path / ".p2p/local/replica.yml",
    ]
    before = {path: path.read_bytes() for path in paths}

    def fail(stage: str, target: str) -> None:
        if stage == "after_replace" and target == ".p2p/project/identity.yml":
            raise OSError("injected identity write failure")

    service = ProjectIdentityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        authority=workspace._project_authority_service(),
        receipts=workspace._mutation_receipt_service(),
        atomic_writer=AtomicMutationWriter(
            root=tmp_path,
            p2p_dir=tmp_path / ".p2p",
            failure_injector=fail,
        ),
    )
    preview = service.preview_derivation(
        operation_key="derive-rollback-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    result = service.apply_derivation(
        operation_key="derive-rollback-12345678",
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert {path: path.read_bytes() for path in paths} == before


def test_stale_authority_blocks_derivation_without_writes(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    preview = _derive_preview(workspace, "derive-authority-12345678")
    permissions_path = tmp_path / ".p2p/project/permissions.yml"
    permissions = yaml.safe_load(permissions_path.read_text(encoding="utf-8"))
    permissions["identities"]["replacement-owner"] = {
        "role": "owner",
        "kind": "person",
        "display_name": "Replacement Owner",
    }
    permissions["identities"]["owner"]["role"] = "contributor"
    permissions_path.write_text(yaml.safe_dump(permissions), encoding="utf-8")

    with assert_no_workspace_mutation(tmp_path):
        with pytest.raises(ValueError, match="P2P_AUTHORIZATION_DENIED"):
            workspace.apply_project_identity_derivation(
                operation_key="derive-authority-12345678",
                actor_id="owner",
                executor_id="owner",
                executor_kind="person",
                preview_token=preview.mutation.preview_token,
                confirm=True,
            )


@pytest.mark.parametrize(
    ("intent", "allowed"),
    [
        ("", False),
        (CopyIntent.same_instance.value, True),
        (CopyIntent.read_only.value, True),
        (CopyIntent.new_replica.value, False),
        (CopyIntent.derive.value, False),
    ],
)
def test_duplicate_copy_detection_requires_explicit_operational_choice(
    tmp_path: Path,
    intent: str,
    allowed: bool,
) -> None:
    workspace = _workspace(tmp_path)
    identity = workspace.project_identity()
    assert identity.replica_id is not None
    result = workspace.assess_project_copy(
        observed_project_uuid=identity.project_uuid.value,
        observed_replica_id=identity.replica_id.value,
        intent=intent,
    )
    assert result.state == "replica_collision"
    assert result.allowed is allowed
    assert result.next_actions


def test_cli_and_mcp_identity_reads_have_semantic_parity_and_no_raw_setter(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    cli = runner.invoke(
        app,
        ["project", "identity", "show", "--format", "json", "--root", str(tmp_path)],
    )
    assert cli.exit_code == 0, cli.stdout
    cli_identity = cli_data(cli, operation="project.identity.show")["project_identity"]
    mcp = call_tool("p2p_project_identity_show", {"root": str(tmp_path)})

    assert cli_identity == mcp["project_identity"] == workspace.project_identity().to_dict()
    names = {str(item["name"]) for item in tool_definitions()}
    assert "p2p_project_identity_set" not in names
    assert not any(name.endswith("identity_raw_set") for name in names)
    missing_setter = runner.invoke(app, ["project", "identity", "set", "--root", str(tmp_path)])
    assert missing_setter.exit_code != 0


def test_mcp_derivation_is_consent_gated_and_replays_exact_result(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    key = "mcp-derive-project-12345678"
    preview = call_tool(
        "p2p_project_identity_derive_preview",
        {"root": str(tmp_path), "operation_key": key, "actor_id": "owner"},
    )["project_identity_derivation"]
    token = preview["mutation"]["preview_token"]
    consent = workspace.consent_grant(
        "project_identity_derive_apply",
        f"project-identity@{token}",
        "owner",
        approved_by="owner",
    )
    arguments = {
        "root": str(tmp_path),
        "operation_key": key,
        "preview_token": token,
        "confirm": True,
        "actor_id": "owner",
        "consent_id": consent.consent_id,
    }

    first = call_tool("p2p_project_identity_derive_apply", arguments)
    replay = call_tool("p2p_project_identity_derive_apply", arguments)
    assert first["project_identity_mutation"]["status"] == "applied"
    assert first["consent"]["status"] == "consumed"
    assert replay["project_identity_mutation"]["status"] == "already_applied"
    assert replay["consent"]["status"] == "consumed"


def test_mcp_adoption_is_explicit_consent_gated_and_backup_protected(
    tmp_path: Path,
) -> None:
    workspace = _legacy_workspace(tmp_path)
    key = "mcp-adopt-project-12345678"
    preview = call_tool(
        "p2p_project_identity_adopt_preview",
        {"root": str(tmp_path), "operation_key": key, "actor_id": "owner"},
    )["project_identity_adoption"]
    token = preview["mutation"]["preview_token"]
    consent = workspace.consent_grant(
        "project_identity_adopt_apply",
        f"project-identity@{token}",
        "owner",
        approved_by="owner",
    )
    result = call_tool(
        "p2p_project_identity_adopt_apply",
        {
            "root": str(tmp_path),
            "operation_key": key,
            "preview_token": token,
            "confirm": True,
            "actor_id": "owner",
            "consent_id": consent.consent_id,
        },
    )

    assert result["project_identity_mutation"]["status"] == "applied"
    assert result["consent"]["status"] == "consumed"
    assert (tmp_path / preview["backup_path"]).is_file()


def test_generated_agent_guidance_is_identity_aware_and_storage_neutral(
    tmp_path: Path,
) -> None:
    _workspace(tmp_path)
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    policy = yaml.safe_load((tmp_path / ".p2p/agent-policy.yml").read_text(encoding="utf-8"))

    assert "p2p project identity status --format json" in agents
    assert "There is no public raw identity" in agents
    assert "setter" in agents
    assert "Never invent, replace, copy between projects" in agents
    generated = [
        tmp_path / "AGENTS.md",
        tmp_path / "CLAUDE.md",
        tmp_path / "GEMINI.md",
        tmp_path / ".cursor/rules/p2p.mdc",
        tmp_path / ".github/copilot-instructions.md",
        tmp_path / ".agents/skills/p2p-project/SKILL.md",
    ]
    for path in generated:
        content = path.read_text(encoding="utf-8")
        assert "p2p project identity status --format json" in content
        assert "Never invent" in content
    identity_policy = policy["project_identity"]
    assert identity_policy["manual_identity_edits"] == "forbidden"
    assert identity_policy["raw_identity_setter"] is False
    serialized = yaml.safe_dump(identity_policy).lower()
    assert "identity.yml" not in serialized
    assert "sqlite" not in serialized


def test_identity_public_outputs_and_receipts_do_not_expose_credentials(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    preview = _derive_preview(workspace, "derive-private-output-12345678")
    payload = preview.to_dict()
    rendered = yaml.safe_dump(payload).lower()
    assert "access_token" not in rendered
    assert "password" not in rendered
    assert "private_key" not in rendered
    assert str(tmp_path).lower() not in rendered


def test_lineage_is_historical_only_and_does_not_carry_binding_or_authority() -> None:
    source = ProjectUuid.new()
    current = ProjectUuid.new()
    lineage = ProjectLineage(
        relation=LineageRelation.detached_from,
        source_project_uuid=source,
        source_revision=SourceMemoryRevision("1" * 64),
        visibility=LineageVisibility.private,
    )
    identity = ProjectIdentity(
        project_uuid=current,
        display_name="Detached",
        mode=ProjectMode.detached,
        replica_id=ReplicaId.new(),
        lineage=(lineage,),
    )
    serialized = identity.to_dict()

    assert serialized["remote_binding"] is None
    assert set(serialized["lineage"][0]) == {
        "relation",
        "source_project_uuid",
        "source_revision",
        "visibility",
    }
    assert "authority" not in yaml.safe_dump(serialized).lower()

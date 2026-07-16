from __future__ import annotations

import hashlib
import multiprocessing
import socket
from pathlib import Path

import pytest
import yaml

from p2p_engine.services.candidate_workspace import CandidateWorkspaceView
from p2p_engine.services.workspace_compatibility import WorkspaceCompatibilityService
from p2p_engine.services.workspace_migrations import WorkspaceMigrationService
from p2p_engine.services.workspace_schema import WorkspaceSchemaService
from p2p_engine.services.workspace_transactions import MigrationLockService
from p2p_engine.storage.filesystem import P2PWorkspace


class SimulatedCrash(BaseException):
    pass


def _concurrent_apply_worker(
    root_text: str,
    plan_fingerprint: str,
    start_event,
    results,
) -> None:
    root = Path(root_text)
    schema = WorkspaceSchemaService(root=root, p2p_dir=root / ".p2p", engine_version="0.2.0")
    compatibility = WorkspaceCompatibilityService(
        root=root,
        p2p_dir=root / ".p2p",
        schema_service=schema,
        engine_version="0.2.0",
    )
    migration = WorkspaceMigrationService(
        root=root,
        p2p_dir=root / ".p2p",
        compatibility=compatibility,
        schema_service=schema,
    )
    start_event.wait(timeout=10)
    result = migration.apply(
        target_version=1,
        owner_inputs={"metadata": {"workflow_phase": "delivery"}},
        plan_fingerprint=plan_fingerprint,
        actor="davide",
        confirm=True,
    )
    results.put(result.status)


def _legacy_services(
    root: Path,
    *,
    failure_injector=None,
) -> tuple[P2PWorkspace, WorkspaceCompatibilityService, WorkspaceMigrationService]:
    workspace = P2PWorkspace(root)
    workspace.init_project("Legacy", owner="Davide")
    (root / ".p2p" / "project" / "workspace-schema.yml").unlink()
    schema = WorkspaceSchemaService(root=root, p2p_dir=root / ".p2p", engine_version="0.2.0")
    compatibility = WorkspaceCompatibilityService(
        root=root,
        p2p_dir=root / ".p2p",
        schema_service=schema,
        engine_version="0.2.0",
    )
    lock = MigrationLockService(root=root, p2p_dir=root / ".p2p")
    migration = WorkspaceMigrationService(
        root=root,
        p2p_dir=root / ".p2p",
        compatibility=compatibility,
        schema_service=schema,
        lock_service=lock,
        failure_injector=failure_injector,
        clock=lambda: "2026-07-15T12:00:00Z",
    )
    return workspace, compatibility, migration


def _workspace_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == ".p2p/.internal" or relative.startswith(".p2p/.internal/"):
            continue
        digest.update(relative.encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_migration_apply_commits_schema_last_and_is_idempotent(tmp_path: Path) -> None:
    stages: list[tuple[str, str]] = []
    _, compatibility, migration = _legacy_services(
        tmp_path,
        failure_injector=lambda stage, target: stages.append((stage, target)),
    )
    plan = compatibility.plan(1, {"metadata": {"workflow_phase": "delivery"}})

    result = migration.apply(
        target_version=1,
        owner_inputs={"metadata": {"workflow_phase": "delivery"}},
        plan_fingerprint=plan.fingerprint_sha256,
        actor="davide",
        confirm=True,
    )
    second = migration.apply(
        target_version=1,
        owner_inputs={"metadata": {"workflow_phase": "delivery"}},
        plan_fingerprint=plan.fingerprint_sha256,
        actor="davide",
        confirm=True,
    )

    assert result.status == "applied"
    assert result.changed_paths[-1] == ".p2p/project/workspace-schema.yml"
    replace_targets = [target for stage, target in stages if stage == "before_replace"]
    assert replace_targets[-1] == ".p2p/project/workspace-schema.yml"
    assert second.status == "no_op"
    assert migration.schema_service.status().state == "upgrade_available"
    assert migration.recovery_status().required is False
    assert not migration.lock_service.lock_path.exists()
    assert not migration.lock_service.transactions_root.exists()


def test_apply_rejects_missing_changed_or_omitted_input_before_lock(tmp_path: Path) -> None:
    _, compatibility, migration = _legacy_services(tmp_path)
    owner_inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, owner_inputs)
    before = _workspace_hash(tmp_path)

    stale = migration.apply(
        target_version=1,
        owner_inputs={"metadata": {"workflow_phase": "planning"}},
        plan_fingerprint=plan.fingerprint_sha256,
        actor="davide",
        confirm=True,
    )
    omitted = migration.apply(
        target_version=1,
        owner_inputs=None,
        plan_fingerprint=plan.fingerprint_sha256,
        actor="davide",
        confirm=True,
    )

    assert stale.status == "stale_plan"
    assert omitted.status == "stale_plan"
    assert _workspace_hash(tmp_path) == before
    assert not migration.lock_service.lock_path.exists()


@pytest.mark.parametrize(
    "failed_target",
    (".p2p/project.yml", ".p2p/project/workspace-schema.yml"),
)
def test_failure_after_each_replacement_rolls_back_exact_original_bytes(
    tmp_path: Path,
    failed_target: str,
) -> None:
    def fail(stage: str, target: str) -> None:
        if stage == "after_replace" and target == failed_target:
            raise RuntimeError("injected replacement failure")

    _, compatibility, migration = _legacy_services(tmp_path, failure_injector=fail)
    project_path = tmp_path / ".p2p" / "project.yml"
    original = project_path.read_bytes()
    original_mode = project_path.stat().st_mode & 0o777
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, inputs)

    result = migration.apply(
        target_version=1,
        owner_inputs=inputs,
        plan_fingerprint=plan.fingerprint_sha256,
        actor="davide",
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert project_path.read_bytes() == original
    assert project_path.stat().st_mode & 0o777 == original_mode
    assert not (tmp_path / ".p2p" / "project" / "workspace-schema.yml").exists()
    assert migration.recovery_status().required is False


@pytest.mark.parametrize("failed_stage", ("before_staging", "before_candidate_validation"))
def test_precommit_failures_leave_no_transaction_or_workspace_change(
    tmp_path: Path,
    failed_stage: str,
) -> None:
    def fail(stage: str, target: str) -> None:
        if stage == failed_stage:
            raise RuntimeError(f"injected {failed_stage} failure")

    _, compatibility, migration = _legacy_services(tmp_path, failure_injector=fail)
    before = _workspace_hash(tmp_path)
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, inputs)

    result = migration.apply(
        target_version=1,
        owner_inputs=inputs,
        plan_fingerprint=plan.fingerprint_sha256,
        actor="davide",
        confirm=True,
    )

    assert result.status == "stage_failed"
    assert _workspace_hash(tmp_path) == before
    assert migration.recovery_status().required is False
    assert not migration.lock_service.lock_path.exists()
    assert not migration.lock_service.transactions_root.exists()


def test_crash_leaves_recovery_state_and_explicit_rollback_cleans_it(tmp_path: Path) -> None:
    def crash(stage: str, target: str) -> None:
        if stage == "after_replace" and target == ".p2p/project.yml":
            raise SimulatedCrash()

    _, compatibility, migration = _legacy_services(tmp_path, failure_injector=crash)
    project_path = tmp_path / ".p2p" / "project.yml"
    original = project_path.read_bytes()
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, inputs)

    with pytest.raises(SimulatedCrash):
        migration.apply(
            target_version=1,
            owner_inputs=inputs,
            plan_fingerprint=plan.fingerprint_sha256,
            actor="davide",
            confirm=True,
        )

    recovery = migration.recovery_status()
    assert recovery.required is True
    assert recovery.journal_state == "committing"
    rollback = migration.rollback(
        transaction_id=recovery.transaction_id,
        actor="davide",
        confirm=True,
    )
    assert rollback.status == "rolled_back"
    assert project_path.read_bytes() == original
    assert migration.recovery_status().required is False


def test_rollback_preserves_external_edit_and_keeps_recovery_evidence(tmp_path: Path) -> None:
    project_path = tmp_path / ".p2p" / "project.yml"

    def edit_then_fail(stage: str, target: str) -> None:
        if stage == "after_replace" and target == ".p2p/project.yml":
            project_path.write_text("external edit\n", encoding="utf-8")
            raise RuntimeError("non-cooperating writer")

    _, compatibility, migration = _legacy_services(tmp_path, failure_injector=edit_then_fail)
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, inputs)

    result = migration.apply(
        target_version=1,
        owner_inputs=inputs,
        plan_fingerprint=plan.fingerprint_sha256,
        actor="davide",
        confirm=True,
    )

    assert result.status == "recovery_required"
    assert result.recovery_required is True
    assert project_path.read_text(encoding="utf-8") == "external edit\n"
    assert migration.recovery_status().required is True


def test_lock_blocks_other_migration_and_common_governed_write(tmp_path: Path) -> None:
    workspace, _, migration = _legacy_services(tmp_path)
    runtime = workspace.runtime_status()
    runtime_preview = workspace.runtime_contract_update_preview(
        requires=runtime.requires or "==0.1.9",
        recommended=runtime.recommended or "0.1.9",
        actor="davide",
    )
    lock = migration.lock_service.acquire("migration-test", owner="davide")
    assert lock.state == "active"

    blocked_writes = (
        lambda: workspace.create_proposal("Blocked"),
        workspace.refresh_project_state,
        lambda: workspace.runtime_contract_update_apply(
            requires=runtime.requires or "==0.1.9",
            recommended=runtime.recommended or "0.1.9",
            expected_state_token=runtime_preview.expected_state_token or "",
            actor="davide",
            confirm=True,
        ),
        lambda: workspace.next_action_add(
            kind="blocked",
            target="workspace",
            reason="Must not write during migration.",
        ),
        workspace.prepare_project_publication,
    )
    for write in blocked_writes:
        with pytest.raises(ValueError, match="GOVERNED_WRITE_BLOCKED_BY_MIGRATION"):
            write()
    with pytest.raises(ValueError, match="MIGRATION_LOCKED"):
        migration.lock_service.acquire("migration-other", owner="davide")

    assert workspace.workspace_schema_status().recovery["required"] is True
    blocked_plan = workspace.workspace_migration_plan(1)
    assert blocked_plan.status == "blocked"
    assert any(
        finding.code == "P2P337_WORKSPACE_MIGRATION_RECOVERY_REQUIRED"
        for finding in blocked_plan.findings
    )
    assert workspace.context_packet().current_state["workspace_schema"]["recovery_required"] is True

    migration.lock_service.release("migration-test")


def test_candidate_view_never_falls_back_for_owned_target(tmp_path: Path) -> None:
    view = CandidateWorkspaceView(
        root=tmp_path,
        candidates={".p2p/project.yml": b"project: {id: candidate}\n"},
        preserved={".p2p/project.yml": b"project: {id: live}\n"},
        owned_paths={".p2p/project.yml", ".p2p/project/domain.yml"},
    )

    assert view.read_yaml_mapping(".p2p/project.yml")["project"] == {"id": "candidate"}
    with pytest.raises(FileNotFoundError):
        view.read_bytes(".p2p/project/domain.yml")
    with pytest.raises(ValueError, match="did not read candidate"):
        view.assert_owned_reads_used_candidates()


def test_candidate_and_transaction_paths_reject_escape_and_symlink(tmp_path: Path) -> None:
    _, _, migration = _legacy_services(tmp_path)
    with pytest.raises(ValueError, match="outside governed"):
        CandidateWorkspaceView(
            root=tmp_path,
            candidates={"../escape": b"x"},
            preserved={},
        )
    target = tmp_path / ".p2p" / "project" / "linked.yml"
    target.symlink_to(tmp_path / "outside.yml")
    with pytest.raises(ValueError, match="symlink"):
        migration.filesystem.target_path(".p2p/project/linked.yml")


def test_two_processes_cannot_commit_the_same_migration_concurrently(tmp_path: Path) -> None:
    _, compatibility, migration = _legacy_services(tmp_path)
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, inputs)
    context = multiprocessing.get_context("fork")
    start_event = context.Event()
    results = context.Queue()
    processes = [
        context.Process(
            target=_concurrent_apply_worker,
            args=(str(tmp_path), plan.fingerprint_sha256, start_event, results),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    start_event.set()
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0

    statuses = sorted(results.get(timeout=2) for _ in processes)
    assert statuses.count("applied") == 1
    assert set(statuses) <= {"applied", "blocked", "no_op", "stale_plan"}
    state = migration.schema_service.read_state()
    assert len(state.applied_migrations) == 1
    assert migration.recovery_status().required is False


def test_resume_after_crash_at_staged_journal_commits_exact_candidates(tmp_path: Path) -> None:
    def crash(stage: str, target: str) -> None:
        if stage == "after_journal":
            raise SimulatedCrash()

    _, compatibility, migration = _legacy_services(tmp_path, failure_injector=crash)
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, inputs)
    with pytest.raises(SimulatedCrash):
        migration.apply(
            target_version=1,
            owner_inputs=inputs,
            plan_fingerprint=plan.fingerprint_sha256,
            actor="davide",
            confirm=True,
        )

    recovery = migration.recovery_status()
    resumed = migration.resume(
        transaction_id=recovery.transaction_id,
        actor="davide",
        confirm=True,
    )

    assert resumed.status == "applied"
    assert migration.schema_service.status().state == "upgrade_available"
    assert migration.recovery_status().required is False
    assert not migration.lock_service.transactions_root.exists()


@pytest.mark.parametrize(
    ("crash_stage", "crash_target"),
    (
        ("after_replace", ".p2p/project.yml"),
        ("after_replace", ".p2p/project/workspace-schema.yml"),
        ("before_lock_cleanup", ""),
    ),
)
def test_resume_after_crash_at_every_commit_boundary(
    tmp_path: Path,
    crash_stage: str,
    crash_target: str,
) -> None:
    def crash(stage: str, target: str) -> None:
        if stage == crash_stage and target == crash_target:
            raise SimulatedCrash()

    _, compatibility, migration = _legacy_services(tmp_path, failure_injector=crash)
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, inputs)
    with pytest.raises(SimulatedCrash):
        migration.apply(
            target_version=1,
            owner_inputs=inputs,
            plan_fingerprint=plan.fingerprint_sha256,
            actor="davide",
            confirm=True,
        )

    recovery = migration.recovery_status()
    resumed = migration.resume(
        transaction_id=recovery.transaction_id,
        actor="davide",
        confirm=True,
    )

    assert resumed.status == "applied"
    assert migration.schema_service.status().state == "upgrade_available"
    assert migration.recovery_status().required is False
    assert not migration.lock_service.lock_path.exists()
    assert not migration.lock_service.transactions_root.exists()


def test_migration_is_repository_and_network_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_network(*args, **kwargs):
        raise AssertionError("Migration attempted network access")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    _, compatibility, migration = _legacy_services(tmp_path)
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, inputs)

    result = migration.apply(
        target_version=1,
        owner_inputs=inputs,
        plan_fingerprint=plan.fingerprint_sha256,
        actor="davide",
        confirm=True,
    )

    assert result.status == "applied"
    assert plan.advisory_checkpoint == "Create a repository checkpoint before apply."
    assert not (tmp_path / ".git").exists()


def test_recovery_requires_current_owner_or_original_actor_when_permissions_are_absent(
    tmp_path: Path,
) -> None:
    def crash(stage: str, target: str) -> None:
        if stage == "after_journal":
            raise SimulatedCrash()

    _, compatibility, migration = _legacy_services(tmp_path, failure_injector=crash)
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, inputs)
    with pytest.raises(SimulatedCrash):
        migration.apply(
            target_version=1,
            owner_inputs=inputs,
            plan_fingerprint=plan.fingerprint_sha256,
            actor="davide",
            confirm=True,
        )

    recovery = migration.recovery_status()
    blocked = migration.resume(
        transaction_id=recovery.transaction_id,
        actor="contributor",
        confirm=True,
    )

    assert blocked.status == "blocked"
    assert blocked.recovery_required is True
    assert migration.recovery_status().required is True


def test_owner_confirmed_recovery_removes_stale_lock_without_journal(tmp_path: Path) -> None:
    _, _, migration = _legacy_services(tmp_path)
    lock_path = migration.lock_service.lock_path
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        yaml.safe_dump(
            {
                "transaction_id": "migration-stale",
                "pid": 999_999_999,
                "acquired_at": "2026-07-15T12:00:00Z",
                "owner": "owner",
            }
        ),
        encoding="utf-8",
    )

    recovery = migration.recovery_status()
    result = migration.rollback(
        transaction_id="migration-stale",
        actor="davide",
        confirm=True,
    )

    assert recovery.lock.state == "stale"
    assert result.status == "rolled_back"
    assert not lock_path.exists()
    assert migration.recovery_status().required is False


def test_external_edit_to_not_yet_replaced_target_is_preserved(tmp_path: Path) -> None:
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"

    def edit_before_replace(stage: str, target: str) -> None:
        if stage == "before_replace" and target == ".p2p/project/workspace-schema.yml":
            schema_path.write_text("external: schema\n", encoding="utf-8")

    _, compatibility, migration = _legacy_services(
        tmp_path,
        failure_injector=edit_before_replace,
    )
    project_path = tmp_path / ".p2p" / "project.yml"
    original_project = project_path.read_bytes()
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plan = compatibility.plan(1, inputs)

    result = migration.apply(
        target_version=1,
        owner_inputs=inputs,
        plan_fingerprint=plan.fingerprint_sha256,
        actor="davide",
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert project_path.read_bytes() == original_project
    assert schema_path.read_text(encoding="utf-8") == "external: schema\n"
    assert migration.recovery_status().required is False


def test_semantic_plan_hash_is_stable_across_apply_dates_but_physical_hash_changes(
    tmp_path: Path,
) -> None:
    roots = [tmp_path / "first", tmp_path / "second"]
    services = []
    for root, timestamp in zip(
        roots,
        ("2026-07-15T12:00:00Z", "2026-07-16T12:00:00Z"),
        strict=True,
    ):
        _, compatibility, migration = _legacy_services(root)
        migration.clock = lambda value=timestamp: value
        services.append((compatibility, migration))
    inputs = {"metadata": {"workflow_phase": "delivery"}}
    plans = [compatibility.plan(1, inputs) for compatibility, _ in services]
    results = [
        migration.apply(
            target_version=1,
            owner_inputs=inputs,
            plan_fingerprint=plan.fingerprint_sha256,
            actor="davide",
            confirm=True,
        )
        for plan, (_, migration) in zip(plans, services, strict=True)
    ]

    assert plans[0].fingerprint_sha256 == plans[1].fingerprint_sha256
    assert results[0].semantic_hashes == results[1].semantic_hashes
    assert results[0].physical_hashes[".p2p/project/workspace-schema.yml"] != results[1].physical_hashes[
        ".p2p/project/workspace-schema.yml"
    ]

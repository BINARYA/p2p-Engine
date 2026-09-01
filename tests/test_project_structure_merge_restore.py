from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.authority import AuthorityContext
from p2p_engine.core.project_memory import ProjectMemoryScopeKind
from p2p_engine.core.project_structure_merge_restore import (
    PROJECT_STRUCTURE_MERGE_CAPABILITY,
    PROJECT_STRUCTURE_RESTORE_CAPABILITY,
    STRUCTURE_MERGE_PLAN_CONTRACT,
    STRUCTURE_RESTORE_PLAN_CONTRACT,
    STRUCTURE_SNAPSHOT_RETENTION_LIMIT,
    RetainedStructureLedger,
    RetainedStructureSnapshot,
    StructureCollisionDecision,
    StructureMergePlan,
    StructurePlacement,
    StructureRestorePlan,
)
from p2p_engine.core.project_structure_retirement import StructureRetirementDisposition
from p2p_engine.mcp.registry import TOOL_NAMES
from p2p_engine.mcp.tools import call_tool
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data
from tests.test_project_structure_replacement import (
    _add_section,
    _external_context,
    _pack,
    _workspace,
)

runner = CliRunner()


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _source_and_plan(tmp_path: Path):
    workspace = _workspace(tmp_path / "project")
    source_dir = tmp_path / "source"
    _pack(source_dir)
    source_archive = tmp_path / "source.p2pv"
    workspace.package_portable_vertical(source_dir, output=source_archive)
    comparison = workspace.compare_project_structure_merge(
        source=str(source_archive),
        selected=[{"kind": "section", "id": "target_scope"}],
    )
    refs = (*comparison.selected, *comparison.dependency_closure)
    plan = StructureMergePlan(
        source=comparison.source,
        expected_target_revision=workspace.project_structure().revision,
        expected_target_checksum=workspace.project_structure().checksum,
        expected_memory_revision=workspace.project_memory_revision(),
        selected=comparison.selected,
        dependency_closure=comparison.dependency_closure,
        placements=tuple(
            StructurePlacement(
                identity=ref.identity,
                parent_id=(
                    "target_scope" if ref.kind in {"field", "question", "criterion"} else "root"
                ),
                order=0,
            )
            for ref in refs
        ),
        collisions=(),
    )
    return workspace, source_archive, comparison, plan


def _plan_path(path: Path, root_key: str, plan: object) -> Path:
    path.write_text(
        yaml.safe_dump({root_key: plan.to_dict()}, sort_keys=False),  # type: ignore[attr-defined]
        encoding="utf-8",
    )
    return path


@pytest.mark.service
@pytest.mark.smoke
def test_merge_and_restore_are_forward_atomic_and_idempotent(tmp_path: Path) -> None:
    workspace, source, comparison, plan = _source_and_plan(tmp_path)
    before = workspace.project_structure()
    preview = workspace.preview_project_structure_merge(
        source=str(source),
        plan=plan,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )

    assert preview.apply_allowed is True
    assert preview.source == comparison.source
    assert preview.candidate is not None
    assert preview.candidate.revision == before.revision + 1
    assert preview.readiness_projection["status"] == "projected"
    assert ".p2p/" not in str(preview.to_dict())

    result = workspace.apply_project_structure_merge(
        source=str(source),
        plan=plan,
        preview_token=preview.preview_token,
        operation_key="structure-merge-apply-0001",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    replay = workspace.apply_project_structure_merge(
        source=str(source),
        plan=plan,
        preview_token=preview.preview_token,
        operation_key="structure-merge-apply-0001",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )

    assert result.status == "applied"
    assert replay.status == "already_applied"
    assert result.current.revision == before.revision + 1
    assert result.current.structure_id == before.structure_id
    assert result.event["event_type"] == "structure_merged"
    assert result.event["authority"]["claims"][0]["capability"] == (
        PROJECT_STRUCTURE_MERGE_CAPABILITY
    )
    assert result.to_dict()["active_release_subscription"] is False
    assert ".p2p/" not in str(result.to_dict())

    retained = workspace.inspect_retained_project_structure_revision(revision=before.revision)[
        "snapshot"
    ]
    current = workspace.project_structure()
    restore_plan = StructureRestorePlan(
        source_revision=before.revision,
        source_checksum=str(retained["checksum"]),
        expected_target_revision=current.revision,
        expected_target_checksum=current.checksum,
        expected_memory_revision=workspace.project_memory_revision(),
    )
    restore_preview = workspace.preview_project_structure_restore(
        plan=restore_plan,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    restored = workspace.apply_project_structure_restore(
        plan=restore_plan,
        preview_token=restore_preview.preview_token,
        operation_key="structure-restore-apply-0001",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )

    assert restored.current.revision == current.revision + 1
    assert restored.current.checksum == before.checksum
    assert restored.event["event_type"] == "structure_restored"
    assert restored.event["authority"]["claims"][0]["capability"] == (
        PROJECT_STRUCTURE_RESTORE_CAPABILITY
    )
    assert workspace.project_identity().project_uuid == workspace.project_identity().project_uuid


@pytest.mark.service
def test_restore_reuses_impact_dispositions_and_updates_classification(
    tmp_path: Path,
) -> None:
    workspace, source, _comparison, plan = _source_and_plan(tmp_path)
    merge_preview = workspace.preview_project_structure_merge(
        source=str(source),
        plan=plan,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    workspace.apply_project_structure_merge(
        source=str(source),
        plan=plan,
        preview_token=merge_preview.preview_token,
        operation_key="restore-impact-merge-seed",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    proposal = workspace.create_proposal("Restore scoped memory")
    workspace.assign_proposal_memory_scope(
        proposal_id=proposal.proposal_id,
        kind="sections",
        section_ids=["target_scope"],
        operation_key="restore-impact-scope-seed",
        expected_memory_revision=workspace.project_memory_revision(),
        expected_structure_revision=workspace.project_structure().revision,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    retained = workspace.inspect_retained_project_structure_revision(revision=1)["snapshot"]
    current = workspace.project_structure()
    incomplete = StructureRestorePlan(
        source_revision=1,
        source_checksum=str(retained["checksum"]),
        expected_target_revision=current.revision,
        expected_target_checksum=current.checksum,
        expected_memory_revision=workspace.project_memory_revision(),
    )
    blocked = workspace.preview_project_structure_restore(
        plan=incomplete,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    assert "P2P_STRUCTURE_REPLACEMENT_DISPOSITION_REQUIRED" in blocked.blockers
    assert blocked.required_dispositions

    disposition = StructureRetirementDisposition(
        disposition_id=f"proposal:{proposal.proposal_id}:scope",
        action="project_global",
        reason="Keep the proposal active after restoring the empty structure.",
    )
    complete = replace(incomplete, dispositions=(disposition,))
    preview = workspace.preview_project_structure_restore(
        plan=complete,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    result = workspace.apply_project_structure_restore(
        plan=complete,
        preview_token=preview.preview_token,
        operation_key="restore-impact-apply",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )

    assert result.current.revision == current.revision + 1
    assert workspace.proposal_memory_scope(proposal.proposal_id).kind == (
        ProjectMemoryScopeKind.project_global
    )
    assert workspace.project_memory_classification().structure_revision == (
        result.current.revision
    )


@pytest.mark.service
def test_merge_requires_exact_closure_placements_and_collision_decisions(
    tmp_path: Path,
) -> None:
    workspace, source, comparison, plan = _source_and_plan(tmp_path)
    incomplete = replace(plan, dependency_closure=())
    blocked = workspace.preview_project_structure_merge(
        source=str(source),
        plan=incomplete,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    assert "P2P_STRUCTURE_MERGE_DEPENDENCY_CLOSURE_MISMATCH" in blocked.blockers
    assert blocked.preview_token == ""

    workspace.apply_project_structure_merge(
        source=str(source),
        plan=plan,
        preview_token=workspace.preview_project_structure_merge(
            source=str(source),
            plan=plan,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
        ).preview_token,
        operation_key="structure-collision-seed-0001",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    collision = workspace.compare_project_structure_merge(
        source=str(source), selected=comparison.selected
    )
    current = workspace.project_structure()
    missing_decisions = replace(
        plan,
        expected_target_revision=current.revision,
        expected_target_checksum=current.checksum,
        expected_memory_revision=workspace.project_memory_revision(),
    )
    blocked_collision = workspace.preview_project_structure_merge(
        source=str(source),
        plan=missing_decisions,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    assert collision.collisions
    assert "P2P_STRUCTURE_MERGE_COLLISION_PLAN_INCOMPLETE" in (blocked_collision.blockers)


@pytest.mark.service
def test_collision_actions_are_explicit_and_import_as_new_id_is_typed(
    tmp_path: Path,
) -> None:
    workspace, source, comparison, plan = _source_and_plan(tmp_path)
    seed = workspace.preview_project_structure_merge(
        source=str(source),
        plan=plan,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    workspace.apply_project_structure_merge(
        source=str(source),
        plan=plan,
        preview_token=seed.preview_token,
        operation_key="structure-collision-actions-seed",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )

    collision = workspace.compare_project_structure_merge(
        source=str(source), selected=comparison.selected
    )
    refs = (*collision.selected, *collision.dependency_closure)
    current = workspace.project_structure()
    keep = StructureMergePlan(
        source=collision.source,
        expected_target_revision=current.revision,
        expected_target_checksum=current.checksum,
        expected_memory_revision=workspace.project_memory_revision(),
        selected=collision.selected,
        dependency_closure=collision.dependency_closure,
        placements=tuple(
            StructurePlacement(
                identity=ref.identity,
                parent_id=(
                    "target_scope"
                    if ref.kind in {"field", "question", "criterion"}
                    else "root"
                ),
                order=0,
            )
            for ref in refs
        ),
        collisions=tuple(
            StructureCollisionDecision(
                identity=str(item["identity"]), action="keep-current"
            )
            for item in collision.collisions
        ),
    )
    no_op = workspace.preview_project_structure_merge(
        source=str(source),
        plan=keep,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    assert "P2P_STRUCTURE_MERGE_NO_CHANGE" in no_op.blockers
    assert "P2P_STRUCTURE_MERGE_COLLISION_PLAN_INCOMPLETE" not in no_op.blockers

    copied_section = "target_scope_copy"
    import_copy = replace(
        keep,
        placements=tuple(
            StructurePlacement(
                identity=ref.identity,
                parent_id=(
                    copied_section
                    if ref.kind in {"field", "question", "criterion"}
                    else "root"
                ),
                order=1,
            )
            for ref in refs
        ),
        collisions=tuple(
            StructureCollisionDecision(
                identity=ref.identity,
                action="import-as-new-id",
                new_id=(
                    copied_section
                    if ref.kind == "section"
                    else f"copy_{ref.element_id}"
                ),
            )
            for ref in refs
        ),
    )
    copy_preview = workspace.preview_project_structure_merge(
        source=str(source),
        plan=import_copy,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    assert copy_preview.apply_allowed is True
    assert copy_preview.candidate is not None
    assert copied_section in copy_preview.candidate.active_section_ids()

    changed_dir = tmp_path / "changed-source"
    _pack(changed_dir, section_title="Changed Target Scope", version="2.0.0")
    changed_source = tmp_path / "changed-source.p2pv"
    workspace.package_portable_vertical(changed_dir, output=changed_source)
    changed = workspace.compare_project_structure_merge(
        source=str(changed_source), selected=comparison.selected
    )
    changed_refs = (*changed.selected, *changed.dependency_closure)
    replace_plan = StructureMergePlan(
        source=changed.source,
        expected_target_revision=current.revision,
        expected_target_checksum=current.checksum,
        expected_memory_revision=workspace.project_memory_revision(),
        selected=changed.selected,
        dependency_closure=changed.dependency_closure,
        placements=tuple(
            StructurePlacement(
                identity=ref.identity,
                parent_id=(
                    "target_scope"
                    if ref.kind in {"field", "question", "criterion"}
                    else "root"
                ),
                order=0,
            )
            for ref in changed_refs
        ),
        collisions=tuple(
            StructureCollisionDecision(
                identity=str(item["identity"]), action="replace-with-impact"
            )
            for item in changed.collisions
        ),
    )
    replace_preview = workspace.preview_project_structure_merge(
        source=str(changed_source),
        plan=replace_plan,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    assert replace_preview.apply_allowed is True
    assert replace_preview.candidate is not None
    assert replace_preview.candidate.sections[0].title == "Changed Target Scope"


@pytest.mark.service
def test_merge_accepts_exact_canonical_bundle_source(tmp_path: Path) -> None:
    source_workspace = _workspace(tmp_path / "source-project")
    _add_section(source_workspace, title="Bundle Scope", key="bundle-source-section")
    source_structure = source_workspace.project_structure()
    selected_id = source_structure.active_section_ids()[0]
    bundle = tmp_path / "source.p2pbundle"
    source_workspace.canonical_bundle_export(bundle)

    target = _workspace(tmp_path / "target-project")
    comparison = target.compare_project_structure_merge(
        source=str(bundle), selected=[{"kind": "section", "id": selected_id}]
    )
    refs = (*comparison.selected, *comparison.dependency_closure)
    plan = StructureMergePlan(
        source=comparison.source,
        expected_target_revision=target.project_structure().revision,
        expected_target_checksum=target.project_structure().checksum,
        expected_memory_revision=target.project_memory_revision(),
        selected=comparison.selected,
        dependency_closure=comparison.dependency_closure,
        placements=tuple(
            StructurePlacement(
                identity=ref.identity,
                parent_id=(selected_id if ref.kind != "section" else "root"),
                order=0,
            )
            for ref in refs
        ),
        collisions=(),
    )
    preview = target.preview_project_structure_merge(
        source=str(bundle),
        plan=plan,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )

    assert comparison.source.kind == "bundle"
    assert preview.apply_allowed is True
    assert preview.source.digest == comparison.source.digest
    assert str(bundle) not in str(preview.to_dict())


@pytest.mark.service
def test_retention_prunes_deterministically_and_missing_revision_fails_closed(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path / "project")
    base = workspace.project_structure()
    ledger = RetainedStructureLedger(structure_id=base.structure_id)
    for revision in range(1, STRUCTURE_SNAPSHOT_RETENTION_LIMIT + 2):
        ledger = ledger.retain(
            RetainedStructureSnapshot(
                structure=replace(base, revision=revision),
                retained_at="2026-09-01T00:00:00Z",
                retained_by="owner",
                reason="retention-test",
            )
        )

    assert len(ledger.snapshots) == STRUCTURE_SNAPSHOT_RETENTION_LIMIT
    assert ledger.snapshots[0].revision == 2
    with pytest.raises(ValueError, match="unavailable or has been pruned"):
        ledger.resolve(1)


@pytest.mark.service
def test_merge_failure_rolls_back_structure_snapshot_and_receipt(tmp_path: Path) -> None:
    workspace, source, _comparison, plan = _source_and_plan(tmp_path)
    preview = workspace.preview_project_structure_merge(
        source=str(source),
        plan=plan,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    before = {
        path.relative_to(workspace.root).as_posix(): path.read_bytes()
        for path in workspace.root.rglob("*")
        if path.is_file()
    }

    def fail(stage: str, _target: str) -> None:
        if stage == "before_journal":
            raise RuntimeError("injected merge failure")

    workspace._project_structure_merge_restore_service().atomic_writer = AtomicMutationWriter(
        root=workspace.root,
        p2p_dir=workspace.p2p_dir,
        failure_injector=fail,
    )
    with pytest.raises(ValueError, match="P2P_STRUCTURE_TRANSITION_MUTATION_FAILED"):
        workspace.apply_project_structure_merge(
            source=str(source),
            plan=plan,
            preview_token=preview.preview_token,
            operation_key="structure-merge-failure-0001",
            confirm=True,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
        )

    after = {
        path.relative_to(workspace.root).as_posix(): path.read_bytes()
        for path in workspace.root.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert (
        workspace.mutation_status(idempotency_key="structure-merge-failure-0001").state
        == "not_found"
    )


@pytest.mark.service
def test_transition_rejects_expired_preview_and_concurrent_target_drift(
    tmp_path: Path,
) -> None:
    workspace, source, _comparison, plan = _source_and_plan(tmp_path / "expired")
    service = workspace._project_structure_merge_restore_service()
    service.clock = lambda: "2026-09-01T10:00:00Z"
    expired = workspace.preview_project_structure_merge(
        source=str(source),
        plan=plan,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    service.clock = lambda: "2026-09-01T10:15:01Z"
    with pytest.raises(ValueError, match="P2P_STRUCTURE_TRANSITION_PREVIEW_EXPIRED"):
        workspace.apply_project_structure_merge(
            source=str(source),
            plan=plan,
            preview_token=expired.preview_token,
            operation_key="structure-expired-preview-0001",
            confirm=True,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
        )

    workspace2, source2, _comparison2, plan2 = _source_and_plan(tmp_path / "drift")
    preview = workspace2.preview_project_structure_merge(
        source=str(source2),
        plan=plan2,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    _add_section(workspace2, title="Concurrent Change", key="concurrent-target-change")
    with pytest.raises(ValueError, match="P2P_STRUCTURE_TRANSITION_PREVIEW_MISMATCH"):
        workspace2.apply_project_structure_merge(
            source=str(source2),
            plan=plan2,
            preview_token=preview.preview_token,
            operation_key="structure-concurrent-preview-0001",
            confirm=True,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
        )

    workspace3, source3, _comparison3, plan3 = _source_and_plan(
        tmp_path / "source-drift"
    )
    source_preview = workspace3.preview_project_structure_merge(
        source=str(source3),
        plan=plan3,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    changed_dir = tmp_path / "source-drift" / "changed"
    _pack(changed_dir, section_title="Changed Source", version="2.0.0")
    source3.unlink()
    workspace3.package_portable_vertical(changed_dir, output=source3)
    with pytest.raises(ValueError, match="P2P_STRUCTURE_TRANSITION_PREVIEW_MISMATCH"):
        workspace3.apply_project_structure_merge(
            source=str(source3),
            plan=plan3,
            preview_token=source_preview.preview_token,
            operation_key="structure-source-drift-0001",
            confirm=True,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
        )


@pytest.mark.service
def test_merge_and_restore_require_distinct_external_capabilities(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path / "project")
    workspace.init_project(
        "Hosted Structure Transition",
        starter_id="empty",
        authority_context=_external_context("project.initialize"),
    )
    source_dir = tmp_path / "source"
    _pack(source_dir)
    source = tmp_path / "source.p2pv"
    workspace.package_portable_vertical(source_dir, output=source)
    comparison = workspace.compare_project_structure_merge(
        source=str(source), selected=[{"kind": "section", "id": "target_scope"}]
    )
    refs = (*comparison.selected, *comparison.dependency_closure)
    plan = StructureMergePlan(
        source=comparison.source,
        expected_target_revision=workspace.project_structure().revision,
        expected_target_checksum=workspace.project_structure().checksum,
        expected_memory_revision=workspace.project_memory_revision(),
        selected=comparison.selected,
        dependency_closure=comparison.dependency_closure,
        placements=tuple(
            StructurePlacement(
                identity=ref.identity,
                parent_id=(
                    "target_scope"
                    if ref.kind in {"field", "question", "criterion"}
                    else "root"
                ),
                order=0,
            )
            for ref in refs
        ),
        collisions=(),
    )
    wrong = _external_context("project.structure.edit")
    with pytest.raises(ValueError, match="P2P_CAPABILITY_MISMATCH"):
        workspace.preview_project_structure_merge(
            source=str(source),
            plan=plan,
            actor_id=wrong.subject.identity_id,
            executor_id=wrong.executor.identity_id,
            executor_kind=wrong.executor.kind.value,
            authority_context=wrong,
        )

    merge_context: AuthorityContext = _external_context(PROJECT_STRUCTURE_MERGE_CAPABILITY)
    preview = workspace.preview_project_structure_merge(
        source=str(source),
        plan=plan,
        actor_id=merge_context.subject.identity_id,
        executor_id=merge_context.executor.identity_id,
        executor_kind=merge_context.executor.kind.value,
        authority_context=merge_context,
    )
    workspace.apply_project_structure_merge(
        source=str(source),
        plan=plan,
        preview_token=preview.preview_token,
        operation_key="hosted-merge-apply-0001",
        confirm=True,
        actor_id=merge_context.subject.identity_id,
        executor_id=merge_context.executor.identity_id,
        executor_kind=merge_context.executor.kind.value,
        authority_context=merge_context,
    )
    retained = workspace.inspect_retained_project_structure_revision(revision=1)["snapshot"]
    current = workspace.project_structure()
    restore_plan = StructureRestorePlan(
        source_revision=1,
        source_checksum=str(retained["checksum"]),
        expected_target_revision=current.revision,
        expected_target_checksum=current.checksum,
        expected_memory_revision=workspace.project_memory_revision(),
    )
    with pytest.raises(ValueError, match="P2P_CAPABILITY_MISMATCH"):
        workspace.preview_project_structure_restore(
            plan=restore_plan,
            actor_id=merge_context.subject.identity_id,
            executor_id=merge_context.executor.identity_id,
            executor_kind=merge_context.executor.kind.value,
            authority_context=merge_context,
        )
    restore_context = _external_context(PROJECT_STRUCTURE_RESTORE_CAPABILITY)
    restore_preview = workspace.preview_project_structure_restore(
        plan=restore_plan,
        actor_id=restore_context.subject.identity_id,
        executor_id=restore_context.executor.identity_id,
        executor_kind=restore_context.executor.kind.value,
        authority_context=restore_context,
    )
    assert restore_preview.apply_allowed is True


@pytest.mark.mcp
def test_mcp_has_byte_invariant_reads_and_no_transition_apply(tmp_path: Path) -> None:
    workspace, source, comparison, _plan = _source_and_plan(tmp_path)
    _add_section(workspace, title="Retained Source", key="retained-inspect-seed")
    arguments = {
        "root": str(workspace.root),
        "source": str(source),
        "selected": [item.to_dict() for item in comparison.selected],
    }
    before = _snapshot(workspace.root)
    first = call_tool("p2p_project_structure_merge_compare", arguments)
    second = call_tool("p2p_project_structure_merge_compare", arguments)
    retained = call_tool(
        "p2p_project_structure_retained_inspect",
        {"root": str(workspace.root), "revision": 1},
    )
    after = _snapshot(workspace.root)

    assert first == second
    assert first["mutation_performed"] is False
    assert retained["mutation_performed"] is False
    assert before == after
    assert "p2p_project_structure_merge_apply" not in TOOL_NAMES
    assert "p2p_project_structure_restore_apply" not in TOOL_NAMES
    with pytest.raises(ValueError, match="unavailable or has been pruned"):
        call_tool(
            "p2p_project_structure_retained_inspect",
            {"root": str(workspace.root), "revision": 999},
        )


@pytest.mark.cli
def test_cli_merge_restore_and_status_use_stable_json_contracts(tmp_path: Path) -> None:
    workspace, source, _comparison, plan = _source_and_plan(tmp_path)
    merge_plan = _plan_path(
        tmp_path / "merge-plan.yml", "project_structure_merge_plan", plan
    )
    preview_result = runner.invoke(
        app,
        [
            "project",
            "structure",
            "merge",
            "preview",
            str(source),
            "--plan",
            str(merge_plan),
            "--format",
            "json",
            "--root",
            str(workspace.root),
        ],
    )
    merge_preview = cli_data(
        preview_result, operation="project.structure.merge.preview"
    )["project_structure_merge_preview"]
    applied_result = runner.invoke(
        app,
        [
            "project",
            "structure",
            "merge",
            "apply",
            str(source),
            "--plan",
            str(merge_plan),
            "--preview-token",
            str(merge_preview["preview_token"]),
            "--operation-key",
            "cli-structure-merge-0001",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(workspace.root),
        ],
    )
    applied = cli_data(applied_result, operation="project.structure.merge.apply")[
        "project_structure_merge"
    ]
    status = cli_data(
        runner.invoke(
            app,
            [
                "project",
                "structure",
                "merge",
                "status",
                "--operation-key",
                "cli-structure-merge-0001",
                "--format",
                "json",
                "--root",
                str(workspace.root),
            ],
        ),
        operation="project.structure.merge.status",
    )["mutation_status"]

    assert applied["status"] == "applied"
    assert status["state"] == "applied"
    assert ".p2p/" not in json.dumps(applied, sort_keys=True)

    retained = workspace.inspect_retained_project_structure_revision(revision=1)["snapshot"]
    current = workspace.project_structure()
    restore_plan = StructureRestorePlan(
        source_revision=1,
        source_checksum=str(retained["checksum"]),
        expected_target_revision=current.revision,
        expected_target_checksum=current.checksum,
        expected_memory_revision=workspace.project_memory_revision(),
    )
    restore_plan_path = _plan_path(
        tmp_path / "restore-plan.yml",
        "project_structure_restore_plan",
        restore_plan,
    )
    restore_preview = cli_data(
        runner.invoke(
            app,
            [
                "project",
                "structure",
                "restore",
                "preview",
                "--plan",
                str(restore_plan_path),
                "--format",
                "json",
                "--root",
                str(workspace.root),
            ],
        ),
        operation="project.structure.restore.preview",
    )["project_structure_restore_preview"]
    restored = cli_data(
        runner.invoke(
            app,
            [
                "project",
                "structure",
                "restore",
                "apply",
                "--plan",
                str(restore_plan_path),
                "--preview-token",
                str(restore_preview["preview_token"]),
                "--operation-key",
                "cli-structure-restore-0001",
                "--confirm",
                "--format",
                "json",
                "--root",
                str(workspace.root),
            ],
        ),
        operation="project.structure.restore.apply",
    )["project_structure_restore"]
    assert restored["current"]["revision"] == current.revision + 1
    assert ".p2p/" not in json.dumps(restored, sort_keys=True)


def test_plan_contracts_are_versioned() -> None:
    assert STRUCTURE_MERGE_PLAN_CONTRACT == "p2p-structure-merge-plan/v1"
    assert STRUCTURE_RESTORE_PLAN_CONTRACT == "p2p-structure-restore-plan/v1"

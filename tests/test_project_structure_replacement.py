from __future__ import annotations

from pathlib import Path

import pytest
import yaml
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
from p2p_engine.core.project_structure_replacement import (
    PROJECT_STRUCTURE_REPLACEMENT_CAPABILITY,
    PROJECT_STRUCTURE_REPLACEMENT_OPERATION,
    STRUCTURE_REPLACEMENT_PLAN_CONTRACT,
    STRUCTURE_REPLACEMENT_RESULT_CONTRACT,
)
from p2p_engine.mcp.registry import TOOL_NAMES
from p2p_engine.mcp.tools import call_tool
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.cli_assertions import cli_data


runner = CliRunner()


def _workspace(tmp_path: Path, *, starter: str = "empty", vertical_id: str = "") -> P2PWorkspace:
    workspace = P2PWorkspace(tmp_path)
    kwargs: dict[str, object] = {"owner": "owner"}
    if vertical_id:
        kwargs["vertical_id"] = vertical_id
    else:
        kwargs["starter_id"] = starter
    workspace.init_project("Structure Replacement", **kwargs)
    return workspace


def _add_section(
    workspace: P2PWorkspace,
    *,
    title: str,
    key: str,
) -> None:
    workspace.change_project_structure(
        operation="add_section",
        operation_key=key,
        expected_revision=workspace.project_structure().revision,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        request={
            "title": title,
            "description": f"{title} section.",
            "required": True,
        },
    )


def _pack(
    target: Path,
    *,
    publisher: str = "acme",
    vertical_id: str = "replacement_vertical",
    version: str = "1.0.0",
    section_id: str = "target_scope",
    section_title: str = "Target Scope",
    rubrics: bool = True,
) -> str:
    (target / "sections").mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifest": {
            "schema_version": 3,
            "publisher": publisher,
            "id": vertical_id,
            "name": "Replacement Vertical",
            "version": version,
            "license": "MIT",
            "extends": None,
            "lineage": {},
            "dependencies": [],
            "compatibility": {},
        }
    }
    vertical = {
        "vertical": {
            "schema_version": 3,
            "id": vertical_id,
            "name": "Replacement Vertical",
            "version": version,
            "description": "Local offline replacement target.",
            "extends": None,
            "questions": [
                {
                    "id": f"{section_id}_question",
                    "section_id": section_id,
                    "priority": "high",
                    "question": "What must be defined for the target scope?",
                }
            ],
            "artifacts": [
                {
                    "id": f"{section_id}_artifact",
                    "title": f"{section_title} Artifact",
                    "section_ids": [section_id],
                    "required": True,
                }
            ],
        }
    }
    section = {
        "section": {
            "id": section_id,
            "title": section_title,
            "purpose": f"{section_title} purpose.",
            "required": True,
            "priority": 10,
            "fields": [
                {
                    "id": "summary",
                    "label": "Summary",
                    "required": True,
                    "question": "What must be defined?",
                }
            ],
        }
    }
    rubric_payload = {
        "rubrics": [
            {
                "id": f"{section_id}_coverage",
                "title": f"{section_title} coverage",
                "section_id": section_id,
                "required": True,
                "keywords": ["scope"],
            }
        ]
        if rubrics
        else []
    }
    (target / "manifest.yml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    (target / "vertical.yml").write_text(yaml.safe_dump(vertical, sort_keys=False), encoding="utf-8")
    (target / "sections" / f"{section_id}.yml").write_text(yaml.safe_dump(section, sort_keys=False), encoding="utf-8")
    (target / "rubrics.yml").write_text(yaml.safe_dump(rubric_payload, sort_keys=False), encoding="utf-8")
    return f"{publisher}/{vertical_id}@{version}"


def _plan(preview, *, dispositions: list[dict[str, object]] | None = None) -> dict[str, object]:
    target = preview.target.to_dict()
    return {
        "contract": STRUCTURE_REPLACEMENT_PLAN_CONTRACT,
        "target": {
            "coordinate": target["coordinate"],
            "semantic_checksum": target["semantic_checksum"],
        },
        "dispositions": dispositions or [],
    }


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _external_context(capability: str) -> AuthorityContext:
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
        authorization_decision_id="replace-authz-01",
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
def test_replacement_applies_detached_offline_pack_and_replay_status(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path / "project")
    _add_section(workspace, title="Alpha", key="replace-alpha-add")
    target_dir = tmp_path / "pack"
    _pack(target_dir)
    package = workspace.package_portable_vertical(
        target_dir,
        output=tmp_path / "replacement.p2pv",
    )
    first = workspace.preview_project_structure_replacement(
        target=str(tmp_path / "replacement.p2pv"),
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    assert first.apply_token is None
    assert "P2P_STRUCTURE_REPLACEMENT_PLAN_REQUIRED" in first.blockers

    preview = workspace.preview_project_structure_replacement(
        target=str(tmp_path / "replacement.p2pv"),
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        plan=_plan(first),
    )
    result = workspace.apply_project_structure_replacement(
        target=str(tmp_path / "replacement.p2pv"),
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        preview_token=preview.apply_token or "",
        operation_key="replace-valid-apply-key",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        plan=_plan(preview),
    )
    replay = workspace.apply_project_structure_replacement(
        target=str(tmp_path / "replacement.p2pv"),
        expected_structure_revision=2,
        expected_memory_revision=first.previous_memory_revision,
        preview_token=preview.apply_token or "",
        operation_key="replace-valid-apply-key",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        plan=_plan(preview),
    )
    status = workspace.mutation_status(idempotency_key="replace-valid-apply-key")

    assert package.coordinate == "acme/replacement_vertical@1.0.0"
    assert preview.apply_token
    assert result.contract == STRUCTURE_REPLACEMENT_RESULT_CONTRACT
    assert result.status == "applied"
    assert replay.status == "already_applied"
    assert result.event.event_type == "structure_replaced"
    assert workspace.project_structure().origin.identity == package.coordinate
    assert workspace.project_structure().origin.checksum == package.semantic_checksum
    assert workspace.project_structure().active_section_ids() == ("target_scope",)
    assert workspace.project_structure(include_retired=True).sections[1].lifecycle == "retired"
    assert status.result["operation"] == PROJECT_STRUCTURE_REPLACEMENT_OPERATION
    assert status.result["active_release_subscription"] is False

    (target_dir / "sections" / "target_scope.yml").write_text("broken: true\n", encoding="utf-8")
    assert workspace.project_structure().active_section_ids() == ("target_scope",)


@pytest.mark.service
def test_replacement_rebases_active_memory_with_explicit_disposition(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path / "project")
    _add_section(workspace, title="Alpha", key="replace-scope-alpha")
    proposal = workspace.create_proposal("Scoped replacement")
    workspace.assign_proposal_memory_scope(
        proposal_id=proposal.proposal_id,
        kind="sections",
        section_ids=["alpha"],
        operation_key="replace-scope-assign",
        expected_memory_revision=workspace.project_memory_revision(),
        expected_structure_revision=workspace.project_structure().revision,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    target_dir = tmp_path / "pack"
    _pack(target_dir, section_id="gamma", section_title="Gamma")
    blocked = workspace.preview_project_structure_replacement(
        target=str(target_dir),
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    disposition = {
        "id": f"proposal:{proposal.proposal_id}:scope",
        "action": "reassign_sections",
        "section_ids": ["gamma"],
        "reason": "Move active proposal memory to the replacement section.",
    }
    preview = workspace.preview_project_structure_replacement(
        target=str(target_dir),
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        plan=_plan(blocked, dispositions=[disposition]),
    )
    result = workspace.apply_project_structure_replacement(
        target=str(target_dir),
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        preview_token=preview.apply_token or "",
        operation_key="replace-scope-apply-key",
        confirm=True,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        plan=_plan(preview, dispositions=[disposition]),
    )

    scope = workspace.proposal_memory_scope(proposal.proposal_id)
    classification = workspace.project_memory_classification()
    readiness = workspace.project_readiness_result()

    assert "P2P_STRUCTURE_REPLACEMENT_DISPOSITION_REQUIRED" in blocked.blockers
    assert preview.apply_token
    assert result.current_memory_revision == classification.memory_revision
    assert scope.section_ids == ("gamma",)
    assert classification.structure_revision == result.current.revision
    assert readiness.snapshot.structure_revision == result.current.revision


@pytest.mark.service
def test_replacement_blocks_colliding_ids_and_empty_targets(
    tmp_path: Path,
) -> None:
    workspace = _workspace(
        tmp_path / "project",
        vertical_id="binarya/software_project@2.0.0",
    )
    section_id = workspace.project_structure().active_section_ids()[0]
    workspace.change_project_structure(
        operation="update_metadata",
        operation_key="replace-conflict-metadata",
        expected_revision=workspace.project_structure().revision,
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        request={
            "element_kind": "section",
            "element_id": section_id,
            "title": "Changed Stable Identity",
        },
    )
    inspect = workspace.inspect_project_structure_replacement_target(
        "binarya/software_project@2.0.0"
    )
    plan = _plan(
        workspace.preview_project_structure_replacement(
            target="binarya/software_project@2.0.0",
            expected_structure_revision=workspace.project_structure().revision,
            expected_memory_revision=workspace.project_memory_revision(),
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
        )
    )
    collision = workspace.preview_project_structure_replacement(
        target="binarya/software_project@2.0.0",
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        plan=plan,
    )

    invalid_target = tmp_path / "invalid-pack"
    _pack(invalid_target, rubrics=False)
    with pytest.raises(ValueError, match="vertical.rubrics: at least one rubric is required"):
        workspace.preview_project_structure_replacement(
            target=str(invalid_target),
            expected_structure_revision=workspace.project_structure().revision,
            expected_memory_revision=workspace.project_memory_revision(),
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
        )

    assert inspect.valid is True
    assert "P2P_STRUCTURE_REPLACEMENT_ID_CONFLICT" in collision.blockers
    assert collision.apply_token is None
    assert any(item.state == "conflicting" for item in collision.elements)


@pytest.mark.service
def test_replacement_rejects_changed_source_or_target_after_preview(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path / "project")
    _add_section(workspace, title="Alpha", key="replace-stale-alpha")
    target_dir = tmp_path / "pack"
    _pack(target_dir)
    first = workspace.preview_project_structure_replacement(
        target=str(target_dir),
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    plan = _plan(first)
    preview = workspace.preview_project_structure_replacement(
        target=str(target_dir),
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        plan=plan,
    )
    _add_section(workspace, title="Beta", key="replace-stale-beta")

    with pytest.raises(ValueError, match="P2P_STRUCTURE_REPLACEMENT_STALE_STRUCTURE"):
        workspace.apply_project_structure_replacement(
            target=str(target_dir),
            expected_structure_revision=1,
            expected_memory_revision=first.previous_memory_revision,
            preview_token=preview.apply_token or "",
            operation_key="replace-stale-source-key",
            confirm=True,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
            plan=plan,
        )

    workspace2 = _workspace(tmp_path / "target-project")
    _add_section(workspace2, title="Alpha", key="replace-target-alpha")
    target2 = tmp_path / "target-pack"
    _pack(target2, section_id="one", vertical_id="changed_target")
    first2 = workspace2.preview_project_structure_replacement(
        target=str(target2),
        expected_structure_revision=workspace2.project_structure().revision,
        expected_memory_revision=workspace2.project_memory_revision(),
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    plan2 = _plan(first2)
    preview2 = workspace2.preview_project_structure_replacement(
        target=str(target2),
        expected_structure_revision=workspace2.project_structure().revision,
        expected_memory_revision=workspace2.project_memory_revision(),
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
        plan=plan2,
    )
    _pack(target2, section_id="two", vertical_id="changed_target")

    with pytest.raises(ValueError, match="P2P_STRUCTURE_REPLACEMENT_PLAN_TARGET_MISMATCH"):
        workspace2.apply_project_structure_replacement(
            target=str(target2),
            expected_structure_revision=workspace2.project_structure().revision,
            expected_memory_revision=workspace2.project_memory_revision(),
            preview_token=preview2.apply_token or "",
            operation_key="replace-stale-target-key",
            confirm=True,
            actor_id="owner",
            executor_id="owner",
            executor_kind="person",
            plan=plan2,
        )


@pytest.mark.service
def test_replacement_requires_replace_authority_not_structure_edit(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path / "project")
    workspace.init_project(
        "Hosted Replacement",
        starter_id="empty",
        authority_context=_external_context("project.initialize"),
    )
    target_dir = tmp_path / "pack"
    _pack(target_dir)
    context = _external_context("project.structure.edit")

    with pytest.raises(ValueError, match="P2P_CAPABILITY_MISMATCH"):
        workspace.preview_project_structure_replacement(
            target=str(target_dir),
            expected_structure_revision=workspace.project_structure().revision,
            expected_memory_revision=workspace.project_memory_revision(),
            actor_id=context.subject.identity_id,
            executor_id=context.executor.identity_id,
            executor_kind=context.executor.kind.value,
            authority_context=context,
        )

    correct = _external_context(PROJECT_STRUCTURE_REPLACEMENT_CAPABILITY)
    preview = workspace.preview_project_structure_replacement(
        target=str(target_dir),
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        actor_id=correct.subject.identity_id,
        executor_id=correct.executor.identity_id,
        executor_kind=correct.executor.kind.value,
        authority_context=correct,
        plan={
            "contract": STRUCTURE_REPLACEMENT_PLAN_CONTRACT,
            "target": {
                "coordinate": "acme/replacement_vertical@1.0.0",
                "semantic_checksum": workspace.inspect_project_structure_replacement_target(str(target_dir)).target.semantic_checksum,
            },
            "dispositions": [],
        },
    )
    assert preview.apply_token


@pytest.mark.mcp
def test_mcp_replacement_inspect_and_preview_are_read_only_and_apply_absent(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path / "project")
    target_dir = tmp_path / "pack"
    _pack(target_dir)
    before = _snapshot(workspace.root)
    inspection = call_tool(
        "p2p_project_structure_replacement_inspect",
        {"root": str(workspace.root), "target": str(target_dir)},
    )
    first = call_tool(
        "p2p_project_structure_replacement_preview",
        {
            "root": str(workspace.root),
            "target": str(target_dir),
            "expected_structure_revision": workspace.project_structure().revision,
            "expected_memory_revision": workspace.project_memory_revision(),
            "actor_id": "owner",
        },
    )
    target = first["project_structure_replacement_preview"]["target"]
    second = call_tool(
        "p2p_project_structure_replacement_preview",
        {
            "root": str(workspace.root),
            "target": str(target_dir),
            "expected_structure_revision": workspace.project_structure().revision,
            "expected_memory_revision": workspace.project_memory_revision(),
            "actor_id": "owner",
            "plan": {
                "contract": STRUCTURE_REPLACEMENT_PLAN_CONTRACT,
                "target": {
                    "coordinate": target["coordinate"],
                    "semantic_checksum": target["semantic_checksum"],
                },
                "dispositions": [],
            },
        },
    )

    assert inspection["mutation_performed"] is False
    assert first["mutation_performed"] is False
    assert second["mutation_performed"] is False
    assert _snapshot(workspace.root) == before
    assert second["project_structure_replacement_preview"]["apply_token"]
    assert "p2p_project_structure_replacement_apply" not in TOOL_NAMES


@pytest.mark.cli
def test_cli_replacement_preview_apply_status_contract(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path / "project")
    target_dir = tmp_path / "pack"
    _pack(target_dir)
    first = workspace.preview_project_structure_replacement(
        target=str(target_dir),
        expected_structure_revision=workspace.project_structure().revision,
        expected_memory_revision=workspace.project_memory_revision(),
        actor_id="owner",
        executor_id="owner",
        executor_kind="person",
    )
    plan_path = tmp_path / "replacement-plan.yml"
    plan_path.write_text(yaml.safe_dump(_plan(first), sort_keys=False), encoding="utf-8")
    preview_result = runner.invoke(
        app,
        [
            "project",
            "structure",
            "replace",
            "preview",
            str(target_dir),
            "--expected-structure-revision",
            str(workspace.project_structure().revision),
            "--expected-memory-revision",
            workspace.project_memory_revision(),
            "--plan",
            str(plan_path),
            "--root",
            str(workspace.root),
            "--format",
            "json",
        ],
    )
    assert preview_result.exit_code == 0, preview_result.output
    preview = cli_data(preview_result, operation="project.structure.replace.preview")[
        "project_structure_replacement_preview"
    ]
    apply_result = runner.invoke(
        app,
        [
            "project",
            "structure",
            "replace",
            "apply",
            str(target_dir),
            "--expected-structure-revision",
            str(workspace.project_structure().revision),
            "--expected-memory-revision",
            workspace.project_memory_revision(),
            "--preview-token",
            preview["apply_token"],
            "--operation-key",
            "replace-cli-key",
            "--plan",
            str(plan_path),
            "--confirm",
            "--root",
            str(workspace.root),
            "--format",
            "json",
        ],
    )
    status_result = runner.invoke(
        app,
        [
            "project",
            "structure",
            "replace",
            "status",
            "--operation-key",
            "replace-cli-key",
            "--root",
            str(workspace.root),
            "--format",
            "json",
        ],
    )

    assert apply_result.exit_code == 0, apply_result.output
    applied = cli_data(apply_result, operation="project.structure.replace.apply")[
        "project_structure_replacement"
    ]
    assert applied["contract"] == STRUCTURE_REPLACEMENT_RESULT_CONTRACT
    assert applied["operation"] == PROJECT_STRUCTURE_REPLACEMENT_OPERATION
    assert applied["active_release_subscription"] is False
    assert status_result.exit_code == 0, status_result.output
    status = cli_data(status_result, operation="project.structure.replace.status")[
        "mutation_status"
    ]
    assert status["state"] == "applied"
    assert status["operation"] == PROJECT_STRUCTURE_REPLACEMENT_OPERATION

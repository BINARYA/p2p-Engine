from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.services.workspace_compatibility import (
    WorkspaceCompatibilityService,
    normalize_owner_inputs,
)
from p2p_engine.core.workspace_schema import OP_PRESERVE_LEGACY
from p2p_engine.services.workspace_migrations import WorkspaceMigrationService
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.workspace_migration_fixtures import initialize_legacy_workspace


def _v1_workspace(root: Path, *, legacy_question: bool = True) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("V1 Project", owner="owner", vertical_id="base_project")
    questions_path = root / ".p2p" / "project" / "questions.yml"
    questions_path.unlink()
    schema_path = root / ".p2p" / "project" / "workspace-schema.yml"
    schema_payload = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    schema = schema_payload["workspace_schema"]
    schema["current_version"] = 1
    schema["baseline"] = "initialized_current"
    schema["applied_migrations"] = []
    schema_path.write_text(yaml.safe_dump(schema_payload, sort_keys=False), encoding="utf-8")
    definition_path = root / ".p2p" / "project" / "definition.yml"
    definition_payload = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
    sections = definition_payload["project_definition"]["sections"]
    for section in sections:
        section["open_questions"] = []
    if legacy_question:
        section = next(item for item in sections if item["id"] == "vision")
        section["open_questions"] = [
            {
                "id": "Q001",
                "question": "What project vision should be adopted?",
                "field_id": "summary",
                "status": "open",
            }
        ]
    definition_path.write_text(yaml.safe_dump(definition_payload, sort_keys=False), encoding="utf-8")
    return workspace


def _services(root: Path, *, failure_injector=None):
    workspace = P2PWorkspace(root)
    compatibility = workspace._workspace_compatibility_service()
    migration = workspace._workspace_migration_service()
    migration.failure_injector = failure_injector
    return compatibility, migration


def test_v1_to_v2_plan_owns_only_question_definition_schema_and_derived_state(tmp_path: Path) -> None:
    _v1_workspace(tmp_path)
    compatibility, _ = _services(tmp_path)

    plan = compatibility.plan(2)

    assert plan.applicable is True
    assert plan.migration_ids == ("workspace-v1-to-v2",)
    canonical_targets = {item.target for item in plan.operations if item.canonical}
    assert canonical_targets == {
        ".p2p/project/questions.yml",
        ".p2p/project/definition.yml",
        ".p2p/project/workspace-schema.yml",
    }
    assert not canonical_targets.intersection(
        {
            ".p2p/project/domain.yml",
            ".p2p/project/permissions.yml",
            ".p2p/project/vertical.yml",
            ".p2p/project/rubrics.yml",
        }
    )
    canonical_operations = [item for item in plan.operations if item.canonical]
    assert canonical_operations[-1].target == ".p2p/project/workspace-schema.yml"


def test_v1_to_v2_apply_preserves_legacy_question_once_and_is_idempotent(tmp_path: Path) -> None:
    workspace = _v1_workspace(tmp_path)
    compatibility, migration = _services(tmp_path)
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"
    plan = compatibility.plan(2)

    result = migration.apply(
        target_version=2,
        owner_inputs={},
        plan_fingerprint=plan.fingerprint_sha256,
        actor="owner",
        confirm=True,
    )

    assert result.status == "applied"
    assert result.changed_paths[-1] == ".p2p/project/workspace-schema.yml"
    assert workspace.workspace_schema_status().state == "current"
    definition = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
    assert all(
        not section["open_questions"]
        for section in definition["project_definition"]["sections"]
    )
    artifact = ProjectQuestionStateService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
    ).read()
    migrated = [item for item in artifact.questions if item.source_question_id == "Q001"]
    assert len(migrated) == 1
    assert migrated[0].state.value == "to_answer"
    assert migrated[0].answers == ()

    no_op = compatibility.plan(2)
    assert no_op.status == "no_op"
    assert no_op.candidate_files == {}


@pytest.mark.parametrize(
    "failed_target",
    [
        ".p2p/project/definition.yml",
        ".p2p/project/questions.yml",
        ".p2p/project/workspace-schema.yml",
    ],
)
def test_v1_to_v2_failure_after_each_replace_restores_exact_v1_bytes(
    tmp_path: Path,
    failed_target: str,
) -> None:
    _v1_workspace(tmp_path)
    questions_path = tmp_path / ".p2p" / "project" / "questions.yml"
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    originals = {path: path.read_bytes() for path in (definition_path, schema_path)}

    def fail(stage: str, target: str) -> None:
        if stage == "after_replace" and target == failed_target:
            raise RuntimeError("injected v2 failure")

    compatibility, migration = _services(tmp_path, failure_injector=fail)
    plan = compatibility.plan(2)
    result = migration.apply(
        target_version=2,
        owner_inputs={},
        plan_fingerprint=plan.fingerprint_sha256,
        actor="owner",
        confirm=True,
    )

    assert result.status == "rolled_back"
    assert not questions_path.exists()
    assert definition_path.read_bytes() == originals[definition_path]
    assert schema_path.read_bytes() == originals[schema_path]


def test_v1_to_v2_preserves_repeated_section_local_legacy_ids_once_per_section(
    tmp_path: Path,
) -> None:
    _v1_workspace(tmp_path)
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"
    definition = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
    sections = definition["project_definition"]["sections"]
    second = next(item for item in sections if item["id"] != "vision" and item["missing_required_fields"])
    second["open_questions"] = [
        {
            "id": "Q001",
            "question": "What section-local value is required?",
            "field_id": second["missing_required_fields"][0],
            "status": "open",
        }
    ]
    definition_path.write_text(yaml.safe_dump(definition, sort_keys=False), encoding="utf-8")

    plan = WorkspaceCompatibilityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
    ).plan(2)

    assert plan.applicable is True
    questions = ProjectQuestionStateService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
    ).parse_bytes(
        plan.candidate_files[".p2p/project/questions.yml"],
        target="candidate",
    )
    migrated = [item for item in questions.questions if item.source_question_id == "Q001"]
    assert len(migrated) == 2
    assert len({item.question_id for item in migrated}) == 2
    assert len({item.section_id for item in migrated}) == 2


def test_v1_to_v2_invalid_definition_is_not_misreported_as_owner_binding_input(
    tmp_path: Path,
) -> None:
    _v1_workspace(tmp_path)
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"
    definition = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
    definition["project_definition"]["sections"].pop()
    definition_path.write_text(yaml.safe_dump(definition, sort_keys=False), encoding="utf-8")

    plan = WorkspaceCompatibilityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
    ).plan(2)

    assert plan.applicable is False
    assert any(item.code == "P2P340_PROJECT_QUESTIONS_INVALID" for item in plan.findings)
    assert all(item.code != "P2P350_AMBIGUOUS_LEGACY_QUESTION" for item in plan.findings)


def test_multistep_legacy_to_v2_uses_adjacent_handlers_without_question_loss(tmp_path: Path) -> None:
    initialize_legacy_workspace(tmp_path, owner="owner")
    unknown = tmp_path / ".p2p" / "owner-memory.bin"
    unknown.write_bytes(b"preserve")
    compatibility = WorkspaceCompatibilityService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    plan = compatibility.plan(
        2,
        {"vertical": {"id": "base_project"}, "owner": {"id": "owner", "name": "owner"}},
    )

    assert plan.applicable is True
    assert plan.migration_ids == ("workspace-legacy-to-v1", "workspace-v1-to-v2")
    schema = yaml.safe_load(plan.candidate_files[".p2p/project/workspace-schema.yml"])
    history = schema["workspace_schema"]["applied_migrations"]
    assert [(item["from"], item["to"]) for item in history] == [
        ("legacy_undeclared", 1),
        (1, 2),
    ]
    questions = yaml.safe_load(plan.candidate_files[".p2p/project/questions.yml"])
    assert questions["project_questions"]["vertical"]["id"] == "base_project"
    preserves = [item.target for item in plan.operations if item.kind == OP_PRESERVE_LEGACY]
    assert preserves == [".p2p/owner-memory.bin"]


def test_migration_owner_input_accepts_target_binding_and_rejects_answer_content() -> None:
    normalized = normalize_owner_inputs(
        {
            "project_questions": {
                "legacy_bindings": {
                    "decisions/Q001": {
                        "target_kind": "field",
                        "target_id": "summary",
                        "answer_contract": "field_value",
                    }
                }
            }
        }
    )

    assert normalized["project_questions"] == {
        "legacy_bindings": {
            "decisions/Q001": {
                "target_kind": "field",
                "target_id": "summary",
                "answer_contract": "field_value",
            }
        }
    }

    with pytest.raises(ValueError, match="forbidden fields"):
        normalize_owner_inputs(
            {
                "project_questions": {
                    "legacy_bindings": {
                        "decisions/Q001": {
                            "target_kind": "field",
                            "target_id": "summary",
                            "answer": "must not be accepted",
                        }
                    }
                }
            }
        )

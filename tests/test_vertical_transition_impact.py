from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import hashlib
import json

import pytest
import yaml

from p2p_engine.core.vertical_transition_impact import (
    BoundedCollection,
    EvidenceKind,
    QuestionImpact,
    TransitionOperation,
)
from p2p_engine.core.vertical_transition_plan import parse_transition_plan
from p2p_engine.core.vertical_transition_plan import VERTICAL_TRANSITION_PLAN_MAX_DECISIONS
from p2p_engine.core.project_verticals import ProjectDefinitionOrphan
from p2p_engine import __version__
from p2p_engine.services.vertical_evidence_classifier import VerticalEvidenceClassifier
from p2p_engine.services.project_verticals import project_definition_state_payload
from p2p_engine.services.vertical_transition_analysis import (
    _transition_material_exceeds_limit,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.test_portable_verticals import _portable_pack


def _classifier(project: P2PWorkspace) -> VerticalEvidenceClassifier:
    return VerticalEvidenceClassifier(
        root=project.root,
        p2p_dir=project.p2p_dir,
        vertical_service=project._project_vertical_service(),
    )


def _patch(project: P2PWorkspace, path: Path, operation: dict[str, object]) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "project_definition_patch": {
                    "schema_version": 1,
                    "actor": "owner",
                    "operations": [operation],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    project.update_project_definition(path)


@pytest.mark.service
def test_classifier_treats_false_and_zero_as_evidence_but_not_untouched_defaults(
    tmp_path: Path,
) -> None:
    project = P2PWorkspace(tmp_path / "project")
    project.init_project("Classifier", owner="owner")
    project.select_project_vertical("base_project", actor="owner")
    empty = _classifier(project).capture()
    assert empty.source_state.classification == "empty"
    assert empty.source_state.evidence.total == 0

    state = project.project_definition_view().state
    assert state is not None
    section = state.sections[0]
    field_id = section.missing_required_fields[0]
    _patch(
        project,
        tmp_path / "false.yml",
        {
            "op": "set_field",
            "section_id": section.section_id,
            "field_id": field_id,
            "value": False,
        },
    )
    populated = _classifier(project).capture()
    assert populated.source_state.classification == "populated"
    assert populated.source_state.evidence.definition_fields == 1

    _patch(
        project,
        tmp_path / "zero.yml",
        {
            "op": "set_field",
            "section_id": section.section_id,
            "field_id": field_id,
            "value": 0,
        },
    )
    assert _classifier(project).capture().source_state.evidence.definition_fields == 1


@pytest.mark.service
@pytest.mark.parametrize(
    ("operation", "expected_field"),
    [
        ({"op": "add_assumption", "text": "private assumption"}, "assumptions"),
        ({"op": "add_blocker", "text": "private blocker"}, "blockers"),
    ],
)
def test_classifier_counts_definition_evidence_families(
    tmp_path: Path,
    operation: dict[str, object],
    expected_field: str,
) -> None:
    project = P2PWorkspace(tmp_path / expected_field)
    project.init_project("Classifier family", owner="owner")
    project.select_project_vertical("base_project", actor="owner")
    state = project.project_definition_view().state
    assert state is not None
    payload = {**operation, "section_id": state.sections[0].section_id}
    _patch(project, tmp_path / f"{expected_field}.yml", payload)
    counts = _classifier(project).capture().source_state.evidence
    assert getattr(counts, expected_field) == 1


@pytest.mark.service
def test_classifier_counts_owner_question_and_rubric_customization(tmp_path: Path) -> None:
    question_project = P2PWorkspace(tmp_path / "questions")
    question_project.init_project("Question evidence", owner="owner")
    question_project.select_project_vertical("base_project", actor="owner")
    question = question_project.next_project_question()
    assert question is not None
    question_project.defer_project_question(
        question.question_id,
        actor="owner",
        expected_revision=question.revision,
        reason="owner decision",
    )
    question_counts = _classifier(question_project).capture().source_state.evidence
    assert question_counts.owner_question_evidence == 1

    rubric_project = P2PWorkspace(tmp_path / "rubrics")
    rubric_project.init_project("Rubric evidence", owner="owner")
    rubric_project.select_project_vertical("base_project", actor="owner")
    rubric_path = rubric_project.p2p_dir / "project" / "rubrics.yml"
    payload = yaml.safe_load(rubric_path.read_text(encoding="utf-8"))
    payload["criteria"][0]["enabled"] = False
    rubric_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    rubric_counts = _classifier(rubric_project).capture().source_state.evidence
    assert rubric_counts.rubric_customizations == 1


@pytest.mark.service
def test_classifier_counts_existing_definition_orphan(tmp_path: Path) -> None:
    project = P2PWorkspace(tmp_path / "orphan")
    project.init_project("Orphan evidence", owner="owner")
    project.select_project_vertical("base_project", actor="owner")
    state = project.project_definition_view().state
    assert state is not None
    orphan = ProjectDefinitionOrphan(
        orphan_id="ORPH-existing",
        source_vertical=state.vertical_id,
        source_section_id="legacy",
        source_field_id="answer",
        value="private orphan evidence",
        source="owner",
        reason="retained",
        target_vertical=state.vertical_id,
    )
    definition_path = project.p2p_dir / "project" / "definition.yml"
    definition_path.write_text(
        yaml.safe_dump(
            project_definition_state_payload(replace(state, orphans=[orphan])),
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    counts = _classifier(project).capture().source_state.evidence
    assert counts.definition_orphans == 1


@pytest.mark.service
@pytest.mark.parametrize(
    ("artifact", "expected_code"),
    [
        ("rubrics", "P2P_VERTICAL_SOURCE_RUBRICS_INVALID"),
        ("lock", "P2P_VERTICAL_SOURCE_LOCK_INVALID"),
    ],
)
def test_classifier_rejects_malformed_current_artifacts(
    tmp_path: Path,
    artifact: str,
    expected_code: str,
) -> None:
    project = P2PWorkspace(tmp_path / artifact)
    project.init_project("Invalid classifier input", owner="owner")
    project.select_project_vertical("base_project", actor="owner")
    if artifact == "rubrics":
        target = project.p2p_dir / "project" / "rubrics.yml"
        target.write_text("criteria: invalid\n", encoding="utf-8")
    else:
        target = project.p2p_dir / "project" / "vertical.lock.yml"
        target.write_text("project_vertical_lock: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match=expected_code):
        _classifier(project).capture()


@pytest.mark.unit
def test_transition_plan_is_strict_and_fingerprint_is_order_independent() -> None:
    analysis = "a" * 64
    first = {
        "id": "VTD-1111111111111111",
        "action": "preserve_as_orphan",
        "source": {
            "kind": "definition_field",
            "ref": "definition_field:old.one",
        },
    }
    second = {
        "id": "VTD-2222222222222222",
        "action": "map",
        "source": {"kind": "rubric", "ref": "rubric:old"},
        "target": {"kind": "rubric", "ref": "rubric:new"},
    }

    def payload(decisions: list[dict[str, object]]) -> dict[str, object]:
        return {
            "vertical_transition_plan": {
                "schema_version": 1,
                "contract_version": "p2p-vertical-transition-plan/v1",
                "analysis_fingerprint_sha256": analysis,
                "decisions": decisions,
            }
        }

    one = parse_transition_plan(payload([first, second]))
    two = parse_transition_plan(payload([second, first]))
    assert one.fingerprint_sha256 == two.fingerprint_sha256

    with pytest.raises(ValueError, match="P2P_VERTICAL_TRANSITION_PLAN_INVALID"):
        parse_transition_plan({"field_mapping": {"old.one": "new.one"}})
    with pytest.raises(ValueError, match="duplicate decision id"):
        parse_transition_plan(payload([first, first]))
    with pytest.raises(ValueError, match="P2P_VERTICAL_IMPACT_LIMIT_EXCEEDED"):
        parse_transition_plan(
            payload(
                [
                    {
                        "id": f"VTD-{index:016x}",
                        "action": "preserve_as_orphan",
                        "source": {
                            "kind": "definition_field",
                            "ref": f"definition_field:section.field{index}",
                        },
                    }
                    for index in range(VERTICAL_TRANSITION_PLAN_MAX_DECISIONS + 1)
                ]
            )
        )


@pytest.mark.unit
def test_transition_enums_and_material_limits_fail_closed() -> None:
    with pytest.raises(ValueError):
        TransitionOperation("replace")
    with pytest.raises(ValueError):
        EvidenceKind("free_form")

    empty = BoundedCollection(total=0, items=(), truncated=False)
    one_question = BoundedCollection(total=1, items=("Q-001",), truncated=False)
    questions = QuestionImpact(
        preserved=one_question,
        revised=empty,
        created=empty,
        retired=empty,
        superseded=empty,
        inactive_owner_evidence=empty,
        owner_review_required=empty,
    )
    empty_questions = QuestionImpact(
        preserved=empty,
        revised=empty,
        created=empty,
        retired=empty,
        superseded=empty,
        inactive_owner_evidence=empty,
        owner_review_required=empty,
    )
    assert not _transition_material_exceeds_limit(
        [[object()] * 127, [object()] * 128, [object()] * 128, [object()] * 128],
        question_impact=empty_questions,
    )
    assert _transition_material_exceeds_limit(
        [[object()] * 128, [object()] * 128, [object()] * 128, [object()] * 128],
        question_impact=questions,
    )
    assert _transition_material_exceeds_limit(
        [[object()] * 129],
        question_impact=empty_questions,
    )


@pytest.mark.service
def test_public_vertical_preview_is_path_free_and_redacts_evidence(tmp_path: Path) -> None:
    authoring = P2PWorkspace(tmp_path)
    source_archive, source_checksum, source_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="privacy-source",
        version="1.0.0",
    )
    target_archive, target_checksum, target_coordinate = _portable_pack(
        authoring,
        tmp_path,
        vertical_id="privacy-target",
        version="2.0.0",
        field_id="renamed_summary",
    )
    project = P2PWorkspace(tmp_path / "project")
    project.init_project("Privacy", owner="owner")
    for archive, checksum in (
        (source_archive, source_checksum),
        (target_archive, target_checksum),
    ):
        install = project.preview_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            actor="owner",
        )
        assert set(install.impact.to_dict()) == {
            "contract_version",
            "operation",
            "analysis_fingerprint_sha256",
            "target",
            "artifact_kinds",
            "dependency_closure",
            "disposition",
            "conflict",
            "blockers",
            "warnings",
        }
        assert set(install.to_dict()["preview"]) == {
            "operation_id",
            "actor",
            "authority",
            "confirmation_required",
            "policy_version",
            "apply_allowed",
            "preview_token",
        }
        project.apply_portable_vertical_install(
            archive,
            expected_checksum=checksum,
            preview_token=install.preview.preview_token,
            confirmed=True,
            actor="owner",
            idempotency_key=f"install:{checksum}",
        )
    adoption = project.preview_project_vertical_adoption(source_coordinate, actor="owner")
    assert set(adoption.impact.to_dict()) == {
        "contract_version",
        "operation",
        "analysis_fingerprint_sha256",
        "source_state",
        "source",
        "target",
        "lock",
        "artifacts",
        "blockers",
        "warnings",
    }
    project.apply_project_vertical_adoption(
        source_coordinate,
        preview_token=adoption.preview.preview_token,
        confirmed=True,
        actor="owner",
        idempotency_key="adopt:privacy-source",
    )
    state = project.project_definition_view().state
    assert state is not None
    section = state.sections[0]
    field_id = section.missing_required_fields[0]
    secret = "DISTINCTIVE-PRIVATE-VALUE-424242"
    _patch(
        project,
        tmp_path / "secret.yml",
        {
            "op": "set_field",
            "section_id": section.section_id,
            "field_id": field_id,
            "value": secret,
        },
    )
    preview = project.preview_project_vertical_migration(
        target_coordinate,
        actor="owner",
    )
    serialized = str(preview.to_dict())
    assert set(preview.impact.to_dict()) == {
        "contract_version",
        "operation",
        "analysis_fingerprint_sha256",
        "plan_fingerprint_sha256",
        "source_state",
        "source",
        "target",
        "sections",
        "evidence_transitions",
        "rubrics",
        "questions",
        "lock",
        "artifacts",
        "required_decisions",
        "blockers",
        "warnings",
    }
    assert secret not in serialized
    assert ".p2p/" not in serialized
    assert "source_preconditions" not in serialized
    assert "candidate_semantic_hashes" not in serialized


@pytest.mark.unit
def test_wavekit_handoff_fixture_manifest_is_current_bounded_and_path_free() -> None:
    root = Path(__file__).parent / "fixtures" / "vertical_transition"
    manifest = json.loads((root / "manifest-v1.json").read_text(encoding="utf-8"))
    assert manifest["engine_version"] == __version__
    assert manifest["impact_contract_version"] == "p2p-vertical-transition-impact/v1"
    assert manifest["plan_contract_version"] == "p2p-vertical-transition-plan/v1"
    assert manifest["limits"] == {
        "collection_items": 128,
        "transition_material_items": 512,
        "plan_decisions": 128,
        "receipt_bytes": 65536,
    }
    for name, expected in manifest["fixtures"].items():
        content = (root / name).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected
        assert b".p2p/" not in content
        payload = json.loads(content)
        _assert_collection_envelopes(payload)

    legacy = json.loads(
        (root / "legacy-0.4.7-characterization.json").read_text(encoding="utf-8")
    )
    assert legacy["release_tag"] == "v0.4.7"
    assert legacy["source_commit"] == "6bc23d2cac2af9f9a249bc2504e7e87331659226"
    assert set(legacy["cases"]) == {
        "install_preview",
        "empty_adoption",
        "populated_adoption_rejection",
        "migration_with_mapping",
        "implicit_orphaning",
        "rubric_collision",
        "question_reconciliation",
        "apply",
        "replay",
    }


def _assert_collection_envelopes(value: object) -> None:
    if isinstance(value, dict):
        if {"total", "returned", "truncated", "items"} <= set(value):
            assert value["returned"] == len(value["items"])
            assert value["returned"] <= value["total"]
            assert value["truncated"] is (value["returned"] < value["total"])
        for item in value.values():
            _assert_collection_envelopes(item)
    elif isinstance(value, list):
        for item in value:
            _assert_collection_envelopes(item)

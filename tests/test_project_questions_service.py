from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from p2p_engine.core.project_questions import (
    ProjectQuestionAnswerKind,
    ProjectQuestionApplicability,
    ProjectQuestionSourceType,
    ProjectQuestionState,
    project_question_identity,
)
from p2p_engine.core.project_verticals import (
    ProjectDefinitionAssumption,
    ProjectDefinitionBlocker,
    ProjectDefinitionFieldValue,
    ProjectDefinitionSectionState,
    ProjectDefinitionState,
    VerticalCompletionPolicy,
    VerticalField,
    VerticalPack,
    VerticalQuestion,
    VerticalSection,
)
from p2p_engine.services.project_questions import ProjectQuestionStateService
from p2p_engine.services.permissions import PermissionsService


def _pack(*, field_count: int = 1, declared_target: bool = False) -> VerticalPack:
    fields = [
        VerticalField(
            field_id=f"field_{index}",
            label=f"Field {index}",
            required=True,
            question=f"What is field {index}?",
        )
        for index in range(1, field_count + 1)
    ]
    question = VerticalQuestion(
        question_id="declared-main",
        section_id="decisions",
        question="What decision policy applies?",
        priority="high",
        target_kind="field" if declared_target else "",
        target_id="field_1" if declared_target else "",
        answer_contract=(
            {
                "kind": "field_value",
                "required_fields": ["value"],
                "allowed_definition_operations": ["set_field"],
            }
            if declared_target
            else {}
        ),
    )
    return VerticalPack(
        vertical_id="software_project",
        name="Software Project",
        version="1.0.0",
        description="Test vertical",
        extends=None,
        source="test",
        path=None,
        sections=[
            VerticalSection(
                section_id="decisions",
                title="Decisions",
                purpose="Define decisions.",
                required=True,
                priority=10,
                fields=fields,
                completion_policy=VerticalCompletionPolicy(required_fields=[item.field_id for item in fields]),
            )
        ],
        rubrics=[],
        questions=[question],
        artifacts=[],
    )


def _definition(*, field_count: int = 1, status: str = "partial") -> ProjectDefinitionState:
    section = ProjectDefinitionSectionState(
        section_id="decisions",
        status=status,
        missing_required_fields=[f"field_{index}" for index in range(1, field_count + 1)],
    )
    return ProjectDefinitionState(
        schema_version=1,
        vertical_id="software_project",
        vertical_version="1.0.0",
        lock_checksum="lock",
        sections=[section],
    )


def test_question_identity_ignores_wording_lock_time_and_root() -> None:
    first = project_question_identity(
        vertical_id="software_project",
        section_id="decisions",
        gap_kind="incomplete_required_definition",
        target_kind="field",
        target_id="field_1",
        source_key="declared:main",
    )
    second = project_question_identity(
        vertical_id="software_project",
        section_id="decisions",
        gap_kind="incomplete_required_definition",
        target_kind="field",
        target_id="field_1",
        source_key="declared:main",
    )

    assert first == second
    assert first[0].startswith("PRQ-")
    assert len(first[1]) == 64


def test_empty_artifact_round_trip_and_semantic_hash_ignore_audit(tmp_path: Path) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    first = service.empty_artifact(
        project_id="demo",
        vertical_id="software_project",
        vertical_version="1.0.0",
        lock_checksum="lock",
        actor="owner",
        audit_at="2026-01-01T00:00:00Z",
    )
    second = replace(
        first,
        created_at="2027-01-01T00:00:00Z",
        updated_at="2027-01-01T00:00:00Z",
    )

    parsed = service.parse_bytes(service.candidate_bytes(first), target="candidate")

    assert parsed == first
    assert first.semantic_sha256 == second.semantic_sha256


def test_incomplete_section_uses_declared_or_deterministic_fallback(tmp_path: Path) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    declared = service.seed_from_definition(
        project_id="demo",
        definition=_definition(),
        pack=_pack(declared_target=True),
        lock_checksum="lock",
        actor="system",
        audit_at="now",
    )
    fallback = service.seed_from_definition(
        project_id="demo",
        definition=_definition(),
        pack=replace(_pack(), questions=[]),
        lock_checksum="lock",
        actor="system",
        audit_at="now",
    )

    assert declared.artifact.questions[0].source_kind == ProjectQuestionSourceType.VERTICAL_DECLARED
    assert fallback.artifact.questions[0].source_kind == ProjectQuestionSourceType.DETERMINISTIC_FALLBACK
    assert fallback.artifact.questions[0].target.target_id == "field_1"


@pytest.mark.parametrize(
    ("section", "expected_kind", "expected_target"),
    [
        (
            ProjectDefinitionSectionState(
                section_id="decisions",
                status="partial",
                assumptions=[ProjectDefinitionAssumption("A001", "Assumption")],
            ),
            ProjectQuestionAnswerKind.ASSUMPTION_RESOLUTION,
            "A001",
        ),
        (
            ProjectDefinitionSectionState(
                section_id="decisions",
                status="blocked",
                blockers=[ProjectDefinitionBlocker("B001", "Blocker")],
            ),
            ProjectQuestionAnswerKind.BLOCKER_RESOLUTION,
            "B001",
        ),
        (
            ProjectDefinitionSectionState(section_id="decisions", status="partial"),
            ProjectQuestionAnswerKind.SECTION_DISPOSITION,
            "decisions",
        ),
    ],
)
def test_deterministic_fallback_contracts_cover_assumption_blocker_and_section(
    tmp_path: Path,
    section: ProjectDefinitionSectionState,
    expected_kind: ProjectQuestionAnswerKind,
    expected_target: str,
) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    definition = ProjectDefinitionState(
        schema_version=1,
        vertical_id="software_project",
        vertical_version="1.0.0",
        lock_checksum="lock",
        sections=[section],
    )

    result = service.seed_from_definition(
        project_id="demo",
        definition=definition,
        pack=replace(_pack(), questions=[]),
        lock_checksum="lock",
        actor="system",
        audit_at="now",
    )

    question = result.artifact.questions[0]
    assert question.answer_contract.kind == expected_kind
    assert question.target.target_id == expected_target


def test_multiple_missing_targets_emit_no_safe_question_without_inventing_content(
    tmp_path: Path,
) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    result = service.seed_from_definition(
        project_id="demo",
        definition=_definition(field_count=2),
        pack=replace(_pack(field_count=2), questions=[]),
        lock_checksum="lock",
        actor="system",
        audit_at="now",
    )

    assert result.artifact.questions == ()
    assert [item.code for item in result.diagnostics] == ["P2P344_PROJECT_QUESTION_NO_SAFE_FALLBACK"]


@pytest.mark.parametrize("status", ["complete", "not_applicable"])
def test_complete_or_not_applicable_section_is_not_seeded(tmp_path: Path, status: str) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    result = service.seed_from_definition(
        project_id="demo",
        definition=_definition(status=status),
        pack=_pack(declared_target=True),
        lock_checksum="lock",
        actor="system",
        audit_at="now",
    )

    assert result.artifact.questions == ()


def test_parser_rejects_unknown_fields_and_identity_tampering(tmp_path: Path) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    result = service.seed_from_definition(
        project_id="demo",
        definition=_definition(),
        pack=_pack(declared_target=True),
        lock_checksum="lock",
        actor="system",
        audit_at="now",
    )
    payload = result.artifact.to_payload()
    raw = payload["project_questions"]
    assert isinstance(raw, dict)
    raw["unknown"] = True

    with pytest.raises(ValueError, match="unknown fields"):
        service.parse_payload(payload, target="candidate")

    payload = result.artifact.to_payload()
    raw = payload["project_questions"]
    assert isinstance(raw, dict)
    questions = raw["questions"]
    assert isinstance(questions, list) and isinstance(questions[0], dict)
    questions[0]["identity_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="identity mismatch"):
        service.parse_payload(payload, target="candidate")


def test_parser_rejects_nested_unknown_fields_and_invalid_group_scope(tmp_path: Path) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    artifact = service.seed_from_definition(
        project_id="demo",
        definition=_definition(),
        pack=_pack(declared_target=True),
        lock_checksum="lock",
        actor="system",
        audit_at="now",
    ).artifact
    payload = artifact.to_payload()
    raw = payload["project_questions"]
    assert isinstance(raw, dict)
    questions = raw["questions"]
    assert isinstance(questions, list) and isinstance(questions[0], dict)
    target = questions[0]["target"]
    assert isinstance(target, dict)
    target["unknown"] = True

    with pytest.raises(ValueError, match="target.*unknown fields"):
        service.parse_payload(payload, target="candidate")

    payload = artifact.to_payload()
    raw = payload["project_questions"]
    assert isinstance(raw, dict)
    groups = raw["groups"]
    assert isinstance(groups, list) and isinstance(groups[0], dict)
    groups[0]["section_id"] = "wrong-section"
    with pytest.raises(ValueError, match="group identity mismatch"):
        service.parse_payload(payload, target="candidate")

    payload = artifact.to_payload()
    raw = payload["project_questions"]
    assert isinstance(raw, dict)
    policies = raw["policy_versions"]
    assert isinstance(policies, dict)
    policies["identity"] = []
    with pytest.raises(ValueError, match="must be an integer"):
        service.parse_payload(payload, target="candidate")

    broken = replace(
        artifact.questions[0],
        state=ProjectQuestionState.SUPERSEDED,
        superseded_by="PRQ-missing",
    )
    with pytest.raises(ValueError, match="unknown replacement"):
        service.candidate_bytes(replace(artifact, questions=(broken,)))


def test_multiple_explicit_declared_questions_require_independent_targets(tmp_path: Path) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    pack = _pack(field_count=2, declared_target=True)
    second = replace(
        pack.questions[0],
        question_id="declared-second",
        question="What second policy applies?",
        target_id="field_2",
    )
    pack = replace(pack, questions=[pack.questions[0], second])

    seeded = service.seed_from_definition(
        project_id="demo",
        definition=_definition(field_count=2),
        pack=pack,
        lock_checksum="lock",
        actor="system",
        audit_at="now",
    )

    assert seeded.generated_count == 2
    assert {item.target.target_id for item in seeded.artifact.questions} == {"field_1", "field_2"}

    duplicate = replace(second, target_id="field_1")
    with pytest.raises(ValueError, match="multiple declared questions target"):
        service.seed_from_definition(
            project_id="demo",
            definition=_definition(field_count=2),
            pack=replace(pack, questions=[pack.questions[0], duplicate]),
            lock_checksum="lock",
            actor="system",
            audit_at="now",
        )


def test_serialized_question_artifact_has_one_registered_root(tmp_path: Path) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    artifact = service.empty_artifact(
        project_id="demo",
        vertical_id="software_project",
        vertical_version="1.0.0",
        lock_checksum="lock",
        actor="system",
        audit_at="now",
    )

    payload = yaml.safe_load(service.candidate_bytes(artifact))

    assert list(payload) == ["project_questions"]
    assert payload["project_questions"]["schema_version"] == 1


def _persist_question_fixture(tmp_path: Path) -> tuple[ProjectQuestionStateService, str]:
    p2p_dir = tmp_path / ".p2p"
    permissions = PermissionsService(root=tmp_path, p2p_dir=p2p_dir)
    permissions.write_policy(permissions.default_policy_payload(owner_name="Mr Jungle"))
    service = ProjectQuestionStateService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        permissions=permissions,
        clock=lambda: "2026-07-16T10:00:00Z",
    )
    artifact = service.seed_from_definition(
        project_id="demo",
        definition=_definition(),
        pack=_pack(declared_target=True),
        lock_checksum="lock",
        actor="system",
        audit_at="2026-07-16T09:00:00Z",
    ).artifact
    service.path.parent.mkdir(parents=True, exist_ok=True)
    service.path.write_bytes(service.candidate_bytes(artifact))
    return service, artifact.questions[0].question_id


def test_owner_answer_is_a_single_target_atomic_write_and_does_not_change_definition(tmp_path: Path) -> None:
    service, question_id = _persist_question_fixture(tmp_path)
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"
    definition_path.write_text("project_definition: {}\n", encoding="utf-8")
    before_definition = definition_path.read_bytes()

    result = service.answer(
        question_id,
        values={"value": "Use accepted decisions."},
        actor="Mr Jungle",
        expected_revision=1,
    )

    assert result.status == "applied"
    assert result.mutation_performed is True
    assert result.question is not None
    assert result.question.state == ProjectQuestionState.ANSWERED
    assert result.question.revision == 2
    assert result.question.answers[0].provided_by == "mr-jungle"
    assert result.question.answers[0].recorded_by == "mr-jungle"
    assert definition_path.read_bytes() == before_definition


@pytest.mark.parametrize(
    ("actor", "values", "error"),
    [
        ("contributor", {"value": "not authorized"}, "P2P343_PROJECT_QUESTION_OWNER_REQUIRED"),
        ("Mr Jungle", {"unexpected": "value"}, "P2P342_PROJECT_QUESTION_TRANSITION_INVALID"),
    ],
)
def test_failed_answer_checks_are_byte_invariant(
    tmp_path: Path,
    actor: str,
    values: dict[str, object],
    error: str,
) -> None:
    service, question_id = _persist_question_fixture(tmp_path)
    before = service.path.read_bytes()

    with pytest.raises(ValueError, match=error):
        service.answer(
            question_id,
            values=values,
            actor=actor,
            expected_revision=1,
        )

    assert service.path.read_bytes() == before


def test_answer_replacement_is_explicit_revision_checked_and_preserves_history(tmp_path: Path) -> None:
    service, question_id = _persist_question_fixture(tmp_path)
    service.answer(question_id, values={"value": "first"}, actor="Mr Jungle", expected_revision=1)
    before = service.path.read_bytes()

    with pytest.raises(ValueError, match="STALE_PREVIEW"):
        service.answer(
            question_id,
            values={"value": "stale"},
            actor="Mr Jungle",
            expected_revision=1,
            replace_answer=True,
        )
    assert service.path.read_bytes() == before

    result = service.answer(
        question_id,
        values={"value": "second"},
        actor="Mr Jungle",
        expected_revision=2,
        replace_answer=True,
    )

    assert result.question is not None
    assert [item.values["value"] for item in result.question.answers] == ["first", "second"]
    assert [item.revision for item in result.question.answers] == [1, 2]
    assert result.question.revision == 3


def test_defer_mute_and_reopen_follow_transition_matrix_and_next_skips_inactive(tmp_path: Path) -> None:
    service, question_id = _persist_question_fixture(tmp_path)

    deferred = service.defer(
        question_id,
        actor="Mr Jungle",
        expected_revision=1,
        reason="Wait for evidence.",
    )
    assert deferred.question is not None
    assert deferred.question.state == ProjectQuestionState.DEFERRED
    assert service.next_question() is None

    reopened = service.reopen(
        question_id,
        actor="Mr Jungle",
        expected_revision=2,
        reason="Evidence is now available.",
    )
    assert reopened.question is not None
    assert reopened.question.state == ProjectQuestionState.TO_ANSWER
    assert service.next_question() is not None

    muted = service.mute(
        question_id,
        actor="Mr Jungle",
        expected_revision=3,
        reason="Do not ask automatically.",
    )
    assert muted.question is not None
    assert muted.question.state == ProjectQuestionState.MUTED
    assert service.next_question() is None


def test_lifecycle_requires_reason_and_terminal_states_do_not_transition(tmp_path: Path) -> None:
    service, question_id = _persist_question_fixture(tmp_path)
    before = service.path.read_bytes()
    with pytest.raises(ValueError, match="non-empty reason"):
        service.defer(question_id, actor="Mr Jungle", expected_revision=1, reason=" ")
    assert service.path.read_bytes() == before


def test_only_versioned_declared_deferred_trigger_reopens_deterministically(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    permissions = PermissionsService(root=tmp_path, p2p_dir=p2p_dir)
    permissions.write_policy(permissions.default_policy_payload(owner_name="owner"))
    service = ProjectQuestionStateService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        permissions=permissions,
        clock=lambda: "2026-07-16T10:00:00Z",
    )
    pack = _pack(declared_target=True)
    pack = replace(
        pack,
        questions=[
            replace(
                pack.questions[0],
                deferred_trigger={
                    "policy_version": 1,
                    "kind": "definition_field_present",
                    "section_id": "decisions",
                    "field_id": "field_1",
                },
            )
        ],
    )
    artifact = service.seed_from_definition(
        project_id="demo",
        definition=_definition(),
        pack=pack,
        lock_checksum="lock",
        actor="system",
        audit_at="now",
    ).artifact
    service.path.parent.mkdir(parents=True, exist_ok=True)
    service.path.write_bytes(service.candidate_bytes(artifact))
    question_id = artifact.questions[0].question_id
    service.defer(question_id, actor="owner", expected_revision=1, reason="Wait for field.")
    unchanged = service.reopen_deferred_triggers(_definition(), actor="system")
    assert unchanged.status == "no_op"

    section = _definition().sections[0]
    definition = replace(
        _definition(),
        sections=[
            replace(
                section,
                fields={
                    "field_1": ProjectDefinitionFieldValue(
                        field_id="field_1",
                        value="present",
                        source="owner",
                    )
                },
            )
        ],
    )
    reopened = service.reopen_deferred_triggers(definition, actor="system")

    assert reopened.status == "applied"
    question = service.question(question_id)
    assert question.state == ProjectQuestionState.TO_ANSWER
    assert question.transitions[-1].operation == "declared_trigger_reopen"


def test_malformed_deferred_trigger_never_reopens(tmp_path: Path) -> None:
    service, question_id = _persist_question_fixture(tmp_path)
    artifact = service.read()
    question = replace(artifact.questions[0], deferred_trigger={"kind": "free_text", "text": "anything"})
    service.path.write_bytes(service.candidate_bytes(replace(artifact, questions=(question,))))
    service.defer(question_id, actor="Mr Jungle", expected_revision=1, reason="Wait.")

    result = service.reopen_deferred_triggers(_definition(), actor="system")

    assert result.status == "no_op"
    assert service.question(question_id).state == ProjectQuestionState.DEFERRED

    artifact = service.read()
    malformed = replace(
        artifact.questions[0],
        deferred_trigger={"policy_version": [], "kind": "definition_field_present"},
    )
    service.path.write_bytes(service.candidate_bytes(replace(artifact, questions=(malformed,))))
    assert service.reopen_deferred_triggers(_definition(), actor="system").status == "no_op"


def test_reconciliation_supersedes_changed_declared_target_without_copying_answer(
    tmp_path: Path,
) -> None:
    service, old_question_id = _persist_question_fixture(tmp_path)
    service.answer(
        old_question_id,
        values={"value": "owner evidence for the old target"},
        actor="Mr Jungle",
        expected_revision=1,
    )
    current = service.read()
    pack = _pack(field_count=2, declared_target=True)
    changed = replace(pack.questions[0], target_id="field_2")

    candidate = service.reconcile_candidate(
        current=current,
        project_id="demo",
        definition=_definition(field_count=2),
        pack=replace(pack, questions=[changed]),
        lock_checksum="new-lock",
        actor="owner",
        audit_at="later",
    )

    old = next(item for item in candidate.artifact.questions if item.question_id == old_question_id)
    new = next(item for item in candidate.artifact.questions if item.question_id != old_question_id)
    assert old.state == ProjectQuestionState.SUPERSEDED
    assert old.applicability == ProjectQuestionApplicability.TARGET_REMOVED
    assert old.superseded_by == new.question_id
    assert old.answers[-1].values["value"] == "owner evidence for the old target"
    assert new.state == ProjectQuestionState.TO_ANSWER
    assert new.answers == ()
    assert candidate.owner_evidence_affected is True


def test_reconciliation_reactivates_terminal_identity_as_a_new_revision(tmp_path: Path) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    pack = _pack(declared_target=True)
    seeded = service.seed_from_definition(
        project_id="demo",
        definition=_definition(),
        pack=pack,
        lock_checksum="old-lock",
        actor="system",
        audit_at="before",
    ).artifact
    old = replace(
        seeded.questions[0],
        state=ProjectQuestionState.RETIRED,
        applicability=ProjectQuestionApplicability.TARGET_REMOVED,
    )
    current = replace(seeded, questions=(old,))

    candidate = service.reconcile_candidate(
        current=current,
        project_id="demo",
        definition=_definition(),
        pack=pack,
        lock_checksum="new-lock",
        actor="system",
        audit_at="after",
    )

    reactivated = candidate.artifact.questions[0]
    assert reactivated.question_id == old.question_id
    assert reactivated.state == ProjectQuestionState.TO_ANSWER
    assert reactivated.revision == old.revision + 1
    assert reactivated.revisions[-1].revision == old.revision
    assert reactivated.superseded_by == ""


def test_reconciliation_uses_only_explicit_aliases_and_never_fuzzy_wording(
    tmp_path: Path,
) -> None:
    service = ProjectQuestionStateService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    original_pack = _pack(field_count=2, declared_target=True)
    current = service.seed_from_definition(
        project_id="demo",
        definition=_definition(field_count=2),
        pack=original_pack,
        lock_checksum="old-lock",
        actor="system",
        audit_at="before",
    ).artifact
    old = current.questions[0]
    replacement = replace(
        original_pack.questions[0],
        question_id="declared-replacement",
        target_id="field_2",
        aliases=("declared-main",),
    )
    aliased = service.reconcile_candidate(
        current=current,
        project_id="demo",
        definition=_definition(field_count=2),
        pack=replace(original_pack, questions=[replacement]),
        lock_checksum="new-lock",
        actor="system",
        audit_at="after",
    )
    old_aliased = next(item for item in aliased.artifact.questions if item.question_id == old.question_id)
    new_aliased = next(item for item in aliased.artifact.questions if item.question_id != old.question_id)
    assert old_aliased.state == ProjectQuestionState.SUPERSEDED
    assert old_aliased.superseded_by == new_aliased.question_id

    fuzzy_only = replace(replacement, aliases=(), question=old.question)
    unaliased = service.reconcile_candidate(
        current=current,
        project_id="demo",
        definition=_definition(field_count=2),
        pack=replace(original_pack, questions=[fuzzy_only]),
        lock_checksum="new-lock",
        actor="system",
        audit_at="after",
    )
    old_unaliased = next(item for item in unaliased.artifact.questions if item.question_id == old.question_id)
    assert old_unaliased.state == ProjectQuestionState.RETIRED
    assert old_unaliased.superseded_by == ""

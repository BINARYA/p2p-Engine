from __future__ import annotations

import multiprocessing
from pathlib import Path

import pytest

from p2p_engine.core.project_questions import ProjectQuestionApplicability, ProjectQuestionState
from p2p_engine.services.project_readiness_convergence import ProjectReadinessConvergenceService
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from p2p_engine.storage.filesystem import P2PWorkspace


def _concurrent_convergence_worker(
    root: str,
    question_id: str,
    preview_token: str,
    start_event,
    results,
) -> None:
    workspace = P2PWorkspace(Path(root))
    start_event.wait(timeout=10)
    result = workspace.apply_project_readiness_convergence(
        [question_id],
        actor="owner",
        preview_token=preview_token,
        confirm=True,
    )
    results.put(result.status)


def _answered_workspace(tmp_path: Path) -> tuple[P2PWorkspace, str]:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Convergence", owner="owner", vertical_id="base_project")
    question = workspace.next_project_question()
    assert question is not None
    result = workspace.answer_project_question(
        question.question_id,
        values={"value": "Owner supplied value"},
        actor="owner",
        expected_revision=question.revision,
    )
    assert result.status == "applied"
    return workspace, question.question_id


def test_convergence_preview_is_stable_read_only_and_binds_all_sources(tmp_path: Path) -> None:
    workspace, question_id = _answered_workspace(tmp_path)
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"
    questions_path = tmp_path / ".p2p" / "project" / "questions.yml"
    before = (definition_path.read_bytes(), questions_path.read_bytes())

    first = workspace.preview_project_readiness_convergence([question_id], actor="owner")
    second = workspace.preview_project_readiness_convergence([question_id], actor="owner")

    assert first.preview.preview_token == second.preview.preview_token
    assert first.preview.apply_allowed is True
    assert set(item.path for item in first.preview.source_preconditions) == {
        ".p2p/project/definition.yml",
        ".p2p/project/questions.yml",
        ".p2p/project/permissions.yml",
        ".p2p/project/workspace-schema.yml",
        ".p2p/project/vertical.yml",
        ".p2p/project/vertical.lock.yml",
    }
    assert first.question_ids == (question_id,)
    assert first.affected_gap_ids
    assert first.progress_effect["aggregate_percentage_added"] is False
    assert first.rebuild_plan
    assert set(first.preview.semantic_diff) == {
        ".p2p/project/definition.yml",
        ".p2p/project/questions.yml",
    }
    assert (definition_path.read_bytes(), questions_path.read_bytes()) == before


def test_convergence_commits_definition_and_question_once_then_replays_exactly(tmp_path: Path) -> None:
    workspace, question_id = _answered_workspace(tmp_path)
    preview = workspace.preview_project_readiness_convergence([question_id], actor="owner")

    blocked = workspace.apply_project_readiness_convergence(
        [question_id],
        actor="owner",
        preview_token=preview.preview.preview_token,
        confirm=False,
    )
    assert blocked.status == "blocked"

    result = workspace.apply_project_readiness_convergence(
        [question_id],
        actor="owner",
        preview_token=preview.preview.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    assert set(result.mutation.changed_paths) == {
        ".p2p/project/definition.yml",
        ".p2p/project/questions.yml",
    }
    question = workspace.project_question(question_id)
    assert question.state == ProjectQuestionState.APPLIED
    application = question.applications[-1]
    assert application.preview_token == preview.preview.preview_token
    assert application.operation_id == "project-readiness-convergence"
    assert application.actor == "owner"
    assert application.question_ids == (question_id,)
    assert application.question_revisions == {question_id: 2}
    assert application.definition_semantic_sha256 == preview.definition_candidate_sha256
    assert application.question_semantic_sha256 == preview.question_candidate_sha256
    definition = workspace.project_definition_view().state
    assert definition is not None
    section = next(item for item in definition.sections if item.section_id == question.section_id)
    assert section.fields[question.target.target_id].value == "Owner supplied value"

    replay = workspace.apply_project_readiness_convergence(
        [question_id],
        actor="owner",
        preview_token=preview.preview.preview_token,
        confirm=True,
    )
    assert replay.status == "already_applied"
    assert replay.already_applied is True
    assert replay.mutation_performed is False


def test_convergence_reused_token_with_changed_request_returns_replay_mismatch(tmp_path: Path) -> None:
    workspace, question_id = _answered_workspace(tmp_path)
    preview = workspace.preview_project_readiness_convergence([question_id], actor="owner")
    applied = workspace.apply_project_readiness_convergence(
        [question_id], actor="owner", preview_token=preview.preview.preview_token, confirm=True
    )
    assert applied.status == "applied"

    mismatch = workspace.apply_project_readiness_convergence(
        ["PRQ-does-not-match"],
        actor="owner",
        preview_token=preview.preview.preview_token,
        confirm=True,
    )

    assert mismatch.status == "replay_mismatch"
    assert mismatch.diagnostic_code == "P2P346_PREVIEW_REPLAY_MISMATCH"


def test_convergence_stale_permission_source_is_rejected_before_replacement(tmp_path: Path) -> None:
    workspace, question_id = _answered_workspace(tmp_path)
    preview = workspace.preview_project_readiness_convergence([question_id], actor="owner")
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"
    questions_path = tmp_path / ".p2p" / "project" / "questions.yml"
    before = (definition_path.read_bytes(), questions_path.read_bytes())
    permissions_path = tmp_path / ".p2p" / "project" / "permissions.yml"
    permissions_path.write_bytes(permissions_path.read_bytes() + b"\n")

    result = workspace.apply_project_readiness_convergence(
        [question_id], actor="owner", preview_token=preview.preview.preview_token, confirm=True
    )

    assert result.status == "stale_preview"
    assert (definition_path.read_bytes(), questions_path.read_bytes()) == before


@pytest.mark.parametrize(
    "relative",
    [
        ".p2p/project/definition.yml",
        ".p2p/project/questions.yml",
        ".p2p/project/workspace-schema.yml",
        ".p2p/project/vertical.yml",
        ".p2p/project/vertical.lock.yml",
    ],
)
def test_convergence_rejects_every_stale_source_without_overwriting_external_bytes(
    tmp_path: Path,
    relative: str,
) -> None:
    workspace, question_id = _answered_workspace(tmp_path)
    preview = workspace.preview_project_readiness_convergence([question_id], actor="owner")
    path = tmp_path / relative
    path.write_bytes(path.read_bytes() + b"\n")
    expected = path.read_bytes()

    result = workspace.apply_project_readiness_convergence(
        [question_id], actor="owner", preview_token=preview.preview.preview_token, confirm=True
    )

    assert result.status == "stale_preview"
    assert result.mutation_performed is False
    assert path.read_bytes() == expected


@pytest.mark.parametrize(
    "failed_target",
    [".p2p/project/definition.yml", ".p2p/project/questions.yml"],
)
def test_convergence_failure_after_each_replace_rolls_back_both_targets(
    tmp_path: Path,
    failed_target: str,
) -> None:
    workspace, question_id = _answered_workspace(tmp_path)
    definition_path = tmp_path / ".p2p" / "project" / "definition.yml"
    questions_path = tmp_path / ".p2p" / "project" / "questions.yml"
    before = (definition_path.read_bytes(), questions_path.read_bytes())

    def fail(stage: str, target: str) -> None:
        if stage == "after_replace" and target == failed_target:
            raise RuntimeError("injected failure")

    service = ProjectReadinessConvergenceService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        vertical_service=workspace._project_vertical_service(),
        question_service=workspace._project_question_state_service(),
        permissions=workspace._permissions_service(),
        atomic_writer=AtomicMutationWriter(
            root=tmp_path,
            p2p_dir=tmp_path / ".p2p",
            failure_injector=fail,
        ),
    )
    preview = service.preview([question_id], actor="owner")

    result = service.apply(
        [question_id], actor="owner", preview_token=preview.preview.preview_token, confirm=True
    )

    assert result.status == "rolled_back"
    assert (definition_path.read_bytes(), questions_path.read_bytes()) == before

    retry = workspace.apply_project_readiness_convergence(
        [question_id],
        actor="owner",
        preview_token=preview.preview.preview_token,
        confirm=True,
    )
    assert retry.status == "applied"


def test_convergence_preview_identity_ignores_injected_audit_clock(tmp_path: Path) -> None:
    workspace, question_id = _answered_workspace(tmp_path)

    def service(clock_value: str) -> ProjectReadinessConvergenceService:
        return ProjectReadinessConvergenceService(
            root=tmp_path,
            p2p_dir=tmp_path / ".p2p",
            vertical_service=workspace._project_vertical_service(),
            question_service=workspace._project_question_state_service(),
            permissions=workspace._permissions_service(),
            clock=lambda: clock_value,
        )

    first = service("2026-01-01T00:00:00Z").preview([question_id], actor="owner")
    second = service("2030-12-31T23:59:59Z").preview([question_id], actor="owner")

    assert first.preview.preview_token == second.preview.preview_token
    assert first.definition_candidate_sha256 == second.definition_candidate_sha256
    assert first.question_candidate_sha256 == second.question_candidate_sha256


def test_two_process_convergence_has_one_commit_and_no_second_commit(tmp_path: Path) -> None:
    workspace, question_id = _answered_workspace(tmp_path)
    preview = workspace.preview_project_readiness_convergence([question_id], actor="owner")
    context = multiprocessing.get_context("fork")
    start_event = context.Event()
    results = context.Queue()
    processes = [
        context.Process(
            target=_concurrent_convergence_worker,
            args=(
                str(tmp_path),
                question_id,
                preview.preview.preview_token,
                start_event,
                results,
            ),
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
    assert set(statuses) <= {"applied", "already_applied", "stale_preview", "blocked"}
    question = workspace.project_question(question_id)
    matching = [
        item
        for item in question.applications
        if item.preview_token == preview.preview.preview_token
    ]
    assert len(matching) == 1


def test_same_vertical_reconciliation_preserves_answer_and_can_be_applied_by_known_actor(tmp_path: Path) -> None:
    workspace, question_id = _answered_workspace(tmp_path)

    selected = workspace.select_project_vertical("base_project", actor="owner")
    assert selected.reconciliation_required is True
    assert "reconcile-preview" in selected.reconciliation_command

    preview = workspace.preview_project_question_reconciliation(actor="contributor")
    assert question_id in preview.revised_ids
    assert preview.owner_apply_required is False
    assert preview.preview.apply_allowed is True

    result = workspace.apply_project_question_reconciliation(
        actor="contributor",
        preview_token=preview.preview.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    question = workspace.project_question(question_id)
    assert question.state == ProjectQuestionState.ANSWERED
    assert question.applicability == ProjectQuestionApplicability.ACTIVE
    assert question.answers[-1].values["value"] == "Owner supplied value"
    assert workspace.active_project_vertical().reconciliation_required is False


def test_cross_vertical_reconciliation_never_moves_answer_to_new_question(tmp_path: Path) -> None:
    workspace, old_question_id = _answered_workspace(tmp_path)
    selected = workspace.select_project_vertical("software_project", actor="owner")
    assert selected.reconciliation_required is True

    contributor = workspace.preview_project_question_reconciliation(actor="contributor")
    assert contributor.owner_apply_required is True
    assert contributor.preview.apply_allowed is False
    assert old_question_id in contributor.inactive_evidence_ids

    owner = workspace.preview_project_question_reconciliation(actor="owner")
    result = workspace.apply_project_question_reconciliation(
        actor="owner",
        preview_token=owner.preview.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    artifact = workspace.project_questions()
    old = next(item for item in artifact.questions if item.question_id == old_question_id)
    assert old.state == ProjectQuestionState.ANSWERED
    assert old.applicability == ProjectQuestionApplicability.TARGET_REMOVED
    assert old.answers[-1].values["value"] == "Owner supplied value"
    new_questions = [item for item in artifact.questions if item.question_id != old_question_id]
    assert new_questions
    assert all(not item.answers for item in new_questions)


def test_module_change_reconciliation_preserves_only_matching_owner_evidence(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Module Reconciliation",
        owner="owner",
        project_domain="software",
        vertical_id="software_project",
    )
    question = workspace.next_project_question()
    assert question is not None
    workspace.answer_project_question(
        question.question_id,
        values={"value": "Owner evidence before module selection"},
        actor="owner",
        expected_revision=question.revision,
    )

    selected = workspace.select_project_vertical(
        "software_project",
        actor="owner",
        modules=["software_spec_lifecycle"],
    )
    assert selected.reconciliation_required is True
    preview = workspace.preview_project_question_reconciliation(actor="owner")
    result = workspace.apply_project_question_reconciliation(
        actor="owner",
        preview_token=preview.preview.preview_token,
        confirm=True,
    )

    assert result.status == "applied"
    artifact = workspace.project_questions()
    original = next(item for item in artifact.questions if item.question_id == question.question_id)
    assert len(original.answers) == 1
    assert original.answers[0].values["value"] == "Owner evidence before module selection"
    assert all(
        not item.answers
        for item in artifact.questions
        if item.question_id != question.question_id
    )

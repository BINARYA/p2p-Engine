from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.storage.filesystem import P2PWorkspace


runner = CliRunner()


def _workspace(root: Path) -> tuple[P2PWorkspace, str]:
    workspace = P2PWorkspace(root)
    workspace.init_project("CLI Readiness", owner="owner", vertical_id="base_project")
    question = workspace.next_project_question()
    assert question is not None
    return workspace, question.question_id


def test_cli_readiness_review_gaps_and_questions_are_bounded_json_reads(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    questions_path = tmp_path / ".p2p" / "project" / "questions.yml"
    before = questions_path.read_bytes()

    review = runner.invoke(
        app,
        ["project", "readiness", "review", "--format", "json", "--limit", "2", "--root", str(tmp_path)],
    )
    gaps = runner.invoke(
        app,
        ["project", "readiness", "gaps", "--format", "json", "--limit", "2", "--root", str(tmp_path)],
    )
    questions = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "questions",
            "status",
            "--format",
            "json",
            "--limit",
            "2",
            "--root",
            str(tmp_path),
        ],
    )

    assert review.exit_code == gaps.exit_code == questions.exit_code == 0
    assert json.loads(review.output)["project_readiness"]["gaps"]["limit"] == 2
    assert json.loads(gaps.output)["project_readiness_page"]["limit"] == 2
    question_payload = json.loads(questions.output)["project_questions"]
    assert question_payload["limit"] == 2
    assert any(item["id"] == question_id for item in question_payload["items"])
    assert questions_path.read_bytes() == before


def test_cli_answer_preview_apply_and_exact_retry(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    question = workspace.project_question(question_id)
    answered = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "questions",
            "answer",
            question_id,
            "--value",
            "Owner answer",
            "--actor",
            "owner",
            "--expected-revision",
            str(question.revision),
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert answered.exit_code == 0
    assert json.loads(answered.output)["project_question"]["status"] == "applied"

    preview = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "preview",
            "--question",
            question_id,
            "--actor",
            "owner",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert preview.exit_code == 0
    token = json.loads(preview.output)["project_readiness_preview"]["preview"]["preview_token"]

    blocked = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "apply",
            "--question",
            question_id,
            "--preview-token",
            token,
            "--actor",
            "owner",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert blocked.exit_code == 1
    assert json.loads(blocked.output)["project_readiness_apply"]["status"] == "blocked"

    applied = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "apply",
            "--question",
            question_id,
            "--preview-token",
            token,
            "--actor",
            "owner",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    replay = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "apply",
            "--question",
            question_id,
            "--preview-token",
            token,
            "--actor",
            "owner",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert applied.exit_code == replay.exit_code == 0
    assert json.loads(applied.output)["project_readiness_apply"]["status"] == "applied"
    assert json.loads(replay.output)["project_readiness_apply"]["status"] == "already_applied"


def test_cli_structured_answer_is_root_bounded_and_derives_owner_identity(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    question = workspace.project_question(question_id)
    answer_path = tmp_path / "answer.yml"
    answer_path.write_text(
        yaml.safe_dump(
            {
                "project_question_answer": {
                    "schema_version": 1,
                    "question_id": question_id,
                    "expected_revision": question.revision,
                    "values": {"value": "Structured owner answer"},
                    "evidence_refs": [],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "questions",
            "answer",
            question_id,
            "--input",
            str(answer_path),
            "--actor",
            "owner",
            "--expected-revision",
            str(question.revision),
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    stored = workspace.project_question(question_id).answers[-1]
    assert stored.provided_by == stored.recorded_by == "owner"


def test_cli_answer_file_rejects_symlink_and_oversized_payload_with_structured_error(
    tmp_path: Path,
) -> None:
    workspace, question_id = _workspace(tmp_path)
    question = workspace.project_question(question_id)
    real = tmp_path / "real-answer.yml"
    real.write_text("project_question_answer: {}\n", encoding="utf-8")
    linked = tmp_path / "linked-answer.yml"
    linked.symlink_to(real)

    symlink = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "questions",
            "answer",
            question_id,
            "--input",
            str(linked),
            "--actor",
            "owner",
            "--expected-revision",
            str(question.revision),
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert symlink.exit_code == 1
    assert json.loads(symlink.output)["error"]["mutation_performed"] is False

    oversized = tmp_path / "oversized-answer.yml"
    oversized.write_bytes(b"x" * (64 * 1024 + 1))
    too_large = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "questions",
            "answer",
            question_id,
            "--input",
            str(oversized),
            "--actor",
            "owner",
            "--expected-revision",
            str(question.revision),
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    error = json.loads(too_large.output)["error"]
    assert too_large.exit_code == 1
    assert error["code"] == "P2P353_READINESS_PAYLOAD_LIMIT"
    assert error["mutation_performed"] is False


def test_cli_question_lifecycle_commands_preserve_expected_revision_contract(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    revision = workspace.project_question(question_id).revision

    deferred = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "questions",
            "defer",
            question_id,
            "--reason",
            "Wait for evidence",
            "--actor",
            "owner",
            "--expected-revision",
            str(revision),
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert deferred.exit_code == 0
    deferred_payload = json.loads(deferred.output)["project_question"]
    assert deferred_payload["question"]["state"] == "deferred"

    stale = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "questions",
            "reopen",
            question_id,
            "--reason",
            "Try stale revision",
            "--actor",
            "owner",
            "--expected-revision",
            str(revision),
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert stale.exit_code == 1
    assert json.loads(stale.output)["error"]["code"] == "P2P345_PROJECT_READINESS_STALE_PREVIEW"

    reopened = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "questions",
            "reopen",
            question_id,
            "--reason",
            "Evidence is ready",
            "--actor",
            "owner",
            "--expected-revision",
            str(revision + 1),
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert reopened.exit_code == 0
    assert json.loads(reopened.output)["project_question"]["question"]["state"] == "to_answer"


def test_cli_question_reconciliation_preview_and_apply_use_owner_token(tmp_path: Path) -> None:
    workspace, question_id = _workspace(tmp_path)
    question = workspace.project_question(question_id)
    workspace.answer_project_question(
        question_id,
        values={"value": "Owner answer before lock refresh"},
        actor="owner",
        expected_revision=question.revision,
    )
    workspace.select_project_vertical("base_project", actor="owner")

    preview = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "questions",
            "reconcile-preview",
            "--actor",
            "owner",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )
    assert preview.exit_code == 0
    preview_payload = json.loads(preview.output)["project_question_reconciliation"]
    token = preview_payload["preview"]["preview_token"]

    applied = runner.invoke(
        app,
        [
            "project",
            "readiness",
            "questions",
            "reconcile-apply",
            "--preview-token",
            token,
            "--actor",
            "owner",
            "--confirm",
            "--format",
            "json",
            "--root",
            str(tmp_path),
        ],
    )

    assert applied.exit_code == 0
    payload = json.loads(applied.output)["project_question_reconciliation"]
    assert payload["status"] == "applied"
    assert payload["mutation_performed"] is True

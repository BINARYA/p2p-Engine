from __future__ import annotations

import yaml

from p2p_engine.core.proposal_questions import ProposalQuestionPriority, ProposalQuestionState
from p2p_engine.services.proposal_questions import ProposalQuestionService
from p2p_engine.services.proposals import ProposalDocumentService


def _services(tmp_path):
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    questions = ProposalQuestionService(root=tmp_path, find_proposal_dir=proposals.find_dir)
    return proposals, questions


def test_proposal_question_service_handles_missing_state_and_lifecycle(tmp_path) -> None:
    proposals, questions = _services(tmp_path)
    proposal = proposals.create("Question Flow")

    missing = questions.read(proposal.proposal_id)
    assert missing.status == "not_initialized"
    assert missing.questions == []

    initialized = questions.initialize(proposal.proposal_id, actor="codex")
    added = questions.add(
        proposal.proposal_id,
        gap="alternatives_quality",
        question="Which alternative should be compared first?",
        priority=ProposalQuestionPriority.high,
        rationale="Readiness is missing alternatives.",
        actor="codex",
    )
    answered = questions.answer(
        proposal.proposal_id,
        added.question.question_id,
        "Use a first-class CLI object.",
        source="owner",
        actor="codex",
    )
    deferred = questions.add(
        proposal.proposal_id,
        gap="risk_coverage",
        question="Which risk matters most?",
        priority=ProposalQuestionPriority.medium,
        actor="codex",
    )
    questions.set_state(
        proposal.proposal_id,
        deferred.question.question_id,
        ProposalQuestionState.defer,
        reason="Ask after alternatives.",
        actor="codex",
    )
    replacement = questions.add(
        proposal.proposal_id,
        gap="risk_coverage",
        question="Which implementation risk matters most?",
        priority=ProposalQuestionPriority.medium,
        actor="codex",
    )
    superseded = questions.supersede(
        proposal.proposal_id,
        deferred.question.question_id,
        replacement.question.question_id,
        actor="codex",
    )
    retired = questions.set_state(
        proposal.proposal_id,
        replacement.question.question_id,
        ProposalQuestionState.retired,
        reason="No longer needed.",
        actor="codex",
    )

    view = questions.read(proposal.proposal_id)
    next_question = questions.next_question(proposal.proposal_id)
    apply = questions.apply_summary(proposal.proposal_id, actor="codex")
    applied_view = questions.read(proposal.proposal_id)

    assert initialized.status == "initialized"
    assert added.question.question_id == "Q001"
    assert added.question.group_id == "QG001"
    assert answered.question.state == ProposalQuestionState.answered
    assert superseded.question.state == ProposalQuestionState.superseded
    assert superseded.question.superseded_by == "Q003"
    assert retired.question.state == ProposalQuestionState.retired
    assert len(view.questions) == 3
    assert next_question is None
    assert "Q001" in apply.summary
    assert apply.update_plan
    assert apply.update_plan[0].artifact == "proposal.md"
    assert any(item.artifact == "alternatives.md" for item in apply.update_plan)
    assert applied_view.questions[0].state == ProposalQuestionState.applied
    assert applied_view.questions[0].apply_plan


def test_proposal_question_service_group_state_and_validation(tmp_path) -> None:
    proposals, questions = _services(tmp_path)
    proposal = proposals.create("Question Groups")
    added = questions.add(
        proposal.proposal_id,
        gap="owner_questions_resolution",
        question="What owner input is missing?",
        actor="codex",
    )

    muted = questions.group_state(proposal.proposal_id, added.question.group_id, ProposalQuestionState.muted)
    assert muted.groups[0].state == ProposalQuestionState.muted
    assert questions.next_question(proposal.proposal_id) is None
    assert questions.next_question(proposal.proposal_id, include_muted=True).question_id == "Q001"

    question_path = tmp_path / added.path
    payload = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    payload["proposal_questions"]["questions"][0]["state"] = "invalid"
    question_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    try:
        questions.read(proposal.proposal_id)
    except ValueError as exc:
        assert "Invalid proposal question" in str(exc)
    else:
        raise AssertionError("invalid question state should fail validation")

from __future__ import annotations

import yaml

from p2p_engine.core.proposal_questions import ProposalQuestionPriority, ProposalQuestionState
from p2p_engine.services.proposal_questions import ProposalQuestionService
from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.services.readiness import ReadinessService
from p2p_engine.core.proposal_artifact_state import ProposalArtifactStatus
from p2p_engine.storage.filesystem import P2PWorkspace


def _services(tmp_path):
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    readiness = ReadinessService(root=tmp_path, p2p_dir=tmp_path / ".p2p", find_proposal_dir=proposals.find_dir)
    return proposals, readiness


def _services_with_questions(tmp_path):
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    readiness = ReadinessService(root=tmp_path, p2p_dir=tmp_path / ".p2p", find_proposal_dir=proposals.find_dir)
    questions = ProposalQuestionService(root=tmp_path, find_proposal_dir=proposals.find_dir)
    return proposals, readiness, questions


def _complete_readiness_proposal(tmp_path, proposals, *, title: str = "Structured Question Readiness"):
    proposal = proposals.create_with_details(
        title=title,
        problem=(
            "This proposal describes a concrete readiness question-state problem with enough detail "
            "to support evidence-aware readiness assessment from current artifacts."
        ),
        goals=[
            "Use structured question state as readiness evidence while preserving owner governance boundaries."
        ],
        non_goals=["Do not make owner governance decisions."],
        proposal="Assess owner-question readiness from structured lifecycle state when available.",
        acceptance_criteria=[
            "Readiness assessment reports structured owner-question categories and ignores stale markdown blockers."
        ],
    )
    proposal_dir = tmp_path / proposal.path
    (proposal_dir / "alternatives.md").write_text(
        "# Alternatives\n\nUse structured question state when available, or keep markdown fallback for legacy proposals.\n",
        encoding="utf-8",
    )
    (proposal_dir / "findings.md").write_text(
        "# Findings\n\nStructured question lifecycle state avoids stale markdown false blockers while preserving fallback compatibility.\n",
        encoding="utf-8",
    )
    (proposal_dir / "risks.md").write_text(
        "# Risks\n\nThe main risk is hiding real owner input gaps, mitigated by making high-priority to_answer questions explicit blockers.\n",
        encoding="utf-8",
    )
    (proposal_dir / "assumptions.md").write_text(
        "# Assumptions\n\nProposal question state validates before readiness consumes it, and markdown remains fallback for legacy proposals.\n",
        encoding="utf-8",
    )
    (proposal_dir / "suggested-scope.md").write_text(
        "# Scope\n\nProposal-level readiness question state is in scope; whole-project readiness and governance decisions are out of scope.\n",
        encoding="utf-8",
    )
    (proposal_dir / "impact-map.yml").write_text(
        "impact:\n  proposal: PROP-001\n  features:\n    - structured proposal question state convergence for readiness\n",
        encoding="utf-8",
    )
    (proposal_dir / "execution-plan.md").write_text(
        "# Execution Plan\n\nAdd focused readiness service tests, preserve public CLI and MCP contracts, and validate legacy fallback.\n",
        encoding="utf-8",
    )
    return proposal, proposal_dir


def _question_ids(owner_question_state: dict[str, object], key: str) -> list[str]:
    return [str(item["id"]) for item in owner_question_state.get(key, [])]


def test_readiness_service_profile_missing_write_read_and_override(tmp_path) -> None:
    proposals, readiness = _services(tmp_path)
    proposal = proposals.create("Readiness Work")

    profile = readiness.profile()
    missing = readiness.read(proposal.proposal_id)

    assert profile.profile_id == "default-readiness-v0.1"
    assert profile.version == "0.1"
    assert missing.status == "not_assessed"
    assert missing.computed_score is None

    path = readiness.write(
        proposal.proposal_id,
        {
            "status": "assessed",
            "profile_id": profile.profile_id,
            "profile_version": profile.version,
            "computed_score": 82,
            "computed_label": "partial",
            "confidence": "medium",
            "failed_gates": ["owner_questions_resolution"],
            "missing": ["acceptance_criteria_quality"],
            "suggested_next": ["define_acceptance_criteria"],
        },
    )
    read = readiness.read(proposal.proposal_id)
    override_path = readiness.record_override(proposal.proposal_id, "Owner accepts intentionally.", "owner")
    payload = yaml.safe_load((tmp_path / override_path).read_text(encoding="utf-8"))["readiness"]

    assert path == proposal.path / "readiness.yml"
    assert read.computed_score == 82
    assert read.failed_gates == ["owner_questions_resolution"]
    assert payload["owner_override"] is True
    assert payload["effective_status"] == "forced_ready"
    assert payload["effective_score"] == 100


def test_readiness_service_refresh_and_initialize_scoring(tmp_path) -> None:
    proposals, readiness = _services(tmp_path)
    proposal = proposals.create_with_details(
        title="Readiness Workflow",
        problem="This proposal explains the problem with enough meaningful detail to exceed thin content thresholds.",
        goals=["Expose a conservative readiness assessment with advisory gaps and next actions."],
        acceptance_criteria=["Readiness artifacts exist and remain advisory."],
    )
    profile = readiness.profile()
    readiness.write(
        proposal.proposal_id,
        {
            "status": "assessed",
            "profile_id": profile.profile_id,
            "profile_version": profile.version,
            "confidence": "medium",
            "criteria": {
                "problem_clarity": {"awarded_points": 10, "artifact_quality": "ready"},
                "owner_questions_resolution": {"awarded_points": 10, "artifact_quality": "needs_owner_input"},
            },
            "missing": ["acceptance_criteria_quality"],
            "suggested_next": ["define_acceptance_criteria"],
            "failed_gates": [],
        },
    )

    refreshed = readiness.refresh(proposal.proposal_id)
    initialized = readiness.initialize(proposal.proposal_id)

    assert refreshed.computed_score == 17
    assert refreshed.computed_label == "weak"
    assert refreshed.failed_gates == ["owner_questions_resolution:needs_owner_input"]
    assert "acceptance_criteria_quality" in refreshed.missing
    assert initialized.status == "assessed"
    assert initialized.computed_score is not None
    assert initialized.confidence == "low"


def test_readiness_service_assess_promotes_complete_artifact_evidence(tmp_path) -> None:
    proposals, readiness = _services(tmp_path)
    proposal = proposals.create_with_details(
        title="Complete Readiness",
        problem=(
            "This proposal explains a concrete readiness problem with enough detail for assessment: "
            "refresh remains conservative while current artifacts may already contain complete evidence."
        ),
        goals=[
            "Generate evidence-aware readiness from complete proposal artifacts and question state without changing owner governance decisions."
        ],
        non_goals=["Do not make owner governance decisions."],
        proposal="Use current artifacts and question state to assess proposal readiness.",
        acceptance_criteria=[
            "Readiness assess can promote confidence when evidence is complete and no blocking owner questions or high-priority questions remain."
        ],
    )
    proposal_dir = tmp_path / proposal.path
    (proposal_dir / "alternatives.md").write_text(
        "# Alternatives\n\nUse assess instead of overloading refresh because refresh must remain a conservative compatibility command.\n",
        encoding="utf-8",
    )
    (proposal_dir / "findings.md").write_text(
        "# Findings\n\nAssess gives qualitative recalculation while refresh stays conservative and explainable for existing users.\n",
        encoding="utf-8",
    )
    (proposal_dir / "risks.md").write_text(
        "# Risks\n\nThe main risk is accidental governance automation, mitigated by keeping owner decisions outside readiness commands.\n",
        encoding="utf-8",
    )
    (proposal_dir / "assumptions.md").write_text(
        "# Assumptions\n\nQuestion state and artifacts are available locally and can be inspected without external model calls.\n",
        encoding="utf-8",
    )
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\nOwner-facing questions have been resolved and no additional decision-blocking questions remain for this proposal.\n",
        encoding="utf-8",
    )
    (proposal_dir / "suggested-scope.md").write_text(
        "# Scope\n\nReadiness assess is in scope for this proposal, while autonomous governance decisions remain out of scope.\n",
        encoding="utf-8",
    )
    (proposal_dir / "impact-map.yml").write_text(
        "impact:\n  proposal: PROP-001\n  features:\n    - evidence-aware readiness assessment with current artifact inspection and question-state awareness\n",
        encoding="utf-8",
    )
    (proposal_dir / "execution-plan.md").write_text(
        "# Execution Plan\n\nVerify evidence-aware readiness assessment, preserve owner governance boundaries, and keep refresh conservative.\n",
        encoding="utf-8",
    )

    initialized = readiness.initialize(proposal.proposal_id)
    assessed = readiness.assess(proposal.proposal_id)

    assert initialized.computed_score == 70
    assert initialized.confidence == "low"
    assert assessed.computed_score == 100
    assert assessed.computed_label == "decision_ready"
    assert assessed.confidence == "high"
    assert assessed.missing == []
    assert assessed.failed_gates == []


def test_readiness_review_reports_advisory_merge_candidates(tmp_path) -> None:
    proposals, readiness = _services(tmp_path)
    first = proposals.create_with_details(
        title="Artifact Aware Readiness",
        problem="Proposal questions need artifact aware readiness coverage and answer application.",
        proposal="Generate artifact aware readiness questions and apply answers to proposal artifacts.",
    )
    second = proposals.create_with_details(
        title="Artifact Aware Question Coverage",
        problem="Proposal questions need artifact aware readiness coverage across proposal artifacts.",
        proposal="Generate artifact aware readiness questions and apply answers to proposal artifacts.",
    )

    readiness.initialize(first.proposal_id)
    review = readiness.review(first.proposal_id)

    assert any(second.proposal_id in candidate for candidate in review.merge_candidates)
    assert proposals.show(first.proposal_id).status == "draft"
    assert proposals.show(second.proposal_id).status == "draft"


def test_readiness_assess_consumes_artifact_state_gaps_and_owner_visible_cautions(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    proposal = workspace.create_proposal_with_details(
        title="Artifact Aware Readiness",
        proposal="This changes CLI, MCP, storage, and source-of-truth behavior.",
    )
    workspace.set_proposal_artifact_state(
        proposal.proposal_id,
        "impact_map",
        status=ProposalArtifactStatus.not_applicable,
        reason="Agent thinks this has no impact.",
        actor="codex",
    )

    assessed = workspace.assess_proposal_readiness(proposal.proposal_id)
    review = workspace.review_proposal_readiness(proposal.proposal_id)

    assert any(item.startswith("artifact:findings:") for item in assessed.missing)
    assert any("p2p proposal artifact status PROP-001" in item for item in assessed.suggested_next)
    assert any("impact_map is not_applicable" in warning for warning in review.thin_artifact_warnings)
    assert any("p2p proposal artifact confirm PROP-001 impact_map" in item for item in review.suggested_next)


def test_readiness_assess_uses_structured_questions_over_stale_markdown(tmp_path) -> None:
    proposals, readiness, questions = _services_with_questions(tmp_path)
    proposal, proposal_dir = _complete_readiness_proposal(tmp_path, proposals)
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\n- Should this already-applied owner answer still block readiness?\n",
        encoding="utf-8",
    )
    added = questions.add(
        proposal.proposal_id,
        gap="owner_questions_resolution",
        question="Should structured questions be authoritative?",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )
    questions.answer(
        proposal.proposal_id,
        added.question.question_id,
        "Yes, structured question state is authoritative when present.",
        actor="codex",
    )
    questions.apply_summary(proposal.proposal_id, actor="codex")

    assessed = readiness.assess(proposal.proposal_id)

    assert assessed.computed_score == 100
    assert assessed.failed_gates == []
    assert assessed.owner_question_state["source"] == "structured"
    assert assessed.owner_question_state["markdown_fallback_used"] is False
    assert assessed.owner_question_state["blocking_owner_questions"] == []
    assert _question_ids(assessed.owner_question_state, "closed_questions") == ["Q001"]


def test_readiness_assess_reports_high_priority_structured_blocker(tmp_path) -> None:
    proposals, readiness, questions = _services_with_questions(tmp_path)
    proposal, proposal_dir = _complete_readiness_proposal(tmp_path, proposals)
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\nNo markdown blocker should be needed when structured questions exist.\n",
        encoding="utf-8",
    )
    questions.add(
        proposal.proposal_id,
        gap="owner_questions_resolution",
        question="Which owner decision is still missing?",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )

    assessed = readiness.assess(proposal.proposal_id)

    assert "owner_questions_resolution:needs_owner_input" in assessed.failed_gates
    assert _question_ids(assessed.owner_question_state, "blocking_owner_questions") == ["Q001"]
    assert "Q001" in " ".join(assessed.owner_question_state["confidence_notes"])


def test_readiness_assess_reports_answered_questions_without_missing_owner_input(tmp_path) -> None:
    proposals, readiness, questions = _services_with_questions(tmp_path)
    proposal, proposal_dir = _complete_readiness_proposal(tmp_path, proposals)
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\n- This stale markdown question should not reopen an answered structured question?\n",
        encoding="utf-8",
    )
    added = questions.add(
        proposal.proposal_id,
        gap="owner_questions_resolution",
        question="Has the owner answered the source-of-truth question?",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )
    questions.answer(
        proposal.proposal_id,
        added.question.question_id,
        "Yes, but the answer still needs to be applied to artifacts.",
        actor="codex",
    )

    assessed = readiness.assess(proposal.proposal_id)

    assert "owner_questions_resolution:needs_owner_input" not in assessed.failed_gates
    assert _question_ids(assessed.owner_question_state, "answered_not_applied") == ["Q001"]
    assert assessed.owner_question_state["blocking_owner_questions"] == []
    assert any("p2p proposal questions apply" in item for item in assessed.suggested_next)


def test_readiness_assess_closes_retired_and_superseded_questions(tmp_path) -> None:
    proposals, readiness, questions = _services_with_questions(tmp_path)
    proposal, proposal_dir = _complete_readiness_proposal(tmp_path, proposals)
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\n- Old markdown question text should not reopen closed structured questions?\n",
        encoding="utf-8",
    )
    retired = questions.add(
        proposal.proposal_id,
        gap="owner_questions_resolution",
        question="Should this retired question block?",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )
    questions.set_state(
        proposal.proposal_id,
        retired.question.question_id,
        ProposalQuestionState.retired,
        reason="No longer relevant.",
        actor="codex",
    )
    old = questions.add(
        proposal.proposal_id,
        gap="acceptance_criteria_quality",
        question="Should this superseded question block?",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )
    replacement = questions.add(
        proposal.proposal_id,
        gap="acceptance_criteria_quality",
        question="Replacement question that is no longer needed.",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )
    questions.supersede(proposal.proposal_id, old.question.question_id, replacement.question.question_id, actor="codex")
    questions.set_state(
        proposal.proposal_id,
        replacement.question.question_id,
        ProposalQuestionState.retired,
        reason="Replacement also retired.",
        actor="codex",
    )

    assessed = readiness.assess(proposal.proposal_id)

    assert assessed.failed_gates == []
    assert _question_ids(assessed.owner_question_state, "closed_questions") == ["Q001", "Q002", "Q003"]


def test_readiness_assess_treats_muted_deferred_and_lower_priority_questions_as_residual(tmp_path) -> None:
    proposals, readiness, questions = _services_with_questions(tmp_path)
    proposal, _proposal_dir = _complete_readiness_proposal(tmp_path, proposals)
    muted_group = questions.add(
        proposal.proposal_id,
        gap="owner_questions_resolution",
        question="Muted group question?",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )
    questions.group_state(proposal.proposal_id, muted_group.question.group_id, ProposalQuestionState.muted, actor="codex")
    deferred_question = questions.add(
        proposal.proposal_id,
        gap="risk_coverage",
        question="Deferred high-priority question?",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )
    questions.set_state(
        proposal.proposal_id,
        deferred_question.question.question_id,
        ProposalQuestionState.defer,
        reason="Review later.",
        actor="codex",
    )
    questions.add(
        proposal.proposal_id,
        gap="assumptions_clarity",
        question="Medium follow-up question?",
        priority=ProposalQuestionPriority.medium,
        actor="codex",
    )
    questions.add(
        proposal.proposal_id,
        gap="impact_overlap_analysis",
        question="Low follow-up question?",
        priority=ProposalQuestionPriority.low,
        actor="codex",
    )

    assessed = readiness.assess(proposal.proposal_id)

    assert "owner_questions_resolution:needs_owner_input" not in assessed.failed_gates
    assert assessed.owner_question_state["blocking_owner_questions"] == []
    assert _question_ids(assessed.owner_question_state, "residual_follow_up") == ["Q001", "Q002", "Q003", "Q004"]
    assert assessed.confidence == "medium"


def test_readiness_assess_preserves_markdown_fallback_without_structured_questions(tmp_path) -> None:
    proposals, readiness = _services(tmp_path)
    proposal, proposal_dir = _complete_readiness_proposal(tmp_path, proposals)
    (proposal_dir / "open-questions.md").write_text(
        "# Open Questions\n\n- Which owner input is still missing?\n",
        encoding="utf-8",
    )

    assessed = readiness.assess(proposal.proposal_id)

    assert "owner_questions_resolution:needs_owner_input" in assessed.failed_gates
    assert assessed.owner_question_state["source"] == "markdown_fallback"
    assert assessed.owner_question_state["markdown_fallback_used"] is True
    assert assessed.owner_question_state["blocking_owner_questions"]


def test_readiness_assess_rejects_invalid_structured_question_state(tmp_path) -> None:
    proposals, readiness, questions = _services_with_questions(tmp_path)
    proposal, _proposal_dir = _complete_readiness_proposal(tmp_path, proposals)
    questions.add(
        proposal.proposal_id,
        gap="owner_questions_resolution",
        question="Invalid state should fail validation?",
        actor="codex",
    )
    question_path = tmp_path / proposal.path / "questions.yml"
    payload = yaml.safe_load(question_path.read_text(encoding="utf-8"))
    payload["proposal_questions"]["questions"][0]["state"] = "invalid"
    question_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    try:
        readiness.assess(proposal.proposal_id)
    except ValueError as exc:
        assert "Invalid proposal question" in str(exc)
    else:
        raise AssertionError("invalid structured question state should fail readiness assessment")


def test_readiness_review_reports_structured_question_categories(tmp_path) -> None:
    proposals, readiness, questions = _services_with_questions(tmp_path)
    proposal, _proposal_dir = _complete_readiness_proposal(tmp_path, proposals)
    blocking = questions.add(
        proposal.proposal_id,
        gap="owner_questions_resolution",
        question="Blocking question?",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )
    answered = questions.add(
        proposal.proposal_id,
        gap="acceptance_criteria_quality",
        question="Answered but unapplied question?",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )
    questions.answer(
        proposal.proposal_id,
        answered.question.question_id,
        "Answered but not applied yet.",
        actor="codex",
    )
    applied = questions.add(
        proposal.proposal_id,
        gap="risk_coverage",
        question="Already applied question?",
        priority=ProposalQuestionPriority.high,
        actor="codex",
    )
    questions.set_state(
        proposal.proposal_id,
        applied.question.question_id,
        ProposalQuestionState.applied,
        reason="Already applied.",
        actor="codex",
    )
    readiness.assess(proposal.proposal_id)

    review = readiness.review(proposal.proposal_id)

    assert _question_ids(review.owner_question_state, "blocking_owner_questions") == [blocking.question.question_id]
    assert _question_ids(review.owner_question_state, "answered_not_applied") == [answered.question.question_id]
    assert applied.question.question_id in _question_ids(review.owner_question_state, "closed_questions")
    assert any(blocking.question.question_id in question for question in review.owner_questions)
    assert not any(applied.question.question_id in question for question in review.owner_questions)

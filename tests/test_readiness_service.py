from __future__ import annotations

import yaml

from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.services.readiness import ReadinessService
from p2p_engine.core.proposal_artifact_state import ProposalArtifactStatus
from p2p_engine.storage.filesystem import P2PWorkspace


def _services(tmp_path):
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    readiness = ReadinessService(root=tmp_path, p2p_dir=tmp_path / ".p2p", find_proposal_dir=proposals.find_dir)
    return proposals, readiness


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

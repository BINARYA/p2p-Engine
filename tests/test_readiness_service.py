from __future__ import annotations

import yaml

from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.services.readiness import ReadinessService


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

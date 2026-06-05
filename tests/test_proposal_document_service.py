from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from p2p_engine.core.contribution import ContributionType
from p2p_engine.services.proposals import ProposalDocumentService


def _service(root: Path) -> ProposalDocumentService:
    return ProposalDocumentService(root=root, p2p_dir=root / ".p2p")


def test_proposal_document_service_create_show_update_and_contributions(tmp_path: Path) -> None:
    service = _service(tmp_path)

    proposal = service.create_with_details(
        title="Prompt generator hardening",
        problem="Generated prompts inherit too many placeholders.",
        goals=["Make prompts useful with incomplete proposals."],
        proposal="Add structured proposal metadata and prompt context.",
        acceptance_criteria=["Digest prompts call out missing information."],
    )

    assert proposal.proposal_id == "PROP-001"
    assert proposal.slug == "prompt-generator-hardening"
    detail = service.show("PROP-001")
    assert detail.title == "Prompt generator hardening"
    assert detail.problem == "Generated prompts inherit too many placeholders."
    assert detail.proposal == "Add structured proposal metadata and prompt context."

    updated_path = service.update("PROP-001", problem="The prompt has too little context.")
    updated_text = (tmp_path / updated_path).read_text(encoding="utf-8")
    assert "The prompt has too little context." in updated_text
    assert "## Context\n\nPending." in updated_text

    contribution = service.add_contribution(
        "PROP-001",
        ContributionType.objective,
        text="Explore rough ideas before synthesis.",
        relevance_hint="high",
        author="owner",
    )
    listed = service.list_contributions("PROP-001")

    assert contribution.contribution_id == "C001"
    assert listed.contributions[0].text == "Explore rough ideas before synthesis."


def test_proposal_document_service_lookup_and_duplicate_detection(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create("Draft Work")
    proposals_dir = tmp_path / ".p2p" / "proposals"
    shutil.copytree(proposals_dir / "PROP-001-draft-work", proposals_dir / "PROP-001-other-draft")

    duplicates = service.duplicate_ids()

    assert "PROP-001" in duplicates
    with pytest.raises(ValueError, match="Ambiguous proposal ID: PROP-001"):
        service.find_dir("PROP-001")

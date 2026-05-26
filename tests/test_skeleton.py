from p2p_engine.core.contribution import ContributionType
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace


def test_domain_enums_expose_expected_values() -> None:
    assert ContributionType.suggestion.value == "suggestion"
    assert DecisionOutcome.accepted.value == "accepted"


def test_create_proposal_with_details_writes_useful_sections(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")

    proposal = workspace.create_proposal_with_details(
        title="Prompt generator hardening",
        problem="Generated prompts inherit too many placeholders.",
        goals=["Make prompts useful with incomplete proposals."],
        proposal="Add structured proposal metadata and prompt context.",
        acceptance_criteria=["Digest prompts call out missing information."],
    )

    content = (tmp_path / proposal.path / "proposal.md").read_text(encoding="utf-8")

    assert "Generated prompts inherit too many placeholders." in content
    assert "- Make prompts useful with incomplete proposals." in content
    assert "Add structured proposal metadata and prompt context." in content
    assert "- Digest prompts call out missing information." in content


def test_update_proposal_replaces_only_requested_sections(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")
    proposal = workspace.create_proposal("Prompt generator hardening")

    workspace.update_proposal(
        proposal.proposal_id,
        problem="The prompt has too little context.",
        goals=["Add governance context."],
    )

    content = (tmp_path / proposal.path / "proposal.md").read_text(encoding="utf-8")

    assert "The prompt has too little context." in content
    assert "- Add governance context." in content
    assert "## Context\n\nPending." in content


def test_digest_prompt_includes_governance_and_missing_info_instruction(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")
    proposal = workspace.create_proposal("Prompt generator hardening")

    prompt_path = workspace.generate_prompt(proposal.proposal_id, "digest")
    content = (tmp_path / prompt_path).read_text(encoding="utf-8")

    assert "Treat `Pending.`" in content
    assert "## Governance Context" in content
    assert "### Decision Rules" in content


def test_explore_prompt_and_status_track_exploration_artifacts(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")
    proposal = workspace.create_proposal("Exploration Phase")

    prompt_path = workspace.generate_prompt(proposal.proposal_id, "explore")
    prompt = (tmp_path / prompt_path).read_text(encoding="utf-8")
    status = workspace.exploration_status(proposal.proposal_id)

    assert "P2P Exploration Prompt" in prompt
    assert "findings.md" in prompt
    assert "p2p explore prompt PROP-001" == status.suggested_next_command
    assert any(artifact.filename == "findings.md" for artifact in status.artifacts)


def test_import_exploration_file_updates_exploration_artifact(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")
    proposal = workspace.create_proposal("Exploration Phase")
    source = tmp_path / "exploration-output.md"
    source.write_text("# Exploration\n\nA concrete finding.\n", encoding="utf-8")

    imported = workspace.import_exploration(proposal.proposal_id, source)
    content = (tmp_path / proposal.path / "exploration.md").read_text(encoding="utf-8")

    assert imported == [proposal.path / "exploration.md"]
    assert "A concrete finding." in content

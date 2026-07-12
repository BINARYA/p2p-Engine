from pathlib import Path
import tomllib

import yaml

from p2p_engine import __version__
from p2p_engine.core.contribution import ContributionType
from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace


def test_package_version_matches_pyproject() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert __version__ == project["project"]["version"]


def test_domain_enums_expose_expected_values() -> None:
    assert ContributionType.suggestion.value == "suggestion"
    assert ContributionType.finding.value == "finding"
    assert ContributionType.open_question.value == "open_question"
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
    assert all(artifact.quality_state == "missing" for artifact in status.artifacts)


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
    status = workspace.exploration_status(proposal.proposal_id)
    exploration = next(artifact for artifact in status.artifacts if artifact.filename == "exploration.md")
    assert exploration.quality_state == "thin"


def test_init_project_creates_default_readiness_profile(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")

    profile = workspace.readiness_profile()

    assert profile.profile_id == "default-readiness-v0.1"
    assert profile.version == "0.1"
    assert profile.criteria["alternatives_quality"] == 15
    assert sum(profile.criteria.values()) == 100
    assert profile.thresholds["decision_ready"] == 95
    assert "governance-critical" in profile.tier_requirements


def test_readiness_profile_is_created_for_existing_workspace(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")
    profile_path = tmp_path / ".p2p" / "config" / "readiness-profiles" / "default-readiness-v0.1.yml"
    profile_path.unlink()

    profile = workspace.readiness_profile()

    assert profile.profile_id == "default-readiness-v0.1"
    assert profile_path.exists()


def test_missing_proposal_readiness_is_not_assessed(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")
    proposal = workspace.create_proposal("Exploration Phase")

    readiness = workspace.read_proposal_readiness(proposal.proposal_id)

    assert readiness.status == "not_assessed"
    assert readiness.profile_id is None
    assert readiness.computed_score is None
    assert readiness.path == proposal.path / "readiness.yml"


def test_write_and_read_proposal_readiness_assessment(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")
    proposal = workspace.create_proposal("Exploration Phase")

    path = workspace.write_proposal_readiness(
        proposal.proposal_id,
        {
            "status": "assessed",
            "profile_id": "default-readiness-v0.1",
            "profile_version": "0.1",
            "computed_score": 82,
            "computed_label": "partial",
            "confidence": "medium",
            "failed_gates": ["owner_questions_resolution"],
            "missing": ["acceptance_criteria_quality"],
            "suggested_next": ["define_acceptance_criteria"],
            "criteria": {
                "alternatives_quality": {
                    "max_points": 15,
                    "awarded_points": 11,
                    "artifact_quality": "meaningful",
                    "evidence": [{"artifact": "alternatives.md"}],
                    "notes": "Alternatives are real but not fully scored.",
                }
            },
        },
    )
    readiness = workspace.read_proposal_readiness(proposal.proposal_id)

    assert path == proposal.path / "readiness.yml"
    assert readiness.status == "assessed"
    assert readiness.profile_id == "default-readiness-v0.1"
    assert readiness.profile_version == "0.1"
    assert readiness.computed_score == 82
    assert readiness.computed_label == "partial"
    assert readiness.confidence == "medium"
    assert readiness.failed_gates == ["owner_questions_resolution"]
    assert readiness.missing == ["acceptance_criteria_quality"]
    assert readiness.suggested_next == ["define_acceptance_criteria"]


def test_refresh_proposal_readiness_computes_score_with_artifact_caps(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")
    proposal = workspace.create_proposal("Exploration Phase")
    profile = workspace.readiness_profile()
    criteria = {
        criterion: {
            "awarded_points": max_points,
            "artifact_quality": "ready",
            "evidence": [{"artifact": "proposal.md"}],
        }
        for criterion, max_points in profile.criteria.items()
    }
    criteria["alternatives_quality"]["artifact_quality"] = "meaningful"
    criteria["risk_coverage"]["artifact_quality"] = "thin"
    criteria["owner_questions_resolution"]["artifact_quality"] = "needs_owner_input"
    del criteria["acceptance_criteria_quality"]
    workspace.write_proposal_readiness(
        proposal.proposal_id,
        {
            "status": "assessed",
            "profile_id": profile.profile_id,
            "profile_version": profile.version,
            "confidence": "medium",
            "criteria": criteria,
        },
    )

    readiness = workspace.refresh_proposal_readiness(proposal.proposal_id)
    readiness_path = tmp_path / proposal.path / "readiness.yml"
    payload = yaml.safe_load(readiness_path.read_text(encoding="utf-8"))["readiness"]

    assert readiness.computed_score == 78
    assert readiness.computed_label == "partial"
    assert readiness.missing == ["acceptance_criteria_quality"]
    assert readiness.failed_gates == ["owner_questions_resolution:needs_owner_input"]
    assert payload["criteria"]["alternatives_quality"]["effective_points"] == 11
    assert payload["criteria"]["risk_coverage"]["effective_points"] == 5
    assert payload["criteria"]["owner_questions_resolution"]["effective_points"] == 7
    assert payload["criteria"]["acceptance_criteria_quality"]["effective_points"] == 0


def test_validate_rejects_invalid_readiness_profile(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")
    profile_path = tmp_path / ".p2p" / "config" / "readiness-profiles" / "default-readiness-v0.1.yml"
    data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    data["readiness_profile"]["criteria"]["alternatives_quality"] = 14
    profile_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = workspace.validate()

    assert result.errors == 1
    assert result.findings[0].code == "P2P230_INVALID_READINESS_PROFILE"


def test_validate_rejects_invalid_readiness_assessment(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Demo")
    proposal = workspace.create_proposal("Exploration Phase")
    readiness_path = tmp_path / proposal.path / "readiness.yml"
    readiness_path.write_text(
        "readiness:\n"
        "  profile_id: default-readiness-v0.1\n"
        "  profile_version: '0.1'\n"
        "  computed_score: 140\n",
        encoding="utf-8",
    )

    result = workspace.validate()

    assert result.errors == 1
    assert result.findings[0].code == "P2P231_INVALID_READINESS_ASSESSMENT"

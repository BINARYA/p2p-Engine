from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from p2p_engine.cli import app
from p2p_engine.core.proposal_artifact_state import (
    ProposalArtifactExpectation,
    ProposalArtifactStatus,
)
from p2p_engine.services.proposal_artifact_state import ProposalArtifactStateService
from p2p_engine.services.proposals import ProposalDocumentService
from p2p_engine.storage.filesystem import P2PWorkspace

runner = CliRunner()


def _services(tmp_path: Path) -> tuple[ProposalDocumentService, ProposalArtifactStateService]:
    proposals = ProposalDocumentService(root=tmp_path, p2p_dir=tmp_path / ".p2p")
    artifacts = ProposalArtifactStateService(root=tmp_path, find_proposal_dir=proposals.find_dir)
    return proposals, artifacts


def test_artifact_state_service_initializes_default_records(tmp_path: Path) -> None:
    proposals, artifacts = _services(tmp_path)
    proposal = proposals.create_with_details(
        title="Artifact State",
        problem="A simple proposal needs artifact coverage state.",
    )

    view = artifacts.initialize(proposal.proposal_id)

    assert view.status == "active"
    assert view.schema_version == 1
    assert {artifact.artifact_id for artifact in view.artifacts} == {
        "proposal",
        "readiness",
        "open_questions",
        "clarifications",
        "findings",
        "exploration",
        "impact_map",
    }
    proposal_record = next(artifact for artifact in view.artifacts if artifact.artifact_id == "proposal")
    assert proposal_record.expectation == ProposalArtifactExpectation.required
    assert proposal_record.status in {ProposalArtifactStatus.weak, ProposalArtifactStatus.satisfied}


def test_workspace_create_initializes_artifact_state_by_default(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)

    proposal = workspace.create_proposal_with_details(
        title="CLI MCP Storage Proposal",
        proposal="Changing CLI and MCP storage behavior should trigger artifact coverage.",
    )
    view = workspace.read_proposal_artifacts(proposal.proposal_id)

    assert view.schema_version == 1
    assert (tmp_path / proposal.path / "artifact-state.yml").exists()
    findings = next(artifact for artifact in view.artifacts if artifact.artifact_id == "findings")
    impact = next(artifact for artifact in view.artifacts if artifact.artifact_id == "impact_map")
    assert findings.expectation == ProposalArtifactExpectation.required
    assert impact.expectation == ProposalArtifactExpectation.required


def test_artifact_state_requires_rationale_for_not_applicable_and_deferred(tmp_path: Path) -> None:
    proposals, artifacts = _services(tmp_path)
    proposal = proposals.create("Rationale Required")
    artifacts.initialize(proposal.proposal_id)

    with pytest.raises(ValueError, match="requires a non-empty reason"):
        artifacts.set_artifact(proposal.proposal_id, "impact_map", status=ProposalArtifactStatus.not_applicable)

    with pytest.raises(ValueError, match="requires a non-empty reason"):
        artifacts.set_artifact(proposal.proposal_id, "impact_map", status=ProposalArtifactStatus.deferred)


def test_artifact_state_set_and_confirm_preserve_owner_visible_state(tmp_path: Path) -> None:
    proposals, artifacts = _services(tmp_path)
    proposal = proposals.create("Owner Confirmation")
    artifacts.initialize(proposal.proposal_id)

    operation = artifacts.set_artifact(
        proposal.proposal_id,
        "impact-map",
        status=ProposalArtifactStatus.not_applicable,
        reason="This proposal has no cross-module impact.",
        actor="codex",
    )
    confirmed = artifacts.confirm(proposal.proposal_id, "impact-map.yml", actor="owner")

    assert operation.artifact is not None
    assert operation.artifact.confirmation.value == "agent_proposed"
    assert confirmed.artifact is not None
    assert confirmed.artifact.confirmation.value == "owner_confirmed"
    assert confirmed.artifact.confirmed_by == "owner"
    payload = yaml.safe_load((tmp_path / proposal.path / "artifact-state.yml").read_text(encoding="utf-8"))
    impact = next(item for item in payload["proposal_artifacts"]["artifacts"] if item["id"] == "impact_map")
    assert impact["history"]


def test_missing_artifact_state_reads_as_absent_legacy(tmp_path: Path) -> None:
    proposals, artifacts = _services(tmp_path)
    proposal = proposals.create("Legacy Proposal")

    view = artifacts.read(proposal.proposal_id)

    assert view.status == "legacy_absent"
    assert view.legacy_state == ProposalArtifactStatus.absent_legacy
    assert view.artifacts == []
    assert f"p2p proposal artifact init {proposal.proposal_id}" in view.suggested_next


def test_cli_proposal_artifact_commands(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "Artifact CLI Demo", "--root", str(tmp_path)])
    assert result.exit_code == 0
    result = runner.invoke(
        app,
        [
            "proposal",
            "create",
            "Artifact CLI",
            "--proposal",
            "This proposal changes MCP and CLI command behavior.",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(app, ["proposal", "artifact", "status", "PROP-001", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Proposal artifact state for PROP-001" in result.output
    assert "impact_map" in result.output
    assert "required" in result.output

    result = runner.invoke(
        app,
        [
            "proposal",
            "artifact",
            "set",
            "PROP-001",
            "impact_map",
            "--status",
            "not_applicable",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0
    assert "requires a non-empty reason" in result.output

    result = runner.invoke(
        app,
        [
            "proposal",
            "artifact",
            "set",
            "PROP-001",
            "impact_map",
            "--status",
            "not_applicable",
            "--reason",
            "No impact outside the proposal document.",
            "--actor",
            "codex",
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Artifact state updated: impact_map" in result.output
    assert "agent_proposed" in result.output

    result = runner.invoke(
        app,
        ["proposal", "artifact", "confirm", "PROP-001", "impact_map", "--actor", "owner", "--root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "owner_confirmed" in result.output


def test_cli_mark_legacy_records_advisory_state(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    proposal = workspace.create_proposal("Legacy Mark")
    (tmp_path / proposal.path / "artifact-state.yml").unlink()

    result = runner.invoke(
        app,
        [
            "proposal",
            "artifact",
            "mark-legacy",
            proposal.proposal_id,
            "--reason",
            "Created before artifact-aware state.",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "legacy_state: absent_legacy" in result.output
    assert "Created before artifact-aware state." in result.output

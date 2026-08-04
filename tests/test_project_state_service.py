from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.core.proposal_decision_events import ProposalDecisionEventType
from p2p_engine.core.vertical_memory import (
    VerticalMemoryContribution,
    VerticalMemorySection,
    VerticalProjectMemoryView,
)
from p2p_engine.services.project_state import (
    ProjectStateService,
    vertical_project_overview_markdown,
    vertical_project_problem_markdown,
    vertical_project_scope_markdown,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision
from tests.test_vertical_project_memory_incremental import _apply_coverage


@dataclass(frozen=True)
class _NextAction:
    action_id: str
    priority: str
    kind: str
    target: str


@dataclass(frozen=True)
class _RegistryStatus:
    registries_dir: Path
    stale: bool
    proposals_count: int
    changes_count: int


def _accepted(tmp_path):
    proposal_dir = tmp_path / ".p2p" / "proposals" / "PROP-001-project-state"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_dir.joinpath("tasks.yml").write_text("tasks:\n  - id: T001\n", encoding="utf-8")
    return [
        {
            "proposal_id": "PROP-001",
            "title": "Project State",
            "status": "accepted",
            "feature_id": "project-state",
            "source": ".p2p/proposals/PROP-001-project-state",
            "path": proposal_dir,
            "problem": "The project needs generated state.",
            "goals": "- Keep state visible.",
            "non_goals": "- Do not decide for the owner.",
            "proposal": "Generate project state artifacts.",
            "decision": "# Decision - PROP-001\n\n## Status\n\n`accepted`\n",
        }
    ]


def _service(tmp_path):
    return ProjectStateService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        accepted_proposals=lambda: _accepted(tmp_path),
        project_name=lambda: "Demo Project",
        next_actions=lambda: [_NextAction("NEXT-001", "high", "create_change", "PROP-001")],
        registry_status=lambda: _RegistryStatus(Path(".p2p/registries"), False, 1, 1),
        project_brief_context=lambda status: f"# Project Brief Context\n\n- Path: `{status.registries_dir}`\n",
        validate_yaml_key=lambda content, key: None if f"{key}:" in content else (_ for _ in ()).throw(ValueError(key)),
    )


def test_project_state_service_refresh_writes_project_and_feature_artifacts(tmp_path) -> None:
    service = _service(tmp_path)

    written = service.refresh()

    assert Path(".p2p/project/overview.md") in written
    assert Path(".p2p/project/project-swot.md") in written
    assert Path(".p2p/project/projection-manifest.yml") in written
    assert Path(".p2p/project/features/project-state/feature.md") in written
    overview = (tmp_path / ".p2p" / "project" / "overview.md").read_text(encoding="utf-8")
    feature = (tmp_path / ".p2p" / "project" / "features" / "project-state" / "feature.md").read_text(
        encoding="utf-8"
    )
    tasks = (tmp_path / ".p2p" / "project" / "features" / "project-state" / "tasks.yml").read_text(
        encoding="utf-8"
    )
    assert "# Project State - Demo Project" in overview
    assert "PROP-001 - Project State" in overview
    assert "Generate project state artifacts." in feature
    assert "id: T001" in tasks
    assert not (tmp_path / ".p2p" / "project" / "conflicts.yml").exists()


def test_project_state_service_status_and_show(tmp_path) -> None:
    service = _service(tmp_path)
    service.refresh()

    status = service.status()
    overview = service.show("overview")
    feature = service.show("project-state")

    assert status.accepted_proposals == 1
    assert status.features == ["project-state"]
    assert status.operational_brief_available is False
    assert status.next_actions_count == 1
    assert status.first_next_action is not None
    assert "# Project State - Demo Project" in overview
    assert "# Project State" in feature
    with pytest.raises(ValueError, match="Project section not found: missing"):
        service.show("missing")


def test_project_state_service_brief_prompt_import_and_show(tmp_path) -> None:
    service = _service(tmp_path)

    prompt = service.create_brief_prompt()
    output_dir = tmp_path / "brief-output"
    output_dir.mkdir()
    output_dir.joinpath("operational-brief.md").write_text("# Operational Brief\n\nReady.\n", encoding="utf-8")
    output_dir.joinpath("next-actions.yml").write_text("next_actions:\n  - id: NEXT-001\n", encoding="utf-8")
    imported = service.import_brief(output_dir)
    shown = service.show_brief()

    assert prompt.context_path == Path(".p2p/project/brief-context.md")
    assert prompt.prompt_path == Path(".p2p/project/brief.prompt.md")
    assert "P2P Operational Brief Prompt" in (tmp_path / prompt.prompt_path).read_text(encoding="utf-8")
    assert Path(".p2p/project/operational-brief.md") in imported
    assert Path(".p2p/project/next-actions.yml") in imported
    assert "Ready." in shown

    single = tmp_path / "brief.md"
    single.write_text("# Operational Brief\n\nSingle file.\n", encoding="utf-8")
    assert service.import_brief(single) == [Path(".p2p/project/operational-brief.md")]
    assert "Single file." in service.show_brief()
    with pytest.raises(ValueError, match="Project brief source not found"):
        service.import_brief(tmp_path / "missing")


def test_workspace_project_state_facade_delegates(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Project State Facade")
    proposal = workspace.create_proposal("Facade State")
    record_decision(workspace, proposal.proposal_id, DecisionOutcome.accepted, "Ready.", "owner")

    written = workspace.refresh_project_state()
    status = workspace.project_state_status()
    overview = workspace.show_project_state("overview")
    prompt = workspace.create_project_brief_prompt()

    assert Path(".p2p/project/overview.md") in written
    assert status.accepted_proposals == 1
    assert "Facade State" in overview
    assert prompt.prompt_path == Path(".p2p/project/brief.prompt.md")


def test_project_refresh_is_idempotent_and_preserves_projection_manifest(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Idempotent project refresh")
    proposal = workspace.create_proposal("Stable Projection")
    record_decision(workspace, proposal.proposal_id, DecisionOutcome.accepted, "Ready.", "owner")

    first_written = workspace.refresh_project_state()
    manifest_path = tmp_path / ".p2p" / "project" / "projection-manifest.yml"
    first_manifest = manifest_path.read_bytes()
    second_written = workspace.refresh_project_state()

    assert manifest_path.read_bytes() == first_manifest
    assert Path(".p2p/project/projection-manifest.yml") in first_written
    assert Path(".p2p/project/projection-manifest.yml") in second_written


def test_vertical_first_project_projection_separates_current_historical_and_unmapped(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Vertical projection",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    current = workspace.create_proposal_with_details(
        "Current data model",
        problem="The current model is incomplete.",
        goals=["Define current domain entities."],
        non_goals=["Claim implementation completion."],
        proposal="Define the authoritative project data model.",
    )
    historical = workspace.create_proposal_with_details(
        "Historical data model",
        problem="An earlier model was incomplete.",
        proposal="Use an earlier data model direction.",
    )
    unmapped = workspace.create_proposal("Accepted but unmapped")
    for proposal in (current, historical, unmapped):
        record_decision(
            workspace,
            proposal.proposal_id,
            DecisionOutcome.accepted,
            "Accepted project direction.",
            "owner",
        )
    _apply_coverage(workspace, current.proposal_id, "data_model")
    _apply_coverage(workspace, historical.proposal_id, "data_model")
    decision = workspace._proposal_decision_service()
    request = decision.request(
        proposal_id=historical.proposal_id,
        event_type=ProposalDecisionEventType.revoked,
        reason="The earlier direction is retained only as history.",
        actor_id="owner",
        source_head_event_id=workspace.proposal_decision_status(
            historical.proposal_id
        ).head_event_id,
    )
    preview = workspace.preview_proposal_decision(request)
    workspace.apply_proposal_decision(
        request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )

    workspace.refresh_project_state()
    overview = workspace.show_project_state("overview")
    decisions = yaml.safe_load(
        (tmp_path / ".p2p" / "project" / "decisions-map.yml").read_text(
            encoding="utf-8"
        )
    )

    assert "## Current Direction By Vertical Section" in overview
    assert "Data Model (`data_model`)" in overview
    assert "## Unmapped Active Proposals" in overview
    assert unmapped.proposal_id in overview
    assert "## Historical Context" in overview
    assert "does not establish governance, readiness, implementation" in overview
    assert ".p2p/` remains the authoritative project source of truth" in overview
    active = {item["proposal"]: item for item in decisions["decisions"]}
    old = {item["proposal"]: item for item in decisions["historical_decisions"]}
    assert active[current.proposal_id]["sections"] == ["data_model"]
    assert active[unmapped.proposal_id]["sections"] == []
    assert old[historical.proposal_id]["sections"] == ["data_model"]
    assert (
        tmp_path
        / ".p2p"
        / "project"
        / "features"
        / "current-data-model"
        / "feature.md"
    ).is_file()


def test_vertical_first_renderer_handles_base_custom_partial_and_conflict_states() -> None:
    contribution = VerticalMemoryContribution(
        contribution_id="PROP-001:accepted:core",
        proposal_id="PROP-001",
        title="Current custom direction",
        section_id="core",
        authority="active",
        activation="active",
        effective_state="accepted",
        head_event_id="EVENT-001",
        head_event_type="accepted",
        rationale="Owner accepted the custom direction.",
        constraints=("Do not infer implementation.",),
        applicability="direct",
        coverage_rationale="Owner-declared custom coverage.",
        source_path=".p2p/proposals/PROP-001-custom/proposal.md",
        proposal_semantic_sha256="a" * 64,
        decision_semantic_sha256="b" * 64,
    )
    view = VerticalProjectMemoryView(
        vertical_id="custom_product",
        vertical_version="1.0",
        vertical_checksum="c" * 64,
        sections=(
            VerticalMemorySection(
                section_id="core",
                title="Core Direction",
                purpose="Define the current custom project direction.",
                required=True,
                priority=1,
                definition={
                    "status": "partial",
                    "assumptions": (
                        {"id": "ASM-001", "status": "to_validate", "text": "Owner validation is pending."},
                    ),
                    "blockers": (
                        {"id": "BLK-001", "status": "open", "text": "A governing choice is unresolved."},
                    ),
                },
                questions=(
                    {"id": "PQ-001", "state": "to_answer"},
                ),
                active_contributions=(contribution,),
                historical_contributions=(),
                conflicts=(
                    {"id": "CONFLICT-001", "kind": "conflict", "status": "unresolved", "reason": "Owner decision required."},
                ),
            ),
            VerticalMemorySection(
                section_id="delivery",
                title="Delivery",
                purpose="Define delivery boundaries.",
                required=True,
                priority=2,
                definition={"status": "missing"},
                questions=(),
                active_contributions=(),
                historical_contributions=(),
            ),
        ),
        unmapped_active_proposals=(
            {
                "proposal_id": "PROP-002",
                "title": "Legacy unmapped direction",
                "source_path": ".p2p/proposals/PROP-002-legacy/proposal.md",
            },
        ),
        diagnostics=(),
        source_fingerprint_sha256="d" * 64,
        source="canonical_fallback",
    )

    overview = vertical_project_overview_markdown("Custom Project", view)

    assert "custom_product" in overview
    assert "## Current Direction By Vertical Section" in overview
    assert "PROP-001" in overview
    assert "CONFLICT-001" in overview
    assert "PQ-001" in overview
    assert "ASM-001" in overview
    assert "BLK-001" in overview
    assert "`delivery` - Delivery" in overview
    assert "PROP-002" in overview
    assert "does not establish governance, readiness, implementation" in overview
    assert ".p2p/` remains the authoritative project source of truth" in overview

    base = VerticalProjectMemoryView(
        vertical_id="base_project",
        vertical_version="1.0",
        vertical_checksum="e" * 64,
        sections=(
            VerticalMemorySection(
                section_id="objective",
                title="Objective",
                purpose="Define the objective.",
                required=True,
                priority=1,
                definition={"status": "missing"},
                questions=(),
                active_contributions=(),
                historical_contributions=(),
            ),
        ),
        unmapped_active_proposals=(),
        diagnostics=(),
        source_fingerprint_sha256="f" * 64,
    )
    assert "No active declared problem evidence" in vertical_project_problem_markdown(base)
    assert "No active declared scope evidence" in vertical_project_scope_markdown(base)

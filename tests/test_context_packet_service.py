from pathlib import Path

import pytest

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.decision_context_fixtures import project_files, write_yaml
from tests.proposal_decision_fixtures import record_decision


def _workspace_with_context_items(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Context Project", project_domain="software")
    proposal = workspace.create_proposal_with_details(
        "Context Proposal",
        problem="This problem should appear in medium context.",
        proposal="This proposal should appear in medium context.",
    )
    workspace._choice_lifecycle_service().create(
        "Context Choice",
        ["A", "B"],
        related=[proposal.proposal_id],
        problem="Choose the context direction.",
        context="Context packet tests require a complete Choice frame.",
    )
    record_decision(workspace, proposal.proposal_id, DecisionOutcome.accepted, "Ready.", "owner")
    change = workspace.create_change_set(proposal.proposal_id)
    workspace.refresh_software_spec(change.change_id)
    workspace.export_software_spec(change.change_id, "generic")
    workspace.create_work_plan(change.change_id, "generic")
    return workspace


def _workspace_with_nearby_items(root: Path) -> P2PWorkspace:
    workspace = _workspace_with_context_items(root)
    related = workspace.create_proposal_with_details(
        "Related Decision",
        problem="Decision memory is fragmented.",
        goals=["Preserve decision rationale."],
        non_goals=["Replace canonical Markdown."],
        proposal="Build a derived decision index.",
    )
    record_decision(
        workspace,
        related.proposal_id,
        DecisionOutcome.accepted,
        "Keep canonical files and derive retrieval.",
        "owner",
    )
    write_yaml(
        root,
        ".p2p/proposals/PROP-001-context-proposal/related-proposals.yml",
        {
            "related_proposals": [
                {"proposal": related.proposal_id, "relationship": "depends_on"}
            ]
        },
    )
    return workspace


def test_context_packet_service_builds_small_default_packet(tmp_path: Path) -> None:
    workspace = _workspace_with_context_items(tmp_path)
    packet = workspace._context_packet_service().context_packet()

    assert packet.budget == "small"
    assert packet.target is None
    assert packet.current_state["project"] == "Context Project"
    assert packet.current_state["proposals"] == 1
    assert packet.current_state["choices"] == 1
    assert packet.current_state["changes"] == 1
    assert packet.current_state["work_items"] == 1
    assert packet.current_state["interaction_style"]["technical_verbosity"]["value"] == 2
    assert packet.current_state["interaction_style"]["formality"]["value"] == 2
    assert packet.current_state["interaction_style"]["assertiveness"]["value"] == 0
    assert packet.current_state["interaction_style"]["update_command"].startswith("p2p project interaction-style set")
    assert packet.allowed_commands[:4] == [
        "p2p context --budget small",
        "p2p next --top 1",
        "p2p validate",
        "p2p assess show",
    ]
    assert "p2p project interaction-style show" in packet.allowed_commands
    assert "p2p proposal list" in packet.allowed_commands
    assert packet.bounded_next_step
    assert any("Do not scan all .p2p" in item for item in packet.do_not_read)


def test_context_packet_reuses_one_request_snapshot_for_shared_summaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace_with_context_items(tmp_path)
    calls = {
        name: 0
        for name in (
            "validate",
            "registry_status",
            "proposal_summaries",
            "choice_statuses",
            "change_set_statuses",
            "work_summaries",
            "next_actions",
        )
    }

    for name in tuple(calls):
        original = getattr(workspace, name)

        def counted(*args, _name=name, _original=original, **kwargs):
            calls[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(workspace, name, counted)

    workspace._context_packet_service_instance = None
    workspace._validation_service_instance = None
    workspace._next_action_service_instance = None
    workspace._project_state_service_instance = None

    packet = workspace._context_packet_service().context_packet()

    assert packet.current_state["proposals"] == 1
    assert calls == {
        **{name: 1 for name in calls},
        "validate": 0,
    }
    assert packet.current_state["verification"] == {
        "validation": "not_run",
        "freshness": "not_run",
        "decision_context": "not_requested",
        "vertical_memory": "rebuilt_in_memory",
        "readiness": "rebuilt_in_memory",
        "registry_sources": "not_verified",
    }


def test_context_packet_service_builds_medium_proposal_target(tmp_path: Path) -> None:
    workspace = _workspace_with_context_items(tmp_path)

    packet = workspace._context_packet_service().context_packet(budget="medium", target="prop-001")
    artifact = packet.relevant_artifacts[0]

    assert packet.target == "PROP-001"
    assert packet.bounded_next_step == "p2p proposal show PROP-001"
    assert packet.allowed_commands[:2] == [
        "p2p proposal show PROP-001",
        "p2p context --target PROP-001 --budget medium",
    ]
    assert artifact["type"] == "proposal"
    assert artifact["id"] == "PROP-001"
    assert artifact["problem"] == "This problem should appear in medium context."
    assert artifact["proposal"] == "This proposal should appear in medium context."
    assert artifact["artifact_coverage"]["status"] == "active"
    assert any(gap["artifact"] == "open_questions" for gap in artifact["artifact_coverage"]["gaps"])


def test_context_packet_service_builds_change_choice_and_work_targets(tmp_path: Path) -> None:
    workspace = _workspace_with_context_items(tmp_path)
    service = workspace._context_packet_service()

    change = service.context_packet(target="CHANGE-001").relevant_artifacts[0]
    choice = service.context_packet(target="CHOICE-001").relevant_artifacts[0]
    work = service.context_packet(target="WORK-001").relevant_artifacts[0]

    assert change["type"] == "change"
    assert change["command"] == "p2p change show CHANGE-001"
    assert choice["type"] == "choice"
    assert choice["options_count"] == 2
    assert work["type"] == "work"
    assert work["command"] == "p2p work show WORK-001"
    assert service.context_packet(target="CHANGE-001").nearby_context is None
    assert service.context_packet(target="CHOICE-001").nearby_context is None
    assert service.context_packet(target="WORK-001").nearby_context is None


def test_proposal_context_adds_bounded_nearby_decisions(tmp_path: Path) -> None:
    workspace = _workspace_with_nearby_items(tmp_path)

    small = workspace.context_packet(target="PROP-001", budget="small")
    medium = workspace.context_packet(target="PROP-001", budget="medium")

    assert small.nearby_context is not None
    assert medium.nearby_context is not None
    assert small.nearby_context.schema_version == "decision-context-v1"
    assert small.nearby_context.budget.value == "small"
    small_related = next(hit for hit in small.nearby_context.hits if hit.owner_id == "PROP-002")
    medium_related = next(hit for hit in medium.nearby_context.hits if hit.owner_id == "PROP-002")
    assert small_related.non_goals == ()
    assert "Replace canonical Markdown." in medium_related.non_goals
    assert medium_related.decisions
    assert medium.nearby_context.evidence
    assert medium.nearby_context.source_fingerprint_sha256


def test_proposal_context_builds_one_index_after_target_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace_with_nearby_items(tmp_path)
    original = workspace.decision_context_index
    calls = 0

    def counted_index():
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(workspace, "decision_context_index", counted_index)
    workspace._context_packet_service_instance = None

    workspace.context_packet(target="PROP-001")
    assert calls == 1

    with pytest.raises(ValueError, match="Proposal not found"):
        workspace.context_packet(target="PROP-999")
    assert calls == 1


def test_empty_and_partial_nearby_context_are_explicit_and_read_only(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Partial Context", project_domain="software")
    workspace.create_proposal_with_details(
        "Isolated Proposal",
        problem="Isolated decision context.",
        proposal="No related proposal exists.",
    )
    malformed = tmp_path / ".p2p/proposals/PROP-001-isolated-proposal/impact-map.yml"
    malformed.write_text("impact: [\n", encoding="utf-8")
    before = project_files(tmp_path)

    packet = workspace.context_packet(target="PROP-001", budget="medium")

    assert packet.nearby_context is not None
    assert packet.nearby_context.hits == ()
    assert packet.nearby_context.empty_reason == "no_relevant_context"
    assert packet.nearby_context.completeness.value == "partial"
    assert {item.code for item in packet.nearby_context.diagnostics} >= {
        "DC-RETRIEVAL-EMPTY",
        "DC-INDEX-PARTIAL",
    }
    assert project_files(tmp_path) == before


def test_no_target_context_keeps_nearby_context_disabled(tmp_path: Path) -> None:
    workspace = _workspace_with_context_items(tmp_path)
    packet = workspace.context_packet()
    assert packet.nearby_context is None


def test_context_packet_service_rejects_invalid_budget(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Context Project")

    with pytest.raises(ValueError, match="Context budget must be small or medium"):
        workspace._context_packet_service().context_packet(budget="large")


def test_context_packet_service_rejects_invalid_target_prefix(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Context Project")

    with pytest.raises(ValueError, match="Context target must start"):
        workspace._context_packet_service().context_packet(target="BAD-001")

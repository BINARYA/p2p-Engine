from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.project_readiness import ProjectReadinessGapService
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.proposal_decision_fixtures import record_decision


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project(
        "Readiness projection",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    proposal = workspace.create_proposal_with_details(
        "Data model",
        problem="Domain entities need an explicit lifecycle.",
        proposal="Define domain entities and their lifecycle.",
    )
    record_decision(
        workspace,
        proposal.proposal_id,
        DecisionOutcome.accepted,
        "The data model is required.",
        "owner",
    )
    coverage = {
        "vertical_coverage": {
            "schema_version": 2,
            "proposal_id": proposal.proposal_id,
            "vertical_id": "software_project",
            "sections": [
                {
                    "id": "data_model",
                    "relevance": "direct",
                    "rationale": "Defines the domain lifecycle.",
                    "source": "owner_review",
                    "provenance": {"evidence": ["proposal.md"]},
                }
            ],
            "provenance": {
                "operation_id": f"proposal-vertical-coverage:{proposal.proposal_id}",
                "actor": "owner",
                "authority": "owner_confirmed",
                "source": "owner_review",
            },
        }
    }
    preview = workspace.preview_proposal_vertical_coverage(
        proposal.proposal_id,
        coverage,
        actor="owner",
    )
    applied = workspace.apply_proposal_vertical_coverage(
        proposal.proposal_id,
        coverage,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )
    assert applied.status == "applied"
    return workspace


def _section_semantics(snapshot: object) -> list[dict[str, object]]:
    return [asdict(section) for section in getattr(snapshot, "sections")]


def _gap_semantics(result: object) -> list[tuple[object, ...]]:
    return [
        (
            gap.gap_id,
            gap.kind,
            gap.severity,
            gap.section_id,
            gap.target_kind,
            gap.target_id,
            gap.definition_status,
            gap.missing_fields,
            gap.declared_evidence,
            gap.heuristic_suggestions,
            gap.question_id,
            gap.question_revision,
            gap.next_operation,
        )
        for gap in getattr(result, "gaps")
    ]


def test_projection_snapshot_preserves_canonical_readiness_semantics(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._project_vertical_service()
    memory_callback = service.vertical_memory_view
    service.vertical_memory_view = None
    canonical = service.project_readiness_snapshot()
    service.vertical_memory_view = memory_callback

    projected = service.project_readiness_snapshot()

    assert projected.identity.vertical_id == canonical.identity.vertical_id
    assert projected.identity.vertical_lock_checksum == canonical.identity.vertical_lock_checksum
    assert projected.definition_exists == canonical.definition_exists
    assert projected.definition_valid == canonical.definition_valid
    assert projected.owner_available == canonical.owner_available
    assert _section_semantics(projected) == _section_semantics(canonical)
    assert _gap_semantics(ProjectReadinessGapService().classify(projected)) == _gap_semantics(
        ProjectReadinessGapService().classify(canonical)
    )


def test_materialized_and_canonical_fallback_readiness_match(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    fallback = workspace.project_readiness_result()
    workspace.refresh_vertical_project_memory()

    materialized = workspace.project_readiness_result()

    assert _gap_semantics(materialized) == _gap_semantics(fallback)
    assert materialized.counts == fallback.counts


def test_vertical_memory_builder_does_not_depend_on_readiness_classification() -> None:
    source = (
        Path(__file__).parents[1]
        / "src/p2p_engine/services/vertical_memory.py"
    ).read_text(encoding="utf-8")

    assert "services.project_readiness" not in source
    assert "ProjectReadinessGapService" not in source

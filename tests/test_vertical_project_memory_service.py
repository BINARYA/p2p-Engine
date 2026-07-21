from __future__ import annotations

from pathlib import Path
import threading

import pytest
import yaml

from p2p_engine.core.proposal_decision_events import ProposalDecisionEventType
from p2p_engine.core.vertical_memory import VerticalMemoryAggregate
from p2p_engine.storage.filesystem import P2PWorkspace
from p2p_engine.services.workspace_transactions import AtomicMutationWriter
from tests.proposal_decision_fixtures import record_decision
from p2p_engine.core.decision import DecisionOutcome
from tests.read_performance import tree_digest


def _workspace(root: Path) -> tuple[P2PWorkspace, str]:
    workspace = P2PWorkspace(root)
    workspace.init_project(
        "Vertical Memory",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    proposal = workspace.create_proposal_with_details(
        "Domain lifecycle",
        problem="Domain entities need an explicit lifecycle.",
        goals=["Define entities and transitions."],
        non_goals=["Track implementation completion."],
        proposal="Define a durable domain model and state transitions.",
        acceptance_criteria=["The domain lifecycle is explicit."],
    )
    record_decision(
        workspace,
        proposal.proposal_id,
        DecisionOutcome.accepted,
        "The domain lifecycle is required.",
        "owner",
    )
    payload = {
        "vertical_coverage": {
            "schema_version": 2,
            "proposal_id": proposal.proposal_id,
            "vertical_id": "software_project",
            "sections": [
                {
                    "id": "data_model",
                    "relevance": "direct",
                    "rationale": "Defines domain entities and transitions.",
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
        payload,
        actor="owner",
    )
    result = workspace.apply_proposal_vertical_coverage(
        proposal.proposal_id,
        payload,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )
    assert result.status == "applied"
    return workspace, proposal.proposal_id


def test_full_vertical_memory_candidate_is_complete_deterministic_and_read_only(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    service = workspace._vertical_project_memory_service()

    first = service.build_full()
    second = service.build_full()

    assert first.candidates == second.candidates
    assert len(first.view.sections) == 19
    data_model = next(item for item in first.view.sections if item.section_id == "data_model")
    assert [item.proposal_id for item in data_model.active_contributions] == [proposal_id]
    contribution = data_model.active_contributions[0]
    assert contribution.rationale == "The domain lifecycle is required."
    assert contribution.evidence
    assert all(not item.source_path.startswith("/") for item in contribution.evidence)
    assert first.view.unmapped_active_proposals == ()
    assert not (tmp_path / ".p2p" / "project" / "vertical-memory").exists()


def test_vertical_memory_refresh_status_materialized_view_and_stale_fallback(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    result = workspace.refresh_vertical_project_memory()

    assert result.status == "applied"
    assert workspace.vertical_project_memory_status().state == "current"
    materialized = workspace.vertical_project_memory(allow_fallback=False)
    assert materialized.source == "materialized"
    unchanged = workspace.refresh_vertical_project_memory()
    assert unchanged.status == "unchanged"

    proposal_path = workspace._proposal_document_service().find_dir(proposal_id) / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8").replace(
            "Domain entities need an explicit lifecycle.",
            "Domain entities need an explicit governed lifecycle.",
        ),
        encoding="utf-8",
    )
    status = workspace.vertical_project_memory_status()
    fallback = workspace.vertical_project_memory()

    assert status.state == "stale"
    assert "proposals" in status.changed_scopes
    assert proposal_path.relative_to(tmp_path).as_posix() in status.changed_paths
    assert fallback.source == "canonical_fallback"


def test_vertical_memory_fast_status_checks_generation_without_rehashing_sources(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    workspace.refresh_vertical_project_memory()
    proposal_path = workspace._proposal_document_service().find_dir(proposal_id) / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8") + "\nChanged after refresh.\n",
        encoding="utf-8",
    )
    service = workspace._vertical_project_memory_service()

    fast = service.fast_status()
    complete = service.status()

    assert fast.state == "current"
    assert "not rehashed" in fast.reason
    assert complete.state == "stale"


def test_unmapped_active_proposal_is_not_section_evidence(tmp_path: Path) -> None:
    workspace, mapped_id = _workspace(tmp_path)
    unmapped = workspace.create_proposal("Unmapped active")
    record_decision(
        workspace,
        unmapped.proposal_id,
        DecisionOutcome.accepted,
        "Accepted but not mapped.",
        "owner",
    )

    view = workspace.vertical_project_memory()

    assert [item["proposal_id"] for item in view.unmapped_active_proposals] == [
        unmapped.proposal_id
    ]
    section_proposals = {
        contribution.proposal_id
        for section in view.sections
        for contribution in section.active_contributions
    }
    assert mapped_id in section_proposals
    assert unmapped.proposal_id not in section_proposals


def test_revoked_previously_active_contribution_becomes_historical(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    service = workspace._proposal_decision_service()
    request = service.request(
        proposal_id=proposal_id,
        event_type=ProposalDecisionEventType.revoked,
        reason="The direction is no longer authoritative.",
        actor_id="owner",
        source_head_event_id=workspace.proposal_decision_status(proposal_id).head_event_id,
    )
    preview = service.preview(request)
    applied = service.apply(request, preview_token=preview.mutation.preview_token, confirm=True)
    assert applied.status == "applied"

    view = workspace.vertical_project_memory()
    section = next(item for item in view.sections if item.section_id == "data_model")

    assert section.active_contributions == ()
    assert [item.proposal_id for item in section.historical_contributions] == [proposal_id]


def test_vertical_memory_show_uses_exact_section_and_stable_pagination(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)

    page = workspace.show_vertical_project_memory(section_id="data_model", limit=1)

    assert page.total == 1
    assert page.returned == 1
    assert page.items[0]["proposal_id"] == proposal_id


def test_vertical_memory_cursor_is_bound_to_semantic_result_set(tmp_path: Path) -> None:
    workspace, first_id = _workspace(tmp_path)
    second = workspace.create_proposal_with_details(
        "Additional domain entity",
        problem="A second entity needs a lifecycle.",
        proposal="Extend the domain model with another governed entity.",
    )
    record_decision(
        workspace,
        second.proposal_id,
        DecisionOutcome.accepted,
        "The entity is part of the domain model.",
        "owner",
    )
    from tests.test_vertical_project_memory_incremental import _apply_coverage

    _apply_coverage(workspace, second.proposal_id, "data_model")

    first = workspace.show_vertical_project_memory(section_id="data_model", limit=1)
    repeated = workspace.show_vertical_project_memory(section_id="data_model", limit=1)
    second_page = workspace.show_vertical_project_memory(
        section_id="data_model",
        limit=1,
        cursor=first.next_cursor,
    )

    assert first.next_cursor == repeated.next_cursor
    assert first.truncated is True
    assert {first.items[0]["proposal_id"], second_page.items[0]["proposal_id"]} == {
        first_id,
        second.proposal_id,
    }
    assert second_page.next_cursor == ""

    with pytest.raises(ValueError, match="does not match"):
        workspace.show_vertical_project_memory(
            section_id="data_model",
            include_history=True,
            limit=1,
            cursor=first.next_cursor,
        )
    with pytest.raises(ValueError, match="does not match"):
        workspace.show_vertical_project_memory(
            section_id="workflows_use_cases",
            limit=1,
            cursor=first.next_cursor,
        )

    proposal_path = workspace._proposal_document_service().find_dir(first_id) / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8") + "\nChanged after cursor creation.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not match"):
        workspace.show_vertical_project_memory(
            section_id="data_model",
            limit=1,
            cursor=first.next_cursor,
        )


@pytest.mark.parametrize("limit", [0, 101])
def test_vertical_memory_show_rejects_invalid_limits(tmp_path: Path, limit: int) -> None:
    workspace, _ = _workspace(tmp_path)

    with pytest.raises(ValueError, match="between 1 and 100"):
        workspace.show_vertical_project_memory(section_id="data_model", limit=limit)


def test_vertical_memory_show_rejects_legacy_numeric_cursor(tmp_path: Path) -> None:
    workspace, _ = _workspace(tmp_path)

    with pytest.raises(ValueError, match="Invalid vertical-memory cursor"):
        workspace.show_vertical_project_memory(
            section_id="data_model",
            cursor="1",
        )


def test_vertical_memory_aggregate_is_compact_and_pages_unmapped_items(tmp_path: Path) -> None:
    workspace, _ = _workspace(tmp_path)
    for title in ("Unmapped one", "Unmapped two"):
        proposal = workspace.create_proposal(title)
        record_decision(
            workspace,
            proposal.proposal_id,
            DecisionOutcome.accepted,
            "Accepted without declared vertical coverage.",
            "owner",
        )

    aggregate = workspace.show_vertical_project_memory(limit=1)

    assert isinstance(aggregate, VerticalMemoryAggregate)
    assert aggregate.total == 2
    assert aggregate.returned == 1
    assert aggregate.truncated is True
    assert aggregate.next_cursor
    assert all("active_contributions" in item for item in aggregate.sections)
    assert all(not isinstance(item.get("active_contributions"), list) for item in aggregate.sections)


def test_vertical_memory_refresh_failure_rolls_back_complete_generation(tmp_path: Path) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    workspace.refresh_vertical_project_memory()
    service = workspace._vertical_project_memory_service()
    manifest = service._manifest_optional()
    assert manifest is not None
    before = {
        str(path): (tmp_path / str(path)).read_bytes()
        for path in manifest["owned_paths"]
    }
    proposal_path = workspace._proposal_document_service().find_dir(proposal_id) / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8") + "\nChanged before failed refresh.\n",
        encoding="utf-8",
    )
    candidate = service.build_full()

    def fail_after_replace(stage: str, target: str) -> None:
        if stage == "after_replace":
            raise RuntimeError(f"injected failure at {target}")

    service.atomic_writer = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=fail_after_replace,
    )

    with pytest.raises(ValueError, match="rolled back"):
        service._commit_candidate(candidate, mode="full")

    assert {
        path: (tmp_path / path).read_bytes()
        for path in before
    } == before
    assert workspace.vertical_project_memory_status().state == "stale"


def test_vertical_memory_commit_rejects_source_change_after_candidate_validation(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    workspace.refresh_vertical_project_memory()
    service = workspace._vertical_project_memory_service()
    proposal_path = workspace._proposal_document_service().find_dir(proposal_id) / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8") + "\nCandidate source change.\n",
        encoding="utf-8",
    )
    candidate = service.build_full()
    injected = False

    def change_source(stage: str, target: str) -> None:
        nonlocal injected
        if stage == "after_candidate_validation" and not injected:
            injected = True
            proposal_path.write_text(
                proposal_path.read_text(encoding="utf-8") + "\nConcurrent source change.\n",
                encoding="utf-8",
            )

    service.atomic_writer = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=change_source,
    )

    with pytest.raises(ValueError, match="source changed"):
        service._commit_candidate(candidate, mode="full")

    assert workspace.vertical_project_memory_status().state == "stale"


def test_concurrent_reader_falls_back_instead_of_exposing_mixed_generation(
    tmp_path: Path,
) -> None:
    workspace, proposal_id = _workspace(tmp_path)
    workspace.refresh_vertical_project_memory()
    service = workspace._vertical_project_memory_service()
    proposal_path = workspace._proposal_document_service().find_dir(proposal_id) / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8") + "\nConcurrent refresh content.\n",
        encoding="utf-8",
    )
    candidate = service.build_full()
    replaced = threading.Event()
    release = threading.Event()

    def block_after_first_replace(stage: str, target: str) -> None:
        if stage == "after_replace" and not replaced.is_set():
            replaced.set()
            assert release.wait(timeout=10)

    service.atomic_writer = AtomicMutationWriter(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        failure_injector=block_after_first_replace,
    )
    errors: list[BaseException] = []

    def commit() -> None:
        try:
            service._commit_candidate(candidate, mode="full")
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=commit)
    worker.start()
    assert replaced.wait(timeout=10)
    try:
        view = workspace.vertical_project_memory()
        assert view.source == "canonical_fallback"
        assert view.source_fingerprint_sha256 == candidate.view.source_fingerprint_sha256
    finally:
        release.set()
        worker.join(timeout=10)

    assert not errors
    assert not worker.is_alive()
    assert workspace.vertical_project_memory_status().state == "current"


def test_vertical_switch_replaces_owned_section_set_atomically(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Vertical switch",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    workspace.refresh_vertical_project_memory()
    service = workspace._vertical_project_memory_service()
    prior = service._manifest_optional()
    assert prior is not None
    prior_sections = {
        str(path)
        for path in prior["owned_paths"]
        if "/sections/" in str(path)
    }

    selected = workspace.select_project_vertical("base_project", actor="owner")
    derived = selected.derived_updates["vertical_project_memory"]
    assert derived["state"] == "stale"
    assert workspace.vertical_project_memory_status().state == "stale"

    refreshed = workspace.refresh_vertical_project_memory()
    current = service._manifest_optional()
    assert refreshed.status == "applied"
    assert current is not None
    current_sections = {
        str(path)
        for path in current["owned_paths"]
        if "/sections/" in str(path)
    }
    assert prior_sections - current_sections
    assert all(not (tmp_path / path).exists() for path in prior_sections - current_sections)
    assert all((tmp_path / path).is_file() for path in current_sections)
    assert workspace.vertical_project_memory_status().state == "current"


def test_unsupported_vertical_memory_reads_are_byte_invariant(tmp_path: Path) -> None:
    workspace, _ = _workspace(tmp_path)
    workspace.refresh_vertical_project_memory()
    manifest_path = tmp_path / ".p2p/project/vertical-memory/manifest.yml"
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["vertical_project_memory_manifest"]["manifest_version"] = 999
    manifest_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    before = tree_digest(tmp_path)

    status = workspace.vertical_project_memory_status()
    fallback = workspace.vertical_project_memory()

    assert status.state == "unsupported"
    assert fallback.source == "canonical_fallback"
    assert tree_digest(tmp_path) == before

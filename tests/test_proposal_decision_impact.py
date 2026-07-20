from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from p2p_engine.core.proposal_decision_events import (
    ProposalDecisionDependencyControl,
    ProposalDecisionDependencyKind,
    ProposalDecisionEventType,
)
from p2p_engine.services.proposal_decision_impact import (
    ProposalDecisionImpactService,
)
from p2p_engine.storage.filesystem import P2PWorkspace


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".p2p/.internal"):
            continue
        digest.update(relative.encode("utf-8"))
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _workspace(root: Path) -> tuple[P2PWorkspace, str, Path]:
    workspace = P2PWorkspace(root)
    workspace.init_project("Impact Fixture", owner="owner")
    proposal = workspace.create_proposal("Decision impact")
    service = workspace._proposal_decision_service()
    preview = service.preview(
        service.request(
            proposal_id=proposal.proposal_id,
            event_type=ProposalDecisionEventType.accepted,
            reason="Accepted for impact tests.",
            actor_id="owner",
        )
    )
    service.apply(
        preview.request,
        preview_token=preview.mutation.preview_token,
        confirm=True,
    )
    return workspace, proposal.proposal_id, root / proposal.path


def _write_dependency_graph(
    root: Path,
    proposal_id: str,
    proposal_dir: Path,
) -> None:
    change_dir = root / ".p2p" / "changes" / "CHANGE-001-impact"
    change_dir.mkdir(parents=True)
    (change_dir / "change.md").write_text(
        "---\n"
        "change_id: CHANGE-001\n"
        "status: in_progress\n"
        "source:\n"
        f"  accepted_proposals: [{proposal_id}]\n"
        "---\n\n# Change\n",
        encoding="utf-8",
    )
    (change_dir / "included-proposals.yml").write_text(
        f"included_proposals: [{proposal_id}]\n",
        encoding="utf-8",
    )
    work_dir = root / ".p2p" / "work" / "WORK-001"
    work_dir.mkdir(parents=True)
    (work_dir / "manifest.yml").write_text(
        "work_id: WORK-001\n"
        "status: in_progress\n"
        "source:\n"
        "  change: CHANGE-001\n"
        "  proposals: []\n",
        encoding="utf-8",
    )
    spec_dir = root / ".p2p" / "outputs" / "software-spec" / "CHANGE-001"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text(
        f"# Spec\n\nSource: {proposal_id}\n",
        encoding="utf-8",
    )
    (proposal_dir / "vertical-coverage.yml").write_text(
        "vertical_coverage:\n"
        f"  proposal_id: {proposal_id}\n"
        "  sections:\n"
        "    - id: data_model\n"
        "    - id: acceptance_validation\n",
        encoding="utf-8",
    )
    registries = root / ".p2p" / "registries"
    registries.mkdir(exist_ok=True)
    (registries / "relations.yml").write_text(
        "relations:\n"
        "  - id: REL-001\n"
        "    source: CHANGE-001\n"
        f"    target: {proposal_id}\n"
        "    type: includes\n",
        encoding="utf-8",
    )
    project = root / ".p2p" / "project"
    (project / "conflicts.yml").write_text(
        "conflicts:\n"
        "  - id: CONFLICT-001\n"
        f"    proposals: [{proposal_id}, PROP-999]\n",
        encoding="utf-8",
    )
    (project / "decisions-map.yml").write_text(
        "decisions:\n"
        f"  - proposal: {proposal_id}\n",
        encoding="utf-8",
    )
    (project / "projection-manifest.yml").write_text(
        f"source_proposals: [{proposal_id}]\n",
        encoding="utf-8",
    )
    outputs = root / "outputs" / "latest"
    outputs.mkdir(parents=True)
    (outputs / "project.md").write_text(
        f"# Project\n\nDecision: {proposal_id}\n",
        encoding="utf-8",
    )


def test_capture_finds_direct_and_transitive_dependencies_with_stable_identity(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    _write_dependency_graph(tmp_path, proposal_id, proposal_dir)
    service = ProposalDecisionImpactService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=workspace._proposal_document_service().find_dir,
        freshness_status=lambda: type("Freshness", (), {"status": "attention_required"})(),
    )
    head = workspace.proposal_decision_status(proposal_id).head_event_id

    first = service.capture(
        proposal_id,
        source_head_event_id=head,
        event_type=ProposalDecisionEventType.revoked,
    )
    second = service.capture(
        proposal_id,
        source_head_event_id=head,
        event_type=ProposalDecisionEventType.revoked,
    )

    assert first.complete is True
    assert first.to_dict() == second.to_dict()
    assert first.total_count == 11
    assert {item.dependency_kind for item in first.items} == set(
        ProposalDecisionDependencyKind
    )
    controls = {item.dependency_control for item in first.items}
    assert controls == {
        ProposalDecisionDependencyControl.generated,
        ProposalDecisionDependencyControl.curated,
        ProposalDecisionDependencyControl.owner_controlled,
    }
    assert first.access_counters["change_directories"] == 1
    assert first.access_counters["work_directories"] == 1
    assert first.access_counters["software_spec_directories"] == 1


def test_capture_reuses_supplied_freshness_snapshot(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    _write_dependency_graph(tmp_path, proposal_id, proposal_dir)
    provider_calls = 0

    def freshness_provider() -> object:
        nonlocal provider_calls
        provider_calls += 1
        return type("Freshness", (), {"status": "current"})()

    service = ProposalDecisionImpactService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=workspace._proposal_document_service().find_dir,
        freshness_status=freshness_provider,
    )
    snapshot = service.capture(
        proposal_id,
        source_head_event_id=workspace.proposal_decision_status(
            proposal_id
        ).head_event_id,
        event_type=ProposalDecisionEventType.revoked,
        freshness_status_snapshot=type(
            "Freshness",
            (),
            {"status": "attention_required"},
        )(),
    )

    freshness = next(
        item
        for item in snapshot.items
        if item.dependency_kind == ProposalDecisionDependencyKind.freshness
    )
    assert provider_calls == 0
    assert freshness.dependency_status.value == "stale"
    assert freshness.remediation_command == "p2p project freshness"


def test_page_is_bounded_but_hidden_source_changes_snapshot_and_apply_token(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    _write_dependency_graph(tmp_path, proposal_id, proposal_dir)
    service = workspace._proposal_decision_impact_service()
    lifecycle = workspace.proposal_decision_status(proposal_id)
    snapshot = service.capture(
        proposal_id,
        source_head_event_id=lifecycle.head_event_id,
        event_type=ProposalDecisionEventType.revoked,
    )
    page = service.page(snapshot, limit=1)
    decision_service = workspace._proposal_decision_service()
    preview = decision_service.preview(
        decision_service.request(
            proposal_id=proposal_id,
            event_type=ProposalDecisionEventType.revoked,
            reason="Revoke after impact review.",
            actor_id="owner",
            source_head_event_id=lifecycle.head_event_id,
            impact_preview_token=snapshot.preview_token,
        )
    )
    relation_path = tmp_path / ".p2p" / "registries" / "relations.yml"
    relation_path.write_text(
        relation_path.read_text(encoding="utf-8") + "# changed\n",
        encoding="utf-8",
    )
    changed = service.capture(
        proposal_id,
        source_head_event_id=lifecycle.head_event_id,
        event_type=ProposalDecisionEventType.revoked,
    )
    before = _tree_digest(tmp_path)

    assert page.returned_count == 1
    assert page.omitted_count == snapshot.total_count - 1
    assert page.next_cursor is not None
    assert changed.source_fingerprint_sha256 != snapshot.source_fingerprint_sha256
    assert changed.preview_token != snapshot.preview_token
    with pytest.raises(ValueError, match="P2P365_DECISION_STALE_PREVIEW"):
        decision_service.apply(
            preview.request,
            preview_token=preview.mutation.preview_token,
            confirm=True,
        )
    assert _tree_digest(tmp_path) == before


def test_malformed_canonical_dependency_blocks_authority_preview(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    _write_dependency_graph(tmp_path, proposal_id, proposal_dir)
    included = (
        tmp_path
        / ".p2p"
        / "changes"
        / "CHANGE-001-impact"
        / "included-proposals.yml"
    )
    included.write_text(
        f"included_proposals: [{proposal_id}]\n"
        f"included_proposals: [{proposal_id}]\n",
        encoding="utf-8",
    )
    service = workspace._proposal_decision_service()
    before = _tree_digest(tmp_path)

    with pytest.raises(ValueError, match="P2P370_DECISION_IMPACT_INCOMPLETE"):
        service.preview(
            service.request(
                proposal_id=proposal_id,
                event_type=ProposalDecisionEventType.revoked,
                reason="Must fail closed.",
                actor_id="owner",
            )
        )

    assert _tree_digest(tmp_path) == before


def test_impact_reads_are_side_effect_free_and_cursor_is_snapshot_bound(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, proposal_dir = _workspace(tmp_path)
    _write_dependency_graph(tmp_path, proposal_id, proposal_dir)
    before = _tree_digest(tmp_path)
    snapshot = workspace.proposal_decision_impact(
        proposal_id,
        event_type=ProposalDecisionEventType.revoked,
    )
    first_page = workspace.proposal_decision_impact_page(snapshot, limit=2)

    assert _tree_digest(tmp_path) == before
    assert first_page.next_cursor is not None
    other = ProposalDecisionImpactService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=workspace._proposal_document_service().find_dir,
    ).capture(
        proposal_id,
        source_head_event_id=snapshot.source_head_event_id,
        event_type=ProposalDecisionEventType.reinstated,
    )
    with pytest.raises(ValueError, match="cursor is stale"):
        workspace.proposal_decision_impact_page(
            other,
            limit=2,
            cursor=first_page.next_cursor,
        )


def test_impact_capture_is_deterministic_for_one_hundred_dependency_chains(
    tmp_path: Path,
) -> None:
    workspace, proposal_id, _ = _workspace(tmp_path)
    changes_root = tmp_path / ".p2p" / "changes"
    work_root = tmp_path / ".p2p" / "work"
    specs_root = tmp_path / ".p2p" / "outputs" / "software-spec"
    for number in range(1, 101):
        change_id = f"CHANGE-{number:03d}"
        work_id = f"WORK-{number:03d}"
        change_dir = changes_root / f"{change_id}-scale"
        change_dir.mkdir(parents=True)
        (change_dir / "change.md").write_text(
            "---\n"
            f"change_id: {change_id}\n"
            "status: in_progress\n"
            "source:\n"
            f"  accepted_proposals: [{proposal_id}]\n"
            "---\n\n# Scale Change\n",
            encoding="utf-8",
        )
        (change_dir / "included-proposals.yml").write_text(
            f"included_proposals: [{proposal_id}]\n",
            encoding="utf-8",
        )
        work_dir = work_root / work_id
        work_dir.mkdir(parents=True)
        (work_dir / "manifest.yml").write_text(
            f"work_id: {work_id}\n"
            "status: in_progress\n"
            "source:\n"
            f"  change: {change_id}\n",
            encoding="utf-8",
        )
        spec_dir = specs_root / change_id
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text(
            f"# {change_id} Spec\n",
            encoding="utf-8",
        )
    service = ProposalDecisionImpactService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        find_proposal_dir=workspace._proposal_document_service().find_dir,
    )
    head = workspace.proposal_decision_status(proposal_id).head_event_id

    first = service.capture(
        proposal_id,
        source_head_event_id=head,
        event_type=ProposalDecisionEventType.revoked,
    )
    second = service.capture(
        proposal_id,
        source_head_event_id=head,
        event_type=ProposalDecisionEventType.revoked,
    )
    page = service.page(first, limit=10)

    assert first.to_dict() == second.to_dict()
    assert first.total_count == 300
    assert page.returned_count == 10
    assert page.omitted_count == 290
    assert first.access_counters["change_directories"] == 1
    assert first.access_counters["work_directories"] == 1
    assert first.access_counters["software_spec_directories"] == 1

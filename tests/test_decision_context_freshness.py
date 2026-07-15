from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from p2p_engine.core.decision_context import (
    AUTHORITY_POLICY_VERSION,
    BUDGET_POLICY_VERSION,
    ContextBudget,
    EXTRACTOR_VERSION,
    Freshness,
    RELATION_POLICY_VERSION,
    RETRIEVAL_POLICY_VERSION,
    RetrievalRequest,
    to_json_ready,
)
from p2p_engine.services.decision_context import ProjectDecisionContextService
from p2p_engine.services.decision_context_freshness import (
    DecisionContextFreshnessService,
    manifests_semantically_equal,
    packet_semantic_fingerprint,
    semantic_fingerprint,
)
from p2p_engine.services.decision_context_retrieval import DecisionContextRetrievalService
from tests.decision_context_fixtures import project_files, write_proposal


def _index(root: Path):
    return ProjectDecisionContextService(root=root).build_index()


def test_source_fingerprint_tracks_same_size_content_and_presence_changes(tmp_path: Path) -> None:
    proposal_dir = write_proposal(tmp_path, "PROP-001", decision_outcome="accepted")
    first = _index(tmp_path)
    proposal_path = proposal_dir / "proposal.md"
    original_size = proposal_path.stat().st_size
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8").replace("derived", "indexed"),
        encoding="utf-8",
    )
    second = _index(tmp_path)
    assert proposal_path.stat().st_size == original_size
    assert second.source_fingerprint_sha256 != first.source_fingerprint_sha256

    (proposal_dir / "decision.md").unlink()
    third = _index(tmp_path)
    assert third.source_fingerprint_sha256 != second.source_fingerprint_sha256
    assert any(
        source.path.endswith("decision.md") and source.presence.value == "missing"
        for source in third.sources
    )


def test_semantic_fingerprint_invalidates_each_policy_independently() -> None:
    baseline = semantic_fingerprint(
        "source",
        extractor_version=EXTRACTOR_VERSION,
        authority_policy_version=AUTHORITY_POLICY_VERSION,
        relation_policy_version=RELATION_POLICY_VERSION,
    )

    assert baseline != semantic_fingerprint(
        "source",
        extractor_version=EXTRACTOR_VERSION + ".next",
        authority_policy_version=AUTHORITY_POLICY_VERSION,
        relation_policy_version=RELATION_POLICY_VERSION,
    )
    assert baseline != semantic_fingerprint(
        "source",
        extractor_version=EXTRACTOR_VERSION,
        authority_policy_version=AUTHORITY_POLICY_VERSION + ".next",
        relation_policy_version=RELATION_POLICY_VERSION,
    )
    assert baseline != semantic_fingerprint(
        "source",
        extractor_version=EXTRACTOR_VERSION,
        authority_policy_version=AUTHORITY_POLICY_VERSION,
        relation_policy_version=RELATION_POLICY_VERSION + ".next",
    )


def test_packet_semantics_include_retrieval_and_budget_policy_versions(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001", proposal="Quasar retrieval")
    packet = DecisionContextRetrievalService().retrieve(
        _index(tmp_path),
        RetrievalRequest(ContextBudget.SMALL, idea_text="quasar retrieval"),
    )

    assert packet_semantic_fingerprint(packet) != packet_semantic_fingerprint(
        replace(packet, retrieval_policy_version=packet.retrieval_policy_version + ".next")
    )
    assert packet_semantic_fingerprint(packet) != packet_semantic_fingerprint(
        replace(packet, budget_policy_version=packet.budget_policy_version + ".next")
    )


def test_manifest_clock_is_observational_and_manifest_build_is_read_only(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001")
    index = _index(tmp_path)
    before = project_files(tmp_path)
    first_service = DecisionContextFreshnessService(
        clock=lambda: datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)
    )
    second_service = DecisionContextFreshnessService(
        clock=lambda: datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
    )

    first = first_service.manifest(index, generator_version="context-projection-v1")
    second = second_service.manifest(index, generator_version="context-projection-v1")
    serialized = to_json_ready(first)

    assert first.generated_at != second.generated_at
    assert manifests_semantically_equal(first, second)
    assert serialized["source_catalog_version"] == index.source_catalog_version
    assert serialized["extractor_version"] == index.extractor_version
    assert serialized["generated_at"] == "2026-07-15T08:00:00Z"
    assert [item["path"] for item in serialized["inputs"]] == sorted(
        item["path"] for item in serialized["inputs"]
    )
    assert project_files(tmp_path) == before
    assert not any("decision-context" in path and "manifest" in path for path in before)


@pytest.mark.parametrize(
    ("field", "reason_prefix"),
    [
        ("source_catalog_version", "source_catalog_version_changed:"),
        ("extractor_version", "extractor_version_changed:"),
        ("authority_policy_version", "authority_policy_version_changed:"),
        ("relation_policy_version", "relation_policy_version_changed:"),
        ("retrieval_policy_version", "retrieval_policy_version_changed:"),
        ("budget_policy_version", "budget_policy_version_changed:"),
    ],
)
def test_manifest_stale_reasons_distinguish_policy_versions(
    tmp_path: Path,
    field: str,
    reason_prefix: str,
) -> None:
    write_proposal(tmp_path, "PROP-001")
    index = _index(tmp_path)
    service = DecisionContextFreshnessService()
    manifest = service.manifest(
        index,
        generator_version="context-projection-v1",
        retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
        budget_policy_version=BUDGET_POLICY_VERSION,
    )
    stale_manifest = replace(manifest, **{field: "old-version"})

    result = service.check(
        stale_manifest,
        index,
        generator_version="context-projection-v1",
        retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
        budget_policy_version=BUDGET_POLICY_VERSION,
    )

    assert result.status == Freshness.STALE
    assert any(reason.startswith(reason_prefix) for reason in result.reasons)


def test_manifest_reports_source_presence_and_hash_changes(tmp_path: Path) -> None:
    proposal_dir = write_proposal(tmp_path, "PROP-001")
    service = DecisionContextFreshnessService()
    first_index = _index(tmp_path)
    manifest = service.manifest(first_index, generator_version="context-projection-v1")

    write_proposal(tmp_path, "PROP-001", decision_outcome="accepted")
    present_check = service.check(
        manifest,
        _index(tmp_path),
        generator_version="context-projection-v1",
    )
    assert present_check.status == Freshness.STALE
    assert any(reason.startswith("source_presence_changed:") for reason in present_check.reasons)

    current_index = _index(tmp_path)
    current_manifest = service.manifest(current_index, generator_version="context-projection-v1")
    proposal_path = proposal_dir / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8").replace("derived", "updated derived"),
        encoding="utf-8",
    )
    hash_check = service.check(
        current_manifest,
        _index(tmp_path),
        generator_version="context-projection-v1",
    )
    assert any(reason.startswith("source_hash_changed:") for reason in hash_check.reasons)
    assert "source_fingerprint_changed" in hash_check.reasons
    assert "semantic_fingerprint_changed" in hash_check.reasons

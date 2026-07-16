from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from p2p_engine.storage.filesystem import P2PWorkspace

from p2p_engine.core.project_readiness import (
    PROJECT_READINESS_NEUTRAL_DEPENDENCY_RANK,
    ProjectReadinessAssumptionSnapshot,
    ProjectReadinessGapKind,
    ProjectReadinessQuestionSnapshot,
    ProjectReadinessSectionSnapshot,
    ProjectReadinessSnapshot,
    readiness_snapshot_identity,
)
from p2p_engine.services.project_readiness import (
    ProjectReadinessGapService,
    ProjectReadinessPaginationService,
    ProjectReadinessSourceAccess,
)


def _snapshot(*, source_hash: str = "a", definition_valid: bool = True) -> ProjectReadinessSnapshot:
    identity = readiness_snapshot_identity(
        workspace_schema_version=1,
        workspace_schema_state="declared",
        vertical_id="software_project",
        vertical_version="1.0.0",
        vertical_lock_checksum="lock-checksum",
        profile="default",
        modules=(),
        source_hashes={".p2p/project/definition.yml": source_hash},
        policy_versions={"gap": 1, "snapshot": 1},
    )
    return ProjectReadinessSnapshot(
        identity=identity,
        definition_valid=definition_valid,
        definition_exists=True,
        fallback_used=False,
        vertical_source="internal",
        sections=(
            ProjectReadinessSectionSnapshot(
                section_id="decisions",
                title="Decisions",
                required=True,
                priority=20,
                definition_status="blocked",
                missing_required_fields=("decision_policy",),
                open_blocker_ids=("BLOCK-001",),
                assumptions=(
                    ProjectReadinessAssumptionSnapshot(
                        assumption_id="ASSUME-001",
                        status="to_validate",
                    ),
                ),
                heuristic_proposals=("PROP-010",),
            ),
            ProjectReadinessSectionSnapshot(
                section_id="scope",
                title="Scope",
                required=True,
                priority=10,
                definition_status="partial",
                missing_required_fields=("boundaries",),
                declared_proposals=("PROP-020",),
                active_declared_proposals=("PROP-020",),
            ),
        ),
        unmapped_proposals=("PROP-030", "PROP-040", "PROP-050"),
    )


def test_gap_classification_is_typed_prioritized_and_explainable() -> None:
    result = ProjectReadinessGapService().classify(_snapshot())

    assert result.gaps
    assert [gap.priority_class for gap in result.gaps] == sorted(
        gap.priority_class for gap in result.gaps
    )
    assert result.gaps[0].kind == ProjectReadinessGapKind.OWNER_DECISION_BLOCKER
    assumption = next(
        gap for gap in result.gaps if gap.kind == ProjectReadinessGapKind.ASSUMPTION_TO_VALIDATE
    )
    assert assumption.dependency_rank == PROJECT_READINESS_NEUTRAL_DEPENDENCY_RANK
    assert assumption.priority_rationale
    assert assumption.tie_break[-1] == assumption.gap_id
    incomplete = next(
        gap
        for gap in result.gaps
        if gap.kind == ProjectReadinessGapKind.INCOMPLETE_REQUIRED_DEFINITION
        and gap.section_id == "decisions"
    )
    assert incomplete.declared_evidence == ()
    assert incomplete.heuristic_suggestions == ("PROP-010",)


def test_gap_classification_covers_compatibility_authority_and_answered_state() -> None:
    snapshot = _snapshot()
    identity = replace(snapshot.identity, workspace_schema_state="invalid")
    first_section = replace(
        snapshot.sections[0],
        question_states=(
            ProjectReadinessQuestionSnapshot(
                question_id="PRQ-answered",
                revision=2,
                state="answered",
                target_kind="field",
                target_id="decision_policy",
            ),
            ProjectReadinessQuestionSnapshot(
                question_id="PRQ-stale",
                revision=1,
                state="to_answer",
                target_kind="field",
                target_id="legacy_field",
                applicability="vertical_mismatch",
            ),
        ),
    )
    snapshot = replace(
        snapshot,
        identity=identity,
        owner_available=False,
        sections=(first_section, snapshot.sections[1]),
    )

    result = ProjectReadinessGapService().classify(snapshot)
    kinds = {gap.kind for gap in result.gaps}

    assert ProjectReadinessGapKind.COMPATIBILITY_BLOCKER in kinds
    assert ProjectReadinessGapKind.AUTHORITY_BLOCKER in kinds
    assert ProjectReadinessGapKind.ANSWERED_NOT_APPLIED in kinds
    answered = next(gap for gap in result.gaps if gap.kind == ProjectReadinessGapKind.ANSWERED_NOT_APPLIED)
    assert answered.question_id == "PRQ-answered"
    assert answered.question_revision == 2


def test_gap_identity_is_independent_from_snapshot_drift() -> None:
    first = ProjectReadinessGapService().classify(_snapshot(source_hash="a"))
    second = ProjectReadinessGapService().classify(_snapshot(source_hash="b"))

    first_by_target = {(gap.kind, gap.section_id, gap.target_id): gap for gap in first.gaps}
    second_by_target = {(gap.kind, gap.section_id, gap.target_id): gap for gap in second.gaps}
    assert set(first_by_target) == set(second_by_target)
    for key in first_by_target:
        assert first_by_target[key].gap_id == second_by_target[key].gap_id
        assert first_by_target[key].identity_sha256 == second_by_target[key].identity_sha256
        assert first_by_target[key].snapshot_fingerprint != second_by_target[key].snapshot_fingerprint


def test_invalid_definition_returns_integrity_gap_without_fabricating_sections() -> None:
    snapshot = replace(_snapshot(definition_valid=False), sections=())

    result = ProjectReadinessGapService().classify(snapshot)

    assert result.gaps[0].kind == ProjectReadinessGapKind.INTEGRITY_BLOCKER
    assert result.gaps[0].next_operation == "p2p project definition show"
    assert all(not gap.section_id for gap in result.gaps)


def test_gap_pagination_is_stable_bounded_and_snapshot_bound() -> None:
    service = ProjectReadinessPaginationService()
    result = ProjectReadinessGapService().classify(_snapshot())

    first = service.page_gaps(result, limit=2)
    second = service.page_gaps(result, limit=2, cursor=first.next_cursor)

    assert first.truncated is True
    assert first.next_cursor
    assert set(item.gap_id for item in first.items).isdisjoint(
        item.gap_id for item in second.items
    )
    drifted = ProjectReadinessGapService().classify(_snapshot(source_hash="changed"))
    with pytest.raises(ValueError, match="stale_cursor"):
        service.page_gaps(drifted, limit=2, cursor=first.next_cursor)


@pytest.mark.parametrize("limit", [0, 101])
def test_gap_pagination_rejects_unbounded_limits(limit: int) -> None:
    result = ProjectReadinessGapService().classify(_snapshot())

    with pytest.raises(ValueError, match="between 1 and 100"):
        ProjectReadinessPaginationService().page_gaps(result, limit=limit)


def test_value_pagination_rejects_corrupt_and_cross_collection_cursors() -> None:
    service = ProjectReadinessPaginationService()
    page = service.page_values(
        collection="unmapped_proposals",
        snapshot_fingerprint="snapshot",
        values=("PROP-003", "PROP-001", "PROP-002"),
        limit=1,
    )

    with pytest.raises(ValueError, match="different collection"):
        service.page_values(
            collection="questions",
            snapshot_fingerprint="snapshot",
            values=("Q1", "Q2"),
            limit=1,
            cursor=page.next_cursor,
        )
    with pytest.raises(ValueError, match="Invalid readiness cursor"):
        service.page_values(
            collection="unmapped_proposals",
            snapshot_fingerprint="snapshot",
            values=("PROP-001",),
            cursor="not-a-cursor",
        )


def test_classification_and_pagination_do_not_read_after_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Snapshot Budget", vertical_id="base_project")
    snapshot = workspace.project_readiness_snapshot()

    def unexpected_read(_path: Path) -> bytes:
        raise AssertionError("read after readiness snapshot construction")

    monkeypatch.setattr(Path, "read_bytes", unexpected_read)
    result = ProjectReadinessGapService().classify(snapshot)
    page = ProjectReadinessPaginationService().page_gaps(result, limit=2)

    assert page.items


def test_source_access_reads_and_hashes_one_physical_preimage_once(tmp_path: Path) -> None:
    source = tmp_path / "source.yml"
    source.write_text("value: one\n", encoding="utf-8")
    calls: list[Path] = []

    def reader(path: Path) -> bytes:
        calls.append(path)
        return path.read_bytes()

    access = ProjectReadinessSourceAccess(root=tmp_path, reader=reader)

    assert access.read_optional(source) == b"value: one\n"
    assert access.read_optional(source) == b"value: one\n"
    assert calls == [source.resolve()]
    assert access.counts == {"source.yml": 1}


def test_representative_legacy_collection_is_bounded() -> None:
    values = tuple(f"PROP-{index:03d}" for index in range(1, 101))
    snapshot = replace(_snapshot(), unmapped_proposals=values)
    result = ProjectReadinessGapService().classify(snapshot)

    page = ProjectReadinessPaginationService().page_values(
        collection="unmapped_proposals",
        snapshot_fingerprint=result.snapshot.fingerprint,
        values=values,
    )

    assert page.total == 100
    assert len(page.items) == 20
    assert page.truncated is True
    assert page.payload_bytes < 64 * 1024


def test_oversized_record_reports_payload_diagnostic() -> None:
    page = ProjectReadinessPaginationService().page_values(
        collection="unmapped_proposals",
        snapshot_fingerprint="snapshot",
        values=("P" * (70 * 1024),),
    )

    assert page.items == ()
    assert page.truncated is True
    assert page.diagnostics[0].code == "P2P353_READINESS_PAYLOAD_LIMIT"


def test_gap_prefix_collision_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    import p2p_engine.services.project_readiness as readiness_module

    def colliding_identity(**values: object) -> tuple[str, str]:
        return "PGAP-collision", f"digest-{values['target_id']}"

    monkeypatch.setattr(readiness_module, "readiness_gap_identity", colliding_identity)

    with pytest.raises(ValueError, match="gap id collision"):
        ProjectReadinessGapService().classify(_snapshot())

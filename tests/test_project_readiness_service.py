from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from p2p_engine.storage.filesystem import P2PWorkspace

from p2p_engine.core.project_memory import (
    MemoryClassificationItem,
    MemoryClassificationSnapshot,
)
from p2p_engine.core.project_readiness import (
    PROJECT_READINESS_NEUTRAL_DEPENDENCY_RANK,
    ProjectReadinessAssumptionSnapshot,
    ProjectReadinessGapKind,
    ProjectReadinessQuestionSnapshot,
    ProjectReadinessSectionSnapshot,
    ProjectReadinessSnapshot,
    readiness_snapshot_identity,
)
from p2p_engine.core.project_structure import (
    ProjectStructure,
    StructureCriterion,
    StructureOrigin,
    StructureSection,
)
from p2p_engine.core.project_verticals import (
    ProjectDefinitionSectionState,
    ProjectDefinitionState,
    ProjectDefinitionView,
)
from p2p_engine.services.project_readiness import (
    ProjectReadinessCompositionService,
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
    assert all(
        not gap.next_operation.startswith("p2p project questions ")
        for gap in result.gaps
    )
    assert assumption.next_operation == "p2p project readiness questions next"
    assert incomplete.next_operation == "p2p project readiness questions next"


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
    compatibility = next(
        gap
        for gap in result.gaps
        if gap.kind == ProjectReadinessGapKind.COMPATIBILITY_BLOCKER
        and gap.question_id == "PRQ-stale"
    )
    assert compatibility.next_operation == (
        "p2p project readiness questions reconcile-preview --actor <ACTOR>"
    )


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


def test_project_readiness_v2_zero_active_criteria_is_not_configured(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Empty Structure", starter_id="empty", owner="owner")

    readiness = workspace.project_readiness_result()

    assert readiness.contract_version == "p2p-project-readiness/v2"
    assert readiness.status == "not_configured"
    assert readiness.definition is not None
    assert readiness.definition.ratio.denominator == 0
    assert readiness.definition.ratio.score is None
    assert readiness.evidence is not None
    assert readiness.evidence.ratio.score is None
    assert readiness.snapshot.structure_revision == workspace.project_structure().revision
    assert readiness.snapshot.structure_checksum == workspace.project_structure().checksum
    assert readiness.snapshot.memory_revision == workspace.project_memory_revision()


def test_memory_classification_debt_does_not_change_definition_readiness(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project(
        "Classification Separation",
        project_domain="software",
        vertical_id="software_project",
        owner="owner",
    )
    before = workspace.project_readiness_result()
    workspace.create_proposal_with_details(
        "Unassigned evidence",
        problem="A proposal exists but is not section-classified.",
        proposal="Keep classification debt outside the definition formula.",
    )
    after = workspace.project_readiness_result()

    assert before.definition is not None
    assert after.definition is not None
    assert after.definition.ratio.score == before.definition.ratio.score
    assert "memory classification" in " ".join(after.actions)
    assert after.evidence is not None
    assert after.evidence.ratio.exclusions["unassigned_items"] == 1


def test_readiness_v2_is_bounded_over_active_structure_and_indexed_memory(
    tmp_path: Path,
) -> None:
    section_count = 64
    sections = tuple(
        StructureSection(
            section_id=f"s{index:03d}",
            title=f"Section {index}",
            order=index,
        )
        for index in range(section_count)
    ) + (
        StructureSection(
            section_id="retired_section",
            title="Retired Section",
            order=section_count,
            lifecycle="retired",
        ),
    )
    criteria = tuple(
        criterion
        for index in range(section_count)
        for criterion in (
            StructureCriterion(
                criterion_id=f"c{index:03d}_definition",
                section_id=f"s{index:03d}",
                title=f"Definition {index}",
                order=index * 2,
            ),
            StructureCriterion(
                criterion_id=f"c{index:03d}_evidence",
                section_id=f"s{index:03d}",
                title=f"Evidence {index}",
                evaluation="declared_evidence",
                order=index * 2 + 1,
            ),
        )
    ) + (
        StructureCriterion(
            criterion_id="retired_criterion",
            section_id="retired_section",
            title="Retired Criterion",
            lifecycle="retired",
        ),
    )
    structure = ProjectStructure(
        structure_id="bounded_structure",
        revision=7,
        checksum="a" * 64,
        origin=StructureOrigin(
            kind="starter",
            identity="bounded",
            checksum=None,
            applied_at="2026-08-26T00:00:00Z",
            applied_by="test",
        ),
        sections=sections,
        criteria=criteria,
    )
    definition = ProjectDefinitionView(
        exists=True,
        valid=True,
        path=tmp_path / "definition.yml",
        state=ProjectDefinitionState(
            schema_version=1,
            vertical_id="bounded",
            vertical_version="1.0.0",
            structure_id=structure.structure_id,
            structure_revision=structure.revision,
            structure_checksum=structure.checksum,
            sections=[
                ProjectDefinitionSectionState(
                    section_id=f"s{index:03d}",
                    status="complete" if index % 2 == 0 else "missing",
                )
                for index in range(section_count)
            ],
        ),
    )
    classified_items = tuple(
        MemoryClassificationItem(
            object_type="proposal",
            object_id=f"PROP-{index + 1:03d}",
            lifecycle="active",
            state="section_classified",
            scope_kind="sections",
            section_ids=(f"s{index:03d}",),
            active_section_ids=(f"s{index:03d}",),
        )
        for index in range(0, section_count, 4)
    )
    debt_items = tuple(
        MemoryClassificationItem(
            object_type="proposal",
            object_id=f"PROP-{index + 101:03d}",
            lifecycle="active",
            state="unassigned",
            scope_kind="unassigned",
        )
        for index in range(section_count)
    )
    retired_item = MemoryClassificationItem(
        object_type="proposal",
        object_id="PROP-999",
        lifecycle="active",
        state="requires_reassignment",
        scope_kind="sections",
        section_ids=("retired_section",),
        retired_section_ids=("retired_section",),
    )
    classification = MemoryClassificationSnapshot(
        status="incomplete",
        structure_id=structure.structure_id,
        structure_revision=structure.revision,
        structure_checksum=structure.checksum,
        memory_revision="b" * 64,
        counts={
            "section_classified": len(classified_items),
            "unassigned": len(debt_items),
            "requires_reassignment": 1,
        },
        per_type={
            "proposal": {
                "section_classified": len(classified_items),
                "unassigned": len(debt_items),
                "requires_reassignment": 1,
            }
        },
        items=classified_items + debt_items + (retired_item,),
    )

    readiness = ProjectReadinessGapService().classify(
        ProjectReadinessCompositionService().compose(
            structure=structure,
            definition_view=definition,
            memory_classification=classification,
            workspace_schema_status=SimpleNamespace(
                current_version=4,
                state="current",
                layout_status="current",
            ),
            owner_available=True,
        )
    )

    assert readiness.definition is not None
    assert readiness.definition.ratio.denominator == section_count * 2
    assert readiness.definition.ratio.numerator == 48
    assert readiness.evidence is not None
    assert readiness.evidence.ratio.denominator == section_count * 2
    assert readiness.evidence.ratio.numerator == 32
    assert readiness.evidence.ratio.exclusions == {
        "not_applicable_weight": 0.0,
        "project_global_items": 0,
        "requires_reassignment_items": 1,
        "unassigned_items": section_count,
    }
    assert len(readiness.sections) == section_count
    assert all(section.section_id != "retired_section" for section in readiness.sections)

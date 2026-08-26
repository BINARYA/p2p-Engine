from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.core.vertical_memory import (
    VerticalMemoryContribution,
    VerticalMemorySection,
    VerticalProjectMemoryView,
)
from p2p_engine.core.project_memory import (
    MemoryClassificationItem,
    MemoryClassificationSnapshot,
)
from p2p_engine.services.project_publication_evidence import (
    ProjectPublicationEvidenceService,
)


def _write_sources(root: Path) -> tuple[Path, Path]:
    p2p_dir = root / ".p2p"
    project = p2p_dir / "project"
    active = p2p_dir / "proposals" / "PROP-001-active"
    historical = p2p_dir / "proposals" / "PROP-002-historical"
    change = p2p_dir / "changes" / "CHANGE-001-process"
    for path in (project, active, historical, change):
        path.mkdir(parents=True)
    (p2p_dir / "project.yml").write_text("project:\n  name: Demo\n", encoding="utf-8")
    (project / "definition.yml").write_text(
        "project_definition:\n  sections:\n  - id: product_scope\n    objective: Complete scope.\n",
        encoding="utf-8",
    )
    (active / "proposal.md").write_text("# Active\n\nComplete active content.\n", encoding="utf-8")
    (active / "decision-events.yml").write_text("events: []\n", encoding="utf-8")
    (active / "contributions.yml").write_text(
        "contributions:\n"
        "- id: C001\n  type: finding\n  author: alice\n  text: One.\n"
        "- id: C002\n  type: risk\n  author: bob\n  text: Two.\n"
        "- id: C003\n  type: assumption\n  author: ''\n  text: Three.\n",
        encoding="utf-8",
    )
    (historical / "proposal.md").write_text("# Historical\n\nOld content.\n", encoding="utf-8")
    (historical / "contributions.yml").write_text(
        "contributions:\n- id: C001\n  type: finding\n  author: ignored\n  text: Old.\n",
        encoding="utf-8",
    )
    (change / "change.md").write_text("# Change\n\nProcess record.\n", encoding="utf-8")
    output = root / "outputs" / "latest" / "project.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Complete Export\n", encoding="utf-8")
    return p2p_dir, output


def _vertical_view(*, mapped: bool = True) -> VerticalProjectMemoryView:
    contribution = VerticalMemoryContribution(
        contribution_id="VMC-001",
        proposal_id="PROP-001",
        title="Active",
        section_id="product_scope",
        authority="active",
        activation="accepted",
        effective_state="accepted",
        head_event_id="EVENT-001",
        head_event_type="accepted",
        rationale="Defines product scope.",
        constraints=(),
        applicability="direct",
        coverage_rationale="Owner confirmed.",
        source_path=".p2p/proposals/PROP-001-active/proposal.md",
        proposal_semantic_sha256="a" * 64,
        decision_semantic_sha256="b" * 64,
    )
    section = VerticalMemorySection(
        section_id="product_scope",
        title="Product Scope",
        purpose="Define scope.",
        required=True,
        priority=1,
        definition={"objective": "Complete scope."},
        questions=(),
        declared_questions=("What does the project include?",),
        active_contributions=(contribution,) if mapped else (),
        historical_contributions=(),
    )
    return VerticalProjectMemoryView(
        vertical_id="software_project",
        vertical_version="1.0.0",
        vertical_checksum="c" * 64,
        sections=(section,),
        unmapped_active_proposals=(() if mapped else ({"proposal_id": "PROP-001"},)),
        diagnostics=(),
        source_fingerprint_sha256="d" * 64,
        definition_exists=True,
        definition_valid=True,
        source="generated",
    )


def test_publication_evidence_is_complete_vertical_aware_and_deterministic(tmp_path: Path) -> None:
    p2p_dir, export = _write_sources(tmp_path)
    service = ProjectPublicationEvidenceService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        accepted_proposals=lambda: [{"proposal_id": "PROP-001"}],
        vertical_memory=lambda: _vertical_view(),
    )

    first = service.build(
        source_fingerprint_sha256="e" * 64,
        source_export_path=export,
        source_export_sha256="f" * 64,
    )
    second = service.build(
        source_fingerprint_sha256="e" * 64,
        source_export_path=export,
        source_export_sha256="f" * 64,
    )

    assert first == second
    assert first["semantic_sha256"] == second["semantic_sha256"]
    entries = {item["source_path"]: item for item in first["entries"]}
    active = entries[".p2p/proposals/PROP-001-active/proposal.md"]
    historical = entries[".p2p/proposals/PROP-002-historical/proposal.md"]
    process = entries[".p2p/changes/CHANGE-001-process/change.md"]
    assert active["vertical_sections"] == ["product_scope"]
    assert active["payload"]["value"] == "# Active\n\nComplete active content.\n"
    assert active["content_mode"] == "inline_complete"
    assert historical["editorial_class"] == "historical_context"
    assert process["editorial_class"] == "process_only"
    assert first["vertical"]["reader_questions"][0]["question"] == "What does the project include?"
    assert first["counts"]["total"] == len(first["entries"])


def test_publication_evidence_retains_active_unmapped_sources(tmp_path: Path) -> None:
    p2p_dir, export = _write_sources(tmp_path)
    service = ProjectPublicationEvidenceService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        accepted_proposals=lambda: [{"proposal_id": "PROP-001"}],
        vertical_memory=lambda: _vertical_view(mapped=False),
    )

    payload = service.build(
        source_fingerprint_sha256="e" * 64,
        source_export_path=export,
        source_export_sha256="f" * 64,
    )

    proposal = next(
        item for item in payload["entries"] if item["source_path"].endswith("PROP-001-active/proposal.md")
    )
    assert proposal["editorial_class"] == "cross_cutting"
    assert payload["counts"]["cross_cutting"] > 0


def test_publication_evidence_retains_explicit_unassigned_memory(tmp_path: Path) -> None:
    p2p_dir, export = _write_sources(tmp_path)
    classification = MemoryClassificationSnapshot(
        status="incomplete",
        structure_id="publication-structure",
        structure_revision=3,
        structure_checksum="a" * 64,
        memory_revision="b" * 64,
        counts={"active_total": 1, "unassigned": 1},
        per_type={"proposal": {"active_total": 1, "unassigned": 1}},
        items=(
            MemoryClassificationItem(
                object_type="proposal",
                object_id="PROP-001",
                lifecycle="accepted",
                state="unassigned",
                scope_kind="unassigned",
                decision_blocking=True,
            ),
        ),
    )
    service = ProjectPublicationEvidenceService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        accepted_proposals=lambda: [{"proposal_id": "PROP-001"}],
        vertical_memory=lambda: _vertical_view(),
        memory_classification=lambda: classification,
    )

    payload = service.build(
        source_fingerprint_sha256="e" * 64,
        source_export_path=export,
        source_export_sha256="f" * 64,
    )

    proposal = next(
        item
        for item in payload["entries"]
        if item["source_path"].endswith("PROP-001-active/proposal.md")
    )
    assert payload["memory_classification"] == classification.to_dict()
    assert proposal["memory_scope_kind"] == "unassigned"
    assert proposal["vertical_sections"] == []
    assert proposal["editorial_class"] == "cross_cutting"
    assert any(item["code"] == "publication_cross_cutting_evidence" for item in payload["diagnostics"])


def test_publication_contribution_summary_uses_only_active_records(tmp_path: Path) -> None:
    p2p_dir, export = _write_sources(tmp_path)
    service = ProjectPublicationEvidenceService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        accepted_proposals=lambda: [{"proposal_id": "PROP-001"}],
    )

    payload = service.build(
        source_fingerprint_sha256="e" * 64,
        source_export_path=export,
        source_export_sha256="f" * 64,
    )

    summary = payload["contributions"]
    assert summary["denominator"] == 3
    assert {item["author"] for item in summary["rows"]} == {"alice", "bob", "Unattributed"}
    assert sum(item["basis_points"] for item in summary["rows"]) == 10_000


def test_publication_evidence_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    p2p_dir, export = _write_sources(tmp_path)
    (p2p_dir / "project" / "definition.yml").write_text("value: one\nvalue: two\n", encoding="utf-8")
    service = ProjectPublicationEvidenceService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        accepted_proposals=lambda: [],
    )

    with pytest.raises(ValueError, match="Duplicate YAML key"):
        service.build(
            source_fingerprint_sha256="e" * 64,
            source_export_path=export,
            source_export_sha256="f" * 64,
        )


def test_publication_evidence_classifies_duplicates_conflicts_and_gaps(tmp_path: Path) -> None:
    p2p_dir, export = _write_sources(tmp_path)
    duplicate = p2p_dir / "proposals" / "PROP-003-duplicate"
    duplicate.mkdir()
    duplicate.joinpath("proposal.md").write_text(
        "# Active\n\nComplete active content.\n",
        encoding="utf-8",
    )
    (p2p_dir / "project" / "questions.yml").write_text(
        "questions:\n- id: Q-001\n  text: What remains unknown?\n",
        encoding="utf-8",
    )
    (p2p_dir / "project" / "conflicts.yml").write_text(
        "conflicts:\n- id: C-001\n  status: unresolved\n",
        encoding="utf-8",
    )
    service = ProjectPublicationEvidenceService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        accepted_proposals=lambda: [
            {"proposal_id": "PROP-001"},
            {"proposal_id": "PROP-003"},
        ],
    )

    payload = service.build(
        source_fingerprint_sha256="e" * 64,
        source_export_path=export,
        source_export_sha256="f" * 64,
    )

    classes = {item["editorial_class"] for item in payload["entries"]}
    assert {"duplicate", "contradictory", "insufficient"} <= classes
    assert payload["counts"]["duplicate"] == 1
    assert payload["counts"]["contradictory"] == 1
    assert payload["counts"]["insufficient"] == 1
    assert "generated_registries" in payload["source_catalog"]["excluded_classes"]


def test_publication_evidence_excludes_generated_project_projections(tmp_path: Path) -> None:
    p2p_dir, export = _write_sources(tmp_path)
    project = p2p_dir / "project"
    for name in ("overview.md", "decisions-map.yml", "projection-manifest.yml"):
        (project / name).write_text("generated: true\n", encoding="utf-8")
    service = ProjectPublicationEvidenceService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        accepted_proposals=lambda: [{"proposal_id": "PROP-001"}],
    )

    payload = service.build(
        source_fingerprint_sha256="e" * 64,
        source_export_path=export,
        source_export_sha256="f" * 64,
    )

    paths = {item["source_path"] for item in payload["entries"]}
    assert ".p2p/project/definition.yml" in paths
    assert not any(path.endswith(("overview.md", "decisions-map.yml", "projection-manifest.yml")) for path in paths)
    assert "overview.md" in payload["source_catalog"]["excluded_project_files"]


def test_evidence_id_is_stable_when_only_vertical_classification_changes(tmp_path: Path) -> None:
    p2p_dir, export = _write_sources(tmp_path)

    def build(mapped: bool) -> dict[str, object]:
        return ProjectPublicationEvidenceService(
            root=tmp_path,
            p2p_dir=p2p_dir,
            accepted_proposals=lambda: [{"proposal_id": "PROP-001"}],
            vertical_memory=lambda: _vertical_view(mapped=mapped),
        ).build(
            source_fingerprint_sha256="e" * 64,
            source_export_path=export,
            source_export_sha256="f" * 64,
        )

    mapped = next(
        item
        for item in build(True)["entries"]
        if item["source_path"].endswith("PROP-001-active/proposal.md")
    )
    unmapped = next(
        item
        for item in build(False)["entries"]
        if item["source_path"].endswith("PROP-001-active/proposal.md")
    )

    assert mapped["editorial_class"] == "project_evidence"
    assert unmapped["editorial_class"] == "cross_cutting"
    assert mapped["id"] == unmapped["id"]
    assert mapped["semantic_sha256"] == unmapped["semantic_sha256"]

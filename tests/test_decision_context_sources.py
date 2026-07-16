from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.core.decision_context import Completeness, SourceKind, SourcePresence
from p2p_engine.services.decision_context import ProjectDecisionContextService
from p2p_engine.services.decision_context_sources import (
    DecisionContextSourceService,
    FileSourceAccessor,
    SourceDescriptor,
    SourceClassification,
    fragments_for_label,
    parse_markdown_source,
)
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.decision_context_fixtures import initialize_project, project_files, write_proposal


class ReverseAccessor(FileSourceAccessor):
    def proposal_directories(self, proposals_root: Path) -> list[Path]:
        return list(reversed(super().proposal_directories(proposals_root)))


def test_source_session_reads_hashes_and_parses_each_source_once(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001", decision_outcome="accepted")
    write_proposal(tmp_path, "PROP-002")

    session = DecisionContextSourceService(root=tmp_path).build_proposal_decision_session()

    assert session.access_stats.discovery_passes == 1
    assert set(session.access_stats.reads.values()) == {1}
    assert set(session.access_stats.hashes.values()) == {1}
    assert set(session.access_stats.parses.values()) == {1}
    assert len(session.sources) == 4
    assert sum(source.presence == SourcePresence.MISSING for source in session.sources) == 1


def test_source_fingerprint_is_independent_from_directory_enumeration(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-002", decision_outcome="accepted")
    write_proposal(tmp_path, "PROP-001", decision_outcome="deferred")

    normal = DecisionContextSourceService(root=tmp_path).build_proposal_decision_session()
    reversed_session = DecisionContextSourceService(root=tmp_path, accessor=ReverseAccessor()).build_proposal_decision_session()

    assert normal.source_fingerprint_sha256 == reversed_session.source_fingerprint_sha256
    assert [source.path for source in normal.sources] == [source.path for source in reversed_session.sources]


def test_missing_governed_root_is_fatal(tmp_path: Path) -> None:
    session = DecisionContextSourceService(root=tmp_path).build_proposal_decision_session()

    assert session.completeness == Completeness.UNAVAILABLE
    assert session.diagnostics[0].fatal is True
    assert session.diagnostics[0].code == "DC-SOURCE-MISSING-GOVERNED-ROOT"


def test_project_questions_are_conditional_inactive_quality_sources_without_relations(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Decision Context Questions", owner="owner", vertical_id="base_project")

    index = workspace.decision_context_index()

    source = next(item for item in index.sources if item.source_kind == SourceKind.PROJECT_QUESTIONS)
    assert source.classification == SourceClassification.QUALITY_METADATA
    question_evidence = {
        item.evidence_id: item
        for item in index.evidence
        if item.source_kind == SourceKind.PROJECT_QUESTIONS
    }
    records = [
        item
        for item in index.records
        if any(evidence_id in question_evidence for evidence_id in item.evidence_ids)
    ]
    assert records
    assert all(item.activation.value == "inactive" for item in records)
    evidence_ids = set(question_evidence)
    assert not any(set(item.evidence_ids) & evidence_ids for item in index.relations)


def test_schema_v1_without_project_questions_has_no_missing_source_diagnostic(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Legacy Context", owner="owner")
    (tmp_path / ".p2p" / "project" / "questions.yml").unlink()
    schema_path = tmp_path / ".p2p" / "project" / "workspace-schema.yml"
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    schema["workspace_schema"]["current_version"] = 1
    schema_path.write_text(yaml.safe_dump(schema, sort_keys=False), encoding="utf-8")

    index = workspace.decision_context_index()

    assert not any(item.source_kind == SourceKind.PROJECT_QUESTIONS for item in index.sources)
    assert not any("question" in item.message.casefold() for item in index.diagnostics)


def test_applied_project_question_is_inactive_traceability_without_definition_double_count(
    tmp_path: Path,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Applied Question Context", owner="owner", vertical_id="base_project")
    question = workspace.next_project_question()
    assert question is not None
    unique_answer = "Owner-defined-context-value-9f31"
    workspace.answer_project_question(
        question.question_id,
        values={"value": unique_answer},
        actor="owner",
        expected_revision=question.revision,
    )
    preview = workspace.preview_project_readiness_convergence(
        [question.question_id],
        actor="owner",
    )
    applied = workspace.apply_project_readiness_convergence(
        [question.question_id],
        actor="owner",
        preview_token=preview.preview.preview_token,
        confirm=True,
    )
    assert applied.status == "applied"

    index = workspace.decision_context_index()
    question_evidence = {
        item.evidence_id
        for item in index.evidence
        if item.source_kind == SourceKind.PROJECT_QUESTIONS
    }
    question_records = [
        item
        for item in index.records
        if set(item.evidence_ids) & question_evidence
    ]
    active_answer_records = [
        item
        for item in index.records
        if item.activation.value == "active" and unique_answer in item.text
    ]

    assert question_records
    assert all(item.activation.value == "inactive" for item in question_records)
    assert len(active_answer_records) == 1
    assert active_answer_records[0].owner_id == "PROJECT"


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_markdown_parser_handles_line_endings_and_heading_spacing(tmp_path: Path, newline: str) -> None:
    proposal_dir = write_proposal(tmp_path, "PROP-001", newline=newline)
    content = (proposal_dir / "proposal.md").read_bytes().replace(b"## Problem", b"## Problem\n")
    descriptor = SourceDescriptor(
        path=proposal_dir / "proposal.md",
        owner_id="PROP-001",
        source_kind=SourceKind.PROPOSAL_BODY,
        classification=SourceClassification.CANONICAL_SEMANTIC,
        required=True,
    )

    document, diagnostics = parse_markdown_source(
        descriptor=descriptor,
        relative_path=".p2p/proposals/prop-001-example/proposal.md",
        content=content,
        source_hash="hash",
    )

    assert fragments_for_label(document, "Problem")[0].text.startswith("The project")
    assert all(item.code != "DC-SOURCE-MALFORMED-YAML" for item in diagnostics)


def test_markdown_parser_ignores_headings_inside_fences_and_tracks_duplicates(tmp_path: Path) -> None:
    proposal_dir = write_proposal(tmp_path, "PROP-001")
    path = proposal_dir / "proposal.md"
    content = path.read_text(encoding="utf-8")
    content += "\n## Notes\n\n```markdown\n## Problem\nignored\n```\n\n## Notes\n\nsecond\n"
    descriptor = SourceDescriptor(
        path=path,
        owner_id="PROP-001",
        source_kind=SourceKind.PROPOSAL_BODY,
        classification=SourceClassification.CANONICAL_SEMANTIC,
        required=True,
    )

    document, diagnostics = parse_markdown_source(
        descriptor=descriptor,
        relative_path="proposal.md",
        content=content.encode(),
        source_hash="hash",
    )

    assert len(fragments_for_label(document, "Problem")) == 1
    assert [fragment.occurrence for fragment in fragments_for_label(document, "Notes")] == [1, 2]
    assert any(item.code == "DC-SOURCE-DUPLICATE-SECTION" for item in diagnostics)


@pytest.mark.parametrize(
    ("frontmatter", "code"),
    [
        ("---\nkey: [\n---\n", "DC-SOURCE-MALFORMED-YAML"),
        ("---\nkey: one\nkey: two\n---\n", "DC-SOURCE-DUPLICATE-KEY"),
        ("---\n- one\n- two\n---\n", "DC-SOURCE-INVALID-FRONTMATTER-SHAPE"),
    ],
)
def test_frontmatter_failures_are_diagnostic_and_body_remains_parseable(
    tmp_path: Path,
    frontmatter: str,
    code: str,
) -> None:
    proposal_dir = write_proposal(tmp_path, "PROP-001")
    path = proposal_dir / "proposal.md"
    content = frontmatter + path.read_text(encoding="utf-8")
    descriptor = SourceDescriptor(
        path=path,
        owner_id="PROP-001",
        source_kind=SourceKind.PROPOSAL_BODY,
        classification=SourceClassification.CANONICAL_SEMANTIC,
        required=True,
    )

    document, diagnostics = parse_markdown_source(
        descriptor=descriptor,
        relative_path="proposal.md",
        content=content.encode(),
        source_hash="hash",
    )

    assert document.completeness == Completeness.PARTIAL
    assert fragments_for_label(document, "Proposal")
    assert any(item.code == code for item in diagnostics)


def test_build_and_query_foundation_is_read_only_and_fresh_in_same_service(tmp_path: Path) -> None:
    proposal_dir = write_proposal(tmp_path, "PROP-001")
    service = ProjectDecisionContextService(root=tmp_path)
    before = project_files(tmp_path)

    first = service.build_index()
    proposal_path = proposal_dir / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8").replace(
            "Build a derived decision context index.",
            "Build a fresh derived decision context index.",
        ),
        encoding="utf-8",
    )
    expected_after_edit = project_files(tmp_path)
    second = service.build_index()

    first_claim = next(record for record in first.records if record.kind.value == "proposal_claim")
    second_claim = next(record for record in second.records if record.kind.value == "proposal_claim")
    assert first_claim.record_id == second_claim.record_id
    assert first_claim.text_sha256 != second_claim.text_sha256
    assert first.source_fingerprint_sha256 != second.source_fingerprint_sha256
    assert project_files(tmp_path) == expected_after_edit
    assert before.keys() == expected_after_edit.keys()


def test_missing_optional_decision_changes_fingerprint_when_created(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001")
    service = ProjectDecisionContextService(root=tmp_path)
    first = service.build_index()

    write_proposal(tmp_path, "PROP-001", decision_outcome="accepted")
    second = service.build_index()

    assert first.source_fingerprint_sha256 != second.source_fingerprint_sha256
    assert any(record.kind.value == "decision_state" for record in second.records)

from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.core.decision_context import (
    AUTHORITY_RANK,
    Activation,
    Authority,
    Canonicality,
    Confidence,
    NodeType,
    RecordKind,
    RelationType,
)
from p2p_engine.services.decision_context import ProjectDecisionContextService
from p2p_engine.services.decision_context_authority import (
    AuthorityPolicy,
    SourceAuthority,
    lifecycle_rules,
)
from p2p_engine.services.decision_context_topology import (
    build_adjacency,
    relation_aliases,
    traverse_relations,
)
from tests.decision_context_fixtures import write_markdown, write_proposal, write_yaml


def _build(root: Path):
    return ProjectDecisionContextService(root=root).build_index()


def _accepted_pair(root: Path) -> None:
    write_proposal(root, "PROP-001", status="accepted", decision_outcome="accepted")
    write_proposal(root, "PROP-002", status="accepted", decision_outcome="accepted")


def test_authority_rank_and_lifecycle_policy_are_complete() -> None:
    assert list(AUTHORITY_RANK.values()) == sorted(AUTHORITY_RANK.values(), reverse=True)
    assert set(AUTHORITY_RANK) == set(Authority)
    rules = lifecycle_rules()
    assert rules["accepted"].decision_activation == Activation.ACTIVE
    assert rules["accepted_with_changes"].decision_authority == Authority.CONDITIONALLY_ACCEPTED_DECISION
    assert rules["deferred"].decision_activation == Activation.UNRESOLVED
    for outcome in ("rejected", "split", "merged_into_other", "superseded"):
        assert rules[outcome].proposal_activation == Activation.HISTORICAL
    assert rules["draft"].proposal_activation == Activation.EXPLORATORY


def test_authority_policy_rejects_unsupported_combinations() -> None:
    policy = AuthorityPolicy()
    with pytest.raises(ValueError, match="Unsupported"):
        policy.validate(
            SourceAuthority(
                Canonicality.DERIVED,
                Authority.HEURISTIC_SIGNAL,
                Activation.ACTIVE,
                Confidence.HEURISTIC,
            )
        )
    with pytest.raises(ValueError, match="Heuristic confidence"):
        policy.validate(
            SourceAuthority(
                Canonicality.CANONICAL,
                Authority.SYSTEM_STATE,
                Activation.ACTIVE,
                Confidence.HEURISTIC,
            )
        )


def test_source_catalog_excludes_derived_and_generated_paths(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001")
    write_yaml(tmp_path, ".p2p/registries/proposals.yml", {"records": ["PROP-001"]})
    write_markdown(tmp_path, "outputs/latest/project.md", title="Generated")
    write_markdown(tmp_path, ".p2p/outputs/generated-prompt.md", title="Prompt")
    paths = {source.path for source in _build(tmp_path).sources}
    assert not any("registries" in path for path in paths)
    assert not any(path.startswith("outputs/") for path in paths)
    assert not any("generated-prompt" in path for path in paths)


def test_artifact_metadata_does_not_invent_owner_confirmation(tmp_path: Path) -> None:
    _accepted_pair(tmp_path)
    proposal_dir = tmp_path / ".p2p/proposals/prop-001-example"
    write_yaml(
        tmp_path,
        str((proposal_dir / "related-proposals.yml").relative_to(tmp_path)),
        {"related_proposals": [{"proposal": "PROP-002", "relationship": "related"}]},
    )
    relation = next(item for item in _build(tmp_path).relations if item.scope == "proposal_relation")
    assert relation.authority == Authority.AGENT_PROPOSED_EVIDENCE

    write_yaml(
        tmp_path,
        str((proposal_dir / "artifact-state.yml").relative_to(tmp_path)),
        {
            "proposal_artifacts": {
                "artifacts": [
                    {
                        "filename": "related-proposals.yml",
                        "confirmation": "owner_confirmed",
                    }
                ]
            }
        },
    )
    relation = next(item for item in _build(tmp_path).relations if item.scope == "proposal_relation")
    assert relation.authority == Authority.OWNER_CONFIRMED_EVIDENCE


def test_change_relations_merge_duplicate_evidence_and_report_divergence(tmp_path: Path) -> None:
    _accepted_pair(tmp_path)
    change_path = ".p2p/changes/CHANGE-001-example"
    write_markdown(
        tmp_path,
        f"{change_path}/change.md",
        title="CHANGE-001 - Example",
        frontmatter={
            "change_id": "CHANGE-001",
            "title": "Example",
            "status": "planned",
            "source": {"accepted_proposals": ["PROP-001"]},
        },
    )
    write_yaml(tmp_path, f"{change_path}/included-proposals.yml", {"included_proposals": ["PROP-001"]})
    write_yaml(tmp_path, f"{change_path}/included-decisions.yml", {"included_decisions": [{"proposal": "PROP-001"}]})
    index = _build(tmp_path)
    included = [
        item
        for item in index.relations
        if item.source_id == "CHANGE-001"
        and item.target_id == "PROP-001"
        and item.relation_type == RelationType.INCLUDES
    ]
    assert len(included) == 1
    assert len(included[0].evidence_ids) == 2
    assert not any(item.code == "DC-SOURCE-DIVERGENT-CHANGE-LINKS" for item in index.diagnostics)
    assert any(item.target_id == "decision:PROP-001" for item in index.relations)

    write_yaml(tmp_path, f"{change_path}/included-proposals.yml", {"included_proposals": ["PROP-002"]})
    divergent = _build(tmp_path)
    assert any(item.code == "DC-SOURCE-DIVERGENT-CHANGE-LINKS" for item in divergent.diagnostics)


@pytest.mark.parametrize(
    ("relationship", "expected"),
    [
        ("extends", RelationType.DEPENDS_ON),
        ("builds_on", RelationType.DEPENDS_ON),
        ("compatible_with", RelationType.REFERENCES),
        ("overlaps", RelationType.REFERENCES),
        ("supersedes", RelationType.SUPERSEDES),
    ],
)
def test_related_proposal_aliases(relationship: str, expected: RelationType, tmp_path: Path) -> None:
    _accepted_pair(tmp_path)
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/related-proposals.yml",
        {
            "related_proposals": {
                "proposal_id": "PROP-001",
                "items": [{"id": "PROP-002", "relationship": relationship}],
            }
        },
    )
    relation = next(item for item in _build(tmp_path).relations if item.scope == "proposal_relation")
    assert relation.relation_type == expected
    assert relationship in relation_aliases()


def test_unsupported_self_and_missing_relations_are_quarantined(tmp_path: Path) -> None:
    _accepted_pair(tmp_path)
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/related-proposals.yml",
        {
            "related_proposals": [
                {"proposal": "PROP-001", "relationship": "related"},
                {"proposal": "PROP-999", "relationship": "related"},
                {"proposal": "PROP-002", "relationship": "teleports_to"},
            ]
        },
    )
    index = _build(tmp_path)
    assert not any(item.scope == "proposal_relation" for item in index.relations)
    assert {item.code for item in index.diagnostics} >= {
        "DC-RELATION-SELF",
        "DC-RELATION-INVALID-TARGET",
        "DC-RELATION-UNSUPPORTED-TYPE",
    }


def test_impact_map_creates_typed_symbolic_nodes(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001")
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/impact-map.yml",
        {
            "impact": {
                "capabilities": ["decision memory"],
                "surfaces": [{"surface": "CLI"}],
                "features": ["retrieval"],
                "commands": [{"command": "p2p context"}],
                "files": [{"path": "src/p2p_engine/context.py"}],
            }
        },
    )
    index = _build(tmp_path)
    assert {node.node_type for node in index.nodes} >= {
        NodeType.CAPABILITY,
        NodeType.SURFACE,
        NodeType.FEATURE,
        NodeType.COMMAND,
        NodeType.FILE,
    }
    assert {item.relation_type for item in index.relations} >= {
        RelationType.AFFECTS_CAPABILITY,
        RelationType.AFFECTS_SURFACE,
        RelationType.AFFECTS_FEATURE,
        RelationType.TOUCHES_COMMAND,
        RelationType.TOUCHES_FILE,
    }


def test_conflicts_are_symmetric_single_edges_with_resolution(tmp_path: Path) -> None:
    _accepted_pair(tmp_path)
    write_yaml(
        tmp_path,
        ".p2p/project/conflicts.yml",
        {
            "conflicts": [
                {
                    "proposals": ["PROP-002", "PROP-001"],
                    "winner": "PROP-001",
                    "rejected": "PROP-002",
                },
                {"proposals": ["PROP-001", "PROP-002"]},
            ]
        },
    )
    index = _build(tmp_path)
    conflicts = [item for item in index.relations if item.relation_type == RelationType.CONFLICTS_WITH]
    assert len(conflicts) == 1
    assert (conflicts[0].source_id, conflicts[0].target_id) == ("PROP-001", "PROP-002")
    assert len(conflicts[0].evidence_ids) == 2
    assert any(item.relation_type == RelationType.SUPERSEDES for item in index.relations)
    incoming, outgoing = build_adjacency(index.relations)
    assert conflicts[0].relation_id in outgoing["PROP-001"]
    assert conflicts[0].relation_id in outgoing["PROP-002"]
    assert conflicts[0].relation_id in incoming["PROP-001"]
    assert conflicts[0].relation_id in incoming["PROP-002"]


def test_project_choices_are_distinct_from_proposal_local_votes(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001")
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/contributions.yml",
        {"contributions": [{"id": "CHOICE-PROP-001-001", "status": "open"}]},
    )
    choice_path = ".p2p/choices/CHOICE-001-example"
    write_markdown(
        tmp_path,
        f"{choice_path}/choice.md",
        title="CHOICE-001 - Example",
        frontmatter={
            "choice_id": "CHOICE-001",
            "title": "Example",
            "status": "decided",
            "related": {"proposals": ["PROP-001"]},
        },
    )
    write_markdown(
        tmp_path,
        f"{choice_path}/decision.md",
        title="Decision - CHOICE-001",
        sections=(("Status", "`decided`"), ("Selected Option", "Option A"), ("Reason", "Bounded scope.")),
    )
    index = _build(tmp_path)
    choice_nodes = [item.node_id for item in index.nodes if item.node_type == NodeType.CHOICE]
    assert choice_nodes == ["CHOICE-001"]
    assert any(
        item.authority == Authority.DECIDED_PROJECT_CHOICE and item.text == "Option A"
        for item in index.records
    )
    local_vote = next(item for item in index.records if "CHOICE-PROP" in item.text)
    assert local_vote.kind == RecordKind.EVENT
    assert local_vote.activation == Activation.INACTIVE


def test_open_choice_placeholder_is_not_a_decided_choice(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001")
    choice_path = ".p2p/choices/CHOICE-001-example"
    write_markdown(
        tmp_path,
        f"{choice_path}/choice.md",
        title="CHOICE-001 - Example",
        frontmatter={"choice_id": "CHOICE-001", "title": "Example", "status": "open"},
    )
    write_markdown(
        tmp_path,
        f"{choice_path}/decision.md",
        title="Decision - CHOICE-001",
        sections=(("Status", "`pending`"), ("Selected Option", "Pending."), ("Reason", "Pending.")),
    )

    index = _build(tmp_path)

    assert not any(
        record.owner_id == "CHOICE-001"
        and record.authority == Authority.DECIDED_PROJECT_CHOICE
        for record in index.records
    )


def test_choice_blocks_are_normalized_and_missing_targets_are_quarantined(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001")
    choice_path = ".p2p/choices/CHOICE-001-example"
    write_markdown(
        tmp_path,
        f"{choice_path}/choice.md",
        title="CHOICE-001 - Example",
        frontmatter={"choice_id": "CHOICE-001", "title": "Example", "status": "open"},
    )
    write_yaml(
        tmp_path,
        f"{choice_path}/links.yml",
        {
            "blocks": [
                {"target": "PROP-001", "target_type": "proposal", "status": "active"},
                {"target": "PROP-999", "target_type": "proposal", "status": "active"},
            ]
        },
    )

    index = _build(tmp_path)
    blocks = [relation for relation in index.relations if relation.relation_type == RelationType.BLOCKS]

    assert [(relation.source_id, relation.target_id) for relation in blocks] == [
        ("CHOICE-001", "PROP-001")
    ]
    assert any(
        diagnostic.code == "DC-RELATION-INVALID-TARGET"
        and diagnostic.target_id == "PROP-999"
        for diagnostic in index.diagnostics
    )


def test_quality_metadata_never_activates_a_decision(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001")
    write_yaml(tmp_path, ".p2p/proposals/prop-001-example/readiness.yml", {"score": 100})
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/questions.yml",
        {
            "proposal_questions": {
                "questions": [
                    {"id": "Q001", "state": "answered", "applied_to_proposal": False},
                    {"id": "Q002", "state": "applied", "applied_to_proposal": True},
                ]
            }
        },
    )
    records = [item for item in _build(tmp_path).records if item.kind == RecordKind.EVENT]
    assert records
    assert all(item.kind != RecordKind.DECISION_STATE for item in records)
    readiness = next(item for item in records if item.text.startswith("Readiness"))
    assert readiness.activation == Activation.INACTIVE
    assert next(item for item in records if "Q001" in item.text).activation == Activation.INACTIVE
    assert next(item for item in records if "Q002" in item.text).activation == Activation.ACTIVE


def test_precedents_governance_allowlist_and_definition_constraints(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001")
    choice_path = ".p2p/choices/CHOICE-001-example"
    write_markdown(
        tmp_path,
        f"{choice_path}/choice.md",
        title="CHOICE-001",
        frontmatter={"choice_id": "CHOICE-001", "title": "Example", "status": "open"},
    )
    write_yaml(
        tmp_path,
        ".p2p/governance/decision-precedents.yml",
        {
            "precedents": [
                {
                    "id": "DP001",
                    "statement": "Prefer deterministic local reads.",
                    "related_proposals": ["PROP-001"],
                    "related_choices": ["CHOICE-001"],
                    "tags": ["retrieval"],
                }
            ]
        },
    )
    write_markdown(
        tmp_path,
        ".p2p/governance/constitution.md",
        title="Constitution",
        sections=(("Purpose", "Preserve owner authority."), ("Uncataloged Notes", "Do not ingest me.")),
    )
    write_yaml(
        tmp_path,
        ".p2p/project/definition.yml",
        {"purpose": "Decision support", "constraints": ["No network retrieval"], "random_notes": "Ignore me"},
    )
    records = _build(tmp_path).records
    precedent = next(item for item in records if item.kind == RecordKind.PRECEDENT)
    assert precedent.authority == Authority.EXPLICIT_DECISION_PRECEDENT
    assert precedent.owner_id == "precedent:DP001"
    assert precedent.applicability_tokens == (
        "choice:CHOICE-001",
        "proposal:PROP-001",
        "tag:retrieval",
    )
    applicability = [
        item for item in _build(tmp_path).relations if item.scope == "precedent_applicability"
    ]
    assert {item.target_id for item in applicability} == {"PROP-001", "CHOICE-001"}
    constraints = [item.text for item in records if item.kind == RecordKind.CONSTRAINT]
    assert any("Preserve owner authority" in item for item in constraints)
    assert "Decision support" in constraints
    assert "No network retrieval" in constraints
    assert not any("Do not ingest me" in item or "Ignore me" in item for item in constraints)


def test_incompatible_active_lineage_assertions_emit_diagnostic(tmp_path: Path) -> None:
    _accepted_pair(tmp_path)
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/related-proposals.yml",
        {
            "related_proposals": [
                {"proposal": "PROP-002", "relationship": "supersedes"},
                {"proposal": "PROP-002", "relationship": "split_into"},
            ]
        },
    )
    index = _build(tmp_path)
    assert any(item.code == "DC-RELATION-INCOMPATIBLE-ASSERTIONS" for item in index.diagnostics)


def test_dependency_alias_is_supported_but_ambiguous_terms_require_curation(tmp_path: Path) -> None:
    _accepted_pair(tmp_path)
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/related-proposals.yml",
        {
            "related_proposals": [
                {"proposal": "PROP-002", "relationship": "dependency"},
                {"proposal": "PROP-002", "relationship": "enables"},
                {"proposal": "PROP-002", "relationship": "informs"},
                {"proposal": "PROP-002", "relationship": "constrained_by"},
            ]
        },
    )

    index = _build(tmp_path)

    dependencies = [item for item in index.relations if item.relation_type == RelationType.DEPENDS_ON]
    assert len(dependencies) == 1
    ambiguous = [item for item in index.diagnostics if item.code == "DC-RELATION-AMBIGUOUS-TYPE"]
    assert len(ambiguous) == 3


def test_conflict_collection_emits_one_supersession_per_rejected_proposal(tmp_path: Path) -> None:
    for proposal_id in ("PROP-001", "PROP-002", "PROP-003"):
        write_proposal(tmp_path, proposal_id, status="accepted", decision_outcome="accepted")
    write_yaml(
        tmp_path,
        ".p2p/project/conflicts.yml",
        {
            "conflicts": [
                {
                    "id": "CONFLICT-001",
                    "proposals": ["PROP-001", "PROP-002", "PROP-003"],
                    "winner": "PROP-001",
                    "rejected": ["PROP-002", "PROP-003"],
                    "reason": "One approach remains authoritative.",
                }
            ]
        },
    )

    index = _build(tmp_path)

    supersessions = [item for item in index.relations if item.relation_type == RelationType.SUPERSEDES]
    assert {(item.source_id, item.target_id) for item in supersessions} == {
        ("PROP-001", "PROP-002"),
        ("PROP-001", "PROP-003"),
    }
    assert not any("['PROP-002'" in item.target_id for item in index.relations)


def test_vertical_coverage_and_work_lineage_are_explicit(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001")
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/vertical-coverage.yml",
        {"vertical_coverage": {"sections": [{"id": "architecture"}, "operations"]}},
    )
    write_markdown(
        tmp_path,
        ".p2p/changes/CHANGE-001-example/change.md",
        title="CHANGE-001",
        frontmatter={"change_id": "CHANGE-001", "title": "Example", "status": "active", "source": {}},
    )
    write_yaml(
        tmp_path,
        ".p2p/work/WORK-001/manifest.yml",
        {"work_id": "WORK-001", "status": "completed", "source": {"change": "CHANGE-001", "proposals": ["PROP-001"]}},
    )
    index = _build(tmp_path)
    assert len([item for item in index.relations if item.relation_type == RelationType.MAPS_TO_VERTICAL_SECTION]) == 2
    work_relation = next(item for item in index.relations if item.relation_type == RelationType.IMPLEMENTS)
    assert (work_relation.source_id, work_relation.target_id) == ("WORK-001", "CHANGE-001")
    work_state = next(item for item in index.records if item.owner_id == "WORK-001")
    assert work_state.kind == RecordKind.EXECUTION_STATE
    assert work_state.text == "completed"


def test_vertical_coverage_preserves_tracked_owner_confirmation(tmp_path: Path) -> None:
    write_proposal(tmp_path, "PROP-001", status="accepted", decision_outcome="accepted")
    proposal_path = ".p2p/proposals/prop-001-example"
    write_yaml(
        tmp_path,
        f"{proposal_path}/vertical-coverage.yml",
        {
            "vertical_coverage": {
                "proposal_id": "PROP-001",
                "vertical_id": "software_project",
                "sections": [{"id": "architecture"}],
            }
        },
    )
    write_yaml(
        tmp_path,
        f"{proposal_path}/artifact-state.yml",
        {
            "proposal_artifacts": {
                "artifacts": [
                    {
                        "filename": "vertical-coverage.yml",
                        "confirmation": "owner_confirmed",
                    }
                ]
            }
        },
    )

    index = _build(tmp_path)
    relation = next(
        item
        for item in index.relations
        if item.relation_type == RelationType.MAPS_TO_VERTICAL_SECTION
    )
    evidence = next(item for item in index.evidence if item.evidence_id in relation.evidence_ids)

    assert relation.authority == Authority.OWNER_CONFIRMED_EVIDENCE
    assert relation.activation == Activation.ACTIVE
    assert evidence.canonicality == Canonicality.CANONICAL
    assert evidence.authority == Authority.OWNER_CONFIRMED_EVIDENCE


def test_traversal_terminates_for_cycles_and_fan_out(tmp_path: Path) -> None:
    for number in range(1, 8):
        write_proposal(tmp_path, f"PROP-{number:03d}")
    for number in range(1, 8):
        target = number + 1 if number < 7 else 1
        write_yaml(
            tmp_path,
            f".p2p/proposals/prop-{number:03d}-example/related-proposals.yml",
            {"related_proposals": [{"proposal": f"PROP-{target:03d}", "relationship": "depends_on"}]},
        )
    relations = _build(tmp_path).relations
    steps = traverse_relations("PROP-001", relations, max_depth=20, fan_out=2)
    assert len(steps) <= 6
    assert len({item.node_id for item in steps}) == len(steps)
    assert all(item.depth <= 6 for item in steps)


def test_relation_ids_and_evidence_are_deterministic(tmp_path: Path) -> None:
    _accepted_pair(tmp_path)
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/related-proposals.yml",
        {"related_proposals": [{"proposal": "PROP-002", "relationship": "related"}]},
    )
    first = _build(tmp_path)
    second = _build(tmp_path)
    assert first.relations == second.relations
    assert first.evidence == second.evidence

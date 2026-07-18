from __future__ import annotations

from pathlib import Path

from p2p_engine.core.decision_context import (
    Activation,
    ContextBudget,
    RetrievalRequest,
    to_json_ready,
)
from p2p_engine.services.decision_context import ProjectDecisionContextService
from p2p_engine.services.decision_context_retrieval import (
    DecisionContextRetrievalService,
    budget_policy,
    lexical_policy_version,
    normalize_lexical,
    retrieval_policy,
    serialized_packet_size,
)
from tests.test_decision_context_sources import ReverseAccessor
from tests.decision_context_fixtures import write_proposal, write_yaml


def _index(root: Path):
    return ProjectDecisionContextService(root=root).build_index()


def _retrieve(root: Path, *, target: str = "", idea: str = "", budget: ContextBudget = ContextBudget.SMALL):
    return DecisionContextRetrievalService().retrieve(
        _index(root), RetrievalRequest(budget=budget, target_id=target, idea_text=idea)
    )


def _related(root: Path, source: str, target: str, relationship: str = "related") -> None:
    write_yaml(
        root,
        f".p2p/proposals/{source.lower()}-example/related-proposals.yml",
        {"related_proposals": [{"proposal": target, "relationship": relationship}]},
    )


def _distinct_proposal(
    root: Path,
    proposal_id: str,
    word: str,
    *,
    status: str = "draft",
    outcome: str | None = None,
    date: str = "2026-07-15",
) -> None:
    write_proposal(
        root,
        proposal_id,
        title=f"{word} design",
        status=status,
        problem=f"{word} failure",
        goals=(f"Preserve {word}",),
        non_goals=(f"Replace {word}",),
        proposal=f"Implement {word}",
        acceptance=(f"Verify {word}",),
        decision_outcome=outcome,
        decision_reason=f"Approve {word}",
        decision_date=date,
    )


def test_policy_constants_are_versioned_and_match_v2_limits() -> None:
    policy = retrieval_policy()
    assert policy.version == "decision-context-retrieval-v2"
    assert policy.candidate_limit == 200
    assert policy.minimum_score == 15
    assert policy.historical_threshold == 35
    assert dict(policy.signal_weights) == {
        "blocker_or_conflict": 60,
        "explicit_relation": 50,
        "applicable_decision": 40,
        "shared_domain": 25,
        "shared_vertical": 20,
        "lexical_overlap": 20,
        "heuristic_vertical": 8,
        "draft_penalty": -5,
        "historical_penalty": -15,
    }
    assert budget_policy(ContextBudget.SMALL).max_serialized_bytes == 12_000
    assert budget_policy(ContextBudget.MEDIUM).transitive_depth == 1
    assert lexical_policy_version() == "decision-context-lexical-v1"


def test_lexical_normalizer_is_fixed_unicode_and_domain_aware() -> None:
    tokens = normalize_lexical(
        "**QUALITÀ** e The `PROP-100` usa p2p context target in src/p2p_engine/core.py"
    )
    assert "qualità" in tokens
    assert "domain:id:prop-100" in tokens
    assert "domain:path:src/p2p_engine/core.py" in tokens
    assert any(token.startswith("domain:command:p2p context") for token in tokens)
    assert "the" not in tokens
    assert "e" not in tokens


def test_explicit_relation_and_applicable_decision_have_reproducible_score(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "orchestration")
    _distinct_proposal(
        tmp_path,
        "PROP-002",
        "orchestration",
        status="accepted",
        outcome="accepted",
    )
    _related(tmp_path, "PROP-001", "PROP-002", "depends_on")

    packet = _retrieve(tmp_path, target="PROP-001", budget=ContextBudget.MEDIUM)

    assert [hit.owner_id for hit in packet.hits] == ["PROP-002"]
    hit = packet.hits[0]
    assert hit.score == min(100, sum(reason.contribution for reason in hit.reasons))
    assert {reason.signal for reason in hit.reasons} == {
        "explicit_relation",
        "applicable_decision",
        "lexical_overlap",
    }
    assert hit.decisions
    assert hit.claims
    assert hit.evidence_ids
    assert hit.owner_id != "PROP-001"


def test_blocker_conflict_is_exclusive_with_generic_relation_score(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "alpha")
    _distinct_proposal(tmp_path, "PROP-002", "beta")
    write_yaml(
        tmp_path,
        ".p2p/project/conflicts.yml",
        {"conflicts": [{"proposals": ["PROP-001", "PROP-002"]}]},
    )

    hit = _retrieve(tmp_path, target="PROP-001").hits[0]

    signals = [reason.signal for reason in hit.reasons]
    assert "blocker_or_conflict" in signals
    assert "explicit_relation" not in signals
    assert hit.score == min(100, sum(reason.contribution for reason in hit.reasons))


def test_duplicate_edge_evidence_scores_once(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "alpha")
    _distinct_proposal(tmp_path, "PROP-002", "beta")
    change_path = ".p2p/changes/CHANGE-001-example"
    from tests.decision_context_fixtures import write_markdown

    write_markdown(
        tmp_path,
        f"{change_path}/change.md",
        title="CHANGE-001",
        frontmatter={
            "change_id": "CHANGE-001",
            "title": "Example",
            "status": "active",
            "source": {"accepted_proposals": ["PROP-001"]},
        },
    )
    write_yaml(tmp_path, f"{change_path}/included-proposals.yml", {"included_proposals": ["PROP-001"]})

    hit = next(item for item in _retrieve(tmp_path, target="PROP-001").hits if item.owner_id == "CHANGE-001")

    assert len([reason for reason in hit.reasons if reason.signal == "explicit_relation"]) == 1
    assert len(hit.selected_relation_ids) == 1


def test_shared_declared_domain_makes_accepted_decision_applicable(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "alpha")
    _distinct_proposal(tmp_path, "PROP-002", "beta", status="accepted", outcome="accepted")
    for proposal_id in ("PROP-001", "PROP-002"):
        write_yaml(
            tmp_path,
            f".p2p/proposals/{proposal_id.lower()}-example/impact-map.yml",
            {"impact": {"capabilities": ["decision-memory"]}},
        )

    hit = _retrieve(tmp_path, target="PROP-001", budget=ContextBudget.MEDIUM).hits[0]

    assert hit.owner_id == "PROP-002"
    assert {"shared_domain", "applicable_decision"}.issubset(
        {reason.signal for reason in hit.reasons}
    )
    assert hit.score >= 65
    assert hit.score == min(100, sum(reason.contribution for reason in hit.reasons))


def test_vertical_heuristic_remains_a_reason_not_a_topology_edge(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "target")
    _distinct_proposal(tmp_path, "PROP-002", "architecture")
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/vertical-coverage.yml",
        {
            "vertical_coverage": {
                "proposal_id": "PROP-001",
                "vertical_id": "software_project",
                "sections": [{"id": "architecture"}],
            }
        },
    )

    index = _index(tmp_path)
    packet = DecisionContextRetrievalService().retrieve(
        index,
        RetrievalRequest(ContextBudget.MEDIUM, target_id="PROP-001"),
    )

    candidate = next(hit for hit in packet.hits if hit.owner_id == "PROP-002")
    assert "heuristic_vertical" in {reason.signal for reason in candidate.reasons}
    assert not any(
        relation.source_id == "PROP-002"
        and relation.relation_type.value == "maps_to_vertical_section"
        for relation in index.relations
    )


def test_ubiquitous_and_stop_word_queries_return_empty_without_first_n_fallback(tmp_path: Path) -> None:
    for number in range(1, 11):
        _distinct_proposal(tmp_path, f"PROP-{number:03d}", "common vocabulary")

    common = _retrieve(tmp_path, idea="common vocabulary")
    stop_words = _retrieve(tmp_path, idea="the e di and")
    unrelated = _retrieve(tmp_path, idea="unfindable-zeta-token")

    assert common.hits == ()
    assert stop_words.hits == ()
    assert unrelated.hits == ()
    assert all(packet.diagnostics[0].code == "DC-RETRIEVAL-EMPTY" for packet in (common, stop_words, unrelated))
    assert to_json_ready(common)["empty_reason"]


def test_rare_idea_text_returns_content_not_only_ids(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "quasar-indexing")
    _distinct_proposal(tmp_path, "PROP-002", "unrelated")

    packet = _retrieve(tmp_path, idea="quasar-indexing")

    assert [hit.owner_id for hit in packet.hits] == ["PROP-001"]
    assert packet.hits[0].claims
    assert packet.evidence


def test_precedent_requires_explicit_or_qualified_applicability(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "deployment")
    write_yaml(
        tmp_path,
        ".p2p/governance/decision-precedents.yml",
        {
            "precedents": [
                {
                    "id": "DP001",
                    "title": "Release boundary",
                    "related_proposals": ["PROP-001"],
                    "tags": ["deployment"],
                },
                {"id": "DP002", "title": "Generic policy", "tags": ["unrelated"]},
            ]
        },
    )

    target_packet = _retrieve(tmp_path, target="PROP-001")
    idea_packet = _retrieve(tmp_path, idea="deployment")

    assert "precedent:DP001" in {hit.owner_id for hit in target_packet.hits}
    assert "precedent:DP002" not in {hit.owner_id for hit in target_packet.hits}
    assert "precedent:DP001" in {hit.owner_id for hit in idea_packet.hits}


def test_historical_lexical_overlap_needs_threshold_or_explicit_relation(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "archive")
    _distinct_proposal(
        tmp_path,
        "PROP-002",
        "archive",
        status="rejected",
        outcome="rejected",
    )

    lexical_only = _retrieve(tmp_path, target="PROP-001")
    assert "PROP-002" not in {hit.owner_id for hit in lexical_only.hits}

    _related(tmp_path, "PROP-001", "PROP-002", "alternative_to")
    explicit = _retrieve(tmp_path, target="PROP-001")
    historical = next(hit for hit in explicit.hits if hit.owner_id == "PROP-002")
    assert historical.activation == Activation.HISTORICAL
    assert historical.score >= retrieval_policy().historical_threshold


def test_small_is_direct_only_and_medium_allows_one_bounded_extra_hop(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "alpha")
    _distinct_proposal(tmp_path, "PROP-002", "beta")
    _distinct_proposal(tmp_path, "PROP-003", "gamma")
    _related(tmp_path, "PROP-001", "PROP-002", "depends_on")
    _related(tmp_path, "PROP-002", "PROP-003", "depends_on")

    small = _retrieve(tmp_path, target="PROP-001", budget=ContextBudget.SMALL)
    medium = _retrieve(tmp_path, target="PROP-001", budget=ContextBudget.MEDIUM)

    assert "PROP-002" in {hit.owner_id for hit in small.hits}
    assert "PROP-003" not in {hit.owner_id for hit in small.hits}
    assert "PROP-003" in {hit.owner_id for hit in medium.hits}
    transitive = next(hit for hit in medium.hits if hit.owner_id == "PROP-003")
    assert len(transitive.selected_relation_ids) == 2


def test_tie_breaking_uses_dates_only_when_both_exist(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "target")
    _distinct_proposal(tmp_path, "PROP-002", "older", status="accepted", outcome="accepted", date="2026-01-01")
    _distinct_proposal(tmp_path, "PROP-003", "newer", status="accepted", outcome="accepted", date="2026-06-01")
    _related(tmp_path, "PROP-001", "PROP-002", "related")
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/related-proposals.yml",
        {
            "related_proposals": [
                {"proposal": "PROP-002", "relationship": "related"},
                {"proposal": "PROP-003", "relationship": "related"},
            ]
        },
    )

    packet = _retrieve(tmp_path, target="PROP-001")
    assert [hit.owner_id for hit in packet.hits[:2]] == ["PROP-003", "PROP-002"]

    decision_path = tmp_path / ".p2p/proposals/prop-002-example/decision.md"
    decision_path.write_text(
        decision_path.read_text(encoding="utf-8").replace("2026-01-01", ""),
        encoding="utf-8",
    )
    neutral = _retrieve(tmp_path, target="PROP-001")
    assert [hit.owner_id for hit in neutral.hits[:2]] == ["PROP-002", "PROP-003"]


def test_budget_limits_bytes_and_reports_deterministic_truncation(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "target")
    related = []
    for number in range(2, 17):
        proposal_id = f"PROP-{number:03d}"
        _distinct_proposal(
            tmp_path,
            proposal_id,
            f"candidate-{number}-" + ("x" * 2_000),
            status="accepted",
            outcome="accepted",
        )
        related.append({"proposal": proposal_id, "relationship": "related"})
    write_yaml(
        tmp_path,
        ".p2p/proposals/prop-001-example/related-proposals.yml",
        {"related_proposals": related},
    )

    small = _retrieve(tmp_path, target="PROP-001", budget=ContextBudget.SMALL)
    medium = _retrieve(tmp_path, target="PROP-001", budget=ContextBudget.MEDIUM)

    for packet, budget in ((small, ContextBudget.SMALL), (medium, ContextBudget.MEDIUM)):
        policy = budget_policy(budget)
        assert len(packet.hits) <= policy.max_hits
        assert sum(len(hit.selected_record_ids) for hit in packet.hits) <= policy.max_records
        assert sum(len(hit.selected_relation_ids) for hit in packet.hits) <= policy.max_relations
        assert all(len(hit.reasons) <= policy.max_reasons_per_hit for hit in packet.hits)
        assert serialized_packet_size(packet) <= policy.max_serialized_bytes
        assert packet.truncation.truncated is True
        assert packet.diagnostics[0].code == "DC-RETRIEVAL-TRUNCATED"
    assert {hit.owner_id for hit in small.hits}.issubset({hit.owner_id for hit in medium.hits})


def test_query_is_source_free_and_repeated_results_are_identical(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "alpha")
    _distinct_proposal(tmp_path, "PROP-002", "alpha", status="accepted", outcome="accepted")
    index = _index(tmp_path)
    before = dict(index.access_stats.reads)
    service = DecisionContextRetrievalService()
    request = RetrievalRequest(ContextBudget.SMALL, target_id="PROP-001")

    first = service.retrieve(index, request)
    second = service.retrieve(index, request)

    assert first == second
    assert dict(index.access_stats.reads) == before
    assert all(count == 1 for count in before.values())


def test_reversed_source_enumeration_preserves_index_and_retrieval(tmp_path: Path) -> None:
    _distinct_proposal(tmp_path, "PROP-001", "alpha")
    _distinct_proposal(tmp_path, "PROP-002", "alpha", status="accepted", outcome="accepted")
    _related(tmp_path, "PROP-001", "PROP-002", "depends_on")
    normal = ProjectDecisionContextService(root=tmp_path).build_index()
    reversed_index = ProjectDecisionContextService(
        root=tmp_path,
        source_accessor=ReverseAccessor(),
    ).build_index()
    request = RetrievalRequest(ContextBudget.MEDIUM, target_id="PROP-001")
    service = DecisionContextRetrievalService()

    assert normal.source_fingerprint_sha256 == reversed_index.source_fingerprint_sha256
    assert normal.semantic_fingerprint_sha256 == reversed_index.semantic_fingerprint_sha256
    assert normal.records == reversed_index.records
    assert normal.relations == reversed_index.relations
    assert service.retrieve(normal, request) == service.retrieve(reversed_index, request)
    for hit in service.retrieve(normal, request).hits:
        assert hit.score == min(100, sum(reason.contribution for reason in hit.reasons))

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from p2p_engine.core.decision_context import ContextBudget, RetrievalRequest
from p2p_engine.services.decision_context import ProjectDecisionContextService
from p2p_engine.services.decision_context_retrieval import DecisionContextRetrievalService
from tests.decision_context_fixtures import write_markdown, write_proposal, write_yaml


def _representative_workspace(root: Path) -> None:
    outcomes = ("accepted", "accepted_with_changes", "rejected", "deferred", "draft")
    for number in range(1, 101):
        proposal_id = f"PROP-{number:03d}"
        outcome = outcomes[(number - 1) % len(outcomes)]
        write_proposal(
            root,
            proposal_id,
            title=f"Decision context capability {number}",
            status=outcome,
            problem=f"Capability {number} loses retrieval evidence.",
            goals=(f"Index capability-{number}.", "Preserve deterministic evidence."),
            proposal=f"Add bounded decision retrieval for capability-{number}.",
            acceptance=(f"Retrieve capability-{number} deterministically.",),
            decision_outcome=None if outcome == "draft" else outcome,
            decision_reason=f"Lifecycle evidence for capability-{number}.",
        )
        if number % 10 == 0:
            write_yaml(
                root,
                f".p2p/proposals/{proposal_id.lower()}-example/vertical-coverage.yml",
                {
                    "vertical_coverage": {
                        "proposal_id": proposal_id,
                        "vertical_id": "software_project",
                        "sections": [{"id": f"section-{number // 10}"}],
                    }
                },
            )
        if number <= 20:
            write_yaml(
                root,
                f".p2p/proposals/{proposal_id.lower()}-example/contributions.yml",
                {
                    "contributions": [
                        {"id": f"CHOICE-{proposal_id}-001", "status": "open"}
                    ]
                },
            )

    write_yaml(
        root,
        ".p2p/proposals/prop-100-example/related-proposals.yml",
        {
            "related_proposals": [
                {"proposal": "PROP-099", "relationship": "depends_on"},
                {"proposal": "PROP-096", "relationship": "references"},
            ]
        },
    )
    malformed = root / ".p2p/proposals/prop-050-example/impact-map.yml"
    malformed.write_text("impact: [\n", encoding="utf-8")

    for number in range(1, 26):
        change_id = f"CHANGE-{number:03d}"
        proposal_ids = [f"PROP-{number:03d}", f"PROP-{number + 25:03d}"]
        path = f".p2p/changes/{change_id.lower()}-example"
        write_markdown(
            root,
            f"{path}/change.md",
            title=change_id,
            frontmatter={
                "change_id": change_id,
                "title": f"Scale Change {number}",
                "status": "active" if number % 2 else "completed",
                "source": {"accepted_proposals": proposal_ids},
            },
        )
        write_yaml(root, f"{path}/included-proposals.yml", {"included_proposals": proposal_ids})
        write_yaml(root, f"{path}/referenced-proposals.yml", {"referenced_proposals": []})

    for number in range(1, 21):
        choice_id = f"CHOICE-{number:03d}"
        path = f".p2p/choices/{choice_id.lower()}-example"
        write_markdown(
            root,
            f"{path}/choice.md",
            title=choice_id,
            frontmatter={
                "choice_id": choice_id,
                "title": f"Scale Choice {number}",
                "status": "decided" if number % 2 else "open",
                "related": {"proposals": [f"PROP-{number:03d}"]},
            },
        )
        if number % 2:
            write_markdown(
                root,
                f"{path}/decision.md",
                title=f"Decision - {choice_id}",
                sections=(("Status", "decided"), ("Selected Option", "A"), ("Reason", "Scale evidence.")),
            )

    write_yaml(
        root,
        ".p2p/project/conflicts.yml",
        {
            "conflicts": [
                {"proposals": ["PROP-099", "PROP-100"], "winner": "PROP-100", "rejected": "PROP-099"}
            ]
        },
    )


def test_representative_build_and_query_stay_structurally_bounded(tmp_path: Path) -> None:
    _representative_workspace(tmp_path)
    started = perf_counter()
    index = ProjectDecisionContextService(root=tmp_path).build_index()
    built = perf_counter()
    before_query_reads = dict(index.access_stats.reads)
    packet = DecisionContextRetrievalService().retrieve(
        index,
        RetrievalRequest(ContextBudget.MEDIUM, target_id="PROP-100"),
    )
    finished = perf_counter()

    assert finished - started < 5.0, {
        "build_seconds": built - started,
        "query_seconds": finished - built,
        "sources": len(index.sources),
        "records": len(index.records),
        "relations": len(index.relations),
    }
    assert index.access_stats.discovery_passes == 1
    assert all(count == 1 for count in index.access_stats.reads.values())
    assert all(count == 1 for count in index.access_stats.hashes.values())
    assert all(count == 1 for count in index.access_stats.parses.values())
    assert dict(index.access_stats.reads) == before_query_reads
    assert packet.hits
    assert "PROP-100" not in {hit.owner_id for hit in packet.hits}
    assert len(index.sources) >= 1_000

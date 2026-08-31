from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.services.workspace_reads import WorkspaceReadContext
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.read_performance import measure_read, tree_digest
from tests.workspace_scale_fixtures import build_scale_workspace


@pytest.mark.unit
def test_measure_read_returns_result_and_non_negative_elapsed() -> None:
    measurement = measure_read(lambda: "value", track_memory=True)

    assert measurement.result == "value"
    assert measurement.elapsed_seconds >= 0
    assert measurement.peak_memory_bytes >= 0


@pytest.mark.adapter
def test_tree_digest_is_deterministic_and_content_sensitive(tmp_path: Path) -> None:
    path = tmp_path / "nested/value.txt"
    path.parent.mkdir()
    path.write_text("one", encoding="utf-8")
    first = tree_digest(tmp_path)

    assert tree_digest(tmp_path) == first
    path.write_text("two", encoding="utf-8")
    assert tree_digest(tmp_path) != first


@pytest.mark.adapter
@pytest.mark.parametrize("schema_version", [4])
def test_scale_workspace_is_deterministic_on_current_schema(
    tmp_path: Path,
    schema_version: int,
) -> None:
    first = build_scale_workspace(
        tmp_path / "first",
        proposal_count=10,
        schema_version=schema_version,
        rich_proposals=5,
    )
    second = build_scale_workspace(
        tmp_path / "second",
        proposal_count=10,
        schema_version=schema_version,
        rich_proposals=5,
        reverse_enumeration=True,
    )

    assert first.proposal_ids == second.proposal_ids
    assert first.schema_version == second.schema_version == schema_version
    assert len(list((first.root / ".p2p/proposals").iterdir())) == 10
    assert len(list((second.root / ".p2p/proposals").iterdir())) == 10
    identity_paths = frozenset(
        {
            "project.yml",
            "project/identity.yml",
            "local/replica.yml",
            "local/storage.yml",
        }
    )
    assert tree_digest(first.root / ".p2p", exclude=identity_paths) == tree_digest(
        second.root / ".p2p", exclude=identity_paths
    )
    first_manifest = yaml.safe_load((first.root / ".p2p/project.yml").read_text(encoding="utf-8"))
    second_manifest = yaml.safe_load((second.root / ".p2p/project.yml").read_text(encoding="utf-8"))
    first_manifest["project"].pop("uuid")
    second_manifest["project"].pop("uuid")
    assert first_manifest == second_manifest
    assert (
        first.root.joinpath(".p2p/project/identity.yml").read_bytes()
        != (second.root / ".p2p/project/identity.yml").read_bytes()
    )


@pytest.mark.slow
@pytest.mark.parametrize("proposal_count", [100, 1_000, 10_000])
def test_lifecycle_and_vertical_coverage_scale_linearly(
    tmp_path: Path,
    proposal_count: int,
) -> None:
    fixture = build_scale_workspace(
        tmp_path / f"scale-{proposal_count}",
        proposal_count=proposal_count,
        schema_version=4,
        rich_proposals=min(100, proposal_count),
    )
    workspace = P2PWorkspace(fixture.root)
    context = WorkspaceReadContext(fixture.root)

    lifecycles = workspace._proposal_lifecycle_authority_service().capture_all(read_context=context)
    vertical = workspace._project_vertical_service()
    coverage = vertical.proposal_vertical_coverage_statuses(
        tuple(sorted(lifecycles)),
        state=vertical.vertical_read_state(),
    )
    counters = context.counters

    assert len(lifecycles) == proposal_count
    assert len(coverage) == proposal_count
    assert counters.schema_preflights == 1
    assert sum(counters.ledger_parses.values()) == proposal_count
    assert sum(counters.discovery_passes.values()) == 1

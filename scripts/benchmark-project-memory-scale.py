#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
from time import perf_counter
import tracemalloc
from typing import Callable

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT / "src"))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(1, str(SOURCE_ROOT))

import p2p_engine
from p2p_engine.services.workspace_reads import WorkspaceReadContext
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.workspace_scale_fixtures import build_scale_workspace


def _measure(operation: Callable[[], object], *, track_memory: bool) -> dict[str, object]:
    if track_memory:
        tracemalloc.start()
    started = perf_counter()
    try:
        result = operation()
        peak = tracemalloc.get_traced_memory()[1] if track_memory else None
    finally:
        if track_memory:
            tracemalloc.stop()
    return {
        "elapsed_seconds": round(perf_counter() - started, 6),
        "peak_memory_bytes": peak,
        "result": result,
    }


def _without_result(measurement: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in measurement.items() if key != "result"}


def _run_scale(
    parent: Path,
    proposal_count: int,
    *,
    rich_proposals: int,
    track_memory: bool,
) -> dict[str, object]:
    root = parent / f"proposals-{proposal_count}"
    fixture = _measure(
        lambda: build_scale_workspace(
            root,
            proposal_count=proposal_count,
            schema_version=4,
            rich_proposals=min(rich_proposals, proposal_count),
        ),
        track_memory=track_memory,
    )
    workspace = P2PWorkspace(root)
    context = WorkspaceReadContext(root)
    lifecycle = _measure(
        lambda: workspace._proposal_lifecycle_authority_service().capture_all(
            read_context=context
        ),
        track_memory=track_memory,
    )
    lifecycles = lifecycle["result"]
    assert isinstance(lifecycles, dict)
    proposal_ids = tuple(sorted(lifecycles))
    vertical = workspace._project_vertical_service()
    vertical_state = vertical.vertical_read_state()
    coverage = _measure(
        lambda: vertical.proposal_vertical_coverage_statuses(
            proposal_ids,
            state=vertical_state,
        ),
        track_memory=track_memory,
    )
    full = _measure(
        workspace._vertical_project_memory_service().build_full,
        track_memory=track_memory,
    )
    candidate = full["result"]
    candidate_size = sum(len(content) for content in candidate.candidates.values())
    refresh = _measure(
        workspace.refresh_vertical_project_memory,
        track_memory=track_memory,
    )
    load = _measure(
        lambda: workspace.vertical_project_memory(allow_fallback=False),
        track_memory=track_memory,
    )
    proposal_id = proposal_ids[0]
    context_small = _measure(
        lambda: workspace.context_packet("small"),
        track_memory=track_memory,
    )
    context_targeted = _measure(
        lambda: workspace.context_packet("small", proposal_id),
        track_memory=track_memory,
    )
    proposal_path = workspace._proposal_document_service().find_dir(proposal_id) / "proposal.md"
    proposal_path.write_text(
        proposal_path.read_text(encoding="utf-8") + "\nScale mutation.\n",
        encoding="utf-8",
    )
    incremental = _measure(
        lambda: workspace._vertical_project_memory_service().build_incremental(
            [proposal_path.relative_to(root).as_posix()],
            typed_proposal_id=proposal_id,
        ),
        track_memory=track_memory,
    )
    incremental_candidate, impact = incremental["result"]
    full_after = workspace._vertical_project_memory_service().build_full()
    if incremental_candidate.candidates != full_after.candidates:
        raise RuntimeError("incremental candidate differs from full candidate")
    counters = context.counters.to_dict()
    return {
        "proposal_count": proposal_count,
        "rich_proposals": min(rich_proposals, proposal_count),
        "fixture_build": _without_result(fixture),
        "lifecycle_batch": {
            **_without_result(lifecycle),
            "records": len(lifecycles),
            "ledger_parses": sum(counters["ledger_parses"].values()),
            "schema_preflights": counters["schema_preflights"],
            "discovery_passes": sum(counters["discovery_passes"].values()),
        },
        "coverage_batch": {
            **_without_result(coverage),
            "records": len(coverage["result"]),
        },
        "full_build": {
            **_without_result(full),
            "output_count": len(candidate.candidates),
            "artifact_bytes": candidate_size,
            "source_count": len(candidate.source_preconditions),
        },
        "materialize": _without_result(refresh),
        "materialized_load": _without_result(load),
        "context_small": _without_result(context_small),
        "context_targeted": _without_result(context_targeted),
        "one_proposal_incremental": {
            **_without_result(incremental),
            "affected_sections": len(impact.section_ids),
            "full_rebuild": impact.full_rebuild,
            "byte_equivalent_to_full": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure file-backed vertical project memory at deterministic scales."
    )
    parser.add_argument("--scale", type=int, action="append", dest="scales")
    parser.add_argument("--rich-proposals", type=int, default=100)
    parser.add_argument("--track-memory", action="store_true")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    scales = tuple(args.scales or (100, 1000, 10_000))
    if any(value < 1 for value in scales):
        parser.error("--scale must be positive")
    expected = (SOURCE_ROOT / "src/p2p_engine/__init__.py").resolve()
    actual = Path(p2p_engine.__file__).resolve()
    if actual != expected:
        parser.error(f"benchmark imported {actual}, expected {expected}")
    parent = Path(tempfile.mkdtemp(prefix="p2p-memory-scale-", dir="/tmp"))
    try:
        results = []
        for scale in scales:
            print(f"measuring deterministic {scale}-proposal fixture", file=sys.stderr)
            result = _run_scale(
                parent,
                scale,
                rich_proposals=args.rich_proposals,
                track_memory=args.track_memory,
            )
            results.append(result)
            print(json.dumps(result, sort_keys=True), file=sys.stderr)
        print(
            json.dumps(
                {
                    "module_path": actual.as_posix(),
                    "package_version": getattr(p2p_engine, "__version__", None),
                    "python_executable": Path(sys.executable).resolve().as_posix(),
                    "python_version": sys.version.split()[0],
                    "temporary_root": parent.as_posix() if args.keep else None,
                    "scales": results,
                    "median_full_build_seconds": statistics.median(
                        float(item["full_build"]["elapsed_seconds"])
                        for item in results
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
    finally:
        if not args.keep:
            shutil.rmtree(parent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
from time import perf_counter
from typing import Callable

import yaml

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT / "src"))

import p2p_engine
from p2p_engine.mcp.handlers.project import handle_project_tool
from p2p_engine.storage.filesystem import P2PWorkspace


TOOLS: dict[str, tuple[str, dict[str, object]]] = {
    "context_small": ("p2p_context", {"budget": "small"}),
    "context_targeted": (
        "p2p_context",
        {"budget": "small", "target": "PROP-100"},
    ),
    "next_top_3": ("p2p_next", {"top": 3}),
    "project_progress": ("p2p_project_progress", {}),
    "registry_status": ("p2p_registry_status", {}),
    "memory_status": ("p2p_project_memory_status", {}),
    "memory_show": ("p2p_project_memory_show", {"limit": 20}),
}


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _measure(operation: Callable[[], object], runs: int) -> dict[str, object]:
    elapsed: list[float] = []
    for _ in range(runs):
        started = perf_counter()
        operation()
        elapsed.append(perf_counter() - started)
    return {
        "runs": runs,
        "median_seconds": round(statistics.median(elapsed), 6),
        "p95_seconds": round(_percentile(elapsed, 0.95), 6),
        "samples_seconds": [round(value, 6) for value in elapsed],
    }


def _mutate_one_proposal(root: Path) -> str:
    proposals = root / ".p2p" / "proposals"
    proposal = next(
        path / "proposal.md"
        for path in sorted(proposals.iterdir())
        if path.is_dir() and (path / "proposal.md").is_file()
    )
    proposal.write_text(
        proposal.read_text(encoding="utf-8") + "\nMCP benchmark mutation.\n",
        encoding="utf-8",
    )
    return proposal.relative_to(root).as_posix()


def _measure_concurrent_change_retry(
    workspace: P2PWorkspace,
    root: Path,
) -> dict[str, object]:
    service = workspace._context_packet_service()
    original = service.context_packet
    project_path = root / ".p2p/project.yml"
    attempts = 0

    def mutate_between_build_and_finalize(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        result = original(*args, **kwargs)
        if attempts == 1:
            payload = yaml.safe_load(project_path.read_text(encoding="utf-8"))
            project = payload.setdefault("project", {})
            project["name"] = f"{project.get('name', 'Project')} [benchmark retry]"
            project_path.write_text(
                yaml.safe_dump(payload, sort_keys=False),
                encoding="utf-8",
            )
        return result

    service.context_packet = mutate_between_build_and_finalize
    try:
        measurement = _measure(workspace.context_packet, 1)
    finally:
        service.context_packet = original
    return {
        **measurement,
        "attempts": attempts,
        "retry_observed": attempts == 2,
        "mutation_point": "after_payload_before_read_context_finalize",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark persistent MCP reads on a disposable workspace copy."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--only", action="append", choices=tuple(TOOLS))
    args = parser.parse_args()
    if args.runs < 1 or args.workers < 1:
        parser.error("--runs and --workers must be positive")
    actual = Path(p2p_engine.__file__).resolve()
    expected = (SOURCE_ROOT / "src" / "p2p_engine" / "__init__.py").resolve()
    if actual != expected:
        parser.error(f"benchmark imported {actual}, expected {expected}")
    source_root = args.root.resolve()
    if not (source_root / ".p2p").is_dir():
        parser.error(f"missing workspace: {source_root / '.p2p'}")
    scratch = Path(tempfile.mkdtemp(prefix="p2p-mcp-benchmark-", dir="/tmp"))
    try:
        shutil.copytree(source_root / ".p2p", scratch / ".p2p")
        workspace = P2PWorkspace(scratch)
        selected = args.only or list(TOOLS)
        results: dict[str, object] = {}
        for key in selected:
            name, arguments = TOOLS[key]
            operation = lambda n=name, a=arguments: handle_project_tool(
                workspace,
                n,
                dict(a),
            )
            first = _measure(operation, 1)
            steady = _measure(operation, args.runs)
            results[key] = {"first_request": first, "steady_state": steady}

        concurrent_change_retry = _measure_concurrent_change_retry(
            workspace,
            scratch,
        )
        changed_path = _mutate_one_proposal(scratch)
        post_mutation = _measure(
            lambda: handle_project_tool(
                workspace,
                "p2p_context",
                {"budget": "small"},
            ),
            1,
        )

        def concurrent_request() -> object:
            return handle_project_tool(
                workspace,
                "p2p_context",
                {"budget": "small"},
            )

        started = perf_counter()
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            concurrent_results = list(
                executor.map(lambda _index: concurrent_request(), range(args.workers))
            )
        concurrent_elapsed = perf_counter() - started
        print(
            json.dumps(
                {
                    "process_model": "persistent_workspace_instance_via_mcp_handler",
                    "module_path": actual.as_posix(),
                    "package_version": getattr(p2p_engine, "__version__", None),
                    "python_executable": Path(sys.executable).resolve().as_posix(),
                    "python_version": sys.version.split()[0],
                    "source_workspace": source_root.as_posix(),
                    "scratch_removed": True,
                    "results": results,
                    "post_mutation": {
                        **post_mutation,
                        "changed_path": changed_path,
                    },
                    "concurrent_read_write_retry": concurrent_change_retry,
                    "concurrent_reads": {
                        "workers": args.workers,
                        "elapsed_seconds": round(concurrent_elapsed, 6),
                        "successful_results": sum(
                            result is not None for result in concurrent_results
                        ),
                    },
                    "concurrent_read_write_retry_evidence": (
                        "measured above and covered by tests/test_fast_read_paths.py::"
                        "test_public_context_retries_after_captured_source_changes"
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
    finally:
        shutil.rmtree(scratch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

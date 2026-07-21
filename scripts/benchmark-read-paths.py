#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
from time import perf_counter
from typing import Callable
import tracemalloc

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT / "src"))

import p2p_engine
from p2p_engine.storage.filesystem import P2PWorkspace

COMMANDS: dict[str, tuple[str, ...]] = {
    "check": ("check",),
    "status": ("status",),
    "proposal_list": ("proposal", "list"),
    "decision_status": ("decision", "status", "PROP-100", "--format", "json"),
    "registry_status": ("registry", "status"),
    "registry_show": ("registry", "show", "proposals"),
    "memory_status": ("project", "memory", "status", "--format", "json"),
    "memory_show": ("project", "memory", "show", "--limit", "20", "--format", "json"),
    "project_progress": ("project", "progress", "--format", "json"),
    "context_small": ("context", "--budget", "small", "--format", "json"),
    "context_targeted": (
        "context",
        "--budget",
        "small",
        "--target",
        "PROP-100",
        "--format",
        "json",
    ),
    "next_top_3": ("next", "--top", "3"),
    "validate": ("validate", "--format", "json"),
    "project_freshness": ("project", "freshness", "--format", "json"),
}


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _cli_operation(
    source_root: Path,
    workspace_root: Path,
    arguments: tuple[str, ...],
) -> Callable[[], None]:
    executable = source_root / ".venv/bin/p2p"
    environment = {
        **os.environ,
        "PYTHONPATH": str(source_root / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    def run() -> None:
        result = subprocess.run(
            [str(executable), *arguments, "--root", str(workspace_root)],
            cwd=source_root,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode not in {0, 1}:
            raise RuntimeError(result.stderr.strip() or f"command failed: {arguments}")

    return run


def _in_process_operations(workspace_root: Path) -> dict[str, Callable[[], object]]:
    workspace = P2PWorkspace(workspace_root)
    return {
        "check": workspace.check,
        "status": workspace.status,
        "proposal_list": workspace.proposal_summaries,
        "decision_status": lambda: workspace.proposal_decision_status("PROP-100"),
        "registry_status": workspace.registry_status,
        "registry_show": lambda: workspace.show_registry("proposals"),
        "memory_status": workspace.vertical_project_memory_status,
        "memory_show": lambda: workspace.show_vertical_project_memory(limit=20),
        "project_progress": workspace.project_progress,
        "context_small": lambda: workspace.context_packet("small"),
        "context_targeted": lambda: workspace.context_packet("small", "PROP-100"),
        "next_top_3": lambda: workspace.next_actions(limit=3),
        "validate": workspace.validate,
        "project_freshness": workspace.project_freshness,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark P2P read paths without writes.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Workspace root to measure; it may be a disposable copy.",
    )
    parser.add_argument("--mode", choices=("cli", "in-process"), default="cli")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--only", action="append", choices=tuple(COMMANDS))
    parser.add_argument(
        "--cache-mode",
        choices=("warm-filesystem", "unspecified"),
        default="warm-filesystem",
    )
    parser.add_argument(
        "--track-memory",
        action="store_true",
        help="Track Python allocations in in-process mode; this adds timing overhead.",
    )
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    workspace_root = args.root.resolve()
    expected = (SOURCE_ROOT / "src/p2p_engine/__init__.py").resolve()
    actual = Path(p2p_engine.__file__).resolve()
    if actual != expected:
        parser.error(f"benchmark imported {actual}, expected {expected}")
    selected = args.only or list(COMMANDS)
    operations = (
        {
            name: _cli_operation(SOURCE_ROOT, workspace_root, COMMANDS[name])
            for name in selected
        }
        if args.mode == "cli"
        else {
            name: operation
            for name, operation in _in_process_operations(workspace_root).items()
            if name in selected
        }
    )
    results: dict[str, object] = {}
    for name, operation in operations.items():
        print(f"benchmarking {name} ({args.mode}, {args.runs} runs)", file=sys.stderr, flush=True)
        elapsed: list[float] = []
        peaks: list[int] = []
        for _ in range(args.runs):
            if args.mode == "in-process" and args.track_memory:
                tracemalloc.start()
            started = perf_counter()
            try:
                operation()
                elapsed.append(perf_counter() - started)
                if args.mode == "in-process" and args.track_memory:
                    peaks.append(tracemalloc.get_traced_memory()[1])
            finally:
                if args.mode == "in-process" and args.track_memory:
                    tracemalloc.stop()
        results[name] = {
            "runs": args.runs,
            "median_seconds": round(statistics.median(elapsed), 6),
            "p95_seconds": round(_percentile(elapsed, 0.95), 6),
            "samples_seconds": [round(value, 6) for value in elapsed],
            "peak_memory_bytes": max(peaks) if peaks else None,
        }
        print(json.dumps({name: results[name]}, sort_keys=True), file=sys.stderr, flush=True)
    print(
        json.dumps(
            {
                "mode": args.mode,
                "process_model": (
                    "separate_cli_process_per_sample"
                    if args.mode == "cli"
                    else "persistent_workspace_instance"
                ),
                "cache_mode": args.cache_mode,
                "memory_tracking": args.track_memory,
                "workspace_root": workspace_root.as_posix(),
                "source_root": SOURCE_ROOT.as_posix(),
                "module_path": actual.as_posix(),
                "package_version": getattr(p2p_engine, "__version__", None),
                "python_executable": Path(sys.executable).resolve().as_posix(),
                "python_version": sys.version.split()[0],
                "git_revision": _git_revision(SOURCE_ROOT),
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _git_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


if __name__ == "__main__":
    raise SystemExit(main())

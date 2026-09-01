#!/usr/bin/env python3
"""Run the frozen step-27A A/B/C local-storage comparison.

The evaluator deliberately loads product code from three detached, immutable
Git checkouts.  The harness may evolve on the experiment branch, but variants
A, B, and C remain the commits frozen below.  Product measurements happen in
short-lived worker processes so Python modules from different revisions can
never contaminate one another.

This script records evidence only.  It cannot merge, discard, tag, release, or
select a product backend on behalf of the owner.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any

HARNESS_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_SCRIPT = HARNESS_ROOT / "scripts/benchmark-local-storage.py"
GATE_CONTRACT = "p2p-local-backend-gate/v1"
PLATFORM_CONTRACT = "p2p-local-backend-platform-evidence/v1"
AGGREGATE_CONTRACT = "p2p-local-backend-cross-platform-evidence/v1"

FROZEN_COMMITS: dict[str, str] = {
    "a": "5314459504747f4930aa2f00a26c094d0d058b64",
    "b": "fdfbf1e21fd8b0dd148a6473270bd862f5c25fe1",
    "c": "e83f7b5435bd22e506dc24e5dc6b5f6a5e4a33b2",
}
VARIANT_NAMES: dict[str, str] = {
    "a": "A-filesystem-before-storage-ports",
    "b": "B-filesystem-behind-storage-ports",
    "c": "C-sqlite-behind-storage-ports",
}
FROZEN_CANDIDATE_C_REFERENCE_WHEEL_SHA256 = (
    "eb948e9556fc127921612b12a66a3e4d3c747d48e896eea37dcb247dc472d563"
)
FROZEN_DATASET_DATE = "2026-08-31"
FROZEN_PROFILES = ("small", "medium", "large", "stress")
FROZEN_WORKLOADS = (
    "project_init",
    "cli_status_cold_start",
    "cold_project_open",
    "warm_proposal_list",
    "targeted_decision_read",
    "memory_classification",
    "canonical_snapshot",
    "bundle_export",
    "archive_verify",
    "physical_backup",
    "governed_proposal_create",
    "bundle_restore",
    "batch_import",
    "concurrent_readers_serialized_writer",
    "crash_recovery",
)
COMMON_OPERATION_WORKLOADS = {
    "project_init",
    "cli_status_cold_start",
    "cold_project_open",
    "warm_proposal_list",
    "targeted_decision_read",
    "memory_classification",
    "canonical_snapshot",
    "governed_proposal_create",
}
FROZEN_BATCH_COUNTS: dict[str, dict[str, int]] = {
    "small": {
        "cold_project_open": 50,
        "warm_proposal_list": 5,
        "targeted_decision_read": 200,
        "memory_classification": 25,
        "canonical_snapshot": 2,
        "archive_verify": 10,
    },
    "medium": {
        "cold_project_open": 50,
        "targeted_decision_read": 100,
        "memory_classification": 10,
        "archive_verify": 4,
    },
    "large": {
        "cold_project_open": 50,
        "targeted_decision_read": 75,
        "memory_classification": 4,
        "archive_verify": 2,
    },
    "stress": {
        "cold_project_open": 50,
        "targeted_decision_read": 50,
    },
}
ORDINARY_WARMUPS = 5
ORDINARY_REPETITIONS = 21
STRESS_WARMUPS = 5
STRESS_REPETITIONS = 11
MAX_RELATIVE_MAD = 0.15
MAX_ABSOLUTE_HALF_DRIFT = 0.15
MEANINGFUL_MEDIAN_RATIO = 0.20
MEANINGFUL_P95_RATIO = 0.25
ROBUST_MAD_MULTIPLIER = 4.0
WORKER_SAMPLE_TIMEOUT_SECONDS = 900
REQUIRED_PLATFORM_TARGETS = {
    "linux-x86_64",
    "macos-arm64",
    "macos-x86_64",
    "windows-x86_64",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _dependency_environment() -> dict[str, Any]:
    distributions = sorted(
        {
            str(item.metadata.get("Name") or "").lower(): item.version
            for item in importlib.metadata.distributions()
            if item.metadata.get("Name")
        }.items()
    )
    encoded = _canonical_json(distributions).encode("utf-8")
    lock_path = HARNESS_ROOT / "uv.lock"
    return {
        "distributions": [{"name": name, "version": version} for name, version in distributions],
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "lock_file": "uv.lock",
        "lock_sha256": _sha256_file(lock_path) if lock_path.is_file() else None,
        "resolver": (
            "uv sync --locked environment shared by A/B/C; exact installed versions recorded"
        ),
    }


def _matrix_identity(
    *,
    harness_digests: Mapping[str, str],
    profiles: Iterable[str],
    workloads: Iterable[str],
) -> dict[str, Any]:
    value = {
        "frozen_commits": FROZEN_COMMITS,
        "variant_names": VARIANT_NAMES,
        "candidate_c_reference_wheel_sha256": FROZEN_CANDIDATE_C_REFERENCE_WHEEL_SHA256,
        "fixture_date": FROZEN_DATASET_DATE,
        "environment_lock_sha256": (
            _sha256_file(HARNESS_ROOT / "uv.lock") if (HARNESS_ROOT / "uv.lock").is_file() else None
        ),
        "harness_digests": dict(harness_digests),
        "profiles": list(profiles),
        "workloads": list(workloads),
        "warmups": {"ordinary": ORDINARY_WARMUPS, "stress": STRESS_WARMUPS},
        "repetitions": {
            "ordinary": ORDINARY_REPETITIONS,
            "stress": STRESS_REPETITIONS,
        },
        "thresholds": {
            "maximum_relative_mad": MAX_RELATIVE_MAD,
            "maximum_absolute_half_drift": MAX_ABSOLUTE_HALF_DRIFT,
            "meaningful_median_ratio": MEANINGFUL_MEDIAN_RATIO,
            "meaningful_p95_ratio": MEANINGFUL_P95_RATIO,
            "robust_mad_multiplier": ROBUST_MAD_MULTIPLIER,
        },
        "batch_counts": FROZEN_BATCH_COUNTS,
    }
    return {
        "value": value,
        "sha256": hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest(),
    }


def _platform_target_from_environment(environment: Mapping[str, Any]) -> str:
    system = str(environment.get("system") or "unknown").lower()
    machine = str(environment.get("machine") or "unknown").lower()
    if system == "darwin":
        system = "macos"
    if machine in {"amd64", "x64"}:
        machine = "x86_64"
    if machine in {"aarch64", "arm64"}:
        machine = "arm64"
    return f"{system}-{machine}"


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: int = WORKER_SAMPLE_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{' '.join(command)} exceeded {timeout} seconds") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"{' '.join(command)} failed ({completed.returncode}): {detail}")
    return completed


def _git(repository: Path, *arguments: str) -> str:
    return _run(["git", *arguments], cwd=repository).stdout.strip()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, path)


def _write_checkpoint(arguments: argparse.Namespace, payload: Mapping[str, Any]) -> None:
    output = getattr(arguments, "output", None)
    if output is None:
        return
    _write_json(Path(output).resolve(), dict(payload))


def _load_benchmark_module(product_root: Path):
    os.environ["P2P_BENCHMARK_PRODUCT_ROOT"] = str(product_root.resolve())
    spec = importlib.util.spec_from_file_location(
        f"p2p_local_benchmark_{os.getpid()}", BENCHMARK_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load local-storage benchmark module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _worker_main(arguments: argparse.Namespace) -> int:
    product_root = arguments.product_root.resolve()
    module = _load_benchmark_module(product_root)
    if arguments.worker_action == "serve":
        for raw in sys.stdin:
            request = json.loads(raw)
            if request.get("action") == "close":
                return 0
            try:
                payload = module.run_definitive_sample(
                    Path(request["dataset_root"]).resolve(),
                    Path(request["scratch"]).resolve(),
                    str(request["workload"]),
                    arguments.variant,
                    int(request["sample_number"]),
                    int(request["batch_count"]),
                )
                response: dict[str, Any] = {"ok": True, "payload": payload}
            except Exception as exc:  # noqa: BLE001 - preserve worker diagnostics.
                response = {
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            print(_canonical_json(response), flush=True)
        return 0
    if arguments.worker_action == "prepare":
        from p2p_engine.core.canonical_memory import (
            CANONICAL_MEMORY_CONTRACT,
            DOMAIN_CONTRACT,
            PROJECT_BUNDLE_SCHEMA,
        )

        baseline = module.verify_baseline(
            arguments.expected_revision,
            variant=arguments.variant,
        )
        baseline["git_tree"] = module._git("rev-parse", "HEAD^{tree}")
        baseline["pyproject_sha256"] = _sha256_file(product_root / "pyproject.toml")
        worker_profile = (arguments.profiles or ["small"])[-1]
        dataset = module.build_dataset(
            arguments.dataset_root.resolve(),
            module.DATASET_PROFILES[worker_profile],
            seed=2501,
            variant=arguments.variant,
        )
        payload: object = {
            "baseline": baseline,
            "dataset": dataset,
            "environment": module.environment_record(arguments.temporary_parent.resolve()),
            "contracts": {
                "harness": module.HARNESS_CONTRACT,
                "dataset": module.DATASET_VERSION,
                "workload": module.WORKLOAD_VERSION,
                "domain": DOMAIN_CONTRACT,
                "canonical_memory": CANONICAL_MEMORY_CONTRACT,
                "bundle": PROJECT_BUNDLE_SCHEMA,
            },
        }
    elif arguments.worker_action == "sample":
        payload = module.run_definitive_sample(
            arguments.dataset_root.resolve(),
            arguments.scratch.resolve(),
            arguments.workload,
            arguments.variant,
            arguments.sample_number,
            arguments.batch_count,
        )
    elif arguments.worker_action == "conformance":
        payload = module.run_conformance(
            arguments.dataset_root.resolve(),
            arguments.scratch.resolve(),
            arguments.variant,
        )
    elif arguments.worker_action == "agents":
        payload = module.compare_clean_agent_artifacts(arguments.scratch.resolve())
    else:  # pragma: no cover - argparse constrains this.
        raise RuntimeError(f"unknown worker action {arguments.worker_action}")
    print(_canonical_json(payload))
    return 0


def _worker(
    *,
    product_root: Path,
    action: str,
    variant: str,
    expected_revision: str,
    temporary_parent: Path,
    dataset_root: Path | None = None,
    scratch: Path | None = None,
    profile: str = "small",
    workload: str = "cold_project_open",
    sample_number: int = 1,
    batch_count: int = 1,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker-action",
        action,
        "--product-root",
        str(product_root),
        "--expected-revision",
        expected_revision,
        "--variant",
        variant,
        "--temporary-parent",
        str(temporary_parent),
        "--profile",
        profile,
        "--workload",
        workload,
        "--sample-number",
        str(sample_number),
        "--batch-count",
        str(batch_count),
    ]
    if dataset_root is not None:
        command.extend(("--dataset-root", str(dataset_root)))
    if scratch is not None:
        command.extend(("--scratch", str(scratch)))
    completed = _run(command, cwd=HARNESS_ROOT)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"{variant}/{action} worker returned no JSON")
    try:
        value = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{variant}/{action} worker returned invalid JSON: {completed.stdout!r}"
        ) from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{variant}/{action} worker returned a non-object")
    return value


class _WorkerSession:
    """One long-lived, revision-isolated product interpreter."""

    def __init__(self, *, product_root: Path, variant: str, temporary_parent: Path) -> None:
        self.variant = variant
        temporary_parent.mkdir(parents=True, exist_ok=True)
        self._stderr_path = temporary_parent / (
            f"p2p-gate-worker-{variant}-{os.getpid()}-{id(self)}.log"
        )
        self._stderr_stream = self._stderr_path.open("w+", encoding="utf-8")
        self._reader = ThreadPoolExecutor(max_workers=1)
        self.process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--worker-action",
                "serve",
                "--product-root",
                str(product_root),
                "--expected-revision",
                FROZEN_COMMITS[variant],
                "--variant",
                variant,
                "--temporary-parent",
                str(temporary_parent),
            ],
            cwd=HARNESS_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr_stream,
            text=True,
            bufsize=1,
        )

    def sample(
        self,
        *,
        dataset_root: Path,
        scratch: Path,
        workload: str,
        sample_number: int,
        batch_count: int,
    ) -> dict[str, Any]:
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError(f"variant {self.variant} worker streams are unavailable")
        if self.process.poll() is not None:
            raise RuntimeError(
                f"variant {self.variant} worker exited before sample: {self._diagnostic()}"
            )
        request = {
            "action": "sample",
            "dataset_root": str(dataset_root),
            "scratch": str(scratch),
            "workload": workload,
            "sample_number": sample_number,
            "batch_count": batch_count,
        }
        self.process.stdin.write(_canonical_json(request) + "\n")
        self.process.stdin.flush()
        pending = self._reader.submit(self.process.stdout.readline)
        try:
            raw = pending.result(timeout=WORKER_SAMPLE_TIMEOUT_SECONDS)
        except FutureTimeoutError as exc:
            self.process.kill()
            pending.result(timeout=10)
            raise RuntimeError(
                f"variant {self.variant} {workload} sample exceeded "
                f"{WORKER_SAMPLE_TIMEOUT_SECONDS} seconds: {self._diagnostic()}"
            ) from exc
        if not raw:
            raise RuntimeError(
                f"variant {self.variant} worker stopped unexpectedly: {self._diagnostic()}"
            )
        response = json.loads(raw)
        if not response.get("ok"):
            raise RuntimeError(
                f"variant {self.variant} {workload} sample failed: "
                f"{response.get('error_type')}: {response.get('error')}"
            )
        payload = response.get("payload")
        if not isinstance(payload, dict):
            raise RuntimeError(f"variant {self.variant} worker returned invalid payload")
        return payload

    def _diagnostic(self) -> str:
        self._stderr_stream.flush()
        self._stderr_stream.seek(0)
        return self._stderr_stream.read().strip()

    def close(self) -> None:
        if self.process.poll() is None and self.process.stdin is not None:
            try:
                self.process.stdin.write('{"action":"close"}\n')
                self.process.stdin.flush()
            except OSError:
                pass
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=10)
        self._reader.shutdown(wait=True, cancel_futures=True)
        self._stderr_stream.close()
        self._stderr_path.unlink(missing_ok=True)

    def __enter__(self) -> _WorkerSession:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _clone_variants(repository: Path, parent: Path) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for variant, revision in FROZEN_COMMITS.items():
        target = parent / f"variant-{variant}"
        _run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-checkout",
                "--no-hardlinks",
                str(repository),
                str(target),
            ]
        )
        _run(["git", "checkout", "--quiet", "--detach", revision], cwd=target)
        observed = _git(target, "rev-parse", "HEAD")
        if observed != revision:
            raise RuntimeError(f"variant {variant} checkout mismatch: {observed} != {revision}")
        if _git(target, "status", "--porcelain"):
            raise RuntimeError(f"variant {variant} detached checkout is dirty")
        roots[variant] = target
    return roots


def _nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    invalid_records = [item for item in records if not bool(item.get("valid", True))]
    valid_records = [
        item
        for item in records
        if bool(item.get("valid", True)) and item.get("per_operation_seconds") is not None
    ]
    if not valid_records:
        return {
            "samples": records,
            "sample_count": 0,
            "invalid_sample_count": len(invalid_records),
            "invalid_samples": invalid_records,
            "minimum_seconds": None,
            "median_seconds": None,
            "p90_seconds": None,
            "p95_seconds": None,
            "maximum_seconds": None,
            "median_absolute_deviation_seconds": None,
            "relative_mad": None,
            "relative_half_drift": None,
            "valid_variance": False,
            "peak_python_bytes": 0,
            "peak_rss_bytes": 0,
            "maximum_disk_delta_bytes": 0,
        }
    samples = [float(item["per_operation_seconds"]) for item in valid_records]
    median = statistics.median(samples)
    mad = statistics.median(abs(value - median) for value in samples)
    half = max(1, len(samples) // 2)
    first = statistics.median(samples[:half])
    second = statistics.median(samples[-half:])
    relative_mad = mad / median if median else 0.0
    half_drift = (second - first) / first if first else 0.0
    return {
        "samples": records,
        "sample_count": len(valid_records),
        "invalid_sample_count": len(invalid_records),
        "invalid_samples": invalid_records,
        "minimum_seconds": min(samples),
        "median_seconds": median,
        "p90_seconds": _nearest_rank(samples, 0.90),
        "p95_seconds": _nearest_rank(samples, 0.95),
        "maximum_seconds": max(samples),
        "median_absolute_deviation_seconds": mad,
        "relative_mad": relative_mad,
        "relative_half_drift": half_drift,
        "valid_variance": not invalid_records
        and (relative_mad <= MAX_RELATIVE_MAD and abs(half_drift) <= MAX_ABSOLUTE_HALF_DRIFT),
        "peak_python_bytes": max(
            int(item.get("tracemalloc_peak_bytes", item.get("peak_python_bytes", 0)))
            for item in valid_records
        ),
        "peak_rss_bytes": max(
            int(
                (item.get("rss_after") or {}).get("current_bytes")
                or (item.get("rss_after") or {}).get("peak_bytes")
                or item.get("peak_rss_bytes", 0)
            )
            for item in valid_records
        ),
        "maximum_disk_delta_bytes": max(
            int(item.get("disk_bytes_after", item.get("disk_after_bytes", 0)))
            - int(item.get("disk_bytes_before", item.get("disk_before_bytes", 0)))
            for item in valid_records
        ),
    }


def _comparison(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    if left.get("median_seconds") is None or right.get("median_seconds") is None:
        return {
            "valid": False,
            "median_ratio": None,
            "median_change": None,
            "p95_ratio": None,
            "p95_change": None,
            "robust_noise_floor": None,
            "meaningful_median_change": False,
            "meaningful_p95_change": False,
        }
    left_median = float(left["median_seconds"])
    right_median = float(right["median_seconds"])
    left_p95 = float(left["p95_seconds"])
    right_p95 = float(right["p95_seconds"])
    median_change = (right_median - left_median) / left_median if left_median else 0.0
    p95_change = (right_p95 - left_p95) / left_p95 if left_p95 else 0.0
    noise_floor = ROBUST_MAD_MULTIPLIER * max(
        float(left.get("relative_mad") or 0.0), float(right.get("relative_mad") or 0.0)
    )
    valid = bool(left["valid_variance"] and right["valid_variance"])
    return {
        "valid": valid,
        "median_ratio": right_median / left_median if left_median else None,
        "median_change": median_change,
        "p95_ratio": right_p95 / left_p95 if left_p95 else None,
        "p95_change": p95_change,
        "robust_noise_floor": noise_floor,
        "meaningful_median_change": (
            valid
            and abs(median_change) >= MEANINGFUL_MEDIAN_RATIO
            and abs(median_change) > noise_floor
        ),
        "meaningful_p95_change": valid and abs(p95_change) >= MEANINGFUL_P95_RATIO,
    }


def _validate_ancestry(repository: Path) -> None:
    for ancestor, descendant in (("a", "b"), ("b", "c")):
        completed = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                FROZEN_COMMITS[ancestor],
                FROZEN_COMMITS[descendant],
            ],
            cwd=repository,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"frozen ancestry {ancestor}->{descendant} is invalid")


def _platform_run(arguments: argparse.Namespace) -> dict[str, Any]:
    repository = HARNESS_ROOT.resolve()
    if not (repository / ".git").exists():
        raise RuntimeError("the evaluator must run from the p2p-engine Git checkout")
    _validate_ancestry(repository)
    temporary_parent = arguments.temporary_parent.resolve()
    if not temporary_parent.is_dir():
        raise RuntimeError("--temporary-parent must be an existing directory")
    profiles = tuple(arguments.profiles or FROZEN_PROFILES)
    workloads = tuple(arguments.workloads or FROZEN_WORKLOADS)
    gate_eligible = profiles == FROZEN_PROFILES and workloads == FROZEN_WORKLOADS
    if arguments.smoke:
        gate_eligible = False
    harness_digests = {
        "evaluator_sha256": _sha256_file(Path(__file__).resolve()),
        "benchmark_worker_sha256": _sha256_file(BENCHMARK_SCRIPT),
    }
    matrix_identity = _matrix_identity(
        harness_digests=harness_digests,
        profiles=profiles,
        workloads=workloads,
    )
    dependency_environment = _dependency_environment()
    platform_target = os.environ.get("P2P_GATE_TARGET", "local-unclassified")
    workflow_provenance = {
        "platform_target": platform_target,
        "github_repository": os.environ.get("GITHUB_REPOSITORY"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_sha": os.environ.get("GITHUB_SHA"),
    }
    with tempfile.TemporaryDirectory(prefix="p2p-local-backend-gate-", dir=temporary_parent) as raw:
        run_root = Path(raw)
        product_roots = _clone_variants(repository, run_root / "products")
        datasets: dict[str, dict[str, Any]] = {variant: {} for variant in FROZEN_COMMITS}
        baselines: dict[str, dict[str, Any]] = {}
        environments: dict[str, dict[str, Any]] = {}
        contracts: dict[str, dict[str, Any]] = {}
        for variant in FROZEN_COMMITS:
            for profile_name in profiles:
                prepared = _worker(
                    product_root=product_roots[variant],
                    action="prepare",
                    variant=variant,
                    expected_revision=FROZEN_COMMITS[variant],
                    temporary_parent=temporary_parent,
                    dataset_root=run_root / "datasets" / variant / profile_name,
                    scratch=run_root / "scratch" / variant / profile_name,
                    profile=profile_name,
                )
                baselines[variant] = prepared["baseline"]
                environments[variant] = prepared["environment"]
                contracts[variant] = prepared["contracts"]
                datasets[variant][profile_name] = prepared["dataset"]

        observed_target = _platform_target_from_environment(environments["a"])
        if platform_target == "local-unclassified":
            platform_target = observed_target
            workflow_provenance["platform_target"] = platform_target
        platform_target_matches = platform_target == observed_target
        environment_control_fields = (
            "system",
            "release",
            "machine",
            "python_version",
            "python_executable",
            "filesystem_type",
            "logical_cpu_count",
            "memory_bytes",
        )
        normalized_environments = {
            variant: {
                field: environments[variant].get(field) for field in environment_control_fields
            }
            for variant in FROZEN_COMMITS
        }
        environment_controls_equal = (
            len({_canonical_json(value) for value in normalized_environments.values()}) == 1
        )
        persistent_filesystem = all(
            str(environments[variant].get("filesystem_type") or "").lower()
            not in {"", "unknown", "tmpfs", "ramfs"}
            for variant in FROZEN_COMMITS
        )
        artifact_coordinates = {
            variant: {
                field: baselines[variant].get(field)
                for field in (
                    "git_revision",
                    "git_tree",
                    "product_source_digest",
                    "pyproject_sha256",
                    "package_version",
                )
            }
            for variant in FROZEN_COMMITS
        }

        fixture_equivalence: dict[str, dict[str, Any]] = {}
        for profile_name in profiles:
            logical = {
                variant: datasets[variant][profile_name]["logical_fixture_digest"]
                for variant in FROZEN_COMMITS
            }
            semantic = {
                variant: datasets[variant][profile_name]["semantic_state_digest"]
                for variant in FROZEN_COMMITS
            }
            identity = {
                variant: datasets[variant][profile_name]["project_uuid"]
                for variant in FROZEN_COMMITS
            }
            fixture_equivalence[profile_name] = {
                "logical_fixture_digests": logical,
                "semantic_state_digests": semantic,
                "project_uuids": identity,
                "pass": len(set(logical.values())) == 1
                and len(set(semantic.values())) == 1
                and len(set(identity.values())) == 1,
            }

        conformance = {
            variant: _worker(
                product_root=product_roots[variant],
                action="conformance",
                variant=variant,
                expected_revision=FROZEN_COMMITS[variant],
                temporary_parent=temporary_parent,
                dataset_root=run_root / "datasets" / variant / profiles[0],
                scratch=run_root / "conformance" / variant,
                profile=profiles[0],
            )
            for variant in FROZEN_COMMITS
        }
        agent_equivalence = _worker(
            product_root=product_roots["c"],
            action="agents",
            variant="c",
            expected_revision=FROZEN_COMMITS["c"],
            temporary_parent=temporary_parent,
            scratch=run_root / "agent-equivalence",
        )

        immutable_sources = all(
            baselines[variant]["git_revision"] == FROZEN_COMMITS[variant]
            and bool(baselines[variant]["product_source_clean"])
            for variant in FROZEN_COMMITS
        )
        contract_equivalence = len({_canonical_json(value) for value in contracts.values()}) == 1
        baseline_contract_equivalence = _canonical_json(contracts["a"]) == _canonical_json(
            contracts["b"]
        )
        fixture_pass = all(bool(item["pass"]) for item in fixture_equivalence.values())
        baseline_fixture_pass = all(
            item["logical_fixture_digests"]["a"] == item["logical_fixture_digests"]["b"]
            and item["semantic_state_digests"]["a"] == item["semantic_state_digests"]["b"]
            and item["project_uuids"]["a"] == item["project_uuids"]["b"]
            for item in fixture_equivalence.values()
        )
        baseline_conformance = all(
            bool(conformance[variant].get("valid")) for variant in ("a", "b")
        )
        candidate_conformance = bool(conformance["c"].get("valid"))
        agent_artifact_equivalence = bool(agent_equivalence.get("valid"))
        execution_integrity = all(
            (
                immutable_sources,
                bool(dependency_environment.get("lock_sha256")),
                platform_target_matches,
                environment_controls_equal,
                persistent_filesystem,
            )
        )
        baseline_pre_measurement_ready = all(
            (
                execution_integrity,
                baseline_contract_equivalence,
                baseline_fixture_pass,
                baseline_conformance,
            )
        )
        filesystem_go_eligible = bool(gate_eligible and baseline_pre_measurement_ready)
        candidate_pre_measurement_ready = all(
            (
                baseline_pre_measurement_ready,
                contract_equivalence,
                fixture_pass,
                candidate_conformance,
                agent_artifact_equivalence,
            )
        )
        pre_measurement_hard_gates = {
            "immutable_sources": immutable_sources,
            "locked_harness_environment": bool(dependency_environment.get("lock_sha256")),
            "baseline_a_b_contract_equivalence": baseline_contract_equivalence,
            "contract_equivalence": contract_equivalence,
            "baseline_a_b_fixture_equivalence": baseline_fixture_pass,
            "fixture_equivalence": fixture_pass,
            "baseline_a_b_functional_recovery_conformance": baseline_conformance,
            "candidate_c_functional_recovery_conformance": candidate_conformance,
            "functional_recovery_conformance": (baseline_conformance and candidate_conformance),
            "agent_artifact_equivalence": agent_artifact_equivalence,
            "platform_target_matches_environment": platform_target_matches,
            "environment_controls_equal": environment_controls_equal,
            "persistent_filesystem": persistent_filesystem,
        }
        if not candidate_pre_measurement_ready and not getattr(
            arguments, "continue_after_hard_gate_failure", False
        ):
            hard_gates = {
                **pre_measurement_hard_gates,
                "variance": False,
                "complete_frozen_matrix": False,
            }
            evidence_valid = filesystem_go_eligible
            remaining_outcomes = (
                ["filesystem-go", "inconclusive"] if filesystem_go_eligible else ["inconclusive"]
            )
            return {
                "contract": PLATFORM_CONTRACT,
                "gate_contract": GATE_CONTRACT,
                # `valid` describes the decision evidence, not whether candidate
                # C passed.  This distinction lets a sound experiment reject C
                # without being confused with an aborted/incomplete run.
                "valid": evidence_valid,
                "execution_valid": execution_integrity,
                "gate_eligible": gate_eligible,
                "status": (
                    "complete-candidate-rejected"
                    if evidence_valid
                    else "complete-inconclusive-evidence"
                ),
                "decision": {
                    "outcome": "pending-owner-review",
                    "sqlite_go_eligible": False,
                    "filesystem_go_eligible": filesystem_go_eligible,
                    "remaining_outcomes": remaining_outcomes,
                    "automated_git_action": False,
                },
                "frozen_commits": FROZEN_COMMITS,
                "variant_names": VARIANT_NAMES,
                "candidate_c_reference_wheel_sha256": (FROZEN_CANDIDATE_C_REFERENCE_WHEEL_SHA256),
                "harness_digests": harness_digests,
                "matrix_identity": matrix_identity,
                "dependency_environment": dependency_environment,
                "workflow_provenance": workflow_provenance,
                "baseline": baselines,
                "artifact_coordinates": artifact_coordinates,
                "environment": environments,
                "contracts": contracts,
                "profiles": list(profiles),
                "workloads": list(workloads),
                "warmup_policy": {
                    "ordinary": ORDINARY_WARMUPS,
                    "stress": STRESS_WARMUPS,
                },
                "repetition_policy": {
                    "ordinary": ORDINARY_REPETITIONS,
                    "stress": STRESS_REPETITIONS,
                },
                "thresholds": matrix_identity["value"]["thresholds"],
                "excluded_metrics": ["complete_test_suite_duration", "test_count"],
                "fixture_equivalence": fixture_equivalence,
                "conformance": conformance,
                "agent_equivalence": agent_equivalence,
                "summaries": {},
                "comparisons": {},
                "hard_gates": hard_gates,
                "performance_matrix": {
                    "status": "not-run",
                    "reason": (
                        "A mandatory correctness/recovery gate failed; latency cannot "
                        "make candidate C eligible."
                    ),
                },
                "limitations": [
                    "Performance evidence was intentionally not interpreted after a hard gate failure.",
                    (
                        "A valid candidate rejection permits owner review of filesystem-go; "
                        "an invalid baseline or execution permits only inconclusive."
                    ),
                    "Automation changes no Git state and makes no backend selection.",
                ],
            }

        raw_samples: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {
            variant: {
                profile_name: {workload: [] for workload in workloads} for profile_name in profiles
            }
            for variant in FROZEN_COMMITS
        }
        schedule: list[dict[str, Any]] = []
        cell_number = 0
        variants = tuple(FROZEN_COMMITS)
        checkpoint_base = {
            "contract": PLATFORM_CONTRACT,
            "gate_contract": GATE_CONTRACT,
            "valid": False,
            "gate_eligible": False,
            "status": "collecting",
            "frozen_commits": FROZEN_COMMITS,
            "variant_names": VARIANT_NAMES,
            "candidate_c_reference_wheel_sha256": (FROZEN_CANDIDATE_C_REFERENCE_WHEEL_SHA256),
            "harness_digests": harness_digests,
            "matrix_identity": matrix_identity,
            "dependency_environment": dependency_environment,
            "workflow_provenance": workflow_provenance,
            "baseline": baselines,
            "artifact_coordinates": artifact_coordinates,
            "environment": environments,
            "contracts": contracts,
            "profiles": list(profiles),
            "workloads": list(workloads),
            "fixture_equivalence": fixture_equivalence,
            "conformance": conformance,
            "agent_equivalence": agent_equivalence,
            "automated_git_action": False,
        }
        _write_checkpoint(
            arguments,
            {**checkpoint_base, "completed_cells": 0, "schedule": [], "raw_samples": {}},
        )
        for profile_name in profiles:
            repetitions = (
                3
                if arguments.smoke
                else (STRESS_REPETITIONS if profile_name == "stress" else ORDINARY_REPETITIONS)
            )
            warmups = (
                0
                if arguments.smoke
                else (STRESS_WARMUPS if profile_name == "stress" else ORDINARY_WARMUPS)
            )
            for workload in workloads:
                cell_number += 1
                # Recreate all three interpreters at each cell boundary. This
                # keeps variant order interleaved without carrying product
                # caches or RSS high-water marks across unrelated workloads.
                with contextlib.ExitStack() as stack:
                    sessions = {
                        variant: stack.enter_context(
                            _WorkerSession(
                                product_root=product_roots[variant],
                                variant=variant,
                                temporary_parent=temporary_parent,
                            )
                        )
                        for variant in variants
                    }
                    batch_count = FROZEN_BATCH_COUNTS.get(profile_name, {}).get(workload, 1)
                    for ordinal in range(1, warmups + repetitions + 1):
                        offset = (cell_number + ordinal - 2) % len(variants)
                        order = variants[offset:] + variants[:offset]
                        schedule.append(
                            {
                                "profile": profile_name,
                                "workload": workload,
                                "ordinal": ordinal,
                                "warmup": ordinal <= warmups,
                                "variant_order": list(order),
                            }
                        )
                        for variant in order:
                            observed = sessions[variant].sample(
                                dataset_root=(run_root / "datasets" / variant / profile_name),
                                scratch=(run_root / "samples" / variant / profile_name / workload),
                                workload=workload,
                                sample_number=ordinal,
                                batch_count=batch_count,
                            )
                            observed["ordinal"] = ordinal
                            observed["warmup"] = ordinal <= warmups
                            if ordinal > warmups:
                                raw_samples[variant][profile_name][workload].append(observed)
                _write_checkpoint(
                    arguments,
                    {
                        **checkpoint_base,
                        "completed_cells": cell_number,
                        "schedule": schedule,
                        "raw_samples": raw_samples,
                    },
                )

        summaries: dict[str, dict[str, dict[str, Any]]] = {
            variant: {
                profile_name: {
                    workload: _summarize(raw_samples[variant][profile_name][workload])
                    for workload in workloads
                }
                for profile_name in profiles
            }
            for variant in FROZEN_COMMITS
        }
        variance_reruns: list[dict[str, Any]] = []
        invalid_cells = {
            (profile_name, workload)
            for profile_name in profiles
            for workload in workloads
            if any(
                not summaries[variant][profile_name][workload]["valid_variance"]
                for variant in variants
            )
        }
        if invalid_cells and not arguments.smoke:
            for rerun_number, (profile_name, workload) in enumerate(sorted(invalid_cells), start=1):
                with contextlib.ExitStack() as stack:
                    rerun_sessions = {
                        variant: stack.enter_context(
                            _WorkerSession(
                                product_root=product_roots[variant],
                                variant=variant,
                                temporary_parent=temporary_parent,
                            )
                        )
                        for variant in variants
                    }
                    before = {
                        variant: summaries[variant][profile_name][workload] for variant in variants
                    }
                    repetitions = (
                        STRESS_REPETITIONS if profile_name == "stress" else ORDINARY_REPETITIONS
                    )
                    warmups = STRESS_WARMUPS if profile_name == "stress" else ORDINARY_WARMUPS
                    rerun_samples: dict[str, list[dict[str, Any]]] = {
                        variant: [] for variant in variants
                    }
                    batch_count = FROZEN_BATCH_COUNTS.get(profile_name, {}).get(workload, 1)
                    for ordinal in range(1, warmups + repetitions + 1):
                        offset = (rerun_number + ordinal - 2) % len(variants)
                        order = variants[offset:] + variants[:offset]
                        for variant in order:
                            observed = rerun_sessions[variant].sample(
                                dataset_root=(run_root / "datasets" / variant / profile_name),
                                scratch=(run_root / "reruns" / variant / profile_name / workload),
                                workload=workload,
                                sample_number=1000 + ordinal,
                                batch_count=batch_count,
                            )
                            observed["ordinal"] = ordinal
                            observed["warmup"] = ordinal <= warmups
                            if ordinal > warmups:
                                rerun_samples[variant].append(observed)
                    for variant in variants:
                        raw_samples[variant][profile_name][workload] = rerun_samples[variant]
                        summaries[variant][profile_name][workload] = _summarize(
                            rerun_samples[variant]
                        )
                    variance_reruns.append(
                        {
                            "profile": profile_name,
                            "workload": workload,
                            "reason": "relative MAD or absolute half-drift exceeded 15%",
                            "initial_summaries": before,
                            "replacement_summaries": {
                                variant: summaries[variant][profile_name][workload]
                                for variant in variants
                            },
                        }
                    )
        comparisons: dict[str, dict[str, dict[str, Any]]] = {}
        for profile_name in profiles:
            comparisons[profile_name] = {}
            for workload in workloads:
                comparisons[profile_name][workload] = {
                    "a_to_b_abstraction": _comparison(
                        summaries["a"][profile_name][workload],
                        summaries["b"][profile_name][workload],
                    ),
                    "b_to_c_backend": _comparison(
                        summaries["b"][profile_name][workload],
                        summaries["c"][profile_name][workload],
                    ),
                }

        variance_pass = all(
            bool(summaries[variant][profile_name][workload]["valid_variance"])
            for variant in FROZEN_COMMITS
            for profile_name in profiles
            for workload in workloads
        )
        hard_gates = {
            **pre_measurement_hard_gates,
            "fixture_equivalence": fixture_pass,
            "variance": variance_pass,
            "complete_frozen_matrix": gate_eligible,
        }
        decision_evidence_valid = bool(filesystem_go_eligible and variance_pass and gate_eligible)
        sqlite_go_eligible = bool(decision_evidence_valid and all(hard_gates.values()))
        return {
            "contract": PLATFORM_CONTRACT,
            "gate_contract": GATE_CONTRACT,
            "valid": decision_evidence_valid,
            "execution_valid": execution_integrity,
            "gate_eligible": gate_eligible,
            "status": ("complete" if decision_evidence_valid else "complete-inconclusive-evidence"),
            "decision": {
                "outcome": "pending-cross-platform-owner-review",
                "sqlite_go_eligible": sqlite_go_eligible,
                "filesystem_go_eligible": decision_evidence_valid,
                "remaining_outcomes": (
                    ["sqlite-go", "filesystem-go", "inconclusive"]
                    if sqlite_go_eligible
                    else ["filesystem-go", "inconclusive"]
                    if decision_evidence_valid
                    else ["inconclusive"]
                ),
                "automated_git_action": False,
            },
            "frozen_commits": FROZEN_COMMITS,
            "variant_names": VARIANT_NAMES,
            "candidate_c_reference_wheel_sha256": (FROZEN_CANDIDATE_C_REFERENCE_WHEEL_SHA256),
            "harness_digests": harness_digests,
            "matrix_identity": matrix_identity,
            "dependency_environment": dependency_environment,
            "workflow_provenance": workflow_provenance,
            "baseline": baselines,
            "artifact_coordinates": artifact_coordinates,
            "environment": environments,
            "contracts": contracts,
            "profiles": list(profiles),
            "workloads": list(workloads),
            "warmup_policy": {"ordinary": ORDINARY_WARMUPS, "stress": STRESS_WARMUPS},
            "repetition_policy": {
                "ordinary": ORDINARY_REPETITIONS,
                "stress": STRESS_REPETITIONS,
            },
            "thresholds": {
                "maximum_relative_mad": MAX_RELATIVE_MAD,
                "maximum_absolute_half_drift": MAX_ABSOLUTE_HALF_DRIFT,
                "meaningful_median_ratio": MEANINGFUL_MEDIAN_RATIO,
                "meaningful_p95_ratio": MEANINGFUL_P95_RATIO,
                "robust_mad_multiplier": ROBUST_MAD_MULTIPLIER,
            },
            "excluded_metrics": ["complete_test_suite_duration", "test_count"],
            "fixture_equivalence": fixture_equivalence,
            "conformance": conformance,
            "agent_equivalence": agent_equivalence,
            "schedule": schedule,
            "controlled_variance_reruns": variance_reruns,
            "summaries": summaries,
            "comparisons": comparisons,
            "hard_gates": hard_gates,
            "limitations": [
                "Absolute timings are comparable only within this platform run.",
                "The owner makes the backend decision after all platform artifacts exist.",
                "A failed variance cell requires one controlled rerun; samples are never trimmed.",
            ],
        }


def _aggregate(paths: Iterable[Path]) -> dict[str, Any]:
    paths = tuple(paths)
    evidence: list[dict[str, Any]] = []
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("contract") != PLATFORM_CONTRACT:
            raise RuntimeError(f"{path} is not 27A platform evidence")
        evidence.append(value)
    by_target: dict[str, dict[str, Any]] = {}
    for item in evidence:
        provenance = item.get("workflow_provenance")
        if not isinstance(provenance, dict):
            raise RuntimeError("platform evidence lacks workflow provenance")
        target = str(provenance.get("platform_target") or "")
        if not target:
            raise RuntimeError("platform evidence lacks an OS/architecture target")
        if target in by_target:
            raise RuntimeError(f"duplicate platform evidence for {target}")
        by_target[target] = item
    missing = sorted(REQUIRED_PLATFORM_TARGETS - set(by_target))
    matrix_digests = {
        str((item.get("matrix_identity") or {}).get("sha256") or "") for item in evidence
    }
    matrix_identity_matches = len(matrix_digests) == 1 and "" not in matrix_digests
    coordinate_fields = (
        "frozen_commits",
        "variant_names",
        "candidate_c_reference_wheel_sha256",
        "harness_digests",
        "artifact_coordinates",
        "profiles",
        "workloads",
        "warmup_policy",
        "repetition_policy",
        "thresholds",
        "excluded_metrics",
    )
    coordinate_equivalence = all(
        len({_canonical_json(item.get(field)) for item in evidence}) == 1
        for field in coordinate_fields
    )
    platform_evidence_complete = (
        not missing
        and len(evidence) == len(REQUIRED_PLATFORM_TARGETS)
        and matrix_identity_matches
        and coordinate_equivalence
        and all(bool(item.get("valid") and item.get("gate_eligible")) for item in evidence)
    )
    filesystem_go_eligible = bool(
        platform_evidence_complete
        and all(
            bool((item.get("decision") or {}).get("filesystem_go_eligible")) for item in evidence
        )
    )
    sqlite_go_eligible = bool(
        platform_evidence_complete
        and all(bool((item.get("decision") or {}).get("sqlite_go_eligible")) for item in evidence)
    )
    common_regressions: list[dict[str, Any]] = []
    common_improvements: list[dict[str, Any]] = []
    abstraction_regressions: list[dict[str, Any]] = []
    high_percentile_regressions: list[dict[str, Any]] = []
    for target, item in by_target.items():
        for profile_name, workloads in (item.get("comparisons") or {}).items():
            for workload, comparison in workloads.items():
                abstraction = comparison["a_to_b_abstraction"]
                if (
                    abstraction.get("meaningful_median_change")
                    and float(abstraction["median_change"]) > 0
                ):
                    abstraction_regressions.append(
                        {
                            "platform": target,
                            "profile": profile_name,
                            "workload": workload,
                            "median_change": abstraction["median_change"],
                        }
                    )
                if workload not in COMMON_OPERATION_WORKLOADS:
                    continue
                backend = comparison["b_to_c_backend"]
                record = {
                    "platform": target,
                    "profile": profile_name,
                    "workload": workload,
                    "median_change": backend["median_change"],
                    "p95_change": backend["p95_change"],
                }
                if backend.get("meaningful_median_change"):
                    if float(backend["median_change"]) > 0:
                        common_regressions.append(record)
                    else:
                        common_improvements.append(record)
                if backend.get("meaningful_p95_change") and float(backend["p95_change"]) > 0:
                    high_percentile_regressions.append(record)
    return {
        "contract": AGGREGATE_CONTRACT,
        "valid": platform_evidence_complete,
        "platforms": sorted(by_target),
        "missing_platforms": missing,
        "matrix_identity_matches": matrix_identity_matches,
        "coordinate_equivalence": coordinate_equivalence,
        "matrix_identity_sha256": sorted(matrix_digests),
        "platform_evidence_sha256": {path.name: _sha256_file(path) for path in paths},
        "a_to_b_abstraction_regressions": abstraction_regressions,
        "common_operation_regressions": common_regressions,
        "common_operation_improvements": common_improvements,
        "common_operation_p95_regressions": high_percentile_regressions,
        "sqlite_go_eligible": sqlite_go_eligible,
        "filesystem_go_eligible": filesystem_go_eligible,
        "remaining_outcomes": (
            ["sqlite-go", "filesystem-go", "inconclusive"]
            if sqlite_go_eligible
            else ["filesystem-go", "inconclusive"]
            if filesystem_go_eligible
            else ["inconclusive"]
        ),
        "technical_gate_status": (
            "candidates-eligible-owner-review"
            if sqlite_go_eligible
            else "candidate-c-rejected-owner-review"
            if filesystem_go_eligible
            else "inconclusive-required"
        ),
        "automated_recommendation": "not-issued",
        "owner_decision": "pending",
        "automated_git_action": False,
        "limitations": [
            "Automation intentionally does not choose sqlite-go or filesystem-go.",
            "Operational complexity, recovery, portability, and dependencies must be reviewed before selection.",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temporary-parent", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--profile", action="append", choices=FROZEN_PROFILES, dest="profiles")
    parser.add_argument("--only", action="append", choices=FROZEN_WORKLOADS, dest="workloads")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Use three samples and no warmups; output is never gate eligible.",
    )
    parser.add_argument(
        "--continue-after-hard-gate-failure",
        action="store_true",
        help=(
            "Collect diagnostic performance samples even when correctness already "
            "makes a candidate ineligible; never changes gate outcome."
        ),
    )
    parser.add_argument("--aggregate", action="append", type=Path, dest="aggregate_paths")

    # Internal worker protocol. It is intentionally absent from product CLI.
    parser.add_argument(
        "--worker-action",
        choices=("prepare", "sample", "conformance", "agents", "serve"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--product-root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--expected-revision", default="", help=argparse.SUPPRESS)
    parser.add_argument("--variant", choices=("a", "b", "c"), default="a", help=argparse.SUPPRESS)
    parser.add_argument("--dataset-root", type=Path, default=Path("."), help=argparse.SUPPRESS)
    parser.add_argument("--scratch", type=Path, default=Path("."), help=argparse.SUPPRESS)
    parser.add_argument("--workload", default="cold_project_open", help=argparse.SUPPRESS)
    parser.add_argument("--sample-number", type=int, default=1, help=argparse.SUPPRESS)
    parser.add_argument("--batch-count", type=int, default=1, help=argparse.SUPPRESS)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    output = arguments.output.resolve() if arguments.output is not None else None
    try:
        if arguments.worker_action:
            if arguments.product_root is None:
                raise RuntimeError("internal worker requires --product-root")
            return _worker_main(arguments)
        if arguments.aggregate_paths:
            result = _aggregate(tuple(path.resolve() for path in arguments.aggregate_paths))
        else:
            result = _platform_run(arguments)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        preserved: dict[str, Any] = {}
        if output is not None and output.is_file():
            try:
                existing = json.loads(output.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    preserved = existing
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                pass
        failure = {
            **preserved,
            "contract": PLATFORM_CONTRACT,
            "valid": False,
            "gate_eligible": False,
            "status": "aborted",
            "error": str(exc),
            "automated_git_action": False,
        }
        if output is not None:
            _write_json(output, failure)
        print(f"local-storage gate invalid: {exc}", file=sys.stderr)
        return 2
    if output is not None:
        _write_json(output, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if bool(result.get("valid")) else 3


if __name__ == "__main__":
    raise SystemExit(main())

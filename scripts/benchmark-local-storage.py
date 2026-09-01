#!/usr/bin/env python3
"""Reproducible local-storage benchmark harness.

Step 25A froze variant A and step 26 added variant B.  Step 27A reuses those
contracts for candidate C.  The harness can be copied next to an immutable
product checkout: ``P2P_BENCHMARK_PRODUCT_ROOT`` selects the product under
test, while the location of this file remains the harness provenance.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import tracemalloc
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import date
from pathlib import Path
from time import perf_counter_ns
from uuid import UUID, uuid5

HARNESS_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ROOT = Path(os.environ.get("P2P_BENCHMARK_PRODUCT_ROOT", str(HARNESS_ROOT))).resolve()
# Backwards-compatible name for callers that imported the A/B pilot module.
SOURCE_ROOT = PRODUCT_ROOT
if str(PRODUCT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT / "src"))
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(1, str(PRODUCT_ROOT))

import p2p_engine  # noqa: E402
from p2p_engine.core.project_identity import (  # noqa: E402
    ProjectIdentity,
    ProjectUuid,
    ReplicaId,
)
from p2p_engine.storage.filesystem import P2PWorkspace  # noqa: E402
from p2p_engine.storage.project_identity import (  # noqa: E402
    FilesystemProjectIdentityStore,
)
from tests.workspace_scale_fixtures import build_scale_workspace  # noqa: E402

HARNESS_CONTRACT = "p2p-local-backend-benchmark/v1"
DATASET_CONTRACT = "p2p-local-backend-dataset/v1"
DATASET_VERSION = "baseline-a-datasets/v1"
WORKLOAD_VERSION = "baseline-a-workloads/v1"
BASELINE_A_VARIANT = "A-filesystem-before-storage-ports"
BASELINE_B_VARIANT = "B-filesystem-behind-storage-ports"
CANDIDATE_C_VARIANT = "C-sqlite-behind-storage-ports"
VARIANT_LABELS = {
    "a": BASELINE_A_VARIANT,
    "b": BASELINE_B_VARIANT,
    "c": CANDIDATE_C_VARIANT,
}
DATASET_NAMESPACE = UUID("9491fe2b-4be8-5ea8-a71b-c40269177d08")
FROZEN_DATASET_DATE = "2026-08-31"


@dataclass(frozen=True)
class DatasetProfile:
    name: str
    proposal_count: int
    rich_proposals: int
    blob_count: int
    blob_bytes: int
    history_records: int


DATASET_PROFILES: dict[str, DatasetProfile] = {
    "small": DatasetProfile("small", 8, 8, 2, 4 * 1024, 16),
    "medium": DatasetProfile("medium", 64, 32, 8, 16 * 1024, 128),
    "large": DatasetProfile("large", 256, 64, 16, 64 * 1024, 512),
    "stress": DatasetProfile("stress", 1024, 128, 32, 256 * 1024, 2048),
}

FROZEN_DATASET_DIGESTS: dict[str, dict[str, str]] = {
    "small": {
        "logical_fixture_digest": "acd4e0dee1ce1cf98d7f5977bcf27dcb614e8f2cb1c1d1c13f427c1dc56ad329",
        "semantic_state_digest": "1b2f765ba65484ec365b691765e081a641e82066e615f1261f7fdd0c06353d02",
    },
    "medium": {
        "logical_fixture_digest": "0b3b2360ab29fd8b8c2d379cee914e9f1b17d7db5858faae7e97959fdc207536",
        "semantic_state_digest": "38b6745a36c41ecd55bf210cc60d72eee44b07b4dfedc5f7cc1f0b37bd1771a4",
    },
    "large": {
        "logical_fixture_digest": "e08bcaa5db40c46368b447e523a0d33512f99d6255e6a1f9da6e1de4cd4f32b4",
        "semantic_state_digest": "6aabd9d46deedbc9c1ff8a6cbbabeeee7861613e3764e6c7841b299ecb9517b6",
    },
    "stress": {
        "logical_fixture_digest": "1fc9da6a33f7e3606535db478b31b00ea40cb2574988ee9bab3406561f728586",
        "semantic_state_digest": "8ca7ce176bf3cd0be09c8c8c4bad774bf3771de7ea4e1e43c766849b5bcebe8a",
    },
}

# Operations below the pilot's stable timing floor are batched by these exact
# counts in the definitive A/B/C runner.  B and C must not tune the counts.
DEFINITIVE_BATCH_COUNTS: dict[str, dict[str, int]] = {
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


@dataclass(frozen=True)
class Workload:
    workload_id: str
    family: str
    cache_condition: str
    mutates: bool
    pilot: bool
    description: str


WORKLOADS: tuple[Workload, ...] = (
    Workload(
        "project_init",
        "init",
        "fresh empty directory per sample",
        True,
        False,
        "Initialize a project through the selected backend and generate integrations.",
    ),
    Workload(
        "cli_status_cold_start",
        "startup",
        "fresh CLI process; operating-system page cache uncontrolled",
        False,
        True,
        "Start the installed CLI process and read project status.",
    ),
    Workload(
        "cold_project_open",
        "open",
        "fresh_workspace_object; operating-system page cache uncontrolled",
        False,
        True,
        "Construct the workspace and load stable project identity.",
    ),
    Workload(
        "warm_proposal_list",
        "common_read",
        "reused_workspace_object; warm-up samples discarded",
        False,
        True,
        "List proposal summaries through the product facade.",
    ),
    Workload(
        "targeted_decision_read",
        "targeted_query",
        "reused_workspace_object; warm-up samples discarded",
        False,
        True,
        "Read the decision status for a deterministic middle proposal.",
    ),
    Workload(
        "memory_classification",
        "readiness_and_classification",
        "reused_workspace_object; warm-up samples discarded",
        False,
        True,
        "Build the project-memory classification snapshot.",
    ),
    Workload(
        "canonical_snapshot",
        "relation_traversal_and_snapshot",
        "reused_workspace_object; warm-up samples discarded",
        False,
        True,
        "Read entities, relations, lineage, and managed-blob metadata.",
    ),
    Workload(
        "bundle_export",
        "snapshot_and_serialization",
        "unique output per sample; source workspace reused",
        True,
        True,
        "Write a deterministic portable bundle.",
    ),
    Workload(
        "archive_verify",
        "integrity_validation",
        "one prebuilt archive; warm-up samples discarded",
        False,
        True,
        "Decode and verify a portable bundle and all checksums.",
    ),
    Workload(
        "physical_backup",
        "backup",
        "unique coordinated backup per sample",
        True,
        True,
        "Create an exact coordinated physical backup.",
    ),
    Workload(
        "governed_proposal_create",
        "multi_entity_mutation",
        "fresh untimed clone per sample",
        True,
        True,
        "Create one proposal with an idempotency receipt and atomic mutation.",
    ),
    Workload(
        "bundle_restore",
        "restore",
        "fresh untimed clone and preview per sample",
        True,
        False,
        "Apply a portable restore with staging, backup, and atomic activation.",
    ),
    Workload(
        "batch_import",
        "batch_import",
        "fresh untimed target per sample",
        True,
        False,
        "Import a frozen logical batch through the selected application port.",
    ),
    Workload(
        "concurrent_readers_serialized_writer",
        "concurrency",
        "fixed reader/writer schedule",
        True,
        False,
        "Measure concurrent readers and one serialized writer.",
    ),
    Workload(
        "crash_recovery",
        "failure_recovery",
        "fresh fault-injection clone per sample",
        True,
        False,
        "Inject interruption and verify deterministic recovery.",
    ),
)

PILOT_WORKLOAD_IDS = tuple(item.workload_id for item in WORKLOADS if item.pilot)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _deterministic_bytes(seed: int, label: str, size: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < size:
        output.extend(hashlib.sha256(f"{seed}:{label}:{counter}".encode()).digest())
        counter += 1
    return bytes(output[:size])


def _write_yaml_json_compatible(path: Path, payload: object) -> None:
    # JSON is valid YAML and avoids emitter-specific ordering in fixture files.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json(payload))


def _stabilize_identity(root: Path, *, seed: int, profile: str) -> str:
    workspace = P2PWorkspace(root)
    current = workspace.project_identity()
    project_uuid = ProjectUuid(str(uuid5(DATASET_NAMESPACE, f"{seed}:{profile}:project")))
    replica_id = ReplicaId(str(uuid5(DATASET_NAMESPACE, f"{seed}:{profile}:replica")))
    stable = ProjectIdentity(
        project_uuid=project_uuid,
        display_name=current.display_name,
        mode=current.mode,
        replica_id=replica_id,
        remote_binding=current.remote_binding,
        lineage=current.lineage,
    )
    store = FilesystemProjectIdentityStore(root=root)
    for relative, content in store.candidate_documents(
        stable, allow_project_uuid_change=True
    ).items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    storage_manifest = root / ".p2p/local/storage.yml"
    if storage_manifest.is_file():
        from p2p_engine.core.project_state_storage import ProjectStorageManifest
        from p2p_engine.storage.project_storage import ProjectStorageManifestStore

        manifest_store = ProjectStorageManifestStore(root)
        manifest = manifest_store.load()
        storage_manifest.write_bytes(
            manifest_store.render(
                ProjectStorageManifest(
                    contract=manifest.contract,
                    project_uuid=project_uuid.value,
                    adapter=manifest.adapter,
                    schema_version=manifest.schema_version,
                )
            )
        )
    return project_uuid.value


def _add_dataset_documents(root: Path, profile: DatasetProfile, *, seed: int) -> None:
    for number in range(1, profile.rich_proposals + 1):
        proposal_id = f"PROP-{number:03d}"
        proposal_dir = root / ".p2p/proposals" / f"{proposal_id}-scale-fixture"
        _write_yaml_json_compatible(
            proposal_dir / "readiness.yml",
            {
                "readiness": {
                    "schema_version": 1,
                    "proposal_id": proposal_id,
                    "status": "assessed",
                    "score": (number * 17) % 101,
                    "evidence": ["proposal.md", "impact-map.yml"],
                }
            },
        )

    work_root = root / ".p2p/work"
    work_count = max(1, min(profile.proposal_count // 4, 64))
    for number in range(1, work_count + 1):
        work_dir = work_root / f"WORK-{number:04d}-benchmark"
        work_dir.mkdir(parents=True, exist_ok=True)
        work_dir.joinpath("work.md").write_text(
            "\n".join(
                (
                    f"# WORK-{number:04d}",
                    "",
                    "## Status",
                    "",
                    "`planned`",
                    "",
                    "## Scope",
                    "",
                    f"Deterministic workload record {number} for seed {seed}.",
                    "",
                )
            ),
            encoding="utf-8",
        )

    history = [
        {
            "sequence": number,
            "entity": f"proposal:PROP-{((number - 1) % profile.proposal_count) + 1:03d}",
            "revision": number,
            "event": "benchmark-observation",
        }
        for number in range(1, profile.history_records + 1)
    ]
    _write_yaml_json_compatible(
        root / ".p2p/governance/benchmark-history.yml",
        {"benchmark_history": history},
    )
    blob_references: list[dict[str, object]] = []
    relations: list[dict[str, object]] = []
    for number in range(1, profile.blob_count + 1):
        content = _deterministic_bytes(seed, f"{profile.name}:blob:{number}", profile.blob_bytes)
        digest = _sha256_bytes(content)
        target = root / ".p2p/blobs/sha256" / digest[:2] / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        blob_references.append(
            {
                "kind": "managed_blob",
                "digest": f"sha256:{digest}",
                "label": f"{profile.name}-blob-{number:03d}",
            }
        )
        relations.append(
            {
                "id": f"benchmark-blob-{number:03d}",
                "type": "supports",
                "target": "project:manifest",
                "payload": {"ordinal": number},
            }
        )
    _write_yaml_json_compatible(
        root / ".p2p/governance/benchmark-dataset.yml",
        {
            "dataset": {
                "contract": DATASET_CONTRACT,
                "version": DATASET_VERSION,
                "profile": profile.name,
                "seed": seed,
                "blob_references": blob_references,
            },
            "canonical_relations": relations,
        },
    )


def _stabilize_dataset_dates(root: Path) -> None:
    """Remove wall-calendar drift from the frozen logical fixture.

    Product initialization deliberately records today's date in canonical
    documents. That is correct product behavior but cannot enter an immutable
    A/B/C fixture: otherwise crossing midnight changes the semantic digest and
    makes a later platform incomparable. Normalize only the date emitted by
    this initialization run, before SQLite activation, and never touch managed
    blob bytes.
    """
    observed = date.today().isoformat().encode("ascii")
    frozen = FROZEN_DATASET_DATE.encode("ascii")
    if observed == frozen:
        return
    p2p = root / ".p2p"
    for path in sorted(p2p.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(p2p)
        if relative.parts and relative.parts[0] == "blobs":
            continue
        content = path.read_bytes()
        if observed in content:
            path.write_bytes(content.replace(observed, frozen))


def directory_size(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _activate_candidate_c(root: Path) -> None:
    """Convert the frozen filesystem fixture to the one SQLite authority."""
    from p2p_engine.core.project_state_storage import ProjectStorageManifest
    from p2p_engine.storage.project_storage import ProjectStorageManifestStore
    from p2p_engine.storage.sqlite_initialization import activate_sqlite_from_filesystem
    from p2p_engine.storage.sqlite_schema import SQLITE_ADAPTER

    workspace = P2PWorkspace(root)
    identity = workspace.project_identity()
    manifest_store = ProjectStorageManifestStore(root)
    manifest_store.path.write_bytes(
        manifest_store.render(
            ProjectStorageManifest(
                project_uuid=identity.project_uuid.value,
                adapter=SQLITE_ADAPTER,
            )
        )
    )
    activate_sqlite_from_filesystem(root)


def build_dataset(
    root: Path,
    profile: DatasetProfile,
    *,
    seed: int,
    variant: str = "a",
) -> dict[str, object]:
    if variant not in VARIANT_LABELS:
        raise ValueError(f"unsupported benchmark variant: {variant}")
    built = build_scale_workspace(
        root,
        proposal_count=profile.proposal_count,
        schema_version=4,
        rich_proposals=profile.rich_proposals,
    )
    project_uuid = _stabilize_identity(root, seed=seed, profile=profile.name)
    _add_dataset_documents(root, profile, seed=seed)
    _stabilize_dataset_dates(root)
    if variant == "c":
        _activate_candidate_c(root)
    workspace = P2PWorkspace(root)
    snapshot = workspace.canonical_memory_snapshot()
    inventory = workspace.canonical_memory_inspect()
    if inventory.blockers:
        raise RuntimeError(
            "dataset has canonical-memory blockers: "
            + ", ".join(item.locator for item in inventory.blockers)
        )
    manifest: dict[str, object] = {
        "contract": DATASET_CONTRACT,
        "dataset_version": DATASET_VERSION,
        "variant": VARIANT_LABELS[variant],
        "profile": profile.name,
        "seed": seed,
        "fixture_date": FROZEN_DATASET_DATE,
        "project_uuid": project_uuid,
        "proposal_count": len(built.proposal_ids),
        "rich_proposals": built.rich_proposals,
        "history_records": profile.history_records,
        "entity_count": len(snapshot.entities),
        "relation_count": len(snapshot.relations),
        "blob_count": len(snapshot.blobs),
        "blob_bytes": sum(item.size for item in snapshot.blobs),
        "semantic_state_digest": snapshot.semantic_state_digest,
        "logical_fixture_digest": _sha256_bytes(
            _canonical_json(
                {
                    "dataset_version": DATASET_VERSION,
                    "profile": profile.__dict__,
                    "seed": seed,
                    "semantic_state_digest": snapshot.semantic_state_digest,
                }
            )
        ),
        "physical_bytes": directory_size(root / ".p2p"),
    }
    expected = FROZEN_DATASET_DIGESTS[profile.name]
    for field, expected_value in expected.items():
        if manifest[field] != expected_value:
            raise RuntimeError(
                f"frozen {profile.name} dataset {field} changed: "
                f"expected {expected_value}, observed {manifest[field]}"
            )
    return manifest


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def summarize(samples: list[float]) -> dict[str, object]:
    median = statistics.median(samples)
    mean = statistics.fmean(samples)
    deviation = statistics.stdev(samples) if len(samples) > 1 else 0.0
    mad = statistics.median(abs(value - median) for value in samples)
    half = max(1, len(samples) // 2)
    first_half_median = statistics.median(samples[:half])
    second_half_median = statistics.median(samples[-half:])
    return {
        "samples_seconds": [round(value, 9) for value in samples],
        "minimum_seconds": round(min(samples), 9),
        "median_seconds": round(median, 9),
        "p95_seconds": round(_percentile(samples, 0.95), 9),
        "maximum_seconds": round(max(samples), 9),
        "mean_seconds": round(mean, 9),
        "sample_stdev_seconds": round(deviation, 9),
        "coefficient_of_variation": round(deviation / mean if mean else 0.0, 6),
        "median_absolute_deviation_seconds": round(mad, 9),
        "relative_mad": round(mad / median if median else 0.0, 6),
        "first_half_median_seconds": round(first_half_median, 9),
        "second_half_median_seconds": round(second_half_median, 9),
        "relative_half_drift": round(
            (second_half_median - first_half_median) / first_half_median
            if first_half_median
            else 0.0,
            6,
        ),
    }


def _run_cli_status(root: Path) -> object:
    completed = subprocess.run(
        [sys.executable, "-m", "p2p_engine", "status", "--root", str(root)],
        cwd=PRODUCT_ROOT,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join((str(PRODUCT_ROOT / "src"), str(PRODUCT_ROOT))),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "p2p status failed")
    return completed


class PilotOperations:
    def __init__(self, root: Path, scratch: Path) -> None:
        self.root = root
        self.scratch = scratch
        self.workspace = P2PWorkspace(root)
        proposal_ids = tuple(item.proposal_id for item in self.workspace.proposal_summaries())
        self.target_proposal_id = proposal_ids[len(proposal_ids) // 2]
        self.bundle = scratch / "source.p2pbundle"
        self.workspace.canonical_bundle_export(self.bundle)
        self.counter = 0

    def operation(self, workload_id: str) -> Callable[[], object]:
        if workload_id == "cli_status_cold_start":
            return self._cli_status
        if workload_id == "cold_project_open":
            return lambda: P2PWorkspace(self.root).project_identity()
        if workload_id == "warm_proposal_list":
            return self.workspace.proposal_summaries
        if workload_id == "targeted_decision_read":
            return lambda: self.workspace.proposal_decision_status(self.target_proposal_id)
        if workload_id == "memory_classification":
            return self.workspace.project_memory_classification
        if workload_id == "canonical_snapshot":
            return self.workspace.canonical_memory_snapshot
        if workload_id == "archive_verify":
            return lambda: self.workspace.canonical_archive_verify(self.bundle)
        if workload_id == "bundle_export":
            return lambda: self._write_unique("bundle", ".p2pbundle")
        if workload_id == "physical_backup":
            return lambda: self._write_unique("backup", ".p2pbackup")
        raise KeyError(workload_id)

    def _cli_status(self) -> object:
        return _run_cli_status(self.root)

    def _write_unique(self, kind: str, suffix: str) -> object:
        self.counter += 1
        output = self.scratch / f"{kind}-{self.counter:06d}{suffix}"
        if kind == "bundle":
            return self.workspace.canonical_bundle_export(output)
        return self.workspace.canonical_memory_backup(output)

    def mutation_operation(
        self, sample_number: int
    ) -> tuple[Callable[[], object], Callable[[], None]]:
        clone = self.scratch / f"mutation-{sample_number:06d}"
        shutil.copytree(self.root, clone)
        workspace = P2PWorkspace(clone)

        def operation() -> object:
            return workspace.create_proposal_with_operation_key(
                title=f"Benchmark mutation {sample_number:06d}",
                operation_key=f"benchmark-baseline-a-{sample_number:06d}-operation",
                actor="owner",
                problem="Measure one governed multi-entity mutation.",
                proposal="Create a deterministic proposal and receipt.",
                acceptance_criteria=["The mutation is atomic and replay-safe."],
            )

        return operation, lambda: shutil.rmtree(clone)


def _measure(operation: Callable[[], object]) -> float:
    started = perf_counter_ns()
    result = operation()
    elapsed = (perf_counter_ns() - started) / 1_000_000_000
    status = getattr(result, "status", None)
    if status in {"invalid", "failed", "blocked"}:
        raise RuntimeError(f"measured operation returned {status}")
    return elapsed


def run_pilot_profile(
    root: Path,
    scratch: Path,
    *,
    selected: Iterable[str],
    warmups: int,
    repetitions: int,
) -> dict[str, object]:
    operations = PilotOperations(root, scratch)
    results: dict[str, object] = {}

    def no_cleanup() -> None:
        return None

    for workload_id in selected:
        samples: list[float] = []
        total = warmups + repetitions
        for sample_number in range(1, total + 1):
            cleanup: Callable[[], None] = no_cleanup
            if workload_id == "governed_proposal_create":
                operation, cleanup = operations.mutation_operation(sample_number)
            else:
                operation = operations.operation(workload_id)
            try:
                elapsed = _measure(operation)
            finally:
                cleanup()
            if sample_number > warmups:
                samples.append(elapsed)
        results[workload_id] = summarize(samples)
    return results


def _result_status(result: object) -> str:
    status = getattr(result, "status", None)
    if isinstance(status, str):
        return status
    if isinstance(result, dict):
        direct = result.get("status")
        if isinstance(direct, str):
            return direct
        mutation = result.get("mutation")
        if isinstance(mutation, dict) and isinstance(mutation.get("status"), str):
            return str(mutation["status"])
    return "ok"


def _result_diagnostics(result: object) -> dict[str, object]:
    diagnostics: dict[str, object] = {
        "result_type": type(result).__name__,
        "status": _result_status(result),
    }
    for field_name in (
        "archive_sha256",
        "archive_size",
        "semantic_state_digest",
        "source_revision",
        "replayed",
    ):
        value = getattr(result, field_name, None)
        if isinstance(value, (str, int, float, bool)):
            diagnostics[field_name] = value
    return diagnostics


def _rss_snapshot() -> dict[str, int | None]:
    """Return portable best-effort RSS/HWM diagnostics without dependencies."""
    current: int | None = None
    peak: int | None = None
    status = Path("/proc/self/status")
    if status.is_file():
        with contextlib.suppress(OSError, ValueError):
            for line in status.read_text(encoding="utf-8").splitlines():
                if line.startswith("VmRSS:"):
                    current = int(line.split()[1]) * 1024
                elif line.startswith("VmHWM:"):
                    peak = int(line.split()[1]) * 1024
    if platform.system() == "Windows":
        with contextlib.suppress(AttributeError, OSError, ValueError):
            import ctypes
            from ctypes import wintypes

            class ProcessMemoryCounters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            process = ctypes.windll.kernel32.GetCurrentProcess()  # type: ignore[attr-defined]
            if ctypes.windll.psapi.GetProcessMemoryInfo(  # type: ignore[attr-defined]
                process, ctypes.byref(counters), counters.cb
            ):
                current = int(counters.WorkingSetSize)
                peak = int(counters.PeakWorkingSetSize)
    if peak is None:
        with contextlib.suppress(ImportError, OSError, ValueError):
            import resource

            usage = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            # Linux reports KiB; Darwin reports bytes.
            peak = usage if platform.system() == "Darwin" else usage * 1024
    return {"current_bytes": current, "peak_bytes": peak}


@dataclass
class PreparedWorkload:
    operation: Callable[[int], object]
    measurement_root: Path
    cleanup: Callable[[], None]
    logical_operations_per_call: int = 1
    before_measure: Callable[[], None] = lambda: None
    after_measure: Callable[[], None] = lambda: None
    diagnostics: dict[str, object] = dc_field(default_factory=dict)


def _copy_for_sample(source: Path, target: Path) -> Path:
    if target.exists():
        raise RuntimeError(f"benchmark scratch target already exists: {target}")
    shutil.copytree(source, target)
    return target


def _proposal_create(workspace: P2PWorkspace, *, operation_key: str, ordinal: int) -> object:
    return workspace.create_proposal_with_operation_key(
        title=f"Benchmark definitive mutation {ordinal:06d}",
        operation_key=operation_key,
        actor="owner",
        problem="Measure a deterministic governed mutation.",
        proposal="Create a proposal and its receipt through the product facade.",
        acceptance_criteria=["The mutation is atomic and replay-safe."],
    )


def _initialize_benchmark_project(root: Path, variant: str, *, name: str) -> object:
    kwargs: dict[str, object] = {
        "owner": "owner",
        "agent_profile": "generic",
    }
    if variant != "a":
        kwargs["storage_adapter"] = "sqlite" if variant == "c" else "filesystem"
    return P2PWorkspace(root).init_project(name, **kwargs)


def _prepare_definitive_workload(
    root: Path,
    scratch: Path,
    workload_id: str,
    variant: str,
    sample_number: int,
    batch_count: int,
) -> PreparedWorkload:
    if variant not in VARIANT_LABELS:
        raise RuntimeError(f"unsupported benchmark variant: {variant}")
    known = {item.workload_id for item in WORKLOADS}
    if workload_id not in known:
        raise RuntimeError(f"unsupported benchmark workload: {workload_id}")
    single_use = {
        "project_init",
        "bundle_restore",
        "batch_import",
        "concurrent_readers_serialized_writer",
        "crash_recovery",
    }
    if workload_id in single_use and batch_count != 1:
        raise RuntimeError(
            f"workload {workload_id} is one logical scenario and requires batch_count=1"
        )

    scratch.mkdir(parents=True, exist_ok=True)
    workspace = P2PWorkspace(root)
    proposal_ids = tuple(item.proposal_id for item in workspace.proposal_summaries())
    target_proposal = proposal_ids[len(proposal_ids) // 2]
    cleanup_paths: list[Path] = []

    def cleanup() -> None:
        for path in reversed(cleanup_paths):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)

    if workload_id == "project_init":
        target = scratch / f"init-{variant}-{sample_number:06d}"
        cleanup_paths.append(target)

        def initialize(_index: int) -> object:
            return _initialize_benchmark_project(
                target,
                variant,
                name="Definitive benchmark project",
            )

        return PreparedWorkload(initialize, target, cleanup)

    if workload_id == "cli_status_cold_start":
        return PreparedWorkload(lambda _index: _run_cli_status(root), root, cleanup)
    if workload_id == "cold_project_open":
        return PreparedWorkload(lambda _index: P2PWorkspace(root).project_identity(), root, cleanup)
    if workload_id == "warm_proposal_list":
        return PreparedWorkload(lambda _index: workspace.proposal_summaries(), root, cleanup)
    if workload_id == "targeted_decision_read":
        return PreparedWorkload(
            lambda _index: workspace.proposal_decision_status(target_proposal),
            root,
            cleanup,
        )
    if workload_id == "memory_classification":
        return PreparedWorkload(
            lambda _index: workspace.project_memory_classification(), root, cleanup
        )
    if workload_id == "canonical_snapshot":
        return PreparedWorkload(lambda _index: workspace.canonical_memory_snapshot(), root, cleanup)

    if workload_id == "bundle_restore":
        # The frozen scale fixture contains synthetic readiness documents that
        # baseline A/B deliberately accepted for read benchmarks but their
        # restore validator rejects.  Use the same clean-init restore contract
        # on A/B/C rather than silently weakening validation or changing the
        # frozen fixture digest.  The limitation is explicit in diagnostics.
        restore_root = scratch / f"restore-{variant}-{sample_number:06d}"
        cleanup_paths.append(restore_root)
        _initialize_benchmark_project(
            restore_root,
            variant,
            name="Definitive restore benchmark",
        )
        restore_workspace = P2PWorkspace(restore_root)
        restore_bundle = scratch / f"restore-{variant}-{sample_number:06d}.p2pbundle"
        cleanup_paths.append(restore_bundle)
        restore_workspace.canonical_bundle_export(restore_bundle)
        operation_key = f"benchmark-{variant}-{sample_number:06d}-restore-apply"
        preview = restore_workspace.canonical_memory_restore_preview(
            source=restore_bundle,
            operation_key=operation_key,
            actor="owner",
        )

        def restore(_index: int) -> object:
            return restore_workspace.canonical_memory_restore_apply(
                source=restore_bundle,
                operation_key=operation_key,
                actor="owner",
                preview_token=preview.preview_token,
                confirm=True,
            )

        return PreparedWorkload(
            restore,
            restore_root,
            cleanup,
            diagnostics={
                "fixture_scope": "clean-init",
                "changed_entity_count": preview.changed_entity_count,
                "limitation": (
                    "frozen scale fixture is read-valid but baseline A/B restore-validation "
                    "invalid; restore uses the common clean-init contract"
                ),
            },
        )

    if workload_id == "archive_verify":
        source_bundle = scratch / f"source-{variant}-{sample_number:06d}.p2pbundle"
        workspace.canonical_bundle_export(source_bundle)
        cleanup_paths.append(source_bundle)
        return PreparedWorkload(
            lambda _index: workspace.canonical_archive_verify(source_bundle), root, cleanup
        )
    if workload_id == "bundle_export":

        def export_bundle(index: int) -> object:
            output = scratch / (f"bundle-{variant}-{sample_number:06d}-{index:06d}.p2pbundle")
            cleanup_paths.append(output)
            return workspace.canonical_bundle_export(output)

        return PreparedWorkload(export_bundle, root, cleanup)
    if workload_id == "physical_backup":

        def backup(index: int) -> object:
            output = scratch / (f"backup-{variant}-{sample_number:06d}-{index:06d}.p2pbackup")
            cleanup_paths.append(output)
            return workspace.canonical_memory_backup(output)

        return PreparedWorkload(backup, root, cleanup)

    if workload_id == "governed_proposal_create":
        clone = _copy_for_sample(root, scratch / f"mutation-{variant}-{sample_number:06d}")
        cleanup_paths.append(clone)
        mutation_workspace = P2PWorkspace(clone)

        def mutate(index: int) -> object:
            return _proposal_create(
                mutation_workspace,
                operation_key=(f"benchmark-{variant}-{sample_number:06d}-{index:06d}-mutation"),
                ordinal=sample_number * 1000 + index,
            )

        return PreparedWorkload(mutate, clone, cleanup)

    if workload_id == "batch_import":
        clone = _copy_for_sample(root, scratch / f"batch-{variant}-{sample_number:06d}")
        cleanup_paths.append(clone)
        batch_workspace = P2PWorkspace(clone)

        def import_batch(_index: int) -> object:
            results = []
            for ordinal in range(1, 9):
                results.append(
                    _proposal_create(
                        batch_workspace,
                        operation_key=(
                            f"benchmark-{variant}-{sample_number:06d}-batch-{ordinal:02d}"
                        ),
                        ordinal=sample_number * 100 + ordinal,
                    )
                )
            return {
                "status": "applied",
                "created": len(results),
                "result_statuses": [_result_status(item) for item in results],
            }

        return PreparedWorkload(
            import_batch,
            clone,
            cleanup,
            logical_operations_per_call=8,
        )

    if workload_id == "concurrent_readers_serialized_writer":
        clone = _copy_for_sample(root, scratch / f"concurrency-{variant}-{sample_number:06d}")
        control_clone = _copy_for_sample(
            root,
            scratch / f"concurrency-control-{variant}-{sample_number:06d}",
        )
        cleanup_paths.append(clone)
        cleanup_paths.append(control_clone)
        readers = tuple(P2PWorkspace(clone) for _ in range(4))
        writer = P2PWorkspace(clone)
        control_writer = P2PWorkspace(control_clone)
        timing: dict[str, float | str] = {
            "lock_wait_measurement": (
                "writer elapsed time is a conservative upper bound; the public "
                "facade does not expose transaction-lock acquisition separately"
            )
        }

        def release_barrier() -> None:
            timing["barrier_release_ns"] = float(perf_counter_ns())

        barrier = threading.Barrier(6, action=release_barrier)
        executor = ThreadPoolExecutor(max_workers=5)
        futures: list[Future[object]] = []

        def reader_call(reader: P2PWorkspace) -> object:
            barrier.wait(timeout=30)
            return reader.canonical_memory_snapshot()

        def writer_call() -> object:
            barrier.wait(timeout=30)
            started = perf_counter_ns()
            result = _proposal_create(
                writer,
                operation_key=f"benchmark-{variant}-{sample_number:06d}-concurrent-writer",
                ordinal=sample_number,
            )
            elapsed = (perf_counter_ns() - started) / 1_000_000_000
            timing["writer_elapsed_seconds"] = elapsed
            timing["lock_wait_upper_bound_seconds"] = elapsed
            uncontended = float(timing.get("uncontended_writer_seconds", elapsed))
            timing["contention_overhead_estimate_seconds"] = max(0.0, elapsed - uncontended)
            release_ns = float(timing.get("barrier_release_ns", started))
            timing["writer_schedule_delay_seconds"] = max(
                0.0, (started - release_ns) / 1_000_000_000
            )
            return result

        def before_measure() -> None:
            control_started = perf_counter_ns()
            _proposal_create(
                control_writer,
                operation_key=f"benchmark-{variant}-{sample_number:06d}-control-writer",
                ordinal=sample_number,
            )
            timing["uncontended_writer_seconds"] = (
                perf_counter_ns() - control_started
            ) / 1_000_000_000
            futures.extend(executor.submit(reader_call, reader) for reader in readers)
            futures.append(executor.submit(writer_call))

        def concurrent(_index: int) -> object:
            barrier.wait(timeout=30)
            results = [future.result(timeout=60) for future in futures]
            timing.pop("barrier_release_ns", None)
            return {
                "status": "applied",
                "reader_entity_counts": [len(getattr(value, "entities")) for value in results[:4]],
                "writer_status": _result_status(results[4]),
            }

        def after_measure() -> None:
            executor.shutdown(wait=True, cancel_futures=True)

        return PreparedWorkload(
            concurrent,
            clone,
            cleanup,
            before_measure=before_measure,
            after_measure=after_measure,
            diagnostics=timing,
        )

    if workload_id == "crash_recovery":
        clone = _copy_for_sample(root, scratch / f"crash-{variant}-{sample_number:06d}")
        cleanup_paths.append(clone)
        operation_key = f"benchmark-{variant}-{sample_number:06d}-lost-ack"
        proposal_count_before = len(P2PWorkspace(clone).proposal_summaries())
        child = """
import os
import sys
from pathlib import Path
from p2p_engine.storage.filesystem import P2PWorkspace
root = Path(sys.argv[1])
key = sys.argv[2]
P2PWorkspace(root).create_proposal_with_operation_key(
    title='Benchmark abrupt exit',
    operation_key=key,
    actor='owner',
    problem='Verify durable recovery after a lost acknowledgement.',
    proposal='Commit durably and exit without acknowledging the caller.',
    acceptance_criteria=['Reopen preserves exactly one durable mutation.'],
)
os._exit(91)
"""

        def crash_and_reopen(_index: int) -> object:
            completed = subprocess.run(
                [sys.executable, "-c", child, str(clone), operation_key],
                cwd=PRODUCT_ROOT,
                env={
                    **os.environ,
                    "PYTHONPATH": os.pathsep.join((str(PRODUCT_ROOT / "src"), str(PRODUCT_ROOT))),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=120,
            )
            if completed.returncode != 91:
                raise RuntimeError(
                    "abrupt-exit child did not reach the durable-commit boundary: "
                    + (completed.stderr.strip() or str(completed.returncode))
                )
            reopened = P2PWorkspace(clone)
            recovery = reopened.canonical_memory_recovery_status()
            proposal_count_after = len(reopened.proposal_summaries())
            if proposal_count_after != proposal_count_before + 1:
                raise RuntimeError("abrupt-exit reopen did not preserve exactly one mutation")
            try:
                replay = reopened.create_proposal_with_operation_key(
                    title="Benchmark abrupt exit",
                    operation_key=operation_key,
                    actor="owner",
                    problem="Verify durable recovery after a lost acknowledgement.",
                    proposal="Commit durably and exit without acknowledging the caller.",
                    acceptance_criteria=["Reopen preserves exactly one durable mutation."],
                )
            except Exception as exc:
                return {
                    "status": "failed",
                    "child_exit_code": completed.returncode,
                    "recovery_state": recovery.state,
                    "durable_reopen_passed": True,
                    "replay_status": "error",
                    "replay_error_type": type(exc).__name__,
                    "replay_error": str(exc),
                    "proposal_count_before": proposal_count_before,
                    "proposal_count_after": proposal_count_after,
                }
            proposal_count_after_replay = len(reopened.proposal_summaries())
            if _result_status(replay) != "already_applied":
                raise RuntimeError("lost-ack replay did not return already_applied")
            if proposal_count_after_replay != proposal_count_after:
                raise RuntimeError("lost-ack replay duplicated the durable mutation")
            return {
                "status": "recovered",
                "child_exit_code": completed.returncode,
                "recovery_state": recovery.state,
                "replay_status": _result_status(replay),
                "proposal_count_before": proposal_count_before,
                "proposal_count_after": proposal_count_after,
                "proposal_count_after_replay": proposal_count_after_replay,
                "semantic_state_digest": reopened.canonical_memory_snapshot().semantic_state_digest,
            }

        return PreparedWorkload(crash_and_reopen, clone, cleanup)

    raise RuntimeError(f"workload implementation is missing: {workload_id}")


def run_definitive_sample(
    root: Path,
    scratch: Path,
    workload_id: str,
    variant: str,
    sample_number: int,
    batch_count: int,
) -> dict[str, object]:
    """Run one definitive cell sample; all setup/cleanup stays outside its span."""
    if sample_number < 1 or batch_count < 1:
        return {
            "valid": False,
            "workload_id": workload_id,
            "variant": VARIANT_LABELS.get(variant, variant),
            "sample_number": sample_number,
            "batch_count": batch_count,
            "error": "sample_number and batch_count must be positive",
        }
    prepared: PreparedWorkload | None = None
    memory_prepared: PreparedWorkload | None = None
    outcomes: list[object] = []
    elapsed = 0.0
    peak_python = 0
    logical_operations_per_call = 1
    rss_before = _rss_snapshot()
    rss_after = rss_before
    disk_before = directory_size(root / ".p2p") if (root / ".p2p").is_dir() else 0
    disk_after = disk_before
    try:
        prepared = _prepare_definitive_workload(
            root.resolve(),
            scratch.resolve(),
            workload_id,
            variant,
            sample_number,
            batch_count,
        )
        prepared.before_measure()
        logical_operations_per_call = prepared.logical_operations_per_call
        disk_before = (
            directory_size(prepared.measurement_root / ".p2p")
            if (prepared.measurement_root / ".p2p").is_dir()
            else 0
        )
        rss_before = _rss_snapshot()
        started = perf_counter_ns()
        try:
            for index in range(1, batch_count + 1):
                result = prepared.operation(index)
                status = _result_status(result)
                if status in {"invalid", "failed", "blocked"}:
                    raise RuntimeError(f"measured operation returned {status}")
                outcomes.append(result)
        finally:
            elapsed = (perf_counter_ns() - started) / 1_000_000_000
        rss_after = _rss_snapshot()
        disk_after = (
            directory_size(prepared.measurement_root / ".p2p")
            if (prepared.measurement_root / ".p2p").is_dir()
            else 0
        )
        primary_diagnostics = dict(prepared.diagnostics)
        with contextlib.suppress(Exception):
            prepared.after_measure()
        with contextlib.suppress(Exception):
            prepared.cleanup()
        prepared = None

        # The A-only freeze requires memory instrumentation outside the latency
        # span.  Recreate the same scenario and collect Python allocation peak
        # in a separate one-call diagnostic pass. RSS and disk values above are
        # snapshots of the uninstrumented primary pass.
        memory_prepared = _prepare_definitive_workload(
            root.resolve(),
            (scratch.resolve() / "memory-diagnostic"),
            workload_id,
            variant,
            sample_number,
            1,
        )
        memory_prepared.before_measure()
        tracemalloc.start()
        try:
            memory_result = memory_prepared.operation(1)
            memory_status = _result_status(memory_result)
            if memory_status in {"invalid", "failed", "blocked"}:
                raise RuntimeError(f"memory diagnostic operation returned {memory_status}")
        finally:
            _current_python, peak_python = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        logical_count = batch_count * logical_operations_per_call
        return {
            "valid": True,
            "workload_id": workload_id,
            "variant": VARIANT_LABELS[variant],
            "sample_number": sample_number,
            "batch_count": batch_count,
            "logical_operation_count": logical_count,
            "elapsed_seconds": round(elapsed, 9),
            "per_operation_seconds": round(elapsed / logical_count, 9),
            "tracemalloc_peak_bytes": peak_python,
            "rss_before": rss_before,
            "rss_after": rss_after,
            "disk_bytes_before": disk_before,
            "disk_bytes_after": disk_after,
            "disk_bytes_delta": disk_after - disk_before,
            "diagnostics": {
                **primary_diagnostics,
                "results": [_result_diagnostics(result) for result in outcomes],
                "setup_and_cleanup_in_measured_span": False,
                "tracemalloc_separate_diagnostic": True,
                "tracemalloc_diagnostic_batch_count": 1,
                "tracemalloc_result": _result_diagnostics(memory_result),
            },
        }
    except Exception as exc:
        rss_after = _rss_snapshot()
        measurement_root = prepared.measurement_root if prepared is not None else root
        disk_after = (
            directory_size(measurement_root / ".p2p") if (measurement_root / ".p2p").is_dir() else 0
        )
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        return {
            "valid": False,
            "workload_id": workload_id,
            "variant": VARIANT_LABELS.get(variant, variant),
            "sample_number": sample_number,
            "batch_count": batch_count,
            "elapsed_seconds": round(elapsed, 9),
            "rss_before": rss_before,
            "rss_after": rss_after,
            "disk_bytes_before": disk_before,
            "disk_bytes_after": disk_after,
            "disk_bytes_delta": disk_after - disk_before,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        if prepared is not None:
            with contextlib.suppress(Exception):
                prepared.after_measure()
            with contextlib.suppress(Exception):
                prepared.cleanup()
        if memory_prepared is not None:
            with contextlib.suppress(Exception):
                memory_prepared.after_measure()
            with contextlib.suppress(Exception):
                memory_prepared.cleanup()


def run_conformance(root: Path, scratch: Path, variant: str) -> dict[str, object]:
    """Exercise storage-neutral correctness gates without mutating the fixture."""
    evidence: dict[str, object] = {
        "variant": VARIANT_LABELS.get(variant, variant),
        "valid": False,
        "checks": {},
        "errors": [],
    }
    checks = evidence["checks"]
    errors = evidence["errors"]
    assert isinstance(checks, dict) and isinstance(errors, list)
    scratch = scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    receipt_root = scratch / f"conformance-receipt-{variant}"
    atomicity_root = scratch / f"conformance-atomicity-{variant}"
    stale_restore_root = scratch / f"conformance-stale-restore-{variant}"
    port_root = scratch / f"conformance-port-{variant}"
    crash_scratch = scratch / f"conformance-crash-{variant}"
    restore_root = scratch / f"conformance-restore-{variant}"
    bundle = scratch / f"conformance-{variant}.p2pbundle"
    backup = scratch / f"conformance-{variant}.p2pbackup"
    restore_bundle = scratch / f"conformance-restore-{variant}.p2pbundle"
    stale_restore_bundle = scratch / f"conformance-stale-restore-{variant}.p2pbundle"
    migration_backup = scratch / f"conformance-migration-{variant}.p2pbackup"
    try:
        workspace = P2PWorkspace(root)
        identity = workspace.project_identity()
        snapshot = workspace.canonical_memory_snapshot()
        checks["identity"] = {
            "project_uuid": identity.project_uuid.value,
            "matches_snapshot": identity.project_uuid.value == snapshot.project_uuid,
        }
        try:
            revision = workspace.project_state_revision()
        except AttributeError:
            checks["revision"] = {"available": False}
        else:
            checks["revision"] = {
                "available": True,
                "sha256": revision.sha256,
                "matches_snapshot": revision.sha256 == snapshot.semantic_state_digest,
            }

        bundle_result = workspace.canonical_bundle_export(bundle)
        bundle_verify = workspace.canonical_archive_verify(bundle)
        backup_result = workspace.canonical_memory_backup(backup)
        backup_verify = workspace.canonical_archive_verify(backup)
        checks["archives"] = {
            "bundle_status": bundle_verify.status,
            "bundle_digest": bundle_result.archive_sha256,
            "bundle_semantic_digest": bundle_verify.semantic_state_digest,
            "backup_status": backup_verify.status,
            "backup_digest": backup_result.archive_sha256,
            "semantic_match": (
                bundle_verify.semantic_state_digest == snapshot.semantic_state_digest
                and backup_verify.semantic_state_digest == snapshot.semantic_state_digest
            ),
        }

        try:
            _copy_for_sample(root, receipt_root)
            receipt_workspace = P2PWorkspace(receipt_root)
            receipt_key = f"conformance-{variant}-receipt-replay"
            first = _proposal_create(receipt_workspace, operation_key=receipt_key, ordinal=1)
            replay = _proposal_create(receipt_workspace, operation_key=receipt_key, ordinal=1)
            checks["receipt_replay"] = {
                "first_status": _result_status(first),
                "replay_status": _result_status(replay),
                "passed": (
                    _result_status(first) == "applied"
                    and _result_status(replay) == "already_applied"
                ),
            }
        except Exception as exc:
            checks["receipt_replay"] = {
                "passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            errors.append(
                {
                    "check": "receipt_replay",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )

        try:
            _initialize_benchmark_project(
                stale_restore_root,
                variant,
                name="Conformance stale restore project",
            )
            stale_workspace = P2PWorkspace(stale_restore_root)
            stale_workspace.canonical_bundle_export(stale_restore_bundle)
            stale_operation_key = f"conformance-{variant}-stale-restore"
            stale_preview = stale_workspace.canonical_memory_restore_preview(
                source=stale_restore_bundle,
                operation_key=stale_operation_key,
                actor="owner",
            )
            _proposal_create(
                stale_workspace,
                operation_key=f"conformance-{variant}-stale-restore-source-change",
                ordinal=301,
            )
            after_source_change = stale_workspace.canonical_memory_snapshot()
            proposal_count_after_source_change = len(stale_workspace.proposal_summaries())
            stale_error_type = ""
            stale_error = ""
            try:
                stale_workspace.canonical_memory_restore_apply(
                    source=stale_restore_bundle,
                    operation_key=stale_operation_key,
                    actor="owner",
                    preview_token=stale_preview.preview_token,
                    confirm=True,
                )
            except Exception as exc:
                stale_error_type = type(exc).__name__
                stale_error = str(exc)
            reopened_after_stale = P2PWorkspace(stale_restore_root)
            after_rejected_restore = reopened_after_stale.canonical_memory_snapshot()
            recovery_after_stale = reopened_after_stale.canonical_memory_recovery_status()
            checks["stale_restore_revision"] = {
                "error_type": stale_error_type,
                "error": stale_error,
                "recognized_stale_error": (
                    "P2P_STALE_PREVIEW" in stale_error
                    or "P2P_STORAGE_STALE_REVISION" in stale_error
                ),
                "semantic_state_unchanged": (
                    after_rejected_restore.semantic_state_digest
                    == after_source_change.semantic_state_digest
                ),
                "proposal_count_unchanged": (
                    len(reopened_after_stale.proposal_summaries())
                    == proposal_count_after_source_change
                ),
                "recovery_state": recovery_after_stale.state,
                "passed": (
                    bool(stale_error_type)
                    and (
                        "P2P_STALE_PREVIEW" in stale_error
                        or "P2P_STORAGE_STALE_REVISION" in stale_error
                    )
                    and after_rejected_restore.semantic_state_digest
                    == after_source_change.semantic_state_digest
                    and len(reopened_after_stale.proposal_summaries())
                    == proposal_count_after_source_change
                    and recovery_after_stale.state == "clean"
                ),
            }
        except Exception as exc:
            checks["stale_restore_revision"] = {
                "passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            errors.append(
                {
                    "check": "stale_restore_revision",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )

        try:
            _copy_for_sample(root, atomicity_root)
            atomicity_workspace = P2PWorkspace(atomicity_root)
            atomicity_key = f"conformance-{variant}-receipt-conflict"
            first = _proposal_create(
                atomicity_workspace,
                operation_key=atomicity_key,
                ordinal=101,
            )
            after_first = atomicity_workspace.canonical_memory_snapshot()
            proposal_count_after_first = len(atomicity_workspace.proposal_summaries())
            conflict_type = ""
            conflict_message = ""
            try:
                _proposal_create(
                    atomicity_workspace,
                    operation_key=atomicity_key,
                    ordinal=102,
                )
            except Exception as exc:
                conflict_type = type(exc).__name__
                conflict_message = str(exc)
            after_conflict = P2PWorkspace(atomicity_root).canonical_memory_snapshot()
            proposal_count_after_conflict = len(P2PWorkspace(atomicity_root).proposal_summaries())
            checks["failed_mutation_atomicity"] = {
                "first_status": _result_status(first),
                "conflict_error_type": conflict_type,
                "conflict_error": conflict_message,
                "semantic_state_unchanged": (
                    after_conflict.semantic_state_digest == after_first.semantic_state_digest
                ),
                "proposal_count_unchanged": (
                    proposal_count_after_conflict == proposal_count_after_first
                ),
                "passed": (
                    _result_status(first) == "applied"
                    and bool(conflict_type)
                    and after_conflict.semantic_state_digest == after_first.semantic_state_digest
                    and proposal_count_after_conflict == proposal_count_after_first
                ),
            }
        except Exception as exc:
            checks["failed_mutation_atomicity"] = {
                "passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            errors.append(
                {
                    "check": "failed_mutation_atomicity",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )

        if variant == "a":
            checks["storage_port_transaction"] = {
                "available": False,
                "passed": True,
                "reason": "baseline A predates the storage-port contract",
            }
            checks["migration_readiness"] = {
                "available": False,
                "passed": True,
                "reason": "baseline A has no backend schema migration port",
            }
        else:
            try:
                from p2p_engine.core.project_state_storage import ProjectStateMutation

                _copy_for_sample(root, port_root)
                port_workspace = P2PWorkspace(port_root)
                before_snapshot = port_workspace.canonical_memory_snapshot()
                before_revision = port_workspace.project_state_revision()
                rollback = port_workspace.project_state_unit_of_work()
                rollback.stage(
                    ProjectStateMutation(
                        operation_id=f"conformance-{variant}-rollback",
                        actor="owner",
                        expected_revision=before_revision,
                        target=before_snapshot,
                    )
                )
                rollback.rollback()
                rollback_unchanged = port_workspace.project_state_revision() == before_revision

                _proposal_create(
                    port_workspace,
                    operation_key=f"conformance-{variant}-stale-source-change",
                    ordinal=201,
                )
                changed_snapshot = port_workspace.canonical_memory_snapshot()
                stale_error_code = ""
                stale_error_type = ""
                try:
                    stale = port_workspace.project_state_unit_of_work()
                    stale.stage(
                        ProjectStateMutation(
                            operation_id=f"conformance-{variant}-stale",
                            actor="owner",
                            expected_revision=before_revision,
                            target=before_snapshot,
                        )
                    )
                except Exception as exc:
                    stale_error_type = type(exc).__name__
                    code = getattr(exc, "code", "")
                    stale_error_code = str(getattr(code, "value", code))
                after_stale = P2PWorkspace(port_root).canonical_memory_snapshot()
                checks["storage_port_transaction"] = {
                    "available": True,
                    "rollback_unchanged": rollback_unchanged,
                    "stale_error_type": stale_error_type,
                    "stale_error_code": stale_error_code,
                    "failed_stale_write_unchanged": (
                        after_stale.semantic_state_digest == changed_snapshot.semantic_state_digest
                    ),
                    "passed": (
                        rollback_unchanged
                        and stale_error_code == "P2P_STORAGE_STALE_REVISION"
                        and after_stale.semantic_state_digest
                        == changed_snapshot.semantic_state_digest
                    ),
                }

                migration = port_workspace.adapter.migrations
                schema_version = migration.schema_version()
                verifies_current = True
                verify_current = getattr(migration, "verify_current", None)
                if callable(verify_current):
                    verify_current()
                can_migrate_current = migration.can_migrate_from(schema_version)
                can_migrate_preversioned = migration.can_migrate_from(0) if variant == "c" else None
                migration_check: dict[str, object] = {
                    "available": True,
                    "schema_version": schema_version,
                    "can_migrate_current": can_migrate_current,
                    "can_migrate_preversioned": can_migrate_preversioned,
                    "verifies_current": verifies_current,
                    "passed": (
                        schema_version >= 1
                        and can_migrate_current
                        and (variant != "c" or can_migrate_preversioned is True)
                    ),
                }
                if variant == "c":
                    import sqlite3

                    from p2p_engine.storage.sqlite_recovery import (
                        SQLiteRecoveryCoordinator,
                    )
                    from p2p_engine.storage.sqlite_schema import (
                        SQLITE_DATABASE_PATH,
                        SQLITE_MAINTENANCE_MARKER,
                    )

                    before_migration = migration.repository.snapshot()
                    with sqlite3.connect(port_root / SQLITE_DATABASE_PATH) as connection:
                        connection.execute("DELETE FROM schema_migrations")
                        connection.execute("PRAGMA user_version = 0")

                    def interrupt_after_commit(stage: str) -> None:
                        if stage == "after_migration_commit":
                            raise OSError("injected after_migration_commit")

                    interrupted = False
                    try:
                        migration.migrate_to_current(
                            backup_path=migration_backup,
                            failure_injector=interrupt_after_commit,
                        )
                    except OSError as exc:
                        interrupted = str(exc) == "injected after_migration_commit"
                    committed_version = migration.schema_version()
                    marker_after_interrupt = (port_root / SQLITE_MAINTENANCE_MARKER).is_file()
                    recovery = SQLiteRecoveryCoordinator(port_root)
                    recovery_status = recovery.status()
                    recovered = recovery.apply(
                        recovery_id=recovery_status.recovery_id,
                        recovery_token=recovery_status.recovery_token,
                        actor="owner",
                        action="rollback",
                        confirm=True,
                    )
                    rolled_back_version = migration.schema_version()
                    retried = migration.migrate_to_current(backup_path=migration_backup)
                    after_migration = migration.repository.snapshot()
                    migration_check.update(
                        {
                            "known_path": "preversioned-0-to-current",
                            "interrupted_after_commit": interrupted,
                            "committed_version_before_rollback": committed_version,
                            "marker_after_interrupt": marker_after_interrupt,
                            "recovery_status": recovered.status,
                            "rolled_back_version": rolled_back_version,
                            "retry_status": retried,
                            "integrity_issues": list(migration.repository.integrity_check()),
                            "semantic_state_unchanged": (
                                after_migration.semantic_state_digest
                                == before_migration.semantic_state_digest
                            ),
                            "maintenance_marker_removed": not (
                                port_root / SQLITE_MAINTENANCE_MARKER
                            ).exists(),
                        }
                    )
                    migration_check["passed"] = bool(
                        migration_check["passed"]
                        and interrupted
                        and committed_version == schema_version
                        and marker_after_interrupt
                        and recovered.status == "rolled_back"
                        and rolled_back_version == 0
                        and retried == "migrated"
                        and not migration_check["integrity_issues"]
                        and migration_check["semantic_state_unchanged"]
                        and migration_check["maintenance_marker_removed"]
                    )
                checks["migration_readiness"] = migration_check
            except Exception as exc:
                checks["storage_port_transaction"] = {
                    "available": True,
                    "passed": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                checks.setdefault(
                    "migration_readiness",
                    {
                        "available": True,
                        "passed": False,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
                errors.append(
                    {
                        "check": "storage_port_transaction",
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
                )

        crash: PreparedWorkload | None = None
        try:
            crash = _prepare_definitive_workload(
                root,
                crash_scratch,
                "crash_recovery",
                variant,
                sample_number=901,
                batch_count=1,
            )
            crash.before_measure()
            crash_result = crash.operation(1)
            assert isinstance(crash_result, dict)
            checks["abrupt_exit_recovery"] = {
                **crash_result,
                "passed": (
                    crash_result.get("status") == "recovered"
                    and crash_result.get("child_exit_code") == 91
                    and crash_result.get("recovery_state") == "clean"
                    and crash_result.get("replay_status") == "already_applied"
                    and int(crash_result.get("proposal_count_after", 0))
                    == int(crash_result.get("proposal_count_before", 0)) + 1
                ),
                "limitation": (
                    "commit followed by os._exit verifies durable reopen after a lost "
                    "acknowledgement; no common A/B/C hook exists for a deterministic "
                    "mid-commit kill"
                ),
            }
        except Exception as exc:
            checks["abrupt_exit_recovery"] = {
                "passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            errors.append(
                {
                    "check": "abrupt_exit_recovery",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )
        finally:
            if crash is not None:
                with contextlib.suppress(Exception):
                    crash.after_measure()
                with contextlib.suppress(Exception):
                    crash.cleanup()

        try:
            _initialize_benchmark_project(
                restore_root,
                variant,
                name="Conformance restore project",
            )
            restore_workspace = P2PWorkspace(restore_root)
            restore_before = restore_workspace.canonical_memory_snapshot()
            restore_workspace.canonical_bundle_export(restore_bundle)
            restore_key = f"conformance-{variant}-restore-apply"
            preview = restore_workspace.canonical_memory_restore_preview(
                source=restore_bundle,
                operation_key=restore_key,
                actor="owner",
            )
            restored = restore_workspace.canonical_memory_restore_apply(
                source=restore_bundle,
                operation_key=restore_key,
                actor="owner",
                preview_token=preview.preview_token,
                confirm=True,
            )
            recovery = restore_workspace.canonical_memory_recovery_status()
            checks["restore_recovery"] = {
                "restore_status": restored.status,
                "semantic_state_digest": restored.semantic_state_digest,
                "semantic_match": restored.semantic_state_digest
                == restore_before.semantic_state_digest,
                "recovery_state": recovery.state,
                "fixture_scope": "clean-init",
                "changed_entity_count": preview.changed_entity_count,
                "limitation": (
                    "frozen scale fixture is not accepted by baseline A/B restore validation"
                ),
                "passed": (
                    restored.status == "applied"
                    and restored.semantic_state_digest == restore_before.semantic_state_digest
                    and recovery.state == "clean"
                ),
            }
        except Exception as exc:
            checks["restore_recovery"] = {
                "passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            errors.append(
                {
                    "check": "restore_recovery",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )
        required = [
            bool(checks["identity"]["matches_snapshot"]),
            bool(checks["archives"]["semantic_match"]),
            bool(checks["receipt_replay"]["passed"]),
            bool(checks["failed_mutation_atomicity"]["passed"]),
            bool(checks["stale_restore_revision"]["passed"]),
            bool(checks["storage_port_transaction"]["passed"]),
            bool(checks["migration_readiness"]["passed"]),
            bool(checks["abrupt_exit_recovery"]["passed"]),
            bool(checks["restore_recovery"]["passed"]),
        ]
        revision_check = checks["revision"]
        if revision_check.get("available"):
            required.append(bool(revision_check.get("matches_snapshot")))
        evidence["valid"] = all(required)
        evidence["semantic_state_digest"] = snapshot.semantic_state_digest
    except Exception as exc:
        errors.append({"type": type(exc).__name__, "message": str(exc)})
    finally:
        shutil.rmtree(receipt_root, ignore_errors=True)
        shutil.rmtree(atomicity_root, ignore_errors=True)
        shutil.rmtree(stale_restore_root, ignore_errors=True)
        shutil.rmtree(port_root, ignore_errors=True)
        shutil.rmtree(crash_scratch, ignore_errors=True)
        shutil.rmtree(restore_root, ignore_errors=True)
        bundle.unlink(missing_ok=True)
        backup.unlink(missing_ok=True)
        restore_bundle.unlink(missing_ok=True)
        stale_restore_bundle.unlink(missing_ok=True)
        migration_backup.unlink(missing_ok=True)
    return evidence


def _agent_artifact_paths(root: Path) -> tuple[Path, ...]:
    paths = {
        Path("AGENTS.md"),
        Path("P2P-SETUP.md"),
        Path(".p2p/agent-policy.yml"),
        Path(".p2p/agent-integrations.yml"),
    }
    agents = root / ".agents"
    if agents.is_dir():
        paths.update(path.relative_to(root) for path in agents.rglob("*") if path.is_file())
    return tuple(sorted(path for path in paths if (root / path).is_file()))


def _normalize_agent_artifact(content: bytes, roots: tuple[Path, ...], suffix: str) -> bytes:
    text = content.decode("utf-8").replace("\r\n", "\n")
    for root in roots:
        variants = {str(root), root.as_posix(), str(root).replace("\\", "/")}
        for value in variants:
            text = text.replace(value, "<PROJECT_ROOT>")
    if suffix in {".yml", ".yaml"}:
        import yaml

        return _canonical_json(yaml.safe_load(text))
    return text.encode("utf-8")


def compare_clean_agent_artifacts(parent: Path) -> dict[str, object]:
    """Compare independent filesystem/SQLite init outputs semantically."""
    parent = parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="p2p-agent-equivalence-", dir=parent))
    filesystem_root = temporary / "filesystem"
    sqlite_root = temporary / "sqlite"
    result: dict[str, object] = {
        "valid": False,
        "differences": [],
        "backend_leaks": [],
        "artifacts": {},
    }
    try:
        common = {
            "owner": "owner",
            "agent_profile": "codex",
        }
        P2PWorkspace(filesystem_root).init_project(
            "Benchmark agent equivalence",
            storage_adapter="filesystem",
            **common,
        )
        P2PWorkspace(sqlite_root).init_project(
            "Benchmark agent equivalence",
            storage_adapter="sqlite",
            **common,
        )
        filesystem_paths = _agent_artifact_paths(filesystem_root)
        sqlite_paths = _agent_artifact_paths(sqlite_root)
        differences: list[str] = result["differences"]  # type: ignore[assignment]
        leaks: list[dict[str, object]] = result["backend_leaks"]  # type: ignore[assignment]
        artifacts: dict[str, object] = result["artifacts"]  # type: ignore[assignment]
        if filesystem_paths != sqlite_paths:
            missing_fs = sorted(
                path.as_posix() for path in set(sqlite_paths) - set(filesystem_paths)
            )
            missing_sqlite = sorted(
                path.as_posix() for path in set(filesystem_paths) - set(sqlite_paths)
            )
            differences.extend(
                [f"missing-filesystem:{item}" for item in missing_fs]
                + [f"missing-sqlite:{item}" for item in missing_sqlite]
            )
        leak_pattern = re.compile(
            r"(?:\.p2p/local/(?:project\.sqlite3|storage\.yml))|"
            r"(?:storage[_ -]?adapter\s*[:=]\s*(?:sqlite|filesystem))|"
            r"(?:adapter\s*:\s*(?:sqlite|filesystem))",
            re.IGNORECASE,
        )
        for relative in sorted(set(filesystem_paths) & set(sqlite_paths)):
            left_raw = (filesystem_root / relative).read_bytes()
            right_raw = (sqlite_root / relative).read_bytes()
            left = _normalize_agent_artifact(
                left_raw, (filesystem_root, sqlite_root), relative.suffix
            )
            right = _normalize_agent_artifact(
                right_raw, (filesystem_root, sqlite_root), relative.suffix
            )
            left_digest = _sha256_bytes(left)
            right_digest = _sha256_bytes(right)
            artifacts[relative.as_posix()] = {
                "filesystem_sha256": left_digest,
                "sqlite_sha256": right_digest,
                "equivalent": left_digest == right_digest,
            }
            if left_digest != right_digest:
                differences.append(relative.as_posix())
            for backend, raw in (("filesystem", left_raw), ("sqlite", right_raw)):
                decoded = raw.decode("utf-8", errors="replace")
                for match in leak_pattern.finditer(decoded):
                    leaks.append(
                        {
                            "backend": backend,
                            "path": relative.as_posix(),
                            "match": match.group(0),
                        }
                    )
        result["valid"] = not differences and not leaks
        result["filesystem_artifact_count"] = len(filesystem_paths)
        result["sqlite_artifact_count"] = len(sqlite_paths)
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
    return result


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=PRODUCT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(arguments)} failed")
    return completed.stdout.strip()


def _product_source_digest() -> str:
    # Hash immutable product inputs only. Importing a candidate may create
    # ignored ``__pycache__`` files; including them would make provenance vary
    # with execution order and Python version.
    candidates = [
        PRODUCT_ROOT / relative
        for relative in _git("ls-files", "--", "pyproject.toml", "uv.lock", "src").splitlines()
    ]
    digest = hashlib.sha256()
    for path in candidates:
        if not path.is_file():
            continue
        relative = path.relative_to(PRODUCT_ROOT).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def verify_baseline(
    expected_revision: str,
    *,
    variant: str = "a",
    allow_dirty_product: bool = False,
) -> dict[str, object]:
    if variant not in VARIANT_LABELS:
        raise RuntimeError(f"unsupported benchmark variant: {variant}")
    revision = _git("rev-parse", "HEAD")
    if revision != expected_revision:
        raise RuntimeError(
            f"baseline revision mismatch: expected {expected_revision}, observed {revision}"
        )
    changed_product = _git("status", "--porcelain", "--", "src", "pyproject.toml", "uv.lock")
    if changed_product and not allow_dirty_product:
        raise RuntimeError("baseline product source is dirty; pilot is invalid")
    expected_module = (PRODUCT_ROOT / "src/p2p_engine/__init__.py").resolve()
    actual_module = Path(p2p_engine.__file__).resolve()
    if actual_module != expected_module:
        raise RuntimeError(f"benchmark imported {actual_module}, expected {expected_module}")
    return {
        "variant": VARIANT_LABELS[variant],
        "git_revision": revision,
        "product_source_digest": _product_source_digest(),
        "product_source_clean": not bool(changed_product),
        "product_source_status": changed_product.splitlines(),
        "module_path": actual_module.as_posix(),
        "product_root": PRODUCT_ROOT.as_posix(),
        "harness_root": HARNESS_ROOT.as_posix(),
        "harness_sha256": _sha256_bytes(Path(__file__).resolve().read_bytes()),
        "package_version": getattr(p2p_engine, "__version__", None),
    }


def _filesystem_type(path: Path) -> str:
    resolved = path.resolve()
    system = platform.system()
    commands: list[list[str]] = []
    if system == "Linux":
        commands.append(["findmnt", "-n", "-o", "FSTYPE", "-T", str(resolved)])
        commands.append(["stat", "-f", "-c", "%T", str(resolved)])
    elif system == "Darwin":
        commands.append(["stat", "-f", "%T", str(resolved)])
    for command in commands:
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            continue
        lines = completed.stdout.splitlines()
        if completed.returncode == 0 and lines and lines[-1].strip():
            return lines[-1].strip().lower()
    if system == "Windows":
        try:
            import ctypes

            volume = ctypes.create_unicode_buffer(261)
            filesystem = ctypes.create_unicode_buffer(261)
            root = Path(resolved.anchor or resolved.drive + "\\")
            succeeded = ctypes.windll.kernel32.GetVolumeInformationW(  # type: ignore[attr-defined]
                str(root),
                volume,
                len(volume),
                None,
                None,
                None,
                filesystem,
                len(filesystem),
            )
            if succeeded and filesystem.value:
                return filesystem.value.lower()
        except (AttributeError, OSError, ValueError):
            pass
    return "unknown"


def environment_record(temporary_parent: Path) -> dict[str, object]:
    cpu = platform.processor().strip() or "unknown"
    cpu_count = os.cpu_count()
    memory_bytes: int | None = None
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                memory_bytes = int(line.split()[1]) * 1024
                break
    cpuinfo = Path("/proc/cpuinfo")
    if cpu == "unknown" and cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": cpu,
        "logical_cpu_count": cpu_count,
        "memory_bytes": memory_bytes,
        "python_executable": Path(sys.executable).resolve().as_posix(),
        "python_version": platform.python_version(),
        "filesystem_type": _filesystem_type(temporary_parent),
        "temporary_parent": temporary_parent.as_posix(),
        "pid": os.getpid(),
    }


def workload_manifest() -> list[dict[str, object]]:
    return [item.__dict__ for item in WORKLOADS]


def run_pilot(
    *,
    expected_revision: str,
    profiles: Iterable[str],
    selected_workloads: Iterable[str],
    seed: int,
    warmups: int,
    repetitions: int,
    temporary_parent: Path,
    allow_memory_filesystem: bool = False,
    variant: str = "a",
    allow_dirty_product: bool = False,
) -> dict[str, object]:
    if variant not in VARIANT_LABELS:
        raise RuntimeError("only frozen variants A, B, and C are enabled")
    if allow_dirty_product and variant == "a":
        raise RuntimeError(
            "dirty product measurement is permitted only for provisional B or C"
        )
    baseline = verify_baseline(
        expected_revision,
        variant=variant,
        allow_dirty_product=allow_dirty_product,
    )
    environment = environment_record(temporary_parent)
    if environment["filesystem_type"] in {"tmpfs", "ramfs"} and not allow_memory_filesystem:
        raise RuntimeError(
            "temporary parent uses an in-memory filesystem; choose the product disk "
            "or pass --allow-memory-filesystem for a non-gating smoke run"
        )
    parent = Path(tempfile.mkdtemp(prefix=f"p2p-baseline-{variant}-pilot-", dir=temporary_parent))
    try:
        datasets: dict[str, object] = {}
        measurements: dict[str, object] = {}
        for profile_name in profiles:
            profile = DATASET_PROFILES[profile_name]
            root = parent / "datasets" / profile_name
            scratch = parent / "scratch" / profile_name
            scratch.mkdir(parents=True, exist_ok=True)
            datasets[profile_name] = build_dataset(
                root,
                profile,
                seed=seed,
                variant=variant,
            )
            measurements[profile_name] = run_pilot_profile(
                root,
                scratch,
                selected=selected_workloads,
                warmups=warmups,
                repetitions=repetitions,
            )
        return {
            "contract": HARNESS_CONTRACT,
            "run_kind": (
                "baseline-a-pilot"
                if variant == "a"
                else "baseline-b-pilot"
                if variant == "b" and baseline["product_source_clean"]
                else "baseline-b-provisional"
                if variant == "b"
                else "candidate-c-pilot"
                if baseline["product_source_clean"]
                else "candidate-c-provisional"
            ),
            "valid": True,
            "gate_eligible": bool(baseline["product_source_clean"]),
            "baseline": baseline,
            "environment": environment,
            "dataset_version": DATASET_VERSION,
            "workload_version": WORKLOAD_VERSION,
            "seed": seed,
            "warmups": warmups,
            "repetitions": repetitions,
            "cache_policy": {
                "os_page_cache": "not purged; comparisons are within-platform",
                "cold_project_open": "fresh P2PWorkspace object only",
                "warm_operations": "workspace reused and warm-up samples discarded",
            },
            "datasets": datasets,
            "workload_catalog": workload_manifest(),
            "pilot_workloads": list(selected_workloads),
            "definitive_batch_counts": DEFINITIVE_BATCH_COUNTS,
            "measurements": measurements,
            "excluded_metrics": ["complete_test_suite_duration", "test_count"],
        }
    finally:
        shutil.rmtree(parent)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run frozen variants A/B or SQLite candidate C.")
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--variant", choices=("a", "b", "c"), default="a")
    parser.add_argument(
        "--profile",
        action="append",
        choices=tuple(DATASET_PROFILES),
        dest="profiles",
        help="Repeat to select profiles; defaults to small, medium, and large.",
    )
    parser.add_argument(
        "--allow-dirty-product",
        action="store_true",
        help="Record a clearly non-gating provisional B or C run before the owner commit.",
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=PILOT_WORKLOAD_IDS,
        dest="workloads",
        help="Repeat to select pilot workloads.",
    )
    parser.add_argument("--seed", type=int, default=2501)
    parser.add_argument("--warmups", type=int, default=3)
    parser.add_argument("--repetitions", type=int, default=15)
    parser.add_argument("--temporary-parent", type=Path, default=Path("/tmp"))
    parser.add_argument(
        "--allow-memory-filesystem",
        action="store_true",
        help="Allow tmpfs/ramfs only for a non-gating smoke run.",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.warmups < 0:
        raise SystemExit("--warmups cannot be negative")
    if args.repetitions < 3:
        raise SystemExit("--repetitions must be at least 3")
    if not args.temporary_parent.is_dir():
        raise SystemExit("--temporary-parent must be an existing directory")
    profiles = tuple(args.profiles or ("small", "medium", "large"))
    selected = tuple(args.workloads or PILOT_WORKLOAD_IDS)
    try:
        result = run_pilot(
            expected_revision=args.expected_revision,
            profiles=profiles,
            selected_workloads=selected,
            seed=args.seed,
            warmups=args.warmups,
            repetitions=args.repetitions,
            temporary_parent=args.temporary_parent.resolve(),
            allow_memory_filesystem=args.allow_memory_filesystem,
            variant=args.variant,
            allow_dirty_product=args.allow_dirty_product,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"baseline-{args.variant.upper()} pilot invalid: {exc}", file=sys.stderr)
        return 2
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
        temporary.write_text(encoded, encoding="utf-8")
        os.replace(temporary, output)
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

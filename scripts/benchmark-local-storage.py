#!/usr/bin/env python3
"""Reproducible local-storage benchmark harness.

Step 25A froze variant A. Step 26 adds variant B without changing the dataset,
workload, batching, noise or decision contracts. Candidate C remains disabled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from uuid import UUID, uuid5

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT / "src"))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(1, str(SOURCE_ROOT))

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
DATASET_NAMESPACE = UUID("9491fe2b-4be8-5ea8-a71b-c40269177d08")


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
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
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


def directory_size(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def build_dataset(root: Path, profile: DatasetProfile, *, seed: int) -> dict[str, object]:
    built = build_scale_workspace(
        root,
        proposal_count=profile.proposal_count,
        schema_version=4,
        rich_proposals=profile.rich_proposals,
    )
    project_uuid = _stabilize_identity(root, seed=seed, profile=profile.name)
    _add_dataset_documents(root, profile, seed=seed)
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
        "profile": profile.name,
        "seed": seed,
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


class PilotOperations:
    def __init__(self, root: Path, scratch: Path) -> None:
        self.root = root
        self.scratch = scratch
        self.workspace = P2PWorkspace(root)
        proposal_ids = tuple(
            item.proposal_id for item in self.workspace.proposal_summaries()
        )
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
        executable = SOURCE_ROOT / ".venv/bin/p2p"
        completed = subprocess.run(
            [str(executable), "status", "--root", str(self.root)],
            cwd=SOURCE_ROOT,
            env={
                **os.environ,
                "PYTHONPATH": str(SOURCE_ROOT / "src"),
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

    def _write_unique(self, kind: str, suffix: str) -> object:
        self.counter += 1
        output = self.scratch / f"{kind}-{self.counter:06d}{suffix}"
        if kind == "bundle":
            return self.workspace.canonical_bundle_export(output)
        return self.workspace.canonical_memory_backup(output)

    def mutation_operation(self, sample_number: int) -> tuple[Callable[[], object], Callable[[], None]]:
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


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=SOURCE_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(arguments)} failed")
    return completed.stdout.strip()


def _product_source_digest() -> str:
    candidates = [SOURCE_ROOT / "pyproject.toml", SOURCE_ROOT / "uv.lock"]
    candidates.extend(sorted((SOURCE_ROOT / "src").rglob("*")))
    digest = hashlib.sha256()
    for path in candidates:
        if not path.is_file():
            continue
        relative = path.relative_to(SOURCE_ROOT).as_posix().encode()
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
    revision = _git("rev-parse", "HEAD")
    if revision != expected_revision:
        raise RuntimeError(
            f"baseline revision mismatch: expected {expected_revision}, observed {revision}"
        )
    changed_product = _git("status", "--porcelain", "--", "src", "pyproject.toml", "uv.lock")
    if changed_product and not allow_dirty_product:
        raise RuntimeError("baseline product source is dirty; pilot is invalid")
    expected_module = (SOURCE_ROOT / "src/p2p_engine/__init__.py").resolve()
    actual_module = Path(p2p_engine.__file__).resolve()
    if actual_module != expected_module:
        raise RuntimeError(f"benchmark imported {actual_module}, expected {expected_module}")
    return {
        "variant": BASELINE_A_VARIANT if variant == "a" else BASELINE_B_VARIANT,
        "git_revision": revision,
        "product_source_digest": _product_source_digest(),
        "product_source_clean": not bool(changed_product),
        "product_source_status": changed_product.splitlines(),
        "module_path": actual_module.as_posix(),
        "package_version": getattr(p2p_engine, "__version__", None),
    }


def _filesystem_type(path: Path) -> str:
    completed = subprocess.run(
        ["findmnt", "-n", "-o", "FSTYPE", "-T", str(path.resolve())],
        check=False,
        capture_output=True,
        text=True,
    )
    lines = completed.stdout.splitlines()
    return lines[-1].strip() if completed.returncode == 0 and lines else "unknown"


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
    if variant not in {"a", "b"}:
        raise RuntimeError("only frozen variants A and B are enabled")
    if allow_dirty_product and variant != "b":
        raise RuntimeError("dirty product measurement is permitted only for provisional B")
    baseline = verify_baseline(
        expected_revision,
        variant=variant,
        allow_dirty_product=allow_dirty_product,
    )
    environment = environment_record(temporary_parent)
    if (
        environment["filesystem_type"] in {"tmpfs", "ramfs"}
        and not allow_memory_filesystem
    ):
        raise RuntimeError(
            "temporary parent uses an in-memory filesystem; choose the product disk "
            "or pass --allow-memory-filesystem for a non-gating smoke run"
        )
    parent = Path(
        tempfile.mkdtemp(prefix=f"p2p-baseline-{variant}-pilot-", dir=temporary_parent)
    )
    try:
        datasets: dict[str, object] = {}
        measurements: dict[str, object] = {}
        for profile_name in profiles:
            profile = DATASET_PROFILES[profile_name]
            root = parent / "datasets" / profile_name
            scratch = parent / "scratch" / profile_name
            scratch.mkdir(parents=True, exist_ok=True)
            datasets[profile_name] = build_dataset(root, profile, seed=seed)
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
                if baseline["product_source_clean"]
                else "baseline-b-provisional"
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
    parser = argparse.ArgumentParser(
        description="Run frozen filesystem variant A or post-port variant B."
    )
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--variant", choices=("a", "b"), default="a")
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
        help="Record a clearly non-gating provisional B run before the owner commit.",
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

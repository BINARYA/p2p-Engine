from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/benchmark-local-storage.py"


def _module():
    spec = importlib.util.spec_from_file_location("benchmark_local_storage", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_dataset_is_deterministic_and_covers_frozen_categories(tmp_path: Path) -> None:
    module = _module()
    first = module.build_dataset(
        tmp_path / "first", module.DATASET_PROFILES["small"], seed=2501
    )
    second = module.build_dataset(
        tmp_path / "second", module.DATASET_PROFILES["small"], seed=2501
    )

    assert first["logical_fixture_digest"] == second["logical_fixture_digest"]
    assert first["semantic_state_digest"] == second["semantic_state_digest"]
    assert first["project_uuid"] == second["project_uuid"]
    assert first["proposal_count"] == 8
    assert first["history_records"] == 16
    assert first["blob_count"] == 2
    assert first["relation_count"] == 2
    assert first["logical_fixture_digest"] == module.FROZEN_DATASET_DIGESTS["small"][
        "logical_fixture_digest"
    ]


def test_pilot_is_machine_readable_and_never_exposes_b_or_c(tmp_path: Path) -> None:
    module = _module()
    revision = module._git("rev-parse", "HEAD")
    result = module.run_pilot(
        expected_revision=revision,
        profiles=("small",),
        selected_workloads=("cold_project_open", "governed_proposal_create"),
        seed=2501,
        warmups=0,
        repetitions=3,
        temporary_parent=tmp_path,
        allow_memory_filesystem=True,
    )

    assert result["contract"] == "p2p-local-backend-benchmark/v1"
    assert result["run_kind"] == "baseline-a-pilot"
    assert result["baseline"]["variant"] == "A-filesystem-before-storage-ports"
    assert set(result["measurements"]) == {"small"}
    assert set(result["measurements"]["small"]) == {
        "cold_project_open",
        "governed_proposal_create",
    }
    assert len(
        result["measurements"]["small"]["cold_project_open"]["samples_seconds"]
    ) == 3
    assert all(
        variant not in str(result)
        for variant in ("B-filesystem-behind-storage-ports", "C-sqlite-behind-storage-ports")
    )


def test_baseline_revision_mismatch_is_rejected() -> None:
    module = _module()
    try:
        module.verify_baseline("0" * 40)
    except RuntimeError as exc:
        assert "baseline revision mismatch" in str(exc)
    else:
        raise AssertionError("mismatched baseline revision was accepted")


def test_workload_catalog_freezes_required_families() -> None:
    module = _module()
    families = {item.family for item in module.WORKLOADS}
    assert {
        "open",
        "init",
        "startup",
        "common_read",
        "targeted_query",
        "relation_traversal_and_snapshot",
        "readiness_and_classification",
        "multi_entity_mutation",
        "snapshot_and_serialization",
        "integrity_validation",
        "backup",
        "restore",
        "batch_import",
        "concurrency",
        "failure_recovery",
    } <= families
    assert module.PILOT_WORKLOAD_IDS
    assert all(
        next(item for item in module.WORKLOADS if item.workload_id == workload_id).pilot
        for workload_id in module.PILOT_WORKLOAD_IDS
    )

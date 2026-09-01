from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

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
    first = module.build_dataset(tmp_path / "first", module.DATASET_PROFILES["small"], seed=2501)
    second = module.build_dataset(tmp_path / "second", module.DATASET_PROFILES["small"], seed=2501)

    assert first["logical_fixture_digest"] == second["logical_fixture_digest"]
    assert first["semantic_state_digest"] == second["semantic_state_digest"]
    assert first["project_uuid"] == second["project_uuid"]
    assert first["proposal_count"] == 8
    assert first["history_records"] == 16
    assert first["blob_count"] == 2
    assert first["relation_count"] == 2
    assert (
        first["logical_fixture_digest"]
        == module.FROZEN_DATASET_DIGESTS["small"]["logical_fixture_digest"]
    )


def test_dataset_date_normalization_does_not_touch_blob_bytes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    document = tmp_path / ".p2p/project.yml"
    blob = tmp_path / ".p2p/blobs/sha256/aa/aa"
    document.parent.mkdir(parents=True)
    blob.parent.mkdir(parents=True)
    document.write_text("initialized_at: 2099-07-12\n", encoding="utf-8")
    blob.write_bytes(b"binary-2099-07-12-payload")

    class ObservedDate:
        @staticmethod
        def today():
            class Value:
                @staticmethod
                def isoformat() -> str:
                    return "2099-07-12"

            return Value()

    monkeypatch.setattr(module, "date", ObservedDate)
    module._stabilize_dataset_dates(tmp_path)

    assert module.FROZEN_DATASET_DATE in document.read_text(encoding="utf-8")
    assert blob.read_bytes() == b"binary-2099-07-12-payload"


def test_pilot_is_machine_readable_and_never_exposes_b_or_c(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    revision = module._git("rev-parse", "HEAD")
    original_git = module._git

    def clean_git(*arguments: str) -> str:
        if arguments[:2] == ("status", "--porcelain"):
            return ""
        return original_git(*arguments)

    monkeypatch.setattr(module, "_git", clean_git)
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
    assert result["gate_eligible"] is True
    assert set(result["measurements"]) == {"small"}
    assert set(result["measurements"]["small"]) == {
        "cold_project_open",
        "governed_proposal_create",
    }
    assert len(result["measurements"]["small"]["cold_project_open"]["samples_seconds"]) == 3
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


def test_variants_b_and_c_allow_explicit_non_gating_dirty_diagnostics(
    monkeypatch,
) -> None:
    module = _module()
    revision = module._git("rev-parse", "HEAD")
    original_git = module._git

    def dirty_git(*arguments: str) -> str:
        if arguments[:2] == ("status", "--porcelain"):
            return " M src/p2p_engine/example.py"
        return original_git(*arguments)

    monkeypatch.setattr(module, "_git", dirty_git)
    observed = module.verify_baseline(
        revision,
        variant="b",
        allow_dirty_product=True,
    )
    observed_c = module.verify_baseline(
        revision,
        variant="c",
        allow_dirty_product=True,
    )

    assert observed["variant"] == "B-filesystem-behind-storage-ports"
    assert observed["product_source_clean"] is False
    assert observed["product_source_status"]
    assert observed_c["variant"] == "C-sqlite-behind-storage-ports"
    assert observed_c["product_source_clean"] is False
    assert observed_c["product_source_status"]


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


def test_candidate_c_dataset_preserves_frozen_logical_state(tmp_path: Path) -> None:
    module = _module()
    manifest = module.build_dataset(
        tmp_path / "candidate-c",
        module.DATASET_PROFILES["small"],
        seed=2501,
        variant="c",
    )

    assert manifest["variant"] == "C-sqlite-behind-storage-ports"
    assert (
        manifest["logical_fixture_digest"]
        == module.FROZEN_DATASET_DIGESTS["small"]["logical_fixture_digest"]
    )
    assert (
        manifest["semantic_state_digest"]
        == module.FROZEN_DATASET_DIGESTS["small"]["semantic_state_digest"]
    )
    assert (tmp_path / "candidate-c/.p2p/local/project.sqlite3").is_file()
    assert not (tmp_path / "candidate-c/.p2p/project.yml").exists()


def test_definitive_sample_api_reports_normalized_metrics(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "candidate-c"
    module.build_dataset(
        root,
        module.DATASET_PROFILES["small"],
        seed=2501,
        variant="c",
    )

    result = module.run_definitive_sample(
        root,
        tmp_path / "scratch",
        "cold_project_open",
        "c",
        sample_number=1,
        batch_count=2,
    )

    assert result["valid"] is True
    assert result["variant"] == "C-sqlite-behind-storage-ports"
    assert result["logical_operation_count"] == 2
    assert result["elapsed_seconds"] >= result["per_operation_seconds"] > 0
    assert result["tracemalloc_peak_bytes"] > 0
    assert result["disk_bytes_before"] > 0
    assert result["diagnostics"]["setup_and_cleanup_in_measured_span"] is False


def test_concurrency_sample_reports_separate_contention_timing(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "filesystem-ports"
    module.build_dataset(
        root,
        module.DATASET_PROFILES["small"],
        seed=2501,
        variant="b",
    )

    result = module.run_definitive_sample(
        root,
        tmp_path / "scratch",
        "concurrent_readers_serialized_writer",
        "b",
        sample_number=1,
        batch_count=1,
    )

    assert result["valid"] is True, result
    diagnostics = result["diagnostics"]
    assert diagnostics["uncontended_writer_seconds"] > 0
    assert diagnostics["writer_elapsed_seconds"] > 0
    assert diagnostics["lock_wait_upper_bound_seconds"] == diagnostics["writer_elapsed_seconds"]
    assert diagnostics["contention_overhead_estimate_seconds"] >= 0


def test_clean_agent_artifacts_are_backend_equivalent(tmp_path: Path) -> None:
    module = _module()
    result = module.compare_clean_agent_artifacts(tmp_path)

    assert result["valid"] is True, result
    assert result["differences"] == []
    assert result["backend_leaks"] == []
    assert result["filesystem_artifact_count"] == result["sqlite_artifact_count"]
    assert result["filesystem_artifact_count"] > 4


@pytest.mark.parametrize("variant", ("b", "c"))
def test_conformance_exercises_independent_recovery_and_transaction_gates(
    tmp_path: Path,
    variant: str,
) -> None:
    module = _module()
    root = tmp_path / f"candidate-{variant}"
    module.build_dataset(
        root,
        module.DATASET_PROFILES["small"],
        seed=2501,
        variant=variant,
    )

    result = module.run_conformance(root, tmp_path / "conformance", variant)
    checks = result["checks"]

    assert checks["failed_mutation_atomicity"]["passed"] is True
    assert checks["stale_restore_revision"]["passed"] is True
    assert checks["storage_port_transaction"]["passed"] is True
    assert checks["migration_readiness"]["passed"] is True
    if variant == "b":
        assert checks["receipt_replay"]["passed"] is True
        assert checks["abrupt_exit_recovery"]["passed"] is True
        assert result["valid"] is True
    else:
        # The harness reports the candidate actually loaded by this checkout:
        # immutable C1 fails these gates, while a remediated C2 must pass them.
        # In either case the aggregate may not hide or override the observation.
        candidate_passed = bool(checks["receipt_replay"]["passed"]) and bool(
            checks["abrupt_exit_recovery"]["passed"]
        )
        assert result["valid"] is candidate_passed

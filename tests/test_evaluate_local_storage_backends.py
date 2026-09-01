from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/evaluate-local-storage-backends.py"


def _module():
    spec = importlib.util.spec_from_file_location("evaluate_local_storage_backends", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _records(values: list[float]) -> list[dict[str, Any]]:
    return [
        {
            "per_operation_seconds": value,
            "peak_python_bytes": 100 + index,
            "peak_rss_bytes": 1_000 + index,
            "disk_before_bytes": 10,
            "disk_after_bytes": 20 + index,
        }
        for index, value in enumerate(values)
    ]


def _comparison(*, meaningful: bool = False, change: float = -0.25) -> dict[str, Any]:
    return {
        "valid": True,
        "median_ratio": 1.0 + change,
        "median_change": change,
        "p95_ratio": 1.0 + change,
        "p95_change": change,
        "robust_noise_floor": 0.04,
        "meaningful_median_change": meaningful,
        "meaningful_p95_change": meaningful,
    }


def _platform_evidence(
    target: str,
    *,
    regression: bool = False,
    sqlite_go_eligible: bool = True,
) -> dict[str, Any]:
    backend = _comparison(
        meaningful=regression,
        change=0.30 if regression else -0.25,
    )
    return {
        "contract": "p2p-local-backend-platform-evidence/v1",
        "valid": True,
        "gate_eligible": True,
        "decision": {
            "sqlite_go_eligible": sqlite_go_eligible,
            "filesystem_go_eligible": True,
        },
        "workflow_provenance": {"platform_target": target},
        "matrix_identity": {"sha256": "frozen-matrix"},
        "frozen_commits": {"a": "a", "b": "b", "c": "c"},
        "variant_names": {"a": "A", "b": "B", "c": "C"},
        "candidate_c_reference_wheel_sha256": "candidate-c",
        "harness_digests": {"evaluator": "one", "worker": "two"},
        "artifact_coordinates": {"a": "one", "b": "two", "c": "three"},
        "profiles": ["small"],
        "workloads": ["cold_project_open"],
        "warmup_policy": {"ordinary": 5, "stress": 5},
        "repetition_policy": {"ordinary": 21, "stress": 11},
        "thresholds": {"median": 0.20},
        "excluded_metrics": ["complete_test_suite_duration", "test_count"],
        "comparisons": {
            "small": {
                "cold_project_open": {
                    "a_to_b_abstraction": _comparison(),
                    "b_to_c_backend": backend,
                }
            }
        },
    }


def _write_evidence(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_frozen_variant_coordinates_are_exact_distinct_and_immutable() -> None:
    module = _module()

    assert module.FROZEN_COMMITS == {
        "a": "5314459504747f4930aa2f00a26c094d0d058b64",
        "b": "fdfbf1e21fd8b0dd148a6473270bd862f5c25fe1",
        "c": "e83f7b5435bd22e506dc24e5dc6b5f6a5e4a33b2",
    }
    assert len(set(module.FROZEN_COMMITS.values())) == 3
    assert all(
        len(revision) == 40 and all(character in "0123456789abcdef" for character in revision)
        for revision in module.FROZEN_COMMITS.values()
    )
    assert module.VARIANT_NAMES == {
        "a": "A-filesystem-before-storage-ports",
        "b": "B-filesystem-behind-storage-ports",
        "c": "C-sqlite-behind-storage-ports",
    }
    assert module.FROZEN_CANDIDATE_C_REFERENCE_WHEEL_SHA256 == (
        "eb948e9556fc127921612b12a66a3e4d3c747d48e896eea37dcb247dc472d563"
    )


def test_summary_records_resources_and_applies_both_variance_limits() -> None:
    module = _module()

    stable = module._summarize(_records([1.0] * 21))
    noisy = module._summarize(_records([0.5, 1.0, 1.5] * 7))
    drifting = module._summarize(_records(([1.0] * 10) + ([1.30] * 11)))

    assert stable["sample_count"] == 21
    assert stable["median_seconds"] == 1.0
    assert stable["p95_seconds"] == 1.0
    assert stable["valid_variance"] is True
    assert stable["peak_python_bytes"] == 120
    assert stable["peak_rss_bytes"] == 1_020
    assert stable["maximum_disk_delta_bytes"] == 30

    assert noisy["relative_mad"] > module.MAX_RELATIVE_MAD
    assert noisy["valid_variance"] is False
    assert abs(drifting["relative_half_drift"]) > module.MAX_ABSOLUTE_HALF_DRIFT
    assert drifting["valid_variance"] is False


def test_comparison_enforces_frozen_median_p95_and_robust_noise_thresholds() -> None:
    module = _module()
    left = {
        "median_seconds": 1.0,
        "p95_seconds": 1.0,
        "relative_mad": 0.01,
        "valid_variance": True,
    }

    below = module._comparison(
        left,
        {
            "median_seconds": 1.19,
            "p95_seconds": 1.24,
            "relative_mad": 0.01,
            "valid_variance": True,
        },
    )
    meaningful = module._comparison(
        left,
        {
            "median_seconds": 1.21,
            "p95_seconds": 1.26,
            "relative_mad": 0.01,
            "valid_variance": True,
        },
    )
    hidden_by_noise = module._comparison(
        left,
        {
            "median_seconds": 1.30,
            "p95_seconds": 1.30,
            "relative_mad": 0.10,
            "valid_variance": True,
        },
    )
    invalid = module._comparison(
        left,
        {
            "median_seconds": 2.0,
            "p95_seconds": 2.0,
            "relative_mad": 0.20,
            "valid_variance": False,
        },
    )

    assert module.MEANINGFUL_MEDIAN_RATIO == 0.20
    assert module.MEANINGFUL_P95_RATIO == 0.25
    assert module.ROBUST_MAD_MULTIPLIER == 4.0
    assert below["meaningful_median_change"] is False
    assert below["meaningful_p95_change"] is False
    assert meaningful["meaningful_median_change"] is True
    assert meaningful["meaningful_p95_change"] is True
    assert hidden_by_noise["robust_noise_floor"] == pytest.approx(0.40)
    assert hidden_by_noise["meaningful_median_change"] is False
    assert hidden_by_noise["meaningful_p95_change"] is True
    assert invalid["valid"] is False
    assert invalid["meaningful_median_change"] is False
    assert invalid["meaningful_p95_change"] is False


def test_aggregate_marks_missing_platforms_and_never_runs_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    linux = _write_evidence(tmp_path / "linux.json", _platform_evidence("linux-x86_64"))

    def forbidden(*_arguments: object, **_kwargs: object) -> object:
        raise AssertionError("aggregate attempted a subprocess or Git action")

    monkeypatch.setattr(module, "_run", forbidden)
    monkeypatch.setattr(module, "_git", forbidden)
    result = module._aggregate((linux,))

    assert result["valid"] is False
    assert result["platforms"] == ["linux-x86_64"]
    assert result["missing_platforms"] == [
        "macos-arm64",
        "macos-x86_64",
        "windows-x86_64",
    ]
    assert result["automated_recommendation"] == "not-issued"
    assert result["owner_decision"] == "pending"
    assert result["automated_git_action"] is False


def test_aggregate_requires_unique_platforms_and_reports_regressions(
    tmp_path: Path,
) -> None:
    module = _module()
    linux = _write_evidence(
        tmp_path / "linux.json",
        _platform_evidence("linux-x86_64", regression=True),
    )
    darwin_arm = _write_evidence(tmp_path / "darwin-arm.json", _platform_evidence("macos-arm64"))
    darwin_intel = _write_evidence(
        tmp_path / "darwin-intel.json", _platform_evidence("macos-x86_64")
    )
    windows = _write_evidence(tmp_path / "windows.json", _platform_evidence("windows-x86_64"))

    result = module._aggregate((linux, darwin_arm, darwin_intel, windows))

    assert result["valid"] is True
    assert result["technical_gate_status"] == "candidates-eligible-owner-review"
    assert result["missing_platforms"] == []
    assert result["automated_recommendation"] == "not-issued"
    assert result["common_operation_regressions"] == [
        {
            "platform": "linux-x86_64",
            "profile": "small",
            "workload": "cold_project_open",
            "median_change": 0.30,
            "p95_change": 0.30,
        }
    ]
    assert result["automated_git_action"] is False

    duplicate = _write_evidence(
        tmp_path / "linux-duplicate.json", _platform_evidence("linux-x86_64")
    )
    with pytest.raises(RuntimeError, match="duplicate platform evidence for linux-x86_64"):
        module._aggregate((linux, duplicate))


def test_aggregate_distinguishes_valid_candidate_rejection_from_invalid_evidence(
    tmp_path: Path,
) -> None:
    module = _module()
    paths = tuple(
        _write_evidence(
            tmp_path / f"{target}.json",
            _platform_evidence(target, sqlite_go_eligible=False),
        )
        for target in sorted(module.REQUIRED_PLATFORM_TARGETS)
    )

    result = module._aggregate(paths)

    assert result["valid"] is True
    assert result["sqlite_go_eligible"] is False
    assert result["filesystem_go_eligible"] is True
    assert result["remaining_outcomes"] == ["filesystem-go", "inconclusive"]
    assert result["technical_gate_status"] == "candidate-c-rejected-owner-review"


def test_synthetic_platform_run_excludes_full_suite_metrics_and_git_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    monkeypatch.setattr(module, "_validate_ancestry", lambda _repository: None)
    monkeypatch.setattr(
        module,
        "_clone_variants",
        lambda _repository, parent: {
            variant: parent / variant for variant in module.FROZEN_COMMITS
        },
    )

    def worker(**kwargs: Any) -> dict[str, Any]:
        action = kwargs["action"]
        variant = kwargs["variant"]
        profile = kwargs.get("profile", "small")
        if action == "prepare":
            return {
                "baseline": {
                    "git_revision": module.FROZEN_COMMITS[variant],
                    "product_source_clean": True,
                },
                "dataset": {
                    "logical_fixture_digest": f"logical-{profile}",
                    "semantic_state_digest": f"semantic-{profile}",
                    "project_uuid": f"project-{profile}",
                },
                "environment": {
                    "system": "Linux",
                    "release": "test",
                    "machine": "x86_64",
                    "python_version": "3.12.0",
                    "python_executable": sys.executable,
                    "filesystem_type": "ext4",
                    "logical_cpu_count": 8,
                    "memory_bytes": 1024,
                },
                "contracts": {
                    "domain": "p2p-domain/v1",
                    "canonical_memory": "p2p-canonical-memory/v1",
                    "bundle": "p2p-project-bundle/v1",
                },
            }
        if action == "conformance":
            return {"valid": True}
        if action == "agents":
            return {"valid": True}
        raise AssertionError(action)

    monkeypatch.setattr(module, "_worker", worker)

    class FakeSession:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def sample(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "valid": True,
                "per_operation_seconds": 1.0,
                "tracemalloc_peak_bytes": 10,
                "rss_after": {"current_bytes": 20, "peak_bytes": 20},
                "disk_bytes_before": 100,
                "disk_bytes_after": 110,
            }

    monkeypatch.setattr(module, "_WorkerSession", FakeSession)
    arguments = argparse.Namespace(
        temporary_parent=tmp_path,
        profiles=("small",),
        workloads=("cold_project_open",),
        smoke=True,
        output=None,
    )

    result = module._platform_run(arguments)

    assert result["excluded_metrics"] == [
        "complete_test_suite_duration",
        "test_count",
    ]
    assert result["decision"]["automated_git_action"] is False
    assert result["gate_eligible"] is False
    assert result["hard_gates"]["complete_frozen_matrix"] is False
    assert len(result["schedule"]) == 3


def test_main_writes_atomic_failure_envelope_without_partial_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _module()
    output = tmp_path / "failure.json"
    output.write_text("incomplete", encoding="utf-8")
    missing_parent = tmp_path / "missing"
    monkeypatch.setattr(module, "_validate_ancestry", lambda _repository: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--temporary-parent",
            str(missing_parent),
            "--output",
            str(output),
        ],
    )

    assert module.main() == 2
    failure = json.loads(output.read_text(encoding="utf-8"))
    captured = capsys.readouterr()

    assert failure["contract"] == module.PLATFORM_CONTRACT
    assert failure["valid"] is False
    assert failure["gate_eligible"] is False
    assert failure["automated_git_action"] is False
    assert "--temporary-parent must be an existing directory" in failure["error"]
    assert "local-storage gate invalid" in captured.err
    assert not list(tmp_path.glob(".failure.json.*.tmp"))


def test_main_treats_valid_candidate_rejection_as_preserved_decision_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    output = tmp_path / "candidate-rejected.json"
    monkeypatch.setattr(
        module,
        "_platform_run",
        lambda _arguments: {
            "contract": module.PLATFORM_CONTRACT,
            "valid": True,
            "gate_eligible": True,
            "status": "complete-candidate-rejected",
            "decision": {
                "sqlite_go_eligible": False,
                "filesystem_go_eligible": True,
                "remaining_outcomes": ["filesystem-go", "inconclusive"],
                "automated_git_action": False,
            },
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "--temporary-parent", str(tmp_path), "--output", str(output)],
    )

    assert module.main() == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "complete-candidate-rejected"
    assert result["decision"]["sqlite_go_eligible"] is False

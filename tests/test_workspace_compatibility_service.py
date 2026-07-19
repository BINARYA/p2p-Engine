from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest

from p2p_engine.core.workspace_schema import (
    CURRENT_WORKSPACE_SCHEMA_VERSION,
    FINDING_OWNER_INPUT_REQUIRED,
    OP_PRESERVE_LEGACY,
)
from p2p_engine.services.workspace_compatibility import (
    WorkspaceCompatibilityService,
    load_owner_input_patch,
    normalize_owner_inputs,
)
from p2p_engine.services.workspace_schema import WorkspaceSchemaService
from p2p_engine.storage.filesystem import P2PWorkspace
from tests.filesystem_assertions import assert_no_workspace_mutation
from tests.workspace_migration_fixtures import add_proposal_corpus, initialize_legacy_workspace


def _legacy_workspace(root: Path, *, domain: str = "none") -> WorkspaceCompatibilityService:
    workspace = P2PWorkspace(root)
    workspace.init_project("Legacy", project_domain=domain)
    (root / ".p2p" / "project" / "workspace-schema.yml").unlink()
    schema = WorkspaceSchemaService(root=root, p2p_dir=root / ".p2p", engine_version="0.2.0")
    return WorkspaceCompatibilityService(
        root=root,
        p2p_dir=root / ".p2p",
        schema_service=schema,
        engine_version="0.2.0",
    )


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_snapshot_and_plan_are_read_only_and_exclude_internal_scratch(tmp_path: Path) -> None:
    service = _legacy_workspace(tmp_path)
    internal = tmp_path / ".p2p" / ".internal" / "workspace-migrations" / "apply.lock"
    internal.parent.mkdir(parents=True)
    internal.write_text("diagnostic", encoding="utf-8")
    before = _tree_hash(tmp_path)

    snapshot = service.snapshot()
    plan = service.plan(1)

    assert _tree_hash(tmp_path) == before
    assert all(".p2p/.internal" not in item.path for item in snapshot.inventory)
    assert plan.applicable is True
    assert plan.migration_ids == ("workspace-legacy-to-v1",)
    assert not (tmp_path / ".p2p" / "project" / "workspace-schema.yml").exists()


@pytest.mark.slow
def test_legacy_plan_scales_to_one_hundred_proposals_with_bounded_source_access(
    tmp_path: Path,
) -> None:
    initialize_legacy_workspace(tmp_path)
    add_proposal_corpus(tmp_path, count=100)
    service = WorkspaceCompatibilityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        engine_version="0.2.0",
    )

    started = time.monotonic()
    with assert_no_workspace_mutation(tmp_path):
        snapshot = service.snapshot()
        plan = service.plan(1)
    elapsed = time.monotonic() - started

    counters = snapshot.source_access
    assert plan.applicable is True
    assert counters["files_discovered"] >= 100
    assert counters["files_read"] == counters["files_discovered"]
    assert counters["bytes_read"] > 0
    assert counters["yaml_parses"] <= 3
    assert counters["files_written"] == 0
    assert elapsed < 10.0


def test_plan_fingerprint_is_independent_from_absolute_root_and_apply_date(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = _legacy_workspace(first_root)
    second = _legacy_workspace(second_root)

    first_plan = first.plan(1)
    second_plan = second.plan(1)

    assert first_plan.fingerprint_sha256 == second_plan.fingerprint_sha256
    assert first_plan.to_dict() == second_plan.to_dict()
    assert b"__P2P_APPLY_AT__" in first_plan.candidate_files[".p2p/project/workspace-schema.yml"]


def test_unknown_durable_artifact_is_preserved_and_reported(tmp_path: Path) -> None:
    service = _legacy_workspace(tmp_path)
    unknown = tmp_path / ".p2p" / "custom-memory.bin"
    unknown.write_bytes(b"owner data")

    plan = service.plan(1)

    preserve = [item for item in plan.operations if item.kind == OP_PRESERVE_LEGACY]
    assert [item.target for item in preserve] == [".p2p/custom-memory.bin"]
    assert unknown.read_bytes() == b"owner data"


def test_software_workspace_requires_explicit_vertical_owner_input(tmp_path: Path) -> None:
    service = _legacy_workspace(tmp_path, domain="software")

    blocked = service.plan(1)
    applicable = service.plan(
        1,
        {
            "vertical": {"id": "software_project", "profile": "default", "modules": []},
        },
    )

    assert blocked.applicable is False
    assert any(item.classification == FINDING_OWNER_INPUT_REQUIRED for item in blocked.findings)
    assert applicable.applicable is True
    assert any(item.operation_id == "select-project-vertical" for item in applicable.operations)


def test_current_and_downgrade_plans_have_stable_no_write_results(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Current")
    service = WorkspaceCompatibilityService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        engine_version="0.2.0",
    )
    before = _tree_hash(tmp_path)

    current = service.plan(CURRENT_WORKSPACE_SCHEMA_VERSION)
    downgrade = service.plan(CURRENT_WORKSPACE_SCHEMA_VERSION - 1)

    assert current.status == "no_op"
    assert current.applicable is True
    assert downgrade.status == "blocked"
    assert downgrade.applicable is False
    assert downgrade.findings[0].code == "P2P310_UNSUPPORTED_DOWNGRADE"
    assert _tree_hash(tmp_path) == before


def test_inspect_but_not_apply_runtime_produces_actionable_blocker(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    base = _legacy_workspace(root)
    service = WorkspaceCompatibilityService(
        root=root,
        p2p_dir=root / ".p2p",
        schema_service=base.schema_service,
        engine_version="0.1.9",
    )

    plan = service.plan(1)

    assert plan.applicable is False
    assert any(item.code == "P2P321_MIGRATION_PLAN_RUNTIME_REQUIRED" for item in plan.findings)
    assert plan.transition_support[0].apply is False


def test_owner_input_parser_rejects_unknown_and_unsafe_values() -> None:
    with pytest.raises(ValueError, match="Unknown migration owner input"):
        normalize_owner_inputs({"secret": {"value": "x"}})
    with pytest.raises(ValueError, match="Unsafe"):
        normalize_owner_inputs({"vertical": {"id": "../outside"}})
    with pytest.raises(ValueError, match="modules"):
        normalize_owner_inputs({"vertical": {"id": "software", "modules": "all"}})


def test_owner_input_normalization_is_order_independent() -> None:
    first = normalize_owner_inputs(
        {
            "metadata": {"status": "active", "workflow_phase": "delivery"},
            "vertical": {"modules": ["api", "core", "api"], "id": "software_project"},
        }
    )
    second = normalize_owner_inputs(
        {
            "vertical": {"id": "software_project", "modules": ["core", "api"]},
            "metadata": {"workflow_phase": "delivery", "status": "active"},
        }
    )
    assert first == second


def test_decision_attestation_input_is_closed_bounded_and_order_independent() -> None:
    hashes = {
        "proposal.md": "a" * 64,
        "decision.md": "b" * 64,
    }
    first = normalize_owner_inputs(
        {
            "proposal_decisions": {
                "attestation_contract_version": 1,
                "authority_attestations": {
                    "PROP-010": {
                        "owner_id": "owner",
                        "legacy_status": "accepted_with_changes",
                        "legacy_approver": "local",
                        "decided_on": "2026-07-19",
                        "source_sha256": hashes,
                        "conditions": [
                            {"id": "C002", "text": "Second."},
                            {"id": "C001", "text": "First."},
                        ],
                    }
                },
            }
        }
    )
    second = normalize_owner_inputs(
        {
            "proposal_decisions": {
                "authority_attestations": {
                    "PROP-010": {
                        "conditions": [
                            {"text": "First.", "id": "C001"},
                            {"text": "Second.", "id": "C002"},
                        ],
                        "source_sha256": {
                            "decision.md": "b" * 64,
                            "proposal.md": "a" * 64,
                        },
                        "decided_on": "2026-07-19",
                        "legacy_approver": "local",
                        "legacy_status": "accepted_with_changes",
                        "owner_id": "owner",
                    }
                },
                "attestation_contract_version": 1,
            }
        }
    )

    assert first == second
    conditions = first["proposal_decisions"]["authority_attestations"][
        "PROP-010"
    ]["conditions"]
    assert [item["id"] for item in conditions] == ["C001", "C002"]


@pytest.mark.parametrize(
    "attestation",
    (
        {
            "owner_id": "owner",
            "legacy_status": "superseded",
            "legacy_approver": "local",
            "decided_on": "2026-07-19",
            "source_sha256": {
                "proposal.md": "a" * 64,
                "decision.md": "b" * 64,
            },
        },
        {
            "owner_id": "Owner Name",
            "legacy_status": "accepted",
            "legacy_approver": "local",
            "decided_on": "2026-07-19",
            "source_sha256": {
                "proposal.md": "a" * 64,
                "decision.md": "b" * 64,
            },
        },
        {
            "owner_id": "owner",
            "legacy_status": "accepted",
            "legacy_approver": "local",
            "decided_on": "not-a-date",
            "source_sha256": {
                "proposal.md": "a" * 64,
                "decision.md": "b" * 64,
            },
        },
        {
            "owner_id": "owner",
            "legacy_status": "accepted",
            "legacy_approver": "local",
            "decided_on": "2026-07-19",
            "source_sha256": {"proposal.md": "a" * 64},
        },
    ),
)
def test_decision_attestation_input_rejects_unsafe_or_incomplete_values(
    attestation: dict[str, object],
) -> None:
    with pytest.raises(
        ValueError,
        match="P2P390_MIGRATION_ATTESTATION_INVALID",
    ):
        normalize_owner_inputs(
            {
                "proposal_decisions": {
                    "attestation_contract_version": 1,
                    "authority_attestations": {"PROP-001": attestation},
                }
            }
        )


def test_decision_attestation_requires_conditions_only_for_conditional_acceptance() -> None:
    base = {
        "owner_id": "owner",
        "legacy_approver": "local",
        "decided_on": "2026-07-19",
        "source_sha256": {
            "proposal.md": "a" * 64,
            "decision.md": "b" * 64,
        },
    }
    with pytest.raises(ValueError, match="requires at least one structured condition"):
        normalize_owner_inputs(
            {
                "proposal_decisions": {
                    "attestation_contract_version": 1,
                    "authority_attestations": {
                        "PROP-001": {
                            **base,
                            "legacy_status": "accepted_with_changes",
                        }
                    },
                }
            }
        )
    with pytest.raises(ValueError, match="allowed only"):
        normalize_owner_inputs(
            {
                "proposal_decisions": {
                    "attestation_contract_version": 1,
                    "authority_attestations": {
                        "PROP-001": {
                            **base,
                            "legacy_status": "accepted",
                            "conditions": [{"id": "C001", "text": "Not allowed."}],
                        }
                    },
                }
            }
        )


def test_decision_attestation_yaml_rejects_duplicate_proposal_and_condition_ids(
    tmp_path: Path,
) -> None:
    duplicate_proposal = tmp_path / "duplicate-proposal.yml"
    duplicate_proposal.write_text(
        "proposal_decisions:\n"
        "  attestation_contract_version: 1\n"
        "  authority_attestations:\n"
        "    PROP-001: {}\n"
        "    PROP-001: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate migration owner input YAML key"):
        load_owner_input_patch(duplicate_proposal)

    duplicate_condition = {
        "proposal_decisions": {
            "attestation_contract_version": 1,
            "authority_attestations": {
                "PROP-001": {
                    "owner_id": "owner",
                    "legacy_status": "accepted_with_changes",
                    "legacy_approver": "local",
                    "decided_on": "2026-07-19",
                    "source_sha256": {
                        "proposal.md": "a" * 64,
                        "decision.md": "b" * 64,
                    },
                    "conditions": [
                        {"id": "C001", "text": "First."},
                        {"id": "C001", "text": "Second."},
                    ],
                }
            },
        }
    }
    with pytest.raises(ValueError, match="duplicate condition ID"):
        normalize_owner_inputs(duplicate_condition)

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.storage.filesystem import P2PWorkspace


def _write_contract(root: Path, requires: str, recommended: str) -> None:
    path = root / ".p2p" / "project" / "runtime.yml"
    path.write_text(
        yaml.safe_dump(
            {
                "runtime_contract": {"schema_version": 1},
                "runtime": {"p2p": {"requires": requires, "recommended": recommended}},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _remove_runtime_marker(root: Path) -> None:
    project_path = root / ".p2p" / "project.yml"
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    project.pop("runtime_contract")
    project_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")


def test_runtime_write_gate_allows_compatible_contract(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Compatible Project")

    proposal = workspace.create_proposal("Allowed Write")

    assert proposal.proposal_id == "PROP-001"


def test_runtime_write_gate_blocks_missing_required_contract_before_mutation(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Missing Runtime Project")
    (tmp_path / ".p2p" / "project" / "runtime.yml").unlink()

    with pytest.raises(ValueError, match="missing_contract"):
        workspace.create_proposal("Blocked Write")

    assert list((tmp_path / ".p2p" / "proposals").iterdir()) == []


def test_runtime_write_gate_blocks_incompatible_contract_before_mutation(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Incompatible Runtime Project")
    _write_contract(tmp_path, "==99.0.0", "99.0.0")

    with pytest.raises(ValueError, match="incompatible"):
        workspace.create_change_set("proposal:PROP-001", title="Blocked Change")

    changes_dir = tmp_path / ".p2p" / "changes"
    assert not changes_dir.exists() or list(changes_dir.iterdir()) == []


def test_runtime_write_gate_allows_legacy_undeclared_without_inference(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Legacy Runtime Project")
    (tmp_path / ".p2p" / "project" / "runtime.yml").unlink()
    _remove_runtime_marker(tmp_path)

    proposal = workspace.create_proposal("Legacy Allowed")

    assert proposal.proposal_id == "PROP-001"
    assert workspace.runtime_status().state == "legacy_undeclared"


def test_runtime_preflight_classifies_read_only_and_guarded_paths(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Preflight Project")
    (tmp_path / ".p2p" / "project" / "runtime.yml").unlink()

    assert workspace.runtime_status().state == "missing_contract"
    assert workspace.validate().ok is False
    with pytest.raises(ValueError, match="missing_contract"):
        workspace.refresh_registries()

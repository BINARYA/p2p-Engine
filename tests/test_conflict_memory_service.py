from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Demo Project")
    workspace.create_proposal("Project State")
    workspace.create_proposal("Alternative State")
    return workspace


def test_conflict_memory_service_returns_empty_status(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    status = workspace._conflict_memory_service().status()

    assert status.conflicts_count == 0
    assert status.conflicts == []
    assert status.conflicts_file == Path(".p2p/project/conflicts.yml")


def test_conflict_memory_service_records_conflict_with_winner(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    status = workspace._conflict_memory_service().record(
        proposals=["PROP-001", "PROP-002"],
        conflict_type="mutually_exclusive",
        reason="Two alternative project-state models.",
        winner="PROP-001",
    )

    assert status.conflicts_count == 1
    assert status.conflicts[0]["id"] == "CONFLICT-001"
    assert status.conflicts[0]["winner"] == "PROP-001"
    assert status.conflicts[0]["rejected"] == ["PROP-002"]
    payload = yaml.safe_load((tmp_path / ".p2p" / "project" / "conflicts.yml").read_text(encoding="utf-8"))
    assert payload["conflicts"][0]["reason"] == "Two alternative project-state models."


def test_conflict_memory_service_validates_record_inputs(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._conflict_memory_service()

    with pytest.raises(ValueError, match="At least two proposals"):
        service.record(
            proposals=["PROP-001"],
            conflict_type="overlaps",
            reason="Too few proposals.",
            winner=None,
        )

    with pytest.raises(ValueError, match="winner must be one"):
        service.record(
            proposals=["PROP-001", "PROP-002"],
            conflict_type="overlaps",
            reason="Invalid winner.",
            winner="PROP-003",
        )


def test_conflict_memory_service_rejects_invalid_payload_shape(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    conflict_path = tmp_path / ".p2p" / "project" / "conflicts.yml"
    conflict_path.parent.mkdir(parents=True, exist_ok=True)
    conflict_path.write_text("conflicts: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="expected `conflicts` list"):
        workspace._conflict_memory_service().status()

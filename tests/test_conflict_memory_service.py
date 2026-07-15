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


def test_conflict_update_preview_is_stale_safe_and_updates_by_stable_id(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._conflict_memory_service()
    service.record(
        proposals=["PROP-001", "PROP-002"],
        conflict_type="overlap",
        reason="Initial reason.",
        winner=None,
    )
    patch = {
        "type": "mutually_exclusive",
        "winner": "PROP-001",
        "rejected": ["PROP-002"],
        "reason": "Owner selected the first model.",
        "provenance": {"source": "M3 review"},
    }

    preview = service.preview_update("CONFLICT-001", patch, actor="owner")
    stale = service.update(
        "CONFLICT-001",
        {**patch, "reason": "Different candidate."},
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )
    result = service.update(
        "CONFLICT-001",
        patch,
        preview_token=preview.preview_token,
        actor="owner",
        confirm=True,
    )

    assert preview.apply_allowed is True
    assert stale.status == "stale_preview"
    assert result.status == "applied"
    assert service.status().conflicts_count == 1
    conflict = service.show("CONFLICT-001")
    assert conflict["winner"] == "PROP-001"
    assert conflict["rejected"] == ["PROP-002"]
    assert conflict["provenance"]["updated_by"] == "owner"


def test_conflict_update_rejects_unauthorized_and_append_shaped_patch(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._conflict_memory_service()
    service.record(
        proposals=["PROP-001", "PROP-002"],
        conflict_type="overlap",
        reason="Initial reason.",
        winner=None,
    )
    patch = {"reason": "Updated reason."}

    preview = service.preview_update("CONFLICT-001", patch, actor="contributor")

    assert preview.apply_allowed is False
    assert service.update(
        "CONFLICT-001",
        patch,
        preview_token=preview.preview_token,
        actor="contributor",
        confirm=True,
    ).status == "blocked"
    with pytest.raises(ValueError, match="Unsupported conflict patch field"):
        service.preview_update("CONFLICT-001", {"conflicts": []}, actor="owner")
    assert service.status().conflicts_count == 1


def test_conflict_update_validates_resolution_consistency_before_write(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    service = workspace._conflict_memory_service()
    service.record(
        proposals=["PROP-001", "PROP-002"],
        conflict_type="overlap",
        reason="Initial reason.",
        winner=None,
    )
    before = (tmp_path / ".p2p" / "project" / "conflicts.yml").read_bytes()

    with pytest.raises(ValueError, match="reject every non-winning"):
        service.preview_update(
            "CONFLICT-001",
            {"winner": "PROP-001", "rejected": []},
            actor="owner",
        )

    assert (tmp_path / ".p2p" / "project" / "conflicts.yml").read_bytes() == before

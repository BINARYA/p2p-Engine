from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.work_planning import WorkPlanningService
from p2p_engine.storage.filesystem import P2PWorkspace


@dataclass(frozen=True)
class _Validation:
    path: Path
    checked: list[Path]


def _service(tmp_path, *, scanned_items=None):
    change_dir = tmp_path / ".p2p" / "changes" / "CHANGE-001-test"
    change_dir.mkdir(parents=True)
    change_dir.joinpath("change.md").write_text(
        "---\n"
        "source:\n"
        "  accepted_proposals:\n"
        "    - PROP-001\n"
        "---\n"
        "# CHANGE-001\n",
        encoding="utf-8",
    )

    return WorkPlanningService(
        root=tmp_path,
        p2p_dir=tmp_path / ".p2p",
        export_targets=lambda: ("generic", "speckit"),
        validate_export=lambda change_id, target: _Validation(
            path=Path(f".p2p/outputs/spec-export/{change_id}/{target}"),
            checked=[Path("project.md"), Path("propose.md")],
        ),
        find_change_dir=lambda change_id: change_dir,
        scanned_work_items=lambda: scanned_items or [],
    )


def test_work_planning_service_creates_plan_manifest_and_detail(tmp_path) -> None:
    service = _service(tmp_path)

    detail = service.create_plan("CHANGE-001", "speckit")
    manifest_path = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"

    assert detail.work_id == "WORK-001"
    assert detail.status == "planned"
    assert detail.change_id == "CHANGE-001"
    assert detail.target == "speckit"
    assert detail.branch_name == "p2p/work/work-001-change-001-speckit"
    assert manifest_path.exists()
    manifest = detail.manifest
    assert manifest["visibility"] == "internal_git"
    assert manifest["source"]["proposals"] == ["PROP-001"]
    assert manifest["handoff"]["export_validated"] is True
    assert manifest["allowed_files"] == ["project.md", "propose.md"]
    assert manifest["policy"]["auto_branch"] is False


def test_work_planning_service_rejects_unsupported_target(tmp_path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="Unsupported work handoff target: openspec"):
        service.create_plan("CHANGE-001", "openspec")


def test_work_planning_service_lists_local_and_scanned_work(tmp_path) -> None:
    service = _service(
        tmp_path,
        scanned_items=[
            {
                "work_id": "WORK-999",
                "status": "planned",
                "change": "CHANGE-999",
                "target": "generic",
                "branch": "p2p/work/work-999-change-999-generic",
                "branch_name": "p2p/work/work-999-change-999-generic",
                "path": ".p2p/work/WORK-999/manifest.yml",
            }
        ],
    )
    service.create_plan("CHANGE-001", "generic")

    statuses = service.statuses()
    summaries = service.summaries()

    assert [status.work_id for status in statuses] == ["WORK-001", "WORK-999"]
    assert statuses[0].change_id == "CHANGE-001"
    assert statuses[1].path == Path(".p2p/work/WORK-999/manifest.yml")
    assert summaries[0].next_action == "p2p work branch WORK-001"
    assert summaries[1].next_action == "p2p work show WORK-999"
    assert summaries[1].note == "scanned from a managed branch registry"


def test_work_planning_service_retires_planned_work(tmp_path) -> None:
    service = _service(tmp_path)
    service.create_plan("CHANGE-001", "generic")

    retired = service.retire("WORK-001", "No longer needed.")
    shown = service.show("WORK-001")
    summaries = service.summaries()

    assert retired.work_id == "WORK-001"
    assert retired.status == "retired"
    assert retired.reason == "No longer needed."
    assert retired.path == Path(".p2p/work/WORK-001")
    assert shown.status == "retired"
    assert shown.manifest["retirement"]["reason"] == "No longer needed."
    assert shown.manifest["retirement"]["mode"] == "metadata_only"
    assert summaries[0].next_action == "none"
    assert summaries[0].note == "retired"


def test_work_planning_service_retire_validation_errors(tmp_path) -> None:
    service = _service(tmp_path)
    service.create_plan("CHANGE-001", "generic")

    with pytest.raises(ValueError, match="Work retire reason is required"):
        service.retire("WORK-001", "  ")

    manifest_path = tmp_path / ".p2p" / "work" / "WORK-001" / "manifest.yml"
    manifest_text = manifest_path.read_text(encoding="utf-8").replace("status: planned", "status: branched")
    manifest_path.write_text(manifest_text, encoding="utf-8")

    with pytest.raises(ValueError, match="Work item must be planned before retire. Current status: branched"):
        service.retire("WORK-001", "Too late.")


def test_workspace_work_planning_facade_delegates(tmp_path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Work Planning")
    proposal = workspace.create_proposal_with_details(
        title="Work Planning Proposal",
        problem="Need a handoff.",
        proposal="Create a Work plan.",
        acceptance_criteria=["Work manifest exists."],
    )
    workspace.record_decision(proposal.proposal_id, DecisionOutcome.accepted, "Ready.", "owner")
    change = workspace.create_change_set(proposal.proposal_id)
    workspace.refresh_software_spec(change.change_id)
    workspace.export_software_spec(change.change_id, "generic")

    detail = workspace.create_work_plan(change.change_id, "generic")
    statuses = workspace.work_statuses()
    summaries = workspace.work_summaries()
    shown = workspace.show_work(detail.work_id)

    assert detail.work_id == "WORK-001"
    assert statuses[0].work_id == "WORK-001"
    assert summaries[0].next_action == "p2p work branch WORK-001"
    assert shown.branch_name == "p2p/work/work-001-change-001-generic"

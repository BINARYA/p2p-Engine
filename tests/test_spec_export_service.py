from __future__ import annotations

from pathlib import Path

import pytest

from p2p_engine.core.decision import DecisionOutcome
from p2p_engine.services.registry_records import RegistryRecordBuilderService
from p2p_engine.services.spec_export import SpecExportService
from p2p_engine.storage.filesystem import P2PWorkspace


def _workspace_with_spec(root: Path) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project("Demo Project")
    workspace.create_proposal_with_details(
        title="Spec Work",
        problem="Need implementation-facing specs.",
        proposal="Generate a deterministic software spec.",
        acceptance_criteria=["Spec artifacts exist."],
    )
    workspace.record_decision("PROP-001", DecisionOutcome.accepted, "Needed.", "owner")
    workspace.create_change_set("PROP-001")
    workspace.refresh_software_spec("CHANGE-001")
    return workspace


def _service(workspace: P2PWorkspace) -> SpecExportService:
    registry_records = RegistryRecordBuilderService(
        root=workspace.root,
        p2p_dir=workspace.p2p_dir,
        read_proposal_readiness=workspace.read_proposal_readiness,
    )
    return SpecExportService(
        root=workspace.root,
        p2p_dir=workspace.p2p_dir,
        show_change_set=workspace.show_change_set,
        status=workspace.status,
        accepted_proposals=registry_records.accepted_proposals,
        proposal_summaries=workspace.proposal_summaries,
        required_spec_files=workspace._software_spec_service().required_files,
    )


def test_spec_export_service_exports_and_validates_targets(tmp_path: Path) -> None:
    workspace = _workspace_with_spec(tmp_path)
    service = _service(workspace)

    generic = service.export("CHANGE-001", "generic")
    openspec = service.export("CHANGE-001", "openspec")
    speckit = service.export("CHANGE-001", "speckit")

    assert generic.path == Path(".p2p/outputs/spec-export/CHANGE-001/generic")
    assert openspec.target == "openspec"
    assert speckit.target == "speckit"
    assert "Demo Project Project Definition" in service.show("CHANGE-001", "generic")
    assert "OpenSpec Proposal Input" in service.show("CHANGE-001", "openspec")
    assert "Spec Kit Constitution Prompt" in service.show("CHANGE-001", "speckit")
    assert {item.target for item in service.statuses()} == {"generic", "openspec", "speckit"}

    for target in ("generic", "openspec", "speckit"):
        validation = service.validate("CHANGE-001", target)
        assert validation.target == target
        assert validation.checked


def test_spec_export_service_validation_errors(tmp_path: Path) -> None:
    workspace = _workspace_with_spec(tmp_path)
    service = _service(workspace)

    with pytest.raises(ValueError, match="Unsupported software spec export target"):
        service.export("CHANGE-001", "other")

    service.export("CHANGE-001", "openspec")
    (tmp_path / ".p2p" / "outputs" / "spec-export" / "CHANGE-001" / "openspec" / "propose.md").unlink()

    with pytest.raises(ValueError, match="Missing required software spec export artifact: propose.md"):
        service.validate("CHANGE-001", "openspec")

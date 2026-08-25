from pathlib import Path

import pytest

from p2p_engine.core.workspace_reads import FastFreshnessSummary, ReadCostClass
from p2p_engine.services.workspace_status import WorkspaceStatusService
from p2p_engine.services.workspace_status import (
    PUBLIC_READ_COST_POLICIES,
    public_read_cost_policy,
)
from p2p_engine.storage.filesystem import P2PWorkspace


def test_workspace_status_service_reads_project_and_proposals(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    proposal_dir = p2p_dir / "proposals" / "PROP-001-demo"
    proposal_dir.mkdir(parents=True)
    (p2p_dir / "project.yml").write_text("project:\n  name: Demo Project\n", encoding="utf-8")
    (proposal_dir / "proposal.md").write_text(
        "# PROP-001 - Demo Proposal\n\n"
        "## Status `accepted`\n\n"
        "## Problem\n\n"
        "Need a proposal.\n",
        encoding="utf-8",
    )
    service = WorkspaceStatusService(root=tmp_path, p2p_dir=p2p_dir)

    status = service.status()
    accepted = service.proposal_summaries("accepted")

    assert status.project_name == "Demo Project"
    assert status.proposals[0].proposal_id == "PROP-001"
    assert status.proposals[0].slug == "PROP-001-demo"
    assert status.proposals[0].status == "accepted"
    assert status.proposals[0].title == "Demo Proposal"
    assert accepted == status.proposals
    assert service.proposal_summaries("draft") == []


def test_workspace_status_service_reports_missing_required_paths(tmp_path: Path) -> None:
    service = WorkspaceStatusService(root=tmp_path, p2p_dir=tmp_path / ".p2p")

    check = service.check()

    assert check.ok is False
    assert Path(".p2p/project.yml") in check.missing
    assert Path(".p2p/proposals") in check.missing


def test_workspace_status_facade_delegates(tmp_path: Path) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Facade Project")
    workspace.create_proposal_with_details(
        title="Facade Proposal",
        problem="Need a facade check.",
        proposal="Keep compatibility.",
        acceptance_criteria=["Status remains visible."],
    )

    status = workspace.status()
    summaries = workspace.proposal_summaries("draft")
    check = workspace.check()

    assert status.project_name == "Facade Project"
    assert summaries[0].proposal_id == "PROP-001"
    assert summaries[0].title == "Facade Proposal"
    assert check.ok is True
    assert status.workspace_schema["verification"] == "fast_checked"
    assert status.derived_freshness["status"] == "attention"
    assert status.derived_freshness["verification"] == "fast_checked"
    assert "vertical_project_memory" in status.derived_freshness["attention"]


def test_fast_status_uses_preflight_and_never_calls_deep_providers(tmp_path: Path) -> None:
    p2p_dir = tmp_path / ".p2p"
    p2p_dir.mkdir()
    calls = {"preflight": 0, "schema": 0, "fast": 0, "deep": 0}

    def counted(name: str, value):
        def provider():
            calls[name] += 1
            return value

        return provider

    preflight = type(
        "Preflight",
        (),
        {
            "state": "current",
            "layout_status": "layout_current",
            "current_version": 4,
            "target_version": 4,
            "migration_required": False,
            "recovery": {},
        },
    )()
    fast = FastFreshnessSummary(
        status="current",
        schema_state="current",
        registry_state="current",
        vertical_memory_state="current",
        project_projection_state="current_basis",
    )
    service = WorkspaceStatusService(
        root=tmp_path,
        p2p_dir=p2p_dir,
        workspace_schema_status=counted("schema", object()),
        workspace_schema_preflight=counted("preflight", preflight),
        fast_freshness_status=counted("fast", fast),
        derived_freshness_status=counted("deep", object()),
    )

    result = service.status()

    assert result.workspace_schema["verification"] == "fast_checked"
    assert result.derived_freshness["verification"] == "fast_checked"
    assert calls == {"preflight": 1, "schema": 0, "fast": 1, "deep": 0}


def test_public_read_cost_catalog_classifies_every_declared_operation() -> None:
    names = [item.operation for item in PUBLIC_READ_COST_POLICIES]

    assert len(names) == len(set(names))
    assert public_read_cost_policy("status").cost_class == ReadCostClass.FAST
    assert public_read_cost_policy("context_targeted").cost_class == ReadCostClass.TARGETED
    assert public_read_cost_policy("validate").cost_class == ReadCostClass.DEEP
    assert "complete_freshness" in public_read_cost_policy("status").forbidden_providers


def test_proposal_summaries_use_verified_current_registry_without_lifecycle_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = P2PWorkspace(tmp_path)
    workspace.init_project("Registry summaries")
    workspace.create_proposal("Current proposal")
    workspace.refresh_registries()
    lifecycle = workspace._proposal_lifecycle_authority_service()

    def forbidden(*args, **kwargs):
        raise AssertionError("current proposal registry must avoid lifecycle rebuild")

    monkeypatch.setattr(lifecycle, "capture_all", forbidden)
    workspace._workspace_status_service_instance = None

    summaries = workspace.proposal_summaries()

    assert [(item.proposal_id, item.title, item.status) for item in summaries] == [
        ("PROP-001", "Current proposal", "draft")
    ]

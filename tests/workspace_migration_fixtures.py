from __future__ import annotations

from pathlib import Path

from p2p_engine.storage.filesystem import P2PWorkspace
from tests.decision_context_fixtures import write_proposal


def initialize_current_workspace(
    root: Path,
    *,
    name: str = "Current Workspace",
    domain: str = "none",
    owner: str = "owner",
) -> P2PWorkspace:
    workspace = P2PWorkspace(root)
    workspace.init_project(name, project_domain=domain, owner=owner)
    return workspace


def initialize_legacy_workspace(
    root: Path,
    *,
    name: str = "Legacy Workspace",
    domain: str = "none",
    owner: str = "owner",
) -> P2PWorkspace:
    workspace = initialize_current_workspace(root, name=name, domain=domain, owner=owner)
    (root / ".p2p" / "project" / "workspace-schema.yml").unlink()
    return workspace


def add_proposal_corpus(root: Path, *, count: int, status: str = "accepted") -> None:
    for number in range(1, count + 1):
        proposal_id = f"PROP-{number:03d}"
        write_proposal(
            root,
            proposal_id,
            title=f"Migration fixture {number:03d}",
            status=status,
            decision_outcome=status,
        )

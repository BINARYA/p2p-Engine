from pathlib import Path
from types import SimpleNamespace

import pytest

from p2p_engine.services.proposal_drafts import ProposalDraftCommitService


def _service(
    tmp_path: Path,
    *,
    git_status=None,
    changed_files=None,
    commit="abc123",
    found: bool = True,
) -> ProposalDraftCommitService:
    def find_proposal_dir(proposal_id: str) -> Path:
        if not found:
            raise ValueError(f"Proposal not found: {proposal_id}")
        return tmp_path / ".p2p" / "proposals" / f"{proposal_id}-demo"

    return ProposalDraftCommitService(
        root=tmp_path,
        find_proposal_dir=find_proposal_dir,
        git_status=lambda root: git_status
        or SimpleNamespace(is_repository=True, branch="main", is_clean=False),
        changed_files=lambda root: changed_files if changed_files is not None else ["proposal.md"],
        commit_all=lambda root, message: commit,
        identity_slug=lambda actor: actor.strip().lower().replace(" ", "-") or "local",
    )


def test_proposal_draft_commit_service_commits_changed_files(tmp_path: Path) -> None:
    service = _service(tmp_path)

    result = service.commit("PROP-001", "Local User")

    assert result.proposal_id == "PROP-001"
    assert result.commit == "abc123"
    assert result.changed_files == ["proposal.md"]


def test_proposal_draft_commit_service_validates_git_state(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Cannot commit proposal draft outside a Git repository"):
        _service(tmp_path, git_status=SimpleNamespace(is_repository=False, branch=None)).commit("PROP-001")

    with pytest.raises(ValueError, match="Cannot commit proposal draft from detached HEAD"):
        _service(tmp_path, git_status=SimpleNamespace(is_repository=True, branch="")).commit("PROP-001")

    with pytest.raises(ValueError, match="Cannot commit proposal draft without uncommitted changes"):
        _service(tmp_path, changed_files=[]).commit("PROP-001")

    with pytest.raises(ValueError, match="Failed to create proposal draft commit"):
        _service(tmp_path, commit=None).commit("PROP-001")

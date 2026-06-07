from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProposalDraftCommit:
    proposal_id: str
    commit: str
    changed_files: list[str]


class ProposalDraftCommitService:
    def __init__(
        self,
        *,
        root: Path,
        find_proposal_dir: Callable[[str], Path],
        git_status: Callable[[Path], Any],
        changed_files: Callable[[Path], list[str]],
        commit_all: Callable[[Path, str], str | None],
        identity_slug: Callable[[str], str],
    ) -> None:
        self.root = root
        self.find_proposal_dir = find_proposal_dir
        self.git_status = git_status
        self.changed_files = changed_files
        self.commit_all = commit_all
        self.identity_slug = identity_slug

    def commit(self, proposal_id: str, actor: str = "local") -> ProposalDraftCommit:
        self.find_proposal_dir(proposal_id)
        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot commit proposal draft outside a Git repository")
        if not getattr(git_status, "branch", None):
            raise ValueError("Cannot commit proposal draft from detached HEAD")
        changed = self.changed_files(self.root)
        if not changed:
            raise ValueError("Cannot commit proposal draft without uncommitted changes")
        commit = self.commit_all(self.root, f"P2P proposal draft {proposal_id} by {self.identity_slug(actor)}")
        if commit is None:
            raise ValueError("Failed to create proposal draft commit")
        return ProposalDraftCommit(proposal_id=proposal_id, commit=commit, changed_files=changed)

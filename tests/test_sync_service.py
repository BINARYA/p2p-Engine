from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from p2p_engine.services.sync import SyncService


@dataclass(frozen=True)
class FakeProfile:
    mode: str = "local"
    provider: str = "local"
    remote: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class FakeGitStatus:
    is_repository: bool
    branch: str | None
    is_clean: bool


class FakeGit:
    def __init__(
        self,
        *,
        status: FakeGitStatus,
        urls: dict[str, str | None] | None = None,
        fetch_ok: bool = True,
        pull_ok: bool = True,
        push_ok: bool = True,
    ) -> None:
        self.status = status
        self.urls = urls or {}
        self.fetch_ok = fetch_ok
        self.pull_ok = pull_ok
        self.push_ok = push_ok
        self.fetches: list[str] = []
        self.pulls: list[tuple[str, str]] = []
        self.pushes: list[tuple[str, str]] = []

    def git_status(self, _root: Path) -> FakeGitStatus:
        return self.status

    def remote_url(self, _root: Path, remote: str) -> str | None:
        return self.urls.get(remote)

    def fetch_remote(self, _root: Path, remote: str) -> bool:
        self.fetches.append(remote)
        return self.fetch_ok

    def pull_branch(self, _root: Path, branch: str, remote: str) -> bool:
        self.pulls.append((branch, remote))
        return self.pull_ok

    def push_branch(self, _root: Path, branch: str, remote: str) -> bool:
        self.pushes.append((branch, remote))
        return self.push_ok


def _service(root: Path, profile: FakeProfile, git: FakeGit) -> SyncService:
    return SyncService(
        root=root,
        remote_profile=lambda: profile,
        git_status=git.git_status,
        remote_url=git.remote_url,
        fetch_remote=git.fetch_remote,
        pull_branch=git.pull_branch,
        push_branch=git.push_branch,
    )


def test_sync_status_reports_local_project_outside_git_repository(tmp_path: Path) -> None:
    git = FakeGit(status=FakeGitStatus(is_repository=False, branch=None, is_clean=False))
    service = _service(tmp_path, FakeProfile(), git)

    status = service.status()

    assert status.is_repository is False
    assert status.mode == "local"
    assert status.can_sync is False
    assert status.reason == "not a Git repository"


def test_sync_status_reports_local_profile_with_git_origin_diagnostic(tmp_path: Path) -> None:
    git = FakeGit(
        status=FakeGitStatus(is_repository=True, branch="main", is_clean=True),
        urls={"origin": "git@example.com:demo.git"},
    )
    service = _service(tmp_path, FakeProfile(), git)

    status = service.status()

    assert status.remote is None
    assert status.remote_url is None
    assert status.can_sync is False
    assert status.reason == (
        "project remote profile is local, but Git remote origin exists; "
        "run p2p project remote configure --mode remote --remote origin"
    )


def test_sync_status_uses_explicit_remote_override_for_local_profile(tmp_path: Path) -> None:
    git = FakeGit(
        status=FakeGitStatus(is_repository=True, branch="main", is_clean=True),
        urls={"upstream": "git@example.com:demo.git"},
    )
    service = _service(tmp_path, FakeProfile(), git)

    status = service.status(remote="upstream")

    assert status.remote == "upstream"
    assert status.remote_url == "git@example.com:demo.git"
    assert status.can_sync is True
    assert status.reason == "ready"


def test_sync_status_detects_remote_profile_url_mismatch(tmp_path: Path) -> None:
    git = FakeGit(
        status=FakeGitStatus(is_repository=True, branch="main", is_clean=True),
        urls={"origin": "git@example.com:git-url.git"},
    )
    service = _service(
        tmp_path,
        FakeProfile(mode="remote", provider="github", remote="origin", url="git@example.com:p2p-url.git"),
        git,
    )

    status = service.status()

    assert status.profile_url == "git@example.com:p2p-url.git"
    assert status.remote_url == "git@example.com:git-url.git"
    assert status.can_sync is False
    assert status.reason == (
        "P2P remote profile URL does not match Git remote origin; "
        "run p2p project remote configure with the intended URL"
    )


def test_sync_status_reports_missing_remote_with_profile_url_guidance(tmp_path: Path) -> None:
    git = FakeGit(status=FakeGitStatus(is_repository=True, branch="main", is_clean=True), urls={})
    service = _service(
        tmp_path,
        FakeProfile(mode="remote", provider="generic", remote="origin", url="git@example.com:demo.git"),
        git,
    )

    status = service.status()

    assert status.can_sync is False
    assert status.reason == (
        "Git remote not found: origin; add it with git remote add origin "
        "git@example.com:demo.git or update the P2P profile with p2p project remote configure"
    )


def test_sync_fetch_pull_and_push_delegate_to_git_adapters(tmp_path: Path) -> None:
    git = FakeGit(
        status=FakeGitStatus(is_repository=True, branch="main", is_clean=True),
        urls={"origin": "git@example.com:demo.git"},
    )
    service = _service(
        tmp_path,
        FakeProfile(mode="remote", provider="generic", remote="origin", url="git@example.com:demo.git"),
        git,
    )

    fetched = service.fetch()
    pulled = service.pull()
    pushed = service.push()

    assert fetched.status == "fetched"
    assert pulled.status == "pulled"
    assert pushed.status == "pushed"
    assert git.fetches == ["origin"]
    assert git.pulls == [("main", "origin")]
    assert git.pushes == [("main", "origin")]


def test_sync_pull_and_push_reject_dirty_worktree(tmp_path: Path) -> None:
    git = FakeGit(
        status=FakeGitStatus(is_repository=True, branch="main", is_clean=False),
        urls={"origin": "git@example.com:demo.git"},
    )
    service = _service(
        tmp_path,
        FakeProfile(mode="remote", provider="generic", remote="origin", url="git@example.com:demo.git"),
        git,
    )

    with pytest.raises(ValueError, match="Cannot pull with uncommitted changes"):
        service.pull()
    with pytest.raises(ValueError, match="Cannot push with uncommitted changes"):
        service.push()


def test_sync_pull_and_push_reject_detached_head(tmp_path: Path) -> None:
    git = FakeGit(
        status=FakeGitStatus(is_repository=True, branch=None, is_clean=True),
        urls={"origin": "git@example.com:demo.git"},
    )
    service = _service(
        tmp_path,
        FakeProfile(mode="remote", provider="generic", remote="origin", url="git@example.com:demo.git"),
        git,
    )

    with pytest.raises(ValueError, match="Cannot pull from detached HEAD"):
        service.pull()
    with pytest.raises(ValueError, match="Cannot push from detached HEAD"):
        service.push()


def test_sync_adapter_failures_preserve_error_messages(tmp_path: Path) -> None:
    profile = FakeProfile(mode="remote", provider="generic", remote="origin", url="git@example.com:demo.git")

    fetch_git = FakeGit(
        status=FakeGitStatus(is_repository=True, branch="main", is_clean=True),
        urls={"origin": "git@example.com:demo.git"},
        fetch_ok=False,
    )
    with pytest.raises(ValueError, match="Failed to fetch Git remote: origin"):
        _service(tmp_path, profile, fetch_git).fetch()

    pull_git = FakeGit(
        status=FakeGitStatus(is_repository=True, branch="main", is_clean=True),
        urls={"origin": "git@example.com:demo.git"},
        pull_ok=False,
    )
    with pytest.raises(ValueError, match="Failed to pull origin/main with fast-forward only"):
        _service(tmp_path, profile, pull_git).pull()

    push_git = FakeGit(
        status=FakeGitStatus(is_repository=True, branch="main", is_clean=True),
        urls={"origin": "git@example.com:demo.git"},
        push_ok=False,
    )
    with pytest.raises(ValueError, match="Failed to push main to origin"):
        _service(tmp_path, profile, push_git).push()

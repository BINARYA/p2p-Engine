from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SyncStatus:
    is_repository: bool
    branch: str | None
    is_clean: bool
    mode: str
    provider: str
    remote: str | None
    profile_url: str | None
    remote_url: str | None
    can_sync: bool
    reason: str


@dataclass(frozen=True)
class SyncResult:
    action: str
    status: str
    branch: str | None
    remote: str
    remote_url: str


class SyncService:
    def __init__(
        self,
        *,
        root: Path,
        remote_profile: Callable[[], object],
        git_status: Callable[[Path], object],
        remote_url: Callable[[Path, str], str | None],
        fetch_remote: Callable[[Path, str], bool],
        pull_branch: Callable[[Path, str, str], bool],
        push_branch: Callable[[Path, str, str], bool],
    ) -> None:
        self.root = root
        self.remote_profile = remote_profile
        self.git_status = git_status
        self.remote_url = remote_url
        self.fetch_remote = fetch_remote
        self.pull_branch = pull_branch
        self.push_branch = push_branch

    def status(self, remote: str | None = None) -> SyncStatus:
        profile = self.remote_profile()
        git_status = self.git_status(self.root)
        selected_remote = self.sync_remote(remote)
        resolved_remote_url = (
            self.remote_url(self.root, selected_remote)
            if getattr(git_status, "is_repository", False) and selected_remote
            else None
        )

        profile_mode = str(getattr(profile, "mode", "local"))
        profile_provider = str(getattr(profile, "provider", "local"))
        profile_remote = getattr(profile, "remote", None)
        profile_url = getattr(profile, "url", None)

        reason = "ready"
        can_sync = True
        if not getattr(git_status, "is_repository", False):
            can_sync = False
            if profile_mode == "remote":
                reason = (
                    "not a Git repository; initialize or clone the repository, then ensure "
                    f"Git remote {profile_remote or 'origin'} matches the P2P remote profile"
                )
            else:
                reason = "not a Git repository"
        elif profile_mode == "local" and remote is None and not profile_remote:
            origin_url = self.remote_url(self.root, "origin") if getattr(git_status, "is_repository", False) else None
            can_sync = False
            if origin_url:
                reason = (
                    "project remote profile is local, but Git remote origin exists; "
                    "run p2p project remote configure --mode remote --remote origin"
                )
            else:
                reason = "project remote profile is local"
        elif not selected_remote:
            can_sync = False
            reason = "no Git remote configured"
        elif resolved_remote_url is None:
            can_sync = False
            if profile_url:
                reason = (
                    f"Git remote not found: {selected_remote}; add it with "
                    f"git remote add {selected_remote} {profile_url} or update the P2P profile "
                    "with p2p project remote configure"
                )
            else:
                reason = (
                    f"Git remote not found: {selected_remote}; configure it locally or run "
                    "p2p project remote configure with --url"
                )
        elif profile_url and resolved_remote_url != profile_url:
            can_sync = False
            reason = (
                f"P2P remote profile URL does not match Git remote {selected_remote}; "
                "run p2p project remote configure with the intended URL"
            )

        return SyncStatus(
            is_repository=bool(getattr(git_status, "is_repository", False)),
            branch=getattr(git_status, "branch", None),
            is_clean=bool(getattr(git_status, "is_clean", False)),
            mode=profile_mode,
            provider=profile_provider,
            remote=selected_remote,
            profile_url=str(profile_url) if profile_url else None,
            remote_url=resolved_remote_url,
            can_sync=can_sync,
            reason=reason,
        )

    def fetch(self, remote: str | None = None) -> SyncResult:
        status = self.status(remote)
        selected_remote = self.require_sync_remote(status)
        if not self.fetch_remote(self.root, selected_remote):
            raise ValueError(f"Failed to fetch Git remote: {selected_remote}")
        return SyncResult(
            action="fetch",
            status="fetched",
            branch=status.branch,
            remote=selected_remote,
            remote_url=str(status.remote_url),
        )

    def pull(self, remote: str | None = None) -> SyncResult:
        status = self.status(remote)
        selected_remote = self.require_sync_remote(status)
        if not status.branch:
            raise ValueError("Cannot pull from detached HEAD")
        if not status.is_clean:
            raise ValueError("Cannot pull with uncommitted changes")
        if not self.pull_branch(self.root, status.branch, selected_remote):
            raise ValueError(f"Failed to pull {selected_remote}/{status.branch} with fast-forward only")
        return SyncResult(
            action="pull",
            status="pulled",
            branch=status.branch,
            remote=selected_remote,
            remote_url=str(status.remote_url),
        )

    def push(self, remote: str | None = None) -> SyncResult:
        status = self.status(remote)
        selected_remote = self.require_sync_remote(status)
        if not status.branch:
            raise ValueError("Cannot push from detached HEAD")
        if not status.is_clean:
            raise ValueError("Cannot push with uncommitted changes")
        if not self.push_branch(self.root, status.branch, selected_remote):
            raise ValueError(f"Failed to push {status.branch} to {selected_remote}")
        return SyncResult(
            action="push",
            status="pushed",
            branch=status.branch,
            remote=selected_remote,
            remote_url=str(status.remote_url),
        )

    def sync_remote(self, remote: str | None) -> str | None:
        if remote:
            return remote
        profile = self.remote_profile()
        profile_remote = getattr(profile, "remote", None)
        return str(profile_remote) if profile_remote else None

    def require_sync_remote(self, status: SyncStatus) -> str:
        if not status.is_repository:
            raise ValueError("Cannot sync outside a Git repository")
        if not status.remote:
            raise ValueError("Cannot sync project without a configured Git remote")
        if status.remote_url is None:
            raise ValueError(f"Cannot sync project: Git remote not found: {status.remote}")
        return status.remote

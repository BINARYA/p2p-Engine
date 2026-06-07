from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from p2p_engine.foundation.files import (
    read_yaml_mapping_or_default as _read_yaml_mapping,
    yaml_dump as _yaml_dump,
)


@dataclass(frozen=True)
class WorkBranch:
    work_id: str
    branch_name: str
    base_branch: str
    base_commit: str
    head_commit: str
    path: Path


@dataclass(frozen=True)
class WorkSubmit:
    work_id: str
    branch_name: str
    commit: str
    changed_files: list[str]
    path: Path


@dataclass(frozen=True)
class WorkReview:
    work_id: str
    branch_name: str
    review_commit: str
    metadata_commit: str
    path: Path


@dataclass(frozen=True)
class WorkPublish:
    work_id: str
    branch_name: str
    remote: str
    remote_url: str
    publish_commit: str
    path: Path


@dataclass(frozen=True)
class WorkAccept:
    work_id: str
    branch_name: str
    base_branch: str
    merge_commit: str
    path: Path


@dataclass(frozen=True)
class WorkAcceptConflict:
    work_id: str
    branch_name: str
    base_branch: str
    conflicted_files: list[str]
    path: Path


@dataclass(frozen=True)
class WorkFinalize:
    work_id: str
    base_branch: str
    remote: str
    remote_url: str
    finalize_commit: str
    path: Path


@dataclass(frozen=True)
class WorkCleanup:
    work_id: str
    branch_name: str
    base_branch: str
    remote: str
    cleanup_commit: str
    local_deleted: bool
    remote_deleted: bool
    path: Path


@dataclass(frozen=True)
class WorkReviewRequest:
    work_id: str
    branch_name: str
    provider: str
    remote: str
    remote_url: str
    metadata_commit: str
    suggested_next: str
    path: Path


@dataclass(frozen=True)
class WorkScan:
    scanned_branches: list[str]
    work_items: list[dict[str, object]]
    path: Path


def _file_has_conflict_markers(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return any(marker in text for marker in ("<<<<<<<", "=======", ">>>>>>>"))


def _review_request_suggestion(provider: str, remote_url: str, branch_name: str) -> str:
    if provider == "github":
        web_url = _github_web_url(remote_url)
        if web_url:
            return f"Open a GitHub pull request from {branch_name}: {web_url}/compare/{branch_name}?expand=1"
        return f"Open a GitHub pull request from branch {branch_name}."
    if provider == "gitlab":
        web_url = _gitlab_web_url(remote_url)
        if web_url:
            return f"Open a GitLab merge request from {branch_name}: {web_url}/-/merge_requests/new?merge_request[source_branch]={branch_name}"
        return f"Open a GitLab merge request from branch {branch_name}."
    return f"Ask for external review of remote branch {branch_name} at {remote_url}."


def _github_web_url(remote_url: str) -> str | None:
    match = re.match(r"git@github\.com:(?P<owner>[^/]+)/(?P<repo>.+?)(?:\.git)?$", remote_url)
    if match:
        return f"https://github.com/{match.group('owner')}/{match.group('repo')}"
    match = re.match(r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>.+?)(?:\.git)?$", remote_url)
    if match:
        return f"https://github.com/{match.group('owner')}/{match.group('repo')}"
    return None


def _gitlab_web_url(remote_url: str) -> str | None:
    match = re.match(r"git@gitlab\.com:(?P<path>.+?)(?:\.git)?$", remote_url)
    if match:
        return f"https://gitlab.com/{match.group('path')}"
    match = re.match(r"https://gitlab\.com/(?P<path>.+?)(?:\.git)?$", remote_url)
    if match:
        return f"https://gitlab.com/{match.group('path')}"
    return None


class WorkBranchService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_work_dir: Callable[[str], Path],
        list_local_work_branches: Callable[[Path], list[str]],
        list_files_at_ref: Callable[[Path, str, str], list[str]],
        read_file_at_ref: Callable[[Path, str, str], object | None],
        git_status: Callable[[Path], object],
        branch_exists: Callable[[Path, str], bool],
        head_commit: Callable[[Path], str | None],
        create_and_checkout_branch: Callable[[Path, str], bool],
        changed_files: Callable[[Path], list[str]],
        commit_all: Callable[[Path, str], str | None],
        remote_url: Callable[[Path, str], str | None],
        push_branch: Callable[[Path, str, str], bool],
        remote_profile: Callable[[], object],
        review_request_suggestion: Callable[[str, str, str], str] = _review_request_suggestion,
        checkout_branch: Callable[[Path, str], bool],
        merge_branch_no_commit: Callable[[Path, str], bool],
        conflicted_files: Callable[[Path], list[str]],
        merge_in_progress: Callable[[Path], bool],
        stage_all: Callable[[Path], bool],
        restore_path: Callable[[Path, str], bool],
        abort_merge: Callable[[Path], bool],
        show_work: Callable[[str], object],
        delete_local_branch: Callable[[Path, str], bool],
        delete_remote_branch: Callable[[Path, str, str], bool],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_work_dir = find_work_dir
        self.list_local_work_branches = list_local_work_branches
        self.list_files_at_ref = list_files_at_ref
        self.read_file_at_ref = read_file_at_ref
        self.git_status = git_status
        self.branch_exists = branch_exists
        self.head_commit = head_commit
        self.create_and_checkout_branch = create_and_checkout_branch
        self.changed_files = changed_files
        self.commit_all = commit_all
        self.remote_url = remote_url
        self.push_branch = push_branch
        self.remote_profile = remote_profile
        self.review_request_suggestion = review_request_suggestion
        self.checkout_branch = checkout_branch
        self.merge_branch_no_commit = merge_branch_no_commit
        self.conflicted_files = conflicted_files
        self.merge_in_progress = merge_in_progress
        self.stage_all = stage_all
        self.restore_path = restore_path
        self.abort_merge = abort_merge
        self.show_work = show_work
        self.delete_local_branch = delete_local_branch
        self.delete_remote_branch = delete_remote_branch

    def branch(self, work_id: str) -> WorkBranch:
        work_dir = self.find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "planned":
            raise ValueError(f"Work item must be planned before branching. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")
        if not branch_name.startswith("p2p/work/"):
            raise ValueError("Invalid Work manifest: git.branch_name must start with p2p/work/")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot create managed work branch outside a Git repository")
        current_branch = str(getattr(git_status, "branch", "") or "")
        if not current_branch:
            raise ValueError("Cannot create managed work branch from detached HEAD")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot create managed work branch with uncommitted changes")

        base_branch = str(git.get("base_branch") or current_branch)
        if current_branch != base_branch:
            raise ValueError(
                f"Cannot create managed work branch from {current_branch}; expected base branch {base_branch}"
            )
        if self.branch_exists(self.root, branch_name):
            raise ValueError(f"Managed work branch already exists: {branch_name}")

        base_commit = self.head_commit(self.root)
        if base_commit is None:
            raise ValueError("Cannot resolve current Git commit")
        if not self.create_and_checkout_branch(self.root, branch_name):
            raise ValueError(f"Failed to create managed work branch: {branch_name}")
        new_head_commit = self.head_commit(self.root)
        if new_head_commit is None:
            raise ValueError("Cannot resolve managed work branch commit")

        manifest["status"] = "branched"
        levels = manifest.get("managed_git_levels", [])
        if isinstance(levels, list):
            for level in levels:
                if isinstance(level, dict) and level.get("level") == 2:
                    level["enabled"] = True
        git["mode"] = "managed_branch"
        git["base_branch"] = base_branch
        git["base_commit"] = base_commit
        git["head_commit"] = new_head_commit
        git["current_branch"] = branch_name
        git["branched_at"] = date.today().isoformat()
        manifest["git"] = git
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        return WorkBranch(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            base_branch=base_branch,
            base_commit=base_commit,
            head_commit=new_head_commit,
            path=work_dir.relative_to(self.root),
        )

    def submit(self, work_id: str) -> WorkSubmit:
        work_dir = self.find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest_rel = manifest_path.relative_to(self.root).as_posix()
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "branched":
            raise ValueError(f"Work item must be branched before submit. Current status: {status}")

        source = manifest.get("source", {})
        change_id = str(source.get("change") if isinstance(source, dict) else "unknown")
        git = manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot submit managed work outside a Git repository")
        current_branch = getattr(git_status, "branch", None)
        if current_branch != branch_name:
            raise ValueError(f"Cannot submit managed work from {current_branch}; expected branch {branch_name}")

        changed = self.changed_files(self.root)
        if not changed:
            raise ValueError("Cannot submit managed work without changes")
        work_changes = [path for path in changed if path != manifest_rel]
        if not work_changes:
            raise ValueError("Cannot submit managed work with only Work manifest changes")

        manifest["status"] = "submitted"
        levels = manifest.get("managed_git_levels", [])
        if isinstance(levels, list):
            for level in levels:
                if isinstance(level, dict) and level.get("level") == 3:
                    level["enabled"] = True
        git["mode"] = "managed_submit"
        git["submitted_at"] = date.today().isoformat()
        manifest["git"] = git
        manifest["submission"] = {
            "mode": "local_commit",
            "pushed": False,
            "merged": False,
            "changed_files": changed,
            "work_changes": work_changes,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        message = f"P2P submit {work_id}: {change_id}"
        commit = self.commit_all(self.root, message)
        if commit is None:
            raise ValueError("Failed to create managed work submit commit")

        return WorkSubmit(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            commit=commit,
            changed_files=work_changes,
            path=work_dir.relative_to(self.root),
        )

    def review(self, work_id: str) -> WorkReview:
        work_dir = self.find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "submitted":
            raise ValueError(f"Work item must be submitted before review. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot request managed work review outside a Git repository")
        current_branch = getattr(git_status, "branch", None)
        if current_branch != branch_name:
            raise ValueError(
                f"Cannot request managed work review from {current_branch}; expected branch {branch_name}"
            )
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot request managed work review with uncommitted changes")

        review_commit = self.head_commit(self.root)
        if review_commit is None:
            raise ValueError("Cannot resolve managed work review commit")

        manifest["status"] = "review_requested"
        levels = manifest.get("managed_git_levels", [])
        if isinstance(levels, list):
            for level in levels:
                if isinstance(level, dict) and level.get("level") == 4:
                    level["enabled"] = True
        git["mode"] = "managed_review"
        git["review_requested_at"] = date.today().isoformat()
        manifest["git"] = git
        manifest["review"] = {
            "mode": "local_review",
            "review_commit": review_commit,
            "pushed": False,
            "pull_request": None,
            "merged": False,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        metadata_commit = self.commit_all(self.root, f"P2P review {work_id}")
        if metadata_commit is None:
            raise ValueError("Failed to create managed work review metadata commit")

        return WorkReview(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            review_commit=review_commit,
            metadata_commit=metadata_commit,
            path=work_dir.relative_to(self.root),
        )

    def publish(self, work_id: str, remote: str = "origin") -> WorkPublish:
        work_dir = self.find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "review_requested":
            raise ValueError(f"Work item must be review_requested before publish. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot publish managed work outside a Git repository")
        current_branch = getattr(git_status, "branch", None)
        if current_branch != branch_name:
            raise ValueError(f"Cannot publish managed work from {current_branch}; expected branch {branch_name}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot publish managed work with uncommitted changes")

        resolved_remote_url = self.remote_url(self.root, remote)
        if resolved_remote_url is None:
            raise ValueError(f"Cannot publish managed work: Git remote not found: {remote}")

        review = manifest.get("review", {})
        review_commit = str(review.get("review_commit") if isinstance(review, dict) else "")
        if not review_commit:
            raise ValueError("Invalid Work manifest: review.review_commit is required before publish")

        manifest["status"] = "published"
        git["mode"] = "managed_publish"
        git["published_at"] = date.today().isoformat()
        manifest["git"] = git
        manifest["publish"] = {
            "mode": "remote_branch",
            "remote": remote,
            "remote_url": resolved_remote_url,
            "remote_branch": branch_name,
            "review_commit": review_commit,
            "pull_request": None,
            "merged": False,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        publish_commit = self.commit_all(self.root, f"P2P publish {work_id}")
        if publish_commit is None:
            raise ValueError("Failed to create managed work publish metadata commit")
        if not self.push_branch(self.root, branch_name, remote):
            raise ValueError(f"Failed to push managed work branch to {remote}: {branch_name}")

        return WorkPublish(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            remote=remote,
            remote_url=resolved_remote_url,
            publish_commit=publish_commit,
            path=work_dir.relative_to(self.root),
        )

    def request_external_review(
        self,
        work_id: str,
        provider: str | None = None,
    ) -> WorkReviewRequest:
        work_dir = self.find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "published":
            raise ValueError(f"Work item must be published before external review request. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot request external work review outside a Git repository")
        current_branch = getattr(git_status, "branch", None)
        if current_branch != branch_name:
            raise ValueError(
                f"Cannot request external work review from {current_branch}; expected branch {branch_name}"
            )
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot request external work review with uncommitted changes")

        publish = manifest.get("publish", {})
        if not isinstance(publish, dict):
            raise ValueError("Invalid Work manifest: publish metadata is required before external review request")
        remote = str(publish.get("remote") or "origin")
        resolved_remote_url = str(publish.get("remote_url") or "")
        if not resolved_remote_url:
            resolved_remote_url = self.remote_url(self.root, remote) or ""
        if not resolved_remote_url:
            raise ValueError(f"Cannot request external work review: Git remote not found: {remote}")

        profile = self.remote_profile()
        profile_url = str(getattr(profile, "url", "") or "")
        if profile_url:
            resolved_remote_url = profile_url
        selected_provider = (provider or getattr(profile, "provider", None) or "generic").strip().lower()
        if selected_provider == "local":
            selected_provider = "generic"
        if selected_provider not in {"generic", "github", "gitlab"}:
            raise ValueError("External review provider must be generic, github, or gitlab")

        suggested_next = self.review_request_suggestion(
            selected_provider,
            resolved_remote_url,
            branch_name,
        )
        manifest["external_review"] = {
            "mode": "provider_advisory",
            "provider": selected_provider,
            "remote": remote,
            "remote_url": resolved_remote_url,
            "remote_branch": branch_name,
            "opens_external_request": False,
            "requested_at": date.today().isoformat(),
            "suggested_next": suggested_next,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        metadata_commit = self.commit_all(self.root, f"P2P request review {work_id}")
        if metadata_commit is None:
            raise ValueError("Failed to create external review request metadata commit")

        return WorkReviewRequest(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            provider=selected_provider,
            remote=remote,
            remote_url=resolved_remote_url,
            metadata_commit=metadata_commit,
            suggested_next=suggested_next,
            path=work_dir.relative_to(self.root),
        )

    def accept(self, work_id: str) -> WorkAccept | WorkAcceptConflict:
        work_dir = self.find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        local_manifest = _read_yaml_mapping(manifest_path, default={})
        git = local_manifest.get("git", {})
        if not isinstance(git, dict):
            raise ValueError("Invalid Work manifest: git must be a mapping")
        branch_name = str(git.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid Work manifest: git.branch_name is required")
        base_branch = str(git.get("base_branch") or "main")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot accept managed work outside a Git repository")
        current_branch = getattr(git_status, "branch", None)
        if current_branch != base_branch:
            raise ValueError(f"Cannot accept managed work from {current_branch}; expected base branch {base_branch}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot accept managed work with uncommitted changes")
        if not self.branch_exists(self.root, branch_name):
            raise ValueError(f"Managed work branch not found: {branch_name}")

        manifest_rel = manifest_path.relative_to(self.root).as_posix()
        branch_file = self.read_file_at_ref(self.root, branch_name, manifest_rel)
        if branch_file is None:
            raise ValueError(f"Managed work branch does not contain manifest: {manifest_rel}")
        try:
            branch_manifest = yaml.safe_load(str(getattr(branch_file, "content", ""))) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid Work manifest on branch {branch_name}") from exc
        if not isinstance(branch_manifest, dict):
            raise ValueError(f"Invalid Work manifest on branch {branch_name}")
        status = str(branch_manifest.get("status") or "unknown")
        if status != "published":
            raise ValueError(f"Work item must be published before accept. Current status: {status}")

        if not self.merge_branch_no_commit(self.root, branch_name):
            conflicts = self.conflicted_files(self.root)
            if not conflicts:
                raise ValueError(f"Failed to merge managed work branch: {branch_name}")
            conflict_manifest = dict(branch_manifest)
            conflict_git = conflict_manifest.get("git", {})
            if not isinstance(conflict_git, dict):
                conflict_git = {}
            conflict_manifest["status"] = "merge_conflict"
            conflict_git["mode"] = "managed_accept_conflict"
            conflict_git["merge_conflict_at"] = date.today().isoformat()
            conflict_manifest["git"] = conflict_git
            conflict_manifest["merge_conflict"] = {
                "source_branch": branch_name,
                "base_branch": base_branch,
                "conflicted_files": conflicts,
                "continue_command": f"p2p work accept --continue {work_id}",
                "abort_command": f"p2p work accept --abort {work_id}",
            }
            manifest_path.write_text(_yaml_dump(conflict_manifest), encoding="utf-8")
            return WorkAcceptConflict(
                work_id=str(conflict_manifest.get("work_id") or work_id),
                branch_name=branch_name,
                base_branch=base_branch,
                conflicted_files=conflicts,
                path=work_dir.relative_to(self.root),
            )

        merged_manifest = _read_yaml_mapping(manifest_path, default={})
        merged_git = merged_manifest.get("git", {})
        if not isinstance(merged_git, dict):
            merged_git = {}
        merged_manifest["status"] = "accepted"
        levels = merged_manifest.get("managed_git_levels", [])
        if isinstance(levels, list):
            for level in levels:
                if isinstance(level, dict) and level.get("level") == 5:
                    level["enabled"] = True
        merged_git["mode"] = "managed_accept"
        merged_git["accepted_at"] = date.today().isoformat()
        merged_manifest["git"] = merged_git
        merged_manifest["acceptance"] = {
            "mode": "local_merge",
            "source_branch": branch_name,
            "merged_into": base_branch,
            "pushed": False,
            "cleanup": False,
        }
        manifest_path.write_text(_yaml_dump(merged_manifest), encoding="utf-8")

        merge_commit = self.commit_all(self.root, f"P2P accept {work_id}")
        if merge_commit is None:
            raise ValueError("Failed to create managed work accept merge commit")
        if not self.checkout_branch(self.root, base_branch):
            raise ValueError(f"Failed to stay on base branch after accept: {base_branch}")

        return WorkAccept(
            work_id=str(merged_manifest.get("work_id") or work_id),
            branch_name=branch_name,
            base_branch=base_branch,
            merge_commit=merge_commit,
            path=work_dir.relative_to(self.root),
        )

    def continue_accept(self, work_id: str) -> WorkAccept:
        work_dir = self.find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "merge_conflict":
            raise ValueError(f"Work item must be merge_conflict before accept --continue. Current status: {status}")
        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot continue managed work accept outside a Git repository")
        if not self.merge_in_progress(self.root):
            raise ValueError("Cannot continue managed work accept: no merge is in progress")
        unresolved = [path for path in self.conflicted_files(self.root) if _file_has_conflict_markers(self.root / path)]
        if unresolved:
            raise ValueError("Cannot continue managed work accept with unresolved conflicts: " + ", ".join(unresolved))
        self.stage_all(self.root)
        conflicts = self.conflicted_files(self.root)
        if conflicts:
            raise ValueError("Cannot continue managed work accept with unresolved conflicts: " + ", ".join(conflicts))

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            git = {}
        conflict = manifest.get("merge_conflict", {})
        if not isinstance(conflict, dict):
            conflict = {}
        branch_name = str(conflict.get("source_branch") or git.get("branch_name") or "")
        base_branch = str(conflict.get("base_branch") or git.get("base_branch") or getattr(git_status, "branch", None) or "main")
        manifest["status"] = "accepted"
        levels = manifest.get("managed_git_levels", [])
        if isinstance(levels, list):
            for level in levels:
                if isinstance(level, dict) and level.get("level") == 5:
                    level["enabled"] = True
        git["mode"] = "managed_accept"
        git["accepted_at"] = date.today().isoformat()
        manifest["git"] = git
        manifest.pop("merge_conflict", None)
        manifest["acceptance"] = {
            "mode": "local_merge",
            "source_branch": branch_name,
            "merged_into": base_branch,
            "pushed": False,
            "cleanup": False,
            "resolved_conflict": True,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")
        merge_commit = self.commit_all(self.root, f"P2P accept {work_id}")
        if merge_commit is None:
            raise ValueError("Failed to create managed work accept merge commit")
        return WorkAccept(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            base_branch=base_branch,
            merge_commit=merge_commit,
            path=work_dir.relative_to(self.root),
        )

    def abort_accept(self, work_id: str) -> object:
        work_dir = self.find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "merge_conflict":
            raise ValueError(f"Work item must be merge_conflict before accept --abort. Current status: {status}")
        conflict = manifest.get("merge_conflict", {})
        if not isinstance(conflict, dict):
            conflict = {}
        manifest_rel = manifest_path.relative_to(self.root).as_posix()
        if self.merge_in_progress(self.root):
            self.restore_path(self.root, manifest_rel)
            if not self.abort_merge(self.root):
                raise ValueError("Failed to abort managed work merge")
        restored = _read_yaml_mapping(manifest_path, default=manifest)
        restored["status"] = "published"
        git = restored.get("git", {})
        if not isinstance(git, dict):
            git = {}
        git["mode"] = "managed_publish"
        git["accept_aborted_at"] = date.today().isoformat()
        restored["git"] = git
        restored.pop("merge_conflict", None)
        restored["acceptance_abort"] = {
            "source_branch": str(conflict.get("source_branch") or git.get("branch_name") or ""),
            "base_branch": str(conflict.get("base_branch") or git.get("base_branch") or "main"),
            "aborted": True,
        }
        manifest_path.write_text(_yaml_dump(restored), encoding="utf-8")
        if self.commit_all(self.root, f"P2P abort accept {work_id}") is None:
            raise ValueError("Failed to create managed work accept abort commit")
        return self.show_work(work_id)

    def finalize(self, work_id: str, remote: str = "origin") -> WorkFinalize:
        work_dir = self.find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "accepted":
            raise ValueError(f"Work item must be accepted before finalize. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            git = {}
        acceptance = manifest.get("acceptance", {})
        if not isinstance(acceptance, dict):
            acceptance = {}
        base_branch = str(acceptance.get("merged_into") or git.get("base_branch") or "main")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot finalize managed work outside a Git repository")
        current_branch = getattr(git_status, "branch", None)
        if current_branch != base_branch:
            raise ValueError(f"Cannot finalize managed work from {current_branch}; expected base branch {base_branch}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot finalize managed work with uncommitted changes")

        resolved_remote_url = self.remote_url(self.root, remote)
        if resolved_remote_url is None:
            raise ValueError(f"Cannot finalize managed work: Git remote not found: {remote}")

        manifest["status"] = "finalized"
        git["mode"] = "managed_finalize"
        git["finalized_at"] = date.today().isoformat()
        manifest["git"] = git
        acceptance["pushed"] = True
        manifest["acceptance"] = acceptance
        manifest["finalize"] = {
            "mode": "base_branch_push",
            "remote": remote,
            "remote_url": resolved_remote_url,
            "base_branch": base_branch,
            "cleanup": False,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        finalize_commit = self.commit_all(self.root, f"P2P finalize {work_id}")
        if finalize_commit is None:
            raise ValueError("Failed to create managed work finalize commit")
        if not self.push_branch(self.root, base_branch, remote):
            raise ValueError(f"Failed to push base branch to {remote}: {base_branch}")

        return WorkFinalize(
            work_id=str(manifest.get("work_id") or work_id),
            base_branch=base_branch,
            remote=remote,
            remote_url=resolved_remote_url,
            finalize_commit=finalize_commit,
            path=work_dir.relative_to(self.root),
        )

    def cleanup(self, work_id: str, delete_remote: bool = False, remote: str = "origin") -> WorkCleanup:
        work_dir = self.find_work_dir(work_id)
        manifest_path = work_dir / "manifest.yml"
        manifest = _read_yaml_mapping(manifest_path, default={})
        status = str(manifest.get("status") or "unknown")
        if status != "finalized":
            raise ValueError(f"Work item must be finalized before cleanup. Current status: {status}")

        git = manifest.get("git", {})
        if not isinstance(git, dict):
            git = {}
        finalize = manifest.get("finalize", {})
        if not isinstance(finalize, dict):
            finalize = {}
        publish = manifest.get("publish", {})
        if not isinstance(publish, dict):
            publish = {}
        acceptance = manifest.get("acceptance", {})
        if not isinstance(acceptance, dict):
            acceptance = {}

        branch_name = str(
            acceptance.get("source_branch")
            or publish.get("remote_branch")
            or git.get("branch_name")
            or ""
        )
        if not branch_name:
            raise ValueError("Invalid Work manifest: managed branch is required before cleanup")
        base_branch = str(finalize.get("base_branch") or acceptance.get("merged_into") or git.get("base_branch") or "main")
        remote = str(finalize.get("remote") or publish.get("remote") or remote)

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot cleanup managed work outside a Git repository")
        current_branch = getattr(git_status, "branch", None)
        if current_branch != base_branch:
            raise ValueError(f"Cannot cleanup managed work from {current_branch}; expected base branch {base_branch}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot cleanup managed work with uncommitted changes")
        if not self.branch_exists(self.root, branch_name):
            raise ValueError(f"Managed work branch not found: {branch_name}")

        resolved_remote_url = self.remote_url(self.root, remote)
        if resolved_remote_url is None:
            raise ValueError(f"Cannot cleanup managed work: Git remote not found: {remote}")

        if not self.delete_local_branch(self.root, branch_name):
            raise ValueError(f"Failed to delete local managed work branch: {branch_name}")
        remote_deleted = False
        if delete_remote:
            if not self.delete_remote_branch(self.root, branch_name, remote):
                raise ValueError(f"Failed to delete remote managed work branch from {remote}: {branch_name}")
            remote_deleted = True

        manifest["status"] = "cleaned"
        git["mode"] = "managed_cleanup"
        git["cleaned_at"] = date.today().isoformat()
        manifest["git"] = git
        finalize["cleanup"] = True
        manifest["finalize"] = finalize
        manifest["cleanup"] = {
            "mode": "branch_cleanup",
            "source_branch": branch_name,
            "base_branch": base_branch,
            "remote": remote,
            "remote_url": resolved_remote_url,
            "local_deleted": True,
            "remote_deleted": remote_deleted,
        }
        manifest_path.write_text(_yaml_dump(manifest), encoding="utf-8")

        cleanup_commit = self.commit_all(self.root, f"P2P cleanup {work_id}")
        if cleanup_commit is None:
            raise ValueError("Failed to create managed work cleanup commit")
        if not self.push_branch(self.root, base_branch, remote):
            raise ValueError(f"Failed to push cleanup metadata to {remote}: {base_branch}")

        return WorkCleanup(
            work_id=str(manifest.get("work_id") or work_id),
            branch_name=branch_name,
            base_branch=base_branch,
            remote=remote,
            cleanup_commit=cleanup_commit,
            local_deleted=True,
            remote_deleted=remote_deleted,
            path=work_dir.relative_to(self.root),
        )

    def scan(self) -> WorkScan:
        branches = self.list_local_work_branches(self.root)
        items: list[dict[str, object]] = []
        for branch in branches:
            manifest_paths = [
                path
                for path in self.list_files_at_ref(self.root, branch, ".p2p/work")
                if re.match(r"\.p2p/work/WORK-\d{3}/manifest\.yml$", path)
            ]
            for manifest_path in manifest_paths:
                git_file = self.read_file_at_ref(self.root, branch, manifest_path)
                if git_file is None:
                    continue
                try:
                    manifest = yaml.safe_load(str(getattr(git_file, "content", ""))) or {}
                except yaml.YAMLError:
                    continue
                if not isinstance(manifest, dict):
                    continue
                source = manifest.get("source", {})
                handoff = manifest.get("handoff", {})
                git = manifest.get("git", {})
                items.append(
                    {
                        "work_id": str(manifest.get("work_id") or Path(manifest_path).parent.name),
                        "status": str(manifest.get("status") or "unknown"),
                        "change": str(source.get("change") if isinstance(source, dict) else "unknown"),
                        "target": str(handoff.get("target") if isinstance(handoff, dict) else "none"),
                        "branch": branch,
                        "branch_name": str(git.get("branch_name") if isinstance(git, dict) else branch),
                        "path": manifest_path,
                    }
                )
        registry_path = self.p2p_dir / "registries" / "work.yml"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            _yaml_dump({"scanned_branches": branches, "work_items": items}),
            encoding="utf-8",
        )
        return WorkScan(
            scanned_branches=branches,
            work_items=items,
            path=registry_path.relative_to(self.root),
        )

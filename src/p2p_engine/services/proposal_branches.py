from __future__ import annotations

import hashlib
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from p2p_engine.foundation.files import (
    read_yaml_mapping_or_default as _read_yaml_mapping,
    slugify as _foundation_slugify,
    yaml_dump as _yaml_dump,
)
from p2p_engine.foundation.markdown import read_title


@dataclass(frozen=True)
class ProposalBranchDetail:
    proposal_id: str
    status: str
    branch_name: str
    base_branch: str
    actor: str
    branch_hash16: str
    remote: str | None
    remote_url: str | None
    path: Path
    metadata: dict[str, object]


@dataclass(frozen=True)
class ProposalBranchScan:
    scanned_branches: list[str]
    proposals: list[dict[str, object]]
    path: Path


@dataclass(frozen=True)
class ProposalMerge:
    proposal_id: str
    branch_name: str
    base_branch: str
    merge_commit: str
    path: Path


@dataclass(frozen=True)
class ProposalMergeConflict:
    proposal_id: str
    branch_name: str
    base_branch: str
    conflicted_files: list[str]
    path: Path


@dataclass(frozen=True)
class ProposalFinalize:
    proposal_id: str
    branch_name: str
    base_branch: str
    remote: str
    remote_url: str
    finalize_commit: str
    path: Path


@dataclass(frozen=True)
class ProposalCleanup:
    proposal_id: str
    branch_name: str
    base_branch: str
    remote: str
    remote_url: str
    cleanup_commit: str
    local_deleted: bool
    remote_deleted: bool
    path: Path


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _slugify(value: str) -> str:
    return _foundation_slugify(value.strip(), fallback="")


def _clean_proposal_title(title: str, proposal_id: str) -> str:
    cleaned = re.sub(rf"^{re.escape(proposal_id)}\s*[-—]\s*", "", title).strip()
    return cleaned or title


def _branch_hash16(proposal_id: str, title: str, actor_slug: str, base_commit: str) -> str:
    source = f"{proposal_id}\n{title}\n{actor_slug}\n{base_commit}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def _proposal_branch_name(proposal_id: str, title: str, actor_slug: str, branch_hash16: str) -> str:
    title_slug = _slugify(title)[:48].strip("-") or "proposal"
    return f"p2p/proposal/{proposal_id}-{title_slug}-{actor_slug}-{branch_hash16}"


def _proposal_id_from_dir_name(name: str) -> str | None:
    match = re.match(r"^(PROP-\d{3})-", name)
    return match.group(1) if match else None


def _proposal_id_from_branch_name(name: str) -> str | None:
    match = re.search(r"/(PROP-\d{3})-", name)
    return match.group(1) if match else None


def _review_request_suggestion(provider: str, remote_url: str, branch_name: str) -> str:
    if provider == "github":
        return f"Open a GitHub pull request from `{branch_name}` against the base branch for {remote_url}."
    if provider == "gitlab":
        return f"Open a GitLab merge request from `{branch_name}` against the base branch for {remote_url}."
    return (
        f"Share branch `{branch_name}` from remote {remote_url} for external review; "
        "record the review result before merge."
    )


def _file_has_conflict_markers(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return "<<<<<<<" in text or "=======" in text or ">>>>>>>" in text


def _detail_from_metadata(proposal_id: str, metadata: dict[str, object], path: Path) -> ProposalBranchDetail:
    return ProposalBranchDetail(
        proposal_id=str(metadata.get("proposal_id") or proposal_id),
        status=str(metadata.get("status") or "unknown"),
        branch_name=str(metadata.get("branch_name") or ""),
        base_branch=str(metadata.get("base_branch") or ""),
        actor=str(metadata.get("actor") or ""),
        branch_hash16=str(metadata.get("branch_hash16") or ""),
        remote=str(metadata.get("remote")) if metadata.get("remote") else None,
        remote_url=str(metadata.get("remote_url")) if metadata.get("remote_url") else None,
        path=path,
        metadata=metadata,
    )


class ProposalBranchService:
    def __init__(
        self,
        *,
        root: Path,
        p2p_dir: Path,
        find_proposal_dir: Callable[[str], Path],
        git_status: Callable[[Path], object],
        checkout_branch: Callable[[Path, str], bool],
        head_commit: Callable[[Path], str | None],
        branch_exists: Callable[[Path, str], bool],
        create_and_checkout_branch: Callable[[Path, str], bool],
        rename_current_branch: Callable[[Path, str], bool],
        commit_all: Callable[[Path, str], str | None],
        remote_profile: Callable[[], object],
        remote_url: Callable[[Path, str], str | None],
        fetch_remote: Callable[[Path, str], bool],
        push_branch: Callable[[Path, str, str], bool],
        merge_branch_no_commit: Callable[[Path, str], bool],
        conflicted_files: Callable[[Path], list[str]],
        merge_in_progress: Callable[[Path], bool],
        stage_all: Callable[[Path], bool],
        restore_path: Callable[[Path, str], bool],
        abort_merge: Callable[[Path], bool],
        delete_local_branch: Callable[[Path, str], bool],
        delete_local_branch_force: Callable[[Path, str], bool],
        delete_remote_branch: Callable[[Path, str, str], bool],
        list_local_proposal_branches: Callable[[Path], list[str]],
        list_remote_proposal_branches: Callable[[Path, str], list[str]],
        list_files_at_ref: Callable[[Path, str, str], list[str]],
        read_file_at_ref: Callable[[Path, str, str], object | None],
    ) -> None:
        self.root = root
        self.p2p_dir = p2p_dir
        self.find_proposal_dir = find_proposal_dir
        self.git_status = git_status
        self.checkout_branch = checkout_branch
        self.head_commit = head_commit
        self.branch_exists = branch_exists
        self.create_and_checkout_branch = create_and_checkout_branch
        self.rename_current_branch = rename_current_branch
        self.commit_all = commit_all
        self.remote_profile = remote_profile
        self.remote_url = remote_url
        self.fetch_remote = fetch_remote
        self.push_branch = push_branch
        self.merge_branch_no_commit = merge_branch_no_commit
        self.conflicted_files = conflicted_files
        self.merge_in_progress = merge_in_progress
        self.stage_all = stage_all
        self.restore_path = restore_path
        self.abort_merge = abort_merge
        self.delete_local_branch = delete_local_branch
        self.delete_local_branch_force = delete_local_branch_force
        self.delete_remote_branch = delete_remote_branch
        self.list_local_proposal_branches = list_local_proposal_branches
        self.list_remote_proposal_branches = list_remote_proposal_branches
        self.list_files_at_ref = list_files_at_ref
        self.read_file_at_ref = read_file_at_ref

    def branch(
        self,
        proposal_id: str,
        actor: str = "local",
        base_branch: str | None = None,
        allow_proposal_base: bool = False,
    ) -> ProposalBranchDetail:
        proposal_dir = self.find_proposal_dir(proposal_id)
        proposal_text = _read_optional(proposal_dir / "proposal.md")
        title = _clean_proposal_title(read_title(proposal_text) or proposal_id, proposal_id)
        actor_slug = _slugify(actor) or "local"

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot create managed proposal branch outside a Git repository")
        if not getattr(git_status, "branch", None):
            raise ValueError("Cannot create managed proposal branch from detached HEAD")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot create managed proposal branch with uncommitted changes")

        selected_base = (base_branch or str(getattr(git_status, "branch", ""))).strip()
        if not selected_base:
            raise ValueError("Base branch is required")
        if selected_base.startswith("p2p/proposal/") and not allow_proposal_base:
            raise ValueError("Cannot create managed proposal branch from another proposal branch without explicit allow_proposal_base")
        if getattr(git_status, "branch", None) != selected_base:
            if not self.checkout_branch(self.root, selected_base):
                raise ValueError(f"Failed to check out base branch: {selected_base}")
            git_status = self.git_status(self.root)
            if not getattr(git_status, "is_clean", False):
                raise ValueError("Cannot create managed proposal branch with uncommitted changes")
        base_commit = self.head_commit(self.root)
        if base_commit is None:
            raise ValueError("Cannot resolve current Git commit")
        branch_hash16 = _branch_hash16(proposal_id, title, actor_slug, base_commit)
        branch_name = _proposal_branch_name(proposal_id, title, actor_slug, branch_hash16)
        if self.branch_exists(self.root, branch_name):
            raise ValueError(f"Managed proposal branch already exists: {branch_name}")

        if not self.create_and_checkout_branch(self.root, branch_name):
            raise ValueError(f"Failed to create managed proposal branch: {branch_name}")
        head = self.head_commit(self.root)
        if head is None:
            raise ValueError("Cannot resolve managed proposal branch commit")

        metadata = {
            "proposal_id": proposal_id,
            "status": "branched",
            "branch_name": branch_name,
            "branch_hash16": branch_hash16,
            "actor": actor,
            "actor_slug": actor_slug,
            "base_branch": selected_base,
            "base_commit": base_commit,
            "head_commit": head,
            "created_at": date.today().isoformat(),
            "remote": None,
            "remote_url": None,
            "remote_branch": None,
        }
        metadata_path = proposal_dir / "branch.yml"
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        if self.commit_all(self.root, f"P2P proposal branch {proposal_id}") is None:
            raise ValueError("Failed to create managed proposal branch metadata commit")
        return self.show(proposal_id)

    def publish(
        self,
        proposal_id: str,
        remote: str | None = None,
        *,
        auto_renumber: bool = False,
    ) -> ProposalBranchDetail:
        proposal_dir, metadata, metadata_path = self.metadata(proposal_id)
        status = str(metadata.get("status") or "unknown")
        if status not in {"branched", "revised", "review_requested"}:
            raise ValueError(f"Proposal branch must be branched, revised, or review_requested before publish. Current status: {status}")
        branch_name = str(metadata.get("branch_name") or "")
        if not branch_name:
            raise ValueError("Invalid proposal branch metadata: branch_name is required")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot publish managed proposal branch outside a Git repository")
        if getattr(git_status, "branch", None) != branch_name:
            raise ValueError(f"Cannot publish managed proposal branch from {getattr(git_status, 'branch', None)}; expected branch {branch_name}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot publish managed proposal branch with uncommitted changes")

        profile = self.remote_profile()
        selected_remote = remote or getattr(profile, "remote", None) or "origin"
        resolved_remote_url = self.remote_url(self.root, selected_remote)
        if resolved_remote_url is None:
            raise ValueError(f"Cannot publish managed proposal branch: Git remote not found: {selected_remote}")

        if not self.fetch_remote(self.root, selected_remote):
            raise ValueError(f"Failed to fetch Git remote before proposal publish: {selected_remote}")
        remote_ids = self.remote_proposal_ids(selected_remote, str(metadata.get("base_branch") or "main"))
        if proposal_id in remote_ids:
            if not auto_renumber:
                raise ValueError(
                    f"Proposal ID collision detected on remote: {proposal_id}. "
                    f"Run `p2p proposal publish {proposal_id} --auto-renumber` to allocate the next available ID."
                )
            proposal_id, proposal_dir, metadata, metadata_path = self.auto_renumber(
                proposal_id=proposal_id,
                metadata=metadata,
                remote_ids=remote_ids,
            )
            branch_name = str(metadata.get("branch_name") or "")
            if not branch_name:
                raise ValueError("Invalid proposal branch metadata after auto-renumber: branch_name is required")
            git_status = self.git_status(self.root)
            if getattr(git_status, "branch", None) != branch_name:
                raise ValueError(
                    f"Cannot publish auto-renumbered proposal branch from {getattr(git_status, 'branch', None)}; expected branch {branch_name}"
                )
            if not getattr(git_status, "is_clean", False):
                raise ValueError("Cannot publish auto-renumbered proposal branch with uncommitted changes")
            if proposal_id in self.remote_proposal_ids(selected_remote, str(metadata.get("base_branch") or "main")):
                raise ValueError(f"Proposal ID collision remains after auto-renumber: {proposal_id}")

        metadata["status"] = "published"
        metadata["remote"] = selected_remote
        metadata["remote_url"] = resolved_remote_url
        metadata["remote_branch"] = branch_name
        metadata["published_at"] = date.today().isoformat()
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        if self.commit_all(self.root, f"P2P proposal publish {proposal_id}") is None:
            raise ValueError("Failed to create managed proposal publish metadata commit")
        if not self.push_branch(self.root, branch_name, selected_remote):
            raise ValueError(f"Failed to push managed proposal branch to {selected_remote}: {branch_name}")
        return self.show(proposal_id)

    def request_review(self, proposal_id: str, provider: str | None = None) -> ProposalBranchDetail:
        _proposal_dir, metadata, metadata_path = self.metadata(proposal_id)
        status = str(metadata.get("status") or "unknown")
        if status != "published":
            raise ValueError(f"Proposal branch must be published before request-review. Current status: {status}")
        branch_name = str(metadata.get("branch_name") or "")
        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot request managed proposal review outside a Git repository")
        if getattr(git_status, "branch", None) != branch_name:
            raise ValueError(f"Cannot request managed proposal review from {getattr(git_status, 'branch', None)}; expected branch {branch_name}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot request managed proposal review with uncommitted changes")

        profile = self.remote_profile()
        remote = str(metadata.get("remote") or getattr(profile, "remote", None) or "origin")
        resolved_remote_url = str(metadata.get("remote_url") or self.remote_url(self.root, remote) or "")
        if not resolved_remote_url:
            raise ValueError(f"Cannot request managed proposal review: Git remote not found: {remote}")
        selected_provider = (provider or getattr(profile, "provider", None) or "generic").strip().lower()
        if selected_provider == "local":
            selected_provider = "generic"
        if selected_provider not in {"generic", "github", "gitlab"}:
            raise ValueError("Proposal review provider must be generic, github, or gitlab")

        metadata["status"] = "review_requested"
        metadata["review"] = {
            "mode": "provider_advisory",
            "provider": selected_provider,
            "remote": remote,
            "remote_url": resolved_remote_url,
            "remote_branch": branch_name,
            "opens_external_request": False,
            "requested_at": date.today().isoformat(),
            "suggested_next": _review_request_suggestion(selected_provider, resolved_remote_url, branch_name),
        }
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        if self.commit_all(self.root, f"P2P proposal request review {proposal_id}") is None:
            raise ValueError("Failed to create managed proposal review metadata commit")
        return self.show(proposal_id)

    def retire(self, proposal_id: str, reason: str) -> ProposalBranchDetail:
        reason = reason.strip()
        if not reason:
            raise ValueError("Proposal branch retire reason is required")
        _proposal_dir, metadata, metadata_path = self.metadata(proposal_id)
        status = str(metadata.get("status") or "unknown")
        if status in {"merged", "finalized", "retired"}:
            raise ValueError(f"Proposal branch cannot be retired from status: {status}")
        branch_name = str(metadata.get("branch_name") or "")
        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot retire managed proposal branch outside a Git repository")
        if getattr(git_status, "branch", None) != branch_name:
            raise ValueError(f"Cannot retire managed proposal branch from {getattr(git_status, 'branch', None)}; expected branch {branch_name}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot retire managed proposal branch with uncommitted changes")

        metadata["status"] = "retired"
        metadata["retirement"] = {
            "reason": reason,
            "retired_at": date.today().isoformat(),
        }
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        if self.commit_all(self.root, f"P2P proposal retire {proposal_id}") is None:
            raise ValueError("Failed to create managed proposal retire metadata commit")
        return self.show(proposal_id)

    def accept(self, proposal_id: str, reason: str) -> ProposalBranchDetail:
        reason = reason.strip()
        if not reason:
            raise ValueError("Proposal branch accept reason is required")
        return self.decide(proposal_id, "accepted", reason)

    def reject(self, proposal_id: str, reason: str) -> ProposalBranchDetail:
        reason = reason.strip()
        if not reason:
            raise ValueError("Proposal branch reject reason is required")
        return self.decide(proposal_id, "rejected", reason)

    def decide(self, proposal_id: str, outcome: str, reason: str) -> ProposalBranchDetail:
        proposal_dir, metadata, metadata_path = self.metadata(proposal_id)
        status = str(metadata.get("status") or "unknown")
        if status not in {"published", "review_requested"}:
            raise ValueError(
                f"Proposal branch must be published or review_requested before {outcome}. Current status: {status}"
            )
        branch_name = str(metadata.get("branch_name") or "")
        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError(f"Cannot {outcome} managed proposal branch outside a Git repository")
        if getattr(git_status, "branch", None) != branch_name:
            raise ValueError(f"Cannot {outcome} managed proposal branch from {getattr(git_status, 'branch', None)}; expected branch {branch_name}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError(f"Cannot {outcome} managed proposal branch with uncommitted changes")

        metadata["status"] = outcome
        metadata["branch_decision"] = {
            "outcome": outcome,
            "reason": reason,
            "decided_at": date.today().isoformat(),
            "governance_decision": True,
        }
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        verb = "accept" if outcome == "accepted" else "reject"
        if self.commit_all(self.root, f"P2P proposal branch {verb} {proposal_id}") is None:
            raise ValueError(f"Failed to create managed proposal branch {verb} metadata commit")
        return _detail_from_metadata(proposal_id, metadata, proposal_dir.relative_to(self.root))

    def merge(self, proposal_id: str) -> ProposalMerge | ProposalMergeConflict:
        branch_name, metadata, branch_metadata_path = self.metadata_from_local_ref(proposal_id)
        status = str(metadata.get("status") or "unknown")
        if status not in {"published", "review_requested", "accepted"}:
            raise ValueError(
                f"Proposal branch must be published, review_requested, or accepted before merge. Current status: {status}"
            )
        base_branch = str(metadata.get("base_branch") or "main")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot merge managed proposal branch outside a Git repository")
        if getattr(git_status, "branch", None) != base_branch:
            raise ValueError(f"Cannot merge managed proposal branch from {getattr(git_status, 'branch', None)}; expected base branch {base_branch}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot merge managed proposal branch with uncommitted changes")
        if not self.branch_exists(self.root, branch_name):
            raise ValueError(f"Managed proposal branch not found: {branch_name}")

        if not self.merge_branch_no_commit(self.root, branch_name):
            conflicts = self.conflicted_files(self.root)
            if not conflicts:
                raise ValueError(f"Failed to merge managed proposal branch: {branch_name}")
            metadata["status"] = "merge_conflict"
            metadata["merge_conflict"] = {
                "source_branch": branch_name,
                "base_branch": base_branch,
                "conflicted_files": conflicts,
                "continue_command": f"p2p proposal merge --continue {proposal_id}",
                "abort_command": f"p2p proposal merge --abort {proposal_id}",
            }
            metadata["merge_conflict_at"] = date.today().isoformat()
            metadata_path = self.root / branch_metadata_path
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
            return ProposalMergeConflict(
                proposal_id=proposal_id,
                branch_name=branch_name,
                base_branch=base_branch,
                conflicted_files=conflicts,
                path=branch_metadata_path.parent,
            )

        metadata_path = self.root / branch_metadata_path
        merged_metadata = _read_yaml_mapping(metadata_path, default=metadata)
        merged_metadata["status"] = "merged"
        merged_metadata["merged_at"] = date.today().isoformat()
        merged_metadata["merge"] = {
            "mode": "local_merge",
            "source_branch": branch_name,
            "merged_into": base_branch,
            "pushed": False,
            "cleanup": False,
        }
        metadata_path.write_text(_yaml_dump(merged_metadata), encoding="utf-8")
        merge_commit = self.commit_all(self.root, f"P2P proposal merge {proposal_id}")
        if merge_commit is None:
            raise ValueError("Failed to create managed proposal merge commit")
        return ProposalMerge(
            proposal_id=proposal_id,
            branch_name=branch_name,
            base_branch=base_branch,
            merge_commit=merge_commit,
            path=branch_metadata_path.parent,
        )

    def continue_merge(self, proposal_id: str) -> ProposalMerge:
        proposal_dir = self.find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default={})
        status = str(metadata.get("status") or "unknown")
        if status != "merge_conflict":
            raise ValueError(f"Proposal branch must be merge_conflict before merge --continue. Current status: {status}")
        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot continue managed proposal merge outside a Git repository")
        if not self.merge_in_progress(self.root):
            raise ValueError("Cannot continue managed proposal merge: no merge is in progress")
        unresolved = [path for path in self.conflicted_files(self.root) if _file_has_conflict_markers(self.root / path)]
        if unresolved:
            raise ValueError("Cannot continue managed proposal merge with unresolved conflicts: " + ", ".join(unresolved))
        self.stage_all(self.root)
        conflicts = self.conflicted_files(self.root)
        if conflicts:
            raise ValueError("Cannot continue managed proposal merge with unresolved conflicts: " + ", ".join(conflicts))
        conflict = metadata.get("merge_conflict", {})
        if not isinstance(conflict, dict):
            conflict = {}
        branch_name = str(conflict.get("source_branch") or metadata.get("branch_name") or "")
        base_branch = str(conflict.get("base_branch") or metadata.get("base_branch") or getattr(git_status, "branch", None) or "main")
        metadata["status"] = "merged"
        metadata["merged_at"] = date.today().isoformat()
        metadata.pop("merge_conflict", None)
        metadata["merge"] = {
            "mode": "local_merge",
            "source_branch": branch_name,
            "merged_into": base_branch,
            "pushed": False,
            "cleanup": False,
            "resolved_conflict": True,
        }
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        merge_commit = self.commit_all(self.root, f"P2P proposal merge {proposal_id}")
        if merge_commit is None:
            raise ValueError("Failed to create managed proposal merge commit")
        return ProposalMerge(
            proposal_id=proposal_id,
            branch_name=branch_name,
            base_branch=base_branch,
            merge_commit=merge_commit,
            path=proposal_dir.relative_to(self.root),
        )

    def abort_merge_branch(self, proposal_id: str) -> ProposalBranchDetail:
        proposal_dir = self.find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default={})
        status = str(metadata.get("status") or "unknown")
        if status != "merge_conflict":
            raise ValueError(f"Proposal branch must be merge_conflict before merge --abort. Current status: {status}")
        branch_name = str(metadata.get("branch_name") or "")
        if self.merge_in_progress(self.root):
            self.restore_path(self.root, metadata_path.relative_to(self.root).as_posix())
            if not self.abort_merge(self.root):
                raise ValueError("Failed to abort managed proposal merge")
        if not self.checkout_branch(self.root, branch_name):
            raise ValueError(f"Failed to return to managed proposal branch after merge abort: {branch_name}")
        return self.show(proposal_id)

    def finalize(self, proposal_id: str, remote: str | None = None) -> ProposalFinalize:
        proposal_dir = self.find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default={})
        status = str(metadata.get("status") or "unknown")
        if status != "merged":
            raise ValueError(f"Proposal branch must be merged before finalize. Current status: {status}")
        merge = metadata.get("merge", {})
        if not isinstance(merge, dict):
            merge = {}
        branch_name = str(metadata.get("branch_name") or merge.get("source_branch") or "")
        base_branch = str(merge.get("merged_into") or metadata.get("base_branch") or "main")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot finalize managed proposal branch outside a Git repository")
        if getattr(git_status, "branch", None) != base_branch:
            raise ValueError(f"Cannot finalize managed proposal branch from {getattr(git_status, 'branch', None)}; expected base branch {base_branch}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot finalize managed proposal branch with uncommitted changes")

        profile = self.remote_profile()
        selected_remote = remote or str(metadata.get("remote") or getattr(profile, "remote", None) or "origin")
        resolved_remote_url = self.remote_url(self.root, selected_remote)
        if resolved_remote_url is None:
            raise ValueError(f"Cannot finalize managed proposal branch: Git remote not found: {selected_remote}")

        metadata["status"] = "finalized"
        metadata["finalized_at"] = date.today().isoformat()
        merge["pushed"] = True
        merge["cleanup"] = False
        metadata["merge"] = merge
        metadata["finalize"] = {
            "mode": "base_branch_push",
            "remote": selected_remote,
            "remote_url": resolved_remote_url,
            "base_branch": base_branch,
            "source_branch": branch_name,
            "cleanup": False,
        }
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        finalize_commit = self.commit_all(self.root, f"P2P proposal finalize {proposal_id}")
        if finalize_commit is None:
            raise ValueError("Failed to create managed proposal finalize commit")
        if not self.push_branch(self.root, base_branch, selected_remote):
            raise ValueError(f"Failed to push base branch to {selected_remote}: {base_branch}")
        return ProposalFinalize(
            proposal_id=proposal_id,
            branch_name=branch_name,
            base_branch=base_branch,
            remote=selected_remote,
            remote_url=resolved_remote_url,
            finalize_commit=finalize_commit,
            path=proposal_dir.relative_to(self.root),
        )

    def cleanup(
        self,
        proposal_id: str,
        *,
        delete_remote: bool = False,
        remote: str | None = None,
    ) -> ProposalCleanup:
        proposal_dir = self.find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default={}) if metadata_path.exists() else {}
        status = str(metadata.get("status") or "unknown")
        if status not in {"finalized", "rejected", "retired"}:
            branch_name_from_ref, metadata_from_ref, ref_metadata_path = self.metadata_from_local_ref(proposal_id)
            metadata = metadata_from_ref
            status = str(metadata.get("status") or "unknown")
            metadata_path = self.root / ref_metadata_path
            proposal_dir = metadata_path.parent
            if not str(metadata.get("branch_name") or ""):
                metadata["branch_name"] = branch_name_from_ref

        if status not in {"finalized", "rejected", "retired"}:
            raise ValueError(
                f"Proposal branch must be finalized, rejected, or retired before cleanup. Current status: {status}"
            )

        merge = metadata.get("merge", {})
        if not isinstance(merge, dict):
            merge = {}
        finalize = metadata.get("finalize", {})
        if not isinstance(finalize, dict):
            finalize = {}
        branch_name = str(
            metadata.get("branch_name")
            or finalize.get("source_branch")
            or merge.get("source_branch")
            or metadata.get("remote_branch")
            or ""
        )
        if not branch_name:
            raise ValueError("Invalid proposal branch metadata: managed branch is required before cleanup")
        base_branch = str(finalize.get("base_branch") or merge.get("merged_into") or metadata.get("base_branch") or "main")
        if branch_name == base_branch:
            raise ValueError("Cannot cleanup managed proposal branch: source branch matches base branch")

        git_status = self.git_status(self.root)
        if not getattr(git_status, "is_repository", False):
            raise ValueError("Cannot cleanup managed proposal branch outside a Git repository")
        if getattr(git_status, "branch", None) != base_branch:
            raise ValueError(f"Cannot cleanup managed proposal branch from {getattr(git_status, 'branch', None)}; expected base branch {base_branch}")
        if not getattr(git_status, "is_clean", False):
            raise ValueError("Cannot cleanup managed proposal branch with uncommitted changes")
        if not self.branch_exists(self.root, branch_name):
            raise ValueError(f"Managed proposal branch not found: {branch_name}")

        profile = self.remote_profile()
        selected_remote = remote or str(finalize.get("remote") or metadata.get("remote") or getattr(profile, "remote", None) or "origin")
        resolved_remote_url = self.remote_url(self.root, selected_remote) or ""
        if delete_remote and not resolved_remote_url:
            raise ValueError(f"Cannot cleanup managed proposal branch: Git remote not found: {selected_remote}")

        local_deleted = (
            self.delete_local_branch(self.root, branch_name)
            if status == "finalized"
            else self.delete_local_branch_force(self.root, branch_name)
        )
        if not local_deleted:
            raise ValueError(f"Failed to delete local managed proposal branch: {branch_name}")
        remote_deleted = False
        if delete_remote:
            if not self.delete_remote_branch(self.root, branch_name, selected_remote):
                raise ValueError(f"Failed to delete remote managed proposal branch from {selected_remote}: {branch_name}")
            remote_deleted = True

        metadata["status"] = "cleaned"
        metadata["cleaned_at"] = date.today().isoformat()
        if finalize:
            finalize["cleanup"] = True
            metadata["finalize"] = finalize
        if merge:
            merge["cleanup"] = True
            metadata["merge"] = merge
        metadata["cleanup"] = {
            "mode": "branch_cleanup",
            "previous_status": status,
            "source_branch": branch_name,
            "base_branch": base_branch,
            "remote": selected_remote,
            "remote_url": resolved_remote_url,
            "local_deleted": True,
            "remote_deleted": remote_deleted,
        }
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")
        cleanup_commit = self.commit_all(self.root, f"P2P proposal cleanup {proposal_id}")
        if cleanup_commit is None:
            raise ValueError("Failed to create managed proposal cleanup commit")
        if resolved_remote_url and not self.push_branch(self.root, base_branch, selected_remote):
            raise ValueError(f"Failed to push cleanup metadata to {selected_remote}: {base_branch}")

        return ProposalCleanup(
            proposal_id=str(metadata.get("proposal_id") or proposal_id),
            branch_name=branch_name,
            base_branch=base_branch,
            remote=selected_remote,
            remote_url=resolved_remote_url,
            cleanup_commit=cleanup_commit,
            local_deleted=True,
            remote_deleted=remote_deleted,
            path=proposal_dir.relative_to(self.root),
        )

    def remote_proposal_ids(self, remote: str, base_branch: str) -> set[str]:
        proposal_ids: set[str] = set()
        for branch in self.list_remote_proposal_branches(self.root, remote):
            proposal_id = _proposal_id_from_branch_name(branch)
            if proposal_id:
                proposal_ids.add(proposal_id)

        remote_base = f"{remote}/{base_branch}"
        for path in self.list_files_at_ref(self.root, remote_base, ".p2p/proposals"):
            parts = Path(path).parts
            if len(parts) < 3:
                continue
            proposal_id = _proposal_id_from_dir_name(parts[2])
            if proposal_id:
                proposal_ids.add(proposal_id)
        return proposal_ids

    def auto_renumber(
        self,
        *,
        proposal_id: str,
        metadata: dict[str, object],
        remote_ids: set[str],
    ) -> tuple[str, Path, dict[str, object], Path]:
        old_dir = self.find_proposal_dir(proposal_id)
        proposal_text = _read_optional(old_dir / "proposal.md")
        title = _clean_proposal_title(read_title(proposal_text) or proposal_id, proposal_id)
        actor_slug = str(metadata.get("actor_slug") or _slugify(str(metadata.get("actor") or "local")) or "local")
        base_commit = str(metadata.get("base_commit") or self.head_commit(self.root) or "")
        if not base_commit:
            raise ValueError("Cannot auto-renumber proposal branch without a base commit")

        new_id = self.next_available_proposal_id(remote_ids)
        title_slug = _slugify(title)
        new_dir = self.p2p_dir / "proposals" / f"{new_id}-{title_slug}"
        if new_dir.exists():
            raise ValueError(f"Cannot auto-renumber proposal branch; target proposal already exists: {new_id}")

        branch_hash16 = _branch_hash16(new_id, title, actor_slug, base_commit)
        new_branch_name = _proposal_branch_name(new_id, title, actor_slug, branch_hash16)
        if self.branch_exists(self.root, new_branch_name):
            raise ValueError(f"Cannot auto-renumber proposal branch; branch already exists: {new_branch_name}")

        shutil.move(str(old_dir), str(new_dir))
        for path in sorted(new_dir.iterdir()):
            if path.is_file() and path.suffix in {".md", ".yml", ".yaml"}:
                text = path.read_text(encoding="utf-8")
                path.write_text(text.replace(proposal_id, new_id), encoding="utf-8")

        metadata_path = new_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default=metadata)
        old_branch_name = str(metadata.get("branch_name") or "")
        metadata["proposal_id"] = new_id
        metadata["status"] = "branched"
        metadata["branch_name"] = new_branch_name
        metadata["branch_hash16"] = branch_hash16
        metadata["renumbered_from"] = proposal_id
        metadata["renumbered_at"] = date.today().isoformat()
        metadata["id_collision_check"] = {
            "remote_ids": sorted(remote_ids),
            "old_proposal_id": proposal_id,
            "new_proposal_id": new_id,
        }
        metadata["remote"] = None
        metadata["remote_url"] = None
        metadata["remote_branch"] = None
        metadata_path.write_text(_yaml_dump(metadata), encoding="utf-8")

        if old_branch_name and not self.rename_current_branch(self.root, new_branch_name):
            raise ValueError(f"Failed to rename managed proposal branch to {new_branch_name}")
        if self.commit_all(self.root, f"P2P proposal auto-renumber {proposal_id} to {new_id}") is None:
            raise ValueError("Failed to create managed proposal auto-renumber commit")
        return new_id, new_dir, metadata, metadata_path

    def next_available_proposal_id(self, extra_ids: set[str] | None = None) -> str:
        used: set[int] = set()
        proposals_dir = self.p2p_dir / "proposals"
        for path in proposals_dir.iterdir() if proposals_dir.exists() else []:
            proposal_id = _proposal_id_from_dir_name(path.name)
            if proposal_id:
                used.add(int(proposal_id.removeprefix("PROP-")))
        for proposal_id in extra_ids or set():
            if re.match(r"^PROP-\d{3}$", proposal_id):
                used.add(int(proposal_id.removeprefix("PROP-")))
        next_id = max(used or {0}) + 1
        return f"PROP-{next_id:03d}"

    def metadata(self, proposal_id: str) -> tuple[Path, dict[str, object], Path]:
        proposal_dir = self.find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        if not metadata_path.exists():
            raise ValueError(
                f"Managed proposal branch metadata not found for {proposal_id}. "
                f"Run `p2p proposal branch {proposal_id}` first."
            )
        metadata = _read_yaml_mapping(metadata_path, default={})
        return proposal_dir, metadata, metadata_path

    def metadata_from_local_ref(self, proposal_id: str) -> tuple[str, dict[str, object], Path]:
        matches: list[tuple[str, dict[str, object], Path]] = []
        for branch in self.list_local_proposal_branches(self.root):
            for metadata_path in self.list_files_at_ref(self.root, branch, ".p2p/proposals"):
                if not metadata_path.endswith("/branch.yml"):
                    continue
                branch_file = self.read_file_at_ref(self.root, branch, metadata_path)
                if branch_file is None:
                    continue
                try:
                    metadata = yaml.safe_load(str(getattr(branch_file, "content", ""))) or {}
                except yaml.YAMLError:
                    continue
                if not isinstance(metadata, dict):
                    continue
                if str(metadata.get("proposal_id") or "") == proposal_id:
                    matches.append((branch, metadata, Path(metadata_path)))
        if not matches:
            raise ValueError(f"Managed proposal branch metadata not found for {proposal_id}. Run `p2p proposal scan`.")
        if len(matches) > 1:
            branches = ", ".join(branch for branch, _, _ in matches)
            raise ValueError(f"Ambiguous managed proposal branches for {proposal_id}: {branches}")
        return matches[0]

    def show(self, proposal_id: str) -> ProposalBranchDetail:
        proposal_dir = self.find_proposal_dir(proposal_id)
        metadata_path = proposal_dir / "branch.yml"
        metadata = _read_yaml_mapping(metadata_path, default={})
        if not metadata:
            return ProposalBranchDetail(
                proposal_id=proposal_id,
                status="unbranched",
                branch_name="",
                base_branch="",
                actor="",
                branch_hash16="",
                remote=None,
                remote_url=None,
                path=proposal_dir.relative_to(self.root),
                metadata={},
            )
        return _detail_from_metadata(proposal_id, metadata, proposal_dir.relative_to(self.root))

    def scan(self) -> ProposalBranchScan:
        branches = self.list_local_proposal_branches(self.root)
        items: list[dict[str, object]] = []
        for branch in branches:
            for manifest_path in self.list_files_at_ref(self.root, branch, ".p2p/proposals"):
                if not manifest_path.endswith("/branch.yml"):
                    continue
                branch_file = self.read_file_at_ref(self.root, branch, manifest_path)
                if branch_file is None:
                    continue
                try:
                    metadata = yaml.safe_load(str(getattr(branch_file, "content", ""))) or {}
                except yaml.YAMLError:
                    continue
                if not isinstance(metadata, dict):
                    continue
                items.append(
                    {
                        "proposal_id": str(metadata.get("proposal_id") or "PROP-???"),
                        "status": str(metadata.get("status") or "unknown"),
                        "branch_name": str(metadata.get("branch_name") or branch),
                        "actor": str(metadata.get("actor") or ""),
                        "branch_hash16": str(metadata.get("branch_hash16") or ""),
                        "path": manifest_path,
                    }
                )
        scan_path = self.p2p_dir / "registries" / "proposal-branches.yml"
        scan_path.parent.mkdir(parents=True, exist_ok=True)
        scan_path.write_text(
            _yaml_dump({"scanned_branches": branches, "proposal_branches": items}),
            encoding="utf-8",
        )
        return ProposalBranchScan(
            scanned_branches=branches,
            proposals=items,
            path=scan_path.relative_to(self.root),
        )

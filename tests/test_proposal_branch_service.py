from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from p2p_engine.services.proposal_branches import ProposalBranchService


@dataclass(frozen=True)
class FakeFileAtRef:
    content: str


@dataclass(frozen=True)
class FakeGitStatus:
    is_repository: bool
    branch: str | None
    is_clean: bool


@dataclass(frozen=True)
class FakeProfile:
    mode: str = "remote"
    provider: str = "generic"
    remote: str | None = "origin"
    url: str | None = "git@example.com:demo.git"


class FakeGit:
    def __init__(
        self,
        *,
        is_repository: bool = True,
        branch: str | None = "main",
        is_clean: bool = True,
        head: str | None = "abc123",
        branch_exists: bool = False,
        checkout_ok: bool = True,
        create_ok: bool = True,
        commit: str | None = "commit123",
        urls: dict[str, str | None] | None = None,
        fetch_ok: bool = True,
        push_ok: bool = True,
        merge_ok: bool = True,
        merge_in_progress: bool = False,
        abort_ok: bool = True,
        delete_local_ok: bool = True,
        delete_remote_ok: bool = True,
        remote_branches: list[str] | None = None,
        conflicts: list[str] | None = None,
        conflicts_after_stage: list[str] | None = None,
    ) -> None:
        self.is_repository = is_repository
        self.branch = branch
        self.is_clean = is_clean
        self.head = head
        self.branch_exists_result = branch_exists
        self.checkout_ok = checkout_ok
        self.create_ok = create_ok
        self.commit = commit
        self.urls = urls if urls is not None else {"origin": "git@example.com:demo.git"}
        self.fetch_ok = fetch_ok
        self.push_ok = push_ok
        self.merge_ok = merge_ok
        self.merge_in_progress_result = merge_in_progress
        self.abort_ok = abort_ok
        self.delete_local_ok = delete_local_ok
        self.delete_remote_ok = delete_remote_ok
        self.remote_branches = remote_branches or []
        self.conflicts = conflicts or []
        self.conflicts_after_stage = conflicts_after_stage
        self.checked_out: list[str] = []
        self.created: list[str] = []
        self.renamed: list[str] = []
        self.commits: list[str] = []
        self.fetches: list[str] = []
        self.pushes: list[tuple[str, str]] = []
        self.merges: list[str] = []
        self.staged = False
        self.restored: list[str] = []
        self.aborted = False
        self.deleted_local: list[tuple[str, bool]] = []
        self.deleted_remote: list[tuple[str, str]] = []

    def git_status(self, _root: Path) -> FakeGitStatus:
        return FakeGitStatus(
            is_repository=self.is_repository,
            branch=self.branch,
            is_clean=self.is_clean,
        )

    def checkout_branch(self, _root: Path, branch: str) -> bool:
        self.checked_out.append(branch)
        if self.checkout_ok:
            self.branch = branch
        return self.checkout_ok

    def head_commit(self, _root: Path) -> str | None:
        return self.head

    def branch_exists(self, _root: Path, _branch: str) -> bool:
        return self.branch_exists_result

    def create_and_checkout_branch(self, _root: Path, branch: str) -> bool:
        self.created.append(branch)
        if self.create_ok:
            self.branch = branch
        return self.create_ok

    def rename_current_branch(self, _root: Path, branch: str) -> bool:
        self.renamed.append(branch)
        self.branch = branch
        return True

    def commit_all(self, _root: Path, message: str) -> str | None:
        self.commits.append(message)
        return self.commit

    def remote_url(self, _root: Path, remote: str) -> str | None:
        return self.urls.get(remote)

    def fetch_remote(self, _root: Path, remote: str) -> bool:
        self.fetches.append(remote)
        return self.fetch_ok

    def push_branch(self, _root: Path, branch: str, remote: str) -> bool:
        self.pushes.append((branch, remote))
        return self.push_ok

    def list_remote_proposal_branches(self, _root: Path, _remote: str) -> list[str]:
        return self.remote_branches

    def merge_branch_no_commit(self, _root: Path, branch: str) -> bool:
        self.merges.append(branch)
        return self.merge_ok

    def conflicted_files(self, _root: Path) -> list[str]:
        return self.conflicts

    def merge_in_progress(self, _root: Path) -> bool:
        return self.merge_in_progress_result

    def stage_all(self, _root: Path) -> bool:
        self.staged = True
        if self.conflicts_after_stage is not None:
            self.conflicts = self.conflicts_after_stage
        return True

    def restore_path(self, _root: Path, path: str) -> bool:
        self.restored.append(path)
        return True

    def abort_merge(self, _root: Path) -> bool:
        self.aborted = True
        return self.abort_ok

    def delete_local_branch(self, _root: Path, branch: str) -> bool:
        self.deleted_local.append((branch, False))
        return self.delete_local_ok

    def delete_local_branch_force(self, _root: Path, branch: str) -> bool:
        self.deleted_local.append((branch, True))
        return self.delete_local_ok

    def delete_remote_branch(self, _root: Path, branch: str, remote: str) -> bool:
        self.deleted_remote.append((branch, remote))
        return self.delete_remote_ok


class FakeRefs:
    def __init__(self) -> None:
        self.branches: list[str] = []
        self.files: dict[tuple[str, str], FakeFileAtRef | None] = {}

    def list_local_proposal_branches(self, _root: Path) -> list[str]:
        return self.branches

    def list_files_at_ref(self, _root: Path, ref: str, path: str) -> list[str]:
        prefix = f"{path}/"
        return [file_path for branch, file_path in self.files if branch == ref and file_path.startswith(prefix)]

    def read_file_at_ref(self, _root: Path, ref: str, path: str) -> FakeFileAtRef | None:
        return self.files.get((ref, path))


def _proposal_dir(root: Path, proposal_id: str = "PROP-001") -> Path:
    proposal_dir = root / ".p2p" / "proposals" / f"{proposal_id}-demo"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    return proposal_dir


def _find_proposal_dir(root: Path, proposal_id: str) -> Path:
    proposals_dir = root / ".p2p" / "proposals"
    matches = sorted(proposals_dir.glob(f"{proposal_id}-*")) if proposals_dir.exists() else []
    if matches:
        return matches[0]
    return _proposal_dir(root, proposal_id)


def _seed_ref_metadata(refs: FakeRefs, branch: str, metadata: dict[str, object], path: str = ".p2p/proposals/PROP-001-demo/branch.yml") -> None:
    refs.branches = [branch]
    refs.files[(branch, path)] = FakeFileAtRef(yaml.safe_dump(metadata, sort_keys=False))


def _service(
    root: Path,
    refs: FakeRefs | None = None,
    git: FakeGit | None = None,
    profile: FakeProfile | None = None,
) -> ProposalBranchService:
    refs = refs or FakeRefs()
    git = git or FakeGit()
    profile = profile or FakeProfile()
    return ProposalBranchService(
        root=root,
        p2p_dir=root / ".p2p",
        find_proposal_dir=lambda proposal_id: _find_proposal_dir(root, proposal_id),
        git_status=git.git_status,
        checkout_branch=git.checkout_branch,
        head_commit=git.head_commit,
        branch_exists=git.branch_exists,
        create_and_checkout_branch=git.create_and_checkout_branch,
        rename_current_branch=git.rename_current_branch,
        commit_all=git.commit_all,
        remote_profile=lambda: profile,
        remote_url=git.remote_url,
        fetch_remote=git.fetch_remote,
        push_branch=git.push_branch,
        merge_branch_no_commit=git.merge_branch_no_commit,
        conflicted_files=git.conflicted_files,
        merge_in_progress=git.merge_in_progress,
        stage_all=git.stage_all,
        restore_path=git.restore_path,
        abort_merge=git.abort_merge,
        delete_local_branch=git.delete_local_branch,
        delete_local_branch_force=git.delete_local_branch_force,
        delete_remote_branch=git.delete_remote_branch,
        list_local_proposal_branches=refs.list_local_proposal_branches,
        list_remote_proposal_branches=git.list_remote_proposal_branches,
        list_files_at_ref=refs.list_files_at_ref,
        read_file_at_ref=refs.read_file_at_ref,
    )


def test_proposal_branch_service_show_unbranched_status(tmp_path: Path) -> None:
    detail = _service(tmp_path).show("PROP-001")

    assert detail.proposal_id == "PROP-001"
    assert detail.status == "unbranched"
    assert detail.branch_name == ""
    assert detail.path == Path(".p2p/proposals/PROP-001-demo")
    assert detail.metadata == {}


def test_proposal_branch_service_show_metadata_backed_status(tmp_path: Path) -> None:
    proposal_dir = _proposal_dir(tmp_path)
    (proposal_dir / "branch.yml").write_text(
        yaml.safe_dump(
            {
                "proposal_id": "PROP-001",
                "status": "review_requested",
                "branch_name": "p2p/proposal/PROP-001-demo-agent-aaaaaaaaaaaaaaaa",
                "base_branch": "main",
                "actor": "agent",
                "branch_hash16": "aaaaaaaaaaaaaaaa",
                "remote": "origin",
                "remote_url": "git@example.com:demo.git",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    detail = _service(tmp_path).show("PROP-001")

    assert detail.status == "review_requested"
    assert detail.branch_name == "p2p/proposal/PROP-001-demo-agent-aaaaaaaaaaaaaaaa"
    assert detail.remote == "origin"
    assert detail.remote_url == "git@example.com:demo.git"


def test_proposal_branch_service_metadata_requires_existing_branch_file(tmp_path: Path) -> None:
    service = _service(tmp_path)

    try:
        service.metadata("PROP-001")
    except ValueError as exc:
        assert "Managed proposal branch metadata not found for PROP-001" in str(exc)
        assert "p2p proposal branch PROP-001" in str(exc)
    else:
        raise AssertionError("missing branch metadata should fail")


def test_proposal_branch_service_scan_tolerates_malformed_inputs(tmp_path: Path) -> None:
    refs = FakeRefs()
    refs.branches = ["p2p/proposal/PROP-001-demo-agent-aaaaaaaaaaaaaaaa"]
    refs.files = {
        (
            refs.branches[0],
            ".p2p/proposals/PROP-001-demo/branch.yml",
        ): FakeFileAtRef(
            yaml.safe_dump(
                {
                    "proposal_id": "PROP-001",
                    "status": "branched",
                    "branch_name": refs.branches[0],
                    "actor": "agent",
                    "branch_hash16": "aaaaaaaaaaaaaaaa",
                },
                sort_keys=False,
            )
        ),
        (refs.branches[0], ".p2p/proposals/PROP-002-demo/branch.yml"): FakeFileAtRef("["),
        (refs.branches[0], ".p2p/proposals/PROP-003-demo/proposal.md"): FakeFileAtRef("# ignored"),
    }

    scan = _service(tmp_path, refs).scan()

    assert scan.scanned_branches == refs.branches
    assert scan.path == Path(".p2p/registries/proposal-branches.yml")
    assert scan.proposals == [
        {
            "proposal_id": "PROP-001",
            "status": "branched",
            "branch_name": refs.branches[0],
            "actor": "agent",
            "branch_hash16": "aaaaaaaaaaaaaaaa",
            "path": ".p2p/proposals/PROP-001-demo/branch.yml",
        }
    ]

    registry = yaml.safe_load((tmp_path / ".p2p" / "registries" / "proposal-branches.yml").read_text(encoding="utf-8"))
    assert registry["scanned_branches"] == refs.branches
    assert registry["proposal_branches"] == scan.proposals


def test_proposal_branch_service_branch_creates_metadata_and_commit(tmp_path: Path) -> None:
    proposal_dir = _proposal_dir(tmp_path)
    (proposal_dir / "proposal.md").write_text("# PROP-001 - Chiusura Magnetica\n", encoding="utf-8")
    git = FakeGit(head="base123")

    detail = _service(tmp_path, git=git).branch("PROP-001", actor="Lorenzo")

    assert detail.status == "branched"
    assert detail.branch_name.startswith("p2p/proposal/PROP-001-chiusura-magnetica-lorenzo-")
    assert len(detail.branch_name.rsplit("-", 1)[1]) == 16
    assert git.created == [detail.branch_name]
    assert git.commits == ["P2P proposal branch PROP-001"]
    metadata = yaml.safe_load((proposal_dir / "branch.yml").read_text(encoding="utf-8"))
    assert metadata["proposal_id"] == "PROP-001"
    assert metadata["status"] == "branched"
    assert metadata["actor"] == "Lorenzo"
    assert metadata["actor_slug"] == "lorenzo"
    assert metadata["base_branch"] == "main"
    assert metadata["base_commit"] == "base123"
    assert metadata["head_commit"] == "base123"
    assert metadata["remote"] is None
    assert metadata["remote_url"] is None
    assert metadata["remote_branch"] is None


def test_proposal_branch_service_branch_rejects_detached_and_dirty_worktree(tmp_path: Path) -> None:
    detached = _service(tmp_path, git=FakeGit(branch=None))
    dirty = _service(tmp_path, git=FakeGit(is_clean=False))

    try:
        detached.branch("PROP-001", actor="agent")
    except ValueError as exc:
        assert "Cannot create managed proposal branch from detached HEAD" in str(exc)
    else:
        raise AssertionError("detached HEAD should fail")

    try:
        dirty.branch("PROP-001", actor="agent")
    except ValueError as exc:
        assert "Cannot create managed proposal branch with uncommitted changes" in str(exc)
    else:
        raise AssertionError("dirty worktree should fail")


def test_proposal_branch_service_branch_refuses_proposal_base_without_opt_in(tmp_path: Path) -> None:
    service = _service(tmp_path)

    try:
        service.branch(
            "PROP-001",
            actor="agent",
            base_branch="p2p/proposal/PROP-000-other-agent-aaaaaaaaaaaaaaaa",
        )
    except ValueError as exc:
        assert "Cannot create managed proposal branch from another proposal branch" in str(exc)
    else:
        raise AssertionError("proposal base without opt-in should fail")


def test_proposal_branch_service_branch_allows_explicit_base_checkout(tmp_path: Path) -> None:
    git = FakeGit(branch="feature")
    detail = _service(tmp_path, git=git).branch("PROP-001", actor="agent", base_branch="main")

    assert git.checked_out == ["main"]
    assert detail.base_branch == "main"
    assert git.created == [detail.branch_name]


def test_proposal_branch_service_publish_updates_metadata_and_pushes_branch(tmp_path: Path) -> None:
    git = FakeGit()
    service = _service(tmp_path, git=git)
    branched = service.branch("PROP-001", actor="agent")

    published = service.publish("PROP-001")

    assert published.status == "published"
    assert git.fetches == ["origin"]
    assert git.pushes == [(branched.branch_name, "origin")]
    assert git.commits[-1] == "P2P proposal publish PROP-001"
    metadata = yaml.safe_load((_proposal_dir(tmp_path) / "branch.yml").read_text(encoding="utf-8"))
    assert metadata["status"] == "published"
    assert metadata["remote"] == "origin"
    assert metadata["remote_url"] == "git@example.com:demo.git"
    assert metadata["remote_branch"] == branched.branch_name


def test_proposal_branch_service_publish_rejects_missing_remote_and_id_collision(tmp_path: Path) -> None:
    missing_remote_git = FakeGit(urls={})
    missing_remote_service = _service(tmp_path / "missing", git=missing_remote_git)
    missing_remote_service.branch("PROP-001", actor="agent")

    try:
        missing_remote_service.publish("PROP-001")
    except ValueError as exc:
        assert "Cannot publish managed proposal branch: Git remote not found: origin" in str(exc)
    else:
        raise AssertionError("missing remote should fail")

    collision_git = FakeGit(remote_branches=["p2p/proposal/PROP-001-existing-agent-aaaaaaaaaaaaaaaa"])
    collision_service = _service(tmp_path / "collision", git=collision_git)
    collision_service.branch("PROP-001", actor="agent")

    try:
        collision_service.publish("PROP-001")
    except ValueError as exc:
        assert "Proposal ID collision detected on remote: PROP-001" in str(exc)
        assert "--auto-renumber" in str(exc)
    else:
        raise AssertionError("remote collision should fail without auto-renumber")


def test_proposal_branch_service_publish_auto_renumbers_collision(tmp_path: Path) -> None:
    git = FakeGit(remote_branches=["p2p/proposal/PROP-001-existing-agent-aaaaaaaaaaaaaaaa"])
    service = _service(tmp_path, git=git)
    (_proposal_dir(tmp_path) / "proposal.md").write_text("# PROP-001 - Demo\n", encoding="utf-8")
    old_detail = service.branch("PROP-001", actor="agent")

    published = service.publish("PROP-001", auto_renumber=True)

    assert published.proposal_id == "PROP-002"
    assert published.status == "published"
    assert not (tmp_path / ".p2p" / "proposals" / "PROP-001-demo").exists()
    new_dir = tmp_path / ".p2p" / "proposals" / "PROP-002-demo"
    assert new_dir.exists()
    metadata = yaml.safe_load((new_dir / "branch.yml").read_text(encoding="utf-8"))
    assert metadata["proposal_id"] == "PROP-002"
    assert metadata["renumbered_from"] == "PROP-001"
    assert metadata["id_collision_check"]["old_proposal_id"] == "PROP-001"
    assert metadata["id_collision_check"]["new_proposal_id"] == "PROP-002"
    assert metadata["status"] == "published"
    assert git.renamed == [metadata["branch_name"]]
    assert old_detail.branch_name != metadata["branch_name"]
    assert git.commits[-2:] == [
        "P2P proposal auto-renumber PROP-001 to PROP-002",
        "P2P proposal publish PROP-002",
    ]


def test_proposal_branch_service_request_review_records_provider_metadata(tmp_path: Path) -> None:
    git = FakeGit()
    service = _service(tmp_path, git=git, profile=FakeProfile(provider="github"))
    published = service.publish("PROP-001") if (_proposal_dir(tmp_path) / "branch.yml").exists() else None
    if published is None:
        service.branch("PROP-001", actor="agent")
        published = service.publish("PROP-001")

    reviewed = service.request_review("PROP-001")

    assert reviewed.status == "review_requested"
    assert git.commits[-1] == "P2P proposal request review PROP-001"
    review = reviewed.metadata["review"]
    assert review["provider"] == "github"
    assert review["remote"] == "origin"
    assert review["remote_url"] == "git@example.com:demo.git"
    assert review["remote_branch"] == published.branch_name
    assert review["opens_external_request"] is False
    assert "GitHub pull request" in review["suggested_next"]


def test_proposal_branch_service_request_review_rejects_invalid_provider(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.branch("PROP-001", actor="agent")
    service.publish("PROP-001")

    try:
        service.request_review("PROP-001", provider="bitbucket")
    except ValueError as exc:
        assert "Proposal review provider must be generic, github, or gitlab" in str(exc)
    else:
        raise AssertionError("invalid provider should fail")


def test_proposal_branch_service_retire_requires_reason_and_records_metadata(tmp_path: Path) -> None:
    git = FakeGit()
    service = _service(tmp_path, git=git)
    branched = service.branch("PROP-001", actor="agent")

    try:
        service.retire("PROP-001", " ")
    except ValueError as exc:
        assert "Proposal branch retire reason is required" in str(exc)
    else:
        raise AssertionError("blank retire reason should fail")

    retired = service.retire("PROP-001", "Superseded.")

    assert retired.status == "retired"
    assert retired.branch_name == branched.branch_name
    assert git.commits[-1] == "P2P proposal retire PROP-001"
    metadata = yaml.safe_load((_proposal_dir(tmp_path) / "branch.yml").read_text(encoding="utf-8"))
    assert metadata["status"] == "retired"
    assert metadata["retirement"]["reason"] == "Superseded."


def test_proposal_branch_service_retire_rejects_terminal_status(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.branch("PROP-001", actor="agent")
    metadata_path = _proposal_dir(tmp_path) / "branch.yml"
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    metadata["status"] = "finalized"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")

    try:
        service.retire("PROP-001", "Done.")
    except ValueError as exc:
        assert "Proposal branch cannot be retired from status: finalized" in str(exc)
    else:
        raise AssertionError("terminal status retire should fail")


def test_proposal_branch_service_accept_and_reject_require_reason(tmp_path: Path) -> None:
    service = _service(tmp_path)

    try:
        service.accept("PROP-001", "")
    except ValueError as exc:
        assert "Proposal branch accept reason is required" in str(exc)
    else:
        raise AssertionError("blank accept reason should fail")

    try:
        service.reject("PROP-001", " ")
    except ValueError as exc:
        assert "Proposal branch reject reason is required" in str(exc)
    else:
        raise AssertionError("blank reject reason should fail")


def test_proposal_branch_service_accept_records_decision_metadata(tmp_path: Path) -> None:
    git = FakeGit()
    service = _service(tmp_path, git=git)
    published = service.publish("PROP-001") if (_proposal_dir(tmp_path) / "branch.yml").exists() else None
    if published is None:
        service.branch("PROP-001", actor="agent")
        published = service.publish("PROP-001")

    accepted = service.accept("PROP-001", "Ready to merge.")

    assert accepted.status == "accepted"
    assert accepted.branch_name == published.branch_name
    assert accepted.remote == "origin"
    assert accepted.remote_url == "git@example.com:demo.git"
    assert git.commits[-1] == "P2P proposal branch accept PROP-001"
    decision = accepted.metadata["branch_decision"]
    assert decision["outcome"] == "accepted"
    assert decision["reason"] == "Ready to merge."
    assert decision["governance_decision"] is True


def test_proposal_branch_service_reject_records_decision_metadata_from_review_requested(tmp_path: Path) -> None:
    git = FakeGit()
    service = _service(tmp_path, git=git)
    service.branch("PROP-001", actor="agent")
    service.publish("PROP-001")
    service.request_review("PROP-001")

    rejected = service.reject("PROP-001", "Out of scope.")

    assert rejected.status == "rejected"
    assert git.commits[-1] == "P2P proposal branch reject PROP-001"
    decision = rejected.metadata["branch_decision"]
    assert decision["outcome"] == "rejected"
    assert decision["reason"] == "Out of scope."
    assert decision["governance_decision"] is True


def test_proposal_branch_service_decision_rejects_invalid_status_and_dirty_worktree(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.branch("PROP-001", actor="agent")

    try:
        service.accept("PROP-001", "Ready.")
    except ValueError as exc:
        assert "Proposal branch must be published or review_requested before accepted. Current status: branched" in str(exc)
    else:
        raise AssertionError("branched status should not be accepted")

    dirty_git = FakeGit()
    dirty_service = _service(tmp_path / "dirty", git=dirty_git)
    dirty_service.branch("PROP-001", actor="agent")
    dirty_service.publish("PROP-001")
    dirty_git.is_clean = False

    try:
        dirty_service.reject("PROP-001", "No.")
    except ValueError as exc:
        assert "Cannot rejected managed proposal branch with uncommitted changes" in str(exc)
    else:
        raise AssertionError("dirty worktree should fail branch decision")


def test_proposal_branch_service_merge_records_merge_metadata(tmp_path: Path) -> None:
    branch = "p2p/proposal/PROP-001-demo-agent-aaaaaaaaaaaaaaaa"
    metadata = {
        "proposal_id": "PROP-001",
        "status": "review_requested",
        "branch_name": branch,
        "base_branch": "main",
        "actor": "agent",
        "branch_hash16": "aaaaaaaaaaaaaaaa",
    }
    refs = FakeRefs()
    _seed_ref_metadata(refs, branch, metadata)
    proposal_dir = _proposal_dir(tmp_path)
    (proposal_dir / "branch.yml").write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    git = FakeGit(branch="main", branch_exists=True, commit="merge123")

    result = _service(tmp_path, refs=refs, git=git).merge("PROP-001")

    assert result.proposal_id == "PROP-001"
    assert result.branch_name == branch
    assert result.base_branch == "main"
    assert result.merge_commit == "merge123"
    assert git.merges == [branch]
    assert git.commits[-1] == "P2P proposal merge PROP-001"
    merged = yaml.safe_load((proposal_dir / "branch.yml").read_text(encoding="utf-8"))
    assert merged["status"] == "merged"
    assert merged["merge"]["source_branch"] == branch
    assert merged["merge"]["merged_into"] == "main"
    assert merged["merge"]["pushed"] is False


def test_proposal_branch_service_merge_records_conflict_metadata(tmp_path: Path) -> None:
    branch = "p2p/proposal/PROP-001-demo-agent-aaaaaaaaaaaaaaaa"
    metadata = {
        "proposal_id": "PROP-001",
        "status": "published",
        "branch_name": branch,
        "base_branch": "main",
    }
    refs = FakeRefs()
    _seed_ref_metadata(refs, branch, metadata)
    proposal_dir = _proposal_dir(tmp_path)
    (proposal_dir / "branch.yml").write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    git = FakeGit(branch="main", branch_exists=True, merge_ok=False, conflicts=["proposal.md"])

    conflict = _service(tmp_path, refs=refs, git=git).merge("PROP-001")

    assert conflict.conflicted_files == ["proposal.md"]
    stored = yaml.safe_load((proposal_dir / "branch.yml").read_text(encoding="utf-8"))
    assert stored["status"] == "merge_conflict"
    assert stored["merge_conflict"]["source_branch"] == branch
    assert stored["merge_conflict"]["continue_command"] == "p2p proposal merge --continue PROP-001"
    assert stored["merge_conflict"]["abort_command"] == "p2p proposal merge --abort PROP-001"


def test_proposal_branch_service_continue_merge_rejects_unresolved_markers(tmp_path: Path) -> None:
    proposal_dir = _proposal_dir(tmp_path)
    (proposal_dir / "branch.yml").write_text(
        yaml.safe_dump({"status": "merge_conflict", "merge_conflict": {"source_branch": "branch", "base_branch": "main"}}, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_path / "conflict.md").write_text("<<<<<<< ours\nx\n=======\ny\n>>>>>>> theirs\n", encoding="utf-8")
    git = FakeGit(merge_in_progress=True, conflicts=["conflict.md"])

    try:
        _service(tmp_path, git=git).continue_merge("PROP-001")
    except ValueError as exc:
        assert "Cannot continue managed proposal merge with unresolved conflicts: conflict.md" in str(exc)
    else:
        raise AssertionError("unresolved conflict markers should fail")


def test_proposal_branch_service_continue_merge_records_resolved_metadata(tmp_path: Path) -> None:
    proposal_dir = _proposal_dir(tmp_path)
    (proposal_dir / "branch.yml").write_text(
        yaml.safe_dump(
            {
                "status": "merge_conflict",
                "branch_name": "branch",
                "base_branch": "main",
                "merge_conflict": {"source_branch": "branch", "base_branch": "main"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    git = FakeGit(merge_in_progress=True, commit="merge456")

    result = _service(tmp_path, git=git).continue_merge("PROP-001")

    assert result.merge_commit == "merge456"
    assert git.staged is True
    stored = yaml.safe_load((proposal_dir / "branch.yml").read_text(encoding="utf-8"))
    assert stored["status"] == "merged"
    assert "merge_conflict" not in stored
    assert stored["merge"]["resolved_conflict"] is True


def test_proposal_branch_service_abort_merge_restores_metadata_and_checks_out_branch(tmp_path: Path) -> None:
    proposal_dir = _proposal_dir(tmp_path)
    branch = "p2p/proposal/PROP-001-demo-agent-aaaaaaaaaaaaaaaa"
    (proposal_dir / "branch.yml").write_text(
        yaml.safe_dump({"status": "merge_conflict", "branch_name": branch}, sort_keys=False),
        encoding="utf-8",
    )
    git = FakeGit(merge_in_progress=True)

    detail = _service(tmp_path, git=git).abort_merge_branch("PROP-001")

    assert detail.status == "merge_conflict"
    assert git.restored == [".p2p/proposals/PROP-001-demo/branch.yml"]
    assert git.aborted is True
    assert git.checked_out == [branch]


def test_proposal_branch_service_finalize_pushes_base_branch_and_records_metadata(tmp_path: Path) -> None:
    proposal_dir = _proposal_dir(tmp_path)
    branch = "p2p/proposal/PROP-001-demo-agent-aaaaaaaaaaaaaaaa"
    (proposal_dir / "branch.yml").write_text(
        yaml.safe_dump(
            {
                "proposal_id": "PROP-001",
                "status": "merged",
                "branch_name": branch,
                "base_branch": "main",
                "remote": "origin",
                "merge": {
                    "source_branch": branch,
                    "merged_into": "main",
                    "pushed": False,
                    "cleanup": False,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    git = FakeGit(branch="main", commit="finalize123")

    result = _service(tmp_path, git=git).finalize("PROP-001")

    assert result.finalize_commit == "finalize123"
    assert result.branch_name == branch
    assert result.base_branch == "main"
    assert result.remote == "origin"
    assert git.pushes[-1] == ("main", "origin")
    stored = yaml.safe_load((proposal_dir / "branch.yml").read_text(encoding="utf-8"))
    assert stored["status"] == "finalized"
    assert stored["merge"]["pushed"] is True
    assert stored["merge"]["cleanup"] is False
    assert stored["finalize"]["base_branch"] == "main"
    assert stored["finalize"]["cleanup"] is False


def test_proposal_branch_service_finalize_rejects_missing_remote(tmp_path: Path) -> None:
    proposal_dir = _proposal_dir(tmp_path)
    (proposal_dir / "branch.yml").write_text(
        yaml.safe_dump({"status": "merged", "branch_name": "branch", "base_branch": "main"}, sort_keys=False),
        encoding="utf-8",
    )
    service = _service(tmp_path, git=FakeGit(branch="main", urls={}))

    try:
        service.finalize("PROP-001")
    except ValueError as exc:
        assert "Cannot finalize managed proposal branch: Git remote not found: origin" in str(exc)
    else:
        raise AssertionError("missing remote should fail finalize")


def test_proposal_branch_service_cleanup_finalized_deletes_local_and_remote_branch(tmp_path: Path) -> None:
    proposal_dir = _proposal_dir(tmp_path)
    branch = "p2p/proposal/PROP-001-demo-agent-aaaaaaaaaaaaaaaa"
    (proposal_dir / "branch.yml").write_text(
        yaml.safe_dump(
            {
                "proposal_id": "PROP-001",
                "status": "finalized",
                "branch_name": branch,
                "base_branch": "main",
                "remote": "origin",
                "merge": {"source_branch": branch, "merged_into": "main", "cleanup": False},
                "finalize": {
                    "remote": "origin",
                    "remote_url": "git@example.com:demo.git",
                    "base_branch": "main",
                    "source_branch": branch,
                    "cleanup": False,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    git = FakeGit(branch="main", branch_exists=True, commit="cleanup123")

    result = _service(tmp_path, git=git).cleanup("PROP-001", delete_remote=True)

    assert result.cleanup_commit == "cleanup123"
    assert result.local_deleted is True
    assert result.remote_deleted is True
    assert git.deleted_local == [(branch, False)]
    assert git.deleted_remote == [(branch, "origin")]
    assert git.pushes[-1] == ("main", "origin")
    stored = yaml.safe_load((proposal_dir / "branch.yml").read_text(encoding="utf-8"))
    assert stored["status"] == "cleaned"
    assert stored["cleanup"]["previous_status"] == "finalized"
    assert stored["cleanup"]["local_deleted"] is True
    assert stored["cleanup"]["remote_deleted"] is True
    assert stored["finalize"]["cleanup"] is True
    assert stored["merge"]["cleanup"] is True


def test_proposal_branch_service_cleanup_rejected_uses_force_delete(tmp_path: Path) -> None:
    proposal_dir = _proposal_dir(tmp_path)
    branch = "p2p/proposal/PROP-001-demo-agent-aaaaaaaaaaaaaaaa"
    (proposal_dir / "branch.yml").write_text(
        yaml.safe_dump(
            {
                "proposal_id": "PROP-001",
                "status": "rejected",
                "branch_name": branch,
                "base_branch": "main",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    git = FakeGit(branch="main", branch_exists=True)

    result = _service(tmp_path, git=git).cleanup("PROP-001")

    assert result.remote_deleted is False
    assert git.deleted_local == [(branch, True)]
    stored = yaml.safe_load((proposal_dir / "branch.yml").read_text(encoding="utf-8"))
    assert stored["status"] == "cleaned"
    assert stored["cleanup"]["previous_status"] == "rejected"

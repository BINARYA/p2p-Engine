from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from p2p_engine.services.work_branches import WorkBranchService


@dataclass(frozen=True)
class FakeFileAtRef:
    content: str


class FakeRefs:
    def __init__(self) -> None:
        self.branches: list[str] = []
        self.files: dict[tuple[str, str], FakeFileAtRef | None] = {}

    def list_local_work_branches(self, _root: Path) -> list[str]:
        return self.branches

    def list_files_at_ref(self, _root: Path, ref: str, path: str) -> list[str]:
        prefix = f"{path}/"
        return [file_path for branch, file_path in self.files if branch == ref and file_path.startswith(prefix)]

    def read_file_at_ref(self, _root: Path, ref: str, path: str) -> FakeFileAtRef | None:
        return self.files.get((ref, path))


@dataclass
class FakeGitStatus:
    is_repository: bool = True
    branch: str = "main"
    is_clean: bool = True


@dataclass
class FakeRemoteProfile:
    provider: str = "generic"
    url: str | None = None


class FakeGit:
    def __init__(self) -> None:
        self.status = FakeGitStatus()
        self.existing_branches: set[str] = set()
        self.head_commits = ["base-commit", "branch-commit"]
        self.created_branches: list[str] = []
        self.changed: list[str] = []
        self.commit = "submit-commit"
        self.commit_messages: list[str] = []
        self.remote_urls: dict[str, str] = {}
        self.pushed_branches: list[tuple[str, str]] = []
        self.profile = FakeRemoteProfile()
        self.merge_succeeds = True
        self.conflicts: list[str] = []
        self.merge_in_progress_value = False
        self.checked_out: list[str] = []
        self.staged = False
        self.restored_paths: list[str] = []
        self.abort_succeeds = True
        self.deleted_local_branches: list[str] = []
        self.deleted_remote_branches: list[tuple[str, str]] = []

    def git_status(self, _root: Path) -> FakeGitStatus:
        return self.status

    def branch_exists(self, _root: Path, branch_name: str) -> bool:
        return branch_name in self.existing_branches

    def head_commit(self, _root: Path) -> str | None:
        if self.head_commits:
            return self.head_commits.pop(0)
        return "branch-commit"

    def create_and_checkout_branch(self, _root: Path, branch_name: str) -> bool:
        self.created_branches.append(branch_name)
        self.status.branch = branch_name
        return True

    def changed_files(self, _root: Path) -> list[str]:
        return self.changed

    def commit_all(self, _root: Path, message: str) -> str | None:
        self.commit_messages.append(message)
        return self.commit

    def remote_url(self, _root: Path, remote: str) -> str | None:
        return self.remote_urls.get(remote)

    def push_branch(self, _root: Path, branch_name: str, remote: str) -> bool:
        self.pushed_branches.append((branch_name, remote))
        return True

    def checkout_branch(self, _root: Path, branch_name: str) -> bool:
        self.checked_out.append(branch_name)
        self.status.branch = branch_name
        return True

    def merge_branch_no_commit(self, _root: Path, _branch_name: str) -> bool:
        return self.merge_succeeds

    def conflicted_files(self, _root: Path) -> list[str]:
        return self.conflicts

    def merge_in_progress(self, _root: Path) -> bool:
        return self.merge_in_progress_value

    def stage_all(self, _root: Path) -> bool:
        self.staged = True
        self.conflicts = []
        return True

    def restore_path(self, _root: Path, path: str) -> bool:
        self.restored_paths.append(path)
        return True

    def abort_merge(self, _root: Path) -> bool:
        self.merge_in_progress_value = False
        return self.abort_succeeds

    def delete_local_branch(self, _root: Path, branch_name: str) -> bool:
        self.deleted_local_branches.append(branch_name)
        self.existing_branches.discard(branch_name)
        return True

    def delete_remote_branch(self, _root: Path, branch_name: str, remote: str) -> bool:
        self.deleted_remote_branches.append((branch_name, remote))
        return True


def _work_dir(root: Path, work_id: str = "WORK-001") -> Path:
    return root / ".p2p" / "work" / work_id


def _write_manifest(root: Path, payload: dict[str, object], work_id: str = "WORK-001") -> Path:
    work_dir = _work_dir(root, work_id)
    work_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = work_dir / "manifest.yml"
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return manifest_path


def _service(root: Path, refs: FakeRefs | None = None, git: FakeGit | None = None) -> WorkBranchService:
    refs = refs or FakeRefs()
    git = git or FakeGit()
    return WorkBranchService(
        root=root,
        p2p_dir=root / ".p2p",
        find_work_dir=lambda work_id: _work_dir(root, work_id),
        list_local_work_branches=refs.list_local_work_branches,
        list_files_at_ref=refs.list_files_at_ref,
        read_file_at_ref=refs.read_file_at_ref,
        git_status=git.git_status,
        branch_exists=git.branch_exists,
        head_commit=git.head_commit,
        create_and_checkout_branch=git.create_and_checkout_branch,
        changed_files=git.changed_files,
        commit_all=git.commit_all,
        remote_url=git.remote_url,
        push_branch=git.push_branch,
        remote_profile=lambda: git.profile,
        review_request_suggestion=lambda provider, remote_url, branch_name: (
            f"{provider}|{remote_url}|{branch_name}"
        ),
        checkout_branch=git.checkout_branch,
        merge_branch_no_commit=git.merge_branch_no_commit,
        conflicted_files=git.conflicted_files,
        merge_in_progress=git.merge_in_progress,
        stage_all=git.stage_all,
        restore_path=git.restore_path,
        abort_merge=git.abort_merge,
        show_work=lambda work_id: {"work_id": work_id},
        delete_local_branch=git.delete_local_branch,
        delete_remote_branch=git.delete_remote_branch,
    )


def test_work_branch_service_scan_writes_empty_registry(tmp_path: Path) -> None:
    scan = _service(tmp_path).scan()

    assert scan.scanned_branches == []
    assert scan.work_items == []
    assert scan.path == Path(".p2p/registries/work.yml")
    registry = yaml.safe_load((tmp_path / ".p2p" / "registries" / "work.yml").read_text(encoding="utf-8"))
    assert registry == {"scanned_branches": [], "work_items": []}


def test_work_branch_service_scan_extracts_work_manifest_metadata(tmp_path: Path) -> None:
    refs = FakeRefs()
    branch = "p2p/work/work-001-change-001-speckit"
    refs.branches = [branch]
    refs.files[(branch, ".p2p/work/WORK-001/manifest.yml")] = FakeFileAtRef(
        yaml.safe_dump(
            {
                "work_id": "WORK-001",
                "status": "published",
                "source": {"change": "CHANGE-001"},
                "handoff": {"target": "speckit"},
                "git": {"branch_name": branch},
            },
            sort_keys=False,
        )
    )

    scan = _service(tmp_path, refs).scan()

    assert scan.work_items == [
        {
            "work_id": "WORK-001",
            "status": "published",
            "change": "CHANGE-001",
            "target": "speckit",
            "branch": branch,
            "branch_name": branch,
            "path": ".p2p/work/WORK-001/manifest.yml",
        }
    ]


def test_work_branch_service_scan_tolerates_malformed_and_ignored_files(tmp_path: Path) -> None:
    refs = FakeRefs()
    branch = "p2p/work/work-001-change-001-speckit"
    refs.branches = [branch]
    refs.files[(branch, ".p2p/work/WORK-001/manifest.yml")] = FakeFileAtRef("[")
    refs.files[(branch, ".p2p/work/WORK-001/notes.md")] = FakeFileAtRef("# ignored")
    refs.files[(branch, ".p2p/work/not-a-work/manifest.yml")] = FakeFileAtRef(
        yaml.safe_dump({"work_id": "ignored"}, sort_keys=False)
    )

    scan = _service(tmp_path, refs).scan()

    assert scan.scanned_branches == [branch]
    assert scan.work_items == []


def test_work_branch_service_scan_uses_defaults_for_partial_manifest(tmp_path: Path) -> None:
    refs = FakeRefs()
    branch = "p2p/work/work-002-change-002-generic"
    refs.branches = [branch]
    refs.files[(branch, ".p2p/work/WORK-002/manifest.yml")] = FakeFileAtRef(
        yaml.safe_dump({"git": []}, sort_keys=False)
    )

    scan = _service(tmp_path, refs).scan()

    assert scan.work_items == [
        {
            "work_id": "WORK-002",
            "status": "unknown",
            "change": "None",
            "target": "None",
            "branch": branch,
            "branch_name": branch,
            "path": ".p2p/work/WORK-002/manifest.yml",
        }
    ]


def test_work_branch_service_branch_updates_manifest_and_creates_branch(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "planned",
            "git": {"branch_name": branch_name, "base_branch": "main"},
            "managed_git_levels": [{"level": 2, "enabled": False}],
        },
    )
    git = FakeGit()

    result = _service(tmp_path, git=git).branch("WORK-001")

    assert result.branch_name == branch_name
    assert result.base_branch == "main"
    assert result.base_commit == "base-commit"
    assert result.head_commit == "branch-commit"
    assert result.path == Path(".p2p/work/WORK-001")
    assert git.created_branches == [branch_name]
    manifest = yaml.safe_load((_work_dir(tmp_path) / "manifest.yml").read_text(encoding="utf-8"))
    assert manifest["status"] == "branched"
    assert manifest["managed_git_levels"][0]["enabled"] is True
    assert manifest["git"]["mode"] == "managed_branch"
    assert manifest["git"]["current_branch"] == branch_name
    assert manifest["git"]["base_commit"] == "base-commit"
    assert manifest["git"]["head_commit"] == "branch-commit"


def test_work_branch_service_branch_requires_planned_status(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        {"work_id": "WORK-001", "status": "submitted", "git": {"branch_name": "p2p/work/work-001"}},
    )

    with pytest.raises(ValueError, match="Work item must be planned before branching"):
        _service(tmp_path).branch("WORK-001")


def test_work_branch_service_branch_rejects_dirty_worktree(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        {"work_id": "WORK-001", "status": "planned", "git": {"branch_name": "p2p/work/work-001"}},
    )
    git = FakeGit()
    git.status.is_clean = False

    with pytest.raises(ValueError, match="Cannot create managed work branch with uncommitted changes"):
        _service(tmp_path, git=git).branch("WORK-001")


def test_work_branch_service_branch_rejects_wrong_base_branch(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "planned",
            "git": {"branch_name": "p2p/work/work-001", "base_branch": "develop"},
        },
    )

    with pytest.raises(ValueError, match="expected base branch develop"):
        _service(tmp_path).branch("WORK-001")


def test_work_branch_service_branch_requires_git_mapping(tmp_path: Path) -> None:
    _write_manifest(tmp_path, {"work_id": "WORK-001", "status": "planned", "git": []})

    with pytest.raises(ValueError, match="Invalid Work manifest: git must be a mapping"):
        _service(tmp_path).branch("WORK-001")


def test_work_branch_service_submit_updates_manifest_and_commits(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "branched",
            "source": {"change": "CHANGE-001"},
            "git": {"branch_name": branch_name},
            "managed_git_levels": [{"level": 3, "enabled": False}],
        },
    )
    git = FakeGit()
    git.status.branch = branch_name
    git.changed = ["feature.txt", ".p2p/work/WORK-001/manifest.yml"]

    result = _service(tmp_path, git=git).submit("WORK-001")

    assert result.branch_name == branch_name
    assert result.commit == "submit-commit"
    assert result.changed_files == ["feature.txt"]
    assert git.commit_messages == ["P2P submit WORK-001: CHANGE-001"]
    manifest = yaml.safe_load((_work_dir(tmp_path) / "manifest.yml").read_text(encoding="utf-8"))
    assert manifest["status"] == "submitted"
    assert manifest["managed_git_levels"][0]["enabled"] is True
    assert manifest["git"]["mode"] == "managed_submit"
    assert manifest["submission"]["changed_files"] == ["feature.txt", ".p2p/work/WORK-001/manifest.yml"]
    assert manifest["submission"]["work_changes"] == ["feature.txt"]


def test_work_branch_service_submit_rejects_without_changes(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {"work_id": "WORK-001", "status": "branched", "git": {"branch_name": branch_name}},
    )
    git = FakeGit()
    git.status.branch = branch_name

    with pytest.raises(ValueError, match="Cannot submit managed work without changes"):
        _service(tmp_path, git=git).submit("WORK-001")


def test_work_branch_service_submit_rejects_manifest_only_changes(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {"work_id": "WORK-001", "status": "branched", "git": {"branch_name": branch_name}},
    )
    git = FakeGit()
    git.status.branch = branch_name
    git.changed = [".p2p/work/WORK-001/manifest.yml"]

    with pytest.raises(ValueError, match="Cannot submit managed work with only Work manifest changes"):
        _service(tmp_path, git=git).submit("WORK-001")


def test_work_branch_service_review_updates_manifest_and_commits(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "submitted",
            "git": {"branch_name": branch_name},
            "managed_git_levels": [{"level": 4, "enabled": False}],
        },
    )
    git = FakeGit()
    git.status.branch = branch_name
    git.head_commits = ["review-commit"]
    git.commit = "metadata-commit"

    result = _service(tmp_path, git=git).review("WORK-001")

    assert result.branch_name == branch_name
    assert result.review_commit == "review-commit"
    assert result.metadata_commit == "metadata-commit"
    assert git.commit_messages == ["P2P review WORK-001"]
    manifest = yaml.safe_load((_work_dir(tmp_path) / "manifest.yml").read_text(encoding="utf-8"))
    assert manifest["status"] == "review_requested"
    assert manifest["managed_git_levels"][0]["enabled"] is True
    assert manifest["git"]["mode"] == "managed_review"
    assert manifest["review"] == {
        "mode": "local_review",
        "review_commit": "review-commit",
        "pushed": False,
        "pull_request": None,
        "merged": False,
    }


def test_work_branch_service_review_requires_submitted_status(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        {"work_id": "WORK-001", "status": "branched", "git": {"branch_name": "p2p/work/work-001"}},
    )

    with pytest.raises(ValueError, match="Work item must be submitted before review"):
        _service(tmp_path).review("WORK-001")


def test_work_branch_service_review_rejects_dirty_worktree(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {"work_id": "WORK-001", "status": "submitted", "git": {"branch_name": branch_name}},
    )
    git = FakeGit()
    git.status.branch = branch_name
    git.status.is_clean = False

    with pytest.raises(ValueError, match="Cannot request managed work review with uncommitted changes"):
        _service(tmp_path, git=git).review("WORK-001")


def test_work_branch_service_publish_updates_manifest_commits_and_pushes(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "review_requested",
            "git": {"branch_name": branch_name},
            "review": {"review_commit": "review-commit"},
        },
    )
    git = FakeGit()
    git.status.branch = branch_name
    git.commit = "publish-commit"
    git.remote_urls["origin"] = "git@example.com:demo/project.git"

    result = _service(tmp_path, git=git).publish("WORK-001")

    assert result.branch_name == branch_name
    assert result.remote == "origin"
    assert result.remote_url == "git@example.com:demo/project.git"
    assert result.publish_commit == "publish-commit"
    assert git.commit_messages == ["P2P publish WORK-001"]
    assert git.pushed_branches == [(branch_name, "origin")]
    manifest = yaml.safe_load((_work_dir(tmp_path) / "manifest.yml").read_text(encoding="utf-8"))
    assert manifest["status"] == "published"
    assert manifest["git"]["mode"] == "managed_publish"
    assert manifest["publish"] == {
        "mode": "remote_branch",
        "remote": "origin",
        "remote_url": "git@example.com:demo/project.git",
        "remote_branch": branch_name,
        "review_commit": "review-commit",
        "pull_request": None,
        "merged": False,
    }


def test_work_branch_service_publish_requires_review_requested_status(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        {"work_id": "WORK-001", "status": "submitted", "git": {"branch_name": "p2p/work/work-001"}},
    )

    with pytest.raises(ValueError, match="Work item must be review_requested before publish"):
        _service(tmp_path).publish("WORK-001")


def test_work_branch_service_publish_rejects_missing_remote(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "review_requested",
            "git": {"branch_name": branch_name},
            "review": {"review_commit": "review-commit"},
        },
    )
    git = FakeGit()
    git.status.branch = branch_name

    with pytest.raises(ValueError, match="Cannot publish managed work: Git remote not found: origin"):
        _service(tmp_path, git=git).publish("WORK-001")


def test_work_branch_service_publish_requires_review_mapping_commit(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "review_requested",
            "git": {"branch_name": branch_name},
            "review": [],
        },
    )
    git = FakeGit()
    git.status.branch = branch_name
    git.remote_urls["origin"] = "git@example.com:demo/project.git"

    with pytest.raises(ValueError, match="Invalid Work manifest: review.review_commit is required before publish"):
        _service(tmp_path, git=git).publish("WORK-001")


def test_work_branch_service_request_external_review_records_profile_provider_metadata(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "published",
            "git": {"branch_name": branch_name},
            "publish": {
                "remote": "origin",
                "remote_url": "git@example.com:git-remote/project.git",
            },
        },
    )
    git = FakeGit()
    git.status.branch = branch_name
    git.commit = "review-request-commit"
    git.profile = FakeRemoteProfile(provider="github", url="git@github.com:example/demo.git")

    result = _service(tmp_path, git=git).request_external_review("WORK-001")

    assert result.provider == "github"
    assert result.remote == "origin"
    assert result.remote_url == "git@github.com:example/demo.git"
    assert result.metadata_commit == "review-request-commit"
    assert result.suggested_next == f"github|git@github.com:example/demo.git|{branch_name}"
    assert git.commit_messages == ["P2P request review WORK-001"]
    manifest = yaml.safe_load((_work_dir(tmp_path) / "manifest.yml").read_text(encoding="utf-8"))
    assert manifest["status"] == "published"
    assert manifest["external_review"]["provider"] == "github"
    assert manifest["external_review"]["remote_url"] == "git@github.com:example/demo.git"
    assert manifest["external_review"]["opens_external_request"] is False


def test_work_branch_service_request_external_review_converts_local_provider_to_generic(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "published",
            "git": {"branch_name": branch_name},
            "publish": {"remote": "origin", "remote_url": "git@example.com:demo/project.git"},
        },
    )
    git = FakeGit()
    git.status.branch = branch_name
    git.profile = FakeRemoteProfile(provider="local")

    result = _service(tmp_path, git=git).request_external_review("WORK-001")

    assert result.provider == "generic"
    assert result.suggested_next == f"generic|git@example.com:demo/project.git|{branch_name}"


def test_work_branch_service_request_external_review_rejects_invalid_provider(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "published",
            "git": {"branch_name": branch_name},
            "publish": {"remote": "origin", "remote_url": "git@example.com:demo/project.git"},
        },
    )
    git = FakeGit()
    git.status.branch = branch_name

    with pytest.raises(ValueError, match="External review provider must be generic, github, or gitlab"):
        _service(tmp_path, git=git).request_external_review("WORK-001", provider="bitbucket")


def test_work_branch_service_request_external_review_falls_back_to_git_remote_url(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "published",
            "git": {"branch_name": branch_name},
            "publish": {"remote": "upstream"},
        },
    )
    git = FakeGit()
    git.status.branch = branch_name
    git.remote_urls["upstream"] = "git@example.com:fallback/project.git"

    result = _service(tmp_path, git=git).request_external_review("WORK-001", provider="gitlab")

    assert result.provider == "gitlab"
    assert result.remote == "upstream"
    assert result.remote_url == "git@example.com:fallback/project.git"
    assert result.suggested_next == f"gitlab|git@example.com:fallback/project.git|{branch_name}"


def test_work_branch_service_request_external_review_requires_remote_url(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "published",
            "git": {"branch_name": branch_name},
            "publish": {"remote": "origin"},
        },
    )
    git = FakeGit()
    git.status.branch = branch_name

    with pytest.raises(ValueError, match="Cannot request external work review: Git remote not found: origin"):
        _service(tmp_path, git=git).request_external_review("WORK-001")


def test_work_branch_service_request_external_review_rejects_dirty_worktree(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "published",
            "git": {"branch_name": branch_name},
            "publish": {"remote": "origin", "remote_url": "git@example.com:demo/project.git"},
        },
    )
    git = FakeGit()
    git.status.branch = branch_name
    git.status.is_clean = False

    with pytest.raises(ValueError, match="Cannot request external work review with uncommitted changes"):
        _service(tmp_path, git=git).request_external_review("WORK-001")


def test_work_branch_service_accept_merges_published_branch(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    manifest_path = _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "published",
            "git": {"branch_name": branch_name, "base_branch": "main"},
            "managed_git_levels": [{"level": 5, "enabled": False}],
        },
    )
    refs = FakeRefs()
    refs.files[(branch_name, manifest_path.relative_to(tmp_path).as_posix())] = FakeFileAtRef(
        yaml.safe_dump({"work_id": "WORK-001", "status": "published"}, sort_keys=False)
    )
    git = FakeGit()
    git.existing_branches.add(branch_name)
    git.commit = "accept-commit"

    result = _service(tmp_path, refs=refs, git=git).accept("WORK-001")

    assert result.branch_name == branch_name
    assert result.base_branch == "main"
    assert result.merge_commit == "accept-commit"
    assert git.commit_messages == ["P2P accept WORK-001"]
    assert git.checked_out == ["main"]
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "accepted"
    assert manifest["managed_git_levels"][0]["enabled"] is True
    assert manifest["git"]["mode"] == "managed_accept"
    assert manifest["acceptance"] == {
        "mode": "local_merge",
        "source_branch": branch_name,
        "merged_into": "main",
        "pushed": False,
        "cleanup": False,
    }


def test_work_branch_service_accept_rejects_unpublished_branch_manifest(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    manifest_path = _write_manifest(
        tmp_path,
        {"work_id": "WORK-001", "git": {"branch_name": branch_name, "base_branch": "main"}},
    )
    refs = FakeRefs()
    refs.files[(branch_name, manifest_path.relative_to(tmp_path).as_posix())] = FakeFileAtRef(
        yaml.safe_dump({"work_id": "WORK-001", "status": "review_requested"}, sort_keys=False)
    )
    git = FakeGit()
    git.existing_branches.add(branch_name)

    with pytest.raises(ValueError, match="Work item must be published before accept"):
        _service(tmp_path, refs=refs, git=git).accept("WORK-001")


def test_work_branch_service_accept_records_merge_conflict(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    manifest_path = _write_manifest(
        tmp_path,
        {"work_id": "WORK-001", "git": {"branch_name": branch_name, "base_branch": "main"}},
    )
    refs = FakeRefs()
    refs.files[(branch_name, manifest_path.relative_to(tmp_path).as_posix())] = FakeFileAtRef(
        yaml.safe_dump(
            {
                "work_id": "WORK-001",
                "status": "published",
                "git": {"branch_name": branch_name, "base_branch": "main"},
            },
            sort_keys=False,
        )
    )
    git = FakeGit()
    git.existing_branches.add(branch_name)
    git.merge_succeeds = False
    git.conflicts = ["conflict.txt"]

    result = _service(tmp_path, refs=refs, git=git).accept("WORK-001")

    assert result.conflicted_files == ["conflict.txt"]
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "merge_conflict"
    assert manifest["git"]["mode"] == "managed_accept_conflict"
    assert manifest["merge_conflict"]["source_branch"] == branch_name
    assert manifest["merge_conflict"]["base_branch"] == "main"
    assert manifest["merge_conflict"]["continue_command"] == "p2p work accept --continue WORK-001"
    assert manifest["merge_conflict"]["abort_command"] == "p2p work accept --abort WORK-001"


def test_work_branch_service_continue_accept_rejects_unresolved_conflict_markers(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "merge_conflict",
            "git": {"branch_name": branch_name, "base_branch": "main"},
            "merge_conflict": {"source_branch": branch_name, "base_branch": "main"},
        },
    )
    (tmp_path / "conflict.txt").write_text("<<<<<<< ours\n=======\n>>>>>>> theirs\n", encoding="utf-8")
    git = FakeGit()
    git.merge_in_progress_value = True
    git.conflicts = ["conflict.txt"]

    with pytest.raises(ValueError, match="unresolved conflicts: conflict.txt"):
        _service(tmp_path, git=git).continue_accept("WORK-001")


def test_work_branch_service_continue_accept_marks_accepted_after_resolution(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    manifest_path = _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "merge_conflict",
            "git": {"branch_name": branch_name, "base_branch": "main"},
            "managed_git_levels": [{"level": 5, "enabled": False}],
            "merge_conflict": {"source_branch": branch_name, "base_branch": "main"},
        },
    )
    git = FakeGit()
    git.merge_in_progress_value = True
    git.commit = "accept-commit"

    result = _service(tmp_path, git=git).continue_accept("WORK-001")

    assert result.merge_commit == "accept-commit"
    assert git.staged is True
    assert git.commit_messages == ["P2P accept WORK-001"]
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "accepted"
    assert "merge_conflict" not in manifest
    assert manifest["managed_git_levels"][0]["enabled"] is True
    assert manifest["acceptance"]["resolved_conflict"] is True


def test_work_branch_service_abort_accept_restores_published_status(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    manifest_path = _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "merge_conflict",
            "git": {"branch_name": branch_name, "base_branch": "main"},
            "merge_conflict": {"source_branch": branch_name, "base_branch": "main"},
        },
    )
    git = FakeGit()
    git.merge_in_progress_value = True

    result = _service(tmp_path, git=git).abort_accept("WORK-001")

    assert result == {"work_id": "WORK-001"}
    assert git.restored_paths == [".p2p/work/WORK-001/manifest.yml"]
    assert git.commit_messages == ["P2P abort accept WORK-001"]
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "published"
    assert manifest["git"]["mode"] == "managed_publish"
    assert "merge_conflict" not in manifest
    assert manifest["acceptance_abort"] == {
        "source_branch": branch_name,
        "base_branch": "main",
        "aborted": True,
    }


def test_work_branch_service_finalize_updates_manifest_and_pushes_base_branch(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "accepted",
            "git": {"base_branch": "main"},
            "acceptance": {"merged_into": "main", "pushed": False},
        },
    )
    git = FakeGit()
    git.remote_urls["origin"] = "git@example.com:demo/project.git"
    git.commit = "finalize-commit"

    result = _service(tmp_path, git=git).finalize("WORK-001")

    assert result.base_branch == "main"
    assert result.remote == "origin"
    assert result.remote_url == "git@example.com:demo/project.git"
    assert result.finalize_commit == "finalize-commit"
    assert git.commit_messages == ["P2P finalize WORK-001"]
    assert git.pushed_branches == [("main", "origin")]
    manifest = yaml.safe_load((_work_dir(tmp_path) / "manifest.yml").read_text(encoding="utf-8"))
    assert manifest["status"] == "finalized"
    assert manifest["git"]["mode"] == "managed_finalize"
    assert manifest["acceptance"]["pushed"] is True
    assert manifest["finalize"] == {
        "mode": "base_branch_push",
        "remote": "origin",
        "remote_url": "git@example.com:demo/project.git",
        "base_branch": "main",
        "cleanup": False,
    }


def test_work_branch_service_finalize_requires_accepted_status(tmp_path: Path) -> None:
    _write_manifest(tmp_path, {"work_id": "WORK-001", "status": "published"})

    with pytest.raises(ValueError, match="Work item must be accepted before finalize"):
        _service(tmp_path).finalize("WORK-001")


def test_work_branch_service_finalize_rejects_missing_remote(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "accepted",
            "git": {"base_branch": "main"},
            "acceptance": {"merged_into": "main"},
        },
    )

    with pytest.raises(ValueError, match="Cannot finalize managed work: Git remote not found: origin"):
        _service(tmp_path).finalize("WORK-001")


def test_work_branch_service_cleanup_deletes_local_and_remote_branches(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "finalized",
            "git": {"branch_name": branch_name, "base_branch": "main"},
            "acceptance": {"source_branch": branch_name, "merged_into": "main"},
            "publish": {"remote_branch": branch_name, "remote": "origin"},
            "finalize": {"base_branch": "main", "remote": "origin", "cleanup": False},
        },
    )
    git = FakeGit()
    git.existing_branches.add(branch_name)
    git.remote_urls["origin"] = "git@example.com:demo/project.git"
    git.commit = "cleanup-commit"

    result = _service(tmp_path, git=git).cleanup("WORK-001", delete_remote=True)

    assert result.branch_name == branch_name
    assert result.base_branch == "main"
    assert result.remote == "origin"
    assert result.cleanup_commit == "cleanup-commit"
    assert result.local_deleted is True
    assert result.remote_deleted is True
    assert git.deleted_local_branches == [branch_name]
    assert git.deleted_remote_branches == [(branch_name, "origin")]
    assert git.pushed_branches == [("main", "origin")]
    manifest = yaml.safe_load((_work_dir(tmp_path) / "manifest.yml").read_text(encoding="utf-8"))
    assert manifest["status"] == "cleaned"
    assert manifest["git"]["mode"] == "managed_cleanup"
    assert manifest["finalize"]["cleanup"] is True
    assert manifest["cleanup"] == {
        "mode": "branch_cleanup",
        "source_branch": branch_name,
        "base_branch": "main",
        "remote": "origin",
        "remote_url": "git@example.com:demo/project.git",
        "local_deleted": True,
        "remote_deleted": True,
    }


def test_work_branch_service_cleanup_requires_finalized_status(tmp_path: Path) -> None:
    _write_manifest(tmp_path, {"work_id": "WORK-001", "status": "accepted"})

    with pytest.raises(ValueError, match="Work item must be finalized before cleanup"):
        _service(tmp_path).cleanup("WORK-001")


def test_work_branch_service_cleanup_requires_existing_managed_branch(tmp_path: Path) -> None:
    branch_name = "p2p/work/work-001-change-001-speckit"
    _write_manifest(
        tmp_path,
        {
            "work_id": "WORK-001",
            "status": "finalized",
            "git": {"branch_name": branch_name, "base_branch": "main"},
            "finalize": {"base_branch": "main", "remote": "origin"},
        },
    )
    git = FakeGit()
    git.remote_urls["origin"] = "git@example.com:demo/project.git"

    with pytest.raises(ValueError, match=f"Managed work branch not found: {branch_name}"):
        _service(tmp_path, git=git).cleanup("WORK-001")

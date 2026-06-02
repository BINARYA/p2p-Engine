from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitStatus:
    is_repository: bool
    branch: str | None
    is_clean: bool = False


@dataclass(frozen=True)
class GitFileAtRef:
    ref: str
    path: str
    content: str


def get_git_status(root: Path) -> GitStatus:
    is_repository = _run_git(root, "rev-parse", "--is-inside-work-tree") == "true"
    if not is_repository:
        return GitStatus(is_repository=False, branch=None, is_clean=False)
    branch = _run_git(root, "branch", "--show-current")
    status = _run_git(root, "status", "--porcelain")
    return GitStatus(is_repository=True, branch=branch, is_clean=status == "")


def head_commit(root: Path) -> str | None:
    return _run_git(root, "rev-parse", "HEAD")


def branch_exists(root: Path, branch_name: str) -> bool:
    return _run_git(root, "rev-parse", "--verify", "--quiet", branch_name) is not None


def create_and_checkout_branch(root: Path, branch_name: str) -> bool:
    return _run_git(root, "checkout", "-b", branch_name) is not None


def checkout_branch(root: Path, branch_name: str) -> bool:
    return _run_git(root, "checkout", branch_name) is not None


def rename_current_branch(root: Path, branch_name: str) -> bool:
    return _run_git(root, "branch", "-m", branch_name) is not None


def changed_files(root: Path) -> list[str]:
    output = _run_git(root, "status", "--porcelain")
    if output is None:
        return []
    files: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        path = line[2:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            files.append(path)
    return files


def commit_all(root: Path, message: str) -> str | None:
    if _run_git(root, "add", "-A") is None:
        return None
    if _run_git(root, "commit", "-m", message) is None:
        return None
    return head_commit(root)


def stage_all(root: Path) -> bool:
    return _run_git(root, "add", "-A") is not None


def remote_url(root: Path, remote: str = "origin") -> str | None:
    return _run_git(root, "remote", "get-url", remote)


def fetch_remote(root: Path, remote: str = "origin") -> bool:
    return _run_git(root, "fetch", remote) is not None


def pull_branch(root: Path, branch_name: str, remote: str = "origin") -> bool:
    return _run_git(root, "pull", "--ff-only", remote, branch_name) is not None


def push_branch(root: Path, branch_name: str, remote: str = "origin") -> bool:
    return _run_git(root, "push", "-u", remote, branch_name) is not None


def delete_local_branch(root: Path, branch_name: str) -> bool:
    return _run_git(root, "branch", "-d", branch_name) is not None


def delete_local_branch_force(root: Path, branch_name: str) -> bool:
    return _run_git(root, "branch", "-D", branch_name) is not None


def delete_remote_branch(root: Path, branch_name: str, remote: str = "origin") -> bool:
    return _run_git(root, "push", remote, "--delete", branch_name) is not None


def merge_branch_no_commit(root: Path, branch_name: str) -> bool:
    return _run_git(root, "merge", "--no-ff", "--no-commit", branch_name) is not None


def conflicted_files(root: Path) -> list[str]:
    output = _run_git(root, "diff", "--name-only", "--diff-filter=U")
    if output is None:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def merge_in_progress(root: Path) -> bool:
    return (root / ".git" / "MERGE_HEAD").exists()


def abort_merge(root: Path) -> bool:
    return _run_git(root, "merge", "--abort") is not None


def restore_path(root: Path, path: str) -> bool:
    return _run_git(root, "checkout", "--", path) is not None


def list_local_work_branches(root: Path) -> list[str]:
    output = _run_git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/p2p/work")
    if output is None:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def list_local_proposal_branches(root: Path) -> list[str]:
    output = _run_git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/p2p/proposal")
    if output is None:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def list_remote_proposal_branches(root: Path, remote: str = "origin") -> list[str]:
    output = _run_git(root, "ls-remote", "--heads", remote, "p2p/proposal/*")
    if output is None:
        return []
    branches: list[str] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        ref = parts[1]
        prefix = "refs/heads/"
        if ref.startswith(prefix):
            branches.append(ref.removeprefix(prefix))
    return branches


def list_files_at_ref(root: Path, ref: str, path: str) -> list[str]:
    output = _run_git(root, "ls-tree", "-r", "--name-only", ref, path)
    if output is None:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def read_file_at_ref(root: Path, ref: str, path: str) -> GitFileAtRef | None:
    output = _run_git(root, "show", f"{ref}:{path}")
    if output is None:
        return None
    return GitFileAtRef(ref=ref, path=path, content=output)


def _run_git(root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()

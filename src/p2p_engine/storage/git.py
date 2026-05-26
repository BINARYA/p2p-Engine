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


def list_local_work_branches(root: Path) -> list[str]:
    output = _run_git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/p2p/work")
    if output is None:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


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

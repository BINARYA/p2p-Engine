from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitStatus:
    is_repository: bool
    branch: str | None


@dataclass(frozen=True)
class GitFileAtRef:
    ref: str
    path: str
    content: str


def get_git_status(root: Path) -> GitStatus:
    branch = _run_git(root, "branch", "--show-current")
    return GitStatus(is_repository=branch is not None, branch=branch)


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

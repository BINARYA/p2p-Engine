from __future__ import annotations

import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def workspace_tree_snapshot(root: Path) -> tuple[tuple[str, str, str], ...]:
    entries: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        kind = "symlink" if path.is_symlink() else "file" if path.is_file() else "directory"
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        entries.append((relative, kind, digest))
    return tuple(entries)


@contextmanager
def assert_no_workspace_mutation(root: Path) -> Iterator[None]:
    before = workspace_tree_snapshot(root)
    yield
    after = workspace_tree_snapshot(root)
    assert after == before

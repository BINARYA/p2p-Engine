from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Literal


class UnsafeProjectStoragePath(ValueError):
    """Raised when an authoritative local-storage path is not safely confined."""


def lexical_absolute(path: Path) -> Path:
    """Return an absolute, normalized path without resolving filesystem links."""

    return Path(os.path.abspath(os.fspath(path)))


def is_link_or_reparse_point(path: Path) -> bool:
    """Recognize POSIX links and Windows junction/reparse-point indirection."""

    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if callable(is_junction) and is_junction():
            return True
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_flag)


def validate_confined_project_path(
    root: Path,
    path: Path,
    *,
    expected: Literal["file", "directory"],
    must_exist: bool,
) -> Path:
    """Validate a path without accepting indirection outside the project root.

    Every existing component below ``root`` is inspected with ``lstat`` semantics
    before the final resolved-containment check. Missing components are allowed
    only when ``must_exist`` is false, which supports safe initialization paths.
    """

    resolved_root = root.resolve()
    root_exists = resolved_root.exists()
    if root_exists and not resolved_root.is_dir():
        raise UnsafeProjectStoragePath("project root is not a directory")
    candidate = lexical_absolute(path)
    try:
        relative = candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise UnsafeProjectStoragePath("path is outside the project root") from exc

    if not relative.parts:
        if not root_exists and must_exist:
            raise UnsafeProjectStoragePath(f"required {expected} is missing")
        if expected != "directory":
            raise UnsafeProjectStoragePath("path is not a regular file")
        return candidate
    if not root_exists:
        if must_exist:
            raise UnsafeProjectStoragePath(f"required {expected} is missing")
        return candidate

    current = resolved_root
    missing_component = False
    for index, component in enumerate(relative.parts):
        current /= component
        is_leaf = index == len(relative.parts) - 1
        if is_link_or_reparse_point(current):
            raise UnsafeProjectStoragePath("path contains a symlink, junction, or reparse point")
        if missing_component or not current.exists():
            missing_component = True
            continue
        if not is_leaf and not current.is_dir():
            raise UnsafeProjectStoragePath("path parent is not a directory")
        if is_leaf:
            if expected == "file" and not current.is_file():
                raise UnsafeProjectStoragePath("path is not a regular file")
            if expected == "directory" and not current.is_dir():
                raise UnsafeProjectStoragePath("path is not a directory")

    if must_exist and missing_component:
        raise UnsafeProjectStoragePath(f"required {expected} is missing")
    try:
        if not candidate.resolve(strict=False).is_relative_to(resolved_root):
            raise UnsafeProjectStoragePath("path resolves outside the project root")
    except OSError as exc:
        raise UnsafeProjectStoragePath("path cannot be resolved safely") from exc
    return candidate

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

from p2p_engine.foundation.yaml_loaders import load_yaml


def slugify(value: str, *, fallback: str = "project") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def identity_slug(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Actor identity is required")
    return slugify(text)


def relative_to_root(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def yaml_dump(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


@dataclass(frozen=True)
class DurabilityReport:
    file_synced: bool
    directory_synced: bool
    directory_sync_supported: bool


def sync_directory(path: Path) -> bool:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except (AttributeError, NotImplementedError, OSError):
        return False
    try:
        os.fsync(descriptor)
    except (AttributeError, NotImplementedError, OSError):
        return False
    finally:
        os.close(descriptor)
    return True


def write_bytes_atomic(path: Path, content: bytes, *, mode: int | None = None) -> DurabilityReport:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=path.parent,
            delete=False,
        ) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)
        if mode is not None:
            temp_path.chmod(mode)
        temp_path.replace(path)
        directory_synced = sync_directory(path.parent)
        return DurabilityReport(
            file_synced=True,
            directory_synced=directory_synced,
            directory_sync_supported=directory_synced,
        )
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def write_text_atomic(path: Path, content: str, *, encoding: str = "utf-8") -> DurabilityReport:
    return write_bytes_atomic(path, content.encode(encoding))


def write_yaml_atomic(path: Path, data: object) -> DurabilityReport:
    return write_text_atomic(path, yaml_dump(data))


def read_yaml(path: Path, default: object) -> object:
    if not path.exists():
        return default
    data = load_yaml(path.read_bytes())
    return data if data is not None else default


def read_yaml_mapping(
    path: Path,
    default: dict[str, object],
    *,
    error_message: str | None = None,
) -> dict[str, object]:
    data = read_yaml(path, default)
    if not isinstance(data, dict):
        raise ValueError((error_message or "Invalid YAML mapping: {path}").format(path=path))
    return data


def read_yaml_mapping_or_default(
    path: Path,
    default: dict[str, object] | None = None,
) -> dict[str, object]:
    if not path.exists():
        return default or {}
    data = load_yaml(path.read_bytes())
    return data if isinstance(data, dict) else (default or {})

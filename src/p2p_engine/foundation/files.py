from __future__ import annotations

import re
from pathlib import Path

import yaml


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


def read_yaml(path: Path, default: object) -> object:
    if not path.exists():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
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
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else (default or {})

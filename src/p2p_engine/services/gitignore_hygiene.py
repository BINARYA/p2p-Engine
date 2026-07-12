from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from p2p_engine.foundation.files import write_text_atomic


BEGIN_MARKER = "# --- P2P local development artifacts ---"
END_MARKER = "# --- end P2P local development artifacts ---"
REQUIRED_PATTERNS = (
    ".venv/",
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "build/",
    "dist/",
    "*.egg-info/",
)


@dataclass(frozen=True)
class GitignoreHygieneResult:
    path: Path
    status: str
    added_patterns: list[str]
    warnings: list[str]


def apply_gitignore_hygiene(root: Path) -> GitignoreHygieneResult:
    path = Path(root) / ".gitignore"
    relative_path = Path(".gitignore")
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    warnings = _p2p_ignore_warnings(existing)
    if warnings:
        return GitignoreHygieneResult(
            path=relative_path,
            status="warning_only",
            added_patterns=[],
            warnings=warnings,
        )

    existing_keys = _existing_pattern_keys(existing)
    missing = [pattern for pattern in REQUIRED_PATTERNS if _pattern_key(pattern) not in existing_keys]
    if not missing:
        return GitignoreHygieneResult(
            path=relative_path,
            status="already_covered",
            added_patterns=[],
            warnings=[],
        )

    updated = _apply_missing_patterns(existing, missing)
    write_text_atomic(path, updated)
    return GitignoreHygieneResult(
        path=relative_path,
        status="applied",
        added_patterns=missing,
        warnings=[],
    )


def _apply_missing_patterns(existing: str, missing: list[str]) -> str:
    section = _section(missing)
    if not existing:
        return section
    if BEGIN_MARKER in existing and END_MARKER in existing:
        before, marker, after = existing.partition(END_MARKER)
        separator = "" if before.endswith("\n") else "\n"
        return f"{before}{separator}{_patterns_text(missing)}{marker}{after}"
    separator = "\n\n" if existing.endswith("\n") else "\n\n"
    return f"{existing}{separator}{section}"


def _section(patterns: list[str]) -> str:
    return f"{BEGIN_MARKER}\n{_patterns_text(patterns)}{END_MARKER}\n"


def _patterns_text(patterns: list[str]) -> str:
    return "".join(f"{pattern}\n" for pattern in patterns)


def _existing_pattern_keys(content: str) -> set[str]:
    keys: set[str] = set()
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue
        if stripped in {BEGIN_MARKER, END_MARKER}:
            continue
        keys.add(_pattern_key(stripped))
    return keys


def _pattern_key(pattern: str) -> str:
    normalized = pattern.strip().lstrip("/")
    while normalized.endswith("/"):
        normalized = normalized[:-1]
    return normalized


def _p2p_ignore_warnings(content: str) -> list[str]:
    warnings: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue
        normalized = stripped.lstrip("/")
        if _pattern_key(normalized) in {".p2p", "**/.p2p"}:
            warnings.append(
                "WARNING: `.p2p/` appears to be ignored by .gitignore. "
                "P2P governed state may not be tracked by Git. P2P did not modify your .gitignore automatically."
            )
            break
        if normalized in {".*", "**/.*"}:
            warnings.append(
                "WARNING: a broad dotfile ignore pattern may ignore `.p2p/`. "
                "P2P governed state may not be tracked by Git. P2P did not modify your .gitignore automatically."
            )
            break
    return warnings

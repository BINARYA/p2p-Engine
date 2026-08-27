#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "ROADMAP.md",
    ROOT / "docs",
)
LINK = re.compile(r"!?\[[^\]]*\]\((?P<target><[^>]+>|[^)\s]+)(?:\s+['\"][^)]*['\"])?\)")
IGNORED_PREFIXES = ("#", "http://", "https://", "mailto:")


def markdown_files() -> tuple[Path, ...]:
    files: list[Path] = []
    for root in DOC_ROOTS:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(root.rglob("*.md"))
    return tuple(sorted(files))


def broken_links() -> list[str]:
    issues: list[str] = []
    for document in markdown_files():
        text = document.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            raw = match.group("target").strip("<>")
            if raw.startswith(IGNORED_PREFIXES):
                continue
            relative = unquote(raw.split("#", 1)[0])
            if not relative:
                continue
            target = (document.parent / relative).resolve()
            try:
                target.relative_to(ROOT)
            except ValueError:
                issues.append(f"{document.relative_to(ROOT)}: link escapes repository: {raw}")
                continue
            if not target.exists():
                issues.append(f"{document.relative_to(ROOT)}: missing link target: {raw}")
    return issues


def main() -> int:
    issues = broken_links()
    if issues:
        for issue in issues:
            print(issue)
        return 1
    print(f"documentation links verified: files={len(markdown_files())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

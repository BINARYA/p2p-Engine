#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys

import p2p_engine


def _git_revision(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def provenance(root: Path) -> dict[str, object]:
    resolved_root = root.resolve()
    module_path = Path(p2p_engine.__file__).resolve()
    source_package = (resolved_root / "src" / "p2p_engine").resolve()
    return {
        "git_root": resolved_root.as_posix(),
        "git_revision": _git_revision(resolved_root),
        "module_path": module_path.as_posix(),
        "package_version": getattr(p2p_engine, "__version__", None),
        "python_executable": Path(sys.executable).resolve().as_posix(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "source_package": source_package.as_posix(),
        "uses_source_checkout": module_path == source_package / "__init__.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report P2P Engine import provenance.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--expect-source", action="store_true")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()
    payload = provenance(args.root)
    if args.format == "json":
        print(json.dumps(payload, sort_keys=True))
    else:
        for key in sorted(payload):
            print(f"{key}: {payload[key]}")
    if args.expect_source and not payload["uses_source_checkout"]:
        print("Expected import from the current source checkout.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

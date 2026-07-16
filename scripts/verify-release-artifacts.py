#!/usr/bin/env python3
from __future__ import annotations

import argparse
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import tarfile
import tomllib
import zipfile


FORBIDDEN_ROOTS = frozenset(
    {
        ".agents",
        ".codex",
        ".git",
        ".p2p",
        ".pytest_cache",
        ".venv",
        "dist",
        "drafts",
        "outputs",
        "specs",
    }
)
FORBIDDEN_PARTS = frozenset({"__pycache__", ".mypy_cache", ".ruff_cache", ".tox", ".nox"})


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate P2P Engine wheel and sdist contents.")
    parser.add_argument("--dist", type=Path, default=Path("dist"), help="Distribution directory")
    parser.add_argument("--version", help="Expected version; defaults to pyproject.toml")
    return parser.parse_args()


def _project_version() -> str:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def _normalized_members(names: list[str], *, archive_root: str | None) -> set[str]:
    normalized: set[str] = set()
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe archive member: {name}")
        parts = list(path.parts)
        if archive_root is not None:
            if not parts or parts[0] != archive_root:
                raise ValueError(f"sdist member outside {archive_root}: {name}")
            parts = parts[1:]
        if not parts:
            continue
        if parts[0] in FORBIDDEN_ROOTS:
            raise ValueError(f"forbidden release root: {name}")
        if any(part in FORBIDDEN_PARTS for part in parts):
            raise ValueError(f"forbidden cache path: {name}")
        if parts[-1].endswith((".pyc", ".pyo")):
            raise ValueError(f"forbidden bytecode: {name}")
        normalized.add(PurePosixPath(*parts).as_posix())
    return normalized


def _metadata_version(raw: bytes, *, target: str) -> str:
    value = BytesParser().parsebytes(raw).get("Version")
    if not value:
        raise ValueError(f"missing Version metadata in {target}")
    return value


def _require(members: set[str], required: set[str], *, target: str) -> None:
    missing = sorted(required - members)
    if missing:
        raise ValueError(f"missing required {target} members: {', '.join(missing)}")


def verify_wheel(path: Path, *, version: str) -> int:
    metadata = f"p2p_engine-{version}.dist-info/METADATA"
    required = {
        "p2p_engine/cli_commands/project_readiness.py",
        "p2p_engine/core/project_questions.py",
        "p2p_engine/core/project_readiness.py",
        "p2p_engine/core/project_readiness_convergence.py",
        "p2p_engine/mcp/catalog/project_readiness.py",
        "p2p_engine/mcp/handlers/project_readiness.py",
        "p2p_engine/resources/verticals/software_project/vertical.yml",
        "p2p_engine/services/agent_templates.py",
        "p2p_engine/services/project_questions.py",
        "p2p_engine/services/project_readiness.py",
        "p2p_engine/services/project_readiness_convergence.py",
        "p2p_engine/services/workspace_migration_handlers.py",
        "p2p_engine/services/workspace_operation_compatibility.py",
        metadata,
    }
    with zipfile.ZipFile(path) as archive:
        members = _normalized_members(archive.namelist(), archive_root=None)
        _require(members, required, target="wheel")
        actual_version = _metadata_version(archive.read(metadata), target=metadata)
    if actual_version != version:
        raise ValueError(f"wheel version {actual_version} does not match {version}")
    return len(members)


def verify_sdist(path: Path, *, version: str) -> int:
    archive_root = f"p2p_engine-{version}"
    required = {
        ".github/workflows/release.yml",
        "CHANGELOG.md",
        "README.md",
        "docs/WORKSPACE-MIGRATION.md",
        "PKG-INFO",
        "pyproject.toml",
        "scripts/verify-release-artifacts.py",
        "src/p2p_engine/core/project_questions.py",
        "src/p2p_engine/resources/verticals/software_project/vertical.yml",
        "src/p2p_engine/services/project_readiness_convergence.py",
        "src/p2p_engine/services/workspace_migration_handlers.py",
    }
    with tarfile.open(path, mode="r:gz") as archive:
        members = _normalized_members(archive.getnames(), archive_root=archive_root)
        _require(members, required, target="sdist")
        metadata_member = archive.getmember(f"{archive_root}/PKG-INFO")
        extracted = archive.extractfile(metadata_member)
        if extracted is None:
            raise ValueError("unable to read sdist PKG-INFO")
        actual_version = _metadata_version(extracted.read(), target="PKG-INFO")
    if actual_version != version:
        raise ValueError(f"sdist version {actual_version} does not match {version}")
    return len(members)


def main() -> int:
    args = _parse_args()
    version = args.version or _project_version()
    wheel = args.dist / f"p2p_engine-{version}-py3-none-any.whl"
    sdist = args.dist / f"p2p_engine-{version}.tar.gz"
    missing = [path.as_posix() for path in (wheel, sdist) if not path.is_file()]
    if missing:
        raise SystemExit("missing release artifacts: " + ", ".join(missing))

    try:
        wheel_count = verify_wheel(wheel, version=version)
        sdist_count = verify_sdist(sdist, version=version)
    except (KeyError, OSError, tarfile.TarError, ValueError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"release artifact verification failed: {exc}") from exc

    print(f"release artifacts verified: version={version} wheel_files={wheel_count} sdist_files={sdist_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
BUNDLED_VERTICAL_PACK_SECTIONS = {
    "base_project": (
        "010-vision.yml",
        "020-objective.yml",
        "030-stakeholders.yml",
        "040-scope.yml",
        "050-assumptions.yml",
        "060-risks.yml",
        "070-decisions.yml",
        "080-milestones.yml",
        "090-definition_of_done.yml",
        "100-artifacts.yml",
    ),
    "packaging_or_physical_product_design": (
        "010-contained_product.yml",
        "020-success_definition.yml",
        "030-user_experience.yml",
        "040-structure_materials.yml",
        "050-protection_logistics.yml",
        "060-production_cost.yml",
        "070-prototype_testing.yml",
    ),
    "social_impact_program_design": (
        "010-social_impact_vision.yml",
        "020-theory_of_change.yml",
        "030-beneficiary_communities.yml",
        "040-impact_areas.yml",
        "050-governance_accountability.yml",
        "060-measurement_reporting.yml",
        "070-program_roadmap.yml",
    ),
    "software_project": (
        "110-system_objective.yml",
        "120-users_and_actors.yml",
        "130-mvp_scope.yml",
        "140-workflows_use_cases.yml",
        "150-data_model.yml",
        "160-integrations_dependencies.yml",
        "170-constraints_nfrs.yml",
        "180-acceptance_validation.yml",
        "190-risks_alternatives_decisions.yml",
    ),
}
DECISION_LIFECYCLE_WHEEL_MEMBERS = {
    "p2p_engine/cli_commands/proposal_decisions.py",
    "p2p_engine/core/proposal_decision_diagnostics.py",
    "p2p_engine/core/proposal_decision_events.py",
    "p2p_engine/mcp/handlers/proposal_decisions.py",
    "p2p_engine/services/decision_context_ledger.py",
    "p2p_engine/services/proposal_decision_impact.py",
    "p2p_engine/services/proposal_decision_ledger.py",
    "p2p_engine/services/proposal_decision_legacy.py",
    "p2p_engine/services/proposal_decisions.py",
    "p2p_engine/services/workspace_migration_handlers.py",
    "p2p_engine/services/workspace_migration_registry.py",
    "p2p_engine/services/workspace_migrations.py",
}
DECISION_LIFECYCLE_SDIST_MEMBERS = {
    *(f"src/{member}" for member in DECISION_LIFECYCLE_WHEEL_MEMBERS),
    "tests/proposal_decision_fixtures.py",
    "tests/test_proposal_decision_cli.py",
    "tests/test_proposal_decision_ledger.py",
    "tests/test_workspace_v3_migration.py",
}


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


def _vertical_pack_required_members(package_prefix: str) -> set[str]:
    required: set[str] = set()
    for vertical_id, sections in BUNDLED_VERTICAL_PACK_SECTIONS.items():
        root = f"{package_prefix}/resources/verticals/{vertical_id}"
        required.update(
            {
                f"{root}/manifest.yml",
                f"{root}/vertical.yml",
                f"{root}/rubrics.yml",
            }
        )
        required.update(f"{root}/sections/{section}" for section in sections)
    return required


def verify_wheel(path: Path, *, version: str) -> int:
    metadata = f"p2p_engine-{version}.dist-info/METADATA"
    required = {
        "p2p_engine/cli_commands/project_readiness.py",
        "p2p_engine/core/project_questions.py",
        "p2p_engine/core/project_readiness.py",
        "p2p_engine/core/project_readiness_convergence.py",
        "p2p_engine/mcp/catalog/project_readiness.py",
        "p2p_engine/mcp/handlers/project_readiness.py",
        "p2p_engine/services/agent_templates.py",
        "p2p_engine/services/project_questions.py",
        "p2p_engine/services/project_readiness.py",
        "p2p_engine/services/project_readiness_convergence.py",
        "p2p_engine/services/workspace_migration_handlers.py",
        "p2p_engine/services/workspace_operation_compatibility.py",
        metadata,
    }
    required.update(DECISION_LIFECYCLE_WHEEL_MEMBERS)
    required.update(_vertical_pack_required_members("p2p_engine"))
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
        "src/p2p_engine/services/project_readiness_convergence.py",
        "src/p2p_engine/services/workspace_migration_handlers.py",
    }
    required.update(DECISION_LIFECYCLE_SDIST_MEMBERS)
    required.update(_vertical_pack_required_members("src/p2p_engine"))
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

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import NamedTuple

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
    "board_game_design": (
        "010-core_loop.yml",
        "020-components.yml",
        "030-rules.yml",
        "040-playtesting.yml",
    ),
    "grant_document_design": (
        "010-call_requirements.yml",
        "020-objectives.yml",
        "030-budget.yml",
        "040-evaluation_criteria.yml",
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
    "p2p_engine/services/proposal_decisions.py",
}
DECISION_LIFECYCLE_SDIST_MEMBERS = {
    *(f"src/{member}" for member in DECISION_LIFECYCLE_WHEEL_MEMBERS),
    "tests/proposal_decision_fixtures.py",
    "tests/test_proposal_decision_cli.py",
    "tests/test_proposal_decision_ledger.py",
    "tests/test_proposal_decision_service.py",
}
CURRENT_SCHEMA_WHEEL_MEMBERS = {
    "p2p_engine/cli_commands/workspace_schema.py",
    "p2p_engine/cli_commands/workspace_transactions.py",
    "p2p_engine/core/workspace_schema.py",
    "p2p_engine/services/workspace_operation_compatibility.py",
    "p2p_engine/services/workspace_schema.py",
    "p2p_engine/services/workspace_transactions.py",
    "p2p_engine/storage/filesystem.py",
}
CURRENT_SCHEMA_SDIST_MEMBERS = {
    *(f"src/{member}" for member in CURRENT_SCHEMA_WHEEL_MEMBERS),
    "tests/test_cli_workspace_transactions.py",
    "tests/test_mutation_preview_and_writer.py",
    "tests/test_workspace_operation_compatibility.py",
    "tests/test_workspace_read_context.py",
    "tests/test_workspace_schema_service.py",
}
PROJECT_STRUCTURE_WHEEL_MEMBERS = {
    "p2p_engine/cli_commands/project_structure.py",
    "p2p_engine/core/project_structure_export.py",
    "p2p_engine/core/project_structure.py",
    "p2p_engine/core/project_structure_replacement.py",
    "p2p_engine/core/project_structure_retirement.py",
    "p2p_engine/mcp/catalog/project.py",
    "p2p_engine/mcp/handlers/project.py",
    "p2p_engine/services/project_structure.py",
    "p2p_engine/services/project_structure_export.py",
    "p2p_engine/services/project_structure_replacement.py",
    "p2p_engine/services/project_structure_retirement.py",
}
PROJECT_STRUCTURE_SDIST_MEMBERS = {
    *(f"src/{member}" for member in PROJECT_STRUCTURE_WHEEL_MEMBERS),
    "docs/CLI-CONTRACT.md",
    "docs/CLI-GUIDE.md",
    "docs/MCP.md",
    "docs/WORKSPACE-SCHEMA.md",
    "tests/test_project_structure.py",
    "tests/test_project_structure_export.py",
    "tests/test_project_structure_replacement.py",
    "tests/test_skeleton.py",
}
PROJECT_MEMORY_WHEEL_MEMBERS = {
    "p2p_engine/cli_commands/project_memory.py",
    "p2p_engine/core/project_memory.py",
    "p2p_engine/mcp/catalog/project.py",
    "p2p_engine/mcp/handlers/project.py",
    "p2p_engine/services/project_memory.py",
}
PROJECT_MEMORY_SDIST_MEMBERS = {
    *(f"src/{member}" for member in PROJECT_MEMORY_WHEEL_MEMBERS),
    "docs/CLI-CONTRACT.md",
    "docs/CLI-GUIDE.md",
    "docs/MCP.md",
    "tests/fixtures/project_memory/current-contract-v1.json",
    "tests/test_project_memory_classification.py",
    "tests/test_skeleton.py",
}
CLI_CONTRACT_WHEEL_MEMBERS = {
    "p2p_engine/cli.py",
    "p2p_engine/cli_contract.py",
    "p2p_engine/cli_shared.py",
    "p2p_engine/cli_commands/mutations.py",
}
CLI_CONTRACT_SDIST_MEMBERS = {
    *(f"src/{member}" for member in CLI_CONTRACT_WHEEL_MEMBERS),
    "docs/CLI-CONTRACT.md",
    "tests/cli_assertions.py",
    "tests/fixtures/cli_contract/error-v1.json",
    "tests/fixtures/cli_contract/success-v1.json",
    "tests/test_cli_contract.py",
}
PORTABLE_VERTICAL_WHEEL_MEMBERS = {
    "p2p_engine/core/mutation_receipts.py",
    "p2p_engine/core/portable_verticals.py",
    "p2p_engine/core/project_verticals.py",
    "p2p_engine/services/mutation_receipts.py",
    "p2p_engine/services/project_verticals.py",
    "p2p_engine/services/vertical_lifecycle.py",
    "p2p_engine/services/vertical_packages.py",
}
PORTABLE_VERTICAL_SDIST_MEMBERS = {
    *(f"src/{member}" for member in PORTABLE_VERTICAL_WHEEL_MEMBERS),
    "tests/test_mutation_receipts.py",
    "tests/test_portable_verticals.py",
}
TYPED_VERTICAL_TRANSITION_WHEEL_MEMBERS = {
    "p2p_engine/core/vertical_transition_impact.py",
    "p2p_engine/core/vertical_transition_plan.py",
    "p2p_engine/services/vertical_evidence_classifier.py",
    "p2p_engine/services/vertical_transition_analysis.py",
    "p2p_engine/services/vertical_transition_materialization.py",
}
TYPED_VERTICAL_TRANSITION_SDIST_MEMBERS = {
    *(f"src/{member}" for member in TYPED_VERTICAL_TRANSITION_WHEEL_MEMBERS),
    "docs/development/wavekit-vertical-transition-handoff.md",
    "tests/fixtures/vertical_transition/adoption-apply-v1.json",
    "tests/fixtures/vertical_transition/adoption-empty-v1.json",
    "tests/fixtures/vertical_transition/adoption-populated-v1.json",
    "tests/fixtures/vertical_transition/install-apply-v1.json",
    "tests/fixtures/vertical_transition/install-preview-v1.json",
    "tests/fixtures/vertical_transition/legacy-0.4.7-characterization.json",
    "tests/fixtures/vertical_transition/manifest-v1.json",
    "tests/fixtures/vertical_transition/migration-apply-v1.json",
    "tests/fixtures/vertical_transition/migration-complete-plan-v1.json",
    "tests/fixtures/vertical_transition/migration-decision-required-v1.json",
    "tests/test_vertical_transition_impact.py",
}
VERTICAL_REGISTRY_WHEEL_MEMBERS = {
    "p2p_engine/adapters/credential_store.py",
    "p2p_engine/adapters/vertical_registry_http.py",
    "p2p_engine/cli_commands/verticals.py",
    "p2p_engine/core/vertical_registry.py",
    "p2p_engine/mcp/catalog/vertical_registry.py",
    "p2p_engine/mcp/handlers/vertical_registry.py",
    "p2p_engine/services/vertical_catalog.py",
    "p2p_engine/services/vertical_registry.py",
}
VERTICAL_REGISTRY_SDIST_MEMBERS = {
    *(f"src/{member}" for member in VERTICAL_REGISTRY_WHEEL_MEMBERS),
    "docs/VERTICAL-REGISTRY.md",
    "tests/test_vertical_registry.py",
    "tests/test_vertical_registry_remote.py",
}
VERTICAL_DRAFT_WHEEL_MEMBERS = {
    "p2p_engine/core/vertical_drafts.py",
    "p2p_engine/services/vertical_draft_lifecycle.py",
    "p2p_engine/services/vertical_draft_materializer.py",
    "p2p_engine/services/vertical_drafts.py",
}
VERTICAL_DRAFT_SDIST_MEMBERS = {
    *(f"src/{member}" for member in VERTICAL_DRAFT_WHEEL_MEMBERS),
    "docs/VERTICAL-DRAFTS.md",
    "tests/fixtures/vertical_drafts/create-v1.json",
    "tests/fixtures/vertical_drafts/inspect-v1.json",
    "tests/fixtures/vertical_drafts/publication-v1.json",
    "tests/fixtures/vertical_drafts/update-v1.json",
    "tests/fixtures/vertical_drafts/validation-v1.json",
    "tests/test_vertical_drafts.py",
}
CURRENT_SURFACE_WHEEL_MEMBERS = {
    "p2p_engine/services/agent_capabilities.py",
    "p2p_engine/services/agent_instructions.py",
    "p2p_engine/services/agent_templates.py",
    "p2p_engine/services/public_surface_inventory.py",
}
CURRENT_SURFACE_SDIST_MEMBERS = {
    *(f"src/{member}" for member in CURRENT_SURFACE_WHEEL_MEMBERS),
    "tests/test_current_only_surface.py",
    "tests/test_public_surface_inventory.py",
    "tests/test_version_consistency.py",
}
UV_INSTALLATION_WHEEL_MEMBERS = {
    "p2p_engine/cli_commands/doctor.py",
    "p2p_engine/services/installation_guidance.py",
    "p2p_engine/services/mcp_hints.py",
    "p2p_engine/services/runtime_contract.py",
}
UV_INSTALLATION_SDIST_MEMBERS = {
    *(f"src/{member}" for member in UV_INSTALLATION_WHEEL_MEMBERS),
    "docs/AGENT-INTEGRATION.md",
    "docs/CLI-GUIDE.md",
    "docs/INSTALL.md",
    "docs/MCP.md",
    "docs/TUTORIAL.md",
    "scripts/test-uv-installed.py",
    "tests/test_doctor_discovery.py",
    "tests/test_installation_guidance.py",
    "tests/test_mcp_hint_service.py",
    "tests/test_uv_installation_docs.py",
    "tests/test_uv_installation_harness.py",
}
RELEASE_CONVERGENCE_WHEEL_MEMBERS = {
    "p2p_engine/core/release_contracts.py",
    "p2p_engine/resources/contracts/__init__.py",
    "p2p_engine/resources/contracts/wavekit-cli-fixtures-v1.json",
    "p2p_engine/services/release_convergence.py",
}
RELEASE_CONVERGENCE_SDIST_MEMBERS = {
    *(f"src/{member}" for member in RELEASE_CONVERGENCE_WHEEL_MEMBERS),
    "docs/development/project-structure-surface-convergence.md",
    "scripts/verify-convergence-gate.py",
    "tests/test_release_convergence.py",
}
DISCARDED_SURFACE_TOKENS = (
    "legacy_undeclared",
    "absent_legacy",
    "legacy_absent",
    "legacy_unverifiable",
    "current_legacy",
    "unknown_legacy",
    "unknown_origin",
    "legacy_mtime_fallback",
    "current_legacy_fallback",
    "workspace migrate",
    "legacy-resolution",
    "mark-legacy",
    "proposal_decision_legacy",
    "codex-legacy",
)
REMOVED_PACKAGE_MEMBERS = {
    "p2p_engine/core/project.py",
    "p2p_engine/core/task.py",
    "p2p_engine/core/plan.py",
    "p2p_engine/exporters/markdown.py",
    "p2p_engine/exporters/openspec.py",
    "p2p_engine/storage/git.py",
    "p2p_engine/services/sync.py",
    "p2p_engine/services/proposal_branches.py",
    "p2p_engine/services/work_branches.py",
    "p2p_engine/services/proposal_drafts.py",
    "p2p_engine/services/gitignore_hygiene.py",
    "p2p_engine/services/remote_profile.py",
}
REMOVED_PRODUCT_TOKENS = (
    "p2p_sync_status",
    "p2p_sync_fetch",
    "p2p_sync_pull",
    "p2p_sync_push",
    "p2p_project_remote_show",
    "p2p_project_remote_configure",
    "p2p_proposal_draft_commit",
    "p2p_proposal_branch",
    "p2p_proposal_branch_status",
    "p2p_proposal_publish",
    "p2p_proposal_request_review",
    "p2p_proposal_accept_branch",
    "p2p_proposal_reject_branch",
    "p2p_proposal_merge",
    "p2p_proposal_finalize",
    "p2p_proposal_cleanup",
    "p2p_proposal_branch_scan",
    "p2p_work_branch",
    "p2p_work_submit",
    "p2p_work_review",
    "p2p_work_publish",
    "p2p_work_request_review",
    "p2p_work_accept",
    "p2p_work_finalize",
    "p2p_work_cleanup",
    "managed_git_collaboration",
    "raw_git_managed_branch",
)
SDIST_REMOVED_TOKEN_ALLOWLIST = {
    "scripts/check-source-boundary.py": {
        "p2p_sync_status", "p2p_sync_fetch", "p2p_sync_pull", "p2p_sync_push",
        "p2p_project_remote_show", "p2p_project_remote_configure",
        "p2p_proposal_draft_commit", "p2p_proposal_branch",
        "p2p_proposal_branch_status", "p2p_proposal_publish",
        "p2p_proposal_request_review", "p2p_proposal_accept_branch",
        "p2p_proposal_reject_branch", "p2p_proposal_merge",
        "p2p_proposal_finalize", "p2p_proposal_cleanup",
        "p2p_proposal_branch_scan", "p2p_work_branch", "p2p_work_submit",
        "p2p_work_review", "p2p_work_publish", "p2p_work_request_review",
        "p2p_work_accept", "p2p_work_finalize", "p2p_work_cleanup",
    },
    "scripts/test-installed.sh": set(REMOVED_PRODUCT_TOKENS) - {
        "managed_git_collaboration", "raw_git_managed_branch",
    },
    "scripts/verify-release-artifacts.py": set(REMOVED_PRODUCT_TOKENS),
    "tests/test_mcp.py": {
        "p2p_sync_status", "p2p_sync_fetch", "p2p_sync_pull", "p2p_sync_push",
        "p2p_project_remote_show", "p2p_project_remote_configure",
        "p2p_proposal_draft_commit", "p2p_proposal_branch",
        "p2p_proposal_branch_status", "p2p_proposal_publish",
        "p2p_proposal_request_review", "p2p_proposal_accept_branch",
        "p2p_proposal_reject_branch", "p2p_proposal_merge",
        "p2p_proposal_finalize", "p2p_proposal_cleanup",
        "p2p_proposal_branch_scan", "p2p_work_branch", "p2p_work_submit",
        "p2p_work_review", "p2p_work_publish", "p2p_work_request_review",
        "p2p_work_accept", "p2p_work_finalize", "p2p_work_cleanup",
        "managed_git_collaboration",
    },
    "tests/test_mcp_collaboration_handler.py": {
        "p2p_sync_status", "p2p_project_remote_show", "p2p_proposal_branch",
        "p2p_proposal_draft_commit", "p2p_work_branch",
    },
    "tests/test_release_artifacts.py": {"p2p_sync_status"},
}
SDIST_DISCARDED_TOKEN_ALLOWLIST = {
    # Guard implementations and negative regressions must name what they reject.
    "scripts/verify-release-artifacts.py": set(DISCARDED_SURFACE_TOKENS),
    "tests/test_agent_instructions_service.py": {"legacy_undeclared", "codex-legacy"},
    "tests/test_current_only_surface.py": set(DISCARDED_SURFACE_TOKENS),
    "tests/test_proposal_artifact_state_service.py": {"mark-legacy"},
    "tests/test_release_artifacts.py": {"proposal_decision_legacy"},
}
SDIST_PRIVATE_PATTERN_ALLOWLIST = {
    # Negative regressions deliberately contain synthetic host paths/key markers.
    "tests/test_project_verticals.py": {"POSIX home path"},
    "tests/test_release_artifacts.py": {"POSIX home path", "UNC path", "private key"},
    # The verifier must contain the UNC detector it applies to archive members.
    "scripts/verify-release-artifacts.py": {"UNC path"},
}
TEXT_SUFFIXES = frozenset(
    {
        ".cfg",
        ".html",
        ".ini",
        ".json",
        ".md",
        ".py",
        ".rst",
        ".sh",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
MAX_TEXT_MEMBER_BYTES = 1024 * 1024
PRIVATE_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "OpenAI-style secret": re.compile(rb"\bsk-[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "POSIX home path": re.compile(rb"(?:^|[\s\"'])/(?:home|Users)/[^\s\"']+"),
    "Windows home path": re.compile(rb"\b[A-Za-z]:\\Users\\[^\s\"']+", re.IGNORECASE),
    "UNC path": re.compile(rb"\\\\[^\\\s]+\\[^\\\s]+"),
}


class ProjectMetadataContract(NamedTuple):
    name: str
    version: str
    requires_python: str
    license_expression: str
    authors: tuple[str, ...]
    maintainers: tuple[str, ...]
    urls: dict[str, str]
    dependencies: frozenset[str]
    classifiers: frozenset[str]


def _project_metadata_contract() -> ProjectMetadataContract:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    return ProjectMetadataContract(
        name=str(project["name"]),
        version=str(project["version"]),
        requires_python=str(project["requires-python"]),
        license_expression=str(project["license"]),
        authors=tuple(str(item["name"]) for item in project["authors"]),
        maintainers=tuple(str(item["name"]) for item in project["maintainers"]),
        urls={str(key): str(value) for key, value in project["urls"].items()},
        dependencies=frozenset(str(value) for value in project["dependencies"]),
        classifiers=frozenset(str(value) for value in project.get("classifiers", [])),
    )


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


def _verify_core_metadata(raw: bytes, *, version: str, target: str) -> None:
    metadata = BytesParser().parsebytes(raw)
    expected = _project_metadata_contract()
    exact_fields = {
        "Name": expected.name,
        "Version": version,
        "Requires-Python": expected.requires_python,
        "License-Expression": expected.license_expression,
        "Author": ", ".join(expected.authors),
        "Maintainer": ", ".join(expected.maintainers),
    }
    for field, value in exact_fields.items():
        if metadata.get(field) != value:
            raise ValueError(
                f"{target} metadata {field} is {metadata.get(field)!r}, expected {value!r}"
            )
    if "LICENSE" not in set(metadata.get_all("License-File", [])):
        raise ValueError(f"{target} metadata does not declare LICENSE")
    actual_urls: dict[str, str] = {}
    for value in metadata.get_all("Project-URL", []):
        label, separator, url = value.partition(",")
        if not separator:
            raise ValueError(f"malformed Project-URL in {target}: {value}")
        actual_urls[label.strip()] = url.strip()
    if actual_urls != expected.urls:
        raise ValueError(f"{target} project URLs do not match pyproject.toml")
    actual_dependencies = set(metadata.get_all("Requires-Dist", []))
    missing_dependencies = sorted(expected.dependencies - actual_dependencies)
    if missing_dependencies:
        raise ValueError(
            f"{target} metadata is missing runtime dependencies: "
            + ", ".join(missing_dependencies)
        )
    if not expected.classifiers <= set(metadata.get_all("Classifier", [])):
        raise ValueError(f"{target} metadata classifiers do not match pyproject.toml")


def _require_version(actual: str, expected: str, *, target: str) -> None:
    if actual != expected:
        raise ValueError(f"{target} version {actual} does not match {expected}")


def _require(members: set[str], required: set[str], *, target: str) -> None:
    missing = sorted(required - members)
    if missing:
        raise ValueError(f"missing required {target} members: {', '.join(missing)}")


def _require_used_allowlist(
    members: set[str],
    configured: dict[str, set[str]],
    used: dict[str, set[str]],
    *,
    label: str,
) -> None:
    for member, allowed in configured.items():
        if member not in members:
            raise ValueError(f"{label} allowlist member is absent: {member}")
        unused = sorted(allowed - used.get(member, set()))
        if unused:
            raise ValueError(
                f"unused {label} allowlist entries for {member}: {', '.join(unused)}"
            )


def _reject_discarded_surface(
    content: bytes,
    *,
    member: str,
    target: str,
    allowed: set[str] | None = None,
) -> set[str]:
    text = content.decode("utf-8", errors="ignore")
    hits = {token for token in DISCARDED_SURFACE_TOKENS if token in text}
    unexpected = sorted(hits - (allowed or set()))
    if unexpected:
        raise ValueError(
            f"discarded compatibility surface in {target} member {member}: "
            + ", ".join(unexpected)
        )
    return hits


def _scan_text_member(
    content: bytes,
    *,
    member: str,
    target: str,
    allowed_removed_tokens: set[str] | None = None,
    allowed_discarded_tokens: set[str] | None = None,
    allowed_private_patterns: set[str] | None = None,
) -> set[str]:
    if len(content) > MAX_TEXT_MEMBER_BYTES:
        raise ValueError(f"text member exceeds scan bound in {target}: {member}")
    _reject_discarded_surface(
        content,
        member=member,
        target=target,
        allowed=allowed_discarded_tokens,
    )
    text = content.decode("utf-8", errors="ignore")
    removed = {token for token in REMOVED_PRODUCT_TOKENS if token in text}
    unexpected = sorted(removed - (allowed_removed_tokens or set()))
    if unexpected:
        raise ValueError(
            f"removed product surface in {target} member {member}: {', '.join(unexpected)}"
        )
    private_hits = _private_pattern_hits(content)
    unexpected_private = sorted(private_hits - (allowed_private_patterns or set()))
    if unexpected_private:
        raise ValueError(
            f"{', '.join(unexpected_private)} detected in {target} member {member}"
        )
    return removed


def _private_pattern_hits(content: bytes) -> set[str]:
    return {label for label, pattern in PRIVATE_PATTERNS.items() if pattern.search(content)}


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
    entry_points = f"p2p_engine-{version}.dist-info/entry_points.txt"
    license_member = f"p2p_engine-{version}.dist-info/licenses/LICENSE"
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
        "p2p_engine/services/workspace_operation_compatibility.py",
        metadata,
        entry_points,
        license_member,
    }
    required.update(DECISION_LIFECYCLE_WHEEL_MEMBERS)
    required.update(CURRENT_SCHEMA_WHEEL_MEMBERS)
    required.update(PROJECT_STRUCTURE_WHEEL_MEMBERS)
    required.update(PROJECT_MEMORY_WHEEL_MEMBERS)
    required.update(CLI_CONTRACT_WHEEL_MEMBERS)
    required.update(PORTABLE_VERTICAL_WHEEL_MEMBERS)
    required.update(TYPED_VERTICAL_TRANSITION_WHEEL_MEMBERS)
    required.update(VERTICAL_REGISTRY_WHEEL_MEMBERS)
    required.update(VERTICAL_DRAFT_WHEEL_MEMBERS)
    required.update(CURRENT_SURFACE_WHEEL_MEMBERS)
    required.update(UV_INSTALLATION_WHEEL_MEMBERS)
    required.update(RELEASE_CONVERGENCE_WHEEL_MEMBERS)
    required.update(_vertical_pack_required_members("p2p_engine"))
    with zipfile.ZipFile(path) as archive:
        members = _normalized_members(archive.namelist(), archive_root=None)
        _require(members, required, target="wheel")
        forbidden = sorted(REMOVED_PACKAGE_MEMBERS & members)
        if forbidden:
            raise ValueError("removed wheel members present: " + ", ".join(forbidden))
        for member in sorted(members):
            if PurePosixPath(member).suffix.lower() in TEXT_SUFFIXES:
                _scan_text_member(archive.read(member), member=member, target="wheel")
        actual_version = _metadata_version(archive.read(metadata), target=metadata)
        _verify_core_metadata(archive.read(metadata), version=version, target="wheel")
        if archive.read(license_member) != Path("LICENSE").read_bytes():
            raise ValueError("wheel LICENSE bytes do not match the source license")
        scripts = archive.read(entry_points).decode("utf-8")
        if "p2p = p2p_engine.cli:app" not in scripts or "p2p-mcp-server = p2p_engine.mcp.server:main" not in scripts:
            raise ValueError("wheel console entry points are incomplete")
    _require_version(actual_version, version, target="wheel")
    return len(members)


def verify_sdist(path: Path, *, version: str) -> int:
    archive_root = f"p2p_engine-{version}"
    required = {
        ".github/workflows/release.yml",
        ".github/workflows/ci.yml",
        ".github/workflows/release-candidate.yml",
        "AGENTS.md",
        "CHANGELOG.md",
        "CLAUDE.md",
        "LICENSE",
        "README.md",
        "security-audit-exceptions.yml",
        "docs/WORKSPACE-SCHEMA.md",
        f"docs/releases/{version}.md",
        "PKG-INFO",
        "pyproject.toml",
        "scripts/verify-release-artifacts.py",
        "scripts/verify-release-metadata.py",
        "scripts/verify-audit-exceptions.py",
        "scripts/audit-wheel.sh",
        "scripts/build-release-candidate.sh",
        "scripts/check-static.sh",
        "scripts/check-doc-links.py",
        "scripts/test-installed.sh",
        "scripts/test-uv-installed.py",
        "scripts/archive-project-state.py",
        "src/p2p_engine/core/project_questions.py",
        "src/p2p_engine/services/project_readiness_convergence.py",
        "tests/test_archive_project_state_script.py",
    }
    required.update(DECISION_LIFECYCLE_SDIST_MEMBERS)
    required.update(CURRENT_SCHEMA_SDIST_MEMBERS)
    required.update(PROJECT_STRUCTURE_SDIST_MEMBERS)
    required.update(PROJECT_MEMORY_SDIST_MEMBERS)
    required.update(CLI_CONTRACT_SDIST_MEMBERS)
    required.update(PORTABLE_VERTICAL_SDIST_MEMBERS)
    required.update(TYPED_VERTICAL_TRANSITION_SDIST_MEMBERS)
    required.update(VERTICAL_REGISTRY_SDIST_MEMBERS)
    required.update(VERTICAL_DRAFT_SDIST_MEMBERS)
    required.update(CURRENT_SURFACE_SDIST_MEMBERS)
    required.update(UV_INSTALLATION_SDIST_MEMBERS)
    required.update(RELEASE_CONVERGENCE_SDIST_MEMBERS)
    required.update(_vertical_pack_required_members("src/p2p_engine"))
    with tarfile.open(path, mode="r:gz") as archive:
        members = _normalized_members(archive.getnames(), archive_root=archive_root)
        _require(members, required, target="sdist")
        forbidden = sorted({f"src/{member}" for member in REMOVED_PACKAGE_MEMBERS} & members)
        if forbidden:
            raise ValueError("removed sdist members present: " + ", ".join(forbidden))
        if "P2P-SETUP.md" in members:
            raise ValueError("stale repository-root P2P-SETUP.md is packaged")
        used_allowlist: dict[str, set[str]] = {}
        used_discarded_allowlist: dict[str, set[str]] = {}
        used_private_allowlist: dict[str, set[str]] = {}
        for member in sorted(members):
            if PurePosixPath(member).suffix.lower() not in TEXT_SUFFIXES:
                continue
            extracted_member = archive.extractfile(f"{archive_root}/{member}")
            if extracted_member is not None:
                content = extracted_member.read()
                used_allowlist[member] = _scan_text_member(
                    content,
                    member=member,
                    target="sdist",
                    allowed_removed_tokens=SDIST_REMOVED_TOKEN_ALLOWLIST.get(member),
                    allowed_discarded_tokens=SDIST_DISCARDED_TOKEN_ALLOWLIST.get(member),
                    allowed_private_patterns=SDIST_PRIVATE_PATTERN_ALLOWLIST.get(member),
                )
                used_discarded_allowlist[member] = _reject_discarded_surface(
                    content,
                    member=member,
                    target="sdist",
                    allowed=SDIST_DISCARDED_TOKEN_ALLOWLIST.get(member),
                )
                used_private_allowlist[member] = _private_pattern_hits(content)
        _require_used_allowlist(
            members,
            SDIST_REMOVED_TOKEN_ALLOWLIST,
            used_allowlist,
            label="removed-token",
        )
        _require_used_allowlist(
            members,
            SDIST_DISCARDED_TOKEN_ALLOWLIST,
            used_discarded_allowlist,
            label="discarded-token",
        )
        _require_used_allowlist(
            members,
            SDIST_PRIVATE_PATTERN_ALLOWLIST,
            used_private_allowlist,
            label="private-pattern",
        )
        metadata_member = archive.getmember(f"{archive_root}/PKG-INFO")
        extracted = archive.extractfile(metadata_member)
        if extracted is None:
            raise ValueError("unable to read sdist PKG-INFO")
        actual_version = _metadata_version(extracted.read(), target="PKG-INFO")
        metadata_stream = archive.extractfile(metadata_member)
        if metadata_stream is None:
            raise ValueError("unable to reread sdist PKG-INFO")
        _verify_core_metadata(
            metadata_stream.read(),
            version=version,
            target="sdist",
        )
        license_stream = archive.extractfile(f"{archive_root}/LICENSE")
        if license_stream is None or license_stream.read() != Path("LICENSE").read_bytes():
            raise ValueError("sdist LICENSE bytes do not match the source license")
    _require_version(actual_version, version, target="sdist")
    return len(members)


def main() -> int:
    args = _parse_args()
    version = args.version or _project_version()
    wheel = args.dist / f"p2p_engine-{version}-py3-none-any.whl"
    sdist = args.dist / f"p2p_engine-{version}.tar.gz"
    missing = [path.as_posix() for path in (wheel, sdist) if not path.is_file()]
    if missing:
        raise SystemExit("missing release artifacts: " + ", ".join(missing))
    allowed_names = {wheel.name, sdist.name, "SHA256SUMS"}
    unexpected = sorted(path.name for path in args.dist.iterdir() if path.name not in allowed_names)
    if unexpected:
        raise SystemExit("unexpected release artifacts: " + ", ".join(unexpected))

    try:
        wheel_count = verify_wheel(wheel, version=version)
        sdist_count = verify_sdist(sdist, version=version)
    except (KeyError, OSError, tarfile.TarError, ValueError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"release artifact verification failed: {exc}") from exc

    print(f"release artifacts verified: version={version} wheel_files={wheel_count} sdist_files={sdist_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

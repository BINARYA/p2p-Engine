from __future__ import annotations

from pathlib import Path

import pytest


_DIRECT_FILE_MARKERS: dict[str, tuple[str, ...]] = {
    "test_cli.py": ("cli", "integration", "slow"),
    "test_mcp.py": ("mcp", "integration", "slow"),
    "test_foundation_helpers.py": ("unit", "adapter"),
    "test_skeleton.py": ("service", "integration", "smoke"),
}

_ADAPTER_FILES = {
    "test_foundation_helpers.py",
    "test_remote_profile_service.py",
    "test_sync_service.py",
}

_GIT_FILES = {
    "test_mcp_collaboration_handler.py",
    "test_mcp_consent_audit.py",
    "test_proposal_branch_service.py",
    "test_proposal_draft_commit_service.py",
    "test_sync_service.py",
    "test_work_branch_service.py",
}

_SLOW_FILES = {
    "test_cli.py",
    "test_mcp.py",
    "test_proposal_branch_service.py",
    "test_work_branch_service.py",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        for marker_name in _markers_for_item(item):
            item.add_marker(getattr(pytest.mark, marker_name))


def _markers_for_item(item: pytest.Item) -> tuple[str, ...]:
    file_name = Path(item.path).name
    markers: set[str] = set(_DIRECT_FILE_MARKERS.get(file_name, ()))

    if file_name.startswith("test_mcp_"):
        markers.update({"mcp", "integration"})
    if file_name.endswith("_service.py"):
        markers.add("service")
    if file_name in _ADAPTER_FILES:
        markers.add("adapter")
    if file_name in _GIT_FILES:
        markers.update({"git", "integration"})
    if file_name in _SLOW_FILES:
        markers.add("slow")

    test_name = item.name
    if test_name.startswith("test_cli_") or test_name == "test_python_module_entrypoint_exposes_cli_help":
        markers.update({"cli", "integration"})
    if test_name.startswith("test_mcp_"):
        markers.update({"mcp", "integration"})
    if _is_git_contract_test(test_name):
        markers.update({"git", "integration"})

    if not markers:
        markers.add("service")

    return tuple(sorted(markers))


def _is_git_contract_test(test_name: str) -> bool:
    git_terms = (
        "branch",
        "cleanup",
        "finalize",
        "git",
        "merge",
        "publish",
        "remote",
        "request_review",
        "sync",
        "work_accept",
        "work_branch",
        "work_cleanup",
        "work_finalize",
        "work_publish",
        "work_request_review",
        "work_review",
        "work_scan",
        "work_submit",
    )
    return any(term in test_name for term in git_terms)

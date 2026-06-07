# P2PWorkspace Change Set Lifecycle Service Extraction Design

## Summary

Create `ChangeSetLifecycleService` as the owner of `.p2p/changes` runtime
behavior. Keep `P2PWorkspace` as a compatibility facade for CLI/MCP and as the
provider of `_find_change_dir` for existing internal services.

## Target Module

`src/p2p_engine/services/changes.py`

Expected contents:

- `ChangeSetStatus` dataclass.
- `ChangeSetPolicy` dataclass.
- `ChangeSetDetail` dataclass.
- `ChangeSetTaskView` dataclass.
- `CHANGE_STATUS_TRANSITIONS`.
- `ChangeSetLifecycleService` class.
- Local helpers for YAML, optional reads, title cleanup, slugging, string lists,
  metadata-only git policy, and Change Set markdown.

`src/p2p_engine/storage/filesystem.py` should import and re-export the Change
Set dataclasses for compatibility.

## Service Responsibilities

- Allocate sequential `CHANGE-001` IDs.
- Resolve existing Change Set directories by ID.
- Create Change Set artifact sets from accepted proposals.
- List Change Set statuses.
- Read git policy.
- Show Change Set detail.
- Validate and update lifecycle status.
- Read tasks and actions.

## Facade Responsibilities

`P2PWorkspace` should provide:

- a cached `_change_set_lifecycle_service()` factory;
- public delegating methods:
  - `create_change_set`
  - `change_set_statuses`
  - `change_set_policy`
  - `show_change_set`
  - `update_change_set_status`
  - `change_set_tasks`
- private compatibility delegation:
  - `_find_change_dir`

The facade passes `find_proposal_dir` as a dependency.

## Compatibility Notes

- `SoftwareSpecService`, `SpecExportService`, `WorkPlanningService`, and
  `ChoiceLifecycleService` can keep receiving `P2PWorkspace._find_change_dir`
  and `P2PWorkspace.show_change_set`.
- The new service should not import CLI, MCP, or workspace classes.
- The service may duplicate small local helpers to avoid import cycles.

## Verification Plan

Focused tests:

- `tests/test_change_set_lifecycle_service.py`
- `tests/test_cli.py -k change_create_status_and_policy`
- `tests/test_mcp.py -k change`
- affected service tests:
  `test_software_spec_service.py`, `test_spec_export_service.py`,
  `test_work_planning_service.py`, `test_registry_service.py`,
  `test_next_actions_service.py`

Regression tests:

- full `pytest`
- `.venv/bin/p2p validate`

# P2PWorkspace Intake Lifecycle Service Extraction Design

## Summary

Create `IntakeLifecycleService` as the owner of `.p2p/intake` runtime behavior.
Keep `P2PWorkspace` as the compatibility facade that wires registry/context,
contribution, and choice dependencies into the service.

This slice follows the choice lifecycle extraction, allowing intake apply to
call the choice facade instead of carrying choice implementation details.

## Target Module

`src/p2p_engine/services/intake.py`

Expected contents:

- `IntakePrompt` dataclass.
- `IntakeStatus` dataclass.
- `IntakeApplyPlan` dataclass.
- `IntakeAppliedAction` dataclass.
- `IntakeLifecycleService` class.
- Local helpers for YAML, optional reads, meaningful recommendation detection,
  prompt markdown, action metadata, and apply-plan action lookup.

`src/p2p_engine/storage/filesystem.py` should import and re-export the intake
dataclasses for compatibility.

## Service Responsibilities

- Allocate sequential `INTAKE-001` IDs.
- Resolve intake directories.
- Create intake prompt artifacts.
- Import intake output artifacts.
- Report intake status.
- Build controlled apply plans from `suggested-actions.yml`.
- Show existing apply plans.
- Run supported apply actions:
  - `add_contribution`
  - `open_choice`
- Append `applied-actions.yml` audit records.

## Facade Responsibilities

`P2PWorkspace` should provide:

- a cached `_intake_lifecycle_service()` factory;
- public delegating methods:
  - `create_intake_prompt`
  - `import_intake`
  - `intake_statuses`
  - `create_intake_apply_plan`
  - `show_intake_apply_plan`
  - `run_intake_apply_action`

The facade passes these dependencies:

- `registry_status`
- `intake_context`
- `add_contribution`
- `create_choice`

## Compatibility Notes

- `NextActionService` consumes intake through the workspace facade.
- MCP and CLI modules keep using `P2PWorkspace`.
- The service imports `ContributionType` because intake apply persists
  contribution actions using the existing domain enum.

## Verification Plan

Focused tests:

- `tests/test_intake_lifecycle_service.py`
- `tests/test_cli.py -k "intake_prompt_import_and_status or intake_apply_plan_show_and_run"`
- `tests/test_mcp.py -k intake`
- `tests/test_next_actions_service.py -k intake` if present

Regression tests:

- full `pytest`
- `.venv/bin/p2p validate`

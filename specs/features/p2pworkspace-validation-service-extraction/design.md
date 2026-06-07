# P2PWorkspace Validation Service Extraction Design

## Current Runtime Shape

`P2PWorkspace.validate()` currently owns validation orchestration directly in
`src/p2p_engine/storage/filesystem.py`. It builds findings, checks workspace
paths and YAML files, validates several governance payloads, inspects proposal
directories, checks duplicate proposal IDs, and asks `registry_status()` whether
registries are stale.

The method is consumed by:

- CLI project status commands, especially `p2p validate`;
- MCP project validation handlers;
- project assessment computation;
- tests that import validation result dataclasses from the storage facade.

## Target Shape

Add `src/p2p_engine/services/validation.py` with:

- `ValidationFinding`;
- `ValidationResult`;
- `ValidationService`;
- validation-local payload helper functions for readiness profiles,
  readiness assessments, and agent integrations.

`P2PWorkspace` keeps a lazy validation service factory and delegates
`validate()` to that service. The facade re-exports the dataclasses by importing
them from the service.

## Service Dependencies

The service receives only stable filesystem paths and callbacks:

- `root`;
- `p2p_dir`;
- `duplicate_proposal_ids`;
- `registry_status`;
- `agent_integrations_path`;
- `permissions_path`.

The service may import shared constants from extracted services:

- `PERMISSION_ROLES` and `ACTOR_KINDS` from `services.permissions`;
- `CONSENT_OPERATIONS` from `services.consent`.

The service may import foundation markdown helpers for section checks.

## Compatibility Rules

- Keep finding order aligned with the existing method.
- Keep path values relative to project root.
- Keep warning/error counts derived from finding severities.
- Keep `P2PWorkspace.validate()` as the single public workspace entry point.
- Do not move CLI or MCP presentation logic.

## Verification Map

```bash
.venv/bin/pytest tests/test_validation_service.py
.venv/bin/pytest tests/test_skeleton.py -k validate
.venv/bin/pytest tests/test_cli.py -k validate
.venv/bin/pytest tests/test_mcp.py -k validate
.venv/bin/pytest tests/test_mcp_project_handler.py tests/test_project_assessment_service.py -k validation
.venv/bin/p2p validate
.venv/bin/pytest
```

## Implementation Evidence

Implemented in:

- `src/p2p_engine/services/validation.py`;
- `src/p2p_engine/storage/filesystem.py` facade wiring;
- `tests/test_validation_service.py`;
- `specs/features/p2pworkspace-validation-service-extraction/tasks.md`.

Verification:

```bash
.venv/bin/pytest tests/test_validation_service.py
# 4 passed

.venv/bin/pytest tests/test_skeleton.py -k validate
# 2 passed, 11 deselected

.venv/bin/pytest tests/test_cli.py -k validate
# 5 passed, 88 deselected

.venv/bin/pytest tests/test_mcp.py -k validate
# 2 passed, 42 deselected

.venv/bin/pytest tests/test_mcp_project_handler.py tests/test_project_assessment_service.py -k validation
# 1 passed, 7 deselected

.venv/bin/p2p validate
# errors: 0, warnings: 0, infos: 0, findings: none

.venv/bin/pytest
# 322 passed
```

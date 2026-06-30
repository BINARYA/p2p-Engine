# Implementation Note - Agent Integration Registry Production Hardening

## Summary

Implemented production hardening for the existing Agent Integration Registry
MVP. The work keeps the current adapter set and public lifecycle commands while
making registry state, file writes, default init behavior, health reporting,
doctor diagnostics, path handling, and force behavior safer.

## Implemented

- Refreshed the existing MVP feature evidence to current service, CLI, MCP, and
  test modules.
- Aligned MCP project initialization default agent behavior with CLI default
  behavior: omitted agent now means all built-in adapters.
- Added explicit service, CLI, and MCP tests for mandatory `generic` baseline
  behavior and uninstall refusal.
- Added conservative refresh behavior for drifted and unmanaged generated files.
- Added atomic write helpers for text/YAML writes used by agent registry,
  policy, and generated instruction files.
- Added file `status` and adapter `health` service fields while preserving the
  compatibility `drift` field.
- Added semantic validation for `.p2p/agent-integrations.yml`, including
  generic baseline, known adapters, forbidden active/default/current agent
  state, required metadata, safe paths, duplicate ownership, valid status/hash
  format, missing managed files, and hash mismatch detection.
- Documented and tested shared-file ownership and OpenCode shared-only behavior.
- Added service-backed agent doctor findings, CLI `agent doctor` rendering and
  exit behavior, and read-only MCP `p2p_agent_doctor`.
- Scoped force behavior to the named install/update target so it does not
  overwrite drifted files owned only by another adapter.
- Added service lifecycle path safety guards for absolute paths and `..`
  escapes.
- Updated `docs/AGENT-INTEGRATION.md`, `docs/MCP.md`, and `docs/CLI-GUIDE.md`.

## Verification

Final verification command:

```bash
.venv/bin/python -m pytest
```

Result:

```text
452 passed in 74.50s
```

Focused suites run during implementation included:

- `tests/test_agent_instructions_service.py`
- `tests/test_validation_service.py`
- selected CLI agent lifecycle and doctor tests from `tests/test_cli.py`
- selected MCP agent lifecycle, registry, and doctor tests from `tests/test_mcp.py`
- `tests/test_mcp_registry.py`
- `tests/test_foundation_helpers.py`

## Compatibility Notes

- Existing CLI/MCP lifecycle commands remain in place.
- Existing persisted registry schema version remains `1`.
- Existing `drift` fields remain available for compatibility.
- New service/CLI/MCP outputs add health/status/doctor data rather than
  removing existing fields.
- MCP gains a new read-only tool: `p2p_agent_doctor`.

## Deferred

- Moving inline templates to package data.
- Dedicated template staleness calculation against template versions.
- Agent lifecycle dry-run mode.
- JSON output for agent CLI lifecycle/doctor commands.

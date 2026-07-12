# PROP-093D Bootstrap Agent Lifecycle Tasks

## Status

`implemented`

## Implementation Rules

- Do not rewrite the agent integration registry.
- Preserve existing lifecycle command names and safe behavior.
- Keep default-selection logic testable without relying on the real shell or IDE.
- Keep init deterministic and non-interview-based.
- Additive MCP fields are allowed; breaking schema changes are not.
- Do not persist detected current-agent metadata as project identity.
- Do not remove or weaken `PROP-093C` generated persistence policy blocks.

## Tasks

- [x] D1. Review existing init, agent lifecycle, and MCP init tests to identify
      assumptions about default `all` or exact init output.

- [x] D1a. Review all `init_project()` callers and record compatibility
      expectations before changing any init return type or facade behavior.

- [x] D2. Add service tests for explicit single-adapter selection preserving
      generic baseline.

- [x] D3. Add service tests for explicit multi-adapter selection preserving
      generic baseline.

- [x] D4. Add service tests for explicit `all` selection preserving current
      broad adapter support.

- [x] D5. Add service tests for reliable detected-agent default producing
      `generic` plus detected adapter.

- [x] D6. Add service tests for unknown detection fallback to `all` with a
      warning.

- [x] D6a. Add service tests proving detected-agent metadata is reported as
      selection metadata only and is not persisted as project identity or
      registry authority.

- [x] D7. Implement a small agent default-selection helper with injectable
      detection inputs and existing adapter normalization.

- [x] D8. Wire project initialization through the selection helper without
      breaking the existing `init_project()` compatibility facade.

- [x] D8a. Add or preserve an additive init summary/result path for selection
      metadata while keeping existing created-path callers compatible.

- [x] D9. Add CLI guided-init tests for adaptive default prompt behavior.

- [x] D10. Add CLI guided-init tests proving explicit `all` remains available
       and emits footprint warning.

- [x] D11. Update guided init prompt ordering/defaults and warning text.

- [x] D12. Add CLI tests for grouped init summary agent integration section.

- [x] D13. Update init summary to list installed adapters and lifecycle
       commands for list/install/update/doctor/uninstall/refresh.

- [x] D13a. Verify lifecycle command names in init summary and generated
       guidance against the implemented CLI command surface.

- [x] D14. Add MCP init tests proving default selection matches CLI selection
       policy.

- [x] D15. Update MCP init handler/payload with additive selection metadata or
       warning fields where useful.

- [x] D15a. Update MCP `p2p_init_project` catalog description/schema text so it
       describes adaptive defaults and no longer claims blind default `all`
       behavior.

- [x] D16. Add generated instruction tests proving post-init lifecycle commands
       are visible to agents.

- [x] D16a. Add generated instruction tests proving lifecycle guidance coexists
       with `PROP-093C` persistence policy blocks.

- [x] D17. Update generated agent instructions with concise lifecycle guidance.

- [x] D17a. Add lifecycle guidance through shared or adjacent template blocks
       without duplicating or replacing the existing persistence policy block.

- [x] D18. Update `docs/INSTALL.md`, `docs/AGENT-INTEGRATION.md`, and any CLI
       guide sections that describe init agent selection or lifecycle commands.

- [x] D18a. Update docs to explain that detected current-agent information is a
       bootstrap hint, not permanent project identity.

- [x] D18b. Update docs to explain that existing broad adapter installations
       are not automatically narrowed by refresh, update, or upgrade.

- [x] D19. Run focused validation for agent selection, project initialization,
       and agent instruction service tests.

- [x] D20. Run public-contract validation for CLI init and MCP init/lifecycle
       tests.

- [x] D20a. Run compatibility validation proving existing `all` installations
       are preserved unless the owner invokes safe uninstall.

- [x] D20b. Run MCP catalog/schema validation proving adaptive init wording is
       exposed to MCP clients.

- [x] D21. Record validation evidence and compatibility notes in the
       implementation summary.

## Implementation Summary

- Added a dedicated agent selection service with explicit, detected, and fallback
  outcomes. Detection currently uses project-specific environment signals only
  and remains runtime metadata.
- Added `init_project_with_summary()` for CLI/MCP selection metadata while
  preserving `init_project()` as a created-path compatibility facade.
- Updated CLI and MCP init to share adaptive selection behavior and expose
  installed adapters, warnings, and lifecycle commands.
- Updated generated agent guidance to include lifecycle commands beside the
  existing persistent-write policy blocks.
- Updated docs to describe adaptive bootstrap, fallback `all`, non-persisted
  detection, and lifecycle management.

## Validation Evidence

- `tests/test_agent_selection_service.py`
- `tests/test_project_initialization_service.py`
- `tests/test_agent_instructions_service.py`
- `tests/test_cli.py -k "init or agent"`
- `tests/test_mcp.py -k "init or agent"`
- `tests/test_mcp_registry.py tests/test_mcp_maintenance_handler.py`
- `git diff --check`
- `.venv/bin/python -m pytest -q` -> 542 passed

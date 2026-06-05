# P2PWorkspace Refactoring Inventory And Extraction Map Design

## Overview

This feature produces a technical map, not runtime refactoring. It is the
analysis layer between the accepted architecture contract and future code
changes.

The current source shape is strongly concentrated:

- `src/p2p_engine/storage/filesystem.py`: about 9,971 lines.
- `src/p2p_engine/cli.py`: about 3,147 lines.
- `src/p2p_engine/mcp/tools.py`: about 2,105 lines.
- `src/p2p_engine/storage/git.py`: about 184 lines.
- `tests/test_cli.py`: about 3,969 lines.
- `tests/test_mcp.py`: about 1,622 lines.

The inventory must make this structure explicit and turn it into a staged
extraction plan.

## Covered Requirements

- R001: Runtime Surface Inventory
- R002: P2PWorkspace Method Map
- R003: Target Module Boundaries
- R004: Compatibility Test Map
- R005: Extraction Order
- R006: Facade Contract
- R007: Implementation Task Derivation

## Proposed Inventory Format

Create a maintained inventory document, preferably:

```text
specs/features/p2pworkspace-refactoring-inventory-and-extraction-map/inventory.md
```

The document should contain:

- current file responsibility matrix;
- `P2PWorkspace` method groups;
- proposed target services/modules;
- compatibility-sensitive surfaces;
- tests covering each group;
- missing tests;
- extraction order;
- follow-up feature/task seeds.

## Responsibility Groups

Initial groups to map:

- project initialization and domain/rubrics setup;
- agent integration and generated instructions;
- permissions and consent receipts;
- remote profile, sync, and Git helpers;
- proposal lifecycle and proposal branches;
- proposal readiness and readiness profiles;
- prompts and prompt import workflows;
- governance, votes, decisions, and precedents;
- project refresh, assessment, maturity, and brief;
- specs/export and project definition output;
- Change Sets and Work lifecycle;
- registries;
- intake and controlled apply;
- choices, blockers, conflicts, impact, and next actions;
- validation and YAML/Markdown parsing helpers.

## Target Module Candidates

The map should evaluate target modules such as:

- `p2p_engine.services.permissions`
- `p2p_engine.services.consent`
- `p2p_engine.services.proposals`
- `p2p_engine.services.readiness`
- `p2p_engine.services.project_state`
- `p2p_engine.services.spec_exports`
- `p2p_engine.services.work`
- `p2p_engine.services.registries`
- `p2p_engine.services.intake`
- `p2p_engine.services.choices`
- `p2p_engine.adapters.filesystem`
- `p2p_engine.adapters.git`
- `p2p_engine.mcp.registry`
- `p2p_engine.cli_commands.*`

Final module names are not decided by this feature; the map should recommend
names and boundaries.

## Compatibility Strategy

`P2PWorkspace` remains the public compatibility facade. During extraction:

- CLI should continue calling `P2PWorkspace` unless a later feature explicitly
  changes the command layer.
- MCP should continue using stable tool names and payloads.
- Services should initially be internal and delegate-compatible.
- Storage paths and YAML/Markdown formats must remain unchanged.
- Git/sync and consent side effects must preserve current audit behavior.

## Test Mapping Strategy

For each responsibility group, map:

- current tests in `tests/test_cli.py`;
- current tests in `tests/test_mcp.py`;
- missing focused tests;
- fixtures or helper extraction that would make future tests easier.

The first future extraction, permissions/consent, should map at minimum:

- CLI tests around permission actors and consent receipts;
- CLI validation tests for permissions policy;
- MCP tests for permission/consent read tools;
- MCP permission-gated tool tests that consume consent;
- Git/audit behavior where consent consumption creates commits or pushes.

## Output Of This Feature

This feature is complete when the inventory map can answer:

- which source area is being extracted;
- which service owns it afterward;
- what stays in `P2PWorkspace`;
- which tests prove behavior is unchanged;
- which missing tests must be added before extraction;
- what follow-up feature should be created for implementation.

No `src/` behavior changes are part of this feature.

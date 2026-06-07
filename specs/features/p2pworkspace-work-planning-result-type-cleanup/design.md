# P2PWorkspace Work Planning Result Type Cleanup Design

## Current State

`WorkPlanningService` defines and returns `WorkStatus`, `WorkDetail`, and
`WorkSummary`. `storage.filesystem` still defines duplicate dataclasses with the
same fields and uses them only for type annotations.

This creates misleading ownership: the facade appears to own Work planning
result models even though the service constructs them.

## Target State

- Import `WorkStatus`, `WorkDetail`, and `WorkSummary` from
  `p2p_engine.services.work_planning`.
- Remove duplicate dataclasses from `storage.filesystem`.
- Keep facade methods as delegating compatibility methods.

## Verification

The change is type/model cleanup. Verification focuses on Work planning,
context/MCP consumers, CLI Work commands, `p2p validate`, and the full test
suite.

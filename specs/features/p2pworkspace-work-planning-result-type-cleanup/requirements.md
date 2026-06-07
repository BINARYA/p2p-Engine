# P2PWorkspace Work Planning Result Type Cleanup Requirements

## Goal

Remove duplicated Work planning result dataclasses from `P2PWorkspace` and use
the result types owned by `WorkPlanningService`.

## Requirements

- `WorkStatus`, `WorkDetail`, and `WorkSummary` must be imported from
  `services.work_planning`.
- `P2PWorkspace` public method names and return shapes must remain unchanged.
- CLI, MCP, context packet, and Work planning tests must continue to observe the
  same attributes.
- No Work manifest or `.p2p/` output behavior may change.

## Non-Goals

- Do not change Work branch lifecycle result types.
- Do not change Work status, summary, show, or retirement behavior.
- Do not remove compatibility facade methods in this step.

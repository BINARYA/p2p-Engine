# P2PWorkspace Work Retire Service Ownership Design

## Current State

`WorkPlanningService` owns Work plan creation, status listing, summary creation,
detail lookup, id allocation, and Work directory lookup. `P2PWorkspace` still
implements `retire_work()` directly by reading and rewriting the Work manifest.

This leaves Work planning metadata lifecycle split across the service and the
facade.

## Target State

- Add `WorkRetire` to `services.work_planning`.
- Add `WorkPlanningService.retire()`.
- Change `P2PWorkspace.retire_work()` to delegate to
  `self._work_planning_service().retire(work_id, reason)`.
- Import/re-export the `WorkRetire` result type through `storage.filesystem`
  compatibility imports as needed.

## Compatibility

The CLI command continues calling `workspace.retire_work()`. The manifest output
and `work status` summary output remain unchanged.

## Verification Strategy

- Unit-test retirement directly on `WorkPlanningService`.
- Keep facade coverage through existing CLI Work retirement regression.
- Run `p2p validate` and the full pytest suite.

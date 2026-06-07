# P2PWorkspace Work Retire Service Ownership Requirements

## Goal

Move planned Work retirement behavior out of `P2PWorkspace` and into
`WorkPlanningService`, which already owns Work planning metadata, status, show,
and summary behavior.

## Requirements

- `WorkPlanningService` must own the `WorkRetire` result type.
- `WorkPlanningService.retire(work_id, reason)` must preserve current behavior:
  - trim and require a non-empty reason;
  - require the Work item status to be `planned`;
  - update `manifest.yml` status to `retired`;
  - write `retirement.reason`, `retirement.retired_at`, and
    `retirement.mode: metadata_only`;
  - return work id, status, reason, and relative Work path.
- `P2PWorkspace.retire_work()` must remain as the public compatibility facade.
- CLI output and existing Work status/summary behavior must remain unchanged.
- No `.p2p/` governance state may be edited by hand.

## Non-Goals

- Do not change Work branch lifecycle behavior.
- Do not allow retirement of branched/submitted/reviewed Work items.
- Do not change managed Git semantics.
- Do not change Work manifest schema beyond preserving existing retirement
  fields.

---
change_id: CHANGE-010
title: Choice Blocking and Discovery MVP
status: completed
created_at: '2026-05-25'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-024
  accepted_decisions: []
implementation_targets:
- local_cli
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-010 - Choice Blocking and Discovery MVP

## Summary

Implement choice blocking and discovery in two steps. First add deterministic advisory inspection commands that surface project choices, proposal-local choice candidates, and unresolved discovery findings. Then add formal block/unblock commands that write links.yml for project choices, distinguishing related metadata from active blockers.

## Rationale

The project now has p2p next and operational brief artifacts. The next intelligence step is to distinguish related choices, discovered candidate blockers, and formal blocks without letting the CLI decide on behalf of the owner.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Advisory choice inspection commands: `show`, `status`, `discover`.
- Explicit choice blocker commands: `block`, `unblock`.
- `links.yml` blocker records for project choices.
- `p2p next` prioritization for active unresolved choice blockers.
- Updated P2P skill guidance.

## Acceptance Criteria

- `p2p choice show CHOICE-XXX` shows project choice details and active blockers.
- `p2p choice status` lists project choices and proposal-local candidates.
- `p2p choice discover` reports advisory findings without modifying state.
- `p2p choice block/unblock` records and clears explicit blockers in `links.yml`.
- `p2p next` prioritizes active unresolved choice blockers before generic Change Set continuation.
- Tests cover discovery, blocking, unblocking, and next-action integration.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.

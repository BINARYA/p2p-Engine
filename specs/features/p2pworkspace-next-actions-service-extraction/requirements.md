# P2PWorkspace Next Actions Service Extraction Requirements

## Purpose

Extract the next-action lifecycle and generated-action logic from
`P2PWorkspace` into a cohesive service while preserving the existing CLI, MCP,
context, project-status, and assessment behavior.

This is local software-development planning. It is not P2P governance state and
does not change the P2P project workflow.

## Current Behavior To Preserve

- `p2p next` and `p2p next list` show active curated actions, active choice
  blocker actions, and generated fallback actions.
- `p2p next add` writes curated actions to
  `.p2p/project/next-actions.yml`.
- `p2p next complete` and `p2p next retire` remove the curated action from the
  active file and append an audit entry to
  `.p2p/project/next-actions-log.yml`.
- `p2p next refresh` normalizes curated action records and reports the number
  of generated actions available after refresh.
- MCP tools `p2p_next`, `p2p_next_add`, `p2p_next_complete`,
  `p2p_next_retire`, and `p2p_next_refresh` continue to return the same JSON
  shapes.
- `project status`, `project assess`, and `context` continue to consume next
  actions through the existing `P2PWorkspace` facade.

## Functional Requirements

1. The service MUST own next-action file paths, reads, writes, normalization,
   curated ID allocation, lifecycle closure, audit-log append behavior,
   deduplication, and generated fallback construction.
2. The service MUST preserve the current priority order:
   active choice blockers, active curated actions, generated fallback actions.
3. The service MUST preserve deduplication by `(kind, target)`, keeping the
   first action in priority order.
4. The service MUST keep `limit` semantics unchanged: `None` returns all
   actions and any integer returns at most `max(limit, 0)` actions.
5. The service MUST raise `ValueError` with compatible messages for invalid
   curated action payloads, duplicate IDs, missing close IDs, and missing close
   reasons.
6. Generated fallback actions MUST keep current command text and source values.
7. Generated fallback actions MUST remain advisory. This extraction MUST NOT
   execute commands, make governance decisions, or mutate proposal/choice/change
   state.
8. The service MUST avoid direct CLI and MCP imports.
9. `P2PWorkspace` MUST remain the compatibility facade for public callers.

## Compatibility Requirements

- Public method names on `P2PWorkspace` remain:
  `next_actions`, `next_action_add`, `next_action_complete`,
  `next_action_retire`, and `next_actions_refresh`.
- Existing imports of `NextAction` from `p2p_engine.storage.filesystem` remain
  valid.
- No `.p2p/` storage layout change is allowed.
- No CLI option, command name, output label, MCP tool name, or MCP response key
  changes are allowed.

## Non-Goals

- Do not redesign the next-action model.
- Do not introduce a new task engine or scheduler.
- Do not change proposal readiness, choice, intake, registry, or change-set
  semantics.
- Do not move initialization, agent-instruction generation, rubrics, or
  maturity assessment in this slice.

## Acceptance Criteria

- `src/p2p_engine/services/next_actions.py` contains the extracted service and
  next-action model or model alias.
- `src/p2p_engine/storage/filesystem.py` delegates next-action public behavior
  to the service and no longer contains the large private next-action helper
  block.
- Existing CLI and MCP next-action tests pass unchanged.
- New service-level tests cover curated lifecycle, fallback generation,
  deduplication, choice blockers, and invalid payload handling.
- The refactoring status tracker identifies this slice as the active next step
  and records completion when code and tests are done.

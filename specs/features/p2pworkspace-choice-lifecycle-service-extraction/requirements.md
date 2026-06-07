# P2PWorkspace Choice Lifecycle Service Extraction Requirements

## Purpose

Extract project choice lifecycle behavior from `P2PWorkspace` into a cohesive
service while preserving existing CLI, MCP, next-action, context, registry, and
project-assessment behavior.

This is local software-development planning. It is not P2P governance state.

## Current Behavior To Preserve

- `p2p choice create` creates a project choice with markdown, options,
  decision, and link artifacts under `.p2p/choices/CHOICE-XXX-<slug>/`.
- `p2p choice list` and `p2p choice status` list project choices and selected
  options.
- `p2p choice show` reads choice details, options, related proposals/changes,
  and blockers.
- `p2p choice discover` reports advisory findings for proposal-local choice
  candidates, active blockers, and open project choices.
- `p2p choice block` and `p2p choice unblock` mutate active blocker metadata in
  `links.yml`.
- `p2p choice decide` marks one option as selected, writes `decision.md`, and
  updates choice frontmatter status to `decided`.
- MCP `p2p_choice_list`, `p2p_choice_show`, and `p2p_choice_discover` keep the
  same JSON response shapes.
- Next actions continue to discover active choice blockers through
  `P2PWorkspace.choice_statuses()` and `P2PWorkspace.show_choice()`.

## Functional Requirements

1. The service MUST own choice directory path resolution, ID allocation, create,
   list, show, discover, block, unblock, and decide behavior.
2. The service MUST keep the `.p2p/choices` file layout unchanged.
3. The service MUST preserve existing validation messages for missing options,
   invalid target type, invalid `links.yml`, invalid `options.yml`, missing
   active blockers, and missing choice options.
4. The service MUST preserve date behavior for `created_at`, `recorded_on`,
   `cleared_on`, and decision date.
5. The service MUST preserve current advisory semantics: discovery does not
   mutate state and choices are not auto-decided.
6. The service MUST avoid direct CLI and MCP imports.
7. `P2PWorkspace` MUST remain the compatibility facade for public callers.

## Compatibility Requirements

- Public method names on `P2PWorkspace` remain:
  `create_choice`, `choice_statuses`, `show_choice`, `discover_choices`,
  `block_choice`, `unblock_choice`, and `decide_choice`.
- Existing imports of `ChoiceStatus`, `ChoiceDetail`, and
  `ChoiceDiscoveryFinding` from `p2p_engine.storage.filesystem` remain valid.
- No CLI command, CLI output, MCP tool name, or MCP response key changes are
  allowed.
- Existing next-action behavior for active choice blockers remains unchanged.

## Non-Goals

- Do not extract intake apply in this slice.
- Do not extract Change Set lifecycle in this slice.
- Do not change proposal-local vote metadata or registry generation.
- Do not add automatic choice decisions.

## Acceptance Criteria

- `src/p2p_engine/services/choices.py` contains the extracted service and
  choice models.
- `src/p2p_engine/storage/filesystem.py` delegates choice public behavior to
  the service and no longer contains inline choice lifecycle implementation.
- Existing CLI, MCP, and next-action tests for choices pass unchanged.
- New service-level tests cover create/list/show, discover, block/unblock,
  decide, and invalid payload/error paths.

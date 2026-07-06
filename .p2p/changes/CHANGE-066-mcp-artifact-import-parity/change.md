---
change_id: CHANGE-066
title: MCP Artifact Import Parity
status: completed
created_at: '2026-07-06'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-088
  accepted_decisions: []
implementation_targets:
- local_cli
spec_targets:
- p2p_spec
export_targets:
- openspec
- speckit
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-066 - MCP Artifact Import Parity

## Summary

Add explicit write-safe MCP tools that call existing P2P Engine import services for proposal artifact content. The MVP scope covers total MCP parity with the existing controlled CLI import primitives that have fixed targets and validation: exploration imports, impact imports, clarification imports, synthesis/proposal imports, plan imports, and tasks imports. Generic arbitrary artifact import/update remains deferred until a stricter allowlist, validation model, and audit boundary are designed. MCP import tools should support both source paths and direct content payloads: source paths preserve parity with current CLI services and directory-based imports, while direct payloads support real MCP client workflows where generated content is already available in the tool call. All tools must use explicit artifact kinds, preserve existing validation behavior, return structured metadata about imported files, and keep unsupported artifact-content mutations as explicit missing-primitive errors. Documentation should describe the new MCP surface, supported artifact kinds, unsupported cases, path-vs-payload behavior, validation/audit boundaries, and the relationship between artifact content imports and artifact coverage state.

## Rationale

PROP-086 made artifact-aware readiness depend on public CLI or explicit MCP write tools, with no direct .p2p writes or temporary-file copying into managed proposal folders. Today MCP exposes p2p_impact_prompt and artifact state tools, but not MCP equivalents for p2p impact import, p2p explore import, or clarify/import-style content ingestion. This prevents an agent-first workflow from closing artifact gaps after it identifies them.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Change Set metadata.

## Acceptance Criteria

- Change Set metadata is present and reviewable.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.

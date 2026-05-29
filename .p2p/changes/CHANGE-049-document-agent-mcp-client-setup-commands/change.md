---
change_id: CHANGE-049
title: Document Agent MCP Client Setup Commands
status: completed
created_at: '2026-05-29'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-068
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

# CHANGE-049 - Document Agent MCP Client Setup Commands

## Summary

Update docs/INSTALL.md with an agent MCP setup section covering the common stdio command, Codex CLI, Claude Code, Claude Desktop JSON, and generic MCP clients. Keep README as a pointer to the install/MCP docs.

## Rationale

README should stay concise and avoid contributor-specific examples. INSTALL is the right place for new-project MCP client setup. CONTRIBUTING remains the only place for configuring an agent against the P2P Engine repository itself.

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

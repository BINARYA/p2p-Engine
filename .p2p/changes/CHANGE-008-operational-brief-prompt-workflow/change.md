---
change_id: CHANGE-008
title: Operational Brief Prompt Workflow
status: completed
created_at: '2026-05-25'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-022
  accepted_decisions: []
implementation_targets:
- local_cli
plan_ref: execution-plan.md
tasks_ref: tasks.yml
---

# CHANGE-008 - Operational Brief Prompt Workflow

## Summary

Add a prompt-only operational brief workflow under project commands: the CLI gathers project state, registries, conflicts, choices, intake and changes into a context file, generates instructions for an AI/human synthesis, and imports the resulting operational brief and optional next-actions YAML.

## Rationale

The project uses prompt-only workflows for exploration, impact, and intake. The same pattern should introduce intelligence without making the CLI decide on behalf of the owner.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Project brief prompt generation command.
- Project brief import and show commands.
- Stored operational brief artifacts under `.p2p/project/`.
- Updated P2P agent skill guidance.

## Acceptance Criteria

- `p2p project brief prompt` creates a context file and prompt file.
- `p2p project brief import` stores `operational-brief.md` and optional `next-actions.yml`.
- `p2p project brief show` prints the stored operational brief.
- Tests cover the prompt/import/show workflow.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.

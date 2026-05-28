---
change_id: CHANGE-043
title: README and Install Documentation MVP
status: completed
created_at: '2026-05-28'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-058
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

# CHANGE-043 - README and Install Documentation MVP

## Summary

Create a concise README and docs/INSTALL.md. README should explain what P2P Engine is, core principles, five-layer architecture, current implementation status, quick start commands, token-aware context, project definition maturity, MCP overview, and roadmap. docs/INSTALL.md should provide source install steps with Python venv, editable install, verification commands, project initialization, MCP local setup for Codex/compatible clients, troubleshooting, and current limitations.

## Rationale

The current installation path is source-based Python with a virtual environment. Future packaging may move toward a compiled/installable CLI, but the immediate user need is clear documentation for cloning, installing, initializing a project, using compact context, running assessment, and configuring MCP locally.

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

---
change_id: CHANGE-038
title: Core Validation Layer MVP
status: completed
created_at: '2026-05-28'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-053
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

# CHANGE-038 - Core Validation Layer MVP

## Summary

Implement p2p validate with stable findings. The MVP validates required project structure, YAML readability for known structured files, proposal directory naming, required proposal sections, decision status presence, proposal/decision status consistency, and registry freshness. Findings have severity error/warning/info, stable codes, paths, messages, and optional suggested commands. Add --format text/json and exit code 1 when errors exist. Add p2p_validate MCP as read-only/advisory. Keep p2p check as minimal bootstrap validation.

## Rationale

The current p2p check command only verifies minimal bootstrap files. Before packaging and before owner-gated MCP mutations, the core should expose a semantic validation pass with stable finding codes, severities, JSON output, and MCP access.

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

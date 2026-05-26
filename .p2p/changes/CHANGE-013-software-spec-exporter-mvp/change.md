---
change_id: CHANGE-013
title: Software Spec Exporter MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-027
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

# CHANGE-013 - Software Spec Exporter MVP

## Summary

Add p2p spec export/status/show support for software spec export bundles. The MVP should export from .p2p/outputs/software-spec/CHANGE-XXX/ into .p2p/outputs/spec-export/CHANGE-XXX/TARGET/, starting with generic and openspec targets. Spec Kit remains a downstream target but is not implemented in this MVP unless the mapping becomes explicit.

## Rationale

CHANGE-012 introduced the P2P-native software spec layer. The next step is to export from that normalized layer instead of reading raw proposal folders.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- `p2p spec export --change CHANGE-XXX --target generic`
- `p2p spec export --change CHANGE-XXX --target openspec`
- `p2p spec export-status`
- `p2p spec export-show CHANGE-XXX --target TARGET`
- Generic export bundle under `.p2p/outputs/spec-export/CHANGE-XXX/generic/`
- OpenSpec-oriented export bundle under `.p2p/outputs/spec-export/CHANGE-XXX/openspec/`
- P2P skill guidance for exporting from the P2P-native software spec layer.
- Tests for successful export, export inspection, and unsupported target rejection.

## Acceptance Criteria

- `p2p spec export --change CHANGE-XXX --target generic` writes a generic export bundle from an existing P2P software spec.
- `p2p spec export --change CHANGE-XXX --target openspec` writes an OpenSpec-oriented bundle from an existing P2P software spec.
- `p2p spec export-status` lists generated export bundles.
- `p2p spec export-show CHANGE-XXX --target TARGET` prints the export index.
- Unsupported export targets fail explicitly instead of silently generating an undefined format.
- Tests cover successful generic/OpenSpec export, export status/show, and unsupported targets.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.

---
change_id: CHANGE-015
title: Spec Export Validation MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-029
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

# CHANGE-015 - Spec Export Validation MVP

## Summary

Add p2p spec export-validate CHANGE-XXX --target TARGET. The command validates that the export directory exists, manifest.yml is valid and coherent, index.md exists, and target-specific required files are present for generic, openspec, and speckit bundles.

## Rationale

CHANGE-013 and CHANGE-014 added software spec export targets. Downstream handoff should not rely only on generation success; agents need a read-only validation command.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- `p2p spec export-validate CHANGE-XXX --target TARGET`
- Read-only validation for generic export bundles.
- Read-only validation for OpenSpec-oriented export bundles.
- Read-only validation for Spec Kit-oriented export bundles.
- Manifest coherence checks for `source.change` and `target`.
- Tests for valid bundles, missing files, and manifest mismatch failures.
- P2P skill guidance for validating export bundles before downstream use.

## Acceptance Criteria

- `p2p spec export-validate CHANGE-XXX --target generic` validates generic bundle structure.
- `p2p spec export-validate CHANGE-XXX --target openspec` validates OpenSpec-oriented bundle structure.
- `p2p spec export-validate CHANGE-XXX --target speckit` validates Spec Kit-oriented bundle structure.
- Missing required export artifacts fail explicitly.
- Manifest mismatch failures are reported explicitly.
- Validation is read-only and does not regenerate or mutate export bundles.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.

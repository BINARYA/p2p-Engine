---
change_id: CHANGE-012
title: P2P Software Spec Generator MVP
status: completed
created_at: '2026-05-26'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-026
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

# CHANGE-012 - P2P Software Spec Generator MVP

## Summary

Add p2p spec refresh/status/show/prompt/import. The refresh command deterministically generates a minimal software spec from a Change Set. The prompt command generates an AI/human refinement prompt from the deterministic spec and source context. The import command validates and imports refined spec artifacts.

## Rationale

CHANGE-001 established Change Set as the operational unit and separated execution_domains, implementation_targets, spec_targets and export_targets. PROP-010 already selected a P2P-native software spec before downstream export.

## Scope

### Included

- Derived from accepted proposal scope.

### Excluded

- Automatic Git commits, branches, tags, or merges.

## Deliverables

- Top-level `p2p spec` command group.
- Deterministic software spec generation from Change Sets.
- Software spec status and show commands.
- Optional prompt/import refinement workflow.
- Required artifact validation for imported specs.
- P2P skill guidance and tests.

## Acceptance Criteria

- `p2p spec refresh --change CHANGE-XXX` generates required artifacts under `.p2p/outputs/software-spec/CHANGE-XXX/`.
- `p2p spec status` lists generated specs.
- `p2p spec show CHANGE-XXX` prints `index.md`.
- `p2p spec prompt --change CHANGE-XXX` writes a refinement prompt.
- `p2p spec import CHANGE-XXX output-dir/` validates required files and YAML keys.
- Tests cover deterministic generation, prompt creation, status/show, and import.

## Dependencies

- None recorded.

## Risks

- Metadata may need manual refinement before implementation.

## Related Choices

- None recorded.

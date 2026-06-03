---
change_id: CHANGE-059
title: Project-Local Wheel Installation and Upgrade Model
status: completed
created_at: '2026-06-03'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-078
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

# CHANGE-059 - Project-Local Wheel Installation and Upgrade Model

## Summary

Introduce a packaging and installation model based on versioned wheel artifacts attached to GitHub Releases as the first distribution channel. Project setup documentation should install P2P Engine into the project-local .venv from a release wheel URL, and project upgrade documentation should use python -m pip install --upgrade <wheel-url>, followed by p2p doctor, p2p agent doctor, p2p registry refresh, p2p agent instructions refresh, and p2p validate. This is a transitional distribution model: the long-term target remains a public package such as PyPI, where installation becomes python -m pip install p2p-engine and upgrade becomes python -m pip install --upgrade p2p-engine. The proposal should avoid requiring users to reference external source checkout paths during normal project use.

## Rationale

Not provided.

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

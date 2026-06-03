---
change_id: CHANGE-061
title: Automated GitHub Release Wheel Publishing
status: completed
created_at: '2026-06-03'
created_by: local
execution_domains:
- software
source:
  accepted_proposals:
  - PROP-080
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

# CHANGE-061 - Automated GitHub Release Wheel Publishing

## Summary

Add a GitHub Actions release workflow triggered by version tags matching v*. The workflow should check out the repository, set up Python, install development dependencies, run the test suite, run p2p validate, build the source distribution and wheel with python -m build, verify expected dist artifacts exist, and upload the .whl and .tar.gz as assets to the matching GitHub Release. Document the new release flow: update pyproject.toml version, commit and push main, create and push an annotated tag such as v0.1.1, then GitHub Actions publishes the release assets. Keep manual release notes as a fallback, but make the tag-triggered workflow the normal path.

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

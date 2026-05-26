# Execution Plan - PROP-012

## Objective

Add proposal-level impact analysis and persistent project-level conflict memory.

## Workstreams

### WS1 - Impact Prompt And Import

Add prompt-only impact analysis that asks AI/humans to produce:

- `impact-map.yml`
- `related-proposals.yml`
- `conflict-analysis.yml`

### WS2 - Conflict Memory

Add commands to record and inspect conflicts in `.p2p/project/conflicts.yml`.

### WS3 - Project Refresh Safety

Ensure `p2p project refresh` preserves conflict memory instead of resetting it.

### WS4 - Documentation And Tests

Document the workflow and add CLI tests.

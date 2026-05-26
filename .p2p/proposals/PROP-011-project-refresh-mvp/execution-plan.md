# Execution Plan - PROP-011

## Objective

Implement the first deterministic `.p2p/project/` refresh workflow.

## Workstreams

### WS1 - Storage

Add filesystem methods that collect accepted proposals and generate project-state files.

### WS2 - CLI

Add:

- `p2p project refresh`
- `p2p project status`
- `p2p project show`

### WS3 - Verification

Add CLI tests that accept a proposal, refresh project state, inspect status, and show a generated feature.

## Constraints

- No AI invocation.
- No automatic refresh after decision yet.
- No exporter implementation yet.

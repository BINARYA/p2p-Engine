# Execution Plan - PROP-015

## Objective

Add lifecycle transitions and task/action inspection for metadata-only Change Sets.

## Workstreams

### WS1 - Lifecycle Storage

- Parse and update `change.md` frontmatter.
- Validate allowed transitions.

### WS2 - CLI

Add:

- `p2p change show CHANGE-001`
- `p2p change set-status CHANGE-001 planned`
- `p2p change tasks CHANGE-001`

### WS3 - Verification

- Test invalid transition rejection.
- Test primary lifecycle flow.
- Test action checklist rendering.

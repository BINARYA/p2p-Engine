# Execution Plan - PROP-014

## Objective

Implement metadata-only Change Set creation and inspection.

## Workstreams

### WS1 - Storage

Add filesystem methods to:

- create `CHANGE-XXX` directories;
- reject non-accepted proposal sources;
- write `change.md`;
- write included/reference/excluded metadata;
- write metadata-only `git-policy.yml`.

### WS2 - CLI

Add commands:

- `p2p change create --from PROP-XXX`
- `p2p change status`
- `p2p change policy CHANGE-XXX`

### WS3 - Verification

Add tests for:

- rejected draft proposal source;
- accepted proposal source;
- generated files;
- metadata-only policy output.

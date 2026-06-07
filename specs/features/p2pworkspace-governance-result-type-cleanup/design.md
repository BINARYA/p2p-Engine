# P2PWorkspace Governance Result Type Cleanup Design

## Current State

`storage.filesystem` still defines dataclasses for proposal detail,
contribution list, readiness, permission actor, and consent receipt. These
objects are already created by extracted services:

- `ProposalDocumentService`;
- `ReadinessService`;
- `PermissionsService`;
- `ConsentService`.

This creates duplicate ownership and makes the facade appear responsible for
result models it delegates.

## Target State

- Import service-owned result types in `storage.filesystem`.
- Remove duplicate dataclasses from the facade.
- Remove `_consent_receipt_from_payload()` if still unused after the type move.

## Compatibility

The dataclass fields are the same as the previous facade definitions. Runtime
objects already come from services, so CLI/MCP output should remain unchanged.

## Verification

Run focused tests for proposal document, readiness, permissions/consent,
CLI/MCP coverage that touches those areas, `p2p validate`, and the full suite.

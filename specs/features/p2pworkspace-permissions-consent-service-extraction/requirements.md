# P2PWorkspace Permissions Consent Service Extraction Requirements

## Scope

This feature implements the first runtime extraction from the P2PWorkspace
refactoring roadmap.

It extracts permission policy behavior and consent receipt lifecycle behavior
from `P2PWorkspace` into internal services while preserving the public facade,
CLI behavior, MCP behavior, storage paths, dataclasses, and governance
semantics.

## Origin

- Accepted source proposal: `PROP-059 - P2PWorkspace Modular Refactoring Plan`
- Architecture contract:
  `specs/features/p2pworkspace-modular-refactoring-contract/`
- Detailed inventory:
  `specs/features/p2pworkspace-refactoring-inventory-and-extraction-map/`
- Seed section:
  `specs/features/p2pworkspace-refactoring-inventory-and-extraction-map/inventory.md`
  under `Seed: Permissions And Consent Service Extraction`

## In Scope

- Introduce internal service modules for permission policy and consent receipt
  lifecycle behavior.
- Keep `P2PWorkspace` as the compatibility facade.
- Delegate existing permission and consent facade methods to the new services.
- Preserve existing `.p2p/project/permissions.yml` and
  `.p2p/consents/CONSENT-XXX/consent.yml` storage formats.
- Add focused tests for moved normalization, validation, id allocation, status
  transition, and expiry behavior.
- Run existing CLI and MCP compatibility tests for permissions, consent, and
  permission-gated operations.

## Out Of Scope

- Changing CLI command names, options, output, or exit behavior.
- Changing MCP tool names, schemas, payloads, or permission classifications.
- Moving MCP consent audit helpers out of `src/p2p_engine/mcp/tools.py`.
- Changing Git audit commit or push behavior.
- Changing consent authorization semantics.
- Changing `.p2p` storage layout or receipt/policy YAML keys.
- Extracting broader proposal, sync, branch, Work, or registry behavior.
- Splitting `cli.py` or MCP tool registry modules.

## Functional Requirements

### R001 - Permission Service

THE SYSTEM SHALL provide an internal permission service that owns permission
policy read/write behavior, default policy payload generation, actor id
normalization, role normalization, actor kind normalization, and actor
add/update behavior.

Acceptance: `P2PWorkspace.permissions_show` and
`P2PWorkspace.permissions_actor_add` delegate to the service and return the same
objects/payloads as before.

Status: implemented

### R002 - Permission Storage Compatibility

THE SYSTEM SHALL preserve `.p2p/project/permissions.yml` layout and semantics.

Acceptance: project initialization still creates the same owner/admin policy,
and actor add/update writes the same YAML shape.

Status: implemented

### R003 - Consent Service

THE SYSTEM SHALL provide an internal consent service that owns consent id
allocation, receipt path resolution, grant, request, show, status/list, revoke,
validate, consume, and used-with-error transitions.

Acceptance: all existing `P2PWorkspace` consent methods delegate to the service
and return the same `ConsentReceipt`-compatible objects as before.

Status: implemented

### R004 - Consent Storage Compatibility

THE SYSTEM SHALL preserve `.p2p/consents/CONSENT-XXX/consent.yml` layout,
sequential `CONSENT-XXX` ids, and receipt status semantics.

Acceptance: existing CLI/MCP tests can read the same receipt YAML keys and
status values after extraction.

Status: implemented

### R005 - Consent Validation Semantics

THE SYSTEM SHALL preserve consent validation for operation, target, actor,
status, expiry, owner approver, requested receipts, consumed receipts, revoked
receipts, and used-with-error receipts.

Acceptance: requested receipts do not authorize execution, actor mismatch does
not consume a receipt, expired granted receipts mutate to `expired`, and
permission-gated MCP operations still require matching granted consent.

Status: implemented

### R006 - MCP Audit Boundary Preservation

THE SYSTEM SHALL keep MCP consent audit orchestration outside the core consent
service in this feature.

Acceptance: `_consume_consent_with_audit`,
`_commit_and_push_consent_audit`, and `_mark_consent_error_on_head_change`
remain MCP-side helpers or equivalent MCP-side behavior, and continue to call
the `P2PWorkspace` facade.

Status: implemented

### R007 - Facade Compatibility

THE SYSTEM SHALL preserve public `P2PWorkspace` method names, signatures,
return shapes, and error behavior for permissions and consent.

Acceptance: CLI and MCP layers require no command/tool behavior changes to use
the extracted services.

Status: implemented

### R008 - Focused Test Coverage

THE SYSTEM SHALL add focused tests for moved permission and consent logic.

Acceptance: focused tests cover owner default payload, actor id normalization,
role/kind normalization, consent id allocation, requested-not-authorized,
actor mismatch, expiry mutation, used-with-error, and consumed/revoked guards.

Status: implemented

### R009 - Compatibility Test Preservation

THE SYSTEM SHALL keep all mapped CLI/MCP compatibility tests passing unchanged.

Acceptance: the existing permission, consent, and permission-gated MCP tests
listed in the design pass without weakening or rewriting their assertions.

Status: implemented

## Non-Functional Requirements

### N001 - No Behavior Drift

THE SYSTEM SHALL treat this as an internal extraction only.

Acceptance: no public CLI/MCP/storage/governance behavior changes are made.

Status: implemented

### N002 - No Presentation Coupling

THE SYSTEM SHALL keep new services free of Typer, Rich, and MCP transport
imports.

Acceptance: services are called from `P2PWorkspace` and return domain objects
or existing-compatible payloads.

Status: implemented

### N003 - Narrow Extraction

THE SYSTEM SHALL avoid moving unrelated proposal, branch, sync, registry, or
MCP audit behavior.

Acceptance: source changes are limited to service modules, facade delegation,
and focused tests required by this feature.

Status: implemented

## Edge Cases And Errors

- Invalid permission role.
- Invalid actor kind.
- Missing or malformed permission policy.
- Non-owner approver for granted consent.
- Unknown actor id.
- Invalid consent operation.
- Invalid consent id.
- Missing consent receipt.
- Requested receipt used for execution.
- Actor mismatch.
- Operation mismatch.
- Target mismatch.
- Expired receipt.
- Revoked receipt.
- Consumed receipt.
- Used-with-error receipt.
- Consent consume result payload preservation.

## Acceptance Criteria

- AC001: `P2PWorkspace` remains the public facade for permissions and consent.
- AC002: Permission and consent behavior is implemented behind internal
  services.
- AC003: Existing CLI/MCP permission and consent tests pass unchanged.
- AC004: Focused service tests cover the moved behavior and negative paths.
- AC005: No CLI command, MCP tool, storage path, YAML shape, id format, or
  governance semantic changes are introduced.
- AC006: MCP consent audit behavior remains outside the core consent service.
- AC007: The completed implementation report lists facade methods delegated,
  helpers moved, helpers intentionally left in place, tests run, and remaining
  gaps.

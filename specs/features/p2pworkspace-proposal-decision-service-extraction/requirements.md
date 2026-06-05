# P2PWorkspace Proposal Decision Service Extraction Requirements

## Scope

Extract non-branch proposal decision recording from `P2PWorkspace` into an
internal service while preserving CLI, MCP, storage, and governance semantics.

This feature covers proposal decisions recorded against draft/local proposal
artifacts. It does not cover managed proposal branch lifecycle, Git operations,
sync, Work decisions, choice decisions, registry refresh, project-state refresh,
or owner readiness checks.

## Functional Requirements

### R001 - Decision Service

THE SYSTEM SHALL provide an internal service that records proposal decisions
for accepted, rejected, deferred, and other `DecisionOutcome` values currently
accepted by `P2PWorkspace.record_decision`.

Status: implemented

### R002 - Storage Compatibility

WHEN a proposal decision is recorded, THE SYSTEM SHALL preserve the existing
`.p2p/proposals/PROP-XXX-*/decision.md` path and markdown section shape.

Status: implemented

### R003 - Proposal Status Compatibility

WHEN a proposal decision is recorded, THE SYSTEM SHALL update the proposal
`## Status` section to the decision outcome exactly as before.

Status: implemented

### R004 - Facade Compatibility

THE SYSTEM SHALL keep `P2PWorkspace.record_decision` as the public runtime
facade used by CLI, MCP, tests, and internal callers.

Status: implemented

### R005 - Governance Boundary

THE SYSTEM SHALL NOT move managed proposal branch decisions, consent
validation/consumption, readiness override checks, registry refresh, project
state refresh, Git operations, or owner-controlled acceptance policy into the
decision service.

Status: implemented

## Non-Functional Requirements

### N001 - No Presentation Or Transport Coupling

THE SYSTEM SHALL keep the service free of Typer, Rich, MCP, and JSON-RPC
imports.

Status: implemented

### N002 - Focused Compatibility Tests

THE SYSTEM SHALL add focused service tests for decision markdown generation,
proposal status mutation, and facade compatibility.

Status: implemented

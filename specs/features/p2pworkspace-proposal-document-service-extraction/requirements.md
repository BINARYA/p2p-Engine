# P2PWorkspace Proposal Document Service Extraction Requirements

## Scope

Extract proposal document lifecycle behavior from `P2PWorkspace` into an
internal service while excluding branch lifecycle and governance decisions.

## Functional Requirements

### R001 - Proposal Document Service

THE SYSTEM SHALL provide an internal service for proposal create, show, update,
contribution add/list, id allocation, directory lookup, and duplicate-id
detection.

Status: implemented

### R002 - Storage Compatibility

THE SYSTEM SHALL preserve `.p2p/proposals/PROP-XXX-slug` layout and generated
proposal files.

Status: implemented

### R003 - Facade Compatibility

THE SYSTEM SHALL keep `P2PWorkspace` as the public caller boundary.

Status: implemented

### R004 - Governance/Branch Boundary

THE SYSTEM SHALL leave proposal decisions, readiness, branch lifecycle, and Git
behavior outside this service.

Status: implemented

## Non-Functional Requirements

### N001 - No Presentation Coupling

THE SYSTEM SHALL keep the service free of Typer, Rich, and MCP imports.

Status: implemented

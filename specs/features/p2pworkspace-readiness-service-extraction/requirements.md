# P2PWorkspace Readiness Service Extraction Requirements

## Scope

Extract proposal readiness profile and assessment behavior from `P2PWorkspace`
into an internal service while preserving advisory semantics and public CLI/MCP
behavior.

## Functional Requirements

### R001 - Readiness Service

THE SYSTEM SHALL provide an internal service for readiness profile read/create,
proposal readiness read/write, owner override, refresh, and initialization.

Status: implemented

### R002 - Storage Compatibility

THE SYSTEM SHALL preserve readiness profile and proposal readiness YAML paths
and payload shapes.

Status: implemented

### R003 - Scoring Compatibility

THE SYSTEM SHALL preserve computed score, label, failed gates, missing items,
suggested next actions, quality caps, and owner-input gate behavior.

Status: implemented

### R004 - Advisory Boundary

THE SYSTEM SHALL keep readiness advisory and shall not move proposal acceptance
or owner governance decisions into the service.

Status: implemented

### R005 - Facade Compatibility

THE SYSTEM SHALL keep `P2PWorkspace` as the public caller boundary.

Status: implemented

## Non-Functional Requirements

### N001 - No Presentation Coupling

THE SYSTEM SHALL keep the service free of Typer, Rich, and MCP imports.

Status: implemented

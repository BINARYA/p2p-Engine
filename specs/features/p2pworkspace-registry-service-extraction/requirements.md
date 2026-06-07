# P2PWorkspace Registry Service Extraction Requirements

## Scope

Extract registry write/read/status behavior from `P2PWorkspace` into an
internal service while preserving CLI, MCP, and `.p2p/registries` compatibility.

This feature covers:

- writing generated registry YAML files;
- registry status freshness/count checks;
- registry show/read behavior;
- supported registry name mapping;
- duplicate proposal guard before refresh.

It does not cover the domain-specific record builders for proposals, decisions,
changes, choices, relations, artifacts, or readiness. Those remain facade
callbacks for this slice.

## Functional Requirements

### R001 - Registry Service

THE SYSTEM SHALL provide an internal service for registry refresh, status, and
show operations.

Status: implemented

### R002 - Registry File Compatibility

WHEN registries are refreshed, THE SYSTEM SHALL preserve the existing
`.p2p/registries/*.yml` filenames, top-level keys, `generated: true`, and
`source` values.

Status: implemented

### R003 - Freshness Compatibility

WHEN registry status is requested, THE SYSTEM SHALL preserve stale detection
for missing files, non-generated files, proposal count drift, and change count
drift.

Status: implemented

### R004 - Show Compatibility

WHEN a registry is shown, THE SYSTEM SHALL preserve supported registry names,
missing registry errors, invalid registry errors, and record filtering to
mapping records.

Status: implemented

### R005 - Facade Compatibility

THE SYSTEM SHALL keep `P2PWorkspace.refresh_registries`, `registry_status`, and
`show_registry` as the public facade methods used by CLI, MCP, project
assessment, context, and intake flows.

Status: implemented

### R006 - Record Builder Boundary

THE SYSTEM SHALL NOT move proposal, decision, change, choice, relation,
artifact, readiness, project-state, intake, CLI, MCP, Git, or sync behavior into
the registry service.

Status: implemented

## Non-Functional Requirements

### N001 - No Presentation Or Lifecycle Coupling

THE SYSTEM SHALL keep the service free of Typer, Rich, MCP, JSON-RPC, Git,
sync, project-state assessment, intake, and Work/proposal lifecycle imports.

Status: implemented

### N002 - Focused Compatibility Tests

THE SYSTEM SHALL add focused service tests for refresh payload shape, stale
status detection, show validation, and facade delegation.

Status: implemented

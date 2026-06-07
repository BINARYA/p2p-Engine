# P2PWorkspace Software Spec Service Extraction Requirements

## Scope

Extract native software-spec generation and import behavior from `P2PWorkspace`
into an internal service while preserving CLI, MCP, storage, and export
compatibility.

## Origin

- Accepted source proposal: `PROP-059 - P2PWorkspace Modular Refactoring Plan`
- Prerequisite foundation:
  `specs/features/p2pworkspace-renderers-validators-foundation/`

## In Scope

- Extract software-spec refresh/status/show/prompt/import behavior.
- Preserve `.p2p/outputs/software-spec/CHANGE-XXX` artifact layout.
- Keep `P2PWorkspace` as compatibility facade.
- Keep generic/OpenSpec/Spec Kit export behavior out of this service.
- Add focused tests and run mapped CLI/MCP compatibility tests.

## Out Of Scope

- Project definition synthesis.
- Generic/OpenSpec/Spec Kit export rendering.
- Work planning.
- CLI/MCP modularization.
- Changing generated artifact content or required artifact list.

## Functional Requirements

### R001 - Software Spec Service

THE SYSTEM SHALL provide an internal service for software-spec refresh,
statuses, show, prompt creation, and import.

Acceptance: corresponding `P2PWorkspace` methods delegate to the service.

Status: implemented

### R002 - Artifact Compatibility

THE SYSTEM SHALL preserve the required software-spec files and generated
content shape.

Acceptance: `index.md`, `requirements.md`, `design.md`, `commands.yml`,
`data-model.yml`, `acceptance.md`, and `provenance.yml` are generated/imported
as before.

Status: implemented

### R003 - Import Validation Compatibility

THE SYSTEM SHALL preserve import validation for required files and YAML
top-level keys.

Acceptance: missing files and invalid `commands`, `entities`, or `source` YAML
keys raise the same error message fragments.

Status: implemented

### R004 - Export Boundary

THE SYSTEM SHALL leave `export_software_spec`, export statuses, export show,
and export validation in `P2PWorkspace` for this feature.

Acceptance: export methods continue to work through existing facade behavior.

Status: implemented

### R005 - Compatibility Tests

THE SYSTEM SHALL keep existing CLI/MCP software-spec and export tests passing.

Acceptance: mapped CLI/MCP tests and full suite pass.

Status: implemented

## Non-Functional Requirements

### N001 - No Presentation Coupling

THE SYSTEM SHALL keep the service free of Typer, Rich, and MCP imports.

Status: implemented

### N002 - Narrow Extraction

THE SYSTEM SHALL avoid moving project-definition/spec-export renderers in this
feature.

Status: implemented

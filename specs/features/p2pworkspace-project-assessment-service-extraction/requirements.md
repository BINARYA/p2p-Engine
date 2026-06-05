# P2PWorkspace Project Assessment Service Extraction Requirements

## Scope

Extract deterministic project assessment refresh/show behavior from
`P2PWorkspace` into an internal service while preserving CLI, MCP, and storage
compatibility.

This feature covers:

- project assessment computation;
- `.p2p/project/assessment.yml` write/read;
- completion score/status/confidence factors;
- maturity status/score inclusion when maturity assessment exists.

It does not cover project definition maturity computation, rubrics, project
state refresh, registry generation, next-action lifecycle, context packets,
intake, Git, sync, CLI formatting, or MCP formatting.

## Functional Requirements

### R001 - Project Assessment Service

THE SYSTEM SHALL provide an internal service for project assessment refresh,
show, payload writing, and payload reading.

Status: implemented

### R002 - Assessment Computation Compatibility

THE SYSTEM SHALL preserve the existing deterministic completion score,
completion status, confidence, factors, gaps, and suggested action computation.

Status: implemented

### R003 - Storage Compatibility

WHEN assessment is refreshed, THE SYSTEM SHALL preserve
`.p2p/project/assessment.yml` and the existing YAML payload shape.

Status: implemented

### R004 - Maturity Compatibility

WHEN `.p2p/project/maturity-assessment.yml` exists, THE SYSTEM SHALL preserve
the existing maturity status and score inclusion in project assessment.

Status: implemented

### R005 - Show Compatibility

WHEN assessment is shown, THE SYSTEM SHALL preserve existing parsing defaults
and missing-assessment error behavior.

Status: implemented

### R006 - Facade Compatibility

THE SYSTEM SHALL keep `P2PWorkspace.refresh_project_assessment`,
`show_project_assessment`, and `_compute_project_assessment` as compatibility
facade methods.

Status: implemented

## Non-Functional Requirements

### N001 - Boundary Isolation

THE SYSTEM SHALL keep maturity computation, rubrics, project-state refresh,
registry generation, next-action lifecycle, context packets, intake, Git, sync,
CLI formatting, and MCP formatting outside the service.

Status: implemented

### N002 - Focused Compatibility Tests

THE SYSTEM SHALL add focused service tests for score computation, persistence,
show parsing, maturity inclusion, missing-assessment errors, and facade
delegation.

Status: implemented

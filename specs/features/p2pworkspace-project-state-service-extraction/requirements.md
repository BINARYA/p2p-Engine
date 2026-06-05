# P2PWorkspace Project State Service Extraction Requirements

## Scope

Extract project-state artifact and operational brief behavior from
`P2PWorkspace` into an internal service while preserving CLI, MCP, and storage
compatibility.

This feature covers:

- project refresh files under `.p2p/project`;
- project state status;
- project state section show;
- project brief prompt creation;
- project brief import;
- project brief show.

It does not cover project assessment, definition maturity, rubrics, next-action
lifecycle, registry generation, intake, context packets, Git, sync, CLI
formatting, or MCP formatting.

## Functional Requirements

### R001 - Project State Service

THE SYSTEM SHALL provide an internal service for project refresh, project state
status, project state show, project brief prompt, project brief import, and
project brief show.

Status: implemented

### R002 - Project Artifact Compatibility

WHEN project state is refreshed, THE SYSTEM SHALL preserve the existing
`.p2p/project` file paths and generated file shapes.

Status: implemented

### R003 - Feature Artifact Compatibility

WHEN project state is refreshed, THE SYSTEM SHALL preserve per-feature
directories, `feature.md`, copied `tasks.yml`, and generated `actions.yml` for
accepted proposals.

Status: implemented

### R004 - Project Status Compatibility

WHEN project status is requested, THE SYSTEM SHALL preserve accepted proposal
count, feature list, project directory path, operational brief availability,
next action count, and first next action fields.

Status: implemented

### R005 - Project Show Compatibility

WHEN a project section is shown, THE SYSTEM SHALL preserve supported sections
and feature-id lookup behavior, including the existing missing-section error.

Status: implemented

### R006 - Brief Compatibility

THE SYSTEM SHALL preserve project brief prompt paths, context generation,
single-file import, directory import for `operational-brief.md` and
`next-actions.yml`, YAML validation for imported next actions, and missing brief
errors.

Status: implemented

### R007 - Facade Compatibility

THE SYSTEM SHALL keep `P2PWorkspace.refresh_project_state`,
`project_state_status`, `show_project_state`, `create_project_brief_prompt`,
`import_project_brief`, and `show_project_brief` as public facade methods.

Status: implemented

## Non-Functional Requirements

### N001 - Boundary Isolation

THE SYSTEM SHALL keep assessment, maturity, rubrics, next-action lifecycle,
registry generation, intake, context packets, Git, sync, CLI formatting, and MCP
formatting outside the service.

Status: implemented

### N002 - Focused Compatibility Tests

THE SYSTEM SHALL add focused service tests for project refresh, status/show,
brief prompt/import/show, and facade delegation.

Status: implemented

# P2PWorkspace Work Planning Service Extraction Requirements

## Scope

Extract Work planning metadata behavior from `P2PWorkspace` into an internal
service while preserving CLI, MCP, storage, and lifecycle compatibility.

This feature covers planned Work metadata only:

- create Work plan from a validated spec export;
- list local and scanned Work statuses;
- list Work summaries with next-action hints;
- show Work detail;
- allocate and resolve Work directories.

It does not cover managed Work branch creation, retire, submit, review,
publish, accept, finalize, cleanup, scan implementation, Git operations, sync,
or provider review handoff.

## Functional Requirements

### R001 - Work Planning Service

THE SYSTEM SHALL provide an internal service for Work plan creation, Work
status listing, Work summary listing, Work detail reads, Work id allocation,
and Work directory lookup.

Status: implemented

### R002 - Manifest Compatibility

WHEN a Work plan is created, THE SYSTEM SHALL preserve the existing
`.p2p/work/WORK-XXX/manifest.yml` path and manifest payload shape.

Status: implemented

### R003 - Handoff Compatibility

WHEN a Work plan is created, THE SYSTEM SHALL validate the requested export
target and use the existing export validation result for export path and
allowed files.

Status: implemented

### R004 - Listing Compatibility

THE SYSTEM SHALL preserve `work_statuses`, `work_summaries`, and `show_work`
return attributes and next-action semantics for local and scanned Work items.

Status: implemented

### R005 - Facade Compatibility

THE SYSTEM SHALL keep `P2PWorkspace.create_work_plan`, `work_statuses`,
`work_summaries`, `show_work`, `_next_work_id`, and `_find_work_dir` as public
or compatibility facade methods.

Status: implemented

### R006 - Lifecycle Boundary

THE SYSTEM SHALL NOT move Work branch, retire, submit, review, publish, accept,
finalize, cleanup, scan implementation, Git, sync, or provider handoff behavior
into the planning service.

Status: implemented

## Non-Functional Requirements

### N001 - No Presentation Or Git Coupling

THE SYSTEM SHALL keep the service free of Typer, Rich, MCP, JSON-RPC, Git
adapter, sync, provider, and consent imports.

Status: implemented

### N002 - Focused Compatibility Tests

THE SYSTEM SHALL add focused service tests for Work plan creation, status/list
mapping, scanned-item summaries, and facade compatibility.

Status: implemented

# Design - Export Project Structure As Vertical

## Requirements Covered

- R001-R017
- N001-N004
- AC001-AC010

## Decision Summary

Add an explicit structure-export adapter over the existing vertical draft and
portable-pack services. The adapter snapshots active project structure,
validates export metadata and lineage, and materializes a schema-3 vertical
draft/package. It never changes the source project or publishes remotely.

## Key Decisions

### D001 - Export Active Structure, Not Project Memory

The pack contains structural guidance only: active sections, fields, questions,
criteria, artifacts, profiles/modules and portable metadata. Proposal,
decision, evidence and retired history remain project memory and are excluded.

### D002 - Explicit Social Lineage

The user chooses derived or independent for every export. Derived mode names an
exact source release and checks policy/license. Independent mode removes social
lineage but cannot erase attribution required by source licenses.

### D003 - Reuse Draft And Pack Services

The export service produces the canonical document accepted by the existing
vertical draft validator. Draft materialization, package normalization,
checksum and local-catalog insertion remain owned by current portable vertical
services.

### D004 - Preview Binds Exact Source Revision

Preview token binds project identity, structure revision/checksum, export
metadata, lineage mode and active-element semantic hash. Apply rejects any
structure change and uses an operation key for safe response-loss recovery.

### D005 - MCP Write Explicitly Deferred

MCP exposes export eligibility and preview metadata through read-only tools,
but it does not receive a path-writing package command. Standalone agents use
the documented CLI for apply; the WaveKit worker invokes that CLI with
server-owned destinations.

### D006 - Export Authority Is Not Artifact Ownership

Durable export declares `project.vertical.export` through the shared
AuthorityContext. That authority permits reading the exact project structure
into a new private draft; it does not prove publisher ownership, permit remote
publication or grant moderation rights. Local and hosted policy resolve those
separate boundaries independently.

## Components And Ownership

- Structure export snapshot/preview service.
- Export metadata and lineage validator.
- Adapter to vertical draft/materialize/package services.
- Receipt/status integration for durable local export.
- CLI text/JSON commands and optional MCP read-only preview.
- Documentation and installed-wheel fixtures.

## Alternatives Considered

- Automatically release every structure revision: rejected because it creates
  catalog noise and conflates project editing with vertical authoring.
- Copy the current vertical origin then apply project deltas: rejected because
  origin may no longer resemble current structure.
- Export retired history: rejected because a reusable starting structure should
  contain only current active guidance.

## Compatibility

Export produces only the current schema-3 portable format and requires a
schema-4 project. Old pack and workspace formats are not emitted.

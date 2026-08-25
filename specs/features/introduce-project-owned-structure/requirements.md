# Requirements - Introduce Project-Owned Structure

## Scope

Introduce a first-class structure owned by each project. Initialization copies
one effective starter or vertical release into this mutable project aggregate;
the source release remains immutable provenance and no longer defines the
project's live structural identity.

## Origin

- Source: owner-approved domain, vertical and project-structure review.
- Target train: P2P Engine `0.5.0`, workspace schema 4.
- Depends on: `separate-domain-from-structure-source` and
  `support-typed-authority-context-in-governed-mutations`.

## In Scope

- Canonical `ProjectStructure` identity, revision, checksum and origin.
- Stable identifiers for sections, fields, questions, criteria and artifacts.
- Active/retired lifecycle support in the structure schema.
- Initialization by detached copy of an effective source.
- Empty structure support.
- Atomic add, metadata update and reorder mutations.
- Read-only structure snapshot and bounded history/event reads.
- Separation of invariant P2P memory capabilities from configurable structure.

## Out Of Scope

- Referenced-element retirement and disposition planning.
- Proposal/global/unassigned memory classification.
- Readiness scoring and vertical export.
- Full structure replacement, merge or restore.
- WaveKit drafts, authorization or catalog models.

## Public Surface And MCP Impact

- CLI impact: new versioned structure reads and receipt-backed simple mutation
  commands; active-vertical-as-structure commands become breaking/deprecated.
- MCP impact: read parity and consent-gated simple mutation parity are required.
- Storage impact: workspace schema 4 canonical project-structure aggregate and
  append-only structure event evidence.
- Agent-facing behavior: agents operate on project structure and treat origin
  as provenance only.

## Functional Requirements

### Canonical Aggregate

- R001: Every initialized project SHALL have exactly one canonical
  `ProjectStructure` with a stable project-local identifier.
- R002: The structure SHALL expose monotonically increasing revision and a
  deterministic semantic checksum.
- R003: The structure SHALL own its sections, fields, questions, readiness
  criteria, artifacts and their ordering independently from its origin.
- R004: Every structural element SHALL have an immutable bounded stable ID that
  is distinct from its editable title and description.
- R005: Stable IDs SHALL never be reused for a semantically different element.
- R006: Each canonical element SHALL have lifecycle `active` or `retired`.

### Initialization And Origin

- R007: Initialization from a starter or vertical release SHALL copy the
  effective normalized structure into project-owned state.
- R008: Later changes to the source release SHALL NOT modify an initialized
  project automatically.
- R009: Structure origin SHALL record source kind, exact release identity where
  applicable, checksum, opaque external reference and application timestamp.
- R010: Origin SHALL NOT constrain edits, contribute to readiness or imply that
  the current project remains conformant to the source.
- R011: Empty initialization SHALL create revision 1 with zero active sections
  and zero active criteria.

### Simple Mutations

- R012: A subject authorized for `project.structure.edit` SHALL be able to add
  a new section with server-generated or validated stable ID.
- R013: Structure mutation SHALL support editing bounded metadata while
  preserving stable identity.
- R014: Structure mutation SHALL support reordering the complete active section
  set without changing identity or meaning.
- R015: Removing an unapplied draft-only element MAY be handled by a caller,
  but retiring a canonical element SHALL use the impact-resolution feature.
- R016: Every canonical mutation SHALL require expected structure revision,
  typed authority context and operation key.
- R017: Successful mutation SHALL atomically commit structure, event and receipt
  and return previous/new revision plus checksum.
- R018: A stale expected revision SHALL fail without partial writes.
- R019: Exact replay SHALL return the original result; divergent key reuse SHALL
  fail deterministically.

### Definition And Core Boundary

- R020: Project definition values SHALL reference structure IDs and SHALL not
  define the structural schema themselves.
- R021: Ideas, proposal storage, decisions, contributions, audit and project
  identity services SHALL remain available when the structure is empty.
- R022: Feature-specific validation MAY require active structural targets, but
  absence of structure SHALL not make the workspace invalid.

### Reads And History

- R023: Structured reads SHALL return active and optionally retired elements,
  revision, checksum, origin and bounded event history without physical paths.
- R024: Reads SHALL be side-effect free and deterministic for unchanged state.
- R025: Structure validation SHALL diagnose duplicate IDs, broken references,
  invalid lifecycle, ordering errors and checksum drift.

### Governed Capability Contract

- R026: Add, metadata-update and reorder apply operations SHALL declare
  capability `project.structure.edit` and bind the exact typed authority
  context to preview, apply, event and receipt.
- R027: P2P local policy SHALL preserve standalone owner control, while hosted
  delegability remains an external-provider policy and SHALL NOT be inferred
  from transport or WaveKit roles.

## Non-Functional Requirements

- N001: Structural mutations SHALL use the existing cross-process workspace
  lock, atomic writer and receipt service.
- N002: Public collections SHALL be bounded and report total, returned and
  truncation state.
- N003: Internal storage layout SHALL remain private and SHALL not become a CLI
  or MCP contract.
- N004: Structure services SHALL not depend on CLI formatting, MCP transport or
  WaveKit concepts.
- N005: Normalization and checksum generation SHALL be deterministic across
  supported Python versions and installed wheels.

## Edge Cases And Errors

- Empty source structure.
- Duplicate or reserved structural IDs.
- Rename that attempts to change stable ID.
- Reorder with missing, duplicate or unknown IDs.
- Stale revision, concurrent mutation and lost response.
- Corrupt origin or event history.
- Structure checksum mismatch.
- Existing schema-3 active vertical and definition state.
- Read with more elements or events than the public bound.

## Acceptance Criteria

- AC001: Generic and exact-pack initialization produce detached revision-1
  structures whose future source changes have no effect.
- AC002: Empty initialization is valid and returns zero active elements.
- AC003: Add, rename and reorder preserve stable IDs and advance revision once.
- AC004: Stale apply and divergent replay produce no structural change.
- AC005: Origin remains queryable but never participates in validation of
  current completeness or readiness.
- AC006: Project definition values continue to resolve through current stable
  structure IDs.
- AC007: CLI and MCP reads expose the same logical structure and no internal
  paths.
- AC008: Fault-injection proves atomic structure/event/receipt behavior.
- AC009: Structure apply records `project.structure.edit` authority and rejects
  a changed or mismatched authority context without structural mutation.

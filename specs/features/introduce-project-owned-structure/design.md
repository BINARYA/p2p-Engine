# Design - Introduce Project-Owned Structure

## Requirements Covered

- R001-R027
- N001-N005
- AC001-AC009

## Decision Summary

Create one logical `ProjectStructure` aggregate in workspace schema 4. The
effective selected source is normalized and copied at initialization. Origin is
immutable provenance plus append-only events; the live structure has its own
identity, revision and checksum. Simple edits are receipt-backed. Retirement
and cross-memory disposition are delegated to the next feature.

## Key Decisions

### D001 - One Logical Aggregate, Private Physical Layout

The aggregate owns normalized sections, fields, questions, criteria, artifacts
and order. It may be persisted in more than one private artifact for bounded
updates, but one validator, revision and checksum define the atomic aggregate.
No public payload exposes those filenames.

### D002 - Copy Effective Source, Do Not Keep A Live Lock

Initialization resolves inheritance and dependencies before copying normalized
effective content. The old active vertical lock is replaced by
`StructureOrigin`; it cannot cause later pack updates or conformity checks.

### D003 - Stable IDs And Lifecycle Are Foundational

Title changes preserve IDs. IDs are unique within their element namespace and
cannot be reused after retirement. Lifecycle is present from schema 4 even
before referenced retirement is implemented, avoiding a second schema rewrite.

### D004 - Separate Structure Revision From Memory Revision

Structure revision advances only for structure changes. Existing project-memory
revision continues to identify broader state changes. Mutations validate the
structure revision and register all physical source preconditions; callers such
as WaveKit may additionally serialize by their own operational revision.

### D005 - Simple Mutation Contract

Public operations cover add, metadata update and reorder. Their payload contract
is `p2p-project-structure-mutation/v1`; read contract is
`p2p-project-structure/v1`. Retirement, replacement and merge have separate
operation IDs and cannot be smuggled through a generic patch document.

### D006 - Core Memory Exists Without Structural Targets

The structure is a configurable organization and readiness layer. Workspace
identity and core memory services remain valid at zero sections. Individual
operations may impose stronger target requirements until memory-classification
semantics are introduced.

### D007 - Simple Structure Apply Uses One Capability Contract

Add, metadata-update and reorder plans declare `project.structure.edit` and
carry the shared AuthorityContext through preview, apply and receipts. Local
policy remains owner-controlled. Hosted delegability is neither assumed nor
encoded, allowing providers to keep the capability root-only initially and
extend policy later without changing structure payloads.

## Components And Ownership

- Core structure models and deterministic serializers.
- Structure repository/validator and event ledger.
- Initialization materializer from normalized starter or effective pack.
- Structure query service and simple mutation service.
- Definition-state adapter keyed by structure IDs.
- CLI and MCP handlers over shared services.
- Validation and snapshot services updated for structure identity.

## Transaction And Recovery

Planning reads one immutable source snapshot. Apply binds expected structure
revision, candidate checksum and source preconditions into the preview token and
receipt fingerprint. Structure, event evidence and receipt commit in one atomic
transaction. Existing transaction status/resume rules handle interruption.

## Alternatives Considered

- Keep a synthetic private vertical release as current structure: rejected
  because every project edit would remain vertical authoring by another name.
- Store only deltas over the origin pack: rejected because origin would remain a
  runtime dependency and long-lived merge base.
- Use section titles as identity: rejected because rename would break memory
  references and historical interpretation.

## Migration And Compatibility

The implementation is schema-4-only. Schema-3 vertical lock, domain rubric and
definition layout have no runtime compatibility adapter. Bundled and official
vertical releases are regenerated under the new pack schema before the 0.5.0
release gate.

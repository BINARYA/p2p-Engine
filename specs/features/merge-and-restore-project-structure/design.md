# Design - Merge And Restore Project Structure

## Requirements Covered

- R001-R015
- N001-N004
- AC001-AC009

## Decision Summary

Treat merge and restore as future specialized structure transitions. They reuse
the same source normalizer, stable-ID comparator, impact/disposition planner,
atomic writer and receipt model as replacement. Restore creates a new revision
from a retained historical snapshot; it never rewinds the project filesystem or
project-memory ledger.

## Key Decisions

### D001 - Deferred Capability, Complete Specification

The feature is specified now to prevent P2/P4 storage choices from making it
impossible, but it is not part of the initial 0.5.0 implementation gate. Agent
capabilities remain disabled until implementation evidence exists.

### D002 - Selective Import Is Structural, Not Textual Merge

A plan identifies exact source element IDs, dependencies, destination order and
collision decisions. It operates on normalized typed models and never performs
YAML or prose merge.

### D003 - Restore Is A Forward Mutation

Historical revision N is read as a source snapshot. Applying it creates revision
current+1 and `StructureRestored`; current project memory is reconciled through
the normal impact plan. History is never rewound.

### D004 - Retention Is A Precondition

Restore can only target snapshots retained and validated by the project-
structure history policy. The CLI cannot reconstruct missing private artifacts
from receipts, publications or origin packs.

### D005 - MCP Apply Deferred

MCP exposes only side-effect-free merge comparison and retained-revision
inspection over already available sources. Advanced multi-decision apply,
local pack acquisition and restore authority remain CLI-only until a later
explicit consent feature is reviewed.

### D006 - Merge And Restore Never Share Implicit Authority

Merge declares `project.structure.merge`; restore declares
`project.structure.restore`. Both consume the shared AuthorityContext when they
become implementable. Their deferred status means no caller can infer either
capability from simple edit, replacement, local file access or MCP read access.

## Components And Ownership

- Selective import plan and dependency resolver.
- Historical structure snapshot reader.
- Existing comparator, impact and materialization services.
- Merge/restore event and receipt serializers.
- Future CLI apply and required read-only MCP comparison/inspection surfaces.

## Alternatives Considered

- Git-like three-way merge: rejected because project structure is typed domain
  state, not source text.
- Rewind workspace files to an old revision: rejected because it would also
  rewind unrelated project memory or break references.
- Implement before replacement: rejected because replacement provides the
  simpler transition and recovery foundation.

## Compatibility

Only schema-4 history and schema-3 vertical packs are eligible. No older
workspace reconstruction path is included.

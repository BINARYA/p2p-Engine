# Design - Retire Structure Elements With Impact Resolution

## Requirements Covered

- R001-R030
- N001-N005
- AC001-AC009

## Decision Summary

Model ordinary structural removal as lifecycle retirement. A typed impact
analyzer joins current structure with the project-memory reference index and
produces explicit disposition decisions. A complete plan is re-previewed to
obtain the only token eligible for one atomic apply.

## Key Decisions

### D001 - Tombstone Identity, Not Physical Delete

Retired elements remain in canonical history with stable IDs, retirement
revision, actor and reason. Active views filter them; history and old decision
references can still resolve their labels and provenance. IDs cannot be reused.

### D002 - Two-Preview Decision Loop

The first preview discovers impact and required dispositions. The caller submits
a strict `p2p-structure-retirement-plan/v1` keyed by decision IDs. The second
preview validates completeness and returns a state-bound apply token. Apply
never accepts an unreviewed free-form mapping.

### D003 - Active And Historical References Have Different Rules

Historical records retain retired references. Active pending work may become
unassigned; active authoritative work must remain section-classified or
explicitly global. Questions, evidence and artifacts use their declared
lifecycle actions. Unknown active kinds fail closed.

### D004 - One Reference Index And One Impact Analyzer

Extend the structure-aware memory projection created by P3. The retirement
analyzer consumes one immutable snapshot and does not let CLI, MCP or storage
facades perform their own emptiness checks. Completeness and truncation are
first-class blockers.

### D005 - Preview Includes Two Independent Impacts

The preview reports projected readiness and memory-classification changes but
does not merge them into one score. The applied result is validated by fresh
reads of both contracts.

### D006 - Apply Is A Cross-Memory Atomic Mutation

The plan fingerprint binds target IDs, dispositions, structure/memory
revisions, source identities, actor and policy version. Materialization updates
structure lifecycle and supported memory references together with event and
receipt. Existing workspace recovery owns interruption handling.

### D007 - Retirement Has A Dedicated Capability

Retirement declares `project.structure.retire` rather than inheriting generic
edit authority. The exact AuthorityContext is part of both preview phases and
the final receipt. Local policy keeps owner control; a hosted provider can keep
this higher-risk capability nondelegable without P2P importing provider roles.

## Components And Ownership

- Core retirement impact, decision, disposition and result contracts.
- Structure reference-index query service.
- Retirement analysis and plan-validation service.
- Retirement materialization service.
- Readiness and classification projected-impact adapters.
- Atomic lifecycle orchestration and receipt/status support.
- CLI/MCP serializers and agent guidance.

## Public Contracts

- `p2p-structure-retirement-impact/v1`
- `p2p-structure-retirement-plan/v1`
- `p2p-structure-retirement-result/v1`

Collections expose totals and truncation. References use domain IDs such as
`proposal:PROP-001` and `section:market`, never filesystem paths.

## Alternatives Considered

- Permanently block every referenced section: safe but rejects the product's
  required structural freedom.
- Delete and move everything to unassigned automatically: rejected because it
  hides owner decisions and destroys historical interpretation.
- Keep old sections active but mark them optional: rejected because they would
  remain part of current structure and could still distort readiness.

## Compatibility

Retirement is defined only for workspace schema 4 and explicit project-memory
scope. Old orphan and vertical-transition mapping formats are not accepted.

# Design - Rebase Readiness On Project Structure

## Requirements Covered

- R001-R027
- N001-N005
- AC001-AC009

## Decision Summary

Build one pure readiness composition service from an immutable current
ProjectStructure plus indexed project memory. Publish definition completeness
and evidence coverage as separate axes. Publish memory classification alongside,
never inside, readiness. Remove domain-template maturity and origin-conformity
logic from the current runtime.

## Key Decisions

### D001 - One Source Snapshot, Multiple Explicit Axes

One snapshot binds active structure, definition values, evidence projection,
memory classification identity and algorithm version. Definition and evidence
axes share source identity but retain independent numerators, denominators and
status.

### D002 - Optional Weights, No Formula Language

Criteria carry a bounded numeric weight defaulting to one and one enumerated
evaluation kind. The first schema supports current deterministic completion and
declared-evidence semantics. No expressions, scripts or provider callbacks are
allowed in packs.

### D003 - Not Configured Is Not Zero

When no active applicable criterion exists, readiness is unavailable by design.
Returning zero would imply failure; returning 100 would imply completion. The
contract therefore publishes `not_configured` and null ratios.

### D004 - Classification Is A Sibling Contract

Unassigned and reassignment counts are visible in project snapshots and user
guidance, but cannot enter the readiness formula. This permits legitimate score
changes after structure retirement without hiding organizational work.

### D005 - Derived Cache Is Disposable

The service may persist an internal derived cache for performance, keyed by all
source revisions and algorithm version. Reads can rebuild it and canonical
truth remains structure plus project memory. No CLI read writes merely to refresh
the cache.

### D006 - Converge Existing Readiness Services

Refactor project maturity, progress, review and gap services around shared
criterion and source-snapshot components. Proposal readiness remains separate.
Compatibility aliases that preserve old domain/orphan semantics are removed.

### D007 - Readiness Reads Do Not Manufacture Mutation Authority

Project and section readiness are deterministic reads. They remain protected by
the calling transport or application but do not carry a governed-mutation
AuthorityContext. A future persisted override must use a separate explicit
capability contract; it cannot be represented as a read option or cache write.

## Public Contract

`p2p-project-readiness/v2` contains:

- contract and algorithm versions;
- structure and memory identity;
- overall status;
- definition and evidence axes;
- section results;
- bounded project/section gaps, diagnostics and actions.

`p2p-memory-classification/v1` is returned as a sibling by project snapshot and
its dedicated command.

## Error And Freshness Model

Malformed canonical structure is an error, not partial readiness. Missing or
bounded derived evidence can produce partial/stale status with diagnostics.
Different structure revisions are explicitly incomparable but individually
valid. Algorithm changes invalidate derived cache and projection identity.

## Alternatives Considered

- One combined score: rejected because definition, evidence and organization
  answer different questions.
- Penalize customization versus origin: rejected because origin is analytical.
- Persist readiness as manually refreshed truth: rejected because it risks
  stale canonical state and unnecessary mutations.

## Compatibility

This is a breaking project-readiness contract in P2P Engine 0.5.0. The global
CLI envelope can remain v1, while the domain payload advances to v2. WaveKit and
other machine consumers must pin and validate the new contract.

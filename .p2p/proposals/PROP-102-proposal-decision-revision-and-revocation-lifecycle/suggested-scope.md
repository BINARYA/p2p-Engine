# Suggested Scope

## Include

- versioned decision-event and effective-state domain models;
- explicit transition matrix and lifecycle authority policy;
- initial rejection, withdrawal, revocation, supersession and narrowly defined
  reinstatement semantics;
- preview, owner authority, consent, idempotency, stale checks, locking,
  atomicity and recovery;
- migration and compatibility for current single-decision proposal artifacts;
- CLI and permission-gated MCP parity;
- validation, diagnostics and repair guidance;
- project status, registries, decision context, vertical evidence, conflicts,
  Change Sets, Work, software specs, next actions and publication impact;
- tests for every transition and affected consumer;
- a stable authority and lineage contract for later memory consolidation.

## Exclude

- automatic source-code rollback;
- automatic cancellation or completion of Change Sets and Work;
- physical deletion of decided proposals;
- thematic decision-memory compaction;
- persistent decision-context caching;
- publication curator redesign;
- provider-specific remote orchestration.

## Suggested Delivery Slices

1. Domain vocabulary, transition matrix and authority contract.
2. Versioned event persistence, projection, preview and atomic mutation.
3. Legacy compatibility and forward migration.
4. CLI and permission-gated MCP operations.
5. Downstream consumer convergence and impact diagnostics.
6. Validation, recovery, documentation and full regression evidence.

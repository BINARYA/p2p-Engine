# Execution Plan - PROP-101

## Delivery Principle

Implement the feature as nine gated slices. No repository migration or pilot write begins until schema dispatch, legacy mapping, authority and multi-target failure-injection gates pass. Each slice produces a stable core contract before adding CLI or MCP adapters.

## S1 - Gap Contracts, Snapshot And Priority

### Work

- Introduce immutable convergence snapshot and source-access accounting.
- Define versioned gap, question reference, authority, pagination and result models.
- Separate declared evidence, heuristic suggestions, definition status and question applicability.
- Implement six-class priority with deterministic section/id tie-breaking.
- Preserve existing readiness review text/JSON compatibility.

### Gate

- Repeated and reversed-input builds are identical.
- Definition/evidence axes remain independent.
- One source discovery/read/hash/parse occurs per snapshot.
- Default output is bounded.

## S2 - Schema Status And Transition Handler Architecture

### Work

- Extend workspace status to distinguish v0 undeclared, v1 upgradeable, v2 current, ahead, invalid and recovery-required.
- Add transition-handler protocol owning inventory interpretation, inputs, targets, candidates and validators.
- Dispatch every adjacent transition through its handler.
- Compose multi-step transitions over candidate workspace overlays.
- Preserve current legacy-to-v1 behavior behind its own handler.

### Gate

- A synthetic v1-to-v2 transition does not emit legacy-to-v1 domain, permission, metadata or vertical operations.
- Multi-step plan fingerprints are deterministic.
- Runtime inspect/plan/apply support is reported per transition.
- Existing v0-to-v1 fixtures remain green.

## S3 - Schema-v2 Question Artifact And Legacy Migration

### Work

- Define the engine-owned project-question artifact schema and validator.
- Implement stable identity, revisions, history, apply references and semantic hashing.
- Define fresh-v2 initialization and active-vertical seeding behavior.
- Register `workspace-v1-to-v2` and its transition handler.
- Map v1 definition open questions to v2 records.
- Select declared/fallback questions for incomplete required sections lacking legacy questions.
- Normalize every legacy definition `open_questions` list to empty in the same migration transaction and disable those legacy patch operations under v2.

### Gate

- Every valid legacy question is represented exactly once.
- Absence never creates answered/applied state.
- Ambiguous or malformed mapping blocks with typed diagnostics and no writes.
- v2 validation rejects non-empty definition `open_questions` and no compatibility shadow remains.
- Unknown artifacts are preserved.
- Plan/apply/retry/rollback/recovery/stale-plan fixtures pass.

## S4 - Selection, Lifecycle, Authority And Reconciliation

### Work

- Implement declared question precedence and deterministic fallback/no-safe behavior.
- Implement steady-state transition matrix and reopen event.
- Resolve actor role, provided-by, recorded-by, consent and reason requirements centrally.
- Prevent free-form source/actor values from manufacturing owner authority.
- Reconcile wording revisions, semantic replacements, removed targets and profile/module changes.

### Gate

- Every incomplete required section has a question or diagnostic.
- Invalid and unauthorized transitions write nothing.
- Wording-only changes preserve identity/state.
- Semantic changes supersede without copying answers.
- Removed targets preserve history and become inapplicable.

## S5 - Governed Multi-Target Convergence

### Work

- Extract or expose pure definition candidate rendering and validation.
- Render definition and question candidates from one snapshot.
- Produce semantic diff and affected-gap/freshness preview.
- Commit both targets through one `AtomicMutationWriter` transaction.
- Return final hashes and apply references.

### Gate

- No sequential canonical definition/question commits exist.
- Failure injection at journal, validation and every replacement point proves rollback or explicit recovery.
- Applied question and definition commit invariants are checked by candidate validation and post-commit validation.

## S6 - Preview Retry, Concurrency And Hash Discipline

### Work

- Bind preview tokens explicitly to actor, source preimages, lock, both candidates and policies.
- Exclude audit-only timestamps and observation fields from semantic hashes.
- Record apply operation/token/final hashes in question history.
- Return `already_applied` for exact committed retries.
- Reject divergent replay and serialize concurrent apply under lock.

### Gate

- Response-loss retry is deterministic.
- Same token with changed actor/source/candidate is rejected.
- Concurrent apply produces one commit and one typed retry/stale result.
- Rolled-back and recovery-required states follow documented retry rules.

## S7 - Operational And Decision-Context Integration

### Work

- Feed one convergence result into managed next actions.
- Add stable kind/target deduplication and avoid review self-loops.
- Preserve definition/evidence progress axes and descriptive question counts.
- Add question-only and definition-apply freshness dependencies.
- Register dedicated project-question Source Catalog kind and inactive extraction/activation policy.

### Gate

- Pending answers cannot become active decisions, constraints or relations.
- Applied definition is not double-counted through question history.
- Deferred/muted state suppresses re-ask but retains residual gap.
- Publication/curation/owner stages remain separate.

## S8 - CLI, Pagination And MCP Reads

### Work

- Add structured gap/detail and question lifecycle CLI operations.
- Add reconcile, preview/apply and actionable schema-gate diagnostics.
- Define default/max page size and opaque snapshot-bound cursor.
- Return `stale_cursor` after source drift.
- Add MCP read parity only after CLI/core payload stabilization.

### Gate

- Existing readiness review remains compatible.
- Text and JSON defaults are bounded.
- Cursor continuation is stable and stale cursors fail explicitly.
- CLI and MCP read payloads are semantically equivalent.
- No MCP mutation logic is introduced.

## S9 - Compatibility Matrix, Robustness And Repository Pilot

### Work

- Publish operation-level v1/v2 minimum-schema matrix.
- Test v1-safe writes and v2-dependent zero-write blocks through the common boundary.
- Build synthetic vertical, empty workspace, no-coverage, 100-proposal and malformed migration fixtures.
- Run focused and full test suites plus global validation.
- Plan and apply this repository's v1-to-v2 migration through supported commands.
- Exercise assumptions, decisions and risks/alternatives/decisions gaps through answer/apply or defer/mute.
- Compare progress, next actions, freshness, decision context and source-access metrics before/after.

### Gate

- Repository operation requires no manual `.p2p` edits.
- Migration lock/recovery state is clear.
- No unexplained validation warning or derived authority change remains.
- Residual gaps and owner-controlled work are reported explicitly.

## Cross-Cutting Verification

- Unit tests for every enum, transition, identity and mapping rule.
- Service tests for stale snapshots, authority, candidate closure and exact retry.
- Failure injection for every multi-target replacement point.
- CLI golden tests for bounded text/JSON and schema diagnostics.
- MCP contract tests for read parity and absence of write tools in the first release.
- Access-count and payload-size tests for the 100-proposal fixture.
- Documentation and generated-agent-template drift tests.

## Adoption Boundary

Acceptance of the proposal authorizes later feature specification, not implementation or repository migration. Implementation must be represented by an accepted Change Set and follow the software specification lifecycle. Repository v1-to-v2 adoption remains a separate owner-confirmed migration apply.

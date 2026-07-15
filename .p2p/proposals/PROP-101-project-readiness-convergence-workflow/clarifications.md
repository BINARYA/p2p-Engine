# Clarifications - PROP-101

## Applied Owner Answers

### Q001 - Canonical Project-Question Authority

Status: resolved and incorporated.

- Use a dedicated project-scoped question lifecycle artifact.
- It is authoritative for project-question status, owner answers, revisions and history.
- Project definition remains authoritative only for content committed through owner-reviewed preview/apply.
- Legacy definition open questions are fallback evidence only while structured project-question state is absent.

Consequences: recording an answer cannot mutate definition; schema v2 must eliminate parallel writable authority; validation reports divergence rather than merging by last-write-wins.

### Q002 - Workspace Schema Compatibility And Upgrade

Status: resolved and incorporated.

- Preserve backward compatibility with workspace schema v1.
- Define workspace schema v2 as an explicit upgrade target.
- Require deterministic v1-to-v2 plan and owner-confirmed transactional apply.
- Require idempotency and recovery through existing migration primitives.
- Never migrate implicitly.

Consequences: feature specifications define v1/v2 runtime support, fresh-workspace behavior, migration fixtures and operation-level schema dependencies.

### Q008 - Unmigrated Schema-v1 Write Mode

Status: resolved and incorporated.

- Keep every read and governed write available when its canonical contract remains valid under v1.
- Block only operations requiring v2 state or semantics.
- Perform no partial write when a schema gate blocks.
- Report current/required versions, reason and exact migration plan command.

Consequences: minimum schema classification belongs in a common governed-write boundary, not scattered CLI handlers.

### Q003 - Fallback Question Policy

Status: resolved and incorporated.

- Use an applicable question declared by the active locked vertical first.
- Otherwise generate only a conservative deterministic fallback from declarative metadata.
- Version fallback policy and stable identity.
- Never let a fallback answer owner input, validate assumptions or complete a section.
- Emit `no_safe_question` when safe generation is impossible.

### Q004 - Gap Priority Policy

Status: resolved and incorporated.

1. Integrity, compatibility and authority blockers plus explicit owner-decision blockers.
2. Owner answers received but not yet applied.
3. Incomplete required definition sections.
4. Assumptions ordered by declared dependency impact.
5. Optional declared-evidence curation.
6. Informational legacy state.

Within a class, use vertical section priority and stable gap/question id. Expose rationale and tie-break inputs.

### Q005 - Post-Apply Freshness And Rebuild

Status: resolved and incorporated.

- Atomically update only directly involved project-definition and project-question canonical state.
- Complete candidate validation before replacement.
- Report dependent derived nodes as stale and return their topological rebuild plan.
- Do not execute refresh, curation, publication or owner review automatically.

### Q006 - MCP Write Scope

Status: resolved and incorporated.

- Stabilize core service and CLI mutation contracts first.
- Add MCP read parity after structured payload stabilization.
- Defer MCP answer/apply tools to a later gated slice.
- Require later MCP writes to delegate to the complete permission, preview, stale-detection, authority, transaction and result path.

### Q007 - Pilot Exit Meaning

Status: resolved and incorporated.

- Permit governed `deferred` or `muted` outcomes when evidence is unavailable or the owner declines the question.
- Require actor, reason, timestamp, provenance and reopenability.
- Deferred re-eligibility requires a declared trigger or owner reopen.
- Muted questions remain excluded until explicit owner action.
- Preserve the underlying partial, assumed or blocked state and residual gap.

## Applied Robustness Refinements

The owner requested incorporation of every refinement from the post-definition code audit. These are technical hardening contracts and do not change Q001-Q008.

### R001 - Transition-Specific Migration Planning

Schema v2 requires a registered v1-to-v2 transition handler, not only registry metadata. Each adjacent handler owns candidate targets, owner inputs and validators. Candidate overlays compose handlers in order. The v1-to-v2 handler cannot replay v0-to-v1 domain, permission, metadata or vertical bootstrap.

### R002 - Legacy Question Mapping

Migration preserves every valid legacy open question exactly once with section-scoped identity and `to_answer` state. It never infers an answer or applied state from absence. Ambiguous ids, fields, sections, statuses or texts block lossy migration. Incomplete required sections without a legacy question use declared/fallback selection. The same transaction normalizes definition `open_questions` to empty; v2 validation prevents their reintroduction and no compatibility shadow remains.

### R003 - One Multi-Target Apply

Definition and question candidates commit through one durable transaction. Existing definition parsing and validation are reused as pure logic; the single-target definition apply is not followed by a second canonical write. Compensating rollback between independent commits is excluded.

### R004 - Operation Authority Matrix

Every lifecycle mutation defines allowed source/target states, role, consent, reason, provenance and side effects. Owner answers distinguish `provided_by` from `recorded_by`. A caller-provided actor or `source=owner` is insufficient authority.

### R005 - Retry And Replay

Preview tokens bind actor, both source preimages, lock, candidates and policies. Exact retry after a successful commit returns `already_applied`; changed reuse is rejected. Time expiry is deferred until a durable receipt contract exists. Audit timestamps do not participate in semantic hashes.

### R006 - Vertical Reconciliation

Wording-only changes preserve identity and state as a new revision. Semantic target changes supersede. Removed targets retire. Answers are never copied to a changed target automatically. Lock changes invalidate outstanding previews.

### R007 - Decision-Context Authority

Project-question state is indexed as inactive metadata or pending evidence. It cannot create active decisions, constraints or relations. Applied definition remains the sole semantic project-definition authority, with traceability back to the question.

### R008 - Snapshot Pagination And Performance

Cursors bind to snapshot fingerprint and fail with `stale_cursor` after source drift. Scale acceptance uses deterministic discovery/read/hash/parse and payload budgets, with wall-clock timing only as supporting evidence.

## Remaining Owner Questions

None. Any implementation discovery that requires changing these owner policies must create a new focused question instead of selecting a hidden default.

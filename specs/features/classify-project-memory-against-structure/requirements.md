# Requirements - Classify Project Memory Against Structure

## Scope

Make structural classification an explicit property of active project memory.
Proposals and other supported memory objects may target active sections, the
project globally, or remain intentionally unassigned while work is incomplete.
A separate memory-classification read model reports organizational state without
altering project readiness.

## Origin

- Source: owner-approved permissive-empty and memory-classification review.
- Target train: P2P Engine `0.5.0`.
- Depends on: `introduce-project-owned-structure` and
  `support-typed-authority-context-in-governed-mutations`.

## In Scope

- `ProjectMemoryScope` with `sections`, `project_global` and `unassigned`.
- Multi-section proposal scope.
- Proposal creation in an empty project.
- Decision gate requiring explicit section or global scope.
- Scope assignment/reassignment as receipt-backed mutations.
- Derived `MemoryClassificationSnapshot` with counts and blocking state.
- Explicit treatment of active, historical and retired-target references.
- Read, output, CLI, MCP and generated-agent representation.

## Out Of Scope

- Automatic AI classification.
- Readiness score penalties for unassigned content.
- Section retirement and impact resolution.
- WaveKit inbox, UI actions or authorization.
- A generic free-form tagging system.

## Public Surface And MCP Impact

- CLI impact: breaking replacement of vertical-coverage-only semantics with a
  versioned project-memory scope contract; additive classification reads.
- MCP impact: read parity and consent-gated scope mutation parity are required.
- Storage impact: current-only scope schema and derived classification index.
- Agent-facing behavior: agents must distinguish unassigned from intentionally
  global content and must not treat either as section evidence.

## Functional Requirements

### Scope Model

- R001: An active classifiable memory object SHALL have exactly one normalized
  scope kind: `sections`, `project_global` or `unassigned`.
- R002: Section scope SHALL contain one or more unique active section IDs.
- R003: Project-global scope SHALL be explicit and SHALL NOT be inferred merely
  because section IDs are absent.
- R004: Unassigned scope SHALL represent incomplete organization rather than an
  invalid or global object.
- R005: Historical objects MAY preserve references to retired sections without
  being classified as active unassigned work.

### Proposal Workflow

- R006: Proposal creation SHALL succeed with unassigned scope even when the
  current project structure has zero active sections.
- R007: A proposal SHALL be assignable to multiple active sections through one
  atomic scope mutation.
- R008: A proposal SHALL be assignable explicitly to project-global scope.
- R009: Draft, pending and otherwise non-authoritative proposals MAY remain
  unassigned.
- R010: A proposal decision that would create active authority SHALL fail until
  the proposal has active section scope or explicit project-global scope.
- R011: Rejected, revoked and archived proposal history SHALL remain readable
  without creating current classification debt.
- R012: Scope changes SHALL not rewrite proposal narrative or decision history.

### Other Memory Families

- R013: The feature SHALL define a documented applicability matrix for formal
  questions, evidence and artifacts that can reference structure.
- R014: Any supported active object with no required scope SHALL be counted as
  unassigned; unsupported memory families SHALL remain unchanged explicitly.
- R015: Active objects that reference only retired sections SHALL be classified
  as `requires_reassignment`, not silently unassigned or valid.

### Classification Snapshot

- R016: The system SHALL expose a side-effect-free
  `MemoryClassificationSnapshot` separate from readiness.
- R017: Snapshot status SHALL be one of `complete`, `incomplete`,
  `not_applicable`, `unknown` or `stale`.
- R018: Snapshot SHALL bind structure revision, memory revision and structure
  checksum.
- R019: Snapshot SHALL report bounded totals for section-classified,
  project-global, unassigned, requires-reassignment and decision-blocking
  objects, including supported per-type counts.
- R020: Historical, rejected, revoked and archived objects SHALL not increase
  current unassigned or decision-blocking counts.
- R021: Empty project with no classifiable active memory SHALL report
  `not_applicable`; empty project with unassigned active memory SHALL report
  `incomplete`.

### Mutation Contract

- R022: Scope assignment SHALL require typed authority context, operation key,
  expected memory revision and expected structure revision.
- R023: Assignment to sections SHALL validate every target against one current
  structure snapshot.
- R024: Scope mutation and receipt SHALL commit atomically and support status,
  exact replay and divergent-key conflict.
- R025: Public results SHALL report logical scope and revisions without paths or
  raw operation keys.

### Output And Read Models

- R026: Project snapshots and publications SHALL preserve global and unassigned
  content in explicit collections rather than omit them.
- R027: Unassigned and global content SHALL not count as section evidence.
- R028: Classification status SHALL never reduce, increase or otherwise alter a
  readiness score.

### Governed Capability Contract

- R029: Scope assignment SHALL declare capability `project.memory.classify` and
  bind the exact authority context to preview, apply, event and receipt.
- R030: The authority-creating proposal decision gate SHALL remain separate
  from classification authority: decision apply requires `proposal.decide`,
  and any readiness override additionally requires
  `proposal.readiness.override`.
- R031: P2P local policy SHALL preserve standalone owner rules; hosted
  delegability is supplied through the typed external authority contract and
  this feature SHALL NOT import provider memberships or grants.

## Non-Functional Requirements

- N001: Classification reads SHALL be deterministic, bounded and side-effect
  free.
- N002: Scope mutation SHALL reuse existing transactions and receipts.
- N003: Classification indexing SHALL scale linearly with bounded active memory
  and support incremental refresh where the current memory projection does.
- N004: Public payloads SHALL use stable IDs and omit internal paths.
- N005: The implementation SHALL not introduce WaveKit-specific roles or
  persistence concepts.

## Edge Cases And Errors

- Empty project with first unassigned proposal.
- Assignment to duplicate, unknown or retired sections.
- Clearing section scope without selecting global or unassigned explicitly.
- Decision apply against an unassigned proposal.
- Retired-section historical proposal versus active proposal.
- Stale structure or memory revision.
- Classification projection truncated, corrupt or ahead of canonical state.
- Lost response and exact/divergent retries.

## Acceptance Criteria

- AC001: An empty project can create and read an unassigned proposal.
- AC002: One proposal can be assigned atomically to multiple active sections.
- AC003: An unassigned proposal cannot receive an authority-creating decision;
  explicit global or active-section assignment unblocks it.
- AC004: Classification reports accurate active counts and excludes historical
  terminal content.
- AC005: Readiness is unchanged when only classification state changes.
- AC006: Active references to retired sections appear as
  `requires_reassignment`.
- AC007: CLI, MCP, project snapshots and publications expose global and
  unassigned content consistently.
- AC008: Scope replay, conflicts and concurrent structure changes are safe.
- AC009: A classification authority context cannot authorize a proposal
  decision or readiness override, and each receipt names its exact capability.

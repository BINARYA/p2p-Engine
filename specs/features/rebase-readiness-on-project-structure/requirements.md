# Requirements - Rebase Readiness On Project Structure

## Scope

Replace overlapping domain-, vertical- and definition-based readiness semantics
with one authoritative project-readiness contract derived from the current
active project structure and current project memory. Keep definition maturity,
evidence coverage and memory classification as distinct dimensions.

## Origin

- Source: owner-approved readiness and classification separation.
- Target train: P2P Engine `0.5.0`.
- Depends on: `introduce-project-owned-structure`,
  `classify-project-memory-against-structure`, retirement lifecycle and the
  read/mutation boundary from
  `support-typed-authority-context-in-governed-mutations`.

## In Scope

- Versioned `ProjectReadinessSnapshot` bound to structure and memory identity.
- Active criteria with optional positive weights defaulting to one.
- Definition-completeness and declared-evidence axes.
- Project and section states, gaps and actionable guidance.
- Explicit zero-criteria `not_configured` behavior.
- Algorithm version and deterministic source identity.
- Separate `MemoryClassificationSnapshot` in related reads.
- Convergence/removal of obsolete domain maturity and orphan-rubric behavior.

## Out Of Scope

- Penalizing readiness for unassigned content.
- Cross-project comparability or public ranking by readiness.
- User-supplied executable scoring expressions.
- Automatic mutation merely to refresh a read model.
- Proposal-specific readiness redesign.
- WaveKit presentation and projection persistence.

## Public Surface And MCP Impact

- CLI impact: breaking project-readiness payload convergence; reads remain
  side-effect free.
- MCP impact: read-only parity is required; no generic readiness mutation is
  introduced.
- Storage impact: structure criteria gain optional weight/evaluation metadata;
  current derived snapshots may be cached but remain reconstructible.
- Agent-facing behavior: guidance must explain axes, source revisions,
  classification separation and `not_configured`.

## Functional Requirements

### Source Of Truth

- R001: Project readiness SHALL use only active criteria in the current
  `ProjectStructure` revision.
- R002: Domain and structure origin SHALL NOT add criteria, penalties or
  conformity requirements.
- R003: Retired sections and criteria SHALL not contribute to any active
  readiness denominator.
- R004: A readiness result SHALL bind structure revision, structure checksum,
  memory revision and readiness algorithm version.
- R005: Reads against unchanged canonical state and algorithm SHALL be
  deterministic.

### Criteria And Weighting

- R006: Every active criterion SHALL have a positive bounded weight, defaulting
  to `1` when omitted.
- R007: The scoring schema SHALL support only declared deterministic evaluation
  kinds; it SHALL reject executable expressions or unknown evaluators.
- R008: Definition completeness SHALL calculate satisfied active weight divided
  by total applicable active weight.
- R009: Evidence coverage SHALL remain a separate axis and SHALL not be averaged
  implicitly into definition completeness.
- R010: A criterion marked not applicable through a supported governed state
  SHALL be excluded from numerator and denominator with traceable rationale.

### Status And Sections

- R011: Zero applicable active criteria SHALL produce status `not_configured`
  and no numeric score.
- R012: Configured readiness status SHALL distinguish `calculated`, `partial`,
  `stale` and `error` where source completeness requires it.
- R013: Section results SHALL expose active/applicable weight, satisfied weight,
  status and bounded gaps without fabricating unavailable percentages.
- R014: Project-level gaps SHALL reference stable structure or memory IDs and
  SHALL not expose physical paths.
- R015: Unassigned or project-global content SHALL not count as section evidence.
- R016: Active references requiring reassignment SHALL appear in memory
  classification and MAY produce guidance, but SHALL not alter the readiness
  score formula.

### Public Contract

- R017: Project readiness reads SHALL expose contract version, source identity,
  status, definition axis, evidence axis, sections, gaps, diagnostics and
  bounded actions.
- R018: Related project snapshot reads SHALL expose readiness and
  `memory_classification` as independent sibling objects.
- R019: Readiness reads SHALL perform no persistent mutation.
- R020: An implementation cache SHALL be invalidated by relevant structure,
  memory or algorithm identity changes and SHALL never become canonical state.
- R021: The contract SHALL permit callers to identify incomparable snapshots
  from different structure revisions without declaring one invalid.

### Convergence

- R022: Obsolete domain-rubric maturity SHALL be removed from current project
  readiness behavior.
- R023: Origin-pack orphan rubrics SHALL not survive merely to preserve a former
  readiness denominator.
- R024: Project progress, readiness review and gap commands SHALL share one
  structure snapshot and one criterion interpretation.
- R025: Generated guidance SHALL distinguish project readiness, proposal
  readiness and memory classification.

### Authority And Capability Boundary

- R026: Project and section readiness review/gap operations in this feature
  SHALL remain side-effect-free reads and SHALL NOT require a governed-mutation
  capability or fabricate an AuthorityContext.
- R027: Any future persisted readiness override SHALL be a separately specified
  governed mutation using `proposal.readiness.override` or another exact
  registry capability; it SHALL NOT be smuggled into a readiness read.

## Non-Functional Requirements

- N001: Readiness reads SHALL be side-effect free, bounded and deterministic.
- N002: Calculation SHALL have bounded linear behavior over active structure and
  indexed relevant memory.
- N003: The algorithm version SHALL change whenever scoring semantics change.
- N004: Public output SHALL be safe for logs after caller authorization and
  SHALL omit internal paths and raw source contents.
- N005: Calculation services SHALL remain independent from CLI, MCP and WaveKit.

## Edge Cases And Errors

- Empty structure or all criteria retired/not applicable.
- Missing optional weight versus zero, negative or oversized weight.
- Unknown criterion evaluator.
- Structure changes between related readiness reads.
- Active proposal is global, unassigned or points to retired structure.
- Partial or truncated evidence projection.
- Cache identity behind or ahead of canonical revisions.
- Algorithm version changes with unchanged memory.

## Acceptance Criteria

- AC001: Removing or retiring criteria changes the denominator immediately and
  no origin criterion remains hidden in the calculation.
- AC002: Zero criteria returns `not_configured` and `score: null`.
- AC003: Weighted definition completeness and separate evidence coverage match
  deterministic fixtures.
- AC004: Memory-classification counts do not change readiness scores.
- AC005: Section and project gaps reference only current stable IDs or explicit
  project-level targets.
- AC006: Snapshot identity includes structure revision/checksum, memory revision
  and algorithm version.
- AC007: CLI, MCP and project snapshot contracts are semantically consistent.
- AC008: Domain maturity and orphan-rubric compatibility paths are absent from
  the current runtime.
- AC009: Readiness review/gap calls remain read-only and produce neither a
  mutation receipt nor an invented mutation authority context.

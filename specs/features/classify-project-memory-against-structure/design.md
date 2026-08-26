# Design - Classify Project Memory Against Structure

## Requirements Covered

- R001-R031
- N001-N005
- AC001-AC009

## Decision Summary

Replace absence-based vertical coverage with explicit `ProjectMemoryScope`.
Proposal scope is authoritative and supports multiple sections, global project
scope and unassigned work. A separate derived classification snapshot reports
organizational completeness. It is never folded into readiness.

## Key Decisions

### D001 - Absence Is Not Global

Every classifiable active object normalizes to a tagged scope. Existing proposal
creation defaults to `unassigned`; only an explicit mutation creates
`project_global` or `sections`. This prevents accidental authority outside the
structure.

### D002 - Decisions Require Explicit Scope

Draft and pending proposals may remain unassigned. An authority-creating
decision validates current scope in the same source snapshot and fails with a
typed blocker when it is unassigned or requires reassignment. Rejection or
archival that creates no active project contribution may preserve unassigned
history.

### D003 - Classification Is A Separate Derived Axis

`MemoryClassificationSnapshot` is not readiness and has no composite score.
Counts are more interpretable than a percentage and avoid treating all content
as equal. The snapshot is bound to both memory and structure identity.

### D004 - Retired References Remain Typed

Historical references retain their retired section IDs. Active references to
retired sections are `requires_reassignment`; they are not rewritten by reads.
The retirement feature supplies explicit dispositions and atomic updates.

### D005 - Project Memory Replaces Structural Authority

The project-structure classification index owns section, global, unassigned and
reassignment semantics. Canonical proposal, decision, scope and formal-question
artifacts remain sources of truth. The pre-rebase vertical-memory projection
may remain as a temporary readiness/publication consumer, but it cannot supply
scope, satisfy classification or pass the decision gate. Its final replacement
belongs to the dependent `rebase-readiness-on-project-structure` feature so the
repository remains executable between ordered plan steps.

### D006 - Versioned Public Contract

Scope uses `p2p-project-memory-scope/v1`; classification uses
`p2p-memory-classification/v1`. The old `vertical_coverage` contract is removed
from structural authority in the current-only schema-4 runtime. Its temporary
pre-rebase read surface is explicitly non-authoritative and is removed when the
readiness services converge on ProjectStructure; it is not accepted as a
fallback for missing scope.

### D007 - Classification And Decision Authority Stay Separate

Scope mutation declares `project.memory.classify`. The downstream gate that
permits an authority-creating proposal decision is not classification
authority: decision apply separately resolves `proposal.decide`, and readiness
override separately resolves `proposal.readiness.override`. All three use the
shared AuthorityContext, preventing a classification grant from becoming a
decision grant by implication.

## Applicability Matrix

- Proposals: full section/global/unassigned lifecycle.
- Formal questions: section/global/unassigned when they are project-level and
  active; proposal-local questions inherit proposal identity and do not create
  a second independent scope.
- Evidence: preserve explicit section/global scope; unassigned evidence is not
  counted as readiness evidence.
- Expected artifacts: structural declarations live in ProjectStructure;
  produced artifact instances use section/global/unassigned where applicable.
- Historical decisions: retain the proposal scope snapshot needed to explain
  past authority.

The implementation inventory may narrow unsupported legacy families only by
documenting the exclusion and proving they cannot become hidden active memory.

## Components And Ownership

- Core scope and classification contracts.
- Proposal scope repository and receipt-backed mutation service.
- Decision service scope gate.
- Project-structure memory projection and incremental invalidation.
- Project snapshot/publication renderers.
- CLI and MCP scope/classification handlers.
- Agent capability and guidance updates.

## Error And Concurrency Model

Scope planning captures proposal/object fingerprint, memory revision, structure
revision and target section set. Apply validates them under the workspace lock.
An intervening structure change or object update produces conflict before any
scope write. Receipt replay is independent from later classification drift.

## Alternatives Considered

- Continue treating missing coverage as a gap only: rejected because empty
  projects and global content remain ambiguous.
- Create a fake `miscellaneous` section: rejected because it pollutes readiness
  and hides incomplete organization.
- Penalize readiness for unassigned content: rejected because readiness and
  organization answer different questions.

## Compatibility

The feature is schema-4-only. Existing `vertical_coverage` artifacts are not
accepted as scope by runtime 0.5.0 and cannot satisfy classification or the
decision gate. The temporary reader needed by the not-yet-rebased readiness
service is deleted by the ordered readiness feature, not maintained as a
historical-memory compatibility path. Test fixtures use the new explicit scope
format.

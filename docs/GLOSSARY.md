# Glossary

This glossary defines the core P2P Engine terms used in the README, CLI guide,
MCP guide, and generated project artifacts.

## Agent

An AI or automation actor that reads project context and may perform bounded
work. Agents should use CLI or MCP primitives and must not edit `.p2p/` internals
by hand.

## Change Set

An operational package derived from accepted project intent. A Change Set
connects governance state to implementation planning, tasks, specs, and managed
work metadata.

## Choice

An explicit decision point with two or more alternatives. Choices are useful when
the project needs to compare options rather than simply accept or reject one
proposal.

## Context Packet

A compact, token-aware summary of project state for agents. `p2p context` and
`p2p_context` are intended to be used before broad file reads.

## Contribution

A typed addition to a proposal, such as a finding, open question, alternative,
risk, assumption, constraint, objection, implementation suggestion, or scope
boundary. Contributions preserve review input without rewriting the proposal
body.

## Artifact Status

The logical proposal artifact catalog. It describes expected proposal components,
their status, materialization, source/evidence hints, provenance confidence, and
next actions without requiring every possible artifact to exist as a file.

## Decision

An owner-controlled governance event. Proposal decision history is append-only
in workspace schema v4; the current effective state is reduced from the event
chain. Choice decisions remain a separate lifecycle.

## Rejection

An initial terminal proposal decision for a direction that was never active. A
rejected proposal is reconsidered through a new linked proposal rather than by
rewriting its history. Decision status exposes the supported creation command
without creating the replacement automatically.

## Revocation

An event that closes the active authority of a previously accepted proposal.
It preserves the original decision, rationale, authority interval and dependent
artifact history. It does not cancel or rewrite Change Sets, Work, specs, code,
vertical evidence or publication state.

## Reinstatement

An explicit owner decision that reopens authority from a prior accepted event
after its matching revocation. Reinstatement does not restore technical state
automatically; affected dependencies remain reviewable.

## Decision Event Ledger

The canonical schema-4 `decision-events.yml` chain for one proposal. Events
bind predecessor, operation key, proposal/decision fingerprints, authority,
lineage and impact evidence. `proposal.md` status and `decision.md` are derived
projections, not independent authority.

## Export Target

A downstream-oriented software-spec handoff generated from a P2P-native
software spec. Current compatibility targets include generic, OpenSpec, and
Spec Kit initialization outputs. This is distinct from the visible project
definition produced by `p2p project export`.

## Publication Edition

One language-specific human rendering of the same project scope. Its immutable
identity is `(output_name, canonical_language)`, expressed as an edition key
such as `project-en`. Markdown, PDF, freshness, and owner review are isolated
from other editions.

## Publication Evidence Index

A shared derived index of complete, vertical-aware project evidence used by all
publication editions. It classifies current, cross-cutting, historical,
contradictory, insufficient, contribution, and process-only material without
turning the generated index into canonical project authority.

## Publication Project Model

The traceable editorial sidecar connecting reader questions, claims, evidence,
adaptive outline, vertical coverage, and editorial self-assessment. Together
with exact evidence accounting, it lets the final reader document remain free
from internal workflow IDs and paths.

## Governance

The project authority boundary around intent, decisions, and lifecycle state.
P2P Engine can store and validate governance artifacts, but the owner decides.

## Intake

An advisory workflow for raw ideas. Intake helps analyze overlap, possible
actions, and related artifacts before turning messy input into proposals,
contributions, choices, or deferred work.

## Maturity Assessment

A deterministic check of project definition coverage against configured rubrics.
It measures whether the project definition has enough explicit intent; it is not
implementation completeness.

## Owner

The human or accountable authority that decides governance outcomes. Agents may
suggest, draft, or analyze, but owner decisions require explicit instruction.

## Proposal

A structured candidate direction for the project. A proposal usually records the
problem, context, goals, non-goals, proposed direction, and acceptance criteria.

## Proposal Full View

An explicit owner-facing proposal review view. It combines proposal sections,
decision state, readiness, contributions, grouped question sources, narrative
artifact summaries, artifact status, and next actions without making governance
decisions.

## Registry

A generated index over P2P artifacts such as proposals, decisions, relations,
changes, and other project state. Registries are refreshed from source artifacts.

## Vertical Project Memory

A deterministic, compact, section-oriented read model derived from the active
project vertical, definition, questions, proposal decision authority, declared
coverage, choices and conflicts. It accelerates readiness, context, next actions
and project rendering. It is disposable and rebuildable; `.p2p` canonical
sources remain authoritative. It does not represent implementation status.

## Fast Freshness

A bounded status check over schema preflight and derived bundle manifests. It
reports what was checked without constructing complete validation, decision
context, publication, software specs or the full freshness dependency graph.

## Canonical Fallback

A read-only in-memory reconstruction from canonical sources used when a derived
read model is missing, stale, invalid or unsupported. It does not persist a
cache or silently refresh the workspace.

## Software Spec Freshness

A per-spec semantic comparison between exact authoritative inputs, versioned
generated provenance, and deterministic candidate bytes. It distinguishes
current, compatible legacy, stale source, manually modified output, unknown
origin, and incomplete artifacts without using file age as identity.

## Project Domain

A portable subject-classification descriptor with a free key, display name,
source and optional external reference. It does not own project structure.

## Structure Source

The exclusive initialization source for project structure: the `generic` or
`empty` starter, or one exact vertical release.

## Project Memory Scope

The explicit structural organization of one classifiable memory object. A
proposal has exactly one scope kind: one or more active `sections`,
`project_global`, or `unassigned`. Absence of section IDs never implies global
scope.

## Memory Classification

A bounded, revision-bound projection reporting whether active project memory is
classified, global, unassigned, or requires reassignment. It is separate from
readiness and never modifies readiness scores.

## Rubric

A structure-owned checklist used to assess project definition maturity.
Rubrics make it clear which aspects of intent have or have not been covered.

## Project Vertical

A pure-data pack that describes domain-specific project sections, questions,
fields, artifacts, and default rubrics. Vertical content is domain data; it does
not override system, developer, governance, repository, safety, or permission
rules.

## Vertical Lock

The deterministic `.p2p/project/vertical.lock.yml` record of the selected
vertical source, version, schema version, checksum, actor, and timestamp.

## Project Definition State

The durable `.p2p/project/definition.yml` state for owner answers, assumptions,
open questions, missing fields, blockers, section completion, and provenance.

## Selected Project Rubric Maturity

The maturity score computed from enabled project criteria. It is distinct from
full default vertical baseline coverage.

## Work

Managed metadata for implementation or handoff activity, usually connected to a
Change Set and branch-based workflow. Work metadata does not replace Git history
or code review.

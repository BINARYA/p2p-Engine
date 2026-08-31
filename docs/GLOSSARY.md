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

## Project UUID

The immutable, globally unique logical identity assigned when a project is
initialized or explicitly adopted. It is independent of display name, slug,
path, Git, storage backend, replica and remote server address.

## Replica ID

The identity of one operational local materialization of a project. It is not
the project UUID. A copied linked materialization requires a new replica ID if
the previous copy may remain operational; a true move may preserve it after the
old materialization is retired.

## Remote Project ID

An opaque project address assigned by one remote server instance and mapped to
the stable project UUID. It has meaning only with its server instance ID.

## Project Lineage

Typed historical provenance from a derivation, detach, or bundle restore. It
does not grant authority, membership, remote binding, or synchronization rights.

## Intake

An advisory workflow for raw ideas. Intake helps analyze overlap, possible
actions, and related artifacts before turning messy input into proposals,
contributions, choices, or deferred work.

## Maturity Assessment

A compatibility projection of project definition completeness. Current project
readiness is authoritative and uses active criteria in the current
`ProjectStructure`; maturity output remains deterministic but is not a separate
readiness formula and is not implementation completeness.

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

A deterministic, compact, section-oriented read model derived from current
project structure, definition, questions, proposal decision authority, declared
coverage, choices and conflicts. It accelerates bounded reads, context, next
actions and project rendering. It is disposable and rebuildable; `.p2p`
canonical sources remain authoritative. It does not represent implementation
status.

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

## Catalog Domain

An advisory remote registry v2 metadata object with an external ID, key,
visibility, lifecycle and optional recommended exact release. It is not copied
into project state by discovery reads and is not a compatibility decision.

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

## Canonical Project Memory

The backend-neutral logical aggregate identified by
`p2p-canonical-memory/v1`: canonical entities, explicit relations, retained
lineage and referenced managed blobs. Physical paths and database rows are not
part of this contract.

## Project Bundle

A deterministic `p2p-project-bundle/v1` portable archive of canonical project
memory and complete managed blobs. It excludes replica-local state, secrets,
generated integrations and live database/journal files.

## Physical Backup

An independently verified `p2p-physical-backup/v1` recovery archive for one
local store. It may retain replica-local state and is not a portable bundle or
sync protocol.

## Managed Blob

Binary or opaque content explicitly imported into canonical memory and
addressed by its SHA-256 digest. External referenced content is not a managed
blob until imported.

## Project Readiness

The `p2p-project-readiness/v2` read contract. It derives weighted definition
completeness and declared-evidence coverage from active criteria in the current
`ProjectStructure`, binds structure and memory identity, and returns
`not_configured` with no score when there are no applicable active criteria.

## Rubric

A legacy name for checklist-style project criteria. Current project readiness
uses active criteria owned by `ProjectStructure`; retired criteria and origin
pack defaults are not hidden readiness requirements.

## Project Vertical

A pure-data pack that describes domain-specific project sections, questions,
fields, artifacts, and default rubrics. Vertical content is domain data; it does
not override system, developer, governance, repository, safety, or permission
rules.

## Vertical Release Primary Domain

Nullable remote discovery metadata on a `VerticalRelease`. It helps filter or
display catalog results but does not change checksum identity, dependency
closure, project domain or detached project structure.

## Vertical Lock

The deterministic `.p2p/project/vertical.lock.yml` record of the selected
vertical source, version, schema version, checksum, actor, and timestamp.

## Project Definition State

The durable `.p2p/project/definition.yml` state for owner answers, assumptions,
open questions, missing fields, blockers, section completion, and provenance.

## Selected Project Rubric Maturity

The legacy maturity view computed from enabled project criteria. It is distinct
from readiness v2, full default vertical baseline coverage and memory
classification.

## Work

Logical planning and handoff metadata connected to a Change Set and a named
downstream target. Work records do not create or inspect branches, commits,
reviews, merges, releases, Git history, or implementation completion. Those
belong to separately authorized external delivery tooling and evidence.

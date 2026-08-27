# P2P Concepts

This page is the short operational concept guide for P2P Engine. It explains the
model used by the CLI, MCP server, tutorial, and generated `.p2p/` project
state.

For definitions, see [GLOSSARY.md](GLOSSARY.md). Current implementation
boundaries are documented in
[DEVELOPMENT-GUIDELINES.md](DEVELOPMENT-GUIDELINES.md).

## The Core Loop

P2P Engine preserves a project intent chain:

```text
rough idea
  -> proposal
  -> owner decision
  -> Change Set
  -> generated registries
  -> compact agent context
```

The engine is useful when project direction starts as conversation, notes,
alternatives, or agent output, and needs to become explicit, versioned project
memory.

## Project State Lives In `.p2p/`

P2P Engine stores project governance state under `.p2p/`. Filesystem state is
the runtime boundary; an external source-control system may version it.
Schema 4 stores one project authority descriptor. In standalone mode, local
permissions resolve owner authority. A hosted provider may attest an exact
capability while P2P records the subject and executor separately.

Common artifact areas:

```text
.p2p/
  proposals/    structured candidate directions
  choices/      explicit alternatives and selected outcomes
  changes/      operational Change Sets from accepted intent
  work/         logical planning and handoff metadata
  registries/   generated indexes over project state
  project/      project overview, rubrics, assessments, and next actions
```

Generated registries should be refreshed from source artifacts with:

```bash
p2p registry refresh
```

## Proposal

A proposal is a structured candidate direction. It usually records:

- problem;
- context;
- goals;
- non-goals;
- proposed direction;
- acceptance criteria.

Proposals start as drafts. The owner can accept, reject, or defer them.

## Decision

A decision records an authority-controlled outcome and rationale. Local policy
requires the current owner. External-attestation mode may accept a delegated
`proposal.decide` subject, while readiness override remains root-only. P2P
Engine stores the immutable authority evidence and does not become a hosted
identity or grant service.

Use decisions when the project needs to remember why a direction was selected,
rejected, or postponed.

## Choice

A choice is for explicit alternatives, such as:

```text
CLI-only first
MCP-first
Hosted web app first
```

Choices are better than burying tradeoffs in prose when the project needs a
clear selected option and rationale.

## Change Set

A Change Set turns accepted intent into operational work metadata. It connects
governance state to implementation planning, generated specs, tasks, and managed
work.

Change Sets do not replace implementation, source-control commits or code
review. They explain what work is derived from accepted project intent.

## Work

Work metadata tracks logical implementation planning or handoff around a Change
Set. It can be planned, listed, inspected or retired; repository delivery
lifecycle remains external.

Use Work when implementation needs managed lifecycle state beyond a single
proposal or Change Set.

## Registries

Registries are generated indexes over P2P artifacts. They make project state
quick to inspect and easier for agents to summarize.

Registries are not the source of truth. Refresh them after meaningful changes:

```bash
p2p registry refresh
p2p validate
```

## Context Packets

Context packets are compact summaries for agents:

```bash
p2p context --budget small
```

With MCP, use:

```text
p2p_context
```

The context packet tells agents what is relevant, which commands are allowed, and
what not to read.

## Project Readiness And Maturity

Project readiness describes what a complete enough project definition should
cover for the current project structure. A domain classifies the subject but
does not inject criteria, rubrics or sections.

Readiness v2 derives weighted definition completeness and declared evidence
coverage from active criteria in the current `ProjectStructure`. The two axes
remain separate. Empty or fully retired criteria produce `not_configured`,
not a zero score.

Maturity assessment is now a compatibility projection of the readiness-v2
definition axis. It is not implementation completeness and not a separate
source of readiness truth.

Project verticals are immutable pure-data releases that provide reusable
sections, questions, fields, artifacts and default rubrics. Initialization
copies one effective release or starter into a detached `ProjectStructure`.
That structure has its own stable ID, revision and checksum and remains usable
without resolving its source again. Origin identity and checksum are provenance,
not a live lock or readiness constraint.

Simple structure edits add sections, update bounded metadata or reorder the
complete active section set. They require `project.structure.edit`, an expected
structure revision and an idempotency key. Referenced-element retirement and
release replacement use separate impact-aware lifecycles.

Portable schema-version-3 verticals use exact
`publisher/vertical-id@semantic-version` coordinates and immutable local
artifacts. P2P Engine validates and installs those artifacts offline; catalog
discovery, user policy, moderation, download and popularity counters belong to
an external system such as WaveKit. Multiple exact versions may coexist.
Remote registry v2 catalog domains and release `primary_domain` values are
advisory discovery metadata only. They do not change the project's free domain
classification, prove compatibility, or select a detached structure source.
Transitional release adoption or migration does not replace the project-owned
structure. The implemented structure replacement lifecycle uses
`p2p project structure replace preview/apply/status` to compare an exact
schema-3 release with current structure and memory revisions, require an impact
plan where needed, and govern every affected memory reference before applying
a detached replacement copy.

`.p2p/project/definition.yml` stores durable owner answers, assumptions,
missing required fields, blockers, open questions, section status, and
provenance for project-definition work. Agents should inspect current project
structure, active criteria and definition state before asking follow-up
questions, then ask one primary question at a time.

Project progress, readiness review, gaps and snapshot reads use the same
criterion interpretation. Memory classification is published beside readiness
and cannot change its score.

### Vertical-Aware Derived Memory

P2P may materialize a compact per-section project view for repeated reads. It
groups current authority, historical context, definition facts, questions,
assumptions, blockers, choices and conflicts according to explicit vertical
coverage. Heuristic similarity remains advisory and cannot satisfy declared
evidence.

This read model is an accelerator, not another source of truth. It can be
deleted and rebuilt with `p2p project refresh`. Read commands never refresh it
implicitly, and a successful governance mutation remains successful even when a
separate derived update fails.

```bash
p2p project readiness review
p2p project readiness gaps --limit 20 --format json
p2p project progress --format json
```

## Human Project Publication

A publication edition is a language-specific, derived document for a reader who
does not know P2P. It represents the project itself, not the chronological
proposal or governance process.

All editions use one shared, complete evidence index. A curator builds a strict
project model, accounts for every evidence item, and writes localized reader
prose using the current project structure as a completeness lens rather than a fixed table
of contents. Model and accounting sidecars preserve traceability so internal IDs,
hashes, paths, readiness scores, and `.p2p` authority boilerplate do not need to
appear in the reader document.

An optional Contributions chapter reports only the distribution of selected
attributed project records. It is not an estimate of effort, merit, ownership,
or intellectual-property shares. Prepared figures remain invariant across
editions, while the accompanying limitation is localized for the reader.

Language changes presentation, not project scope. Each edition has independent
freshness, validation, PDF, and owner review. Publication approval is not a P2P
proposal decision and never transfers between editions or from legacy output.

## Agent Boundary

Agents should:

- start with compact context;
- inspect only relevant artifacts;
- use CLI or MCP primitives for P2P writes;
- stop and report missing primitives;
- avoid manual `.p2p/` edits.

Owner-controlled decisions remain explicit owner actions.

## What To Read Next

- [TUTORIAL.md](TUTORIAL.md) for the end-to-end first result.
- [CLI-GUIDE.md](CLI-GUIDE.md) for practical command workflows.
- [MCP.md](MCP.md) for local agent integration.
- [GLOSSARY.md](GLOSSARY.md) for short definitions.

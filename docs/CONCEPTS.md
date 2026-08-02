# P2P Concepts

This page is the short operational concept guide for P2P Engine. It explains the
model used by the CLI, MCP server, tutorial, and generated `.p2p/` project
state.

For definitions, see [GLOSSARY.md](GLOSSARY.md). For the longer design
rationale, see [vision/p2p-engine-foundation.md](vision/p2p-engine-foundation.md).

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

P2P Engine stores project governance state under `.p2p/`. Git stores the history.
The owner keeps authority over decisions.

Common artifact areas:

```text
.p2p/
  proposals/    structured candidate directions
  choices/      explicit alternatives and selected outcomes
  changes/      operational Change Sets from accepted intent
  work/         managed handoff and branch lifecycle metadata
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

A decision records an owner-controlled outcome and rationale. P2P Engine can
store decisions and expose them to agents, but it does not remove owner
authority.

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

Change Sets do not replace Git commits or code review. They explain what work is
derived from accepted project intent.

## Work

Work metadata tracks implementation or handoff lifecycle around a Change Set.
Depending on the command, Work can involve local Git branches, review handoff,
publish, accept, finalize, and cleanup steps.

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

## Rubrics And Maturity

Rubrics describe what a complete enough project definition should cover for a
domain, such as software, grant documents, or board games.

Maturity assessment checks definition coverage against those rubrics. It is not
implementation completeness.

Project verticals are pure-data packs that provide domain-specific sections,
questions, fields, artifacts, and default rubrics. A selected vertical is pinned
by `.p2p/project/vertical.lock.yml`; after a lock exists, commands must fail
closed on missing sources or checksum mismatch rather than silently falling back
to `base_project`.

Portable schema-version-2 verticals use exact
`publisher/vertical-id@semantic-version` coordinates and immutable local
artifacts. P2P Engine validates, installs and adopts those artifacts offline;
catalog discovery, user policy, moderation, download and popularity counters
belong to an external system such as WaveKit. Multiple exact versions may
coexist. Migration preserves exact matching evidence and retains unmatched
evidence as explicit project-definition orphans.

`.p2p/project/definition.yml` stores durable owner answers, assumptions,
missing required fields, blockers, open questions, section status, and
provenance for project-definition work. Agents should inspect vertical context,
definition state, and rubrics before asking follow-up questions, then ask one
primary question at a time.

Selected project rubric maturity measures only enabled project criteria. Full
vertical baseline coverage is reported separately through baseline/default
counts where available.

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
p2p project rubrics show
p2p assess maturity refresh
p2p assess maturity show
```

## Human Project Publication

A publication edition is a language-specific, derived document for a reader who
does not know P2P. It represents the project itself, not the chronological
proposal or governance process.

All editions use one shared, complete evidence index. A curator builds a strict
project model, accounts for every evidence item, and writes localized reader
prose using the active vertical as a completeness lens rather than a fixed table
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

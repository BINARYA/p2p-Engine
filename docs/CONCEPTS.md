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

`.p2p/project/definition.yml` stores durable owner answers, assumptions,
missing required fields, blockers, open questions, section status, and
provenance for project-definition work. Agents should inspect vertical context,
definition state, and rubrics before asking follow-up questions, then ask one
primary question at a time.

Selected project rubric maturity measures only enabled project criteria. Full
vertical baseline coverage is reported separately through baseline/default
counts where available.

```bash
p2p project rubrics show
p2p assess maturity refresh
p2p assess maturity show
```

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

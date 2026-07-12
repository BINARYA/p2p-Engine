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

An owner-controlled governance outcome. Proposal decisions include accept,
reject, and defer. Choice decisions select one option and record the rationale.

## Export Target

A downstream-oriented prompt or document generated from P2P-native project
state. Current software spec export targets include generic, OpenSpec, and Spec
Kit initialization outputs.

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

## Rubric

A project-domain checklist used to assess project definition maturity. Rubrics
make it clear which aspects of intent have or have not been covered.

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

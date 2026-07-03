# Exploration - PROP-091

## Interpretation

This proposal is a convergence and policy-evaluation feature. It does not
replace existing governance artifacts. It makes them coherent enough for the
owner, agents, MCP clients, and future UI layers to understand the governance
state before decisions are finalized.

The central design principle is:

```text
CLI core = deterministic structured truth
agents/intermediaries = optional analysis and authoring support
owner = final decision authority
```

The core should not become a political system or an AI-powered precedent search
engine. It should provide a reliable preflight result from explicit, versioned
artifacts.

## Current State

P2P Engine already has:

- governance artifact initialization;
- proposal-local votes;
- decision precedents;
- SWOT prompt support;
- project choices and choice blockers;
- permissions and actor identities;
- consent receipts;
- owner-controlled governance boundaries;
- MCP advisory and permission-gated surfaces.

These capabilities are useful but not converged. A proposed choice decision can
be made without a single deterministic view of actor authority, vote alignment,
blockers, related precedents, and governance validity.

## Desired State

A caller can ask:

```text
Given actor X, target Y, and proposed selection Z, what does governance say?
```

The answer is a structured preflight result, not a final decision. It should be
stable, versioned, testable, and renderable by CLI/MCP/UI layers.

## Key Boundaries

- The owner remains the final decision maker.
- Votes do not enforce decisions.
- Related precedents do not enforce decisions.
- Explicit active blockers stop normal finalization but can be owner-overridden
  with rationale.
- Structural invalidity and unauthorized actors are non-overrideable blocks.
- Soft analysis may suggest links, but core behavior only uses explicit links.
- MCP phase 1 observes and evaluates; it does not mutate governance state.

## Implementation Implications

This proposal implies a cohesive policy service or equivalent boundary that can
be reused by CLI, validation, MCP, and future UI layers. It should avoid
duplicating governance interpretation inside command handlers or MCP handlers.

The preflight result should be a structured domain object before it is rendered
as human-readable CLI output, YAML, JSON, or MCP payload.

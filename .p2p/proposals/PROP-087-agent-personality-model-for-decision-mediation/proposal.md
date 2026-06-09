# PROP-087 - Agent Personality Model For Decision Mediation

## Status

`accepted`

## Problem

Agents currently adapt tone and technical detail only through prompt text or chat habit. The project needs an explicit, configurable interaction model for how an agent or mediator addresses the decision owner.

## Context

The owner defines personality as project interaction style: how an agent or mediator addresses the decision owner. The first implementation uses three independent 0-5 scales. technical_verbosity=0 avoids engine terms in owner-facing language while 5 reports technical operations in detail. formality=0 is very informal while 5 is detached and highly formal. assertiveness=0 preserves the current standard while 5 is highly persistent about unresolved gaps, evidence, order, and follow-up. The owner chose project-level defaults shared by all agents, no persisted presets, and CLI/MCP access under project interaction-style.

## Goals

- Define a durable project-level interaction-style model for agent mediation with the decision owner.
- Persist three explicit independent scales: technical_verbosity, formality, and assertiveness.
- Provide stable defaults: technical_verbosity=2, formality=2, assertiveness=0.
- Expose read/update behavior through public project interaction-style CLI commands and matching MCP tools.
- Update generated agent instructions and project/local skills so agents know how to inspect and update style through CLI/MCP only.

## Non-Goals

- Do not let personality change governance authority, readiness scores, validation, permissions, facts, or audit evidence.
- Do not introduce open-ended persona prose or persisted named presets as the primary configuration model.
- Do not implement per-agent or runtime/session style overrides in the first slice.
- Do not require migration or manual completion for existing projects.

## Proposal

Introduce a project-level interaction_style configuration model with three independent integer fields: technical_verbosity 0..5, formality 0..5, and assertiveness 0..5. technical_verbosity controls how much engine/technical language the agent uses with the decision owner. formality controls how informal or formal the tone is. assertiveness, informally described by the owner as pedanteria, controls how strongly the agent pushes on unresolved gaps, evidence, order, and follow-up before moving on. Defaults: technical_verbosity=2, formality=2, assertiveness=0. The first implementation stores one project-level default interaction_style because the project should define a shared interaction style for all agents and mediators that address the decision owner. The public CLI namespace should be project interaction-style, with matching MCP tools. Values must be readable and modifiable through public P2P CLI commands and exposed through explicit MCP tools with read-only and write-safe behavior. Generated agent instructions and local/project skills must describe how agents inspect and update the style through those CLI/MCP surfaces. Per-agent and per-session overrides are future extension points. Named presets should not be persisted as source of truth; scales remain explicit and independent.

## Acceptance Criteria

- Project-level interaction_style is stored as the first implementation scope with no per-agent or session override in the first slice.
- The model validates technical_verbosity, formality, and assertiveness as integers from 0 to 5.
- Missing interaction_style configuration falls back to technical_verbosity=2, formality=2, and assertiveness=0 without breaking existing projects.
- Users and agents can read the project interaction style through a public CLI command under project interaction-style.
- Users and agents can update the project interaction style through a public CLI command under project interaction-style with validation and actionable errors.
- MCP exposes explicit read-only and write-safe tools for project interaction style status and update operations.
- Generated agent instructions and project/local skills explain how to inspect and update interaction style through CLI/MCP and prohibit direct .p2p edits for this state.
- Rendered agent guidance translates numeric values into concrete communication behavior for technical verbosity, formality, and assertiveness.
- Persisted named presets are not introduced; scales remain the source of truth and any labels are non-authoritative help text only.
- Tests cover defaults, validation bounds, CLI show/set, MCP status/update, generated instruction text, missing-config fallback, and no-direct-write guidance.

## Decision

Pending.

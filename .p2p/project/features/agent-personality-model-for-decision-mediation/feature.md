# Agent Personality Model For Decision Mediation

## Provenance

- Proposal: PROP-087
- Source: .p2p/proposals/PROP-087-agent-personality-model-for-decision-mediation

## Problem

Agents currently adapt tone and technical detail only through prompt text or chat habit. The project needs an explicit, configurable interaction model for how an agent or mediator addresses the decision owner.

## Proposal

Introduce a project-level interaction_style configuration model with three independent integer fields: technical_verbosity 0..5, formality 0..5, and assertiveness 0..5. technical_verbosity controls how much engine/technical language the agent uses with the decision owner. formality controls how informal or formal the tone is. assertiveness, informally described by the owner as pedanteria, controls how strongly the agent pushes on unresolved gaps, evidence, order, and follow-up before moving on. Defaults: technical_verbosity=2, formality=2, assertiveness=0. The first implementation stores one project-level default interaction_style because the project should define a shared interaction style for all agents and mediators that address the decision owner. The public CLI namespace should be project interaction-style, with matching MCP tools. Values must be readable and modifiable through public P2P CLI commands and exposed through explicit MCP tools with read-only and write-safe behavior. Generated agent instructions and local/project skills must describe how agents inspect and update the style through those CLI/MCP surfaces. Per-agent and per-session overrides are future extension points. Named presets should not be persisted as source of truth; scales remain explicit and independent.

## Decision

# Decision - PROP-087

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted by owner. The proposal is decision-ready and defines a project-level interaction_style model with three explicit scales, defaults, CLI/MCP surfaces, generated instruction updates, and no persisted presets.

## Date

2026-06-09

## Approver

owner

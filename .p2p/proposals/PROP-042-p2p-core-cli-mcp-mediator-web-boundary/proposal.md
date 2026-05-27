# PROP-042 - P2P Core CLI MCP Mediator Web Boundary

## Status

`accepted`

## Problem

P2P Engine needs a clear product and architecture boundary before adding MCP, mediator, web UI, or direct AI integrations. Without this boundary, the deterministic engine risks being coupled to optional AI or web infrastructure too early.

## Context

The accepted direction is to keep P2P usable as an open local product while enabling optional intermediaries: agent skills, MCP tools, mediators, and later web collaboration. The owner wants users to choose their intermediary without making the core depend on AI infrastructure.

## Goals

- Define P2P Core as the deterministic library for models, rules, validation, .p2p memory, proposal, choice, change, work, and registry operations.
- Define P2P CLI as the terminal interface for users, agents, scripts, and local automations.
- Define Skill, MCP, and Agent Interfaces as optional ways for agents to use P2P without owning project decisions.
- Define P2P Mediator as an optional intelligent assistant layer that helps contributors but uses Core/CLI/MCP as source of truth.
- Define P2P Web as a later product UI over the same source-of-truth operations.

## Non-Goals

- Implement the MCP server in this proposal.
- Implement the mediator or web application in this proposal.
- Allow AI or mediator layers to decide governance outcomes by default.

## Proposal

Adopt a five-layer architecture: Level 1 P2P Core, Level 2 P2P CLI, Level 3 Skill/MCP/Agent Interfaces, Level 4 P2P Mediator, Level 5 P2P Web. Core remains deterministic and provider-neutral. Intelligence lives in optional mediator or agent-facing layers. MCP exposes core capabilities to agents and mediators. Governance decisions remain owner-controlled unless an explicit future policy permits bounded automation.

## Acceptance Criteria

- The architecture boundary is recorded as accepted project direction.
- Future MCP work must be scoped as an interface over the deterministic core, not as the mediator itself.
- Future mediator/web work must consume Core/CLI/MCP operations instead of becoming the source of truth.
- AI-assisted behavior remains advisory by default; owner-controlled governance remains the default policy.

## Decision

Pending.

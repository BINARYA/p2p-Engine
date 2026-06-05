# Product Steering

## Product

P2P Engine is a local, deterministic engine for turning project conversations
into governed project memory and exportable project definitions.

The product vision is to organize confused, distributed, and discontinuous
project intent into a governed project definition that humans and agents can use
without rediscovering context from scratch.

## Primary Users

- Owners who decide project direction.
- Contributors who propose, refine, and implement changes.
- AI agents that need bounded, explicit project context.
- Downstream tools that consume project definitions.

## Product Boundary

P2P Engine should define and export projects. It should not make owner decisions
or act as a hidden software development workflow for its own repository.

Governance and project memory live in P2P state. Local code implementation for
this repository is managed through Git, tests, review, and these local specs.

P2P Engine outputs are project theory and source context until bound to
implementation evidence. Generated `project.md` files can inform specs, but they
do not prove that code exists.

## Current Development Intent

The repository needs a clear separation between:

- project definition export for users;
- local development specs for implementing P2P Engine;
- P2P governance state;
- downstream software-only formats such as OpenSpec and Spec Kit.

The current project definition export shows that the engine already spans CLI,
proposal governance, readiness, prompt workflows, project state, registries,
MCP, agent integration, managed work, sync, consent, and next-action workflows.
These are implementation feature groups in `specs/features/`, not independent
coding plans inside `.p2p/`.

# PROP-067 - Agent-First Setup Documentation Split

## Status

`accepted`

## Problem

Public setup documentation still mixes two workflows: using P2P Engine for a new project and contributing to the P2P Engine repository itself. This can make users think they should operate the CLI manually or initialize work inside the engine repository when the normal workflow is to install P2P once and let an agent use it on a separate target project.

## Context

README currently has a 5-minute demo with manual CLI commands. INSTALL documents source installation, project init, MCP setup, and manual first commands. CONTRIBUTING has basic developer setup but does not clearly explain how contributors should enable their agent to add proposals to the P2P Engine project state.

## Goals

- Make public setup documentation primarily about using P2P for a new target project.
- Keep P2P Engine repository contribution setup exclusively in CONTRIBUTING.md, with README linking there but not showing potentially confusing examples.
- Make manual CLI usage clearly secondary: useful for inspection, debugging, recovery, and learning the model.

## Non-Goals

- Change runtime behavior or installation code.
- Document unverified agent-specific desktop integrations as definitive commands.

## Proposal

Revise README and INSTALL around an agent-first new-project setup model. Add or update agent setup guidance so the P2P Engine checkout, target project, and agent client are clearly separated. Move repository-contributor instructions for installing P2P and enabling an agent against the P2P Engine repository into CONTRIBUTING.md, and keep README limited to a concise contribution pointer.

## Acceptance Criteria

- README no longer presents manual CLI proposal creation as the primary 5-minute path.
- README frames setup as installing P2P Engine, initializing a separate target project, connecting an agent, and letting the agent use P2P.
- INSTALL focuses on using P2P for a new project and marks manual CLI commands as optional.
- CONTRIBUTING contains the instructions for contributors who want to use P2P to add proposals to the P2P Engine repository itself.
- README links to CONTRIBUTING for P2P Engine contributor setup without showing explicit contributor-agent examples.

## Decision

Pending.

# PROP-061 - Focused README and Documentation Map

## Status

`accepted`

## Problem

The README should be the entry point for the p2p-engine repository, but it currently mixes engine scope with broader future product layers and does not yet provide a clean documentation map for CLI, MCP, agent integration, and core API references.

## Context

P2P Engine documentation now has an installation guide, but the repository still needs a focused README and stubs for the detailed documentation areas identified as important for humans, agents, and contributors.

## Goals

- Rewrite README.md as a concise repository entry point for P2P Engine.
- Keep mediator and web out of the main README scope except as out-of-repo future directions.
- Add documentation stubs for CLI guide, MCP reference, agent integration, and core API reference.
- Make README link to each detailed documentation file with a short explanation.

## Non-Goals

- Do not fully document every CLI command in this change.
- Do not add Python docstrings in this change.
- Do not implement packaging changes.

## Proposal

Refine documentation with four steps: rewrite README.md around what P2P Engine is, what it does, repository components, installation, quick start, and agent usage; keep docs/INSTALL.md; add docs/CLI-GUIDE.md, docs/MCP.md, docs/AGENT-INTEGRATION.md, and docs/API.md as structured stubs; and create a documentation index in README.md describing each docs file.

## Acceptance Criteria

- README.md is focused on the p2p-engine repository scope.
- README.md explains what P2P Engine is, what it enables, repository components, install, CLI usage, and agent usage.
- README.md includes a documentation map with short descriptions for each docs file.
- docs/CLI-GUIDE.md exists as a structured stub.
- docs/MCP.md exists as a structured stub.
- docs/AGENT-INTEGRATION.md exists as a structured stub.
- docs/API.md exists as a structured stub.

## Decision

Pending.

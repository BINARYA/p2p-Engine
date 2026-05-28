# PROP-058 - Project README and Installation Guide

## Status

`accepted`

## Problem

P2P Engine now has a mature Core/CLI/MCP MVP with init wizard, context packets, validation, readiness assessment, project definition rubrics, maturity assessment, spec/export flows, and managed work lifecycle. The repository README and installation guidance need to become an accurate entry point for new users instead of relying on chat history or internal project state.

## Context

The current installation path is source-based Python with a virtual environment. Future packaging may move toward a compiled/installable CLI, but the immediate user need is clear documentation for cloning, installing, initializing a project, using compact context, running assessment, and configuring MCP locally.

## Goals

- Update README.md as the product entry point.
- Add a practical installation guide.
- Document current architecture, quick start, init wizard, context discipline, rubrics, assessment, and MCP local setup.
- Be explicit about current limits and future packaging direction.

## Non-Goals

- Do not implement packaging changes in this proposal.
- Do not add a full website or generated docs site.
- Do not document unstable internals exhaustively.

## Proposal

Create a concise README and docs/INSTALL.md. README should explain what P2P Engine is, core principles, five-layer architecture, current implementation status, quick start commands, token-aware context, project definition maturity, MCP overview, and roadmap. docs/INSTALL.md should provide source install steps with Python venv, editable install, verification commands, project initialization, MCP local setup for Codex/compatible clients, troubleshooting, and current limitations.

## Acceptance Criteria

- README.md describes P2P Engine, principles, architecture, current status, quick start, and roadmap.
- docs/INSTALL.md documents installation from source with Python virtualenv.
- docs/INSTALL.md documents local MCP setup with PATH and explicit python -m alternatives.
- Documentation is honest that packaged/compiled CLI is future work.
- Docs reference p2p context, p2p assess, p2p assess maturity, and init wizard rubric selection.

## Decision

Pending.

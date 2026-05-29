# PROP-070 - Clarify README Agent Access Modes

## Status

`accepted`

## Problem

The README says to connect an agent through MCP but does not clearly distinguish CLI access from MCP access. This can make MCP appear complete even though the current MCP surface is intentionally agent-safe and excludes privileged governance, imports, Git operations, and Work lifecycle actions.

## Context

P2P Engine supports agent-mediated use through CLI access or MCP access. CLI access can reach the full local command surface when the owner explicitly authorizes actions. MCP access is structured and safer, but intentionally limited until a repository permission and ownership model is accepted.

## Goals

- Make the README quick start explicit about CLI access versus MCP access.
- State that current MCP access is intentionally limited and does not expose privileged operations.
- Point readers to INSTALL and MCP docs for detailed client setup and tool boundaries.

## Non-Goals

- Change MCP behavior or add privileged MCP tools now.

## Proposal

Update README's 5-minute agent setup to describe two valid agent connection modes: CLI access and MCP access. Add a short warning that MCP is currently an agent-safe tool surface and not the full P2P command surface.

## Acceptance Criteria

- README lists CLI access and MCP access as distinct agent connection modes.
- README says MCP does not currently expose proposal accept/reject/defer, choice decide/block, spec import, Git branch/commit/push/PR/merge, or privileged Work lifecycle operations.
- README points to INSTALL and MCP docs for detailed setup and boundaries.

## Decision

Pending.

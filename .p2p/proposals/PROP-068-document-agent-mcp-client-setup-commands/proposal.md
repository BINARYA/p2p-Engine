# PROP-068 - Document Agent MCP Client Setup Commands

## Status

`accepted`

## Problem

The new-project setup explains the P2P MCP server command but does not clearly show how to add that server to specific agent environments. Users need concrete setup commands for common MCP-capable clients without confusing target-project setup with P2P Engine contributor setup.

## Context

README should stay concise and avoid contributor-specific examples. INSTALL is the right place for new-project MCP client setup. CONTRIBUTING remains the only place for configuring an agent against the P2P Engine repository itself.

## Goals

- Add concrete MCP client setup examples for verified terminal clients.
- Show Claude Desktop/local MCP JSON using the same target-project server command.
- Keep unverified desktop or IDE-specific integrations framed as generic MCP client configuration rather than definitive commands.

## Non-Goals

- Document P2P Engine repository contributor MCP setup outside CONTRIBUTING.md.
- Claim support for unverified Codex desktop, Codex VSCode, or other IDE-specific MCP flows.

## Proposal

Update docs/INSTALL.md with an agent MCP setup section covering the common stdio command, Codex CLI, Claude Code, Claude Desktop JSON, and generic MCP clients. Keep README as a pointer to the install/MCP docs.

## Acceptance Criteria

- INSTALL contains a copy-pastable Codex CLI MCP add command for a new target project.
- INSTALL contains a Claude Code MCP add command for a new target project.
- INSTALL contains a Claude Desktop local MCP JSON example for a new target project.
- INSTALL clearly says unverified desktop/IDE clients should use the same command/args through their MCP configuration UI.

## Decision

Pending.

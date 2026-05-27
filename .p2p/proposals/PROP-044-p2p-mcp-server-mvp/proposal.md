# PROP-044 - P2P MCP Server MVP

## Status

`accepted`

## Problem

Agents should access P2P project state through structured tools instead of parsing CLI text or reading .p2p files directly.

## Context

PROP-042 established that MCP is an agent-facing interface over the deterministic P2P Core, not the mediator itself. The first MCP implementation should be local, read-only, and provider-neutral.

## Goals

- Add a local stdio MCP server inside this repository.
- Expose a minimal read-only tool surface over P2PWorkspace.
- Keep governance and Work mutation commands out of the MCP MVP.
- Avoid web server, cloud deployment, auth, container, direct AI invocation, and mediator logic.

## Non-Goals

- Implement MCP over HTTP.
- Expose proposal accept, choice decide, work accept, Git branch, commit, merge, cleanup, or provider actions.
- Implement P2P Mediator or Web.

## Proposal

Add src/p2p_engine/mcp with a small JSON-RPC stdio MCP server and a p2p-mcp-server entrypoint. The server exposes read-only tools for project status, next actions, proposal list/show, choice list/show, change status, work status, and registry show. Each tool returns structured JSON derived from P2PWorkspace.

## Acceptance Criteria

- p2p-mcp-server can initialize over stdio and list tools.
- tools/call works for p2p_project_status, p2p_next, p2p_proposal_list, p2p_proposal_show, p2p_choice_list, p2p_choice_show, p2p_change_status, p2p_work_status, and p2p_registry_show.
- MCP tools are read-only in the MVP.
- Tests cover tool listing and representative tool calls without requiring a web server or network.

## Decision

Pending.

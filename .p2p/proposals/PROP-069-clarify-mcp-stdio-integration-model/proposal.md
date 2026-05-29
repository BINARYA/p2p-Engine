# PROP-069 - Clarify MCP Stdio Integration Model

## Status

`accepted`

## Problem

The installation and MCP documentation show client setup commands but do not explain that MCP stdio is not a shared server process. Users may misunderstand how multiple agents connect to P2P, where shared state lives, and when Streamable HTTP would be needed.

## Context

P2P Engine currently exposes a local stdio MCP server through the Python module p2p_engine.mcp.server. In stdio mode, each MCP client starts its own local process and shared project state lives in the target repository, .p2p, Git, and P2P core storage. The docs should distinguish this from future shared Streamable HTTP operation.

## Goals

- Document the MCP stdio integration model clearly.
- Clarify that each client may start its own P2P MCP process and that shared state is repository-backed.
- Refine verified setup examples for Claude Code, Claude Desktop, Codex CLI/config, Codex IDE extension, and VS Code Copilot MCP.

## Non-Goals

- Implement Streamable HTTP MCP support now.
- Change MCP server runtime behavior.

## Proposal

Update docs/INSTALL.md and docs/MCP.md with a clear MCP stdio model, verified client setup sections, and explicit notes about future Streamable HTTP for shared long-running multi-client services. Keep all examples based on the current Python MCP server command and --root target-project argument.

## Acceptance Criteria

- MCP docs explain that stdio clients launch the server as a subprocess and that stdout must contain only MCP messages.
- Docs explain that multiple clients may create multiple MCP server processes and shared state must live in the repository/.p2p/Git/core storage.
- Docs state that a future shared multi-client service would use Streamable HTTP, not the current stdio process model.
- INSTALL client examples use the current Python module command and --root, not Node or P2P_ROOT placeholders.

## Decision

Pending.

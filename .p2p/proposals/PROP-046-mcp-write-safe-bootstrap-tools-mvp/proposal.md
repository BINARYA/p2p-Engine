# PROP-046 - MCP Write-Safe Bootstrap Tools MVP

## Status

`accepted`

## Problem

The MCP server can read project state but cannot perform safe bootstrap operations. When an agent is asked to initialize or harden a project through MCP, it may fall back to manual filesystem edits if no explicit MCP primitive exists.

## Context

CHANGE-030 added agent-safe init and instruction refresh in the CLI/Core. The next increment is to expose only those safe bootstrap mutations through MCP, without adding governance decisions or managed-work mutations.

## Goals

- Allow MCP clients to initialize P2P projects, refresh agent instructions, and refresh registries through explicit controlled tools.

## Non-Goals

- Pending.

## Proposal

Add p2p_init_project, p2p_agent_instructions_refresh, and p2p_registry_refresh MCP tools. Keep owner-controlled actions such as proposal accept/reject/defer, choice decide, work accept/finalize/cleanup, and direct Git merge out of MCP. Tool descriptions must make the governance boundary explicit.

## Acceptance Criteria

- MCP tool definitions include the three write-safe bootstrap tools; p2p_init_project generates AGENTS.md and .p2p/agent-policy.yml; p2p_agent_instructions_refresh can add Codex/Claude/generic/all profiles; p2p_registry_refresh returns written registry paths; tests cover tool calls and confirm governance tools remain absent.

## Decision

Pending.

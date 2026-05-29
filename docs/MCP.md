# P2P MCP Server

This document describes how agents can access P2P Engine through the local MCP server.

Status: scaffold. Tool coverage exists in the code; this guide will become the human-readable reference.

## Server

Run the stdio server from an installed environment:

```bash
p2p-mcp-server --root /path/to/project
```

Robust source-checkout form:

```bash
/path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/project
```

## Codex Example

```bash
codex mcp add p2p-my-project -- \
  /path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

## Safety Model

MCP tools are grouped by behavior:

- read-only tools inspect state;
- write-safe tools create drafts or deterministic generated artifacts;
- governance decisions remain owner-controlled;
- missing write primitives must be reported, not bypassed by manual `.p2p/` edits.

## Recommended First Tool

Use compact context first:

```text
p2p_context
```

This reduces token usage and tells the agent what not to read.

## Current Tool Areas

- project init and agent instruction refresh;
- registry refresh and show;
- validation;
- compact context;
- readiness and maturity assessment;
- project rubrics;
- proposal create/update/show/list;
- proposal contribution add;
- intake prompt/status;
- project brief prompt/show;
- choice discovery/list/show;
- conflict status;
- impact prompt;
- change/work status.

## To Be Expanded

- full tool schema table;
- read-only vs write-safe matrix;
- examples for Codex, Claude, and generic MCP clients;
- troubleshooting and security notes.


---
name: p2p-project
description: Use when working in this P2P-managed project. Enforces P2P Engine boundaries for Codex.
---

# P2P Project Skill - Minimal Software Project

Use P2P Engine as the source of truth for project governance and planning.

## Required Behavior

- Read `AGENTS.md` and `.p2p/agent-policy.yml` before modifying project state.
- Use `p2p` CLI commands for P2P mutations.
- Use MCP only within the tool schema; read-only MCP tools do not authorize filesystem writes.
- If no CLI command or MCP write tool exists for the requested operation, stop and report the missing primitive.
- Do not edit `.p2p/` internals directly, invent IDs, or synthesize decision files.
- Do not accept, reject, defer, decide, merge, finalize, or cleanup without explicit owner instruction.
- Before explaining existing proposals, choices, Change Sets, or Work items, use the relevant `p2p ... show` command or equivalent MCP read tool.
- Use `p2p context --budget small` or MCP `p2p_context` before broad file reads.
- Do not scan all `.p2p/`, registries, source files, or Git history unless the task explicitly requires it.

## Useful Commands

```bash
p2p status
p2p context --budget small
p2p registry refresh
p2p next
p2p proposal list
p2p choice list
p2p change status
p2p work status
```

Repository mode: `local`.

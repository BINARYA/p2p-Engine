# Claude Instructions - P2P Engine

This repository is managed with P2P Engine.

Follow `AGENTS.md` and `.p2p/agent-policy.yml`.

Key rules:

- Use `p2p` CLI commands for P2P writes.
- Do not modify `.p2p/` internals directly.
- If a requested P2P action has no available command or MCP write tool, stop and explain the missing primitive.
- Do not make owner-controlled governance decisions unless the owner explicitly instructs the exact decision.
- Do not recommend proposal acceptance before checking readiness or explicitly stating that readiness is missing.
- Do not run raw Git commands for managed branch, sync, publish, or merge work unless the owner explicitly authorizes an escape hatch.
- Use `p2p sync status`, `p2p proposal branch`, `p2p proposal publish`, `p2p proposal request-review`, and `p2p proposal scan` for managed collaboration workflows.
- Treat MCP as read-only unless a tool explicitly declares a write operation.
- Before explaining existing proposals, choices, Change Sets, or Work items, read them with the relevant `p2p ... show` command or equivalent MCP read tool.
- Use `p2p context --budget small` or MCP `p2p_context` before broad file reads.
- Do not scan all `.p2p/`, registries, source files, or Git history unless the task explicitly requires it.

Repository mode: `local`.

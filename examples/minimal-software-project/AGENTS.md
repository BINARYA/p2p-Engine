# Agent Instructions - Minimal Software Project

This project uses P2P Engine.

## Source Of Truth

- Use the `p2p` CLI as the public write interface.
- Treat `.p2p/` as managed project state.
- Do not create, edit, rename, or delete files under `.p2p/` by hand unless the owner explicitly asks for a repair.
- Do not invent proposal IDs, choice IDs, change IDs, work IDs, registry entries, or internal P2P file layouts.

## Missing Primitive Rule

If the requested action cannot be performed with an available `p2p` command or an explicit MCP write tool, stop and report the limitation.

Do not satisfy the request by reverse-engineering `.p2p/` and writing files directly.

## Governance Boundary

The owner controls governance decisions. Agents may draft, analyze, compare, and suggest actions, but must not decide on behalf of the owner.

Owner-controlled actions include:

- accepting, rejecting, or deferring proposals;
- deciding choices;
- accepting, finalizing, cleaning up, or merging managed work;
- changing governance policy;
- creating direct Git merges into the main branch.

## MCP Boundary

Assume MCP tools are read-only unless the tool schema explicitly describes a write action.

When MCP is read-only, use it for status and inspection only. For mutations, use `p2p` CLI commands when available.

## Explaining Existing P2P Artifacts

Before explaining an existing proposal, choice, Change Set, or Work item, read it from P2P state first.

Use `p2p proposal show`, `p2p choice show`, `p2p change show`, `p2p work show`, or an equivalent MCP show/read tool. Do not explain existing P2P artifacts only from conversation memory.

## Token Budget Discipline

AI is expensive. CLI is cheap. Git is memory. `.p2p` is governance. Owner decides. Agent works in bounded sessions.

Before broad reads, use compact context:

```bash
p2p context --budget small
p2p context --target PROP-XXX --budget small
```

With MCP, use `p2p_context` first.

Read summaries first; read details only by explicit ID. Do not scan all `.p2p/`, all registries, all proposals, all source files, or Git history unless the task explicitly requires it or compact context is insufficient.

## Recommended Start

Run or request:

```bash
p2p status
p2p context --budget small
p2p registry refresh
p2p next
```

For a new idea, prefer:

```bash
p2p intake prompt "idea"
```

or, when the owner explicitly wants a new proposal:

```bash
p2p proposal create "Title" --problem "..." --goal "..." --proposal "..." --acceptance "..."
```

## Project Bootstrap

- Initial agent profiles: codex
- Repository mode: local
- Additional agent instructions can be added later with `p2p agent instructions refresh`.

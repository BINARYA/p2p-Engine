# Agent Integration

This guide explains how Codex, Claude, and other agents should use P2P Engine.

Status: scaffold. The rules here mirror the generated `AGENTS.md`, `.p2p/agent-policy.yml`, Codex skill, and MCP tool boundaries.

## Core Rules

```text
AI is expensive.
CLI is cheap.
Git is memory.
.p2p is governance.
Owner decides.
Agents work in bounded sessions.
```

## Start With Compact Context

CLI:

```bash
p2p context --budget small
```

MCP:

```text
p2p_context
```

Agents should not scan all `.p2p/`, all registries, all proposals, source code, or Git history unless the task explicitly requires it or compact context is insufficient.

## Allowed Behavior

Agents may:

- create draft proposals through CLI or MCP write-safe tools;
- update draft proposal sections through explicit primitives;
- add proposal contributions;
- generate prompts and advisory analysis;
- inspect project state, registries, validation, context, and assessment;
- suggest next actions.

## Owner-Controlled Behavior

Agents must not perform these unless the owner explicitly instructs the exact action:

- accept, reject, or defer proposals;
- decide choices;
- accept, finalize, cleanup, or merge managed work;
- change governance policy;
- perform direct Git merges into main.

## Missing Primitive Rule

If an action cannot be performed with a CLI command or explicit MCP write tool:

```text
Stop and report the missing primitive.
Do not invent .p2p files.
Do not reverse-engineer IDs or registry entries.
```

## Codex

For a P2P-managed project, use the generated agent instructions:

```text
AGENTS.md
.p2p/agent-policy.yml
.codex/skills/p2p-project/SKILL.md
```

Configure MCP when available:

```bash
codex mcp add p2p-my-project -- \
  /path/to/p2p-Engine/.venv/bin/python \
  -m p2p_engine.mcp.server \
  --root /path/to/my-project
```

## Claude

For Claude-oriented projects, initialize or refresh instructions with:

```bash
p2p agent instructions refresh --profile claude
```

Then connect Claude through any compatible MCP client using the same stdio server command.

## To Be Expanded

- Codex workflow examples;
- Claude workflow examples;
- generic MCP client setup;
- prompt-injection and malicious-proposal handling;
- recommended bounded-session patterns.


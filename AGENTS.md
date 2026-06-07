# Agent Instructions - P2P Engine

This project uses P2P Engine.

## Source Of Truth

- Use the `p2p` CLI as the public write interface.
- Treat `.p2p/` as managed project state.
- Do not create, edit, rename, or delete files under `.p2p/` by hand unless the owner explicitly asks for a repair.
- Do not invent proposal IDs, choice IDs, change IDs, work IDs, registry entries, or internal P2P file layouts.

## Missing Primitive Rule

If the requested action cannot be performed with an available `p2p` command or an explicit MCP write tool, stop and report the limitation.

Do not satisfy the request by reverse-engineering `.p2p/` and writing files directly.

## Runtime Bootstrap

If `p2p` is not available on `PATH`, try this discovery order before stopping:

```bash
p2p doctor
.venv/bin/p2p agent doctor
python -m p2p_engine agent doctor
python -m p2p_engine.mcp.server --root /path/to/project
```

Use the first available P2P command as the write interface. If no CLI command or explicit MCP write tool is available, report the diagnostics and ask the owner to install P2P Engine or provide a runner/container with P2P installed. Do not edit `.p2p/` manually as a fallback.

## Governance Boundary

The owner controls governance decisions. Agents may draft, analyze, compare, and suggest actions, but must not decide on behalf of the owner.

Owner-controlled actions include:

- accepting, rejecting, or deferring proposals;
- deciding choices;
- accepting, finalizing, cleaning up, or merging managed work;
- accepting, rejecting, merging, or finalizing managed proposal branches;
- changing governance policy;
- creating direct Git merges into the main branch.

## Local Code Development Specs

When the owner asks to implement code, or to translate an accepted P2P proposal
into expanded development context and operational implementation tasks, use
`AGENTS-p2p-dev-specs.md`.

When implementing, refactoring, reviewing, or cleaning runtime code in `src/`,
also read and apply `specs/skills/ENGINEERING_QUALITY_SKILL.md`. Treat it as
the local engineering-quality policy for maintainability, compatibility,
testability, responsibility boundaries, side effects, and review discipline.

Keep this layer outside P2P governance state:

- Use P2P only to read the accepted direction, decisions, readiness, and
  constraints.
- Put implementation context and delivery tasks under local `specs/` files such
  as `requirements.md`, `design.md`, and `tasks.md`.
- Do not write coding steps, branch state, or implementation task checklists into
  `.p2p/` by hand.
- Treat local specs as repository development aids, not P2P Engine release
  artifacts, unless the owner explicitly decides otherwise.

Over time, local development specs and implementation tasks may derive from P2P
outputs, but they must remain a separate local development layer.

When asked to bind generated project-definition output such as `project.md` and
`propose.md` into local software development specs, use
`specs/methods/project-output-binding.md` and
`specs/skills/project-output-binding.md`. Do not mark implementation tasks
complete from generated project output alone; require evidence from `src/`,
`tests/`, `docs/`, or observed CLI behavior.

## P2PWorkspace Refactoring Architecture

When changing runtime code, do not add new unrelated domain behavior directly to
`src/p2p_engine/cli.py`, `src/p2p_engine/storage/filesystem.py`, or
`src/p2p_engine/mcp/tools.py` by default.

Use the local specs and `docs/DEVELOPMENT-GUIDELINES.md` to place new behavior
behind cohesive services, adapters, renderers, validators, or existing
boundaries. `P2PWorkspace` remains the compatibility facade while internal
behavior is extracted.

The large compatibility files may still receive facade delegation,
orchestration, compatibility glue, small command/tool wiring, or bug fixes when
an accepted local spec justifies the change and existing CLI/MCP/storage
behavior is preserved.

These architecture rules do not bypass P2P governance. Owner-controlled
decisions, consent requirements, managed branch/work boundaries, `.p2p` state
rules, and public CLI/MCP compatibility remain in force.

## Proposal Readiness

Before recommending proposal acceptance, inspect readiness with:

```bash
p2p proposal readiness show PROP-XXX
p2p proposal readiness refresh PROP-XXX
p2p proposal readiness explain PROP-XXX
```

If readiness is missing, weak, below target, or blocked by failed gates, ask focused owner questions and identify concrete missing artifacts before recommending acceptance. Readiness is advisory; the owner may still decide, but an owner override must be described separately from the computed score.

## Managed Git Collaboration

Do not run raw `git branch`, `git fetch`, `git pull`, `git push`, `git merge`, or provider PR/MR commands for managed P2P project state unless the owner explicitly authorizes an escape hatch.

Use P2P-managed commands instead:

```bash
p2p sync status
p2p sync fetch
p2p sync pull
p2p sync push
p2p proposal branch PROP-XXX --actor "name-or-agent"
p2p proposal status PROP-XXX
p2p proposal publish PROP-XXX
p2p proposal publish PROP-XXX --auto-renumber
p2p proposal request-review PROP-XXX
p2p proposal scan
p2p proposal retire-branch PROP-XXX --reason "..."
```

Before creating proposal or Work branches, inspect P2P state and sync state. Stop for owner approval before remote publication, accept, reject, merge, finalize, cleanup, or any operation marked owner-controlled by policy.

## MCP Boundary

Assume MCP tools are read-only unless the tool schema explicitly describes a write action.

When MCP is read-only, use it for status and inspection only. For mutations, use `p2p` CLI commands when available or explicit write-safe MCP tools such as `p2p_project_remote_configure`, `p2p_consent_request`, `p2p_proposal_draft_commit`, `p2p_proposal_branch`, and `p2p_sync_fetch` when their schema matches the requested action.

MCP may use implemented permission-gated repository tools only with a valid consent receipt. MCP must not retire or create provider PR/MR handoffs until those operations are explicitly implemented and authorized.

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

- Initial agent profiles: claude, codex, generic
- Repository mode: local
- Additional agent instructions can be added later with `p2p agent instructions refresh`.

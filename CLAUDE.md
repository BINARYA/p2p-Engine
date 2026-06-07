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
- When asked to implement code, or to translate an accepted P2P proposal into development context and operational implementation tasks, read and follow `AGENTS-p2p-dev-specs.md`.
- Keep implementation specs and tasks in local `specs/` files, not in `.p2p/`; treat them as repository development aids, not P2P Engine release artifacts unless the owner explicitly decides otherwise.

## Local Software Development Specs

When implementing code in `src/`, Claude must use the local specs as the
implementation source of truth:

- Read `AGENTS-p2p-dev-specs.md` first.
- Read relevant steering files in `specs/steering/`.
- Read or create the relevant feature spec under `specs/features/<feature>/`.
- Implement only behavior that is described by local `requirements.md` and
  `design.md`, or first update those specs before changing code.
- Track implementation steps in `specs/features/<feature>/tasks.md`.
- Do not use `.p2p/changes`, `.p2p/work`, `.p2p/outputs`, or chat history as
  the direct coding plan.
- When implementing, refactoring, reviewing, or cleaning runtime code in `src/`,
  read and apply `specs/skills/ENGINEERING_QUALITY_SKILL.md`.

If a requested implementation is not represented in `specs/`, Claude should
create or update the local specs before editing `src/`.

## Project Output Binding

When asked to bind generated project output such as `project.md` and
`propose.md` into the local software specs, Claude must use:

- `specs/methods/project-output-binding.md`
- `specs/skills/project-output-binding.md`
- `specs/bindings/_template.md`

Binding rules:

- Treat generated `project.md` as project theory and source context, not proof
  of implemented behavior.
- Treat `propose.md` as an instruction prompt, not requirements.
- Classify export content into steering context, feature candidates, current
  export focus, and gaps.
- Update `specs/steering/*` only with stable cross-feature context.
- Create or update feature specs under `specs/features/`.
- Mark tasks complete only when evidence exists in `src/`, `tests/`, `docs/`,
  or observed CLI behavior.
- Record substantial binding work under `specs/bindings/`.

Repository mode: `local`.

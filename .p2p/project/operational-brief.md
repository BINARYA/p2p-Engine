# P2P Engine Operational Brief

## Where We Are

P2P Engine now has a formal five-layer architecture boundary:

```text
Level 1 - P2P Core
Level 2 - P2P CLI
Level 3 - Skill / MCP / Agent Interfaces
Level 4 - P2P Mediator
Level 5 - P2P Web
```

The accepted direction is that P2P Core remains deterministic, provider-neutral and usable without AI, MCP, web infrastructure or hosted services. CLI remains the reference local interface. MCP and skills are agent-facing interfaces over the core. Mediator and Web are optional higher layers.

The project state is current at 42 proposals and 27 Change Sets. All recorded Change Sets are completed. Registries are not stale.

## Accepted Direction

- P2P remains CLI-first, file-based and Git-native.
- P2P Core owns models, validation, `.p2p/` memory and deterministic operations.
- P2P CLI exposes the core to humans, agents, scripts and local automation.
- Skill/MCP/Agent Interfaces allow agents to use P2P without becoming the source of truth.
- MCP server is a tool interface to P2P Core, not the mediator itself.
- P2P Mediator is optional and intelligent, but must use Core/CLI/MCP as source of truth.
- P2P Web is a later product UI over the same source-of-truth operations.
- AI-assisted behavior is advisory by default.
- Owner-controlled governance remains the default for proposal decisions, choice decisions, policy changes, work merge, remote branch deletion and irreversible cleanup.
- Direct Codex invocation remains out of current MVP scope; `CHOICE-001` decided prompt-only first, Codex adapter later.

## Active Work

- `WORK-001` exists and is still `planned` for `CHANGE-012` / `speckit`.
- No Change Set is currently planned or in progress.
- `INTAKE-001` is analyzed and has a controlled apply plan with pending actions.
- `INTAKE-002` is analyzed; its useful contribution was applied to `PROP-006`.
- Draft proposals remain: `PROP-002`, `PROP-006`, `PROP-007`, and `PROP-008`.

## Blockers / Inconsistencies

- No active formal choice blockers are recorded.
- `CHOICE-001` is decided: prompt-only first, Codex adapter later.
- `CHOICE-PROP-008` remains proposal-local vote metadata rather than a project-level choice.
- `WORK-001` is an older planned handoff artifact and should be inspected before use.

## Recommended Next Actions

1. Define P2P MCP Server MVP.
   Reason: `PROP-042` establishes that MCP is the next agent-facing interface over the deterministic core.
   Command: create an accepted proposal for MCP tool surface and then implement a small server MVP.

2. Review `INTAKE-001`.
   Reason: it still has pending actions, but much of it is now covered by `CHOICE-001` and the applied `INTAKE-002` contribution.
   Command: `.venv/bin/p2p intake apply show INTAKE-001`

3. Decide whether to retire, stage, or execute `WORK-001`.
   Reason: `WORK-001` predates the completed managed Work lifecycle.
   Command: `.venv/bin/p2p work status`

## Not Yet

- Do not implement Mediator or Web before the MCP/Core boundary is stable.
- Do not add automatic PR/MR creation without a new accepted proposal and Change Set.
- Do not move from prompt-only/Codex-assisted workflows to direct provider integration without revisiting the accepted AI integration choice.

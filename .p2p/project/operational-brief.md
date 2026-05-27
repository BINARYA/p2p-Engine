# P2P Engine Operational Brief

## Where We Are

P2P Engine has a deterministic Core/CLI foundation, managed Work lifecycle through cleanup, provider-agnostic remote review handoff, and an explicit five-layer architecture boundary:

```text
Level 1 - P2P Core
Level 2 - P2P CLI
Level 3 - Skill / MCP / Agent Interfaces
Level 4 - P2P Mediator
Level 5 - P2P Web
```

The project state is current at 43 proposals and 28 Change Sets. All recorded Change Sets are completed. Registries are not stale.

## Accepted Direction

- P2P Core remains deterministic, provider-neutral and usable without AI, MCP, web infrastructure or hosted services.
- P2P CLI remains the reference local interface.
- MCP is the next agent-facing interface over the deterministic Core.
- Mediator and Web remain later optional layers.
- AI-assisted behavior is advisory by default.
- Owner-controlled governance remains the default for proposal decisions, choice decisions, policy changes, work merge, remote branch deletion and irreversible cleanup.
- Direct Codex invocation remains out of current MVP scope; `CHOICE-001` decided prompt-only first, Codex adapter later.
- Spec export targets already include `generic`, `openspec`, and `speckit`.
- Obsolete planned Work manifests should be retired through `p2p work retire`, not edited by hand.

## Active Work

- `WORK-001` has been retired because `CHANGE-012` and the `speckit` export are already completed.
- No Change Set is currently planned or in progress.
- `INTAKE-001` has applied the useful contribution to `PROP-004`.
- `INTAKE-002` has applied the useful contribution to `PROP-006`.
- Draft proposals remain: `PROP-002`, `PROP-006`, `PROP-007`, and `PROP-008`.

## Blockers / Inconsistencies

- No active formal choice blockers are recorded.
- `CHOICE-001` is decided: prompt-only first, Codex adapter later.
- `CHOICE-PROP-008` remains proposal-local vote metadata rather than a project-level choice.

## Recommended Next Actions

1. Define P2P MCP Server MVP.
   Reason: `PROP-042` establishes that MCP is the next agent-facing interface over the deterministic core, and stale intake/work items have now been cleared.
   Command: `.venv/bin/p2p proposal create "P2P MCP Server MVP"`

2. Decide MCP tool surface.
   Reason: the MVP should expose a small deterministic read/write set and keep governance owner-controlled.
   Candidate tools: project/status, next, proposal/list/show/create, choice/list/show, change/status, work/status, registry/show.

3. Keep direct AI/provider invocation out of core.
   Reason: direct Codex/Claude execution belongs to future mediator or adapter layers, not the MCP/Core MVP.

## Not Yet

- Do not implement Mediator or Web before the MCP/Core boundary is stable.
- Do not add automatic PR/MR creation without a new accepted proposal and Change Set.
- Do not move from prompt-only/Codex-assisted workflows to direct provider integration without revisiting the accepted AI integration choice.

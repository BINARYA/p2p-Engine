# P2P Engine Operational Brief

## Where We Are

P2P Engine now includes the first MCP layer over the deterministic Core.

The current architecture remains:

```text
Level 1 - P2P Core
Level 2 - P2P CLI
Level 3 - Skill / MCP / Agent Interfaces
Level 4 - P2P Mediator
Level 5 - P2P Web
```

The MCP server is local, stdio-based, read-only, and lives in `src/p2p_engine/mcp/`. It is an interface to P2P Core, not a mediator and not a web/cloud service.

The project state is current at 44 proposals and 29 Change Sets. All recorded Change Sets are completed. Registries are not stale.

## Accepted Direction

- P2P Core remains deterministic, provider-neutral and usable without AI, MCP, web infrastructure or hosted services.
- P2P CLI remains the reference local interface.
- MCP exposes structured read-only tools for agents over P2P Core.
- MCP does not perform governance decisions, Git mutation, direct AI invocation, PR/MR creation, mediation, or web serving.
- Mediator and Web remain later optional layers.
- AI-assisted behavior is advisory by default.
- Owner-controlled governance remains the default.

## Implemented MCP MVP

Entrypoint:

```text
p2p-mcp-server
python -m p2p_engine.mcp.server
```

Read-only tools:

```text
p2p_project_status
p2p_next
p2p_proposal_list
p2p_proposal_show
p2p_choice_list
p2p_choice_show
p2p_change_status
p2p_work_status
p2p_registry_show
```

## Active Work

- No Change Set is currently planned or in progress.
- `WORK-001` is retired.
- `INTAKE-001` and `INTAKE-002` have had their useful contributions applied.
- Draft proposals remain: `PROP-002`, `PROP-006`, `PROP-007`, and `PROP-008`.

## Blockers / Inconsistencies

- No active formal choice blockers are recorded.
- `CHOICE-001` is decided: prompt-only first, Codex adapter later.
- `CHOICE-PROP-008` remains proposal-local vote metadata rather than a project-level choice.

## Recommended Next Actions

1. Test MCP from a real agent/client configuration.
   Reason: the server responds to stdio JSON-RPC locally, but should be verified from an actual MCP-capable client.
   Command: configure a client to run `p2p-mcp-server --root <project>`.

2. Define MCP write-safe tools.
   Reason: the MVP is intentionally read-only. The next scope should decide which low-risk mutations can be exposed, such as proposal creation or intake prompt generation.

3. Keep Mediator and Web deferred.
   Reason: the Core/CLI/MCP boundary should stabilize before adding an intelligent mediator or hosted product UI.

## Not Yet

- Do not add MCP governance mutations such as proposal accept, choice decide, or work accept without a dedicated policy.
- Do not add automatic PR/MR creation without a new accepted proposal and Change Set.
- Do not move direct AI/provider invocation into Core or MCP.

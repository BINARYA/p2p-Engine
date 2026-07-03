# Assumptions - PROP-091

- The project remains owner-led for the current governance phase.
- `owner_decides` is the default operational mode.
- Votes are decision evidence and transparency, not automatic enforcement.
- `permissions.yml` exists in modern projects and is the preferred actor source.
- Some older projects may still rely on `governance/roles.yml`.
- Missing optional governance artifacts should not block by themselves.
- Corrupt governance artifacts should block because the core cannot evaluate
  state reliably.
- Precedent lookup in the core must be deterministic.
- Agents and future UI tools may perform soft analysis outside the core.
- Soft analysis affects core behavior only after explicit artifact links are
  written.
- MCP phase 1 should not mutate governance state.
- The preflight schema should be reusable across CLI, MCP, tests, and future UI.

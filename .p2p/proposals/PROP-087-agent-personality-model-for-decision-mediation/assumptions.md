# Assumptions - PROP-087

- The decision owner wants a shared project interaction contract across agents.
- The current behavior corresponds to `assertiveness=0`.
- `technical_verbosity=2` and `formality=2` are acceptable defaults for normal
  mediation.
- The first implementation does not need per-agent or per-session overrides.
- Numeric scales are easier to validate and evolve than named persona presets.
- Generated agent instructions are the first consumer of the model.
- CLI and MCP should be the public mutation surfaces for interaction style.

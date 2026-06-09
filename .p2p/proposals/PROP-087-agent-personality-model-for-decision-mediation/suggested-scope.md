# Suggested Scope - PROP-087

## In Scope

- Project-level `interaction_style` configuration.
- Three validated integer fields:
  - `technical_verbosity` from 0 to 5.
  - `formality` from 0 to 5.
  - `assertiveness` from 0 to 5.
- Defaults:
  - `technical_verbosity: 2`
  - `formality: 2`
  - `assertiveness: 0`
- CLI namespace: `p2p project interaction-style`.
- MCP tools for status/read and write-safe update.
- Generated agent instruction updates.
- Project/local skill updates explaining how to inspect and update style.
- Backward-compatible fallback when no style is configured.

## Out Of Scope

- Persisted named presets.
- Per-agent style overrides.
- Runtime/session style overrides.
- Any change to governance authority, validation truth, readiness scoring,
  permission gates, or audit behavior.

## Suggested CLI Shape

```text
p2p project interaction-style show
p2p project interaction-style set --technical-verbosity 2 --formality 2 --assertiveness 0
```

The exact command spelling can still be refined during implementation specs,
but the namespace should remain project-scoped.

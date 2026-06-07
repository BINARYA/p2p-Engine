# P2PWorkspace Foundation Helper Service Consolidation 3 Design

## Decision

The selected services have helper contracts that map cleanly to
`foundation.files`:

- `software_spec` uses tolerant YAML mapping reads and YAML dumps.
- `registries` uses strict YAML mapping reads and YAML dumps.
- `agent_instructions` uses strict YAML mapping reads and YAML dumps.

`project_maturity` is explicitly skipped because its local reader raises
`ValueError("YAML document must be a mapping: <path>")`, not the foundation
strict helper's `"Invalid YAML mapping"` message.

## Implementation

- Replace local helper definitions with imports from `foundation.files`.
- Keep call sites unchanged by using local aliases.
- Remove unused `yaml` imports.
- Verify focused service tests and CLI/MCP registry/spec/instruction surfaces.

## Compatibility

No public behavior changes are expected. The replacement helpers preserve
existing YAML serialization and strict/tolerant read semantics for the selected
services.

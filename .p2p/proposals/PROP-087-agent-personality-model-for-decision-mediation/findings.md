# Findings - PROP-087

## Key Findings

- Interaction style should be a project property in the first implementation,
  not an agent-specific property.
- The model should persist numeric scale values, not prose personas.
- The first-slice defaults are:
  - `technical_verbosity: 2`
  - `formality: 2`
  - `assertiveness: 0`
- `assertiveness` is a separate behavioral dimension. It should not be encoded
  through formality or technical verbosity.
- The public command surface should use `project interaction-style`.
- MCP tools must mirror the CLI boundary with explicit read-only and write-safe
  operations.
- Generated agent instructions and project/local skills must teach agents how
  to inspect and update interaction style through CLI/MCP only.
- Existing projects must work without configured interaction style by falling
  back to the defaults.

## Implementation Findings

- A compact, versioned configuration record is preferable to prompt-only
  instructions because it is inspectable, validated, and reusable by CLI, MCP,
  generated instructions, and future UIs.
- The behavior should be rendered into instructions through deterministic text
  mapping. The persisted values remain the source of truth.
- Direct `.p2p` edits must stay out of the workflow. If a future surface needs
  to change interaction style remotely, it must use explicit MCP tools.

## Risk Findings

- If `assertiveness` is too high by default, the agent may block normal owner
  flow. Keeping the default at `0` preserves current behavior.
- If `technical_verbosity` is too low, the owner may lose operational
  transparency. Diagnostics and audit evidence must remain available.
- If labels/presets become the source of truth, the model becomes hard to scale
  when additional dimensions are added.

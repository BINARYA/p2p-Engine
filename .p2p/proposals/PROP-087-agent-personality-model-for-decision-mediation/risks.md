# Risks - PROP-087

## Behavioral Risks

- High assertiveness can make the agent feel obstructive.
  Mitigation: default `assertiveness` is `0`; higher values are explicit owner
  choices.
- Low technical verbosity can hide useful operational detail from the owner.
  Mitigation: owner-facing tone changes, but diagnostics, audit evidence, and
  command outputs remain available where appropriate.
- High informality may be inappropriate for some project contexts.
  Mitigation: `formality` is explicit and project-level.

## Product Risks

- Named presets could become a parallel source of truth.
  Mitigation: do not persist presets in the first implementation.
- Per-agent overrides could fragment the owner experience.
  Mitigation: defer per-agent style until project-level defaults are stable.
- Session overrides could be hard to audit.
  Mitigation: defer runtime/session overrides until explicit CLI/MCP primitives
  exist.

## Implementation Risks

- Prompt-only implementation would be fragile and hard to inspect.
  Mitigation: use validated project configuration and deterministic instruction
  rendering.
- Direct `.p2p` edits would break local/remote parity.
  Mitigation: expose CLI and MCP primitives and document them in generated
  skills/instructions.

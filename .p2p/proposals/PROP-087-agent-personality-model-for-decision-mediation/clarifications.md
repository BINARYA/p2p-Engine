# Clarifications - PROP-087

## Owner Decisions

- The first implementation stores `interaction_style` as a project-level
  default. It is common to all agents and mediators that address the decision
  owner.
- Per-agent defaults and runtime/session overrides are future extension points,
  not first-slice requirements.
- The persisted model uses explicit independent numeric scales, not named
  presets.
- `technical_verbosity` default is `2`.
- `formality` default is `2`.
- `assertiveness` default is `0`.
- `assertiveness` is the operational form of the informal "pedanteria" concept:
  it controls how strongly the agent pushes on unresolved gaps, evidence, order,
  and follow-up before moving on.
- The public CLI namespace should be `project interaction-style`.
- MCP should expose matching read-only and write-safe tools.
- Generated agent instructions and project/local skills must explain how to
  inspect and update the project interaction style through CLI/MCP primitives.

## Clarified Boundaries

- Personality affects owner-facing interaction style and proactivity, not
  governance authority.
- Personality must not change proposal acceptance, readiness scores,
  validation, permission gates, facts, or audit requirements.
- Technical verbosity `0` changes wording for the decision owner; it does not
  suppress real operations, evidence, or required diagnostics.
- Named labels may exist as non-authoritative UI/help text, but the source of
  truth remains the numeric scales.

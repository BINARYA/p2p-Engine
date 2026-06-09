# Execution Plan - PROP-085

## Implementation Slices

### Slice 1 - Vertical Pack Data Model

- Define the MVP vertical pack schema.
- Define `base_project` as a concrete default pack with cross-domain sections:
  vision, objective/outcome, owner/stakeholders, target/beneficiaries, scope,
  constraints, assumptions, risks, decisions/open questions, milestones/next
  actions, definition of done/readiness criteria, expected artifacts, and
  maturity/readiness status.
- Add validation for required fields: metadata, sections/capisaldi, minimal
  rubrics, blocking questions, and expected artifacts.
- Provide actionable diagnostics for missing or malformed project-local packs.

### Slice 2 - Vertical CLI And Project-Local Loading

- Ship `base_project` as an internal versioned data resource.
- Add one complete demonstration vertical.
- Load project-local custom packs before internal defaults.
- Preserve existing behavior when no vertical pack is present.
- Add `p2p project vertical list`.
- Add `p2p project vertical show <vertical-id>`.
- Add `p2p project vertical validate <path-or-id>`.
- Add `p2p project vertical propose "<project idea>"`.
- Add `p2p project vertical add <path>`.

### Slice 3 - Project Readiness Review

- Add `p2p project readiness review`.
- Read project context, existing rubrics/maturity, vertical packs, and custom
  packs.
- Report missing capisaldi, weak rubric coverage, missing initial questions, and
  suggested next project-definition actions.
- Use the custom vertical candidate procedure when no suitable vertical exists.

### Slice 4 - Agent Orchestrator Guidance

- Update generated/local agent instructions.
- Instruct agents to prioritize uninitialized projects and missing capisaldi.
- Describe how to propose and confirm custom verticals.
- Keep owner governance boundaries explicit.
- Include reference behavior for the two candidate examples:
  `packaging_or_physical_product_design` and `social_impact_program_design`.

### Slice 5 - Documentation And Tests

- Document vertical pack structure and override order.
- Add CLI and service tests for loading, validation, fallback, and review output.
- Add regression tests proving existing projects without packs remain compatible.

## Deferred Work

- Remote REST registry.
- Executable vertical plugins.
- Full five-vertical MVP catalog.
- Publishing project-local packs to a shared registry.

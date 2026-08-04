# Binding Report - PROP-108 Current-Only Memory And Agent Surface Convergence

## Inputs

- Accepted P2P proposal: `PROP-108`.
- Owner decision: accepted by `mrjungle` on 2026-08-04 without readiness
  override.
- Readiness: `100`, `decision_ready`, high confidence, no missing artifacts and
  no failed gates.
- Owner-confirmed vertical coverage:
  - `mvp_scope`;
  - `workflows_use_cases`;
  - `data_model`;
  - `constraints_nfrs`;
  - `integrations_dependencies`;
  - `risks_alternatives_decisions`;
  - `acceptance_validation`.
- Related accepted direction: `PROP-021`, `PROP-045`, `PROP-065`, `PROP-074`,
  `PROP-078`, `PROP-091`, `PROP-095`, `PROP-103` through `PROP-107`.
- Existing steering: `specs/steering/*`.
- Existing implementation contracts: current agent integration, MCP surface,
  runtime contract, proposal lifecycle, project readiness, publication and
  `PROP-104` through `PROP-107` feature specs.

## Audit Inputs

- Registered surface baseline at proposal creation: 265 CLI leaf commands and
  171 MCP tools.
- Source inspected: agent templates/instructions, CLI command registration, MCP
  registry/catalog/handlers, workspace/runtime contracts, proposal artifacts
  and decisions, questions, permissions, decision context, registries, software
  specs, publications, readiness, derived freshness and facade wiring.
- Maintained docs inspected: README, install, CLI, MCP, agent integration,
  workspace schema, changelog and development inventories.
- Tests inspected: agent instructions, CLI contract, MCP registry/handlers,
  workspace schema, proposal artifacts/decisions, project questions,
  permissions, decision context, registries, software specs, publications,
  readiness and derived freshness.

## Classification

### Steering Context

- P2P Engine remains a local deterministic project-memory engine.
- Governance state remains distinct from local implementation specs.
- MCP remains a governed subset rather than an automatic CLI mirror.
- The accepted breaking cleanup is compatible with the steering rule that a
  separate accepted proposal is required for public CLI, MCP and storage
  changes.

No steering update is required before implementation. Maintained user and
release documentation must be updated with the implementation.

### Feature Spec Created

`specs/features/prop-108-current-only-memory-and-agent-surface-convergence/`

- `requirements.md`
- `design.md`
- `tasks.md`
- `compatibility-inventory.md`

### Current Implementation Focus

The feature is specified but runtime implementation has not started. The first
implementation block must establish public-surface and template-generation
checks before compatibility deletion begins.

### Open Questions And Gaps

- No owner question blocks implementation.
- Inventory E005 requires technical classification of proposal decision
  shortcuts. Retaining one requires a current convenience rationale and a spec
  update; compatibility alone is not sufficient.
- Any other retained `legacy` symbol requires proof that it is historical-only
  or current domain terminology and cannot activate discarded behavior.

## Requirement-To-Evidence Matrix

| Requirements | Expected behavior | Planned evidence | Status |
| --- | --- | --- | --- |
| R001-R008 | CLI/MCP/docs/release surfaces converge | registry extraction, capability validation and docs contract tests | planned |
| R009-R014 | Standalone agent guidance covers current local/remote vertical workflows | generated adapter snapshots and command/tool resolution tests | planned |
| R015-R024 | Product generation detects obsolete templates independently from content drift | service, CLI, MCP and source/wheel adapter tests | planned |
| R025-R034 | One current contract per memory family with no reachable compatibility behavior | completed inventory, zero-write rejection and forbidden-entry-point tests | planned |
| R035-R046 | Required workspace/runtime/proposal/governance/derived families converge | focused family service plus CLI/MCP tests | planned |
| R047-R051 | Release artifacts and canonical project use only current state | archive inventory, clean wheel init, package scan and validation | planned |
| N001-N006 | Checks are deterministic, reviewable and release-gated | focused, public, wheel and full-suite evidence | planned |

## Task Completion Decisions

- T001 is complete because the accepted governance state is now bound to local
  requirements, design, tasks and an initial audit inventory.
- No implementation task is marked complete. Audit observations identify gaps
  but do not prove source changes, test coverage or release behavior.
- T002 must complete the exact path-level inventory before any broad deletion.

## Implementation Gaps

Proceed in dependency order:

1. complete exact family and public-entry-point inventory;
2. implement runtime-derived CLI/MCP inventory and capability classification;
3. implement template generation identity and two-axis diagnostics;
4. regenerate current agent guidance and establish source/wheel checks;
5. remove compatibility families from core outward to CLI/MCP/docs/tests;
6. archive and recreate the canonical project on the release candidate;
7. run focused, public-contract, package and full-suite validation.

## Owner Questions

None. `PROP-108` explicitly authorizes the breaking current-only direction,
template-obsolescence detection, agent-surface convergence and clean canonical
project recreation. WaveKit changes remain separate.

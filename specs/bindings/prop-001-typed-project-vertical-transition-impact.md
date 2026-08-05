# Binding Report - PROP-001 Typed Project Vertical Transition Impact

## Inputs

- Accepted P2P proposal: `PROP-001`, "Typed vertical transition impact and
  explicit migration decisions".
- Owner decision: accepted by `mrjungle` on 2026-08-05 without readiness
  override.
- Readiness at acceptance: `100`, `decision_ready`, high confidence, no
  missing artifacts and no failed gates.
- Owner-confirmed vertical coverage:
  - `mvp_scope`;
  - `workflows_use_cases`;
  - `data_model`;
  - `integrations_dependencies`;
  - `constraints_nfrs`;
  - `acceptance_validation`;
  - `risks_alternatives_decisions`.
- Existing steering: `specs/steering/*`.
- Prior implementation contracts:
  - `prop-103-portable-versioned-vertical-packs-and-governed-project-adoption`;
  - `prop-107-versioned-cli-contract-and-idempotent-mutation-receipts`;
  - `prop-108-current-only-memory-and-agent-surface-convergence`.
- Downstream evidence: WaveKit OpenSpec change
  `manage-versioned-project-verticals`, especially task `7.8` and its missing
  empty/populated classification and preservation/mapping completeness tests.

## Audit Inputs

- Source inspected:
  - `src/p2p_engine/core/portable_verticals.py`;
  - `src/p2p_engine/core/project_verticals.py`;
  - `src/p2p_engine/core/project_questions.py`;
  - `src/p2p_engine/core/mutation_preview.py`;
  - `src/p2p_engine/core/mutation_receipts.py`;
  - `src/p2p_engine/services/vertical_lifecycle.py`;
  - `src/p2p_engine/services/project_verticals.py`;
  - `src/p2p_engine/services/project_questions.py`;
  - `src/p2p_engine/services/project_readiness_convergence.py`;
  - `src/p2p_engine/services/mutation_receipts.py`;
  - `src/p2p_engine/storage/filesystem.py`;
  - `src/p2p_engine/cli_commands/project_ops.py`;
  - agent capability and template services.
- Tests inspected: portable vertical lifecycle, project questions,
  reconciliation, CLI contract, receipts and installed-wheel verification.
- Maintained documentation inspected: CLI contract, CLI guide, MCP guidance,
  generated agent guidance and the CLI primitive inventory.
- Released baseline: P2P Engine `0.4.7`, `p2p-cli/v1`, workspace schema `3`,
  vertical schema `2`, portable package format `1`.

## Classification

### Steering Context

- P2P Engine remains the only component that interprets and mutates project
  memory.
- WaveKit and standalone agents consume the same versioned CLI contract and do
  not inspect `.p2p` to reconstruct migration semantics.
- The global `p2p-cli/v1` envelope remains current. The change introduces an
  operation-level domain contract because the envelope itself is unchanged.
- MCP remains a governed subset. Project vertical install/adopt/migrate
  mutations stay CLI-only; MCP catalogs and agent guidance must describe that
  boundary accurately.
- The released `0.4.7` wheel remains immutable. The implementation targets the
  next release, expected to be `0.4.8`.

No steering update is required before implementation.

### Feature Spec Created

`specs/features/prop-001-typed-project-vertical-transition-impact/`

- `requirements.md`
- `design.md`
- `tasks.md`

### Current Implementation Baseline

- `VerticalLifecyclePreview.impact` is `dict[str, object]` and has no domain
  contract version.
- adoption classifies only definition fields, assumptions, blockers and
  definition orphans;
- owner question evidence and rubric customization do not participate in one
  authoritative empty/populated decision;
- migration silently turns an unmapped field into an orphan;
- rubric collisions raise before a structured preview can explain the
  required resolution;
- question impact is reduced to `reconciliation_required`;
- receipts do not record the normalized transition plan or typed semantic
  postconditions;
- generated guidance names the commands but does not teach the explicit
  decision loop.

### Open Questions And Gaps

- No owner decision blocks implementation.
- Concrete Python class names may change while preserving the specified module
  ownership and public contract.
- Collection limits are implementation constants, but they must fit the
  existing receipt size bound, fail closed when completeness is lost and be
  documented in the contract.
- P2P preview tokens remain state-bound and do not gain wall-clock expiry;
  WaveKit continues to own its shorter application-level `expires_at` policy.

## Requirement-To-Evidence Matrix

| Requirements | Expected behavior | Planned evidence | Status |
| --- | --- | --- | --- |
| R001-R008 | A strict `p2p-vertical-transition-impact/v1` contract exists under `p2p-cli/v1` | typed model tests and golden JSON fixtures | planned |
| R009-R015 | One classifier decides empty versus populated from every approved evidence family | classifier service tests for definition, questions, rubrics and orphans | planned |
| R016-R027 | Install, adoption and migration report complete structured impact | analyzer tests and CLI contract fixtures | planned |
| R028-R035 | Every non-automatic evidence destination is an exact owner decision | plan parser and materialization tests | planned |
| R036-R044 | Preview/apply remains write-free, atomic, stale-safe and idempotent | transaction, token, receipt, replay and failure-injection tests | planned |
| R045-R052 | CLI, docs, MCP inventory, generated guidance and wheel handoff converge | public-surface, template, docs and installed-wheel checks | planned |
| N001-N008 | Output is deterministic, bounded, private and release-verifiable | property-style ordering, bounds, privacy and package tests | planned |

## Task Completion Decisions

- T001 is complete because the accepted proposal, owner decision, current
  source evidence and downstream WaveKit gap are bound to local requirements,
  design and tasks.
- No implementation task is complete. Existing partial impact fields are a
  baseline and do not satisfy the new contract.
- WaveKit task `7.8` remains open until the released wheel exposes the complete
  contract and WaveKit updates its pin, fixtures, parser and missing tests.

## Implementation Gaps

Proceed in dependency order:

1. freeze the typed impact and plan schemas plus bounds;
2. implement the shared evidence classifier;
3. separate transition analysis from candidate materialization;
4. require and validate explicit decisions;
5. bind plan and impact fingerprints to preview, apply and receipts;
6. update CLI presentation and operation fixtures;
7. update MCP inventory, generated guidance and maintained docs;
8. verify source and installed-wheel parity;
9. hand the exact released contract to WaveKit for its `7.8` closure.

## Owner Questions

None. `PROP-001` explicitly selects a typed operation contract, rejects
implicit orphaning and WaveKit-side derivation, and authorizes the next-release
behavior change.

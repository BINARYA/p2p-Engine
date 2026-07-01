# Design - test-suite-strategy-and-quality-policy

## Requirements Covered

- R001-R015
- N001-N006
- E001-E005

## Key Decisions

- D001: Segment the suite instead of reducing it by default.
  Rationale: The suite size is a maintainability and feedback-loop problem, not
  evidence that coverage is wrong. Removing tests without a coverage-intent
  review would increase regression risk.

- D002: Use pytest markers as the primary selection mechanism.
  Rationale: Pytest markers are already supported by the existing stack, can be
  registered in `pyproject.toml`, and avoid introducing a new dependency before
  the repository has a clear test taxonomy.

- D003: Define three validation tiers: focused, public-contract, and full.
  Rationale: A developer needs fast local feedback while coding, but public
  surfaces and the full suite still need explicit validation before higher-risk
  handoff, commit, push, release, or merge.

- D004: Add `specs/skills/TEST_QUALITY_SKILL.md` as the durable policy artifact.
  Rationale: A one-time cleanup will not hold unless future agents have a local
  skill that tells them which tests to generate, which tests are unnecessary,
  and how to choose the lowest useful layer.

- D005: Update local agent/development instructions to reference the test skill.
  Rationale: The policy must be pulled into normal implementation flow. Keeping
  it only in a feature spec would make it easy to ignore during future features.

- D006: Split large test modules only after marker intent is clear.
  Rationale: `tests/test_cli.py` and `tests/test_mcp.py` are large because they
  protect broad public surfaces. Splitting them should improve ownership and
  targeted execution, not create a mechanical churn-only refactor.

- D007: Do not introduce test-impact tooling in the first implementation slice.
  Rationale: Marker-based subsets and scripts solve the immediate problem with
  less operational complexity. Coverage-based or dependency-aware selection can
  be evaluated later if the suite grows beyond what marker tiers can handle.

- D008: Assign the initial marker taxonomy centrally in `tests/conftest.py`.
  Rationale: Central collection-time marking gives immediate focused selection
  without adding mechanical `pytestmark` imports to 46 existing test files.
  Tests can still opt into explicit local markers later when a finer-grained
  distinction is needed.

## Components

- `pyproject.toml`: register pytest markers and keep marker names discoverable.
- `tests/`: apply markers and, where useful, split large mixed modules into
  domain-oriented files.
- `tests/conftest.py`: central collection-time marker assignment for the initial
  taxonomy.
- `scripts/`: optional developer entry points for common validation tiers.
- `docs/TESTING.md`: explain supported commands, marker meanings, and expected
  validation by change type.
- `specs/skills/TEST_QUALITY_SKILL.md`: durable local policy for future test
  generation and review.
- `AGENTS.md`: reference the test quality skill when agents add, update, or
  review tests.
- `AGENTS-p2p-dev-specs.md`: reference test validation expectations inside local
  feature task guidance.
- `specs/features/_template/tasks.md`: require future feature tasks to include
  focused and broad validation evidence.

## Marker Taxonomy

Initial marker names should stay small and stable:

- `unit`: pure or near-pure behavior with no external process, CLI, MCP, Git, or
  broad filesystem workflow.
- `service`: domain or application service behavior.
- `adapter`: filesystem, serialization, Git client wrapper, or integration
  adapter behavior.
- `cli`: observable CLI command behavior, output, exit behavior, or side effects.
- `mcp`: observable MCP tool schema, payload, error, or permission behavior.
- `integration`: workflow crossing multiple application boundaries.
- `git`: tests that exercise Git or sync-related behavior.
- `slow`: tests that are materially slower than normal focused feedback.
- `smoke`: minimal broad confidence checks suitable after small changes.

Markers may be combined. For example, a Git-backed sync CLI test can be marked
`cli`, `git`, and `integration`.

## Validation Tiers

Focused validation:

- Purpose: fast feedback while implementing a small change.
- Typical commands: direct file selection or marker expression such as
  `pytest -m "service and not slow"` plus the specific changed test file.
- Required for: every implementation task that changes behavior.

Public-contract validation:

- Purpose: prove externally observed behavior still works.
- Typical command: marker expression covering `cli or mcp` and any other public
  surface affected by the change.
- Required for: changes touching CLI/MCP output, payloads, persisted contracts,
  validation findings, generated artifacts, Git/sync behavior, or compatibility
  facades.

Full validation:

- Purpose: release-quality confidence and detection of cross-module regressions.
- Typical command: `.venv/bin/pytest` or the documented full-suite script.
- Required for: before commit/push/release/merge, after broad refactors, and
  after changes that affect shared services or persistence behavior.

## Test Quality Policy Outline

`TEST_QUALITY_SKILL.md` should include these rules:

- Add the lowest-layer test that proves the behavior.
- Add a public-surface test only when the public contract changes or when the
  public surface has distinct behavior from the lower layer.
- Do not duplicate the same scenario in service, CLI, and MCP tests unless each
  layer has a separate contract to protect.
- Prefer behavior assertions over private implementation assertions.
- Prefer deterministic fixtures with explicit roots and isolated temporary
  directories.
- Mark tests that involve Git, broad workflows, generated artifacts, or slow
  paths.
- Avoid broad snapshots unless the serialized output is itself the contract.
- For bug fixes, add the regression test at the layer where the bug is
  observable and add lower-layer tests only if they protect reusable logic.
- For refactors, preserve existing behavior and run the broad tier required by
  the affected public contracts.
- For future feature specs, record both useful focused tests and required broad
  validation in `tasks.md` or the implementation summary.

## Test Reorganization Strategy

1. Inventory the current suite before changing markers or files.
2. Register the marker taxonomy in `pyproject.toml`.
3. Mark tests by current intent without moving files.
4. Add docs/scripts for the three validation tiers.
5. Split only the largest mixed modules where markers reveal clear domain
   clusters.
6. Validate each split with focused tests and the full suite.
7. Update future feature templates and agent instructions after the policy is
   concrete.

## Data And Contracts

No runtime data contracts change.

Test markers become a local developer contract. Marker names should therefore be
treated as stable once documented, and removed only through a deliberate spec
update.

## Error Handling

Marker misuse should fail early through pytest marker registration warnings.
Documentation should show how to handle:

- unknown marker warnings;
- focused commands that collect zero tests;
- slow tests that unexpectedly enter fast subsets;
- tests that require Git or filesystem side effects.

## Migration And Compatibility

- Production behavior remains unchanged.
- Existing test names may move files only when pytest node IDs are not treated as
  external contracts. If external automation depends on node IDs, split work
  must include a compatibility note.
- Existing full-suite execution remains supported.
- The new policy is additive for future work; it does not retroactively make
  previously accepted implementation summaries invalid.

## Risks And Tradeoffs

- Risk: too many markers can make selection confusing.
  Mitigation: keep the first taxonomy small and document combined markers.

- Risk: focused subsets can create false confidence.
  Mitigation: keep full-suite validation mandatory before higher-risk handoff.

- Risk: splitting large files can create churn.
  Mitigation: split only when there is a clear ownership or execution benefit.

- Risk: policy is ignored by future agents.
  Mitigation: reference `TEST_QUALITY_SKILL.md` from local agent and spec
  guidance.

## Out Of Scope

- Runtime behavior changes.
- P2P governance changes.
- CI provider redesign.
- Coverage threshold enforcement.
- Test impact analysis tooling.

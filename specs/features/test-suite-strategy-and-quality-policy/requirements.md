# Requirements - test-suite-strategy-and-quality-policy

## Scope

Define a local development feature for reviewing the current automated test
suite, introducing reliable test subsets, and establishing a repository-level
test quality policy for future implementation work.

The goal is not to reduce coverage by deleting tests. The goal is to make the
suite easier to understand, cheaper to run during focused development, and more
consistent when future agents or developers add tests.

## Origin

- Source: local owner request.
- Reference: discussion after the readiness question state convergence feature
  reached a full-suite baseline of roughly 462 tests across 46 test files, with
  large public-surface test modules such as `tests/test_cli.py` and
  `tests/test_mcp.py`.
- P2P scope: none. This is a local development specification under `specs/`.

## In Scope

- Review the current `tests/` layout, test cost, and coverage intent.
- Define a stable pytest marker taxonomy for focused and broad test runs.
- Introduce supported commands or scripts for focused, public-contract, and full
  validation.
- Add a local `specs/skills/TEST_QUALITY_SKILL.md` policy analogous to
  `specs/skills/ENGINEERING_QUALITY_SKILL.md`.
- Update local agent/development guidance so future implementation work reads
  and applies the test quality policy when adding or changing tests.
- Refactor test organization where it improves maintainability without changing
  production behavior or weakening coverage.
- Update feature task conventions so every future implementation records the
  focused tests that are useful and the broader validation required before
  commit, release, or merge.

## Out Of Scope

- Removing tests only to make the suite smaller.
- Weakening CLI, MCP, storage, lifecycle, validation, consent, Git, or
  persistence coverage.
- Changing runtime behavior in `src/` as part of the test-suite policy work.
- Introducing test-selection dependencies such as coverage-based test impact
  tools before the marker/script strategy has been evaluated.
- Redesigning CI or release governance beyond documenting recommended local
  validation tiers.
- Editing managed `.p2p/` state.

## Functional Requirements

- R001: WHEN the feature starts, THE SYSTEM SHALL have a recorded inventory of
  current test files, collected test counts, approximate runtime, and high-cost
  modules.
- R002: WHEN a test file or test function belongs to a known execution tier, THE
  SYSTEM SHALL identify that tier with a registered pytest marker.
- R003: WHEN developers need fast feedback for a local code change, THE SYSTEM
  SHALL provide a supported focused test command or documented marker expression.
- R004: WHEN developers need to validate public contracts, THE SYSTEM SHALL
  provide a supported command or marker expression covering CLI, MCP, and other
  externally observed behavior.
- R005: WHEN developers need release-quality confidence, THE SYSTEM SHALL keep a
  full-suite command as the required final validation tier.
- R006: WHEN a future feature adds or changes tests, THE SYSTEM SHALL require the
  feature tasks or implementation summary to state the focused test subset and
  the broader validation that was run.
- R007: WHEN a test can prove behavior at a lower layer, THE TEST POLICY SHALL
  prefer that lower-layer test unless a public-surface contract also changes.
- R008: WHEN a public CLI contract changes, THE TEST POLICY SHALL require CLI
  tests for observable command behavior, output, exit behavior, or persisted
  side effects.
- R009: WHEN an MCP tool schema, payload, permission boundary, or error contract
  changes, THE TEST POLICY SHALL require MCP tests for the observable machine
  contract.
- R010: WHEN a service, parser, validator, renderer, or persistence adapter
  changes without public-surface changes, THE TEST POLICY SHALL prefer focused
  service or adapter tests over duplicating the same scenario in every public
  surface.
- R011: WHEN tests cover Git, sync, filesystem side effects, generated artifacts,
  or slow workflows, THE SYSTEM SHALL make those tests discoverable through an
  explicit marker.
- R012: WHEN a large test module mixes unrelated domains, THE SYSTEM SHALL split
  it only when the split improves ownership, focused execution, or readability
  while preserving test semantics.
- R013: WHEN markers, scripts, or test organization change, THE SYSTEM SHALL
  update documentation so developers and agents know which command to run for
  the current change type.
- R014: WHEN a test is skipped, slow, broad, or intentionally duplicated across
  layers, THE TEST POLICY SHALL require an explicit reason visible in code or
  documentation.
- R015: WHEN future agents implement features, THE LOCAL INSTRUCTIONS SHALL
  direct them to apply `TEST_QUALITY_SKILL.md` together with the engineering
  quality policy for any non-trivial test work.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL preserve existing production behavior while reorganizing
  or marking tests.
- N002: THE SYSTEM SHALL preserve existing coverage intent unless a test is
  explicitly proven obsolete or duplicate and removed in a dedicated review.
- N003: THE SYSTEM SHALL avoid adding new test infrastructure dependencies unless
  a written design note justifies the cost and migration path.
- N004: THE SYSTEM SHALL keep local test commands deterministic and usable from a
  clean checkout with the repository's existing Python environment.
- N005: THE SYSTEM SHALL keep pytest markers registered in `pyproject.toml` to
  avoid untracked marker drift.
- N006: THE TEST POLICY SHALL optimize for behavior protection, not line-count
  growth or superficial coverage metrics.

## Edge Cases And Errors

- E001: IF a test reasonably belongs to multiple tiers, THEN the marker strategy
  SHALL allow multiple markers and document the expected focused command.
- E002: IF a test is expensive but protects a critical public contract, THEN it
  SHALL remain in the broad validation tier and may also be marked `slow`.
- E003: IF marker application would require a large mechanical change, THEN the
  work SHALL be sliced by domain or file family and validated incrementally.
- E004: IF a proposed test split changes fixture behavior or test isolation,
  THEN the split SHALL be treated as a behavior-risking test refactor and proven
  by focused and full validation.
- E005: IF a future implementation skips the full suite because only a focused
  subset was run, THEN the implementation summary SHALL state the residual risk
  and the missing validation explicitly.

## Acceptance Criteria

- AC001: A current test inventory exists and identifies large or expensive test
  areas.
- AC002: `pyproject.toml` registers the agreed marker taxonomy.
- AC003: The repository has documented commands or scripts for focused,
  public-contract, and full-suite validation.
- AC004: `specs/skills/TEST_QUALITY_SKILL.md` exists and defines how future tests
  should be selected, scoped, named, layered, and justified.
- AC005: Local agent/development instructions reference the test quality policy
  for future test additions and review.
- AC006: The largest mixed test modules have either been marked clearly or split
  into maintainable domain-oriented modules with behavior preserved.
- AC007: The feature template or local task guidance requires future tasks to
  record useful focused tests and required broad validation.
- AC008: Focused marker commands, public-contract commands, and the full suite
  have been run successfully after the test-suite changes.

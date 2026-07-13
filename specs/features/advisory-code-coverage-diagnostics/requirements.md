# Requirements - advisory-code-coverage-diagnostics

## Scope

Add an optional, non-blocking code coverage diagnostic for P2P Engine
maintainers. The diagnostic helps maintainers see which `src/p2p_engine` modules
and lines are not exercised by a chosen pytest validation run.

This feature is development tooling and documentation only. It does not change
runtime behavior, governance behavior, validation routing, or user-facing P2P
project evidence assessment.

## Origin

- Source: accepted P2P proposal.
- Reference: `PROP-060 - Real Test Coverage Reporting`.
- Accepted scope name: Advisory Code Coverage Diagnostics.
- Decision boundary: coverage is optional and non-blocking; deterministic test
  impact routing remains separate in `PROP-098`.

## In Scope

- Add a standard pytest coverage integration as a development-only dependency.
- Document terminal `term-missing` coverage commands for `src/p2p_engine`.
- Show how to run coverage against smoke, focused, and full validation tiers.
- Preserve existing `./scripts/test-focused.sh`, `./scripts/test-public.sh`,
  `./scripts/test-smoke.sh`, and `./scripts/test-full.sh` behavior unless a
  small documentation-only clarification is enough.
- Verify that pytest accepts coverage options after development dependencies are
  installed.
- Verify that existing smoke and focused validation still pass without coverage.

## Out Of Scope

- Test impact routing or automatic test selection.
- User-facing project evidence coverage.
- CI gates, fail-under thresholds, or release blocking policy.
- HTML, XML, or generated coverage report artifacts.
- Mandatory per-change coverage execution.
- Runtime dependencies for P2P Engine users.
- MCP tools or MCP parity work.
- New public `p2p` CLI commands.
- Changes to source behavior under `src/p2p_engine`.

## Public Surface And MCP Impact

- CLI impact: none for the `p2p` CLI; pytest developer commands are documented.
- MCP impact: not applicable.
- Storage impact: none.
- Docs impact: contributor/developer testing documentation changes.
- Test impact: validation commands exercise the pytest plugin and existing
  validation tiers; no production behavior tests are required unless scripts are
  changed.
- Agent-facing behavior: documentation only; agents may use the documented
  coverage command as optional diagnostics, not as default validation.
- MCP parity decision: not applicable because the feature adds local pytest
  tooling, not a P2P runtime command, workflow, payload, permission boundary, or
  lifecycle operation.

## Functional Requirements

- R001: WHEN the development environment is installed with the repository's dev
  extra, THE SYSTEM SHALL provide a pytest coverage integration that accepts
  `--cov=src/p2p_engine` and `--cov-report=term-missing`.
- R002: WHEN a maintainer runs the documented smoke coverage command, THE SYSTEM
  SHALL print terminal coverage output for `src/p2p_engine` without requiring
  HTML, XML, or persisted report artifacts.
- R003: WHEN a maintainer wants focused coverage diagnostics, THE DOCUMENTATION
  SHALL show a command that combines the focused marker expression with
  `--cov=src/p2p_engine --cov-report=term-missing`.
- R004: WHEN a maintainer wants broad coverage diagnostics, THE DOCUMENTATION
  SHALL show how to add coverage options to the full-suite validation command.
- R005: WHEN coverage diagnostics are documented, THE DOCUMENTATION SHALL state
  that coverage is optional, advisory, and non-blocking.
- R006: WHEN coverage diagnostics are documented, THE DOCUMENTATION SHALL state
  that coverage does not decide which tests to run after a change.
- R007: WHEN the feature is implemented, THE SYSTEM SHALL NOT add a fail-under
  threshold, CI gate, HTML report, XML report, or generated coverage artifact
  requirement.
- R008: WHEN existing validation scripts run without coverage options, THE
  SYSTEM SHALL preserve their current behavior and exit semantics.
- R009: WHEN pytest coverage creates local transient data such as `.coverage`,
  THE REPOSITORY SHALL keep that data ignored and out of committed artifacts.

## Non-Functional Requirements

- N001: THE SYSTEM SHALL keep coverage tooling in development dependencies only.
- N002: THE SYSTEM SHALL preserve runtime package dependencies for normal P2P
  Engine users.
- N003: THE SYSTEM SHALL avoid new abstractions, services, or command surfaces
  for this first slice.
- N004: THE SYSTEM SHALL keep coverage commands copy-pasteable from a clean
  development checkout after dev dependencies are installed.
- N005: THE SYSTEM SHALL keep coverage documentation aligned with
  `specs/skills/TEST_QUALITY_SKILL.md`: coverage is diagnostic evidence, not a
  substitute for useful focused tests or public-contract validation.

## Edge Cases And Errors

- E001: IF pytest reports `unrecognized arguments: --cov`, THEN the development
  coverage dependency is missing and the implementer SHALL fix the dev extra or
  environment installation instructions.
- E002: IF a coverage command collects zero tests, THEN the command SHALL be
  treated as invalid documentation and corrected before handoff.
- E003: IF local coverage data is produced as `.coverage`, THEN it SHALL remain
  ignored by Git and SHALL NOT become a maintained artifact.
- E004: IF a maintainer needs an HTML, XML, CI, or threshold-based report later,
  THEN that change SHALL be handled as a separate proposal or spec update.
- E005: IF coverage output shows a low percentage, THEN that result SHALL NOT
  fail validation by itself in this feature.

## Acceptance Criteria

- AC001: `pyproject.toml` includes a development-only pytest coverage
  integration compatible with the repository's pytest setup.
- AC002: Pytest accepts `--cov=src/p2p_engine --cov-report=term-missing` after
  dev dependencies are installed.
- AC003: `docs/TESTING.md` documents terminal-only coverage diagnostics for
  smoke, focused, and full validation contexts.
- AC004: `docs/TESTING.md` explicitly states that coverage is optional,
  advisory, non-blocking, and separate from test impact routing.
- AC005: No fail-under threshold, CI gate, HTML report, XML report, or generated
  report artifact requirement is introduced.
- AC006: Existing smoke validation passes without coverage.
- AC007: Existing focused validation passes without coverage.
- AC008: At least one documented coverage command runs successfully and prints a
  terminal missing-lines report.

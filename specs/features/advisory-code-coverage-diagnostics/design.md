# Design - advisory-code-coverage-diagnostics

## Requirements Covered

- R001-R009
- N001-N005
- E001-E005

## Key Decisions

- D001: Use `pytest-cov` or an equivalent pytest-native coverage integration as
  a development-only dependency.
  Rationale: The repository already uses pytest as its test runner. A
  pytest-native integration keeps the diagnostic close to existing validation
  commands and avoids a custom coverage wrapper.

- D002: Keep the first slice terminal-only with `--cov-report=term-missing`.
  Rationale: The accepted proposal is about occasional maintainer diagnostics,
  not report publishing, CI enforcement, or artifact management.

- D003: Do not add a new `p2p` CLI command or MCP tool.
  Rationale: Coverage is a local development diagnostic over pytest execution.
  Exposing it through P2P runtime surfaces would expand the public contract
  without product value for P2P users.

- D004: Do not add a dedicated coverage script in the first slice.
  Rationale: The current scripts already support smoke and full pytest options,
  and focused coverage can be documented with an explicit marker expression.
  Avoiding another script keeps this feature small and reduces command-surface
  drift.

- D005: Preserve existing validation scripts.
  Rationale: The feature must not change default feedback loops. Coverage should
  be opt-in; `./scripts/test-focused.sh` and `./scripts/test-smoke.sh` should
  remain useful fast validation commands without coverage overhead.

## Components

- `pyproject.toml`: add the coverage integration to `[project.optional-dependencies].dev`.
- `docs/TESTING.md`: add a coverage diagnostics section with terminal-only
  commands and scope boundaries.
- `.gitignore`: already ignores `.coverage`; verify this remains true.
- `scripts/`: no planned changes in the first slice.
- `tests/`: no new behavior tests are expected unless script behavior changes.
- `src/p2p_engine/`: no changes.
- `specs/features/advisory-code-coverage-diagnostics/`: local implementation
  context and task plan.

## Diagnostic Commands

The documentation should include commands equivalent to:

```bash
./scripts/test-smoke.sh --cov=src/p2p_engine --cov-report=term-missing
```

```bash
.venv/bin/pytest -m "(unit or service or adapter) and not slow" --cov=src/p2p_engine --cov-report=term-missing
```

```bash
./scripts/test-full.sh --cov=src/p2p_engine --cov-report=term-missing
```

The focused coverage command uses an explicit marker expression because
`test-focused.sh` treats user-provided arguments as a full pytest argument list
for narrow target selection.

## Public Surface And MCP Parity

- CLI contract: unchanged for `p2p`; pytest commands are developer tooling.
- MCP contract: not applicable.
- Storage contract: unchanged; no P2P persisted artifact changes.
- Documentation contract: `docs/TESTING.md` becomes the maintained source for
  coverage diagnostic usage.
- Test contract: validation is command-based. Run existing smoke/focused
  scripts without coverage to prove defaults are preserved, plus one documented
  coverage command to prove the diagnostic works.

MCP parity is not required because this feature does not add or change a P2P
workflow, command, lifecycle, permission boundary, Git/sync behavior, or
machine-facing payload.

## Error Handling

- Missing dependency: pytest will reject `--cov`; fix the dev extra or reinstall
  the development environment.
- Zero collected tests: treat as a documentation error and correct the command.
- Local coverage data: `.coverage` is transient and ignored; it is not a
  maintained output.
- Low coverage percentage: report it as diagnostic information only, not as a
  validation failure.

## Migration And Compatibility

- Runtime users are unaffected because the dependency is dev-only.
- Existing pytest markers and validation scripts remain compatible.
- Existing CI or release behavior is unchanged unless a separate future feature
  introduces coverage gates.
- No `.p2p/` state is modified by implementation.

## Risks And Tradeoffs

- Risk: maintainers treat coverage percentage as a global quality score.
  Mitigation: document coverage as advisory and separate from test quality and
  routing.

- Risk: maintainers assume coverage decides which tests to run.
  Mitigation: document that routing remains outside this feature and belongs to
  `PROP-098`.

- Risk: coverage commands slow down normal local feedback.
  Mitigation: keep coverage opt-in and preserve existing no-coverage scripts.

- Risk: adding another development dependency increases setup surface.
  Mitigation: keep it in the existing `dev` extra and avoid runtime dependency
  changes.

## Out Of Scope

- Coverage thresholds.
- HTML/XML reports.
- CI integration.
- Test impact routing.
- User project evidence coverage.
- New P2P CLI or MCP surfaces.
- Runtime source changes.

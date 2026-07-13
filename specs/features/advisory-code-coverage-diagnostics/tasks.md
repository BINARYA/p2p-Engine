# Tasks - advisory-code-coverage-diagnostics

- [x] T001: Review `PROP-060`, this feature spec, `docs/TESTING.md`, and
  `specs/skills/TEST_QUALITY_SKILL.md`; completion is an implementation boundary
  that keeps coverage diagnostic-only and separate from test routing.
- [x] T002: Inspect current dependency metadata for R001/N001; completion is
  confirmation that coverage tooling is absent from the dev extra before the
  change.
- [x] T003: Add a pytest coverage integration to `[project.optional-dependencies].dev`
  in `pyproject.toml` for R001/AC001; completion is dependency metadata that
  keeps coverage dev-only and does not change runtime dependencies.
- [x] T004: Reinstall or refresh the local development environment after T003;
  completion is pytest accepting `--cov=src/p2p_engine --cov-report=term-missing`
  in `--help` or an equivalent no-test command.
- [x] T005: Verify `.gitignore` handling for R009/E003; completion is `.coverage`
  ignored and no maintained coverage artifact path added.
- [x] T006: Update `docs/TESTING.md` for R002-R006/AC003-AC004; completion is a
  Coverage Diagnostics section with smoke, focused, and full terminal commands.
- [x] T007: Document the boundaries from R007/N005 in `docs/TESTING.md`;
  completion is explicit text saying coverage is optional, advisory,
  non-blocking, not a routing mechanism, and not user project evidence coverage.
- [x] T008: Confirm MCP and public `p2p` CLI impact for this feature; completion
  is no changes under `src/p2p_engine/mcp/` or `src/p2p_engine/cli.py`, or a
  documented reason if implementation discovers an unexpected need.
- [x] T009: Confirm script impact for D004-D005/R008; completion is either no
  changes to `scripts/test-*.sh` or a documented reason and matching validation
  if a script change becomes necessary.
- [x] T010: Run the smoke coverage diagnostic for R002/AC008:
  `./scripts/test-smoke.sh --cov=src/p2p_engine --cov-report=term-missing`;
  completion is terminal coverage output reviewed.
- [x] T011: Run the focused coverage diagnostic for R003:
  `.venv/bin/pytest -m "(unit or service or adapter) and not slow" --cov=src/p2p_engine --cov-report=term-missing`;
  completion is terminal coverage output reviewed.
- [x] T012: Run existing smoke validation without coverage for R008/AC006:
  `./scripts/test-smoke.sh`; completion is a passing result.
- [x] T013: Run existing focused validation without coverage for R008/AC007:
  `./scripts/test-focused.sh`; completion is a passing result.
- [x] T014: Run public-contract validation only if implementation changes CLI,
  MCP, scripts, persisted artifacts, or public documentation behavior beyond
  testing docs; completion is `./scripts/test-public.sh` passing or an explicit
  not-applicable note.
- [x] T015: Run full-suite validation before handoff:
  `./scripts/test-full.sh`; completion is a passing result or an explicit
  residual-risk note if deferred.
- [x] T016: Check the final diff for AC005; completion is no fail-under
  threshold, CI gate, HTML report, XML report, or generated report artifact
  requirement.
- [x] T017: Record implementation evidence in the final handoff summary;
  completion is a concise list of dependency/docs changes and the focused,
  smoke, coverage, public-contract, and full validation evidence that was run or
  explicitly deferred.

## Implementation Evidence

- Dependency update: `pytest-cov>=5.0.0` added to the `dev` extra in
  `pyproject.toml`; runtime dependencies unchanged.
- Environment refresh: `.venv/bin/python -m pip install -e ".[dev]"` installed
  `pytest-cov 7.1.0` and `coverage 7.15.1`.
- Coverage option check: `.venv/bin/pytest --help` lists `--cov` and
  `--cov-report`.
- Smoke coverage diagnostic:
  `./scripts/test-smoke.sh --cov=src/p2p_engine --cov-report=term-missing`
  passed with `14 passed, 607 deselected`.
- Focused coverage diagnostic:
  `.venv/bin/pytest -m "(unit or service or adapter) and not slow" --cov=src/p2p_engine --cov-report=term-missing`
  passed with `333 passed, 288 deselected`.
- Existing smoke validation: `./scripts/test-smoke.sh` passed with `14 passed,
  607 deselected`.
- Existing focused validation: `./scripts/test-focused.sh` passed with
  `333 passed, 288 deselected`.
- Public-contract validation: not run as a separate command because no `p2p`
  CLI, MCP, script, persisted artifact, Git/sync, validation finding, or runtime
  contract changed; the full suite below still covered public tests.
- Full validation: `./scripts/test-full.sh` passed with `621 passed`.
- Artifact check: `.coverage` is ignored by `.gitignore`; no HTML/XML report or
  maintained coverage artifact was added.

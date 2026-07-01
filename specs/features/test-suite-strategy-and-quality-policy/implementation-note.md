# Implementation Note - test-suite-strategy-and-quality-policy

## Summary

Implemented a local test-suite policy and selection strategy without changing
runtime behavior.

The implementation keeps the full suite as the final confidence gate, introduces
pytest markers for useful subsets, adds scripts and documentation for supported
validation tiers, and creates a durable test quality skill for future work.

## Design Choices

- Marker-based selection was implemented before any file split.
- Initial markers are assigned centrally in `tests/conftest.py` to avoid
  mechanical churn across 46 test files.
- `tests/test_cli.py` and `tests/test_mcp.py` were reviewed and kept intact for
  this slice. They are large public-contract files, but central markers now make
  them selectable without forcing a behavior-preserving move.
- No new test infrastructure dependency was added.
- No production code under `src/` was changed.
- Managed `.p2p/` state was not edited.

## Marker Coverage

Collection checks after marker introduction:

```text
cli: 105/462 tests collected
mcp: 82/462 tests collected
git: 140/462 tests collected
smoke: 14/462 tests collected
focused default: 212/462 tests collected
```

The public-contract script selects 187 tests because some tests outside the main
CLI/MCP files also exercise public CLI or MCP contracts.

## Files Added

- `docs/TESTING.md`
- `scripts/test-focused.sh`
- `scripts/test-public.sh`
- `scripts/test-smoke.sh`
- `scripts/test-full.sh`
- `specs/skills/TEST_QUALITY_SKILL.md`
- `specs/features/test-suite-strategy-and-quality-policy/test-suite-inventory.md`
- `specs/features/test-suite-strategy-and-quality-policy/implementation-note.md`
- `tests/conftest.py`

## Files Updated

- `AGENTS.md`
- `AGENTS-p2p-dev-specs.md`
- `pyproject.toml`
- `specs/features/_template/tasks.md`
- `specs/features/test-suite-strategy-and-quality-policy/design.md`
- `specs/features/test-suite-strategy-and-quality-policy/tasks.md`

## Validation

```text
./scripts/test-focused.sh
212 passed, 250 deselected in 6.26s

./scripts/test-public.sh
187 passed, 275 deselected in 60.77s

./scripts/test-smoke.sh
14 passed, 448 deselected in 0.61s

./scripts/test-full.sh
462 passed in 67.18s
```

## Residual Risks

- Public-contract validation is still expensive because `tests/test_cli.py` and
  `tests/test_mcp.py` intentionally cover broad public surfaces.
- A future slice may split CLI/MCP by command or handler family if ownership or
  CI runtime requires narrower boundaries.
- Marker assignment is centralized; if a future test needs finer-grained marker
  behavior, it should use explicit local marks and update the policy if needed.

## Engineering Quality Review

- Public behavior was preserved.
- No runtime code was changed.
- No dependency was added.
- No broad test file split was mixed into the marker/policy implementation.
- The full suite passed after collection behavior changed.

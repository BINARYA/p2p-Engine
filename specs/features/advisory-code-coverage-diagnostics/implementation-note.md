# Implementation Note - advisory-code-coverage-diagnostics

## Summary

Implemented the advisory coverage diagnostic as development tooling and
documentation only.

## Changes

- Added `pytest-cov>=5.0.0` to the `dev` optional dependency group in
  `pyproject.toml`.
- Added a Coverage Diagnostics section to `docs/TESTING.md`.
- Kept existing validation scripts unchanged.
- Kept runtime package dependencies unchanged.
- Did not add P2P CLI, MCP, CI, threshold, HTML, XML, or generated report
  behavior.

## Validation

- `.venv/bin/python -m pip install -e ".[dev]"`: installed `pytest-cov 7.1.0`
  and `coverage 7.15.1`.
- `.venv/bin/python -c "import pytest_cov; print(pytest_cov.__version__)"`:
  printed `7.1.0`.
- `.venv/bin/pytest --help`: listed `--cov` and `--cov-report`.
- `./scripts/test-smoke.sh --cov=src/p2p_engine --cov-report=term-missing`:
  `14 passed, 607 deselected`.
- `.venv/bin/pytest -m "(unit or service or adapter) and not slow" --cov=src/p2p_engine --cov-report=term-missing`:
  `333 passed, 288 deselected`.
- `./scripts/test-smoke.sh`: `14 passed, 607 deselected`.
- `./scripts/test-focused.sh`: `333 passed, 288 deselected`.
- `./scripts/test-full.sh`: `621 passed`.

## Public Surface

No public `p2p` CLI behavior changed. No MCP behavior changed. No persisted P2P
state layout changed. The only maintained public documentation change is
developer testing guidance.

## Residual Risk

Coverage output is intentionally advisory. There is no fail-under threshold or
CI gate in this slice, so low coverage cannot fail validation by itself.

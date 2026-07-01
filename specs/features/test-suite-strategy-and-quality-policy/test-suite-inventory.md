# Test Suite Inventory

## Baseline

- Date: 2026-07-01
- Test files: 46
- Collected tests: 462
- Collection command: `.venv/bin/pytest --collect-only -q`
- Collection result: `462 tests collected in 0.27s`
- Full-suite runtime after marker introduction:
  `462 passed in 67.18s`
- Focused validation after marker introduction:
  `212 passed, 250 deselected in 6.26s`
- Public-contract validation after marker introduction:
  `187 passed, 275 deselected in 60.77s`
- Smoke validation after marker introduction:
  `14 passed, 448 deselected in 0.61s`

## Largest Files By Test Count

- `tests/test_cli.py`: 103 tests
- `tests/test_mcp.py`: 52 tests
- `tests/test_work_branch_service.py`: 37 tests
- `tests/test_proposal_branch_service.py`: 28 tests
- `tests/test_validation_service.py`: 18 tests
- `tests/test_agent_instructions_service.py`: 16 tests
- `tests/test_skeleton.py`: 14 tests
- `tests/test_readiness_service.py`: 13 tests
- `tests/test_project_interaction_style_service.py`: 13 tests
- `tests/test_foundation_helpers.py`: 10 tests

## Largest Files By Line Count

- `tests/test_cli.py`: 4336 lines
- `tests/test_mcp.py`: 1863 lines
- `tests/test_work_branch_service.py`: 961 lines
- `tests/test_proposal_branch_service.py`: 866 lines
- `tests/test_readiness_service.py`: 525 lines
- `tests/test_agent_instructions_service.py`: 282 lines
- `tests/test_skeleton.py`: 261 lines
- `tests/test_validation_service.py`: 254 lines
- `tests/test_sync_service.py`: 242 lines
- `tests/test_project_verticals.py`: 217 lines

## Observations

- The suite is not too large to keep, but it is too undifferentiated for fast
  daily feedback.
- Public-surface coverage is concentrated in `tests/test_cli.py` and
  `tests/test_mcp.py`.
- Git and managed-collaboration behavior appears both in dedicated service tests
  and in CLI/MCP public-contract tests.
- Before this feature, pytest markers were not registered in `pyproject.toml`.
  Existing marker usage was limited to parametrization.
- The first production-safe improvement is marker-based selection with docs and
  scripts. Splitting large files should be done only after marker intent is
  visible and stable.

## Split Review

`tests/test_cli.py` and `tests/test_mcp.py` are intentionally broad
public-contract files. They can be split later by command family or MCP handler,
but the first implementation slice keeps them intact and marks them clearly.

Reason: central marker assignment gives focused selection immediately without a
large behavior-preserving file move. Splitting is still useful later if these
files keep growing or if CI needs narrower ownership boundaries.

This review satisfies the current production-safety goal without a file split:
the largest files are now selectable through `cli`, `mcp`, `integration`, and
`slow` markers, and focused development no longer needs to run them by default.

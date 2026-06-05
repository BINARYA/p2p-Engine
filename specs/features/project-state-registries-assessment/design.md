# Design - Project State Registries Assessment

## Requirements Covered

- R001, R002, R003, R004, R005, R006

## Key Decisions

- D001: Generated project state is derived from accepted memory.
  Rationale: project state should be rationalized but not replace proposal and
  decision history.

- D002: Registries are deterministic indexes.
  Rationale: agents need compact lookup surfaces without scanning all P2P files.

## Components

- `src/p2p_engine/cli.py`
  - `project`, `registry`, `validate`, `assess`, `project rubrics`,
    `project brief`, `next`.
- `src/p2p_engine/storage/filesystem.py`
  - `refresh_project_state`, `refresh_registries`, validation, rubrics,
    maturity, next-action lifecycle.
- `tests/test_cli.py`, `tests/test_mcp.py`
  - project state, registry, assessment, next-action coverage.

## Evidence

- CLI definitions: `src/p2p_engine/cli.py:731`, `src/p2p_engine/cli.py:780`,
  `src/p2p_engine/cli.py:831`, `src/p2p_engine/cli.py:1793`,
  `src/p2p_engine/cli.py:1805`, `src/p2p_engine/cli.py:1835`,
  `src/p2p_engine/cli.py:2076`, `src/p2p_engine/cli.py:2118`,
  `src/p2p_engine/cli.py:2771`, `src/p2p_engine/cli.py:2783`.
- Storage behavior: `src/p2p_engine/storage/filesystem.py:3202`,
  `src/p2p_engine/storage/filesystem.py:3376`,
  `src/p2p_engine/storage/filesystem.py:5129`,
  `src/p2p_engine/storage/filesystem.py:5408`.
- Tests: `tests/test_cli.py:774`, `tests/test_cli.py:1602`,
  `tests/test_cli.py:1866`, `tests/test_cli.py:3680`,
  `tests/test_cli.py:3760`, `tests/test_cli.py:3832`,
  `tests/test_mcp.py:1180`, `tests/test_mcp.py:1251`.

## Risks

- Derived state can become stale if refresh commands are not run.
- Broad generated outputs can be mistaken for implementation state without the
  binding method.

# Design - Intake Choice Conflict Next

## Requirements Covered

- R001, R002, R003, R004, R005

## Key Decisions

- D001: Intake converts rough ideas into advisory recommendations, not
  decisions.
  Rationale: owners control governance outcomes.

- D002: Choices and blockers are explicit project artifacts.
  Rationale: blocked proposals and alternatives should be visible to agents and
  humans.

## Components

- `src/p2p_engine/cli.py`
  - `intake`, `intake apply`, `choice`, `impact`, `conflict`, `next`.
- `src/p2p_engine/storage/filesystem.py`
  - intake prompt/apply, choice management, conflict memory, next actions.
- `tests/test_cli.py`, `tests/test_mcp.py`
  - coverage for intake, choice, conflict, impact, next.

## Evidence

- CLI definitions: `src/p2p_engine/cli.py:2155`,
  `src/p2p_engine/cli.py:2184`, `src/p2p_engine/cli.py:2851`,
  `src/p2p_engine/cli.py:2898`, `src/p2p_engine/cli.py:2958`,
  `src/p2p_engine/cli.py:3062`, `src/p2p_engine/cli.py:3079`,
  `src/p2p_engine/cli.py:3122`.
- Storage behavior: `src/p2p_engine/storage/filesystem.py:5555`,
  `src/p2p_engine/storage/filesystem.py:5647`,
  `src/p2p_engine/storage/filesystem.py:5799`,
  `src/p2p_engine/storage/filesystem.py:5129`.
- Tests: `tests/test_cli.py:3317`, `tests/test_cli.py:3352`,
  `tests/test_cli.py:3424`, `tests/test_cli.py:3504`,
  `tests/test_cli.py:3760`, `tests/test_mcp.py:1384`,
  `tests/test_mcp.py:1417`, `tests/test_mcp.py:1443`.

## Risks

- Advisory output can be mistaken for decisions; command names and docs must
  keep the boundary explicit.

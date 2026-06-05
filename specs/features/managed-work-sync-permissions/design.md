# Design - Managed Work Sync Permissions

## Requirements Covered

- R001, R002, R003, R004, R005, R006

## Key Decisions

- D001: Change Sets and Work are user-facing abstractions over operational work.
  Rationale: users and agents should not need raw Git as the default interface.

- D002: Git remains the persistence and collaboration adapter.
  Rationale: branches and commits provide audit while P2P controls workflow.

- D003: Consent receipts gate owner-sensitive operations.
  Rationale: publishing, merging, cleanup, and sync can alter shared state.

## Components

- `src/p2p_engine/cli.py`
  - `change`, `work`, `sync`, `permissions`, `consent`, `project remote`.
- `src/p2p_engine/storage/filesystem.py`
  - Change Set metadata, Work manifests/lifecycle, sync, consent.
- `src/p2p_engine/storage/git.py`
  - Git subprocess boundary.
- `tests/test_cli.py`, `tests/test_mcp.py`
  - lifecycle, sync, permission-gated operation tests.

## Evidence

- CLI definitions: `src/p2p_engine/cli.py:1848`,
  `src/p2p_engine/cli.py:1892`, `src/p2p_engine/cli.py:1962`,
  `src/p2p_engine/cli.py:1993`, `src/p2p_engine/cli.py:2224`,
  `src/p2p_engine/cli.py:2476`, `src/p2p_engine/cli.py:2543`,
  `src/p2p_engine/cli.py:2582`, `src/p2p_engine/cli.py:2667`.
- Storage behavior: `src/p2p_engine/storage/filesystem.py:1211`,
  `src/p2p_engine/storage/filesystem.py:1553`,
  `src/p2p_engine/storage/filesystem.py:4225`,
  `src/p2p_engine/storage/filesystem.py:5252`.
- Tests: `tests/test_cli.py:1749`, `tests/test_cli.py:1809`,
  `tests/test_cli.py:2119`, `tests/test_cli.py:2282`,
  `tests/test_cli.py:2369`, `tests/test_cli.py:2460`,
  `tests/test_cli.py:2558`, `tests/test_cli.py:2684`,
  `tests/test_cli.py:2941`, `tests/test_cli.py:3096`,
  `tests/test_cli.py:3148`, `tests/test_cli.py:3184`.

## Risks

- Work lifecycle is powerful and can overlap with the local `specs/` coding
  workflow. For this repository, implementation tasks belong in `specs/`, not
  Work manifests.

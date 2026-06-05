# Design - CLI Proposal Governance

## Requirements Covered

- R001, R002, R003, R004, R005, R006

## Key Decisions

- D001: Keep proposal governance as file-backed CLI behavior.
  Rationale: P2P Engine is local and deterministic; Git and files provide audit.

- D002: Separate proposal contributions from proposal decisions.
  Rationale: agents and contributors can add context without taking
  owner-controlled actions.

## Components

- `src/p2p_engine/cli.py`
  - command groups: `init`, `proposal`, `contribution`, `decision`,
    `governance`, `vote`, `swot`, `precedent`.
- `src/p2p_engine/storage/filesystem.py`
  - workspace creation, proposal persistence, decision records, contribution
    files, governance artifacts.
- `tests/test_cli.py`
  - CLI behavior coverage for init, proposal, contribution, decision, and
    governance surfaces.

## Evidence

- CLI command definitions: `src/p2p_engine/cli.py:218`,
  `src/p2p_engine/cli.py:885`, `src/p2p_engine/cli.py:951`,
  `src/p2p_engine/cli.py:966`, `src/p2p_engine/cli.py:1326`,
  `src/p2p_engine/cli.py:1387`, `src/p2p_engine/cli.py:1485`,
  `src/p2p_engine/cli.py:1682`.
- Storage behavior: `src/p2p_engine/storage/filesystem.py:734`,
  `src/p2p_engine/storage/filesystem.py:2763`,
  `src/p2p_engine/storage/filesystem.py:2898`.
- Tests: `tests/test_cli.py:22`, `tests/test_cli.py:1232`,
  `tests/test_cli.py:1296`, `tests/test_cli.py:1363`.

## Risks

- Most behavior is concentrated in `filesystem.py`; future refactoring should
  preserve CLI compatibility with focused tests.

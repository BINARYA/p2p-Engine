# Design - Legacy Software Spec Export

## Requirements Covered

- R001, R002, R003, R004

## Key Decisions

- D001: Treat this as implemented legacy/software-only behavior.
  Rationale: the code and tests exist, but the desired future path is
  domain-aware project definition export.

- D002: Keep compatibility evidence separate from future export requirements.
  Rationale: otherwise current implementation can obscure the product boundary
  correction.

## Components

- `src/p2p_engine/cli.py`
  - `spec refresh/status/show/prompt/import/export/export-status/export-show/export-validate`.
- `src/p2p_engine/storage/filesystem.py`
  - software-spec generation, export files, validation.
- `tests/test_cli.py`, `tests/test_mcp.py`
  - software-spec and export coverage.

## Evidence

- CLI definitions: `src/p2p_engine/cli.py:2340`,
  `src/p2p_engine/cli.py:2356`, `src/p2p_engine/cli.py:2368`,
  `src/p2p_engine/cli.py:2381`, `src/p2p_engine/cli.py:2396`,
  `src/p2p_engine/cli.py:2412`, `src/p2p_engine/cli.py:2456`.
- Storage behavior: `src/p2p_engine/storage/filesystem.py:3964`,
  `src/p2p_engine/storage/filesystem.py:4090`,
  `src/p2p_engine/storage/filesystem.py:4166`,
  `src/p2p_engine/storage/filesystem.py:8870`.
- Tests: `tests/test_cli.py:1935`, `tests/test_mcp.py:1498`.

## Migration And Compatibility

This feature should remain factual until the domain-aware export feature
replaces the recommended workflow. Future implementation should update docs and
skills to label this workflow software-only or compatibility.

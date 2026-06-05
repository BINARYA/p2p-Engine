# Design - Proposal Readiness And Prompts

## Requirements Covered

- R001, R002, R003, R004, R005

## Key Decisions

- D001: Readiness is advisory and deterministic.
  Rationale: owners retain governance control while agents receive concrete
  quality gaps.

- D002: Prompt workflows are file/prompt-only.
  Rationale: P2P Engine keeps direct AI invocation outside core runtime.

## Components

- `src/p2p_engine/cli.py`
  - `proposal readiness`, `explore`, `digest`, `clarify`, `synthesize`,
    `plan`, `tasks`, `swot`, `impact`, `context`.
- `src/p2p_engine/prompts/`
  - prompt text generation modules.
- `src/p2p_engine/storage/filesystem.py`
  - readiness profiles, assessments, imports, context packets.
- `tests/test_cli.py`, `tests/test_mcp.py`
  - readiness, prompt, context behavior.

## Evidence

- CLI command definitions: `src/p2p_engine/cli.py:657`,
  `src/p2p_engine/cli.py:1024`, `src/p2p_engine/cli.py:1037`,
  `src/p2p_engine/cli.py:1053`, `src/p2p_engine/cli.py:1067`,
  `src/p2p_engine/cli.py:1509`, `src/p2p_engine/cli.py:1561`,
  `src/p2p_engine/cli.py:1574`, `src/p2p_engine/cli.py:1601`,
  `src/p2p_engine/cli.py:1628`, `src/p2p_engine/cli.py:1655`.
- Storage behavior: `src/p2p_engine/storage/filesystem.py:2542`.
- Tests: `tests/test_cli.py:1188`, `tests/test_cli.py:1453`,
  `tests/test_mcp.py:1199`, `tests/test_mcp.py:1229`,
  `tests/test_mcp.py:1563`.

## Risks

- Readiness may remain weak when artifacts are thin. Agents must convert gaps
  into refinement work rather than treating scores as decisions.

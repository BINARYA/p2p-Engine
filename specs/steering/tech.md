# Tech Steering

## Runtime

- Language: Python 3.11+
- CLI framework: Typer
- Terminal output: Rich
- YAML handling: PyYAML
- Packaging: Hatchling

## Entry Points

- CLI: `p2p = p2p_engine.cli:app`
- MCP server: `p2p-mcp-server = p2p_engine.mcp.server:main`

## Main Runtime Surfaces

- `src/p2p_engine/cli.py`: Typer command groups for init, proposals,
  readiness, prompts, governance, project state, registries, intake, choices,
  changes, specs, work, sync, permissions, consent, agents, assessments, and
  next actions.
- `src/p2p_engine/storage/filesystem.py`: filesystem-backed workspace behavior,
  generated artifacts, validation, and most domain logic.
- `src/p2p_engine/mcp/tools.py`: MCP tool definitions and dispatch.
- `src/p2p_engine/prompts/`: prompt generators for advisory workflows.

## Verification

Use the project test suite for behavior changes:

```bash
.venv/bin/python -m pytest
```

Focused tests are acceptable for narrow changes:

```bash
.venv/bin/python -m pytest tests/test_cli.py
.venv/bin/python -m pytest tests/test_mcp.py
```

## Implementation Constraints

- Keep P2P state mutations behind CLI or explicit MCP tools.
- Do not hand-edit managed `.p2p/` internals for implementation work.
- Prefer small behavior changes with direct CLI/MCP tests.
- Avoid adding new abstraction layers unless they remove real duplication or
  clarify a product boundary.
- Do not mark tasks complete in `specs/features/*/tasks.md` unless the evidence
  can be traced to `src/`, `tests`, `docs`, or observed CLI behavior.

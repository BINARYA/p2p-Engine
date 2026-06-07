# CLI Command Module Split Design

## Current Shape

`src/p2p_engine/cli.py` currently owns:

- Typer app and sub-app construction;
- command registration;
- command implementations;
- shared output helpers;
- error handling;
- runtime diagnostics;
- domain-specific formatting.

This makes small CLI changes expensive to review and increases the risk of unrelated regressions.

## Target Shape

Keep `src/p2p_engine/cli.py` as the compatibility facade that exposes `app`.

Introduce shared helper modules before moving command groups:

- `src/p2p_engine/cli_shared.py`: console, workspace factory, CLI failure, YAML rendering.

Then extract command groups into modules that expose registration functions, for example:

- `cli_commands/doctor.py`;
- `cli_commands/agents.py`;
- `cli_commands/next_actions.py`;
- `cli_commands/project.py`;
- `cli_commands/proposals.py`;
- `cli_commands/collaboration.py`;
- `cli_commands/work_specs.py`.

Each command module should receive the Typer app or sub-app it needs and register commands there. During the split, `cli.py` remains the only external entry point.

## First Extraction

The first extraction is intentionally small:

- move shared CLI helpers to `cli_shared.py`;
- update `cli.py` imports;
- keep all command definitions in `cli.py`;
- run focused CLI tests and full suite.

This lowers risk before moving decorated Typer functions.

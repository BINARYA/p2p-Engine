# CLI Collaboration Command Domain Split Requirements

## Purpose

Split `src/p2p_engine/cli_commands/collaboration.py` by CLI command domain
while preserving the public CLI surface.

This is a local development refactoring feature. It does not mutate `.p2p/`
state and does not change P2P governance behavior.

## Requirements

- R001: Preserve `register_collaboration_commands(...)` as the public
  registration function imported by `cli.py`.
- R002: Preserve all governance, vote, precedent, impact, conflict, registry,
  intake, intake apply, and choice command names, options, help text, output,
  and exit behavior.
- R003: Split implementation by CLI domain: governance, project analysis,
  registries, intake, and choices.
- R004: Keep CLI modules as presentation glue only.
- R005: Update local refactoring tracker and task checklist with verification
  evidence.

## Non-Goals

- This feature does not add or remove CLI commands.
- This feature does not change services, MCP handlers, or P2P state files.

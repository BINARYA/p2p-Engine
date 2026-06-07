# CLI Work/Spec Command Domain Split Requirements

## Purpose

Split `src/p2p_engine/cli_commands/work_specs.py` by CLI command domain while
preserving the existing public CLI surface.

This is a local development refactoring feature. It does not mutate `.p2p/`
state and does not change P2P governance behavior.

## Requirements

- R001: Preserve `register_work_spec_commands(change_app, spec_app, work_app)`
  as the public registration function imported by `cli.py`.
- R002: Preserve all existing `p2p change`, `p2p spec`, and `p2p work` command
  names, options, arguments, help text, output text, and exit behavior.
- R003: Split implementation by CLI domain:
  `change`, `spec`, and `work`.
- R004: Keep CLI modules as presentation glue only; do not move domain behavior
  out of services or `P2PWorkspace`.
- R005: Preserve `WorkAcceptConflict` handling for `p2p work accept`.
- R006: Update local refactoring tracker and task checklist with verification
  evidence.

## Non-Goals

- This feature does not add or remove CLI commands.
- This feature does not change MCP handlers.
- This feature does not change software spec, Change Set, or Work service
  behavior.

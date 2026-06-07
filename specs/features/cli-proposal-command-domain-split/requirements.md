# CLI Proposal Command Domain Split Requirements

## Purpose

Split `src/p2p_engine/cli_commands/proposals.py` by proposal command domain
while preserving the public CLI surface.

This is a local development refactoring feature. It does not mutate `.p2p/`
state and does not change P2P governance behavior.

## Requirements

- R001: Preserve `register_proposal_commands(...)` as the public registration
  function imported by `cli.py`.
- R002: Preserve all existing `p2p proposal`, `p2p proposal readiness`,
  `p2p contribution`, `p2p proposal contribution`, and `p2p decision` command
  names, options, arguments, help text, output text, and exit behavior.
- R003: Split implementation by CLI domain: proposal core, readiness, branch
  lifecycle, decisions, and contributions.
- R004: Keep CLI modules as presentation glue only; do not move service/domain
  behavior.
- R005: Preserve `ProposalMergeConflict` handling and readiness override warning
  behavior.
- R006: Update local refactoring tracker and task checklist with verification
  evidence.

## Non-Goals

- This feature does not add or remove proposal CLI commands.
- This feature does not change proposal services, MCP handlers, or P2P state
  files.

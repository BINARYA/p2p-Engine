# CLI Command Module Split Requirements

## Goal

Split the large Typer CLI implementation into smaller modules while keeping the public `p2p` command surface unchanged.

## Requirements

- `src/p2p_engine/cli.py` must remain the importable public CLI app module.
- Existing command names, options, help behavior, and output semantics must remain compatible.
- Command modules must depend on shared CLI helpers instead of duplicating console, workspace, YAML, and error handling code.
- Extraction must be incremental and test-backed by command group.
- Each moved command group must keep its existing service/facade calls unchanged unless a local spec explicitly requires behavior changes.

## Non-Goals

- Do not redesign the CLI UX.
- Do not change Typer command names or option names.
- Do not move P2P governance state or write `.p2p` files by hand.
- Do not combine this work with new runtime services.

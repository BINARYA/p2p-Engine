# Findings - PROP-092

## Current System Position

P2P Engine already has a complete CLI Work lifecycle: plan, branch, submit, review, publish, request-review, accept, finalize, cleanup, retire, list, status, show, and scan.

P2P MCP already has a permission-gated pattern for proposal branch operations and managed sync. That pattern validates a consent receipt, executes a domain operation, consumes the receipt with structured result metadata, and records audit state.

Work MCP coverage is currently incomplete. Agents can inspect Work state and create Work plans through MCP, but they cannot complete the operational lifecycle through local MCP without returning to CLI or using an unsafe raw Git escape hatch.

## Architectural Finding

The system should separate adapters, not duplicate lifecycle logic. The CLI, local MCP adapter, and future Wavekit remote gateway must all call the same Work lifecycle command layer or service methods.

## Security Finding

The local MCP adapter can expose the complete catalog because it operates in the self-managed local project context. That does not mean it has unrestricted authority. Every mutating tool must still validate Work state, branch context, consent, and operation target.

## Product Boundary Finding

Remote MCP is a different product boundary. It involves authenticated users, client identity, grants, rate limits, hosted projects, external agents, commercial policy, and anti-abuse controls. Those concerns belong in Wavekit or a separate gateway layer.


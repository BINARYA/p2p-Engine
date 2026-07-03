# Exploration - PROP-092

PROP-092 resolves the NEXT-004 product decision by choosing local MCP Work lifecycle parity while keeping remote multi-user MCP outside the P2P Engine core.

The core issue is not whether agents should be able to drive the Work lifecycle. They already can drive many repository-sensitive operations through the CLI and through permission-gated proposal MCP tools. The issue is where authority and transport boundaries belong.

The selected direction is:

- P2P Engine core remains local-first and deterministic.
- CLI and local MCP are adapters over the same Work lifecycle command layer.
- Local MCP exposes the full Work lifecycle through domain-specific P2P tools.
- Mutating local MCP operations are state-gated, consent-gated, and audit-aware.
- Remote Wavekit MCP is a future gateway/control-plane adapter, not a P2P core responsibility.

This keeps the local agent-first workflow complete without loading the P2P core with remote authentication, OAuth, tenant isolation, billing, client registration, or hosted-project abuse controls.


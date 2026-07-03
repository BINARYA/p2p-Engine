# Suggested Scope - PROP-092

## In Scope

- Local MCP Work lifecycle parity for existing CLI Work transitions.
- New domain-specific local MCP tools for Work branch, submit, review, publish, request-review, accept, finalize, and cleanup.
- Reuse of existing Work lifecycle services or a shared command layer.
- Consent receipt validation for privileged and owner-controlled Work operations.
- Structured responses for success, conflict, consent, governance, and effect metadata.
- Explicit fail-closed behavior for invalid state, branch, worktree, remote, manifest, or receipt conditions.
- Documentation that distinguishes local MCP parity from remote Wavekit MCP.
- Tests covering the public MCP surface and representative failure modes.

## Out Of Scope

- Remote HTTP MCP server inside P2P Engine core.
- OAuth, dynamic client registration, Wavekit login, hosted project tenancy, billing, global rate limiting, and abuse prevention.
- Provider PR/MR creation or provider-side review object creation.
- Generic raw Git tools.
- Arbitrary branch, commit, reset, clean, force-push, or merge commands.
- Rewriting the Work lifecycle state machine.
- Changing the owner-controlled governance model.

## Boundary Statement

P2P Engine core should be MCP-ready and include local MCP parity. Wavekit remote MCP should be a separate gateway that reuses the same command layer while applying authenticated users, client identity, grants, scoped receipts, audit retention, rate limits, and commercial collaboration policy.


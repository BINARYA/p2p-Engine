# Risks - PROP-092

## Raw Git Bypass

Risk: agents may use raw Git commands instead of P2P lifecycle tools if Work MCP coverage remains incomplete.

Mitigation: expose domain-specific Work MCP tools and explicitly exclude arbitrary Git tools.

## Confused Deputy

Risk: an agent has tool access but not legitimate authority for an owner-controlled action.

Mitigation: require consent receipts for privileged and owner-controlled Work operations. Future Wavekit remote MCP must add authenticated principal, client identity, grants, scoped receipts, and server-side audit.

## TOCTOU

Risk: Work or repository state changes after consent is granted but before execution.

Mitigation: fail closed on wrong Work status, wrong current branch, dirty worktree, missing branch, missing remote, malformed manifest, and receipt mismatch. Expected commit SHA binding should be considered for stronger future receipts.

## Merge Conflict Ambiguity

Risk: MCP accept could hide or mishandle merge conflicts.

Mitigation: preserve existing Work accept conflict semantics and return structured conflict output. Do not finalize or cleanup after a conflict.

## Cleanup Destructiveness

Risk: cleanup can delete local and optionally remote managed branches.

Mitigation: keep cleanup separate from finalize, make remote deletion explicit, consent-gate cleanup, and return local_deleted and remote_deleted metadata.

## Remote Scope Creep

Risk: local MCP parity could become a pretext for putting remote HTTP MCP, OAuth, Wavekit users, billing, and multi-tenancy into the P2P core.

Mitigation: make the remote gateway boundary explicit in the proposal. P2P core is MCP-ready and local-MCP capable; remote multi-user MCP belongs to Wavekit or another external gateway.

## Duplicated State Machine

Risk: CLI, MCP, and future Wavekit adapters each implement their own Work logic.

Mitigation: adapters must call shared Work lifecycle services or a shared command layer. No duplicate Work state machine per adapter.


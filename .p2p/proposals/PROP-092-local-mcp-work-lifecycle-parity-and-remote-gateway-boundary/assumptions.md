# Assumptions - PROP-092

- The existing CLI Work lifecycle is the behavioral source for local MCP parity.
- Local MCP is an adapter distributed with P2P Engine and intended primarily for same-machine, self-managed, owner-controlled workflows.
- Project-declared permissions and consent receipts are sufficient for the local MVP, consistent with PROP-066.
- Strong remote identity, OAuth, client registration, grants, rate limits, billing, and tenant isolation are Wavekit gateway concerns, not core P2P concerns.
- Provider PR/MR creation is out of scope and remains a future adapter decision.
- Existing Work lifecycle services already enforce key state and repository preconditions and should be reused.
- Existing proposal-branch MCP consent/audit patterns provide a suitable implementation precedent.
- The owner remains the final authority over owner-controlled actions.


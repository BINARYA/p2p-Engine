# Alternatives - PROP-092

## Alternative A - Keep Work lifecycle CLI-only

Keep the Work lifecycle available only through CLI commands.

Benefits:

- Lowest implementation cost.
- No new MCP mutating surface.
- Avoids new consent/audit tests.

Costs:

- Agent-first local workflows remain incomplete.
- Agents must hand control back to a shell user for key lifecycle steps.
- External integrations may be tempted to use raw Git commands.
- MCP remains inconsistent: proposal branches have permission-gated lifecycle tools, Work items do not.

Verdict: rejected. It preserves safety by omission, but it weakens the agent-first product direction and leaves a predictable gap.

## Alternative B - Add only read/status Work MCP tools

Expose only list, status, show, scan, and perhaps plan.

Benefits:

- Safe and simple.
- Useful for project visibility.
- No owner-controlled lifecycle operations through MCP.

Costs:

- The current system is already close to this state.
- It does not solve NEXT-004, which is explicitly about Work publish/finalize/accept/cleanup parity.
- It creates a permanent CLI/MCP mismatch.

Verdict: rejected as insufficient.

## Alternative C - Full local MCP Work lifecycle parity with domain gates

Expose the full CLI-backed Work lifecycle through local MCP tools, but only as domain-specific P2P operations with state, consent, branch, remote, and audit gates.

Benefits:

- Completes local agent-first workflows.
- Reuses existing CLI/service behavior.
- Avoids raw Git tools.
- Keeps owner-controlled operations explicit.
- Gives Wavekit a future reusable command contract without putting remote MCP into the core.

Costs:

- Requires careful MCP catalog and handler implementation.
- Requires focused tests for consent consumption, failure modes, merge conflicts, cleanup, and remote handoff.
- Requires clear documentation to avoid confusing local MCP parity with remote multi-user authorization.

Verdict: selected.

## Alternative D - Put remote MCP server into P2P Engine core

Implement HTTP remote MCP, auth, sessions, grants, and multi-user behavior directly in P2P Engine.

Benefits:

- One installable package could expose both local and remote MCP.
- Remote clients might integrate directly.

Costs:

- Pollutes the local-first core with Wavekit/server concerns.
- Introduces OAuth, tenant isolation, rate limits, hosted audit, client registration, and abuse prevention before the core needs them.
- Makes the commercial Wavekit boundary unclear.
- Increases security and operational burden for local users.

Verdict: rejected. Remote MCP should be a separate Wavekit gateway that calls P2P core commands.


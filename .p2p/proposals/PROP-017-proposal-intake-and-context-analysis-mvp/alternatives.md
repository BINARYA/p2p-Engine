# Alternatives - PROP-017

## Alternative A - Manual Intake Only

Users and agents manually inspect `p2p status`, registries and proposal files before creating new proposals.

Pros:

- no new CLI surface;
- simple to understand;
- useful while project is small.

Cons:

- does not scale;
- easy to miss overlaps or accepted decisions;
- weak support for multi-agent collaboration.

## Alternative B - Prompt-Only Intake

The CLI gathers registry/project context and generates an intake prompt. AI output is imported back into `.p2p/intake/`.

Pros:

- fits current MVP architecture;
- no direct AI adapter required;
- keeps auditability;
- lets agents reason over shared context.

Cons:

- still requires manual prompt/output flow;
- quality depends on user importing structured output;
- not fully interactive.

## Alternative C - Direct AI Intake

The CLI directly invokes an AI adapter for intake analysis.

Pros:

- smoother UX;
- can provide immediate recommendations.

Cons:

- requires AI credentials/provider handling;
- harder to test deterministically;
- premature before prompt-only intake proves the model.

## Alternative D - MCP Tooling

Expose intake as MCP tools for Codex, Claude or other agents.

Pros:

- best fit for multi-agent workflows;
- agents call P2P functions directly;
- avoids shell command parsing.

Cons:

- later-stage architecture;
- requires stable P2P tool contracts;
- not necessary for local MVP.

## Preferred Direction

Start with Alternative B: prompt-only intake backed by registries.

This aligns with the current architecture and creates a stable workflow that can later be automated by AI adapters or MCP.

# PROP-055 - Agent Token Budget and Context Discipline

## Status

`accepted`

## Problem

P2P Engine reduces conversational memory by storing governance state in .p2p and Git, but agents can still consume excessive tokens by scanning broad project context, reading full registries, loading many proposal/change files, or explaining artifacts from conversation memory instead of compact deterministic views. This is especially visible in the P2P Engine repository because the project is using P2P to build P2P, but the risk applies to any large P2P workspace used by CLI or MCP agents.

## Context

The product direction is: AI is expensive, CLI is cheap, Git is memory, .p2p is governance, owner decides, and agents work in bounded sessions. Current skills already require using CLI/MCP primitives and avoiding manual .p2p edits, but they do not yet define an explicit token budget discipline or compact context contract for agents.

## Goals

- Define a token-aware operating policy for agents.
- Prefer compact deterministic context views before detailed file reads.
- Make CLI and MCP expose bounded context packets for common agent tasks.
- Prevent agents from scanning unrelated .p2p, source, test, or Git history context when a smaller command output is enough.

## Non-Goals

- Do not remove detailed proposal/change/registry commands.
- Do not introduce autonomous AI decision-making inside the core.
- Do not optimize runtime performance or rewrite the CLI in Rust as part of this proposal.

## Proposal

Introduce an Agent Token Budget and Context Discipline with a narrow MVP based on compact deterministic context packets. The first implementation combines skill policy, CLI context view, and MCP context tool. Agents must read compact summaries first, then details only by explicit ID, and stop once the next bounded action is clear. Add p2p context, p2p context --budget small, p2p context --target ID, and an equivalent p2p_context MCP tool. The context output should include current state, next actions, relevant artifacts, allowed commands, explicit do-not-read guidance, and the smallest sufficient next step. Full repository scans, broad .p2p traversal, full registry reads, source-code exploration, and Git history reads are disallowed unless the user task explicitly requires them or the compact context is insufficient. Advanced token estimation, numeric budgets, read tracking, and model-specific optimization are deferred until after the MVP works in practice.

## Acceptance Criteria

- p2p context returns a compact deterministic context packet.
- p2p context --target ID limits output to one proposal, change, choice, or work target when possible.
- p2p context --budget small omits full document bodies and favors IDs, statuses, commands, and short reasons.
- MCP exposes equivalent compact context through p2p_context.
- Agent skill instructs agents to call compact context before broad file reads.
- The policy explicitly forbids broad scans when a CLI/MCP context command is sufficient.
- Advanced token estimation and numeric token budgets are deferred.

## Decision

Pending.

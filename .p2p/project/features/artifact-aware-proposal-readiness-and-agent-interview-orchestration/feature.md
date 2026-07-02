# Artifact-aware Proposal Readiness And Agent Interview Orchestration

## Provenance

- Proposal: PROP-086
- Source: .p2p/proposals/PROP-086-artifact-aware-proposal-readiness-and-agent-interview-orchestration

## Problem

Agents are willing to explore new proposals, but proposal-side artifacts such as open questions, clarifications, findings, exploration notes, and impact maps often remain nearly empty. Current readiness can mark a proposal decision-ready when the main proposal body is coherent, without making artifact coverage visible as a gap or requiring the agent to explain why an artifact is empty. This weakens auditability, owner prompting, impact analysis, and long-term proposal memory for complex or cross-cutting work.

## Proposal

Introduce artifact-aware proposal readiness backed by a dedicated artifact-specific primitive. Each proposal artifact type receives an expectation class: required for decision, required when applicable, optional memory, or not applicable with reason. The source of truth for artifact applicability is a public CLI/MCP surface such as proposal artifact state commands/tools, not free-form contribution text, not hidden readiness-only metadata, and not direct filesystem writes. Readiness and compact context consume artifact state: they surface empty or weak applicable artifacts as concrete gaps, report not-applicable and legacy reasons, and suggest owner-facing questions. The artifact state lifecycle should include unknown, missing, weak, satisfied, deferred, not_applicable, and absent_legacy. unknown means a new proposal artifact has not yet been assessed. missing means it is applicable but absent or empty. weak means present but insufficient. satisfied means adequate for the current readiness profile. deferred means a known gap is intentionally postponed and must remain visible. not_applicable requires a concrete rationale. absent_legacy marks proposals created before artifact-aware state existed; it is advisory and non-blocking. Artifact state records at least artifact id/type, expectation, status, reason, actor/source, timestamp, risk flags, and whether the state is agent-proposed or owner-confirmed when relevant. Agents may propose artifact status and rationale, but the owner has final authority over governance decisions and acceptance. For always-required or auto-required artifacts, agent-proposed not_applicable or deferred states remain owner-visible and should not be treated as silently equivalent to satisfied. The MVP CLI/MCP surface should be narrow: initialize artifact state for a proposal, show/list artifact coverage, set an artifact expectation/status/reason, mark legacy absence, and expose the same operations through explicit write-safe MCP tools that internally use the P2P engine write path. Example command shape: p2p proposal artifact status PROP-XXX; p2p proposal artifact init PROP-XXX; p2p proposal artifact set PROP-XXX impact-map --expectation required_when_applicable --status not_applicable --reason '...'; p2p proposal artifact mark-legacy PROP-XXX. Exact names may change, but the public primitive must exist before agents are expected to persist artifact state. The default artifact policy is graduated by risk. proposal.md, readiness.yml, and open-questions.md are always required for proposal maturity. clarifications.md, findings.md, exploration.md, and impact-map.yml are required when applicable. findings.md and impact-map.yml become auto-required when robust risk triggers are present: governance or policy changes; public CLI, MCP, API, or command behavior changes; storage schema, registry, proposal layout, or persistent state changes; compatibility or migration impact; cross-module/shared service/core workflow impact; permission, consent, security, remote sync, provider, or destructive-operation concerns; source-of-truth, agent instruction, memory, or artifact-writing behavior changes; user-visible workflow, docs/install/release impact; new dependency/runtime/infrastructure assumptions; high uncertainty, multiple credible alternatives, or claims that depend on technical evidence. exploration.md becomes required when multiple credible alternatives exist, uncertainty is high, or the proposal chooses between materially different designs. clarifications.md becomes required when owner answers correct, narrow, or change an assumption. Existing proposals are handled compatibly: when artifact-aware state is absent, artifact-aware commands, readiness refresh, context generation, or a dedicated migration/status command should detect it and mark/report absent_legacy through the P2P write interface. Legacy absence must not raise validation errors, block decisions, or force manual retroactive completion. Coverage improves naturally for new proposals without requiring review of historical work. Integration boundaries are strict. Agents interact with P2P memory only through the p2p CLI or explicit MCP write tools whose schema describes the mutation. A local agent must follow the same boundary as a future remote MCP client: no direct edits under .p2p, no copying prepared temporary files into artifacts, no reverse-engineering internal layouts, and no filesystem workaround when a primitive is missing. If an artifact update requires large text, the solution is a CLI/MCP import/update primitive, not a temp-file copy into managed state. If no supported primitive exists, the agent stops and reports the missing primitive. Readiness, context, validation, registries, and MCP tools must reuse artifact state rather than duplicating a parallel lifecycle. Validation checks structural consistency; readiness scores maturity; context summarizes next action; artifact state remains the source of truth for artifact coverage. Test coverage should include a new simple proposal, a new cross-cutting proposal that auto-requires findings and impact map, a legacy proposal without artifact state, not_applicable with rationale, deferred with owner visibility, MCP write-safe behavior, missing-primitive refusal, and a guard that direct/temp-file artifact writes are not part of the workflow.

## Decision

# Decision - PROP-086

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted by owner as an explicit readiness override. The current default-readiness-v0.1 score remains weak because it is not artifact-aware, but the owner accepts the refined direction: introduce a dedicated artifact-specific CLI/MCP primitive, graduated-by-risk artifact requirements, default coverage for new proposals, advisory absent_legacy handling for old proposals, strict CLI/MCP-only memory mutation, and tests for readiness/context/MCP/missing-primitive behavior.

## Date

2026-06-09

## Approver

owner

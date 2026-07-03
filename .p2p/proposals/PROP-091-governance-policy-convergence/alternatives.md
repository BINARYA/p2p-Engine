# Alternatives - PROP-091

## Alternative A - Keep Governance Artifacts As Passive Audit Records

Continue with the current model: votes, roles, precedents, blockers, and
permissions are stored and inspectable, but no unified policy evaluation is
introduced.

Pros:

- Minimal implementation effort.
- No compatibility risk.
- Avoids introducing a new policy service.

Cons:

- Agents and MCP clients lack a stable governance preflight contract.
- Vote conflicts, active blockers, and precedents remain fragmented.
- The owner lacks a single structured view before decision finalization.
- The system remains artifact-rich but policy-weak.

Assessment: insufficient for production-grade governance transparency.

## Alternative B - Full Governance Enforcement

Implement stronger governance rules immediately: quorum, weighted voting,
deadlines, delegations, automatic vote enforcement, strict consensus, and
mandatory override rationale for all contrary signals.

Pros:

- Strong formal governance semantics.
- Clear decision mechanics for multi-owner or committee-driven projects.

Cons:

- Premature for the current project stage.
- High compatibility and complexity risk.
- Could confuse owner authority with voting machinery.
- Requires deeper identity, authority, delegation, and remote enforcement model.

Assessment: too heavy for the current phase.

## Alternative C - Governance Policy Convergence With Owner Authority

Introduce deterministic preflight evaluation across permissions, governance,
choices, votes, blockers, and precedents. Keep `owner_decides` as default.
Treat votes and precedents as transparent warning/context. Treat structural
invalidity and unauthorized actors as blocking errors. Treat active explicit
blockers as normal-flow blocks overrideable only by owner rationale.

Pros:

- Gives agents and tools a stable contract.
- Keeps owner authority clear.
- Makes vote alignment or conflict visible.
- Preserves deterministic CLI behavior.
- Avoids premature democratic enforcement.
- Provides a migration path from legacy `roles.yml` to `permissions.yml`.

Cons:

- Requires a new policy-evaluation boundary.
- Requires schema and validation decisions.
- Does not solve advanced multi-owner governance yet.

Assessment: recommended.

## Alternative D - Agent Or UI Soft Governance Only

Leave the core unchanged and let Wavekit or agents infer governance context from
titles, text, votes, and precedents.

Pros:

- Flexible.
- Can support richer analysis outside the core.

Cons:

- Not deterministic.
- Harder to test.
- Different agents may reach different conclusions.
- Risk of hidden governance assumptions.

Assessment: useful as authoring support, but not acceptable as core truth.

## Recommended Direction

Choose Alternative C. Keep the core deterministic and artifact-driven. Allow
agents and UI layers to suggest links or analysis, but require those suggestions
to become explicit versioned artifact relations before the core preflight uses
them.

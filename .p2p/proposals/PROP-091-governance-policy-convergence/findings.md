# Findings - PROP-091

## F001 - Governance Artifacts Are Present But Not Policy

P2P Engine can store governance-related files and record votes or precedents,
but the current system does not evaluate them together as a decision preflight.

Impact: high.

## F002 - Owner Authority Must Remain Explicit

The owner remains the final decision maker in the current project phase. The
system should make vote alignment and conflicts visible without converting votes
into automatic outcomes.

Impact: high.

## F003 - Permissions Are The Better Actor Source

`permissions.yml` contains project-declared identities and roles and already
supports consent-sensitive flows. It is the strongest source for actor
resolution. `governance/roles.yml` should remain available for legacy/display
or fallback during migration.

Impact: high.

## F004 - Precedent Lookup Must Be Deterministic

Core precedent lookup must avoid fuzzy matching, title inference, semantic
similarity, embeddings, or AI. Explicit artifact links and declared tags keep
preflight reproducible.

Impact: high.

## F005 - Blocking Errors Should Protect Reliability

Blocking errors should represent inability to decide reliably, not ordinary
dissent. Structural invalidity, unknown targets, invalid governance mode, and
unauthorized actors must block. Vote disagreement and related precedents should
warn.

Impact: high.

## F006 - MCP Should Start With Visibility

MCP can safely expose status, validation, preflight, vote status, and
deterministic precedent lookup. Mutation and final decision tools should wait
until actor authority, override rationale, and managed delegation are fully
specified.

Impact: medium.

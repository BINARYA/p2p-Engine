# Suggested Scope - PROP-091

## In Scope

- Governance policy evaluation service or equivalent cohesive boundary.
- Versioned governance preflight output contract.
- Actor resolution using `permissions.yml` as primary source.
- Legacy/fallback handling for `governance/roles.yml`.
- Vote summary and vote alignment evaluation.
- Warning for owner selection that conflicts with vote winner.
- Deterministic explicit precedent lookup.
- Active blocker evaluation.
- Distinction between warnings, non-overrideable blocking errors, and
  owner-overrideable active blockers.
- Structural validation for governance artifacts.
- CLI or core surfaces for governance status and preflight.
- MCP phase 1 read-only/low-risk governance tools.

## Out Of Scope

- Full democratic governance enforcement.
- Automatic vote-based finalization.
- Quorum, weighted voting, delegation, complex deadlines, or vote expiry.
- Fuzzy precedent search in the core.
- AI, embeddings, or semantic matching in core preflight.
- MCP vote recording, precedent recording, or choice finalization in phase 1.
- Removing legacy governance artifacts without migration.

## Suggested First Delivery Slice

1. Define the preflight domain model and schema.
2. Implement read-only preflight for choices.
3. Implement actor resolution and vote summary alignment.
4. Implement active blocker and deterministic precedent reporting.
5. Add validation for governance artifacts.
6. Expose CLI YAML/JSON output.
7. Expose MCP read-only tools.

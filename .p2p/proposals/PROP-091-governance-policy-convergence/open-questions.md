# Open Questions - PROP-091

## Resolved By Owner Discussion

- Should the owner remain the final decision maker?
  Resolved: yes. `owner_decides` remains the default for now.

- Should vote conflict block owner decisions?
  Resolved: no. Vote conflict creates a strong warning, not a hard block.

- Should `permissions.yml` or `roles.yml` be authoritative for actors?
  Resolved: use a soft migration. `permissions.yml` is primary when present;
  `roles.yml` remains legacy/display/fallback.

- Should core precedent lookup use fuzzy or AI matching?
  Resolved: no. Core lookup is explicit, deterministic, and artifact-driven.

- Should active explicit blockers be true blocks?
  Resolved: yes for normal finalization, but owner override with explicit
  rationale is allowed.

- Should MCP phase 1 include mutation/finalization tools?
  Resolved: no. MCP phase 1 is read-only or low-risk evaluation only.

## Remaining Questions

1. Which exact CLI command names should expose governance preflight?
2. Should preflight be available for proposals immediately, or should phase 1
   focus on choices first?
3. What exact artifact fields should represent `related_precedents`,
   `applies_to`, and `governance_tags`?
4. Should `requires_rationale` be computed for vote conflicts even though it is
   not mandatory for finalization?
5. Should `governance/roles.yml` be regenerated from `permissions.yml` in a
   later migration, or simply retained as legacy input?

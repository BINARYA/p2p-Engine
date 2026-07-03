# Clarifications - PROP-091

## Owner Authority

The owner remains the final decision maker in the current model. Future
governance proposals may introduce stricter or more collaborative models, but
this proposal preserves `owner_decides` as the operational default.

## Vote Transparency

Votes are transparency and decision evidence. The system should show whether an
owner decision aligns with the vote winner, conflicts with it, has no votes, or
faces a tie. Vote disagreement creates a warning, not an automatic block.

## Actor And Role Source

`permissions.yml` is primary for actor and role resolution when present.
`governance/roles.yml` remains legacy/display/fallback. Legacy role arguments
may be tolerated during migration but should warn if they diverge from the
resolved permissions role.

## Precedents

The core uses only explicit and deterministic precedent relationships declared
in versioned artifacts. Soft analysis can suggest relations externally, but
those relations affect core behavior only after being saved as explicit links.

## Blocking Errors

Blocking errors protect reliability. They are not a mechanism to suppress
dissent. Unauthorized actors, invalid targets, unsupported modes, and corrupt
artifacts block because the system cannot evaluate governance safely.

## Active Explicit Blockers

An active explicit blocker blocks normal finalization. An authorized owner may
override it only with explicit rationale recorded in the final decision record.

## MCP Phase 1

MCP phase 1 can evaluate and expose governance state. It cannot record votes,
create precedents, or finalize choices/proposals.

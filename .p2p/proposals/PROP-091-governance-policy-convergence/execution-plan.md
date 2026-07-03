# Execution Plan - PROP-091

## Phase 1 - Policy Contract

Define the governance preflight domain contract:

- schema version;
- target;
- governance mode and authority source;
- actor resolution;
- proposed selection;
- result status;
- blocking errors;
- warnings;
- vote summary;
- active blockers;
- explicit and tag-declared precedents.

This phase must preserve owner authority and keep vote outcomes advisory.

## Phase 2 - Actor And Role Resolution

Introduce actor resolution with `permissions.yml` as the primary source when
present. Preserve `governance/roles.yml` as legacy/display/fallback during
migration. Legacy role inputs are tolerated but inconsistencies are warnings.

## Phase 3 - Choice Governance Preflight

Implement read-only/evaluation-only preflight for choices first. The result
must distinguish:

- ready;
- requires_rationale;
- requires_owner_override;
- blocked.

Normal finalization is blocked by non-overrideable integrity errors and by
active explicit blockers. Active explicit blockers may be overridden only by an
authorized owner with recorded rationale.

## Phase 4 - Deterministic Precedent Lookup

Implement precedent lookup based only on explicit artifact relations and
declared tags. Do not use fuzzy matching, free-text inference, semantic
similarity, embeddings, or AI in the core.

## Phase 5 - Validation

Extend validation to cover governance artifacts, including governance mode,
roles, votes, precedents, explicit links, duplicate IDs, and structurally
invalid present artifacts.

## Phase 6 - CLI And MCP Read Surfaces

Expose CLI and MCP read surfaces for:

- governance status;
- governance validation;
- choice governance preflight;
- vote status;
- deterministic precedent search.

MCP phase 1 must not mutate votes, create precedents, or finalize decisions.

## Phase 7 - Follow-Up Boundaries

Defer mutating MCP tools and advanced governance models to later proposals:

- vote recording through MCP;
- precedent recording through MCP;
- choice decision through MCP;
- quorum;
- weighted voting;
- delegation;
- automatic vote enforcement.

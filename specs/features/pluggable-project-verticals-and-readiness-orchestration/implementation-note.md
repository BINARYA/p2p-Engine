# Implementation Note - Pluggable Project Verticals And Readiness Orchestration

## Implemented

- Added typed project vertical models and package resource packs:
  `base_project`, `packaging_or_physical_product_design`, and
  `social_impact_program_design`.
- Added `ProjectVerticalService` for internal/project-local loading, source
  precedence, fallback active state, schema validation, candidate generation,
  add/select persistence, proposal vertical coverage parsing, and project
  readiness review.
- Added `P2PWorkspace` facade methods and semantic validation integration for
  project-local vertical packs, active vertical state, and proposal coverage.
- Added CLI commands:
  `p2p project vertical list/show/validate/propose/add/select` and
  `p2p project readiness review`.
- Added MCP tools for the same project vertical and readiness review operations.
- Updated generated agent instructions and policy with project vertical
  orchestration guidance.
- Updated visible project export to include vertical skeleton coverage when a
  review provider is available.
- Updated public CLI and MCP docs.

## Deferred

- Remote vertical registry discovery/detail APIs remain deferred. The service
  boundary keeps source metadata and project-local override behavior ready for a
  future registry.
- A dedicated CLI writer for proposal `vertical-coverage.yml` remains deferred;
  the MVP validates and reads coverage artifacts when present.

## Verification

- `.venv/bin/pytest`: `392 passed`
- `.venv/bin/p2p validate`: `errors: 0`, `warnings: 0`, `infos: 0`

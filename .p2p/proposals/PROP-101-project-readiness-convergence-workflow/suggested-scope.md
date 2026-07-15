# Suggested Scope

## In Scope

- immutable readiness snapshot and typed priority gaps;
- schema-v2 project-question artifact and lifecycle;
- operation-level role/consent transition matrix;
- declared and deterministic fallback questions;
- transition-handler migration architecture and v1-to-v2 mapping;
- pure definition candidate rendering and atomic definition/question apply;
- actor-bound preview, exact retry and concurrency handling;
- vertical question reconciliation and revision history;
- next actions, progress, freshness and decision-context integration;
- bounded CLI, snapshot cursors and MCP read parity;
- source-access budgets, adversarial fixtures and repository migration pilot.

## Explicitly Deferred

- MCP answer/apply tools until the canonical CLI mutation path is stable;
- clock-based preview expiry until a durable receipt lifecycle is proposed;
- persistent database or cache;
- automatic proposal coverage mapping;
- automatic deterministic rebuild after canonical apply;
- agent curation, publication or owner review side effects;
- remote fleet migration.

## Exit Boundary

Do not begin repository adoption until transition-specific planning, legacy mapping, authority checks, multi-target failure injection and exact retry tests pass. Do not claim project-definition convergence when only question state has been deferred or muted.

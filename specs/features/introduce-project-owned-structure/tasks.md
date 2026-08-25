# Tasks - Introduce Project-Owned Structure

## Model And Storage

- [ ] T001 [R001-R011, D001-D003] Inventory every active-vertical, lock,
  definition, rubric, question and artifact assumption that currently defines
  project shape.
- [ ] T002 [R001-R006, D001-D003] Define typed structure, element, lifecycle,
  origin, event and bounded collection models.
- [ ] T003 [R001-R006, N003-N005, D001-D003] Select and document the private schema-4
  storage layout, canonical normalization and semantic checksum algorithm.
- [ ] T004 [R023-R025, D001, D003-D005] Implement strict repository reads, validation and bounded
  history projection.

## Initialization And Definition

- [ ] T005 [R007-R011, D002] Materialize one detached structure from generic,
  empty and effective exact-pack sources.
- [ ] T006 [R020-R022, D006] Rebind project definition state and validation to
  project-structure IDs instead of active pack identity.
- [ ] T007 [R007-R011, D002] Replace active vertical lock semantics with origin
  provenance and append-only initialization event evidence.

## Mutations

- [ ] T008 [R012-R019, D004-D005] Implement pure plans for add, metadata update
  and exact-set reorder operations.
- [ ] T009 [R016-R019, N001, D004-D005, D007] Implement atomic event/structure/receipt apply,
  replay, status and recovery behavior.
- [ ] T010 [R012-R019, D005] Add strict CLI text/JSON commands and error mapping.
- [ ] T011 [R012-R019, D005] Add MCP read and consent-gated simple mutation
  parity through the same services.

## Tests And Documentation

- [ ] T012 [AC001-AC007, D001-D006] Add model, source-copy, empty, stable-ID, rename,
  reorder, origin and definition-integration tests.
- [ ] T013 [AC004, AC008, D004-D005, D007] Add stale revision, concurrent apply, response loss,
  divergent replay and transaction fault-injection tests.
- [ ] T014 [N002-N005, D001-D006] Add bounded payload, deterministic checksum and
  installed-wheel contract tests.
- [ ] T015 [AC005-AC007, D001-D007] Update CLI/MCP docs, architecture guidance, primitive
  inventory and generated agent templates.
- [ ] T016 [AC001-AC009, D001-D007] Run focused tests, CLI/MCP public-contract tests and
  the full suite.
- [ ] T017 [R026-R027, D007, AC009] Integrate `project.structure.edit` authority
  resolution and context binding into plans, receipts, CLI/MCP contracts,
  generated guidance and local/external policy tests.

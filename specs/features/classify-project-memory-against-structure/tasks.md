# Tasks - Classify Project Memory Against Structure

## Contract And Inventory

- [x] T001 [R001-R015, D001-D005] Inventory proposal coverage, project-memory,
  question, evidence, artifact, decision and publication section references.
- [x] T002 [R001-R005, D001-D004] Define strict scope, classification status,
  per-type count and retired-reference core models.
- [x] T003 [R013-R015, D005] Complete and document the applicability matrix for
  every current memory family.

## Proposal And Memory Behavior

- [x] T004 [R006-R012, D001-D002] Remove the zero-section proposal-creation gate
  and persist explicit unassigned proposal scope.
- [x] T005 [R006-R012, D002] Add the authority-creating decision scope gate and
  stable blocker contract.
- [x] T006 [R022-R025, D001, D004, D007] Implement pure scope assignment/reassignment planning and
  atomic receipt-backed apply/status/replay.
- [x] T007 [R013-R015, D004-D005] Adapt supported question, evidence and artifact
  references without hiding unsupported active memory.

## Classification Projection

- [x] T008 [R016-R021, D003-D005] Establish the structure-aware classification
  index with incremental invalidation, remove vertical coverage from scope
  authority and leave final pre-rebase projection deletion to the ordered
  readiness-convergence feature.
- [x] T009 [R016-R021, N001-N004, D003-D006] Add bounded side-effect-free classification
  reads bound to structure and memory revisions.
- [x] T010 [R026-R028, D003, D006] Update project snapshot and publication models to retain
  global, unassigned and retired historical content explicitly.

## Public Surfaces

- [x] T011 [R022-R025, D006] Add CLI scope show/set and classification read JSON
  contracts with human summaries and stable errors.
- [x] T012 [R022-R025, D006] Add MCP read and consent-gated scope mutation
  parity over the shared services.
- [x] T013 [AC007, D006-D007] Update capability registry, generated templates, CLI guide,
  MCP docs and primitive inventory.

## Validation

- [x] T014 [AC001-AC006, D001-D005] Add empty-project, multi-section, global, unassigned,
  decision-gate, historical and retired-target tests.
- [x] T015 [AC004-AC008, D003-D006] Add classification count, truncation, stale revision,
  incremental refresh, replay and concurrent structure-change tests.
- [x] T016 [AC007-AC008, D005-D007] Add installed-wheel CLI/MCP/publication contract smoke
  tests and sanitized golden fixtures.
- [x] T017 [AC001-AC009, D001-D007] Run focused tests, public-contract tests and the full
  suite.
- [x] T018 [R029-R031, N005, D007, AC009] Integrate `project.memory.classify` authority and
  prove classification, `proposal.decide` and
  `proposal.readiness.override` cannot authorize one another implicitly.

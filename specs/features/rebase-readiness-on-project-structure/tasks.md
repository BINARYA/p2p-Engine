# Tasks - Rebase Readiness On Project Structure

## Inventory And Contract

- [x] T001 [R001-R025, D006] Inventory all project maturity, progress,
  readiness, gap, snapshot, publication and guidance calculations and identify
  duplicated criterion semantics.
- [x] T002 [R006-R016, D002-D004] Define criterion weight/evaluator, readiness
  status, axis, section, gap, diagnostic and snapshot core contracts.
- [x] T003 [R017-R021, D001-D004] Define `p2p-project-readiness/v2` and its relationship to
  `p2p-memory-classification/v1`.

## Calculation

- [x] T004 [R001-R016, D001-D003] Implement one immutable source snapshot and
  pure weighted definition/evidence calculations.
- [x] T005 [R011-R016, D003-D004] Implement not-configured, retired,
  not-applicable, global, unassigned and reassignment semantics.
- [x] T006 [R013-R018, D001-D004] Implement bounded section/project gaps, diagnostics and
  actions over stable IDs.
- [x] T007 [R019-R021, D005] Implement optional disposable cache identity and
  prove reads remain side-effect free.

## Convergence

- [x] T008 [R022-R025, D006] Refactor progress, review, gaps and snapshot reads
  to use shared criterion/source services.
- [x] T009 [R022-R025, D006] Remove domain-template maturity and origin-orphan
  compatibility paths from current runtime.
- [x] T010 [R017-R025, D004, D006-D007] Update CLI/MCP serializers and human renderers while
  preserving proposal-readiness separation.

## Validation

- [x] T011 [AC001-AC006, D001-D004] Add weighted, zero-criteria, retirement, global,
  unassigned, evidence and revision-identity fixtures.
- [x] T012 [AC004-AC008, D001-D007] Add contract parity, side-effect, cache invalidation,
  truncation and algorithm-version tests.
- [x] T013 [N002, D001-D002, D005] Add bounded performance tests over active structure and
  indexed memory.
- [x] T014 [AC007-AC008, D004, D006-D007] Update CLI contract, MCP docs, agent guidance,
  primitive inventory and release documentation.
- [x] T015 [N001, N003-N005, AC001-AC009, D001-D007] Run focused,
  public-contract, installed-wheel and full
  test suites.
- [x] T016 [R026-R027, D007, AC009] Prove readiness reads create no mutation receipt or
  AuthorityContext and document the separate capability boundary for any
  future persisted override.

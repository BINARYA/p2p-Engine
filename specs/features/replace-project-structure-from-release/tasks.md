# Tasks - Replace Project Structure From Release

## Analysis And Contract

- [x] T001 [R001-R007, D001-D003] Define replacement impact, plan, event and
  result contracts over current structure and retirement types.
- [x] T002 [R001-R007, D002-D003] Implement exact target normalization and
  stable-ID semantic comparison.
- [x] T003 [R003-R007, D001-D004] Implement first preview with preserved/added/retired/
  conflicting elements and readiness/classification impact.
- [x] T004 [R005-R008, D003-D004] Implement strict disposition plan validation
  and token-bearing second preview.

## Apply And Recovery

- [x] T005 [R008-R015, D001-D004] Materialize detached target structure,
  dispositions and replacement event deterministically.
- [x] T006 [R008-R015, D003-D006] Integrate atomic apply, receipt, mutation status, replay,
  recovery and postcondition validation.
- [x] T007 [R011-R012, D001-D005] Update origin/history reads without creating an
  active release subscription.

## Public Surfaces And Validation

- [x] T008 [R001-R015, D001-D006] Add CLI preview/apply/status JSON and human summaries.
- [x] T009 [R001-R008, R018, D004] Add side-effect-free MCP exact-release
  inspection/comparison over the shared service, keep apply absent and add
  catalog/guidance tests proving the deferral.
- [x] T010 [AC001-AC006, D001-D005] Add exact, divergent, collision, empty, reference,
  stale and no-auto-update tests.
- [x] T011 [AC007-AC008, D004-D006] Add response-loss, recovery, offline installed-wheel and
  contract fixture tests.
- [x] T012 [N001-N004, AC001-AC010, D001-D006] Update docs and run
  focused/public/full validation.
- [x] T013 [R016-R017, D006, AC009] Integrate `project.structure.replace` authority
  into both previews, apply, receipt and tests without deriving authority from
  target-release visibility.

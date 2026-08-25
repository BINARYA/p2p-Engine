# Tasks - Merge And Restore Project Structure

## Deferred Preconditions

- [ ] T001 [D001, AC007] Confirm implementation evidence for replacement,
  retirement impact, history retention and recovery before enabling work.
- [ ] T002 [R006, N003, D004] Define and approve historical snapshot retention
  guarantees required by restore.

## Merge

- [ ] T003 [R001-R005, D002] Define selective import, dependency and collision
  contracts.
- [ ] T004 [R001-R005, D002] Implement exact source comparison and complete merge
  preview without writes.
- [ ] T005 [R003-R005, D002] Implement strict collision decisions and disposition-plan
  integration.

## Restore

- [ ] T006 [R006-R008, D003-D004] Implement validated historical snapshot lookup
  and forward restore preview.
- [ ] T007 [R006-R012, D003] Reuse transition materialization to create one new
  revision, event and receipt.

## Public Surfaces And Validation

- [ ] T008 [R009-R012, D005] Add CLI JSON/human preview/apply/status only after
  deferred preconditions pass.
- [ ] T009 [R001-R005, R014-R015, D005] Add byte-invariant MCP merge comparison
  and retained-revision inspection over shared services; keep merge/restore
  apply absent with an explicit consent deferral.
- [ ] T010 [N001-N002, AC001-AC006, D001-D006] Add selective dependency,
  collision, restore, history,
  disposition, replay and fault-injection tests.
- [ ] T011 [N004, AC007-AC009, D001, D005-D006] Update capabilities/docs only
  with implementation evidence and
  run focused/public/full validation.
- [ ] T012 [R013-R014, D006, AC008] Bind future merge and restore applies to their
  distinct capabilities and AuthorityContext, and keep generated write
  capability disabled until the deferred implementation gate passes.

# Tasks - Export Project Structure As Vertical

## Contract And Planning

- [ ] T001 [R001-R008, D001-D002] Define active structure export snapshot,
  eligibility, metadata and lineage contracts.
- [ ] T002 [R001-R008, D004] Implement read-only preview and exact source-token
  binding.
- [ ] T003 [R003-R008, N002, D002-D003] Implement strict metadata, license, attribution and
  parent-lineage validation.

## Materialization

- [ ] T004 [R009-R014, D003] Map active structure deterministically into the
  current vertical draft document without project memory or retired elements.
- [ ] T005 [R009-R014, D003-D004] Integrate draft creation/update, validation,
  package generation, operation receipt and status replay.
- [ ] T006 [R013-R014, D001, D004] Prove source project state and readiness are unchanged by
  export.

## Public Surfaces And Validation

- [ ] T007 [R001-R014, D005] Add CLI preview/export JSON and human output with
  safe server/local destination handling.
- [ ] T008 [R001-R002, R017, D005] Add MCP read-only eligibility/preview over
  the shared service, prove byte invariance and keep destination-writing apply
  absent from the MCP catalog.
- [ ] T009 [AC001-AC006, D001-D004, D006] Add derived, independent, attribution, empty, retired,
  stale, collision and replay tests.
- [ ] T010 [AC007-AC008, D003-D005] Add installed-wheel offline pack validation and update
  CLI/MCP/agent/registry documentation.
- [ ] T011 [N001, N003-N004, AC001-AC010, D001-D006] Run focused,
  portable-pack, public-contract and full
  test suites.
- [ ] T012 [R015-R016, D006, AC009] Integrate `project.vertical.export` authority into
  durable export identity and prove it grants neither artifact ownership nor
  remote publication authority.

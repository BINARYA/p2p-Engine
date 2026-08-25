# Tasks - Separate Domain From Structure Source

## Contract And Inventory

- [ ] T001 [R001-R012, D001-D003] Inventory every domain/template/init branch,
  bundled preset, schema artifact, CLI option, MCP tool and generated guidance
  that still assigns structural meaning to domain.
- [ ] T002 [R001-R012, D001-D003] Define strict core models and serializers for
  `ProjectDomainRef` and the exclusive `StructureSource` union.
- [ ] T003 [R019-R021, D001] Define schema-3 optional vertical domain metadata,
  bounds and deterministic serialization.

## Initialization And Storage

- [ ] T004 [R006-R014, D002-D003] Refactor initialization normalization so one
  explicit source is resolved before any workspace candidate is rendered.
- [ ] T005 [R009-R011, D003] Package generic/empty starter behavior and convert
  specialized built-ins to ordinary bundled vertical releases.
- [ ] T006 [R001-R005, R022-R024, D005] Persist the new domain descriptor and
  source provenance in workspace schema 4 and reject schema-3 semantics.
- [ ] T007 [R012-R014, D006] Publish strict structured init results with domain,
  source, origin and structure revision.

## Domain Mutation

- [ ] T008 [R015-R018, D004] Implement pure domain set/clear planning and
  semantic fingerprinting.
- [ ] T009 [R015-R018, D004] Add atomic receipt-backed apply, replay and mutation
  status integration.
- [ ] T010 [R015-R018, D004-D006] Add CLI text/JSON show, set and clear commands
  with stable errors and exits.
- [ ] T011 [R015-R018, D004] Add MCP read and consent-gated mutation parity over
  the shared domain service.

## Validation And Convergence

- [ ] T012 [AC001-AC006, D001-D006] Add focused unit, initialization, pack and receipt tests
  for arbitrary domains, generic, empty, exact packs and conflicting sources.
- [ ] T013 [N001-N005, D001-D006] Add bounds, unsafe-input, offline, concurrency, response
  loss and unsupported-schema tests.
- [ ] T014 [AC007, D001-D007] Update CLI guide, contract, MCP docs, primitive inventory,
  generated skill templates and examples.
- [ ] T015 [AC008, D001-D006] Build a wheel and run installed-wheel smoke tests for all
  three initialization sources and domain mutation replay.
- [ ] T016 [AC001-AC009, D001-D007] Run focused tests, public-contract tests and the full
  suite under the repository test-quality policy.
- [ ] T017 [R025-R027, D007, AC009] Integrate `project.initialize` and
  `project.domain.change` AuthorityContext validation, semantic binding and
  local/external policy tests without importing provider roles.

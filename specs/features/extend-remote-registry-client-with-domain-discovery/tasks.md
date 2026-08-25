# Tasks - Extend Remote Registry Client With Domain Discovery

## Contract And Inventory

- [ ] T001 [R001-R004, D001] Inventory registry-v1 capability, endpoint,
  parser, configuration, fixture, CLI, MCP, docs and generated-guidance
  surfaces and freeze the v2 replacement matrix.
- [ ] T002 [R001-R009, D001-D003] Define strict v2 capability,
  `RegistryDomain`, recommendation, primary-domain and pagination contracts with
  canonical serializers and bounds.
- [ ] T003 [R020-R023, D006] Freeze CLI command/option, JSON envelope, MCP tool,
  network-permission and typed-error contracts before implementation.

## Core Client And Services

- [ ] T004 [R001-R004, D001] Replace registry-v1 negotiation/config validation
  with current-only v2 required endpoint parsing and same-origin validation.
- [ ] T005 [R005-R009, D002] Implement strict domain page/detail parsing,
  visibility/lifecycle policy and non-enumerating inaccessible-detail mapping.
- [ ] T006 [R010-R014, D003] Extend remote vertical release parsing and query
  services with nullable primary-domain metadata and exact domain filters.
- [ ] T007 [R015-R019, D004-D005] Implement bounded cursor traversal, duplicate
  conflict detection, existing Device Flow authorization and redacted failures.
- [ ] T008 [R014, R019, N003, D003-D004] Prove domain reads and domain-filtered discovery
  perform no project write, pull or implicit artifact-cache commit.

## CLI, MCP And Agent Surfaces

- [ ] T009 [R020, D002-D004] Add `vertical domain list/search/inspect` CLI text
  and JSON commands plus the exact `vertical list/search --domain` filter.
- [ ] T010 [R021-R023, D006] Add read-only MCP domain catalog and
  domain-filtered vertical search tools over the same services with explicit
  remote-network descriptions and permission classification.
- [ ] T011 [R020-R023, AC008, D002-D003, D006] Update capability inventory, generated agent
  templates, CLI help and registry docs to distinguish catalog domain, project
  domain, release and detached project structure.

## Validation And Release Gate

- [ ] T012 [AC001-AC005, D001-D005] Add parser/service tests for public/private domains,
  recommendations, uncategorized releases, filters, v1 rejection, cross-origin
  endpoints, malformed pages, throttling and secret redaction.
- [ ] T013 [AC003-AC006, D004, D006] Add CLI/MCP parity and zero-side-effect tests using one
  provider-neutral in-memory v2 registry fixture.
- [ ] T014 [N001-N005, D004-D005] Add deterministic ordering, page/document bounds,
  timeout, token refresh, unavailable keyring and no-registry tests.
- [ ] T015 [AC001-AC008, D001-D006] Build the candidate wheel and run installed-wheel CLI,
  MCP, offline and v2 mock-provider smoke tests.
- [ ] T016 [AC001-AC008, D001-D006] Add the v2 commands and fixtures to the 0.5 convergence
  inventory, run focused/public/full suites on supported Python versions and
  record release evidence.

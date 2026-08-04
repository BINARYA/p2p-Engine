# Tasks - Local Vertical Catalog And Remote Registry Client

## Phase 0 - Contract

- [x] T001: Bind accepted `PROP-105` to requirements, design and tasks and
  declare `PROP-104`, `PROP-103` and `PROP-107` dependencies. Covers R001-R030.
- [x] T002: Define typed registry protocol-v1, release metadata, configuration,
  cache and error models. Covers R001-R005, R013-R022, R028-R030.

## Phase 1 - Configuration And Credentials

- [x] T003: Implement `P2P_HOME`/platform root resolution and atomic registry
  configuration storage outside `.p2p`. Covers R001-R005, R022.
- [x] T004: Implement keyring-backed credential storage with injected in-memory
  test adapter and redaction. Covers R006-R010.
- [x] T005: Implement capability negotiation and OAuth device login/logout
  services. Covers R006-R010, R028-R029, AC002, AC006.
- [x] T006: Add `vertical registry` and `vertical login/logout` CLI commands
  with versioned JSON envelopes. Covers R001-R010, R030.

## Phase 2 - Catalog, HTTP And Cache

- [x] T007: Implement normalized local catalog discovery for bundled, cached
  and explicit portable packs. Covers R011-R013, R019-R022.
- [x] T008: Implement the bounded HTTPS adapter with explicit timeouts,
  streaming size limits and token-redacted errors. Covers R014-R015, R028-R029.
- [x] T009: Implement exact dependency planning, verification and atomic
  immutable cache commit. Covers R013-R018, R020, AC004-AC005.
- [x] T010: Add hostile transport/cache tests for timeout, overflow, checksum,
  malformed archive, partial closure and immutability conflict. Covers R014-
  R018, AC004-AC005.
- [x] T011: Add `vertical search/list/pull/inspect` CLI commands and text/JSON
  contract tests. Covers R011-R022, R030, AC001-AC002.

## Phase 3 - Initialization

- [x] T012: Extend init with explicit `--pull` and `--registry` while retaining
  offline `--vertical-pack` exclusivity. Covers R023-R026.
- [x] T013: Pass cached artifacts through existing install-before-init and
  guarantee cleanup on cache/workspace failure. Covers R026-R027, AC001,
  AC003-AC004.
- [x] T014: Add integration tests proving no network without `--pull`, public
  pull init, private pull init and failure rollback. Covers R023-R027,
  AC001-AC004.

## Phase 4 - Documentation And Verification

- [x] T015: Document protocol v1, configuration roots, authentication, cache
  semantics and WaveKit's retained local-artifact handoff. Covers R028-R030.
- [x] T016: Run focused service/adapter tests, public CLI tests, wheel smoke and
  full suite; record evidence. Covers AC001-AC007.
- [x] T017: Add an implementation note linking delivered surfaces and deferred
  MCP parity to `PROP-105`.

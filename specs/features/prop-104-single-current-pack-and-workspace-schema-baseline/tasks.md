# Tasks - Single Current Pack And Workspace Schema Baseline

## Phase 0 - Binding And Inventory

- [x] T001: Bind accepted `PROP-104` to requirements, design and implementation
  tasks. Covers R001-R019.
- [x] T002: Inventory obsolete vertical/workspace branches, packaged resources,
  tests, docs and agent guidance; classify each as convert/delete/retain. Covers
  R004, R014-R015.

## Phase 1 - Current Vertical Contract

- [x] T003: Convert every bundled vertical to schema 2 with exact identity,
  license and dependencies while preserving semantic content. Covers R001,
  R003-R005, AC001.
- [x] T004: Remove implicit schema defaults and schema-1 parsing/composition
  branches from typed models and vertical services. Covers R006, R008,
  R014-R015.
- [x] T005: Add stable unsupported-pack diagnostics and zero-write regression
  tests. Covers R006, R009, R016, AC002.
- [x] T006: Update package-resource and deterministic archive tests for every
  bundled schema-2 pack. Covers R017-R018, AC001, AC005.

## Phase 2 - Current Workspace Contract

- [x] T007: Make workspace schema 3 the sole runtime-supported memory contract
  and remove obsolete mutation entry points. Covers R002, R007-R009, R014.
- [x] T008: Add unsupported-workspace zero-write tests across facade, CLI and
  representative MCP calls. Covers R007, R016, AC003.
- [x] T009: Audit the canonical project; if necessary run a disposable
  copy-first conversion and record semantic before/after evidence. Covers
  R011-R013, AC006.
- [x] T010: Remove obsolete workspace fixtures, migration guidance and runtime
  code after canonical evidence is current. Covers R014, AC004.

## Phase 3 - Discovery, Docs And Verification

- [x] T011: Expose the three separately named current contract versions through
  the version surface implemented by `PROP-107`. Covers R010.
- [x] T012: Update maintained documentation and release notes with the 0.4.6
  break and WaveKit rebuild/recreation requirements. Covers R019.
- [x] T013: Run focused schema/resource tests, public CLI/MCP tests, installed-
  wheel smoke tests and the full suite; record evidence. Covers AC001-AC007.
- [x] T014: Add an implementation note linking completed tasks, deliberate
  deletions and canonical conversion evidence to `PROP-104`.

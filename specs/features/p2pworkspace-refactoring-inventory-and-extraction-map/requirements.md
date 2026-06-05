# P2PWorkspace Refactoring Inventory And Extraction Map Requirements

## Source

- Accepted proposal: `PROP-059 - P2PWorkspace Modular Refactoring Plan`
- Prior feature:
  `specs/features/p2pworkspace-modular-refactoring-contract/`
- Source analysis baseline:
  `src/p2p_engine/storage/filesystem.py`, `src/p2p_engine/cli.py`,
  `src/p2p_engine/mcp/tools.py`, `src/p2p_engine/storage/git.py`,
  `tests/test_cli.py`, `tests/test_mcp.py`

## Purpose

This feature creates the detailed technical map required before runtime
refactoring starts. It bridges the architecture contract and future
implementation tasks.

## Requirements

### R001 - Runtime Surface Inventory

THE SYSTEM SHALL document the current runtime surfaces that participate in the
refactoring: `P2PWorkspace`, CLI command modules, MCP tool definitions and
dispatch, Git helpers, core models, exporters, prompt renderers, and tests.

Acceptance: the inventory lists each relevant file, its current responsibility,
approximate size, and refactoring concern.

Status: implemented

### R002 - P2PWorkspace Method Map

THE SYSTEM SHALL map `P2PWorkspace` methods into responsibility groups.

Acceptance: every public `P2PWorkspace` method and significant private helper is
assigned to a proposed target area such as agents, permissions/consent,
sync/git, proposals, readiness, project state, specs/export, work, registries,
intake, choices, next actions, or validation.

Status: implemented

### R003 - Target Module Boundaries

THE SYSTEM SHALL define target internal modules/services and their ownership
boundaries.

Acceptance: each proposed service has a name, responsibility, facade
relationship, persistence boundary, side effects, and initial extraction risk.

Status: implemented

### R004 - Compatibility Test Map

THE SYSTEM SHALL map each extraction area to existing tests and missing test
coverage.

Acceptance: the map identifies CLI tests, MCP tests, storage/validation tests,
Git/sync tests, and missing tests that must be added before extraction.

Status: implemented

### R005 - Extraction Order

THE SYSTEM SHALL define a safe extraction order.

Acceptance: the order starts with architecture/documentation, then
permissions/consent, then later areas based on coupling, risk, and available
tests; CLI module splitting is scheduled after service/use-case extraction.

Status: implemented

### R006 - Facade Contract

THE SYSTEM SHALL define what remains in `P2PWorkspace` during the transition.

Acceptance: the map identifies facade methods that delegate to services,
methods that remain temporarily in place, and methods that require a separate
proposal before public behavior changes.

Status: implemented

### R007 - Implementation Task Derivation

THE SYSTEM SHALL produce enough detail to derive future implementation feature
tasks without re-analyzing the whole source tree.

Acceptance: each extraction area has candidate follow-up feature names and
task seeds, but no source code is changed as part of this feature.

Status: implemented

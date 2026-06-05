# P2PWorkspace Modular Refactoring Contract Requirements

## Source

- Accepted proposal: `PROP-059 - P2PWorkspace Modular Refactoring Plan`
- Contributions: `C001` through `C014`
- Binding report:
  `specs/bindings/prop-059-p2pworkspace-modular-refactoring.md`

## Requirements

### R001 - Agent Architecture Rules

THE SYSTEM SHALL provide short non-negotiable agent development rules that
prevent new unrelated domain behavior from being added directly to
`src/p2p_engine/cli.py`, `src/p2p_engine/storage/filesystem.py`, or
`src/p2p_engine/mcp/tools.py` by default.

Acceptance: `AGENTS.md` contains concise architecture rules that complement P2P
governance boundaries without replacing them.

Status: implemented

### R002 - Development Guidelines

THE SYSTEM SHALL provide a maintained development guide that describes the
current architecture, target layering, module ownership, anti-patterns,
compatibility constraints, test expectations, and refactoring roadmap.

Acceptance: `docs/DEVELOPMENT-GUIDELINES.md` exists and covers the architecture
contract accepted in `PROP-059`.

Status: implemented

### R003 - Stable Compatibility Facade

THE SYSTEM SHALL treat `P2PWorkspace` as the stable compatibility facade while
future behavior is extracted into cohesive services and adapters behind it.

Acceptance: development guidance states that public CLI, MCP, and existing
workspace call patterns remain compatible unless a separate proposal authorizes
a breaking change.

Status: implemented

### R004 - Compatibility Boundaries

THE SYSTEM SHALL preserve CLI commands, MCP tool names and payloads, `.p2p`
storage artifacts, validation behavior, registry refresh behavior, consent
receipts, Git/sync behavior, and owner-controlled governance semantics unless a
separate proposal explicitly approves a breaking change.

Acceptance: development guidance lists these compatibility-sensitive surfaces
and requires focused tests for touched surfaces.

Status: implemented

### R005 - Refactoring Sequence

THE SYSTEM SHALL require service/use-case extraction before CLI modularization.

Acceptance: the roadmap orders internal service extraction before CLI command
module splitting.

Status: implemented

### R006 - First Future Extraction Candidate

THE SYSTEM SHALL record consent/permissions as the preferred first future code
extraction after the architecture contract is implemented and bound into local
specs.

Acceptance: the roadmap identifies consent/permissions as the first extraction
candidate and explains the boundary and safety rationale.

Status: implemented

### R007 - No Runtime Change In First Deliverable

THE SYSTEM SHALL keep the first deliverable documentation-only, with no runtime
behavior change.

Acceptance: initial implementation changes only `AGENTS.md`, docs, local specs,
or equivalent development guidance files; no `src/` behavior changes are made.

Status: implemented

# P2PWorkspace Renderers Validators Foundation Requirements

## Scope

This feature creates a small shared foundation for pure Markdown helpers and
generic YAML validators currently embedded in `P2PWorkspace` storage code.

It is a prerequisite for later software-spec, project-definition, proposal, and
readiness service extractions.

## Origin

- Accepted source proposal: `PROP-059 - P2PWorkspace Modular Refactoring Plan`
- Architecture contract:
  `specs/features/p2pworkspace-modular-refactoring-contract/`
- Detailed inventory:
  `specs/features/p2pworkspace-refactoring-inventory-and-extraction-map/`
- Backlog seed:
  `p2pworkspace-renderers-validators-foundation`

## In Scope

- Extract pure Markdown parsing/manipulation helpers used across proposals,
  choices, changes, software specs, and project exports.
- Extract generic YAML shape validators for top-level key and tasks-list
  validation.
- Keep domain renderers in place unless a helper is purely shared.
- Keep `P2PWorkspace` as the compatibility facade.
- Preserve all existing rendered Markdown, parsed values, validation errors,
  CLI output, MCP output, and storage shapes.
- Add focused tests for the extracted foundation helpers.

## Out Of Scope

- Extracting software-spec refresh/status/show/import behavior.
- Extracting project definition or spec export renderers.
- Extracting proposal document service behavior.
- Extracting readiness scoring or readiness validation.
- Rewriting renderer output formats.
- Changing YAML schema rules or validation error messages.
- Moving CLI or MCP presentation code.

## Functional Requirements

### R001 - Markdown Foundation

THE SYSTEM SHALL provide shared Markdown helper functions for title reading,
section reading, section existence checks, section replacement, frontmatter
reading/replacement, and title stripping.

Acceptance: existing `P2PWorkspace` call sites use the shared helpers and return
the same values as before.

Status: implemented

### R002 - Markdown Behavior Compatibility

THE SYSTEM SHALL preserve current Markdown parsing semantics.

Acceptance: pending placeholders still read as missing section content,
frontmatter parse errors still return an empty mapping, and replacement keeps
the same section format.

Status: implemented

### R003 - YAML Validation Foundation

THE SYSTEM SHALL provide shared YAML validator functions for top-level key
validation and tasks YAML validation.

Acceptance: current validation call sites use the shared validators and raise
the same error message fragments as before.

Status: implemented

### R004 - Domain Renderer Boundary

THE SYSTEM SHALL leave domain-specific Markdown renderers in
`P2PWorkspace`/storage for this feature.

Acceptance: proposal, change, software-spec, project-definition, OpenSpec,
Spec Kit, project state, and agent instruction renderers are not moved as part
of this slice.

Status: implemented

### R005 - Compatibility Preservation

THE SYSTEM SHALL preserve existing CLI, MCP, validation, proposal update, and
spec export behavior.

Acceptance: mapped compatibility tests and the full test suite pass unchanged.

Status: implemented

### R006 - Focused Test Coverage

THE SYSTEM SHALL add focused tests for the shared Markdown and YAML foundation.

Acceptance: tests cover title reading, missing title, meaningful section
reading, pending section suppression, section existence, section replacement,
frontmatter read/replace, invalid frontmatter fallback, title stripping,
tasks YAML validation, top-level key validation, and invalid YAML errors.

Status: implemented

## Non-Functional Requirements

### N001 - Pure Foundation

THE SYSTEM SHALL keep new foundation helpers free of Typer, Rich, MCP, Git, and
`P2PWorkspace` imports.

Acceptance: helper modules are pure functions over strings, dictionaries, and
simple values.

Status: implemented

### N002 - No Behavior Drift

THE SYSTEM SHALL treat this as an internal extraction only.

Acceptance: no generated output, storage path, command behavior, or MCP schema
changes are introduced.

Status: implemented

### N003 - Narrow Extraction

THE SYSTEM SHALL avoid moving broad renderer groups before their owning
services exist.

Acceptance: source changes are limited to helper modules, imports/delegation in
`filesystem.py`, focused tests, and local feature specs.

Status: implemented

## Edge Cases And Errors

- Missing Markdown title.
- Pending section content.
- Missing Markdown section.
- Section replacement when section exists.
- Section replacement when section is absent.
- Missing frontmatter.
- Invalid YAML frontmatter.
- Non-mapping frontmatter.
- Frontmatter replacement with existing and missing frontmatter.
- Markdown title stripping with and without a blank line.
- Invalid tasks YAML syntax.
- Tasks YAML without top-level `tasks` list.
- Invalid YAML syntax for top-level key validation.
- YAML document without required top-level key.

## Acceptance Criteria

- AC001: Shared Markdown helpers exist outside `P2PWorkspace`.
- AC002: Shared YAML validators exist outside `P2PWorkspace`.
- AC003: `P2PWorkspace` uses the shared foundation helpers.
- AC004: Domain-specific renderers are intentionally left in place.
- AC005: Focused helper tests pass.
- AC006: Mapped compatibility tests and full test suite pass.
- AC007: The completed implementation report lists helpers moved, helpers left
  in place, tests run, and remaining gaps.

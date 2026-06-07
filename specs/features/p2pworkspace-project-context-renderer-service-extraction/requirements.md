# P2PWorkspace Project Context Renderer Service Extraction Requirements

## Status

Implemented and verified.

## Goal

Extract intake and project brief context rendering from `P2PWorkspace` into a
dedicated service while preserving existing intake prompt and project brief
prompt behavior.

## Requirements

- [x] R001: Intake context rendering must preserve registry status lines,
  proposals/changes/decisions/relations sections, missing-registry fallback,
  empty-registry fallback, 30-record limit, and project overview inclusion.

- [x] R002: Project brief context rendering must preserve registry status lines,
  governance warning text, proposals/changes/choices/decisions/relations
  sections, missing-registry fallback, empty-registry fallback, 50-record
  limit, project file inclusion, and intake status inclusion.

- [x] R003: `IntakeLifecycleService` must keep receiving equivalent context for
  `create_intake_prompt()`.

- [x] R004: `ProjectStateService.create_brief_prompt()` must keep producing the
  same `brief-context.md` and `brief.prompt.md` semantics.

- [x] R005: Existing CLI and MCP project brief/intake behavior must continue
  working through the same workspace facade methods.

- [x] R006: The renderer service must not import Typer, Rich, MCP, JSON-RPC,
  Git/sync, branch lifecycle, proposal mutation, project initialization, or CLI
  formatting.

## Non-Goals

- Changing intake recommendation logic.
- Changing project state refresh or import behavior.
- Changing registry generation.
- Changing prompt wording beyond preserving existing context text.

# P2PWorkspace Proposal Prompt Artifact Service Extraction Requirements

## Status

Implemented and verified.

## Goal

Extract proposal prompt generation and proposal artifact import/status behavior
from `P2PWorkspace` into a dedicated runtime service while preserving CLI, MCP,
and direct workspace compatibility.

## Requirements

- [x] R001: `P2PWorkspace.generate_prompt()` must preserve supported prompt
  kinds, generated prompt path, context payload keys, and renderer behavior.

- [x] R002: `P2PWorkspace.import_exploration()` must preserve directory/file
  import behavior, target file names, relative return paths, and no-artifact
  errors.

- [x] R003: `P2PWorkspace.exploration_status()` must preserve artifact list,
  content/quality classification, unresolved question count, and suggested next
  command semantics.

- [x] R004: `P2PWorkspace.import_artifact()` must preserve target mapping,
  source existence validation, task YAML validation, file writes, and relative
  return path.

- [x] R005: `P2PWorkspace.import_impact()` must preserve directory/file import
  behavior, YAML key validation, target file names, relative return paths, and
  no-artifact errors.

- [x] R006: Existing prompt CLI commands and MCP prompt tools must continue
  working through the same workspace facade methods.

- [x] R007: The proposal prompt artifact service must not import Typer, Rich,
  MCP, JSON-RPC, Git/sync, branch lifecycle, registry generation, project
  initialization, or CLI formatting.

## Non-Goals

- Changing prompt templates.
- Changing proposal document creation/update behavior.
- Changing decision, readiness, branch, or governance behavior.
- Adding new prompt kinds or artifact kinds.

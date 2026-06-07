# P2PWorkspace Validation Service Extraction Requirements

## Status

Implemented and verified.

## Goal

Extract project validation behavior from `P2PWorkspace` into a cohesive runtime
service while preserving the public CLI, MCP, and storage facade behavior.

## Requirements

- [x] R001: `P2PWorkspace.validate()` must keep returning the same
  `ValidationResult` shape with `ok`, `errors`, `warnings`, `infos`, and
  ordered `findings`.

- [x] R002: Validation finding records must keep the same fields: `code`,
  `severity`, `path`, `message`, and `suggested_command`.

- [x] R003: The service must preserve all existing validation categories:
  required workspace paths, YAML parsing, readiness profiles, readiness
  assessments, agent integrations, permissions, consent receipts, proposal
  structure, duplicate proposal IDs, and registry staleness.

- [x] R004: Existing finding codes, severities, relative path behavior,
  messages, and suggested commands must remain compatible unless a focused test
  proves an intentional correction.

- [x] R005: The service must not import Typer, Rich, JSON-RPC, MCP handlers, CLI
  command modules, Git sync code, branch lifecycle services, project assessment,
  or maturity/rubric computation.

- [x] R006: `storage/filesystem.py` must remain the compatibility facade for
  callers that import `ValidationFinding`, `ValidationResult`, or call
  `P2PWorkspace.validate()`.

- [x] R007: CLI `p2p validate`, MCP validation tools, skeleton validation, and
  project assessment validation dependencies must keep working through the
  facade.

- [x] R008: Focused direct service tests must cover valid projects, invalid
  YAML, invalid permissions/consents, and duplicate proposal IDs or proposal
  structure checks.

## Non-Goals

- Rewriting validation policy or changing validation codes.
- Moving registry generation, proposal lifecycle, readiness computation, MCP
  formatting, or CLI formatting.
- Editing `.p2p/` managed state by hand.

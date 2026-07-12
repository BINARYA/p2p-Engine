# PROP-093A Canonical Proposal Authoring Requirements

## Status

`draft`

## Traceability

- P2P proposal: `PROP-093 - Agent Persistence Boundaries And Proposal Authoring Flow`
- Accepted slice: `093-A - Canonical Proposal Authoring`
- Related local specs:
  - `specs/features/mcp-artifact-import-parity/`
  - `specs/features/proposal-artifact-state-readiness/`

## Problem

New proposal scaffolding currently makes several narrative exploration files look
like normal editable source files. That creates two recurring problems:

- agents may treat `.p2p/` files as a direct authoring surface instead of using
  P2P primitives;
- owners see different physical files across proposals and may assume the CLI is
  non-deterministic, even when the logical proposal workflow is still valid.

P2P should make the intended authoring flow explicit: use proposal commands,
structured contributions, questions, imports, readiness, and owner decisions as
the canonical interface. Narrative artifacts may still exist, but they must not
look like the primary way to operate P2P state.

## Goals

- Make structured proposal authoring the default and documented path.
- Stop creating editable-looking placeholder narrative artifacts for new
  proposals.
- Keep existing proposals and imported artifacts readable and compatible.
- Align CLI and MCP contribution types with the proposal-authoring concepts that
  agents need to express.
- Make post-create guidance tell agents and owners which P2P commands to use
  next.

## Non-Goals

- Do not redesign readiness scoring.
- Do not implement the full owner proposal view; that belongs to `PROP-093B`.
- Do not implement the complete agent persistent-write policy; that belongs to a
  later `PROP-093C` slice.
- Do not change adaptive init, MCP root handling, or `.gitignore` behavior.
- Do not solve software-specific specs lifecycle; that is handled by `PROP-094`.
- Do not add generic filesystem write tools for `.p2p/`.

## Scope

In scope:

- proposal creation scaffolding;
- structured contribution types and validation;
- CLI and MCP contribution parity;
- prompt/import/status behavior when narrative artifacts are missing;
- owner-facing next-step guidance after proposal creation;
- tests and documentation for the canonical authoring flow.

Out of scope:

- branch publication, merge, or remote collaboration behavior;
- direct migration of old proposal directories;
- file deletion from existing proposals;
- any owner-governance decision automation.

## Requirements

### R001: New proposal scaffolds avoid editable placeholder artifacts

When a new proposal is created, P2P shall not create empty or placeholder
exploration narrative files that look like hand-editable source-of-truth files.

Narrative artifacts such as findings, alternatives, open questions, assumptions,
risks, suggested scope, and free-form exploration shall be materialized only
when there is meaningful generated, imported, or explicitly requested content.

### R002: Existing proposal artifacts remain compatible

P2P shall continue to read, list, import, render, and use existing narrative
artifact files in already-created proposals.

The implementation shall not delete or rewrite existing proposal artifact files
as part of this slice.

### R003: Missing narrative artifacts are expected states

Proposal prompt generation, readiness context, artifact status, imports, and
proposal display code shall tolerate missing narrative artifacts.

Missing optional artifacts shall be represented as logical status, not as
storage corruption.

### R004: Post-create guidance uses P2P primitives

After creating a proposal, CLI output shall guide the owner or agent toward
canonical P2P operations, such as:

- adding structured contributions;
- importing external exploration material;
- initializing or refreshing readiness;
- asking or resolving proposal questions;
- reviewing the full proposal state before owner decision.

The guidance shall not tell agents to edit `.p2p/` files directly.

### R005: Contribution concepts cover canonical authoring needs

The contribution model shall support the concepts needed by proposal authoring:

- finding;
- open question;
- alternative;
- risk;
- assumption;
- constraint;
- objection;
- implementation suggestion;
- scope boundary.

This may be implemented with additive enum values or explicit compatibility
mappings. Existing contribution type values shall remain accepted.

### R006: CLI and MCP contribution schemas stay aligned

Any new or aliased contribution types shall be accepted consistently by:

- service-level validation;
- CLI argument parsing and help;
- MCP tool schemas and handlers;
- tests that assert the allowed value list.

### R007: Invalid contribution types produce actionable errors

When a contribution type is invalid, P2P shall report the allowed contribution
types in the error message.

### R008: Imports remain the way to bind external narrative material

When an owner or agent has external analysis text, the supported path shall be
an explicit P2P import operation, not direct writes into `.p2p/`.

Imports shall preserve existing validation and shall not require all standard
narrative artifact files to exist beforehand.

### R009: No governance decisions are inferred

Structured contributions, imports, and generated guidance shall not accept,
reject, defer, decide, or otherwise finalize governance state.

Owner-controlled actions remain owner-controlled.

### R010: Documentation explains the canonical flow

Documentation and generated command help shall explain that:

- `.p2p/` is governed state;
- proposal authoring happens through P2P commands or explicit write-safe MCP
  tools;
- narrative files may be absent until content exists;
- physical file uniformity is not the same as logical proposal completeness.

## Public Surface Impact

### CLI

- Add or refine post-create guidance.
- Preserve existing proposal creation options.
- Preserve existing contribution commands while adding contribution type support.
- Keep existing `p2p proposal show` behavior stable unless an explicitly
  additive flag is introduced.

### MCP

- Update contribution schemas when contribution types change.
- Keep MCP tools scoped to explicit P2P operations.
- Do not add raw `.p2p` file mutation tools.

### Storage

- Change only the file footprint for newly created proposals.
- Preserve compatibility for existing proposal directories that contain
  narrative files.
- Treat missing optional narrative files as normal.

## Compatibility

Existing projects created by earlier releases may contain placeholder narrative
files. Those files shall continue to be read and displayed.

The implementation shall be additive for contribution types and conservative for
CLI/MCP behavior. Any changed default output shall be limited to clearer
guidance and the absence of new placeholder files.

## Risks

- Removing placeholder creation may break tests that assert exact file lists.
- Agents may still infer direct file editing from old generated instructions.
  Later `PROP-093C` work must harden generated policy text.
- Adding contribution types may create duplicate concepts if aliases are not
  documented clearly.
- MCP schema updates can drift from CLI validation unless both are covered by
  tests.

## Acceptance Criteria

- New proposal creation no longer writes editable-looking empty narrative
  placeholders.
- Existing proposals with narrative files still work without migration.
- Missing optional narrative artifacts do not fail prompt, readiness, import, or
  display flows.
- Contribution types cover findings, open questions, alternatives, risks,
  assumptions, constraints, objections, implementation suggestions, and scope
  boundaries.
- CLI and MCP expose the same allowed contribution types.
- Post-create guidance points to P2P primitives instead of direct `.p2p` edits.
- Focused service, CLI, and MCP tests cover the changed behavior.


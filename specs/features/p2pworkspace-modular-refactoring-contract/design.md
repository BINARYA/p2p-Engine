# P2PWorkspace Modular Refactoring Contract Design

## Overview

This feature converts accepted proposal `PROP-059` into a local development
contract. It does not refactor runtime code. It creates the rules and roadmap
that later implementation work must follow.

## Covered Requirements

- R001: Agent Architecture Rules
- R002: Development Guidelines
- R003: Stable Compatibility Facade
- R004: Compatibility Boundaries
- R005: Refactoring Sequence
- R006: First Future Extraction Candidate
- R007: No Runtime Change In First Deliverable

## Design Decisions

### D001 - Keep Governance And Development Guidance Separate

`AGENTS.md` remains the fast operational boundary for agents. It should include
only concise, non-negotiable architecture rules.

`docs/DEVELOPMENT-GUIDELINES.md` carries the full explanation for humans and
agents: current architecture, target architecture, allowed patterns,
anti-patterns, roadmap, and verification expectations.

Rationale: agents need short hard rules at startup, while maintainers need a
larger reference document.

### D002 - Treat P2PWorkspace As A Facade

The development contract states that `P2PWorkspace` remains the compatibility
facade for existing callers. Future services and adapters should live behind
that facade until a separate proposal changes public APIs.

Rationale: this keeps existing CLI, MCP, tests, and downstream users stable
while allowing internal structure to improve.

### D003 - Prefer Internal Managers Over Mechanical Split

The chosen approach is internal managers/services behind the facade. The
rejected options are monolith-only documentation, mechanical file split, and
immediate public API redesign.

Rationale: mechanical splitting reduces file size but does not reduce coupling.
Public API redesign is too disruptive for the current project stage.

### D004 - Consent/Permissions First

The roadmap should select consent/permissions as the preferred first future
code extraction.

Rationale: it has a relatively clear boundary, high safety value, lower CLI
presentation exposure, and can establish a repeatable extraction pattern.

### D005 - No Runtime Change In First Deliverable

The initial implementation should not modify `src/`. It should update agent
rules and maintained documentation only.

Rationale: the accepted proposal is an architecture contract. Runtime behavior
changes belong to later specs and implementation work.

## Compatibility

Later refactoring must preserve:

- CLI command names and observable output used by tests and agents;
- MCP tool names, schemas, and payload behavior;
- `.p2p` storage paths and artifact formats;
- validation and registry refresh behavior;
- consent receipt lifecycle and permission-gated semantics;
- Git/sync behavior;
- owner-controlled governance boundaries.

Breaking changes require a separate proposal.

## Verification Strategy

For the first deliverable:

- verify no `src/` files changed;
- review `AGENTS.md` for concise hard rules;
- review `docs/DEVELOPMENT-GUIDELINES.md` for complete guidance;
- run `p2p validate`.

For later extraction work:

- run focused CLI tests for touched commands;
- run MCP tests when tools are exposed or payloads are touched;
- run storage/validation tests for `.p2p` artifacts;
- run Git/sync tests for branch, remote, commit, publish, merge, consent, or
  audit behavior.

## Verification Evidence

The first deliverable was verified as documentation-only.

Reviewed commands:

```bash
git status --short src
git diff --name-only -- src
.venv/bin/p2p validate
```

Results:

- `git status --short src` reported no runtime source changes.
- `git diff --name-only -- src` reported no runtime source changes.
- `.venv/bin/p2p validate` completed with `errors: 0`, `warnings: 0`,
  `infos: 0`, and `findings: none`.

Local spec consistency:

- `requirements.md` marks R001-R007 implemented.
- `tasks.md` marks T001-T022 complete with evidence in `AGENTS.md`,
  `docs/DEVELOPMENT-GUIDELINES.md`, this design document, and the completed
  inventory map.
- The inventory map remains the detailed implementation reference for future
  extraction features.

# Design - Domain-Aware Visible Project Definition Export

## Requirements Covered

- R001, R002, R003, R004, R005, R006

## Key Decisions

- D001: Treat generic project definition export as a project-level operation, not
  a Change Set software-spec operation.
  Rationale: every domain can be defined as a project, but not every domain is
  software.

- D002: Keep `.p2p/` available for provenance and indexes, but write
  human-facing project output to a visible root-level directory.
  Rationale: normal users should find the generated definition without knowing
  hidden P2P internals.

- D003: Gate OpenSpec and Spec Kit exports behind software-compatible domain or
  explicit software-compatible export profile.
  Rationale: those targets are meaningful for software, but misleading for
  domains such as physical objects, events, or board games.

- D004: Treat existing `software-spec` commands as legacy or software-only until
  removal/migration is explicitly planned.
  Rationale: abrupt removal may break existing tests and documented examples;
  behavior should move in slices.

## Proposed Components

- `src/p2p_engine/cli.py`
  Add or revise project definition export commands.

- `src/p2p_engine/storage/filesystem.py`
  Add project-level export generation that does not require Change Sets.

- `src/p2p_engine/mcp/tools.py`
  Expose domain-aware project definition export tools if MCP should support the
  workflow.

- `docs/CLI-GUIDE.md`
  Replace default software-spec guidance with project definition export
  guidance.

- `.codex/skills/p2p-engine/SKILL.md`
  Stop telling agents to generate software-spec for project definition export by
  default.

- `tests/test_cli.py`
  Cover CLI behavior.

- `tests/test_mcp.py`
  Cover MCP behavior when MCP tools are updated.

## Output Shape

Candidate visible root-level directory:

```text
p2p-output/
  generic/
    project.md
    traceability.yml
  openspec/
    ...
  speckit/
    ...
```

The exact directory name is still open. It must be visible in the project root
and not start with a dot.

## Data And Contracts

The generic export should be generated from accepted project memory and current
project state. It should include at minimum:

- project identity and domain;
- goals and non-goals;
- scope;
- accepted decisions;
- relevant constraints;
- unresolved questions;
- source traceability;
- domain-specific sections when available.

## Error Handling

- Unsupported target for domain: fail with a clear message naming the domain and
  allowed targets.
- Missing project state: generate from accepted memory when possible or ask the
  user to refresh project state through the appropriate public command.
- Existing output directory: overwrite deterministic generated files only, or
  use a clear conflict policy if user-authored files are present.

## Migration And Compatibility

Initial implementation can keep `p2p spec ...` available while moving docs,
skills, and recommended workflows to project definition export.

Potential migration stages:

1. Add domain-aware project definition export.
2. Update skills and docs to recommend the new workflow.
3. Mark software-spec workflow as software-only or compatibility.
4. Later decide whether to deprecate Change Set based software-spec exports.

## Risks And Tradeoffs

- Keeping both workflows temporarily may confuse users.
- Moving outputs to root may create naming conflicts.
- Domain detection may be too weak unless export profiles are explicit.
- Root-level output requires a clear generated-file policy to avoid overwriting
  user-authored content.

## Out Of Scope

- Implementing code generation for projects.
- Invoking OpenSpec, Spec Kit, or AI tools directly.
- Cleaning old `.p2p/outputs/software-spec` artifacts.

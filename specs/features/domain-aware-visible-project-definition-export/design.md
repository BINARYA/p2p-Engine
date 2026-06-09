# Design - Domain-Aware Visible Project Definition Export

## Requirements Covered

- R001-R012, N001-N005, E001-E005

## Key Decisions

- D001: Implement visible project definition export as a project-level service.
  Rationale: the default output applies to every P2P project and must not depend
  on a Change Set or software-spec workflow.

- D002: Write generated human-facing output to root-level `outputs/`.
  Rationale: `PROP-083` accepted `outputs/` as the MVP convention because it is
  discoverable and avoids confusion with `.p2p/project`.

- D003: Use `outputs/latest/project.md` as the canonical default output.
  Rationale: one chaptered Markdown file is easiest for humans and agents to
  inspect as the default project definition.

- D004: Preserve previous `outputs/latest/` content under deterministic
  `outputs/review-###/` folders before replacing latest.
  Rationale: refresh history should be visible and auditable without becoming
  P2P source-of-truth state.

- D005: Keep `.p2p/outputs/spec-export/...` and `p2p spec export` unchanged as
  compatibility behavior.
  Rationale: existing tests, MCP tools, and Work planning can depend on that
  behavior. Migration or deprecation is a separate owner decision.

- D006: Add nested profile root `outputs/latest/exports/` but do not migrate all
  legacy software profile contents in the first slice.
  Rationale: the proposal requires the shape to exist; moving every legacy export
  immediately would increase compatibility risk.

## Components

- `src/p2p_engine/services/visible_project_export.py`
  New service that renders the default Markdown document, writes `outputs/`,
  archives previous latest output, and reports status.

- `src/p2p_engine/storage/filesystem.py`
  Facade delegation only:
  `export_visible_project_definition()` and
  `visible_project_definition_export_status()`.

- `src/p2p_engine/cli_commands/project_ops.py`
  Project-level CLI commands under `p2p project export` and
  `p2p project export-status`.

- `src/p2p_engine/mcp/catalog/work_specs.py` or project catalog/handler
  Optional MCP surface for write-safe visible export and read-only status.
  Prefer project catalog if a project-specific handler already owns project
  operations.

- `docs/CLI-GUIDE.md`, `docs/MCP.md`
  Document visible project export as the default project definition workflow and
  leave spec export as compatibility/software-oriented handoff.

## Output Shape

```text
outputs/
  latest/
    project.md
    exports/
      .gitkeep or generated profile folders as needed
  review-001/
    project.md
    exports/
  review-002/
    project.md
    exports/
```

The implementation may omit `.gitkeep`; empty `exports/` is enough if the
filesystem preserves it.

## Project Document Chapters

The default `project.md` should contain stable chapters:

- Generated Metadata
- Executive Summary
- Project Purpose
- Domain And Context
- Scope
- Accepted Proposals And Decisions
- Requirements And Acceptance
- Alternatives And Tradeoffs
- Risks
- Assumptions
- Open Questions
- Readiness
- Delivery And Export Context
- Source Traceability

Content should be synthesized from available P2P artifacts. Missing optional
content should be stated explicitly as not recorded, not invented.

## Data Sources

Use local P2P state already exposed through repository services:

- project metadata from `.p2p/project.yml` or existing project state readers;
- proposals from proposal directories, especially accepted proposal documents;
- proposal artifacts such as alternatives, findings, risks, assumptions,
  open-questions, readiness, and impact files when present;
- generated project state/brief where existing services expose it.

The service must treat these as inputs. It must not mutate `.p2p/` when exporting
visible project output.

## Archive Policy

Before writing a new `outputs/latest/`:

1. If `outputs/latest/` does not exist or contains no files, write latest
   directly.
2. If it contains files, copy or move the whole directory to the first available
   `outputs/review-###/`.
3. Remove/recreate `outputs/latest/` for the new export.

Using move is acceptable because the latest directory is generated output, not
source of truth. The operation must stay under repository root.

## CLI Contract

```bash
p2p project export
p2p project export-status
```

`project export` prints the generated path and any archived review path.
`project export-status` prints whether latest exists and lists review snapshots.

## MCP Contract

If implemented in this slice:

- `p2p_project_export`: write-safe deterministic tool that writes visible
  generated project output.
- `p2p_project_export_status`: read-only tool that reports latest and reviews.

These tools must not accept, reject, merge, publish, or otherwise mutate
governance state.

## Compatibility

- Existing `.p2p/outputs/spec-export/...` remains intact.
- Existing `p2p spec export`, `export-status`, `export-show`, and
  `export-validate` behavior remains unchanged.
- Existing Work planning that validates spec exports remains unchanged.

## Follow-Up Note

After this feature is implemented, revisit the proposal-readiness agent skill
and readiness calculation. `PROP-083` exposed that the agent guidance should
push harder through missing artifacts and that readiness `refresh/init` behavior
can remain too conservative after artifacts are complete.

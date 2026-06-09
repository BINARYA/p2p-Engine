# Execution Plan - PROP-083

## Implementation Sequence

1. Inventory existing `.p2p/outputs` producers and consumers across CLI, MCP,
   tests, and documentation before changing behavior.
2. Introduce a domain-generic visible project definition renderer that reads
   accepted P2P memory and produces a chaptered Markdown document.
3. Write the default generated document to `outputs/latest/project.md`.
4. Add deterministic review snapshot handling so prior generated output is
   preserved under `outputs/review-001`, `outputs/review-002`, and later review
   directories before replacing `outputs/latest`.
5. Add export profile routing under `outputs/latest/exports/<profile-or-vertical>/`
   for software-specific and future vertical-specific outputs.
6. Preserve existing `.p2p/outputs` public behavior or provide an explicit
   migration, mirroring, or deprecation path backed by tests.
7. Document that `.p2p/` remains the managed source of truth and `outputs/`
   contains generated human-facing artifacts.

## Verification

- A default export creates `outputs/latest/project.md`.
- Re-running export preserves the previous latest output in the next
  deterministic review directory.
- Software-specific exports are nested under `outputs/latest/exports/` and do
  not replace the default project document.
- Existing tests or compatibility checks for `.p2p/outputs` continue to pass or
  are updated only with an explicit migration rationale.
- Generated output includes source and generation metadata sufficient to avoid
  confusing generated files with managed P2P state.

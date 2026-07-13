# Clarifications - PROP-099

## Resolved Scope Clarifications

### Full Publication Pipeline

PROP-099 should define the full Human Project Publication Pipeline, not only the curated Markdown step. The pipeline includes deterministic complete export, semantic curator skill, publication validation, owner review, and neutral PDF rendering.

The neutral PDF can be part of the first slice only if the flow remains explicitly separated into independently reviewable stages:

- complete export;
- curator skill output;
- publication validation;
- owner review;
- renderer output.

### First Slice Output Convention

The first implementation must not automatically replace `outputs/latest/project.md`. In the first slice:

- `outputs/latest/project.md` remains the complete export;
- `outputs/latest/project.curated.md` is the owner-review candidate;
- `outputs/latest/project.pdf` is rendered from validated curated Markdown.

Promotion of curated Markdown to primary `project.md` can be considered only after owner review and later pipeline validation.

### Hybrid Responsibility Model

Curation should use a hybrid model:

- CLI/engine prepares inputs, defines contracts, archives versions, and validates output;
- `p2p-project-curator` performs semantic synthesis, grouping, rewriting, and narrative construction;
- owner reviews the curated candidate;
- renderer handles presentation only and must not modify project facts.

The agentic curation stage is expected to be the highest-impact part for producing a comprehensible project document with a robust narrative thread around the selected vertical and its specific characteristics. Deterministic preparation, validation, and rendering should bound and review the curator output, not replace the semantic editorial work.

### Software Spec Boundary

The human publication pipeline must remain separate from the P2P-native software specification lifecycle and downstream OpenSpec/Spec Kit exports. The curated project document can describe those lanes, but must not replace them.

# Requirements

## Functional Requirements

### PROP-099 - Project Output Lifecycle and Retention Policy

Define PROP-099 as the Human Project Publication Pipeline. The target pipeline is: .p2p managed state to p2p project export to complete project.md, then p2p-project-curator skill to project.curated.md, then publication validation, then owner review, then neutral PDF renderer to project.pdf. The pipeline must remain explicitly separated into independently reviewable stages. The complete export, curated Markdown, validation result, owner review outcome, and rendered PDF should each have clear boundaries so a single stage can be inspected, revised, replaced, or improved without collapsing the whole flow. The existing deterministic export continues to be complete, traceable, regenerable, and close to P2P state. The curator is an agentic semantic editor and is expected to be the primary quality driver for a comprehensible project document: it identifies the central project thesis, reads the active vertical and project definition, adapts structure to the domain, builds a robust narrative thread around the selected vertical and its peculiarities, groups proposals by capability, separates current state from history, distinguishes accepted, implemented, planned, partial, pending, missing, and legacy evidence, removes placeholders and repetition, moves excessive detail to appendices where appropriate, preserves risks and open questions, and maintains traceability. The first slice should use a minimal publication profile to bound variability: audience mixed, depth standard, language project_default, vertical_structure adaptive, include_appendix false by default, and theme neutral-v1. Deterministic stages provide input discipline, contracts, validation, archival behavior, and rendering; they bound and review the curator output, but they must not replace the semantic editorial work. The publication validator is mostly deterministic and checks the document contract: one H1, coherent headings, executive summary, no known placeholders in the main body, no wholesale proposal dumps in the main text, explicit separation of project state and implementation state, accepted/planned/pending/missing distinctions, source-of-truth warning, traceability, vertical-compatible structure, and Markdown suitable for PDF rendering. The neutral PDF renderer consumes only validated curated Markdown and handles presentation, not content. The first implementation should be an end-to-end minimal slice: valid installable p2p-project-curator skill, compact-surfaces-first input discipline, vertical-aware structure, output project.curated.md, minimal publication validation, neutral project.pdf, manual owner review, traceability, and no direct .p2p mutation. Later slices may add CLI orchestration such as project publish prepare, validate, render, and status; publication packages such as project.full.md, project.md, project.appendix.md, project.pdf, publication-manifest.yml, and render-report.yml; and richer publication profiles for audience, depth, language, vertical structure, appendix inclusion, and theme.

## Non-Goals / Exclusions

- Automatic Git commits, branches, tags, or merges.

## Constraints

Do not treat raw proposal discussion as implementation requirements without accepted scope.

## Open Questions

Not specified yet.

# PROP-099 - Project Output Lifecycle and Retention Policy

## Status

`accepted`

## Problem

P2P Engine can already transform governed project memory, including ideas, contributions, proposals, decisions, readiness, verticals, Change Sets, Work items, risks, assumptions, and requirements, into a visible project export. That export is complete, traceable, useful as consolidated memory, and derived from the managed .p2p state. The problem is that completeness and editorial readability are different goals. The current export still reflects the internal P2P memory structure: proposal-oriented organization, repeated sections, detailed governance blocks, empty placeholders, long lists of requirements and risks, and historical information mixed with current project state. An owner, stakeholder, contributor, or implementer should not need to reconstruct the project by reading many proposals and internal artifacts. The project needs a human publication pipeline that transforms complete governed memory into a readable, project-first, publishable document.

## Context

This proposal follows PROP-083. The source of truth remains .p2p. The existing project export remains valuable as a deterministic and auditable complete export. PROP-099 should add an explicit editorial and publication layer between that complete export and final human-facing outputs. Directly rendering the complete export to PDF would only create a formatted version of a still proposal-first document; therefore curation, validation, and rendering must be separate stages.

## Goals

- Define a Human Project Publication Pipeline from governed P2P state to complete export, curated Markdown, publication validation, and neutral PDF.
- Keep deterministic export, semantic curation, owner review, publication validation, and PDF rendering as independent and inspectable stages.
- Make the curated document project-first, vertical-aware, traceable, and readable by humans who do not know P2P internals.
- Define an incremental implementation path with a minimal end-to-end slice first and richer CLI orchestration, publication packages, profiles, and themes later.

## Non-Goals

- Do not make generated outputs a new source of truth; .p2p remains governed project memory.
- Do not make the curator decide governance outcomes, readiness, implementation status, or owner choices.
- Do not replace the P2P-native software specification lifecycle, OpenSpec, Spec Kit, or downstream implementation exports.
- Do not require a fully deterministic curator in the first slice; semantic curation may be agentic but must be bounded by contracts and validation.
- Do not introduce multiple themes, branding, visual editors, template marketplaces, sophisticated appendices, automatic permanent replacement of project.md, or full MCP parity in the first slice.

## Proposal

Define PROP-099 as the Human Project Publication Pipeline. The target pipeline is: .p2p managed state to p2p project export to complete project.md, then p2p-project-curator skill to project.curated.md, then publication validation, then owner review, then neutral PDF renderer to project.pdf. The pipeline must remain explicitly separated into independently reviewable stages. The complete export, curated Markdown, validation result, owner review outcome, and rendered PDF should each have clear boundaries so a single stage can be inspected, revised, replaced, or improved without collapsing the whole flow. The existing deterministic export continues to be complete, traceable, regenerable, and close to P2P state. The curator is an agentic semantic editor and is expected to be the primary quality driver for a comprehensible project document: it identifies the central project thesis, reads the active vertical and project definition, adapts structure to the domain, builds a robust narrative thread around the selected vertical and its peculiarities, groups proposals by capability, separates current state from history, distinguishes accepted, implemented, planned, partial, pending, missing, and legacy evidence, removes placeholders and repetition, moves excessive detail to appendices where appropriate, preserves risks and open questions, and maintains traceability. The first slice should use a minimal publication profile to bound variability: audience mixed, depth standard, language project_default, vertical_structure adaptive, include_appendix false by default, and theme neutral-v1. Deterministic stages provide input discipline, contracts, validation, archival behavior, and rendering; they bound and review the curator output, but they must not replace the semantic editorial work. The publication validator is mostly deterministic and checks the document contract: one H1, coherent headings, executive summary, no known placeholders in the main body, no wholesale proposal dumps in the main text, explicit separation of project state and implementation state, accepted/planned/pending/missing distinctions, source-of-truth warning, traceability, vertical-compatible structure, and Markdown suitable for PDF rendering. The neutral PDF renderer consumes only validated curated Markdown and handles presentation, not content. The first implementation should be an end-to-end minimal slice: valid installable p2p-project-curator skill, compact-surfaces-first input discipline, vertical-aware structure, output project.curated.md, minimal publication validation, neutral project.pdf, manual owner review, traceability, and no direct .p2p mutation. Later slices may add CLI orchestration such as project publish prepare, validate, render, and status; publication packages such as project.full.md, project.md, project.appendix.md, project.pdf, publication-manifest.yml, and render-report.yml; and richer publication profiles for audience, depth, language, vertical structure, appendix inclusion, and theme.

## Acceptance Criteria

- The proposal defines the Human Project Publication Pipeline and clearly separates governed content, deterministic complete export, agentic editorial curation, publication validation, owner review, and PDF rendering.
- Each pipeline stage is independently reviewable: complete export, curated Markdown, validation result, owner review outcome, and rendered PDF have explicit boundaries and artifacts or reports.
- The proposal defines the first implementation slice: installable p2p-project-curator skill, compact-surfaces-first input discipline, vertical-aware curation, project.curated.md, minimal deterministic publication validation, neutral project.pdf, manual owner review, traceability, and no direct .p2p mutation.
- The proposal defines the agentic curator as the primary quality driver for human comprehensibility, vertical-specific narrative, capability grouping, repetition removal, and robust project-first flow.
- The proposal defines deterministic stages as boundaries and controls around curation: input discipline, contracts, validation, archival behavior, and presentation-only rendering.
- The proposal defines a minimal publication profile for the first slice: audience mixed, depth standard, language project_default, adaptive vertical structure, appendix disabled by default, and neutral-v1 theme.
- The proposal defines status vocabulary for accepted, implemented, planned, partial, pending owner decision, missing evidence, legacy or not assessed, advisory, and blocked material.
- The proposal defines that project.md remains the complete export in the first slice, while project.curated.md is the owner-review candidate and project.pdf is rendered from the curated validated Markdown.
- The proposal defines a later migration path where project.full.md preserves the complete export, project.md may become the curated human document, and publication metadata or appendices may be added.
- The proposal defines publication validation quality gates for headings, placeholders, executive summary, proposal dump avoidance, project versus implementation status separation, traceability, source-of-truth warning, vertical fit, and PDF-ready Markdown.
- The proposal defines that the PDF renderer is neutral and presentation-only: it must not rewrite content, remove sections, alter evidence status, modify decisions, or reinterpret readiness.
- The proposal defines alternatives, tradeoffs, risks, assumptions, impact with PROP-083, and out-of-scope boundaries for software-spec and downstream export workflows.

## Decision

Pending.

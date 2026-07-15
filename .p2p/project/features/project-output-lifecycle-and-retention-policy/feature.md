# Project Output Lifecycle and Retention Policy

## Provenance

- Proposal: PROP-099
- Source: .p2p/proposals/PROP-099-project-output-lifecycle-and-retention-policy

## Problem

P2P Engine can already transform governed project memory, including ideas, contributions, proposals, decisions, readiness, verticals, Change Sets, Work items, risks, assumptions, and requirements, into a visible project export. That export is complete, traceable, useful as consolidated memory, and derived from the managed .p2p state. The problem is that completeness and editorial readability are different goals. The current export still reflects the internal P2P memory structure: proposal-oriented organization, repeated sections, detailed governance blocks, empty placeholders, long lists of requirements and risks, and historical information mixed with current project state. An owner, stakeholder, contributor, or implementer should not need to reconstruct the project by reading many proposals and internal artifacts. The project needs a human publication pipeline that transforms complete governed memory into a readable, project-first, publishable document.

## Proposal

Define PROP-099 as the Human Project Publication Pipeline. The target pipeline is: .p2p managed state to p2p project export to complete project.md, then p2p-project-curator skill to project.curated.md, then publication validation, then owner review, then neutral PDF renderer to project.pdf. The pipeline must remain explicitly separated into independently reviewable stages. The complete export, curated Markdown, validation result, owner review outcome, and rendered PDF should each have clear boundaries so a single stage can be inspected, revised, replaced, or improved without collapsing the whole flow. The existing deterministic export continues to be complete, traceable, regenerable, and close to P2P state. The curator is an agentic semantic editor and is expected to be the primary quality driver for a comprehensible project document: it identifies the central project thesis, reads the active vertical and project definition, adapts structure to the domain, builds a robust narrative thread around the selected vertical and its peculiarities, groups proposals by capability, separates current state from history, distinguishes accepted, implemented, planned, partial, pending, missing, and legacy evidence, removes placeholders and repetition, moves excessive detail to appendices where appropriate, preserves risks and open questions, and maintains traceability. The first slice should use a minimal publication profile to bound variability: audience mixed, depth standard, language project_default, vertical_structure adaptive, include_appendix false by default, and theme neutral-v1. Deterministic stages provide input discipline, contracts, validation, archival behavior, and rendering; they bound and review the curator output, but they must not replace the semantic editorial work. The publication validator is mostly deterministic and checks the document contract: one H1, coherent headings, executive summary, no known placeholders in the main body, no wholesale proposal dumps in the main text, explicit separation of project state and implementation state, accepted/planned/pending/missing distinctions, source-of-truth warning, traceability, vertical-compatible structure, and Markdown suitable for PDF rendering. The neutral PDF renderer consumes only validated curated Markdown and handles presentation, not content. The first implementation should be an end-to-end minimal slice: valid installable p2p-project-curator skill, compact-surfaces-first input discipline, vertical-aware structure, output project.curated.md, minimal publication validation, neutral project.pdf, manual owner review, traceability, and no direct .p2p mutation. Later slices may add CLI orchestration such as project publish prepare, validate, render, and status; publication packages such as project.full.md, project.md, project.appendix.md, project.pdf, publication-manifest.yml, and render-report.yml; and richer publication profiles for audience, depth, language, vertical structure, appendix inclusion, and theme.

## Decision

# Decision - PROP-099

## Status

`accepted`

## Outcome

accepted

## Reason

Owner accepts the decision-ready human project publication pipeline as the direction for readable, vertical-aware project outputs.

## Date

2026-07-13

## Approver

local

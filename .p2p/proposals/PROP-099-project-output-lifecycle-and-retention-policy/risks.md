# Risks - PROP-099

## Elegant PDF On Weak Content

Risk: rendering the raw export could create a polished but still unreadable artifact.

Mitigation: render only curated Markdown that passes publication validation.

## Parallel Source Of Truth

Risk: generated outputs may be mistaken for governed project state.

Mitigation: every output declares `.p2p/` as the source of truth and itself as derived.

## Information Loss During Curation

Risk: semantic compression may remove important decisions, risks, assumptions, or gaps.

Mitigation: preserve traceability, keep optional appendices, and require explicit evidence status labels.

## Status Confusion

Risk: accepted direction, implemented behavior, planned work, pending material, and missing evidence may be blended.

Mitigation: use a required status vocabulary and validation gates.

## Rigid Structure

Risk: the curator may impose a software-like outline on non-software projects.

Mitigation: derive specific sections from the active vertical and project definition.

## Excessive Agent Variability

Risk: repeated curation runs may produce inconsistent structure.

Mitigation: use publication profiles, stable output contracts, compact input discipline, and deterministic validation.

## Renderer Overreach

Risk: the PDF renderer may rewrite or filter content.

Mitigation: define the renderer as presentation-only.

## Scope Creep

Risk: the proposal could absorb themes, branding, visual editors, template marketplaces, advanced packages, MCP parity, or software spec generation.

Mitigation: deliver a minimal end-to-end slice first and defer advanced publication capabilities.

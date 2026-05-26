# Research: P2P Software Spec Generator MVP

## Decision: Export From P2P-Native Software Spec

Rationale: `CHANGE-012` has a normalized software spec with requirements, design, commands, data model, acceptance, and provenance. Exporting from that layer avoids coupling downstream tools to raw P2P proposal folders.

Alternatives considered:

- Export raw proposals directly: rejected because it bypasses the normalized spec layer.
- Invoke Spec Kit directly: rejected for this MVP because the exporter should be deterministic and offline.
- Generate a conservative Spec Kit-oriented directory: selected for traceability and low coupling.

## Open Questions

- NEEDS CLARIFICATION: Whether this bundle should be copied into a real `specs/` directory or consumed from `.p2p/outputs/spec-export/`.
- NEEDS CLARIFICATION: Which Spec Kit integration should execute the generated artifacts.

## Source Provenance

source:
  change: CHANGE-012
  included_proposals:
    - PROP-026
  accepted_decisions: []
  rationale:
    - CHANGE-001 established Change Set as the operational unit and separated execution domains, implementation targets, spec targets, and export targets.
    - PROP-010 selected a P2P-native software spec before downstream export.
generated_from:
  - .p2p/changes/CHANGE-012-p2p-software-spec-generator-mvp/change.md
  - .p2p/changes/CHANGE-012-p2p-software-spec-generator-mvp/tasks.yml
  - .p2p/proposals/PROP-026-p2p-software-spec-generator-mvp/proposal.md
  - .p2p/proposals/PROP-026-p2p-software-spec-generator-mvp/decision.md
refinement:
  mode: external_refined_import
  based_on: .p2p/outputs/software-spec/CHANGE-012/spec-refine.prompt.md
  boundary: Refines structure and clarity without adding requirements outside accepted P2P sources.

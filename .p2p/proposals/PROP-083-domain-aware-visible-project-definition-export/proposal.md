# PROP-083 - Domain-Aware Visible Project Definition Export

## Status

`accepted`

## Problem

P2P Engine currently routes accepted project intent through Change Set software-spec and spec-export outputs. This makes every project look like a software implementation workflow, even when the project domain is not software. P2P Engine is meant to define projects in detail across many vertical domains, not only to produce software delivery artifacts. The current generated outputs are also hidden under .p2p/outputs, which makes the human-facing project definition hard for normal users to find and inspect. Users need a visible, comprehensive, domain-aware project definition that captures what emerged during proposal preparation, exploration, decisions, and refinement.

## Context

The accepted project memory already contains proposals, decisions, readiness, questions, risks, assumptions, alternatives, and refinement history. PROP-083 should turn that memory into a visible human-facing project definition. Existing software-specific exports may remain useful, but they should become specialized export profiles nested under the generic visible output model rather than the universal default. The root folder should be named outputs/ instead of project/ to avoid confusion with .p2p/project. Existing .p2p outputs should not be removed or moved without a compatibility check.

## Goals

- Generate a default human-readable project definition for every P2P project.
- Write the default visible output to outputs/latest/project.md as a single chaptered Markdown document.
- Preserve prior generated project definitions by moving or writing snapshots under outputs/review-001, outputs/review-002, and later review directories.
- Support different vertical domains through a generic project definition model instead of assuming software.
- Allow domain-specific or tool-specific exports, such as software-spec, OpenSpec, or Spec Kit, as nested profiles under outputs/latest/exports/<profile-or-vertical>/ when compatible.
- Preserve compatibility with existing .p2p/outputs and CLI/API behavior until migration or deprecation is explicitly verified.

## Non-Goals

- Do not make software-spec, OpenSpec, or Spec Kit the default export for non-software domains.
- Do not delete existing .p2p outputs without implementation-time compatibility review.
- Do not make the root outputs/ location configurable in the MVP.
- Do not split the default human-facing project definition into many default files.

## Proposal

Introduce a domain-aware visible project definition export. The default export for every P2P project should be a human-facing, comprehensive Markdown document written to outputs/latest/project.md. The document should be organized in chapters and synthesize accepted P2P memory: project purpose, domain, problem framing, accepted proposals, decisions, requirements, scope boundaries, alternatives, tradeoffs, risks, assumptions, open questions, readiness notes, and relevant implementation or delivery context. The output should be generic across verticals and should not assume that the project is software. The visible root-level outputs/ directory is intentional and not configurable in the MVP because human accessibility is more important than keeping the repository root minimal; outputs/ is preferred over project/ because it clearly describes generated visible outputs and avoids confusion with .p2p/project. Each export run should preserve review history by writing or archiving prior versions under outputs/review-001, outputs/review-002, and later review directories. Domain-specific exports are additional nested profiles, not the default. For software-compatible projects, software-spec, OpenSpec, Spec Kit, or similar outputs may be generated under outputs/latest/exports/software-spec/, outputs/latest/exports/openspec/, outputs/latest/exports/speckit/, or equivalent profile folders. Other verticals may define their own export profiles under outputs/latest/exports/<profile-or-vertical>/. Existing .p2p/outputs behavior must be treated as a compatibility surface: the implementation should verify whether current generated artifacts are still needed, preserve public CLI/API expectations, and only remove, deprecate, or relocate legacy outputs through an explicit compatibility path.

## Acceptance Criteria

- A default visible project-definition export generates a single chaptered Markdown file at outputs/latest/project.md.
- The default project document is domain-generic and does not require the project to be software-oriented.
- Each export refresh preserves prior generated output under deterministic review folders such as outputs/review-001 and outputs/review-002 before updating outputs/latest.
- Specialized vertical exports are written under outputs/latest/exports/<profile-or-vertical>/ and do not replace the default project.md output.
- Software-specific exports such as software-spec, OpenSpec, or Spec Kit are represented as nested export profiles, not as the default output shape.
- Existing .p2p/outputs behavior is inventoried and either preserved, mirrored, deprecated, or migrated through an explicit compatibility path before any removal.
- Generated outputs clearly indicate that .p2p remains the managed source of truth and outputs/ contains generated human-facing artifacts.

## Decision

Pending.

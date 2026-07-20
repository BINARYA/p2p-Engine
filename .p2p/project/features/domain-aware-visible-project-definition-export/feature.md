# Domain-Aware Visible Project Definition Export

## Provenance

- Proposal: PROP-083
- Source: .p2p/proposals/PROP-083-domain-aware-visible-project-definition-export

## Problem

P2P Engine currently routes accepted project intent through Change Set software-spec and spec-export outputs. This makes every project look like a software implementation workflow, even when the project domain is not software. P2P Engine is meant to define projects in detail across many vertical domains, not only to produce software delivery artifacts. The current generated outputs are also hidden under .p2p/outputs, which makes the human-facing project definition hard for normal users to find and inspect. Users need a visible, comprehensive, domain-aware project definition that captures what emerged during proposal preparation, exploration, decisions, and refinement.

## Proposal

Introduce a domain-aware visible project definition export. The default export for every P2P project should be a human-facing, comprehensive Markdown document written to outputs/latest/project.md. The document should be organized in chapters and synthesize accepted P2P memory: project purpose, domain, problem framing, accepted proposals, decisions, requirements, scope boundaries, alternatives, tradeoffs, risks, assumptions, open questions, readiness notes, and relevant implementation or delivery context. The output should be generic across verticals and should not assume that the project is software. The visible root-level outputs/ directory is intentional and not configurable in the MVP because human accessibility is more important than keeping the repository root minimal; outputs/ is preferred over project/ because it clearly describes generated visible outputs and avoids confusion with .p2p/project. Each export run should preserve review history by writing or archiving prior versions under outputs/review-001, outputs/review-002, and later review directories. Domain-specific exports are additional nested profiles, not the default. For software-compatible projects, software-spec, OpenSpec, Spec Kit, or similar outputs may be generated under outputs/latest/exports/software-spec/, outputs/latest/exports/openspec/, outputs/latest/exports/speckit/, or equivalent profile folders. Other verticals may define their own export profiles under outputs/latest/exports/<profile-or-vertical>/. Existing .p2p/outputs behavior must be treated as a compatibility surface: the implementation should verify whether current generated artifacts are still needed, preserve public CLI/API expectations, and only remove, deprecate, or relocate legacy outputs through an explicit compatibility path.

## Decision

# Decision - PROP-083

## Status

`accepted`

## Outcome

accepted

## Event Type

accepted

## Effective State

accepted

## Reason

Owner accepts the domain-aware visible project definition export. Readiness has no missing gaps after refinement, but computed score remains partial because the current readiness profile is conservative and keeps confidence low for artifact-derived assessments.

## Date

2026-06-08

## Approver

mrjungle

## Owner

mrjungle

## Ledger Head

PDE-bd33295c27d038f9908d06e3

## Decision Fingerprint

a37fc92b9c79f93af6ebd0477c71587d879fbcc11b448341e28a1b87de4113ea

## Lineage

None.

## Canonical Source

decision-events.yml

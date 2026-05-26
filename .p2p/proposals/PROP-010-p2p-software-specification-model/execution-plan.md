# Execution Plan - PROP-010

## Objective

Define the P2P-native software specification layer that rationalizes accepted proposals before downstream export or implementation.

## Workstreams

### WS1 - Output Directory Model

Define `.p2p/outputs/` and distinguish generated/rationalized artifacts from source artifacts.

### WS2 - Software Specification Shape

Define a minimal Markdown-first software spec model:

- `index.md`
- `modules/<module>.md`
- `decisions-map.yml`

### WS3 - Refresh Workflow

Define how accepted proposals update output artifacts:

- MVP: explicit `p2p output refresh`
- later: optional automatic refresh after `decision record --outcome accepted`

### WS4 - Export Boundary

Define that OpenSpec and Spec Kit exporters consume P2P-native specs, not raw proposal folders.

## Implementation Notes

The first implementation should avoid AI invocation. It can generate deterministic output from accepted proposal metadata, decisions, plans, and tasks.

AI-assisted spec synthesis should remain prompt-only until the deterministic flow is stable.

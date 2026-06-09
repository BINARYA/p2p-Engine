# Risks - PROP-085

## Genericity Risk

If P2P Engine lacks vertical-specific structure, project readiness becomes too
generic. The system may check basic project hygiene but fail to guide the owner
toward domain-specific capisaldi, artifacts, and decisions.

Mitigation:
- require `base_project` plus at least one complete demonstration vertical;
- make project readiness review identify missing vertical coverage;
- instruct the agent to propose custom verticals when no suitable pack exists.

## Catalog Explosion Risk

Trying to create every possible vertical inside the core engine is not realistic.
It would be expensive, hard to maintain, and likely produce many shallow packs.

Mitigation:
- keep the default set small and high quality;
- support project-local custom packs;
- defer broad domain coverage to future registry/plugin data packs.

## Low-Quality Custom Pack Risk

Project-local custom verticals may be incomplete, inconsistent, or too tailored
to one conversation.

Mitigation:
- validate required fields;
- require sections/capisaldi, minimal rubrics, blocking questions, and expected
  artifacts;
- have the agent present the generated pack to the owner for confirmation before
  using it.

## Parallel Maturity System Risk

Vertical packs could accidentally create a second maturity/readiness model.

Mitigation:
- vertical packs must feed existing project rubrics and maturity/readiness;
- `p2p project readiness review` should reuse current assessment artifacts.

## Registry Prematurity Risk

Implementing a remote registry too early would add API, versioning, trust, and
distribution concerns before the local model is proven.

Mitigation:
- keep the MVP internal/project-local;
- design the schema to be registry-ready without implementing registry behavior.

## Agent Passivity Risk

If agent instructions are weak, the CLI may have valid pack data but agents may
still fail to push for capisaldi and initial questions.

Mitigation:
- add explicit project orchestrator skill guidance;
- make missing initialization/capisaldi a high-priority readiness concern;
- instruct the agent to return to deferred foundational questions unless muted
  by the owner.


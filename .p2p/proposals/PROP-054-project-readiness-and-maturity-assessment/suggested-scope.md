# Suggested Scope - PROP-054

## MVP Scope

- Add a deterministic assessment model for project readiness.
- Add CLI commands:
  - `p2p assess refresh`
  - `p2p assess show`
- Include factor-level output for:
  - validation status
  - registry freshness
  - draft/deferred/accepted proposal counts
  - open project choices
  - formal blockers
  - Change Set lifecycle status
  - Work item lifecycle status
  - operational brief availability and freshness
  - next-action availability
- Write a stable assessment artifact with score or status band, confidence, factors, gaps and suggested next actions.
- Add tests for deterministic scoring and command output.

## Stretch Scope

- Add project-type rubric file discovery.
- Generate rubric prompt artifacts.
- Add rubric import validation.
- Expose read-only assessment through MCP.

## Out Of Scope For First Change Set

- AI/provider invocation.
- Automatic governance decisions.
- Automatic blocking of proposals, choices, Change Sets or Work items.
- PR/MR creation or managed Git behavior.
- Hosted web assessment dashboard.
- Complex configurable weighting.

## Likely Execution Domains

- software
- governance metadata
- documentation

## Suggested Next Governance Step

Synthesize PROP-054 with Alternative B: deterministic readiness MVP first, rubric shape documented and deferred to a later Change Set unless the owner explicitly expands scope.

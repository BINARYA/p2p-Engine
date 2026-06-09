# Assumptions - PROP-085

- Vertical packs are pure data in the MVP, primarily `.yaml` and/or `.md`.
- `base_project` is a concrete pack with a default cross-domain structure, not
  only a conceptual fallback.
- Default packs are distributed internally with the project/package as versioned
  and testable resources.
- Project-local custom packs are allowed and take precedence over core defaults.
- The MVP introduces a project vertical CLI surface because the current CLI only
  exposes project domains/rubrics and does not yet list, show, add, or validate
  vertical packs.
- A future registry may expose REST endpoints for listing available packs and
  fetching pack details, but registry behavior is outside the first slice.
- The CLI remains deterministic and does not launch the agent.
- Agent proactivity is delivered through generated/local skills and project
  instructions.
- Vertical packs extend and reuse existing project rubrics and maturity/readiness
  artifacts.
- Backward compatibility is required for projects without vertical packs.
- The first slice can prove the architecture with one complete demonstration
  vertical rather than the later five-vertical MVP set.

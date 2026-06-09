# Findings - PROP-085

- Vertical specificity is necessary for useful project readiness. Without
  domain-specific sections, questions, and artifacts, P2P can only provide
  generic project hygiene and risks feeling banal.
- Full domain coverage inside the core engine is not viable. Creating and
  maintaining every possible vertical would be costly and would lower quality.
- Pure data packs are the right MVP boundary. They are inspectable, testable,
  versionable, and safer than executable plugin code.
- `base_project` should be the universal fallback and extension point. It
  provides common project sections while leaving room for vertical-specific
  specialization.
- The agent must be the proactive orchestrator. The CLI can persist state and
  run deterministic commands, but the agent must recognize weak initialization,
  propose capisaldi, ask owner questions, and return to deferred foundational
  project work when readiness is weak.
- Existing project rubrics and maturity/readiness should be reused. Vertical
  packs should feed structured evidence into the current system, not create a
  parallel maturity engine.
- Registry support should be deferred. The MVP should keep default packs internal
  and project-local overrides possible, while keeping the data model compatible
  with a future REST registry.
- The proposal must define `base_project`, not only the vertical mechanism.
  Without a concrete default structure, fallback behavior remains too abstract.
- Current P2P Engine code has project domains and project rubrics, but does not
  yet have pluggable vertical pack commands. The feature should add a dedicated
  `p2p project vertical ...` CLI surface for list/show/validate/propose/add.
- Example custom vertical candidates are useful as reference fixtures because
  they prove the model can adapt to unrelated domains without hardcoding every
  possible vertical.
- The long-term default catalog should be explicit, but not all of it belongs in
  the first implementation slice. The first slice proves the mechanism with
  `base_project` and one demonstration vertical; the next catalog milestone is
  `base_project` plus five verticals; the V1 default catalog is `base_project`
  plus roughly nine high-quality verticals.
- Profiles and modules reduce vertical proliferation. A profile specializes a
  vertical, while a module adds a cross-cutting concern such as security,
  accessibility, go-to-market, crowdfunding, education, or community building.
- Vertical packs become more useful when proposals are traceable to vertical
  sections/capisaldi. The project should be able to summarize the active
  vertical skeleton and show which proposals cover each point, which points are
  missing, and which proposals are unmapped.

## Tradeoffs

- Internal default packs improve reliability and testing, but reduce immediate
  ecosystem extensibility.
- Project-local custom packs make the system flexible, but require validation
  and agent guidance to avoid low-quality or inconsistent packs.
- A single demonstration vertical keeps scope controllable, but it must be
  complete enough to prove that the pack model works end to end.
- Deferring executable plugins limits advanced behavior, but avoids security,
  compatibility, and governance complexity in the MVP.
- Adding a vertical CLI surface increases implementation scope, but makes the
  model understandable and operational for agents and users.
- Naming the catalog roadmap makes future scope clearer, but the proposal must
  keep the first slice narrow enough to implement and validate.
- Proposal-to-vertical traceability adds modeling work, but it prevents the
  vertical from becoming a static template detached from governance decisions.

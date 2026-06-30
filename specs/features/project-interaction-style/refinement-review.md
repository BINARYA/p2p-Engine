# Refinement Review - Project Interaction Style

## Scope

This review refines accepted `PROP-087 - Agent Personality Model For Decision
Mediation` from an implementation and maturity perspective.

It does not reopen the owner decision, mutate P2P governance state, or propose
manual edits under `.p2p/`. It records the local technical assessment needed to
keep the proposal mature after implementation.

## Current Maturity

- P2P decision state: accepted.
- Readiness state: `decision_ready`, score `100`, confidence `high`.
- Local feature spec: present under `specs/features/project-interaction-style/`.
- Binding evidence: present in
  `specs/bindings/prop-087-project-interaction-style.md`.
- Implementation evidence: present in `src`, `tests`, and `docs`.
- Runtime validation: previous implementation note records full pytest and
  `p2p validate` success; current validation should still be used before
  release or merge decisions.

Maturity judgment: high for the accepted MVP scope.

## Recursive Review Passes

### Pass 1 - Governance And Proposal Fit

Finding: the proposal has a clear problem, explicit owner-facing goal, accepted
defaults, bounded public namespace, and explicit future extension points.

The strongest part of the proposal is the separation between communication
style and governance truth. Style changes how an agent speaks and follows up;
it does not change who decides, what evidence exists, readiness scoring,
validation, permissions, or consent.

Refinement outcome: no change needed to the accepted MVP scope.

### Pass 2 - Implementation Fit

Finding: the implementation matches the proposal through:

- core value objects and descriptors;
- a dedicated project interaction style service;
- CLI and MCP show/set surfaces;
- validation integration;
- compact context integration;
- generated agent instruction and policy integration;
- tests and docs.

The implementation follows the preferred architecture: domain rules live in
core/service code, while CLI and MCP layers delegate.

Refinement outcome: no implementation gap found for the MVP.

### Pass 3 - Alternative Model Review

Finding: several alternatives are plausible, but most would weaken the MVP if
included now because they add precedence, migration, UX, or safety complexity.

The accepted model remains the best first implementation: one project-level
default with three independent numeric scales.

Refinement outcome: keep the MVP stable; treat richer behavior as follow-up
proposals only when concrete use cases appear.

### Pass 4 - Future Evolution Boundary

Finding: the proposal already identifies per-agent and per-session overrides as
future extension points. The local spec should keep those boundaries explicit
so future work does not silently alter `PROP-087` semantics.

Refinement outcome: future extensions should be new specs/proposals with clear
precedence rules and compatibility tests.

## Alternatives Considered

### Alternative A - Project-Level Default Only

Description: store one project-level `interaction_style` used by all agents and
mediators unless future features add overrides.

Pros:

- Simple source of truth.
- Easy to expose through CLI, MCP, context, and generated instructions.
- Low migration risk for existing projects because missing state falls back to
  defaults.
- Avoids disagreement between agents about the owner's preferred interaction
  style.
- Keeps governance and communication boundaries easy to explain.

Cons:

- Cannot express different preferences per agent tool.
- Cannot express temporary session-level preferences.
- Requires the owner to change project state for every persistent adjustment.

Assessment: best MVP and current recommendation.

### Alternative B - Per-Agent Overrides

Description: keep project defaults, but allow agent-specific overrides such as
Codex, Claude, Cursor, Copilot, Gemini, or OpenCode.

Pros:

- Better fit for tools with different UX constraints.
- Allows a terse coding assistant and a more verbose planning assistant in the
  same project.
- Could reuse the existing agent integration registry as an ownership surface.

Cons:

- Needs precedence rules: project default vs adapter override vs generated
  instruction content.
- Adds migration and validation complexity to agent policy payloads.
- Risks turning style into hidden agent behavior if not surfaced clearly in
  context.
- Requires broader tests across every adapter template.

Assessment: good future proposal, not an MVP refinement.

Recommended acceptance criteria for future work:

- explicit override precedence;
- `p2p agent ...` or `p2p project interaction-style ...` namespace decision;
- context output showing both project default and effective agent override;
- tests for every supported adapter.

### Alternative C - Per-Session Overrides

Description: allow temporary style changes that affect a single session or MCP
client interaction without mutating project defaults.

Pros:

- Useful for short-lived collaboration preferences.
- Avoids project-state churn for temporary changes.
- Fits remote/cloud runners where local persistent writes may be undesirable.

Cons:

- Requires a session identity and lifecycle model.
- Harder to make observable in CLI-only workflows.
- Could confuse auditability if transcript behavior differs from project
  context.
- May conflict with generated static instructions unless surfaced in runtime
  context.

Assessment: valuable only after session/runtime identity is defined elsewhere.

### Alternative D - Persisted Named Presets

Description: store names such as `terse`, `balanced`, `pedantic`, or
`executive` instead of explicit numeric scale values.

Pros:

- More approachable for non-technical owners.
- Easier to present in an interactive UI.
- Can encode common combinations quickly.

Cons:

- The owner explicitly rejected persisted presets as source of truth.
- Presets hide independent scale values and make future dimensions harder.
- Preset semantics drift over time unless versioned.
- Agents may interpret labels inconsistently.

Assessment: do not persist presets. Non-authoritative helper labels in output
are acceptable.

### Alternative E - Adaptive Style From Conversation Behavior

Description: infer style from owner language, sentiment, or repeated correction
patterns.

Pros:

- Potentially ergonomic when the owner does not configure settings.
- Could reduce manual style tuning.

Cons:

- High risk of implicit profiling and unstable behavior.
- Hard to test deterministically.
- Could conflict with owner authority and explicit project state.
- Makes audit and reproducibility weaker.

Assessment: reject for this project unless a future proposal defines strict
consent, observability, and deterministic bounds.

### Alternative F - Reuse Readiness Assertiveness

Description: reuse existing readiness-derived `assertiveness_guidance` instead
of adding project interaction `assertiveness`.

Pros:

- Avoids introducing another similarly named concept.
- Keeps pressure tied to objective readiness gaps.

Cons:

- Conflates evidence/risk safety with owner communication preference.
- Cannot express an owner preference for more or less follow-up when readiness
  state is unchanged.
- Would let style preferences leak into proposal acceptance guidance.

Assessment: reject. The implemented separation is correct: readiness guidance
remains safety/evidence logic, while project assertiveness is communication
framing.

### Alternative G - More Dimensions In The MVP

Description: add additional scales such as brevity, empathy, challenge level,
initiative, explanation depth, or language preference.

Pros:

- More expressive.
- Could better match real human communication preferences.

Cons:

- Makes first-use configuration harder.
- Increases generated instruction verbosity.
- Requires more nuanced tests and docs.
- Some dimensions overlap with existing `technical_verbosity`,
  `formality`, or `assertiveness`.

Assessment: defer. Add dimensions only when a repeated concrete need appears.

## Recommended Mature Shape

Keep `PROP-087` as implemented:

- project-level default only;
- three independent numeric scales;
- explicit default values;
- CLI and MCP read/write surfaces;
- generated instructions and policy payload;
- compact context exposure;
- validation for malformed present state;
- no persisted named presets;
- no per-agent or per-session overrides in the MVP;
- no effect on governance, readiness truth, validation truth, permissions,
  consent, or factual claims.

## Follow-Up Proposal Candidates

Only these are worth considering as separate future proposals:

1. Per-agent interaction style overrides.
   Trigger: the owner needs different defaults for different adapter tools.

2. Session-scoped interaction style overrides.
   Trigger: the project has a defined session/runtime identity model.

3. Interactive style configuration helper.
   Trigger: owners repeatedly struggle to choose numeric values directly.

4. Additional independent style dimensions.
   Trigger: a concrete repeated communication need cannot be represented by the
   existing three scales.

## Non-Recommendations

Do not refine the current proposal by adding:

- persisted named presets;
- implicit sentiment/profile-based adaptation;
- hidden agent-specific defaults;
- readiness score or gate effects;
- direct `.p2p` edit workflows;
- broad generated-instruction prose beyond the concise shared block.

## Stop Condition

The refinement loop stops here because:

- P2P readiness is already high-confidence `decision_ready`;
- implementation evidence exists across code, tests, docs, and observed CLI
  behavior;
- alternative review did not reveal a missing MVP requirement;
- further changes would be new scope rather than refinement of `PROP-087`.

Final maturity judgment: high. The proposal should be treated as closed for
the accepted MVP and used as a baseline for future scoped proposals.

# Alternatives - PROP-054

## A - Deterministic Readiness Only

Implement only a Core/CLI readiness assessment from existing P2P state.

Benefits:
- Smallest reliable MVP.
- Fully deterministic and testable.
- Fits current Core/CLI/MCP boundary.

Costs:
- Does not answer broader quality or maturity questions.
- May feel too mechanical for non-software projects.

## B - Hybrid Model With Deferred Rubrics

Implement deterministic readiness now and define rubric artifact shape without scoring rubrics in the first Change Set.

Benefits:
- Preserves the full product direction.
- Avoids premature subjective scoring.
- Gives future AI-assisted review a stable import target.

Costs:
- Requires more design upfront than deterministic-only.
- Some rubric decisions remain open.

## C - Full Readiness And Rubric Assessment MVP

Implement deterministic scoring and domain maturity rubrics together.

Benefits:
- More complete user-facing assessment.
- Exercises prompt/import workflows early.

Costs:
- Higher risk of mixing objective state with subjective quality.
- More difficult acceptance criteria and test strategy.
- More likely to expand scope into AI review policy.

## D - Operational Brief Extension Only

Add readiness and maturity sections to the existing operational brief instead of creating assessment commands.

Benefits:
- Minimal new command surface.
- Reuses an existing project-level synthesis workflow.

Costs:
- Briefs can become stale and narrative-heavy.
- Harder to consume programmatically through CLI/MCP.
- Does not provide a stable assessment model.

## Preferred Direction For Synthesis

Alternative B is the strongest next direction: deterministic readiness in the MVP, rubric shape defined but rubric scoring deferred unless explicitly accepted later.

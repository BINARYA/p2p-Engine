# Alternatives - PROP-089

## Option A - Make `questions.yml` authoritative when present

Use structured question state as the primary source for
`owner_questions_resolution`. `open-questions.md` remains readable supporting
evidence, but no longer creates blocking gates when structured question state
exists.

Pros:

- Aligns implementation with the question workflow design.
- Avoids brittle markdown parsing.
- Makes applied answers matter immediately.
- Gives agents precise remaining question IDs and states.

Cons:

- Needs compatibility handling for proposals without `questions.yml`.
- Requires careful migration semantics for existing proposals.

## Option B - Keep markdown parsing but make it section-aware

Continue using `open-questions.md`, but count only questions under a strict
`Still Open` section and ignore `Answered` sections.

Pros:

- Small implementation change.
- Keeps existing artifact-oriented model.

Cons:

- Still fragile: headings and prose style can drift.
- Duplicates lifecycle logic that already exists in `questions.yml`.
- Does not solve divergence between structured state and markdown.

## Option C - Priority-weighted structured gating

Use structured questions as source of truth, and make only high-priority
unresolved questions hard blockers. Medium and low questions remain visible as
residual follow-up or confidence cautions.

Pros:

- Prevents readiness from staying blocked forever on non-critical follow-up.
- Matches the idea of stepped assertiveness.
- Keeps owner-visible caution without overstating blocker status.

Cons:

- Requires clear policy: when is a medium question still decision-blocking?
- Could be too permissive if agents classify questions too low.

## Option D - Manual owner override only

Keep current readiness logic and ask owners to override when readiness is
obviously too conservative.

Pros:

- No implementation cost.
- Maintains conservative behavior.

Cons:

- Normalizes false blockers.
- Weakens trust in readiness scores.
- Forces owners to use override for routine refinement completion.

## Recommendation

Combine Option A and Option C:

- when `questions.yml` exists, use it as the source of truth;
- unresolved high-priority questions are hard blockers;
- unresolved medium/low questions reduce confidence or appear as residual
  follow-up unless explicitly marked decision-blocking;
- legacy proposals without `questions.yml` keep the markdown fallback.


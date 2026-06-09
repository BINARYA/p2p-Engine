# Suggested Scope - PROP-089

## MVP

- Update readiness owner-question assessment to use `questions.yml` when
  present.
- Keep markdown fallback for legacy proposals without question state.
- Treat unresolved high-priority questions as hard blockers.
- Treat unresolved medium/low questions as residual follow-up or confidence
  cautions unless explicitly configured otherwise.
- Improve readiness review output with concrete remaining question IDs,
  priorities, and states.
- Add tests for applied, answered, to-answer, deferred, muted, retired, and
  superseded questions.

## Deferred

- Project-level configurable gate policy by question priority.
- Full migration of historical `open-questions.md` content into structured
  questions.
- UI-specific rendering of question state.


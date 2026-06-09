# Exploration - PROP-089

This proposal comes from the PROP-088 readiness review. The observed behavior is
not only that PROP-088 has residual questions; it is that readiness can remain
blocked even when an owner answer has been recorded, applied to artifacts, and
the structured question state knows the question is no longer open.

The implementation currently mixes two sources:

- `questions.yml`, which tracks question lifecycle states such as `to_answer`,
  `answered`, `applied`, `muted`, `defer`, `retired`, and `superseded`;
- `open-questions.md`, which is a human-readable artifact and may contain
  historical answered questions, recommendations, or headings.

That mix creates a fragile readiness gate. Markdown is useful for review, but it
should not override structured state when structured state exists.


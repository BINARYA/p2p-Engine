# Risks - PROP-089

- If structured question priority is misused, readiness could become too
  permissive.
- Existing legacy proposals may depend on markdown-only open question behavior.
- Agents may still write vague medium/low questions that hide important owner
  decisions unless guidance is clear.
- Group-level state could become stale if question transitions do not update it
  consistently.

Mitigations:

- Keep markdown fallback only when `questions.yml` is absent.
- Treat high-priority unresolved questions as blockers by default.
- Surface medium/low unresolved questions in review output and confidence
  reasons.
- Add focused tests for all question states and priorities.


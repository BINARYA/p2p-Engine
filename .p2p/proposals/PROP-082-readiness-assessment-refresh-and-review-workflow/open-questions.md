# Open Questions - PROP-082

## Product Questions

1. Should the main reassessment command be named `assess`, `review`, or should
   both exist with separate semantics?

   Current leaning: both. `assess` recomputes analytical readiness; `review`
   records human/owner confirmation of an assessment.

2. Should gate resolution be a standalone command?

   Current leaning: yes, because owner-question gates often require explicit
   human confirmation rather than automatic text analysis.

3. Should imported assessments be accepted from arbitrary agents?

   Current leaning: allow import only after schema validation and source/actor
   recording. The import is evidence, not autonomous governance decision.

4. Should low-confidence assessments ever promote `ready_for_decision`?

   Current leaning: no. Automatic readiness promotion should require score,
   minimum gates, and minimum confidence.

## Implementation Questions

1. What exact readiness assessment schema should be imported or persisted?
2. How should assessment history be recorded: overwrite latest snapshot, append
   history, or both?
3. Should gate resolution write to `readiness.yml`, decision audit, comments, or
   a dedicated assessment history artifact?
4. How should MCP permissioning work for assessment writes versus owner
   overrides?
5. How should existing bootstrapped readiness files migrate?


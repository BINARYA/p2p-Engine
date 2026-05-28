# Risks - PROP-054

- Risk: Users may treat a readiness score as an automatic approval or rejection.
  Mitigation: Label assessment as advisory, include explicit gaps, and keep governance decisions separate.

- Risk: A single number may hide important blockers.
  Mitigation: Always show factor-level results, blocking gaps and confidence alongside any score.

- Risk: The feature duplicates `p2p validate` or `p2p next`.
  Mitigation: Compose existing validation and next-action logic; do not create independent rule systems for the same signals.

- Risk: Rubric maturity becomes subjective and inconsistent.
  Mitigation: Require explicit criteria files, evidence fields and confidence values; treat AI output as importable advisory material only.

- Risk: The MVP scope expands into AI/provider integration.
  Mitigation: Keep Core deterministic; use prompt/import workflows for subjective review; defer mediator/provider behavior.

- Risk: Assessment artifacts become stale.
  Mitigation: Include generation metadata, source timestamps or registry freshness checks, and expose refresh/show behavior clearly.

- Risk: Poor weighting makes the readiness score misleading.
  Mitigation: Start with transparent rule bands and factor severity rather than complex weighted scoring.

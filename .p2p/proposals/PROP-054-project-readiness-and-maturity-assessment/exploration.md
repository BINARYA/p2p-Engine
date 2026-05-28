# Exploration - PROP-054

PROP-054 introduces a project assessment capability that sits above existing P2P state tracking. The core question is not whether P2P can compute another summary, but how to separate objective workflow completeness from subjective project maturity without making the score look like a governance decision.

The proposal naturally splits into two layers:

- Deterministic readiness: derived entirely from recorded P2P state, validation, registries, proposals, choices, blockers, Change Sets, Work items, specs and operational brief metadata.
- Rubric-based maturity: derived from explicit criteria files and optional prompt/import review workflows, with confidence and evidence attached to every scored dimension.

The deterministic layer is suitable for Core/CLI implementation first. It can be repeatable, testable and exposed through MCP as an advisory read-only or write-safe tool. The rubric layer should remain separate because it depends on project type, domain expectations and review judgment.

The main design pressure is score semantics. A single readiness number is useful for scanning, but it can mislead users if it hides blocking gaps or mixes completion with quality. The assessment output should therefore make the factors and gaps primary, with any score treated as a compact derived view.

The feature also overlaps with `p2p validate`, `p2p next`, operational brief generation, registries, and future MCP tools. It should reuse those signals rather than becoming a parallel validator or recommender.

Before synthesis, the proposal should decide the MVP boundary:

- Whether Level 1 ships as `p2p assess refresh` plus `p2p assess show`, or as a lighter `p2p assess show` that computes on demand.
- Which signals are included in the deterministic readiness model.
- Whether scores are percentages, levels, labels, or a combined score plus status bands.
- Where assessment artifacts live under `.p2p/`.
- Whether rubric maturity is deferred or included as prompt-only scaffolding in the first Change Set.

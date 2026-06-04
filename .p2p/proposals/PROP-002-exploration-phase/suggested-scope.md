# Suggested Scope - PROP-002

## Included

- Reframe PROP-002 from a narrow `explore` command proposal into a proposal
  exploration and readiness workflow.
- Keep the existing exploration artifacts as durable proposal memory:
  - `exploration.md`
  - `findings.md`
  - `alternatives.md`
  - `open-questions.md`
  - `risks.md`
  - `assumptions.md`
  - `suggested-scope.md`
- Keep authored proposal artifacts human-readable, while adding
  machine-readable readiness metadata, snapshots, registries, or exports.
- Define readiness as profile-based and versioned.
- Include a default readiness profile:

```yaml
readiness_profile:
  id: default-readiness-v0.1
  version: 0.1
  criteria:
    problem_clarity: 10
    goal_clarity: 10
    scope_boundaries: 10
    alternatives_quality: 15
    tradeoff_analysis: 10
    risk_coverage: 10
    assumptions_clarity: 10
    owner_questions_resolution: 10
    acceptance_criteria_quality: 10
    impact_overlap_analysis: 5
  thresholds:
    weak: 0
    partial: 70
    strong: 85
    decision_ready: 95
  gates: {}
  override_policy: {}
```

- Record `profile_id`, `profile_version`, and `computed_at` with every
  readiness assessment.
- Keep readiness separate from lifecycle state:
  - lifecycle state says where the proposal is procedurally;
  - readiness says how mature the proposal analysis is.
- Represent readiness with computed analytical fields and effective governance
  fields.
- Define tier classification and classify PROP-002 as governance-critical.
- Define minimum gates by tier so essential criteria cannot be compensated away
  by secondary strengths.
- Define artifact quality states and scoring caps:
  - missing: max 0%.
  - placeholder: max 0%.
  - thin: max 50%.
  - meaningful: max 75%.
  - needs_owner_input: max 75% and blocks automatic `ready_for_decision`.
  - ready: max 100%.
- Require criterion-level evidence for readiness scoring.
- Define threshold-driven agent behavior at 70, 85, and 95.
- Define confidence as evidence quality, not writing quality.
- Define governance gates as configurable:
  - warn
  - block_ready_for_decision
  - block_acceptance
  - allow_override
  - require_reason
- Define owner override as an audited governance event, not a score edit.
- Make `override_reason` mandatory when accepting below target readiness.
- Use acceptance-time override as the primary UX:

```bash
p2p proposal accept PROP-XXX --override-readiness --reason "..."
```

- Preserve accepted legacy proposals without rewriting history.
- Apply readiness to new proposals and open drafts.
- Include readiness in registries as a snapshot/cache, not as source of truth.
- Make `p2p next` report concrete proposal refinement gaps, failed gates, and
  highest-impact actions.
- Teach agent skills and MCP-facing workflows to interrogate proposals
  persistently and to say when a proposal is not methodologically ready.
- Expose MCP readiness reads to agents while making override/acceptance writes
  governance-gated and non-autonomous.
- Use a hybrid assessment model:
  - agent assesses criteria, evidence, confidence, and qualitative gaps;
  - CLI validates, caps, aggregates, gates, snapshots, and stores.

## Excluded

- Replacing owner governance decisions with an automatic score.
- Treating maturity 100 as automatic acceptance without owner action.
- Mutating `computed_score` to 100 when the owner uses an override.
- Allowing a high total score to hide failed minimum gates for important
  proposals.
- Allowing generic artifact text to earn full criterion points.
- Treating `needs_owner_input` as a weak/thin artifact rather than owner-gated
  progress.
- Forcing every small/routine proposal through the same heavy exploration depth
  as architectural or governance-critical proposals.
- Rewriting, invalidating, or retroactively blocking already accepted proposals.
- Requiring public package distribution changes.
- Building a web UI for proposal maturity.

## Possible MVP

1. Add versioned readiness profile support with `default-readiness-v0.1`.
2. Add proposal readiness assessment and reporting.
3. Compute or import criterion-level scores with evidence and notes.
4. Apply deterministic caps, gates, labels, thresholds, and aggregation.
5. Add confidence and confidence reasons.
6. Add tier suggestion/confirmation flow.
7. Add artifact quality states and caps, including `needs_owner_input`.
8. Add registry snapshots for readiness.
9. Update `p2p next` to use readiness gaps and highest-impact actions.
10. Update agent skill/MCP guidance for readiness-aware exploration.
11. Support owner acceptance below target only with explicit override reason and
    audit record.
12. Apply readiness to new proposals and open drafts; mark accepted legacy
    proposals without rewriting decisions.

## Deferred

- Strict blocking of all proposal acceptance below maturity threshold.
- Full historical backfill of all accepted proposals.
- Advanced numeric weighting UI.
- Cross-project maturity analytics.
- Optional future artifact states such as `blocked_by_dependency`, `stale`, and
  `superseded`.

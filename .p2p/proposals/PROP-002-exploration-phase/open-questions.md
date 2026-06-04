# Open Questions - PROP-002

## Resolved Product Decisions

These questions are no longer treated as open for the current direction of
PROP-002. They are recorded here as design decisions or MVP leanings.

1. `explore import` should support both a single file and a directory with named
   exploration artifacts.

   Current state: directory import is already supported by the CLI.

2. `findings.md` should remain human-readable Markdown.

   Exploration is primarily authored, reviewed, and discussed by humans and
   agents. Structured data should still exist, but as derived metadata,
   readiness snapshots, registries, or exports. Do not replace `findings.md`
   with mandatory `findings.yml`.

3. `explore status` should distinguish more than file existence.

   It should evolve toward artifact quality states:

   ```text
   missing
   placeholder
   thin
   meaningful
   needs_owner_input
   ready
   ```

   Optional future states such as `blocked_by_dependency`, `stale`, and
   `superseded` are deferred.

4. Agent skills and MCP-facing workflows must become methodologically strict.

   The agent is not sovereign, but it must behave as a method guardian: inspect
   readiness, identify missing alternatives, detect thin artifacts, surface owner
   questions, and avoid turning weak exploration into confident recommendations.

5. Readiness must be profile-based and versioned.

   The 10-criterion model is the first default profile, not a hardcoded forever
   model.

   ```yaml
   readiness_profile:
     id: default-readiness-v0.1
     version: 0.1
     criteria: []
     thresholds: {}
     gates: {}
     override_policy: {}
   ```

   Every computed score must record `profile_id`, `profile_version`, and
   `computed_at`.

6. The MVP readiness score uses a 0-100 default profile with explicit criteria
   and weights.

   | Criterion | Points |
   | --- | ---: |
   | Problem clarity | 10 |
   | Goal clarity | 10 |
   | Scope boundaries | 10 |
   | Alternatives quality | 15 |
   | Tradeoff analysis | 10 |
   | Risk coverage | 10 |
   | Assumptions clarity | 10 |
   | Owner questions resolution | 10 |
   | Acceptance criteria quality | 10 |
   | Impact and overlap analysis | 5 |
   | Total | 100 |

7. `Alternatives quality` should carry extra weight.

   It receives 15 points because the core observed failure is
   solution-first proposal writing.

8. PROP-002 is `governance-critical`.

   It defines how P2P Engine explores, evaluates, challenges, and moves future
   proposals toward decision.

9. Tier and maturity interact through `required_score_for_decision`, minimum
   gates, confidence, and artifact quality gates.

   A high total score is not enough for important proposals if essential
   criteria fail.

10. Artificial completeness should be countered with artifact quality gates and
    criterion-level evidence.

    A criterion cannot receive a high score unless supporting artifacts are at
    least `meaningful` and contain proposal-specific evidence.

11. `p2p next` must report readiness gaps and actionable next steps as part of
    the readiness-driven workflow.

    Useful output should include current score, target score, missing points,
    failed gates, and highest-impact actions.

12. Owner override must not falsify `computed_score`.

    Override creates a governance event and may set `effective_status:
    forced_ready` or `effective_score: 100`, but it must preserve the analytical
    computed score.

13. `override_reason` is mandatory when accepting below target readiness.

    Without a reason, override becomes indistinguishable from accidental bypass.

14. Governance gates must be configurable.

    The product model must support warning, blocking automatic
    `ready_for_decision`, blocking acceptance for critical governance violations,
    allowing override, and requiring reasons.

15. Low maturity should not simply be "warn" or "block".

    Default policy:

    ```text
    low maturity -> warning
    below required score -> strong warning
    failed minimum gates -> block automatic ready_for_decision
    owner override -> allowed with reason
    critical governance violation -> block acceptance
    ```

16. Acceptable owner override requires owner authority, explicit reason,
    acknowledgement of failed gates, computed score preservation, and audit
    event.

17. Legacy accepted proposals must not be rewritten or invalidated.

    New proposals and current open drafts should use readiness. Accepted legacy
    proposals should preserve historical decisions and may be marked or assessed
    retrospectively.

18. Small proposals should have a lightweight path, not a zero-governance path.

    Small proposals still need problem, goal, scope, acceptance criteria, and a
    lightweight risk check. They do not always need a full alternative matrix or
    deep risk register.

19. Analytical labels should be derived; owner decisions should create effective
    governance statuses.

    Example:

    ```yaml
    computed_label: partial
    effective_status: forced_ready
    owner_override: true
    ```

20. High score with low confidence should not automatically be
    `ready_for_decision`.

    Decision readiness requires score target, minimum gates, and required
    confidence. Governance-critical proposals should require at least medium
    confidence before automatic readiness promotion.

21. Proposal tier should be suggested by the agent/system and confirmed by the
    owner.

    The system should warn when the confirmed tier appears inconsistent with
    evidence.

22. Readiness should be required before implementation planning, but at a lower
    threshold than acceptance.

    Planning and decision are different gates.

23. Multi-criteria alternative comparison informs but does not automate the
    owner decision.

    The system may recommend an alternative with rationale and dissenting risks,
    but the owner selects the final option explicitly.

24. Readiness should apply immediately to all open drafts and all new proposals.

    Already accepted proposals should use legacy markers or optional
    retrospective assessment, not retroactive blocking.

25. Readiness should be included in registries as a snapshot/cache, not as the
    source of truth.

## Resolved Implementation Decisions

These are product-level implementation decisions for PROP-002, with progressive
implementation allowed. They should not be treated as temporary MVP shortcuts.

1. Storage should use a layered model.

   ```text
   readiness profile -> scoring rules
   proposal artifacts -> source material
   criterion assessment -> evidence and criterion-level score
   readiness snapshot -> latest computed result
   registry entry -> fast project-level lookup
   decision/audit log -> overrides and governance events
   ```

   `readiness.yml` stores the latest assessment and criterion evidence. It must
   not silently override proposal artifacts or decision records.

2. Readiness commands belong under proposal.

   Recommended command family:

   ```bash
   p2p proposal readiness PROP-002
   p2p proposal readiness refresh PROP-002
   p2p proposal readiness explain PROP-002
   ```

   `p2p explore status` remains focused on artifact quality.

3. Readiness override happens during owner acceptance.

   Primary command:

   ```bash
   p2p proposal accept PROP-002 --override-readiness --reason "..."
   ```

   A standalone readiness override command is not the primary model because it
   can imply that the computed readiness is being edited. Override is a
   governance decision, not score correction.

4. MCP is read-first and write/governance operations are permission-gated.

   MCP read tools are available to agents. MCP write/governance tools are part
   of the product model, but require explicit governance permission and must not
   be agent-autonomous.

5. Confidence is qualitative and hybrid.

   It is derived from evidence quality, unresolved owner questions, assumptions,
   realness of alternatives, risk clarity, and whether the assessment has owner
   review. It should not pretend to be a precise numeric formula in the first
   product model.

6. `p2p next` should rank readiness actions gate-first, then by recoverable
   points.

   Failed gates outrank raw point gain. Recoverable points still help estimate
   which action produces the most improvement.

7. Existing open drafts should be migrated as `not_assessed`.

   `p2p next` should surface readiness assessment as a recommended action
   instead of auto-generating noisy assessments for every draft.

8. Validation should be progressive.

   ```text
   schema/profile invalid -> error
   registry stale -> warning initially
   below threshold -> warning or policy gate
   failed gates -> block automatic ready_for_decision
   accept below threshold -> requires override reason
   ```

9. Artifact quality assessment should be hybrid and include `needs_owner_input`.

   Deterministic checks catch missing, placeholder, and obvious thin artifacts.
   Agent assessment classifies `meaningful`, `ready`, and `needs_owner_input`
   with evidence.

   `needs_owner_input` is not the same as `thin`: an artifact may be well formed
   but blocked because the owner must choose a policy, strictness level, or
   strategic direction.

10. Criterion evidence should use structured data plus Markdown notes.

    The assessment should be machine-readable enough for audit and `p2p next`,
    while remaining understandable to humans.

## Remaining Naming And Schema Details

These are no longer product direction questions. They are concrete naming,
schema, and sequencing details to settle during implementation planning.

1. Exact file paths for readiness profiles, proposal assessment files, registry
   snapshots, and audit events.

   Current leaning:

   ```text
   .p2p/config/readiness-profiles/default-readiness-v0.1.yml
   .p2p/proposals/PROP-XXX/readiness.yml
   .p2p/registries/readiness.yml
   decision/audit event for override
   ```

2. Exact MCP tool names.

   Current leaning:

   ```text
   p2p_proposal_readiness_get
   p2p_proposal_readiness_explain
   p2p_proposal_readiness_refresh
   p2p_proposal_readiness_list_gaps
   p2p_proposal_accept_with_override
   ```

3. Exact confidence labels and rule text.

   Current leaning:

   ```text
   low    -> mostly inferred, weak evidence, unresolved key questions
   medium -> sufficient evidence, some unresolved assumptions, usable for review
   high   -> strong evidence, owner questions resolved, alternatives compared, risks explicit
   ```

4. Exact estimated-gain ranking formula for `p2p next`.

   Current leaning:

   ```text
   priority =
     failed_gate_weight
     + recoverable_points
     + tier_importance
     + dependency_unblocking_value
   ```

5. Exact migration mechanics for existing open drafts.

   Current leaning: mark as `not_assessed`, and let `p2p next` recommend a
   readiness refresh when useful.

6. Exact validation severity per command and governance policy.

   Current leaning: strict schema/profile validation immediately, warnings for
   staleness and low readiness initially, hard gates only for automatic
   readiness promotion and missing override reason.

7. Exact deterministic heuristics for artifact quality.

   Current leaning: deterministic detection for missing, placeholder, and
   obvious thin artifacts; imported agent assessment for richer quality states.

8. Exact criterion-level evidence schema.

   Current leaning:

   ```yaml
   criteria:
     alternatives_quality:
       max_points: 15
       awarded_points: 11
       artifact_quality: meaningful
       evidence:
         - artifact: alternatives.md
           section: Alternative F - Hybrid Exploration And Readiness Model
       notes: "Alternative reali presenti, ma manca matrice comparativa completa."
   ```

9. Exact handling of the current unresolved-question counter.

   Current finding: `p2p explore status` may not reflect all implementation
   decision points. Future status/readiness logic should distinguish explicit
   questions, decision items, grouped subtopics, and artifact quality states.

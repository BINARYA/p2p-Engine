# Execution Plan

## Interpretation

PROP-100 is an umbrella architecture decision coordinated by one repository feature specification. It is not one indivisible Change Set. Every slice below has explicit dependencies, focused tests and an exit gate.

## Preparation

- Capture current context timing and structural scan/read counts.
- Freeze v1 schema, source-catalog, authority, relation, retrieval, budget and diagnostic policy versions in the feature.
- Record source inclusion/exclusion and consumer compatibility matrices.
- Establish a read-only before/after filesystem invariant.

## Slice Sequence

1. Domain, Sources And Proposal Decisions.
   Add typed contracts, versioned serialization, Source Catalog, immutable per-request snapshot, robust captured-text parsing, stable identity, content hashes, proposal claims, complete decision lifecycle, diagnostics and stateless facade. No public surface changes.

2. Authority And Topology.
   Add the policy resolver, source metadata resolution, decision precedents, bounded governance/project-definition constraints, typed nodes, relation vocabulary, Change Set reconciliation, related/impact/conflict/choice/vertical/Work normalization, evidence merge and cycle-safe adjacency.

3. Explainable Retrieval And Budgets.
   Add deterministic normalization, inverted indexes, proposal/idea candidates, explicit applicability, score contributions/caps, historical filters, tie-breaking, grouping, empty result, semantic budgets and golden/adversarial tests. No public consumer change yet.

4. Performance Remediation Gate.
   Profile the current context path, remove nested Change Set and other repeated scans confirmed by measurement, instrument source access and pass a representative scale fixture. Public integration is blocked until structural gates pass.

5. Context Packet, CLI And MCP.
   Add versioned `nearby_context` for supported proposal targets, preserve legacy fields and non-proposal behavior, and update CLI text, structured output and MCP payload tests together.

6. Intake And Proposal Prompts.
   Replace first-N semantic context with bounded idea/proposal retrieval for intake, explore, impact and synthesize while preserving controlled apply and owner authority.

7. Next Actions And Projections.
   Route choice/relation semantics through the typed model. Keep `relations.yml` a legacy derived projection in PROP-100 and never read it back as semantic input.

8. Freshness And Manifests.
   Add source/semantic fingerprints, injected observational time and stale diagnostics for materialized consumers. Ordinary index build remains in memory and read-only.

9. Cache Decision.
   Measure build/query time and index size. Record `cache_deferred` or require a separate cache feature. Do not implement persistent cache in PROP-100.

## Delivery Gates

- Slice 1 must prove one read/hash/parse per proposal/decision source and no stale snapshot in the same workspace.
- Slice 2 must prove complete authority lifecycle, valid typed targets, evidence deduplication and cycle termination.
- Slice 3 must prove score arithmetic, applicability, empty results, deterministic order and exact feature-defined budgets.
- Slice 4 must prove one discovery pass, no nested full scans, zero retrieval I/O and the scale ceiling.
- Slice 5 requires Slice 3 and Slice 4 to pass and must preserve non-proposal public behavior.
- Slices 6 and 7 must prove controlled-apply and registry-projection boundaries.
- Slice 8 must prove source/policy changes affect freshness while `generated_at` does not affect semantic identity.
- Slice 9 cannot add cache code.

## Verification

- Parser table tests for line endings, headings, code fences, malformed frontmatter and legacy placeholders.
- Authority tests for all decision outcomes, precedents, choices, readiness, artifact state, questions and Work state.
- Topology tests for typed nodes, aliases, invalid targets, duplicate evidence, Change Set divergence and cycles.
- Retrieval golden and adversarial tests for scoring, false positives, historical context and budget truncation.
- Metamorphic tests for filesystem order, repeat builds, policy changes and same-workspace freshness.
- Performance tests for scan/read counts and the representative scale fixture.
- CLI text/structured and MCP payload parity tests, including unchanged Change/Choice/Work/no-target behavior.
- Intake/prompt controlled-apply and next-action semantic regressions.
- Read-only filesystem snapshot checks and full/public project validation.

## Handoff Rule

The detailed implementation source is `specs/features/prop-100-decision-context-index/`. Proposal artifacts retain architecture invariants, boundaries and slice gates; implementation constants and task-level evidence remain in that feature to avoid duplicated mutable specifications.

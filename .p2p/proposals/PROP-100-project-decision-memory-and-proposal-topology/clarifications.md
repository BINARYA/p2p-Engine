# Clarifications

## Decision Readiness

PROP-100 is decision-ready as an umbrella architecture direction. It is not authorization to deliver every implementation slice as one Change Set. The repository feature specification may coordinate the whole program, but each slice remains independently gated, testable and reviewable.

## Source Of Truth And Source Catalog

Governed proposal, decision, choice, Change Set, Work, project-definition and explicitly cataloged governance artifacts remain authoritative according to their domain role. The decision context index is derived and read-only. Registries, decision maps, generated project narratives, prompts, publications and caches are explicitly excluded as semantic source material.

## Service And Session Lifetime

`ProjectDecisionContextService` is a stateless facade. A memoized service object must create a fresh request-scoped snapshot for every index build. Hashing and parsing use the same captured bytes; each selected source is discovered once and read, hashed and parsed at most once per build.

## Identity And Completeness

Stable identity derives from normalized source path, owner, record kind and semantic fragment anchor. Content hash and source span are separate evidence metadata. Source and index completeness use `complete`, `partial` and `unavailable`; malformed optional sources cannot silently produce apparently complete context.

## Authority Boundary

Canonicality, authority, activation, confidence and completeness are distinct. The complete decision lifecycle must be represented. `accepted_with_changes` is active but qualified by its reason. Rejected, deferred, split, merged and superseded proposals remain historical or lineage context. Decision evidence controls derived decision authority when proposal status diverges, but the service never repairs source files.

Decision precedents have explicit project-wide precedent authority, not accepted-proposal authority. Readiness and artifact state describe evidence quality. Questions and contributions are advisory until applied to canonical text. Work status is execution context and does not change proposal authority.

## Relation Boundary

Topology uses typed nodes. A relation stores source, relation type and target. Incoming/outgoing direction is computed relative to a query and is not a second inverse edge. Equivalent assertions merge evidence without multiplying score. Unsupported types and invalid targets remain diagnostics. Change Set lineage sources are reconciled with explicit precedence and divergence diagnostics. Traversal is cycle, depth and fan-out bounded.

## Retrieval Boundary

Retrieval is deterministic, explainable and source-free after index construction. Policy versions define lexical normalization, ubiquitous-term handling, candidate limits, applicability, score contributions/caps, historical thresholds, tie-breaking, grouping and budget limits. Acceptance status alone does not broadcast a decision to every query. Empty result never falls back to first-N records.

## Query And Compatibility Boundary

Proposal ID and idea text are the first retrieval inputs. The first public integration enriches only supported `PROP-*` targets. Change, Choice, Work and no-target behavior remain unchanged until separately specified. CLI text, structured output and MCP share selection semantics even when rendering differs.

## Freshness Boundary

Source fingerprints include catalog version plus sorted path, presence and captured-byte hash. Semantic fingerprints also include extractor, authority and relation-policy versions; retrieval packets identify retrieval and budget-policy versions. `generated_at` is injected observational metadata and is excluded from semantic equality.

## Timeout And Performance Boundary

The pre-existing `p2p context` timeout can remain a separate bug fix, but PROP-100 owns the integration gate that prevents new semantic context from compounding it. Before public integration there must be one discovery pass, at most one read/hash/parse per source, no nested full scans and zero filesystem reads during retrieval, plus a representative scale ceiling.

## Cache Boundary

The first implementation has no persistent decision-context cache. Measurements end in either `cache_deferred` or `separate_cache_feature_required`. The latter requires a new specification for path, atomicity, locking, invalidation, migration, corruption, cleanup and rebuild.

## Feature Boundary

The repository feature may describe all dependent slices so contracts remain coherent. Delivery remains incremental: domain/sources, authority/topology, retrieval, performance gate, public context, intake/prompts, next actions/projections, freshness and cache decision. The first slice changes no CLI, MCP, intake, prompt, registry or storage surface.

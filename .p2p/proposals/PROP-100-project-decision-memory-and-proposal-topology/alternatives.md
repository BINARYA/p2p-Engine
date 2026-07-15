# Alternatives

## Deliver The Whole Specification In One Change Set

One repository specification is useful for coherent contracts, but implementing every slice together would combine parsing, authority, topology, retrieval, performance, public context, prompts and freshness in one blast radius. The selected approach keeps one specification and independent delivery gates.

## Add More Fields To Existing Registries

This improves immediate output but keeps consumers coupled to lossy projection shapes and risks a semantic feedback loop. Registries remain derived compatibility views; the index reads governed sources directly through a Source Catalog.

## Persist An Index First

SQLite or another cache may later reduce rebuild cost, but persistence does not solve source authority, duplicate relations, applicability, parser loss or retrieval quality. The selected approach measures an in-memory model first and requires a separate cache feature if needed.

## Use Embeddings First

Embeddings may improve recall later but do not explain authority, applicability, conflict state or stale evidence. Deterministic versioned retrieval remains the first contract.

## Assemble More Files Directly In Prompts

Prompt-only context would duplicate selection logic across agents and could amplify tokens without stable provenance. Retrieval selects and explains context before phase-specific prompt assembly.

## Reuse Publication Fingerprints Directly

Publication fingerprinting is a useful pattern, but publication inputs include derived outputs and are not the decision-context source set. Decision context uses its own versioned Source Catalog and semantic-policy fingerprint.

## Store Query Direction As Duplicate Edges

Persisting incoming and outgoing copies simplifies some reads but duplicates identity and score. The selected topology stores one logical relation and computes direction relative to the query.

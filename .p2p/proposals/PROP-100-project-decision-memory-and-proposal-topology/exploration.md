# Exploration

## Revised Direction

The refined repository feature confirms the original diagnosis: P2P does not first need a new canonical store. It needs a loss-aware derived semantic layer over existing governed sources. The new evidence strengthens the proposal by making source discovery, parser behavior, service lifetime, decision lifecycle, topology and retrieval applicability explicit.

## Architecture Shape

The implementation should use a stateless facade over independently testable source, extraction, authority, topology, retrieval and freshness collaborators. One immutable source snapshot is built per request. A single repository feature can coordinate all slices, but each slice remains an independent delivery gate rather than one broad Change Set.

## Source Boundary

A versioned Source Catalog is required. It includes canonical semantic sources, governed imported evidence, quality metadata and execution state according to explicit policy. It excludes registries, decision maps, generated project narratives, prompts, publications and caches to prevent feedback loops and duplicate authority.

## Semantic Boundary

Canonicality, authority, activation, confidence and completeness are separate dimensions. The complete decision lifecycle and project-wide precedents must be represented. Readiness and artifact state remain evidence-quality signals. Work remains execution context. Similarity remains a retrieval reason unless explicit evidence asserts an edge.

## Delivery Boundary

The first implementation slice remains domain/source/proposal-decision extraction with no public integration. Authority/topology and retrieval follow. Context packet integration is blocked by a performance-remediation gate. Cache persistence is not part of PROP-100 and requires a separate feature if measurements justify it.

## Evidence Source

Detailed implementation contracts, numeric policies and operational tasks live in `specs/features/prop-100-decision-context-index/`. PROP-100 retains architecture invariants, governance boundaries and slice acceptance gates.

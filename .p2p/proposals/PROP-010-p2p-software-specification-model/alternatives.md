# Alternatives - PROP-010

## Alternative A - Export raw proposals directly

Export each accepted proposal directly to OpenSpec or Spec Kit.

Pros:

- Fast to implement.
- Simple mental model.
- Useful for small software-only proposals.

Cons:

- Leaks governance/discussion artifacts into implementation specs.
- Forces each exporter to understand P2P proposal complexity.
- Poor fit for proposals that are methodological, strategic, or mixed-domain.

## Alternative B - Generate P2P-native software specs first

Generate a normalized software specification under `.p2p/outputs/software-spec/`, then export that normalized model to external targets.

Pros:

- Keeps P2P as source of truth.
- Makes exporters simpler and more reliable.
- Separates decision history from implementation-facing specs.
- Supports future internal task tracking.

Cons:

- Requires defining a new P2P spec model.
- Adds one more transformation step.

## Alternative C - Adopt OpenSpec or Spec Kit as the internal model

Use OpenSpec or Spec Kit as the primary specification format and treat P2P as a proposal intake layer.

Pros:

- Reuses existing conventions.
- Faster path to software implementation.

Cons:

- Makes P2P dependent on a downstream tool.
- Weakens P2P's multi-domain and governance-first identity.
- Makes non-software proposals awkward.

## Preferred Direction

Alternative B. P2P Engine should generate a neutral internal software specification first, then export downstream selectively.

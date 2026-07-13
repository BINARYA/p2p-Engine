# Alternatives - PROP-060

## Alternative A: No Coverage Tooling

Keep the current marker-based validation tiers and do not add coverage integration.

Benefit: no new dependency and no new command surface.

Cost: maintainers still cannot measure which runtime modules or branches are unexercised by selected tests.

Assessment: viable but weaker than the preferred option because it preserves the observability gap.

## Alternative B: Advisory Terminal Coverage Diagnostic

Add a development-only coverage integration such as `pytest-cov` and document a terminal missing-lines report for `src/p2p_engine`.

Benefit: gives maintainers useful visibility into unexercised code while keeping existing test tiers and validation scripts intact.

Cost: adds a small development dependency and a diagnostic command that must be documented carefully to avoid misuse.

Assessment: preferred option.

## Alternative C: Mandatory Coverage Threshold In CI

Add coverage and immediately enforce a fail-under threshold in CI.

Benefit: creates a clear numeric gate.

Cost: premature without a baseline, likely to make the percentage too central, and may incentivize tests that raise coverage without improving targeted regression confidence.

Assessment: reject for the first slice; it can be reconsidered only after maintainers have a baseline and know which gaps matter.

## Preferred Tradeoff

Choose Alternative B. It gives real diagnostic value without pretending that coverage is a quality score, release gate, or deterministic routing mechanism.

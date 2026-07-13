# Risks - PROP-060

## R001: Coverage Becomes A False Quality Score

Coverage can be misread as proof that the test suite is good. It only reports code execution, not assertion strength, public contract protection, or business correctness.

Mitigation: document coverage as optional diagnostics only and avoid an initial fail-under threshold.

## R002: Coverage Is Confused With Test Routing

Coverage can show which code a test run exercised, but it cannot determine which tests are necessary after a future change.

Mitigation: keep deterministic test selection in `PROP-098` and explicitly state that `PROP-060` does not solve routing.

## R003: Tooling Adds Process Cost

A coverage plugin adds a development dependency and another command for maintainers to understand.

Mitigation: keep the first slice to a standard pytest integration and one terminal report command.

## R004: Mandatory Threshold Is Premature

Without a baseline, a global fail-under threshold could create noise or incentivize superficial tests.

Mitigation: exclude fail-under gates, HTML reports, and CI blocking from the initial proposal.

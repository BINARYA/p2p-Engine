# Risks - PROP-016

## R1 - Registry Drift

Risk:

Generated registries can diverge from source artifacts.

Mitigation:

Treat registries as derived and refreshable. Add `p2p registry refresh` and make drift detectable with `p2p registry status`.

## R2 - Source Of Truth Confusion

Risk:

Users or agents may edit registries directly and treat them as primary data.

Mitigation:

Mark registries as generated. Source artifacts remain proposals, decisions, changes, governance and project files.

## R3 - Large Diffs

Risk:

Refreshing registries may create broad diffs.

Mitigation:

Use typed registries and stable sorting.

## R4 - Premature Schema Complexity

Risk:

Overdesigning registry schemas may slow MVP progress.

Mitigation:

Start with minimal fields required by current CLI workflows.

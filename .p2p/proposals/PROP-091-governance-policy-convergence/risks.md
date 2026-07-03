# Risks - PROP-091

## R001 - Reintroducing Hidden Enforcement

Risk: governance preflight could become de facto enforcement if warnings are
treated as blocks.

Mitigation: distinguish `warnings`, `blocking_errors`, and `result.status`
clearly. Vote disagreement and related precedents remain non-blocking.

## R002 - Bypassing Owner Authority Through MCP

Risk: MCP decision tools could allow agents or external clients to finalize
choices without owner intent.

Mitigation: phase 1 MCP is read-only or low-risk. Mutating and finalization
tools are deferred.

## R003 - Ambiguous Actor Authority

Risk: `roles.yml`, `permissions.yml`, CLI `--role`, and actor strings could
disagree.

Mitigation: use `permissions.yml` as primary when available, preserve
`roles.yml` as fallback/legacy, and warn on mismatches.

## R004 - Non-Deterministic Precedent Matching

Risk: fuzzy matching or AI search could make preflight unstable and
version-dependent.

Mitigation: core precedent lookup uses only explicit identifiers and declared
tags from versioned artifacts.

## R005 - Overbuilding Governance

Risk: adding quorum, weights, delegation, or automatic enforcement too early
would make the system heavier than the current need.

Mitigation: explicitly exclude full democratic enforcement from this proposal.

## R006 - Schema Drift Across CLI, MCP, And Future UI

Risk: each surface may represent governance preflight differently.

Mitigation: define a versioned preflight output contract and reuse the same
domain result across CLI, MCP, and future UI rendering.

## R007 - Legacy Repository Compatibility

Risk: older repositories may have governance artifacts without modern
permissions or preflight metadata.

Mitigation: use soft migration behavior and distinguish missing optional
artifacts from corrupt present artifacts.

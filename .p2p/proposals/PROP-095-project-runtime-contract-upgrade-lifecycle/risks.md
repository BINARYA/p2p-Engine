# Risks And Mitigations

## Runtime Contract Update Becomes A Write-Gate Bypass

PROP-095 must allow a controlled contract change even when the active runtime is
about to become incompatible. If this exception is too broad, it can become a
general-purpose bypass for governed writes.

Mitigation: only `p2p runtime contract apply` may use the exception, only for
the coordinated contract update, and only after preview, expected-state
verification, owner authority, confirmation, and required reason checks.

## Hidden Mutations After Activating An Incompatible Contract

If `runtime.yml` is replaced before all required outputs are written, subsequent
mutations may happen after the active runtime is outside the new compatible
range.

Mitigation: prepare and validate all output before mutation, write the managed
setup guide before the contract, write `runtime.yml` last, and perform no
further governed mutations afterward.

## Expected-State Token Misunderstood As Authorization

The preview token could be mistaken for owner consent or actor authorization.

Mitigation: token semantics are limited to stale-state protection. `apply`
always performs a fresh authority check and does not rely on the preview's
authority assessment.

## Agent Or Non-Owner Preview Leaks Permission Details

Read-only preview is intentionally available to agents and collaborators, but it
must not expose unnecessary authority structure.

Mitigation: preview reports whether apply appears authorized or blocked, without
listing privileged actors or internal permission details.

## Human-Owned Setup Guide Is Overwritten

`P2P-SETUP.md` may predate P2P management and contain human-owned instructions.

Mitigation: if the stable P2P-managed marker is absent, `apply` is blocked before
any mutation. PROP-095 does not adopt, replace, merge, back up, or overwrite the
file.

## Managed Setup Guide Drift Is Ignored

A drifted managed guide can mislead collaborators if the runtime contract is
updated without regenerating it.

Mitigation: a true contract update may repair managed-guide drift in the same
coordinated operation, and the preview token binds the current guide content or
digest. A drift-only no-op remains outside this feature.

## Invalid Or Missing Current Contract Produces Unsafe Comparison

Impact labels such as `range_tightening` require a trustworthy current
contract.

Mitigation: preview may validate the proposed values in diagnostic mode, but it
does not produce an applicable token, mutation plan, or full transition impact
classification when the current contract is invalid, unsupported, missing, or
legacy undeclared.

## Range Classification Is Too Textual

Textual range comparisons can misclassify equivalent or partially overlapping
ranges.

Mitigation: classification is based on accepted version sets using the supported
PEP 440-compatible range grammar. Partially overlapping or disjoint ranges can
produce both `range_widening` and `range_tightening`.

## Partial Writes Leave Contract And Guide Inconsistent

Filesystem failure during apply can leave one artifact updated and the other
stale.

Mitigation: apply uses coordinated write semantics, temporary content, stale
checks before mutation, contract-last replacement, and handled failures that do
not start mutation after a blocker is detected.

## Release Availability Metadata Is Stale

Release availability checks may be unavailable or stale.

Mitigation: release availability is informational. The command may report
`unverified` without blocking an otherwise valid update.

## Reason Requirements Are Inconsistent

Too many mandatory reasons create friction; too few reduce accountability for
breaking changes.

Mitigation: reasons are mandatory for `range_tightening`, runtime-line changes,
and updates where the active runtime is excluded. Normal `recommended_only`
updates do not require a reason.

## Optional Decision Links Create Ambiguous Governance

If decision links are optional, readers may assume the operation is not governed.

Mitigation: the proposal states that owner authority, confirmation, reason where
required, token verification, and audit reporting govern the operation. Decision
links are optional traceability, not a prerequisite.

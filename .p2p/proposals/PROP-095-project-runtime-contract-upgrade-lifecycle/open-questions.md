# Closed Questions

All owner questions needed for synthesis are closed.

## Q001 - Scope

PROP-095 updates the project runtime contract and generated setup guidance. It
does not install or upgrade P2P Engine.

## Q002 - Governance Model

Runtime contract updates are owner-controlled governed operations. A linked P2P
decision is optional, not mandatory.

## Q003 - Command Shape

The public surface uses separate `preview` and `apply` commands.

## Q004 - Release Availability

Release availability is best-effort and informational. `unverified` is not a
blocking result for an otherwise valid contract.

## Q005 - Preview And Apply Split

Preview is read-only and apply is the only mutation path.

## Q006 - Current Runtime Incompatibility

Apply may execute the narrowly authorized contract update even when the active
runtime is currently outside the old range or will be outside the new range, but
it must not use that exception for other governed writes.

## Q007 - Release Metadata Boundary

The feature consumes available release metadata but does not own release
publication.

## Q008 - CLI Surface

`p2p runtime contract preview` and `p2p runtime contract apply` are the stable
commands for this feature.

## Q009 - Authority During Preview

Preview does not require owner authority. Apply performs a fresh binding
authority check.

## Q010 - Unmanaged Setup Guide

An unmanaged `P2P-SETUP.md` blocks apply before mutation. Adoption or replacement
is out of scope.

## Q011 - Untrusted Current Contract

Preview may validate proposed values diagnostically, but cannot produce an
applicable token or mutation plan when the current contract is untrusted.

## Q012 - Token Semantics

The expected-state token is deterministic, stateless, and replayable as a stale
state guard. It is not authorization or consent.

## Q013 - Recommended-Only Updates

`recommended` may change independently when it remains inside `requires`.

## Q014 - Managed Setup Guide Drift

Managed guide drift may be repaired during a true contract update, but drift-only
repair is a separate capability.

## Q015 - Partially Overlapping Ranges

Range classification is set-based. Partial overlaps and disjoint ranges can
produce both widening and tightening.

## Q016 - Post-Update Incompatibility

When the new contract excludes the active runtime, `runtime.yml` is written last
and no further governed mutations occur afterward.

# P2PWorkspace Dead Filesystem Helper Cleanup Design

## Current State

`storage.filesystem` still contains helpers that were used before extraction but
are now owned by services or no longer called:

- permission/consent constants and normalizers;
- legacy permission payload builder;
- legacy proposal markdown and exploration file renderers;
- legacy status replacement helper;
- unused formatting helpers supporting removed renderers;
- unused proposal id parser;
- unused conflict marker helper.

## Target State

Remove the dead helper block from `storage.filesystem`, leaving only helpers
with active callers in the facade.

## Compatibility

The cleanup is non-behavioral. Equivalent active logic already exists in
extracted services such as `permissions`, `consent`, `proposals`,
`proposal_branches`, and `work_branches`.

## Verification

Use `rg` to confirm no stale references remain, then run focused tests for the
affected service areas, `p2p validate`, and the full pytest suite.

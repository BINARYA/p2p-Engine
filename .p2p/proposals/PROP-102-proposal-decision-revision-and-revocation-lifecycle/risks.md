# Risks

## R001 - Status Explosion

Adding too many terminal states can make CLI output and downstream policy hard
to understand.

Mitigation: keep a small public vocabulary, define exact meanings and separate
event type, effective authority and downstream remediation state.

## R002 - Partial Migration

Some consumers may continue reading only the legacy current status and ignore
event history.

Mitigation: centralize lifecycle authority, inventory every consumer, version
the projection and add compatibility and cross-consumer contract tests.

## R003 - False Rollback

Users may interpret `revoked` as proof that implemented behavior was removed.

Mitigation: report decision authority and implementation/remediation state
separately; never auto-complete rollback work.

## R004 - Concurrent Decisions

Two owner operations based on the same prior event could create conflicting
heads.

Mitigation: source-bound preview tokens, expected-head checks, idempotency keys,
locking and atomic replacement.

## R005 - History Mutation

A generic update or migration path could rewrite or reorder old events.

Mitigation: immutable event identities, content hashes, append-only validation,
explicit repair diagnostics and no silent normalization.

## R006 - Broken Replacement Lineage

Supersession may refer to a missing, rejected or incompatible replacement.

Mitigation: validate target identity and lifecycle, represent pending
replacement separately and prevent active lineage claims without direct
evidence.

## R007 - Authority Bypass

CLI and MCP implementations may diverge or allow an agent-controlled actor field
to simulate owner authority.

Mitigation: one domain service, canonical role resolution, consent binding and
equivalence tests across every privileged operation.

## R008 - Compaction Hides Reversal

A later thematic summary could retain the accepted claim while omitting its
revocation.

Mitigation: make event head, authority interval, replacement lineage and source
fingerprint mandatory inputs to consolidation freshness.
